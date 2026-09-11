"""
Caching layer for API calls and expensive operations.

SECURITY NOTE: Cache files may contain API response data including geocoding
results and dataset contents. Ensure cache directories are gitignored and
not exposed in production.

This module provides a simple file-based caching system to speed up development
and reduce API quota usage.

Versioning convention (go-forward): embed a caller-owned version in cache
identifiers, e.g. ``cached_call("datagovsg:v2:{dataset_id}", ...)``. Bump the
version segment whenever the parse/transform behavior of the producing code
changes, so stale entries written under the old shape are never read back.
Existing identifiers are NOT being renamed retroactively — mass invalidation
without a behavioral change is not justified.
"""

import hashlib
import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

_CACHE_MISS = object()


@dataclass
class CacheManager:
    """File-based cache manager for API responses and computed results."""

    cache_dir: Path
    use_caching: bool = True
    cache_duration_hours: int = 24
    _configuration_locked: bool = field(default=False, init=False, repr=False)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in {
            "cache_dir",
            "use_caching",
            "cache_duration_hours",
        } and getattr(self, "_configuration_locked", False):
            raise AttributeError(f"CacheManager configuration is immutable: {name}")
        super().__setattr__(name, value)

    def __post_init__(self) -> None:
        """Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files.
            use_caching: Whether caching is enabled.
            cache_duration_hours: Default cache validity duration.
        """
        if self.use_caching:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._configuration_locked = True

    def _get_cache_key(self, identifier: str) -> str:
        return hashlib.sha256(identifier.encode()).hexdigest()

    def _cache_paths(self, cache_key: str) -> dict[str, Path]:
        """Return paths for supported cache formats."""
        return {
            "json": self.cache_dir / f"{cache_key}.json",
            "parquet": self.cache_dir / f"{cache_key}.parquet",
        }

    def _get_existing_cache_path(self, cache_key: str) -> Path | None:
        """Return first existing cache path, preferring safe formats."""
        for path in self._cache_paths(cache_key).values():
            if path.exists():
                return path
        return None

    def _is_expired(self, cache_path: Path | None, duration_hours: int) -> bool:
        if cache_path is None or not cache_path.exists():
            return True
        file_age = datetime.now(tz=UTC) - datetime.fromtimestamp(cache_path.stat().st_mtime, tz=UTC)
        return file_age > timedelta(hours=duration_hours)

    @staticmethod
    def _unlink_best_effort(path: Path) -> None:
        """Remove ``path`` if present; stale-cache cleanup must never raise."""
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.debug("Could not remove cache file: %s", path)

    def get(self, identifier: str, duration_hours: int | None = None) -> Any:
        """Retrieve a cached value.

        Returns ``_CACHE_MISS`` sentinel if not found, expired, or caching disabled.
        Expired entries are unlinked (best-effort) so they cannot shadow future writes.
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
            if cache_path is not None:
                self._unlink_best_effort(cache_path)
            return _CACHE_MISS

        assert cache_path is not None

        try:
            if cache_path.suffix == ".json":
                with open(cache_path, encoding="utf-8") as f:
                    value = json.load(f)
            elif cache_path.suffix == ".parquet":
                value = pd.read_parquet(cache_path)
            else:
                logger.warning("Unsupported cache format: %s", cache_path)
                return _CACHE_MISS
            logger.info("Cache hit: %s...", identifier[:100])
            return value
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.warning("Failed to load cache: %s", e)
            return _CACHE_MISS

    def set(self, identifier: str, value: Any) -> None:
        """Store a value in cache.

        Writes are atomic (temp file + ``os.replace``) so a crash mid-write can
        never leave a truncated entry that reads as a permanent miss. The
        sibling-format path for the same key is removed to prevent a stale
        json/parquet shadowing the fresh entry.
        """
        if not self.use_caching:
            return

        cache_key = self._get_cache_key(identifier)
        cache_paths = self._cache_paths(cache_key)
        json_path = cache_paths["json"]
        parquet_path = cache_paths["parquet"]

        try:
            if hasattr(value, "to_parquet") and callable(value.to_parquet):
                self._atomic_write(parquet_path, lambda p: value.to_parquet(p, index=False))
                self._unlink_best_effort(json_path)
            else:

                def _write_json(path: Path) -> None:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(value, f)

                self._atomic_write(json_path, _write_json)
                self._unlink_best_effort(parquet_path)
            logger.info("Cached: %s...", identifier[:100])
        except (OSError, TypeError, ValueError) as e:
            logger.warning("Failed to cache value: %s", e)

    @staticmethod
    def _atomic_write(path: Path, write: Callable[[Path], None]) -> None:
        """Write through a ``.tmp`` sibling, then atomically replace ``path``."""
        tmp_path = path.with_name(path.name + ".tmp")
        write(tmp_path)
        os.replace(tmp_path, path)

    def cached_call(
        self,
        identifier: str,
        func: Callable,
        duration_hours: int | None = None,
    ) -> Any:
        """Execute ``func`` on a cache miss using this manager."""
        cached_value = self.get(identifier, duration_hours)
        if cached_value is not _CACHE_MISS:
            return cached_value
        result = func()
        self.set(identifier, result)
        return result

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
            # *.pkl is kept in the sweep so legacy pickle files from removed
            # behavior are still cleaned up, even though they are never read.
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


def cached_call(
    identifier: str,
    func: Callable,
    duration_hours: int | None = None,
    *,
    cache_manager: CacheManager,
) -> Any:
    """Execute a function with the explicitly injected cache manager.

    Args:
        identifier: Cache identifier (e.g., URL, function name + args). See the
            module docstring for the versioning convention
            (e.g. ``"datagovsg:v2:{dataset_id}"``).
        func: Function to execute if cache miss
        duration_hours: Cache duration (defaults to manager's configured value)

    Returns:
        Function result (from cache or freshly computed)
    """
    return cache_manager.cached_call(identifier, func, duration_hours)
