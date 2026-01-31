#!/usr/bin/env python3
"""Download HDB rental data from data.gov.sg.

This script downloads the "Renting Out of Flats from Jan 2021" dataset
from data.gov.sg and saves it as a parquet file.

Usage:
    uv run python scripts/download_hdb_rental_data.py
"""

import sys
from pathlib import Path

# Add project root to path for src imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

import pandas as pd
import requests

from scripts.core.config import Config
from scripts.core.network_check import check_local_file_exists, require_network

logger = logging.getLogger(__name__)

OUTPUT_PATH = Config.PARQUETS_DIR / "L1" / "housing_hdb_rental.parquet"


def download_hdb_rental_data(dataset_id: str = "d_c9f57187485a850908655db0e8cfe651", batch_size: int = 10000) -> pd.DataFrame:
    """Download HDB rental data from data.gov.sg API.

    Args:
        dataset_id: Dataset ID on data.gov.sg
        batch_size: Number of records to fetch per request

    Returns:
        DataFrame with rental data
    """
    logger.info(f"Downloading HDB rental data (dataset: {dataset_id})...")

    url = "https://data.gov.sg/api/action/datastore_search"

    params = {"resource_id": dataset_id, "limit": 1}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    total = data['result']['total']
    logger.info(f"Total records in dataset: {total:,}")

    all_records = []
    offset = 0

    while offset < total:
        params = {
            "resource_id": dataset_id,
            "limit": batch_size,
            "offset": offset
        }
        logger.info(f"Downloading records {offset:,} to {min(offset + batch_size, total):,}...")
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        records = data['result']['records']
        all_records.extend(records)
        offset += batch_size
        if len(records) < batch_size:
            break

    logger.info(f"Downloaded {len(all_records):,} records")

    df = pd.DataFrame(all_records)
    df.columns = df.columns.str.lower().str.replace(' ', '_')

    if '_id' in df.columns:
        df = df.drop(columns=['_id'])

    if 'monthly_rent' in df.columns:
        df['monthly_rent'] = pd.to_numeric(df['monthly_rent'], errors='coerce')
    if 'rent_approval_date' in df.columns:
        df['rent_approval_date'] = pd.to_datetime(df['rent_approval_date'])

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
    df.to_parquet(OUTPUT_PATH, compression='snappy', index=False)
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
