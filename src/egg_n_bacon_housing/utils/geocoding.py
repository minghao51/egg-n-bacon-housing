"""Geocoding module: unified interface for address-to-coordinate resolution.

One interface, two adapters:
- OneMapGeocoder: production geocoding via OneMap API
- InMemoryGeocoder: test geocoding from a fixed lookup table

Extracts geocoding logic that was duplicated across ingestion
(_geocode_shopping_malls), school_features (geocode_schools),
and the onemap adapter.
"""

import logging
import re
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from egg_n_bacon_housing.config import Settings
from egg_n_bacon_housing.utils.cache import CacheManager

logger = logging.getLogger(__name__)


def normalize_name_tokens(value: str) -> list[str]:
    """Lowercase a name and split it into alphanumeric tokens (punctuation dropped)."""
    return re.sub(r"[^0-9a-z]+", " ", str(value).casefold()).split()


# Filler words that never identify a project on their own. Tokens shorter
# than 4 characters ("THE", "AT", ...) are already insignificant by length;
# the longer entries are building-type and country filler that OneMap freely
# appends to or drops from name variants ("PARC ROSEWOOD CONDOMINIUM",
# "... SINGAPORE 088568"). "TOWER"/"TOWERS" is deliberately NOT filler:
# sibling projects are distinguished by exactly such words ("THE TRELLIS" vs
# "TRELLIS TOWERS"), so they stay significant and demand explanation.
_GENERIC_NAME_TOKENS = frozenset(
    {
        "the",
        "parc",
        "residence",
        "residences",
        "condominium",
        "condo",
        "apartment",
        "apartments",
        "court",
        "heights",
        "villa",
        "villas",
        "singapore",
    }
)

# Minimum length for a token to (a) be significant enough to identify a
# project and (b) match another token as a prefix (so "18" never "18"~"180").
_MIN_SIGNIFICANT_TOKEN_LEN = 4


def _significant_tokens(tokens: list[str]) -> list[str]:
    """Tokens that can identify a project: >= 4 chars, non-filler, non-numeric.

    Purely numeric tokens (block numbers, postal codes — "18 ... SINGAPORE
    088568") never reject a candidate, matching the filler semantics.
    """
    return [
        token
        for token in tokens
        if len(token) >= _MIN_SIGNIFICANT_TOKEN_LEN
        and token not in _GENERIC_NAME_TOKENS
        and not token.isdigit()
    ]


def _variant_token_match(token: str, candidate_token: str) -> bool:
    """Equal tokens, or one starts with the other and the shorter has >= 4 chars."""
    if token == candidate_token:
        return True
    shorter, longer = sorted((token, candidate_token), key=len)
    return len(shorter) >= _MIN_SIGNIFICANT_TOKEN_LEN and longer.startswith(shorter)


def _is_variant_subsequence(needles: list[str], haystack: list[str]) -> bool:
    """Whether every needle matches, in order, as a subsequence of ``haystack``."""
    remaining = iter(haystack)
    return all(
        any(_variant_token_match(needle, token) for token in remaining) for needle in needles
    )


def plausible_project_match(
    project_name: str,
    matched_name: str | None,
    matched_address: str | None = None,
    street_name: str | None = None,
) -> bool:
    """Decide whether a geocode result plausibly belongs to ``project_name``.

    Both sides are normalized (casefold + punctuation-to-space + whitespace
    split). A token is *significant* when it has at least 4 characters and is
    not in ``_GENERIC_NAME_TOKENS`` — filler such as "THE", "PARC",
    "CONDOMINIUM" or "SINGAPORE" is what OneMap freely adds to or drops from
    name variants (digits are likewise never significant). Token matching is
    *variant-tolerant*: two tokens match when equal, or when one starts with
    the other and the shorter side has >= 4 characters (TERRACE~TERRACES,
    ROSE~ROSEWOOD), so legitimate OneMap name variants no longer force a
    useless street-only fallback.

    Acceptance requires ALL of:

    1. **Name containment** — every significant project token matches, in
       order, a (not necessarily contiguous) subsequence of the matched
       name's OR matched address's tokens, e.g. "THE TERRACE" ⊂ "THE TERRACES
       AT PUNGGOL".
    2. **Street corroboration** (weak-name guard) — at least one
       ``street_name`` token appears in the matched address. Required for
       every acceptance: a lone significant token ("SPOTTISWOODE", or the
       ROSE in "PARC ROSE") would otherwise match any similarly named
       project anywhere. The pass-1 query embeds the street, so true matches
       normally satisfy this.
    3. **No unexplained significant tokens** (sibling guard) — every
       significant token of the matched name/address must itself be
       explained: variant-matched by a significant project token, contained
       in ``street_name``, or filler/numeric. Sibling projects sharing all
       project tokens and a street ("THE TRELLIS" vs "TRELLIS TOWERS")
       therefore cannot both pass.

    Projects with no significant token (all filler) cannot be verified at all
    and are rejected, as are blank names, blank streets, and results without
    a usable matched address. Blank project names are never plausible
    (callers geocode those without a project query). Rejection is always
    safe: callers fall back to street-only geocoding.
    """
    project_tokens = normalize_name_tokens(project_name)
    if not project_tokens:
        return False
    significant = _significant_tokens(project_tokens)
    if not significant:
        return False
    if street_name is None or pd.isna(street_name) or not str(street_name):
        return False
    street_tokens = normalize_name_tokens(street_name)

    name_token_lists: list[list[str]] = []
    address_tokens: list[str] = []
    for candidate, is_address in ((matched_name, False), (matched_address, True)):
        if candidate is None or pd.isna(candidate) or not str(candidate):
            continue
        tokens = normalize_name_tokens(candidate)
        name_token_lists.append(tokens)
        if is_address:
            address_tokens = tokens
    if not any(_is_variant_subsequence(significant, tokens) for tokens in name_token_lists):
        return False
    if not any(street_token in address_tokens for street_token in street_tokens):
        return False
    candidate_significant = [
        token for tokens in name_token_lists for token in _significant_tokens(tokens)
    ]
    return all(
        any(_variant_token_match(project_token, token) for project_token in significant)
        or token in street_tokens
        for token in candidate_significant
    )


class _RateLimiter:
    """Thread-safe minimum-interval pacer for outbound API calls.

    Hands out slots at least ``interval`` apart across all threads; the first
    caller goes through immediately, later callers sleep for the remainder of
    their slot. Never paces cache hits — callers must check the cache first.
    """

    def __init__(self, min_interval_seconds: float):
        self._interval = max(0.0, float(min_interval_seconds))
        self._lock = threading.Lock()
        self._next_slot = 0.0

    @property
    def interval(self) -> float:
        """Configured minimum spacing between outbound calls, in seconds."""
        return self._interval

    def wait(self) -> None:
        """Block until the caller's slot (no-op when pacing is disabled)."""
        if self._interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_slot - now)
            self._next_slot = now + self._interval
        if delay:
            time.sleep(delay)


class Geocoder(ABC):
    """Abstract geocoding interface."""

    @abstractmethod
    def geocode(self, addresses: pd.Series) -> pd.DataFrame:
        """Geocode a series of addresses/postal codes.

        Args:
            addresses: Series of address strings or postal codes.

        Returns:
            DataFrame with columns: input, lat, lon, matched_name,
            postal_code, address. One row per input value.
            Lat/lon are None for failed geocodes.
        """
        ...

    def geocode_dataframe(
        self,
        df: pd.DataFrame,
        address_column: str,
    ) -> pd.DataFrame:
        """Geocode a DataFrame by adding lat/lon columns.

        Args:
            df: Input DataFrame.
            address_column: Column containing addresses or postal codes.

        Returns:
            DataFrame with lat, lon columns added.
        """
        df = df.copy()
        results = self.geocode(df[address_column])
        df["lat"] = results["lat"].values
        df["lon"] = results["lon"].values
        return df


class OneMapGeocoder(Geocoder):
    """Production geocoder using OneMap API via the onemap adapter.

    Cache-first: addresses already in the OneMap cache resolve instantly
    without an API call. Misses are geocoded in parallel (``max_workers``)
    or sequentially with rate-limit pacing (``rate_limit_seconds``, applied
    only on actual API calls, never on cache hits).
    """

    def __init__(
        self,
        headers: dict[str, str],
        cache_manager: CacheManager,
        cache_duration_hours: int = 24,
        max_workers: int = 5,
        timeout: int = 30,
        rate_limit_seconds: float = 0.0,
        on_auth_expired: Callable[[], dict[str, str]] | None = None,
    ):
        self.headers = headers
        self.cache_duration_hours = cache_duration_hours
        self.max_workers = max_workers
        self.timeout = timeout
        self._limiter = _RateLimiter(rate_limit_seconds)
        self._on_auth_expired = on_auth_expired
        self._auth_lock = threading.Lock()
        self._cache_manager = cache_manager

    def query_geocode_cache(self, address: str) -> tuple[float, float] | None:
        """Read-only lookup of the OneMap cache for one address.

        Returns ``(lat, lon)`` if a cached result exists, else ``None``. Makes
        no API call. Keeps the OneMap cache-key format inside this module
        instead of leaking it to callers.
        """
        from egg_n_bacon_housing.utils.cache import _CACHE_MISS

        if self._cache_manager is None:
            raise RuntimeError("OneMapGeocoder requires an injected CacheManager")
        manager = self._cache_manager
        cached = manager.get(f"onemap_search:{address}", duration_hours=self.cache_duration_hours)
        if cached is _CACHE_MISS or not isinstance(cached, pd.DataFrame) or cached.empty:
            return None
        return self._coords_from_row(cached.iloc[0])

    @staticmethod
    def _coords_from_row(row: pd.Series) -> tuple[float, float] | None:
        lat = pd.to_numeric(row.get("LATITUDE") or row.get("Y"), errors="coerce")
        lon = pd.to_numeric(row.get("LONGITUDE") or row.get("X"), errors="coerce")
        if pd.isna(lat) or pd.isna(lon):
            return None
        return (float(lat), float(lon))

    def _row_from_result(self, addr: str, df: pd.DataFrame | None) -> dict:
        if df is not None and not df.empty:
            first = df.iloc[0]
            coords = self._coords_from_row(first)
            if coords is not None:
                return {
                    "input": addr,
                    "lat": coords[0],
                    "lon": coords[1],
                    "matched_name": first.get("SEARCHVAL"),
                    "postal_code": first.get("POSTAL"),
                    "address": first.get("ADDRESS"),
                }
        return self._empty_row(addr)

    @staticmethod
    def _empty_row(addr: str) -> dict:
        return {
            "input": addr,
            "lat": None,
            "lon": None,
            "matched_name": None,
            "postal_code": None,
            "address": str(addr),
        }

    def _refresh_headers(self, stale_headers: dict[str, str]) -> bool:
        """Obtain fresh OneMap headers mid-run. Thread-safe; False on failure.

        Single-flight: callers pass the headers object their failing request
        used. If another thread already swapped in a replacement, the network
        refresh is skipped and the caller retries with the new headers — a
        mid-run expiry across ``max_workers`` threads costs one refresh, not
        one per worker.
        """
        if self._on_auth_expired is None:
            return False
        try:
            with self._auth_lock:
                if self.headers is not stale_headers:
                    return True
                self.headers = self._on_auth_expired()
            return True
        except Exception as exc:
            logger.warning("OneMap token refresh failed: %s", exc)
            return False

    def _geocode_via_api(self, addr: str) -> dict:
        from egg_n_bacon_housing.adapters.onemap import OneMapAuthError, fetch_data_cached

        cached = self.query_geocode_cache(addr)
        if cached is not None:
            return {**self._empty_row(addr), "lat": cached[0], "lon": cached[1]}
        self._limiter.wait()
        for attempt in (1, 2):
            try:
                headers = self.headers
                df = fetch_data_cached(
                    addr,
                    headers=headers,
                    timeout=self.timeout,
                    cache_manager=self._cache_manager,
                    duration_hours=self.cache_duration_hours,
                )
                return self._row_from_result(addr, df)
            except OneMapAuthError as exc:
                if attempt == 2 or not self._refresh_headers(headers):
                    logger.warning("Geocoding failed after auth refresh for %s: %s", addr, exc)
                    break
                logger.info("OneMap token expired mid-run; refreshed headers, retrying once")
            except Exception as exc:
                logger.warning("Geocoding failed for %s: %s", addr, exc)
                break
        return self._empty_row(addr)

    def geocode(self, addresses: pd.Series) -> pd.DataFrame:
        addrs = [str(a) for a in addresses]
        columns = ["input", "lat", "lon", "matched_name", "postal_code", "address"]
        if not addrs:
            return pd.DataFrame(columns=columns)

        if self.max_workers > 1 and len(addrs) > 1:
            return self._geocode_parallel(addrs)
        return self._geocode_sequential(addrs)

    def _geocode_sequential(self, addrs: list[str]) -> pd.DataFrame:
        return pd.DataFrame([self._geocode_via_api(addr) for addr in addrs])

    def _geocode_parallel(self, addrs: list[str]) -> pd.DataFrame:
        rows: list[dict] = [self._empty_row(a) for a in addrs]
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(self._geocode_via_api, a): i for i, a in enumerate(addrs)}
            for future in as_completed(futures):
                rows[futures[future]] = future.result()
        return pd.DataFrame(rows)


def build_default_geocoder(settings: Settings, cache_manager: CacheManager) -> Geocoder:
    """Construct the production OneMap geocoder from settings.

    Reads ``settings`` once at the wiring point and returns a fully-wired
    ``Geocoder``. Call sites pass the result around so the OneMap cache-key
    format, rate limiting, and concurrency stay local to this module.
    """
    from egg_n_bacon_housing.adapters.onemap import setup_onemap_headers

    return OneMapGeocoder(
        headers=setup_onemap_headers(settings),
        cache_duration_hours=settings.geocoding.cache_duration_hours,
        max_workers=settings.geocoding.max_workers,
        timeout=settings.geocoding.timeout_seconds,
        rate_limit_seconds=settings.geocoding.api_delay_seconds,
        on_auth_expired=lambda: setup_onemap_headers(settings),
        cache_manager=cache_manager,
    )


class InMemoryGeocoder(Geocoder):
    """Test geocoder from a fixed lookup table."""

    def __init__(self, lookup: dict[str, tuple[float, float]]):
        self.lookup = {k.strip().lower(): v for k, v in lookup.items()}

    def geocode(self, addresses: pd.Series) -> pd.DataFrame:
        columns = ["input", "lat", "lon", "matched_name", "postal_code", "address"]
        results = []
        for addr in addresses:
            coords = self.lookup.get(str(addr).strip().lower())
            results.append(
                {
                    "input": addr,
                    "lat": coords[0] if coords else None,
                    "lon": coords[1] if coords else None,
                    "matched_name": str(addr) if coords else None,
                    "postal_code": None,
                    "address": str(addr),
                }
            )
        if not results:
            return pd.DataFrame(columns=columns)
        return pd.DataFrame(results)
