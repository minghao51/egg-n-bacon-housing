"""
Caching layer for API calls and expensive operations.

This module provides a simple file-based caching system to speed up development
and reduce API quota usage.
"""

import hashlib
import json
import pickle
import logging
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, Union

try:
    from scripts.core.config import Config
except ImportError:
    try:
        from core.config import Config
    except ImportError:
        from config import Config

logger = logging.getLogger(__name__)


class CacheManager:
    """File-based cache manager for API responses and computed results."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files (defaults to Config.CACHE_DIR)
        """
        self.cache_dir = cache_dir or Config.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, identifier: str) -> str:
        """
        Generate a cache key from an identifier.

        Args:
            identifier: String to generate key from (e.g., URL, function name + args)

        Returns:
            MD5 hash of the identifier
        """
        return hashlib.md5(identifier.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """
        Get the file path for a cache entry.

        Args:
            cache_key: Cache key from _get_cache_key()

        Returns:
            Path to cache file
        """
        return self.cache_dir / f"{cache_key}.pkl"

    def _is_expired(self, cache_path: Path, duration_hours: int) -> bool:
        """
        Check if a cache file has expired.

        Args:
            cache_path: Path to cache file
            duration_hours: Cache duration in hours

        Returns:
            True if cache is expired or doesn't exist
        """
        if not cache_path.exists():
            return True

        file_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        return file_age > timedelta(hours=duration_hours)

    def get(self, identifier: str, duration_hours: int = 24) -> Optional[Any]:
        """
        Retrieve a cached value.

        Args:
            identifier: Cache identifier (e.g., URL, function name + args)
            duration_hours: How long cache is valid (default from Config.CACHE_DURATION_HOURS)

        Returns:
            Cached value, or None if not found/expired
        """
        if not Config.USE_CACHING:
            logger.debug("Caching is disabled")
            return None

        cache_key = self._get_cache_key(identifier)
        cache_path = self._get_cache_path(cache_key)

        if self._is_expired(cache_path, duration_hours):
            logger.debug(f"Cache miss or expired: {identifier[:100]}...")
            return None

        try:
            with open(cache_path, "rb") as f:
                value = pickle.load(f)
            logger.info(f"✅ Cache hit: {identifier[:100]}...")
            return value
        except Exception as e:
            logger.warning(f"⚠️  Failed to load cache: {e}")
            return None

    def set(self, identifier: str, value: Any) -> None:
        """
        Store a value in cache.

        Args:
            identifier: Cache identifier
            value: Value to cache (must be pickle-able)
        """
        if not Config.USE_CACHING:
            return

        cache_key = self._get_cache_key(identifier)
        cache_path = self._get_cache_path(cache_key)

        try:
            with open(cache_path, "wb") as f:
                pickle.dump(value, f)
            logger.info(f"💾 Cached: {identifier[:100]}...")
        except Exception as e:
            logger.warning(f"⚠️  Failed to cache value: {e}")

    def clear(self, identifier: Optional[str] = None) -> None:
        """
        Clear cache entries.

        Args:
            identifier: Specific cache entry to clear, or None to clear all
        """
        if identifier:
            cache_key = self._get_cache_key(identifier)
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"🗑️  Cleared cache: {identifier[:100]}...")
        else:
            # Clear all cache files
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            logger.info(f"🗑️  Cleared all cache files")

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (count, total size, oldest/newest)
        """
        cache_files = list(self.cache_dir.glob("*.pkl"))

        if not cache_files:
            return {"count": 0, "total_size_mb": 0, "oldest": None, "newest": None}

        total_size = sum(f.stat().st_size for f in cache_files)
        mtimes = [datetime.fromtimestamp(f.stat().st_mtime) for f in cache_files]

        return {
            "count": len(cache_files),
            "total_size_mb": round(total_size / 1024**2, 2),
            "oldest": min(mtimes).isoformat(),
            "newest": max(mtimes).isoformat(),
        }


# Global cache manager instance
_cache_manager = CacheManager()


def cached_call(
    identifier: str,
    func: Callable,
    duration_hours: Optional[int] = None,
) -> Any:
    """
    Execute a function with caching.

    Args:
        identifier: Cache identifier (e.g., URL, function name + args)
        func: Function to execute if cache miss
        duration_hours: Cache duration (defaults to Config.CACHE_DURATION_HOURS)

    Returns:
        Function result (from cache or freshly computed)

    Example:
        >>> result = cached_call("api_call_123", lambda: requests.get(url))
    """
    duration = duration_hours or Config.CACHE_DURATION_HOURS

    # Try to get from cache
    cached_value = _cache_manager.get(identifier, duration)
    if cached_value is not None:
        return cached_value

    # Cache miss - execute function
    result = func()

    # Store in cache
    _cache_manager.set(identifier, result)

    return result


def cached_api_call(
    url: str,
    params: Optional[dict] = None,
    method: str = "GET",
    duration_hours: Optional[int] = None,
) -> Callable:
    """
    Decorator for caching API calls.

    Args:
        url: API endpoint URL
        params: Query parameters
        method: HTTP method
        duration_hours: Cache duration

    Returns:
        Decorated function

    Example:
        >>> @cached_api_call("https://api.example.com/data", {"param": "value"})
        >>> def fetch_data():
        ...     return requests.get("https://api.example.com/data", params={"param": "value"})
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Create cache identifier
            cache_id = f"{method}:{url}:{json.dumps(params or {})}"
            duration = duration_hours or Config.CACHE_DURATION_HOURS

            # Try cache first
            cached_value = _cache_manager.get(cache_id, duration)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            _cache_manager.set(cache_id, result)

            return result

        return wrapper

    return decorator


def clear_cache(identifier: Optional[str] = None) -> None:
    """
    Clear cache entries.

    Args:
        identifier: Specific entry to clear, or None to clear all

    Example:
        >>> clear_cache()  # Clear all
        >>> clear_cache("api_call_123")  # Clear specific entry
    """
    _cache_manager.clear(identifier)


def get_cache_stats() -> dict:
    """
    Get cache statistics.

    Returns:
        Dictionary with cache stats
    """
    return _cache_manager.get_stats()
