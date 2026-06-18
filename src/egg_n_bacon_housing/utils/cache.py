"""
Caching layer for API calls and expensive operations.

SECURITY NOTE: Cache files may contain API response data including geocoding
results and dataset contents. Ensure cache directories are gitignored and
not exposed in production.

This module provides a simple file-based caching system to speed up development
and reduce API quota usage.
"""

import hashlib
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

_CACHE_MISS = object()


class CacheManager:
    """File-based cache manager for API responses and computed results."""

    def __init__(
        self,
        cache_dir: Path,
        use_caching: bool = True,
        allow_legacy_pickle: bool = False,
        cache_duration_hours: int = 24,
    ):
        """Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files.
            use_caching: Whether caching is enabled.
            allow_legacy_pickle: Whether to read legacy .pkl cache files.
            cache_duration_hours: Default cache validity duration.
        """
        self.cache_dir = cache_dir
        self.use_caching = use_caching
        self.allow_legacy_pickle = allow_legacy_pickle
        self.cache_duration_hours = cache_duration_hours
        if self.use_caching:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, identifier: str) -> str:
        return hashlib.sha256(identifier.encode()).hexdigest()

    def _cache_paths(self, cache_key: str) -> dict[str, Path]:
        """Return paths for supported cache formats."""
        return {
            "json": self.cache_dir / f"{cache_key}.json",
            "parquet": self.cache_dir / f"{cache_key}.parquet",
            "pickle": self.cache_dir / f"{cache_key}.pkl",
        }

    def _get_existing_cache_path(self, cache_key: str) -> Path | None:
        """Return first existing cache path, preferring safe formats."""
        paths = self._cache_paths(cache_key)
        ordered_keys = ["json", "parquet"]
        if self.allow_legacy_pickle:
            ordered_keys.append("pickle")
        for key in ordered_keys:
            path = paths[key]
            if path.exists():
                return path
        return None

    def _is_expired(self, cache_path: Path | None, duration_hours: int) -> bool:
        if cache_path is None or not cache_path.exists():
            return True
        file_age = datetime.now(tz=UTC) - datetime.fromtimestamp(cache_path.stat().st_mtime, tz=UTC)
        return file_age > timedelta(hours=duration_hours)

    def get(self, identifier: str, duration_hours: int | None = None) -> Any:
        """Retrieve a cached value.

        Returns ``_CACHE_MISS`` sentinel if not found, expired, or caching disabled.
        """
        if not self.use_caching:
            logger.debug("Caching is disabled")
            return _CACHE_MISS

        effective_duration = (
            duration_hours if duration_hours is not None else self.cache_duration_hours
        )

        cache_key = self._get_cache_key(identifier)
        cache_path = self._get_existing_cache_path(cache_key)

        if self._is_expired(cache_path, effective_duration):
            logger.debug("Cache miss or expired: %s...", identifier[:100])
            return _CACHE_MISS

        assert cache_path is not None

        try:
            if cache_path.suffix == ".json":
                with open(cache_path, encoding="utf-8") as f:
                    value = json.load(f)
            elif cache_path.suffix == ".parquet":
                value = pd.read_parquet(cache_path)
            else:
                logger.warning("Legacy pickle cache disabled: %s", cache_path)
                return _CACHE_MISS
            logger.info("Cache hit: %s...", identifier[:100])
            return value
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to load cache: %s", e)
            return _CACHE_MISS

    def set(self, identifier: str, value: Any) -> None:
        """Store a value in cache."""
        if not self.use_caching:
            return

        cache_key = self._get_cache_key(identifier)
        cache_paths = self._cache_paths(cache_key)
        json_path = cache_paths["json"]
        parquet_path = cache_paths["parquet"]

        try:
            if hasattr(value, "to_parquet") and callable(value.to_parquet):
                value.to_parquet(parquet_path, index=False)
            else:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(value, f)
            logger.info("Cached: %s...", identifier[:100])
        except (OSError, TypeError, ValueError) as e:
            logger.warning("Failed to cache value: %s", e)

    def clear(self, identifier: str | None = None) -> None:
        """Clear cache entries."""
        if identifier:
            cache_key = self._get_cache_key(identifier)
            paths = self._cache_paths(cache_key)
            deleted_any = False
            for path in paths.values():
                if path.exists():
                    path.unlink()
                    deleted_any = True
            if deleted_any:
                logger.info("Cleared cache: %s...", identifier[:100])
        else:
            for pattern in ("*.json", "*.parquet", "*.pkl"):
                for cache_file in self.cache_dir.glob(pattern):
                    cache_file.unlink()
            logger.info("Cleared all cache files")

    def get_stats(self) -> dict:
        """Get cache statistics."""
        cache_files: list[Path] = []
        for pattern in ("*.json", "*.parquet", "*.pkl"):
            cache_files.extend(self.cache_dir.glob(pattern))

        if not cache_files:
            return {"count": 0, "total_size_mb": 0, "oldest": None, "newest": None}

        total_size = sum(f.stat().st_size for f in cache_files)
        mtimes = [datetime.fromtimestamp(f.stat().st_mtime, tz=UTC) for f in cache_files]

        return {
            "count": len(cache_files),
            "total_size_mb": round(total_size / 1024**2, 2),
            "oldest": min(mtimes).isoformat(),
            "newest": max(mtimes).isoformat(),
        }


_cache_manager: CacheManager | None = None


def configure(
    cache_dir: Path,
    use_caching: bool = True,
    allow_legacy_pickle: bool = False,
    cache_duration_hours: int = 24,
) -> CacheManager:
    """Set up the global cache manager (call once at startup)."""
    global _cache_manager
    _cache_manager = CacheManager(
        cache_dir=cache_dir,
        use_caching=use_caching,
        allow_legacy_pickle=allow_legacy_pickle,
        cache_duration_hours=cache_duration_hours,
    )
    return _cache_manager


def get_cache_manager() -> CacheManager:
    """Return the configured cache manager, raising if not yet configured."""
    if _cache_manager is None:
        raise RuntimeError(
            "Cache not configured. Call egg_n_bacon_housing.utils.cache.configure() first."
        )
    return _cache_manager


def cached_call(
    identifier: str,
    func: Callable,
    duration_hours: int | None = None,
) -> Any:
    """Execute a function with caching.

    Falls back to direct execution (no caching) if the cache manager is not
    configured. This allows callers to use ``cached_call`` without worrying
    about configuration — tests and analytics scripts that don't call
    ``configure()`` simply skip caching.

    Args:
        identifier: Cache identifier (e.g., URL, function name + args)
        func: Function to execute if cache miss
        duration_hours: Cache duration (defaults to manager's configured value)

    Returns:
        Function result (from cache or freshly computed)
    """
    if _cache_manager is None:
        return func()
    cached_value = _cache_manager.get(identifier, duration_hours)
    if cached_value is not _CACHE_MISS:
        return cached_value

    result = func()
    _cache_manager.set(identifier, result)
    return result


def clear_cache(identifier: str | None = None) -> None:
    """Clear cache entries."""
    get_cache_manager().clear(identifier)


def get_cache_stats() -> dict:
    """Get cache statistics."""
    return get_cache_manager().get_stats()
