"""Tests for utils/cache.py."""

import importlib
import pickle

import pandas as pd


def _get_cache_module():
    return importlib.import_module("egg_n_bacon_housing.utils.cache")


class TestCacheSentinel:
    def test_cached_call_stores_falsy_empty_dataframe(self, tmp_path, monkeypatch):
        cache = _get_cache_module()
        monkeypatch.setattr(cache._cache_manager, "cache_dir", tmp_path)
        monkeypatch.setattr(cache.settings.pipeline, "use_caching", True)

        call_count = 0

        def returns_empty():
            nonlocal call_count
            call_count += 1
            return pd.DataFrame()

        result1 = cache.cached_call("test_empty_df", returns_empty, duration_hours=1)
        assert result1.empty
        assert call_count == 1

        result2 = cache.cached_call("test_empty_df", returns_empty, duration_hours=1)
        assert result2.empty
        assert call_count == 1

    def test_cached_call_stores_none(self, tmp_path, monkeypatch):
        cache = _get_cache_module()
        monkeypatch.setattr(cache._cache_manager, "cache_dir", tmp_path)
        monkeypatch.setattr(cache.settings.pipeline, "use_caching", True)

        call_count = 0

        def returns_none():
            nonlocal call_count
            call_count += 1
            return None

        result1 = cache.cached_call("test_none", returns_none, duration_hours=1)
        assert result1 is None
        assert call_count == 1

        result2 = cache.cached_call("test_none", returns_none, duration_hours=1)
        assert result2 is None
        assert call_count == 1

    def test_cached_call_stores_zero(self, tmp_path, monkeypatch):
        cache = _get_cache_module()
        monkeypatch.setattr(cache._cache_manager, "cache_dir", tmp_path)
        monkeypatch.setattr(cache.settings.pipeline, "use_caching", True)

        call_count = 0

        def returns_zero():
            nonlocal call_count
            call_count += 1
            return 0

        result1 = cache.cached_call("test_zero", returns_zero, duration_hours=1)
        assert result1 == 0
        assert call_count == 1

        result2 = cache.cached_call("test_zero", returns_zero, duration_hours=1)
        assert result2 == 0
        assert call_count == 1


class TestCacheDuration:
    def test_duration_hours_zero_means_no_cache(self, tmp_path, monkeypatch):
        """duration_hours=0 should not fall back to default — it means no caching."""
        cache = _get_cache_module()
        monkeypatch.setattr(cache._cache_manager, "cache_dir", tmp_path)
        monkeypatch.setattr(cache.settings.pipeline, "use_caching", True)

        call_count = 0

        def returns_value():
            nonlocal call_count
            call_count += 1
            return "value"

        cache.cached_call("test_zero_dur", returns_value, duration_hours=0)
        cache.cached_call("test_zero_dur", returns_value, duration_hours=0)

        assert call_count == 2

    def test_duration_hours_none_falls_back_to_default(self, tmp_path, monkeypatch):
        cache = _get_cache_module()
        monkeypatch.setattr(cache._cache_manager, "cache_dir", tmp_path)
        monkeypatch.setattr(cache.settings.pipeline, "use_caching", True)
        monkeypatch.setattr(cache.settings.pipeline, "cache_duration_hours", 24)

        call_count = 0

        def returns_value():
            nonlocal call_count
            call_count += 1
            return "value"

        result = cache.cached_call("test_none_dur", returns_value, duration_hours=None)
        assert result == "value"
        assert call_count == 1

        result2 = cache.cached_call("test_none_dur", returns_value, duration_hours=None)
        assert result2 == "value"
        assert call_count == 1


class TestCacheSerialization:
    def test_dataframe_cached_as_parquet(self, tmp_path, monkeypatch):
        cache = _get_cache_module()
        monkeypatch.setattr(cache._cache_manager, "cache_dir", tmp_path)
        monkeypatch.setattr(cache.settings.pipeline, "use_caching", True)

        df = pd.DataFrame([{"x": 1, "y": "a"}])
        cache.cached_call("df_cache", lambda: df, duration_hours=1)

        key = cache._cache_manager._get_cache_key("df_cache")
        assert (tmp_path / f"{key}.parquet").exists()
        assert not (tmp_path / f"{key}.pkl").exists()

    def test_scalar_cached_as_json(self, tmp_path, monkeypatch):
        cache = _get_cache_module()
        monkeypatch.setattr(cache._cache_manager, "cache_dir", tmp_path)
        monkeypatch.setattr(cache.settings.pipeline, "use_caching", True)

        cache.cached_call("scalar_cache", lambda: 42, duration_hours=1)
        key = cache._cache_manager._get_cache_key("scalar_cache")

        assert (tmp_path / f"{key}.json").exists()
        assert not (tmp_path / f"{key}.pkl").exists()

    def test_legacy_pickle_still_loads(self, tmp_path, monkeypatch):
        cache = _get_cache_module()
        monkeypatch.setattr(cache._cache_manager, "cache_dir", tmp_path)
        monkeypatch.setattr(cache.settings.pipeline, "use_caching", True)

        key = cache._cache_manager._get_cache_key("legacy_cache")
        with open(tmp_path / f"{key}.pkl", "wb") as f:
            pickle.dump({"legacy": True}, f)

        result = cache.cached_call("legacy_cache", lambda: {"legacy": False}, duration_hours=1)
        assert result == {"legacy": True}
