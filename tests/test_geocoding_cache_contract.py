"""Cold/warm equivalence for the OneMap geocode cache (CORE-1).

The OneMap cache stores the raw result frame the adapter fetched. A warm run
must reconstruct the *same* geocode row a cold run produced — including
OneMap's matched name and matched address — so condo project plausibility
(``plausible_project_match`` through ``_accept_plausible_project_coords``)
reaches the same accept/reject decision either way.

Pre-fix, the warm path returned lat/lon stitched onto an empty row whose
``address`` was the *query*, so plausibility compared the query with itself and
accepted coordinates the cold path rejected. These tests pin that divergence
shut, pin that a coordinate-only cache entry is a miss (never upgraded with a
fabricated matched address), and pin that a cache hit still costs no API call.
"""

import pandas as pd
import pytest

from egg_n_bacon_housing.adapters import onemap as onemap_adapter
from egg_n_bacon_housing.components.cleaning import _accept_plausible_project_coords
from egg_n_bacon_housing.utils.cache import CacheManager
from egg_n_bacon_housing.utils.geocoding import OneMapGeocoder, plausible_project_match

pytestmark = pytest.mark.unit

PROJECT = "THE TRELLIS"
STREET = "JALAN LEMPENG"
QUERY = f"{PROJECT} {STREET} Singapore"

# OneMap's first hit for the bare road name: a point ON the road, not the
# project. Same coordinates as a project hit would give, so only the metadata
# can tell them apart.
IMPLAUSIBLE_HIT = {
    "SEARCHVAL": "JALAN LEMPENG",
    "ADDRESS": "JALAN LEMPENG Singapore 128812",
    "POSTAL": "128812",
    "LATITUDE": "1.3155",
    "LONGITUDE": "103.7644",
}

# A genuine project hit for the same project/street.
PLAUSIBLE_HIT = {
    "SEARCHVAL": "THE TRELLIS",
    "ADDRESS": "THE TRELLIS JALAN LEMPENG SINGAPORE 128812",
    "POSTAL": "128812",
    "LATITUDE": "1.3155",
    "LONGITUDE": "103.7644",
}


@pytest.fixture()
def cache(tmp_path) -> CacheManager:
    return CacheManager(tmp_path / "onemap_cache", use_caching=True)


@pytest.fixture()
def api_calls(monkeypatch, request) -> list[str]:
    """Patch the OneMap transport (the adapter's real caching still runs).

    Counting at the transport is what makes "the warm run made no API call"
    meaningful: ``fetch_data_cached``'s own cache layer stays in play.
    """
    hit = getattr(request, "param", IMPLAUSIBLE_HIT)
    calls: list[str] = []

    def fake_fetch(search_string, headers, timeout=30):
        calls.append(search_string)
        return pd.DataFrame([hit])

    monkeypatch.setattr(onemap_adapter, "fetch_data", fake_fetch)
    return calls


def _geocoder(cache: CacheManager) -> OneMapGeocoder:
    return OneMapGeocoder(headers={"Authorization": "x"}, cache_manager=cache, max_workers=1)


def _geocode(cache: CacheManager, query: str = QUERY) -> dict:
    """One geocode row as a plain dict (typed loosely on purpose: pandas
    scalar access on a mixed-dtype frame is ``Any``)."""
    frame = _geocoder(cache).geocode(pd.Series([query]))
    return dict(frame.iloc[0].to_dict())


def _same_row(cold: dict, warm: dict) -> None:
    for column in ("input", "lat", "lon", "matched_name", "postal_code", "address"):
        cold_value, warm_value = cold[column], warm[column]
        both_null = bool(pd.isna(cold_value)) and bool(pd.isna(warm_value))
        assert both_null or cold_value == warm_value, f"{column}: {cold_value!r} != {warm_value!r}"


class TestColdWarmEquivalence:
    """A warm run reproduces the cold row exactly — coordinates and metadata."""

    def test_implausible_project_hit_keeps_its_metadata_on_the_warm_run(self, cache, api_calls):
        cold = _geocode(cache)
        assert api_calls == [QUERY]  # cold run: one API call

        warm = _geocode(cache)
        assert api_calls == [QUERY]  # warm run: served from cache, no API call

        _same_row(cold, warm)
        # The warm row carries OneMap's matched data, not the query.
        assert warm["lat"] == pytest.approx(1.3155)
        assert warm["lon"] == pytest.approx(103.7644)
        assert warm["matched_name"] == "JALAN LEMPENG"
        assert warm["address"] == "JALAN LEMPENG Singapore 128812"
        assert warm["address"] != QUERY

    @pytest.mark.parametrize("api_calls", [IMPLAUSIBLE_HIT], indirect=True)
    def test_cold_and_warm_rejection_are_identical(self, cache, api_calls):
        query_project = {QUERY: (PROJECT, STREET)}

        cold_lookup = _geocoder(cache).geocode(pd.Series([QUERY]))
        warm_lookup = _geocoder(cache).geocode(pd.Series([QUERY]))
        assert api_calls == [QUERY]  # second lookup was a pure cache read

        assert _accept_plausible_project_coords(cold_lookup, query_project) == {}
        assert _accept_plausible_project_coords(warm_lookup, query_project) == {}
        # The rejection is a decision, not a missing row: coordinates exist.
        assert warm_lookup.loc[0, "lat"] == pytest.approx(1.3155)
        assert not plausible_project_match(
            PROJECT,
            warm_lookup.loc[0, "matched_name"],
            warm_lookup.loc[0, "address"],
            street_name=STREET,
        )
        # Direction of the bug: the pre-fix warm row (matched address == the
        # query) WOULD have been accepted, so the metadata is what suppresses it.
        assert plausible_project_match(PROJECT, None, QUERY, street_name=STREET)

    @pytest.mark.parametrize("api_calls", [PLAUSIBLE_HIT], indirect=True)
    def test_cold_and_warm_acceptance_are_identical(self, cache, api_calls):
        query_project = {QUERY: (PROJECT, STREET)}

        cold = _accept_plausible_project_coords(
            _geocoder(cache).geocode(pd.Series([QUERY])), query_project
        )
        warm = _accept_plausible_project_coords(
            _geocoder(cache).geocode(pd.Series([QUERY])), query_project
        )
        assert api_calls == [QUERY]

        assert cold == warm == {QUERY: (pytest.approx(1.3155), pytest.approx(103.7644))}


class TestCacheEntryShape:
    """Only entries carrying OneMap metadata may seed a geocode row."""

    def test_coordinate_only_entry_is_a_miss_and_is_never_upgraded(self, cache, api_calls):
        """A legacy coordinate-only record has no matched name/address to verify
        against, so it must not become a row with the query as its address."""
        geocoder = _geocoder(cache)
        legacy = pd.DataFrame([{"LATITUDE": 1.3155, "LONGITUDE": 103.7644}])
        cache.set(geocoder._cache_id(QUERY), legacy)

        assert geocoder.query_geocode_cache(QUERY) is None

        row = _geocode(cache)
        # Treated as a miss: the query is re-fetched with its real metadata
        # (the unusable entry is dropped rather than silently reused).
        assert api_calls == [QUERY]
        assert row["lat"] == pytest.approx(1.3155)
        assert row["matched_name"] == "JALAN LEMPENG"
        assert row["address"] == "JALAN LEMPENG Singapore 128812"

    def test_coordinate_tuple_entry_is_a_miss(self, cache, api_calls):
        """A non-frame legacy value is a miss too (no attribute guessing)."""
        geocoder = _geocoder(cache)
        cache.set(geocoder._cache_id(QUERY), {"lat": 1.3155, "lon": 103.7644})

        assert geocoder.query_geocode_cache(QUERY) is None

        row = _geocode(cache)
        assert api_calls == [QUERY]
        assert row["matched_name"] == "JALAN LEMPENG"

    def test_entry_with_null_metadata_fails_closed_not_open(self, cache, api_calls):
        """Metadata genuinely unavailable (columns present, values null): the row
        keeps nulls and is rejected — reject, then street fallback."""
        geocoder = _geocoder(cache)
        cached = pd.DataFrame(
            [{"SEARCHVAL": None, "ADDRESS": None, "LATITUDE": 1.3155, "LONGITUDE": 103.7644}]
        )
        cache.set(geocoder._cache_id(QUERY), cached)

        row = _geocode(cache)
        assert api_calls == []  # a hit, not a miss: coordinates exist
        assert row["lat"] == pytest.approx(1.3155)
        assert bool(pd.isna(row["matched_name"]))
        assert bool(pd.isna(row["address"]))

        lookup = pd.DataFrame([row])
        assert _accept_plausible_project_coords(lookup, {QUERY: (PROJECT, STREET)}) == {}

    def test_failed_lookup_fabricates_no_metadata(self, cache, monkeypatch):
        """An API failure yields a coordinate-less row with null metadata."""

        def boom(search_string, headers, timeout=30):
            raise RuntimeError("onemap down")

        monkeypatch.setattr(onemap_adapter, "fetch_data", boom)

        row = _geocode(cache)

        assert row["input"] == QUERY  # the query echoes in "input" only
        assert row["lat"] is None
        assert row["lon"] is None
        assert bool(pd.isna(row["matched_name"]))
        assert bool(pd.isna(row["address"]))
        assert not plausible_project_match(PROJECT, row["matched_name"], row["address"], STREET)
