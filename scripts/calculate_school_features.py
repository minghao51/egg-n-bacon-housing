#!/usr/bin/env python3
"""Calculate school proximity features for properties.

This script:
1. Loads the MOE school directory
2. Geocodes schools using postal codes (OneMap API)
3. Calculates distance from each property to nearest schools by level
4. Saves school features to parquet
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
import requests
from scipy.spatial import cKDTree
from shapely.geometry import Point

from scripts.core.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def geocode_postal_code(postal_code: str) -> Optional[tuple]:
    """Convert Singapore postal code to lat/lon using OneMap API."""
    if pd.isna(postal_code) or len(str(postal_code).strip()) < 6:
        return None

    postal_code = str(postal_code).strip()

    try:
        url = f"https://www.onemap.gov.sg/api/common/elastic/search"
        params = {
            "searchVal": postal_code,
            "returnGeom": "Y",
            "getAddrDetails": "Y",
            "pageNum": 1
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get("found", 0) > 0:
            result = data["results"][0]
            lat = float(result["LATITUDE"])
            lon = float(result["LONGITUDE"])
            return (lat, lon)
    except Exception as e:
        logger.debug(f"Geocoding error for {postal_code}: {e}")

    return None


def geocode_all_schools(schools_df: pd.DataFrame) -> pd.DataFrame:
    """Geocode all schools using postal codes with rate limiting."""
    schools_df = schools_df.copy()
    schools_df["latitude"] = None
    schools_df["longitude"] = None

    total = len(schools_df)
    geocoded = 0

    for idx, row in schools_df.iterrows():
        postal_code = row.get("postal_code")
        if postal_code:
            coords = geocode_postal_code(postal_code)
            if coords:
                schools_df.at[idx, "latitude"] = coords[0]
                schools_df.at[idx, "longitude"] = coords[1]
                geocoded += 1

        # Rate limiting to respect API
        time.sleep(0.2)

        if (geocoded + 1) % 50 == 0:
            logger.info(f"Geocoded {geocoded}/{total} schools...")

    logger.info(f"Geocoded {geocoded}/{total} schools ({100*geocoded/total:.1f}%)")
    return schools_df


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in meters."""
    from math import radians, cos, sin, asin, sqrt

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    r = 6371000  # Earth radius in meters
    return c * r


def radians_to_meters(radians: float) -> float:
    """Convert radians to meters (Earth radius = 6,371,000m)."""
    return radians * 6371000


def calculate_school_features(
    properties_df: pd.DataFrame,
    schools_df: pd.DataFrame,
    levels: list = ["PRIMARY", "SECONDARY (S1-S5)", "JUNIOR COLLEGE"]
) -> pd.DataFrame:
    """Calculate comprehensive school features similar to MRT features.

    Features include:
    - Distance to nearest school (by level)
    - School type, name, and attributes
    - School quality indicators (SAP, Autonomous, Gifted, IP)
    - Total school counts within radii
    - School accessibility score
    """
    properties_df = properties_df.copy()

    # Prepare school data by level
    schools_by_level = {}
    for level in levels:
        level_schools = schools_df[
            schools_df["mainlevel_code"] == level
        ].dropna(subset=["latitude", "longitude"]).copy()
        if not level_schools.empty:
            coords = list(zip(
                level_schools["latitude"],
                level_schools["longitude"]
            ))
            schools_by_level[level] = {
                'coords': coords,
                'data': level_schools,
                'n': len(level_schools)
            }

    # Build KD-tree for each level
    trees_by_level = {}
    for level, school_data in schools_by_level.items():
        if school_data['coords']:
            tree = cKDTree(school_data['coords'])
            trees_by_level[level] = (tree, school_data['data'], school_data['n'])

    # Initialize columns for each level
    for level in levels:
        level_key = level.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_").upper()
        level_short = level.split()[0].upper()  # PRIMARY -> PRIMARY, SECONDARY (S1-S5) -> SECONDARY

        # Distance to nearest school of this level
        properties_df[f"nearest_school_{level_short}_dist"] = None

        # School details for nearest school of this level
        properties_df[f"nearest_school_{level_short}_name"] = None
        properties_df[f"nearest_school_{level_short}_type"] = None
        properties_df[f"nearest_school_{level_short}_dgp"] = None  # Town area
        properties_df[f"nearest_school_{level_short}_zone"] = None  # Zone (NORTH/SOUTH/EAST/WEST)
        properties_df[f"nearest_school_{level_short}_nature"] = None  # CO-ED/GIRLS/BOYS
        properties_df[f"nearest_school_{level_short}_mrt_desc"] = None  # Nearest MRT

        # Quality indicators
        properties_df[f"nearest_school_{level_short}_sap"] = None
        properties_df[f"nearest_school_{level_short}_autonomous"] = None
        properties_df[f"nearest_school_{level_short}_gifted"] = None
        properties_df[f"nearest_school_{level_short}_ip"] = None

    # Aggregate school counts (all levels combined)
    properties_df["school_within_500m"] = 0
    properties_df["school_within_1km"] = 0
    properties_df["school_within_2km"] = 0

    # Calculate features for each property
    properties_with_coords = properties_df.dropna(subset=["lat", "lon"])
    total = len(properties_with_coords)

    # Build combined tree for total counts
    all_coords = []
    for level, school_data in schools_by_level.items():
        all_coords.extend(school_data['coords'])
    if all_coords:
        combined_tree = cKDTree(all_coords)
    else:
        combined_tree = None

    for idx, (_, prop) in enumerate(properties_with_coords.iterrows()):
        prop_lat = prop["lat"]
        prop_lon = prop["lon"]

        # Aggregate school counts
        if combined_tree:
            for radius_m in [500, 1000, 2000]:
                radius_radians = radius_m / 6371000
                count = combined_tree.query_ball_point([prop_lat, prop_lon], r=radius_radians)
                if radius_m == 500:
                    properties_df.at[prop.name, "school_within_500m"] = len(count)
                elif radius_m == 1000:
                    properties_df.at[prop.name, "school_within_1km"] = len(count)
                else:
                    properties_df.at[prop.name, "school_within_2km"] = len(count)

        # Features per level
        for level, (tree, school_data, n_schools) in trees_by_level.items():
            if n_schools == 0:
                continue

            level_key = level.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_").upper()
            level_short = level.split()[0].upper()

            # Query nearest school (returns index into coords)
            dist_radians, nearest_idx = tree.query([prop_lat, prop_lon], k=1)
            dist_meters = radians_to_meters(dist_radians)

            # Get school details
            school_row = school_data.iloc[nearest_idx]

            # Distance
            properties_df.at[prop.name, f"nearest_school_{level_short}_dist"] = dist_meters

            # School details
            properties_df.at[prop.name, f"nearest_school_{level_short}_name"] = school_row.get("school_name")
            properties_df.at[prop.name, f"nearest_school_{level_short}_type"] = school_row.get("type_code")
            properties_df.at[prop.name, f"nearest_school_{level_short}_dgp"] = school_row.get("dgp_code")
            properties_df.at[prop.name, f"nearest_school_{level_short}_zone"] = school_row.get("zone_code")
            properties_df.at[prop.name, f"nearest_school_{level_short}_nature"] = school_row.get("nature_code")
            properties_df.at[prop.name, f"nearest_school_{level_short}_mrt_desc"] = school_row.get("mrt_desc")

            # Quality indicators (convert "Yes"/"No" to boolean)
            sap = school_row.get("sap_ind")
            autonomous = school_row.get("autonomous_ind")
            gifted = school_row.get("gifted_ind")
            ip = school_row.get("ip_ind")

            properties_df.at[prop.name, f"nearest_school_{level_short}_sap"] = (sap == "Yes") if pd.notna(sap) else None
            properties_df.at[prop.name, f"nearest_school_{level_short}_autonomous"] = (autonomous == "Yes") if pd.notna(autonomous) else None
            properties_df.at[prop.name, f"nearest_school_{level_short}_gifted"] = (gifted == "Yes") if pd.notna(gifted) else None
            properties_df.at[prop.name, f"nearest_school_{level_short}_ip"] = (ip == "Yes") if pd.notna(ip) else None

        if (idx + 1) % 10000 == 0:
            logger.info(f"Calculated school features for {idx + 1}/{total} properties...")

    return properties_df


def calculate_school_score(properties_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate composite school accessibility score.

    Score factors:
    - Distance to nearest primary school (most important for families)
    - Distance to nearest secondary school
    - School quality (SAP, Autonomous, Gifted, IP indicators)
    - Number of schools within 1km
    """
    properties_df = properties_df.copy()

    # Distance scores (closer = higher score, max 100)
    def dist_score(dist_m):
        if pd.isna(dist_m) or dist_m > 2000:
            return 0
        return max(0, min(100, 100 * (1 - dist_m / 2000)))

    # Quality score (0-25 per indicator)
    def quality_score(row, level_short):
        score = 0
        for indicator in ['sap', 'autonomous', 'gifted', 'ip']:
            col = f"nearest_school_{level_short}_{indicator}"
            if col in row.index and row[col] is True:
                score += 25
        return min(100, score)  # Max 100

    # Primary school score (weighted)
    if 'nearest_school_PRIMARY_dist' in properties_df.columns:
        properties_df['school_primary_dist_score'] = properties_df['nearest_school_PRIMARY_dist'].apply(dist_score)
        properties_df['school_primary_quality_score'] = properties_df.apply(
            lambda r: quality_score(r, 'PRIMARY'), axis=1
        )

    # Secondary school score
    if 'nearest_school_SECONDARY_dist' in properties_df.columns:
        properties_df['school_secondary_dist_score'] = properties_df['nearest_school_SECONDARY_dist'].apply(dist_score)
        properties_df['school_secondary_quality_score'] = properties_df.apply(
            lambda r: quality_score(r, 'SECONDARY'), axis=1
        )

    # JC school score
    if 'nearest_school_JUNIOR_dist' in properties_df.columns:
        properties_df['school_jc_dist_score'] = properties_df['nearest_school_JUNIOR_dist'].apply(dist_score)

    # Density score (schools within 1km)
    if 'school_within_1km' in properties_df.columns:
        properties_df['school_density_score'] = properties_df['school_within_1km'].apply(
            lambda x: min(100, x * 10) if pd.notna(x) else 0
        )

    # Composite school score
    score_cols = []
    for col in ['school_primary_dist_score', 'school_secondary_dist_score', 'school_density_score']:
        if col in properties_df.columns:
            score_cols.append(col)

    if score_cols:
        # Weighted average: 40% primary distance, 30% secondary distance, 30% density
        weights = {'school_primary_dist_score': 0.4, 'school_secondary_dist_score': 0.3, 'school_density_score': 0.3}
        properties_df['school_accessibility_score'] = sum(
            properties_df[col].fillna(0) * weights.get(col, 0) for col in score_cols
        )

    return properties_df


def main():
    """Main pipeline for school feature calculation."""
    logger.info("🚀 Starting school feature calculation")

    # Load school directory
    school_path = Config.DATA_DIR / "pipeline" / "raw_datagov_school_directory.parquet"
    if not school_path.exists():
        school_path = Config.DATA_DIR / "parquets" / "L1" / "raw_datagov_school_directory.parquet"
    if not school_path.exists():
        logger.error(f"School directory not found: {school_path}")
        logger.info("Run L0_collect.py first to download school data")
        return

    schools_df = pd.read_parquet(school_path)
    logger.info(f"Loaded {len(schools_df)} schools")

    # Geocode schools
    logger.info("Geocoding schools...")
    schools_df = geocode_all_schools(schools_df)

    # Save geocoded schools as GeoJSON
    schools_output = Config.DATA_DIR / "manual" / "csv" / "datagov" / "SchoolsMOE.geojson"

    # Convert to GeoDataFrame
    schools_geo = schools_df.dropna(subset=["latitude", "longitude"]).copy()
    schools_geo["geometry"] = schools_geo.apply(
        lambda row: Point(row["longitude"], row["latitude"]), axis=1
    )
    schools_gdf = gpd.GeoDataFrame(schools_geo, geometry="geometry", crs="EPSG:4326")
    schools_gdf.to_file(schools_output, driver="GeoJSON")
    logger.info(f"Saved geocoded schools to {schools_output}")

    # Load property data
    property_path = Config.DATA_DIR / "pipeline" / "L3" / "housing_unified.parquet"
    if not property_path.exists():
        property_path = Config.DATA_DIR / "parquets" / "L3" / "housing_unified.parquet"
    if not property_path.exists():
        logger.error(f"Property data not found: {property_path}")
        return

    properties_df = pd.read_parquet(property_path)
    logger.info(f"Loaded {len(properties_df)} properties")

    # Calculate school distances
    logger.info("Calculating school features...")
    properties_df = calculate_school_features(properties_df, schools_df)

    # Calculate school accessibility score
    logger.info("Calculating school accessibility score...")
    properties_df = calculate_school_score(properties_df)

    # Save enhanced property data
    properties_df.to_parquet(property_path)
    logger.info(f"Updated property data with school features")

    # Create summary
    school_summary = schools_df.groupby("mainlevel_code").agg({
        "school_name": "count",
        "latitude": "mean",
        "longitude": "mean"
    }).rename(columns={"school_name": "count"})

    logger.info("\n📊 School Summary by Level:")
    print(school_summary)

    logger.info("\n✅ School feature calculation complete")


if __name__ == "__main__":
    main()
