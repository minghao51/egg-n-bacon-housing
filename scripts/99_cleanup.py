"""Cleanup script: remove stale cache and old data."""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.cache import CacheManager
from egg_n_bacon_housing.utils.logging_config import get_logger, setup_logging_from_env


def main():
    setup_logging_from_env()
    logger = get_logger(__name__)
    logger.info("Running cleanup...")
    cache_manager = CacheManager(
        cache_dir=settings.data_dir / "cache",
        use_caching=settings.pipeline.use_caching,
        cache_duration_hours=settings.pipeline.cache_duration_hours,
    )
    stats = cache_manager.get_stats()
    logger.info(f"Cache stats before cleanup: {stats}")
    cache_manager.clear()
    logger.info("Cache cleared")

    cutoff = datetime.now(tz=UTC) - timedelta(days=settings.pipeline.quarantine_retention_days)
    removed = 0
    for layer in ("silver", "gold", "platinum", "platinum_metrics"):
        quarantine_root = settings.layer_dir(layer) / "_quarantine"
        if not quarantine_root.exists():
            continue
        for path in quarantine_root.rglob("*.parquet"):
            if datetime.fromtimestamp(path.stat().st_mtime, tz=UTC) < cutoff:
                path.unlink()
                removed += 1
    logger.info("Removed %d expired quarantine artifact(s)", removed)


if __name__ == "__main__":
    main()
