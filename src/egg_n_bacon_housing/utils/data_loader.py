"""Data loading utilities for Singapore Housing Price Pipeline.

This module provides optimized data loading functions with caching
for HDB, Condo, and amenity data.
"""

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Literal

import pandas as pd
from shapely.geometry import Point, shape

from egg_n_bacon_housing.config import settings

logger = logging.getLogger(__name__)

DATA_DIR = settings.data_dir / "pipeline"
RAW_DATA_DIR = settings.data_dir / "manual" / "geojsons"
SINGAPORE_CENTER = {"lat": 1.3521, "lon": 103.8198}

_planning_areas = None


def load_planning_areas() -> list[dict]:
    """
    Load Singapore planning area polygons from GeoJSON.

    Returns:
        List of planning areas with properties and geometry
    """
    global _planning_areas

    if _planning_areas is not None:
        return _planning_areas

    geojson_path = RAW_DATA_DIR / "onemap_planning_area_polygon.geojson"

    if not geojson_path.exists():
        logger.warning(f"Planning area GeoJSON not found at {geojson_path}")
        _planning_areas = []
        return _planning_areas

    try:
        with open(geojson_path) as f:
            geojson_data = json.load(f)

        planning_areas = []
        for feature in geojson_data.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry")

            planning_areas.append(
                {
                    "name": props.get("pln_area_n", "Unknown"),
                    "geometry": shape(geom) if geom else None,
                }
            )

        _planning_areas = planning_areas
        return _planning_areas

    except Exception as e:
        logger.warning(f"Error loading planning areas: {e}")
        _planning_areas = []
        return _planning_areas


def get_planning_area_for_point(lat: float, lon: float) -> str | None:
    """
    Get the planning area name for a given lat/lon coordinate.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Planning area name or None if not found
    """
    planning_areas = load_planning_areas()

    if not planning_areas:
        return None

    point = Point(lon, lat)

    for area in planning_areas:
        if area["geometry"] and area["geometry"].contains(point):
            return area["name"]

    return None


def load_hdb_amenity_data() -> pd.DataFrame:
    """
    Load HDB amenity data (car parks, schools, etc.).

    Returns:
        DataFrame with amenity locations
    """
    path = DATA_DIR / "L2" / "hdb_amenities.parquet"

    if not path.exists():
        logger.warning(f"HDB amenity data not found at {path}")
        return pd.DataFrame()

    return pd.read_parquet(path)


def load_rental_yield_data() -> pd.DataFrame:
    """
    Load precomputed rental yield data by town and month.

    Returns:
        DataFrame with rental yield percentages
    """
    path = DATA_DIR / "L2" / "rental_yield.parquet"

    if not path.exists():
        logger.warning(f"Rental yield data not found at {path}")
        return pd.DataFrame()

    return pd.read_parquet(path)


def load_market_summary() -> pd.DataFrame:
    """
    Load precomputed market summary table.

    Returns:
        DataFrame with aggregated market statistics
    """
    path = DATA_DIR / "L3" / "market_summary.parquet"

    if not path.exists():
        logger.warning(f"Market summary not found at {path}")
        return pd.DataFrame()

    return pd.read_parquet(path)


def load_planning_area_metrics() -> pd.DataFrame:
    """
    Load precomputed planning area metrics.

    Returns:
        DataFrame with metrics by planning area
    """
    path = DATA_DIR / "L3" / "planning_area_metrics.parquet"

    if not path.exists():
        logger.warning(f"Planning area metrics not found at {path}")
        return pd.DataFrame()

    return pd.read_parquet(path)


def load_rental_yield_top_combos() -> pd.DataFrame:
    """
    Load precomputed top rental yield combinations.

    Returns:
        DataFrame with town/flat_type combinations ranked by yield
    """
    path = DATA_DIR / "L3" / "rental_yield_top_combos.parquet"

    if not path.exists():
        logger.warning(f"Rental yield combos not found at {path}")
        return pd.DataFrame()

    return pd.read_parquet(path)


class PropertyType(Enum):
    """Property type enumeration."""

    HDB = "hdb"
    CONDO = "condo"
    EC = "ec"


class TransactionLoader:
    """Load transaction data from L1 parquet files.

    This class provides a consistent interface for loading transaction data
    across different property types and pipeline stages. Uses settings path constants
    to ensure single source of truth for data locations.
    """

    def __init__(self, use_config_paths: bool = True):
        """Initialize loader.

        Args:
            use_config_paths: If True, use settings path constants; else use custom base
        """
        self.use_config_paths = use_config_paths

    def load_transaction(
        self,
        property_type: PropertyType | str,
        stage: Literal["L0", "L1", "L2", "L3"] = "L1",
    ) -> pd.DataFrame:
        """Load transaction data for a property type.

        Args:
            property_type: Type of property (HDB, CONDO, EC) as enum or string
            stage: Pipeline stage (default "L1")

        Returns:
            DataFrame with transaction data, empty DataFrame if file not found
        """
        if isinstance(property_type, str):
            property_type = PropertyType(property_type.lower())

        dataset_name_map = {
            PropertyType.HDB: "housing_hdb_transaction",
            PropertyType.CONDO: "housing_condo_transaction",
            PropertyType.EC: "housing_ec_transaction",
        }
        dataset_name = dataset_name_map[property_type]

        stage_map = {
            "L0": settings.bronze_dir,
            "L1": settings.silver_dir,
            "L2": settings.gold_dir,
            "L3": settings.platinum_dir,
        }
        stage_dir = stage_map[stage]
        path = stage_dir / f"{dataset_name}.parquet"

        if not path.exists():
            if settings.logging.verbose:
                logger.warning(f"Transaction file not found: {path}")
            return pd.DataFrame()

        return pd.read_parquet(path)

    def load_all_transactions(
        self, stage: Literal["L0", "L1", "L2", "L3"] = "L1"
    ) -> dict[PropertyType, pd.DataFrame]:
        """Load all transaction types.

        Args:
            stage: Pipeline stage (default "L1")

        Returns:
            Dictionary mapping property type to DataFrame
        """
        return {pt: self.load_transaction(pt, stage) for pt in PropertyType}


class CSVLoader:
    """Load manual CSV data sources.

    This class provides a consistent interface for loading CSV data from
    manual downloads (URA, HDB resale, etc.). Uses settings path constants.
    """

    def __init__(self, base_path: Path | None = None):
        """Initialize loader.

        Args:
            base_path: Base path for CSV files (defaults to settings.data_dir / "manual")
        """
        self.base_path = base_path or settings.data_dir / "manual"

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
            if settings.logging.verbose:
                logger.warning(f"HDB resale directory not found: {resale_dir}")
            return pd.DataFrame()

        files = list(resale_dir.glob("*.csv"))

        if not files:
            if settings.logging.verbose:
                logger.warning(f"No CSV files found in: {resale_dir}")
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
            if settings.logging.verbose:
                logger.warning(f"CSV file not found: {path}")
            return pd.DataFrame()

        return pd.read_csv(path, **kwargs)


def load_unified_data() -> pd.DataFrame:
    """
    Load the unified housing dataset (L3).

    Returns:
        DataFrame with all housing transactions and features
    """
    path = settings.data_dir / "pipeline" / "L3" / "housing_unified.parquet"

    if not path.exists():
        logger.warning(f"Unified dataset not found at {path}")
        return pd.DataFrame()

    logger.info(f"Loading unified dataset from {path}")
    df = pd.read_parquet(path)

    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    logger.info(f"Loaded {len(df)} records from unified dataset")

    return df
