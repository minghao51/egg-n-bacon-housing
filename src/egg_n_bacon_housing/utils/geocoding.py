"""Geocoding module: unified interface for address-to-coordinate resolution.

One interface, two adapters:
- OneMapGeocoder: production geocoding via OneMap API
- InMemoryGeocoder: test geocoding from a fixed lookup table

Extracts geocoding logic that was duplicated across ingestion
(_geocode_shopping_malls), school_features (_geocode_schools),
and the onemap adapter.
"""

import logging
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from egg_n_bacon_housing.config import Settings

logger = logging.getLogger(__name__)


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
        cache_duration_hours: int = 24,
        max_workers: int = 5,
        timeout: int = 30,
        rate_limit_seconds: float = 0.0,
    ):
        self.headers = headers
        self.cache_duration_hours = cache_duration_hours
        self.max_workers = max_workers
        self.timeout = timeout
        self.rate_limit_seconds = rate_limit_seconds

    def query_geocode_cache(self, address: str) -> tuple[float, float] | None:
        """Read-only lookup of the OneMap cache for one address.

        Returns ``(lat, lon)`` if a cached result exists, else ``None``. Makes
        no API call. Keeps the OneMap cache-key format inside this module
        instead of leaking it to callers.
        """
        from egg_n_bacon_housing.utils.cache import _CACHE_MISS, get_cache_manager

        cached = get_cache_manager().get(
            f"onemap_search:{address}", duration_hours=self.cache_duration_hours
        )
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

    def _geocode_via_api(self, addr: str) -> dict:
        from egg_n_bacon_housing.adapters.onemap import fetch_data_cached

        try:
            df = fetch_data_cached(addr, headers=self.headers, timeout=self.timeout)
            return self._row_from_result(addr, df)
        except Exception as exc:
            logger.warning("Geocoding failed for %s: %s", addr, exc)
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
        rows = []
        for addr in addrs:
            cached = self.query_geocode_cache(addr)
            if cached is not None:
                rows.append({**self._empty_row(addr), "lat": cached[0], "lon": cached[1]})
                continue
            rows.append(self._geocode_via_api(addr))
            if self.rate_limit_seconds:
                time.sleep(self.rate_limit_seconds)
        return pd.DataFrame(rows)

    def _geocode_parallel(self, addrs: list[str]) -> pd.DataFrame:
        rows: list[dict] = [self._empty_row(a) for a in addrs]
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(self._geocode_via_api, a): i for i, a in enumerate(addrs)}
            for future in as_completed(futures):
                rows[futures[future]] = future.result()
        return pd.DataFrame(rows)


def build_default_geocoder(settings: Settings) -> Geocoder:
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
