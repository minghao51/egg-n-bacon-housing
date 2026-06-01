"""02_cleaning: Silver layer cleaning and validation (Hamilton DAG node).

This module provides Hamilton-compatible functions for cleaning and
validating bronze data into the silver layer.
"""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from hamilton.function_modifiers import check_output

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.contracts import require_columns
from egg_n_bacon_housing.utils.io_helpers import save_parquet
from egg_n_bacon_housing.utils.validation import validate_schema

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
    df = df[df["price"] > 0]

    return df


def _quarantine_path(silver_dir: Path, dataset_name: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return silver_dir / "_quarantine" / f"{dataset_name}_{timestamp}.parquet"


@check_output(data_type=pd.DataFrame, importance="warn")
def hdb_validated(cleaned_hdb_transactions: pd.DataFrame, silver_dir: Path) -> pd.DataFrame:
    """Validate HDB transactions against schema."""
    from egg_n_bacon_housing.schemas.clean_models import HCleanHDBTransaction

    valid_df, quarantine_df = validate_schema(cleaned_hdb_transactions, HCleanHDBTransaction, "HDB")

    save_parquet(
        valid_df, silver_dir / "cleaned_hdb_transactions.parquet", "validated HDB transactions"
    )

    if not quarantine_df.empty:
        q_path = _quarantine_path(silver_dir, "hdb_transactions")
        save_parquet(quarantine_df, q_path, "quarantined HDB transactions")

    return valid_df


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

    df = df.dropna(subset=["price", "transaction_date"])
    df = df[df["price"] > 0]

    return df


@check_output(data_type=pd.DataFrame, importance="warn")
def condo_validated(cleaned_condo_transactions: pd.DataFrame, silver_dir: Path) -> pd.DataFrame:
    """Validate condo transactions against schema."""
    from egg_n_bacon_housing.schemas.clean_models import HCleanCondoTransaction

    valid_df, quarantine_df = validate_schema(
        cleaned_condo_transactions, HCleanCondoTransaction, "condo"
    )

    save_parquet(
        valid_df, silver_dir / "cleaned_condo_transactions.parquet", "validated condo transactions"
    )

    if not quarantine_df.empty:
        q_path = _quarantine_path(silver_dir, "condo_transactions")
        save_parquet(quarantine_df, q_path, "quarantined condo transactions")

    return valid_df


def geocoded_properties(
    hdb_validated: pd.DataFrame, condo_validated: pd.DataFrame, silver_dir: Path
) -> pd.DataFrame:
    """Merge geocoding data onto validated transactions.

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

    if "lat" not in combined.columns or "lon" not in combined.columns:
        logger.warning(
            "lat/lon columns missing from validated datasets — "
            "geocoding must happen externally before coordinate coverage checks"
        )
        combined["lat"] = pd.NA
        combined["lon"] = pd.NA
    else:
        coordinate_coverage = combined[["lat", "lon"]].notna().all(axis=1).mean()
        min_coverage = settings.geocoding.min_coordinate_coverage
        if coordinate_coverage < min_coverage:
            logger.warning(
                f"Geocoding coverage too low: {coordinate_coverage:.1%} "
                f"(required >= {min_coverage:.1%}) — proceeding without coordinate gate"
            )

    save_parquet(combined, silver_dir / "geocoded_properties.parquet", "geocoded properties")

    return combined


@check_output(data_type=pd.DataFrame, importance="warn")
def geocoded_validated(geocoded_properties: pd.DataFrame, silver_dir: Path) -> pd.DataFrame:
    """Validate geocoded properties against schema."""
    from egg_n_bacon_housing.schemas.clean_models import GeocodedProperty

    valid_df, quarantine_df = validate_schema(geocoded_properties, GeocodedProperty, "geocoded")

    save_parquet(
        valid_df,
        silver_dir / "validated_geocoded_properties.parquet",
        "validated geocoded properties",
    )

    if not quarantine_df.empty:
        q_path = _quarantine_path(silver_dir, "geocoded_properties")
        save_parquet(quarantine_df, q_path, "quarantined geocoded records")

    return valid_df
