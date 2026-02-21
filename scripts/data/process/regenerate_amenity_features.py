#!/usr/bin/env python3
"""Regenerate housing multi-amenity features with updated amenity data."""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.core.data_helpers import load_parquet, save_parquet

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculate haversine distance in meters."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1-a))


def main():
    """Regenerate multi-amenity features."""
    logger.info("🚀 Regenerating housing multi-amenity features")

    # Load unique properties (from L2 housing_unique_searched)
    properties_df = load_parquet("L2_housing_unique_searched")
    properties_df = properties_df.dropna(subset=["LATITUDE", "LONGITUDE"])
    properties_df["lon"] = properties_df["LONGITUDE"].astype(float)
    properties_df["lat"] = properties_df["LATITUDE"].astype(float)
    logger.info(f"Loaded {len(properties_df)} unique properties")

    # Load amenities (including new malls)
    amenities_df = load_parquet("L1_amenity")
    amenities_df = amenities_df.dropna(subset=["lat", "lon"])
    amenities_df["lon"] = amenities_df["lon"].astype(float)
    amenities_df["lat"] = amenities_df["lat"].astype(float)
    logger.info(f"Loaded {len(amenities_df)} amenities")
    logger.info(f"Amenity types: {amenities_df['type'].value_counts().to_dict()}")

    # Calculate for each postal code
    amenity_types = amenities_df["type"].unique()
    postal_features = []

    for postal in properties_df["POSTAL"].unique():
        prop_rows = properties_df[properties_df["POSTAL"] == postal]
        if len(prop_rows) == 0:
            continue

        prop_lon = float(prop_rows.iloc[0]["lon"])
        prop_lat = float(prop_rows.iloc[0]["lat"])

        feature = {"POSTAL": postal}

        for amenity_type in amenity_types:
            type_amenities = amenities_df[amenities_df["type"] == amenity_type]

            if len(type_amenities) == 0:
                continue

            # Calculate distances to all amenities of this type
            distances = []
            for _, am in type_amenities.iterrows():
                d = haversine(prop_lon, prop_lat, float(am["lon"]), float(am["lat"]))
                distances.append(d)

            feature[f"dist_to_nearest_{amenity_type}"] = min(distances) if distances else None
            feature[f"{amenity_type}_within_500m"] = sum(1 for d in distances if d <= 500)
            feature[f"{amenity_type}_within_1km"] = sum(1 for d in distances if d <= 1000)
            feature[f"{amenity_type}_within_2km"] = sum(1 for d in distances if d <= 2000)

        postal_features.append(feature)

    postal_df = pd.DataFrame(postal_features)
    logger.info(f"Calculated features for {len(postal_df)} postal codes")

    # Merge back to properties
    result = properties_df.merge(postal_df, on="POSTAL", how="left")

    # Save
    save_parquet(result, "L2_housing_multi_amenity_features", source="Regenerated with mall data")
    logger.info(f"✅ Saved {len(result)} records to housing_multi_amenity_features.parquet")

    # Print summary
    dist_cols = [c for c in result.columns if "dist_to_nearest" in c]
    count_cols = [c for c in result.columns if "_within_" in c]
    logger.info(f"Generated {len(dist_cols)} distance columns: {dist_cols}")
    logger.info(f"Generated {len(count_cols)} count columns")


if __name__ == "__main__":
    main()
