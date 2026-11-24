"""Tests for the geocoding seam.

The interface is the test surface: ``geocode`` / ``geocode_dataframe`` are
exercised through ``InMemoryGeocoder``. ``OneMapGeocoder``'s cache-first,
rate-limit, and parallel paths are covered with the OneMap transport and the
cache manager monkeypatched (no network).
"""

import threading
from typing import Any, cast

import pandas as pd
import pytest

from egg_n_bacon_housing.utils.cache import _CACHE_MISS, CacheManager
from egg_n_bacon_housing.utils.geocoding import (
    Geocoder,
    InMemoryGeocoder,
    OneMapGeocoder,
    _RateLimiter,
    build_default_geocoder,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _inject_cache_manager(monkeypatch, tmp_path):
    """Keep geocoder tests explicit while preserving their cache fakes."""
    import egg_n_bacon_housing.utils.cache as cache_mod

    manager = CacheManager(tmp_path / "cache")
    monkeypatch.setattr(cache_mod, "configure", lambda *args, **kwargs: manager, raising=False)
    monkeypatch.setattr(cache_mod, "get_cache_manager", lambda: manager, raising=False)

    original_init = OneMapGeocoder.__init__

    def init_with_manager(self, headers, cache_manager=None, **kwargs):
        return original_init(self, headers, cache_manager or manager, **kwargs)

    monkeypatch.setattr(OneMapGeocoder, "__init__", init_with_manager)
    return manager


class TestInMemoryGeocoder:
    """The Geocoder contract, verified through the test adapter."""

    @staticmethod
    def _geocoder() -> InMemoryGeocoder:
        return InMemoryGeocoder(
            {"ION Orchard": (1.3048, 103.8318), "tampines mall": (1.3521, 103.9444)}
        )

    def test_is_a_geocoder(self):
        assert isinstance(self._geocoder(), Geocoder)

    def test_geocode_returns_coords_for_known_addresses(self):
        df = self._geocoder().geocode(pd.Series(["ION Orchard", "tampines mall"]))
        assert df.loc[0, "lat"] == pytest.approx(1.3048)
        assert df.loc[0, "lon"] == pytest.approx(103.8318)
        assert df.loc[1, "lat"] == pytest.approx(1.3521)
        assert df.loc[1, "lon"] == pytest.approx(103.9444)

    def test_geocode_returns_none_for_unknown(self):
        df = self._geocoder().geocode(pd.Series(["Nowhere"]))
        assert pd.isna(df.loc[0, "lat"])
        assert pd.isna(df.loc[0, "lon"])

    def test_geocode_is_case_insensitive_and_strips_whitespace(self):
        df = self._geocoder().geocode(pd.Series(["  ion orchard  "]))
        assert df.loc[0, "lat"] == pytest.approx(1.3048)

    def test_geocode_dataframe_adds_lat_lon(self):
        malls = pd.DataFrame([{"shopping_mall": "ION Orchard"}])
        out = self._geocoder().geocode_dataframe(malls, "shopping_mall")
        assert out.loc[0, "lat"] == pytest.approx(1.3048)
        assert out.loc[0, "lon"] == pytest.approx(103.8318)

    def test_geocode_dataframe_preserves_existing_columns(self):
        malls = pd.DataFrame([{"shopping_mall": "ION Orchard", "category": "mall"}])
        out = self._geocoder().geocode_dataframe(malls, "shopping_mall")
        assert out.loc[0, "category"] == "mall"
        assert out.loc[0, "shopping_mall"] == "ION Orchard"

    def test_geocode_dataframe_does_not_mutate_input(self):
        malls = pd.DataFrame([{"shopping_mall": "ION Orchard"}])
        self._geocoder().geocode_dataframe(malls, "shopping_mall")
        assert "lat" not in malls.columns
        assert "lon" not in malls.columns

    def test_geocode_empty_series_returns_empty_frame_with_columns(self):
        df = self._geocoder().geocode(pd.Series([], dtype=object))
        assert df.empty
        assert {"lat", "lon"}.issubset(df.columns)


class TestOneMapGeocoderCacheLookup:
    """query_geocode_cache encapsulates the OneMap cache-key format.

    It returns a full geocode row, not a coordinate tuple: the row carries
    OneMap's matched name/address read from the cached result frame, because
    condo project plausibility is judged from exactly those fields.
    """

    @staticmethod
    def _frame(**overrides) -> pd.DataFrame:
        row = {
            "SEARCHVAL": "ION ORCHARD",
            "ADDRESS": "ION ORCHARD, 2 ORCHARD TURN SINGAPORE 238841",
            "POSTAL": "238841",
            "LATITUDE": 1.3048,
            "LONGITUDE": 103.8318,
        }
        row.update(overrides)
        return pd.DataFrame([row])

    @staticmethod
    def _geocoder(monkeypatch, cache: dict, manager: CacheManager) -> OneMapGeocoder:
        def fake_get(identifier, duration_hours=None):
            return cache.get(identifier, _CACHE_MISS)

        monkeypatch.setattr(manager, "get", fake_get)
        return OneMapGeocoder(cache_manager=manager, headers={"Authorization": "x"})

    def test_cache_hit_returns_the_full_row_with_matched_metadata(
        self, monkeypatch, _inject_cache_manager
    ):
        cache = {"onemap_search:ION Orchard": self._frame()}
        geocoder = self._geocoder(monkeypatch, cache, _inject_cache_manager)

        row = geocoder.query_geocode_cache("ION Orchard")

        assert row is not None
        assert row["input"] == "ION Orchard"
        assert row["lat"] == pytest.approx(1.3048)
        assert row["lon"] == pytest.approx(103.8318)
        assert row["matched_name"] == "ION ORCHARD"
        assert row["address"] == "ION ORCHARD, 2 ORCHARD TURN SINGAPORE 238841"
        assert row["postal_code"] == "238841"

    def test_cache_miss_returns_none(self, monkeypatch, _inject_cache_manager):
        geocoder = self._geocoder(monkeypatch, {}, _inject_cache_manager)
        assert geocoder.query_geocode_cache("Nowhere") is None

    def test_cache_row_with_xy_fallback_is_extracted(self, monkeypatch, _inject_cache_manager):
        cache = {"onemap_search:X": pd.DataFrame([{"SEARCHVAL": "X", "Y": 1.5, "X": 2.5}])}
        geocoder = self._geocoder(monkeypatch, cache, _inject_cache_manager)
        row = geocoder.query_geocode_cache("X")
        assert row is not None
        assert (row["lat"], row["lon"]) == (1.5, 2.5)

    def test_cache_row_with_unparseable_coords_returns_none(
        self, monkeypatch, _inject_cache_manager
    ):
        cache = {"onemap_search:X": self._frame(LATITUDE="bad", LONGITUDE="x")}
        geocoder = self._geocoder(monkeypatch, cache, _inject_cache_manager)
        assert geocoder.query_geocode_cache("X") is None


class TestOneMapGeocoderCacheFirst:
    """Sequential geocode resolves cache hits without an API call or a sleep."""

    @staticmethod
    def _patch_sleep(monkeypatch) -> list:
        sleeps: list = []
        monkeypatch.setattr(
            "egg_n_bacon_housing.utils.geocoding.time.sleep", lambda s: sleeps.append(s)
        )
        return sleeps

    @staticmethod
    def _patch_api(monkeypatch, return_df) -> list:
        calls: list = []

        def fake_fetch(*args, **kwargs):
            calls.append(args)
            return return_df

        monkeypatch.setattr("egg_n_bacon_housing.adapters.onemap.fetch_data_cached", fake_fetch)
        return calls

    def test_sequential_cache_hit_never_calls_api_nor_sleeps(
        self, monkeypatch, _inject_cache_manager
    ):
        cache = {
            "onemap_search:Cached": pd.DataFrame(
                [
                    {
                        "SEARCHVAL": "CACHED BUILDING",
                        "ADDRESS": "1 CACHED ROAD SINGAPORE 123456",
                        "LATITUDE": 1.0,
                        "LONGITUDE": 2.0,
                    }
                ]
            )
        }
        geocoder = OneMapGeocoder(
            cache_manager=_inject_cache_manager,
            headers={"Authorization": "x"},
            max_workers=1,
            rate_limit_seconds=5,
        )
        monkeypatch.setattr(
            _inject_cache_manager,
            "get",
            lambda identifier, duration_hours=24: cache.get(identifier, _CACHE_MISS),
        )
        api_calls = self._patch_api(
            monkeypatch, pd.DataFrame([{"LATITUDE": 9.0, "LONGITUDE": 9.0}])
        )
        sleeps = self._patch_sleep(monkeypatch)

        df = geocoder.geocode(pd.Series(["Cached"]))

        assert df.loc[0, "lat"] == pytest.approx(1.0)  # from cache, not API
        assert api_calls == []
        assert sleeps == []

    def test_sequential_miss_returns_api_coords(self, monkeypatch, _inject_cache_manager):
        geocoder = OneMapGeocoder(
            cache_manager=_inject_cache_manager,
            headers={"Authorization": "x"},
            max_workers=1,
            rate_limit_seconds=0.0,
        )
        monkeypatch.setattr(
            _inject_cache_manager,
            "get",
            lambda identifier, duration_hours=24: _CACHE_MISS,
        )
        self._patch_api(monkeypatch, pd.DataFrame([{"LATITUDE": 7.0, "LONGITUDE": 8.0}]))
        sleeps = self._patch_sleep(monkeypatch)

        df = geocoder.geocode(pd.Series(["Miss"]))

        assert df.loc[0, "lat"] == pytest.approx(7.0)  # from API
        assert sleeps == []  # rate_limit_seconds was 0 -> no sleep

    def test_sequential_miss_with_rate_limit_sleeps(self, monkeypatch, _inject_cache_manager):
        geocoder = OneMapGeocoder(
            cache_manager=_inject_cache_manager,
            headers={"Authorization": "x"},
            max_workers=1,
            rate_limit_seconds=3,
        )
        monkeypatch.setattr(
            _inject_cache_manager,
            "get",
            lambda identifier, duration_hours=24: _CACHE_MISS,
        )
        self._patch_api(monkeypatch, pd.DataFrame([{"LATITUDE": 7.0, "LONGITUDE": 8.0}]))
        sleeps = self._patch_sleep(monkeypatch)

        geocoder.geocode(pd.Series(["Miss One", "Miss Two"]))

        # first call goes through immediately, second waits ~rate_limit_seconds
        assert len(sleeps) == 1
        assert 2.9 <= sleeps[0] <= 3.0

    def test_miss_passes_geocoding_ttl_knob_to_adapter(self, monkeypatch, _inject_cache_manager):
        """API misses must read and write the cache under the geocoder's own
        cache_duration_hours knob, not the pipeline-wide cache default."""
        geocoder = OneMapGeocoder(
            cache_manager=_inject_cache_manager,
            headers={"Authorization": "x"},
            max_workers=1,
            cache_duration_hours=48,
        )
        monkeypatch.setattr(
            _inject_cache_manager,
            "get",
            lambda identifier, duration_hours=24: _CACHE_MISS,
        )
        captured: dict = {}

        def fake_fetch(search_string, headers, timeout, **kwargs):
            captured.update(kwargs)
            return pd.DataFrame([{"LATITUDE": 7.0, "LONGITUDE": 8.0}])

        monkeypatch.setattr("egg_n_bacon_housing.adapters.onemap.fetch_data_cached", fake_fetch)

        geocoder.geocode(pd.Series(["Miss"]))

        assert captured.get("duration_hours") == 48


class TestOneMapGeocoderParallel:
    def test_parallel_geocode_resolves_all_via_api(self, monkeypatch, _inject_cache_manager):
        geocoder = OneMapGeocoder(
            cache_manager=_inject_cache_manager, headers={"Authorization": "x"}, max_workers=3
        )
        monkeypatch.setattr(
            _inject_cache_manager,
            "get",
            lambda identifier, duration_hours=24: _CACHE_MISS,
        )
        monkeypatch.setattr(
            "egg_n_bacon_housing.adapters.onemap.fetch_data_cached",
            lambda *a, **k: pd.DataFrame([{"LATITUDE": 1.5, "LONGITUDE": 2.5}]),
        )

        df = geocoder.geocode(pd.Series(["A", "B", "C"]))

        assert len(df) == 3
        assert df["lat"].tolist() == [1.5, 1.5, 1.5]
        assert df["lon"].tolist() == [2.5, 2.5, 2.5]

    def test_parallel_preserves_input_order(self, monkeypatch, _inject_cache_manager):
        geocoder = OneMapGeocoder(
            cache_manager=_inject_cache_manager, headers={"Authorization": "x"}, max_workers=4
        )

        def fake_get(identifier, duration_hours=24):
            return _CACHE_MISS

        monkeypatch.setattr(_inject_cache_manager, "get", fake_get)

        def fake_fetch(search_string, headers, timeout, **kwargs):
            return pd.DataFrame(
                [{"LATITUDE": float(search_string), "LONGITUDE": float(search_string) * 10}]
            )

        monkeypatch.setattr("egg_n_bacon_housing.adapters.onemap.fetch_data_cached", fake_fetch)

        df = geocoder.geocode(pd.Series(["1", "2", "3", "4"]))

        assert df["input"].tolist() == ["1", "2", "3", "4"]
        assert df["lat"].tolist() == [1.0, 2.0, 3.0, 4.0]


class TestBuildDefaultGeocoder:
    def test_wires_settings_into_onemap_geocoder(self, monkeypatch, _inject_cache_manager):
        monkeypatch.setattr(
            "egg_n_bacon_housing.adapters.onemap.setup_onemap_headers",
            lambda settings: {"Authorization": "token"},
        )

        class _Geo:
            cache_duration_hours = 48
            max_workers = 7
            timeout_seconds = 20
            api_delay_seconds = 0.5

        class FakeSettings:
            geocoding = _Geo()

        geocoder = build_default_geocoder(cast(Any, FakeSettings()), _inject_cache_manager)

        assert isinstance(geocoder, OneMapGeocoder)
        assert geocoder.headers == {"Authorization": "token"}
        assert geocoder.max_workers == 7
        assert geocoder.timeout == 20
        assert geocoder._limiter.interval == 0.5
        assert geocoder.cache_duration_hours == 48


class TestOneMapGeocoderRateLimiting:
    """Pacing is enforced across threads and never applied to cache hits."""

    @staticmethod
    def _cache_miss(monkeypatch, manager: CacheManager) -> None:
        monkeypatch.setattr(
            manager,
            "get",
            lambda identifier, duration_hours=24: _CACHE_MISS,
        )

    def test_parallel_misses_are_rate_limited(self, monkeypatch, _inject_cache_manager):
        geocoder = OneMapGeocoder(
            cache_manager=_inject_cache_manager,
            headers={"Authorization": "x"},
            max_workers=3,
            rate_limit_seconds=0.5,
        )
        self._cache_miss(monkeypatch, _inject_cache_manager)
        waits: list = []
        monkeypatch.setattr(geocoder._limiter, "wait", lambda: waits.append(1))
        monkeypatch.setattr(
            "egg_n_bacon_housing.adapters.onemap.fetch_data_cached",
            lambda *a, **k: pd.DataFrame([{"LATITUDE": 1.0, "LONGITUDE": 2.0}]),
        )

        geocoder.geocode(pd.Series(["A", "B", "C"]))

        assert len(waits) == 3  # every API miss paced

    def test_parallel_cache_hits_are_not_paced(self, monkeypatch, _inject_cache_manager):
        geocoder = OneMapGeocoder(
            cache_manager=_inject_cache_manager,
            headers={"Authorization": "x"},
            max_workers=2,
            rate_limit_seconds=0.5,
        )
        cache = {
            "onemap_search:A": pd.DataFrame(
                [
                    {
                        "SEARCHVAL": "A BUILDING",
                        "ADDRESS": "1 A ROAD SINGAPORE 111111",
                        "LATITUDE": 1.0,
                        "LONGITUDE": 2.0,
                    }
                ]
            ),
            "onemap_search:B": pd.DataFrame(
                [
                    {
                        "SEARCHVAL": "B BUILDING",
                        "ADDRESS": "2 B ROAD SINGAPORE 222222",
                        "LATITUDE": 3.0,
                        "LONGITUDE": 4.0,
                    }
                ]
            ),
        }
        monkeypatch.setattr(
            _inject_cache_manager,
            "get",
            lambda identifier, duration_hours=24: cache.get(identifier, _CACHE_MISS),
        )
        waits: list = []
        monkeypatch.setattr(geocoder._limiter, "wait", lambda: waits.append(1))
        api_calls: list = []

        def fail_fetch(*args, **kwargs):
            api_calls.append(args)
            raise AssertionError("cache hit must not reach the API")

        monkeypatch.setattr("egg_n_bacon_housing.adapters.onemap.fetch_data_cached", fail_fetch)

        df = geocoder.geocode(pd.Series(["A", "B"]))

        assert df["lat"].tolist() == [1.0, 3.0]
        assert waits == []  # cache hits never paced
        assert api_calls == []


class _VirtualClock:
    """Frozen-clock stand-in for the ``time`` module used by ``_RateLimiter``.

    ``monotonic`` never advances, so every waiter counts as arriving in the
    same instant — exactly the burst window the limiter must space out — and
    ``sleep`` records the instant that waiter is scheduled to wake instead of
    blocking. Nothing here sleeps for real time, so the schedule assertion is
    deterministic.
    """

    def __init__(self, start: float = 1000.0) -> None:
        self._now = start
        self._local = threading.local()
        self.wakes: list[float] = []

    def monotonic(self) -> float:
        self._local.arrival = self._now
        return self._now

    def sleep(self, seconds: float) -> None:
        self._local.wake = self._local.arrival + seconds
        self.wakes.append(self._local.wake)

    def release_instant(self) -> float:
        """When the calling waiter actually proceeds (its reserved slot)."""
        wake = getattr(self._local, "wake", None)
        return self._local.arrival if wake is None else wake


class TestRateLimiterSpacing:
    """Concurrent waiters hold slots one interval apart (CORE-6).

    The pre-fix ``wait()`` recomputed ``_next_slot`` from each waiter's own
    arrival time, overwriting the reservations still pending, so a burst of
    waiters all woke at the first slot (the probe measured 20-80 us gaps at an
    80 ms interval). The counter-based parallel test above cannot see that;
    this one asserts the reserved slot schedule itself.
    """

    @staticmethod
    def _release_instants(monkeypatch, waiters: int, interval: float) -> list[float]:
        from egg_n_bacon_housing.utils import geocoding as geocoding_mod

        clock = _VirtualClock()
        monkeypatch.setattr(geocoding_mod, "time", clock)
        limiter = _RateLimiter(interval)
        barrier = threading.Barrier(waiters)
        releases: list[float] = []
        releases_lock = threading.Lock()

        def wait_once() -> None:
            barrier.wait(timeout=10)
            limiter.wait()
            with releases_lock:
                releases.append(clock.release_instant())

        threads = [threading.Thread(target=wait_once, daemon=True) for _ in range(waiters)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert not any(thread.is_alive() for thread in threads), "waiter thread hung"
        assert len(releases) == waiters
        return sorted(releases)

    def test_concurrent_waiters_release_at_least_one_interval_apart(self, monkeypatch):
        interval = 0.08  # the interval the probe used
        waiters = 6

        ordered = self._release_instants(monkeypatch, waiters, interval)

        gaps = [later - earlier for earlier, later in zip(ordered, ordered[1:], strict=False)]
        epsilon = 1e-9  # float slack only: virtual time, so no scheduler jitter
        assert all(gap >= interval - epsilon for gap in gaps), gaps
        # Exactly one reservation per interval: no burst, and no wasted slack
        # (a fix that always slept a full interval would pass the gap check
        # but fail this span check).
        assert ordered[-1] - ordered[0] == pytest.approx(interval * (waiters - 1))
        # The first arrival is never delayed: it takes the slot it arrives on.
        assert ordered[0] == pytest.approx(1000.0)

    def test_waiters_arriving_at_different_times_keep_their_slots(self, monkeypatch):
        """Sequential arrivals still get distinct, interval-spaced slots."""
        from egg_n_bacon_housing.utils import geocoding as geocoding_mod

        clock = _VirtualClock()
        monkeypatch.setattr(geocoding_mod, "time", clock)
        limiter = _RateLimiter(0.25)

        limiter.wait()
        first = clock.release_instant()
        limiter.wait()
        second = clock.release_instant()

        assert first == pytest.approx(1000.0)
        assert second - first == pytest.approx(0.25)

    def test_disabled_pacing_never_sleeps_or_reserves(self, monkeypatch):
        """The ``interval <= 0`` fast path is unchanged."""
        from egg_n_bacon_housing.utils import geocoding as geocoding_mod

        clock = _VirtualClock()
        monkeypatch.setattr(geocoding_mod, "time", clock)
        limiter = _RateLimiter(0)

        limiter.wait()
        limiter.wait()

        assert clock.wakes == []
        assert limiter._next_slot == 0.0


class TestOneMapGeocoderAuthRefresh:
    """A mid-run token expiry refreshes headers once and retries."""

    @staticmethod
    def _cache_miss(monkeypatch, manager: CacheManager) -> None:
        monkeypatch.setattr(
            manager,
            "get",
            lambda identifier, duration_hours=24: _CACHE_MISS,
        )

    def test_auth_error_refreshes_headers_and_retries(self, monkeypatch, _inject_cache_manager):
        from egg_n_bacon_housing.adapters.exceptions import OneMapAuthError

        geocoder = OneMapGeocoder(
            cache_manager=_inject_cache_manager,
            headers={"Authorization": "expired"},
            on_auth_expired=lambda: {"Authorization": "fresh"},
        )
        self._cache_miss(monkeypatch, _inject_cache_manager)

        seen_headers: list = []

        def fake_fetch(search_string, headers, timeout, **kwargs):
            seen_headers.append(headers)
            if headers["Authorization"] == "expired":
                raise OneMapAuthError("OneMap rejected credentials (HTTP 401)")
            return pd.DataFrame([{"LATITUDE": 5.0, "LONGITUDE": 6.0}])

        monkeypatch.setattr("egg_n_bacon_housing.adapters.onemap.fetch_data_cached", fake_fetch)

        df = geocoder.geocode(pd.Series(["Somewhere"]))

        assert df.loc[0, "lat"] == pytest.approx(5.0)
        assert geocoder.headers == {"Authorization": "fresh"}
        assert len(seen_headers) == 2  # expired attempt + retry with fresh token

    def test_refresh_failure_returns_empty_row(self, monkeypatch, _inject_cache_manager):
        from egg_n_bacon_housing.adapters.exceptions import OneMapAuthError

        geocoder = OneMapGeocoder(
            cache_manager=_inject_cache_manager,
            headers={"Authorization": "expired"},
            on_auth_expired=lambda: (_ for _ in ()).throw(RuntimeError("auth service down")),
        )
        self._cache_miss(monkeypatch, _inject_cache_manager)

        calls: list = []

        def fake_fetch(search_string, headers, timeout, **kwargs):
            calls.append(1)
            raise OneMapAuthError("rejected")

        monkeypatch.setattr("egg_n_bacon_housing.adapters.onemap.fetch_data_cached", fake_fetch)

        df = geocoder.geocode(pd.Series(["Somewhere"]))

        assert df.loc[0, "lat"] is None
        # A failed lookup carries no fabricated metadata: the query echoes back
        # in "input" only, so project plausibility fails closed instead of
        # comparing the query with itself.
        assert df.loc[0, "input"] == "Somewhere"
        assert pd.isna(df.loc[0, "address"])
        assert pd.isna(df.loc[0, "matched_name"])
        assert len(calls) == 1  # refresh failed -> no fresh token to retry with

    def test_no_refresh_callback_returns_empty_row(self, monkeypatch, _inject_cache_manager):
        from egg_n_bacon_housing.adapters.exceptions import OneMapAuthError

        geocoder = OneMapGeocoder(
            cache_manager=_inject_cache_manager, headers={"Authorization": "expired"}
        )
        self._cache_miss(monkeypatch, _inject_cache_manager)

        def fake_fetch(search_string, headers, timeout, **kwargs):
            raise OneMapAuthError("rejected")

        monkeypatch.setattr("egg_n_bacon_housing.adapters.onemap.fetch_data_cached", fake_fetch)

        df = geocoder.geocode(pd.Series(["Somewhere"]))

        assert df.loc[0, "lat"] is None

    def test_concurrent_auth_expiry_refreshes_exactly_once(
        self, monkeypatch, _inject_cache_manager
    ):
        """T6: a mid-run token expiry across workers triggers ONE refresh.

        All workers fail against the same stale headers object; only the first
        thread into the auth lock performs the refresh — the rest detect the
        replaced headers and retry without another network round trip."""
        import threading

        from egg_n_bacon_housing.adapters.exceptions import OneMapAuthError

        workers = 5
        geocoder = OneMapGeocoder(
            cache_manager=_inject_cache_manager,
            headers={"Authorization": "expired"},
            max_workers=workers,
        )
        self._cache_miss(monkeypatch, _inject_cache_manager)

        refresh_calls: list[int] = []
        refresh_lock = threading.Lock()

        def on_auth_expired():
            with refresh_lock:
                refresh_calls.append(1)
            return {"Authorization": "fresh"}

        geocoder._on_auth_expired = on_auth_expired

        # Barrier: every worker must fail against the stale headers before any
        # of them proceeds to the refresh, so all 5 contend on the lock.
        fail_barrier = threading.Barrier(workers)

        def fake_fetch(search_string, headers, timeout, **kwargs):
            if headers["Authorization"] == "expired":
                fail_barrier.wait(timeout=10)
                raise OneMapAuthError("OneMap rejected credentials (HTTP 401)")
            return pd.DataFrame([{"LATITUDE": 5.0, "LONGITUDE": 6.0}])

        monkeypatch.setattr("egg_n_bacon_housing.adapters.onemap.fetch_data_cached", fake_fetch)

        df = geocoder.geocode(pd.Series(["A", "B", "C", "D", "E"]))

        assert df["lat"].tolist() == [5.0] * workers  # every address recovered
        assert refresh_calls == [1]  # exactly one refresh across 5 workers
        assert geocoder.headers == {"Authorization": "fresh"}
