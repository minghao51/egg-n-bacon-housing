"""
MRT Impact Comparison by Property Type

Compares MRT proximity impact across:
- HDB (public housing)
- Condominium (private housing)
- EC (Executive Condominium - hybrid)

Research Questions:
1. Does MRT sensitivity differ by property type?
2. What is the MRT premium $/100m for each type?
3. Do feature importance patterns differ?
4. Should investment strategies vary by property type?
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

import xgboost as xgb
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("SHAP not available")

import matplotlib.pyplot as plt
import seaborn as sns

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Paths
DATA_DIR = Path("data/pipeline/L3")
OUTPUT_DIR = Path("data/analytics/mrt_impact")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_data():
    """Load unified dataset with 2021+ data."""
    print("="*80)
    print("MRT IMPACT ANALYSIS - BY PROPERTY TYPE (2021+)")
    print("="*80)

    df = pd.read_parquet(DATA_DIR / "housing_unified.parquet")
    df = df[df['year'] >= 2021].copy()

    # Ensure coordinates are numeric
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')

    print(f"\nDataset: {len(df):,} records (2021+)")
    print("\nRecords by property type:")
    print(df['property_type'].value_counts())

    # Check amenity coverage
    print("\nAmenity coverage by property type:")
    for pt in ['HDB', 'Condominium', 'EC']:
        subset = df[df['property_type'] == pt]
        coverage = subset['dist_to_nearest_mrt'].notna().sum()
        total = len(subset)
        pct = coverage / total * 100 if total > 0 else 0
        print(f"  {pt}: {coverage:,}/{total:,} ({pct:.1f}%)")

    return df


def analyze_by_property_type(df, target_col='price_psf'):
    """Run analysis separately for each property type."""

    results = {}
    property_types = ['HDB', 'Condominium', 'EC']

    for property_type in property_types:
        print(f"\n{'='*80}")
        print(f"ANALYZING: {property_type}")
        print(f"{'='*80}")

        # Filter data
        subset = df[df['property_type'] == property_type].copy()

        # Drop rows without target or MRT distance
        subset = subset.dropna(subset=[target_col, 'dist_to_nearest_mrt'])

        if len(subset) < 100:
            print(f"  Skipping {property_type}: insufficient data ({len(subset)} records)")
            continue

        # Prepare features (only use features that exist for this property type)
        base_features = [
            'dist_to_nearest_mrt',
            'floor_area_sqm',
            'year',
            'mrt_within_500m',
            'mrt_within_1km',
            'hawker_within_500m',
            'hawker_within_1km',
            'supermarket_within_500m',
            'supermarket_within_1km',
            'park_within_500m',
            'park_within_1km'
        ]

        # Add remaining_lease_months for HDB only
        if property_type == 'HDB' and 'remaining_lease_months' in subset.columns:
            base_features.append('remaining_lease_months')

        # Select available features
        available_features = [col for col in base_features if col in subset.columns]

        # Drop NaN (only for selected features)
        X = subset[available_features].copy()
        y = subset[target_col].copy()

        # Drop rows where X has NaN or y has NaN
        valid_mask = X.notna().all(axis=1) & y.notna()
        X = X[valid_mask]
        y = y[valid_mask]

        print(f"  Final dataset: {len(X):,} records, {len(available_features)} features")

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # === OLS Regression ===
        print("\n  Running OLS Regression...")
        ols_model = LinearRegression()
        ols_model.fit(X_train, y_train)

        y_pred_ols = ols_model.predict(X_test)
        ols_r2 = r2_score(y_test, y_pred_ols)
        ols_mae = mean_absolute_error(y_test, y_pred_ols)

        # Extract MRT coefficient
        mrt_idx = available_features.index('dist_to_nearest_mrt')
        mrt_coef = ols_model.coef_[mrt_idx]
        mrt_coef_100m = mrt_coef * 100

        print(f"    R²: {ols_r2:.4f}")
        print(f"    MAE: {ols_mae:.2f}")
        print(f"    MRT Coefficient: {mrt_coef:.4f} PSF/meter")
        print(f"    MRT Premium: ${mrt_coef_100m:.2f} per 100m")

        # === XGBoost ===
        print("\n  Training XGBoost...")
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
        y_pred_xgb = xgb_model.predict(X_test)

        xgb_r2 = r2_score(y_test, y_pred_xgb)
        xgb_mae = mean_absolute_error(y_test, y_pred_xgb)

        print(f"    R²: {xgb_r2:.4f}")
        print(f"    MAE: {xgb_mae:.2f}")

        # Feature importance
        importance = pd.DataFrame({
            'feature': available_features,
            'importance': xgb_model.feature_importances_
        }).sort_values('importance', ascending=False)

        print("\n    Top 5 Features:")
        print(importance.head(5).to_string(index=False))

        # Store results
        results[property_type] = {
            'n': len(X),
            'mean_price': y.mean(),
            'ols_r2': ols_r2,
            'ols_mae': ols_mae,
            'mrt_coef': mrt_coef,
            'mrt_coef_100m': mrt_coef_100m,
            'xgb_r2': xgb_r2,
            'xgb_mae': xgb_mae,
            'importance': importance,
            'features': available_features
        }

    return results


def compare_property_types(results):
    """Compare MRT impact across property types."""

    print(f"\n{'='*80}")
    print("CROSS-PROPERTY-TYPE COMPARISON")
    print(f"{'='*80}")

    # Create comparison DataFrame
    comparison_data = []

    for pt, data in results.items():
        comparison_data.append({
            'property_type': pt,
            'n': data['n'],
            'mean_price': data['mean_price'],
            'mrt_premium_100m': data['mrt_coef_100m'],
            'ols_r2': data['ols_r2'],
            'xgb_r2': data['xgb_r2'],
            'ols_mae': data['ols_mae'],
            'xgb_mae': data['xgb_mae']
        })

    comparison_df = pd.DataFrame(comparison_data)

    print("\nMRT Premium by Property Type:")
    print(comparison_df[['property_type', 'mrt_premium_100m', 'mean_price']].to_string(index=False))

    print("\nModel Performance Comparison:")
    print(comparison_df[['property_type', 'ols_r2', 'xgb_r2']].to_string(index=False))

    # Statistical test of difference
    print("\nStatistical Significance Tests:")
    if 'HDB' in results and 'Condominium' in results:
        hdb_premium = results['HDB']['mrt_coef_100m']
        condo_premium = results['Condominium']['mrt_coef_100m']
        diff = abs(hdb_premium - condo_premium)

        print(f"\n  Difference (HDB vs Condo): ${diff:.2f} per 100m")

        if diff > 1.0:
            print("  → ECONOMICALLY SIGNIFICANT (>$1/100m difference)")
        else:
            print("  → Minimal practical difference")

    return comparison_df


def visualize_comparison(results, comparison_df):
    """Create comparison visualizations."""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. MRT Premium Comparison
    ax = axes[0, 0]
    colors = ['steelblue', 'coral', 'forestgreen']
    ax.bar(comparison_df['property_type'], comparison_df['mrt_premium_100m'], color=colors)
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
    ax.set_ylabel('MRT Premium ($ per 100m closer)')
    ax.set_title('MRT Impact by Property Type', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    # Add value labels
    for i, v in enumerate(comparison_df['mrt_premium_100m']):
        ax.text(i, v + (0.1 if v > 0 else -0.3), f'${v:.2f}',
               ha='center', fontweight='bold')

    # 2. Mean Price Comparison
    ax = axes[0, 1]
    ax.bar(comparison_df['property_type'], comparison_df['mean_price'], color=colors)
    ax.set_ylabel('Mean Price ($ PSF)')
    ax.set_title('Price Level by Property Type', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    # 3. Model Performance (R²)
    ax = axes[1, 0]
    x = np.arange(len(comparison_df))
    width = 0.35

    ax.bar(x - width/2, comparison_df['ols_r2'], width, label='OLS', color='lightblue')
    ax.bar(x + width/2, comparison_df['xgb_r2'], width, label='XGBoost', color='navy')

    ax.set_ylabel('R² Score')
    ax.set_title('Model Performance by Property Type', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(comparison_df['property_type'])
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # 4. Feature Importance Comparison (top 5)
    ax = axes[1, 1]

    # Get top 5 features across all types
    all_importance = pd.concat([
        results[pt]['importance'].head(5).copy()
        for pt in results.keys()
    ])

    all_importance['property_type'] = all_importance.index.map(
        lambda x: next(pt for pt in results.keys() if x in results[pt]['importance'].index)
    )

    # Pivot for heatmap
    pivot_data = all_importance.pivot_table(
        index='feature',
        columns='property_type',
        values='importance',
        fill_value=0
    )

    if not pivot_data.empty:
        sns.heatmap(pivot_data, annot=True, fmt='.3f', cmap='YlOrRd', ax=ax)
        ax.set_title('Feature Importance Comparison', fontweight='bold')
        ax.set_xlabel('')

    plt.tight_layout()

    fig_path = OUTPUT_DIR / "property_type_comparison.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"\nSaved visualization: {fig_path}")
    plt.close()


def create_interaction_model(df, target_col='price_psf'):
    """Run model with property_type × MRT interaction."""

    print(f"\n{'='*80}")
    print("INTERACTION MODEL: property_type × MRT_distance")
    print(f"{'='*80}")

    # Prepare data
    subset = df.dropna(subset=[target_col, 'dist_to_nearest_mrt']).copy()

    # Create property type dummies
    subset['is_condo'] = (subset['property_type'] == 'Condominium').astype(int)
    subset['is_ec'] = (subset['property_type'] == 'EC').astype(int)

    # Interaction terms
    subset['mrt_x_condo'] = subset['dist_to_nearest_mrt'] * subset['is_condo']
    subset['mrt_x_ec'] = subset['dist_to_nearest_mrt'] * subset['is_ec']

    feature_cols = [
        'dist_to_nearest_mrt',
        'is_condo',
        'is_ec',
        'mrt_x_condo',
        'mrt_x_ec',
        'floor_area_sqm',
        'year'
    ]

    # Add remaining_lease_months only if it exists
    if 'remaining_lease_months' in subset.columns:
        feature_cols.append('remaining_lease_months')

    available_features = [col for col in feature_cols if col in subset.columns]

    X = subset[available_features].copy()
    y = subset[target_col].copy()

    # Drop rows where X has NaN or y has NaN
    valid_mask = X.notna().all(axis=1) & y.notna()
    X = X[valid_mask]
    y = y[valid_mask]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"Dataset: {len(X):,} records")

    # Fit model
    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)

    print(f"\nR²: {r2:.4f}")

    # Extract coefficients
    coefs = pd.DataFrame({
        'feature': available_features,
        'coefficient': model.coef_
    })

    print("\nCoefficients:")
    print(coefs.to_string(index=False))

    # Interpret interaction terms
    print("\nInterpretation:")
    print(f"  Baseline (HDB): MRT coefficient = ${coefs.loc[coefs['feature'] == 'dist_to_nearest_mrt', 'coefficient'].values[0]:.4f} PSF/meter")

    if 'mrt_x_condo' in coefs['feature'].values:
        condo_interaction = coefs.loc[coefs['feature'] == 'mrt_x_condo', 'coefficient'].values[0]
        baseline = coefs.loc[coefs['feature'] == 'dist_to_nearest_mrt', 'coefficient'].values[0]
        condo_effect = baseline + condo_interaction
        print(f"  Condo: MRT coefficient = ${condo_effect:.4f} PSF/meter")
        print(f"    (baseline + interaction = ${baseline:.4f} + ${condo_interaction:.4f})")

    if 'mrt_x_ec' in coefs['feature'].values:
        ec_interaction = coefs.loc[coefs['feature'] == 'mrt_x_ec', 'coefficient'].values[0]
        baseline = coefs.loc[coefs['feature'] == 'dist_to_nearest_mrt', 'coefficient'].values[0]
        ec_effect = baseline + ec_interaction
        print(f"  EC: MRT coefficient = ${ec_effect:.4f} PSF/meter")
        print(f"    (baseline + interaction = ${baseline:.4f} + ${ec_interaction:.4f})")

    # Statistical significance
    n = len(X_test)
    p = len(X_test.columns)
    dof = n - p - 1

    # Calculate t-statistics for interaction terms
    if 'mrt_x_condo' in available_features:
        # Simple approximation of standard error
        y_pred_train = model.predict(X_train)
        mse = np.mean((y_train - y_pred_train) ** 2)
        X_with_intercept = np.column_stack([np.ones(len(X_train)), X_train.values])
        var_coef = mse * np.diag(np.linalg.inv(X_with_intercept.T @ X_with_intercept))

        se_condo = np.sqrt(var_coef[available_features.index('mrt_x_condo') + 1])
        t_condo = condo_interaction / se_condo
        p_value_condo = 2 * (1 - stats.t.cdf(abs(t_condo), dof))

        print("\n  Statistical Test (Condo interaction):")
        print(f"    t-statistic: {t_condo:.4f}")
        print(f"    p-value: {p_value_condo:.4f}")

        if p_value_condo < 0.05:
            print("    → SIGNIFICANT at 5% level (p < 0.05)")
        else:
            print("    → NOT significant at 5% level")

    return coefs


def main():
    """Main analysis pipeline."""

    # Load data
    df = load_data()

    # Check amenity coverage
    hdb_coverage = df[df['property_type'] == 'HDB']['dist_to_nearest_mrt'].notna().sum()
    condo_coverage = df[df['property_type'] == 'Condominium']['dist_to_nearest_mrt'].notna().sum()
    ec_coverage = df[df['property_type'] == 'EC']['dist_to_nearest_mrt'].notna().sum()

    if condo_coverage == 0 or ec_coverage == 0:
        print("\n" + "="*80)
        print("⚠️  WARNING: Condo/EC amenity data missing!")
        print("="*80)
        print("\nThe condo/EC amenity calculation script may still be running.")
        print("Please check: tail -f /tmp/condo_amenities.log")
        print("\nOnce complete, re-run this script.")
        print("="*80)
        return

    # Analyze by property type
    results = analyze_by_property_type(df, target_col='price_psf')

    if len(results) == 0:
        print("\nNo property types had sufficient data for analysis")
        return

    # Compare across types
    comparison_df = compare_property_types(results)

    # Visualizations
    visualize_comparison(results, comparison_df)

    # Interaction model
    interaction_coefs = create_interaction_model(df)

    # Save results
    print(f"\n{'='*80}")
    print("SAVING RESULTS")
    print(f"{'='*80}")

    # Save comparison
    comparison_path = OUTPUT_DIR / "property_type_comparison.csv"
    comparison_df.to_csv(comparison_path, index=False)
    print(f"Saved: {comparison_path}")

    # Save feature importances
    for pt, data in results.items():
        importance_path = OUTPUT_DIR / f"importance_{pt.lower()}_xgboost.csv"
        data['importance'].to_csv(importance_path, index=False)
        print(f"Saved: {importance_path}")

    # Save interaction coefficients
    interaction_path = OUTPUT_DIR / "interaction_model_coefficients.csv"
    interaction_coefs.to_csv(interaction_path, index=False)
    print(f"Saved: {interaction_path}")

    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"\nAll results saved to: {OUTPUT_DIR}")

    print("\nKey Findings:")
    for _, row in comparison_df.iterrows():
        print(f"\n  {row['property_type']}:")
        print(f"    MRT Premium: ${row['mrt_premium_100m']:.2f} per 100m")
        print(f"    Mean Price: ${row['mean_price']:.2f} PSF")


if __name__ == "__main__":
    main()
