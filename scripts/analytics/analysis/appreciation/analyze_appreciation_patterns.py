#!/usr/bin/env python3
"""
Singapore Housing Appreciation Analysis

This script analyzes Year-over-Year (YoY) appreciation patterns to understand
what drives property value growth over time, focusing on:

1. Appreciation Rate Distribution & Clustering
   - Identify high-growth vs stagnant areas
   - Cluster planning areas by appreciation patterns
   - Detect appreciation "hotspots" and "coldspots"

2. Drivers of Appreciation (Regression Analysis)
   - Which features predict high appreciation?
   - MRT proximity impact on growth (not just price levels)
   - Amenity access effects on appreciation
   - Lease decay impact on growth rates

3. Temporal Dynamics
   - How appreciation rates evolve (2017-2026)
   - COVID impact on growth patterns
   - Lead-lag relationships between areas

4. Cross-Property Type Comparison
   - Do condos appreciate faster than HDB?
   - EC growth vs condo vs HDB
   - Risk-adjusted returns

Usage:
    uv run python scripts/analytics/analysis/appreciation/analyze_appreciation_patterns.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import xgboost as xgb
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

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
OUTPUT_DIR = Config.DATA_DIR / "analysis" / "appreciation_patterns"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_appreciation_data(min_year=2017):
    """Load L3 data with appreciation metrics."""
    logger.info("Loading L3 unified data with appreciation metrics...")

    path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
    df = pd.read_parquet(path)

    # Filter to recent years
    df = df[df['year'] >= min_year].copy()

    # Focus on properties with appreciation data
    df = df[df['yoy_change_pct'].notna()].copy()

    # Remove extreme outliers (beyond ±99th percentile)
    lower = df['yoy_change_pct'].quantile(0.01)
    upper = df['yoy_change_pct'].quantile(0.99)
    df = df[(df['yoy_change_pct'] >= lower) & (df['yoy_change_pct'] <= upper)].copy()

    logger.info(f"Loaded {len(df):,} transactions with appreciation data")
    logger.info(f"  Date range: {df['year'].min()} - {df['year'].max()}")
    logger.info(f"  YoY range: {df['yoy_change_pct'].min():.1f}% to {df['yoy_change_pct'].max():.1f}%")
    logger.info(f"  Mean YoY: {df['yoy_change_pct'].mean():.2f}%")

    return df


def analyze_appreciation_distribution(df):
    """Analyze distribution of appreciation rates by property type and area."""
    logger.info("\n" + "="*80)
    logger.info("APPRECIATION DISTRIBUTION ANALYSIS")
    logger.info("="*80)

    # By property type
    logger.info("\nBy Property Type:")
    prop_stats = []
    for prop_type in ['HDB', 'Condominium', 'EC']:
        data = df[df['property_type'] == prop_type]['yoy_change_pct']
        if len(data) > 0:
            stats_dict = {
                'property_type': prop_type,
                'count': len(data),
                'mean': data.mean(),
                'median': data.median(),
                'std': data.std(),
                'min': data.min(),
                'max': data.max(),
                'q25': data.quantile(0.25),
                'q75': data.quantile(0.75)
            }
            prop_stats.append(stats_dict)

            logger.info(f"\n{prop_type}:")
            logger.info(f"  Mean YoY: {stats_dict['mean']:.2f}%")
            logger.info(f"  Median YoY: {stats_dict['median']:.2f}%")
            logger.info(f"  Std Dev: {stats_dict['std']:.2f}%")
            logger.info(f"  Range: {stats_dict['min']:.1f}% to {stats_dict['max']:.1f}%")

    prop_stats_df = pd.DataFrame(prop_stats)
    csv_path = OUTPUT_DIR / "appreciation_by_property_type.csv"
    prop_stats_df.to_csv(csv_path, index=False)
    logger.info(f"\nSaved: {csv_path}")

    # Top and bottom planning areas
    logger.info("\nTop 10 Planning Areas by Mean Appreciation:")
    area_stats = df.groupby('planning_area')['yoy_change_pct'].agg(['mean', 'median', 'count'])
    area_stats = area_stats[area_stats['count'] >= 100].sort_values('mean', ascending=False)
    logger.info(f"\n{area_stats.head(10).to_string()}")

    logger.info("\nBottom 10 Planning Areas by Mean Appreciation:")
    logger.info(f"\n{area_stats.tail(10).to_string()}")

    return prop_stats_df, area_stats


def cluster_appreciation_patterns(df, n_clusters=6):
    """Cluster planning areas by appreciation patterns."""
    logger.info("\n" + "="*80)
    logger.info("APPRECIATION PATTERN CLUSTERING")
    logger.info("="*80)

    # Aggregate by planning area
    area_features = df.groupby('planning_area').agg({
        'yoy_change_pct': ['mean', 'median', 'std', 'count'],
        'price_psf': 'median',
        'dist_to_nearest_mrt': 'mean',
        'floor_area_sqm': 'mean'
    }).round(2)

    # Flatten column names
    area_features.columns = ['_'.join(col).strip() for col in area_features.columns.values]
    area_features = area_features[area_features['yoy_change_pct_count'] >= 100].reset_index()

    logger.info(f"Clustering {len(area_features)} planning areas...")

    # Prepare features for clustering
    feature_cols = [
        'yoy_change_pct_mean',
        'yoy_change_pct_median',
        'yoy_change_pct_std',
        'price_psf_median',
        'dist_to_nearest_mrt_mean'
    ]

    X = area_features[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # K-Means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=50)
    clusters = kmeans.fit_predict(X_scaled)

    area_features['cluster'] = clusters

    # Name clusters based on characteristics
    cluster_names = []
    for i in range(n_clusters):
        cluster_data = area_features[area_features['cluster'] == i]
        mean_growth = cluster_data['yoy_change_pct_mean'].mean()
        vol = cluster_data['yoy_change_pct_std'].mean()

        if mean_growth > 15:
            name = f"High Growth Cluster {i+1}"
        elif mean_growth > 5:
            name = f"Moderate Growth Cluster {i+1}"
        elif mean_growth > 0:
            name = f"Low Growth Cluster {i+1}"
        elif mean_growth > -5:
            name = f"Stable/Declining {i+1}"
        else:
            name = f"High Decline Cluster {i+1}"

        cluster_names.append(name)

    area_features['cluster_name'] = area_features['cluster'].map(lambda x: cluster_names[x])

    # Cluster summary
    logger.info("\nCluster Summary:")
    cluster_summary = area_features.groupby('cluster').agg({
        'yoy_change_pct_mean': 'mean',
        'yoy_change_pct_median': 'mean',
        'price_psf_median': 'mean',
        'planning_area': 'count'
    }).round(2)

    cluster_summary.columns = ['Mean YoY %', 'Median YoY %', 'Mean Price PSF', 'Count']
    logger.info(f"\n{cluster_summary.to_string()}")

    # Save
    csv_path = OUTPUT_DIR / "appreciation_clusters.csv"
    area_features[['planning_area', 'cluster', 'cluster_name', 'yoy_change_pct_mean',
                    'yoy_change_pct_std', 'price_psf_median']].to_csv(csv_path, index=False)
    logger.info(f"\nSaved: {csv_path}")

    return area_features, cluster_summary


def run_appreciation_regression(df):
    """Run regression models to predict YoY appreciation."""
    logger.info("\n" + "="*80)
    logger.info("APPRECIATION REGRESSION ANALYSIS")
    logger.info("="*80)

    # Prepare features
    feature_cols = [
        'price_psf',
        'floor_area_sqm',
        'remaining_lease_months',
        'dist_to_nearest_mrt',
        'dist_to_nearest_hawker',
        'dist_to_nearest_supermarket',
        'dist_to_nearest_park',
        'dist_to_nearest_preschool',
        'mrt_within_500m',
        'mrt_within_1km',
        'hawker_within_500m',
        'supermarket_within_500m',
        'park_within_500m'
    ]

    # Filter to recent data (2021+)
    df_recent = df[df['year'] >= 2021].copy()
    df_clean = df_recent[feature_cols + ['yoy_change_pct']].dropna()

    X = df_clean[feature_cols].values
    y = df_clean['yoy_change_pct'].values

    logger.info("\nDataset for regression:")
    logger.info(f"  Samples: {len(X):,}")
    logger.info(f"  Features: {len(feature_cols)}")
    logger.info("  Target: YoY appreciation %")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    results = []

    # 1. Linear Regression (Baseline)
    logger.info("\n1. Linear Regression (Baseline)...")
    ols = LinearRegression()
    ols.fit(X_train, y_train)
    y_pred_ols = ols.predict(X_test)
    r2_ols = r2_score(y_test, y_pred_ols)

    logger.info(f"  R²: {r2_ols:.4f}")
    logger.info(f"  MAE: {mean_absolute_error(y_test, y_pred_ols):.2f}%")
    logger.info(f"  RMSE: {np.sqrt(mean_squared_error(y_test, y_pred_ols)):.2f}%")

    results.append({
        'model': 'OLS',
        'r2': r2_ols,
        'mae': mean_absolute_error(y_test, y_pred_ols),
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred_ols))
    })

    # 2. Ridge Regression
    logger.info("\n2. Ridge Regression...")
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train, y_train)
    y_pred_ridge = ridge.predict(X_test)
    r2_ridge = r2_score(y_test, y_pred_ridge)

    logger.info(f"  R²: {r2_ridge:.4f}")

    results.append({
        'model': 'Ridge',
        'r2': r2_ridge,
        'mae': mean_absolute_error(y_test, y_pred_ridge),
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred_ridge))
    })

    # 3. Random Forest
    logger.info("\n3. Random Forest...")
    rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    r2_rf = r2_score(y_test, y_pred_rf)

    logger.info(f"  R²: {r2_rf:.4f}")

    # Feature importance
    importance_df = pd.DataFrame({
        'feature': feature_cols,
        'importance': rf.feature_importances_
    }).sort_values('importance', ascending=False)

    logger.info("\n  Top 10 Features:")
    for _, row in importance_df.head(10).iterrows():
        logger.info(f"    {row['feature']}: {row['importance']:.4f}")

    results.append({
        'model': 'Random Forest',
        'r2': r2_rf,
        'mae': mean_absolute_error(y_test, y_pred_rf),
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred_rf))
    })

    # 4. XGBoost
    logger.info("\n4. XGBoost...")
    xgb_model = xgb.XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
    xgb_model.fit(X_train, y_train)
    y_pred_xgb = xgb_model.predict(X_test)
    r2_xgb = r2_score(y_test, y_pred_xgb)

    logger.info(f"  R²: {r2_xgb:.4f}")

    results.append({
        'model': 'XGBoost',
        'r2': r2_xgb,
        'mae': mean_absolute_error(y_test, y_pred_xgb),
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred_xgb))
    })

    # Model comparison
    results_df = pd.DataFrame(results)
    logger.info("\nModel Comparison:")
    logger.info(f"\n{results_df.to_string()}")

    # Save
    csv_path = OUTPUT_DIR / "regression_model_comparison.csv"
    results_df.to_csv(csv_path, index=False)
    logger.info(f"\nSaved: {csv_path}")

    importance_path = OUTPUT_DIR / "feature_importance_rf.csv"
    importance_df.to_csv(importance_path, index=False)
    logger.info(f"Saved: {importance_path}")

    return results_df, importance_df, rf, xgb_model


def analyze_mrt_impact_on_appreciation(df):
    """Analyze how MRT proximity affects appreciation rates (not just prices)."""
    logger.info("\n" + "="*80)
    logger.info("MRT PROXIMITY IMPACT ON APPRECIATION RATES")
    logger.info("="*80)

    # Bin by MRT distance
    df_clean = df[df['dist_to_nearest_mrt'].notna()].copy()

    # Create MRT distance bins
    df_clean['mrt_distance_bin'] = pd.cut(
        df_clean['dist_to_nearest_mrt'],
        bins=[0, 500, 1000, 1500, 2000, 10000],
        labels=['0-500m', '500-1000m', '1-1.5km', '1.5-2km', '>2km']
    )

    # Calculate mean appreciation by bin
    mrt_impact = df_clean.groupby('mrt_distance_bin', observed=True).agg({
        'yoy_change_pct': ['mean', 'median', 'count'],
        'price_psf': 'median'
    }).round(2)

    logger.info("\nAppreciation by MRT Distance:")
    logger.info(f"\n{mrt_impact.to_string()}")

    # Regression: appreciation ~ MRT distance + controls
    logger.info("\nRegression Analysis:")

    feature_cols = [
        'dist_to_nearest_mrt',
        'floor_area_sqm',
        'remaining_lease_months',
        'price_psf'
    ]

    df_reg = df_clean[feature_cols + ['yoy_change_pct']].dropna()

    X = df_reg[feature_cols].values
    y = df_reg['yoy_change_pct'].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)

    logger.info(f"\n  R²: {r2:.4f}")
    logger.info(f"  MRT Coefficient: {model.coef_[0]:.6f}")
    logger.info(f"  Interpretation: Every 100m closer to MRT = {model.coef_[0]*100:.2f}% change in YoY appreciation")

    # By property type
    logger.info("\nBy Property Type:")
    for prop_type in ['HDB', 'Condominium', 'EC']:
        df_type = df_clean[df_clean['property_type'] == prop_type].copy()

        if len(df_type) < 100:
            continue

        mrt_type = df_type.groupby('mrt_distance_bin', observed=True).agg({
            'yoy_change_pct': ['mean', 'count']
        }).round(2)

        logger.info(f"\n{prop_type}:")
        logger.info(f"\n{mrt_type.to_string()}")

    # Save
    csv_path = OUTPUT_DIR / "mrt_impact_on_appreciation.csv"
    mrt_impact.reset_index().to_csv(csv_path)
    logger.info(f"\nSaved: {csv_path}")

    return mrt_impact


def analyze_temporal_appreciation_dynamics(df):
    """Analyze how appreciation patterns evolve over time."""
    logger.info("\n" + "="*80)
    logger.info("TEMPORAL APPRECIATION DYNAMICS (2017-2026)")
    logger.info("="*80)

    # Calculate yearly mean appreciation by property type
    yearly_stats = df.groupby(['year', 'property_type'])['yoy_change_pct'].agg([
        'mean', 'median', 'std', 'count'
    ]).reset_index()

    yearly_stats.columns = ['year', 'property_type', 'mean', 'median', 'std', 'count']

    logger.info("\nYearly Appreciation by Property Type:")
    pivot = yearly_stats.pivot(index='year', columns='property_type', values='mean')
    logger.info(f"\n{pivot.to_string()}")

    # COVID impact
    pre_covid = yearly_stats[yearly_stats['year'] < 2020].groupby('property_type')['mean'].mean()
    covid = yearly_stats[yearly_stats['year'].between(2020, 2022)].groupby('property_type')['mean'].mean()
    post_covid = yearly_stats[yearly_stats['year'] > 2022].groupby('property_type')['mean'].mean()

    logger.info("\nCOVID Impact on Appreciation:")
    logger.info(f"\nPre-COVID:\n{pre_covid.to_string()}")
    logger.info(f"\nCOVID (2020-22):\n{covid.to_string()}")
    logger.info(f"\nPost-COVID:\n{post_covid.to_string()}")

    # Volatility analysis
    logger.info("\nVolatility (Std Dev of YoY):")
    volatility = yearly_stats.groupby('property_type')['std'].mean()
    logger.info(f"\n{volatility.to_string()}")

    # Save
    csv_path = OUTPUT_DIR / "yearly_appreciation_by_type.csv"
    yearly_stats.to_csv(csv_path, index=False)
    logger.info(f"\nSaved: {csv_path}")

    return yearly_stats


def identify_appreciation_hotspots(df, percentile_threshold=75):
    """Identify areas with consistently high appreciation."""
    logger.info("\n" + "="*80)
    logger.info("APPRECIATION HOTSPOT ANALYSIS")
    logger.info("="*80)

    # Calculate appreciation by area and year
    area_year = df.groupby(['planning_area', 'year'])['yoy_change_pct'].mean().reset_index()

    # Calculate consistency (how often above threshold)
    threshold = df['yoy_change_pct'].quantile(percentile_threshold / 100)

    hotspot_stats = []
    for area in area_year['planning_area'].unique():
        area_data = area_year[area_year['planning_area'] == area]

        above_threshold = (area_data['yoy_change_pct'] > threshold).sum()
        total_years = len(area_data)
        consistency = above_threshold / total_years if total_years > 0 else 0

        hotspot_stats.append({
            'planning_area': area,
            'mean_yoy': area_data['yoy_change_pct'].mean(),
            'median_yoy': area_data['yoy_change_pct'].median(),
            'std_yoy': area_data['yoy_change_pct'].std(),
            'years': total_years,
            'above_threshold_years': above_threshold,
            'consistency': consistency
        })

    hotspot_df = pd.DataFrame(hotspot_stats)
    hotspot_df = hotspot_df.sort_values('consistency', ascending=False)

    logger.info(f"\nTop 15 Most Consistently High-Appreciation Areas (top {percentile_threshold}%):")
    logger.info(f"\n{hotspot_df.head(15).to_string()}")

    # Classify hotspots
    hotspot_df['category'] = pd.cut(
        hotspot_df['consistency'],
        bins=[0, 0.3, 0.5, 0.7, 1.0],
        labels=['Occasional Growth', 'Moderate Consistency', 'High Consistency', 'Elite Hotspot']
    )

    # Save
    csv_path = OUTPUT_DIR / "appreciation_hotspots.csv"
    hotspot_df.to_csv(csv_path, index=False)
    logger.info(f"\nSaved: {csv_path}")

    return hotspot_df


def create_appreciation_visualizations(df, prop_stats, area_stats, cluster_summary,
                                        results_df, importance_df, yearly_stats, hotspot_df):
    """Create comprehensive visualizations."""
    logger.info("\nCreating appreciation visualizations...")

    # Figure 1: Distribution of appreciation by property type
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    ax = axes[0, 0]
    for prop_type in ['HDB', 'Condominium', 'EC']:
        data = df[df['property_type'] == prop_type]['yoy_change_pct']
        ax.hist(data, bins=50, alpha=0.5, label=prop_type, density=True)
    ax.axvline(x=0, color='black', linestyle='--', linewidth=2, label='No Change')
    ax.set_xlabel('YoY Appreciation %', fontsize=12, fontweight='bold')
    ax.set_ylabel('Density', fontsize=12, fontweight='bold')
    ax.set_title('Distribution of Appreciation Rates by Property Type', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # Figure 2: Yearly appreciation trends
    ax = axes[0, 1]
    for prop_type in ['HDB', 'Condominium', 'EC']:
        data = yearly_stats[yearly_stats['property_type'] == prop_type]
        ax.plot(data['year'], data['mean'], marker='o', label=prop_type, linewidth=2)
    ax.axvspan(2020, 2022, alpha=0.2, color='red', label='COVID Period')
    ax.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Mean YoY Appreciation %', fontsize=12, fontweight='bold')
    ax.set_title('Yearly Appreciation Trends (2017-2026)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Figure 3: Feature importance from Random Forest
    ax = axes[1, 0]
    top_features = importance_df.head(10)
    ax.barh(range(len(top_features)), top_features['importance'].values)
    ax.set_yticks(range(len(top_features)))
    ax.set_yticklabels([f.replace('_', ' ').title() for f in top_features['feature']])
    ax.set_xlabel('Feature Importance', fontsize=12, fontweight='bold')
    ax.set_title('Top 10 Features Predicting Appreciation', fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3, axis='x')

    # Figure 4: Model comparison
    ax = axes[1, 1]
    models = results_df['model'].values
    r2_scores = results_df['r2'].values
    colors = ['steelblue', 'coral', 'seagreen', 'purple']
    ax.bar(models, r2_scores, color=colors, alpha=0.7)
    ax.set_ylabel('R² Score', fontsize=12, fontweight='bold')
    ax.set_title('Model Performance Comparison', fontsize=14, fontweight='bold')
    ax.set_ylim(0, max(r2_scores) * 1.2)
    for i, v in enumerate(r2_scores):
        ax.text(i, v + 0.01, f'{v:.3f}', ha='center', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    plt.suptitle('Singapore Housing Appreciation Analysis', fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()

    fig_path = OUTPUT_DIR / "appreciation_analysis_overview.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved: {fig_path}")
    plt.close()


def generate_investment_insights(df, cluster_summary, hotspot_df, importance_df):
    """Generate actionable investment insights."""
    logger.info("\n" + "="*80)
    logger.info("INVESTMENT INSIGHTS & RECOMMENDATIONS")
    logger.info("="*80)

    insights = []

    # 1. Property type appreciation
    logger.info("\n1. Property Type Appreciation:")
    prop_mean = df.groupby('property_type')['yoy_change_pct'].mean().sort_values(ascending=False)
    logger.info(f"\n{prop_mean.to_string()}")

    if prop_mean.idxmax() == 'Condominium':
        insights.append("✓ Condos show highest appreciation - suitable for growth-focused investors")
    elif prop_mean.idxmax() == 'HDB':
        insights.append("✓ HDB shows highest appreciation - surprising resilience")

    # 2. Hotspot areas
    logger.info("\n2. Elite Appreciation Hotspots:")
    elite = hotspot_df[hotspot_df['category'] == 'Elite Hotspot'].head(10)
    logger.info(f"\n{elite[['planning_area', 'mean_yoy', 'consistency']].to_string()}")

    insights.append(f"✓ {len(elite)} elite hotspot areas identified with consistently high appreciation")

    # 3. Key drivers
    logger.info("\n3. Key Appreciation Drivers:")
    top_drivers = importance_df.head(5)
    for _, row in top_drivers.iterrows():
        feature = row['feature'].replace('_', ' ').title()
        insights.append(f"✓ {feature}: importance {row['importance']:.4f}")

    # 4. Risk assessment
    logger.info("\n4. Risk Assessment (by volatility):")
    prop_std = df.groupby('property_type')['yoy_change_pct'].std()
    logger.info(f"\n{prop_std.to_string()}")

    if prop_std.idxmin() == 'HDB':
        insights.append("✓ HDB shows lowest volatility - safer investment")

    # Save insights
    insights_path = OUTPUT_DIR / "investment_insights.txt"
    with open(insights_path, 'w') as f:
        f.write("INVESTMENT INSIGHTS & RECOMMENDATIONS\n")
        f.write("="*60 + "\n\n")
        for insight in insights:
            f.write(f"{insight}\n")

    logger.info(f"\nSaved: {insights_path}")

    return insights


def main():
    """Main execution."""
    start_time = datetime.now()

    logger.info("="*80)
    logger.info("SINGAPORE HOUSING APPRECIATION ANALYSIS")
    logger.info("Focusing on YoY Growth Patterns Rather Than Static Prices")
    logger.info("="*80)

    # Load data
    df = load_appreciation_data(min_year=2017)

    # Run analyses
    prop_stats, area_stats = analyze_appreciation_distribution(df)
    area_features, cluster_summary = cluster_appreciation_patterns(df, n_clusters=6)
    results_df, importance_df, rf_model, xgb_model = run_appreciation_regression(df)
    mrt_impact = analyze_mrt_impact_on_appreciation(df)
    yearly_stats = analyze_temporal_appreciation_dynamics(df)
    hotspot_df = identify_appreciation_hotspots(df, percentile_threshold=75)

    # Create visualizations
    create_appreciation_visualizations(df, prop_stats, area_stats, cluster_summary,
                                       results_df, importance_df, yearly_stats, hotspot_df)

    # Generate insights
    insights = generate_investment_insights(df, cluster_summary, hotspot_df, importance_df)

    # Final summary
    duration = (datetime.now() - start_time).total_seconds()

    logger.info("\n" + "="*80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*80)

    logger.info("\nKey Findings:")
    logger.info(f"  • Analyzed {len(df):,} transactions with YoY data")
    logger.info(f"  • Identified {len(area_features)} planning area clusters")
    logger.info(f"  • Best model R²: {results_df['r2'].max():.4f} ({results_df.loc[results_df['r2'].idxmax(), 'model']})")
    logger.info(f"  • Top appreciation driver: {importance_df.iloc[0]['feature']}")

    logger.info("\nInvestment Insights:")
    for insight in insights[:5]:
        logger.info(f"  {insight}")

    logger.info(f"\nAll outputs saved to: {OUTPUT_DIR}")
    logger.info(f"\nDuration: {duration:.1f} seconds")
    logger.info("="*80)


if __name__ == "__main__":
    main()
