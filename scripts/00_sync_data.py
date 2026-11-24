"""Sync pipeline data files between local disk and Cloudflare R2.

Three sync sets (R2 prefix <-> local directory):

- ``manual/``   <-> ``data/manual/``  — full tree of manual source
  CSV/GeoJSON data (~52 files, ~123MB).
- ``geocache/`` <-> ``data/cache/``   — flat OneMap geocode cache entries
  only (``*.parquet`` / ``*.json`` at the cache root; ~14k entries, ~92MB).
  The Hamilton node cache under ``data/cache/hamilton/`` is deliberately
  excluded: it is keyed by code/config fingerprints, invalidated by any
  code change, and fully regenerable — syncing it buys nothing.
- ``evidence/`` <-> ``data/pipeline/`` — **opt-in only** (`--only evidence`):
  exactly the pipeline artifacts the read-only evidence producers
  (``scripts/tools/*_evidence.py``) re-measure, enumerated one path at a time in
  :data:`EVIDENCE_FILES`. Nothing else under ``data/pipeline/`` is ever uploaded
  or downloaded, and the set is excluded from the default run so it never
  starts moving ~110MB on a routine sync. This is narrow CI provisioning (see
  ``.github/workflows/evidence.yml``), not a pipeline-data backup.

Every remote key is mapped to a local path by one containment resolver
(:func:`_resolve_local_target`). Keys that cannot be proven to stay inside
their sync root are rejected *before* any transfer is submitted.

Uploads and downloads are idempotent, but the default skip is a **size
pre-filter only**: a file whose remote size already matches is skipped
without comparing bytes. That is fast but can miss equal-size content
changes. ``--verify`` reports ``SIZE-OK (CONTENT-UNVERIFIED)`` rather than
``OK``; ``--verify-content`` downloads and compares bytes (or a SHA-256
recorded as object metadata at upload time) for the selected scope.

Usage:
    uv run python scripts/00_sync_data.py                  # download (default)
    uv run python scripts/00_sync_data.py --upload          # upload local to R2
    uv run python scripts/00_sync_data.py --verify          # size-only compare
    uv run python scripts/00_sync_data.py --verify-content  # compare bytes
    uv run python scripts/00_sync_data.py --upload --only geocache
    uv run python scripts/00_sync_data.py --only evidence   # CI: evidence inputs
"""

import argparse
import hashlib
import sys
import tempfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from egg_n_bacon_housing.config import settings

MANUAL_DATA_DIR = settings.data_dir / "manual"
CACHE_DIR = settings.data_dir / "cache"
PIPELINE_DATA_DIR = settings.data_dir / "pipeline"

MANUAL_PREFIX = "manual"
GEOCACHE_PREFIX = "geocache"
EVIDENCE_PREFIX = "evidence"

# The pipeline artifacts the evidence producers are allowed to read, as paths
# relative to ``data/pipeline/``. ``.github/workflows/evidence.yml`` fails closed
# on exactly this list, so the two must stay in lockstep. Enumerated on purpose:
# a whole-tree ``data/pipeline/**`` sync would push ~4GB of regenerable bronze
# and per-run outputs plus every experiment scratch file to R2, while the
# producers only ever open these seven files.
EVIDENCE_FILES: tuple[str, ...] = (
    "04_platinum/unified_dataset.parquet",
    "01_bronze/raw_hdb_rental.parquet",
    "02_silver/geocoded_validated.parquet",
    "01_bronze/raw_hdb_resale.parquet",
    "01_bronze/raw_condo_transactions.parquet",
    "01_bronze/raw_school_directory.parquet",
    "01_bronze/raw_mrt_stations.parquet",
)

# Bounded transfer concurrency for the ~14k-file geocache set; boto3 clients
# are thread-safe for operations.
_TRANSFER_CONCURRENCY = 16

# Metadata key used to record a per-object content hash at upload time. R2 (like
# S3) supports user metadata, so verification can compare this instead of
# re-downloading the bytes. Providers that drop metadata simply fall back to a
# byte comparison in ``--verify-content``.
_CONTENT_HASH_METADATA_KEY = "sha256"


class KeyRejectedError(ValueError):
    """A remote object key refused because it cannot be mapped safely to disk."""


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
        region_name="auto",
        config=BotoConfig(retries={"max_attempts": 3, "mode": "standard"}),
    )


def _resolve_local_target(key: str, prefix: str, root: Path) -> Path:
    """Map an R2 object ``key`` under ``prefix`` to a path safely under ``root``.

    This is the single containment resolver shared by download and verify. It
    raises :class:`KeyRejectedError` (never returning a path) when the key:

    - does not start with ``<prefix>/``;
    - leaves an empty remainder (``<prefix>/``);
    - leaves an absolute remainder (``<prefix>//etc/passwd``);
    - contains an empty, ``.`` or ``..`` path segment;
    - for the flat ``geocache/`` set, contains any directory component;
    - resolves (following symlinks) outside the resolved ``root``.

    Callers must reject before submitting a transfer.
    """
    prefix_slash = prefix + "/"
    if not key.startswith(prefix_slash):
        raise KeyRejectedError(f"key does not start with {prefix_slash!r}")
    rel = key[len(prefix_slash) :]
    if not rel:
        raise KeyRejectedError("empty object name after prefix")
    if rel.startswith("/") or Path(rel).is_absolute():
        raise KeyRejectedError("absolute object name after prefix")
    parts = rel.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise KeyRejectedError("empty, '.' or '..' path segment")
    if prefix == GEOCACHE_PREFIX and len(parts) != 1:
        raise KeyRejectedError("geocache keys must be flat (no directory component)")

    root_resolved = root.resolve()
    candidate = root / rel
    try:
        candidate.resolve().relative_to(root_resolved)
    except ValueError as exc:
        raise KeyRejectedError(f"resolves outside {root_resolved}") from exc
    return candidate


def _collect_manual_files() -> list[tuple[Path, str]]:
    skip_dirs = {"__pycache__", "ura_backup_20260122", "node_modules", ".git"}
    files = []
    for p in MANUAL_DATA_DIR.rglob("*"):
        if not p.is_file():
            continue
        if ".DS_Store" in p.name:
            continue
        if any(part in skip_dirs for part in p.relative_to(MANUAL_DATA_DIR).parts):
            continue
        key = f"{MANUAL_PREFIX}/{p.relative_to(MANUAL_DATA_DIR)}"
        files.append((p, str(key)))
    return sorted(files, key=lambda x: x[1])


def _evidence_keys() -> dict[str, Path]:
    """Map every enumerated ``evidence/`` object key to its pipeline path.

    The single source of truth for the scope: upload enumerates local files
    through it, and download/verify refuse any remote key that is not in it, so
    ``--only evidence`` can never widen itself to the rest of ``data/pipeline/``.
    """
    return {f"{EVIDENCE_PREFIX}/{rel}": PIPELINE_DATA_DIR / rel for rel in EVIDENCE_FILES}


def _collect_evidence_files() -> list[tuple[Path, str]]:
    """Local pipeline artifacts in the enumerated evidence scope, if present."""
    return [(path, key) for key, path in _evidence_keys().items() if path.is_file()]


def _collect_geocache_files() -> list[tuple[Path, str]]:
    """Flat geocode entries at the cache root only.

    Non-recursive globs deliberately exclude ``data/cache/hamilton/`` (node
    cache: fingerprint-keyed, regenerable) and in-flight atomic-write
    ``.tmp`` siblings (their names end in ``.tmp``, not the glob suffix).
    """
    if not CACHE_DIR.exists():
        return []
    files = []
    for pattern in ("*.parquet", "*.json"):
        for p in sorted(CACHE_DIR.glob(pattern)):
            if p.is_file():
                files.append((p, f"{GEOCACHE_PREFIX}/{p.name}"))
    return files


def _sync_sets(only: str | None = None) -> list[tuple[str, list[tuple[Path, str]]]]:
    """Return (prefix, files) pairs to operate on, optionally filtered.

    The default (``only is None``) is ``manual`` + ``geocache``. The
    ``evidence`` set is **opt-in only**: it carries regenerable pipeline
    artifacts that only CI needs, so a routine ``--verify`` or download must not
    start transferring ~110MB of parquet, and nothing enumerates
    ``data/pipeline/`` unless the caller asked for it.
    """
    candidates: list[tuple[str, Callable[[], list[tuple[Path, str]]]]] = [
        (MANUAL_PREFIX, _collect_manual_files),
        (GEOCACHE_PREFIX, _collect_geocache_files),
        (EVIDENCE_PREFIX, _collect_evidence_files),
    ]
    if only is not None:
        candidates = [(prefix, fn) for prefix, fn in candidates if prefix == only]
    else:
        candidates = [(prefix, fn) for prefix, fn in candidates if prefix != EVIDENCE_PREFIX]
    return [(prefix, fn()) for prefix, fn in candidates]


def _root_for(prefix: str) -> Path:
    """Local sync root for an R2 prefix."""
    if prefix == GEOCACHE_PREFIX:
        return CACHE_DIR
    if prefix == EVIDENCE_PREFIX:
        return PIPELINE_DATA_DIR
    return MANUAL_DATA_DIR


def _out_of_scope_keys(prefix: str, remote_keys) -> list[str]:
    """Remote keys under ``prefix`` that the enumerated scope must ignore.

    Only the ``evidence/`` set is enumerated; ``manual/`` and ``geocache/`` are
    whole-directory sets, so this always returns nothing for them.
    """
    if prefix != EVIDENCE_PREFIX:
        return []
    return sorted(set(remote_keys) - set(_evidence_keys()))


def _list_remote(s3, bucket: str, prefix: str) -> dict[str, int]:
    """Map of R2 object key -> size under ``prefix``."""
    paginator = s3.get_paginator("list_objects_v2")
    remote_keys: dict[str, int] = {}
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            remote_keys[obj["Key"]] = obj["Size"]
    return remote_keys


def _sha256_file(path: Path) -> str:
    """Streaming SHA-256 hex digest of a local file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _recorded_sha256(s3, bucket: str, key: str) -> str | None:
    """SHA-256 recorded in object metadata at upload time, if the provider keeps it."""
    head_object = getattr(s3, "head_object", None)
    if head_object is None:
        return None
    try:
        head = head_object(Bucket=bucket, Key=key)
    except Exception:  # noqa: BLE001 - provider may not expose metadata at all
        return None
    metadata = head.get("Metadata") or {}
    recorded = metadata.get(_CONTENT_HASH_METADATA_KEY)
    return recorded if isinstance(recorded, str) and recorded else None


def _local_content_matches(s3, bucket: str, key: str, local_path: Path, scratch: Path) -> bool:
    """True when the remote object's bytes equal ``local_path``'s bytes.

    Prefers a SHA-256 recorded in object metadata (no download). Falls back to
    downloading the object's bytes and hashing them.
    """
    local_digest = _sha256_file(local_path)
    recorded = _recorded_sha256(s3, bucket, key)
    if recorded is not None:
        return recorded == local_digest
    scratch_path = scratch / "remote-object"
    s3.download_file(bucket, key, str(scratch_path))
    try:
        return _sha256_file(scratch_path) == local_digest
    finally:
        scratch_path.unlink(missing_ok=True)


def upload(dry_run: bool = False, only: str | None = None):
    s3 = _s3_client()
    bucket = settings.r2_bucket
    for prefix, files in _sync_sets(only):
        remote = _list_remote(s3, bucket, prefix)
        pending: list[tuple[Path, str]] = []
        skipped = 0
        for local_path, key in files:
            size = local_path.stat().st_size
            # Exact size match only: a 1-byte correction must propagate. This is
            # a size pre-filter, not a content check.
            if key in remote and remote[key] == size:
                skipped += 1
                continue
            pending.append((local_path, key))

        print(f"Uploading to R2 bucket '{bucket}' ({prefix}/): {len(files)} local file(s)")
        uploaded = 0
        if dry_run:
            for local_path, key in pending:
                size_mb = local_path.stat().st_size / 1024 / 1024
                print(f"  {key} ({size_mb:.1f} MB) [DRY RUN]")
                uploaded += 1
        elif pending:

            def _upload_one(item: tuple[Path, str]) -> None:
                path, key = item
                s3.upload_file(
                    str(path),
                    bucket,
                    key,
                    ExtraArgs={"Metadata": {_CONTENT_HASH_METADATA_KEY: _sha256_file(path)}},
                )

            workers = min(_TRANSFER_CONCURRENCY, len(pending))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_upload_one, item): item[1] for item in pending}
                for future in as_completed(futures):
                    future.result()  # propagate transfer errors
                    uploaded += 1
                    if uploaded % 500 == 0:
                        print(f"  ... {uploaded}/{len(pending)} uploaded")

        print(
            f"Done ({prefix}): {uploaded} uploaded, {skipped} skipped by exact size match "
            "(content not compared)."
        )


def download(dry_run: bool = False, only: str | None = None):
    s3 = _s3_client()
    bucket = settings.r2_bucket

    for prefix, _files in _sync_sets(only):
        root = _root_for(prefix)
        remote_keys = _list_remote(s3, bucket, prefix)
        if not remote_keys:
            print(f"No files found in R2 under '{prefix}/'. Upload first with --upload.")
            continue

        print(f"Found {len(remote_keys)} file(s) in R2 ({prefix}/). Checking local...")
        skipped = 0
        rejected = 0
        out_of_scope = _out_of_scope_keys(prefix, remote_keys)
        for key in out_of_scope:
            print(f"  OUT OF SCOPE:     {key} (not in the enumerated {prefix}/ scope)")
        pending: list[tuple[Path, str, int]] = []
        for key, size in sorted(remote_keys.items()):
            if key in out_of_scope:
                continue
            try:
                local_path = _resolve_local_target(key, prefix, root)
            except KeyRejectedError as exc:
                print(f"  REJECTED KEY:     {key} ({exc})")
                rejected += 1
                continue
            # Exact size match only: a 1-byte correction must propagate.
            if local_path.exists() and local_path.stat().st_size == size:
                skipped += 1
                continue
            pending.append((local_path, key, size))

        downloaded = 0
        if dry_run:
            for _local_path, key, size in pending:
                size_mb = size / 1024 / 1024
                print(f"  {key} ({size_mb:.1f} MB) [DRY RUN]")
                downloaded += 1
        elif pending:

            def _download_one(item: tuple[Path, str, int]) -> None:
                path, key, _size = item
                path.parent.mkdir(parents=True, exist_ok=True)
                s3.download_file(bucket, key, str(path))

            workers = min(_TRANSFER_CONCURRENCY, len(pending))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(_download_one, item): item[1] for item in pending}
                for future in as_completed(futures):
                    future.result()  # propagate transfer errors
                    downloaded += 1
                    if downloaded % 500 == 0:
                        print(f"  ... {downloaded}/{len(pending)} downloaded")

        print(
            f"Done ({prefix}): {downloaded} downloaded, {skipped} skipped by exact size match "
            f"(content not compared), {rejected} rejected key(s)."
        )
        if out_of_scope:
            print(
                f"Note: {len(out_of_scope)} remote key(s) outside the enumerated {prefix}/ "
                "scope were ignored (not transferred)."
            )


def verify(only: str | None = None, check_content: bool = False):
    """Compare local vs R2.

    Size mode (default) never claims content equality: matching sizes print
    ``SIZE-OK (CONTENT-UNVERIFIED)`` and any size difference of 1+ bytes prints
    ``SIZE MISMATCH``. ``check_content=True`` downloads/hashes the selected
    scope and prints ``CONTENT-OK`` / ``CONTENT MISMATCH`` instead.
    """
    s3 = _s3_client()
    bucket = settings.r2_bucket

    size_ok = size_mismatch = 0
    content_ok = content_mismatch = 0
    missing_local = missing_remote = rejected = 0
    # Only the enumerated ``evidence/`` scope can report out-of-scope keys; the
    # whole-directory scopes never do, so their output and summary stay as-is.
    out_of_scope_total = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        scratch = Path(tmpdir)
        for prefix, files in _sync_sets(only):
            root = _root_for(prefix)
            local_files = {key: path for path, key in files}
            remote_keys = _list_remote(s3, bucket, prefix)
            out_of_scope = _out_of_scope_keys(prefix, remote_keys)
            out_of_scope_total += len(out_of_scope)
            for key in out_of_scope:
                print(f"  OUT OF SCOPE:     {key} (not in the enumerated {prefix}/ scope)")
            all_keys = (set(remote_keys.keys()) - set(out_of_scope)) | set(local_files.keys())

            for key in sorted(all_keys):
                try:
                    _resolve_local_target(key, prefix, root)
                except KeyRejectedError as exc:
                    print(f"  REJECTED KEY:     {key} ({exc})")
                    rejected += 1
                    continue
                if key not in remote_keys:
                    print(f"  MISSING IN R2:    {key}")
                    missing_remote += 1
                elif key not in local_files:
                    print(f"  MISSING LOCALLY:  {key}")
                    missing_local += 1
                elif check_content:
                    if _local_content_matches(s3, bucket, key, local_files[key], scratch):
                        print(f"  CONTENT-OK:       {key}")
                        content_ok += 1
                    else:
                        print(
                            f"  CONTENT MISMATCH: {key} "
                            f"(local={local_files[key].stat().st_size}, "
                            f"remote={remote_keys[key]})"
                        )
                        content_mismatch += 1
                else:
                    local_size = local_files[key].stat().st_size
                    remote_size = remote_keys[key]
                    # Any difference of 1+ bytes is a mismatch; size equality is
                    # not evidence of content equality.
                    if local_size != remote_size:
                        print(
                            f"  SIZE MISMATCH:    {key} (local={local_size}, remote={remote_size})"
                        )
                        size_mismatch += 1
                    else:
                        print(f"  SIZE-OK (CONTENT-UNVERIFIED): {key}")
                        size_ok += 1

    if check_content:
        parts = [
            f"{content_ok} CONTENT-OK",
            f"{content_mismatch} content mismatch(es)",
            f"{missing_local} missing locally",
            f"{missing_remote} missing in R2",
            f"{rejected} rejected key(s)",
        ]
    else:
        parts = [f"{size_ok} SIZE-OK (CONTENT-UNVERIFIED)"]
        if size_mismatch:
            parts.append(f"{size_mismatch} SIZE MISMATCH")
        parts.extend(
            [
                f"{missing_local} missing locally",
                f"{missing_remote} missing in R2",
                f"{rejected} rejected key(s)",
            ]
        )
    print("\nSummary: " + ", ".join(parts))
    if out_of_scope_total:
        print(
            f"Note: {out_of_scope_total} remote key(s) outside the enumerated "
            f"{EVIDENCE_PREFIX}/ scope were ignored (not compared)."
        )
    if not check_content:
        print(
            "Content was NOT compared: SIZE-OK means byte sizes matched, not that bytes "
            "match. Re-run with --verify-content to compare bytes or recorded SHA-256."
        )


def main():
    parser = argparse.ArgumentParser(description="Sync manual data with Cloudflare R2")
    parser.add_argument("--upload", action="store_true", help="Upload local data to R2")
    parser.add_argument("--download", action="store_true", help="Download from R2 (default action)")
    parser.add_argument(
        "--verify", action="store_true", help="Compare local vs R2 without transferring"
    )
    parser.add_argument(
        "--verify-content",
        "--check-content",
        dest="verify_content",
        action="store_true",
        help="Like --verify, but download and compare bytes (or recorded SHA-256) for the scope",
    )
    parser.add_argument(
        "--only",
        choices=(MANUAL_PREFIX, GEOCACHE_PREFIX, EVIDENCE_PREFIX),
        default=None,
        help=(
            "Restrict the operation to one sync set (default: manual + geocache). "
            "'evidence' is the enumerated set of pipeline artifacts the evidence "
            "producers read, not all of data/pipeline/"
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would happen without doing it"
    )
    args = parser.parse_args()

    if not settings.r2_account_id or not settings.r2_access_key_id.get_secret_value():
        print(
            "Error: R2 credentials not configured. Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, "
            "and R2_SECRET_ACCESS_KEY in the environment or local .env"
        )
        sys.exit(1)

    if not MANUAL_DATA_DIR.exists():
        MANUAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.verify_content or args.verify:
        verify(only=args.only, check_content=args.verify_content)
    elif args.upload:
        upload(dry_run=args.dry_run, only=args.only)
    else:
        download(dry_run=args.dry_run, only=args.only)


if __name__ == "__main__":
    main()
