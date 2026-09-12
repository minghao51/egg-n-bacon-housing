"""Tests for the explicit-injection file cache."""

import errno
import os
import threading
import time
from pathlib import Path

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


def test_is_expired_survives_file_vanishing_between_probe_and_stat(tmp_path, monkeypatch):
    """A concurrently removed entry must read as a miss, not crash ``get()``."""
    manager = CacheManager(tmp_path)
    vanished = tmp_path / "vanished.parquet"
    vanished.touch()
    real_exists, real_stat = Path.exists, Path.stat

    def fake_exists(self):
        return True if self == vanished else real_exists(self)

    def fake_stat(self, **kwargs):
        if self == vanished:
            raise FileNotFoundError(errno.ENOENT, "vanished concurrently", str(self))
        return real_stat(self, **kwargs)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "stat", fake_stat)
    assert manager._is_expired(vanished, duration_hours=24) is True


def test_concurrent_writers_of_same_key_do_not_collide(tmp_path, caplog):
    """Parallel ``set()`` calls on one key must all succeed without warnings."""
    import logging as _logging

    manager = CacheManager(tmp_path)
    frame = pd.DataFrame({"x": range(10)})
    with caplog.at_level(_logging.WARNING, logger="egg_n_bacon_housing.utils.cache"):
        threads = [threading.Thread(target=manager.set, args=("shared", frame)) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert not [record for record in caplog.records if record.levelname == "WARNING"]
    assert not list(tmp_path.glob("*.tmp"))
    assert len(pd.read_parquet(next(tmp_path.glob("*.parquet")))) == 10


def test_clear_all_sweeps_atomic_write_tmp_orphans(tmp_path):
    """A full clear() removes every cache file, including tmp orphans.

    Covers both the legacy fixed-name ``<key>.json.tmp`` form and the
    pid+thread-unique ``<key>.json.<pid>-<tid>.tmp`` form left behind by
    crashed writers (roadmap item 25 remainder).
    """
    manager = CacheManager(tmp_path)
    legacy_orphan = tmp_path / "some-key.json.tmp"
    legacy_orphan.write_text("{}")
    crashed_orphan = tmp_path / "other-key.json.99999-123.tmp"
    crashed_orphan.write_text("{}")
    live_entry = tmp_path / "real.json"
    live_entry.write_text("{}")

    manager.clear()

    assert not legacy_orphan.exists()
    assert not crashed_orphan.exists()
    assert not live_entry.exists()
    assert list(tmp_path.glob("*.tmp")) == []
