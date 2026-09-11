"""Deterministic Hamilton cache identities for injected runtime services."""

import hashlib
import json
from pathlib import Path
from typing import Any

from hamilton.caching.fingerprinting import hash_value


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _file_tree(path: Path | None) -> list[tuple[str, str, int]]:
    if path is None or not path.exists():
        return []
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    result: list[tuple[str, str, int]] = []
    for file in files:
        try:
            result.append(
                (
                    str(file.relative_to(path if path.is_dir() else file.parent)),
                    hashlib.sha256(file.read_bytes()).hexdigest(),
                    file.stat().st_size,
                )
            )
        except OSError:
            result.append((str(file), "unreadable", -1))
    return result


def register_cache_fingerprints() -> None:
    """Register identities once; mutable locks and caches are intentionally ignored."""
    from egg_n_bacon_housing.utils.cache import CacheManager
    from egg_n_bacon_housing.utils.data_loader import SpatialReferenceRepository
    from egg_n_bacon_housing.utils.geocoding import Geocoder, InMemoryGeocoder, OneMapGeocoder
    from egg_n_bacon_housing.utils.mrt_line_mapping import MrtReferenceRepository
    from egg_n_bacon_housing.utils.school_features import SchoolReferenceRepository

    @hash_value.register(Path)
    def _path(value: Path, *args: Any, **kwargs: Any) -> str:
        return _digest({"path": str(value.resolve())})

    @hash_value.register(CacheManager)
    def _cache_manager(value: CacheManager, *args: Any, **kwargs: Any) -> str:
        return _digest(
            {
                "cache_dir": str(value.cache_dir.resolve()),
                "enabled": value.use_caching,
                "ttl": value.cache_duration_hours,
            }
        )

    @hash_value.register(MrtReferenceRepository)
    def _mrt(value: MrtReferenceRepository, *args: Any, **kwargs: Any) -> str:
        return _digest({"type": "mrt", "files": _file_tree(value.config_dir)})

    @hash_value.register(SpatialReferenceRepository)
    def _spatial(value: SpatialReferenceRepository, *args: Any, **kwargs: Any) -> str:
        return _digest({"type": "spatial", "files": _file_tree(value.raw_data_dir)})

    @hash_value.register(SchoolReferenceRepository)
    def _school(value: SchoolReferenceRepository, *args: Any, **kwargs: Any) -> str:
        return _digest({"type": "school", "files": _file_tree(value.bronze_dir / "external")})

    @hash_value.register(InMemoryGeocoder)
    def _memory_geocoder(value: InMemoryGeocoder, *args: Any, **kwargs: Any) -> str:
        return _digest({"type": "memory_geocoder", "lookup": value.lookup})

    @hash_value.register(OneMapGeocoder)
    def _onemap(value: OneMapGeocoder, *args: Any, **kwargs: Any) -> str:
        return _digest(
            {
                "type": "onemap",
                "workers": value.max_workers,
                "timeout": value.timeout,
                "ttl": value.cache_duration_hours,
            }
        )

    @hash_value.register(Geocoder)
    def _geocoder(value: Geocoder, *args: Any, **kwargs: Any) -> str:
        return _digest({"type": type(value).__qualname__})
