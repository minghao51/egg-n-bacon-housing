#!/usr/bin/env python3
"""Calculate L3 housing market metrics from L2 transaction data.

This script:
1. Loads L1 transaction data (HDB and Condo)
2. Calculates stratified median prices
3. Computes 6 key metrics:
   - Price growth rate
   - Price per square foot (PSF)
   - Transaction volume
   - Market momentum
   - Affordability index (TODO: needs income data)
   - ROI potential score (TODO: needs rental data)
4. Saves results to L3 parquet files
"""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from scripts.core.config import Config
from scripts.core.metrics import (
    calculate_affordability,
    calculate_roi_score,
    compute_monthly_metrics,
    validate_metrics,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load L1 transaction data.

    Returns:
        Tuple of (hdb_df, condo_df)
    """
    logger.info("Loading L1 transaction data...")

    hdb_path = Config.PARQUETS_DIR / "L1" / "housing_hdb_transaction.parquet"
    condo_path = Config.PARQUETS_DIR / "L1" / "housing_condo_transaction.parquet"

    if not hdb_path.exists():
        raise FileNotFoundError(f"HDB data not found: {hdb_path}")
    if not condo_path.exists():
        raise FileNotFoundError(f"Condo data not found: {condo_path}")

    hdb_df = pd.read_parquet(hdb_path)
    condo_df = pd.read_parquet(condo_path)

    logger.info(f"Loaded {len(hdb_df):,} HDB transactions")
    logger.info(f"Loaded {len(condo_df):,} Condo transactions")

    # Clean condo data: Remove commas from price and convert to numeric
    condo_df['Transacted Price ($)'] = (
        condo_df['Transacted Price ($)']
        .astype(str)
        .str.replace(',', '')
        .astype(float)
    )

    # Standardize date columns
    # HDB already has month in YYYY-MM format
    hdb_df['month'] = pd.to_datetime(hdb_df['month'], format='%Y-%m').dt.to_period('M')

    # Condo has MMM-YY format (e.g., "Jan-23")
    condo_df['month'] = pd.to_datetime(
        condo_df['Sale Date'],
        format='%b-%y',
        errors='coerce'
    ).dt.to_period('M')

    return hdb_df, condo_df


def main():
    """Main pipeline execution."""
    logger.info("=" * 60)
    logger.info("L3 Metrics Calculation Pipeline")
    logger.info("=" * 60)

    # Load data
    hdb_df, condo_df = load_data()

    # Compute metrics
    logger.info("Computing monthly metrics...")
    metrics_df = compute_monthly_metrics(
        hdf_df=hdb_df,
        condo_df=condo_df,
        start_date='2015-01',  # Focus on recent data
        end_date=None
    )

    logger.info(f"Computed {len(metrics_df):,} metric records")

    # Validate
    logger.info("Validating metrics...")
    validation = validate_metrics(metrics_df)
    logger.info(f"Validation results: {validation}")

    # Create L3 directory
    l3_dir = Config.PARQUETS_DIR / "L3"
    l3_dir.mkdir(exist_ok=True)

    # Save monthly metrics
    output_path = l3_dir / "metrics_monthly.parquet"
    metrics_df.to_parquet(output_path, compression='snappy', index=False)
    logger.info(f"Saved monthly metrics to {output_path}")

    # Save summary
    summary_path = l3_dir / "metrics_summary.csv"
    summary = metrics_df.groupby(['property_type', 'town']).agg({
        'stratified_median_price': 'last',
        'growth_rate': 'last',
        'transaction_count': 'sum'
    }).reset_index()
    summary.to_csv(summary_path, index=False)
    logger.info(f"Saved summary to {summary_path}")

    logger.info("=" * 60)
    logger.info("Pipeline completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
