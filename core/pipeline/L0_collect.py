"""L0: Data collection from data.gov.sg API.

This module provides functions for collecting raw data from the data.gov.sg API,
including private property transactions, rental indices, price indices, and HDB data.
"""

import logging
import re
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from src.config import Config
from src.data_helpers import save_parquet
from src.cache import cached_call

logger = logging.getLogger(__name__)


def fetch_datagovsg_dataset(url: str, dataset_id: str, use_cache: bool = True) -> pd.DataFrame:
    """
    Fetch data from data.gov.sg API with pagination support.

    Args:
        url: Base URL for the API request
        dataset_id: Dataset ID to fetch
        use_cache: Whether to use caching (default: True)

    Returns:
        DataFrame with fetched data, or empty DataFrame if no data

    Example:
        >>> df = fetch_datagovsg_dataset(
        ...     "https://data.gov.sg/api/action/datastore_search?resource_id=",
        ...     "d_5785799d63a9da091f4e0b456291eeb8"
        ... )
    """

    def _fetch_from_api():
        response_agg = []
        offset_value = 0
        total_records = 0
        current_url = url

        while True:
            try:
                response = requests.get(f"{current_url}{dataset_id}")
                response_text = response.json()

                # Extract records from response
                if "result" not in response_text or "records" not in response_text["result"]:
                    logger.warning(f"No records found in dataset {dataset_id}")
                    break

                records = response_text["result"]["records"]
                response_agg.append(pd.DataFrame(records))

                # Check pagination
                if "next" not in response_text["result"].get("_links", {}):
                    break

                # Get next URL
                next_url = response_text["result"]["_links"]["next"]
                current_url = "https://data.gov.sg" + next_url

                # Update offset for pagination
                match = re.search(r"offset=(\d+)", current_url)
                if match:
                    offset_value = int(match.group(1))
                    total_records = response_text["result"]["total"]

                    if offset_value > total_records:
                        break

            except Exception as e:
                logger.error(f"Error fetching dataset {dataset_id}: {e}")
                break

        if not response_agg:
            logger.warning(f"No data fetched for dataset {dataset_id}")
            return pd.DataFrame()

        return pd.concat(response_agg, ignore_index=True)

    # Use cache if enabled
    if use_cache and Config.USE_CACHING:
        cache_id = f"datagovsg:{dataset_id}"
        return cached_call(cache_id, _fetch_from_api, duration_hours=Config.CACHE_DURATION_HOURS)
    else:
        return _fetch_from_api()


def fetch_private_property_transactions() -> Optional[pd.DataFrame]:
    """Fetch private residential property transactions in rest of central region."""
    df = fetch_datagovsg_dataset(
        url="https://data.gov.sg/api/action/datastore_search?resource_id=",
        dataset_id="d_5785799d63a9da091f4e0b456291eeb8",
    )
    if not df.empty:
        save_parquet(df, "raw_datagov_general_sale", source="data.gov.sg API")
        logger.info(f"✅ Saved private property transactions: {len(df)} records")
        return df
    return None


def fetch_rental_index() -> Optional[pd.DataFrame]:
    """Fetch private residential property rental index."""
    df = fetch_datagovsg_dataset(
        url="https://data.gov.sg/api/action/datastore_search?resource_id=",
        dataset_id="d_8e4c50283fb7052a391dfb746a05c853",
    )
    if not df.empty:
        save_parquet(df, "raw_datagov_rental_index", source="data.gov.sg API")
        logger.info(f"✅ Saved rental index: {len(df)} records")
        return df
    return None


def fetch_price_index() -> Optional[pd.DataFrame]:
    """Fetch private residential property price index."""
    df = fetch_datagovsg_dataset(
        url="https://data.gov.sg/api/action/datastore_search?resource_id=",
        dataset_id="d_97f8a2e995022d311c6c68cfda6dae1af",
    )
    if not df.empty:
        save_parquet(df, "raw_datagov_price_index", source="data.gov.sg API")
        logger.info(f"✅ Saved price index: {len(df)} records")
        return df
    return None


def fetch_median_property_tax() -> Optional[pd.DataFrame]:
    """Fetch median annual value and property tax by property type."""
    df = fetch_datagovsg_dataset(
        url="https://data.gov.sg/api/action/datastore_search?resource_id=",
        dataset_id="d_774a81df45dca33112e59207e6dae1af",
    )
    if not df.empty:
        save_parquet(df, "raw_datagov_median_price_via_property_type", source="data.gov.sg API")
        logger.info(f"✅ Saved median property tax: {len(df)} records")
        return df
    return None


def fetch_private_transactions_whole() -> Optional[pd.DataFrame]:
    """Fetch private residential property transactions in whole of Singapore."""
    df = fetch_datagovsg_dataset(
        url="https://data.gov.sg/api/action/datastore_search?resource_id=",
        dataset_id="d_7c69c943d5f0d89d6a9a773d2b51f337",
    )
    if not df.empty:
        save_parquet(df, "raw_datagov_private_transactions_property_type", source="data.gov.sg API")
        logger.info(f"✅ Saved private transactions (whole SG): {len(df)} records")
        return df
    return None


def load_resale_flat_prices(csv_base_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Load HDB resale flat prices from CSV files.

    Args:
        csv_base_path: Base path to CSV files (defaults to Config.DATA_DIR / 'raw_data' / 'csv')

    Returns:
        DataFrame with all resale flat prices

    Example:
        >>> df = load_resale_flat_prices()
        >>> print(f"Loaded {len(df)} resale records")
    """
    if csv_base_path is None:
        csv_base_path = Config.DATA_DIR / "raw_data" / "csv"

    resale_prices_path = csv_base_path / "ResaleFlatPrices"
    resale_files = list(resale_prices_path.glob("*.csv"))

    if not resale_files:
        logger.warning(f"No CSV files found in {resale_prices_path}")
        return pd.DataFrame()

    logger.info(f"Found {len(resale_files)} resale flat price files")

    resale_dfs = []
    for file in resale_files:
        logger.info(f"Loading: {file.name}")
        df = pd.read_csv(file)
        resale_dfs.append(df)

    # Combine all resale data
    resale_flat_all = pd.concat(resale_dfs, ignore_index=True)
    logger.info(f"Total resale records: {len(resale_flat_all)}")

    # Convert remaining_lease to months
    if "remaining_lease" in resale_flat_all.columns:
        logger.info("Converting 'remaining_lease' from text to months...")
        resale_flat_all["remaining_lease_months"] = resale_flat_all["remaining_lease"].apply(
            _convert_lease_to_months
        )
        resale_flat_all["remaining_lease"] = resale_flat_all["remaining_lease"].astype(str)
        logger.info(
            f"Converted {resale_flat_all['remaining_lease_months'].notna().sum()} lease values"
        )

    return resale_flat_all


def _convert_lease_to_months(lease_str) -> Optional[int]:
    """Convert lease string like '61 years 04 months' to total months."""
    if pd.isna(lease_str):
        return None

    if isinstance(lease_str, (int, float)):
        return int(lease_str)

    lease_str = str(lease_str).lower()

    years_match = re.search(r"(\d+)\s*years?", lease_str)
    months_match = re.search(r"(\d+)\s*months?", lease_str)

    years = int(years_match.group(1)) if years_match else 0
    months = int(months_match.group(1)) if months_match else 0

    return years * 12 + months


def collect_all_datagovsg() -> dict:
    """
    Run all data.gov.sg data collection tasks.

    Returns:
        Dictionary with collection results

    Example:
        >>> results = collect_all_datagovsg()
        >>> print(f"Collected {len(results)} datasets")
    """
    logger.info("🚀 Starting data.gov.sg data collection")

    results = {}

    # Fetch from API
    results["private_transactions"] = fetch_private_property_transactions()
    results["rental_index"] = fetch_rental_index()
    results["price_index"] = fetch_price_index()
    results["median_tax"] = fetch_median_property_tax()
    results["private_whole"] = fetch_private_transactions_whole()

    # Load resale flat prices from CSV
    resale_df = load_resale_flat_prices()
    if not resale_df.empty:
        save_parquet(resale_df, "raw_datagov_resale_flat_all", source="data.gov.sg CSV (all files)")
        results["resale_flat_prices"] = resale_df
        logger.info(f"✅ Saved resale flat prices: {len(resale_df)} records")

    # Count successful collections
    successful = sum(1 for v in results.values() if v is not None and not v.empty)
    logger.info(
        f"✅ Data.gov.sg collection complete: {successful}/{len(results)} datasets collected"
    )

    return results
