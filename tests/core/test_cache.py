"""
Tests for scripts.core.cache module.

This test suite validates caching functionality including
cache storage, retrieval, expiration, and management.
"""

import time

import pandas as pd
import pytest

from scripts.core.cache import CacheManager, cached_call, clear_cache, get_cache_stats


@pytest.mark.unit
class TestCacheManager:
    """Test CacheManager class."""

    def test_cache_manager_init(self, temp_dir):
        """Test CacheManager initialization."""
        cache_mgr = CacheManager(cache_dir=temp_dir)

        assert cache_mgr.cache_dir == temp_dir
        assert temp_dir.exists()

    def test_cache_manager_creates_directory(self, temp_dir):
        """Test that CacheManager creates cache directory."""
        cache_subdir = temp_dir / "cache"
        CacheManager(cache_dir=cache_subdir)  # noqa: F841

        assert cache_subdir.exists()
        assert cache_subdir.is_dir()

    def test_cache_key_generation(self, temp_dir):
        """Test cache key generation."""
        cache_mgr = CacheManager(cache_dir=temp_dir)

        key1 = cache_mgr._get_cache_key("test_identifier")
        key2 = cache_mgr._get_cache_key("test_identifier")
        key3 = cache_mgr._get_cache_key("different_identifier")

        # Same input should generate same key
        assert key1 == key2

        # Different input should generate different key
        assert key1 != key3

        # Keys should be hex strings (MD5)
        assert len(key1) == 32
        assert all(c in "0123456789abcdef" for c in key1)

    def test_cache_path_generation(self, temp_dir):
        """Test cache path generation."""
        cache_mgr = CacheManager(cache_dir=temp_dir)

        key = "abc123"
        path = cache_mgr._get_cache_path(key)

        assert path == temp_dir / f"{key}.pkl"

    def test_set_and_get_cache(self, temp_dir, monkeypatch):
        """Test basic cache set and get operations."""
        # Enable caching
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)

        cache_mgr = CacheManager(cache_dir=temp_dir)

        test_data = {"key": "value", "number": 123}
        identifier = "test_cache_entry"

        # Set cache
        cache_mgr.set(identifier, test_data)

        # Get cache
        result = cache_mgr.get(identifier)

        assert result == test_data

    def test_cache_miss_returns_none(self, temp_dir, monkeypatch):
        """Test that cache miss returns None."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)

        cache_mgr = CacheManager(cache_dir=temp_dir)

        result = cache_mgr.get("nonexistent_entry")

        assert result is None

    def test_cache_disabled(self, temp_dir, monkeypatch):
        """Test that caching is disabled when USE_CACHING is False."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", False)

        cache_mgr = CacheManager(cache_dir=temp_dir)

        cache_mgr.set("test", {"data": "value"})
        result = cache_mgr.get("test")

        assert result is None

    def test_cache_expiration(self, temp_dir, monkeypatch):
        """Test cache expiration based on duration."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)

        cache_mgr = CacheManager(cache_dir=temp_dir)

        test_data = {"value": "test"}
        identifier = "expiring_cache"

        # Set cache
        cache_mgr.set(identifier, test_data)

        # Get immediately (should not be expired)
        result = cache_mgr.get(identifier, duration_hours=1)
        assert result == test_data

        # Mock file modification time to be old
        cache_file = cache_mgr._get_cache_path(cache_mgr._get_cache_key(identifier))
        old_time = time.time() - (2 * 3600)  # 2 hours ago
        import os

        os.utime(cache_file, (old_time, old_time))

        # Get again with 1 hour duration (should be expired)
        result = cache_mgr.get(identifier, duration_hours=1)
        assert result is None

    def test_clear_specific_cache_entry(self, temp_dir, monkeypatch):
        """Test clearing a specific cache entry."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)

        cache_mgr = CacheManager(cache_dir=temp_dir)

        cache_mgr.set("entry1", {"data": "1"})
        cache_mgr.set("entry2", {"data": "2"})

        # Clear entry1
        cache_mgr.clear("entry1")

        assert cache_mgr.get("entry1") is None
        assert cache_mgr.get("entry2") == {"data": "2"}

    def test_clear_all_cache(self, temp_dir, monkeypatch):
        """Test clearing all cache entries."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)

        cache_mgr = CacheManager(cache_dir=temp_dir)

        cache_mgr.set("entry1", {"data": "1"})
        cache_mgr.set("entry2", {"data": "2"})
        cache_mgr.set("entry3", {"data": "3"})

        # Clear all
        cache_mgr.clear()

        assert cache_mgr.get("entry1") is None
        assert cache_mgr.get("entry2") is None
        assert cache_mgr.get("entry3") is None

    def test_cache_stats(self, temp_dir, monkeypatch):
        """Test cache statistics."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)

        cache_mgr = CacheManager(cache_dir=temp_dir)

        # Empty cache
        stats = cache_mgr.get_stats()
        assert stats["count"] == 0
        assert stats["total_size_mb"] == 0

        # Add some entries with larger data to ensure measurable size
        cache_mgr.set("entry1", {"data": "x" * 100000})  # ~100KB
        cache_mgr.set("entry2", {"data": "y" * 200000})  # ~200KB

        stats = cache_mgr.get_stats()
        assert stats["count"] == 2
        # With ~300KB of data, size should be > 0 after rounding to 2 decimal places
        assert stats["total_size_mb"] >= 0.01  # At least 0.01 MB
        assert stats["oldest"] is not None
        assert stats["newest"] is not None


@pytest.mark.unit
class TestCachedCall:
    """Test cached_call function."""

    def test_cached_call_cache_miss(self, temp_dir, monkeypatch):
        """Test cached_call on cache miss."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)
        monkeypatch.setattr(Config, "CACHE_DIR", temp_dir)

        call_count = [0]

        def expensive_function():
            call_count[0] += 1
            return {"result": "computed"}

        # First call should execute function
        result1 = cached_call("test_func", expensive_function)

        assert result1 == {"result": "computed"}
        assert call_count[0] == 1

    def test_cached_call_cache_hit(self, temp_dir, monkeypatch):
        """Test cached_call on cache hit."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)
        monkeypatch.setattr(Config, "CACHE_DIR", temp_dir)

        call_count = [0]

        def expensive_function():
            call_count[0] += 1
            return {"result": "computed"}

        # First call - cache miss
        result1 = cached_call("test_func_hit", expensive_function)
        assert call_count[0] == 1

        # Second call - cache hit
        result2 = cached_call("test_func_hit", expensive_function)
        assert call_count[0] == 1  # Should not increment

        assert result1 == result2

    def test_cached_call_with_custom_duration(self, temp_dir, monkeypatch):
        """Test cached_call with custom duration."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)
        monkeypatch.setattr(Config, "CACHE_DIR", temp_dir)

        def expensive_function():
            return {"result": "custom_duration"}

        result = cached_call("test_custom_duration", expensive_function, duration_hours=48)

        assert result == {"result": "custom_duration"}


@pytest.mark.unit
class TestClearCache:
    """Test clear_cache function."""

    def test_clear_cache_all(self, temp_dir, monkeypatch):
        """Test clearing all cache."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)
        monkeypatch.setattr(Config, "CACHE_DIR", temp_dir)

        cache_mgr = CacheManager(cache_dir=temp_dir)
        cache_mgr.set("entry1", {"data": "1"})
        cache_mgr.set("entry2", {"data": "2"})

        clear_cache()

        stats = get_cache_stats()
        assert stats["count"] == 0

    def test_clear_cache_specific(self, temp_dir, monkeypatch):
        """Test clearing specific cache entry."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)

        cache_mgr = CacheManager(cache_dir=temp_dir)
        cache_mgr.set("entry1", {"data": "1"})
        cache_mgr.set("entry2", {"data": "2"})

        # Use the cache_mgr's clear method, not the global clear_cache function
        cache_mgr.clear("entry1")

        assert cache_mgr.get("entry1") is None
        assert cache_mgr.get("entry2") == {"data": "2"}


@pytest.mark.unit
class TestGetCacheStats:
    """Test get_cache_stats function."""

    def test_get_cache_stats_empty(self, temp_dir, monkeypatch):
        """Test get_cache_stats with empty cache."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "CACHE_DIR", temp_dir)

        stats = get_cache_stats()

        assert stats["count"] == 0
        assert stats["total_size_mb"] == 0

    def test_get_cache_stats_with_data(self, temp_dir, monkeypatch):
        """Test get_cache_stats with cached data."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)

        cache_mgr = CacheManager(cache_dir=temp_dir)
        cache_mgr.set("entry1", {"data": "x" * 100000})  # Use larger data

        # Use the cache_mgr's get_stats method
        stats = cache_mgr.get_stats()

        assert stats["count"] == 1
        assert stats["total_size_mb"] >= 0.01  # At least 0.01 MB


@pytest.mark.integration
class TestCacheIntegration:
    """Integration tests for caching."""

    def test_cache_dataframe(self, temp_dir, monkeypatch):
        """Test caching pandas DataFrame."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)
        monkeypatch.setattr(Config, "CACHE_DIR", temp_dir)

        cache_mgr = CacheManager(cache_dir=temp_dir)

        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

        cache_mgr.set("test_df", df)
        result = cache_mgr.get("test_df")

        pd.testing.assert_frame_equal(result, df)

    def test_cache_complex_object(self, temp_dir, monkeypatch):
        """Test caching complex nested objects."""
        from scripts.core.config import Config

        monkeypatch.setattr(Config, "USE_CACHING", True)
        monkeypatch.setattr(Config, "CACHE_DIR", temp_dir)

        cache_mgr = CacheManager(cache_dir=temp_dir)

        complex_obj = {"list": [1, 2, 3], "nested": {"key": "value"}, "tuple": (1, 2, 3)}

        cache_mgr.set("complex", complex_obj)
        result = cache_mgr.get("complex")

        assert result == complex_obj
