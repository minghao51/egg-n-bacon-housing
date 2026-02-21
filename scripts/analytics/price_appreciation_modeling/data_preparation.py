"""Data preparation for price appreciation modeling analysis.

This script:
1. Loads L3 unified dataset
2. Adds temporal features (lagged appreciation, momentum, acceleration)
3. Adds spatial features (amenity interactions)
4. Adds property features (one-hot encoding, log price)
5. Creates train/test split (time-based)
6. Saves prepared dataset for modeling

Usage:
    uv run python scripts/analytics/price_appreciation_modeling/data_preparation.py
"""  # noqa: N999

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.core.config import Config
from scripts.core.data_helpers import save_parquet

# Configure logging
logger = logging.getLogger(__name__)


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add temporal features for predictive modeling.

    Calculates lagged appreciation, acceleration, and trend stability
    directly on the unified dataset (no merge needed).

    Args:
        df: Unified transaction DataFrame

    Returns:
        DataFrame with temporal features added
    """
    logger.info("Adding temporal features...")

    if df.empty or "planning_area" not in df.columns or "yoy_change_pct" not in df.columns:
        logger.warning("Cannot add temporal features - missing required columns")
        return df

    df = df.copy()

    # Sort for proper shift calculations
    df = df.sort_values(["planning_area", "year", "month"])

    # Lagged YoY appreciation (auto-regressive features)
    logger.info("  Creating lagged features...")
    df["yoy_change_pct_lag1"] = df.groupby("planning_area")["yoy_change_pct"].shift(1)
    df["yoy_change_pct_lag2"] = df.groupby("planning_area")["yoy_change_pct"].shift(2)
    df["yoy_change_pct_lag3"] = df.groupby("planning_area")["yoy_change_pct"].shift(3)

    # Acceleration (change in growth rates)
    logger.info("  Calculating acceleration...")
    df["acceleration_2y"] = df.groupby("planning_area")["yoy_change_pct"].diff(2)

    # Trend stability (rolling standard deviation of growth)
    logger.info("  Calculating trend stability...")
    df["trend_stability"] = df.groupby("planning_area")["yoy_change_pct"].transform(
        lambda x: x.rolling(12, min_periods=3).std()
    )

    # Forward momentum indicator (3m - 12m)
    if "growth_3m" in df.columns and "growth_12m" in df.columns:
        logger.info("  Calculating forward momentum...")
        df["forward_momentum"] = df["growth_3m"] - df["growth_12m"]
    else:
        logger.warning("growth_3m or growth_12m not found, skipping forward_momentum")

    logger.info(f"  Added temporal features to {len(df):,} records")

    return df


def add_spatial_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add spatial interaction features.

    Args:
        df: DataFrame with lat/lon and amenity features

    Returns:
        DataFrame with spatial features added
    """
    logger.info("Adding spatial features...")

    if df.empty:
        return df

    df = df.copy()

    # Amenity distance squared (non-linear effects)
    if "dist_to_nearest_mrt" in df.columns:
        df["dist_mrt_sq"] = df["dist_to_nearest_mrt"] ** 2

    # Amenity synergies (interaction features)
    mrt_col = "mrt_within_500m" if "mrt_within_500m" in df.columns else None
    hawker_col = "hawker_within_500m" if "hawker_within_500m" in df.columns else None

    if mrt_col and hawker_col:
        df["mrt_x_hawker"] = df[mrt_col] * df[hawker_col]

    school_col = "school_within_1km" if "school_within_1km" in df.columns else None
    park_col = "park_within_500m" if "park_within_500m" in df.columns else None

    if school_col and park_col:
        df["school_x_park"] = df[school_col] * df[park_col]

    # Amenity density score
    amenity_cols = [col for col in df.columns if col.endswith("_within_500m")]
    if amenity_cols:
        df["amenity_density_500m"] = df[amenity_cols].sum(axis=1)

    amenity_cols_1km = [col for col in df.columns if col.endswith("_within_1km")]
    if amenity_cols_1km:
        df["amenity_density_1km"] = df[amenity_cols_1km].sum(axis=1)

    logger.info("  Added spatial features to dataset")

    return df


def add_property_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add property-specific features for modeling.

    Args:
        df: DataFrame with property attributes

    Returns:
        DataFrame with property features added
    """
    logger.info("Adding property features...")

    if df.empty:
        return df

    df = df.copy()

    # One-hot encode property type
    if "property_type" in df.columns:
        df["is_hdb"] = (df["property_type"] == "HDB").astype(int)
        df["is_condo"] = (df["property_type"] == "Condominium").astype(int)
        df["is_ec"] = (df["property_type"] == "EC").astype(int)

        logger.info(f"  Encoded property_type: {df['property_type'].value_counts().to_dict()}")

    # Log-transformed price (controls for mean reversion)
    if "price_psf" in df.columns:
        df["log_price_psf"] = np.log1p(df["price_psf"])

    # Lease decay (HDB only)
    if "remaining_lease_months" in df.columns:
        df["remaining_lease_years"] = df["remaining_lease_months"] / 12

        # Non-linear decay factor
        df["lease_decay_factor"] = np.exp(-0.05 * (99 - df["remaining_lease_years"]))

        logger.info("  Added lease decay features")

    return df


def create_train_test_split(
    df: pd.DataFrame, test_years: list = [2023, 2024]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create time-based train/test split.

    Args:
        df: Full prepared dataset
        test_years: Years to hold out for testing

    Returns:
        train_df, test_df
    """
    logger.info(f"Creating train/test split (test on {test_years})...")

    if "year" not in df.columns:
        logger.error("year column not found for train/test split")
        return pd.DataFrame(), pd.DataFrame()

    # Filter to complete records (have year)
    df_complete = df.dropna(subset=["year"]).copy()

    # Split based on year
    train_mask = ~df_complete["year"].isin(test_years)
    test_mask = df_complete["year"].isin(test_years)

    train_df = df_complete[train_mask].copy()
    test_df = df_complete[test_mask].copy()

    logger.info(f"  Train: {len(train_df):,} records ({len(train_df)/len(df_complete)*100:.1f}%)")
    logger.info(f"  Test: {len(test_df):,} records ({len(test_df)/len(df_complete)*100:.1f}%)")

    return train_df, test_df


def main():
    """Run data preparation pipeline."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logger.info("=" * 60)
    logger.info("Price Appreciation Modeling: Data Preparation")
    logger.info("=" * 60)

    # 1. Load L3 unified dataset
    logger.info("\n[1/5] Loading L3 unified dataset...")

    unified_path = Config.DATA_DIR / "pipeline" / "L3" / "housing_unified.parquet"
    if not unified_path.exists():
        logger.error(f"L3 unified dataset not found at {unified_path}")
        return

    unified_df = pd.read_parquet(unified_path)
    logger.info(f"  Loaded {len(unified_df):,} records from L3 unified dataset")

    # 2. Add temporal features
    logger.info("\n[2/5] Adding temporal features...")
    prepared_df = add_temporal_features(unified_df)

    # 3. Add spatial features
    logger.info("\n[3/5] Adding spatial features...")
    prepared_df = add_spatial_features(prepared_df)

    # 4. Add property features
    logger.info("\n[4/5] Adding property features...")
    prepared_df = add_property_features(prepared_df)

    # 5. Create train/test split
    logger.info("\n[5/5] Creating train/test split...")
    train_df, test_df = create_train_test_split(prepared_df)

    # 6. Save outputs (model training script will handle feature selection)
    logger.info("\nSaving prepared datasets...")

    # Save full prepared dataset
    save_parquet(prepared_df, "L5_price_appreciation_prepared", source="data preparation")

    # Save train/test split
    save_parquet(train_df, "L5_price_appreciation_train", source="data preparation")
    save_parquet(test_df, "L5_price_appreciation_test", source="data preparation")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Data Preparation Complete!")
    logger.info("=" * 60)
    logger.info(f"Total records: {len(prepared_df):,}")
    logger.info(f"Records with temporal features: {prepared_df['yoy_change_pct_lag1'].notna().sum():,}")
    logger.info(f"Total features: {len(prepared_df.columns)}")

    feature_breakdown = {
        "Core/Target": [col for col in prepared_df.columns if col in ["year", "month", "yoy_change_pct", "price_psf", "lat", "lon"]],
        "Temporal": [col for col in prepared_df.columns if "lag" in col or "acceleration" in col or "trend_stability" in col],
        "Location/Amenity": [col for col in prepared_df.columns if col.startswith("dist_to_nearest_")],
        "Property": [col for col in prepared_df.columns if col in ["is_hdb", "is_condo", "is_ec", "log_price_psf", "lease_decay_factor"]],
        "Spatial Interaction": [col for col in prepared_df.columns if col in ["dist_mrt_sq", "mrt_x_hawker", "school_x_park", "amenity_density"]],
    }

    for ftype, cols in feature_breakdown.items():
        actual_cols = [col for col in cols if col in prepared_df.columns]
        if actual_cols:
            logger.info(f"  {ftype}: {len(actual_cols)} features")

    logger.info(f"\nTrain set: {len(train_df):,} records × {len(train_df.columns)} total columns")
    logger.info(f"Test set: {len(test_df):,} records × {len(test_df.columns)} total columns")
    logger.info("\n✅ Datasets ready for model training!")
    logger.info("   Next step: uv run python -m scripts.analytics.price_appreciation_modeling.train_models")


if __name__ == "__main__":
    main()
