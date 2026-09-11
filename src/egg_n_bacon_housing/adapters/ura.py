"""URA Data Service API adapter for private residential transactions.

Endpoints (https://eservice.ura.gov.sg/uraDataService):
- ``insertNewToken/v1`` — daily bearer token, requires the ``AccessKey``
  header (free registration at eservice.ura.gov.sg/maps/api/reg.html).
- ``invokeUraDS/v1?service=PMI_Resi_Transaction&batch=1..4`` — row-level
  private residential transactions over a rolling 5-year window, split by
  postal district into four batches.

Gateway notes (live-verified 2026-09-02):
- The Layer7 bot wall serves an HTML JS challenge to bare clients; sending
  browser-like ``User-Agent``/``Accept``/``Referer`` headers on a
  ``requests.Session`` (which persists the ``__nxquid`` cookie) returns JSON.
- Token responses are ``{"Status": "Success", "Result": "<token>"}`` — the
  token lives under ``Result``, not ``Token``.
- Transaction payloads are nested: one entry per property
  (``project``/``street``/``x``/``y``/``marketSegment``) with a list of
  ``transaction`` records (``contractDate`` is MMYY, ``typeOfSale`` is
  1/2/3, ``area`` is sqft for Strata and sqm for Land).
"""

import contextlib
import hashlib
import logging

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from egg_n_bacon_housing.adapters.exceptions import CredentialError, DatasetFetchError, URAAuthError
from egg_n_bacon_housing.utils.cache import (
    CacheManager,
    cached_call,
)

logger = logging.getLogger(__name__)

_URA_BASE_URL = "https://eservice.ura.gov.sg/uraDataService"

# The Layer7 gateway HTML-challenges non-browser clients; these headers are
# required for JSON responses (see module docstring).
_BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://eservice.ura.gov.sg/",
}

# URA tokens are valid for the rest of the registration day; cache for a
# fraction of that so a long-lived process re-fetches before expiry.
_TOKEN_CACHE_HOURS = 8


def _token_cache_id(access_key: str) -> str:
    """Per-access-key token cache id, so key rotation never serves a wrong-key token."""
    key_digest = hashlib.sha256(access_key.encode()).hexdigest()[:12]
    return f"ura_api_token:{key_digest}"


_TRANSACTION_BATCHES = (1, 2, 3, 4)


def _get_session() -> requests.Session:
    """Session with the browser-like headers the URA gateway requires."""
    session = requests.Session()
    session.headers.update(_BROWSER_HEADERS)
    return session


@retry(
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(4),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
    before_sleep=lambda rs: logger.warning(
        "Retrying URA request (%d/4) after error: %s",
        rs.attempt_number,
        rs.outcome.exception() if rs.outcome else "unknown error",
    ),
)
def _ura_request(
    session: requests.Session,
    url: str,
    headers: dict[str, str],
    params: dict[str, str] | None = None,
    timeout: int = 30,
) -> dict:
    """GET a URA endpoint and return parsed JSON, retrying transient failures."""
    response = session.get(url, headers=headers, params=params, timeout=timeout)
    response.raise_for_status()
    try:
        return response.json()
    except ValueError as exc:
        raise DatasetFetchError(f"URA returned non-JSON response from {url}: {exc}") from exc


def _fetch_fresh_token(access_key: str, session: requests.Session) -> str:
    """Call insertNewToken/v1 and return the raw token string."""
    if not access_key:
        raise CredentialError("URA API access key is not configured (URA_API_ACCESS_KEY)")
    payload = _ura_request(
        session,
        f"{_URA_BASE_URL}/insertNewToken/v1",
        headers={"AccessKey": access_key},
    )
    if payload.get("Status") != "Success" or not payload.get("Result"):
        message = payload.get("Message") or "unknown error"
        raise URAAuthError(f"URA token request failed: {message}")
    token = str(payload["Result"])
    logger.info("Acquired URA API token (%d chars)", len(token))
    return token


def _persist_refreshed_token(
    access_key: str, token: str, cache_manager: CacheManager | None
) -> None:
    """Write a force-refreshed token back to the cache.

    ``fetch_ura_token(use_cache=False)`` bypasses ``cached_call`` entirely, so
    without this write-back a rejected cached token would shadow the fresh one
    for the rest of its TTL and every run within the TTL would repeat the
    reject+refresh cycle. TTL is read-time in this cache design (see
    ``CacheManager.get``), so re-setting the entry starts a fresh validity
    window; no explicit duration is needed here.
    """
    if cache_manager is None:
        logger.debug("No cache manager injected — refreshed URA token not persisted")
        return
    manager = cache_manager
    manager.set(_token_cache_id(access_key), token)


def fetch_ura_token(
    access_key: str,
    use_cache: bool = True,
    *,
    cache_manager: CacheManager | None = None,
) -> str:
    """Return a URA bearer token, cached for part of its daily validity."""
    if not use_cache:
        return _fetch_fresh_token(access_key, _get_session())
    if cache_manager is None:
        raise ValueError("cache_manager is required when use_cache=True")
    return cached_call(
        _token_cache_id(access_key),
        lambda: _fetch_fresh_token(access_key, _get_session()),
        duration_hours=_TOKEN_CACHE_HOURS,
        cache_manager=cache_manager,
    )


def fetch_resi_transactions(
    access_key: str,
    token: str,
    batch: int,
    session: requests.Session | None = None,
) -> list[dict]:
    """Fetch one PMI_Resi_Transaction batch (1-4) as raw URA property rows."""
    payload = _ura_request(
        session or _get_session(),
        f"{_URA_BASE_URL}/invokeUraDS/v1",
        headers={"AccessKey": access_key, "Token": token},
        params={"service": "PMI_Resi_Transaction", "batch": str(batch)},
        timeout=60,
    )
    if payload.get("Status") != "Success":
        message = payload.get("Message") or "unknown error"
        lowered = message.lower()
        if "invalid token" in lowered or "invalid access key" in lowered:
            raise URAAuthError(f"URA rejected token for batch {batch}: {message}")
        raise DatasetFetchError(f"URA transaction fetch failed for batch {batch}: {message}")
    result = payload.get("Result") or []
    logger.info("URA batch %d: %d property rows", batch, len(result))
    return list(result)


def fetch_all_resi_transactions(
    access_key: str,
    use_cache: bool = True,
    *,
    cache_manager: CacheManager | None = None,
) -> list[dict]:
    """Fetch all PMI_Resi_Transaction batches, refreshing the token once on auth failure.

    Returns the concatenated raw per-property rows across batches 1-4.
    """
    if not access_key:
        raise CredentialError("URA API access key is not configured (URA_API_ACCESS_KEY)")

    rows: list[dict] = []
    with contextlib.closing(_get_session()) as session:
        token = fetch_ura_token(access_key, use_cache=use_cache, cache_manager=cache_manager)
        token_refreshed = False

        for batch in _TRANSACTION_BATCHES:
            try:
                rows.extend(fetch_resi_transactions(access_key, token, batch, session=session))
            except URAAuthError:
                if token_refreshed:
                    raise
                logger.warning("URA token rejected — refreshing once and retrying batch %d", batch)
                token = fetch_ura_token(access_key, use_cache=False, cache_manager=cache_manager)
                if use_cache:
                    _persist_refreshed_token(access_key, token, cache_manager)
                token_refreshed = True
                rows.extend(fetch_resi_transactions(access_key, token, batch, session=session))
    return rows
