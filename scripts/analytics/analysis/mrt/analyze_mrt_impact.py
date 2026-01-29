"""
MRT Impact Analysis on Singapore Housing Prices

Uses H3 hexagonal grid (H8, ~0.5km² cells) to analyze the impact of MRT proximity
on housing prices, rental yields, and appreciation rates.

Analysis timeframe: 2021+ (recent data only)

Targets:
- price_psf: Transaction price per square foot
- rental_yield_pct: Rental yield percentage
- yoy_change_pct: Year-over-year appreciation rate
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from scipy import stats

import xgboost as xgb
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("SHAP not available - install with: uv add shap")

import matplotlib.pyplot as plt
import seaborn as sns

# Try to import H3
try:
    import h3
    H3_AVAILABLE = True
except ImportError:
    H3_AVAILABLE = False
    print("H3 not available - install with: uv add h3")

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Paths
DATA_DIR = Path("data/pipeline/L3")
OUTPUT_DIR = Path("data/analysis/mrt_impact")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_and_prepare_data():
    """Load unified dataset and filter to 2021+."""
    print("="*80)
    print("MRT IMPACT ANALYSIS - SINGAPORE HOUSING MARKET (2021+)")
    print("="*80)

    print("\nLoading data...")
    df = pd.read_parquet(DATA_DIR / "housing_unified.parquet")
    print(f"  Full dataset: {len(df):,} records")

    # Filter to 2021+
    df = df[df['year'] >= 2021].copy()
    print(f"  Filtered to 2021+: {len(df):,} records")

    # Ensure lat/lon are numeric
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    df = df.dropna(subset=['lat', 'lon'])
    print(f"  After dropping invalid coordinates: {len(df):,} records")

    # Add H3 grid cells if available
    if H3_AVAILABLE:
        print("\nAdding H8 grid cells (~0.5km²)...")
        df['h8_cell'] = df.apply(
            lambda row: h3.latlng_to_cell(float(row['lat']), float(row['lon']), 8),
            axis=1
        )
        n_cells = df['h8_cell'].nunique()
        print(f"  Created {n_cells} unique H8 cells")
    else:
        print("\n  Skipping H3 grid (h3 not installed)")
        df['h8_cell'] = None

    return df


def exploratory_analysis(df):
    """Explore relationships between MRT distance and prices."""
    print("\n" + "="*80)
    print("EXPLORATORY ANALYSIS")
    print("="*80)

    # Create distance bands for visualization
    df['dist_band'] = pd.cut(
        df['dist_to_nearest_mrt'],
        bins=[0, 200, 500, 1000, 2000, 10000],
        labels=['0-200m', '200-500m', '500m-1km', '1-2km', '>2km']
    )

    # Summary by distance band
    print("\nPrice by MRT Distance Band:")
    band_stats = df.groupby('dist_band', observed=True).agg({
        'price_psf': ['mean', 'median', 'count'],
        'dist_to_nearest_mrt': 'mean'
    }).round(2)
    print(band_stats)

    # Correlation analysis
    print("\nCorrelation with MRT Distance:")
    for target in ['price_psf', 'rental_yield_pct', 'yoy_change_pct']:
        if target in df.columns:
            valid_data = df[[target, 'dist_to_nearest_mrt']].dropna()
            if len(valid_data) > 100:
                corr = valid_data.corr().iloc[0, 1]
                print(f"  {target}: {corr:.3f}")

    # Visualizations
    print("\nCreating visualizations...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Price vs Distance scatter
    ax = axes[0, 0]
    sample = df.sample(n=min(5000, len(df)), random_state=42)
    ax.scatter(sample['dist_to_nearest_mrt'], sample['price_psf'], alpha=0.3, s=1)
    ax.set_xlabel('Distance to Nearest MRT (m)')
    ax.set_ylabel('Price PSF ($)')
    ax.set_title('Price vs MRT Distance')
    ax.grid(True, alpha=0.3)

    # 2. Average price by distance band
    ax = axes[0, 1]
    band_prices = df.groupby('dist_band', observed=True)['price_psf'].mean().sort_index()
    band_prices.plot(kind='bar', ax=ax)
    ax.set_xlabel('Distance Band')
    ax.set_ylabel('Average Price PSF ($)')
    ax.set_title('Average Price by Distance Band')
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True, alpha=0.3, axis='y')

    # 3. Distribution of distances
    ax = axes[1, 0]
    ax.hist(df['dist_to_nearest_mrt'], bins=50, edgecolor='black', alpha=0.7)
    ax.axvline(df['dist_to_nearest_mrt'].median(), color='red', linestyle='--',
               label=f"Median: {df['dist_to_nearest_mrt'].median():.0f}m")
    ax.set_xlabel('Distance to Nearest MRT (m)')
    ax.set_ylabel('Frequency')
    ax.set_title('Distribution of MRT Distances')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # 4. Price trends by year
    ax = axes[1, 1]
    yearly_avg = df.groupby('year')['price_psf'].mean()
    yearly_avg.plot(marker='o', ax=ax)
    ax.set_xlabel('Year')
    ax.set_ylabel('Average Price PSF ($)')
    ax.set_title('Price Trends Over Time')
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    fig_path = OUTPUT_DIR / "exploratory_analysis.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"  Saved: {fig_path}")
    plt.close()

    return df


def prepare_features(df, target_col='price_psf'):
    """Prepare features for modeling."""
    print(f"\nPreparing features for: {target_col}")

    # Drop rows with missing target
    df_model = df.dropna(subset=[target_col]).copy()

    # Basic property features
    feature_cols = [
        'dist_to_nearest_mrt',
        'floor_area_sqm',
        'remaining_lease_months',
        'year',
        'month'
    ]

    # Add amenity counts
    amenity_cols = [
        'mrt_within_500m', 'mrt_within_1km', 'mrt_within_2km',
        'hawker_within_500m', 'hawker_within_1km',
        'supermarket_within_500m', 'supermarket_within_1km',
        'park_within_500m', 'park_within_1km'
    ]

    # Add available amenity columns
    for col in amenity_cols:
        if col in df_model.columns:
            feature_cols.append(col)

    # Select only available features
    feature_cols = [col for col in feature_cols if col in df_model.columns]

    # Create distance transformations
    df_model['log_dist_mrt'] = np.log1p(df_model['dist_to_nearest_mrt'])
    df_model['inv_dist_mrt'] = 1 / (df_model['dist_to_nearest_mrt'] + 1)  # +1 to avoid div/0

    # Drop rows with NaN in features
    df_model = df_model.dropna(subset=feature_cols + ['log_dist_mrt', 'inv_dist_mrt'])

    print(f"  Selected {len(feature_cols)} base features")
    print(f"  Dataset size: {len(df_model):,} records")

    return df_model, feature_cols


def run_ols_regression(df, target_col='price_psf'):
    """Run OLS regression with different distance specifications."""
    print(f"\n{'='*80}")
    print(f"OLS REGRESSION: {target_col}")
    print(f"{'='*80}")

    df_model, base_features = prepare_features(df, target_col)

    results = []

    # Model 1: Linear distance
    features_linear = base_features.copy()
    X_linear = df_model[features_linear].select_dtypes(include=[np.number])
    y = df_model[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X_linear, y, test_size=0.2, random_state=42
    )

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    results.append({
        'specification': 'Linear',
        'r2': r2,
        'mae': mae,
        'model': model,
        'features': X_linear.columns.tolist()
    })

    print(f"\nLinear Distance:")
    print(f"  R²: {r2:.4f}")
    print(f"  MAE: {mae:.2f}")

    # Get MRT coefficient
    if 'dist_to_nearest_mrt' in X_linear.columns:
        mrt_idx = X_linear.columns.get_loc('dist_to_nearest_mrt')
        mrt_coef = model.coef_[mrt_idx]
        print(f"  MRT Coefficient: {mrt_coef:.4f} (PSF change per meter)")

        # Calculate marginal effect
        me_100m = mrt_coef * 100
        print(f"  Marginal Effect: Every 100m closer to MRT = ${me_100m:.2f} PSF")

    # Model 2: Log distance
    features_log = base_features + ['log_dist_mrt']
    X_log = df_model[features_log].select_dtypes(include=[np.number])

    X_train, X_test, y_train, y_test = train_test_split(
        X_log, y, test_size=0.2, random_state=42
    )

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    results.append({
        'specification': 'Log',
        'r2': r2,
        'mae': mae,
        'model': model,
        'features': X_log.columns.tolist()
    })

    print(f"\nLog Distance:")
    print(f"  R²: {r2:.4f}")
    print(f"  MAE: {mae:.2f}")

    # Model 3: Inverse distance
    features_inv = base_features + ['inv_dist_mrt']
    X_inv = df_model[features_inv].select_dtypes(include=[np.number])

    X_train, X_test, y_train, y_test = train_test_split(
        X_inv, y, test_size=0.2, random_state=42
    )

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    results.append({
        'specification': 'Inverse',
        'r2': r2,
        'mae': mae,
        'model': model,
        'features': X_inv.columns.tolist()
    })

    print(f"\nInverse Distance:")
    print(f"  R²: {r2:.4f}")
    print(f"  MAE: {mae:.2f}")

    # Select best model
    best = max(results, key=lambda x: x['r2'])
    print(f"\nBest specification: {best['specification']} (R² = {best['r2']:.4f})")

    return results, best


def extract_feature_coefficients(model, feature_names, target_col):
    """Extract coefficients from trained model."""
    coefs = pd.DataFrame({
        'feature': feature_names,
        'coefficient': model.coef_
    }).sort_values('coefficient', key=abs, ascending=False)

    coefs['abs_coef'] = coefs['coefficient'].abs()
    coefs['target'] = target_col

    return coefs


def run_advanced_models(df, target_col='price_psf'):
    """Run XGBoost and Random Forest models."""
    print(f"\n{'='*80}")
    print(f"ADVANCED MODELS: {target_col}")
    print(f"{'='*80}")

    df_model, base_features = prepare_features(df, target_col)

    # Prepare features
    X = df_model[base_features].select_dtypes(include=[np.number])
    y = df_model[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    results = {}

    # XGBoost
    print("\nTraining XGBoost...")
    xgb_model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=-1,
        random_state=42
    )

    xgb_model.fit(X_train, y_train)
    y_pred = xgb_model.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    results['xgboost'] = {
        'model': xgb_model,
        'r2': r2,
        'mae': mae,
        'rmse': rmse
    }

    print(f"  R²: {r2:.4f}")
    print(f"  MAE: {mae:.2f}")
    print(f"  RMSE: {rmse:.2f}")

    # Feature importance
    importance = pd.DataFrame({
        'feature': X.columns,
        'importance': xgb_model.feature_importances_
    }).sort_values('importance', ascending=False)

    importance['target'] = target_col
    importance['model'] = 'xgboost'

    print(f"\n  Top 10 Features:")
    print(importance.head(10)[['feature', 'importance']].to_string(index=False))

    # SHAP analysis
    shap_values = None
    if SHAP_AVAILABLE:
        try:
            print(f"\n  Calculating SHAP values...")
            explainer = shap.TreeExplainer(xgb_model)
            shap_values = explainer.shap_values(X_test)

            shap_importance = pd.DataFrame({
                'feature': X.columns,
                'shap_value': np.abs(shap_values).mean(axis=0)
            }).sort_values('shap_value', ascending=False)

            shap_importance['target'] = target_col

            print(f"\n  Top 10 Features by SHAP:")
            print(shap_importance.head(10)[['feature', 'shap_value']].to_string(index=False))

            results['shap'] = shap_importance
        except Exception as e:
            print(f"  SHAP calculation failed: {e}")

    results['importance'] = importance

    return results, X_test, y_test


def h3_aggregate_analysis(df):
    """Aggregate analysis by H8 cells."""
    print(f"\n{'='*80}")
    print("H3 CELL AGGREGATION ANALYSIS")
    print(f"{'='*80}")

    if not H3_AVAILABLE or 'h8_cell' not in df.columns:
        print("  Skipping (H3 not available)")
        return None

    # Aggregate by H8 cell
    h3_stats = df.groupby('h8_cell').agg({
        'price_psf': ['mean', 'median', 'count'],
        'dist_to_nearest_mrt': 'mean',
        'lat': 'first',
        'lon': 'first'
    }).reset_index()

    h3_stats.columns = ['h8_cell', 'price_mean', 'price_median', 'n_records',
                        'avg_mrt_dist', 'lat', 'lon']

    # Filter cells with sufficient data
    h3_stats = h3_stats[h3_stats['n_records'] >= 10].dropna()

    print(f"\n  H8 cells with >=10 records: {len(h3_stats)}")
    print(f"  Average records per cell: {h3_stats['n_records'].mean():.1f}")

    # Correlation at cell level
    corr = h3_stats[['avg_mrt_dist', 'price_mean']].corr().iloc[0, 1]
    print(f"\n  Correlation (avg MRT distance, avg price): {corr:.3f}")

    # Cell-level regression
    X = h3_stats[['avg_mrt_dist']].values
    y = h3_stats['price_mean'].values

    model = LinearRegression()
    model.fit(X, y)

    print(f"\n  Cell-level Regression:")
    print(f"    R²: {model.score(X, y):.4f}")
    print(f"    Coefficient: {model.coef_[0]:.4f}")
    print(f"    Interpretation: Every 100m closer to MRT = ${model.coef_[0] * 100:.2f} PSF")

    return h3_stats


def main():
    """Main analysis pipeline."""

    # Load data
    df = load_and_prepare_data()

    # Exploratory analysis
    df = exploratory_analysis(df)

    # Run models for each target
    targets = {
        'price_psf': 'Transaction Price (PSF)',
        'rental_yield_pct': 'Rental Yield (%)',
        'yoy_change_pct': 'YoY Appreciation (%)'
    }

    all_ols_results = {}
    all_advanced_results = {}
    all_importance = []

    for target_col, target_name in targets.items():
        print(f"\n{'#'*80}")
        print(f"# ANALYZING: {target_name}")
        print(f"{'#'*80}")

        # OLS models
        ols_results, best_ols = run_ols_regression(df, target_col)
        all_ols_results[target_col] = ols_results

        # Extract coefficients
        coef_df = extract_feature_coefficients(
            best_ols['model'],
            best_ols['features'],
            target_col
        )
        coef_path = OUTPUT_DIR / f"coefficients_{target_col}.csv"
        coef_df.to_csv(coef_path, index=False)
        print(f"\n  Saved coefficients: {coef_path}")

        # Advanced models
        try:
            advanced_results, X_test, y_test = run_advanced_models(df, target_col)
            all_advanced_results[target_col] = advanced_results

            # Save feature importance
            if 'importance' in advanced_results:
                imp = advanced_results['importance']
                imp_path = OUTPUT_DIR / f"importance_{target_col}_xgboost.csv"
                imp.to_csv(imp_path, index=False)
                all_importance.append(imp)

            # Save SHAP if available
            if 'shap' in advanced_results:
                shap_df = advanced_results['shap']
                shap_path = OUTPUT_DIR / f"shap_{target_col}.csv"
                shap_df.to_csv(shap_path, index=False)

        except Exception as e:
            print(f"  Advanced models failed: {e}")
            continue

    # H3 aggregation
    h3_stats = h3_aggregate_analysis(df)

    # Compile results summary
    print(f"\n{'='*80}")
    print("COMPILING RESULTS SUMMARY")
    print(f"{'='*80}")

    summary_data = []
    for target_col, target_name in targets.items():
        if target_col in all_ols_results:
            best_ols = max(all_ols_results[target_col], key=lambda x: x['r2'])
            summary_data.append({
                'target': target_col,
                'target_name': target_name,
                'best_ols_spec': best_ols['specification'],
                'ols_r2': best_ols['r2'],
                'ols_mae': best_ols['mae']
            })

        if target_col in all_advanced_results:
            adv = all_advanced_results[target_col]
            if 'xgboost' in adv:
                summary_data[-1]['xgboost_r2'] = adv['xgboost']['r2']
                summary_data[-1]['xgboost_mae'] = adv['xgboost']['mae']

    summary_df = pd.DataFrame(summary_data)
    summary_path = OUTPUT_DIR / "model_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    print("\nModel Performance Summary:")
    print(summary_df.to_string(index=False))
    print(f"\n  Saved: {summary_path}")

    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"\nAll results saved to: {OUTPUT_DIR}")
    print("\nKey output files:")
    print("  - exploratory_analysis.png")
    print("  - coefficients_*.csv")
    print("  - importance_*_xgboost.csv")
    print("  - shap_*.csv")
    print("  - model_summary.csv")


if __name__ == "__main__":
    main()
