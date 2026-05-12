"""Geocoding adapters for URA transaction processing.

This module provides reusable functions for:
- Loading URA CSV files
- Extracting unique property addresses
- Fetching geocoding data from OneMap API

Uses settings from egg_n_bacon_housing.config for data directory paths.
"""

import re
from pathlib import Path

import pandas as pd

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.data_loader import CSVLoader
from egg_n_bacon_housing.utils.logging_config import get_logger

logger = get_logger(__name__)


def load_ura_files(
    base_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all URA transaction CSV files.

    Args:
        base_path: Base path to data directory (defaults to settings.data_dir / "manual")

    Returns:
        Tuple of (ec_df, condo_df, hdb_df)
    """
    csv_loader = CSVLoader(base_path=base_path)

    ec_list = settings.ura_ec_files
    condo_list = settings.ura_condo_files

    ura_dir = settings.data_dir / "manual" / "csv" / "ura"

    ec_dfs = [pd.read_csv(ura_dir / f"{ec}.csv", encoding="latin1") for ec in ec_list]
    ec_df = pd.concat(ec_dfs, ignore_index=True)
    logger.info("loaded_ura_ec rows=%s files=%s", len(ec_df), len(ec_list))

    condo_dfs = [pd.read_csv(ura_dir / f"{condo}.csv", encoding="latin1") for condo in condo_list]
    condo_df = pd.concat(condo_dfs, ignore_index=True)
    condo_df["Area (SQM)"] = condo_df["Area (SQM)"].str.replace(",", "").str.strip()
    condo_df["Area (SQM)"] = pd.to_numeric(condo_df["Area (SQM)"], errors="coerce")
    logger.info("loaded_ura_condo rows=%s files=%s", len(condo_df), len(condo_list))

    hdb_df = csv_loader.load_hdb_resale(base_path=base_path)

    def standardize_lease_duration(lease):
        if pd.isna(lease):
            return None
        if isinstance(lease, (int, float)):
            return int(lease * 12) if lease < 50 else int(lease)
        lease_str = str(lease).strip()
        if lease_str.isdigit():
            return int(lease_str) * 12
        match = re.match(r"(\d+)\s*years?\s*(\d+)\s*months?", lease_str)
        if match:
            years = int(match.group(1))
            months = int(match.group(2))
            return years * 12 + months
        match = re.match(r"(\d+)\s*years?", lease_str)
        if match:
            return int(match.group(1)) * 12
        return None

    if "remaining_lease" in hdb_df.columns:
        hdb_df["remaining_lease_months"] = hdb_df["remaining_lease"].apply(
            standardize_lease_duration
        )
        hdb_df.drop("remaining_lease", axis=1, inplace=True)
        logger.info("loaded_hdb_resale rows=%s lease_standardized=true", len(hdb_df))
    else:
        logger.info("loaded_hdb_resale rows=%s lease_standardized=false", len(hdb_df))

    return ec_df, condo_df, hdb_df


def extract_unique_addresses(
    ec_df: pd.DataFrame, condo_df: pd.DataFrame, hdb_df: pd.DataFrame
) -> pd.DataFrame:
    """Extract unique property addresses from all transaction data.

    Args:
        ec_df: Executive condominium transactions
        condo_df: Condo transactions
        hdb_df: HDB transactions

    Returns:
        DataFrame with unique addresses and property types
    """
    condo_df = condo_df.copy()
    ec_df = ec_df.copy()
    hdb_df = hdb_df.copy()

    condo_df["property_type"] = "private"
    ec_df["property_type"] = "private"
    hdb_df["property_type"] = "hdb"

    housing_df = pd.concat(
        [
            condo_df[["Project Name", "Street Name", "property_type"]].drop_duplicates(),
            ec_df[["Project Name", "Street Name", "property_type"]].drop_duplicates(),
            hdb_df[["block", "street_name", "property_type"]].drop_duplicates(),
        ],
        ignore_index=True,
    )

    name_address_list = ["Project Name", "Street Name", "block", "street_name"]
    for col in name_address_list:
        housing_df[col] = housing_df[col].fillna("")
    housing_df["NameAddress"] = housing_df[name_address_list].agg(" ".join, axis=1)
    housing_df["NameAddress"] = [addr.strip() for addr in housing_df["NameAddress"]]

    logger.info("extracted_unique_addresses rows=%s", len(housing_df))
    return housing_df
