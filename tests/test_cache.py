"""Tests for the explicit-injection file cache."""

import os
import time

import pandas as pd
import pytest

from egg_n_bacon_housing.utils.cache import CacheManager, cached_call

pytestmark = pytest.mark.unit


def test_explicit_managers_do_not_share_roots(tmp_path):
    first = CacheManager(tmp_path / "first")
    second = CacheManager(tmp_path / "second")
    assert cached_call("same", lambda: "first", cache_manager=first) == "first"
    assert cached_call("same", lambda: "second", cache_manager=second) == "second"


def test_manager_configuration_is_immutable(tmp_path):
    manager = CacheManager(tmp_path)
    with pytest.raises(AttributeError, match="configuration is immutable"):
        manager.cache_dir = tmp_path / "elsewhere"


@pytest.mark.parametrize("value", [pd.DataFrame(), None, 0])
def test_cached_call_stores_falsy_values(tmp_path, value):
    manager = CacheManager(tmp_path)
    calls = 0

    def produce():
        nonlocal calls
        calls += 1
        return value

    first = cached_call("value", produce, cache_manager=manager)
    second = cached_call("value", produce, cache_manager=manager)
    if isinstance(value, pd.DataFrame):
        assert first.empty and second.empty
    else:
        assert first == second == value
    assert calls == 1


def test_duration_zero_always_misses(tmp_path):
    manager = CacheManager(tmp_path)
    calls = 0

    def produce():
        nonlocal calls
        calls += 1
        return "value"

    cached_call("zero", produce, duration_hours=0, cache_manager=manager)
    cached_call("zero", produce, duration_hours=0, cache_manager=manager)
    assert calls == 2


def test_dataframe_and_scalar_serialization(tmp_path):
    manager = CacheManager(tmp_path)
    manager.set("df", pd.DataFrame([{"x": 1}]))
    manager.set("scalar", {"answer": 42})
    assert isinstance(manager.get("df"), pd.DataFrame)
    assert manager.get("scalar") == {"answer": 42}
    assert any(tmp_path.glob("*.parquet"))
    assert any(tmp_path.glob("*.json"))


def test_legacy_pickle_files_are_never_read(tmp_path):
    manager = CacheManager(tmp_path)
    key = manager._get_cache_key("legacy")
    (tmp_path / f"{key}.pkl").write_bytes(b"legacy")
    result = cached_call("legacy", lambda: {"fresh": True}, cache_manager=manager)
    assert result == {"fresh": True}


def test_atomic_writes_remove_temporary_files_and_sibling_formats(tmp_path):
    manager = CacheManager(tmp_path)
    manager.set("same", {"old": True})
    manager.set("same", pd.DataFrame([{"x": 1}]))
    assert not list(tmp_path.glob("*.tmp"))
    key = manager._get_cache_key("same")
    assert (tmp_path / f"{key}.parquet").exists()
    assert not (tmp_path / f"{key}.json").exists()


def test_expired_entry_is_unlinked(tmp_path):
    manager = CacheManager(tmp_path)
    manager.set("expiring", "stale")
    key = manager._get_cache_key("expiring")
    path = tmp_path / f"{key}.json"
    stale = time.time() - 2 * 3600
    os.utime(path, (stale, stale))
    result = manager.get("expiring", duration_hours=1)
    assert result is not None
    assert not path.exists()
