#!/usr/bin/env python3
"""
CBD Accessibility vs MRT Proximity Decomposition

This script disentangles the effects of:
1. MRT proximity (transport access)
2. CBD proximity (city center access)

Key Questions:
- How much of the "MRT premium" is actually about CBD access?
- Are MRT and CBD distance measuring the same thing?
- Which factor matters more for property prices?
- How can we isolate the pure MRT effect?

Methods:
1. Correlation analysis (multicollinearity)
2. Variance Inflation Factor (VIF)
3. Principal Component Analysis (PCA)
4. Hierarchical regression
5. Residual analysis

Usage:
    uv run python scripts/analytics/analysis/spatial/analyze_cbd_mrt_decomposition.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
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
OUTPUT_DIR = Config.DATA_DIR / "analysis" / "cbd_mrt_decomposition"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# CBD coordinates (approximate center of Singapore's CBD)
CBD_LAT = 1.2839
CBD_LON = 103.8513


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance between two points in kilometers."""
    from math import asin, cos, radians, sin, sqrt

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Earth's radius in kilometers

    return c * r


def load_data(min_year=2021, property_type='HDB'):
    """Load transaction data and calculate CBD distance."""
    logger.info(f"Loading {property_type} data from {min_year}+...")

    path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
    df = pd.read_parquet(path)

    # Filter by property type and year
    df = df[df['property_type'] == property_type].copy()
    df = df[df['year'] >= min_year].copy()

    # Ensure lat/lon are numeric
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    df = df.dropna(subset=['lat', 'lon'])

    # Calculate CBD distance for each property
    logger.info("Calculating CBD distances...")
    df['dist_to_cbd_km'] = df.apply(
        lambda row: haversine_distance(float(row['lat']), float(row['lon']), CBD_LAT, CBD_LON),
        axis=1
    )
    df['dist_to_cbd_m'] = df['dist_to_cbd_km'] * 1000  # Convert to meters

    logger.info(f"Loaded {len(df):,} transactions")
    logger.info(f"  Mean MRT distance: {df['dist_to_nearest_mrt'].mean():.0f}m")
    logger.info(f"  Mean CBD distance: {df['dist_to_cbd_km'].mean():.2f}km")

    return df


def analyze_correlation(df):
    """Analyze correlation between MRT and CBD distances."""
    logger.info("\n" + "="*80)
    logger.info("CORRELATION & MULTICOLLINEARITY ANALYSIS")
    logger.info("="*80)

    # Overall correlation
    corr = df[['dist_to_nearest_mrt', 'dist_to_cbd_m', 'price_psf']].corr()

    logger.info("\nCorrelation Matrix:")
    logger.info(f"\n{corr.to_string()}")

    # Scatter plot
    fig, ax = plt.subplots(figsize=(10, 8))
    sample = df.sample(n=min(5000, len(df)), random_state=42)

    scatter = ax.scatter(
        sample['dist_to_nearest_mrt'],
        sample['dist_to_cbd_m'],
        c=sample['price_psf'],
        cmap='viridis',
        alpha=0.5,
        s=10
    )
    ax.set_xlabel('Distance to Nearest MRT (m)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Distance to CBD (m)', fontsize=12, fontweight='bold')
    ax.set_title('MRT vs CBD Distance (colored by Price PSF)', fontsize=14, fontweight='bold')
    plt.colorbar(scatter, ax=ax, label='Price PSF ($)')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = OUTPUT_DIR / "mrt_cbd_scatter.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    logger.info(f"\nSaved: {fig_path}")
    plt.close()

    return corr


def calculate_vif(df):
    """Calculate Variance Inflation Factor to assess multicollinearity."""
    logger.info("\n" + "="*80)
    logger.info("VARIANCE INFLATION FACTOR (VIF) ANALYSIS")
    logger.info("="*80)

    # Prepare features
    features = ['dist_to_nearest_mrt', 'dist_to_cbd_m', 'floor_area_sqm', 'remaining_lease_months']
    df_clean = df[features + ['price_psf']].dropna()

    X = df_clean[features].values
    y = df_clean['price_psf'].values

    # Calculate VIF for each feature
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    vif_data = []
    for i in range(X.shape[1]):
        vif = variance_inflation_factor(X, i)
        vif_data.append({
            'Feature': features[i],
            'VIF': vif,
            'Interpretation': 'Severe' if vif > 10 else 'Moderate' if vif > 5 else 'Low'
        })

    vif_df = pd.DataFrame(vif_data)

    logger.info("\nVIF Results:")
    logger.info(f"\n{vif_df.to_string()}")

    # Save
    csv_path = OUTPUT_DIR / "vif_analysis.csv"
    vif_df.to_csv(csv_path, index=False)
    logger.info(f"\nSaved: {csv_path}")

    return vif_df


def run_hierarchical_regression(df):
    """Run hierarchical regression to isolate effects."""
    logger.info("\n" + "="*80)
    logger.info("HIERARCHICAL REGRESSION ANALYSIS")
    logger.info("="*80)

    df_clean = df[['price_psf', 'dist_to_nearest_mrt', 'dist_to_cbd_m',
                    'floor_area_sqm', 'remaining_lease_months']].dropna()

    results = []

    # Model 1: CBD only
    X1 = df_clean[['dist_to_cbd_m']].values
    y = df_clean['price_psf'].values
    model1 = LinearRegression()
    model1.fit(X1, y)
    y_pred1 = model1.predict(X1)
    r2_1 = r2_score(y, y_pred1)

    results.append({
        'Model': 'Model 1: CBD only',
        'R²': r2_1,
        'CBD Coef': model1.coef_[0],
        'MRT Coef': None
    })

    logger.info("\nModel 1: CBD only")
    logger.info(f"  R²: {r2_1:.4f}")
    logger.info(f"  CBD Coefficient: {model1.coef_[0]:.6f}")

    # Model 2: CBD + MRT
    X2 = df_clean[['dist_to_cbd_m', 'dist_to_nearest_mrt']].values
    model2 = LinearRegression()
    model2.fit(X2, y)
    y_pred2 = model2.predict(X2)
    r2_2 = r2_score(y, y_pred2)

    delta_r2 = r2_2 - r2_1

    results.append({
        'Model': 'Model 2: CBD + MRT',
        'R²': r2_2,
        'CBD Coef': model2.coef_[0],
        'MRT Coef': model2.coef_[1],
        'ΔR²': delta_r2
    })

    logger.info("\nModel 2: CBD + MRT")
    logger.info(f"  R²: {r2_2:.4f} (ΔR²: {delta_r2:+.4f})")
    logger.info(f"  CBD Coefficient: {model2.coef_[0]:.6f}")
    logger.info(f"  MRT Coefficient: {model2.coef_[1]:.6f}")

    # Model 3: Full model
    X3 = df_clean[['dist_to_cbd_m', 'dist_to_nearest_mrt', 'floor_area_sqm', 'remaining_lease_months']].values
    model3 = LinearRegression()
    model3.fit(X3, y)
    y_pred3 = model3.predict(X3)
    r2_3 = r2_score(y, y_pred3)

    delta_r2_3 = r2_3 - r2_2

    results.append({
        'Model': 'Model 3: Full',
        'R²': r2_3,
        'CBD Coef': model3.coef_[0],
        'MRT Coef': model3.coef_[1],
        'ΔR²': delta_r2_3
    })

    logger.info("\nModel 3: Full (CBD + MRT + Area + Lease)")
    logger.info(f"  R²: {r2_3:.4f} (ΔR²: {delta_r2_3:+.4f})")
    logger.info(f"  CBD Coefficient: {model3.coef_[0]:.6f}")
    logger.info(f"  MRT Coefficient: {model3.coef_[1]:.6f}")

    results_df = pd.DataFrame(results)

    # Save
    csv_path = OUTPUT_DIR / "hierarchical_regression.csv"
    results_df.to_csv(csv_path, index=False)
    logger.info(f"\nSaved: {csv_path}")

    return results_df


def run_pca_analysis(df):
    """Run PCA to decompose location features into components."""
    logger.info("\n" + "="*80)
    logger.info("PRINCIPAL COMPONENT ANALYSIS (PCA)")
    logger.info("="*80)

    # Prepare features
    features = ['dist_to_nearest_mrt', 'dist_to_cbd_m']
    df_clean = df[features + ['price_psf']].dropna()

    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_clean[features])
    y = df_clean['price_psf'].values

    # Fit PCA
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)

    # Get loadings
    loadings = pca.components_.T * np.sqrt(pca.explained_variance_)

    logger.info("\nExplained Variance Ratio:")
    for i, var in enumerate(pca.explained_variance_ratio_):
        logger.info(f"  PC{i+1}: {var:.4f} ({var*100:.2f}%)")

    logger.info("\nComponent Loadings:")
    loadings_df = pd.DataFrame(
        loadings,
        columns=['PC1', 'PC2'],
        index=['MRT Distance', 'CBD Distance']
    )
    logger.info(f"\n{loadings_df.to_string()}")

    # Interpret components
    logger.info("\nInterpretation:")
    if abs(loadings[0, 0]) > abs(loadings[1, 0]):
        logger.info(f"  PC1: Primarily {'MRT Distance' if loadings[0, 0] > 0 else 'CBD Distance'}")
    else:
        logger.info("  PC1: Mixed MRT/CBD factor")

    if abs(loadings[0, 1]) > abs(loadings[1, 1]):
        logger.info(f"  PC2: Primarily {'MRT Distance' if loadings[0, 1] > 0 else 'CBD Distance'}")
    else:
        logger.info("  PC2: Mixed MRT/CBD factor")

    # Regress price on PCs
    model_pcs = LinearRegression()
    model_pcs.fit(X_pca, y)
    r2_pcs = r2_score(y, model_pcs.predict(X_pca))

    logger.info("\nRegression on PCs:")
    logger.info(f"  R²: {r2_pcs:.4f}")
    logger.info(f"  PC1 Coef: {model_pcs.coef_[0]:.4f}")
    logger.info(f"  PC2 Coef: {model_pcs.coef_[1]:.4f}")

    # Save loadings
    csv_path = OUTPUT_DIR / "pca_loadings.csv"
    loadings_df.to_csv(csv_path)
    logger.info(f"\nSaved: {csv_path}")

    return pca, loadings_df, model_pcs


def compare_regional_effects(df):
    """Compare MRT vs CBD effects by region (OCR, RCR, CCR)."""
    logger.info("\n" + "="*80)
    logger.info("REGIONAL ANALYSIS: MRT vs CBD Effects")
    logger.info("="*80)

    # Define regions by CBD distance
    df_clean = df[['price_psf', 'dist_to_nearest_mrt', 'dist_to_cbd_m',
                    'floor_area_sqm', 'remaining_lease_months']].copy()

    # Classify regions (convert meters to km first)
    df_clean['dist_to_cbd_km'] = df_clean['dist_to_cbd_m'] / 1000
    df_clean = df_clean.dropna()
    df_clean['region'] = pd.cut(
        df_clean['dist_to_cbd_km'],
        bins=[0, 5, 15, 100],
        labels=['CCR (Core Central)', 'RCR (Rest of Central)', 'OCR (Outside Central)']
    )

    results = []

    for region in ['CCR (Core Central)', 'RCR (Rest of Central)', 'OCR (Outside Central)']:
        df_region = df_clean[df_clean['region'] == region].copy()

        if len(df_region) < 100:
            continue

        X = df_region[['dist_to_nearest_mrt', 'dist_to_cbd_m', 'floor_area_sqm', 'remaining_lease_months']].values
        y = df_region['price_psf'].values

        model = LinearRegression()
        model.fit(X, y)
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)

        results.append({
            'Region': region,
            'n': len(df_region),
            'R²': r2,
            'MRT Coef': model.coef_[0],
            'MRT Premium $/100m': model.coef_[0] * 100,
            'CBD Coef': model.coef_[1],
            'CBD Premium $/km': model.coef_[1] * 1000,
            'Mean Price': y.mean()
        })

    results_df = pd.DataFrame(results)

    logger.info("\nResults by Region:")
    logger.info(f"\n{results_df.to_string()}")

    # Save
    csv_path = OUTPUT_DIR / "regional_effects.csv"
    results_df.to_csv(csv_path, index=False)
    logger.info(f"\nSaved: {csv_path}")

    return results_df


def create_regional_effects_comparison_chart(regional_df):
    """Create grouped bar chart comparing MRT and CBD effects by region."""
    logger.info("\nCreating regional effects comparison chart...")

    # Prepare data
    regions = regional_df['Region'].tolist()
    mrt_premiums = regional_df['MRT Premium $/100m'].tolist()
    cbd_premiums = regional_df['CBD Premium $/km'].tolist()

    x = np.arange(len(regions))
    width = 0.35

    # Create chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # MRT Premiums by Region
    colors_mrt = ['green' if x > 0 else 'red' for x in mrt_premiums]
    bars1 = ax1.bar(x - width/2, mrt_premiums, width, label='MRT Premium',
                    color=colors_mrt, alpha=0.8, edgecolor='black', linewidth=1)

    ax1.set_xlabel('Region', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Premium per 100m Closer to MRT ($ PSF)', fontsize=11, fontweight='bold')
    ax1.set_title('MRT Premium by Region', fontsize=13, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels([r.replace(' (', '\n(') for r in regions], fontsize=10)
    ax1.axhline(y=0, color='black', linestyle='--', linewidth=1)
    ax1.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar, val in zip(bars1, mrt_premiums):
        height = bar.get_height()
        ax1.annotate(f'${val:.1f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5 if val >= 0 else -5),
                    textcoords="offset points",
                    ha='center', va='bottom' if val >= 0 else 'top',
                    fontsize=10, fontweight='bold')

    # CBD Premiums by Region
    colors_cbd = ['green' if x > 0 else 'red' for x in cbd_premiums]
    bars2 = ax2.bar(x + width/2, cbd_premiums, width, label='CBD Premium',
                    color=colors_cbd, alpha=0.8, edgecolor='black', linewidth=1)

    ax2.set_xlabel('Region', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Premium per km Closer to CBD ($ PSF)', fontsize=11, fontweight='bold')
    ax2.set_title('CBD Premium by Region', fontsize=13, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels([r.replace(' (', '\n(') for r in regions], fontsize=10)
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=1)
    ax2.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar, val in zip(bars2, cbd_premiums):
        height = bar.get_height()
        ax2.annotate(f'${val:.1f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5 if val >= 0 else -5),
                    textcoords="offset points",
                    ha='center', va='bottom' if val >= 0 else 'top',
                    fontsize=10, fontweight='bold')

    # Add overall title
    fig.suptitle('Regional Effects Comparison: MRT vs CBD Accessibility',
                 fontsize=15, fontweight='bold', y=1.0)

    plt.tight_layout()
    fig_path = OUTPUT_DIR / "regional_effects_comparison.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    logger.info(f"  Saved: {fig_path}")
    plt.close()


def create_visualization_summary(df, corr, vif_df, hierarchical_df, pca, regional_df):
    """Create comprehensive visualization summary."""
    logger.info("\nCreating visualization summary...")

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # Plot 1: Correlation heatmap
    ax1 = fig.add_subplot(gs[0, 0])
    sns.heatmap(corr, annot=True, fmt='.3f', cmap='coolwarm', center=0,
                square=True, linewidths=1, cbar_kws={"shrink": 0.8}, ax=ax1)
    ax1.set_title('Correlation Matrix', fontweight='bold')

    # Plot 2: VIF scores
    ax2 = fig.add_subplot(gs[0, 1])
    colors = ['green' if v < 5 else 'orange' if v < 10 else 'red' for v in vif_df['VIF']]
    vif_df.plot(kind='barh', x='Feature', y='VIF', color=colors, ax=ax2, legend=False)
    ax2.axvline(x=5, color='orange', linestyle='--', linewidth=1, label='Moderate')
    ax2.axvline(x=10, color='red', linestyle='--', linewidth=1, label='Severe')
    ax2.set_xlabel('VIF Score', fontweight='bold')
    ax2.set_title('Multicollinearity Assessment (VIF)', fontweight='bold')
    ax2.legend()

    # Plot 3: Hierarchical R² progression
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(range(1, 4), hierarchical_df['R²'], marker='o', linewidth=2, markersize=8)
    ax3.set_xticks([1, 2, 3])
    ax3.set_xticklabels(['CBD Only', '+ MRT', '+ Controls'], rotation=15, ha='right')
    ax3.set_ylabel('R² Score', fontweight='bold')
    ax3.set_title('Hierarchical R² Progression', fontweight='bold')
    ax3.grid(True, alpha=0.3)

    # Plot 4: Regional MRT premiums
    ax4 = fig.add_subplot(gs[1, :2])
    regional_df.plot(kind='bar', x='Region', y='MRT Premium $/100m',
                     color=['steelblue', 'coral', 'seagreen'], ax=ax4, legend=False)
    ax4.set_ylabel('MRT Premium ($/100m)', fontweight='bold')
    ax4.set_title('MRT Premium by Region', fontweight='bold')
    ax4.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.tick_params(axis='x', rotation=0)

    # Plot 5: Regional CBD premiums
    ax5 = fig.add_subplot(gs[1, 2])
    regional_df.plot(kind='bar', x='Region', y='CBD Premium $/km',
                     color=['steelblue', 'coral', 'seagreen'], ax=ax5, legend=False)
    ax5.set_ylabel('CBD Premium ($/km)', fontweight='bold')
    ax5.set_title('CBD Premium by Region', fontweight='bold')
    ax5.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
    ax5.grid(True, alpha=0.3, axis='y')
    ax5.tick_params(axis='x', rotation=45)

    # Plot 6: MRT vs CBD distance scatter by region
    ax6 = fig.add_subplot(gs[2, :])
    sample = df.sample(n=min(3000, len(df)), random_state=42)

    for region, color in [('OCR (Outside Central)', 'blue'),
                            ('RCR (Rest of Central)', 'green'),
                            ('CCR (Core Central)', 'red')]:
        if 'dist_to_cbd_km' in sample.columns:
            # Classify sample
            sample_region = pd.cut(
                sample['dist_to_cbd_km'],
                bins=[0, 5, 15, 100],
                labels=['CCR (Core Central)', 'RCR (Rest of Central)', 'OCR (Outside Central)']
            )
            region_sample = sample[sample_region == region]
            if len(region_sample) > 0:
                ax6.scatter(region_sample['dist_to_nearest_mrt'],
                          region_sample['dist_to_cbd_m'],
                          c=color, label=region, alpha=0.3, s=10)

    ax6.set_xlabel('Distance to MRT (m)', fontweight='bold')
    ax6.set_ylabel('Distance to CBD (m)', fontweight='bold')
    ax6.set_title('MRT vs CBD Distance by Region', fontweight='bold')
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    plt.suptitle('CBD vs MRT Decomposition Analysis', fontsize=16, fontweight='bold', y=0.995)

    fig_path = OUTPUT_DIR / "cbd_mrt_decomposition_summary.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved: {fig_path}")
    plt.close()


def main():
    """Main execution."""
    start_time = datetime.now()

    logger.info("="*80)
    logger.info("CBD ACCESSIBILITY VS MRT PROXIMITY DECOMPOSITION")
    logger.info("="*80)

    # Load data
    df = load_data(min_year=2021, property_type='HDB')

    if len(df) < 100:
        logger.error("Insufficient data for analysis")
        return

    # Run analyses
    corr = analyze_correlation(df)
    vif_df = calculate_vif(df)
    hierarchical_df = run_hierarchical_regression(df)
    pca, loadings_df, model_pcs = run_pca_analysis(df)
    regional_df = compare_regional_effects(df)

    # Create visualizations
    create_visualization_summary(df, corr, vif_df, hierarchical_df, pca, regional_df)
    create_regional_effects_comparison_chart(regional_df)

    # Final summary
    duration = (datetime.now() - start_time).total_seconds()

    logger.info("\n" + "="*80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*80)

    logger.info("\nKey Findings:")
    logger.info(f"  • Analyzed {len(df):,} HDB transactions (2021+)")
    logger.info(f"  • MRT-CBD Correlation: {corr.loc['dist_to_nearest_mrt', 'dist_to_cbd_m']:.3f}")
    logger.info(f"  • VIF - MRT: {vif_df[vif_df['Feature'] == 'dist_to_nearest_mrt']['VIF'].values[0]:.2f}")
    logger.info(f"  • VIF - CBD: {vif_df[vif_df['Feature'] == 'dist_to_cbd_m']['VIF'].values[0]:.2f}")

    logger.info(f"\n  • Pure CBD Effect (Model 1): R² = {hierarchical_df.iloc[0]['R²']:.4f}")
    logger.info(f"  • Adding MRT (Model 2): ΔR² = {hierarchical_df.iloc[1]['ΔR²']:.4f}")
    logger.info(f"  • MRT Premium in OCR: ${regional_df[regional_df['Region'] == 'OCR (Outside Central)']['MRT Premium $/100m'].values[0]:.2f}/100m")

    logger.info("\nInterpretation:")
    if vif_df[vif_df['Feature'] == 'dist_to_nearest_mrt']['VIF'].values[0] > 5:
        logger.info("  ⚠️  Moderate-to-high multicollinearity detected")
        logger.info("  → MRT and CBD distance are measuring similar things")
        logger.info("  → 'MRT premium' partially captures CBD access")
    else:
        logger.info("  ✓ Low multicollinearity - MRT and CBD are distinct factors")

    logger.info(f"\nOutputs saved to: {OUTPUT_DIR}")
    logger.info(f"\nDuration: {duration:.1f} seconds")
    logger.info("="*80)


if __name__ == "__main__":
    main()
