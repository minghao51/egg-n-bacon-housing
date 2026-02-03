#!/usr/bin/env python3
"""Calculate school features - optimized using KDTree for nearest search."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from rapidfuzz import process, fuzz
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

    # Ensure coordinates are floats
    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
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


def load_school_tiers() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load school tier CSV files.

    Returns:
        Tuple of (primary_tiers, secondary_tiers) DataFrames
    """
    csv_dir = Config.DATA_DIR / "manual" / "csv"

    primary_path = csv_dir / "school_tiers_primary.csv"
    secondary_path = csv_dir / "school_tiers_secondary.csv"

    primary_tiers = pd.DataFrame()
    secondary_tiers = pd.DataFrame()

    if primary_path.exists():
        primary_tiers = pd.read_csv(primary_path)
        logger.info(f"Loaded {len(primary_tiers)} primary school tiers")
    else:
        logger.warning(f"Primary school tiers not found: {primary_path}")

    if secondary_path.exists():
        secondary_tiers = pd.read_csv(secondary_path)
        logger.info(f"Loaded {len(secondary_tiers)} secondary school tiers")
    else:
        logger.warning(f"Secondary school tiers not found: {secondary_path}")

    return primary_tiers, secondary_tiers


def calculate_primary_quality_score(row: pd.Series) -> float:
    """Calculate quality score for primary schools (0-10 scale).

    Args:
        row: School tier data row

    Returns:
        Quality score from 0-10
    """
    score = 0.0

    # GEP programme
    if str(row.get('gep', 'No')).upper() == 'YES':
        score += 2.5

    # SAP status
    if str(row.get('sap', 'No')).upper() == 'YES':
        score += 2.0

    # Tier classification
    tier = int(row.get('tier', 3))
    if tier == 1:
        score += 3.0
    elif tier == 2:
        score += 2.0
    elif tier == 3:
        score += 1.0

    # Popularity (Phase 2B applicants per vacancy)
    popularity = row.get('popularity_p2b', None)
    if pd.notna(popularity) and popularity != 'High':
        try:
            pop_val = float(popularity)
            score += min(pop_val / 3 * 0.5, 0.5)
        except (ValueError, TypeError):
            pass
    elif popularity == 'High':
        score += 0.5

    return min(score, 10.0)


def calculate_secondary_quality_score(row: pd.Series) -> float:
    """Calculate quality score for secondary schools (0-10 scale).

    Args:
        row: School tier data row

    Returns:
        Quality score from 0-10
    """
    score = 0.0

    # IP track
    if str(row.get('ip', 'No')).upper() == 'YES':
        score += 3.0

    # SAP status
    if str(row.get('sap', 'No')).upper() == 'YES':
        score += 2.0

    # Autonomous status
    if str(row.get('autonomous', 'No')).upper() == 'YES':
        score += 1.5

    # Tier classification
    tier = int(row.get('tier', 3))
    if tier == 1:
        score += 3.0
    elif tier == 2:
        score += 2.0
    elif tier == 3:
        score += 1.0

    # IP cut-off quality (inverse - lower is better)
    cutoff_str = row.get('ip_cutoff_2026', None)
    if pd.notna(cutoff_str) and cutoff_str != '':
        try:
            # Parse range like "4-6" or "7(M)"
            if '-' in str(cutoff_str):
                cutoff = float(str(cutoff_str).split('-')[0])
            else:
                cutoff = float(''.join(filter(str.isdigit, str(cutoff_str)[:2])))
            # Quality score: lower cutoff = higher quality
            cutoff_quality = max(0, (10 - cutoff) / 6 * 1.5)
            score += cutoff_quality
        except (ValueError, TypeError, IndexError):
            pass

    return min(score, 10.0)


def calculate_accessibility_score(distance_m: float, quality_score: float) -> float:
    """Calculate distance-weighted accessibility score.

    Uses exponential decay: quality score decreases with distance.

    Args:
        distance_m: Distance to school in meters
        quality_score: School quality score (0-10)

    Returns:
        Accessibility score from 0-1
    """
    if distance_m <= 0:
        return quality_score / 10.0

    # Distance decay: negligible beyond 2km
    distance_factor = max(0, 1 - (distance_m / 2000))

    # Quality amplification: better schools have wider catchment
    quality_amplification = 1 + (quality_score / 10)

    return distance_factor * quality_amplification * (quality_score / 10)


def fuzzy_match_schools(
    tier_schools: pd.DataFrame,
    official_schools: pd.DataFrame,
    min_score: int = 85
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Fuzzy match tier CSV school names to official school names.

    Args:
        tier_schools: DataFrame with school_name column from CSV
        official_schools: DataFrame with school_name column from parquet
        min_score: Minimum similarity score (0-100) to accept match

    Returns:
        Tuple of (tier_schools with matched names, mapping dict)
    """
    official_names = official_schools['school_name'].unique().tolist()
    official_names_normalized = [name.lower().strip() for name in official_names]

    mapping = {}
    matched_count = 0

    for tier_name in tier_schools['school_name']:
        tier_name_normalized = tier_name.lower().strip()

        # Try exact match first
        if tier_name_normalized in official_names_normalized:
            idx = official_names_normalized.index(tier_name_normalized)
            mapping[tier_name] = official_names[idx]
            matched_count += 1
            continue

        # Try fuzzy match
        result = process.extractOne(
            tier_name_normalized,
            official_names_normalized,
            scorer=fuzz.WRatio
        )

        if result and result[1] >= min_score:
            idx = official_names_normalized.index(result[0])
            mapping[tier_name] = official_names[idx]
            matched_count += 1
        else:
            mapping[tier_name] = None

    logger.info(f"Fuzzy matched {matched_count}/{len(tier_schools)} schools ({matched_count/len(tier_schools)*100:.1f}%)")

    return tier_schools, mapping


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

    # Quality-weighted columns (0)
    df['school_accessibility_score'] = 0.0
    df['school_primary_quality_score'] = 0.0
    df['school_secondary_quality_score'] = 0.0
    df['school_primary_dist_score'] = 0.0
    df['school_secondary_dist_score'] = 0.0
    df['school_density_score'] = 0.0

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


def _create_unique_location_index(properties_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Create unique location index and mapping back to original indices.

    Args:
        properties_df: DataFrame with 'lat', 'lon' columns

    Returns:
        Tuple of (unique_locations_df, index_mapping)
        - unique_locations_df: DataFrame with unique lat/lon pairs
        - index_mapping: Dict mapping unique_idx -> list of original indices
    """
    # Get unique lat/lon combinations
    unique_coords = properties_df[['lat', 'lon']].drop_duplicates()

    # Create mapping from unique coordinates back to original indices
    coord_to_idx = {}
    for orig_idx, row in properties_df[['lat', 'lon']].iterrows():
        coord_key = (row['lat'], row['lon'])
        if coord_key not in coord_to_idx:
            coord_to_idx[coord_key] = []
        coord_to_idx[coord_key].append(orig_idx)

    # Convert to index mapping
    index_mapping = {i: coord_to_idx[(row['lat'], row['lon'])]
                     for i, row in unique_coords.reset_index(drop=True).iterrows()}

    return unique_coords, index_mapping


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

    # Load school quality tiers
    primary_tiers, secondary_tiers = load_school_tiers()

    # Calculate quality scores for tiers
    if not primary_tiers.empty:
        primary_tiers['quality_score'] = primary_tiers.apply(calculate_primary_quality_score, axis=1)
        logger.info(f"Primary school quality scores: mean={primary_tiers['quality_score'].mean():.2f}")

    if not secondary_tiers.empty:
        secondary_tiers['quality_score'] = secondary_tiers.apply(calculate_secondary_quality_score, axis=1)
        logger.info(f"Secondary school quality scores: mean={secondary_tiers['quality_score'].mean():.2f}")

    # Merge quality scores with schools data using fuzzy matching
    schools_with_quality = schools_df.copy()

    if not primary_tiers.empty:
        # Use fuzzy matching to match tier CSV names to official names
        primary_tiers_matched, primary_mapping = fuzzy_match_schools(primary_tiers, schools_df)

        # Create mapping from official name to quality score
        official_to_quality = {}
        for tier_name, official_name in primary_mapping.items():
            if official_name:
                tier_row = primary_tiers[primary_tiers['school_name'] == tier_name].iloc[0]
                official_to_quality[official_name] = {
                    'quality_score': tier_row['quality_score'],
                    'gep': tier_row.get('gep', 'No'),
                    'sap': tier_row.get('sap', 'No'),
                    'tier': tier_row.get('tier', 3)
                }

        # Map quality scores using official school names
        schools_with_quality['primary_quality'] = schools_with_quality['school_name'].map(
            lambda x: official_to_quality.get(x, {}).get('quality_score') if x else None
        )

    if not secondary_tiers.empty:
        # Use fuzzy matching for secondary schools too
        secondary_tiers_matched, secondary_mapping = fuzzy_match_schools(secondary_tiers, schools_df)

        # Create mapping from official name to quality score
        official_to_secondary_quality = {}
        for tier_name, official_name in secondary_mapping.items():
            if official_name:
                tier_row = secondary_tiers[secondary_tiers['school_name'] == tier_name].iloc[0]
                official_to_secondary_quality[official_name] = tier_row['quality_score']

        # Map quality scores using official school names
        schools_with_quality['secondary_quality'] = schools_with_quality['school_name'].map(official_to_secondary_quality)

    # Combine quality scores (prefer primary, fall back to secondary)
    if 'primary_quality' in schools_with_quality.columns and 'secondary_quality' in schools_with_quality.columns:
        schools_with_quality['quality_score'] = schools_with_quality['primary_quality'].fillna(
            schools_with_quality['secondary_quality']
        )
    elif 'primary_quality' in schools_with_quality.columns:
        schools_with_quality['quality_score'] = schools_with_quality['primary_quality']
    elif 'secondary_quality' in schools_with_quality.columns:
        schools_with_quality['quality_score'] = schools_with_quality['secondary_quality']
    else:
        schools_with_quality['quality_score'] = None

    # Filter and prepare school data
    schools_geo = schools_with_quality.dropna(subset=["latitude", "longitude"]).copy()
    if schools_geo.empty:
        logger.warning("No geocoded schools available")
        return properties_df

    # Fill missing quality scores with 0
    if 'quality_score' not in schools_geo.columns:
        schools_geo['quality_score'] = 0.0
    else:
        schools_geo['quality_score'] = schools_geo['quality_score'].fillna(0.0)

    # Build KD-trees for each school level (convert to radians for distance queries)
    schools_by_level = {}
    for level in levels:
        level_schools = schools_geo[schools_geo["mainlevel_code"] == level]
        if level_schools.empty:
            continue

        coords = np.column_stack([
            np.radians(level_schools["latitude"].values),
            np.radians(level_schools["longitude"].values)
        ])

        schools_by_level[level] = {
            'tree': cKDTree(coords),
            'data': level_schools.reset_index(drop=True),
            'coords': coords
        }

    # Build combined tree for aggregate counts (convert to radians for distance queries)
    all_coords = np.column_stack([
        np.radians(schools_geo["latitude"].values),
        np.radians(schools_geo["longitude"].values)
    ])
    all_tree = cKDTree(all_coords)

    level_summary = ', '.join([
        f"{k[:3]}({v['data'].shape[0]})"
        for k, v in schools_by_level.items()
    ])
    logger.info(f"Schools by level: {level_summary}")

    # Initialize columns (including new quality columns)
    properties_df = _initialize_school_columns(properties_df, levels)

    # Initialize quality-weighted columns
    properties_df['school_accessibility_score'] = 0.0
    properties_df['school_primary_quality_score'] = 0.0
    properties_df['school_secondary_quality_score'] = 0.0
    properties_df['school_primary_dist_score'] = 0.0
    properties_df['school_secondary_dist_score'] = 0.0
    properties_df['school_density_score'] = 0.0

    # Create unique location index to avoid redundant calculations
    props_with_coords = properties_df.dropna(subset=["lat", "lon"])
    total_original = len(props_with_coords)

    unique_coords, index_mapping = _create_unique_location_index(props_with_coords)
    logger.info(f"Reduced to {len(unique_coords)} unique locations from {total_original} total records")

    # Initialize a DataFrame to store calculated features for unique locations
    unique_features = pd.DataFrame(index=unique_coords.index)

    # Initialize all feature columns in unique_features
    for level in levels:
        level_code = level.split()[0]
        for suffix in ['_dist', '_name', '_type', '_dgp', '_zone',
                      '_nature', '_mrt_desc', '_sap', '_autonomous',
                      '_gifted', '_ip']:
            unique_features[f"nearest_school{level_code}{suffix}"] = None

    for level in levels:
        level_code = level.split()[0]
        for label in DISTANCES.keys():
            unique_features[f"school{level_code}_count{label}"] = 0

    for label in DISTANCES.keys():
        unique_features[f"school_within_{label}"] = 0

    unique_features['school_accessibility_score'] = 0.0
    unique_features['school_primary_quality_score'] = 0.0
    unique_features['school_secondary_quality_score'] = 0.0
    unique_features['school_primary_dist_score'] = 0.0
    unique_features['school_secondary_dist_score'] = 0.0
    unique_features['school_density_score'] = 0.0

    # Process UNIQUE locations only (not all properties)
    for idx, (unique_idx, coord_row) in enumerate(unique_coords.iterrows(), 1):
        prop_lat, prop_lon = float(coord_row["lat"]), float(coord_row["lon"])

        # Calculate school density (schools within 1km)
        radius_radians = 1000 / 6371000
        nearby_schools = all_tree.query_ball_point([np.radians(prop_lat), np.radians(prop_lon)], r=radius_radians)
        unique_features.at[unique_idx, 'school_density_score'] = min(len(nearby_schools) / 10, 1.0)

        # Aggregate school counts
        for col_suffix, radius_m in DISTANCES.items():
            radius_radians = radius_m / 6371000
            count = all_tree.query_ball_point([np.radians(prop_lat), np.radians(prop_lon)], r=radius_radians)
            unique_features.at[unique_idx, f"school_within_{col_suffix}"] = len(count)

        # Per-level features with quality scores
        primary_accessibility = 0.0
        secondary_accessibility = 0.0

        for level, school_data in schools_by_level.items():
            level_code = level.split()[0]
            tree = school_data['tree']
            level_df = school_data['data']

            # Find nearest school (query in radians)
            dist_radians, nearest_idx = tree.query([np.radians(prop_lat), np.radians(prop_lon)], k=1)
            nearest_school = level_df.iloc[nearest_idx]

            # Calculate true haversine distance
            true_dist = haversine_distance(
                prop_lat, prop_lon,
                nearest_school["latitude"],
                nearest_school["longitude"]
            )
            unique_features.at[unique_idx, f"nearest_school{level_code}_dist"] = true_dist

            # Get school quality score
            quality_score = nearest_school.get('quality_score', 0.0)
            if pd.isna(quality_score):
                quality_score = 0.0

            # Store quality scores
            if level == "PRIMARY":
                unique_features.at[unique_idx, 'school_primary_quality_score'] = quality_score
                dist_score = calculate_accessibility_score(true_dist, quality_score) * 10
                unique_features.at[unique_idx, 'school_primary_dist_score'] = dist_score
                primary_accessibility = calculate_accessibility_score(true_dist, quality_score)
            elif level == "SECONDARY (S1-S5)":
                unique_features.at[unique_idx, 'school_secondary_quality_score'] = quality_score
                dist_score = calculate_accessibility_score(true_dist, quality_score) * 10
                unique_features.at[unique_idx, 'school_secondary_dist_score'] = dist_score
                secondary_accessibility = calculate_accessibility_score(true_dist, quality_score)

            # Get and assign school attributes
            attrs = _get_school_attributes(nearest_school)
            for key, value in attrs.items():
                if key != 'dist':
                    unique_features.at[unique_idx, f"nearest_school{level_code}_{key}"] = value

            # Level-specific school counts (query in radians)
            for col_suffix, radius_m in DISTANCES.items():
                radius_radians = radius_m / 6371000
                count = tree.query_ball_point([np.radians(prop_lat), np.radians(prop_lon)], r=radius_radians)
                unique_features.at[unique_idx, f"school{level_code}_count{col_suffix}"] = len(count)

        # Overall accessibility: weighted combination (40% primary, 60% secondary)
        unique_features.at[unique_idx, 'school_accessibility_score'] = (
            0.4 * primary_accessibility + 0.6 * secondary_accessibility
        )

        if idx % 1000 == 0:
            logger.info(f"Processed {idx}/{len(unique_coords)} unique locations...")

    # Map calculated features back to all original records
    logger.info("Mapping features back to all records...")

    # Get feature columns (exclude coordinate columns if they exist)
    feature_columns = [col for col in unique_features.columns
                      if col not in ['lat', 'lon']]

    # Map features from unique locations back to all original indices
    for unique_idx, orig_indices in index_mapping.items():
        for orig_idx in orig_indices:
            for col in feature_columns:
                properties_df.at[orig_idx, col] = unique_features.at[unique_idx, col]

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

    # Print quality score statistics
    logger.info("\n📊 School Quality Score Statistics:")
    for col, label in [
        ('school_accessibility_score', 'Overall Accessibility'),
        ('school_primary_quality_score', 'Primary School Quality'),
        ('school_secondary_quality_score', 'Secondary School Quality'),
        ('school_primary_dist_score', 'Primary Distance-Weighted'),
        ('school_secondary_dist_score', 'Secondary Distance-Weighted'),
    ]:
        if col in properties_df.columns:
            scores = properties_df[col]
            logger.info(
                f"  {label}:\n"
                f"    mean={scores.mean():.2f}, "
                f"median={scores.median():.2f}, "
                f"min={scores.min():.2f}, "
                f"max={scores.max():.2f}"
            )


if __name__ == "__main__":
    main()
