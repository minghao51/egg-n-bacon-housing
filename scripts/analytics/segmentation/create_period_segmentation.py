#!/usr/bin/env python3
"""
Create Period-Dependent Market Segmentation by Price Tiers.

This script creates price tier classifications (Mass Market, Mid-Tier, Luxury)
based on price percentiles within each property type AND 5-year time period.
This accounts for inflation and market changes over time.

Usage:
    uv run python scripts/create_period_segmentation.py
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


def create_era_segments(df: pd.DataFrame) -> pd.DataFrame:
    """Create broader era segments for comparative analysis.

    Args:
        df: Transaction data with year column

    Returns:
        DataFrame with era column added
    """
    logger.info("\nCreating era segments...")

    df = df.copy()

    # Create era segments based on year
    # pre_covid: 2015-2021 (includes early COVID years 2020-2021)
    # recent: 2022-2026 (post-pandemic recovery)
    def assign_era(year):
        if year <= 2021:
            return 'pre_covid'
        else:
            return 'recent'

    df['era'] = df['year'].apply(assign_era)

    # Report era distribution
    logger.info("\nEra Distribution:")
    for era in sorted(df['era'].unique()):
        count = (df['era'] == era).sum()
        pct = count / len(df) * 100
        logger.info(f"  {era}: {count:,} transactions ({pct:.1f}%)")

    return df


def create_comparison_eras(df: pd.DataFrame) -> pd.DataFrame:
    """Create era comparison groups for side-by-side analysis.

    Args:
        df: Transaction data with year column

    Returns:
        DataFrame with comparison_era column added
    """
    df = df.copy()

    def assign_comparison_era(year):
        if year <= 2019:
            return 'pre_covid_strict'  # 2015-2019, before pandemic
        elif year <= 2021:
            return 'covid_period'  # 2020-2021
        else:
            return 'post_covid'  # 2022-2026

    df['comparison_era'] = df['year'].apply(assign_comparison_era)

    # Report distribution
    logger.info("\nDetailed Era Distribution (for comparison):")
    for era in sorted(df['comparison_era'].unique()):
        count = (df['comparison_era'] == era).sum()
        pct = count / len(df) * 100
        logger.info(f"  {era}: {count:,} transactions ({pct:.1f}%)")

    return df


def create_5year_periods(df: pd.DataFrame) -> pd.DataFrame:
    """Create 5-year period buckets for transactions.

    Args:
        df: Transaction data with transaction_date column

    Returns:
        DataFrame with period_5yr column added
    """
    logger.info("Creating 5-year periods...")

    df = df.copy()

    # Extract year
    df['year'] = pd.to_datetime(df['transaction_date']).dt.year

    # Create 5-year periods
    df['period_5yr'] = (df['year'] // 5) * 5
    df['period_5yr'] = df['period_5yr'].astype(str) + '-' + (df['period_5yr'] + 4).astype(str)

    # Report period distribution
    logger.info("\n5-Year Period Distribution:")
    for period in sorted(df['period_5yr'].unique()):
        count = (df['period_5yr'] == period).sum()
        logger.info(f"  {period}: {count:,} transactions")

    return df


def calculate_period_dependent_tiers(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate price tiers based on price percentiles by property type AND period.

    Args:
        df: Transaction data with price, property_type, and period_5yr columns

    Returns:
        DataFrame with market_tier_period column added
    """
    logger.info("\nCalculating period-dependent price tiers...")

    df = df.copy()

    # Calculate price tiers within each property type AND period
    def assign_tier(group):
        """Assign tier based on price percentile within property type + period."""
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

    # Apply tier assignment within each property type + period
    df['market_tier_period'] = df.groupby(['property_type', 'period_5yr'], group_keys=False).apply(
        lambda g: assign_tier(g)
    )

    # Report tier distribution by period
    logger.info("\nMarket Tier Distribution by Period:")
    for period in sorted(df['period_5yr'].unique()):
        period_data = df[df['period_5yr'] == period]
        logger.info(f"\n{period}:")
        for ptype in period_data['property_type'].unique():
            ptype_data = period_data[period_data['property_type'] == ptype]
            logger.info(f"  {ptype}:")
            for tier in ['Mass Market', 'Mid-Tier', 'Luxury']:
                count = (ptype_data['market_tier_period'] == tier).sum()
                if count > 0:
                    pct = count / len(ptype_data) * 100
                    tier_prices = ptype_data[ptype_data['market_tier_period'] == tier]['price']
                    logger.info(f"    {tier}: {count:,} ({pct:.1f}%) - Median: ${tier_prices.median():,.0f}")

    return df


def calculate_period_psf_tiers(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate period-dependent PSF-based tiers.

    Args:
        df: Transaction data with price_psf column

    Returns:
        DataFrame with psf_tier_period column added
    """
    logger.info("\nCalculating period-dependent PSF tiers...")

    df = df.copy()

    # Calculate PSF tiers within each property type AND period
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

    # Apply tier assignment within each property type + period
    df['psf_tier_period'] = df.groupby(['property_type', 'period_5yr'], group_keys=False).apply(
        lambda g: assign_psf_tier(g)
    )

    return df


def analyze_tier_evolution(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze how tier thresholds evolve over time.

    Args:
        df: Transaction data with market_tier_period

    Returns:
        DataFrame with tier threshold evolution
    """
    logger.info("\nAnalyzing tier threshold evolution...")

    # Calculate threshold for each tier by property type and period
    thresholds = []

    for (ptype, period), group in df.groupby(['property_type', 'period_5yr']):
        p30 = group['price'].quantile(0.30)
        p70 = group['price'].quantile(0.70)
        max_price = group['price'].max()

        thresholds.append({
            'property_type': ptype,
            'period': period,
            'mass_market_max': p30,
            'mid_tier_max': p70,
            'luxury_min': p70,
            'max_price': max_price,
            'transaction_count': len(group)
        })

    threshold_df = pd.DataFrame(thresholds)

    # Show evolution for each property type
    logger.info("\nTier Threshold Evolution (HDB):")
    hdb_thresholds = threshold_df[threshold_df['property_type'] == 'HDB'].sort_values('period')
    for _, row in hdb_thresholds.iterrows():
        logger.info(f"  {row['period']}: Mass ≤${row['mass_market_max']:,.0f} | "
                   f"Mid ${row['mass_market_max']:,.0f}-${row['mid_tier_max']:,.0f} | "
                   f"Luxury ≥${row['luxury_min']:,.0f}")

    logger.info("\nTier Threshold Evolution (Condominium):")
    condo_thresholds = threshold_df[threshold_df['property_type'] == 'Condominium'].sort_values('period')
    for _, row in condo_thresholds.iterrows():
        logger.info(f"  {row['period']}: Mass ≤${row['mass_market_max']:,.0f} | "
                   f"Mid ${row['mass_market_max']:,.0f}-${row['mid_tier_max']:,.0f} | "
                   f"Luxury ≥${row['luxury_min']:,.0f}")

    logger.info("\nTier Threshold Evolution (EC):")
    ec_thresholds = threshold_df[threshold_df['property_type'] == 'EC'].sort_values('period')
    for _, row in ec_thresholds.iterrows():
        logger.info(f"  {row['period']}: Mass ≤${row['mass_market_max']:,.0f} | "
                   f"Mid ${row['mass_market_max']:,.0f}-${row['mid_tier_max']:,.0f} | "
                   f"Luxury ≥${row['luxury_min']:,.0f}")

    return threshold_df


def compare_old_vs_new_segmentation(df: pd.DataFrame):
    """Compare static vs period-dependent segmentation.

    Args:
        df: Transaction data with both segmentation methods
    """
    logger.info("\n" + "="*80)
    logger.info("COMPARISON: Static vs Period-Dependent Segmentation")
    logger.info("="*80)

    # Compare tier distribution changes
    logger.info("\nImpact of Period-Dependent Segmentation:")
    logger.info("(Shows how many transactions moved tiers)")

    # Count tier changes
    if 'market_tier_period' in df.columns and 'market_tier' in df.columns:
        comparison = df.groupby(['property_type', 'market_tier', 'market_tier_period']).size().reset_index(name='count')

        logger.info("\nTier Transitions (Top 20):")
        # Filter to actual transitions (where tiers changed)
        transitions = comparison[comparison['market_tier'] != comparison['market_tier_period']]
        transitions = transitions.sort_values('count', ascending=False).head(20)

        for _, row in transitions.iterrows():
            logger.info(f"  {row['property_type']}: {row['market_tier']} → {row['market_tier_period']}: "
                       f"{row['count']:,} transactions")

        total_changed = transitions['count'].sum()
        total_transactions = len(df)
        logger.info(f"\nTotal tier transitions: {total_changed:,} ({total_changed/total_transactions*100:.1f}%)")


def save_segmentation_results(df: pd.DataFrame, thresholds: pd.DataFrame, output_dir: Path):
    """Save segmentation results.

    Args:
        df: Transaction data with period tiers
        thresholds: Tier threshold evolution
        output_dir: Directory to save results
    """
    logger.info("\nSaving segmentation results...")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save full dataset with period tiers
    segmented_path = output_dir / 'housing_unified_period_segmented.parquet'
    df.to_parquet(segmented_path, compression='snappy', index=False)
    logger.info(f"Saved period-segmented dataset to {segmented_path}")

    # Save threshold evolution
    thresholds_path = output_dir / 'tier_thresholds_evolution.csv'
    thresholds.to_csv(thresholds_path, index=False)
    logger.info(f"Saved tier threshold evolution to {thresholds_path}")

    # Save recent period thresholds (for quick reference)
    recent_thresholds = thresholds.sort_values('period').groupby('property_type').last().reset_index()
    recent_path = output_dir / 'tier_thresholds_recent_periods.csv'
    recent_thresholds.to_csv(recent_path, index=False)
    logger.info(f"Saved recent period thresholds to {recent_path}")

    # Save era summary (Phase 3 enhancement)
    if 'era' in df.columns:
        era_summary_path = output_dir / 'era_summary.csv'
        era_summary = df.groupby(['era', 'property_type']).agg({
            'price': ['count', 'median', 'mean'],
            'price_psf': 'median'
        }).reset_index()
        era_summary.columns = ['era', 'property_type', 'count', 'median_price', 'mean_price', 'median_price_psf']
        era_summary.to_csv(era_summary_path, index=False)
        logger.info(f"Saved era summary to {era_summary_path}")

    # Save comparison era summary
    if 'comparison_era' in df.columns:
        comparison_era_path = output_dir / 'comparison_era_summary.csv'
        comparison_summary = df.groupby(['comparison_era', 'property_type']).agg({
            'price': ['count', 'median', 'mean'],
            'price_psf': 'median'
        }).reset_index()
        comparison_summary.columns = ['comparison_era', 'property_type', 'count', 'median_price', 'mean_price', 'median_price_psf']
        comparison_summary.to_csv(comparison_era_path, index=False)
        logger.info(f"Saved comparison era summary to {comparison_era_path}")


def main():
    """Main pipeline execution."""

    logger.info("=" * 60)
    logger.info("Period-Dependent Market Segmentation")
    logger.info("=" * 60)

    # Load L3 unified dataset
    logger.info("Loading L3 unified dataset...")
    l3_path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"

    if not l3_path.exists():
        logger.error(f"L3 dataset not found: {l3_path}")
        return

    df = pd.read_parquet(l3_path)
    logger.info(f"Loaded {len(df):,} transactions")

    # Create 5-year periods
    df = create_5year_periods(df)

    # Create era segments (Phase 3 enhancement)
    df = create_era_segments(df)

    # Create detailed comparison eras
    df = create_comparison_eras(df)

    # Calculate period-dependent price tiers
    df = calculate_period_dependent_tiers(df)

    # Calculate period-dependent PSF tiers
    df = calculate_period_psf_tiers(df)

    # Analyze tier evolution
    thresholds = analyze_tier_evolution(df)

    # Compare old vs new segmentation (if old exists)
    if 'market_tier' in df.columns:
        compare_old_vs_new_segmentation(df)

    # Save results
    output_dir = Config.DATA_DIR / "analysis" / "market_segmentation_period"
    save_segmentation_results(df, thresholds, output_dir)

    logger.info("=" * 60)
    logger.info("Period-dependent segmentation complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
