"""OneMap API adapter for geocoding and authentication.

This module provides:
- OneMap API token management and authentication
- Geocoding helpers specific to OneMap API
- Retry logic with exponential backoff

OneMap is Singapore's official geospatial data service.
"""

import base64
import json
import logging
import threading
import time
from urllib.parse import quote

import pandas as pd
import requests
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from egg_n_bacon_housing.adapters._http import parse_retry_after as _parse_retry_after
from egg_n_bacon_housing.adapters.exceptions import (
    CredentialError,
    DatasetFetchError,
    OneMapAuthError,
)
from egg_n_bacon_housing.config import Settings
from egg_n_bacon_housing.utils.cache import CacheManager, cached_call

logger = logging.getLogger(__name__)

# Per-thread sessions: the geocoder drives fetch_data from a ThreadPoolExecutor,
# and a shared requests.Session is not thread-safe. Sessions are lazily created
# per thread and live for the thread's lifetime to reuse TLS connections.
_thread_local = threading.local()


def _get_session() -> requests.Session:
    """Return this thread's requests.Session, creating it on first use."""
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        _thread_local.session = session
    return session


def _retry_exception_message(retry_state) -> str:
    """Get the latest retry exception message safely for logging."""
    outcome = retry_state.outcome
    if outcome is None:
        return "unknown error"
    exc = outcome.exception()
    return str(exc) if exc is not None else "unknown error"


def setup_onemap_headers(settings: Settings) -> dict[str, str]:
    """Setup OneMap API authentication headers.

    Args:
        settings: Settings instance with OneMap credentials.

    Returns:
        Dict with Authorization header containing valid JWT token

    Raises:
        OneMapAuthError: If token cannot be obtained or is invalid
    """
    configured_token = settings.onemap_token
    access_token = configured_token.get_secret_value().strip() if configured_token else None

    if access_token:
        try:
            parts = access_token.split(".")
            if len(parts) == 3:
                payload = parts[1]
                payload += "=" * (-len(payload) % 4)
                decoded = base64.b64decode(payload)
                token_data = json.loads(decoded)

                current_time = time.time()
                if token_data.get("exp", 0) > current_time:
                    logger.info("Using existing OneMap token from .env")
                    logger.info(
                        "Token expires in %.1f hours",
                        (token_data.get("exp") - current_time) / 3600,
                    )
                    return {"Authorization": f"{access_token}"}
                logger.warning("Token in .env has expired")
                access_token = None
            else:
                logger.warning("Invalid token format")
                access_token = None
        except (ValueError, TypeError) as e:
            logger.warning("Error decoding token: %s", e)
            access_token = None

    if not access_token:
        return _request_new_token(settings)


def _get_required_secret(settings: Settings, secret_name: str) -> str:
    """Retrieve a secret from settings. Internal-use only — callers must not persist the value."""
    value = getattr(settings, secret_name).get_secret_value().strip()
    if not value:
        raise CredentialError(f"Missing required credential: {secret_name.upper()}")
    return value


@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_not_exception_type(CredentialError),
    before_sleep=lambda retry_state: logger.warning(
        "Retrying OneMap auth (%d/3) after error: %s",
        retry_state.attempt_number,
        _retry_exception_message(retry_state),
    ),
)
def _request_new_token(settings: Settings) -> dict[str, str]:
    """Request a new OneMap API token with retry logic."""
    logger.info("Requesting new OneMap token")
    url = "https://www.onemap.gov.sg/api/auth/post/getToken"
    payload = {
        "email": _get_required_secret(settings, "onemap_email"),
        "password": _get_required_secret(settings, "onemap_password"),
    }

    response = _get_session().post(url, json=payload, timeout=30)
    logger.debug("Token API status: %s", response.status_code)

    if response.status_code == 200:
        response_data = json.loads(response.text)
        access_token = response_data.get("access_token")
        if access_token:
            logger.info("Obtained new OneMap token")
            return {"Authorization": access_token}
        logger.error("No access_token in response")
        raise OneMapAuthError("access_token not found in API response")
    else:
        logger.error("onemap_auth_failed status=%s url=%s", response.status_code, url)
        raise OneMapAuthError(f"Token request failed with status {response.status_code}")


INITIAL_BACKOFF = 1
MAX_BACKOFF = 32
MAX_RETRY_AFTER_WAIT = 60.0

# _parse_retry_after is imported from adapters/_http.py (shared with datagovsg).


def _is_retryable_exception(exc: BaseException) -> bool:
    """True only for transient failures: 429/5xx statuses, network errors, and
    malformed-but-200 payloads.

    Auth and credential errors are permanent for a given call and are handled
    by the caller (token refresh) instead of blind retries.
    """
    if isinstance(exc, (CredentialError, OneMapAuthError)):
        return False
    if isinstance(exc, DatasetFetchError):
        return True
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else 0
        return status == 429 or status >= 500
    return isinstance(exc, requests.RequestException)


def _wait_after_error(retry_state) -> float:
    """Honor ``Retry-After`` on 429 responses; otherwise exponential backoff."""
    outcome = retry_state.outcome
    exc = outcome.exception() if outcome is not None else None
    if (
        isinstance(exc, requests.HTTPError)
        and exc.response is not None
        and exc.response.status_code == 429
    ):
        retry_after = _parse_retry_after(exc.response.headers.get("Retry-After"))
        if retry_after is not None:
            return min(retry_after, MAX_RETRY_AFTER_WAIT)
    return wait_exponential(multiplier=1, min=INITIAL_BACKOFF, max=MAX_BACKOFF)(retry_state)


@retry(
    wait=_wait_after_error,
    stop=stop_after_attempt(3),
    retry=retry_if_exception(_is_retryable_exception),
    reraise=True,
    before_sleep=lambda retry_state: logger.warning(
        "Retrying OneMap API (%d/3) after error: %s",
        retry_state.attempt_number,
        _retry_exception_message(retry_state),
    ),
)
def fetch_data(search_string: str, headers: dict[str, str], timeout: int = 30) -> pd.DataFrame:
    """Fetch geocoding data from OneMap API for a given address.

    Args:
        search_string: Address to search for
        headers: Authentication headers from setup_onemap_headers()
        timeout: Request timeout in seconds (default: 30)

    Returns:
        DataFrame with search results including coordinates

    Raises:
        requests.RequestException: If API call fails after retries
        requests.Timeout: If request times out
        DatasetFetchError: If the 200 payload lacks the ``results`` key
            (malformed response) after retries
    """
    encoded_search = quote(search_string, safe="")
    url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={encoded_search}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
    response = _get_session().get(url, headers=headers, timeout=timeout)
    if response.status_code in (401, 403):
        logger.error("onemap_auth_rejected status=%s url=%s", response.status_code, url)
        raise OneMapAuthError(
            f"OneMap rejected credentials (HTTP {response.status_code}); token refresh required"
        )
    response.raise_for_status()
    payload = json.loads(response.text)
    results = payload.get("results")
    if results is None:
        # A missing 'results' key is an error shape (gateway error page, API
        # contract change), not "0 matches" (which is found:0, results:[]).
        # Raise so the retry path runs and the malformed payload is never
        # cached as an authoritative empty success.
        keys = sorted(payload) if isinstance(payload, dict) else type(payload).__name__
        logger.error("OneMap response missing 'results' key (url=%s, payload keys=%s)", url, keys)
        raise DatasetFetchError(f"OneMap response missing 'results' key from {url}")
    return pd.DataFrame(results).reset_index().rename({"index": "search_result"}, axis=1)


def fetch_data_cached(
    search_string: str,
    headers: dict[str, str],
    timeout: int = 30,
    *,
    cache_manager: CacheManager,
    duration_hours: int | None = None,
) -> pd.DataFrame:
    """Fetch geocoding data from OneMap API with caching support.

    Args:
        search_string: Address to search for
        headers: Authentication headers from setup_onemap_headers()
        timeout: Request timeout in seconds (default: 30)
        cache_manager: Explicit cache manager
        duration_hours: Cache TTL for this entry (defaults to the manager's
            configured duration). The geocoder passes its
            ``geocoding.cache_duration_hours`` so reads and writes share one
            knob instead of the effective TTL silently becoming the max of two.

    Returns:
        DataFrame with search results including coordinates

    Raises:
        requests.RequestException: If API call fails after retries
        requests.Timeout: If request times out
        DatasetFetchError: If the response payload is malformed (e.g. missing
            the ``results`` key) after retries — never cached
    """
    cache_id = f"onemap_search:{search_string}"

    def _fetch_from_api():
        return fetch_data(search_string, headers, timeout)

    return cached_call(
        cache_id, _fetch_from_api, duration_hours=duration_hours, cache_manager=cache_manager
    )
