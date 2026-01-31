#!/usr/bin/env python3
"""
Create Market Segmentation by Price Tiers.

This script creates price tier classifications (Mass Market, Mid-Tier, Luxury)
based on price percentiles within each property type.

Usage:
    uv run python scripts/create_market_segmentation.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def calculate_price_tiers(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate price tiers based on price percentiles by property type.

    Args:
        df: Transaction data with price and property_type columns

    Returns:
        DataFrame with market_tier column added
    """
    logger.info("Calculating price tiers...")

    df = df.copy()

    # Calculate price tiers within each property type
    def assign_tier(group):
        """Assign tier based on price percentile within property type."""
        p30 = group['price'].quantile(0.30)
        p70 = group['price'].quantile(0.70)

        tiers = []
        for price in group['price']:
            if price <= p30:
                tiers.append('Mass Market')
            elif price <= p70:
                tiers.append('Mid-Tier')
            else:
                tiers.append('Luxury')

        return pd.Series(tiers, index=group.index)

    # Apply tier assignment within each property type
    if 'property_type' in df.columns:
        df['market_tier'] = df.groupby('property_type', group_keys=False).apply(
            lambda g: assign_tier(g)
        )
    else:
        # If no property_type, calculate globally
        df['market_tier'] = assign_tier(df)

    # Report tier distribution
    logger.info("\nMarket Tier Distribution:")
    for ptype in df['property_type'].unique():
        ptype_data = df[df['property_type'] == ptype]
        logger.info(f"\n{ptype}:")
        for tier in ['Mass Market', 'Mid-Tier', 'Luxury']:
            count = (ptype_data['market_tier'] == tier).sum()
            pct = count / len(ptype_data) * 100
            tier_prices = ptype_data[ptype_data['market_tier'] == tier]['price']
            logger.info(f"  {tier}: {count:,} ({pct:.1f}%) - Median: ${tier_prices.median():,.0f}")

    return df


def calculate_psf_tiers(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate PSF-based tiers for standardized comparison.

    Args:
        df: Transaction data with price_psf column

    Returns:
        DataFrame with psf_tier column added
    """
    logger.info("\nCalculating PSF tiers...")

    df = df.copy()

    # Calculate PSF tiers within each property type
    def assign_psf_tier(group):
        """Assign PSF tier based on price per sqft percentile."""
        p30 = group['price_psf'].quantile(0.30)
        p70 = group['price_psf'].quantile(0.70)

        tiers = []
        for psf in group['price_psf']:
            if psf <= p30:
                tiers.append('Low PSF')
            elif psf <= p70:
                tiers.append('Medium PSF')
            else:
                tiers.append('High PSF')

        return pd.Series(tiers, index=group.index)

    # Apply tier assignment within each property type
    if 'property_type' in df.columns:
        df['psf_tier'] = df.groupby('property_type', group_keys=False).apply(
            lambda g: assign_psf_tier(g)
        )
    else:
        df['psf_tier'] = assign_psf_tier(df)

    # Report PSF tier distribution
    logger.info("\nPSF Tier Distribution:")
    for ptype in df['property_type'].unique():
        ptype_data = df[df['property_type'] == ptype]
        logger.info(f"\n{ptype}:")
        for tier in ['Low PSF', 'Medium PSF', 'High PSF']:
            count = (ptype_data['psf_tier'] == tier).sum()
            pct = count / len(ptype_data) * 100
            tier_psf = ptype_data[ptype_data['psf_tier'] == tier]['price_psf']
            logger.info(f"  {tier}: {count:,} ({pct:.1f}%) - Median: ${tier_psf.median():,.0f}/sqft")

    return df


def analyze_tier_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze price performance by market tier.

    Args:
        df: Transaction data with market_tier and transaction_date

    Returns:
        DataFrame with tier performance metrics
    """
    logger.info("\nAnalyzing tier performance...")

    # Extract year from transaction date
    df['year'] = pd.to_datetime(df['transaction_date']).dt.year

    # Calculate annual median price by tier and property type
    performance = df.groupby(['property_type', 'market_tier', 'year']).agg({
        'price': ['median', 'count'],
        'price_psf': 'median'
    }).reset_index()

    performance.columns = ['property_type', 'market_tier', 'year',
                          'median_price', 'transaction_count', 'median_psf']

    logger.info("\nRecent Tier Performance (2024-2026):")
    recent = performance[performance['year'] >= 2024]
    for ptype in recent['property_type'].unique():
        logger.info(f"\n{ptype}:")
        ptype_data = recent[recent['property_type'] == ptype]
        for _, row in ptype_data.iterrows():
            logger.info(f"  {row['year']} {row['market_tier']}: "
                       f"${row['median_price']:,.0f} ({row['transaction_count']:,} transactions)")

    return performance


def save_segmentation_results(df: pd.DataFrame, performance: pd.DataFrame, output_dir: Path):
    """Save segmentation results.

    Args:
        df: Transaction data with tiers
        performance: Tier performance metrics
        output_dir: Directory to save results
    """
    logger.info("\nSaving segmentation results...")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save full dataset with tiers
    segmented_path = output_dir / 'housing_unified_segmented.parquet'
    df.to_parquet(segmented_path, compression='snappy', index=False)
    logger.info(f"Saved segmented dataset to {segmented_path}")

    # Save tier performance
    performance_path = output_dir / 'tier_performance.parquet'
    performance.to_parquet(performance_path, compression='snappy', index=False)
    logger.info(f"Saved tier performance to {performance_path}")

    # Save tier thresholds
    if 'property_type' in df.columns and 'market_tier' in df.columns:
        thresholds = df.groupby('property_type').apply(
            lambda g: pd.Series({
                'mass_market_max': g[g['market_tier'] == 'Mass Market']['price'].max(),
                'mid_tier_max': g[g['market_tier'] == 'Mid-Tier']['price'].max(),
                'luxury_min': g[g['market_tier'] == 'Luxury']['price'].min()
            })
        )
        thresholds_path = output_dir / 'tier_thresholds.csv'
        thresholds.to_csv(thresholds_path)
        logger.info(f"Saved tier thresholds to {thresholds_path}")


def main():
    """Main pipeline execution."""

    logger.info("=" * 60)
    logger.info("Market Segmentation Analysis")
    logger.info("=" * 60)

    # Load L3 unified dataset
    logger.info("Loading L3 unified dataset...")
    l3_path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"

    if not l3_path.exists():
        logger.error(f"L3 dataset not found: {l3_path}")
        return

    df = pd.read_parquet(l3_path)
    logger.info(f"Loaded {len(df):,} transactions")

    # Calculate price tiers
    df = calculate_price_tiers(df)

    # Calculate PSF tiers
    df = calculate_psf_tiers(df)

    # Analyze tier performance
    performance = analyze_tier_performance(df)

    # Save results
    output_dir = Config.DATA_DIR / "analysis" / "market_segmentation"
    save_segmentation_results(df, performance, output_dir)

    logger.info("=" * 60)
    logger.info("Market segmentation complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
