#!/usr/bin/env python3
"""
Spatial Interaction Analysis: GWR and Spatial Lag Models

This script implements advanced spatial econometric methods to understand
how MRT proximity effects vary across space:

1. Geographically Weighted Regression (GWR)
   - Local regression where coefficients vary by location
   - Captures spatial heterogeneity in MRT effects

2. Spatial Lag Model
   - Accounts for spatial dependence in errors
   - Measures spillover effects

3. Comparison with Global Models
   - OLS (one-size-fits-all)
   - GWR (location-specific)
   - XGBoost (non-linear)

Usage:
    uv run python scripts/analytics/analysis/spatial/analyze_spatial_interaction.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
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
OUTPUT_DIR = Config.DATA_DIR / "analysis" / "spatial_interaction"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Check for spatial packages
try:
    import libpysal
    from esda.moran import Moran
    from libpysal.weights import KNN
    SPATIAL_AVAILABLE = True
except ImportError:
    SPATIAL_AVAILABLE = False
    logger.warning("libpysal/esda not available - spatial lag models disabled")

try:
    from mgwr.gwr import GWR
    from mgwr.sel_bw import Sel_BW
    GWR_AVAILABLE = True
except ImportError:
    GWR_AVAILABLE = False
    logger.warning("mgwr not available - GWR models disabled (install with: uv add mgwr)")


def load_recent_data(min_year=2021, property_type='HDB'):
    """Load recent transaction data for spatial analysis."""
    logger.info(f"Loading {property_type} data from {min_year}+...")

    path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
    df = pd.read_parquet(path)

    # Filter by property type and year
    df = df[df['property_type'] == property_type].copy()
    df = df[df['year'] >= min_year].copy()

    # Select features
    feature_cols = [
        'price_psf', 'dist_to_nearest_mrt', 'floor_area_sqm',
        'remaining_lease_months', 'lat', 'lon', 'planning_area'
    ]

    df = df[feature_cols].dropna()

    logger.info(f"Loaded {len(df):,} transactions")
    logger.info(f"  Date range: {df['year'].min() if 'year' in df.columns else 'N/A'}")
    logger.info(f"  Planning areas: {df['planning_area'].nunique()}")

    return df


def run_global_ols(df):
    """Run global OLS model (baseline)."""
    logger.info("\nRunning Global OLS Model...")

    X = df[['dist_to_nearest_mrt', 'floor_area_sqm', 'remaining_lease_months']].values
    y = df['price_psf'].values

    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)
    r2 = r2_score(y, y_pred)

    logger.info(f"  R²: {r2:.4f}")
    logger.info(f"  MRT Coefficient: {model.coef_[0]:.4f} ($/meter)")
    logger.info(f"  MRT Premium: ${model.coef_[0] * 100:.2f}/100m")

    results = {
        'model': 'OLS',
        'r2': r2,
        'mrt_coef': model.coef_[0],
        'mrt_premium_100m': model.coef_[0] * 100,
        'predictions': y_pred
    }

    return results, X, y


def run_gwr_model(df, bw=None, fixed=False, kernel='gaussian'):
    """Run Geographically Weighted Regression.

    Args:
        df: DataFrame with coordinates and features
        bw: Bandwidth (None for adaptive selection)
        fixed: True for fixed bandwidth, False for adaptive
        kernel: 'gaussian', 'bisquare', or 'exponential'

    Returns:
        GWR results with local coefficients
    """
    if not GWR_AVAILABLE:
        logger.warning("GWR not available - skipping")
        return None

    logger.info("\nRunning GWR Model...")

    # Prepare data
    coords = list(zip(df['lat'], df['lon']))
    X = df[['dist_to_nearest_mrt', 'floor_area_sqm', 'remaining_lease_months']].values
    y = df['price_psf'].values

    # Standardize features for GWR
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Select bandwidth if not provided
    if bw is None:
        logger.info("  Selecting optimal bandwidth (this may take a while)...")
        try:
            bw_selector = Sel_BW(coords, X_scaled, y, kernel=kernel, fixed=fixed)
            bw = bw_selector.search()
            logger.info(f"  Optimal bandwidth: {bw:.2f}")
        except Exception as e:
            logger.warning(f"  Bandwidth selection failed: {e}")
            logger.info("  Using default bandwidth: 50")
            bw = 50

    # Fit GWR model
    logger.info(f"  Fitting GWR model (bw={bw:.2f}, fixed={fixed})...")
    try:
        gwr_model = GWR(coords, X_scaled, y, bw, kernel=kernel, fixed=fixed)
        gwr_results = gwr_model.fit()

        # Extract results
        r2 = gwr_results.R2
        aic = gwr_results.aic
        local_r2 = gwr_results.localR2

        # Get local MRT coefficients (first column)
        local_mrt_coefs = gwr_results.params[:, 1]  # Column 1 = MRT coefficient

        logger.info(f"  R²: {r2:.4f}")
        logger.info(f"  AIC: {aic:.2f}")
        logger.info(f"  Local R² range: {local_r2.min():.4f} - {local_r2.max():.4f}")
        logger.info(f"  Local MRT coefficient range: ${local_mrt_coefs.min():.2f} to ${local_mrt_coefs.max():.2f} per meter")
        logger.info(f"  Local MRT premium range: ${local_mrt_coefs.min()*100:.2f} to ${local_mrt_coefs.max()*100:.2f} per 100m")

        results = {
            'model': 'GWR',
            'r2': r2,
            'aic': aic,
            'bw': bw,
            'local_r2': local_r2,
            'local_mrt_coefs': local_mrt_coefs,
            'local_mrt_premiums': local_mrt_coefs * 100,
            'predictions': gwr_results.predy,
            'coords': coords
        }

        return results

    except Exception as e:
        logger.error(f"GWR fitting failed: {e}")
        return None


def run_spatial_lag_model(df):
    """Run Spatial Lag Model (if available)."""
    if not SPATIAL_AVAILABLE:
        logger.warning("Spatial lag model not available - skipping")
        return None

    logger.info("\nRunning Spatial Lag Model...")

    try:
        import spreg

        # Prepare data
        X = df[['dist_to_nearest_mrt', 'floor_area_sqm', 'remaining_lease_months']].values
        y = df['price_psf'].values.reshape(-1, 1)
        coords = list(zip(df['lat'], df['lon']))

        # Create spatial weights (KNN)
        logger.info("  Creating spatial weights (K=8)...")
        w = KNN(coords, k=8)
        w.transform = 'r'

        # Run spatial lag model
        logger.info("  Fitting spatial lag model...")
        model = spreg.GM_Lag(y, X, w=w, name_y='price', name_x=['MRT', 'Area', 'Lease'])

        logger.info(f"  R²: {model.pr2:.4f}")
        logger.info(f"  Spatial lag coefficient (rho): {model.betas[0][0]:.4f}")

        results = {
            'model': 'Spatial Lag',
            'r2': model.pr2,
            'rho': model.betas[0][0],
            'mrt_coef': model.betas[1][0],
            'predictions': model.predy
        }

        return results

    except Exception as e:
        logger.error(f"Spatial lag model failed: {e}")
        return None


def create_gwr_coefficient_map(df, gwr_results):
    """Create map of local MRT coefficients from GWR."""
    if gwr_results is None:
        return

    logger.info("\nCreating GWR coefficient map...")

    import geopandas as gpd
    from shapely.geometry import Point

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(
        {
            'local_mrt_premium': gwr_results['local_mrt_premiums'],
            'local_r2': gwr_results['local_r2']
        },
        geometry=[Point(lon, lat) for lat, lon in gwr_results['coords']]
    )

    # Create plot
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))

    # Plot 1: Local MRT Premium
    ax = axes[0]
    gdf.plot(column='local_mrt_premium', cmap='RdBu_r', legend=True,
             markersize=10, alpha=0.6, ax=ax, vmin=-10, vmax=10)
    ax.set_title('GWR: Local MRT Premium ($/100m)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')

    # Plot 2: Local R²
    ax = axes[1]
    gdf.plot(column='local_r2', cmap='viridis', legend=True,
             markersize=10, alpha=0.6, ax=ax)
    ax.set_title('GWR: Local R² (Model Fit)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')

    plt.tight_layout()
    fig_path = OUTPUT_DIR / "gwr_coefficient_maps.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved: {fig_path}")
    plt.close()


def plot_spatial_heterogeneity(df, gwr_results):
    """Plot distribution of local coefficients."""
    if gwr_results is None:
        return

    logger.info("\nPlotting spatial heterogeneity...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # Plot 1: Distribution of local MRT premiums
    ax = axes[0, 0]
    ax.hist(gwr_results['local_mrt_premiums'], bins=50, edgecolor='black', alpha=0.7)
    ax.axvline(x=0, color='red', linestyle='--', linewidth=2, label='No effect')
    ax.set_xlabel('Local MRT Premium ($/100m)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Distribution of Local MRT Effects', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # Plot 2: Local R² distribution
    ax = axes[0, 1]
    ax.hist(gwr_results['local_r2'], bins=50, edgecolor='black', alpha=0.7, color='green')
    ax.set_xlabel('Local R²', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Distribution of Local Model Fit', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    # Plot 3: MRT Premium vs Local R²
    ax = axes[1, 0]
    ax.scatter(gwr_results['local_mrt_premiums'], gwr_results['local_r2'],
               alpha=0.3, s=10)
    ax.set_xlabel('Local MRT Premium ($/100m)', fontsize=12)
    ax.set_ylabel('Local R²', fontsize=12)
    ax.set_title('MRT Effect vs Model Fit', fontsize=14, fontweight='bold')
    ax.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
    ax.axvline(x=0, color='black', linestyle='--', linewidth=0.5)
    ax.grid(True, alpha=0.3)

    # Plot 4: MRT Premium by planning area
    ax = axes[1, 1]

    # Add planning area to results
    df_with_mrt = df.copy()
    df_with_mrt['local_mrt_premium'] = gwr_results['local_mrt_premiums']

    area_mrt = df_with_mrt.groupby('planning_area')['local_mrt_premium'].mean().sort_values(ascending=False)

    area_mrt.head(15).plot(kind='barh', ax=ax, color='steelblue')
    ax.set_xlabel('Mean Local MRT Premium ($/100m)', fontsize=12)
    ax.set_title('Top 15 Planning Areas by MRT Sensitivity', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    fig_path = OUTPUT_DIR / "spatial_heterogeneity_analysis.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved: {fig_path}")
    plt.close()


def compare_models(ols_results, gwr_results, spatial_lag_results):
    """Compare performance across different models."""
    logger.info("\n" + "="*80)
    logger.info("MODEL COMPARISON")
    logger.info("="*80)

    comparison = []

    # OLS
    comparison.append({
        'Model': 'OLS (Global)',
        'R²': ols_results['r2'],
        'MRT Premium ($/100m)': ols_results['mrt_premium_100m']
    })

    # GWR
    if gwr_results is not None:
        comparison.append({
            'Model': 'GWR (Local)',
            'R²': gwr_results['r2'],
            'MRT Premium ($/100m)': f"{gwr_results['local_mrt_premiums'].mean():.2f} (local)"
        })

    # Spatial Lag
    if spatial_lag_results is not None:
        comparison.append({
            'Model': 'Spatial Lag',
            'R²': spatial_lag_results['r2'],
            'MRT Premium ($/100m)': spatial_lag_results['mrt_coef'] * 100
        })

    comp_df = pd.DataFrame(comparison)
    logger.info(f"\n{comp_df.to_string()}")

    # Save
    csv_path = OUTPUT_DIR / "model_comparison.csv"
    comp_df.to_csv(csv_path, index=False)
    logger.info(f"\nSaved: {csv_path}")

    return comp_df


def main():
    """Main execution."""
    start_time = datetime.now()

    logger.info("="*80)
    logger.info("SPATIAL INTERACTION ANALYSIS")
    logger.info("="*80)

    # Load data
    df = load_recent_data(min_year=2021, property_type='HDB')

    if len(df) < 100:
        logger.error("Insufficient data for spatial analysis")
        return

    # Run models
    ols_results, X, y = run_global_ols(df)

    gwr_results = None
    if GWR_AVAILABLE:
        # Sample data for GWR (computationally expensive)
        if len(df) > 5000:
            logger.info(f"\nSampling {5000} records for GWR (computationally expensive)...")
            df_sample = df.sample(n=5000, random_state=42)
        else:
            df_sample = df

        gwr_results = run_gwr_model(df_sample)

    spatial_lag_results = run_spatial_lag_model(df)

    # Create visualizations
    if gwr_results is not None:
        create_gwr_coefficient_map(df_sample, gwr_results)
        plot_spatial_heterogeneity(df_sample, gwr_results)

    # Compare models
    comparison = compare_models(ols_results, gwr_results, spatial_lag_results)

    # Final summary
    duration = (datetime.now() - start_time).total_seconds()

    logger.info("\n" + "="*80)
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*80)
    logger.info("\nKey Findings:")
    logger.info(f"  • Analyzed {len(df):,} HDB transactions (2021+)")
    logger.info(f"  • Global OLS R²: {ols_results['r2']:.4f}")

    if gwr_results is not None:
        logger.info(f"  • GWR R²: {gwr_results['r2']:.4f} ({(gwr_results['r2'] - ols_results['r2'])*100:+.2f}% improvement)")
        logger.info(f"  • MRT premium varies spatially: ${gwr_results['local_mrt_premiums'].min():.2f} to ${gwr_results['local_mrt_premiums'].max():.2f}/100m")

    if spatial_lag_results is not None:
        logger.info(f"  • Spatial lag R²: {spatial_lag_results['r2']:.4f}")
        logger.info(f"  • Spatial dependence (rho): {spatial_lag_results['rho']:.4f}")

    logger.info(f"\nOutputs saved to: {OUTPUT_DIR}")
    logger.info(f"\nDuration: {duration:.1f} seconds")
    logger.info("="*80)


if __name__ == "__main__":
    main()
