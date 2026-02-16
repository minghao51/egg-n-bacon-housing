"""Train improved Condo price appreciation model with luxury features.

Adds luxury-specific features and handles outliers to improve Condo model performance.

Usage:
    uv run python scripts/analytics/price_appreciation_modeling/train_condo_with_luxury_features.py
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Add project root to path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.core.config import Config

# Configure logging
logger = logging.getLogger(__name__)


def add_luxury_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add luxury-specific features for condos."""
    df = df.copy()

    # Luxury segment indicators (by price PSF)
    df["is_luxury"] = (df["price_psf"] > 3000).astype(int)
    df["is_mass_market"] = (df["price_psf"] < 1500).astype(int)
    df["is_mid_market"] = (
        (df["price_psf"] >= 1500) & (df["price_psf"] <= 3000)
    ).astype(int)

    # Size categories
    df["is_shoebox"] = (df["floor_area_sqft"] < 500).astype(int)
    df["is_large_unit"] = (df["floor_area_sqft"] > 1500).astype(int)

    # Price per unit size
    df["price_per_100sqft"] = df["price_psf"] * 100

    # Extreme appreciation flag (potential data issues)
    df["is_extreme_appreciation"] = (df["yoy_change_pct"].abs() > 200).astype(int)

    # Unit age (assuming current year is 2024)
    df["unit_age"] = 2024 - df["lease_commence_date"]
    df["is_new_launch"] = (df["unit_age"] < 3).astype(int)
    df["is_old"] = (df["unit_age"] > 30).astype(int)

    # Location density (Postal District clustering)
    # Districts 9, 10, 11 are prime luxury areas
    df["is_prime_district"] = df["Postal District"].isin([9, 10, 11]).astype(int)

    # Amenity premium (having many amenities within 500m)
    amenity_cols = [col for col in df.columns if col.endswith("_within_500m")]
    if amenity_cols:
        df["amenity_count_500m"] = df[amenity_cols].sum(axis=1)
        df["has_all_amenities"] = (df["amenity_count_500m"] >= 5).astype(int)

    # MRT proximity premium
    if "dist_to_nearest_mrt" in df.columns:
        df["is_mrt_adjacent"] = (df["dist_to_nearest_mrt"] < 300).astype(int)
        df["is_mrt_nearby"] = (
            (df["dist_to_nearest_mrt"] >= 300) & (df["dist_to_nearest_mrt"] < 800)
        ).astype(int)

    return df


def prepare_features(df: pd.DataFrame, target_col: str = "yoy_change_pct", max_missing_pct: float = 0.3):
    """Select and prepare features for modeling."""
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


def train_improved_condo_model():
    """Train improved Condo model with luxury features."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logger.info("=" * 60)
    logger.info("Price Appreciation Modeling: Improved Condo Model")
    logger.info("=" * 60)

    # Setup output directory
    output_dir = Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "improved_condo_model"
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

    # Add luxury features
    logger.info("\nAdding luxury features...")
    train_condo = add_luxury_features(train_condo)
    test_condo = add_luxury_features(test_condo)

    new_features = [col for col in train_condo.columns if col not in train_df.columns]
    logger.info(f"  Added {len(new_features)} luxury features")
    for feat in new_features:
        logger.info(f"    - {feat}")

    # Remove extreme outliers (but keep them for analysis)
    logger.info("\nHandling extreme outliers...")

    # Define outlier thresholds
    extreme_outlier_mask = train_condo["yoy_change_pct"].abs() > 500
    moderate_outlier_mask = train_condo["yoy_change_pct"].abs() > 200

    logger.info(f"  Extreme outliers (>500%): {extreme_outlier_mask.sum():,} ({extreme_outlier_mask.sum()/len(train_condo)*100:.2f}%)")
    logger.info(f"  Moderate outliers (>200%): {moderate_outlier_mask.sum():,} ({moderate_outlier_mask.sum()/len(train_condo)*100:.2f}%)")

    # Train on cleaned data (remove extreme outliers)
    train_clean = train_condo[~extreme_outlier_mask].copy()
    logger.info(f"  Training on {len(train_clean):,} records (after removing extreme outliers)")

    # Prepare target
    target_col = "yoy_change_pct"

    # Drop rows where target is missing
    train_valid_target = train_clean[target_col].notna()
    test_valid_target = test_condo[target_col].notna()

    train_clean = train_clean[train_valid_target]
    test_condo = test_condo[test_valid_target]

    y_train = train_clean[target_col]
    y_test = test_condo[target_col]

    # Prepare features
    X_train = prepare_features(train_clean, target_col, max_missing_pct=0.3)
    X_test = prepare_features(test_condo, target_col, max_missing_pct=0.3)

    # Use intersection of features
    common_features = X_train.columns.intersection(X_test.columns)
    X_train = X_train[common_features]
    X_test = X_test[common_features]

    logger.info(f"  Using {len(common_features)} common features")

    # Train model
    logger.info("\nTraining XGBoost model...")

    model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train, verbose=False)

    # Predictions
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)

    # Metrics on cleaned data
    train_r2 = r2_score(y_train, y_pred_train)
    test_r2 = r2_score(y_test, y_pred_test)
    test_mae = mean_absolute_error(y_test, y_pred_test)
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))

    # Directional accuracy
    direction_correct = ((y_test > 0) == (y_pred_test > 0)).sum()
    directional_acc = direction_correct / len(y_test) * 100

    logger.info("\n" + "=" * 60)
    logger.info("MODEL RESULTS (with outlier handling)")
    logger.info("=" * 60)
    logger.info(f"  Train R²: {train_r2:.4f}")
    logger.info(f"  Test R²:  {test_r2:.4f}")
    logger.info(f"  Test MAE: {test_mae:.2f}%")
    logger.info(f"  Test RMSE: {test_rmse:.2f}%")
    logger.info(f"  Directional Accuracy: {directional_acc:.1f}%")

    # Feature importance
    importance_df = pd.DataFrame(
        {"feature": X_train.columns, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)

    logger.info("\nTop 15 Features:")
    for _, row in importance_df.head(15).iterrows():
        logger.info(f"  {row['feature']}: {row['importance']:.4f}")

    # Save model
    model_path = output_dir / "improved_condo_model.json"
    model.save_model(model_path)
    logger.info(f"\nSaved model to {model_path}")

    # Save feature importance
    importance_path = output_dir / "feature_importance.csv"
    importance_df.to_csv(importance_path, index=False)
    logger.info(f"Saved feature importance to {importance_path}")

    # Save predictions
    pred_df = pd.DataFrame(
        {
            "actual": y_test.values,
            "predicted": y_pred_test,
            "residual": y_test.values - y_pred_test,
            "abs_residual": np.abs(y_test.values - y_pred_test),
        },
        index=y_test.index
    )
    predictions_path = output_dir / "predictions.parquet"
    pred_df.to_parquet(predictions_path, index=False)
    logger.info(f"Saved predictions to {predictions_path}")

    # Analysis by segment
    logger.info("\n" + "=" * 60)
    logger.info("PERFORMANCE BY SEGMENT")
    logger.info("=" * 60)

    # Get test data with luxury features (after filtering)
    test_indices = y_test.index
    test_with_features = test_condo.loc[test_indices].copy()

    # Reset indices for alignment
    pred_df_reset = pred_df.reset_index(drop=True)
    test_features_reset = test_with_features.reset_index(drop=True)

    segments = {
        "Luxury (>3000 psf)": test_features_reset["is_luxury"] == 1,
        "Mass Market (<1500 psf)": test_features_reset["is_mass_market"] == 1,
        "Mid Market": test_features_reset["is_mid_market"] == 1,
        "Shoebox (<500 sqft)": test_features_reset["is_shoebox"] == 1,
        "Large Units (>1500 sqft)": test_features_reset["is_large_unit"] == 1,
        "Prime District (9,10,11)": test_features_reset["is_prime_district"] == 1,
    }

    for segment_name, mask in segments.items():
        if mask.sum() > 100:  # Only analyze if enough samples
            segment_actual = pred_df_reset.loc[mask, "actual"]
            segment_pred = pred_df_reset.loc[mask, "predicted"]

            if len(segment_actual) > 0:
                seg_mae = mean_absolute_error(segment_actual, segment_pred)
                seg_r2 = r2_score(segment_actual, segment_pred)
                logger.info(f"\n{segment_name} (n={len(segment_actual):,}):")
                logger.info(f"  MAE: {seg_mae:.2f}%")
                logger.info(f"  R²: {seg_r2:.4f}")

    logger.info("\n" + "=" * 60)
    logger.info("Training Complete!")
    logger.info("=" * 60)

    return model, pred_df


if __name__ == "__main__":
    train_improved_condo_model()
