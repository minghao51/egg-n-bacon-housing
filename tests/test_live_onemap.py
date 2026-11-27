"""Live (real-network) validation of the OneMap geocode cache contract (WS-A1).

The fix under test: a warm (cache-hit) geocode must reconstruct the *same* row a
cold (API) geocode produced — input/lat/lon/matched_name/postal_code/address —
by running the cached OneMap result frame through ``_row_from_result``, and a
legacy coordinate-only cache entry must be read as a miss (and dropped) instead
of being upgraded with a fabricated matched address.

Everything here is skipped unless ``EGG_LIVE=1``, so the default suite never
touches the network. Addresses are geocoded through the production geocoder
wiring (``setup_onemap_headers`` + ``OneMapGeocoder``) with its own rate limiter,
two addresses per run, one worker — single-digit API calls on purpose.

Run them:

    EGG_LIVE=1 uv run pytest tests/ -m live -q --no-cov

OneMap credentials are required (``ONEMAP_EMAIL``/``ONEMAP_EMAIL_PASSWORD`` or an
unexpired ``ONEMAP_TOKEN``); without them the module skips with a clear reason
rather than failing. Nothing here touches ``data/cache/`` — each test uses a
throwaway cache directory under ``tmp_path``.
"""

import os
from pathlib import Path

import pandas as pd
import pytest

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.cache import _CACHE_MISS, CacheManager
from egg_n_bacon_housing.utils.geocoding import OneMapGeocoder

_LIVE = os.environ.get("EGG_LIVE") == "1"

pytestmark = [
    pytest.mark.live,
    pytest.mark.api,
    pytest.mark.skipif(
        not _LIVE,
        reason="live network tests are opt-in: set EGG_LIVE=1 to geocode against OneMap",
    ),
]


# Real Singapore addresses/identifiers OneMap resolves with full metadata
# (SEARCHVAL/ADDRESS/POSTAL). A postal code and a block address — the two shapes
# the pipeline actually geocodes (condos by project+street, HDB by block).
ADDRESSES: tuple[str, ...] = (
    "128812",
    "462 CLEMENTI AVENUE 3",
)

# Deliberately not one of ADDRESSES: the legacy-entry test must not be able to
# disturb an entry a cold/warm test depends on.
LEGACY_ADDRESS = "1 RAFFLES PLACE"

_ROW_FIELDS = ("input", "lat", "lon", "matched_name", "postal_code", "address")


def _credentials_available() -> bool:
    token = settings.onemap_token
    has_token = bool(token and token.get_secret_value().strip())
    has_password = bool(
        settings.onemap_email.get_secret_value().strip()
        and settings.onemap_password.get_secret_value().strip()
    )
    return has_token or has_password


requires_onemap = pytest.mark.skipif(
    not _credentials_available(),
    reason="OneMap credentials not configured (ONEMAP_TOKEN or ONEMAP_EMAIL/ONEMAP_EMAIL_PASSWORD)",
)


@pytest.fixture(scope="module")
def cache_dir(tmp_path_factory) -> Path:
    """Throwaway OneMap cache directory (never the repo's data/cache/)."""
    return tmp_path_factory.mktemp("onemap_live_cache")


@pytest.fixture(scope="module")
def cold_rows(cache_dir: Path) -> dict[str, dict]:
    """Geocode the live addresses once, through the production wiring."""
    from egg_n_bacon_housing.adapters.onemap import setup_onemap_headers

    cache = CacheManager(cache_dir, use_caching=True)
    geocoder = OneMapGeocoder(
        headers=setup_onemap_headers(settings),
        cache_manager=cache,
        cache_duration_hours=settings.geocoding.cache_duration_hours,
        max_workers=1,
        timeout=settings.geocoding.timeout_seconds,
        # The geocoder's own limiter, as production uses it: one API call per
        # api_delay_seconds, and never on a cache hit.
        rate_limit_seconds=settings.geocoding.api_delay_seconds,
    )
    frame = geocoder.geocode(pd.Series(list(ADDRESSES)))
    return {row["input"]: row for row in frame.to_dict(orient="records")}


@requires_onemap
class TestColdWarmEquivalence:
    """A warm run must reproduce the cold run's row exactly."""

    def test_cold_geocode_resolves_real_metadata(self, cold_rows: dict[str, dict]):
        for address in ADDRESSES:
            row = cold_rows[address]
            assert row["lat"] is not None and row["lon"] is not None, (
                f"cold geocode of {address!r} returned no coordinates: {row}"
            )
            # The metadata columns are what plausibility checks judge; a cold row
            # without them would make the warm comparison vacuous.
            for field in ("matched_name", "address", "postal_code"):
                assert row[field] is not None and str(row[field]).strip(), (
                    f"cold geocode of {address!r} has no {field}: {row}"
                )

    def test_warm_read_returns_the_cold_row(self, cache_dir: Path, cold_rows: dict[str, dict]):
        cache = CacheManager(cache_dir, use_caching=True)
        geocoder = OneMapGeocoder(headers={"Authorization": "unused"}, cache_manager=cache)

        for address in ADDRESSES:
            warm = geocoder.query_geocode_cache(address)
            assert warm is not None, f"cache miss for {address!r} after a cold geocode"
            assert set(warm) == set(_ROW_FIELDS), f"warm row fields differ: {sorted(warm)}"
            assert warm == cold_rows[address], (
                f"warm row for {address!r} differs from the cold row:\n"
                f"  cold={cold_rows[address]}\n  warm={warm}"
            )

    def test_warm_geocode_needs_no_api_call(self, cache_dir: Path, cold_rows: dict[str, dict]):
        # Credentials that cannot authenticate: if the warm path fell through to
        # the network, OneMap would reject them and the row would come back empty.
        cache = CacheManager(cache_dir, use_caching=True)
        geocoder = OneMapGeocoder(
            headers={"Authorization": "not-a-real-token"},
            cache_manager=cache,
            max_workers=1,
            rate_limit_seconds=0.0,
        )

        frame = geocoder.geocode(pd.Series(list(ADDRESSES)))

        for row in frame.to_dict(orient="records"):
            assert row == cold_rows[row["input"]], (
                "warm geocode with invalid credentials did not reproduce the cold row "
                f"— it must be served entirely from cache: {row}"
            )


@requires_onemap
class TestLegacyCoordinateOnlyEntry:
    """A coordinate-only entry is a miss, never a fabricated row."""

    def test_legacy_entry_is_a_miss_and_is_dropped(self, cache_dir: Path):
        cache = CacheManager(cache_dir, use_caching=True)
        # Exactly what an older cache version stored: coordinates, no OneMap
        # identity metadata.
        legacy = pd.DataFrame([{"LATITUDE": "1.2843", "LONGITUDE": "103.8510"}])
        cache.set(OneMapGeocoder._cache_id(LEGACY_ADDRESS), legacy)
        assert cache.get(OneMapGeocoder._cache_id(LEGACY_ADDRESS)) is not _CACHE_MISS

        geocoder = OneMapGeocoder(headers={"Authorization": "unused"}, cache_manager=cache)
        row = geocoder.query_geocode_cache(LEGACY_ADDRESS)

        assert row is None, f"coordinate-only entry was upgraded into a row: {row}"
        # Dropped, so the next fetch repopulates it with full metadata instead of
        # the adapter re-reading the same unusable entry forever.
        assert cache.get(OneMapGeocoder._cache_id(LEGACY_ADDRESS)) is _CACHE_MISS
