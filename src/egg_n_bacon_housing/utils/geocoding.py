"""Geocoding module: unified interface for address-to-coordinate resolution.

One interface, two adapters:
- OneMapGeocoder: production geocoding via OneMap API
- InMemoryGeocoder: test geocoding from a fixed lookup table

Extracts geocoding logic that was duplicated across 01_ingestion
(_geocode_shopping_malls), school_features (_geocode_schools),
and the onemap adapter.
"""

import logging
from abc import ABC, abstractmethod

import pandas as pd

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
    """Production geocoder using OneMap API via the onemap adapter."""

    def __init__(
        self,
        headers: dict[str, str],
        cache_duration_hours: int = 24,
        max_workers: int = 5,
        timeout: int = 30,
    ):
        self.headers = headers
        self.cache_duration_hours = cache_duration_hours
        self.max_workers = max_workers
        self.timeout = timeout

    def geocode(self, addresses: pd.Series) -> pd.DataFrame:
        from egg_n_bacon_housing.adapters.onemap import fetch_data_cached

        results = []
        for addr in addresses:
            try:
                df = fetch_data_cached(
                    str(addr),
                    headers=self.headers,
                    timeout=self.timeout,
                )
                if df is not None and not df.empty:
                    first = df.iloc[0]
                    results.append(
                        {
                            "input": addr,
                            "lat": float(first.get("LATITUDE", 0)),
                            "lon": float(first.get("LONGITUDE", 0)),
                            "matched_name": first.get("SEARCHVAL"),
                            "postal_code": first.get("POSTAL"),
                            "address": first.get("ADDRESS"),
                        }
                    )
                    continue
            except Exception as exc:
                logger.warning("Geocoding failed for %s: %s", addr, exc)

            results.append(
                {
                    "input": addr,
                    "lat": None,
                    "lon": None,
                    "matched_name": None,
                    "postal_code": None,
                    "address": str(addr),
                }
            )

        return pd.DataFrame(results)


class InMemoryGeocoder(Geocoder):
    """Test geocoder from a fixed lookup table."""

    def __init__(self, lookup: dict[str, tuple[float, float]]):
        self.lookup = {k.strip().lower(): v for k, v in lookup.items()}

    def geocode(self, addresses: pd.Series) -> pd.DataFrame:
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
        return pd.DataFrame(results)
