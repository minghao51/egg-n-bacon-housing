"""data.gov.sg API adapter for fetching Singapore government datasets.

This module provides:
- Dataset fetching with pagination support
- Rate limiting and retry logic
- Cache integration for API responses

data.gov.sg is Singapore's official open data portal.
"""

import json
import logging
import re
import time

import pandas as pd
import requests
from requests import RequestException

from egg_n_bacon_housing.adapters.exceptions import (
    DatasetFetchError,
    IncompleteDatasetFetchError,
)
from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.cache import cached_call

logger = logging.getLogger(__name__)

DATAGOVSG_BASE_URL = "https://data.gov.sg/api/action/datastore_search"


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

    max_retry_attempts = 5

    def _sleep_for_retry(retry_attempts: int) -> None:
        sleep_seconds = min(2**retry_attempts, 30)
        logger.warning(
            "Retrying dataset %s after transient failure (attempt %s/%s, sleeping %ss)",
            dataset_id,
            retry_attempts,
            max_retry_attempts,
            sleep_seconds,
        )
        time.sleep(sleep_seconds)

    def _fetch_from_api():
        response_agg = []
        offset_value = 0
        total_records = 0
        request_url = f"{url}{dataset_id}"
        if "datastore_search" in request_url and "limit=" not in request_url:
            request_url = f"{request_url}&limit=10000"
        retry_attempts = 0

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
                if (
                    status is not None
                    and 500 <= status < 600
                    and retry_attempts < max_retry_attempts
                ):
                    retry_attempts += 1
                    _sleep_for_retry(retry_attempts)
                    continue
                logger.error("Error fetching dataset %s (url=%s): %s", dataset_id, request_url, e)
                if response_agg and total_records and offset_value < total_records:
                    raise IncompleteDatasetFetchError(
                        f"Incomplete paginated fetch for {dataset_id}: retrieved {sum(len(df) for df in response_agg):,} "
                        f"of expected {total_records:,} rows before error at offset {offset_value}"
                    ) from e
                raise DatasetFetchError(
                    f"Failed to fetch dataset {dataset_id} from {request_url} (status={status})"
                ) from e
            except RequestException as e:
                if retry_attempts < max_retry_attempts:
                    retry_attempts += 1
                    _sleep_for_retry(retry_attempts)
                    continue
                logger.error(
                    "Request error fetching dataset %s (url=%s): %s",
                    dataset_id,
                    request_url,
                    e,
                )
                if response_agg and total_records and offset_value < total_records:
                    raise IncompleteDatasetFetchError(
                        f"Incomplete paginated fetch for {dataset_id}: retrieved {sum(len(df) for df in response_agg):,} "
                        f"of expected {total_records:,} rows before error at offset {offset_value}"
                    ) from e
                raise DatasetFetchError(
                    f"Request error fetching dataset {dataset_id} from {request_url}"
                ) from e
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
                logger.error("Error fetching dataset %s (url=%s): %s", dataset_id, request_url, e)
                if response_agg and total_records and offset_value < total_records:
                    raise IncompleteDatasetFetchError(
                        f"Incomplete paginated fetch for {dataset_id}: retrieved {sum(len(df) for df in response_agg):,} "
                        f"of expected {total_records:,} rows before error at offset {offset_value}"
                    ) from e
                raise DatasetFetchError(
                    f"Unexpected error fetching dataset {dataset_id} from {request_url}"
                ) from e

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
