"""ProximityEngine: unified amenity proximity computation.

Absorbs mrt_distance.py, school_features.py proximity logic,
and the inline _nearest_mall_features from 03_features.py.

One function: compute_proximity_features(properties_df, poi_dfs) -> DataFrame.
"""

import logging

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.neighbors import BallTree

from egg_n_bacon_housing.utils.geo import haversine_distance
from egg_n_bacon_housing.utils.mrt_line_mapping import (
    get_station_score,
)

logger = logging.getLogger(__name__)


def compute_proximity_features(
    properties_df: pd.DataFrame,
    mrt_stations: pd.DataFrame | None = None,
    schools: pd.DataFrame | None = None,
    malls: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Compute all proximity features for a property dataset.

    Adds columns for nearest MRT, school, and mall distances and names.
    Gracefully handles missing POI datasets (skips those features).

    Args:
        properties_df: Properties with lat/lon columns.
        mrt_stations: DataFrame with name, lat, lon, plus MRT metadata.
        schools: DataFrame with school_name, latitude, longitude, mainlevel_code.
        malls: DataFrame with shopping_mall (or name), lat/latitude, lon/longitude.

    Returns:
        Properties DataFrame with proximity feature columns added.
    """
    df = properties_df.copy()
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    if mrt_stations is not None and not mrt_stations.empty:
        df = _compute_mrt_proximity(df, mrt_stations)

    if malls is not None and not malls.empty:
        df = _compute_mall_proximity(df, malls)

    return df


def _compute_mrt_proximity(df: pd.DataFrame, mrt_stations: pd.DataFrame) -> pd.DataFrame:
    """Add nearest MRT station features."""
    station_coords = mrt_stations[["lon", "lat"]].values
    tree = cKDTree(station_coords)

    valid_mask = df["lat"].notna() & df["lon"].notna()
    valid_df = df.loc[valid_mask]

    if valid_df.empty:
        df["nearest_mrt_station"] = None
        df["nearest_mrt_distance"] = None
        df["dist_to_nearest_mrt"] = None
        df["nearest_mrt_tier"] = None
        df["nearest_mrt_is_interchange"] = False
        return df

    property_coords = valid_df[["lon", "lat"]].values
    _distances, indices = tree.query(property_coords, k=1)
    nearest = mrt_stations.iloc[indices]

    df.loc[valid_mask, "nearest_mrt_station"] = nearest["name"].values
    if "tier" in nearest.columns:
        df.loc[valid_mask, "nearest_mrt_tier"] = nearest["tier"].values
    if "is_interchange" in nearest.columns:
        df.loc[valid_mask, "nearest_mrt_is_interchange"] = nearest["is_interchange"].values
    else:
        df.loc[valid_mask, "nearest_mrt_is_interchange"] = False

    mrt_coords = nearest[["lon", "lat"]].values
    distances = np.array(
        [
            haversine_distance(lat1, lon1, lat2, lon2)
            for (lon1, lat1), (lon2, lat2) in zip(property_coords, mrt_coords, strict=True)
        ]
    )
    df.loc[valid_mask, "nearest_mrt_distance"] = distances
    df.loc[valid_mask, "dist_to_nearest_mrt"] = distances

    df.loc[valid_mask, "nearest_mrt_score"] = [
        get_station_score(name, dist)
        for name, dist in zip(
            df.loc[valid_mask, "nearest_mrt_station"],
            df.loc[valid_mask, "nearest_mrt_distance"],
            strict=True,
        )
    ]

    for col in [
        "nearest_mrt_station",
        "nearest_mrt_distance",
        "dist_to_nearest_mrt",
        "nearest_mrt_tier",
        "nearest_mrt_is_interchange",
        "nearest_mrt_score",
    ]:
        df.loc[~valid_mask, col] = None if col != "nearest_mrt_is_interchange" else False
        if col == "nearest_mrt_score":
            df.loc[~valid_mask, col] = 0.0

    logger.info(
        "MRT proximity: median distance %sm",
        f"{pd.to_numeric(df.loc[valid_mask, 'nearest_mrt_distance'], errors='coerce').median():.0f}",
    )
    return df


def _compute_mall_proximity(df: pd.DataFrame, malls: pd.DataFrame) -> pd.DataFrame:
    """Add nearest mall distance and name features."""
    name_col = next(
        (c for c in ["shopping_mall", "name", "mall_name"] if c in malls.columns),
        None,
    )
    lat_col = next((c for c in ["lat", "latitude"] if c in malls.columns), None)
    lon_col = next((c for c in ["lon", "longitude"] if c in malls.columns), None)

    if not name_col or not lat_col or not lon_col:
        df["dist_to_nearest_mall"] = pd.NA
        df["nearest_mall"] = pd.NA
        return df

    valid_malls = malls[[name_col, lat_col, lon_col]].copy()
    valid_malls[lat_col] = pd.to_numeric(valid_malls[lat_col], errors="coerce")
    valid_malls[lon_col] = pd.to_numeric(valid_malls[lon_col], errors="coerce")
    valid_malls = valid_malls.dropna(subset=[lat_col, lon_col])

    if valid_malls.empty:
        df["dist_to_nearest_mall"] = pd.NA
        df["nearest_mall"] = pd.NA
        return df

    valid_mask = df["lat"].notna() & df["lon"].notna()
    valid_df = df.loc[valid_mask]

    if valid_df.empty:
        df["dist_to_nearest_mall"] = pd.NA
        df["nearest_mall"] = pd.NA
        return df

    property_coords = np.radians(valid_df[["lat", "lon"]].astype(float).to_numpy())
    mall_coords = np.radians(valid_malls[[lat_col, lon_col]].to_numpy())

    tree = BallTree(mall_coords, metric="haversine")
    distances_rad, nearest_indices = tree.query(property_coords, k=1)
    distances_m = distances_rad[:, 0] * 6371000
    nearest_indices_flat = nearest_indices[:, 0]

    df.loc[valid_mask, "dist_to_nearest_mall"] = distances_m
    df.loc[valid_mask, "nearest_mall"] = valid_malls.iloc[nearest_indices_flat][name_col].to_numpy()

    df.loc[~valid_mask, "dist_to_nearest_mall"] = pd.NA
    df.loc[~valid_mask, "nearest_mall"] = pd.NA

    return df
