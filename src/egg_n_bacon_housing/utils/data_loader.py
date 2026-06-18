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


class CSVLoader:
    """Load manual CSV data sources."""

    def __init__(self, base_path: Path | None = None):
        """Initialize loader.

        Args:
            base_path: Base path for CSV files (defaults to configured manual dir)
        """
        self.base_path = base_path or _get("manual_dir")

    def load_ura_data(self, base_path: Path | None = None) -> dict[str, pd.DataFrame]:
        """Load URA private property data.

        Args:
            base_path: Base path for CSV files (defaults to settings.data_dir / "manual")

        Returns:
            Dictionary with keys: 'ec', 'condo', 'condo_rental', 'ec_rental'
        """
        if base_path is None:
            base_path = self.base_path

        ura_dir = base_path / "csv" / "ura"

        result = {}

        ec_path = ura_dir / "ec.csv"
        if ec_path.exists():
            result["ec"] = pd.read_csv(ec_path, encoding="latin1")

        condo_path = ura_dir / "condo.csv"
        if condo_path.exists():
            result["condo"] = pd.read_csv(condo_path, encoding="latin1")

        condo_rental_path = ura_dir / "condo_rental.csv"
        if condo_rental_path.exists():
            result["condo_rental"] = pd.read_csv(condo_rental_path, encoding="latin1")

        ec_rental_path = ura_dir / "ec_rental.csv"
        if ec_rental_path.exists():
            result["ec_rental"] = pd.read_csv(ec_rental_path, encoding="latin1")

        return result

    def load_hdb_resale(self, base_path: Path | None = None) -> pd.DataFrame:
        """Load HDB resale price data.

        Args:
            base_path: Base path for CSV files (defaults to settings.data_dir / "manual")

        Returns:
            Combined DataFrame of all resale files, empty DataFrame if directory missing
        """
        if base_path is None:
            base_path = self.base_path

        resale_dir = base_path / "csv" / "ResaleFlatPrices"

        if not resale_dir.exists():
            logger.warning("HDB resale directory not found: %s", resale_dir)
            return pd.DataFrame()

        files = list(resale_dir.glob("*.csv"))

        if not files:
            logger.warning("No CSV files found in: %s", resale_dir)
            return pd.DataFrame()

        dfs = [pd.read_csv(f) for f in files]

        return pd.concat(dfs, ignore_index=True)

    def load_csv(self, filename: str, base_path: Path | None = None, **kwargs) -> pd.DataFrame:
        """Load a single CSV file.

        Args:
            filename: Name of CSV file (can include subdirectory like 'ura/ec.csv')
            base_path: Base path for CSV files (defaults to settings.data_dir / "manual")
            **kwargs: Additional arguments passed to pd.read_csv

        Returns:
            DataFrame with CSV data, empty DataFrame if file not found
        """
        if base_path is None:
            base_path = self.base_path

        path = base_path / filename

        if not path.exists():
            logger.warning("CSV file not found: %s", path)
            return pd.DataFrame()

        return pd.read_csv(path, **kwargs)


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
