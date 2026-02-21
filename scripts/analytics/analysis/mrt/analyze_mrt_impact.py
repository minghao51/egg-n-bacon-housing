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

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

import xgboost as xgb
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

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
OUTPUT_DIR = Path("data/analytics/mrt_impact")
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

    print("\nLinear Distance:")
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

    print("\nLog Distance:")
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

    print("\nInverse Distance:")
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

    print("\n  Top 10 Features:")
    print(importance.head(10)[['feature', 'importance']].to_string(index=False))

    # SHAP analysis
    shap_values = None
    if SHAP_AVAILABLE:
        try:
            print("\n  Calculating SHAP values...")
            explainer = shap.TreeExplainer(xgb_model)
            shap_values = explainer.shap_values(X_test)

            shap_importance = pd.DataFrame({
                'feature': X.columns,
                'shap_value': np.abs(shap_values).mean(axis=0)
            }).sort_values('shap_value', ascending=False)

            shap_importance['target'] = target_col

            print("\n  Top 10 Features by SHAP:")
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

    print("\n  Cell-level Regression:")
    print(f"    R²: {model.score(X, y):.4f}")
    print(f"    Coefficient: {model.coef_[0]:.4f}")
    print(f"    Interpretation: Every 100m closer to MRT = ${model.coef_[0] * 100:.2f} PSF")

    return h3_stats


def create_feature_importance_chart(all_importance, target_col='price_psf'):
    """Create horizontal bar chart of feature importance."""
    print(f"\nCreating feature importance chart for {target_col}...")

    # Get importance for target
    imp_df = [imp for imp in all_importance if imp['target'].iloc[0] == target_col][0]

    # Sort and get top 15
    imp_df = imp_df.nlargest(15, 'importance').sort_values('importance')

    # Create color mapping based on feature type
    def get_feature_color(feature):
        feature_lower = feature.lower()
        if 'mrt' in feature_lower:
            return '#1f77b4'  # Blue for MRT
        elif 'hawker' in feature_lower:
            return '#ff7f0e'  # Orange for food
        elif 'park' in feature_lower:
            return '#2ca02c'  # Green for parks
        elif 'supermarket' in feature_lower:
            return '#9467bd'  # Purple for shopping
        elif any(x in feature_lower for x in ['year', 'month']):
            return '#d62728'  # Red for temporal
        elif any(x in feature_lower for x in ['lease', 'area', 'floor']):
            return '#8c564b'  # Brown for property attributes
        else:
            return '#7f7f7f'  # Gray for other

    colors = [get_feature_color(f) for f in imp_df['feature']]

    # Create chart
    fig, ax = plt.subplots(figsize=(12, 8))

    bars = ax.barh(range(len(imp_df)), imp_df['importance'], color=colors)

    # Customize
    ax.set_yticks(range(len(imp_df)))
    ax.set_yticklabels(imp_df['feature'])
    ax.set_xlabel('Feature Importance (Gain)', fontsize=12, fontweight='bold')
    ax.set_title(f'XGBoost Feature Importance for {target_col.replace("_", " ").title()}',
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#1f77b4', label='MRT Access'),
        Patch(facecolor='#ff7f0e', label='Food Access'),
        Patch(facecolor='#2ca02c', label='Parks'),
        Patch(facecolor='#9467bd', label='Shopping'),
        Patch(facecolor='#d62728', label='Temporal'),
        Patch(facecolor='#8c564b', label='Property Attributes')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=9)

    plt.tight_layout()
    fig_path = OUTPUT_DIR / f"feature_importance_{target_col}.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"  Saved: {fig_path}")
    plt.close()


def create_model_performance_chart(summary_df):
    """Create grouped bar chart comparing OLS vs XGBoost performance."""
    print("\nCreating model performance comparison chart...")

    # Prepare data
    models = summary_df['target_name'].tolist()
    ols_r2 = summary_df['ols_r2'].tolist()
    xgb_r2 = summary_df['xgboost_r2'].tolist()

    x = np.arange(len(models))
    width = 0.35

    # Create chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # R² comparison
    bars1 = ax1.bar(x - width/2, ols_r2, width, label='OLS', color='#7f7f7f', alpha=0.8)
    bars2 = ax1.bar(x + width/2, xgb_r2, width, label='XGBoost', color='#1f77b4', alpha=0.8)

    ax1.set_xlabel('Target Variable', fontsize=12, fontweight='bold')
    ax1.set_ylabel('R² Score', fontsize=12, fontweight='bold')
    ax1.set_title('Model Performance Comparison (R²)', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(models, rotation=15, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax1.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        height = bar.get_height()
        ax1.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)

    # MAE comparison
    ols_mae = summary_df['ols_mae'].tolist()
    xgb_mae = summary_df['xgboost_mae'].tolist()

    bars3 = ax2.bar(x - width/2, ols_mae, width, label='OLS', color='#7f7f7f', alpha=0.8)
    bars4 = ax2.bar(x + width/2, xgb_mae, width, label='XGBoost', color='#1f77b4', alpha=0.8)

    ax2.set_xlabel('Target Variable', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Mean Absolute Error', fontsize=12, fontweight='bold')
    ax2.set_title('Model Performance Comparison (MAE)', fontsize=14, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(models, rotation=15, ha='right')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for bar in bars3:
        height = bar.get_height()
        ax2.annotate(f'{height:.1f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)
    for bar in bars4:
        height = bar.get_height()
        ax2.annotate(f'{height:.1f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    fig_path = OUTPUT_DIR / "model_performance_comparison.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"  Saved: {fig_path}")
    plt.close()


def create_distance_band_premiums_chart(df):
    """Create line chart showing price premiums by distance band and property type."""
    print("\nCreating distance band premiums chart...")

    # Create distance bands if not exists
    if 'dist_band' not in df.columns:
        df['dist_band'] = pd.cut(
            df['dist_to_nearest_mrt'],
            bins=[0, 200, 500, 1000, 2000, 10000],
            labels=['0-200m', '200-500m', '500m-1km', '1-2km', '>2km']
        )

    # Calculate mean price by band and property type
    band_prices = df.groupby(['dist_band', 'property_type'], observed=True)['price_psf'].mean().reset_index()
    band_prices = band_prices.pivot(index='dist_band', columns='property_type', values='price_psf')

    # Define band order and midpoints for x-axis
    band_order = ['0-200m', '200-500m', '500m-1km', '1-2km', '>2km']
    band_midpoints = [100, 350, 750, 1500, 3000]  # Approximate midpoint of each band

    # Reindex to ensure correct order
    band_prices = band_prices.reindex(band_order)

    # Create chart
    fig, ax = plt.subplots(figsize=(12, 7))

    # Plot each property type
    colors = {'HDB': '#1f77b4', 'Condominium': '#ff7f0e', 'Executive Condominium': '#2ca02c'}
    markers = {'HDB': 'o', 'Condominium': 's', 'Executive Condominium': '^'}

    for prop_type in band_prices.columns:
        if prop_type in colors:
            ax.plot(band_midpoints, band_prices[prop_type],
                   marker=markers[prop_type], markersize=8, linewidth=2,
                   label=prop_type, color=colors[prop_type])

    ax.set_xlabel('Distance to MRT (m)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Average Price PSF ($)', fontsize=12, fontweight='bold')
    ax.set_title('Price Premium by MRT Distance Band and Property Type',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='upper right')
    ax.grid(True, alpha=0.3)

    # Add reference band labels at the bottom
    band_labels = ['0-200m', '', '500m-1km', '', '>2km']
    ax.set_xticks(band_midpoints)
    ax.set_xticklabels(band_labels)

    plt.tight_layout()
    fig_path = OUTPUT_DIR / "distance_band_premiums.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"  Saved: {fig_path}")
    plt.close()


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

    # Create additional visualizations
    print(f"\n{'='*80}")
    print("CREATING ADDITIONAL VISUALIZATIONS")
    print(f"{'='*80}")

    # Feature importance chart for price_psf
    if all_importance:
        create_feature_importance_chart(all_importance, 'price_psf')

    # Model performance comparison
    create_model_performance_chart(summary_df)

    # Distance band premiums
    create_distance_band_premiums_chart(df)

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
