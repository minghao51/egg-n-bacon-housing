#!/usr/bin/env python3
"""
Temporal School Premium Evolution Analysis (2017-2026)

This script analyzes how the school proximity and quality premium has evolved over time,
focusing on:
1. Year-to-year changes in school price premiums
2. COVID-19 impact assessment (2020-2022)
3. Long-term trends by planning area
4. Property type comparison (HDB vs Condo vs EC)

Usage:
    uv run python scripts/analytics/analysis/school/analyze_school_temporal_evolution.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

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
OUTPUT_DIR = Config.DATA_DIR / "analysis" / "school_temporal_evolution"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_historical_data():
    """Load full historical transaction data."""
    logger.info("Loading historical transaction data...")

    path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
    df = pd.read_parquet(path)

    # Filter to 2017+ for temporal analysis
    df['year'] = df['year'].astype(int)
    df = df[df['year'] >= 2017].copy()

    # Check required school features
    school_features = [
        'school_accessibility_score',
        'school_primary_quality_score',
        'school_secondary_quality_score'
    ]

    available_features = [f for f in school_features if f in df.columns]

    if not available_features:
        logger.error("No school features found in dataset!")
        logger.error("Please run L3_export.py to calculate school features first.")
        return None

    logger.info(f"Loaded {len(df):,} transactions from 2017-2026")
    logger.info(f"  Date range: {df['year'].min()} - {df['year'].max()}")
    logger.info(f"  Property types: {df['property_type'].value_counts().to_dict()}")
    logger.info(f"  Available school features: {available_features}")

    return df


def calculate_yearly_school_coefficients(df, property_type='HDB', feature='school_accessibility_score'):
    """Calculate school coefficients by year."""
    logger.info(f"\nCalculating yearly {feature} coefficients for {property_type}...")

    # Filter by property type
    df_type = df[df['property_type'] == property_type].copy()

    # Filter to data with the feature
    df_type = df_type.dropna(subset=[feature])

    results = []
    years = sorted(df_type['year'].unique())

    for year in years:
        df_year = df_type[df_type['year'] == year].copy()

        # Prepare features
        feature_cols = [feature, 'floor_area_sqm', 'year']

        # Add remaining_lease_months for HDB
        if property_type == 'HDB' and 'remaining_lease_months' in df_year.columns:
            feature_cols.append('remaining_lease_months')

        # Select available features
        available_features = [col for col in feature_cols if col in df_year.columns]

        X = df_year[available_features].values
        y = df_year['price_psf'].values

        # Drop NaN
        mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X, y = X[mask], y[mask]

        if len(X) < 30:
            continue

        model = LinearRegression()
        model.fit(X, y)
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)

        # Extract feature coefficient (first column is the school feature)
        feature_idx = 0
        feature_coef = model.coef_[feature_idx]

        results.append({
            'property_type': property_type,
            'year': year,
            'feature': feature,
            'school_coefficient': feature_coef,
            'school_premium_10pt': feature_coef * 10,  # Premium for 0.1 score increase
            'r2': r2,
            'n_transactions': len(df_year),
            'mean_price': y.mean(),
            'mean_feature_value': X[:, feature_idx].mean()
        })

    results_df = pd.DataFrame(results)

    if not results_df.empty:
        logger.info(f"\nYearly {feature} Coefficients ({property_type}):")
        logger.info(f"\n{results_df.to_string()}")

    return results_df


def analyze_by_planning_area(df, property_type='HDB', feature='school_accessibility_score', min_transactions=100):
    """Calculate school coefficients by year and planning area."""
    logger.info(f"\nAnalyzing {feature} coefficients by planning area ({property_type})...")

    df_type = df[df['property_type'] == property_type].copy()
    df_type = df_type.dropna(subset=[feature])

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

            # Prepare features
            feature_cols = [feature, 'floor_area_sqm']

            # Add year if not already there
            if 'year' not in feature_cols:
                feature_cols.append('year')

            available_features = [col for col in feature_cols if col in df_year.columns]

            X = df_year[available_features].values
            y = df_year['price_psf'].values

            # Drop NaN
            mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
            X, y = X[mask], y[mask]

            if len(X) < 20:
                continue

            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)
            r2 = r2_score(y, y_pred)

            results.append({
                'property_type': property_type,
                'planning_area': area,
                'year': year,
                'school_coefficient': model.coef_[0],
                'school_premium_10pt': model.coef_[0] * 10,
                'r2': r2,
                'n_transactions': len(df_year),
                'mean_price': y.mean()
            })

    results_df = pd.DataFrame(results)

    logger.info(f"  Generated {len(results_df)} area-year observations")

    return results_df


def identify_covid_impact(df, feature='school_accessibility_score'):
    """Assess COVID-19 impact on school premiums."""
    logger.info("\n" + "="*80)
    logger.info(f"COVID-19 IMPACT ASSESSMENT (2020-2022) - {feature}")
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
            df_type = df_type.dropna(subset=[feature])

            if len(df_type) < 100:
                continue

            # Prepare features
            feature_cols = [feature, 'floor_area_sqm', 'year']

            if prop_type == 'HDB' and 'remaining_lease_months' in df_type.columns:
                feature_cols.append('remaining_lease_months')

            available_features = [col for col in feature_cols if col in df_type.columns]

            X = df_type[available_features].values
            y = df_type['price_psf'].values

            # Drop NaN
            mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
            X, y = X[mask], y[mask]

            if len(X) < 50:
                continue

            model = LinearRegression()
            model.fit(X, y)

            period_results[prop_type] = {
                'school_premium_10pt': model.coef_[0] * 10,
                'mean_price': y.mean(),
                'n_transactions': len(df_type)
            }

        results[period_name] = period_results

    # Calculate changes
    results_df = pd.DataFrame(results).T

    logger.info("\nSchool Premium Evolution ($/0.1 score increase):")
    logger.info(f"\n{results_df.to_string()}")

    # Save results
    csv_path = OUTPUT_DIR / f"covid_impact_analysis_{feature}.csv"
    results_df.to_csv(csv_path)
    logger.info(f"\nSaved: {csv_path}")

    return results_df


def plot_temporal_evolution(yearly_results, property_types=['HDB', 'Condominium', 'EC']):
    """Create temporal evolution visualizations."""
    logger.info("\nCreating temporal evolution visualizations...")

    # Combine all property types
    combined = pd.concat(yearly_results, ignore_index=True)

    # 1. Overall School Premium Evolution
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Plot 1: School Premium Over Time by Property Type
    ax = axes[0, 0]
    for prop_type in property_types:
        data = combined[combined['property_type'] == prop_type]
        if len(data) > 0:
            ax.plot(data['year'], data['school_premium_10pt'], marker='o', label=prop_type, linewidth=2)

    ax.axvspan(2020, 2022, alpha=0.2, color='red', label='COVID Period')
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('School Premium ($/0.1 score increase)', fontsize=12, fontweight='bold')
    ax.set_title('School Premium Evolution by Property Type (2017-2026)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='black', linestyle='--', linewidth=0.5)

    # Plot 2: Model R² Over Time
    ax = axes[0, 1]
    for prop_type in property_types:
        data = combined[combined['property_type'] == prop_type]
        if len(data) > 0:
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
        if len(data) > 0:
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
        if len(data) > 0:
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
    """Plot school premium evolution for top areas."""
    logger.info(f"\nPlotting top {top_n} areas by school premium ({property_type})...")

    # Filter property type
    data = area_results[area_results['property_type'] == property_type].copy()

    if len(data) == 0:
        logger.warning(f"No data available for {property_type}")
        return

    # Calculate mean school premium per area
    area_means = data.groupby('planning_area')['school_premium_10pt'].mean().sort_values(ascending=False)

    # Get top areas
    top_areas = area_means.head(top_n).index.tolist()

    # Create plot
    fig, ax = plt.subplots(figsize=(14, 8))

    for area in top_areas:
        area_data = data[data['planning_area'] == area].sort_values('year')
        ax.plot(area_data['year'], area_data['school_premium_10pt'],
                marker='o', label=area, linewidth=2, alpha=0.7)

    ax.axvspan(2020, 2022, alpha=0.2, color='red', label='COVID Period')
    ax.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('School Premium ($/0.1 score)', fontsize=12, fontweight='bold')
    ax.set_title(f'Top {top_n} Planning Areas: School Premium Evolution ({property_type})',
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

        pre_covid = data[data['year'] < 2020]['school_premium_10pt'].mean()
        covid = data[data['year'].between(2020, 2022)]['school_premium_10pt'].mean()
        post_covid = data[data['year'] > 2022]['school_premium_10pt'].mean()

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

    logger.info("\nSchool Premium Summary ($/0.1 score increase):")
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
    logger.info("TEMPORAL SCHOOL PREMIUM EVOLUTION ANALYSIS (2017-2026)")
    logger.info("="*80)

    # Load data
    df = load_historical_data()

    if df is None:
        logger.error("Failed to load data. Exiting.")
        return

    # Select primary school feature
    primary_feature = 'school_accessibility_score'

    # Calculate yearly coefficients by property type
    logger.info("\n" + "="*80)
    logger.info(f"YEARLY SCHOOL COEFFICIENTS BY PROPERTY TYPE - {primary_feature}")
    logger.info("="*80)

    yearly_results = []
    for prop_type in ['HDB', 'Condominium', 'EC']:
        result = calculate_yearly_school_coefficients(df, prop_type, primary_feature)
        if result is not None and not result.empty:
            yearly_results.append(result)

            # Save individual results
            csv_path = OUTPUT_DIR / f"yearly_coefficients_{prop_type.lower()}_{primary_feature}.csv"
            result.to_csv(csv_path, index=False)
            logger.info(f"\nSaved: {csv_path}")

    if not yearly_results:
        logger.error("No yearly results generated. Exiting.")
        return

    # Analyze by planning area
    logger.info("\n" + "="*80)
    logger.info("AREA-LEVEL TEMPORAL ANALYSIS")
    logger.info("="*80)

    area_results_hdb = analyze_by_planning_area(df, property_type='HDB', feature=primary_feature, min_transactions=200)
    if not area_results_hdb.empty:
        csv_path = OUTPUT_DIR / f"area_yearly_coefficients_hdb_{primary_feature}.csv"
        area_results_hdb.to_csv(csv_path, index=False)
        logger.info(f"\nSaved: {csv_path}")

    area_results_condo = analyze_by_planning_area(df, property_type='Condominium', feature=primary_feature, min_transactions=100)
    if not area_results_condo.empty:
        csv_path = OUTPUT_DIR / f"area_yearly_coefficients_condominium_{primary_feature}.csv"
        area_results_condo.to_csv(csv_path, index=False)
        logger.info(f"Saved: {csv_path}")

    # COVID impact assessment
    covid_results = identify_covid_impact(df, feature=primary_feature)

    # Generate visualizations
    plot_temporal_evolution(yearly_results)

    if not area_results_hdb.empty:
        plot_top_areas_evolution(area_results_hdb, property_type='HDB', top_n=15)

    if not area_results_condo.empty:
        plot_top_areas_evolution(area_results_condo, property_type='Condominium', top_n=10)

    # Generate summary statistics
    summary = generate_summary_statistics(yearly_results)

    # Final summary
    duration = (datetime.now() - start_time).total_seconds()

    logger.info("\n" + "="*80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*80)
    logger.info("\nKey Findings:")
    logger.info(f"  • Analyzed {len(df):,} transactions from 2017-2026")
    logger.info("  • Tracked school premium evolution for 3 property types")
    logger.info("  • Assessed COVID-19 impact (2020-2022)")
    logger.info("  • Generated area-level evolution plots")
    logger.info(f"\nOutputs saved to: {OUTPUT_DIR}")
    logger.info(f"\nDuration: {duration:.1f} seconds")
    logger.info("="*80)


if __name__ == "__main__":
    main()
