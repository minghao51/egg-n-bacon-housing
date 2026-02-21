"""L0: Data collection from data.gov.sg API.

This module provides functions for collecting raw data from the data.gov.sg API,
including private property transactions, rental indices, price indices, and HDB data.
"""  # noqa: N999

import logging
import re
from pathlib import Path

import pandas as pd
import requests

from scripts.core.cache import cached_call
from scripts.core.config import Config
from scripts.core.data_helpers import save_parquet
from scripts.core.data_loader import CSVLoader
from scripts.core.stages.helpers import collect_helpers

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


def load_resale_flat_prices(csv_base_path: Path | None = None) -> pd.DataFrame:
    """
    Load HDB resale flat prices from CSV files.

    Args:
        csv_base_path: Base path to CSV files (defaults to Config.CSV_DIR)

    Returns:
        DataFrame with all resale flat prices

    Example:
        >>> df = load_resale_flat_prices()
        >>> print(f"Loaded {len(df)} resale records")
    """
    # Use CSVLoader for loading HDB resale data
    csv_loader = CSVLoader(base_path=csv_base_path)

    resale_flat_all = csv_loader.load_hdb_resale(base_path=csv_base_path)

    if resale_flat_all.empty:
        logger.warning("No HDB resale data found")
        return pd.DataFrame()

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


def _convert_lease_to_months(lease_str) -> int | None:
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


def load_existing_or_fetch(
    dataset_name: str, fetch_fn, use_cache: bool = True
) -> pd.DataFrame | None:
    """Load existing parquet file or fetch from API.

    Args:
        dataset_name: Name of the parquet file (without extension)
        fetch_fn: Function to fetch data from API
        use_cache: Whether to use API caching

    Returns:
        DataFrame with data, or None if not available
    """
    # Check for existing local data
    parquet_path = Config.DATA_DIR / "pipeline" / f"{dataset_name}.parquet"
    if parquet_path.exists():
        logger.info(f"📂 Found existing {dataset_name}.parquet, loading local copy")
        df = pd.read_parquet(parquet_path)
        logger.info(f"   Loaded {len(df)} records from local cache")
        return df

    # No local data, fetch from API
    logger.info(f"🌐 No local data found for {dataset_name}, fetching from API...")
    return fetch_fn(use_cache)


def fetch_private_property_transactions(use_cache: bool = True) -> pd.DataFrame | None:
    """Fetch private residential property transactions in rest of central region."""

    def _fetch():
        return fetch_datagovsg_dataset(
            url="https://data.gov.sg/api/action/datastore_search?resource_id=",
            dataset_id="d_5785799d63a9da091f4e0b456291eeb8",
        )

    return collect_helpers.fetch_and_save_datagovsg_dataset(
        "raw_datagov_general_sale", "d_5785799d63a9da091f4e0b456291eeb8", _fetch, use_cache
    )


def fetch_rental_index(use_cache: bool = True) -> pd.DataFrame | None:
    """Fetch private residential property rental index."""

    def _fetch():
        return fetch_datagovsg_dataset(
            url="https://data.gov.sg/api/action/datastore_search?resource_id=",
            dataset_id="d_8e4c50283fb7052a391dfb746a05c853",
        )

    return collect_helpers.fetch_and_save_datagovsg_dataset(
        "raw_datagov_rental_index", "d_8e4c50283fb7052a391dfb746a05c853", _fetch, use_cache
    )


def fetch_price_index(use_cache: bool = True) -> pd.DataFrame | None:
    """Fetch private residential property price index."""

    def _fetch():
        return fetch_datagovsg_dataset(
            url="https://data.gov.sg/api/action/datastore_search?resource_id=",
            dataset_id="d_97f8a2e995022d311c6c68cfda6dae1af",
        )

    return collect_helpers.fetch_and_save_datagovsg_dataset(
        "raw_datagov_price_index", "d_97f8a2e995022d311c6c68cfda6dae1af", _fetch, use_cache
    )


def fetch_median_property_tax(use_cache: bool = True) -> pd.DataFrame | None:
    """Fetch median annual value and property tax by property type."""

    def _fetch():
        return fetch_datagovsg_dataset(
            url="https://data.gov.sg/api/action/datastore_search?resource_id=",
            dataset_id="d_774a81df45dca33112e59207e6dae1af",
        )

    return collect_helpers.fetch_and_save_datagovsg_dataset(
        "raw_datagov_median_price_via_property_type",
        "d_774a81df45dca33112e59207e6dae1af",
        _fetch,
        use_cache,
    )


def fetch_private_transactions_whole(use_cache: bool = True) -> pd.DataFrame | None:
    """Fetch private residential property transactions in whole of Singapore."""

    def _fetch():
        return fetch_datagovsg_dataset(
            url="https://data.gov.sg/api/action/datastore_search?resource_id=",
            dataset_id="d_7c69c943d5f0d89d6a9a773d2b51f337",
        )

    return collect_helpers.fetch_and_save_datagovsg_dataset(
        "raw_datagov_private_transactions_property_type",
        "d_7c69c943d5f0d89d6a9a773d2b51f337",
        _fetch,
        use_cache,
    )


def fetch_school_directory(use_cache: bool = True) -> pd.DataFrame | None:
    """Fetch MOE school directory with locations and information."""

    def _fetch():
        return fetch_datagovsg_dataset(
            url="https://data.gov.sg/api/action/datastore_search?resource_id=",
            dataset_id="d_688b934f82c1059ed0a6993d2a829089",
        )

    return collect_helpers.fetch_and_save_datagovsg_dataset(
        "raw_datagov_school_directory", "d_688b934f82c1059ed0a6993d2a829089", _fetch, use_cache
    )


def fetch_planning_area_boundary(use_cache: bool = True) -> dict | None:
    """
    Fetch URA Master Plan 2019 Planning Area Boundary GeoJSON from data.gov.sg.

    This GeoJSON includes planning area names, abbreviations, and region information
    which can be used to standardize town/area names across all property types.

    Args:
        use_cache: Whether to use caching (default: True)

    Returns:
        Dictionary with path and feature count, or None if failed
    """
    import json

    def _fetch():
        dataset_id = "d_4765db0e87b9c86336792efe8a1f7a66"
        url = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"

        try:
            response = requests.get(url, timeout=60)
            json_data = response.json()

            if json_data.get("code") != 0:
                logger.error(
                    f"Failed to download planning area boundary: {json_data.get('errMsg')}"
                )
                return None

            download_url = json_data["data"]["url"]
            geojson_response = requests.get(download_url, timeout=60)

            output_path = Config.MANUAL_DIR / "geojsons" / "ura_planning_area_boundary.geojson"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                f.write(geojson_response.text)

            geojson = json.loads(geojson_response.text)
            feature_count = len(geojson.get("features", []))

            logger.info(f"✅ Saved planning area boundary to {output_path} ({feature_count} areas)")
            return {"path": str(output_path), "features": feature_count}

        except Exception as e:
            logger.error(f"Error fetching planning area boundary: {e}")
            return None

    if use_cache and Config.USE_CACHING:
        return cached_call("datagovsg:planning_area_boundary", _fetch, duration_hours=24 * 7)
    else:
        return _fetch()


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
    results["school_directory"] = fetch_school_directory()

    # Fetch GeoJSON boundary files
    results["planning_area_boundary"] = fetch_planning_area_boundary()

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
