"""MRT station distance calculation utilities.

This module provides functions for:
- Loading MRT station data from geojson
- Calculating nearest MRT station for properties
- Adding MRT distance features to datasets
"""

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from egg_n_bacon_housing.utils.mrt_line_mapping import (
    get_line_color,
    get_line_name,
    get_station_lines,
    get_station_score,
    get_station_tier,
    is_interchange,
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
        from egg_n_bacon_housing.config import settings

        mrt_geojson_path = settings.data_dir / "manual" / "csv" / "datagov" / "MRTStations.geojson"

    if not mrt_geojson_path.exists():
        logger.warning(f"MRT geojson not found: {mrt_geojson_path}")
        return pd.DataFrame()

    gdf = gpd.read_file(mrt_geojson_path)

    stations = []
    for _, row in gdf.iterrows():
        centroid = row["geometry"].centroid
        station_name = row["NAME"]

        lines = get_station_lines(station_name)
        tier = get_station_tier(station_name)
        is_interch = is_interchange(station_name)
        line_names = [get_line_name(line) for line in lines]
        colors = [get_line_color(line) for line in lines]

        stations.append(
            {
                "name": station_name,
                "lat": centroid.y,
                "lon": centroid.x,
                "rail_type": row.get("RAIL_TYPE", "Unknown"),
                "ground_level": row.get("GRND_LEVEL", "Unknown"),
                "lines": lines,
                "tier": tier,
                "is_interchange": is_interch,
                "line_names": line_names,
                "colors": colors,
            }
        )

    mrt_df = pd.DataFrame(stations)

    logger.info(f"Loaded {len(mrt_df)} MRT stations from {mrt_geojson_path}")
    logger.info(f"  By tier: {mrt_df['tier'].value_counts().to_dict()}")
    logger.info(f"  Interchanges: {mrt_df['is_interchange'].sum()} stations")

    return mrt_df


def calculate_nearest_mrt(
    properties_df: pd.DataFrame, mrt_stations_df: pd.DataFrame = None, show_progress: bool = True
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

    if mrt_stations_df is None or mrt_stations_df.empty:
        mrt_stations_df = load_mrt_stations()

    if mrt_stations_df.empty:
        logger.warning("No MRT station data available")
        properties_df["nearest_mrt_name"] = None
        properties_df["nearest_mrt_distance"] = None
        properties_df["nearest_mrt_lines"] = None
        properties_df["nearest_mrt_line_names"] = None
        properties_df["nearest_mrt_tier"] = None
        properties_df["nearest_mrt_is_interchange"] = False
        properties_df["nearest_mrt_colors"] = None
        properties_df["nearest_mrt_score"] = 0.0
        return properties_df

    if "lat" not in properties_df.columns or "lon" not in properties_df.columns:
        logger.error("properties_df must have 'lat' and 'lon' columns")
        return properties_df

    properties_df = properties_df.copy()
    properties_df["lat"] = pd.to_numeric(properties_df["lat"], errors="coerce")
    properties_df["lon"] = pd.to_numeric(properties_df["lon"], errors="coerce")

    valid_mask = properties_df["lat"].notna() & properties_df["lon"].notna()
    n_invalid = (~valid_mask).sum()
    if n_invalid > 0:
        logger.warning(f"{n_invalid} rows have invalid coordinates (NaN for MRT distance)")

    valid_df = properties_df.loc[valid_mask]

    mrt_coords = mrt_stations_df[["lon", "lat"]].values
    tree = cKDTree(mrt_coords)

    property_coords = valid_df[["lon", "lat"]].values
    distances, indices = tree.query(property_coords, k=1)

    nearest_stations = mrt_stations_df.iloc[indices]

    properties_df.loc[valid_mask, "nearest_mrt_name"] = nearest_stations["name"].values
    properties_df.loc[valid_mask, "nearest_mrt_lines"] = nearest_stations["lines"].values
    properties_df.loc[valid_mask, "nearest_mrt_line_names"] = nearest_stations["line_names"].values
    properties_df.loc[valid_mask, "nearest_mrt_tier"] = nearest_stations["tier"].values
    properties_df.loc[valid_mask, "nearest_mrt_is_interchange"] = nearest_stations[
        "is_interchange"
    ].values
    properties_df.loc[valid_mask, "nearest_mrt_colors"] = nearest_stations["colors"].values

    nearest_mrt_coords = nearest_stations[["lon", "lat"]].values

    mrt_distances = [
        haversine_distance(lon1, lat1, lon2, lat2)
        for lon1, lat1, lon2, lat2 in zip(
            property_coords[:, 0],
            property_coords[:, 1],
            nearest_mrt_coords[:, 0],
            nearest_mrt_coords[:, 1],
        )
    ]
    properties_df.loc[valid_mask, "nearest_mrt_distance"] = mrt_distances

    properties_df.loc[valid_mask, "nearest_mrt_score"] = [
        get_station_score(name, dist)
        for name, dist in zip(
            properties_df.loc[valid_mask, "nearest_mrt_name"],
            properties_df.loc[valid_mask, "nearest_mrt_distance"],
        )
    ]

    properties_df.loc[~valid_mask, "nearest_mrt_name"] = None
    properties_df.loc[~valid_mask, "nearest_mrt_distance"] = None
    properties_df.loc[~valid_mask, "nearest_mrt_lines"] = None
    properties_df.loc[~valid_mask, "nearest_mrt_line_names"] = None
    properties_df.loc[~valid_mask, "nearest_mrt_tier"] = None
    properties_df.loc[~valid_mask, "nearest_mrt_is_interchange"] = False
    properties_df.loc[~valid_mask, "nearest_mrt_colors"] = None
    properties_df.loc[~valid_mask, "nearest_mrt_score"] = 0.0

    logger.info("Added MRT distance features:")
    valid_distances = properties_df.loc[valid_mask, "nearest_mrt_distance"]
    if not valid_distances.empty:
        logger.info(f"  Mean distance to nearest MRT: {valid_distances.mean():.0f}m")
    logger.info(
        f"  Median distance to nearest MRT: {properties_df['nearest_mrt_distance'].median():.0f}m"
    )
    logger.info(f"  Min distance: {properties_df['nearest_mrt_distance'].min():.0f}m")
    logger.info(f"  Max distance: {properties_df['nearest_mrt_distance'].max():.0f}m")

    logger.info(f"  Tier 1 stations: {(properties_df['nearest_mrt_tier'] == 1).sum():,} properties")
    logger.info(f"  Tier 2 stations: {(properties_df['nearest_mrt_tier'] == 2).sum():,} properties")
    logger.info(f"  Tier 3 stations: {(properties_df['nearest_mrt_tier'] == 3).sum():,} properties")
    logger.info(
        f"  Interchange stations: {properties_df['nearest_mrt_is_interchange'].sum():,} properties"
    )

    within_500m = (properties_df["nearest_mrt_distance"] <= 500).sum()
    within_1km = (properties_df["nearest_mrt_distance"] <= 1000).sum()
    logger.info(
        f"  Properties within 500m: {within_500m:,} ({within_500m / len(properties_df) * 100:.1f}%)"
    )
    logger.info(
        f"  Properties within 1km: {within_1km:,} ({within_1km / len(properties_df) * 100:.1f}%)"
    )

    return properties_df


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    logging.basicConfig(level=logging.INFO)

    mrt_df = load_mrt_stations()
    print(f"\nLoaded {len(mrt_df)} MRT stations")
    print("\nFirst 5 stations:")
    print(mrt_df.head())

    sample_properties = pd.DataFrame(
        {
            "lat": [1.3521, 1.3450, 1.3800],
            "lon": [103.8198, 103.8300, 103.8500],
            "address": ["Test Address 1", "Test Address 2", "Test Address 3"],
        }
    )

    print(f"\nTesting on {len(sample_properties)} sample properties:")
    result = calculate_nearest_mrt(sample_properties, mrt_df, show_progress=False)

    print("\nResults:")
    print(result[["address", "nearest_mrt_name", "nearest_mrt_distance"]])
