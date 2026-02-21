#!/usr/bin/env python3
"""Feature importance analysis using XGBoost."""

import logging
import sys
from pathlib import Path

import matplotlib
import pandas as pd
import xgboost as xgb

matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Calculate feature importance using XGBoost."""
    logger.info("🚀 Starting feature importance analysis")

    df = load_parquet("L3_housing_unified")

    feature_cols = [
        "floor_area_sqft",
        "remaining_lease_months",
        "dist_nearest_mall",
        "dist_nearest_mrt_station",
        "dist_nearest_supermarket",
        "count_mall_1000m",
        "count_mrt_station_1000m",
        "count_supermarket_1000m",
    ]

    df_model = df.dropna(subset=feature_cols + ["price"]).copy()
    X = df_model[feature_cols]
    y = df_model["price"]

    logger.info(f"Training on {len(X):,} samples")

    X_sample = X.sample(n=min(10000, len(X)), random_state=42)
    y_sample = y.loc[X_sample.index]

    model = xgb.XGBRegressor(
        n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42
    )
    model.fit(X_sample, y_sample)

    importance = pd.DataFrame({
        "feature": feature_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)

    plt.figure(figsize=(10, 6))
    plt.barh(importance["feature"], importance["importance"])
    plt.xlabel("Feature Importance")
    plt.title("XGBoost Feature Importance")
    plt.gca().invert_yaxis()

    output_path = Config.ANALYSIS_OUTPUT_DIR / "feature_importance.png"
    plt.savefig(output_path, bbox_inches="tight")
    logger.info(f"✅ Saved feature importance plot to {output_path}")

    logger.info("\nFeature Importance:")
    for _, row in importance.iterrows():
        logger.info(f"  {row['feature']}: {row['importance']:.3f}")

    print({
        "key_findings": [
            f"Top feature: {importance.iloc[0]['feature']}",
            f"Feature importance calculated for {len(feature_cols)} features",
            f"Visualization saved to {output_path.name}",
        ],
        "outputs": ["feature_importance.png"],
    })


if __name__ == "__main__":
    main()
