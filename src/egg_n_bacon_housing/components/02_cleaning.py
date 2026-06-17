"""02_cleaning: Silver layer cleaning and validation (Hamilton DAG node).

This module provides Hamilton-compatible functions for cleaning and
validating bronze data into the silver layer.
"""

import logging
from pathlib import Path

import pandas as pd

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.schemas.clean_models import (
    GeocodedProperty,
    HCleanCondoTransaction,
    HCleanHDBTransaction,
)
from egg_n_bacon_housing.utils.contracts import require_columns
from egg_n_bacon_housing.utils.geocoding import build_default_geocoder
from egg_n_bacon_housing.utils.io_helpers import save_parquet
from egg_n_bacon_housing.utils.validation_gateway import validate_and_quarantine

logger = logging.getLogger(__name__)


def cleaned_hdb_transactions(
    raw_hdb_resale_transactions: pd.DataFrame, silver_dir: Path
) -> pd.DataFrame:
    """Clean and validate HDB resale transactions.

    Args:
        raw_hdb_resale_transactions: Raw bronze data.

    Returns:
        Cleaned DataFrame with validated fields.
    """
    if raw_hdb_resale_transactions.empty:
        return pd.DataFrame()

    df = raw_hdb_resale_transactions.copy()
    require_columns(df, {"month"}, "raw_hdb_resale_transactions")

    if "resale_price" in df.columns:
        df = df.rename(columns={"resale_price": "price"})

    if "floor_area_sqm" in df.columns and "floor_area_sqft" not in df.columns:
        df["floor_area_sqft"] = df["floor_area_sqm"] * 10.764

    if "month" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")

    if "property_type" not in df.columns:
        df["property_type"] = "hdb"

    if (
        "remaining_lease_months" in df.columns
        and "lease_commence_date" in df.columns
        and "transaction_date" in df.columns
    ):
        mask = df["remaining_lease_months"].isna()
        if mask.any():
            lease_commence_year = pd.to_numeric(
                df.loc[mask, "lease_commence_date"], errors="coerce"
            )
            transaction_year = pd.to_numeric(
                df.loc[mask, "transaction_date"].dt.year,
                errors="coerce",
            )
            remaining_lease_years = 99 - (transaction_year - lease_commence_year)
            df.loc[mask, "remaining_lease_months"] = (remaining_lease_years * 12).clip(lower=0)

    if "storey_range" in df.columns and "storey_min" not in df.columns:
        storey_parts = df["storey_range"].str.split(" TO ", n=1, expand=True)
        df["storey_min"] = pd.to_numeric(storey_parts[0], errors="coerce").astype("Int64")
        df["storey_max"] = pd.to_numeric(storey_parts[1], errors="coerce").astype("Int64")

    if "address" not in df.columns and "block" in df.columns and "street_name" in df.columns:
        df["address"] = df["block"] + " " + df["street_name"]

    df = df.dropna(subset=["price", "transaction_date"])
    return df[df["price"] > 0]


def hdb_validated(cleaned_hdb_transactions: pd.DataFrame, silver_dir: Path) -> pd.DataFrame:
    """Validate HDB transactions against schema."""
    return validate_and_quarantine(
        cleaned_hdb_transactions,
        HCleanHDBTransaction,
        "HDB",
        layer_dir=silver_dir,
        filename="cleaned_hdb_transactions.parquet",
    )


def cleaned_condo_transactions(
    raw_condo_transactions: pd.DataFrame, silver_dir: Path
) -> pd.DataFrame:
    """Clean and validate condo transactions.

    Args:
        raw_condo_transactions: Raw bronze data.

    Returns:
        Cleaned DataFrame.
    """
    if raw_condo_transactions.empty:
        return pd.DataFrame()

    df = raw_condo_transactions.copy()
    require_columns(df, {"price"}, "raw_condo_transactions")

    if "transaction_date" not in df.columns and "date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["date"], errors="coerce")

    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

    if "area_sqft" in df.columns and "floor_area_sqft" not in df.columns:
        df["floor_area_sqft"] = pd.to_numeric(df["area_sqft"], errors="coerce")

    if "area_sqm" in df.columns and "floor_area_sqm" not in df.columns:
        df["floor_area_sqm"] = pd.to_numeric(df["area_sqm"], errors="coerce")

    if "postal_district" in df.columns:
        df["postal_district"] = pd.to_numeric(df["postal_district"], errors="coerce").astype(
            "Int64"
        )

    if "address" not in df.columns:
        if "street_name" in df.columns:
            df["address"] = df["street_name"].fillna("")
        else:
            df["address"] = ""

    if "area" not in df.columns:
        df["area"] = ""

    if "project_name" not in df.columns:
        df["project_name"] = ""

    if "tenure" not in df.columns:
        df["tenure"] = ""

    df = df.dropna(subset=["price", "transaction_date"])
    return df[df["price"] > 0]


def condo_validated(cleaned_condo_transactions: pd.DataFrame, silver_dir: Path) -> pd.DataFrame:
    """Validate condo transactions against schema."""
    return validate_and_quarantine(
        cleaned_condo_transactions,
        HCleanCondoTransaction,
        "condo",
        layer_dir=silver_dir,
        filename="cleaned_condo_transactions.parquet",
    )


def geocoded_properties(
    hdb_validated: pd.DataFrame,
    condo_validated: pd.DataFrame,
    silver_dir: Path,
    min_coordinate_coverage: float = 0.7,
) -> pd.DataFrame:
    """Merge validated transactions and geocode addresses via OneMap.

    Uses a cache-first bulk lookup: hashes all unique addresses, reads
    cached parquet files in bulk, then makes parallel API calls only
    for uncached addresses.

    Args:
        hdb_validated: Validated HDB transactions.
        condo_validated: Validated condo transactions.

    Returns:
        DataFrame with lat/lon coordinates.
    """

    dfs = []
    for df, ptype in [(hdb_validated, "hdb"), (condo_validated, "condo")]:
        if df.empty:
            continue
        df = df.copy()
        df["property_type"] = ptype
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)

    cached_path = silver_dir / "geocoded_properties.parquet"
    if cached_path.exists():
        existing = pd.read_parquet(cached_path)
        if "lat" in existing.columns and existing["lat"].notna().any():
            logger.info("Loading pre-geocoded properties from %s", cached_path)
            return existing

    address_col = "address" if "address" in combined.columns else None
    if address_col is None:
        combined["lat"] = pd.NA
        combined["lon"] = pd.NA
        logger.warning("No address column found — skipping geocoding")
        save_parquet(combined, cached_path, "geocoded properties (no address)")
        return combined

    unique_addresses = combined[address_col].dropna().astype(str).unique().tolist()
    logger.info("Geocoding %s unique addresses...", len(unique_addresses))

    geocoder = build_default_geocoder(settings)
    lookup = geocoder.geocode(pd.Series(unique_addresses, name=address_col))

    coord_map = lookup.set_index("input")[["lat", "lon"]]
    combined["lat"] = combined[address_col].map(coord_map["lat"])
    combined["lon"] = combined[address_col].map(coord_map["lon"])

    coverage = combined[["lat", "lon"]].notna().all(axis=1).mean()
    logger.info("Geocoding coverage: %.1f%%", coverage * 100)

    if coverage < min_coordinate_coverage:
        logger.warning(
            "Geocoding coverage %.1f%% below threshold %.1f%% — proceeding regardless",
            coverage * 100,
            min_coordinate_coverage * 100,
        )

    save_parquet(combined, cached_path, "geocoded properties")
    return combined


def geocoded_validated(geocoded_properties: pd.DataFrame, silver_dir: Path) -> pd.DataFrame:
    """Validate geocoded properties against schema."""
    return validate_and_quarantine(
        geocoded_properties,
        GeocodedProperty,
        "geocoded",
        layer_dir=silver_dir,
        filename="validated_geocoded_properties.parquet",
    )
