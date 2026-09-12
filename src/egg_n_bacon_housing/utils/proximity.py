"""ProximityEngine: unified amenity proximity computation.

Absorbs school_features.py proximity logic
and the inline _nearest_mall_features from features.

One function: compute_proximity_features(properties_df, poi_dfs) -> DataFrame.
"""

import logging

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from egg_n_bacon_housing.utils.geo import haversine_metres
from egg_n_bacon_housing.utils.mrt_line_mapping import station_score_basis
from egg_n_bacon_housing.utils.runtime import MrtReference

logger = logging.getLogger(__name__)


def compute_proximity_features(
    properties_df: pd.DataFrame,
    mrt_stations: pd.DataFrame | None = None,
    malls: pd.DataFrame | None = None,
    hawkers: pd.DataFrame | None = None,
    supermarkets: pd.DataFrame | None = None,
    parks: pd.DataFrame | None = None,
    childcare: pd.DataFrame | None = None,
    kindergartens: pd.DataFrame | None = None,
    bus_stops: pd.DataFrame | None = None,
    chas_clinics: pd.DataFrame | None = None,
    sports_facilities: pd.DataFrame | None = None,
    community_clubs: pd.DataFrame | None = None,
    green_mark_buildings: pd.DataFrame | None = None,
    *,
    mrt_reference: MrtReference | None = None,
) -> pd.DataFrame:
    """Compute all proximity features for a property dataset.

    Adds columns for nearest MRT, mall, hawker, supermarket, park,
    childcare, kindergarten, bus stop, CHAS clinic, sports facility,
    community club, and green mark building distances and names.
    Gracefully handles missing POI datasets (skips those features).
    School proximity is computed separately by ``utils.school_features``.

    Args:
        properties_df: Properties with lat/lon columns.
        mrt_stations: DataFrame with name, lat, lon, plus MRT metadata.
        malls: DataFrame with shopping_mall (or name), lat/latitude, lon/longitude.
        hawkers: DataFrame with name, lat, lon.
        supermarkets: DataFrame with name, lat, lon.
        parks: DataFrame with name, lat, lon.
        childcare: DataFrame with name, lat, lon.
        kindergartens: DataFrame with name, lat, lon.
        bus_stops: DataFrame with name, lat, lon.
        chas_clinics: DataFrame with name, lat, lon.
        sports_facilities: DataFrame with name, lat, lon.
        community_clubs: DataFrame with name, lat, lon.
        green_mark_buildings: DataFrame with name, lat, lon.

    Returns:
        Properties DataFrame with proximity feature columns added.
    """
    df = properties_df.copy()
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    unparseable_coords = int((df["lat"].isna() | df["lon"].isna()).sum())
    if unparseable_coords:
        # Not a row drop — these rows stay in the frame but every amenity
        # column degrades to NA for them. Counted so the degradation is
        # visible instead of silent.
        logger.info(
            "proximity: %s/%s property row(s) have unparseable coordinates — "
            "their amenity features degrade to NA",
            unparseable_coords,
            len(df),
        )

    if mrt_stations is not None and not mrt_stations.empty:
        if mrt_reference is None:
            raise ValueError("mrt_reference is required when MRT stations are provided")
        df = _compute_mrt_proximity(df, mrt_stations, mrt_reference)

    if malls is not None and not malls.empty:
        df = _compute_mall_proximity(df, malls)

    generic_amenities = {
        "hawker": hawkers,
        "supermarket": supermarkets,
        "park": parks,
        "childcare": childcare,
        "kindergarten": kindergartens,
        "bus_stop": bus_stops,
        "chas_clinic": chas_clinics,
        "sports_facility": sports_facilities,
        "community_club": community_clubs,
        "green_mark_building": green_mark_buildings,
    }
    for label, poi_df in generic_amenities.items():
        if poi_df is not None and not poi_df.empty:
            df = _compute_generic_proximity(df, poi_df, label)

    return df


def _compute_mrt_proximity(
    df: pd.DataFrame,
    mrt_stations: pd.DataFrame,
    mrt_reference: MrtReference,
) -> pd.DataFrame:
    """Add nearest MRT station features."""
    if "tier" not in mrt_stations.columns or "is_interchange" not in mrt_stations.columns:
        # Bronze MRT frames carry name/lat/lon/line only — derive tier and
        # interchange from the line mapping so the columns always exist.
        mrt_stations = mrt_stations.copy()
        names = mrt_stations["name"].astype(str)
        tier_for = mrt_reference.station_tier
        lines_for = mrt_reference.station_lines
        mrt_stations["tier"] = [tier_for(name) for name in names]
        mrt_stations["is_interchange"] = [len(lines_for(name)) >= 2 for name in names]

    # Nearest-station selection uses the same BallTree/haversine metric as
    # the generic amenity path (Euclidean degrees would misrank stations
    # whenever latitude shrinks longitude spacing).
    station_coords = np.radians(mrt_stations[["lat", "lon"]].astype(float).to_numpy())
    tree = BallTree(station_coords, metric="haversine")

    valid_mask = df["lat"].notna() & df["lon"].notna()
    valid_df = df.loc[valid_mask]

    if valid_df.empty:
        df["nearest_mrt_station"] = None
        df["dist_to_nearest_mrt"] = None
        df["nearest_mrt_tier"] = None
        df["nearest_mrt_is_interchange"] = False
        df["nearest_mrt_score"] = 0.0
        return df

    property_coords = np.radians(valid_df[["lat", "lon"]].astype(float).to_numpy())
    _distances_rad, indices = tree.query(property_coords, k=1)
    nearest = mrt_stations.iloc[indices[:, 0]]

    df.loc[valid_mask, "nearest_mrt_station"] = nearest["name"].values
    if "tier" in nearest.columns:
        df.loc[valid_mask, "nearest_mrt_tier"] = nearest["tier"].values
    if "is_interchange" in nearest.columns:
        df.loc[valid_mask, "nearest_mrt_is_interchange"] = nearest["is_interchange"].values
    else:
        df.loc[valid_mask, "nearest_mrt_is_interchange"] = False

    # Vectorized haversine over the matched station coordinates — the shared
    # utils.geo implementation, computed once per frame instead of a per-row
    # Python loop.
    distances = haversine_metres(
        valid_df["lat"].to_numpy(dtype=float),
        valid_df["lon"].to_numpy(dtype=float),
        nearest["lat"].to_numpy(dtype=float),
        nearest["lon"].to_numpy(dtype=float),
    )
    df.loc[valid_mask, "dist_to_nearest_mrt"] = distances

    # Station score = station_score_basis(lines, tier) * 1000 / max(dist, 1),
    # the shared arithmetic from mrt_line_mapping (identical to
    # MrtReferenceRepository.station_score). The line repositories rebuild
    # their station->line dict on every call, so resolve each distinct
    # station once per frame instead of once per row.
    lines_for, tier_for = mrt_reference.station_lines, mrt_reference.station_tier
    score_basis_cache: dict = {}
    tier_scores = np.empty(len(nearest), dtype=float)
    for i, name in enumerate(nearest["name"]):
        basis = score_basis_cache.get(name)
        if basis is None:
            basis = station_score_basis(lines_for(name), tier_for(name))
            score_basis_cache[name] = basis
        tier_scores[i] = basis
    df.loc[valid_mask, "nearest_mrt_score"] = (tier_scores * 1000) / np.maximum(distances, 1.0)

    for col in [
        "nearest_mrt_station",
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
        f"{pd.to_numeric(df.loc[valid_mask, 'dist_to_nearest_mrt'], errors='coerce').median():.0f}",
    )
    return df


def _compute_mall_proximity(df: pd.DataFrame, malls: pd.DataFrame) -> pd.DataFrame:
    """Add nearest mall distance and name features."""
    return _compute_generic_proximity(
        df,
        malls,
        "mall",
        name_candidates=("shopping_mall", "name", "mall_name"),
    )


def _compute_generic_proximity(
    df: pd.DataFrame,
    poi_df: pd.DataFrame,
    label: str,
    *,
    name_candidates: tuple[str, ...] = ("name",),
) -> pd.DataFrame:
    """Add nearest amenity distance and name for a POI type.

    Uses BallTree with haversine metric for accurate distance computation.
    Accepts flexible POI column naming: the name column is the first hit in
    ``name_candidates`` (falling back to the first column), coordinates accept
    ``lat``/``latitude`` and ``lon``/``longitude``. Missing or empty POI data
    degrades to all-NA columns instead of raising.

    Args:
        df: Properties DataFrame with lat/lon.
        poi_df: POI DataFrame with name/lat/lon (naming per above).
        label: Amenity label (e.g. 'hawker', 'supermarket', 'park', 'mall').
        name_candidates: POI name columns to try, in order.
    """
    dist_col = f"dist_to_nearest_{label}"
    name_out_col = f"nearest_{label}"

    if poi_df.empty:
        df[dist_col] = pd.NA
        df[name_out_col] = pd.NA
        return df

    name_col = next((c for c in name_candidates if c in poi_df.columns), poi_df.columns[0])
    lat_col = next((c for c in ("lat", "latitude") if c in poi_df.columns), None)
    lon_col = next((c for c in ("lon", "longitude") if c in poi_df.columns), None)
    if lat_col is None or lon_col is None:
        df[dist_col] = pd.NA
        df[name_out_col] = pd.NA
        return df

    valid_pois = poi_df[[name_col, lat_col, lon_col]].copy()
    valid_pois[lat_col] = pd.to_numeric(valid_pois[lat_col], errors="coerce")
    valid_pois[lon_col] = pd.to_numeric(valid_pois[lon_col], errors="coerce")
    valid_pois = valid_pois.dropna(subset=[lat_col, lon_col])
    dropped_bad_pois = len(poi_df) - len(valid_pois)
    if dropped_bad_pois:
        logger.info(
            "%s proximity: dropped %s/%s POI row(s) with unparseable coordinates; kept %s",
            label,
            dropped_bad_pois,
            len(poi_df),
            len(valid_pois),
        )

    if valid_pois.empty:
        if dropped_bad_pois:
            logger.warning(
                "%s proximity: ALL %s POI row(s) have unparseable coordinates — "
                "%s and %s degrade to all-NA for every property",
                label,
                len(poi_df),
                dist_col,
                name_out_col,
            )
        df[dist_col] = pd.NA
        df[name_out_col] = pd.NA
        return df

    valid_mask = df["lat"].notna() & df["lon"].notna()
    valid_df = df.loc[valid_mask]

    if valid_df.empty:
        df[dist_col] = pd.NA
        df[name_out_col] = pd.NA
        return df

    property_coords = np.radians(valid_df[["lat", "lon"]].astype(float).to_numpy())
    poi_coords = np.radians(valid_pois[[lat_col, lon_col]].to_numpy())

    tree = BallTree(poi_coords, metric="haversine")
    distances_rad, nearest_indices = tree.query(property_coords, k=1)
    distances_m = distances_rad[:, 0] * 6371000
    nearest_indices_flat = nearest_indices[:, 0]

    df.loc[valid_mask, dist_col] = distances_m
    df.loc[valid_mask, name_out_col] = valid_pois.iloc[nearest_indices_flat][name_col].to_numpy()

    df.loc[~valid_mask, dist_col] = pd.NA
    df.loc[~valid_mask, name_out_col] = pd.NA

    logger.info(
        "%s proximity: median distance %sm",
        label.capitalize(),
        f"{pd.to_numeric(df.loc[valid_mask, dist_col], errors='coerce').median():.0f}",
    )
    return df
