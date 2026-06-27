"""Data loading utilities for Singapore Housing Price Pipeline.

This module provides optimized data loading functions with caching
for HDB, Condo, and amenity data.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

import pandas as pd
from shapely import STRtree
from shapely.geometry import Point, shape
from shapely.prepared import prep

logger = logging.getLogger(__name__)

_paths: dict[str, Path] = {}


def configure(data_dir: Path) -> None:
    """Set data paths (call once at pipeline startup).

    Args:
        data_dir: Root data directory (e.g. ``settings.data_dir``).
    """
    global _paths
    _paths = {
        "data_dir": data_dir,
        "pipeline_dir": data_dir / "pipeline",
        "raw_data_dir": data_dir / "manual" / "geojsons",
        "platinum_dir": data_dir / "pipeline" / "04_platinum",
        "manual_dir": data_dir / "manual",
    }
    _load_planning_areas_raw.cache_clear()


def _get(key: str) -> Path:
    """Get a configured path, falling back to settings if not configured."""
    if key in _paths:
        return _paths[key]
    from egg_n_bacon_housing.config import settings

    return {
        "data_dir": settings.data_dir,
        "pipeline_dir": settings.data_dir / "pipeline",
        "raw_data_dir": settings.data_dir / "manual" / "geojsons",
        "platinum_dir": settings.platinum_dir,
        "manual_dir": settings.data_dir / "manual",
    }[key]


def _get_raw_data_dir() -> Path:
    return _paths.get("raw_data_dir", Path())


def _read_first_existing(*paths: Path) -> pd.DataFrame:
    """Read the first existing parquet path, else return an empty DataFrame."""
    for path in paths:
        if path.exists():
            return pd.read_parquet(path)
    logger.warning("No dataset found at any expected path: %s", [str(p) for p in paths])
    return pd.DataFrame()


@lru_cache(maxsize=1)
def _load_planning_areas_raw() -> tuple[list[dict], list[tuple], STRtree | None, list[str]]:
    geojson_path = _get_raw_data_dir() / "onemap_planning_area_polygon.geojson"

    if not geojson_path.exists():
        logger.warning("Planning area GeoJSON not found at %s", geojson_path)
        return ([], [], None, [])

    try:
        with open(geojson_path) as f:
            geojson_data = json.load(f)

        planning_areas = []
        prepared_list = []
        geom_list = []
        name_list = []
        for feature in geojson_data.get("features", []):
            props = feature.get("properties", {})
            geom = shape(geom_data) if (geom_data := feature.get("geometry")) else None

            name = props.get("pln_area_n", "Unknown")
            planning_areas.append({"name": name, "geometry": geom})

            if geom is not None:
                prepared_list.append((name, prep(geom)))
                geom_list.append(geom)
                name_list.append(name)

        tree = STRtree(geom_list) if geom_list else None
        return (planning_areas, prepared_list, tree, name_list)

    except (OSError, json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Error loading planning areas: %s", e)
        return ([], [], None, [])


def load_planning_areas() -> list[dict]:
    """
    Load Singapore planning area polygons from GeoJSON.

    Returns:
        List of planning areas with properties and geometry
    """
    return _load_planning_areas_raw()[0]


def get_planning_area_for_point(lat: float, lon: float) -> str | None:
    """
    Get the planning area name for a given lat/lon coordinate.

    Uses STRtree spatial index for candidate filtering, then prepared
    geometries for exact point-in-polygon tests.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Planning area name or None if not found
    """
    _, prepared_list, tree, name_list = _load_planning_areas_raw()

    if tree is None or not prepared_list:
        return None

    point = Point(lon, lat)

    candidate_indices = tree.query(point)
    for idx in candidate_indices:
        name = name_list[idx]
        _, prepared_geom = prepared_list[idx]
        if prepared_geom.contains(point):
            return name

    return None


def get_planning_areas_for_points(lat: pd.Series, lon: pd.Series) -> pd.Series:
    """Batch point-in-polygon lookup for many coordinates at once.

    Single vectorized ``geopandas.sjoin`` over the planning-area polygons -- far
    faster than calling :func:`get_planning_area_for_point` per row when there
    are many coordinates (e.g. the ~10k unique coords derived in
    ``location_dim``). Mirrors the single-point function's first-match-wins and
    miss-returns-None semantics.

    Args:
        lat: Latitudes (Series, any index).
        lon: Longitudes (Series, same length as ``lat``).

    Returns:
        Series of planning-area names aligned to ``lat.index``; ``None`` for
        misses (point outside every polygon, or NaN coordinates) and when the
        planning-area polygons are unavailable.
    """
    import geopandas as gpd

    miss = pd.Series([None] * len(lat), index=lat.index, dtype=object)

    polys = load_planning_areas()
    if not polys:
        return miss

    valid = [
        (p["name"], p["geometry"])
        for p in polys
        if p.get("geometry") is not None and not p["geometry"].is_empty
    ]
    if not valid:
        return miss

    poly_gdf = gpd.GeoDataFrame(
        {"planning_area": [name for name, _ in valid]},
        geometry=[geom for _, geom in valid],
        crs="EPSG:4326",
    )

    pts_lat = pd.to_numeric(pd.Series(lat), errors="coerce")
    pts_lon = pd.to_numeric(pd.Series(lon), errors="coerce")
    mask = pts_lat.notna() & pts_lon.notna()
    if not mask.any():
        return miss

    points = gpd.GeoDataFrame(
        {"_idx": pts_lat[mask].index.to_numpy()},
        geometry=gpd.points_from_xy(pts_lon[mask].to_numpy(), pts_lat[mask].to_numpy()),
        crs="EPSG:4326",
    )

    joined = gpd.sjoin(points, poly_gdf, how="left", predicate="within")
    # Sliver overlaps can match multiple polygons; keep the first to mirror
    # get_planning_area_for_point's first-candidate-wins behaviour, then drop
    # the left-join misses (planning_area is NaN for points outside everything).
    joined = joined.drop_duplicates(subset="_idx", keep="first")
    joined = joined.dropna(subset=["planning_area"])

    result = miss.copy()
    if not joined.empty:
        result.loc[joined["_idx"].tolist()] = joined["planning_area"].tolist()
    return result


def load_market_summary() -> pd.DataFrame:
    """
    Load precomputed market summary table.

    Returns:
        DataFrame with aggregated market statistics
    """
    return _read_first_existing(
        _get("platinum_dir") / "metrics" / "pa_monthly_metrics.parquet",
        _get("pipeline_dir") / "L3" / "market_summary.parquet",
    )


def load_planning_area_metrics() -> pd.DataFrame:
    """
    Load precomputed planning area metrics.

    Returns:
        DataFrame with metrics by planning area from pa_monthly_metrics.
    """
    return _read_first_existing(
        _get("platinum_dir") / "metrics" / "pa_monthly_metrics.parquet",
        _get("pipeline_dir") / "L3" / "planning_area_metrics.parquet",
    )


def load_unified_data() -> pd.DataFrame:
    """
    Load the unified housing dataset (L3).

    Returns:
        DataFrame with all housing transactions and features
    """
    df = _read_first_existing(
        _get("platinum_dir") / "unified_dataset.parquet",
        _get("pipeline_dir") / "L3" / "housing_unified.parquet",
    )

    if df.empty:
        logger.warning("Unified dataset not found at any expected path")
        return df

    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    logger.info("Loaded %s records from unified dataset", len(df))
    return df
