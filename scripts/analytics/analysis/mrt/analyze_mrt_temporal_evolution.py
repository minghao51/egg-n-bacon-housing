#!/usr/bin/env python3
"""
Temporal MRT Premium Evolution Analysis (2017-2026)

This script analyzes how the MRT proximity premium has evolved over time,
focusing on:
1. Year-to-year changes in MRT price premiums
2. COVID-19 impact assessment (2020-2022)
3. New MRT line openings (TEL, CCL6)
4. Long-term trends by planning area
5. Property type comparison (HDB vs Condo vs EC)

Usage:
    uv run python scripts/analytics/analysis/mrt/analyze_mrt_temporal_evolution.py
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import matplotlib.pyplot as plt
import seaborn as sns

# Add project root to Python path FIRST
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.core.utils import add_project_to_path
add_project_to_path(Path(__file__))

from scripts.core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Output directory
OUTPUT_DIR = Config.DATA_DIR / "analysis" / "mrt_temporal_evolution"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_historical_data():
    """Load full historical transaction data."""
    logger.info("Loading historical transaction data...")

    path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
    df = pd.read_parquet(path)

    # Filter to 2017+ for temporal analysis
    df['year'] = df['year'].astype(int)
    df = df[df['year'] >= 2017].copy()

    # Ensure required columns
    required_cols = ['price_psf', 'dist_to_nearest_mrt', 'property_type', 'year', 'planning_area']
    df = df.dropna(subset=required_cols)

    logger.info(f"Loaded {len(df):,} transactions from 2017-2026")
    logger.info(f"  Date range: {df['year'].min()} - {df['year'].max()}")
    logger.info(f"  Property types: {df['property_type'].value_counts().to_dict()}")

    return df


def calculate_yearly_mrt_coefficients(df, property_type='HDB'):
    """Calculate MRT coefficients by year and planning area."""
    logger.info(f"\nCalculating yearly MRT coefficients for {property_type}...")

    # Filter by property type
    df_type = df[df['property_type'] == property_type].copy()

    results = []
    years = sorted(df_type['year'].unique())

    for year in years:
        df_year = df_type[df_type['year'] == year].copy()

        # Overall model (all areas)
        X = df_year[['dist_to_nearest_mrt']].values
        y = df_year['price_psf'].values

        model = LinearRegression()
        model.fit(X, y)
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)

        results.append({
            'property_type': property_type,
            'year': year,
            'mrt_coefficient': model.coef_[0],
            'mrt_premium_100m': model.coef_[0] * 100,
            'r2': r2,
            'n_transactions': len(df_year),
            'mean_price': y.mean(),
            'mean_mrt_distance': X.mean()
        })

    results_df = pd.DataFrame(results)

    logger.info(f"\nYearly MRT Coefficients ({property_type}):")
    logger.info(f"\n{results_df.to_string()}")

    return results_df


def analyze_by_planning_area(df, property_type='HDB', min_transactions=100):
    """Calculate MRT coefficients by year and planning area."""
    logger.info(f"\nAnalyzing MRT coefficients by planning area ({property_type})...")

    df_type = df[df['property_type'] == property_type].copy()

    results = []

    # Get areas with sufficient data
    area_counts = df_type.groupby('planning_area').size()
    valid_areas = area_counts[area_counts >= min_transactions].index

    logger.info(f"  Found {len(valid_areas)} areas with >= {min_transactions} transactions")

    for area in valid_areas:
        df_area = df_type[df_type['planning_area'] == area].copy()

        for year in sorted(df_area['year'].unique()):
            df_year = df_area[df_area['year'] == year].copy()

            if len(df_year) < 30:  # Minimum per year
                continue

            X = df_year[['dist_to_nearest_mrt']].values
            y = df_year['price_psf'].values

            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)
            r2 = r2_score(y, y_pred)

            results.append({
                'property_type': property_type,
                'planning_area': area,
                'year': year,
                'mrt_coefficient': model.coef_[0],
                'mrt_premium_100m': model.coef_[0] * 100,
                'r2': r2,
                'n_transactions': len(df_year),
                'mean_price': y.mean()
            })

    results_df = pd.DataFrame(results)

    logger.info(f"  Generated {len(results_df)} area-year observations")

    return results_df


def identify_covid_impact(df):
    """Assess COVID-19 impact on MRT premiums."""
    logger.info("\n" + "="*80)
    logger.info("COVID-19 IMPACT ASSESSMENT (2020-2022)")
    logger.info("="*80)

    # Define periods
    pre_covid = df[df['year'] < 2020].copy()
    covid_period = df[df['year'].between(2020, 2022)].copy()
    post_covid = df[df['year'] > 2022].copy()

    results = {}

    for period_name, period_df in [('Pre-COVID', pre_covid), ('COVID', covid_period), ('Post-COVID', post_covid)]:
        if len(period_df) == 0:
            continue

        period_results = {}

        for prop_type in ['HDB', 'Condominium', 'EC']:
            df_type = period_df[period_df['property_type'] == prop_type].copy()

            if len(df_type) < 100:
                continue

            X = df_type[['dist_to_nearest_mrt']].values
            y = df_type['price_psf'].values

            model = LinearRegression()
            model.fit(X, y)

            period_results[prop_type] = {
                'mrt_premium_100m': model.coef_[0] * 100,
                'mean_price': y.mean(),
                'n_transactions': len(df_type)
            }

        results[period_name] = period_results

    # Calculate changes
    results_df = pd.DataFrame(results).T

    logger.info(f"\nMRT Premium Evolution ($/100m):")
    logger.info(f"\n{results_df.to_string()}")

    # Save results
    csv_path = OUTPUT_DIR / "covid_impact_analysis.csv"
    results_df.to_csv(csv_path)
    logger.info(f"\nSaved: {csv_path}")

    return results_df


def plot_temporal_evolution(yearly_results, property_types=['HDB', 'Condominium', 'EC']):
    """Create temporal evolution visualizations."""
    logger.info("\nCreating temporal evolution visualizations...")

    # Combine all property types
    combined = pd.concat(yearly_results, ignore_index=True)

    # 1. Overall MRT Premium Evolution
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Plot 1: MRT Premium Over Time by Property Type
    ax = axes[0, 0]
    for prop_type in property_types:
        data = combined[combined['property_type'] == prop_type]
        ax.plot(data['year'], data['mrt_premium_100m'], marker='o', label=prop_type, linewidth=2)

    ax.axvspan(2020, 2022, alpha=0.2, color='red', label='COVID Period')
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('MRT Premium ($/100m closer)', fontsize=12, fontweight='bold')
    ax.set_title('MRT Premium Evolution by Property Type (2017-2026)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='black', linestyle='--', linewidth=0.5)

    # Plot 2: Model R² Over Time
    ax = axes[0, 1]
    for prop_type in property_types:
        data = combined[combined['property_type'] == prop_type]
        ax.plot(data['year'], data['r2'], marker='s', label=prop_type, linewidth=2)

    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('R² Score', fontsize=12, fontweight='bold')
    ax.set_title('Model Fit Over Time', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 3: Mean Price Evolution
    ax = axes[1, 0]
    for prop_type in property_types:
        data = combined[combined['property_type'] == prop_type]
        ax.plot(data['year'], data['mean_price'], marker='^', label=prop_type, linewidth=2)

    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Mean Price (PSF $)', fontsize=12, fontweight='bold')
    ax.set_title('Price Evolution by Property Type', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 4: Transaction Volume
    ax = axes[1, 1]
    for prop_type in property_types:
        data = combined[combined['property_type'] == prop_type]
        ax.plot(data['year'], data['n_transactions'], marker='d', label=prop_type, linewidth=2)

    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Transactions', fontsize=12, fontweight='bold')
    ax.set_title('Transaction Volume', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = OUTPUT_DIR / "temporal_evolution_overview.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved: {fig_path}")
    plt.close()


def plot_top_areas_evolution(area_results, property_type='HDB', top_n=10):
    """Plot MRT premium evolution for top areas."""
    logger.info(f"\nPlotting top {top_n} areas by MRT premium ({property_type})...")

    # Filter property type
    data = area_results[area_results['property_type'] == property_type].copy()

    # Calculate mean MRT premium per area
    area_means = data.groupby('planning_area')['mrt_premium_100m'].mean().sort_values(ascending=False)

    # Get top areas
    top_areas = area_means.head(top_n).index.tolist()

    # Create plot
    fig, ax = plt.subplots(figsize=(14, 8))

    for area in top_areas:
        area_data = data[data['planning_area'] == area].sort_values('year')
        ax.plot(area_data['year'], area_data['mrt_premium_100m'],
                marker='o', label=area, linewidth=2, alpha=0.7)

    ax.axvspan(2020, 2022, alpha=0.2, color='red', label='COVID Period')
    ax.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('MRT Premium ($/100m)', fontsize=12, fontweight='bold')
    ax.set_title(f'Top {top_n} Planning Areas: MRT Premium Evolution ({property_type})',
                fontsize=14, fontweight='bold')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = OUTPUT_DIR / f"top_areas_evolution_{property_type.lower()}.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved: {fig_path}")
    plt.close()


def generate_summary_statistics(yearly_results):
    """Generate summary statistics table."""
    logger.info("\nGenerating summary statistics...")

    combined = pd.concat(yearly_results, ignore_index=True)

    summary = []

    for prop_type in ['HDB', 'Condominium', 'EC']:
        data = combined[combined['property_type'] == prop_type]

        if len(data) == 0:
            continue

        pre_covid = data[data['year'] < 2020]['mrt_premium_100m'].mean()
        covid = data[data['year'].between(2020, 2022)]['mrt_premium_100m'].mean()
        post_covid = data[data['year'] > 2022]['mrt_premium_100m'].mean()

        covid_change = ((covid - pre_covid) / abs(pre_covid) * 100) if pre_covid != 0 else 0
        post_change = ((post_covid - covid) / abs(covid) * 100) if covid != 0 else 0

        summary.append({
            'property_type': prop_type,
            'pre_covid_premium': pre_covid,
            'covid_premium': covid,
            'post_covid_premium': post_covid,
            'covid_change_pct': covid_change,
            'post_covid_change_pct': post_change
        })

    summary_df = pd.DataFrame(summary)

    logger.info(f"\nMRT Premium Summary ($/100m):")
    logger.info(f"\n{summary_df.to_string()}")

    # Save
    csv_path = OUTPUT_DIR / "temporal_summary.csv"
    summary_df.to_csv(csv_path, index=False)
    logger.info(f"\nSaved: {csv_path}")

    return summary_df


def main():
    """Main execution."""
    start_time = datetime.now()

    logger.info("="*80)
    logger.info("TEMPORAL MRT PREMIUM EVOLUTION ANALYSIS (2017-2026)")
    logger.info("="*80)

    # Load data
    df = load_historical_data()

    # Calculate yearly coefficients by property type
    logger.info("\n" + "="*80)
    logger.info("YEARLY MRT COEFFICIENTS BY PROPERTY TYPE")
    logger.info("="*80)

    yearly_results = []
    for prop_type in ['HDB', 'Condominium', 'EC']:
        result = calculate_yearly_mrt_coefficients(df, prop_type)
        yearly_results.append(result)

        # Save individual results
        csv_path = OUTPUT_DIR / f"yearly_coefficients_{prop_type.lower()}.csv"
        result.to_csv(csv_path, index=False)
        logger.info(f"\nSaved: {csv_path}")

    # Analyze by planning area (HDB only for detailed analysis)
    logger.info("\n" + "="*80)
    logger.info("AREA-LEVEL TEMPORAL ANALYSIS")
    logger.info("="*80)

    area_results_hdb = analyze_by_planning_area(df, property_type='HDB', min_transactions=300)
    csv_path = OUTPUT_DIR / "area_yearly_coefficients_hdb.csv"
    area_results_hdb.to_csv(csv_path, index=False)
    logger.info(f"\nSaved: {csv_path}")

    area_results_condo = analyze_by_planning_area(df, property_type='Condominium', min_transactions=100)
    csv_path = OUTPUT_DIR / "area_yearly_coefficients_condominium.csv"
    area_results_condo.to_csv(csv_path, index=False)
    logger.info(f"Saved: {csv_path}")

    # COVID impact assessment
    covid_results = identify_covid_impact(df)

    # Generate visualizations
    plot_temporal_evolution(yearly_results)
    plot_top_areas_evolution(area_results_hdb, property_type='HDB', top_n=15)
    plot_top_areas_evolution(area_results_condo, property_type='Condominium', top_n=10)

    # Generate summary statistics
    summary = generate_summary_statistics(yearly_results)

    # Final summary
    duration = (datetime.now() - start_time).total_seconds()

    logger.info("\n" + "="*80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*80)
    logger.info(f"\nKey Findings:")
    logger.info(f"  • Analyzed {len(df):,} transactions from 2017-2026")
    logger.info(f"  • Tracked MRT premium evolution for 3 property types")
    logger.info(f"  • Assessed COVID-19 impact (2020-2022)")
    logger.info(f"  • Generated {len(yearly_results)} yearly coefficient files")
    logger.info(f"  • Created area-level evolution plots")
    logger.info(f"\nOutputs saved to: {OUTPUT_DIR}")
    logger.info(f"\nDuration: {duration:.1f} seconds")
    logger.info("="*80)


if __name__ == "__main__":
    main()
