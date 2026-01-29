#!/usr/bin/env python3
"""Test script to add MRT distance to existing unified dataset."""

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Config
from core.mrt_distance import calculate_nearest_mrt, load_mrt_stations

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test MRT distance calculation on sample of housing data."""
    logger.info("=" * 60)
    logger.info("Testing MRT Distance Integration")
    logger.info("=" * 60)

    # Load existing unified dataset
    unified_path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"

    if not unified_path.exists():
        logger.error(f"Unified dataset not found: {unified_path}")
        return

    logger.info(f"Loading unified dataset from {unified_path}")
    df = pd.read_parquet(unified_path)

    logger.info(f"Loaded {len(df):,} records")
    logger.info(f"Columns: {list(df.columns[:10])}...")

    # Check if lat/lon exist
    if 'lat' not in df.columns or 'lon' not in df.columns:
        logger.error("Dataset missing lat/lon columns")
        return

    # Filter to properties with coordinates
    has_coords = df['lat'].notna() & df['lon'].notna()
    logger.info(f"Properties with coordinates: {has_coords.sum():,} of {len(df):,}")

    # Test on a small sample first
    sample_size = min(1000, has_coords.sum())
    sample_df = df[has_coords].head(sample_size).copy()

    logger.info(f"Testing on sample of {len(sample_df):,} properties")

    # Load MRT stations
    logger.info("Loading MRT stations...")
    mrt_stations = load_mrt_stations()
    logger.info(f"Loaded {len(mrt_stations)} MRT stations")

    # Calculate nearest MRT
    logger.info("Calculating nearest MRT stations...")
    sample_with_mrt = calculate_nearest_mrt(
        sample_df,
        mrt_stations_df=mrt_stations,
        show_progress=True
    )

    # Show results
    logger.info("\n" + "=" * 60)
    logger.info("Sample Results:")
    logger.info("=" * 60)

    result_cols = ['address', 'nearest_mrt_name', 'nearest_mrt_distance']
    if 'town' in sample_with_mrt.columns:
        result_cols.insert(1, 'town')
    if 'property_type' in sample_with_mrt.columns:
        result_cols.insert(1, 'property_type')

    print(sample_with_mrt[result_cols].head(10).to_string())

    # Summary statistics
    logger.info("\n" + "=" * 60)
    logger.info("Summary Statistics:")
    logger.info("=" * 60)
    logger.info(f"Total properties processed: {len(sample_with_mrt):,}")
    logger.info(f"Mean distance to MRT: {sample_with_mrt['nearest_mrt_distance'].mean():.0f}m")
    logger.info(f"Median distance to MRT: {sample_with_mrt['nearest_mrt_distance'].median():.0f}m")
    logger.info(f"Min distance: {sample_with_mrt['nearest_mrt_distance'].min():.0f}m")
    logger.info(f"Max distance: {sample_with_mrt['nearest_mrt_distance'].max():.0f}m")

    within_500m = (sample_with_mrt['nearest_mrt_distance'] <= 500).sum()
    within_1km = (sample_with_mrt['nearest_mrt_distance'] <= 1000).sum()
    logger.info(f"Properties within 500m: {within_500m:,} ({within_500m/len(sample_with_mrt)*100:.1f}%)")
    logger.info(f"Properties within 1km: {within_1km:,} ({within_1km/len(sample_with_mrt)*100:.1f}%)")

    # Most common MRT stations
    logger.info("\nTop 10 most common nearest MRT stations:")
    top_mrt = sample_with_mrt['nearest_mrt_name'].value_counts().head(10)
    for mrt, count in top_mrt.items():
        logger.info(f"  {mrt}: {count:,} properties")

    logger.info("\n" + "=" * 60)
    logger.info("Test completed successfully!")
    logger.info("=" * 60)

    # Save test output
    output_path = Config.DATA_DIR / "test_mrt_output.parquet"
    sample_with_mrt.to_parquet(output_path, compression='snappy', index=False)
    logger.info(f"\nTest output saved to: {output_path}")


if __name__ == "__main__":
    main()
