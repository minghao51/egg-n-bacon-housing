#!/usr/bin/env python3
"""
Download URA Private Residential Rental Index.

Downloads the URA rental index data from data.gov.sg and processes it
for calculating condo rental yield.

Usage:
    uv run python scripts/download_ura_rental_index.py
"""

import sys
from pathlib import Path

# Add project root to path for src imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from io import StringIO

import pandas as pd
import requests

from scripts.core.config import Config
from scripts.core.network_check import check_local_file_exists, require_network

logger = logging.getLogger(__name__)

OUTPUT_PATH = Config.PARQUETS_DIR / "L2" / "ura_rental_index.parquet"


def download_ura_rental_index() -> pd.DataFrame:
    """Download URA Private Residential Property Rental Index."""
    logger.info("Downloading URA Private Residential Rental Index...")

    url = "https://data.gov.sg/datasets/d_8e4c50283fb7052a391dfb746a05c853/download"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.content.decode('utf-8')))
        logger.info(f"Downloaded {len(df)} quarters of rental index data")
        logger.info(f"Columns: {df.columns.tolist()}")
        return df
    except Exception as e:
        logger.error(f"Failed to download URA rental index: {e}")
        return pd.DataFrame()


def process_rental_index(df: pd.DataFrame) -> pd.DataFrame:
    """Process URA rental index data."""
    logger.info("Processing URA rental index...")

    if df.empty:
        return pd.DataFrame()

    df.columns = df.columns.str.strip().str.upper()

    if len(df.columns) > 0:
        first_col = df.columns[0]
        df['QUARTER'] = pd.to_datetime(df[first_col], errors='coerce')
        df['YEAR'] = df['QUARTER'].dt.year
        df['QUARTER_NUM'] = df['QUARTER'].dt.quarter

    index_col = None
    for col in df.columns:
        if 'INDEX' in col or 'RENTAL' in col:
            index_col = col
            break
    if index_col is None and len(df.columns) > 1:
        index_col = df.columns[1]

    if index_col:
        df['RENTAL_INDEX'] = pd.to_numeric(df[index_col], errors='coerce')
        logger.info(f"Using column '{index_col}' as rental index")

    result_cols = ['QUARTER', 'YEAR', 'QUARTER_NUM', 'RENTAL_INDEX']
    result_df = df[[col for col in result_cols if col in df.columns]].copy()
    result_df = result_df.dropna(subset=['RENTAL_INDEX'])
    logger.info(f"Processed {len(result_df)} quarters of rental index")
    return result_df


def save_rental_index(df: pd.DataFrame):
    """Save rental index data."""
    logger.info("Saving URA rental index...")
    parquet_dir = Config.PARQUETS_DIR / "L2"
    parquet_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = parquet_dir / "ura_rental_index.parquet"
    df.to_parquet(parquet_path, compression='snappy', index=False)
    logger.info(f"Saved rental index to {parquet_path}")


def main():
    """Main pipeline execution."""
    logger.info("=" * 60)
    logger.info("URA Rental Index Download")
    logger.info("=" * 60)

    if check_local_file_exists(OUTPUT_PATH):
        logger.info(f"Local file already exists: {OUTPUT_PATH}")
        logger.info("Skipping download. To re-download, delete the local file first.")
        return

    if not require_network():
        logger.error("Network unavailable. Cannot download data. Exiting.")
        return

    rental_df = download_ura_rental_index()
    if rental_df.empty:
        logger.error("Failed to download rental index data. Exiting.")
        return

    processed_df = process_rental_index(rental_df)
    if processed_df.empty:
        logger.error("Failed to process rental index data. Exiting.")
        return

    save_rental_index(processed_df)

    logger.info("=" * 60)
    logger.info(f"Total quarters: {len(processed_df)}")
    logger.info(f"Date range: {processed_df['QUARTER'].min()} to {processed_df['QUARTER'].max()}")
    logger.info("=" * 60)
    logger.info("Pipeline completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
