"""Train separate price appreciation models by property type.

Trains XGBoost models separately for HDB, Condo, and EC properties
to address heteroscedasticity and improve predictive performance.

Usage:
    uv run python scripts/analytics/price_appreciation_modeling/train_by_property_type.py
"""

import logging

# Add project root to path for imports
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.core.config import Config

# Configure logging
logger = logging.getLogger(__name__)


def load_data():
    """Load prepared training and test data."""
    logger.info("Loading data...")

    train_path = Config.DATA_DIR / "pipeline" / "L5_price_appreciation_train.parquet"
    test_path = Config.DATA_DIR / "pipeline" / "L5_price_appreciation_test.parquet"

    train_df = pd.read_parquet(train_path)
    test_df = pd.read_parquet(test_path)

    logger.info(f"  Train: {len(train_df):,} records")
    logger.info(f"  Test: {len(test_df):,} records")

    return train_df, test_df


def prepare_features(df: pd.DataFrame, target_col: str = "yoy_change_pct", max_missing_pct: float = 0.2):
    """Select and prepare features for modeling.

    Args:
        df: Input dataframe
        target_col: Target variable column name
        max_missing_pct: Maximum allowed missing percentage (default 20%)

    Returns:
        DataFrame with prepared features (missing values imputed)
    """
    # Select ONLY numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # Remove target from features
    if target_col in numeric_cols:
        numeric_cols.remove(target_col)

    # Remove identifier columns
    exclude_cols = ["year", "month", "latitude", "longitude"]
    numeric_cols = [col for col in numeric_cols if col not in exclude_cols]

    # Filter out features with too many missing values
    feature_df = df[numeric_cols].copy()
    missing_pct = feature_df.isna().sum() / len(feature_df)
    valid_features = missing_pct[missing_pct <= max_missing_pct].index.tolist()

    logger.info(f"    Selected {len(valid_features)}/{len(numeric_cols)} features (missing < {max_missing_pct*100:.0f}%)")

    # Keep only valid features
    feature_df = feature_df[valid_features]

    # Impute remaining missing values with median
    for col in feature_df.columns:
        if feature_df[col].isna().any():
            median_val = feature_df[col].median()
            feature_df[col] = feature_df[col].fillna(median_val)

    return feature_df


def train_model(X_train, y_train, X_test, y_test, property_type: str):
    """Train XGBoost model for specific property type."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Training {property_type} Model")
    logger.info(f"{'='*60}")
    logger.info(f"  Train samples: {len(X_train):,}")
    logger.info(f"  Test samples: {len(X_test):,}")
    logger.info(f"  Features: {len(X_train.columns)}")

    # XGBoost model
    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
    )

    # Train
    logger.info("  Training...")
    model.fit(X_train, y_train, verbose=False)

    # Predictions
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    # Metrics
    train_r2 = r2_score(y_train, y_pred_train)
    test_r2 = r2_score(y_test, y_pred_test)
    test_mae = mean_absolute_error(y_test, y_pred_test)
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))

    # Directional accuracy
    direction_correct = ((y_test > 0) == (y_pred_test > 0)).sum()
    directional_acc = direction_correct / len(y_test) * 100

    logger.info("\n  Results:")
    logger.info(f"    Train R²: {train_r2:.4f}")
    logger.info(f"    Test R²:  {test_r2:.4f}")
    logger.info(f"    Test MAE: {test_mae:.2f}%")
    logger.info(f"    Test RMSE: {test_rmse:.2f}%")
    logger.info(f"    Directional Accuracy: {directional_acc:.1f}%")

    # Feature importance
    importance_df = pd.DataFrame(
        {"feature": X_train.columns, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)

    logger.info("\n  Top 10 Features:")
    for _, row in importance_df.head(10).iterrows():
        logger.info(f"    {row['feature']}: {row['importance']:.4f}")

    return model, {
        "property_type": property_type,
        "train_r2": train_r2,
        "test_r2": test_r2,
        "test_mae": test_mae,
        "test_rmse": test_rmse,
        "directional_accuracy": directional_acc,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "n_features": len(X_train.columns),
    }


def main():
    """Train separate models by property type."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logger.info("=" * 60)
    logger.info("Price Appreciation Modeling: Separate Models by Property Type")
    logger.info("=" * 60)

    # Setup output directory
    output_dir = Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "models_by_property_type"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    train_df, test_df = load_data()

    # Target variable
    target_col = "yoy_change_pct"

    results = []
    predictions_list = []

    # Train separate model for each property type
    property_types = [
        ("HDB", "is_hdb"),
        ("Condo", "is_condo"),
        ("EC", "is_ec"),
    ]

    for prop_name, prop_col in property_types:
        # Filter data
        train_mask = train_df[prop_col] == 1
        test_mask = test_df[prop_col] == 1

        train_subset = train_df[train_mask].copy()
        test_subset = test_df[test_mask].copy()

        if len(train_subset) < 1000:
            logger.warning(f"\n  Skipping {prop_name}: insufficient training data ({len(train_subset)} samples)")
            continue

        # Prepare features (with imputation)
        y_train = train_subset[target_col]
        y_test = test_subset[target_col]

        # Drop rows where target is missing
        train_valid_target = y_train.notna()
        test_valid_target = y_test.notna()

        train_subset = train_subset[train_valid_target]
        test_subset = test_subset[test_valid_target]
        y_train = y_train[train_valid_target]
        y_test = y_test[test_valid_target]

        X_train = prepare_features(train_subset, target_col)
        X_test = prepare_features(test_subset, target_col)

        # Use intersection of features to ensure consistency
        common_features = X_train.columns.intersection(X_test.columns)
        X_train = X_train[common_features]
        X_test = X_test[common_features]

        logger.info(f"    Using {len(common_features)} common features")

        # Align indices
        common_train_idx = X_train.index.intersection(y_train.index)
        common_test_idx = X_test.index.intersection(y_test.index)

        X_train = X_train.loc[common_train_idx]
        y_train = y_train.loc[common_train_idx]
        X_test = X_test.loc[common_test_idx]
        y_test = y_test.loc[common_test_idx]

        # Train model
        model, metrics = train_model(X_train, y_train, X_test, y_test, prop_name)

        # Save model
        model_path = output_dir / f"{prop_name.lower()}_model.json"
        model.save_model(model_path)
        logger.info(f"  Saved model to {model_path}")

        # Generate predictions
        y_pred_test = model.predict(X_test)

        # Store predictions with metadata
        pred_df = pd.DataFrame(
            {
                "property_type": prop_name,
                "actual": y_test.values,
                "predicted": y_pred_test,
                "residual": y_test.values - y_pred_test,
                "abs_residual": np.abs(y_test.values - y_pred_test),
            }
        )
        predictions_list.append(pred_df)

        results.append(metrics)

        # Save feature importance
        importance_df = pd.DataFrame(
            {"feature": X_train.columns, "importance": model.feature_importances_}
        ).sort_values("importance", ascending=False)

        importance_path = output_dir / f"{prop_name.lower()}_feature_importance.csv"
        importance_df.to_csv(importance_path, index=False)
        logger.info(f"  Saved feature importance to {importance_path}")

    # Combine all predictions
    all_predictions = pd.concat(predictions_list, ignore_index=True)

    predictions_path = output_dir / "all_predictions.parquet"
    all_predictions.to_parquet(predictions_path, index=False)
    logger.info(f"\n  Saved all predictions to {predictions_path}")

    # Compare results across property types
    logger.info("\n" + "=" * 60)
    logger.info("MODEL COMPARISON ACROSS PROPERTY TYPES")
    logger.info("=" * 60)

    comparison_df = pd.DataFrame(results)
    comparison_df = comparison_df.sort_values("test_r2", ascending=False)

    logger.info("\n" + comparison_df.to_string(index=False))

    # Save comparison
    comparison_path = output_dir / "model_comparison.csv"
    comparison_df.to_csv(comparison_path, index=False)
    logger.info(f"\n  Saved comparison to {comparison_path}")

    # Overall metrics
    logger.info("\n" + "=" * 60)
    logger.info("OVERALL METRICS (All Property Types Combined)")
    logger.info("=" * 60)

    overall_r2 = r2_score(all_predictions["actual"], all_predictions["predicted"])
    overall_mae = mean_absolute_error(all_predictions["actual"], all_predictions["predicted"])
    overall_rmse = np.sqrt(
        mean_squared_error(all_predictions["actual"], all_predictions["predicted"])
    )
    overall_directional = (
        (all_predictions["actual"] > 0) == (all_predictions["predicted"] > 0)
    ).sum() / len(all_predictions) * 100

    logger.info(f"  R²: {overall_r2:.4f}")
    logger.info(f"  MAE: {overall_mae:.2f}%")
    logger.info(f"  RMSE: {overall_rmse:.2f}%")
    logger.info(f"  Directional Accuracy: {overall_directional:.1f}%")

    # Property-wise residual statistics
    logger.info("\n" + "=" * 60)
    logger.info("RESIDUAL STATISTICS BY PROPERTY TYPE")
    logger.info("=" * 60)

    for prop_name in ["HDB", "Condo", "EC"]:
        prop_preds = all_predictions[all_predictions["property_type"] == prop_name]
        if len(prop_preds) > 0:
            logger.info(f"\n  {prop_name}:")
            logger.info(f"    Mean residual: {prop_preds['residual'].mean():.2f}")
            logger.info(f"    Std residual: {prop_preds['residual'].std():.2f}")
            logger.info(f"    Mean abs residual: {prop_preds['abs_residual'].mean():.2f}")

    logger.info("\n" + "=" * 60)
    logger.info("Training Complete!")
    logger.info("=" * 60)
    logger.info(f"\nOutputs saved to: {output_dir}")


if __name__ == "__main__":
    main()
