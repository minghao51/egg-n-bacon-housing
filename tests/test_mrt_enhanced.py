#!/usr/bin/env python3
"""Test script for enhanced MRT distance features with line information."""

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
    """Test enhanced MRT distance calculation."""
    logger.info("=" * 80)
    logger.info("Testing Enhanced MRT Distance Features")
    logger.info("=" * 80)

    # Load existing unified dataset
    unified_path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"

    if not unified_path.exists():
        logger.error(f"Unified dataset not found: {unified_path}")
        return

    logger.info(f"Loading unified dataset from {unified_path}")
    df = pd.read_parquet(unified_path)

    logger.info(f"Loaded {len(df):,} records")

    # Filter to properties with coordinates
    has_coords = df['lat'].notna() & df['lon'].notna()
    logger.info(f"Properties with coordinates: {has_coords.sum():,} of {len(df):,}")

    # Test on a small sample
    sample_size = min(100, has_coords.sum())
    sample_df = df[has_coords].head(sample_size).copy()

    logger.info(f"Testing on sample of {len(sample_df):,} properties")

    # Load MRT stations
    logger.info("Loading MRT stations with line information...")
    mrt_stations = load_mrt_stations()
    logger.info(f"Loaded {len(mrt_stations)} MRT stations")

    # Show sample stations
    logger.info("\n" + "=" * 80)
    logger.info("Sample MRT Stations:")
    logger.info("=" * 80)
    print(mrt_stations[['name', 'line_names', 'tier', 'is_interchange']].head(10).to_string())

    # Calculate nearest MRT
    logger.info("\n" + "=" * 80)
    logger.info("Calculating nearest MRT stations with enhanced features...")
    logger.info("=" * 80)
    sample_with_mrt = calculate_nearest_mrt(
        sample_df,
        mrt_stations_df=mrt_stations,
        show_progress=False
    )

    # Show results
    logger.info("\n" + "=" * 80)
    logger.info("Enhanced MRT Results - Sample Properties:")
    logger.info("=" * 80)

    result_cols = [
        'address',
        'nearest_mrt_name',
        'nearest_mrt_distance',
        'nearest_mrt_line_names',
        'nearest_mrt_tier',
        'nearest_mrt_is_interchange',
        'nearest_mrt_score'
    ]

    if 'town' in sample_with_mrt.columns:
        result_cols.insert(1, 'town')
    if 'property_type' in sample_with_mrt.columns:
        result_cols.insert(1, 'property_type')

    print(sample_with_mrt[result_cols].head(10).to_string())

    # Enhanced statistics
    logger.info("\n" + "=" * 80)
    logger.info("Enhanced Statistics:")
    logger.info("=" * 80)

    logger.info(f"Total properties processed: {len(sample_with_mrt):,}")

    # Distance stats
    logger.info(f"\nDistance Statistics:")
    logger.info(f"  Mean distance to MRT: {sample_with_mrt['nearest_mrt_distance'].mean():.0f}m")
    logger.info(f"  Median distance to MRT: {sample_with_mrt['nearest_mrt_distance'].median():.0f}m")
    logger.info(f"  Min distance: {sample_with_mrt['nearest_mrt_distance'].min():.0f}m")
    logger.info(f"  Max distance: {sample_with_mrt['nearest_mrt_distance'].max():.0f}m")

    # Tier breakdown
    logger.info(f"\nStation Tier Breakdown:")
    tier_counts = sample_with_mrt['nearest_mrt_tier'].value_counts().sort_index()
    for tier, count in tier_counts.items():
        logger.info(f"  Tier {int(tier)}: {count:,} properties ({count/len(sample_with_mrt)*100:.1f}%)")

    # Interchange breakdown
    interchange_count = sample_with_mrt['nearest_mrt_is_interchange'].sum()
    logger.info(f"\nInterchange Stations:")
    logger.info(f"  Properties near interchanges: {interchange_count:,} ({interchange_count/len(sample_with_mrt)*100:.1f}%)")

    # Score distribution
    logger.info(f"\nStation Score Distribution:")
    logger.info(f"  Mean score: {sample_with_mrt['nearest_mrt_score'].mean():.2f}")
    logger.info(f"  Median score: {sample_with_mrt['nearest_mrt_score'].median():.2f}")
    logger.info(f"  Max score: {sample_with_mrt['nearest_mrt_score'].max():.2f}")

    # Top properties by MRT score
    logger.info("\n" + "=" * 80)
    logger.info("Top 10 Properties by MRT Accessibility Score:")
    logger.info("=" * 80)
    top_properties = sample_with_mrt.nlargest(10, 'nearest_mrt_score')
    print(top_properties[result_cols].to_string())

    # Most common MRT stations
    logger.info("\n" + "=" * 80)
    logger.info("Top 10 Most Common Nearest MRT Stations:")
    logger.info("=" * 80)
    top_mrt = sample_with_mrt['nearest_mrt_name'].value_counts().head(10)
    for mrt, count in top_mrt.items():
        # Get line info for this station
        station_info = sample_with_mrt[sample_with_mrt['nearest_mrt_name'] == mrt].iloc[0]
        lines = station_info['nearest_mrt_line_names']
        tier = int(station_info['nearest_mrt_tier'])
        is_interch = station_info['nearest_mrt_is_interchange']

        interch_marker = " [INTERCHANGE]" if is_interch else ""
        logger.info(f"  {mrt}{interch_marker} (Tier {tier}): {count:,} properties")
        logger.info(f"    Lines: {', '.join(lines)}")

    # Properties within distance by tier
    logger.info("\n" + "=" * 80)
    logger.info("Proximity Analysis by Tier:")
    logger.info("=" * 80)

    for tier in [1, 2, 3]:
        tier_df = sample_with_mrt[sample_with_mrt['nearest_mrt_tier'] == tier]
        if len(tier_df) > 0:
            within_500m = (tier_df['nearest_mrt_distance'] <= 500).sum()
            within_1km = (tier_df['nearest_mrt_distance'] <= 1000).sum()

            logger.info(f"\nTier {tier} Stations:")
            logger.info(f"  Total properties: {len(tier_df):,}")
            logger.info(f"  Within 500m: {within_500m:,} ({within_500m/len(tier_df)*100:.1f}%)")
            logger.info(f"  Within 1km: {within_1km:,} ({within_1km/len(tier_df)*100:.1f}%)")
            logger.info(f"  Mean distance: {tier_df['nearest_mrt_distance'].mean():.0f}m")

    logger.info("\n" + "=" * 80)
    logger.info("Test completed successfully!")
    logger.info("=" * 80)

    # Save test output
    output_path = Config.DATA_DIR / "test_mrt_enhanced_output.parquet"
    sample_with_mrt.to_parquet(output_path, compression='snappy', index=False)
    logger.info(f"\nTest output saved to: {output_path}")


if __name__ == "__main__":
    main()
