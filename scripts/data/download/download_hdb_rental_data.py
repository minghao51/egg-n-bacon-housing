#!/usr/bin/env python3
"""Download HDB rental data from data.gov.sg.

This script downloads the "Renting Out of Flats from Jan 2021" dataset
from data.gov.sg and saves it as a parquet file.

Usage:
    uv run python scripts/data/download/download_hdb_rental_data.py
"""

import sys
from pathlib import Path

# Add project root to path for src imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import random
import time

import pandas as pd
import requests

from scripts.core.config import Config
from scripts.core.network_check import check_local_file_exists, require_network

logger = logging.getLogger(__name__)

OUTPUT_PATH = Config.PARQUETS_DIR / "L1" / "housing_hdb_rental.parquet"
DATASET_DOWNLOAD_BASE = "https://api-open.data.gov.sg/v1/public/api/datasets"


def _get_with_retry(
    session: requests.Session,
    url: str,
    params: dict,
    *,
    max_retries: int = 5,
    timeout: int = 30,
) -> requests.Response:
    """GET with retry/backoff for rate limiting and transient network errors."""
    for attempt in range(max_retries + 1):
        try:
            response = session.get(url, params=params, timeout=timeout)
            status = response.status_code

            if status == 429 or 500 <= status < 600:
                if attempt >= max_retries:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    sleep_seconds = float(retry_after)
                else:
                    sleep_seconds = min(60.0, (2**attempt) + random.uniform(0, 1))
                logger.warning(
                    "Request failed with HTTP %s (attempt %s/%s). Retrying in %.1fs...",
                    status,
                    attempt + 1,
                    max_retries + 1,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)
                continue

            response.raise_for_status()
            return response

        except requests.RequestException as e:
            if attempt >= max_retries:
                raise
            sleep_seconds = min(60.0, (2**attempt) + random.uniform(0, 1))
            logger.warning(
                "Network request error (%s) on attempt %s/%s. Retrying in %.1fs...",
                e.__class__.__name__,
                attempt + 1,
                max_retries + 1,
                sleep_seconds,
            )
            time.sleep(sleep_seconds)

    raise RuntimeError("Unreachable retry loop exit")


def _parse_download_api_payload(response: requests.Response) -> dict:
    """Parse JSON payload from data.gov.sg dataset download APIs."""
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected download API response format")
    return payload


def _download_via_dataset_download_api(
    session: requests.Session, dataset_id: str, poll_attempts: int = 10
) -> pd.DataFrame:
    """Download full dataset via initiate-download + poll-download endpoints."""
    initiate_url = f"{DATASET_DOWNLOAD_BASE}/{dataset_id}/initiate-download"
    poll_url = f"{DATASET_DOWNLOAD_BASE}/{dataset_id}/poll-download"

    logger.info("Trying dataset download API for full HDB rental export...")
    init_resp = _get_with_retry(session, initiate_url, params={})
    init_payload = _parse_download_api_payload(init_resp)
    init_data = init_payload.get("data", {}) if isinstance(init_payload.get("data"), dict) else {}
    logger.debug("initiate-download response keys: %s", list(init_payload.keys()))
    if "message" in init_data:
        logger.info("initiate-download: %s", init_data["message"])

    download_url = None
    for attempt in range(1, poll_attempts + 1):
        poll_resp = _get_with_retry(session, poll_url, params={})
        poll_payload = _parse_download_api_payload(poll_resp)
        poll_data = (
            poll_payload.get("data", {}) if isinstance(poll_payload.get("data"), dict) else {}
        )
        status = str(poll_data.get("status", "")).upper()
        if poll_data.get("url"):
            download_url = poll_data["url"]
            logger.info("Dataset download API ready (status=%s)", status or "unknown")
            break
        if status in {"FAILED", "ERROR"}:
            raise RuntimeError(f"Dataset download API failed (status={status})")
        sleep_seconds = min(10, attempt)
        logger.info(
            "Waiting for dataset export (poll %s/%s, status=%s)...",
            attempt,
            poll_attempts,
            status or "pending",
        )
        time.sleep(sleep_seconds)

    if not download_url:
        raise RuntimeError("Dataset download API did not return a download URL in time")

    file_resp = _get_with_retry(session, download_url, params={})
    file_resp.raise_for_status()
    content_type = file_resp.headers.get("Content-Type", "")
    logger.info(
        "Downloaded dataset file (%s bytes, content-type=%s)", len(file_resp.content), content_type
    )

    # Let pandas infer the delimiter/encoding from the CSV bytes.
    from io import BytesIO

    return pd.read_csv(BytesIO(file_resp.content))


def download_hdb_rental_data(
    dataset_id: str = "d_c9f57187485a850908655db0e8cfe651", batch_size: int = 10000
) -> pd.DataFrame:
    """Download HDB rental data from data.gov.sg API.

    Args:
        dataset_id: Dataset ID on data.gov.sg
        batch_size: Number of records to fetch per request

    Returns:
        DataFrame with rental data
    """
    logger.info(f"Downloading HDB rental data (dataset: {dataset_id})...")

    session = requests.Session()
    df = pd.DataFrame()

    # Preferred path for complete dataset exports per current data.gov.sg docs.
    try:
        df = _download_via_dataset_download_api(session, dataset_id)
        logger.info("Dataset download API returned %s records", len(df))
    except Exception as e:
        logger.warning(
            "Dataset download API failed, falling back to datastore_search pagination: %s", e
        )

    # Fallback path: legacy datastore_search pagination.
    if df.empty:
        url = "https://data.gov.sg/api/action/datastore_search"
        params = {"resource_id": dataset_id, "limit": 1}

        response = _get_with_retry(session, url, params)
        response.raise_for_status()
        data = response.json()

        total = data["result"]["total"]
        logger.info(f"Total records in dataset: {total:,}")

        all_records = []
        offset = 0

        while offset < total:
            params = {"resource_id": dataset_id, "limit": batch_size, "offset": offset}
            logger.info(f"Downloading records {offset:,} to {min(offset + batch_size, total):,}...")
            response = _get_with_retry(session, url, params)
            response.raise_for_status()
            data = response.json()
            records = data["result"]["records"]
            all_records.extend(records)
            offset += batch_size
            if len(records) < batch_size:
                break

        logger.info(f"Downloaded {len(all_records):,} records via datastore_search")
        df = pd.DataFrame(all_records)

    df.columns = df.columns.str.lower().str.replace(" ", "_")

    if "_id" in df.columns:
        df = df.drop(columns=["_id"])

    if "monthly_rent" in df.columns:
        df["monthly_rent"] = pd.to_numeric(df["monthly_rent"], errors="coerce")
    if "rent_approval_date" in df.columns:
        df["rent_approval_date"] = pd.to_datetime(df["rent_approval_date"])

    logger.info(f"DataFrame shape: {df.shape}")
    logger.info(f"Columns: {list(df.columns)}")
    return df


def main():
    """Main execution."""
    logger.info("=" * 60)
    logger.info("HDB Rental Data Download")
    logger.info("=" * 60)

    if check_local_file_exists(OUTPUT_PATH):
        logger.info(f"Local file already exists: {OUTPUT_PATH}")
        logger.info("Skipping download. To re-download, delete the local file first.")
        return

    if not require_network():
        logger.error("Network unavailable. Cannot download data. Exiting.")
        return

    df = download_hdb_rental_data()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH, compression="snappy", index=False)
    logger.info(f"Saved to {OUTPUT_PATH}")

    logger.info("\nSummary Statistics:")
    logger.info(f"Date range: {df['rent_approval_date'].min()} to {df['rent_approval_date'].max()}")
    logger.info(f"Towns: {df['town'].nunique()}")
    logger.info(f"Flat types: {df['flat_type'].nunique()}")
    logger.info(f"Average monthly rent: ${df['monthly_rent'].mean():.2f}")

    logger.info("\n" + "=" * 60)
    logger.info("Download completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
