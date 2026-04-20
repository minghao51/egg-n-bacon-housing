"""Cleanup script: remove stale cache and old data."""
from egg_n_bacon_housing.utils.cache import clear_cache, get_cache_stats
from egg_n_bacon_housing.utils.logging_config import setup_logging_from_env, get_logger

def main():
    setup_logging_from_env()
    logger = get_logger(__name__)
    logger.info("Running cleanup...")
    stats = get_cache_stats()
    logger.info(f"Cache stats before cleanup: {stats}")
    clear_cache()
    logger.info("Cache cleared")

if __name__ == "__main__":
    main()