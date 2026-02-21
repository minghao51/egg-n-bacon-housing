"""
School Impact Comparison by Property Type

Compares school proximity and quality impact across:
- HDB (public housing)
- Condominium (private housing)
- EC (Executive Condominium - hybrid)

Research Questions:
1. Does school quality sensitivity differ by property type?
2. What is the school premium $/unit for each type?
3. Do feature importance patterns differ?
4. Should investment strategies vary by property type?
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

import xgboost as xgb
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
OUTPUT_DIR = Path("data/analytics/school_impact")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_data():
    """Load unified dataset with 2021+ data."""
    print("="*80)
    print("SCHOOL IMPACT ANALYSIS - BY PROPERTY TYPE (2021+)")
    print("="*80)

    df = pd.read_parquet(DATA_DIR / "housing_unified.parquet")
    df = df[df['year'] >= 2021].copy()

    print(f"\nDataset: {len(df):,} records (2021+)")
    print("\nRecords by property type:")
    print(df['property_type'].value_counts())

    # Check school feature coverage by property type
    print("\nSchool feature coverage by property type:")
    for pt in ['HDB', 'Condominium', 'EC']:
        subset = df[df['property_type'] == pt]
        for feature in ['school_within_1km', 'school_accessibility_score', 'school_primary_quality_score']:
            if feature in subset.columns:
                coverage = subset[feature].notna().sum()
                total = len(subset)
                pct = coverage / total * 100 if total > 0 else 0
                print(f"  {pt} - {feature}: {coverage:,}/{total:,} ({pct:.1f}%)")

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

        # Drop rows without target
        subset = subset.dropna(subset=[target_col])

        if len(subset) < 100:
            print(f"  Skipping {property_type}: insufficient data ({len(subset)} records)")
            continue

        # Prepare features (only use features that exist for this property type)
        base_features = [
            'floor_area_sqm',
            'year'
        ]

        # Add school features that exist
        school_features = [
            'school_within_1km',
            'school_accessibility_score',
            'school_primary_quality_score',
            'school_secondary_quality_score',
            'school_density_score'
        ]

        for feature in school_features:
            if feature in subset.columns:
                base_features.append(feature)

        # Add remaining_lease_months for HDB only
        if property_type == 'HDB' and 'remaining_lease_months' in subset.columns:
            base_features.append('remaining_lease_months')

        # Add amenity controls (if available)
        amenity_features = ['dist_to_nearest_mrt']
        for feature in amenity_features:
            if feature in subset.columns:
                base_features.append(feature)

        # Select available features
        available_features = [col for col in base_features if col in subset.columns]

        # Drop NaN (only for selected features)
        X = subset[available_features].copy()
        y = subset[target_col].copy()

        # Drop rows where X has NaN or y has NaN
        valid_mask = X.notna().all(axis=1) & y.notna()
        X = X[valid_mask]
        y = y[valid_mask]

        if len(X) < 50:
            print(f"  Skipping {property_type}: insufficient data after cleaning ({len(X)} records)")
            continue

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

        # Extract school coefficients
        school_coefs = {}
        for feature in available_features:
            if 'school' in feature.lower():
                idx = available_features.index(feature)
                coef = ols_model.coef_[idx]
                school_coefs[f'{feature}_coef'] = coef
                print(f"    {feature}: {coef:.4f}")

        print(f"    R²: {ols_r2:.4f}")
        print(f"    MAE: {ols_mae:.2f}")

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
            'xgb_r2': xgb_r2,
            'xgb_mae': xgb_mae,
            'importance': importance,
            'features': available_features,
            **school_coefs
        }

    return results


def compare_property_types(results):
    """Compare school impact across property types."""

    print(f"\n{'='*80}")
    print("CROSS-PROPERTY-TYPE COMPARISON")
    print(f"{'='*80}")

    # Create comparison DataFrame
    comparison_data = []

    for pt, data in results.items():
        row = {
            'property_type': pt,
            'n': data['n'],
            'mean_price': data['mean_price']
        }

        # Add school coefficients
        for key, value in data.items():
            if key.endswith('_coef'):
                feature_name = key.replace('_coef', '')
                row[feature_name] = value

        row['ols_r2'] = data['ols_r2']
        row['xgb_r2'] = data['xgb_r2']
        row['ols_mae'] = data['ols_mae']
        row['xgb_mae'] = data['xgb_mae']

        comparison_data.append(row)

    comparison_df = pd.DataFrame(comparison_data)

    print("\nModel Performance Comparison:")
    print(comparison_df[['property_type', 'ols_r2', 'xgb_r2']].to_string(index=False))

    # Print key school coefficients
    school_coef_cols = [col for col in comparison_df.columns if 'school' in col and '_coef' not in col]
    if school_coef_cols:
        print("\nSchool Feature Coefficients by Property Type:")
        for col in school_coef_cols:
            print(f"\n  {col}:")
            for _, row in comparison_df.iterrows():
                if pd.notna(row[col]):
                    print(f"    {row['property_type']}: {row[col]:.4f}")

    return comparison_df


def visualize_comparison(results, comparison_df):
    """Create comparison visualizations."""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Mean Price Comparison
    ax = axes[0, 0]
    colors = ['steelblue', 'coral', 'forestgreen']
    ax.bar(comparison_df['property_type'], comparison_df['mean_price'], color=colors)
    ax.set_ylabel('Mean Price ($ PSF)')
    ax.set_title('Price Level by Property Type', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    # 2. Model Performance (R²)
    ax = axes[0, 1]
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

    # 3. School Accessibility Score Coefficient Comparison
    ax = axes[1, 0]
    if 'school_accessibility_score' in comparison_df.columns:
        colors = ['green' if x > 0 else 'red' for x in comparison_df['school_accessibility_score']]
        ax.bar(comparison_df['property_type'], comparison_df['school_accessibility_score'], color=colors)
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
        ax.set_ylabel('Coefficient Value')
        ax.set_title('School Accessibility Impact by Property Type', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
    else:
        ax.text(0.5, 0.5, 'School accessibility score not available',
                ha='center', va='center', transform=ax.transAxes)

    # 4. Feature Importance Comparison (top 5)
    ax = axes[1, 1]

    # Get top 5 features across all types
    all_importance = pd.concat([
        results[pt]['importance'].head(5).copy()
        for pt in results.keys()
    ])

    # Add property type column
    importance_lists = []
    for pt in results.keys():
        imp = results[pt]['importance'].head(5).copy()
        imp['property_type'] = pt
        importance_lists.append(imp)

    all_importance = pd.concat(importance_lists)

    # Pivot for heatmap
    if len(all_importance) > 0:
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
    """Run model with property_type × school_feature interactions."""

    print(f"\n{'='*80}")
    print("INTERACTION MODEL: property_type × school_features")
    print(f"{'='*80}")

    # Prepare data
    subset = df.dropna(subset=[target_col]).copy()

    # Create property type dummies
    subset['is_condo'] = (subset['property_type'] == 'Condominium').astype(int)
    subset['is_ec'] = (subset['property_type'] == 'EC').astype(int)

    # Select key school feature for interaction
    interaction_feature = 'school_accessibility_score'

    if interaction_feature not in subset.columns:
        print(f"  {interaction_feature} not available, skipping interaction model")
        return None

    # Drop rows with missing school feature
    subset = subset.dropna(subset=[interaction_feature])

    # Interaction terms
    subset['school_x_condo'] = subset[interaction_feature] * subset['is_condo']
    subset['school_x_ec'] = subset[interaction_feature] * subset['is_ec']

    feature_cols = [
        interaction_feature,
        'is_condo',
        'is_ec',
        'school_x_condo',
        'school_x_ec',
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

    if len(X) < 100:
        print("  Insufficient data for interaction model")
        return None

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
    baseline_coef = coefs.loc[coefs['feature'] == interaction_feature, 'coefficient'].values
    if len(baseline_coef) > 0:
        print(f"  Baseline (HDB): School coefficient = ${baseline_coef[0]:.4f} PSF/score point")

        if 'school_x_condo' in coefs['feature'].values:
            condo_interaction = coefs.loc[coefs['feature'] == 'school_x_condo', 'coefficient'].values[0]
            condo_effect = baseline_coef[0] + condo_interaction
            print(f"  Condo: School coefficient = ${condo_effect:.4f} PSF/score point")
            print(f"    (baseline + interaction = ${baseline_coef[0]:.4f} + ${condo_interaction:.4f})")

        if 'school_x_ec' in coefs['feature'].values:
            ec_interaction = coefs.loc[coefs['feature'] == 'school_x_ec', 'coefficient'].values[0]
            ec_effect = baseline_coef[0] + ec_interaction
            print(f"  EC: School coefficient = ${ec_effect:.4f} PSF/score point")
            print(f"    (baseline + interaction = ${baseline_coef[0]:.4f} + ${ec_interaction:.4f})")

    return coefs


def main():
    """Main analysis pipeline."""

    # Load data
    df = load_data()

    # Check school feature coverage
    hdb_school_coverage = df[df['property_type'] == 'HDB']['school_accessibility_score'].notna().sum() if 'school_accessibility_score' in df.columns else 0
    condo_school_coverage = df[df['property_type'] == 'Condominium']['school_accessibility_score'].notna().sum() if 'school_accessibility_score' in df.columns else 0

    if hdb_school_coverage == 0 and condo_school_coverage == 0:
        print("\n" + "="*80)
        print("⚠️  WARNING: School feature data missing!")
        print("="*80)
        print("\nPlease ensure school features have been calculated in L3_export.py")
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
    if interaction_coefs is not None:
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
        print(f"    Mean Price: ${row['mean_price']:.2f} PSF")
        if 'school_accessibility_score' in row and pd.notna(row['school_accessibility_score']):
            print(f"    School Accessibility Coefficient: ${row['school_accessibility_score']:.4f} per score point")


if __name__ == "__main__":
    main()
