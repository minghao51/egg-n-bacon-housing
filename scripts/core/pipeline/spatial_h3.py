"""Distance and spatial utilities for feature engineering.

This module provides functions for:
- Haversine distance calculations
- H3 grid cell operations
- Efficient amenity distance calculations using KD-trees
"""

import logging
from typing import List

import h3
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import Polygon
from tqdm import tqdm

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


def generate_h3_grid_cell(lat: float, lon: float, resolution: int = 8) -> str:
    """Generate H3 grid cell from lat/lon coordinates.

    Args:
        lat: Latitude
        lon: Longitude
        resolution: H3 resolution level (default: 8)

    Returns:
        H3 cell index string
    """
    return h3.latlng_to_cell(lat, lon, resolution)


def generate_grid_disk(cell: str, k: int = 5) -> List[str]:
    """Generate H3 grid disk from a cell.

    Args:
        cell: H3 cell index
        k: Radius in cells (default: 5)

    Returns:
        List of H3 cell indices
    """
    return h3.grid_disk(cell, k)


def generate_polygon_from_cells(cells: List[str]) -> Polygon:
    """Generate Shapely Polygon from H3 cells.

    Args:
        cells: List of H3 cell indices

    Returns:
        Shapely Polygon
    """
    return Polygon(h3.cells_to_geo(cells)["coordinates"][0])


def generate_polygons(unique_df: pd.DataFrame, resolution: int = 8, k: int = 3) -> List[Polygon]:
    """Generate polygons from unique_df's lat/lon coordinates.

    Args:
        unique_df: DataFrame containing 'lat' and 'lon' columns
        resolution: H3 resolution level
        k: Grid disk radius

    Returns:
        List of Shapely Polygons
    """
    return [
        generate_polygon_from_cells(
            generate_grid_disk(generate_h3_grid_cell(lat, lon, resolution), k)
        )
        for lat, lon in zip(unique_df["lat"], unique_df["lon"])
    ]


def calculate_amenity_distances(
    housing_df: pd.DataFrame,
    amenities_df: pd.DataFrame,
    amenity_type: str,
    show_progress: bool = True,
) -> pd.DataFrame:
    """Calculate distance features from properties to amenities.

    Uses KD-tree for efficient nearest neighbor search and haversine
    for accurate distance calculations.

    Args:
        housing_df: DataFrame with property lat/lon columns
        amenities_df: DataFrame with amenity lat/lon columns
        amenity_type: Type of amenity (for logging and column naming)
        show_progress: Show progress bar (default: True)

    Returns:
        DataFrame with distance features added
    """
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Processing: {amenity_type.upper()}")
    logger.info(f"{'=' * 60}")

    housing_df = housing_df.copy()
    amenities_df = amenities_df.copy()

    if "LATITUDE" in housing_df.columns and "LONGITUDE" in housing_df.columns:
        housing_df = housing_df.rename(columns={"LATITUDE": "lat", "LONGITUDE": "lon"})

    housing_df["lat"] = pd.to_numeric(housing_df["lat"], errors="coerce")
    housing_df["lon"] = pd.to_numeric(housing_df["lon"], errors="coerce")
    housing_df = housing_df.dropna(subset=["lat", "lon"])

    amenities_df["lat"] = pd.to_numeric(amenities_df["lat"], errors="coerce")
    amenities_df["lon"] = pd.to_numeric(amenities_df["lon"], errors="coerce")
    amenities_df = amenities_df.dropna(subset=["lat", "lon"])

    logger.info(f"  Properties: {len(housing_df):,}")
    logger.info(f"  {amenity_type.capitalize()} locations: {len(amenities_df):,}")

    amenity_coords = amenities_df[["lon", "lat"]].values
    property_coords = housing_df[["lon", "lat"]].values

    tree = cKDTree(amenity_coords)

    distances_rad, indices = tree.query(property_coords, k=1)

    nearest_amenities = amenities_df.iloc[indices]
    distances = np.array(
        [
            haversine_distance(
                row["lon"],
                row["lat"],
                nearest_amenities.iloc[i]["lon"],
                nearest_amenities.iloc[i]["lat"],
            )
            for i, row in housing_df[["lon", "lat"]].iterrows()
        ]
    )

    housing_df[f"dist_to_nearest_{amenity_type}"] = distances

    logger.info(f"  Calculating amenity counts within radius...")

    counts_500m = []
    counts_1km = []
    counts_2km = []

    iterator = tqdm(
        enumerate(property_coords),
        desc=f"  {amenity_type}",
        ncols=60,
        total=len(property_coords),
        disable=not show_progress,
    )

    for i, (lon, lat) in iterator:
        idxs_500m = tree.query_ball_point([lon, lat], r=0.005)
        idxs_1km = tree.query_ball_point([lon, lat], r=0.01)
        idxs_2km = tree.query_ball_point([lon, lat], r=0.02)

        if len(idxs_500m) > 0:
            nearby_amenities = amenities_df.iloc[idxs_500m]
            actual_distances = [
                haversine_distance(lon, lat, a["lon"], a["lat"])
                for _, a in nearby_amenities.iterrows()
            ]
            counts_500m.append(sum(1 for d in actual_distances if d <= 500))
        else:
            counts_500m.append(0)

        if len(idxs_1km) > 0:
            nearby_amenities = amenities_df.iloc[idxs_1km]
            actual_distances = [
                haversine_distance(lon, lat, a["lon"], a["lat"])
                for _, a in nearby_amenities.iterrows()
            ]
            counts_1km.append(sum(1 for d in actual_distances if d <= 1000))
        else:
            counts_1km.append(0)

        if len(idxs_2km) > 0:
            nearby_amenities = amenities_df.iloc[idxs_2km]
            actual_distances = [
                haversine_distance(lon, lat, a["lon"], a["lat"])
                for _, a in nearby_amenities.iterrows()
            ]
            counts_2km.append(sum(1 for d in actual_distances if d <= 2000))
        else:
            counts_2km.append(0)

    housing_df[f"{amenity_type}_within_500m"] = counts_500m
    housing_df[f"{amenity_type}_within_1km"] = counts_1km
    housing_df[f"{amenity_type}_within_2km"] = counts_2km

    logger.info(f"  Average distance to nearest: {distances.mean():.0f}m")
    logger.info(f"  Median distance: {np.median(distances):.0f}m")
    logger.info(f"  Average within 500m: {np.mean(counts_500m):.1f}")
    logger.info(f"  Average within 1km: {np.mean(counts_1km):.1f}")
    logger.info(f"  Average within 2km: {np.mean(counts_2km):.1f}")

    return housing_df


def calculate_nearest_amenity_distances(
    properties_df: pd.DataFrame, amenities_df: pd.DataFrame, amenity_type: str = "hawker"
) -> pd.DataFrame:
    """Calculate distance to nearest amenity and counts within radius.

    This is a simplified version using the more complete calculate_amenity_distances.

    Args:
        properties_df: DataFrame with property lat/lon
        amenities_df: DataFrame with amenity lat/lon
        amenity_type: Type of amenity (default: 'hawker')

    Returns:
        DataFrame with distance features added
    """
    return calculate_amenity_distances(properties_df, amenities_df, amenity_type)
