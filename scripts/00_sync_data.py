"""Sync pipeline data files between local disk and Cloudflare R2.

Two sync sets (R2 prefix <-> local directory):

- ``manual/``   <-> ``data/manual/``  — full tree of manual source
  CSV/GeoJSON data (~52 files, ~123MB).
- ``geocache/`` <-> ``data/cache/``   — flat OneMap geocode cache entries
  only (``*.parquet`` / ``*.json`` at the cache root; ~14k entries, ~92MB).
  The Hamilton node cache under ``data/cache/hamilton/`` is deliberately
  excluded: it is keyed by code/config fingerprints, invalidated by any
  code change, and fully regenerable — syncing it buys nothing.

Uploads and downloads are idempotent: files whose remote size already
matches (within a small tolerance) are skipped, so re-running either
direction only transfers what changed.

Usage:
    uv run python scripts/00_sync_data.py            # download (default)
    uv run python scripts/00_sync_data.py --upload   # upload local to R2
    uv run python scripts/00_sync_data.py --verify   # verify local vs R2
    uv run python scripts/00_sync_data.py --upload --only geocache
"""

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from egg_n_bacon_housing.config import settings

MANUAL_DATA_DIR = settings.data_dir / "manual"
CACHE_DIR = settings.data_dir / "cache"

MANUAL_PREFIX = "manual"
GEOCACHE_PREFIX = "geocache"

_SIZE_TOLERANCE_BYTES = 100

# Bounded transfer concurrency for the ~14k-file geocache set; boto3 clients
# are thread-safe for operations.
_TRANSFER_CONCURRENCY = 16


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
        region_name="auto",
        config=BotoConfig(retries={"max_attempts": 3, "mode": "standard"}),
    )


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
    """Return (prefix, files) pairs to operate on, optionally filtered."""
    candidates: list[tuple[str, callable]] = [
        (MANUAL_PREFIX, _collect_manual_files),
        (GEOCACHE_PREFIX, _collect_geocache_files),
    ]
    if only is not None:
        candidates = [(prefix, fn) for prefix, fn in candidates if prefix == only]
    return [(prefix, fn()) for prefix, fn in candidates]


def _list_remote(s3, bucket: str, prefix: str) -> dict[str, int]:
    """Map of R2 object key -> size under ``prefix``."""
    paginator = s3.get_paginator("list_objects_v2")
    remote_keys: dict[str, int] = {}
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            remote_keys[obj["Key"]] = obj["Size"]
    return remote_keys


def upload(dry_run: bool = False, only: str | None = None):
    s3 = _s3_client()
    bucket = settings.r2_bucket
    for prefix, files in _sync_sets(only):
        remote = _list_remote(s3, bucket, prefix)
        pending: list[tuple[Path, str]] = []
        skipped = 0
        for local_path, key in files:
            size = local_path.stat().st_size
            if key in remote and abs(remote[key] - size) < _SIZE_TOLERANCE_BYTES:
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
            workers = min(_TRANSFER_CONCURRENCY, len(pending))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(s3.upload_file, str(path), bucket, key): key
                    for path, key in pending
                }
                for future in as_completed(futures):
                    future.result()  # propagate transfer errors
                    uploaded += 1
                    if uploaded % 500 == 0:
                        print(f"  ... {uploaded}/{len(pending)} uploaded")

        print(f"Done ({prefix}): {uploaded} uploaded, {skipped} unchanged (skipped).")


def download(dry_run: bool = False, only: str | None = None):
    s3 = _s3_client()
    bucket = settings.r2_bucket

    for prefix, files in _sync_sets(only):
        local_files = {key: path for path, key in files}
        remote_keys = _list_remote(s3, bucket, prefix)
        if not remote_keys:
            print(f"No files found in R2 under '{prefix}/'. Upload first with --upload.")
            continue

        print(f"Found {len(remote_keys)} file(s) in R2 ({prefix}/). Checking local...")
        skipped = 0
        pending: list[tuple[Path, str, int]] = []
        for key, size in sorted(remote_keys.items()):
            local_path = local_files.get(key)
            if local_path is None:
                rel = key.removeprefix(prefix + "/")
                # Geocache entries restore flat into the cache root; manual
                # files restore into their subdirectory tree.
                local_path = CACHE_DIR / rel if prefix == GEOCACHE_PREFIX else MANUAL_DATA_DIR / rel

            if (
                local_path.exists()
                and abs(local_path.stat().st_size - size) < _SIZE_TOLERANCE_BYTES
            ):
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

        print(f"Done ({prefix}): {downloaded} downloaded, {skipped} skipped (already exist).")


def verify(only: str | None = None):
    s3 = _s3_client()
    bucket = settings.r2_bucket

    ok = missing_local = missing_remote = size_mismatch = 0
    for prefix, files in _sync_sets(only):
        local_files = {key: path for path, key in files}
        remote_keys = _list_remote(s3, bucket, prefix)
        all_keys = set(remote_keys.keys()) | set(local_files.keys())

        for key in sorted(all_keys):
            rel = key.removeprefix(prefix + "/")
            if key not in remote_keys:
                print(f"  MISSING IN R2:    {prefix}/{rel}")
                missing_remote += 1
            elif key not in local_files:
                print(f"  MISSING LOCALLY:  {prefix}/{rel}")
                missing_local += 1
            else:
                local_size = local_files[key].stat().st_size
                remote_size = remote_keys[key]
                if abs(local_size - remote_size) > _SIZE_TOLERANCE_BYTES:
                    print(
                        f"  SIZE MISMATCH:    {prefix}/{rel} (local={local_size}, remote={remote_size})"
                    )
                    size_mismatch += 1
                else:
                    ok += 1

    print(
        f"\nSummary: {ok} OK, {missing_local} missing locally, "
        f"{missing_remote} missing in R2, {size_mismatch} size mismatches"
    )


def main():
    parser = argparse.ArgumentParser(description="Sync manual data with Cloudflare R2")
    parser.add_argument("--upload", action="store_true", help="Upload local data to R2")
    parser.add_argument("--download", action="store_true", help="Download from R2 (default action)")
    parser.add_argument(
        "--verify", action="store_true", help="Compare local vs R2 without transferring"
    )
    parser.add_argument(
        "--only",
        choices=(MANUAL_PREFIX, GEOCACHE_PREFIX),
        default=None,
        help="Restrict the operation to one sync set (default: both)",
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

    if args.verify:
        verify(only=args.only)
    elif args.upload:
        upload(dry_run=args.dry_run, only=args.only)
    else:
        download(dry_run=args.dry_run, only=args.only)


if __name__ == "__main__":
    main()
