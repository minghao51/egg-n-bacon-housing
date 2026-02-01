#!/usr/bin/env python3
"""Calculate school features - optimized version using KDTree for nearest search."""

import logging
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import Point

from scripts.core.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two lat/lon points."""
    from math import radians, cos, sin, asin, sqrt

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    return c * 6371000


def load_schools() -> pd.DataFrame:
    """Load or geocode schools."""
    school_path = Config.DATA_DIR / "pipeline" / "raw_datagov_school_directory.parquet"
    schools_df = pd.read_parquet(school_path)

    # Check if already geocoded
    if 'latitude' in schools_df.columns and schools_df['latitude'].notna().sum() > 100:
        logger.info(f"Loaded {schools_df['latitude'].notna().sum()} pre-geocoded schools")
        return schools_df

    # Geocode
    logger.info("Geocoding schools...")
    schools_df["latitude"] = None
    schools_df["longitude"] = None

    import requests
    geocoded = 0
    total = len(schools_df)

    for idx, row in schools_df.iterrows():
        postal_code = row.get("postal_code")
        if postal_code and len(str(postal_code).strip()) >= 6:
            try:
                url = "https://www.onemap.gov.sg/api/common/elastic/search"
                params = {"searchVal": str(postal_code).strip(), "returnGeom": "Y", "getAddrDetails": "Y", "pageNum": 1}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if data.get("found", 0) > 0:
                    result = data["results"][0]
                    schools_df.at[idx, "latitude"] = float(result["LATITUDE"])
                    schools_df.at[idx, "longitude"] = float(result["LONGITUDE"])
                    geocoded += 1
            except Exception:
                pass
            time.sleep(0.1)

        if (geocoded + 1) % 50 == 0:
            logger.info(f"Geocoded {geocoded}/{total} schools...")

    logger.info(f"Geocoded {geocoded}/{total} schools")
    return schools_df


def calculate_school_features(
    properties_df: pd.DataFrame,
    schools_df: pd.DataFrame,
    levels: list = ["PRIMARY", "SECONDARY (S1-S5)", "JUNIOR COLLEGE"]
) -> pd.DataFrame:
    """Calculate school features - optimized version."""
    properties_df = properties_df.copy()

    # Prepare school data
    schools_geo = schools_df.dropna(subset=["latitude", "longitude"]).copy()
    if schools_geo.empty:
        logger.warning("No geocoded schools available")
        return properties_df

    schools_by_level = {}
    for level in levels:
        level_schools = schools_geo[schools_geo["mainlevel_code"] == level].copy()
        if not level_schools.empty:
            # Build KD-tree for this level
            coords = list(zip(level_schools["latitude"], level_schools["longitude"]))
            tree = cKDTree(coords)
            schools_by_level[level] = {
                'tree': tree,
                'data': level_schools.reset_index(drop=True),
                'n': len(level_schools)
            }

    level_info = ', '.join([f'{k[:3]}({v["n"]})' for k, v in schools_by_level.items()])
    logger.info(f"Schools by level: {level_info}")

    # Build combined tree for aggregate counts
    all_coords = list(zip(schools_geo["latitude"], schools_geo["longitude"]))
    all_tree = cKDTree(all_coords) if all_coords else None

    # Initialize columns
    for level in levels:
        level_short = level.split()[0].upper()
        for suffix in ['_dist', '_name', '_type', '_dgp', '_zone', '_nature', '_mrt_desc', '_sap', '_autonomous', '_gifted', '_ip']:
            col = f"nearest_school{level_short}{suffix}"
            if col not in properties_df.columns:
                properties_df[col] = None
        for suffix in ['_500m', '_1km', '_2km']:
            col = f"school{level_short}_count{suffix}"
            if col not in properties_df.columns:
                properties_df[col] = 0

    for col in ["school_within_500m", "school_within_1km", "school_within_2km"]:
        if col not in properties_df.columns:
            properties_df[col] = 0

    # Process properties
    props_with_coords = properties_df.dropna(subset=["lat", "lon"])
    total = len(props_with_coords)

    # Convert lat/lon to numpy arrays for faster access
    prop_lats = props_with_coords["lat"].values
    prop_lons = props_with_coords["lon"].values
    prop_indices = props_with_coords.index.values

    for idx in range(len(prop_indices)):
        prop_idx = prop_indices[idx]
        prop_lat = prop_lats[idx]
        prop_lon = prop_lons[idx]

        # Aggregate counts
        if all_tree:
            for radius_m, col in [(500, "school_within_500m"), (1000, "school_within_1km"), (2000, "school_within_2km")]:
                radius_radians = radius_m / 6371000
                count = all_tree.query_ball_point([prop_lat, prop_lon], r=radius_radians)
                properties_df.at[prop_idx, col] = len(count)

        # Per-level features
        for level, school_data in schools_by_level.items():
            level_short = level.split()[0].upper()
            tree = school_data['tree']
            level_df = school_data['data']

            # KDTree nearest search
            dist_radians, nearest_idx = tree.query([prop_lat, prop_lon], k=1)

            # Get school details
            school = level_df.iloc[nearest_idx]
            school_lat = school["latitude"]
            school_lon = school["longitude"]

            # Calculate true haversine distance
            true_dist = haversine_meters(prop_lat, prop_lon, school_lat, school_lon)

            properties_df.at[prop_idx, f"nearest_school{level_short}_dist"] = true_dist
            properties_df.at[prop_idx, f"nearest_school{level_short}_name"] = school.get("school_name")
            properties_df.at[prop_idx, f"nearest_school{level_short}_type"] = school.get("type_code")
            properties_df.at[prop_idx, f"nearest_school{level_short}_dgp"] = school.get("dgp_code")
            properties_df.at[prop_idx, f"nearest_school{level_short}_zone"] = school.get("zone_code")
            properties_df.at[prop_idx, f"nearest_school{level_short}_nature"] = school.get("nature_code")
            properties_df.at[prop_idx, f"nearest_school{level_short}_mrt_desc"] = school.get("mrt_desc")

            sap = school.get("sap_ind")
            autonomous = school.get("autonomous_ind")
            gifted = school.get("gifted_ind")
            ip = school.get("ip_ind")

            properties_df.at[prop_idx, f"nearest_school{level_short}_sap"] = (sap == "Yes") if pd.notna(sap) else None
            properties_df.at[prop_idx, f"nearest_school{level_short}_autonomous"] = (autonomous == "Yes") if pd.notna(autonomous) else None
            properties_df.at[prop_idx, f"nearest_school{level_short}_gifted"] = (gifted == "Yes") if pd.notna(gifted) else None
            properties_df.at[prop_idx, f"nearest_school{level_short}_ip"] = (ip == "Yes") if pd.notna(ip) else None

            # Level-specific counts
            level_coords = list(zip(level_df["latitude"], level_df["longitude"]))
            level_tree = cKDTree(level_coords)

            for radius_m, col in [(500, f"school{level_short}_count_500m"), (1000, f"school{level_short}_count_1km"), (2000, f"school{level_short}_count_2km")]:
                radius_radians = radius_m / 6371000
                count = level_tree.query_ball_point([prop_lat, prop_lon], r=radius_radians)
                properties_df.at[prop_idx, col] = len(count)

        if (idx + 1) % 10000 == 0:
            logger.info(f"Calculated school features for {idx + 1}/{total} properties...")

    return properties_df


def main():
    logger.info("🚀 Calculating school features (optimized)...")

    schools_df = load_schools()
    logger.info(f"Loaded {len(schools_df)} schools")

    property_path = Config.DATA_DIR / "pipeline" / "L3" / "housing_unified.parquet"
    properties_df = pd.read_parquet(property_path)
    logger.info(f"Loaded {len(properties_df)} properties")

    properties_df = calculate_school_features(properties_df, schools_df)

    properties_df.to_parquet(property_path, compression='snappy', index=False)
    logger.info("Saved updated data")

    print("\n📊 School Distance Statistics (meters):")
    for level in ["PRIMARY", "SECONDARY", "JUNIOR"]:
        col = f"nearest_school{level}_dist"
        if col in properties_df.columns:
            dist = properties_df[col].dropna()
            print(f"  {level}: mean={dist.mean():.0f}m, median={dist.median():.0f}m, min={dist.min():.0f}m, max={dist.max():.0f}m")

    print("\n✅ Complete!")


if __name__ == "__main__":
    main()
