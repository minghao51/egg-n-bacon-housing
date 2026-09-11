"""Spatial reference loading for the Singapore housing pipeline.

Planning-area polygons are loaded once from the OneMap GeoJSON into an
immutable ``SpatialReferenceRepository``; batched point-in-polygon lookup is
a single vectorized ``geopandas.sjoin``.
"""

import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from shapely.geometry import shape

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpatialReferenceRepository:
    """Planning-area reference data rooted at one immutable directory."""

    raw_data_dir: Path
    _lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, repr=False, compare=False
    )
    _cache: list[dict] | None = field(default=None, init=False, repr=False, compare=False)

    def _load(self) -> list[dict]:
        with self._lock:
            if self._cache is None:
                object.__setattr__(self, "_cache", _load_planning_areas_from(self.raw_data_dir))
            assert self._cache is not None
            return self._cache

    def load_planning_areas(self) -> list[dict]:
        return list(self._load())

    def planning_areas_for_points(self, lat: pd.Series, lon: pd.Series) -> pd.Series:
        return _planning_areas_for_points(self.load_planning_areas(), lat, lon)


def _load_planning_areas_from(raw_data_dir: Path) -> list[dict]:
    geojson_path = raw_data_dir / "onemap_planning_area_polygon.geojson"

    if not geojson_path.exists():
        logger.warning("Planning area GeoJSON not found at %s", geojson_path)
        return []

    try:
        with open(geojson_path) as f:
            geojson_data = json.load(f)

        planning_areas = []
        for feature in geojson_data.get("features", []):
            props = feature.get("properties", {})
            geom = shape(geom_data) if (geom_data := feature.get("geometry")) else None
            name = props.get("pln_area_n", "Unknown")
            planning_areas.append({"name": name, "geometry": geom})
        return planning_areas

    except (OSError, json.JSONDecodeError, ValueError, KeyError) as e:
        logger.warning("Error loading planning areas: %s", e)
        return []


def _planning_areas_for_points(polys: list[dict], lat: pd.Series, lon: pd.Series) -> pd.Series:
    """Batch point-in-polygon lookup for many coordinates at once.

    Single vectorized ``geopandas.sjoin`` over the planning-area polygons -- far
    faster than a row-wise point-in-polygon loop when there are many coordinates
    (e.g. the ~10k unique coords derived in ``location_dim``). Preserves
    first-match-wins and miss-returns-None semantics.

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
    # Sliver overlaps can match multiple polygons; keep the first to preserve
    # first-candidate-wins behaviour, then drop
    # the left-join misses (planning_area is NaN for points outside everything).
    joined = joined.drop_duplicates(subset="_idx", keep="first")
    joined = joined.dropna(subset=["planning_area"])

    result = miss.copy()
    if not joined.empty:
        result.loc[joined["_idx"].tolist()] = joined["planning_area"].tolist()
    return result
