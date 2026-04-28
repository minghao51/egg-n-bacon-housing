"""
Caching layer for API calls and expensive operations.

This module provides a simple file-based caching system to speed up development
and reduce API quota usage.
"""

import hashlib
import json
import logging
import pickle
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any

from egg_n_bacon_housing.config import settings

logger = logging.getLogger(__name__)

_CACHE_MISS = object()


class CacheManager:
    """File-based cache manager for API responses and computed results."""

    def __init__(self, cache_dir: Path | None = None):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files (defaults to settings.data_dir / "cache")
        """
        self.cache_dir = cache_dir or settings.data_dir / "cache"
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

    def _cache_paths(self, cache_key: str) -> dict[str, Path]:
        """Return paths for supported cache formats."""
        return {
            "json": self.cache_dir / f"{cache_key}.json",
            "parquet": self.cache_dir / f"{cache_key}.parquet",
            "pickle": self.cache_dir / f"{cache_key}.pkl",  # legacy fallback only
        }

    def _get_existing_cache_path(self, cache_key: str) -> Path | None:
        """Return first existing cache path, preferring safe formats."""
        paths = self._cache_paths(cache_key)
        for key in ["json", "parquet", "pickle"]:
            path = paths[key]
            if path.exists():
                return path
        return None

    def _is_expired(self, cache_path: Path | None, duration_hours: int) -> bool:
        """
        Check if a cache file has expired.

        Args:
            cache_path: Path to cache file
            duration_hours: Cache duration in hours

        Returns:
            True if cache is expired or doesn't exist
        """
        if cache_path is None or not cache_path.exists():
            return True

        file_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        return file_age > timedelta(hours=duration_hours)

    def get(self, identifier: str, duration_hours: int = 24) -> Any:
        """
        Retrieve a cached value.

        Args:
            identifier: Cache identifier (e.g., URL, function name + args)
            duration_hours: How long cache is valid (default from settings.pipeline.cache_duration_hours)

        Returns:
            Cached value, or _CACHE_MISS sentinel if not found/expired
        """
        if not settings.pipeline.use_caching:
            logger.debug("Caching is disabled")
            return _CACHE_MISS

        cache_key = self._get_cache_key(identifier)
        cache_path = self._get_existing_cache_path(cache_key)

        if self._is_expired(cache_path, duration_hours):
            logger.debug(f"Cache miss or expired: {identifier[:100]}...")
            return _CACHE_MISS

        assert cache_path is not None

        try:
            if cache_path.suffix == ".json":
                with open(cache_path, encoding="utf-8") as f:
                    value = json.load(f)
            elif cache_path.suffix == ".parquet":
                import pandas as pd

                value = pd.read_parquet(cache_path)
            else:
                with open(cache_path, "rb") as f:
                    value = pickle.load(f)
            logger.info(f"Cache hit: {identifier[:100]}...")
            return value
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return _CACHE_MISS

    def set(self, identifier: str, value: Any) -> None:
        """
        Store a value in cache.

        Args:
            identifier: Cache identifier
            value: Value to cache (must be pickle-able)
        """
        if not settings.pipeline.use_caching:
            return

        cache_key = self._get_cache_key(identifier)
        cache_paths = self._cache_paths(cache_key)
        json_path = cache_paths["json"]
        parquet_path = cache_paths["parquet"]

        try:
            if hasattr(value, "to_parquet") and callable(value.to_parquet):
                # DataFrame-like payloads: use parquet instead of pickle.
                value.to_parquet(parquet_path, index=False)
            else:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(value, f)
            logger.info(f"Cached: {identifier[:100]}...")
        except Exception as e:
            logger.warning(f"Failed to cache value: {e}")

    def clear(self, identifier: str | None = None) -> None:
        """
        Clear cache entries.

        Args:
            identifier: Specific cache entry to clear, or None to clear all
        """
        if identifier:
            cache_key = self._get_cache_key(identifier)
            paths = self._cache_paths(cache_key)
            deleted_any = False
            for path in paths.values():
                if path.exists():
                    path.unlink()
                    deleted_any = True
            if deleted_any:
                logger.info(f"Cleared cache: {identifier[:100]}...")
        else:
            for pattern in ("*.json", "*.parquet", "*.pkl"):
                for cache_file in self.cache_dir.glob(pattern):
                    cache_file.unlink()
            logger.info("Cleared all cache files")

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (count, total size, oldest/newest)
        """
        cache_files: list[Path] = []
        for pattern in ("*.json", "*.parquet", "*.pkl"):
            cache_files.extend(self.cache_dir.glob(pattern))

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


_cache_manager = CacheManager()


def cached_call(
    identifier: str,
    func: Callable,
    duration_hours: int | None = None,
) -> Any:
    """
    Execute a function with caching.

    Args:
        identifier: Cache identifier (e.g., URL, function name + args)
        func: Function to execute if cache miss
        duration_hours: Cache duration (defaults to settings.pipeline.cache_duration_hours)

    Returns:
        Function result (from cache or freshly computed)

    Example:
        >>> result = cached_call("api_call_123", lambda: requests.get(url))
    """
    duration = settings.pipeline.cache_duration_hours if duration_hours is None else duration_hours

    cached_value = _cache_manager.get(identifier, duration)
    if cached_value is not _CACHE_MISS:
        return cached_value

    result = func()

    _cache_manager.set(identifier, result)

    return result


def cached_api_call(
    url: str,
    params: dict | None = None,
    method: str = "GET",
    duration_hours: int | None = None,
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
            cache_id = f"{method}:{url}:{json.dumps(params or {})} "
            duration = (
                settings.pipeline.cache_duration_hours if duration_hours is None else duration_hours
            )

            cached_value = _cache_manager.get(cache_id, duration)
            if cached_value is not _CACHE_MISS:
                return cached_value

            result = func(*args, **kwargs)

            _cache_manager.set(cache_id, result)

            return result

        return wrapper

    return decorator


def clear_cache(identifier: str | None = None) -> None:
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
