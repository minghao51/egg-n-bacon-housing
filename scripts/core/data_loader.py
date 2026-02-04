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

from scripts.core.config import Config

logger = logging.getLogger(__name__)

# Constants
DATA_DIR = Config.PIPELINE_DIR
RAW_DATA_DIR = Config.MANUAL_DIR / "geojsons"
SINGAPORE_CENTER = {"lat": 1.3521, "lon": 103.8198}


# Global cache for planning areas
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

        # Extract features and convert geometries to shapely objects
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


# ============================================================================
# DATA LOADER FACTORY CLASSES (For Pipeline Usage)
# ============================================================================


class PropertyType(Enum):
    """Property type enumeration."""

    HDB = "hdb"
    CONDO = "condo"
    EC = "ec"


class TransactionLoader:
    """Load transaction data from L1 parquet files.

    This class provides a consistent interface for loading transaction data
    across different property types and pipeline stages. Uses Config path constants
    to ensure single source of truth for data locations.
    """

    def __init__(self, use_config_paths: bool = True):
        """Initialize loader.

        Args:
            use_config_paths: If True, use Config path constants; else use custom base
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
        # Convert string to PropertyType if needed
        if isinstance(property_type, str):
            property_type = PropertyType(property_type.lower())

        # Get dataset name from Config
        dataset_name_map = {
            PropertyType.HDB: Config.DATASET_HDB_TRANSACTION,
            PropertyType.CONDO: Config.DATASET_CONDO_TRANSACTION,
            PropertyType.EC: Config.DATASET_EC_TRANSACTION,
        }
        dataset_name = dataset_name_map[property_type]

        # Build path using Config constants
        stage_dir = getattr(Config, f"{stage}_DIR", Config.PARQUETS_DIR / stage)
        path = stage_dir / f"{dataset_name}.parquet"

        if not path.exists():
            if Config.VERBOSE_LOGGING:
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
    manual downloads (URA, HDB resale, etc.). Uses Config path constants.
    """

    def __init__(self, base_path: Path | None = None):
        """Initialize loader.

        Args:
            base_path: Base path for CSV files (defaults to Config.CSV_DIR)
        """
        self.base_path = base_path or Config.CSV_DIR

    def load_ura_data(self, base_path: Path | None = None) -> dict[str, pd.DataFrame]:
        """Load URA private property data.

        Args:
            base_path: Base path for CSV files (defaults to Config.CSV_DIR)

        Returns:
            Dictionary with keys: 'ec', 'condo', 'condo_rental', 'ec_rental'
        """
        if base_path is None:
            base_path = self.base_path

        ura_dir = base_path / "ura"

        result = {}

        # Load EC data
        ec_path = ura_dir / "ec.csv"
        if ec_path.exists():
            result["ec"] = pd.read_csv(ec_path, encoding="latin1")

        # Load condo data
        condo_path = ura_dir / "condo.csv"
        if condo_path.exists():
            result["condo"] = pd.read_csv(condo_path, encoding="latin1")

        # Load rental data if available
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
            base_path: Base path for CSV files (defaults to Config.CSV_DIR)

        Returns:
            Combined DataFrame of all resale files, empty DataFrame if directory missing
        """
        if base_path is None:
            base_path = self.base_path

        resale_dir = base_path / "ResaleFlatPrices"

        if not resale_dir.exists():
            if Config.VERBOSE_LOGGING:
                logger.warning(f"HDB resale directory not found: {resale_dir}")
            return pd.DataFrame()

        files = list(resale_dir.glob("*.csv"))

        if not files:
            if Config.VERBOSE_LOGGING:
                logger.warning(f"No CSV files found in: {resale_dir}")
            return pd.DataFrame()

        dfs = [pd.read_csv(f) for f in files]

        return pd.concat(dfs, ignore_index=True)

    def load_csv(self, filename: str, base_path: Path | None = None, **kwargs) -> pd.DataFrame:
        """Load a single CSV file.

        Args:
            filename: Name of CSV file (can include subdirectory like 'ura/ec.csv')
            base_path: Base path for CSV files (defaults to Config.CSV_DIR)
            **kwargs: Additional arguments passed to pd.read_csv

        Returns:
            DataFrame with CSV data, empty DataFrame if file not found
        """
        if base_path is None:
            base_path = self.base_path

        path = base_path / filename

        if not path.exists():
            if Config.VERBOSE_LOGGING:
                logger.warning(f"CSV file not found: {path}")
            return pd.DataFrame()

        return pd.read_csv(path, **kwargs)


def load_unified_data() -> pd.DataFrame:
    """
    Load the unified housing dataset (L3).

    Returns:
        DataFrame with all housing transactions and features
    """
    path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"

    if not path.exists():
        logger.warning(f"Unified dataset not found at {path}")
        return pd.DataFrame()

    logger.info(f"Loading unified dataset from {path}")
    df = pd.read_parquet(path)

    # Ensure transaction_date is datetime
    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    logger.info(f"Loaded {len(df)} records from unified dataset")

    return df
