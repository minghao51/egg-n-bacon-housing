#!/usr/bin/env python3
"""
Analyze HDB Rental Market and Compare with Resale Trends.

This script analyzes HDB rental data, compares rental trends with resale prices,
and identifies arbitrage opportunities (rental yield > housing loan interest).

Usage:
    uv run python scripts/analyze_hdb_rental_market.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_rental_data() -> pd.DataFrame:
    """Load HDB rental data.

    Returns:
        DataFrame with rental transactions
    """
    logger.info("Loading HDB rental data...")

    path = Config.PARQUETS_DIR / "L1" / "housing_hdb_rental.parquet"

    if not path.exists():
        logger.error(f"HDB rental data not found: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    # Convert date
    df['rent_approval_date'] = pd.to_datetime(df['rent_approval_date'], errors='coerce')
    df['year'] = df['rent_approval_date'].dt.year
    df['month'] = df['rent_approval_date'].dt.to_period('M').astype(str)

    logger.info(f"Loaded {len(df):,} rental records")
    logger.info(f"Date range: {df['rent_approval_date'].min()} to {df['rent_approval_date'].max()}")

    return df


def load_resale_data() -> pd.DataFrame:
    """Load HDB resale data for comparison.

    Returns:
        DataFrame with resale transactions
    """
    logger.info("Loading HDB resale data...")

    path = Config.PARQUETS_DIR / "L1" / "housing_hdb_transaction.parquet"

    if not path.exists():
        logger.error(f"HDB resale data not found: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)

    # Convert date
    df['month'] = pd.to_datetime(df['month'], errors='coerce').dt.to_period('M').astype(str)
    df['year'] = pd.to_datetime(df['month']).dt.year

    logger.info(f"Loaded {len(df):,} resale records")

    return df


def analyze_rental_trends(rental_df: pd.DataFrame):
    """Analyze rental market trends.

    Args:
        rental_df: HDB rental data
    """
    logger.info("\n" + "="*60)
    logger.info("RENTAL MARKET ANALYSIS")
    logger.info("="*60)

    # Monthly rental trends
    monthly_rent = rental_df.groupby(['year', 'town'])['monthly_rent'].median().reset_index()
    monthly_rent = monthly_rent.groupby('year')['monthly_rent'].median()

    logger.info("\nMedian Monthly Rent by Year:")
    for year, rent in monthly_rent.items():
        if year >= 2015:  # Show recent years
            logger.info(f"  {year}: ${rent:,.0f}")

    # Rental by town
    logger.info("\nTop 10 Towns by Median Rent (Recent):")
    recent_rental = rental_df[rental_df['year'] >= 2024]
    town_rental = recent_rental.groupby('town')['monthly_rent'].agg(['median', 'count'])
    town_rental = town_rental.sort_values('median', ascending=False).head(10)
    for town, row in town_rental.iterrows():
        logger.info(f"  {town}: ${row['median']:,.0f} ({row['count']:,} rentals)")

    # Rental by flat type
    logger.info("\nMedian Rent by Flat Type (Recent):")
    flat_rental = recent_rental.groupby('flat_type')['monthly_rent'].agg(['median', 'count'])
    flat_rental = flat_rental.sort_values('median', ascending=False)
    for flat_type, row in flat_rental.iterrows():
        logger.info(f"  {flat_type}: ${row['median']:,.0f} ({row['count']:,} rentals)")


def compare_rental_vs_resale(rental_df: pd.DataFrame, resale_df: pd.DataFrame):
    """Compare rental and resale price trends.

    Args:
        rental_df: HDB rental data
        resale_df: HDB resale data
    """
    logger.info("\n" + "="*60)
    logger.info("RENTAL VS RESALE COMPARISON")
    logger.info("="*60)

    # Merge rental and resale by town and flat type
    # Use recent data (2024 onwards)
    recent_rental = rental_df[rental_df['year'] >= 2024].copy()
    recent_resale = resale_df[resale_df['year'] >= 2024].copy()

    # Aggregate by town and flat type
    rental_agg = recent_rental.groupby(['town', 'flat_type'])['monthly_rent'].median().reset_index()
    resale_agg = recent_resale.groupby(['town', 'flat_type'])['resale_price'].median().reset_index()

    # Merge
    comparison = pd.merge(
        rental_agg,
        resale_agg,
        on=['town', 'flat_type'],
        how='inner'
    )

    # Calculate annualized rent
    comparison['annual_rent'] = comparison['monthly_rent'] * 12

    # Calculate gross rental yield
    comparison['rental_yield_pct'] = (comparison['annual_rent'] / comparison['resale_price']) * 100

    logger.info("\nTop 15 Highest Rental Yields (by town + flat type):")
    top_yields = comparison.sort_values('rental_yield_pct', ascending=False).head(15)
    for _, row in top_yields.iterrows():
        logger.info(f"  {row['town']} - {row['flat_type']}: "
                   f"${row['monthly_rent']:,.0f}/mo vs ${row['resale_price']:,.0f} = "
                   f"{row['rental_yield_pct']:.2f}% yield")

    # Summary statistics
    logger.info(f"\nRental Yield Summary:")
    logger.info(f"  Median yield: {comparison['rental_yield_pct'].median():.2f}%")
    logger.info(f"  Mean yield: {comparison['rental_yield_pct'].mean():.2f}%")
    logger.info(f"  Min yield: {comparison['rental_yield_pct'].min():.2f}%")
    logger.info(f"  Max yield: {comparison['rental_yield_pct'].max():.2f}%")

    # Count high-yield opportunities (>5%)
    high_yield = comparison[comparison['rental_yield_pct'] > 5.0]
    logger.info(f"\nHigh-yield opportunities (>5%): {len(high_yield)} town/flat_type combos")

    return comparison


def analyze_rental_affordability(rental_df: pd.DataFrame):
    """Analyze rental affordability.

    Args:
        rental_df: HDB rental data
    """
    logger.info("\n" + "="*60)
    logger.info("RENTAL AFFORDABILITY ANALYSIS")
    logger.info("="*60)

    recent_rental = rental_df[rental_df['year'] >= 2024]

    # Analyze rent distribution by flat type
    for flat_type in ['1-Room', '2-Room', '3-Room', '4-Room', '5-Room']:
        if flat_type in recent_rental['flat_type'].values:
            flat_data = recent_rental[recent_rental['flat_type'] == flat_type]['monthly_rent']

            logger.info(f"\n{flat_type} Rent Distribution:")
            logger.info(f"  Min: ${flat_data.min():,.0f}")
            logger.info(f"  25th percentile: ${flat_data.quantile(0.25):,.0f}")
            logger.info(f"  Median: ${flat_data.median():,.0f}")
            logger.info(f"  75th percentile: ${flat_data.quantile(0.75):,.0f}")
            logger.info(f"  Max: ${flat_data.max():,.0f}")


def visualize_rental_market(rental_df: pd.DataFrame, resale_df: pd.DataFrame, output_dir: Path):
    """Create rental market visualizations.

    Args:
        rental_df: HDB rental data
        resale_df: HDB resale data
        output_dir: Directory to save plots
    """
    logger.info("\nCreating rental market visualizations...")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (14, 8)

    # 1. Monthly rent trend over time
    fig, ax = plt.subplots(figsize=(14, 6))
    monthly_trend = rental_df.groupby('year')['monthly_rent'].median()
    monthly_trend.plot(kind='line', marker='o', ax=ax)
    ax.set_title('HDB Median Monthly Rent Trend (2015-2025)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel('Median Monthly Rent (SGD)', fontsize=12)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / 'rental_trend_over_time.png', dpi=150)
    logger.info(f"Saved: {output_dir / 'rental_trend_over_time.png'}")
    plt.close()

    # 2. Rent distribution by flat type
    fig, ax = plt.subplots(figsize=(14, 6))
    recent_rental = rental_df[rental_df['year'] >= 2024]
    sns.boxplot(data=recent_rental, x='flat_type', y='monthly_rent', ax=ax)
    ax.set_title('HDB Monthly Rent Distribution by Flat Type (2024+)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Flat Type', fontsize=12)
    ax.set_ylabel('Monthly Rent (SGD)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'rental_by_flat_type.png', dpi=150)
    logger.info(f"Saved: {output_dir / 'rental_by_flat_type.png'}")
    plt.close()

    logger.info("Visualizations complete!")


def save_rental_analysis(comparison: pd.DataFrame, output_dir: Path):
    """Save rental analysis results.

    Args:
        comparison: Rental vs resale comparison
        output_dir: Directory to save results
    """
    logger.info("\nSaving rental analysis results...")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save comparison
    comparison_path = output_dir / 'rental_vs_resale_comparison.csv'
    comparison.to_csv(comparison_path, index=False)
    logger.info(f"Saved rental vs resale comparison to {comparison_path}")


def main():
    """Main pipeline execution."""

    logger.info("=" * 60)
    logger.info("HDB Rental Market Analysis")
    logger.info("=" * 60)

    # Load data
    rental_df = load_rental_data()
    resale_df = load_resale_data()

    if rental_df.empty:
        logger.error("No rental data available. Exiting.")
        return

    # Analyze rental trends
    analyze_rental_trends(rental_df)

    # Compare rental vs resale
    if not resale_df.empty:
        comparison = compare_rental_vs_resale(rental_df, resale_df)
    else:
        logger.warning("No resale data available for comparison")
        comparison = pd.DataFrame()

    # Analyze affordability
    analyze_rental_affordability(rental_df)

    # Create visualizations
    output_dir = Config.DATA_DIR / "analysis" / "rental_market"
    visualize_rental_market(rental_df, resale_df, output_dir)

    # Save results
    if not comparison.empty:
        # Re-run comparison to get the dataframe
        recent_rental = rental_df[rental_df['year'] >= 2024].copy()
        recent_resale = resale_df[resale_df['year'] >= 2024].copy()
        rental_agg = recent_rental.groupby(['town', 'flat_type'])['monthly_rent'].median().reset_index()
        resale_agg = recent_resale.groupby(['town', 'flat_type'])['resale_price'].median().reset_index()
        comparison = pd.merge(rental_agg, resale_agg, on=['town', 'flat_type'], how='inner')
        comparison['annual_rent'] = comparison['monthly_rent'] * 12
        comparison['rental_yield_pct'] = (comparison['annual_rent'] / comparison['resale_price']) * 100

        save_rental_analysis(comparison, output_dir)

    logger.info("=" * 60)
    logger.info("Rental market analysis complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
