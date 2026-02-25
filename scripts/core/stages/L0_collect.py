"""L0: Data collection from data.gov.sg API.

This module provides functions for collecting raw data from the data.gov.sg API,
including private property transactions, rental indices, price indices, and HDB data.
"""  # noqa: N999

import logging
import re
import time
from pathlib import Path

import pandas as pd
import requests

from scripts.core.cache import cached_call
from scripts.core.config import Config
from scripts.core.data_helpers import save_parquet
from scripts.core.data_loader import CSVLoader
from scripts.core.stages.helpers import collect_helpers

logger = logging.getLogger(__name__)
MIN_HDB_RENTAL_ROWS = 50_000
MIN_HDB_RENTAL_MONTHS = 12


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
        request_url = f"{url}{dataset_id}"
        if "datastore_search" in request_url and "limit=" not in request_url:
            request_url = f"{request_url}&limit=10000"
        retry_attempts = 0
        max_retry_attempts = 5

        while True:
            try:
                response = requests.get(request_url, timeout=60)
                response.raise_for_status()
                response_text = response.json()
                retry_attempts = 0

                # Extract records from response
                if "result" not in response_text or "records" not in response_text["result"]:
                    logger.warning(
                        "No records found in dataset %s (url=%s)", dataset_id, request_url
                    )
                    break

                records = response_text["result"]["records"]
                response_agg.append(pd.DataFrame(records))

                # Check pagination
                if "next" not in response_text["result"].get("_links", {}):
                    break

                # Get next URL
                next_url = response_text["result"]["_links"]["next"]
                if next_url.startswith("http"):
                    request_url = next_url
                else:
                    request_url = "https://data.gov.sg" + next_url

                # Update offset for pagination
                match = re.search(r"offset=(\d+)", request_url)
                if match:
                    offset_value = int(match.group(1))
                    total_records = response_text["result"]["total"]

                    if offset_value > total_records:
                        break

            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else None
                if status == 429 and retry_attempts < max_retry_attempts:
                    retry_after = 0
                    if e.response is not None:
                        retry_after = int(e.response.headers.get("Retry-After", "0") or 0)
                    retry_attempts += 1
                    sleep_seconds = retry_after or min(2**retry_attempts, 30)
                    logger.warning(
                        "Rate limited fetching dataset %s (attempt %s/%s, sleeping %ss, url=%s)",
                        dataset_id,
                        retry_attempts,
                        max_retry_attempts,
                        sleep_seconds,
                        request_url,
                    )
                    time.sleep(sleep_seconds)
                    continue
                logger.error("Error fetching dataset %s (url=%s): %s", dataset_id, request_url, e)
                if response_agg and total_records and offset_value < total_records:
                    raise RuntimeError(
                        f"Incomplete paginated fetch for {dataset_id}: retrieved {sum(len(df) for df in response_agg):,} "
                        f"of expected {total_records:,} rows before error at offset {offset_value}"
                    ) from e
                break
            except Exception as e:
                logger.error("Error fetching dataset %s (url=%s): %s", dataset_id, request_url, e)
                if response_agg and total_records and offset_value < total_records:
                    raise RuntimeError(
                        f"Incomplete paginated fetch for {dataset_id}: retrieved {sum(len(df) for df in response_agg):,} "
                        f"of expected {total_records:,} rows before error at offset {offset_value}"
                    ) from e
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


def fetch_hdb_rental_data(use_cache: bool = True) -> pd.DataFrame | None:
    """Fetch HDB renting-out-of-flats records (historical monthly rental approvals)."""

    def _hdb_rental_coverage_signature(df: pd.DataFrame) -> tuple[int, int, str | None, str | None]:
        if df.empty or "rent_approval_date" not in df.columns:
            return len(df), 0, None, None
        months = pd.to_datetime(df["rent_approval_date"], errors="coerce").dropna().dt.to_period("M")
        if months.empty:
            return len(df), 0, None, None
        return len(df), int(months.nunique()), str(months.min()), str(months.max())

    def _fetch():
        from scripts.data.download.download_hdb_rental_data import (
            download_hdb_rental_data as fetch_hdb_rental_data_full,
        )
        try:
            logger.info("L0 HDB rental: trying dataset download API as primary source")
            full_df = fetch_hdb_rental_data_full()
            full_rows, full_months, full_min, full_max = _hdb_rental_coverage_signature(full_df)
            logger.info(
                "L0 HDB rental download API returned %s rows, %s month(s) (%s to %s)",
                full_rows,
                full_months,
                full_min,
                full_max,
            )
            if full_rows >= MIN_HDB_RENTAL_ROWS and full_months >= MIN_HDB_RENTAL_MONTHS:
                return full_df
            logger.warning(
                "L0 HDB rental download API payload looks truncated; checking datastore_search for broader coverage"
            )
        except Exception as e:
            logger.warning("L0 HDB rental download API failed: %s", e)

        df = fetch_datagovsg_dataset(
            url="https://data.gov.sg/api/action/datastore_search?resource_id=",
            dataset_id="d_c9f57187485a850908655db0e8cfe651",
        )
        row_count, month_count, month_min, month_max = _hdb_rental_coverage_signature(df)
        logger.info(
            "L0 HDB rental datastore_search returned %s rows, %s month(s) (%s to %s)",
            row_count,
            month_count,
            month_min,
            month_max,
        )
        if row_count > 0:
            return df
        return pd.DataFrame()

    return collect_helpers.fetch_and_save_datagovsg_dataset(
        "raw_datagov_hdb_rental", "d_c9f57187485a850908655db0e8cfe651", _fetch, use_cache
    )


def fetch_ura_rental_statistics(use_cache: bool = True) -> pd.DataFrame | None:
    """
    Fetch URA private residential rental statistics by project from e-service.

    This scrapes quarterly rental statistics for non-landed private residential
    properties from URA's e-service, including median rent psf and number of contracts.

    Args:
        use_cache: Whether to use caching (default: True)

    Returns:
        DataFrame with rental statistics or None if failed
    """
    # TODO: Re-enable when scraper is fixed
    logger.warning("URA rental statistics scraper is temporarily disabled")
    return None


def fetch_ura_rental_contracts(use_cache: bool = True) -> pd.DataFrame | None:
    """
    Fetch URA private residential rental contracts from e-service.

    This scrapes individual rental contract details for private residential
    properties from URA's e-service.

    Args:
        use_cache: Whether to use caching (default: True)

    Returns:
        DataFrame with rental contracts or None if failed
    """

    # TODO: Re-enable when scraper is fixed
    logger.warning("URA rental contracts scraper is temporarily disabled")
    return None


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
    results["hdb_rental"] = fetch_hdb_rental_data()

    # Fetch GeoJSON boundary files
    results["planning_area_boundary"] = fetch_planning_area_boundary()

    # Load resale flat prices from CSV
    resale_df = load_resale_flat_prices()
    if not resale_df.empty:
        save_parquet(resale_df, "raw_datagov_resale_flat_all", source="data.gov.sg CSV (all files)")
        results["resale_flat_prices"] = resale_df
        logger.info(f"✅ Saved resale flat prices: {len(resale_df)} records")

    # Count successful collections across mixed result types (DataFrames + metadata dicts)
    successful = 0
    for value in results.values():
        if value is None:
            continue
        if hasattr(value, "empty"):
            if not value.empty:
                successful += 1
            continue
        if isinstance(value, dict):
            if value:
                successful += 1
            continue
        successful += 1
    logger.info(
        f"✅ Data.gov.sg collection complete: {successful}/{len(results)} datasets collected"
    )

    return results
