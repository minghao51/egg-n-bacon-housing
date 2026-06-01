"""Sync manual data files between local disk and Cloudflare R2.

Usage:
    dotenvx run -- uv run python scripts/00_sync_data.py          # download (default)
    dotenvx run -- uv run python scripts/00_sync_data.py --upload  # upload local to R2
    dotenvx run -- uv run python scripts/00_sync_data.py --verify  # verify local vs R2
"""

import argparse
import sys
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from egg_n_bacon_housing.config import settings

MANUAL_DATA_DIR = settings.data_dir / "manual"
_R2_PREFIX = "manual"


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
        region_name="auto",
        config=BotoConfig(retries={"max_attempts": 3, "mode": "standard"}),
    )


def _collect_local_files() -> list[tuple[Path, str]]:
    skip_dirs = {"__pycache__", "ura_backup_20260122", "node_modules", ".git"}
    files = []
    for p in MANUAL_DATA_DIR.rglob("*"):
        if not p.is_file():
            continue
        if ".DS_Store" in p.name:
            continue
        if any(part in skip_dirs for part in p.relative_to(MANUAL_DATA_DIR).parts):
            continue
        key = f"{_R2_PREFIX}/{p.relative_to(MANUAL_DATA_DIR)}"
        files.append((p, str(key)))
    return sorted(files, key=lambda x: x[1])


def upload(dry_run: bool = False):
    s3 = _s3_client()
    bucket = settings.r2_bucket
    files = _collect_local_files()

    print(f"Uploading {len(files)} files to R2 bucket '{bucket}'...")
    for local_path, key in files:
        size_mb = local_path.stat().st_size / 1024 / 1024
        print(f"  {key} ({size_mb:.1f} MB)", end="")
        if dry_run:
            print(" [DRY RUN]")
            continue
        s3.upload_file(str(local_path), bucket, key)
        print(" OK")

    print(f"Done. {len(files)} files uploaded.")


def download(dry_run: bool = False):
    s3 = _s3_client()
    bucket = settings.r2_bucket

    paginator = s3.get_paginator("list_objects_v2")
    remote_keys: dict[str, int] = {}
    for page in paginator.paginate(Bucket=bucket, Prefix=_R2_PREFIX):
        for obj in page.get("Contents", []):
            remote_keys[obj["Key"]] = obj["Size"]

    if not remote_keys:
        print("No files found in R2. Upload first with --upload.")
        return

    print(f"Found {len(remote_keys)} files in R2. Checking local...")

    skipped = downloaded = 0
    for key, size in sorted(remote_keys.items()):
        rel = key.removeprefix(_R2_PREFIX + "/")
        local_path = MANUAL_DATA_DIR / rel

        if local_path.exists() and abs(local_path.stat().st_size - size) < 100:
            skipped += 1
            continue

        size_mb = size / 1024 / 1024
        print(f"  {rel} ({size_mb:.1f} MB)", end="")
        if dry_run:
            print(" [DRY RUN]")
            downloaded += 1
            continue

        local_path.parent.mkdir(parents=True, exist_ok=True)
        s3.download_file(bucket, key, str(local_path))
        print(" OK")
        downloaded += 1

    print(f"Done. {downloaded} downloaded, {skipped} skipped (already exist).")


def verify():
    s3 = _s3_client()
    bucket = settings.r2_bucket

    paginator = s3.get_paginator("list_objects_v2")
    remote_keys: dict[str, int] = {}
    for page in paginator.paginate(Bucket=bucket, Prefix=_R2_PREFIX):
        for obj in page.get("Contents", []):
            remote_keys[obj["Key"]] = obj["Size"]

    local_files = {key: path for path, key in _collect_local_files()}

    all_keys = set(remote_keys.keys()) | set(local_files.keys())

    missing_local = 0
    missing_remote = 0
    size_mismatch = 0
    ok = 0

    for key in sorted(all_keys):
        rel = key.removeprefix(_R2_PREFIX + "/")
        if key not in remote_keys:
            print(f"  MISSING IN R2:    {rel}")
            missing_remote += 1
        elif key not in local_files:
            print(f"  MISSING LOCALLY:  {rel}")
            missing_local += 1
        else:
            local_size = local_files[key].stat().st_size
            remote_size = remote_keys[key]
            if abs(local_size - remote_size) > 100:
                print(f"  SIZE MISMATCH:    {rel} (local={local_size}, remote={remote_size})")
                size_mismatch += 1
            else:
                ok += 1

    print(
        f"\nSummary: {ok} OK, {missing_local} missing locally, {missing_remote} missing in R2, {size_mismatch} size mismatches"
    )


def main():
    parser = argparse.ArgumentParser(description="Sync manual data with Cloudflare R2")
    parser.add_argument("--upload", action="store_true", help="Upload local data to R2")
    parser.add_argument("--download", action="store_true", help="Download from R2 (default action)")
    parser.add_argument(
        "--verify", action="store_true", help="Compare local vs R2 without transferring"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would happen without doing it"
    )
    args = parser.parse_args()

    if not settings.r2_account_id or not settings.r2_access_key_id.get_secret_value():
        print(
            "Error: R2 credentials not configured. Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY in .env"
        )
        sys.exit(1)

    if not MANUAL_DATA_DIR.exists():
        MANUAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.verify:
        verify()
    elif args.upload:
        upload(dry_run=args.dry_run)
    else:
        download(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
