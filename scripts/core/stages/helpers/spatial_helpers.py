"""Helper functions for spatial calculations and distance metrics."""

import logging
from typing import List, Tuple

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

logger = logging.getLogger(__name__)


def count_amenities_within_radius(
    lon: float,
    lat: float,
    tree: cKDTree,
    amenities_df: pd.DataFrame,
    radius_km: float,
    haversine_fn,
) -> int:
    """
    Count amenities within a given radius using haversine distance.

    This function performs an efficient two-step search:
    1. Quick approximate search using KD-tree with degree-based radius
    2. Accurate filtering using haversine distance calculation

    Args:
        lon: Property longitude
        lat: Property latitude
        tree: KD-tree built from amenity coordinates
        amenities_df: DataFrame with amenity data (must have lon, lat columns)
        radius_km: Search radius in kilometers
        haversine_fn: Function to calculate haversine distance

    Returns:
        Count of amenities within the specified radius
    """
    # Approximate: 1 degree ≈ 111 km
    radius_deg = radius_km / 111

    idxs = tree.query_ball_point([lon, lat], r=radius_deg)

    if len(idxs) == 0:
        return 0

    # Filter by actual haversine distance
    nearby_amenities = amenities_df.iloc[idxs]
    actual_distances = [
        haversine_fn(lon, lat, a["lon"], a["lat"])
        for _, a in nearby_amenities.iterrows()
    ]

    return sum(1 for d in actual_distances if d <= radius_km * 1000)


def calculate_amenity_counts_by_radius(
    property_coords: np.ndarray,
    tree: cKDTree,
    amenities_df: pd.DataFrame,
    haversine_fn,
    radius_km_list: List[float] = [0.5, 1.0, 2.0],
    show_progress: bool = True,
) -> Tuple[List[int], List[int], List[int]]:
    """
    Calculate amenity counts at multiple radius levels for all properties.

    This is a vectorized wrapper around count_amenities_within_radius
    that processes all properties efficiently.

    Args:
        property_coords: Array of (lon, lat) pairs for properties
        tree: KD-tree built from amenity coordinates
        amenities_df: DataFrame with amenity data
        haversine_fn: Function to calculate haversine distance
        radius_km_list: List of radii to calculate counts for (in km)
        show_progress: Show progress bar

    Returns:
        Tuple of three lists (counts_500m, counts_1km, counts_2km)
    """
    from tqdm import tqdm

    counts_dict = {radius: [] for radius in radius_km_list}

    iterator = tqdm(
        enumerate(property_coords),
        desc="Calculating amenity counts",
        ncols=60,
        total=len(property_coords),
        disable=not show_progress,
    )

    for i, (lon, lat) in iterator:
        for radius_km in radius_km_list:
            count = count_amenities_within_radius(
                lon, lat, tree, amenities_df, radius_km, haversine_fn
            )
            counts_dict[radius_km].append(count)

    # Return results for standard radii
    return (
        counts_dict[0.5],  # 500m
        counts_dict[1.0],  # 1km
        counts_dict[2.0],  # 2km
    )


def calculate_nearest_amenity_distances(
    property_coords: np.ndarray,
    amenity_coords: np.ndarray,
    amenities_df: pd.DataFrame,
    haversine_fn,
    tree: cKDTree,
) -> np.ndarray:
    """
    Calculate distances to nearest amenity for all properties.

    Uses KD-tree for efficient nearest neighbor search, then refines
    with haversine distance for accuracy.

    Args:
        property_coords: Array of (lon, lat) pairs for properties
        amenity_coords: Array of (lon, lat) pairs for amenities
        amenities_df: DataFrame with amenity data
        haversine_fn: Function to calculate haversine distance
        tree: KD-tree built from amenity coordinates

    Returns:
        Array of distances in meters
    """
    # Find nearest amenity using KD-tree (fast approximation)
    distances_rad, indices = tree.query(property_coords, k=1)

    # Calculate accurate haversine distances
    distances = np.array(
        [
            haversine_fn(
                row["lon"],
                row["lat"],
                amenities_df.iloc[i]["lon"],
                amenities_df.iloc[i]["lat"],
            )
            for i, row in pd.DataFrame(property_coords, columns=["lon", "lat"]).iterrows()
        ]
    )

    return distances
