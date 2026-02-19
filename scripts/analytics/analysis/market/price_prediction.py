#!/usr/bin/env python3
"""Price prediction model using XGBoost."""

import logging
import sys
from pathlib import Path

import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.data_helpers import load_parquet, save_parquet
from scripts.core.config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Train XGBoost model for price prediction."""
    logger.info("🚀 Starting price prediction analysis")

    df = load_parquet("L3_housing_unified")
    logger.info(f"Loaded {len(df):,} records")

    feature_cols = [
        "floor_area_sqft",
        "remaining_lease_months",
        "dist_to_nearest_mall",
        "dist_to_nearest_mrt_station",
        "dist_to_nearest_supermarket",
        "mall_within_1km",
        "mrt_station_within_1km",
        "supermarket_within_1km",
    ]

    df_model = df.dropna(subset=feature_cols + ["price"]).copy()
    logger.info(f"Complete cases: {len(df_model):,}")

    X = df_model[feature_cols]
    y = df_model["price"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    logger.info(f"Train: {len(X_train):,}, Test: {len(X_test):,}")

    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)
    logger.info("✅ Model trained")

    y_pred = model.predict(X_test)

    mse = mean_squared_error(y_test, y_pred)
    rmse = mse ** 0.5
    r2 = r2_score(y_test, y_pred)

    logger.info(f"RMSE: ${rmse:,.0f}")
    logger.info(f"R²: {r2:.3f}")

    importance = pd.DataFrame({
        "feature": feature_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)

    logger.info("\nFeature Importance:")
    for _, row in importance.head(10).iterrows():
        logger.info(f"  {row['feature']}: {row['importance']:.3f}")

    results = X_test.copy()
    results["price_actual"] = y_test
    results["price_predicted"] = y_pred
    results["price_error"] = results["price_predicted"] - results["price_actual"]

    save_parquet(results, "L4_price_predictions", source="XGBoost model")
    logger.info(f"✅ Saved predictions to L4_price_predictions.parquet")

    print({
        "key_findings": [
            f"Trained XGBoost model on {len(X_train):,} transactions",
            f"Test RMSE: ${rmse:,.0f} ({rmse/y_train.mean()*100:.1f}% of mean price)",
            f"R² score: {r2:.3f}",
            f"Top feature: {importance.iloc[0]['feature']}",
        ],
        "outputs": ["L4_price_predictions.parquet"],
    })


if __name__ == "__main__":
    main()
