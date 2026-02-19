# scripts/data/create_l3_unified_dataset.py
"""
Create L3 unified dataset from existing transaction data.

Filters and prepares transaction data for VAR/ARIMAX modeling.
"""

import logging
from pathlib import Path

import pandas as pd

from scripts.core.config import Config
from scripts.core.data_helpers import save_parquet

logger = logging.getLogger(__name__)


def create_l3_unified_dataset(
    source_path: str = None,
    start_date: str = '2021-01-01',
    end_date: str = '2026-02-01'
) -> pd.DataFrame:
    """
    Create L3 unified dataset from existing transaction data.

    Args:
        source_path: Path to source parquet file
        start_date: Start date for filtering
        end_date: End date for filtering

    Returns:
        L3 unified dataset with required columns for VAR modeling
    """
    logger.info("=" * 60)
    logger.info("Creating L3 Unified Dataset")
    logger.info("=" * 60)

    # Default source path
    if source_path is None:
        source_path = Config.DATA_DIR / 'analysis' / 'coming_soon' / 'coming_soon_properties.parquet'

    source_path = Path(source_path)

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    logger.info(f"Loading data from {source_path}")

    # Load data
    df = pd.read_parquet(source_path)

    logger.info(f"Loaded {len(df):,} transactions")

    # Filter to date range
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])
    df_filtered = df[
        (df['transaction_date'] >= start_date) &
        (df['transaction_date'] <= end_date)
    ].copy()

    logger.info(f"Filtered to {len(df_filtered):,} transactions ({start_date} to {end_date})")

    # Select required columns for VAR modeling
    required_columns = [
        'planning_area',
        'transaction_date',
        'price_psf',
        'yoy_change_pct',
        'address',
        'lat',
        'lon'
    ]

    # Add amenity columns if available
    amenity_columns = [
        'mrt_within_1km',
        'hawker_within_1km',
        'supermarket_within_1km'
    ]

    available_columns = [col for col in amenity_columns if col in df_filtered.columns]
    selected_columns = required_columns + available_columns

    # Create L3 dataset
    l3_df = df_filtered[selected_columns].copy()

    # Drop rows with missing critical values
    before_count = len(l3_df)
    l3_df = l3_df.dropna(subset=['planning_area', 'transaction_date', 'price_psf', 'lat'])
    dropped = before_count - len(l3_df)

    if dropped > 0:
        logger.info(f"Dropped {dropped:,} rows with missing critical values")

    logger.info(f"L3 unified dataset: {len(l3_df):,} transactions, {len(l3_df.columns)} columns")

    # Log date range
    logger.info(f"Date range: {l3_df['transaction_date'].min()} to {l3_df['transaction_date'].max()}")

    # Log planning area coverage
    n_areas = l3_df['planning_area'].nunique()
    logger.info(f"Planning areas: {n_areas}")

    # Log amenity coverage
    for col in available_columns:
        coverage = (l3_df[col].sum() / len(l3_df)) * 100
        logger.info(f"{col}: {coverage:.1f}% coverage")

    return l3_df


def save_l3_unified_dataset(df: pd.DataFrame, output_path: str = None):
    """
    Save L3 unified dataset to parquet.

    Args:
        df: L3 unified dataset
        output_path: Output path (defaults to Config.PARQUETS_DIR / "L3" / "housing_unified.parquet")
    """
    if output_path is None:
        output_path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
    else:
        output_path = Path(output_path)

    # Create directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save using data_helpers
    save_parquet(df, "L3_housing_unified", source="create_l3_unified_dataset")

    logger.info(f"✅ Saved L3 unified dataset to {output_path}")


def main():
    """Main entry point for CLI execution."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    l3_df = create_l3_unified_dataset()
    save_l3_unified_dataset(l3_df)

    logger.info("=" * 60)
    logger.info("L3 Unified Dataset Creation Complete!")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
