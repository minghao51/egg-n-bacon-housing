"""
School Impact Analysis on Singapore Housing Prices

Analyzes the impact of school proximity and quality on housing prices,
rental yields, and appreciation rates.

Analysis timeframe: 2021+ (recent data only)

Targets:
- price_psf: Transaction price per square foot
- rental_yield_pct: Rental yield percentage
- yoy_change_pct: Year-over-year appreciation rate

School Features:
- Distance: school_within_500m/1km/2km
- Accessibility: school_accessibility_score
- Primary schools: school_primary_dist_score, school_primary_quality_score
- Secondary schools: school_secondary_dist_score, school_secondary_quality_score
- Density: school_density_score
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

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Paths
DATA_DIR = Path("data/pipeline/L3")
OUTPUT_DIR = Path("data/analysis/school_impact")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_and_prepare_data():
    """Load unified dataset and filter to 2021+."""
    print("="*80)
    print("SCHOOL IMPACT ANALYSIS - SINGAPORE HOUSING MARKET (2021+)")
    print("="*80)

    print("\nLoading data...")
    df = pd.read_parquet(DATA_DIR / "housing_unified.parquet")
    print(f"  Full dataset: {len(df):,} records")

    # Filter to 2021+
    df = df[df['year'] >= 2021].copy()
    print(f"  Filtered to 2021+: {len(df):,} records")

    # Check school feature coverage
    school_cols = [
        'school_within_1km',
        'school_accessibility_score',
        'school_primary_quality_score',
        'school_secondary_quality_score'
    ]

    print("\nSchool feature coverage:")
    for col in school_cols:
        if col in df.columns:
            coverage = df[col].notna().sum()
            pct = coverage / len(df) * 100
            print(f"  {col}: {coverage:,}/{len(df):,} ({pct:.1f}%)")
        else:
            print(f"  {col}: NOT FOUND")

    return df


def exploratory_analysis(df):
    """Explore relationships between school features and prices."""
    print("\n" + "="*80)
    print("EXPLORATORY ANALYSIS")
    print("="*80)

    # Create school quality bands
    if 'school_primary_quality_score' in df.columns:
        df['school_quality_band'] = pd.cut(
            df['school_primary_quality_score'],
            bins=[0, 0.33, 0.67, 1.0],
            labels=['Low Quality', 'Medium Quality', 'High Quality']
        )

    # Summary by school quality band
    if 'school_quality_band' in df.columns:
        print("\nPrice by School Quality Band:")
        band_stats = df.groupby('school_quality_band', observed=True).agg({
            'price_psf': ['mean', 'median', 'count'],
            'school_accessibility_score': 'mean'
        }).round(2)
        print(band_stats)

    # Correlation analysis
    print("\nCorrelation with School Features:")
    school_features = [
        'school_within_500m', 'school_within_1km', 'school_within_2km',
        'school_accessibility_score',
        'school_primary_dist_score', 'school_primary_quality_score',
        'school_secondary_dist_score', 'school_secondary_quality_score',
        'school_density_score'
    ]

    for target in ['price_psf', 'rental_yield_pct', 'yoy_change_pct']:
        if target in df.columns:
            print(f"\n  {target}:")
            for feature in school_features:
                if feature in df.columns:
                    valid_data = df[[target, feature]].dropna()
                    if len(valid_data) > 100:
                        corr = valid_data.corr().iloc[0, 1]
                        print(f"    {feature}: {corr:.3f}")

    # Visualizations
    print("\nCreating visualizations...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Price vs School Accessibility Score
    ax = axes[0, 0]
    if 'school_accessibility_score' in df.columns:
        sample = df.sample(n=min(10000, len(df)), random_state=42)
        ax.scatter(sample['school_accessibility_score'], sample['price_psf'],
                   alpha=0.3, s=1)
        ax.set_xlabel('School Accessibility Score')
        ax.set_ylabel('Price PSF ($)')
        ax.set_title('Price vs School Accessibility')
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'School accessibility data not available',
                ha='center', va='center', transform=ax.transAxes)

    # 2. Average price by school quality band
    ax = axes[0, 1]
    if 'school_quality_band' in df.columns:
        band_prices = df.groupby('school_quality_band', observed=True)['price_psf'].mean().sort_index()
        if not band_prices.empty:
            band_prices.plot(kind='bar', ax=ax, color=['lightcoral', 'gold', 'lightgreen'])
            ax.set_xlabel('School Quality Band')
            ax.set_ylabel('Average Price PSF ($)')
            ax.set_title('Average Price by School Quality')
            ax.tick_params(axis='x', rotation=45)
            ax.grid(True, alpha=0.3, axis='y')
        else:
            ax.text(0.5, 0.5, 'No data for quality bands',
                    ha='center', va='center', transform=ax.transAxes)
    else:
        ax.text(0.5, 0.5, 'School quality data not available',
                ha='center', va='center', transform=ax.transAxes)

    # 3. Distribution of school accessibility scores
    ax = axes[1, 0]
    if 'school_accessibility_score' in df.columns:
        ax.hist(df['school_accessibility_score'], bins=50, edgecolor='black', alpha=0.7)
        ax.axvline(df['school_accessibility_score'].median(), color='red', linestyle='--',
                   label=f"Median: {df['school_accessibility_score'].median():.2f}")
        ax.set_xlabel('School Accessibility Score')
        ax.set_ylabel('Frequency')
        ax.set_title('Distribution of School Accessibility Scores')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
    else:
        ax.text(0.5, 0.5, 'School accessibility data not available',
                ha='center', va='center', transform=ax.transAxes)

    # 4. Primary school quality vs Secondary school quality
    ax = axes[1, 1]
    if 'school_primary_quality_score' in df.columns and 'school_secondary_quality_score' in df.columns:
        sample = df.sample(n=min(10000, len(df)), random_state=42)
        scatter = ax.scatter(sample['school_primary_quality_score'],
                           sample['school_secondary_quality_score'],
                           c=sample['price_psf'], cmap='RdYlGn', alpha=0.3, s=1)
        ax.set_xlabel('Primary School Quality Score')
        ax.set_ylabel('Secondary School Quality Score')
        ax.set_title('Primary vs Secondary School Quality')
        plt.colorbar(scatter, ax=ax, label='Price PSF ($)')
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'School quality data not available',
                ha='center', va='center', transform=ax.transAxes)

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
        'floor_area_sqm',
        'remaining_lease_months',
        'year',
        'month'
    ]

    # School features
    school_feature_cols = [
        'school_within_500m',
        'school_within_1km',
        'school_within_2km',
        'school_accessibility_score',
        'school_primary_dist_score',
        'school_primary_quality_score',
        'school_secondary_dist_score',
        'school_secondary_quality_score',
        'school_density_score'
    ]

    # Add available school features
    for col in school_feature_cols:
        if col in df_model.columns:
            feature_cols.append(col)

    # Add amenity controls (if available)
    amenity_cols = [
        'dist_to_nearest_mrt',
        'dist_to_nearest_hawker',
        'dist_to_nearest_supermarket',
        'dist_to_nearest_park'
    ]

    for col in amenity_cols:
        if col in df_model.columns:
            feature_cols.append(col)

    # Select only available features
    feature_cols = [col for col in feature_cols if col in df_model.columns]

    # Drop rows with NaN in features
    df_model = df_model.dropna(subset=feature_cols)

    print(f"  Selected {len(feature_cols)} features")
    print(f"  Dataset size: {len(df_model):,} records")

    return df_model, feature_cols


def run_ols_regression(df, target_col='price_psf'):
    """Run OLS regression with different feature specifications."""
    print(f"\n{'='*80}")
    print(f"OLS REGRESSION: {target_col}")
    print(f"{'='*80}")

    df_model, base_features = prepare_features(df, target_col)

    results = []

    # Model 1: All school features
    X_all = df_model[base_features].select_dtypes(include=[np.number])
    y = df_model[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X_all, y, test_size=0.2, random_state=42
    )

    model = LinearRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    results.append({
        'specification': 'All Features',
        'r2': r2,
        'mae': mae,
        'model': model,
        'features': X_all.columns.tolist()
    })

    print(f"\nAll Features:")
    print(f"  R²: {r2:.4f}")
    print(f"  MAE: {mae:.2f}")

    # Extract key school coefficients
    school_coefs = []
    for feature in X_all.columns:
        if 'school' in feature.lower():
            idx = X_all.columns.get_loc(feature)
            coef = model.coef_[idx]
            school_coefs.append((feature, coef))
            print(f"  {feature}: {coef:.4f}")

    # Model 2: School quality scores only
    quality_features = [f for f in base_features if 'quality' in f.lower() or 'accessibility' in f.lower()]
    quality_features += [f for f in base_features if f in ['floor_area_sqm', 'year', 'remaining_lease_months']]

    if len(quality_features) > 3:
        X_quality = df_model[quality_features].select_dtypes(include=[np.number])

        X_train, X_test, y_train, y_test = train_test_split(
            X_quality, y, test_size=0.2, random_state=42
        )

        model = LinearRegression()
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)

        results.append({
            'specification': 'Quality Scores',
            'r2': r2,
            'mae': mae,
            'model': model,
            'features': X_quality.columns.tolist()
        })

        print(f"\nQuality Scores Only:")
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

        # Check if target exists and has sufficient data
        if target_col not in df.columns or df[target_col].notna().sum() < 1000:
            print(f"\n  Skipping {target_col}: insufficient data")
            continue

        # OLS models
        try:
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
        except Exception as e:
            print(f"  OLS regression failed: {e}")
            continue

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

    if summary_data:
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
