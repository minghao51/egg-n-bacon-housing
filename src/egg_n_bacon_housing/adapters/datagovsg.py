"""data.gov.sg API adapter for fetching Singapore government datasets.

This module provides:
- Dataset fetching with pagination support
- Rate limiting and retry logic
- Cache integration for API responses

data.gov.sg is Singapore's official open data portal.
"""

import logging
import re
import time
from collections.abc import Callable

import pandas as pd
import requests

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.cache import cached_call

logger = logging.getLogger(__name__)

DATAGOVSG_BASE_URL = "https://data.gov.sg/api/action/datastore_search"
DATAGOVSG_POLL_DOWNLOAD_URL = "https://api-open.data.gov.sg/v1/public/api/datasets"


def fetch_datagovsg_dataset(url: str, dataset_id: str, use_cache: bool = True) -> pd.DataFrame:
    """Fetch data from data.gov.sg API with pagination support.

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

                if "result" not in response_text or "records" not in response_text["result"]:
                    logger.warning(
                        "No records found in dataset %s (url=%s)", dataset_id, request_url
                    )
                    break

                records = response_text["result"]["records"]
                response_agg.append(pd.DataFrame(records))

                if "next" not in response_text["result"].get("_links", {}):
                    break

                next_url = response_text["result"]["_links"]["next"]
                if next_url.startswith("http"):
                    request_url = next_url
                else:
                    request_url = "https://data.gov.sg" + next_url

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

    if use_cache and settings.pipeline.use_caching:
        cache_id = f"datagovsg:{dataset_id}"
        return cached_call(
            cache_id, _fetch_from_api, duration_hours=settings.pipeline.cache_duration_hours
        )
    else:
        return _fetch_from_api()


def fetch_dataset_with_download_api(dataset_id: str) -> dict | None:
    """Fetch dataset using the poll-download API.

    This is an alternative API for downloading complete dataset exports.

    Args:
        dataset_id: data.gov.sg dataset ID

    Returns:
        Dictionary with download result data, or None if failed
    """
    url = f"{DATAGOVSG_POLL_DOWNLOAD_URL}/{dataset_id}/poll-download"

    try:
        response = requests.get(url, timeout=60)
        json_data = response.json()

        if json_data.get("code") != 0:
            logger.error(f"Failed to poll download: {json_data.get('errMsg')}")
            return None

        return json_data.get("data")

    except Exception as e:
        logger.error(f"Error fetching dataset {dataset_id}: {e}")
        return None


def save_datagovsg_dataset(
    dataset_name: str,
    dataset_id: str,
    fetch_fn: Callable[[], pd.DataFrame],
    use_cache: bool = True,
) -> pd.DataFrame | None:
    """Fetch dataset from data.gov.sg with caching and save to parquet.

    Args:
        dataset_name: Name for the parquet file (without extension)
        dataset_id: data.gov.sg dataset ID
        fetch_fn: Function that fetches the data (no arguments)
        use_cache: Whether to use caching

    Returns:
        DataFrame with data, or None if unavailable
    """
    df = fetch_datagovsg_dataset(
        url=f"{DATAGOVSG_BASE_URL}?resource_id=",
        dataset_id=dataset_id,
        use_cache=use_cache,
    )

    if df is not None and not df.empty:
        logger.info(f"✅ Fetched {dataset_name}: {len(df)} records")
        return df

    return None
