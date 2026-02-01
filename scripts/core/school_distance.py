#!/usr/bin/env python3
"""School distance calculation utilities - optimized like MRT module.

This module provides functions for:
- Loading school data from parquet
- Calculating nearest school for properties
- Adding school distance features to datasets
"""

import logging
from pathlib import Path
from typing import List

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from scripts.core.config import Config

logger = logging.getLogger(__name__)


def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculate the great circle distance between two points in meters."""
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371000
    return c * r


def load_schools(school_parquet_path: Path = None) -> pd.DataFrame:
    """Load school data from parquet and prepare for distance calculation.

    Args:
        school_parquet_path: Path to school parquet file.
            Defaults to data/pipeline/raw_datagov_school_directory.parquet

    Returns:
        DataFrame with columns: school_name, lat, lon, mainlevel_code, type_code,
                               dgp_code, zone_code, nature_code, sap_ind, autonomous_ind, gifted_ind, ip_ind
    """
    if school_parquet_path is None:
        school_parquet_path = Config.DATA_DIR / "pipeline" / "raw_datagov_school_directory.parquet"

    if not school_parquet_path.exists():
        logger.warning(f"School parquet not found: {school_parquet_path}")
        return pd.DataFrame()

    df = pd.read_parquet(school_parquet_path)

    # Check if already geocoded
    if 'latitude' not in df.columns:
        logger.warning("School data not geocoded - run geocoding first")
        return pd.DataFrame()

    # Prepare clean dataframe
    schools = df.dropna(subset=['latitude', 'longitude']).copy()
    schools = schools.rename(columns={
        'latitude': 'lat',
        'longitude': 'lon',
        'mainlevel_code': 'level',
        'type_code': 'type',
        'dgp_code': 'town',
        'zone_code': 'zone',
        'nature_code': 'nature',
        'mrt_desc': 'nearest_mrt'
    })

    # Convert quality indicators to boolean
    for col in ['sap_ind', 'autonomous_ind', 'gifted_ind', 'ip_ind']:
        if col in schools.columns:
            schools[col] = schools[col] == 'Yes'

    logger.info(f"Loaded {len(schools)} geocoded schools")
    logger.info(f"  By level: {schools['level'].value_counts().to_dict()}")

    return schools


def calculate_nearest_school(
    properties_df: pd.DataFrame,
    schools_df: pd.DataFrame = None,
    levels: List[str] = None,
    show_progress: bool = True
) -> pd.DataFrame:
    """Calculate nearest school for each property by level.

    Uses KD-tree for efficient nearest neighbor search.

    Args:
        properties_df: DataFrame with lat/lon columns
        schools_df: Schools DataFrame with lat/lon columns. If None, loads from default path.
        levels: School levels to calculate (e.g., ['PRIMARY', 'SECONDARY (S1-S5)'])
        show_progress: Show progress indicators

    Returns:
        DataFrame with new columns added for each level:
        - nearest_school_{LEVEL}_name: Name of closest school
        - nearest_school_{LEVEL}_dist: Distance in meters to closest school
        - nearest_school_{LEVEL}_type: School type (Government/Govt-Aided)
        - nearest_school_{LEVEL}_town: Town area
        - nearest_school_{LEVEL}_zone: Zone (NORTH/SOUTH/EAST/WEST)
        - nearest_school_{LEVEL}_nature: CO-ED/GIRLS/BOYS
        - nearest_school_{LEVEL}_mrt_desc: Nearest MRT
        - nearest_school_{LEVEL}_sap: SAP school indicator
        - nearest_school_{LEVEL}_autonomous: Autonomous indicator
        - nearest_school_{LEVEL}_gifted: Gifted indicator
        - nearest_school_{LEVEL}_ip: IP indicator
        - school_{LEVEL}_count_500m: Number of schools within 500m
        - school_{LEVEL}_count_1km: Number of schools within 1km
        - school_{LEVEL}_count_2km: Number of schools within 2km
    """
    logger.info("Calculating nearest schools...")

    if levels is None:
        levels = ['PRIMARY', 'SECONDARY (S1-S5)', 'JUNIOR COLLEGE']

    # Load schools if not provided
    if schools_df is None or schools_df.empty:
        schools_df = load_schools()

    if schools_df.empty:
        logger.warning("No school data available")
        return properties_df

    # Check required columns
    if 'lat' not in properties_df.columns or 'lon' not in properties_df.columns:
        logger.error("properties_df must have 'lat' and 'lon' columns")
        return properties_df

    # Ensure lat/lon are numeric
    properties_df = properties_df.copy()
    properties_df['lat'] = pd.to_numeric(properties_df['lat'], errors='coerce')
    properties_df['lon'] = pd.to_numeric(properties_df['lon'], errors='coerce')

    # Drop rows with invalid coordinates
    before_count = len(properties_df)
    properties_df = properties_df.dropna(subset=['lat', 'lon'])
    after_count = len(properties_df)
    if before_count != after_count:
        logger.warning(f"Dropped {before_count - after_count} rows with invalid coordinates")

    # Get property coordinates
    property_coords = properties_df[['lon', 'lat']].values

    # Aggregate counts across all schools
    all_coords = schools_df[['lon', 'lat']].values
    all_tree = cKDTree(all_coords)

    for radius_m, col in [(500, 'school_within_500m'), (1000, 'school_within_1km'), (2000, 'school_within_2km')]:
        if col not in properties_df.columns:
            properties_df[col] = 0
        radius_radians = radius_m / 6371000
        # Query ball point and count
        counts = np.array([len(all_tree.query_ball_point(coord, r=radius_radians)) for coord in property_coords])
        properties_df[col] = counts

    # Process each school level
    for level in levels:
        level_schools = schools_df[schools_df['level'] == level].copy()
        if level_schools.empty:
            logger.info(f"  No schools found for level: {level}")
            continue

        level_short = level.split()[0].upper()

        logger.info(f"  Processing {level}: {len(level_schools)} schools")

        # Build KD-tree for this level
        level_coords = level_schools[['lon', 'lat']].values
        tree = cKDTree(level_coords)

        # Query nearest school for all properties
        distances_radians, indices = tree.query(property_coords, k=1)

        # Get nearest school info
        nearest = level_schools.iloc[indices]

        # Calculate accurate haversine distances
        nearest_coords = nearest[['lon', 'lat']].values
        distances = [
            haversine_distance(lon1, lat1, lon2, lat2)
            for lon1, lat1, lon2, lat2 in zip(
                property_coords[:, 0],
                property_coords[:, 1],
                nearest_coords[:, 0],
                nearest_coords[:, 1]
            )
        ]

        # Add columns
        properties_df[f'nearest_school_{level_short}_name'] = nearest['school_name'].values
        properties_df[f'nearest_school_{level_short}_dist'] = distances
        properties_df[f'nearest_school_{level_short}_type'] = nearest['type'].values
        properties_df[f'nearest_school_{level_short}_town'] = nearest['town'].values
        properties_df[f'nearest_school_{level_short}_zone'] = nearest['zone'].values
        properties_df[f'nearest_school_{level_short}_nature'] = nearest['nature'].values
        properties_df[f'nearest_school_{level_short}_mrt_desc'] = nearest['nearest_mrt'].values
        properties_df[f'nearest_school_{level_short}_sap'] = nearest['sap_ind'].values
        properties_df[f'nearest_school_{level_short}_autonomous'] = nearest['autonomous_ind'].values
        properties_df[f'nearest_school_{level_short}_gifted'] = nearest['gifted_ind'].values
        properties_df[f'nearest_school_{level_short}_ip'] = nearest['ip_ind'].values

        # Count schools within radii
        for radius_m, col in [(500, f'school_{level_short}_count_500m'),
                              (1000, f'school_{level_short}_count_1km'),
                              (2000, f'school_{level_short}_count_2km')]:
            if col not in properties_df.columns:
                properties_df[col] = 0
            radius_radians = radius_m / 6371000
            counts = np.array([len(tree.query_ball_point(coord, r=radius_radians)) for coord in property_coords])
            properties_df[col] = counts

        # Log stats
        dist_arr = np.array(distances)
        logger.info(f"    Mean distance: {dist_arr.mean():.0f}m, Median: {np.median(dist_arr):.0f}m")

    # Log aggregate stats
    logger.info(f"Added school distance features:")
    logger.info(f"  Mean schools within 1km: {properties_df['school_within_1km'].mean():.1f}")
    logger.info(f"  Mean schools within 2km: {properties_df['school_within_2km'].mean():.1f}")

    return properties_df


def calculate_school_score(properties_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate school accessibility score.

    Args:
        properties_df: DataFrame with school distance columns

    Returns:
        DataFrame with school accessibility score added
    """
    properties_df = properties_df.copy()

    def dist_score(dist_m):
        if pd.isna(dist_m) or dist_m > 2000:
            return 0
        return max(0, min(100, 100 * (1 - dist_m / 2000)))

    def quality_score(row, level_short):
        score = 0
        for indicator in ['sap', 'autonomous', 'gifted', 'ip']:
            col = f'nearest_school_{level_short}_{indicator}'
            if col in row.index and row[col] is True:
                score += 25
        return min(100, score)

    # Primary school score
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

    # Density score
    if 'school_within_1km' in properties_df.columns:
        properties_df['school_density_score'] = properties_df['school_within_1km'].apply(
            lambda x: min(100, x * 10) if pd.notna(x) else 0
        )

    # Composite score
    score_cols = []
    for col in ['school_primary_dist_score', 'school_secondary_dist_score', 'school_density_score']:
        if col in properties_df.columns:
            score_cols.append(col)

    if score_cols:
        weights = {'school_primary_dist_score': 0.4, 'school_secondary_dist_score': 0.3, 'school_density_score': 0.3}
        properties_df['school_accessibility_score'] = sum(
            properties_df[col].fillna(0) * weights.get(col, 0) for col in score_cols
        )
        logger.info(f"  Mean school accessibility score: {properties_df['school_accessibility_score'].mean():.1f}")

    return properties_df


def run_school_feature_pipeline():
    """Run complete school feature calculation pipeline."""
    logger.info("=" * 50)
    logger.info("School Feature Calculation Pipeline")
    logger.info("=" * 50)

    # Load property data
    property_path = Config.DATA_DIR / "pipeline" / "L3" / "housing_unified.parquet"
    properties_df = pd.read_parquet(property_path)
    logger.info(f"Loaded {len(properties_df):,} properties")

    # Load schools
    schools_df = load_schools()
    if schools_df.empty:
        logger.error("No school data available")
        return

    # Calculate nearest school features
    properties_df = calculate_nearest_school(properties_df, schools_df)

    # Calculate school scores
    properties_df = calculate_school_score(properties_df)

    # Save
    properties_df.to_parquet(property_path, compression='snappy', index=False)
    logger.info(f"Saved updated data to {property_path}")

    # Summary
    print("\n📊 School Distance Summary (meters):")
    for level in ['PRIMARY', 'SECONDARY', 'JUNIOR']:
        col = f'nearest_school_{level}_dist'
        if col in properties_df.columns:
            dist = properties_df[col].dropna()
            print(f"  {level}: mean={dist.mean():.0f}m, median={dist.median():.0f}m, min={dist.min():.0f}m, max={dist.max():.0f}m")

    print(f"\n📊 School Accessibility Score: {properties_df['school_accessibility_score'].mean():.1f}")
    print("✅ School feature pipeline complete!")


if __name__ == "__main__":
    run_school_feature_pipeline()
