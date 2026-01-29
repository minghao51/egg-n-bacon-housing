"""MRT station distance calculation utilities.

This module provides functions for:
- Loading MRT station data from geojson
- Calculating nearest MRT station for properties
- Adding MRT distance features to datasets
"""

import logging
from pathlib import Path
from typing import Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from tqdm import tqdm

from core.mrt_line_mapping import (
    get_station_lines,
    get_station_tier,
    is_interchange,
    get_station_score,
    get_line_color,
    get_line_name
)

logger = logging.getLogger(__name__)


def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculate the great circle distance between two points.

    Args:
        lon1: Longitude of first point (decimal degrees)
        lat1: Latitude of first point (decimal degrees)
        lon2: Longitude of second point (decimal degrees)
        lat2: Latitude of second point (decimal degrees)

    Returns:
        Distance in meters
    """
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371000
    return c * r


def load_mrt_stations(mrt_geojson_path: Path = None) -> pd.DataFrame:
    """Load MRT station data from geojson and extract centroids.

    Args:
        mrt_geojson_path: Path to MRT stations geojson file.
            Defaults to data/manual/csv/datagov/MRTStations.geojson

    Returns:
        DataFrame with columns: name, lat, lon, rail_type, ground_level,
                               lines, tier, is_interchange, line_names, colors
    """
    if mrt_geojson_path is None:
        from core.config import Config
        mrt_geojson_path = Config.MANUAL_DIR / "csv" / "datagov" / "MRTStations.geojson"

    if not mrt_geojson_path.exists():
        logger.warning(f"MRT geojson not found: {mrt_geojson_path}")
        return pd.DataFrame()

    # Load geojson
    gdf = gpd.read_file(mrt_geojson_path)

    # Extract centroid coordinates from geometry
    # MRT stations have Polygon geometries, so we calculate centroids
    stations = []
    for _, row in gdf.iterrows():
        # Get centroid of the polygon
        centroid = row['geometry'].centroid
        station_name = row['NAME']

        # Get line information
        lines = get_station_lines(station_name)
        tier = get_station_tier(station_name)
        is_interch = is_interchange(station_name)
        line_names = [get_line_name(line) for line in lines]
        colors = [get_line_color(line) for line in lines]

        stations.append({
            'name': station_name,  # MRT station name
            'lat': centroid.y,
            'lon': centroid.x,
            'rail_type': row.get('RAIL_TYPE', 'Unknown'),
            'ground_level': row.get('GRND_LEVEL', 'Unknown'),
            'lines': lines,  # List of line codes
            'tier': tier,  # 1=highest, 3=lowest
            'is_interchange': is_interch,
            'line_names': line_names,  # Full line names
            'colors': colors  # Color hex codes
        })

    mrt_df = pd.DataFrame(stations)

    logger.info(f"Loaded {len(mrt_df)} MRT stations from {mrt_geojson_path}")
    logger.info(f"  By tier: {mrt_df['tier'].value_counts().to_dict()}")
    logger.info(f"  Interchanges: {mrt_df['is_interchange'].sum()} stations")

    return mrt_df


def calculate_nearest_mrt(
    properties_df: pd.DataFrame,
    mrt_stations_df: pd.DataFrame = None,
    show_progress: bool = True
) -> pd.DataFrame:
    """Calculate nearest MRT station and distance for each property.

    Uses KD-tree for efficient nearest neighbor search and includes
    enhanced MRT line information.

    Args:
        properties_df: DataFrame with lat/lon columns
        mrt_stations_df: MRT stations DataFrame with lat/lon columns.
            If None, loads from default geojson path.
        show_progress: Show progress bar (default: True)

    Returns:
        DataFrame with new columns added:
        - nearest_mrt_name: Name of closest MRT station
        - nearest_mrt_distance: Distance in meters to closest MRT
        - nearest_mrt_lines: List of MRT line codes (e.g., ['NSL', 'EWL'])
        - nearest_mrt_line_names: List of full line names
        - nearest_mrt_tier: Importance tier (1=highest, 3=lowest)
        - nearest_mrt_is_interchange: Boolean indicating if interchange
        - nearest_mrt_colors: Color hex codes for visualization
        - nearest_mrt_score: Overall station score (higher = better)
    """
    logger.info("Calculating nearest MRT stations...")

    # Load MRT data if not provided
    if mrt_stations_df is None or mrt_stations_df.empty:
        mrt_stations_df = load_mrt_stations()

    if mrt_stations_df.empty:
        logger.warning("No MRT station data available")
        properties_df['nearest_mrt_name'] = None
        properties_df['nearest_mrt_distance'] = None
        properties_df['nearest_mrt_lines'] = None
        properties_df['nearest_mrt_line_names'] = None
        properties_df['nearest_mrt_tier'] = None
        properties_df['nearest_mrt_is_interchange'] = False
        properties_df['nearest_mrt_colors'] = None
        properties_df['nearest_mrt_score'] = 0.0
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

    # Build KD-tree for efficient nearest neighbor search
    mrt_coords = mrt_stations_df[['lon', 'lat']].values
    tree = cKDTree(mrt_coords)

    # Query nearest MRT for each property
    property_coords = properties_df[['lon', 'lat']].values
    distances, indices = tree.query(property_coords, k=1)

    # Get nearest MRT information
    nearest_stations = mrt_stations_df.iloc[indices]

    # Add results to dataframe
    properties_df['nearest_mrt_name'] = nearest_stations['name'].values
    properties_df['nearest_mrt_lines'] = nearest_stations['lines'].values
    properties_df['nearest_mrt_line_names'] = nearest_stations['line_names'].values
    properties_df['nearest_mrt_tier'] = nearest_stations['tier'].values
    properties_df['nearest_mrt_is_interchange'] = nearest_stations['is_interchange'].values
    properties_df['nearest_mrt_colors'] = nearest_stations['colors'].values

    # Calculate accurate distances using haversine for each property
    nearest_mrt_coords = nearest_stations[['lon', 'lat']].values

    properties_df['nearest_mrt_distance'] = [
        haversine_distance(lon1, lat1, lon2, lat2)
        for lon1, lat1, lon2, lat2 in zip(
            property_coords[:, 0],
            property_coords[:, 1],
            nearest_mrt_coords[:, 0],
            nearest_mrt_coords[:, 1]
        )
    ]

    # Calculate station scores (tier + distance)
    properties_df['nearest_mrt_score'] = [
        get_station_score(name, dist)
        for name, dist in zip(properties_df['nearest_mrt_name'], properties_df['nearest_mrt_distance'])
    ]

    # Log summary statistics
    logger.info(f"Added MRT distance features:")
    logger.info(f"  Mean distance to nearest MRT: {properties_df['nearest_mrt_distance'].mean():.0f}m")
    logger.info(f"  Median distance to nearest MRT: {properties_df['nearest_mrt_distance'].median():.0f}m")
    logger.info(f"  Min distance: {properties_df['nearest_mrt_distance'].min():.0f}m")
    logger.info(f"  Max distance: {properties_df['nearest_mrt_distance'].max():.0f}m")

    # Tier breakdown
    logger.info(f"  Tier 1 stations: {(properties_df['nearest_mrt_tier'] == 1).sum():,} properties")
    logger.info(f"  Tier 2 stations: {(properties_df['nearest_mrt_tier'] == 2).sum():,} properties")
    logger.info(f"  Tier 3 stations: {(properties_df['nearest_mrt_tier'] == 3).sum():,} properties")
    logger.info(f"  Interchange stations: {properties_df['nearest_mrt_is_interchange'].sum():,} properties")

    # Count properties within different distance thresholds
    within_500m = (properties_df['nearest_mrt_distance'] <= 500).sum()
    within_1km = (properties_df['nearest_mrt_distance'] <= 1000).sum()
    logger.info(f"  Properties within 500m: {within_500m:,} ({within_500m/len(properties_df)*100:.1f}%)")
    logger.info(f"  Properties within 1km: {within_1km:,} ({within_1km/len(properties_df)*100:.1f}%)")

    return properties_df


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    # Test the module
    logging.basicConfig(level=logging.INFO)

    # Load MRT stations
    mrt_df = load_mrt_stations()
    print(f"\nLoaded {len(mrt_df)} MRT stations")
    print(f"\nFirst 5 stations:")
    print(mrt_df.head())

    # Test on sample properties
    sample_properties = pd.DataFrame({
        'lat': [1.3521, 1.3450, 1.3800],  # Sample coordinates in Singapore
        'lon': [103.8198, 103.8300, 103.8500],
        'address': ['Test Address 1', 'Test Address 2', 'Test Address 3']
    })

    print(f"\nTesting on {len(sample_properties)} sample properties:")
    result = calculate_nearest_mrt(sample_properties, mrt_df, show_progress=False)

    print(f"\nResults:")
    print(result[['address', 'nearest_mrt_name', 'nearest_mrt_distance']])
