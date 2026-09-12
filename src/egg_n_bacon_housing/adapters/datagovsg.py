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
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from egg_n_bacon_housing.adapters._http import (
    MAX_RETRY_AFTER_WAIT,
    is_retryable_exception,
    is_transient_status,
    parse_retry_after,
    retry_after_wait,
)
from egg_n_bacon_housing.adapters.exceptions import (
    DatasetFetchError,
    IncompleteDatasetFetchError,
)
from egg_n_bacon_housing.utils.cache import CacheManager, cached_call

logger = logging.getLogger(__name__)

DATAGOVSG_BASE_URL = "https://data.gov.sg/api/action/datastore_search"
_DATAGOVSG_API_OPEN_BASE = "https://api-open.data.gov.sg/v1/public/api/datasets"

_DEFAULT_PAGE_SIZE = 2000
_MIN_PAGE_SIZE = 250


def resource_url(resource_id: str) -> str:
    """Canonical datastore_search request URL for one dataset/resource id.

    Single-sources the ``?resource_id=`` construction shared by the datagov
    fetch nodes; the result is accepted directly by
    :func:`fetch_datagovsg_dataset`.
    """
    return f"{DATAGOVSG_BASE_URL}?resource_id={resource_id}"


# Module-level session shared by all request paths: datagovsg nodes are
# single-threaded, so one session reuses TLS connections across paginated calls.
_SESSION = requests.Session()


@retry(
    wait=retry_after_wait(wait_exponential(multiplier=2, min=2, max=30)),
    stop=stop_after_attempt(4),
    retry=retry_if_exception(is_retryable_exception),
    reraise=True,
    before_sleep=lambda retry_state: logger.warning(
        "Retrying data.gov.sg initiate-download (%d/4) after error: %s",
        retry_state.attempt_number,
        retry_state.outcome.exception() if retry_state.outcome else "unknown error",
    ),
)
def _initiate_download(dataset_id: str) -> None:
    """Kick off a dataset download job, retrying transient failures only
    (429/5xx/network via the shared `_http` policy; `Retry-After` on 429s is
    honored and capped at `MAX_RETRY_AFTER_WAIT`; permanent 4xx fail fast)."""
    response = _SESSION.get(
        f"{_DATAGOVSG_API_OPEN_BASE}/{dataset_id}/initiate-download",
        params={"geometry": "true"},
        timeout=30,
    )
    response.raise_for_status()


def fetch_datagovsg_geojson(
    dataset_id: str,
    use_cache: bool = True,
    poll_attempts: int = 10,
    poll_interval_seconds: float = 1.0,
    *,
    cache_manager: CacheManager | None = None,
) -> dict:
    """Download a GEOJSON-format dataset from data.gov.sg.

    GEOJSON datasets are not served by the datastore_search API; they use the
    three-step download flow: initiate-download -> poll-download (returns a
    presigned S3 URL) -> GET the presigned URL.

    Args:
        dataset_id: Dataset ID (e.g. "d_65a0bf22c15ef49e9a21b8bcf8c04c87").
        use_cache: Whether to cache the parsed GeoJSON via ``cached_call``.
        poll_attempts: How many times to poll for the presigned URL.
        poll_interval_seconds: Seconds between polls.

    Returns:
        Parsed GeoJSON dict (``{"type": "FeatureCollection", "features": [...]}``).

    Raises:
        DatasetFetchError: On initiate/poll/download failure or malformed payload.
    """

    def _fetch() -> dict:
        try:
            _initiate_download(dataset_id)
        except RequestException as exc:
            raise DatasetFetchError(f"Failed to initiate download for {dataset_id}: {exc}") from exc

        url: str | None = None
        for attempt in range(1, poll_attempts + 1):
            try:
                poll = _SESSION.get(
                    f"{_DATAGOVSG_API_OPEN_BASE}/{dataset_id}/poll-download",
                    timeout=30,
                )
                poll.raise_for_status()
                payload = poll.json()
            except (RequestException, ValueError) as exc:
                raise DatasetFetchError(f"Poll download failed for {dataset_id}: {exc}") from exc
            url = (payload.get("data") or {}).get("url")
            if url:
                break
            logger.debug("Poll %s/%s for %s: no URL yet", attempt, poll_attempts, dataset_id)
            time.sleep(poll_interval_seconds)

        if not url:
            raise DatasetFetchError(
                f"Download for {dataset_id} never became ready after {poll_attempts} polls"
            )

        try:
            blob = _SESSION.get(url, timeout=120)
            blob.raise_for_status()
            return blob.json()
        except (RequestException, ValueError) as exc:
            raise DatasetFetchError(f"Failed to download GeoJSON for {dataset_id}: {exc}") from exc

    if use_cache:
        if cache_manager is None:
            raise ValueError("cache_manager is required when data.gov.sg caching is enabled")
        return cached_call(f"datagovsg_geojson:{dataset_id}", _fetch, cache_manager=cache_manager)
    return _fetch()


def fetch_datagovsg_dataset(
    url: str,
    dataset_id: str,
    use_cache: bool = True,
    *,
    cache_manager: CacheManager | None = None,
) -> pd.DataFrame:
    """Fetch data from data.gov.sg API with pagination support.

    Args:
        url: Request URL — the canonical :func:`resource_url` result or the
            legacy ``...?resource_id=`` prefix; the dataset id is joined
            exactly once either way
        dataset_id: Dataset ID to fetch
        use_cache: Whether to use caching (default: True)

    Returns:
        DataFrame with fetched data, or empty DataFrame if no data

    Example:
        >>> df = fetch_datagovsg_dataset(
        ...     resource_url("d_5785799d63a9da091f4e0b456291eeb8"),
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
        page_size = _DEFAULT_PAGE_SIZE
        # Accept either resource_url(dataset_id) or the legacy
        # "...?resource_id=" prefix; the id is joined exactly once.
        base_url = url if url.endswith(f"resource_id={dataset_id}") else f"{url}{dataset_id}"
        request_url = base_url
        if "datastore_search" in request_url and "limit=" not in request_url:
            request_url = f"{request_url}&limit={page_size}"
        retry_attempts = 0

        def _shrink_page_size() -> str:
            cur_offset = 0
            match = re.search(r"offset=(\d+)", request_url)
            if match:
                cur_offset = int(match.group(1))
            sep = "&" if "?" in base_url else "?"
            return f"{base_url}{sep}limit={page_size}&offset={cur_offset}"

        while True:
            try:
                response = _SESSION.get(request_url, timeout=60)
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
                if status == 413 and page_size > _MIN_PAGE_SIZE:
                    prev = page_size
                    page_size = max(page_size // 2, _MIN_PAGE_SIZE)
                    request_url = _shrink_page_size()
                    logger.warning(
                        "data.gov.sg 413 for dataset %s at limit=%d; retrying at limit=%d (url=%s)",
                        dataset_id,
                        prev,
                        page_size,
                        request_url,
                    )
                    continue
                if status == 429 and retry_attempts < max_retry_attempts:
                    retry_after = 0.0
                    if e.response is not None:
                        # Retry-After may be delta-seconds or an HTTP-date (RFC 7231);
                        # unparseable/missing headers fall back to exponential backoff.
                        retry_after = parse_retry_after(
                            e.response.headers.get("Retry-After"), default=0.0
                        )
                    retry_attempts += 1
                    # Cap at the shared MAX_RETRY_AFTER_WAIT so a hostile
                    # gateway cannot stall the run.
                    retry_after = min(retry_after, MAX_RETRY_AFTER_WAIT)
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
                    and is_transient_status(status)
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
            logger.warning("No data fetched for dataset %s", dataset_id)
            return pd.DataFrame()

        return pd.concat(response_agg, ignore_index=True)

    if use_cache:
        if cache_manager is None:
            raise ValueError("cache_manager is required when data.gov.sg caching is enabled")
        return cached_call(f"datagovsg:{dataset_id}", _fetch_from_api, cache_manager=cache_manager)
    return _fetch_from_api()
