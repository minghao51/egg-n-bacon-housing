"""Train separate Condo models by price segment.

Trains three separate models:
- Mass Market (<1500 psf)
- Mid Market (1500-3000 psf)
- Luxury (>3000 psf)

Usage:
    uv run python scripts/analytics/price_appreciation_modeling/train_condo_by_segment.py
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


def add_condo_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add condo-specific features."""
    df = df.copy()

    # Unit size categories
    df["is_shoebox"] = (df["floor_area_sqft"] < 500).astype(int)
    df["is_large_unit"] = (df["floor_area_sqft"] > 1500).astype(int)

    # Unit age
    df["unit_age"] = 2024 - df["lease_commence_date"]
    df["is_new_launch"] = (df["unit_age"] < 3).astype(int)
    df["is_old"] = (df["unit_age"] > 30).astype(int)

    # Prime district
    df["is_prime_district"] = df["Postal District"].isin([9, 10, 11]).astype(int)

    # Amenity count
    amenity_cols = [col for col in df.columns if col.endswith("_within_500m")]
    if amenity_cols:
        df["amenity_count_500m"] = df[amenity_cols].sum(axis=1)

    # MRT proximity
    if "dist_to_nearest_mrt" in df.columns:
        df["is_mrt_adjacent"] = (df["dist_to_nearest_mrt"] < 300).astype(int)

    return df


def prepare_features(df: pd.DataFrame, target_col: str = "yoy_change_pct", max_missing_pct: float = 0.3):
    """Select and prepare features for modeling."""
    # Select numeric columns
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

    # Keep only valid features
    feature_df = feature_df[valid_features]

    # Impute remaining missing values with median
    for col in feature_df.columns:
        if feature_df[col].isna().any():
            median_val = feature_df[col].median()
            feature_df[col] = feature_df[col].fillna(median_val)

    return feature_df


def train_segment_model(X_train, y_train, X_test, y_test, segment_name: str, segment_params: dict):
    """Train XGBoost model for specific segment."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Training {segment_name} Model")
    logger.info(f"{'='*60}")
    logger.info(f"  Train samples: {len(X_train):,}")
    logger.info(f"  Test samples: {len(X_test):,}")
    logger.info(f"  Features: {len(X_train.columns)}")

    # Adjust model parameters based on segment size
    if segment_params["n_train"] < 20000:
        # Smaller segments - simpler model
        n_estimators = 200
        max_depth = 6
    else:
        # Larger segments - more complex model
        n_estimators = 300
        max_depth = 8

    # XGBoost model
    model = xgb.XGBRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
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
        "segment": segment_name,
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
    """Train separate models by condo price segment."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logger.info("=" * 60)
    logger.info("Price Appreciation Modeling: Condo Models by Segment")
    logger.info("=" * 60)

    # Setup output directory
    output_dir = Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "condo_by_segment"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    logger.info("\nLoading data...")
    train_path = Config.DATA_DIR / "pipeline" / "L5_price_appreciation_train.parquet"
    test_path = Config.DATA_DIR / "pipeline" / "L5_price_appreciation_test.parquet"

    train_df = pd.read_parquet(train_path)
    test_df = pd.read_parquet(test_path)

    logger.info(f"  Train: {len(train_df):,} records")
    logger.info(f"  Test: {len(test_df):,} records")

    # Filter condos
    logger.info("\nFiltering condos...")
    train_condo = train_df[train_df["is_condo"] == 1].copy()
    test_condo = test_df[test_df["is_condo"] == 1].copy()

    logger.info(f"  Train condos: {len(train_condo):,}")
    logger.info(f"  Test condos: {len(test_condo):,}")

    # Add condo features
    logger.info("\nAdding condo-specific features...")
    train_condo = add_condo_features(train_condo)
    test_condo = add_condo_features(test_condo)

    # Define segments
    segments = [
        {
            "name": "Mass Market",
            "condition": lambda df: df["price_psf"] < 1500,
            "description": "<1500 psf",
        },
        {
            "name": "Mid Market",
            "condition": lambda df: (df["price_psf"] >= 1500) & (df["price_psf"] <= 3000),
            "description": "1500-3000 psf",
        },
        {
            "name": "Luxury",
            "condition": lambda df: df["price_psf"] > 3000,
            "description": ">3000 psf",
        },
    ]

    target_col = "yoy_change_pct"
    results = []
    predictions_list = []

    # Train model for each segment
    for segment in segments:
        # Filter by segment
        train_mask = segment["condition"](train_condo)
        test_mask = segment["condition"](test_condo)

        train_segment = train_condo[train_mask].copy()
        test_segment = test_condo[test_mask].copy()

        # Skip if insufficient data
        if len(train_segment) < 1000:
            logger.warning(f"\nSkipping {segment['name']}: insufficient training data ({len(train_segment)} samples)")
            continue

        logger.info(f"\n{segment['name']} Segment ({segment['description']}):")
        logger.info(f"  Train: {len(train_segment):,}")
        logger.info(f"  Test: {len(test_segment):,}")

        # Drop rows where target is missing
        train_valid = train_segment[target_col].notna()
        test_valid = test_segment[target_col].notna()

        train_segment = train_segment[train_valid]
        test_segment = test_segment[test_valid]

        # Prepare features
        X_train = prepare_features(train_segment, target_col)
        X_test = prepare_features(test_segment, target_col)

        y_train = train_segment[target_col]
        y_test = test_segment[target_col]

        # Align indices
        y_train = y_train.loc[X_train.index]
        y_test = y_test.loc[X_test.index]

        # Use intersection of features
        common_features = X_train.columns.intersection(X_test.columns)
        X_train = X_train[common_features]
        X_test = X_test[common_features]

        logger.info(f"  Using {len(common_features)} common features")

        # Train model
        model, metrics = train_segment_model(
            X_train, y_train, X_test, y_test, segment["name"], {"n_train": len(X_train)}
        )

        # Save model
        model_path = output_dir / f"{segment['name'].lower().replace(' ', '_')}_model.json"
        model.save_model(model_path)
        logger.info(f"  Saved model to {model_path}")

        # Generate predictions
        y_pred_test = model.predict(X_test)

        # Store predictions
        pred_df = pd.DataFrame(
            {
                "segment": segment["name"],
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

        importance_path = output_dir / f"{segment['name'].lower().replace(' ', '_')}_feature_importance.csv"
        importance_df.to_csv(importance_path, index=False)
        logger.info(f"  Saved feature importance to {importance_path}")

    # Combine all predictions
    all_predictions = pd.concat(predictions_list, ignore_index=True)

    predictions_path = output_dir / "all_predictions.parquet"
    all_predictions.to_parquet(predictions_path, index=False)
    logger.info(f"\n  Saved all predictions to {predictions_path}")

    # Compare results across segments
    logger.info("\n" + "=" * 60)
    logger.info("MODEL COMPARISON ACROSS SEGMENTS")
    logger.info("=" * 60)

    comparison_df = pd.DataFrame(results)
    comparison_df = comparison_df.sort_values("test_r2", ascending=False)

    logger.info("\n" + comparison_df.to_string(index=False))

    # Save comparison
    comparison_path = output_dir / "segment_comparison.csv"
    comparison_df.to_csv(comparison_path, index=False)
    logger.info(f"\n  Saved comparison to {comparison_path}")

    # Overall metrics
    logger.info("\n" + "=" * 60)
    logger.info("OVERALL METRICS (All Segments Combined)")
    logger.info("=" * 60)

    overall_r2 = r2_score(all_predictions["actual"], all_predictions["predicted"])
    overall_mae = mean_absolute_error(all_predictions["actual"], all_predictions["predicted"])
    overall_rmse = np.sqrt(mean_squared_error(all_predictions["actual"], all_predictions["predicted"]))
    overall_directional = (
        (all_predictions["actual"] > 0) == (all_predictions["predicted"] > 0)
    ).sum() / len(all_predictions) * 100

    logger.info(f"  R²: {overall_r2:.4f}")
    logger.info(f"  MAE: {overall_mae:.2f}%")
    logger.info(f"  RMSE: {overall_rmse:.2f}%")
    logger.info(f"  Directional Accuracy: {overall_directional:.1f}%")

    # Segment-wise residual statistics
    logger.info("\n" + "=" * 60)
    logger.info("RESIDUAL STATISTICS BY SEGMENT")
    logger.info("=" * 60)

    for segment_name in ["Mass Market", "Mid Market", "Luxury"]:
        segment_preds = all_predictions[all_predictions["segment"] == segment_name]
        if len(segment_preds) > 0:
            logger.info(f"\n  {segment_name}:")
            logger.info(f"    Mean residual: {segment_preds['residual'].mean():.2f}")
            logger.info(f"    Std residual: {segment_preds['residual'].std():.2f}")
            logger.info(f"    Mean abs residual: {segment_preds['abs_residual'].mean():.2f}")

    # Compare with original unified Condo model
    logger.info("\n" + "=" * 60)
    logger.info("COMPARISON WITH ORIGINAL UNIFIED CONDO MODEL")
    logger.info("=" * 60)

    original_condo_results = {
        "test_r2": 0.3236,
        "test_mae": 118.40,
        "directional_accuracy": 96.9,
    }

    logger.info("\n  Original Unified Model:")
    logger.info(f"    Test R²: {original_condo_results['test_r2']:.4f}")
    logger.info(f"    Test MAE: {original_condo_results['test_mae']:.2f}%")
    logger.info(f"    Directional Accuracy: {original_condo_results['directional_accuracy']:.1f}%")

    logger.info("\n  New Segmented Models (Combined):")
    logger.info(f"    Test R²: {overall_r2:.4f} ({(overall_r2/original_condo_results['test_r2']-1)*100:+.1f}%)")
    logger.info(f"    Test MAE: {overall_mae:.2f}% ({(overall_mae/original_condo_results['test_mae']-1)*100:+.1f}%)")
    logger.info(f"    Directional Accuracy: {overall_directional:.1f}% ({overall_directional-original_condo_results['directional_accuracy']:+.1f} pp)")

    logger.info("\n" + "=" * 60)
    logger.info("Training Complete!")
    logger.info("=" * 60)
    logger.info(f"\nOutputs saved to: {output_dir}")


if __name__ == "__main__":
    main()
