"""Create smart ensemble that uses best model for each property type/segment.

Ensemble strategy:
- HDB: Use HDB-specific model (R² = 0.798)
- EC: Use EC-specific model (R² = 0.985)
- Condo Mass Market (<1500 psf): Use Mass Market model (R² = 0.856)
- Condo Mid Market (1500-3000 psf): Use Mid Market model (R² = 0.726)
- Condo Luxury (>3000 psf): Use Luxury model (R² = 0.301)

Usage:
    uv run python scripts/analytics/price_appreciation_modeling/create_smart_ensemble.py
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


def add_condo_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add condo-specific features (matching training)."""
    df = df.copy()

    df["is_shoebox"] = (df["floor_area_sqft"] < 500).astype(int)
    df["is_large_unit"] = (df["floor_area_sqft"] > 1500).astype(int)
    df["unit_age"] = 2024 - df["lease_commence_date"]
    df["is_new_launch"] = (df["unit_age"] < 3).astype(int)
    df["is_old"] = (df["unit_age"] > 30).astype(int)
    df["is_prime_district"] = df["Postal District"].isin([9, 10, 11]).astype(int)

    amenity_cols = [col for col in df.columns if col.endswith("_within_500m")]
    if amenity_cols:
        df["amenity_count_500m"] = df[amenity_cols].sum(axis=1)

    if "dist_to_nearest_mrt" in df.columns:
        df["is_mrt_adjacent"] = (df["dist_to_nearest_mrt"] < 300).astype(int)

    return df


def prepare_features(df: pd.DataFrame, feature_cols: list, max_missing_pct: float = 0.3):
    """Prepare features matching the model's expected features."""
    # Create a dataframe with exactly the columns the model expects, in that order
    feature_df = pd.DataFrame()

    for col in feature_cols:
        if col in df.columns:
            feature_df[col] = df[col]
        else:
            # Feature missing from dataframe - fill with zeros
            logger.warning(f"  Feature '{col}' not found in dataframe, filling with zeros")
            feature_df[col] = 0

    # Impute missing values with median
    for col in feature_df.columns:
        if feature_df[col].isna().any():
            median_val = feature_df[col].median()
            feature_df[col] = feature_df[col].fillna(median_val)

    return feature_df


def load_model_and_predict(df, model_path, feature_cols, model_name):
    """Load model and generate predictions."""
    logger.info(f"  Loading {model_name} model...")

    # Load model
    model = xgb.XGBRegressor()
    model.load_model(model_path)

    # Get the actual feature names from the model (in the correct order)
    model_features = model.get_booster().feature_names

    logger.info(f"    Model expects {len(model_features)} features")

    # Prepare features using the model's feature names
    X = prepare_features(df, model_features)

    # Generate predictions
    predictions = model.predict(X)

    logger.info(f"    Generated {len(predictions):,} predictions")
    return predictions


def main():
    """Create smart ensemble predictions."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logger.info("=" * 60)
    logger.info("Price Appreciation Modeling: Smart Ensemble")
    logger.info("=" * 60)

    # Setup output directory
    output_dir = Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "smart_ensemble"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load test data
    logger.info("\nLoading test data...")
    test_path = Config.DATA_DIR / "pipeline" / "L5_price_appreciation_test.parquet"
    test_df = pd.read_parquet(test_path)

    logger.info(f"  Test samples: {len(test_df):,}")

    # Add condo features to test data
    test_df = add_condo_features(test_df)

    # Initialize predictions array
    all_predictions = np.zeros(len(test_df))
    model_used = []

    # Process HDB
    logger.info("\n" + "=" * 60)
    logger.info("Processing HDB")
    logger.info("=" * 60)

    hdb_mask = test_df["is_hdb"] == 1
    hdb_count = hdb_mask.sum()
    logger.info(f"  HDB samples: {hdb_count:,}")

    if hdb_count > 0:
        hdb_test = test_df[hdb_mask].copy()

        hdb_preds = load_model_and_predict(
            hdb_test,
            Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "models_by_property_type" / "hdb_model.json",
            None,  # Not needed, will be loaded from model
            "HDB"
        )

        all_predictions[hdb_mask] = hdb_preds
        model_used.extend(["HDB Model"] * hdb_count)

    # Process EC
    logger.info("\n" + "=" * 60)
    logger.info("Processing EC")
    logger.info("=" * 60)

    ec_mask = test_df["is_ec"] == 1
    ec_count = ec_mask.sum()
    logger.info(f"  EC samples: {ec_count:,}")

    if ec_count > 0:
        ec_test = test_df[ec_mask].copy()

        ec_preds = load_model_and_predict(
            ec_test,
            Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "models_by_property_type" / "ec_model.json",
            None,  # Not needed, will be loaded from model
            "EC"
        )

        all_predictions[ec_mask] = ec_preds
        model_used.extend(["EC Model"] * ec_count)

    # Process Condos by segment
    logger.info("\n" + "=" * 60)
    logger.info("Processing Condos")
    logger.info("=" * 60)

    condo_mask = test_df["is_condo"] == 1
    condo_count = condo_mask.sum()
    logger.info(f"  Condo samples: {condo_count:,}")

    if condo_count > 0:
        condo_test = test_df[condo_mask].copy()

        # Mass Market
        mass_market_mask = condo_test["price_psf"] < 1500
        mass_market_count = mass_market_mask.sum()
        logger.info(f"\n  Mass Market (<1500 psf): {mass_market_count:,}")

        if mass_market_count > 0:
            mass_market_test = condo_test[mass_market_mask]

            mass_market_preds = load_model_and_predict(
                mass_market_test,
                Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "condo_by_segment" / "mass_market_model.json",
                None,  # Not needed, will be loaded from model
                "Mass Market"
            )

            # Map back to original indices
            mass_market_indices = condo_test[mass_market_mask].index
            all_predictions[mass_market_indices] = mass_market_preds
            model_used.extend(["Mass Market Model"] * mass_market_count)

        # Mid Market
        mid_market_mask = (condo_test["price_psf"] >= 1500) & (condo_test["price_psf"] <= 3000)
        mid_market_count = mid_market_mask.sum()
        logger.info(f"\n  Mid Market (1500-3000 psf): {mid_market_count:,}")

        if mid_market_count > 0:
            mid_market_test = condo_test[mid_market_mask]

            mid_market_preds = load_model_and_predict(
                mid_market_test,
                Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "condo_by_segment" / "mid_market_model.json",
                None,  # Not needed, will be loaded from model
                "Mid Market"
            )

            # Map back to original indices
            mid_market_indices = condo_test[mid_market_mask].index
            all_predictions[mid_market_indices] = mid_market_preds
            model_used.extend(["Mid Market Model"] * mid_market_count)

        # Luxury
        luxury_mask = condo_test["price_psf"] > 3000
        luxury_count = luxury_mask.sum()
        logger.info(f"\n  Luxury (>3000 psf): {luxury_count:,}")

        if luxury_count > 0:
            luxury_test = condo_test[luxury_mask]

            luxury_preds = load_model_and_predict(
                luxury_test,
                Config.DATA_DIR / "analysis" / "price_appreciation_modeling" / "condo_by_segment" / "luxury_model.json",
                None,  # Not needed, will be loaded from model
                "Luxury"
            )

            # Map back to original indices
            luxury_indices = condo_test[luxury_mask].index
            all_predictions[luxury_indices] = luxury_preds
            model_used.extend(["Luxury Model"] * luxury_count)

    # Create predictions dataframe
    logger.info("\n" + "=" * 60)
    logger.info("Creating Predictions DataFrame")
    logger.info("=" * 60)

    # Filter to samples with actual values
    valid_target = test_df["yoy_change_pct"].notna()
    test_valid = test_df[valid_target].copy()
    predictions_valid = all_predictions[valid_target.values]

    y_actual = test_valid["yoy_change_pct"]
    y_pred = predictions_valid

    logger.info(f"  Valid samples: {len(y_actual):,}")

    # Calculate metrics
    overall_r2 = r2_score(y_actual, y_pred)
    overall_mae = mean_absolute_error(y_actual, y_pred)
    overall_rmse = np.sqrt(mean_squared_error(y_actual, y_pred))

    # Directional accuracy
    direction_correct = ((y_actual > 0) == (y_pred > 0)).sum()
    directional_acc = direction_correct / len(y_actual) * 100

    logger.info("\n" + "=" * 60)
    logger.info("OVERALL ENSEMBLE PERFORMANCE")
    logger.info("=" * 60)
    logger.info(f"  R²: {overall_r2:.4f}")
    logger.info(f"  MAE: {overall_mae:.2f}%")
    logger.info(f"  RMSE: {overall_rmse:.2f}%")
    logger.info(f"  Directional Accuracy: {directional_acc:.1f}%")

    # Save predictions
    pred_df = pd.DataFrame(
        {
            "actual": y_actual.values,
            "predicted": y_pred,
            "residual": y_actual.values - y_pred,
            "abs_residual": np.abs(y_actual.values - y_pred),
        }
    )

    predictions_path = output_dir / "ensemble_predictions.parquet"
    pred_df.to_parquet(predictions_path, index=False)
    logger.info(f"\n  Saved predictions to {predictions_path}")

    # Analyze by property type/segment
    logger.info("\n" + "=" * 60)
    logger.info("PERFORMANCE BY PROPERTY TYPE/SEGMENT")
    logger.info("=" * 60)

    results = []

    # HDB
    hdb_valid = test_valid["is_hdb"] == 1
    if hdb_valid.sum() > 0:
        hdb_actual = y_actual[hdb_valid]
        hdb_pred = y_pred[hdb_valid]
        hdb_r2 = r2_score(hdb_actual, hdb_pred)
        hdb_mae = mean_absolute_error(hdb_actual, hdb_pred)
        hdb_dir = ((hdb_actual > 0) == (hdb_pred > 0)).sum() / len(hdb_actual) * 100

        logger.info(f"\n  HDB:")
        logger.info(f"    R²: {hdb_r2:.4f}")
        logger.info(f"    MAE: {hdb_mae:.2f}%")
        logger.info(f"    Directional Accuracy: {hdb_dir:.1f}%")

        results.append({
            "segment": "HDB",
            "n_samples": hdb_valid.sum(),
            "r2": hdb_r2,
            "mae": hdb_mae,
            "directional_acc": hdb_dir,
        })

    # Condo segments
    for segment_name, condition in [
        ("Mass Market", lambda df: (df["is_condo"] == 1) & (df["price_psf"] < 1500)),
        ("Mid Market", lambda df: (df["is_condo"] == 1) & (df["price_psf"] >= 1500) & (df["price_psf"] <= 3000)),
        ("Luxury", lambda df: (df["is_condo"] == 1) & (df["price_psf"] > 3000)),
    ]:
        segment_mask = condition(test_valid)
        if segment_mask.sum() > 0:
            seg_actual = y_actual[segment_mask]
            seg_pred = y_pred[segment_mask]
            seg_r2 = r2_score(seg_actual, seg_pred)
            seg_mae = mean_absolute_error(seg_actual, seg_pred)
            seg_dir = ((seg_actual > 0) == (seg_pred > 0)).sum() / len(seg_actual) * 100

            logger.info(f"\n  {segment_name}:")
            logger.info(f"    R²: {seg_r2:.4f}")
            logger.info(f"    MAE: {seg_mae:.2f}%")
            logger.info(f"    Directional Accuracy: {seg_dir:.1f}%")

            results.append({
                "segment": segment_name,
                "n_samples": segment_mask.sum(),
                "r2": seg_r2,
                "mae": seg_mae,
                "directional_acc": seg_dir,
            })

    # EC
    ec_valid = test_valid["is_ec"] == 1
    if ec_valid.sum() > 0:
        ec_actual = y_actual[ec_valid]
        ec_pred = y_pred[ec_valid]
        ec_r2 = r2_score(ec_actual, ec_pred)
        ec_mae = mean_absolute_error(ec_actual, ec_pred)
        ec_dir = ((ec_actual > 0) == (ec_pred > 0)).sum() / len(ec_actual) * 100

        logger.info(f"\n  EC:")
        logger.info(f"    R²: {ec_r2:.4f}")
        logger.info(f"    MAE: {ec_mae:.2f}%")
        logger.info(f"    Directional Accuracy: {ec_dir:.1f}%")

        results.append({
            "segment": "EC",
            "n_samples": ec_valid.sum(),
            "r2": ec_r2,
            "mae": ec_mae,
            "directional_acc": ec_dir,
        })

    # Save segment results
    results_df = pd.DataFrame(results)
    results_path = output_dir / "segment_performance.csv"
    results_df.to_csv(results_path, index=False)
    logger.info(f"\n  Saved segment results to {results_path}")

    # Compare with baseline models
    logger.info("\n" + "=" * 60)
    logger.info("COMPARISON WITH BASELINE MODELS")
    logger.info("=" * 60)

    baselines = {
        "Unified XGBoost (all property types)": {"r2": 0.468, "mae": 58.45},
        "Unified Condo Model": {"r2": 0.324, "mae": 118.40},
        "Property-Type Models (HDB/Condo/EC)": {"r2": 0.374, "mae": 56.67},
    }

    logger.info("\n  Baseline Models:")
    for model_name, metrics in baselines.items():
        logger.info(f"    {model_name}:")
        logger.info(f"      R²: {metrics['r2']:.4f}")
        logger.info(f"      MAE: {metrics['mae']:.2f}%")

    logger.info("\n  Smart Ensemble:")
    logger.info(f"    R²: {overall_r2:.4f}")
    logger.info(f"    MAE: {overall_mae:.2f}%")

    # Calculate improvements
    logger.info("\n  Improvements over Unified XGBoost:")
    logger.info(f"    R²: {(overall_r2/baselines['Unified XGBoost (all property types)']['r2']-1)*100:+.1f}%")
    logger.info(f"    MAE: {(overall_mae/baselines['Unified XGBoost (all property types)']['mae']-1)*100:+.1f}%")

    logger.info("\n  Improvements over Property-Type Models:")
    logger.info(f"    R²: {(overall_r2/baselines['Property-Type Models (HDB/Condo/EC)']['r2']-1)*100:+.1f}%")
    logger.info(f"    MAE: {(overall_mae/baselines['Property-Type Models (HDB/Condo/EC)']['mae']-1)*100:+.1f}%")

    logger.info("\n" + "=" * 60)
    logger.info("Ensemble Creation Complete!")
    logger.info("=" * 60)
    logger.info(f"\nOutputs saved to: {output_dir}")


if __name__ == "__main__":
    main()
