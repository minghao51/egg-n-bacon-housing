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


_OFFSET_PATTERN = re.compile(r"[?&]offset=(\d+)")


def _parse_offset(request_url: str) -> int | None:
    """Page offset carried by a datastore_search URL, or ``None`` when absent."""
    match = _OFFSET_PATTERN.search(request_url)
    return int(match.group(1)) if match else None


def _validate_page_envelope(payload: object, dataset_id: str, request_url: str) -> dict:
    """Validate one ``datastore_search`` page envelope and return its ``result``.

    data.gov.sg reports a rejected request with HTTP 200 and a body like
    ``{"success": false, "error": {"code": ..., "message": ...}}``; a page
    can also arrive without a ``result`` object at all. Both are malformed
    responses for the dataset — never an empty dataset — so they raise at any
    offset instead of silently ending pagination with the rows accumulated so
    far (which would publish a partial dataset as complete).

    Args:
        payload: Decoded JSON body of the page response.
        dataset_id: Dataset/resource id, for the error message.
        request_url: URL of the page that produced ``payload``.

    Returns:
        The ``result`` mapping of a well-formed page.

    Raises:
        DatasetFetchError: The body is not a JSON object, reports
            ``success: false``, or has no ``result`` object.
    """
    if not isinstance(payload, dict):
        raise DatasetFetchError(
            f"Malformed data.gov.sg response for {dataset_id}: expected a JSON object, "
            f"got {type(payload).__name__} (url={request_url})"
        )
    success = payload.get("success")
    if success is not None and not success:
        raise DatasetFetchError(
            f"data.gov.sg returned success=false for {dataset_id} "
            f"({payload.get('error') or payload.get('message') or 'no error detail'}; "
            f"url={request_url})"
        )
    result = payload.get("result")
    if not isinstance(result, dict):
        raise DatasetFetchError(
            f"Malformed data.gov.sg response for {dataset_id}: missing 'result' object "
            f"(url={request_url})"
        )
    return result


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
        DataFrame with fetched data, or empty DataFrame if the source advertises
        an empty dataset (first page with no ``result.records`` and no rows
        claimed). Incomplete or malformed responses raise instead of returning
        rows, so a partial fetch can never be cached as complete bronze.

    Raises:
        IncompleteDatasetFetchError: A later page is malformed, pagination does
            not progress, or fewer rows were fetched than the source's
            advertised ``total``.
        DatasetFetchError: The first page is a malformed envelope
            (``success: false``, or no ``result`` object) or the request fails.

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
        response_agg: list[pd.DataFrame] = []
        offset_value = 0
        total_records: int | None = None
        fetched_rows = 0
        page_size = _DEFAULT_PAGE_SIZE
        # Accept either resource_url(dataset_id) or the legacy
        # "...?resource_id=" prefix; the id is joined exactly once.
        base_url = url if url.endswith(f"resource_id={dataset_id}") else f"{url}{dataset_id}"
        request_url = base_url
        if "datastore_search" in request_url and "limit=" not in request_url:
            request_url = f"{request_url}&limit={page_size}"
        retry_attempts = 0
        # Every page URL already served; a next link pointing back at one of
        # them is non-progressing pagination and must fail, not loop.
        seen_urls: set[str] = set()

        def _shrink_page_size() -> str:
            cur_offset = _parse_offset(request_url) or 0
            sep = "&" if "?" in base_url else "?"
            return f"{base_url}{sep}limit={page_size}&offset={cur_offset}"

        def _incomplete(reason: str, offending_url: str) -> IncompleteDatasetFetchError:
            """Completeness error naming dataset id, advertised/fetched counts and URL."""
            advertised = f"{total_records:,}" if total_records is not None else "unknown"
            return IncompleteDatasetFetchError(
                f"Incomplete paginated fetch for {dataset_id}: fetched {fetched_rows:,} of "
                f"advertised {advertised} rows ({reason}; url={offending_url})"
            )

        while True:
            try:
                response = _SESSION.get(request_url, timeout=60)
                response.raise_for_status()
                response_text = response.json()
                retry_attempts = 0

                result = _validate_page_envelope(response_text, dataset_id, request_url)

                page_total = result.get("total")
                if isinstance(page_total, int) and not isinstance(page_total, bool):
                    total_records = page_total
                elif isinstance(page_total, str) and page_total.isdigit():
                    total_records = int(page_total)

                records = result.get("records")
                if records is None:
                    # Two shapes share "no records": an empty dataset (first
                    # page advertising an empty/absent total) and a malformed
                    # page (any later page, or a first page that still claims
                    # rows). The second must never masquerade as the first.
                    if response_agg or (total_records or 0) > 0:
                        raise _incomplete("page response has no result.records", request_url)
                    logger.warning(
                        "Dataset %s advertises no records — empty dataset (url=%s)",
                        dataset_id,
                        request_url,
                    )
                    break
                if not isinstance(records, list):
                    raise DatasetFetchError(
                        f"Malformed data.gov.sg response for {dataset_id}: "
                        f"result.records is not a list (url={request_url})"
                    )

                seen_urls.add(request_url)
                response_agg.append(pd.DataFrame(records))
                fetched_rows += len(records)

                links = result.get("_links")
                next_url = links.get("next") if isinstance(links, dict) else None
                if not next_url or not isinstance(next_url, str):
                    break

                next_request = (
                    next_url if next_url.startswith("http") else "https://data.gov.sg" + next_url
                )

                # Non-progressing pagination fails loudly instead of looping or
                # silently truncating the dataset.
                if next_request in seen_urls:
                    raise _incomplete(
                        "pagination repeated an already-fetched page URL", next_request
                    )

                next_offset = _parse_offset(next_request)
                served_offset = _parse_offset(request_url)
                if next_offset is not None:
                    offset_value = next_offset
                    if served_offset is not None and next_offset <= served_offset:
                        raise _incomplete(
                            f"pagination offset did not advance ({served_offset} -> {next_offset})",
                            next_request,
                        )
                    if total_records is not None and next_offset > total_records:
                        break
                request_url = next_request

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
                        parsed_retry_after = parse_retry_after(
                            e.response.headers.get("Retry-After"), default=0.0
                        )
                        # ``parse_retry_after`` returns ``None`` only when no default is
                        # given; keep the type narrow for the comparison below.
                        retry_after = 0.0 if parsed_retry_after is None else parsed_retry_after
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

        # Terminal reconciliation: the only place a "successful" pagination is
        # checked against the source's advertised total. Without this, a page
        # that ends pagination early (missing next link, truncated page) return
        # rows silently and gets cached as a complete bronze dataset.
        if total_records is not None and fetched_rows < total_records:
            raise _incomplete(
                "pagination ended before the advertised total was fetched", request_url
            )

        return pd.concat(response_agg, ignore_index=True)

    if use_cache:
        if cache_manager is None:
            raise ValueError("cache_manager is required when data.gov.sg caching is enabled")
        return cached_call(f"datagovsg:{dataset_id}", _fetch_from_api, cache_manager=cache_manager)
    return _fetch_from_api()
