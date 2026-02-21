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
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from scripts.core.config import Config
from scripts.core.metrics import (
    compute_monthly_metrics,
    validate_metrics,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_data() -> pd.DataFrame:
    """Load L3 unified transaction data.

    Returns:
        DataFrame with all transactions (HDB and Condo)
    """
    logger.info("Loading L3 unified transaction data...")

    unified_path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"

    if not unified_path.exists():
        raise FileNotFoundError(f"Unified data not found: {unified_path}")

    df = pd.read_parquet(unified_path)

    logger.info(f"Loaded {len(df):,} total transactions")
    logger.info(f"  HDB: {len(df[df['property_type'] == 'HDB']):,}")
    logger.info(f"  Condominium: {len(df[df['property_type'] == 'Condominium']):,}")

    # Standardize date column
    df['month'] = pd.to_datetime(df['month']).dt.to_period('M')

    return df


def main():
    """Main pipeline execution."""
    logger.info("=" * 60)
    logger.info("L3 Metrics Calculation Pipeline")
    logger.info("=" * 60)

    # Load data
    df = load_data()

    # Compute metrics
    logger.info("Computing monthly metrics...")
    metrics_df = compute_monthly_metrics(
        unified_df=df,
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
    summary = metrics_df.groupby(['property_type', 'planning_area']).agg({
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
