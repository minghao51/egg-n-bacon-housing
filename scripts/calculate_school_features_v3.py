#!/usr/bin/env python3
"""Calculate school features - optimized using KDTree for nearest search."""

import logging
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from scripts.core.config import Config

# Constants
DISTANCES = {
    '500m': 500,
    '1km': 1000,
    '2km': 2000,
}

SCHOOL_LEVELS = ["PRIMARY", "SECONDARY (S1-S5)", "JUNIOR COLLEGE"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two lat/lon points using Haversine formula."""
    from math import radians, sin, cos, sqrt, asin

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * asin(sqrt(a)) * 6371000  # Earth radius in meters


def load_schools() -> pd.DataFrame:
    """Load schools, geocoding if necessary and saving results."""
    school_path = Config.DATA_DIR / "pipeline" / "raw_datagov_school_directory.parquet"
    schools_df = pd.read_parquet(school_path)

    # Check if already geocoded
    if 'latitude' in schools_df.columns and schools_df['latitude'].notna().sum() > 100:
        logger.info(f"Loaded {schools_df['latitude'].notna().sum()} pre-geocoded schools")
        return schools_df

    # Geocode and save
    logger.info("Geocoding schools...")
    schools_df = _geocode_schools(schools_df)
    schools_df.to_parquet(school_path, compression='snappy', index=False)
    logger.info("Saved geocoded schools")

    return schools_df


def _geocode_schools(schools_df: pd.DataFrame) -> pd.DataFrame:
    """Geocode school addresses using OneMap API."""
    import requests
    import time

    schools_df["latitude"] = None
    schools_df["longitude"] = None
    geocoded = 0

    for idx, row in schools_df.iterrows():
        postal_code = str(row.get("postal_code", "")).strip()
        if len(postal_code) < 6:
            continue

        try:
            response = requests.get(
                "https://www.onemap.gov.sg/api/common/elastic/search",
                params={
                    "searchVal": postal_code,
                    "returnGeom": "Y",
                    "getAddrDetails": "Y",
                    "pageNum": "1"
                },
                timeout=10
            )
            data = response.json()

            if data.get("found", 0) > 0:
                result = data["results"][0]
                schools_df.at[idx, "latitude"] = float(result["LATITUDE"])
                schools_df.at[idx, "longitude"] = float(result["LONGITUDE"])
                geocoded += 1

        except Exception as e:
            logger.debug(f"Geocoding failed for {postal_code}: {e}")

        if (geocoded + 1) % 50 == 0:
            logger.info(f"Geocoded {geocoded}/{len(schools_df)} schools...")

        time.sleep(0.1)  # Rate limiting

    logger.info(f"Geocoded {geocoded}/{len(schools_df)} schools")
    return schools_df


def _initialize_school_columns(
    df: pd.DataFrame,
    levels: List[str]
) -> pd.DataFrame:
    """Initialize all school-related columns with defaults."""
    # Nearest school columns (NULL)
    for level in levels:
        level_code = level.split()[0]  # PRIMARY, SECONDARY, JUNIOR
        for suffix in ['_dist', '_name', '_type', '_dgp', '_zone',
                      '_nature', '_mrt_desc', '_sap', '_autonomous',
                      '_gifted', '_ip']:
            df[f"nearest_school{level_code}{suffix}"] = None

    # School count columns (0)
    for level in levels:
        level_code = level.split()[0]
        for label in DISTANCES.keys():
            df[f"school{level_code}_count{label}"] = 0

    # Aggregate school counts
    for label in DISTANCES.keys():
        df[f"school_within_{label}"] = 0

    return df


def _get_school_attributes(school: pd.Series) -> Dict[str, any]:
    """Extract school attributes as a dictionary."""
    return {
        'dist': None,  # Calculated separately
        'name': school.get('school_name'),
        'type': school.get('type_code'),
        'dgp': school.get('dgp_code'),
        'zone': school.get('zone_code'),
        'nature': school.get('nature_code'),
        'mrt_desc': school.get('mrt_desc'),
        'sap': (school.get('sap_ind') == "Yes") if pd.notna(school.get('sap_ind')) else None,
        'autonomous': (school.get('autonomous_ind') == "Yes") if pd.notna(school.get('autonomous_ind')) else None,
        'gifted': (school.get('gifted_ind') == "Yes") if pd.notna(school.get('gifted_ind')) else None,
        'ip': (school.get('ip_ind') == "Yes") if pd.notna(school.get('ip_ind')) else None,
    }


def calculate_school_features(
    properties_df: pd.DataFrame,
    schools_df: pd.DataFrame,
    levels: List[str] = SCHOOL_LEVELS
) -> pd.DataFrame:
    """Calculate school features using KDTree for efficient nearest-neighbor search.

    Args:
        properties_df: DataFrame with property data (must have 'lat', 'lon' columns)
        schools_df: DataFrame with school data (must have 'latitude', 'longitude', 'mainlevel_code')
        levels: List of school levels to process

    Returns:
        DataFrame with school features added
    """
    properties_df = properties_df.copy()

    # Filter and prepare school data
    schools_geo = schools_df.dropna(subset=["latitude", "longitude"]).copy()
    if schools_geo.empty:
        logger.warning("No geocoded schools available")
        return properties_df

    # Build KD-trees for each school level
    schools_by_level = {}
    for level in levels:
        level_schools = schools_geo[schools_geo["mainlevel_code"] == level]
        if level_schools.empty:
            continue

        coords = np.column_stack([
            level_schools["latitude"].values,
            level_schools["longitude"].values
        ])

        schools_by_level[level] = {
            'tree': cKDTree(coords),
            'data': level_schools.reset_index(drop=True),
            'coords': coords
        }

    # Build combined tree for aggregate counts
    all_coords = np.column_stack([
        schools_geo["latitude"].values,
        schools_geo["longitude"].values
    ])
    all_tree = cKDTree(all_coords)

    level_summary = ', '.join([
        f"{k[:3]}({v['data'].shape[0]})"
        for k, v in schools_by_level.items()
    ])
    logger.info(f"Schools by level: {level_summary}")

    # Initialize columns
    properties_df = _initialize_school_columns(properties_df, levels)

    # Process properties with coordinates
    props_with_coords = properties_df.dropna(subset=["lat", "lon"])
    total = len(props_with_coords)
    logger.info(f"Processing {total} properties with coordinates...")

    for idx, (prop_idx, prop) in enumerate(props_with_coords.iterrows(), 1):
        prop_lat, prop_lon = prop["lat"], prop["lon"]

        # Aggregate school counts
        for radius_m, col_suffix in DISTANCES.items():
            radius_radians = radius_m / 6371000
            count = all_tree.query_ball_point([prop_lat, prop_lon], r=radius_radians)
            properties_df.at[prop_idx, f"school_within_{col_suffix}"] = len(count)

        # Per-level features
        for level, school_data in schools_by_level.items():
            level_code = level.split()[0]
            tree = school_data['tree']
            level_df = school_data['data']

            # Find nearest school
            dist_radians, nearest_idx = tree.query([prop_lat, prop_lon], k=1)
            nearest_school = level_df.iloc[nearest_idx]

            # Calculate true haversine distance
            true_dist = haversine_distance(
                prop_lat, prop_lon,
                nearest_school["latitude"],
                nearest_school["longitude"]
            )
            properties_df.at[prop_idx, f"nearest_school{level_code}_dist"] = true_dist

            # Get and assign school attributes
            attrs = _get_school_attributes(nearest_school)
            for key, value in attrs.items():
                if key != 'dist':
                    properties_df.at[prop_idx, f"nearest_school{level_code}_{key}"] = value

            # Level-specific school counts
            for radius_m, col_suffix in DISTANCES.items():
                radius_radians = radius_m / 6371000
                count = tree.query_ball_point([prop_lat, prop_lon], r=radius_radians)
                properties_df.at[prop_idx, f"school{level_code}_count{col_suffix}"] = len(count)

        if idx % 10000 == 0:
            logger.info(f"Processed {idx}/{total} properties...")

    return properties_df


def main():
    """Main entry point for school features calculation."""
    logger.info("🚀 Calculating school features...")

    schools_df = load_schools()
    logger.info(f"Loaded {len(schools_df)} schools")

    property_path = Config.DATA_DIR / "pipeline" / "L3" / "housing_unified.parquet"
    properties_df = pd.read_parquet(property_path)
    logger.info(f"Loaded {len(properties_df)} properties")

    properties_df = calculate_school_features(properties_df, schools_df)
    properties_df.to_parquet(property_path, compression='snappy', index=False)
    logger.info("✅ Saved updated data")

    # Print statistics
    logger.info("\n📊 School Distance Statistics (meters):")
    for level in ["PRIMARY", "SECONDARY", "JUNIOR"]:
        col = f"nearest_school{level}_dist"
        if col in properties_df.columns:
            dist = properties_df[col].dropna()
            logger.info(
                f"  {level}: "
                f"mean={dist.mean():.0f}m, "
                f"median={dist.median():.0f}m, "
                f"min={dist.min():.0f}m, "
                f"max={dist.max():.0f}m"
            )


if __name__ == "__main__":
    main()
