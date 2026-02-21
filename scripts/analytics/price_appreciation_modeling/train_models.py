"""Model training for price appreciation analysis.

Trains multiple regression models and compares performance:
1. Ordinary Least Squares (OLS) - baseline interpretability
2. Ridge, Lasso, ElasticNet - regularized models
3. XGBoost - tree-based non-linear model
4. Stacking ensemble - combines all models

Outputs:
- Trained models (.pkl files)
- Model comparison table (performance metrics)
- Feature importance analysis

Usage:
    uv run python scripts/analytics/price_appreciation_modeling/train_models.py
"""  # noqa: N999

import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import StackingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.core.config import Config

# Configure logging
logger = logging.getLogger(__name__)


def load_prepared_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load train and test datasets.

    Returns:
        train_df, test_df
    """
    logger.info("Loading prepared datasets...")

    train_path = Config.DATA_DIR / "pipeline" / "L5_price_appreciation_train.parquet"
    test_path = Config.DATA_DIR / "pipeline" / "L5_price_appreciation_test.parquet"

    if not train_path.exists():
        logger.error(f"Train dataset not found at {train_path}")
        return pd.DataFrame(), pd.DataFrame()

    if not test_path.exists():
        logger.error(f"Test dataset not found at {test_path}")
        return pd.DataFrame(), pd.DataFrame()

    train_df = pd.read_parquet(train_path)
    test_df = pd.read_parquet(test_path)

    logger.info(f"  Loaded {len(train_df):,} train records")
    logger.info(f"  Loaded {len(test_df):,} test records")

    return train_df, test_df


def prepare_features(
    df: pd.DataFrame, target_col: str = "yoy_change_pct"
) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """Prepare features for modeling.

    Args:
        df: DataFrame with all features
        target_col: Target variable name

    Returns:
        X (features), y (target), feature_names
    """
    logger.info("Preparing features for modeling...")

    if target_col not in df.columns:
        logger.error(f"Target column '{target_col}' not found")
        return pd.DataFrame(), pd.Series(), []

    # Drop rows with missing target
    df = df.dropna(subset=[target_col]).copy()

    # Select ONLY numeric columns for features
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # Drop target from features
    if target_col in numeric_cols:
        numeric_cols.remove(target_col)

    logger.info(f"  Found {len(numeric_cols)} numeric features")

    # Handle missing values in features
    X = df[numeric_cols].copy()
    y = df[target_col].copy()

    # Fill missing values with median
    for col in X.columns:
        if X[col].isna().sum() > 0:
            median_val = X[col].median()
            X[col] = X[col].fillna(median_val)
            logger.info(f"    Filled {X[col].isna().sum():,} missing values in '{col}' with median {median_val:.2f}")

    # Drop columns with too many missing values (>50%)
    missing_pct = X.isna().sum() / len(X) * 100
    drop_cols = missing_pct[missing_pct > 50].index.tolist()
    if drop_cols:
        X = X.drop(columns=drop_cols)
        logger.warning(f"    Dropped {len(drop_cols)} columns with >50% missing: {drop_cols[:5]}")

    # Final feature list
    feature_names = X.columns.tolist()
    logger.info(f"  Using {len(feature_names)} features for modeling")

    return X, y, feature_names


def train_ols(
    X_train: pd.DataFrame, y_train: pd.Series, X_test: pd.DataFrame, y_test: pd.Series
) -> dict:
    """Train Ordinary Least Squares model.

    Returns:
        Dictionary with model and predictions
    """
    logger.info("Training OLS model...")

    model = LinearRegression(n_jobs=-1)
    model.fit(X_train, y_train)

    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    r2_train = r2_score(y_train, y_pred_train)
    r2_test = r2_score(y_test, y_pred_test)
    mae_test = mean_absolute_error(y_test, y_pred_test)
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))

    # Directional accuracy
    direction_test = np.mean(np.sign(y_pred_test) == np.sign(y_test)) * 100

    logger.info(f"  Train R²: {r2_train:.4f}")
    logger.info(f"  Test R²: {r2_test:.4f}")
    logger.info(f"  Test MAE: {mae_test:.2f}")
    logger.info(f"  Test RMSE: {rmse_test:.2f}")
    logger.info(f"  Directional Accuracy: {direction_test:.1f}%")

    return {
        "model": model,
        "name": "OLS",
        "y_pred_test": y_pred_test,
        "residuals_test": y_test - y_pred_test,
        "r2_train": r2_train,
        "r2_test": r2_test,
        "mae_test": mae_test,
        "rmse_test": rmse_test,
        "direction_test": direction_test,
    }


def train_ridge(
    X_train: pd.DataFrame, y_train: pd.Series, X_test: pd.DataFrame, y_test: pd.Series
) -> dict:
    """Train Ridge regression model.

    Returns:
        Dictionary with model and predictions
    """
    logger.info("Training Ridge model...")

    # Use reasonable alpha
    model = Ridge(alpha=1.0, random_state=42, max_iter=1000)
    model.fit(X_train, y_train)

    y_pred_test = model.predict(X_test)

    r2_test = r2_score(y_test, y_pred_test)
    mae_test = mean_absolute_error(y_test, y_pred_test)
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))

    logger.info(f"  Test R²: {r2_test:.4f}")
    logger.info(f"  Test MAE: {mae_test:.2f}")
    logger.info(f"  Test RMSE: {rmse_test:.2f}")

    return {
        "model": model,
        "name": "Ridge",
        "y_pred_test": y_pred_test,
        "r2_test": r2_test,
        "mae_test": mae_test,
        "rmse_test": rmse_test,
    }


def train_lasso(
    X_train: pd.DataFrame, y_train: pd.Series, X_test: pd.DataFrame, y_test: pd.Series
) -> dict:
    """Train Lasso regression model.

    Returns:
        Dictionary with model and predictions
    """
    logger.info("Training Lasso model...")

    model = Lasso(alpha=0.1, random_state=42, max_iter=1000)
    model.fit(X_train, y_train)

    y_pred_test = model.predict(X_test)

    r2_test = r2_score(y_test, y_pred_test)
    mae_test = mean_absolute_error(y_test, y_pred_test)
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))

    logger.info(f"  Test R²: {r2_test:.4f}")
    logger.info(f"  Test MAE: {mae_test:.2f}")
    logger.info(f"  Test RMSE: {rmse_test:.2f}")

    return {
        "model": model,
        "name": "Lasso",
        "y_pred_test": y_pred_test,
        "r2_test": r2_test,
        "mae_test": mae_test,
        "rmse_test": rmse_test,
    }


def train_xgboost(
    X_train: pd.DataFrame, y_train: pd.Series, X_test: pd.DataFrame, y_test: pd.Series
) -> dict:
    """Train XGBoost regression model.

    Returns:
        Dictionary with model and predictions
    """
    logger.info("Training XGBoost model...")

    model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=20,
    )

    # Use validation set for early stopping
    eval_ratio = 0.2
    eval_size = int(len(X_train) * eval_ratio)

    model.fit(
        X_train.iloc[:-eval_size],
        y_train.iloc[:-eval_size],
        eval_set=[(X_train.iloc[-eval_size:], y_train.iloc[-eval_size:])],
        verbose=False,
    )

    y_pred_test = model.predict(X_test)

    r2_test = r2_score(y_test, y_pred_test)
    mae_test = mean_absolute_error(y_test, y_pred_test)
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
    direction_test = np.mean(np.sign(y_pred_test) == np.sign(y_test)) * 100

    logger.info(f"  Test R²: {r2_test:.4f}")
    logger.info(f"  Test MAE: {mae_test:.2f}")
    logger.info(f"  Test RMSE: {rmse_test:.2f}")
    logger.info(f"  Directional Accuracy: {direction_test:.1f}%")

    return {
        "model": model,
        "name": "XGBoost",
        "y_pred_test": y_pred_test,
        "residuals_test": y_test - y_pred_test,
        "r2_test": r2_test,
        "mae_test": mae_test,
        "rmse_test": rmse_test,
        "direction_test": direction_test,
    }


def train_stacking_ensemble(
    results: list[dict], X_train: pd.DataFrame, y_train: pd.Series,
    X_test: pd.DataFrame, y_test: pd.Series,
) -> dict:
    """Train stacking ensemble model.

    Args:
        results: List of model result dictionaries
        X_train, y_train: Training data
        X_test, y_test: Test data

    Returns:
        Dictionary with ensemble model and predictions
    """
    logger.info("Training Stacking Ensemble...")

    # Extract base models
    base_models = [(r["name"], r["model"]) for r in results if "model" in r]

    # Meta-model (Ridge for simplicity)
    meta_model = Ridge(alpha=1.0, random_state=42)

    # Create stacking ensemble
    ensemble = StackingRegressor(
        estimators=base_models,
        final_estimator=meta_model,
        cv=5,
        n_jobs=-1,
    )

    ensemble.fit(X_train, y_train)

    y_pred_test = ensemble.predict(X_test)

    r2_test = r2_score(y_test, y_pred_test)
    mae_test = mean_absolute_error(y_test, y_pred_test)
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
    direction_test = np.mean(np.sign(y_pred_test) == np.sign(y_test)) * 100

    logger.info(f"  Test R²: {r2_test:.4f}")
    logger.info(f"  Test MAE: {mae_test:.2f}")
    logger.info(f"  Test RMSE: {rmse_test:.2f}")
    logger.info(f"  Directional Accuracy: {direction_test:.1f}%")

    return {
        "model": ensemble,
        "name": "Stacking",
        "y_pred_test": y_pred_test,
        "r2_test": r2_test,
        "mae_test": mae_test,
        "rmse_test": rmse_test,
        "direction_test": direction_test,
    }


def save_models(results: list[dict], output_dir: Path) -> None:
    """Save trained models to disk.

    Args:
        results: List of model result dictionaries
        output_dir: Output directory path
    """
    logger.info("Saving trained models...")

    output_dir.mkdir(parents=True, exist_ok=True)

    for result in results:
        if "model" not in result:
            continue

        model_path = output_dir / f"{result['name']}_model.pkl"
        joblib.dump(result["model"], model_path)
        logger.info(f"  Saved {result['name']} model to {model_path}")


def calculate_feature_importance(
    results: list[dict], X_test: pd.DataFrame, y_test: pd.Series,
) -> pd.DataFrame:
    """Calculate feature importance using permutation importance.

    Args:
        results: List of model result dictionaries
        X_test: Test features
        y_test: Test target

    Returns:
        DataFrame with feature importance rankings
    """
    logger.info("Calculating feature importance...")

    importance_dfs = []

    for result in results:
        if "model" not in result or "residuals_test" not in result:
            continue

        try:
            perm_importance = permutation_importance(
                result["model"],
                X_test,
                y_test,
                n_repeats=10,
                random_state=42,
                scoring="r2",
                n_jobs=-1,
            )

            imp_df = pd.DataFrame({
                "feature": X_test.columns,
                "importance": perm_importance.importances_mean,
                "std": perm_importance.importances_std,
            }).sort_values("importance", ascending=False)

            imp_df["model"] = result["name"]
            importance_dfs.append(imp_df)

            logger.info(f"  {result['name']}: Top feature = {imp_df.iloc[0]['feature']}")

        except Exception as e:
            logger.warning(f"  Could not calculate importance for {result['name']}: {e}")

    if not importance_dfs:
        return pd.DataFrame()

    combined_importance = pd.concat(importance_dfs, ignore_index=True)
    top_features = combined_importance.groupby("feature")["importance"].max().sort_values(ascending=False).head(20)

    return top_features


def create_comparison_table(results: list[dict]) -> pd.DataFrame:
    """Create model comparison table.

    Args:
        results: List of model result dictionaries

    Returns:
        DataFrame with comparison metrics
    """
    logger.info("Creating model comparison table...")

    comparison_data = []

    for result in results:
        row = {
            "Model": result["name"],
            "R² (Train)": result.get("r2_train", np.nan),
            "R² (Test)": result["r2_test"],
            "MAE (Test)": result["mae_test"],
            "RMSE (Test)": result["rmse_test"],
        }

        if "direction_test" in result:
            row["Directional Acc (%)"] = result["direction_test"]

        comparison_data.append(row)

    comparison_df = pd.DataFrame(comparison_data)

    # Sort by R² (Test)
    comparison_df = comparison_df.sort_values("R² (Test)", ascending=False)

    return comparison_df


def main():
    """Run model training pipeline."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logger.info("=" * 60)
    logger.info("Price Appreciation Modeling: Model Training")
    logger.info("=" * 60)

    # 1. Load data
    logger.info("\n[1/5] Loading prepared datasets...")
    train_df, test_df = load_prepared_data()

    if train_df.empty or test_df.empty:
        logger.error("No data available for modeling")
        return

    # 2. Prepare features
    logger.info("\n[2/5] Preparing features...")
    X_train, y_train, feature_names = prepare_features(train_df)
    X_test, y_test, _ = prepare_features(test_df)

    logger.info(f"  Train set: {len(X_train):,} records × {len(X_train.columns)} features")
    logger.info(f"  Test set: {len(X_test):,} records × {len(X_test.columns)} features")

    # 3. Train models
    logger.info("\n[3/5] Training models...")

    results = []

    # OLS
    try:
        result_ols = train_ols(X_train, y_train, X_test, y_test)
        results.append(result_ols)
    except Exception as e:
        logger.error(f"OLS training failed: {e}")

    # Ridge
    try:
        result_ridge = train_ridge(X_train, y_train, X_test, y_test)
        results.append(result_ridge)
    except Exception as e:
        logger.error(f"Ridge training failed: {e}")

    # Lasso
    try:
        result_lasso = train_lasso(X_train, y_train, X_test, y_test)
        results.append(result_lasso)
    except Exception as e:
        logger.error(f"Lasso training failed: {e}")

    # XGBoost
    try:
        result_xgb = train_xgboost(X_train, y_train, X_test, y_test)
        results.append(result_xgb)
    except Exception as e:
        logger.error(f"XGBoost training failed: {e}")

    # 4. Stacking Ensemble
    logger.info("\n[4/5] Training stacking ensemble...")
    try:
        result_stacking = train_stacking_ensemble(results, X_train, y_train, X_test, y_test)
        results.append(result_stacking)
    except Exception as e:
        logger.error(f"Stacking training failed: {e}")

    # 5. Feature importance
    logger.info("\n[5/5] Calculating feature importance...")
    feature_importance = calculate_feature_importance(results, X_test, y_test)

    if not feature_importance.empty:
        importance_path = Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "data" / "feature_importance.csv"
        importance_path.parent.mkdir(parents=True, exist_ok=True)
        feature_importance.to_csv(importance_path, index=False)
        logger.info(f"  Saved feature importance to {importance_path}")
    else:
        logger.warning("Feature importance calculation failed")

    # 6. Model comparison
    logger.info("\nCreating model comparison table...")
    comparison_df = create_comparison_table(results)

    comparison_path = Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "model_comparison.csv"
    comparison_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_df.to_csv(comparison_path, index=False)
    logger.info(f"  Saved model comparison to {comparison_path}")

    # 7. Save models
    logger.info("\nSaving trained models...")
    output_dir = Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "models"
    save_models(results, output_dir)

    # 8. Save predictions
    logger.info("\nSaving predictions...")
    predictions_path = Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "predictions" / "test_predictions.parquet"
    predictions_path.parent.mkdir(parents=True, exist_ok=True)

    # Combine all predictions
    all_predictions = pd.DataFrame({
        "actual": y_test,
    })

    for result in results:
        if "y_pred_test" in result:
            all_predictions[f"{result['name']}_predicted"] = result["y_pred_test"]
        if "residuals_test" in result:
            all_predictions[f"{result['name']}_residual"] = result["residuals_test"]

    all_predictions.to_parquet(predictions_path, compression="snappy", index=False)
    logger.info(f"  Saved predictions to {predictions_path}")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Model Training Complete!")
    logger.info("=" * 60)

    # Print comparison table
    print("\nModel Comparison:")
    print(comparison_df.to_string(index=False))

    # Best model
    best_model = comparison_df.iloc[0]
    print(f"\nBest Model: {best_model['Model']} (R² = {best_model['R² (Test)']:.4f})")

    # Top features
    if not feature_importance.empty:
        print("\nTop 10 Features (by importance):")
        print(feature_importance.head(10)[["feature", "importance"]].to_string(index=False))

    logger.info(f"\nTotal records processed: {len(X_train) + len(X_test):,}")
    logger.info(f"Models trained: {len(results)}")
    logger.info(f"Features used: {len(X_train.columns)}")


if __name__ == "__main__":
    main()
