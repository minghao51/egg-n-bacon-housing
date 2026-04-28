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

_planning_areas: list[dict] | None = None


def _read_first_existing(*paths: Path) -> pd.DataFrame:
    """Read the first existing parquet path, else return an empty DataFrame."""
    for path in paths:
        if path.exists():
            return pd.read_parquet(path)
    logger.warning(f"No dataset found at any expected path: {[str(p) for p in paths]}")
    return pd.DataFrame()


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
    return _read_first_existing(
        settings.gold_dir / "features_with_amenities.parquet",
        DATA_DIR / "L2" / "hdb_amenities.parquet",
    )


def load_rental_yield_data() -> pd.DataFrame:
    """
    Load precomputed rental yield data by town and month.

    Returns:
        DataFrame with rental yield percentages
    """
    return _read_first_existing(
        settings.gold_dir / "rental_yield.parquet",
        DATA_DIR / "L2" / "rental_yield.parquet",
    )


def load_market_summary() -> pd.DataFrame:
    """
    Load precomputed market summary table.

    Returns:
        DataFrame with aggregated market statistics
    """
    return _read_first_existing(
        settings.platinum_dir / "metrics" / "L5_price_metrics_by_area.parquet",
        DATA_DIR / "L3" / "market_summary.parquet",
    )


def load_planning_area_metrics() -> pd.DataFrame:
    """
    Load precomputed planning area metrics.

    Returns:
        DataFrame with metrics by planning area. Tries to merge price metrics
        and affordability metrics into a combined result; falls back to whichever
        platinum file exists, then to the legacy path.
    """
    price_path = settings.platinum_dir / "metrics" / "L5_price_metrics_by_area.parquet"
    affordability_path = settings.platinum_dir / "metrics" / "L5_affordability_by_area.parquet"
    legacy_path = DATA_DIR / "L3" / "planning_area_metrics.parquet"

    price_df = pd.read_parquet(price_path) if price_path.exists() else pd.DataFrame()
    affordability_df = (
        pd.read_parquet(affordability_path) if affordability_path.exists() else pd.DataFrame()
    )

    if not price_df.empty and not affordability_df.empty:
        common_cols = ["planning_area", "town"]
        merge_cols = [
            c for c in common_cols if c in price_df.columns and c in affordability_df.columns
        ]
        if merge_cols:
            merged = price_df.merge(
                affordability_df,
                on=merge_cols,
                how="outer",
                suffixes=("", "_affordability"),
            )
            logger.info(f"Merged price and affordability metrics: {len(merged)} rows")
            return merged
        logger.warning(
            "No common key to merge price and affordability metrics, returning price only"
        )

    if not price_df.empty:
        return price_df
    if not affordability_df.empty:
        return affordability_df
    if legacy_path.exists():
        return pd.read_parquet(legacy_path)

    logger.warning("Planning area metrics not found at any expected path")
    return pd.DataFrame()


def load_rental_yield_top_combos() -> pd.DataFrame:
    """
    Load precomputed top rental yield combinations.

    Returns:
        DataFrame with town/flat_type combinations ranked by yield
    """
    return _read_first_existing(
        settings.platinum_dir / "metrics" / "L5_rental_yield_by_area.parquet",
        DATA_DIR / "L3" / "rental_yield_top_combos.parquet",
    )


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

        stage_file_map = {
            "L0": {
                PropertyType.HDB: settings.bronze_dir / "raw_hdb_resale.parquet",
                PropertyType.CONDO: settings.bronze_dir / "raw_condo_transactions.parquet",
                PropertyType.EC: settings.bronze_dir / "raw_condo_transactions.parquet",
            },
            "L1": {
                PropertyType.HDB: settings.silver_dir / "cleaned_hdb_transactions.parquet",
                PropertyType.CONDO: settings.silver_dir / "cleaned_condo_transactions.parquet",
                PropertyType.EC: settings.silver_dir / "cleaned_ec_transactions.parquet",
            },
            "L2": {
                PropertyType.HDB: settings.gold_dir / "unified_features.parquet",
                PropertyType.CONDO: settings.gold_dir / "unified_features.parquet",
                PropertyType.EC: settings.gold_dir / "unified_features.parquet",
            },
            "L3": {
                PropertyType.HDB: settings.platinum_dir / "unified_dataset.parquet",
                PropertyType.CONDO: settings.platinum_dir / "unified_dataset.parquet",
                PropertyType.EC: settings.platinum_dir / "unified_dataset.parquet",
            },
        }
        path = stage_file_map[stage][property_type]

        if not path.exists():
            if settings.logging.verbose:
                logger.warning(f"Transaction file not found: {path}")
            return pd.DataFrame()

        df = pd.read_parquet(path)
        return self._filter_by_property_type(df, property_type)

    def _filter_by_property_type(
        self, df: pd.DataFrame, property_type: PropertyType
    ) -> pd.DataFrame:
        """Return rows for the requested property type when a type column is present."""
        if df.empty or "property_type" not in df.columns:
            return df

        property_series = df["property_type"].astype(str).str.strip().str.lower()
        filtered = df.loc[property_series == property_type.value].copy()

        if filtered.empty and settings.logging.verbose:
            logger.warning(
                f"No rows matched property_type={property_type.value} in loaded transaction dataset"
            )

        return filtered

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
    df = _read_first_existing(
        settings.platinum_dir / "unified_dataset.parquet",
        settings.data_dir / "pipeline" / "L3" / "housing_unified.parquet",
    )

    if df.empty:
        logger.warning("Unified dataset not found at any expected path")
        return df

    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    logger.info(f"Loaded {len(df)} records from unified dataset")
    return df
