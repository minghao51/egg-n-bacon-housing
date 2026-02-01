#!/usr/bin/env python3
"""Calculate school features with proper distance calculation using haversine."""

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


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two lat/lon points."""
    from math import radians, cos, sin, asin, sqrt

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    return c * 6371000  # Earth radius in meters


def geocode_schools_from_parquet(schools_df: pd.DataFrame) -> pd.DataFrame:
    """Geocode schools using postal codes via OneMap API."""
    schools_df = schools_df.copy()
    schools_df["latitude"] = None
    schools_df["longitude"] = None

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
            time.sleep(0.15)

        if (geocoded + 1) % 50 == 0:
            logger.info(f"Geocoded {geocoded}/{total} schools...")

    logger.info(f"Geocoded {geocoded}/{total} schools")
    return schools_df


def calculate_school_features(
    properties_df: pd.DataFrame,
    schools_df: pd.DataFrame,
    levels: list = ["PRIMARY", "SECONDARY (S1-S5)", "JUNIOR COLLEGE"]
) -> pd.DataFrame:
    """Calculate school features with proper haversine distances."""
    properties_df = properties_df.copy()

    # Prepare school data
    schools_geo = schools_df.dropna(subset=["latitude", "longitude"]).copy()
    if schools_geo.empty:
        logger.warning("No geocoded schools available")
        return properties_df

    # Group schools by level
    schools_by_level = {}
    for level in levels:
        level_schools = schools_geo[schools_geo["mainlevel_code"] == level].copy()
        if not level_schools.empty:
            schools_by_level[level] = level_schools

    logger.info(f"Schools by level: {', '.join(f'{k}({len(v)})' for k,v in schools_by_level.items())}")

    # Initialize columns
    for level in levels:
        level_short = level.split()[0].upper()

        properties_df[f"nearest_school_{level_short}_dist"] = None
        properties_df[f"nearest_school_{level_short}_name"] = None
        properties_df[f"nearest_school_{level_short}_type"] = None
        properties_df[f"nearest_school_{level_short}_dgp"] = None
        properties_df[f"nearest_school_{level_short}_zone"] = None
        properties_df[f"nearest_school_{level_short}_nature"] = None
        properties_df[f"nearest_school_{level_short}_mrt_desc"] = None
        properties_df[f"nearest_school_{level_short}_sap"] = None
        properties_df[f"nearest_school_{level_short}_autonomous"] = None
        properties_df[f"nearest_school_{level_short}_gifted"] = None
        properties_df[f"nearest_school_{level_short}_ip"] = None
        properties_df[f"school_{level_short}_count_500m"] = 0
        properties_df[f"school_{level_short}_count_1km"] = 0
        properties_df[f"school_{level_short}_count_2km"] = 0

    # Aggregate counts
    properties_df["school_within_500m"] = 0
    properties_df["school_within_1km"] = 0
    properties_df["school_within_2km"] = 0

    # Build KD-tree for aggregate counts (all schools)
    all_coords = list(zip(schools_geo["latitude"], schools_geo["longitude"]))
    if all_coords:
        all_tree = cKDTree(all_coords)
    else:
        all_tree = None

    # Calculate features for each property
    props_with_coords = properties_df.dropna(subset=["lat", "lon"])
    total = len(props_with_coords)

    for idx, (_, prop) in enumerate(props_with_coords.iterrows()):
        prop_lat = prop["lat"]
        prop_lon = prop["lon"]

        # Aggregate school counts
        if all_tree:
            for radius_m, col in [(500, "school_within_500m"), (1000, "school_within_1km"), (2000, "school_within_2km")]:
                radius_radians = radius_m / 6371000
                count = all_tree.query_ball_point([prop_lat, prop_lon], r=radius_radians)
                properties_df.at[prop.name, col] = len(count)

        # Per-level features
        for level, level_schools in schools_by_level.items():
            level_short = level.split()[0].upper()

            # Find nearest school using haversine
            min_dist = float('inf')
            nearest_idx = None

            for sidx, (_, school) in enumerate(level_schools.iterrows()):
                dist = haversine_meters(
                    prop_lat, prop_lon,
                    school["latitude"], school["longitude"]
                )
                if dist < min_dist:
                    min_dist = dist
                    nearest_idx = sidx

            if nearest_idx is not None:
                school = level_schools.iloc[nearest_idx]

                properties_df.at[prop.name, f"nearest_school_{level_short}_dist"] = min_dist
                properties_df.at[prop.name, f"nearest_school_{level_short}_name"] = school.get("school_name")
                properties_df.at[prop.name, f"nearest_school_{level_short}_type"] = school.get("type_code")
                properties_df.at[prop.name, f"nearest_school_{level_short}_dgp"] = school.get("dgp_code")
                properties_df.at[prop.name, f"nearest_school_{level_short}_zone"] = school.get("zone_code")
                properties_df.at[prop.name, f"nearest_school_{level_short}_nature"] = school.get("nature_code")
                properties_df.at[prop.name, f"nearest_school_{level_short}_mrt_desc"] = school.get("mrt_desc")

                sap = school.get("sap_ind")
                autonomous = school.get("autonomous_ind")
                gifted = school.get("gifted_ind")
                ip = school.get("ip_ind")

                properties_df.at[prop.name, f"nearest_school_{level_short}_sap"] = (sap == "Yes") if pd.notna(sap) else None
                properties_df.at[prop.name, f"nearest_school_{level_short}_autonomous"] = (autonomous == "Yes") if pd.notna(autonomous) else None
                properties_df.at[prop.name, f"nearest_school_{level_short}_gifted"] = (gifted == "Yes") if pd.notna(gifted) else None
                properties_df.at[prop.name, f"nearest_school_{level_short}_ip"] = (ip == "Yes") if pd.notna(ip) else None

                # Count schools by level within radii
                level_coords = list(zip(level_schools["latitude"], level_schools["longitude"]))
                level_tree = cKDTree(level_coords)

                for radius_m, col in [(500, f"school_{level_short}_count_500m"), (1000, f"school_{level_short}_count_1km"), (2000, f"school_{level_short}_count_2km")]:
                    radius_radians = radius_m / 6371000
                    count = level_tree.query_ball_point([prop_lat, prop_lon], r=radius_radians)
                    properties_df.at[prop.name, col] = len(count)

        if (idx + 1) % 10000 == 0:
            logger.info(f"Calculated school features for {idx + 1}/{total} properties...")

    return properties_df


def calculate_school_score(properties_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate school accessibility score."""
    properties_df = properties_df.copy()

    def dist_score(dist_m):
        if pd.isna(dist_m) or dist_m > 2000:
            return 0
        return max(0, min(100, 100 * (1 - dist_m / 2000)))

    def quality_score(row, level_short):
        score = 0
        for indicator in ['sap', 'autonomous', 'gifted', 'ip']:
            col = f"nearest_school_{level_short}_{indicator}"
            if col in row.index and row[col] is True:
                score += 25
        return min(100, score)

    if 'nearest_school_PRIMARY_dist' in properties_df.columns:
        properties_df['school_primary_dist_score'] = properties_df['nearest_school_PRIMARY_dist'].apply(dist_score)
        properties_df['school_primary_quality_score'] = properties_df.apply(
            lambda r: quality_score(r, 'PRIMARY'), axis=1
        )

    if 'nearest_school_SECONDARY_dist' in properties_df.columns:
        properties_df['school_secondary_dist_score'] = properties_df['nearest_school_SECONDARY_dist'].apply(dist_score)
        properties_df['school_secondary_quality_score'] = properties_df.apply(
            lambda r: quality_score(r, 'SECONDARY'), axis=1
        )

    if 'school_within_1km' in properties_df.columns:
        properties_df['school_density_score'] = properties_df['school_within_1km'].apply(
            lambda x: min(100, x * 10) if pd.notna(x) else 0
        )

    score_cols = []
    for col in ['school_primary_dist_score', 'school_secondary_dist_score', 'school_density_score']:
        if col in properties_df.columns:
            score_cols.append(col)

    if score_cols:
        weights = {'school_primary_dist_score': 0.4, 'school_secondary_dist_score': 0.3, 'school_density_score': 0.3}
        properties_df['school_accessibility_score'] = sum(
            properties_df[col].fillna(0) * weights.get(col, 0) for col in score_cols
        )

    return properties_df


def main():
    logger.info("🚀 Calculating school features with proper haversine distances...")

    # Load schools
    school_path = Config.DATA_DIR / "pipeline" / "raw_datagov_school_directory.parquet"
    schools_df = pd.read_parquet(school_path)
    logger.info(f"Loaded {len(schools_df)} schools")

    # Geocode schools
    logger.info("Geocoding schools...")
    schools_df = geocode_schools_from_parquet(schools_df)

    # Save geocoded schools
    schools_output = Config.DATA_DIR / "manual" / "csv" / "datagov" / "SchoolsMOE.geojson"
    schools_geo = schools_df.dropna(subset=["latitude", "longitude"]).copy()
    schools_geo["geometry"] = schools_geo.apply(
        lambda row: Point(row["longitude"], row["latitude"]), axis=1
    )
    schools_gdf = gpd.GeoDataFrame(schools_geo, geometry="geometry", crs="EPSG:4326")
    schools_gdf.to_file(schools_output, driver="GeoJSON")
    logger.info(f"Saved geocoded schools to {schools_output}")

    # Load property data
    property_path = Config.DATA_DIR / "pipeline" / "L3" / "housing_unified.parquet"
    properties_df = pd.read_parquet(property_path)
    logger.info(f"Loaded {len(properties_df)} properties")

    # Calculate school features
    logger.info("Calculating school features...")
    properties_df = calculate_school_features(properties_df, schools_df)

    # Calculate school score
    logger.info("Calculating school accessibility score...")
    properties_df = calculate_school_score(properties_df)

    # Save
    properties_df.to_parquet(property_path, compression='snappy', index=False)
    logger.info(f"Updated property data with school features")

    # Summary
    print("\n📊 School Distance Statistics (meters):")
    for level in ["PRIMARY", "SECONDARY", "JUNIOR"]:
        col = f"nearest_school_{level}_dist"
        if col in properties_df.columns:
            dist = properties_df[col].dropna()
            print(f"  {level}: mean={dist.mean():.0f}m, median={dist.median():.0f}m, min={dist.min():.0f}m, max={dist.max():.0f}m")

    print("\n✅ School feature calculation complete!")


if __name__ == "__main__":
    main()
