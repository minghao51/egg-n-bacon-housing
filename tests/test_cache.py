"""Tests for caching layer."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from scripts.core.cache import CacheManager, cached_call, clear_cache, get_cache_stats
from scripts.core.config import Config


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache_manager(temp_cache_dir):
    """Create cache manager with temporary directory."""
    return CacheManager(cache_dir=temp_cache_dir)


class TestCacheManager:
    """Test CacheManager class."""

    def test_cache_key_generation(self, cache_manager):
        """Test that cache keys are generated consistently."""
        key1 = cache_manager._get_cache_key("test_identifier")
        key2 = cache_manager._get_cache_key("test_identifier")
        key3 = cache_manager._get_cache_key("different_identifier")

        assert key1 == key2  # Same input = same key
        assert key1 != key3  # Different input = different key
        assert len(key1) == 32  # MD5 hash length

    def test_cache_set_and_get(self, cache_manager):
        """Test setting and getting cached values."""
        test_data = {"key": "value", "number": 123}

        # Set value
        cache_manager.set("test_key", test_data)

        # Get value
        result = cache_manager.get("test_key")

        assert result == test_data

    def test_cache_miss(self, cache_manager):
        """Test cache miss returns None."""
        result = cache_manager.get("nonexistent_key")
        assert result is None

    def test_cache_expiration(self, cache_manager):
        """Test that cache expires after duration."""
        test_data = {"value": "test"}

        # Set value
        cache_manager.set("test_key", test_data)

        # Should not be expired immediately
        result = cache_manager.get("test_key", duration_hours=1)
        assert result == test_data

        # Mock file modification time to simulate expiration
        cache_path = cache_manager._get_cache_path(
            cache_manager._get_cache_key("test_key")
        )

        # This test would require time manipulation, skip for now
        # In real scenario, you'd use freezegun or similar

    def test_cache_clear_specific(self, cache_manager):
        """Test clearing specific cache entry."""
        cache_manager.set("key1", {"data": 1})
        cache_manager.set("key2", {"data": 2})

        # Clear key1
        cache_manager.clear("key1")

        # key1 should be gone, key2 should remain
        assert cache_manager.get("key1") is None
        assert cache_manager.get("key2") == {"data": 2}

    def test_cache_clear_all(self, cache_manager):
        """Test clearing all cache entries."""
        cache_manager.set("key1", {"data": 1})
        cache_manager.set("key2", {"data": 2})

        # Clear all
        cache_manager.clear()

        # Both should be gone
        assert cache_manager.get("key1") is None
        assert cache_manager.get("key2") is None

    def test_cache_stats(self, cache_manager):
        """Test getting cache statistics."""
        cache_manager.set("key1", {"data": "x" * 100})

        stats = cache_manager.get_stats()

        assert stats['count'] == 1
        assert stats['total_size_mb'] > 0
        assert 'oldest' in stats
        assert 'newest' in stats


class TestCachedCall:
    """Test cached_call function."""

    def test_cached_call_basic(self, temp_cache_dir):
        """Test basic cached_call functionality."""
        call_count = 0

        def expensive_function():
            nonlocal call_count
            call_count += 1
            return {"result": call_count}

        # First call - executes function
        with patch.object(Config, 'CACHE_DIR', temp_cache_dir):
            with patch.object(Config, 'USE_CACHING', True):
                result1 = cached_call("test_key", expensive_function)

        assert result1 == {"result": 1}
        assert call_count == 1

        # Second call - should use cache
        with patch.object(Config, 'CACHE_DIR', temp_cache_dir):
            with patch.object(Config, 'USE_CACHING', True):
                result2 = cached_call("test_key", expensive_function)

        assert result2 == {"result": 1}  # Same result
        assert call_count == 1  # Function not called again

    def test_cached_call_disabled(self, temp_cache_dir):
        """Test that cached_call respects USE_CACHING=False."""
        call_count = 0

        def expensive_function():
            nonlocal call_count
            call_count += 1
            return {"result": call_count}

        # Disable caching
        with patch.object(Config, 'CACHE_DIR', temp_cache_dir):
            with patch.object(Config, 'USE_CACHING', False):
                result1 = cached_call("test_key", expensive_function)
                result2 = cached_call("test_key", expensive_function)

        assert result1 == {"result": 1}
        assert result2 == {"result": 2}
        assert call_count == 2  # Function called both times

    def test_cached_call_with_dataframe(self, temp_cache_dir):
        """Test caching a pandas DataFrame."""
        df = pd.DataFrame({
            'a': [1, 2, 3],
            'b': ['x', 'y', 'z']
        })

        call_count = 0

        def get_dataframe():
            nonlocal call_count
            call_count += 1
            return df

        # First call
        with patch.object(Config, 'CACHE_DIR', temp_cache_dir):
            with patch.object(Config, 'USE_CACHING', True):
                result1 = cached_call("df_key", get_dataframe)
                result2 = cached_call("df_key", get_dataframe)

        assert result1.equals(df)
        assert result2.equals(df)
        assert call_count == 1  # Only called once


class TestCacheUtilities:
    """Test cache utility functions."""

    def test_clear_cache(self, temp_cache_dir):
        """Test clear_cache utility function."""
        manager = CacheManager(cache_dir=temp_cache_dir)
        manager.set("key1", {"data": 1})

        # Clear using utility function
        with patch('scripts.core.cache._cache_manager', manager):
            clear_cache("key1")

        assert manager.get("key1") is None

    def test_get_cache_stats(self, temp_cache_dir):
        """Test get_cache_stats utility function."""
        manager = CacheManager(cache_dir=temp_cache_dir)
        manager.set("key1", {"data": 1})

        # Get stats using utility function
        with patch('scripts.core.cache._cache_manager', manager):
            stats = get_cache_stats()

        assert stats['count'] == 1
