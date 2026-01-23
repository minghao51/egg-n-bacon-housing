#!/usr/bin/env python3
"""
Analyze HDB Lease Decay Impact.

This script analyzes how HDB prices vary by remaining lease duration.
Helps quantify the lease decay effect on property prices.

Usage:
    uv run python scripts/analyze_lease_decay.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_hdb_data() -> pd.DataFrame:
    """Load HDB transaction data."""
    logger.info("Loading HDB transaction data...")

    path = Config.PARQUETS_DIR / "L1" / "housing_hdb_transaction.parquet"
    df = pd.read_parquet(path)

    logger.info(f"Loaded {len(df):,} transactions")
    return df


def clean_lease_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and prepare lease data for analysis.

    Args:
        df: Raw HDB transaction data

    Returns:
        Cleaned DataFrame with lease years
    """
    logger.info("Cleaning lease data...")

    # Check if remaining_lease_months exists
    if 'remaining_lease_months' not in df.columns:
        logger.error("Column 'remaining_lease_months' not found!")
        return df

    # Convert to years and handle missing values
    df['remaining_lease_years'] = df['remaining_lease_months'] / 12

    # Filter out invalid values
    df = df[df['remaining_lease_years'].between(30, 99)]  # HDB leases are 99 years

    logger.info(f"Valid records: {len(df):,}")
    logger.info(f"Lease range: {df['remaining_lease_years'].min():.0f} - {df['remaining_lease_years'].max():.0f} years")

    return df


def create_lease_bands(df: pd.DataFrame) -> pd.DataFrame:
    """Create lease duration bands for analysis.

    Args:
        df: HDB transaction data with remaining_lease_years

    Returns:
        DataFrame with lease_band column added
    """
    logger.info("Creating lease bands...")

    # Define lease bands
    bins = [0, 60, 70, 80, 90, 100]
    labels = ['<60 years', '60-70 years', '70-80 years', '80-90 years', '90+ years']

    df['lease_band'] = pd.cut(
        df['remaining_lease_years'],
        bins=bins,
        labels=labels,
        include_lowest=True
    )

    # Count records per band
    band_counts = df['lease_band'].value_counts().sort_index()
    logger.info("\nLease band distribution:")
    for band, count in band_counts.items():
        logger.info(f"  {band}: {count:,} ({count/len(df)*100:.1f}%)")

    return df


def calculate_price_by_lease_band(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate price statistics by lease band.

    Args:
        df: HDF transaction data with lease_band

    Returns:
        DataFrame with price statistics per band
    """
    logger.info("Calculating price statistics by lease band...")

    # Calculate PSM if not exists
    if 'floor_area_sqm' in df.columns and 'resale_price' in df.columns:
        df['price_per_sqm'] = df['resale_price'] / df['floor_area_sqm']

    # Group by lease band and calculate statistics
    price_stats = df.groupby('lease_band').agg({
        'resale_price': ['count', 'median', 'mean', 'std'],
        'price_per_sqm': ['median', 'mean'],
        'remaining_lease_years': ['min', 'max', 'mean']
    }).round(0)

    # Flatten column names
    price_stats.columns = ['_'.join(col).strip() for col in price_stats.columns.values]
    price_stats = price_stats.reset_index()

    logger.info("\nPrice by lease band:")
    logger.info(f"\n{price_stats.to_string()}")

    return price_stats


def calculate_lease_decay_rate(df: pd.DataFrame, price_stats: pd.DataFrame) -> pd.DataFrame:
    """Calculate annual decay rate by lease band.

    Args:
        df: HDB transaction data
        price_stats: Price statistics by lease band

    Returns:
        DataFrame with decay rate analysis
    """
    logger.info("Calculating lease decay rate...")

    # Calculate average price per year of remaining lease
    band_analysis = []

    for band in df['lease_band'].cat.categories:
        band_data = df[df['lease_band'] == band]

        avg_lease_years = band_data['remaining_lease_years'].mean()
        avg_price = band_data['resale_price'].median()
        avg_psm = band_data['price_per_sqm'].median()

        band_analysis.append({
            'lease_band': band,
            'avg_remaining_lease_years': avg_lease_years,
            'median_price': avg_price,
            'median_psm': avg_psm,
            'transaction_count': len(band_data)
        })

    analysis_df = pd.DataFrame(band_analysis)

    # Calculate decay rate relative to 90+ years baseline
    baseline = analysis_df[analysis_df['lease_band'] == '90+ years']['median_psm'].values[0]
    analysis_df['discount_to_baseline'] = (
        (baseline - analysis_df['median_psm']) / baseline * 100
    ).round(1)

    # Calculate annual decay rate (simple linear approximation)
    analysis_df['annual_decay_pct'] = (
        analysis_df['discount_to_baseline'] / (99 - analysis_df['avg_remaining_lease_years'])
    ).round(2)

    logger.info("\nLease decay analysis:")
    logger.info(f"\n{analysis_df.to_string()}")

    return analysis_df


def visualize_lease_decay(df: pd.DataFrame, output_dir: Path):
    """Create visualizations for lease decay analysis.

    Args:
        df: HDB transaction data with lease bands
        output_dir: Directory to save plots
    """
    logger.info("Creating visualizations...")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (12, 6)

    # 1. Price distribution by lease band
    fig, ax = plt.subplots(figsize=(12, 6))
    df_sorted = df.sort_values('lease_band')
    sns.boxplot(data=df_sorted, x='lease_band', y='resale_price', ax=ax)
    ax.set_title('HDB Resale Price Distribution by Remaining Lease Band', fontsize=14, fontweight='bold')
    ax.set_xlabel('Remaining Lease Band', fontsize=12)
    ax.set_ylabel('Resale Price (SGD)', fontsize=12)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'lease_decay_price_distribution.png', dpi=150)
    logger.info(f"Saved: {output_dir / 'lease_decay_price_distribution.png'}")
    plt.close()

    # 2. Median price per SQM by lease band
    fig, ax = plt.subplots(figsize=(12, 6))
    psm_by_band = df.groupby('lease_band')['price_per_sqm'].median().reset_index()
    psm_by_band = psm_by_band.sort_values('lease_band')
    sns.barplot(data=psm_by_band, x='lease_band', y='price_per_sqm', ax=ax, palette='RdYlGn')
    ax.set_title('Median Price per SQM by Remaining Lease Band', fontsize=14, fontweight='bold')
    ax.set_xlabel('Remaining Lease Band', fontsize=12)
    ax.set_ylabel('Median Price per SQM (SGD)', fontsize=12)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'lease_decay_psm_by_band.png', dpi=150)
    logger.info(f"Saved: {output_dir / 'lease_decay_psm_by_band.png'}")
    plt.close()

    # 3. Transaction count by lease band
    fig, ax = plt.subplots(figsize=(12, 6))
    count_by_band = df['lease_band'].value_counts().sort_index()
    count_by_band.plot(kind='bar', ax=ax, color='steelblue')
    ax.set_title('Transaction Volume by Remaining Lease Band', fontsize=14, fontweight='bold')
    ax.set_xlabel('Remaining Lease Band', fontsize=12)
    ax.set_ylabel('Transaction Count', fontsize=12)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'lease_decay_transaction_volume.png', dpi=150)
    logger.info(f"Saved: {output_dir / 'lease_decay_transaction_volume.png'}")
    plt.close()

    logger.info("Visualizations complete!")


def save_results(price_stats: pd.DataFrame, decay_analysis: pd.DataFrame, output_dir: Path):
    """Save analysis results to CSV.

    Args:
        price_stats: Price statistics by lease band
        decay_analysis: Lease decay analysis
        output_dir: Directory to save results
    """
    logger.info("Saving results...")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save price statistics
    price_stats_path = output_dir / 'lease_price_statistics.csv'
    price_stats.to_csv(price_stats_path, index=False)
    logger.info(f"Saved: {price_stats_path}")

    # Save decay analysis
    decay_path = output_dir / 'lease_decay_analysis.csv'
    decay_analysis.to_csv(decay_path, index=False)
    logger.info(f"Saved: {decay_path}")


def main():
    """Main pipeline execution."""

    logger.info("=" * 60)
    logger.info("HDB Lease Decay Analysis")
    logger.info("=" * 60)

    # Load data
    hdb_df = load_hdb_data()

    # Clean data
    hdb_df = clean_lease_data(hdb_df)

    # Create lease bands
    hdb_df = create_lease_bands(hdb_df)

    # Calculate price by lease band
    price_stats = calculate_price_by_lease_band(hdb_df)

    # Calculate decay rate
    decay_analysis = calculate_lease_decay_rate(hdb_df, price_stats)

    # Create visualizations
    output_dir = Config.DATA_DIR / "analysis" / "lease_decay"
    visualize_lease_decay(hdb_df, output_dir)

    # Save results
    save_results(price_stats, decay_analysis, output_dir)

    logger.info("=" * 60)
    logger.info("Analysis complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
