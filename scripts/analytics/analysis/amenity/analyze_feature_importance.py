"""
Feature Importance Analysis for Singapore Housing Market

Analyzes which features drive:
1. Transaction prices (price_psf)
2. Rental yields (rental_yield_pct)
3. Appreciation rates (mom_change_pct, yoy_change_pct)

Uses multiple modeling approaches:
- Linear regression (baseline interpretability)
- Tree-based models (non-linear relationships)
- Panel regression (time-series appreciation)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.impute import SimpleImputer

import xgboost as xgb
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("SHAP not available - will skip SHAP analysis")

import matplotlib.pyplot as plt
import seaborn as sns

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Paths
DATA_DIR = Path("data/analysis/market_segmentation")
OUTPUT_DIR = Path("data/analysis/feature_importance")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_data():
    """Load the unified housing dataset."""
    print("Loading dataset...")
    df = pd.read_parquet(DATA_DIR / "housing_unified_segmented.parquet")
    print(f"Loaded {len(df):,} records with {df.shape[1]} features")
    return df


def prepare_features(df, target_col='price_psf'):
    """
    Prepare features for modeling.

    Strategy:
    - Drop columns with >80% missing
    - Keep amenity distance features (impute with median)
    - Encode categoricals (one-hot for low cardinality)
    - Create temporal features
    """
    print(f"\nPreparing features for target: {target_col}")

    df_prep = df.copy()

    # Drop columns with excessive missingness
    high_missing = [
        'Project Name', 'Street Name', 'Postal District',
        'Property Type', 'Market Segment'
    ]
    df_prep = df_prep.drop(columns=high_missing, errors='ignore')

    # For rental/appreciation targets, drop rows with missing target
    if target_col in ['rental_yield_pct', 'mom_change_pct', 'yoy_change_pct']:
        df_prep = df_prep.dropna(subset=[target_col])
        print(f"Dropped rows with missing {target_col}: {len(df_prep):,} remaining")

    # Select feature columns
    # Location features
    location_cols = [
        'dist_to_nearest_mrt', 'dist_to_nearest_hawker',
        'dist_to_nearest_supermarket', 'dist_to_nearest_park',
        'dist_to_nearest_preschool', 'dist_to_nearest_childcare',
        'mrt_within_500m', 'mrt_within_1km', 'mrt_within_2km',
        'hawker_within_500m', 'hawker_within_1km', 'hawker_within_2km',
        'supermarket_within_500m', 'supermarket_within_1km', 'supermarket_within_2km',
        'park_within_500m', 'park_within_1km', 'park_within_2km',
        'preschool_within_500m', 'preschool_within_1km', 'preschool_within_2km',
        'childcare_within_500m', 'childcare_within_1km', 'childcare_within_2km'
    ]

    # Property features (numeric only)
    property_cols = [
        'floor_area_sqm', 'remaining_lease_months'
    ]

    # Market features (numeric only)
    market_cols = [
        'transaction_count', 'volume_3m_avg', 'volume_12m_avg',
        'stratified_median_price'
    ]

    # Temporal features
    temporal_cols = ['year', 'month']

    # Categorical columns for encoding
    categorical_cols = ['town', 'flat_type', 'flat_model', 'storey_range',
                       'market_tier', 'psf_tier', 'property_type', 'momentum_signal']

    # Build feature list
    feature_cols = []
    for col_list in [location_cols, property_cols, market_cols, temporal_cols]:
        feature_cols.extend([c for c in col_list if c in df_prep.columns])

    # Add categoricals (excluding those already added)
    for col in categorical_cols:
        if col in df_prep.columns and col not in feature_cols:
            feature_cols.append(col)

    # Remove target and non-feature columns
    exclude_cols = ['price', 'price_psm', 'price_psf', 'rental_yield_pct',
                   'mom_change_pct', 'yoy_change_pct', 'transaction_date',
                   'month', 'planning_area', 'address', 'lat', 'lon',
                   'lease_commence_date']

    feature_cols = [c for c in feature_cols if c not in exclude_cols]

    print(f"Selected {len(feature_cols)} features")

    # Separate numeric and categorical
    numeric_features = df_prep[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
    categorical_features = df_prep[feature_cols].select_dtypes(include=['object', 'category']).columns.tolist()

    # Limit high-cardinality categoricals (top N most frequent)
    def limit_categoricals(df, col, top_n=20):
        """Limit categorical to top N values, group rest as 'Other'."""
        if col not in df.columns:
            return df
        top_values = df[col].value_counts().head(top_n).index
        df[col] = df[col].where(df[col].isin(top_values), 'Other')
        return df

    for col in ['town', 'flat_model']:
        if col in df_prep.columns:
            df_prep = limit_categoricals(df_prep, col, top_n=20)

    print(f"  Numeric features: {len(numeric_features)}")
    print(f"  Categorical features: {len(categorical_features)}")

    return df_prep, numeric_features, categorical_features, feature_cols


def create_model_pipeline(model_type='linear', numeric_features=[], categorical_features=[]):
    """Create a scikit-learn pipeline with preprocessing."""

    # Preprocessing
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)
        ]
    )

    # Model
    if model_type == 'linear':
        model = LinearRegression()
    elif model_type == 'ridge':
        model = Ridge(alpha=1.0)
    elif model_type == 'lasso':
        model = Lasso(alpha=0.1, max_iter=10000)
    elif model_type == 'elasticnet':
        model = ElasticNet(alpha=0.1, l1_ratio=0.5, max_iter=10000)
    elif model_type == 'random_forest':
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=10,
            n_jobs=-1,
            random_state=42
        )
    elif model_type == 'xgboost':
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            n_jobs=-1,
            random_state=42
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('model', model)
    ])

    return pipeline


def train_and_evaluate(X_train, X_test, y_train, y_test, pipeline, model_name):
    """Train model and evaluate performance."""

    print(f"\nTraining {model_name}...")

    # Train
    pipeline.fit(X_train, y_train)

    # Predict
    y_train_pred = pipeline.predict(X_train)
    y_test_pred = pipeline.predict(X_test)

    # Metrics
    metrics = {
        'model': model_name,
        'train_r2': r2_score(y_train, y_train_pred),
        'test_r2': r2_score(y_test, y_test_pred),
        'train_mae': mean_absolute_error(y_train, y_train_pred),
        'test_mae': mean_absolute_error(y_test, y_test_pred),
        'train_rmse': np.sqrt(mean_squared_error(y_train, y_train_pred)),
        'test_rmse': np.sqrt(mean_squared_error(y_test, y_test_pred))
    }

    print(f"  Train R²: {metrics['train_r2']:.4f}")
    print(f"  Test R²: {metrics['test_r2']:.4f}")
    print(f"  Test MAE: {metrics['test_mae']:.2f}")
    print(f"  Test RMSE: {metrics['test_rmse']:.2f}")

    return pipeline, metrics


def extract_feature_importance(pipeline, model_type, feature_names):
    """Extract feature importance from trained model."""

    if model_type in ['linear', 'ridge', 'lasso', 'elasticnet']:
        # Coefficients
        importances = pipeline.named_steps['model'].coef_
    elif model_type == 'random_forest':
        importances = pipeline.named_steps['model'].feature_importances_
    elif model_type == 'xgboost':
        importances = pipeline.named_steps['model'].feature_importances_
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    # Create DataFrame
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': np.abs(importances) if model_type in ['linear', 'ridge', 'lasso', 'elasticnet'] else importances
    }).sort_values('importance', ascending=False)

    return importance_df


def analyze_shap_values(pipeline, X_train, feature_names, model_name='XGBoost'):
    """Calculate SHAP values for detailed interpretation."""

    print(f"\nCalculating SHAP values for {model_name}...")

    # Get preprocessed data
    preprocessor = pipeline.named_steps['preprocessor']
    X_train_processed = preprocessor.transform(X_train)

    # Get feature names after preprocessing
    ohe_feature_names = preprocessor.named_transformers_['cat'].named_steps['onehot'].get_feature_names_out()
    numeric_feature_names = preprocessor.named_transformers_['num'].named_steps['scaler'].feature_names_in_

    all_feature_names = list(numeric_feature_names) + list(ohe_feature_names)

    # Calculate SHAP
    model = pipeline.named_steps['model']

    if model_name == 'XGBoost':
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_train_processed)
    else:
        explainer = shap.LinearExplainer(model, X_train_processed)
        shap_values = explainer.shap_values(X_train_processed)

    # Mean absolute SHAP values
    mean_shap = np.abs(shap_values).mean(axis=0)

    shap_df = pd.DataFrame({
        'feature': all_feature_names,
        'shap_value': mean_shap
    }).sort_values('shap_value', ascending=False)

    print(f"  Top 10 features by SHAP value:")
    print(shap_df.head(10).to_string(index=False))

    return shap_df, explainer, shap_values, X_train_processed, all_feature_names


def main():
    """Main analysis pipeline."""

    print("="*80)
    print("FEATURE IMPORTANCE ANALYSIS - SINGAPORE HOUSING MARKET")
    print("="*80)

    # Configuration
    USE_TEMPORAL_SPLIT = False  # Set True for temporal split (pre-2020 vs 2020+), False for random 80/20 split
    EXTRACT_FEATURE_IMPORTANCE = True  # Extract and save feature importance from best model

    print(f"\nConfiguration:")
    print(f"  Split Method: {'Temporal (pre-2020 vs 2020+)' if USE_TEMPORAL_SPLIT else 'Random (80/20)'}")
    print(f"  Extract Feature Importance: {EXTRACT_FEATURE_IMPORTANCE}")

    # Load data
    df = load_data()

    # Define targets
    targets = {
        'price_psf': 'Transaction Price (PSF)',
        'rental_yield_pct': 'Rental Yield (%)',
        'yoy_change_pct': 'Year-over-Year Appreciation (%)'
    }

    all_results = []

    for target_col, target_name in targets.items():
        print(f"\n{'='*80}")
        print(f"ANALYZING: {target_name}")
        print(f"{'='*80}")

        # Prepare features
        df_prep, numeric_features, categorical_features, feature_cols = prepare_features(df, target_col)

        # Prepare data
        X = df_prep[feature_cols]
        y = df_prep[target_col]

        # Remove rows with missing target
        mask = ~y.isna()
        X = X[mask]
        y = y[mask]

        print(f"\nFinal dataset: {len(X):,} records")

        # Train/test split
        if USE_TEMPORAL_SPLIT and 'year' in X.columns:
            # Temporal split: pre-2020 for train, 2020+ for test
            X_train = X[X['year'] < 2020].drop(columns=['year'], errors='ignore')
            X_test = X[X['year'] >= 2020].drop(columns=['year'], errors='ignore')
            y_train = y[X['year'] < 2020]
            y_test = y[X['year'] >= 2020]

            print(f"Train set (pre-2020): {len(X_train):,} records")
            print(f"Test set (2020+): {len(X_test):,} records")
        else:
            # Random split: 80/20
            X_train, X_test, y_train, y_test = train_test_split(
                X.drop(columns=['year'], errors='ignore'),
                y,
                test_size=0.2,
                random_state=42
            )
            print(f"Train set (80%): {len(X_train):,} records")
            print(f"Test set (20%): {len(X_test):,} records")

        # Re-create feature lists without 'year'
        numeric_features_clean = [f for f in numeric_features if f != 'year']

        # Test different models
        models_to_test = [
            ('linear', 'Linear Regression'),
            ('ridge', 'Ridge Regression'),
            ('xgboost', 'XGBoost'),
            ('random_forest', 'Random Forest')
        ]

        target_results = {}

        for model_type, model_display_name in models_to_test:
            try:
                # Create pipeline
                pipeline = create_model_pipeline(
                    model_type=model_type,
                    numeric_features=numeric_features_clean,
                    categorical_features=categorical_features
                )

                # Train and evaluate
                pipeline, metrics = train_and_evaluate(
                    X_train, X_test, y_train, y_test,
                    pipeline, model_display_name
                )

                metrics['target'] = target_col
                metrics['target_name'] = target_name
                all_results.append(metrics)
                target_results[model_type] = {
                    'pipeline': pipeline,
                    'metrics': metrics
                }

            except Exception as e:
                print(f"  ERROR: {e}")
                continue

        # SHAP analysis for best model (XGBoost)
        if 'xgboost' in target_results and SHAP_AVAILABLE:
            try:
                shap_df, explainer, shap_values, X_processed, feature_names = analyze_shap_values(
                    target_results['xgboost']['pipeline'],
                    X_train,
                    feature_cols,
                    'XGBoost'
                )

                # Save SHAP results
                shap_df['target'] = target_col
                shap_path = OUTPUT_DIR / f"shap_{target_col}.csv"
                shap_df.to_csv(shap_path, index=False)
                print(f"  Saved SHAP values to {shap_path}")

            except Exception as e:
                print(f"  SHAP ERROR: {e}")
        elif 'xgboost' in target_results and not SHAP_AVAILABLE:
            print(f"  Skipping SHAP analysis (SHAP not installed)")

        # Feature importance extraction
        if EXTRACT_FEATURE_IMPORTANCE:
            print(f"\nExtracting feature importance...")

            # Extract from Random Forest
            if 'random_forest' in target_results:
                try:
                    rf_pipeline = target_results['random_forest']['pipeline']
                    rf_model = rf_pipeline.named_steps['model']

                    # Get feature names after preprocessing
                    preprocessor = rf_pipeline.named_steps['preprocessor']

                    # Get categorical feature names from one-hot encoder
                    ohe = preprocessor.named_transformers_['cat'].named_steps['onehot']
                    ohe_feature_names = ohe.get_feature_names_out(categorical_features).tolist()

                    # Numeric feature names (use the original list)
                    numeric_feature_names = numeric_features_clean

                    all_feature_names = numeric_feature_names + ohe_feature_names

                    # Get feature importances
                    importances = rf_model.feature_importances_

                    # Create DataFrame
                    importance_df = pd.DataFrame({
                        'feature': all_feature_names,
                        'importance': importances
                    }).sort_values('importance', ascending=False)

                    # Save
                    importance_df['target'] = target_col
                    importance_df['model'] = 'random_forest'
                    importance_path = OUTPUT_DIR / f"feature_importance_{target_col}_random_forest.csv"
                    importance_df.to_csv(importance_path, index=False)
                    print(f"  Random Forest - Top 10 features:")
                    print(importance_df.head(10)[['feature', 'importance']].to_string(index=False))

                except Exception as e:
                    print(f"  RF Feature Importance ERROR: {e}")

            # Extract from XGBoost
            if 'xgboost' in target_results:
                try:
                    xgb_pipeline = target_results['xgboost']['pipeline']
                    xgb_model = xgb_pipeline.named_steps['model']

                    # Get feature names after preprocessing
                    preprocessor = xgb_pipeline.named_steps['preprocessor']

                    # Get categorical feature names from one-hot encoder
                    ohe = preprocessor.named_transformers_['cat'].named_steps['onehot']
                    ohe_feature_names = ohe.get_feature_names_out(categorical_features).tolist()

                    # Numeric feature names (use the original list)
                    numeric_feature_names = numeric_features_clean

                    all_feature_names = numeric_feature_names + ohe_feature_names

                    # Get feature importances (gain)
                    importances = xgb_model.feature_importances_

                    # Create DataFrame
                    importance_df = pd.DataFrame({
                        'feature': all_feature_names,
                        'importance': importances
                    }).sort_values('importance', ascending=False)

                    # Save
                    importance_df['target'] = target_col
                    importance_df['model'] = 'xgboost'
                    importance_path = OUTPUT_DIR / f"feature_importance_{target_col}_xgboost.csv"
                    importance_df.to_csv(importance_path, index=False)
                    print(f"\n  XGBoost - Top 10 features:")
                    print(importance_df.head(10)[['feature', 'importance']].to_string(index=False))

                except Exception as e:
                    print(f"  XGBoost Feature Importance ERROR: {e}")

    # Compile results
    print(f"\n{'='*80}")
    print("COMPILING RESULTS")
    print(f"{'='*80}")

    results_df = pd.DataFrame(all_results)
    results_path = OUTPUT_DIR / "model_comparison.csv"
    results_df.to_csv(results_path, index=False)
    print(f"\nSaved model comparison to {results_path}")

    if len(results_df) > 0:
        print("\nModel Performance Summary:")
        print(results_df[['model', 'target_name', 'test_r2', 'test_mae', 'test_rmse']].to_string(index=False))
    else:
        print("\nNo models successfully trained.")

    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"\nResults saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
