"""Hamilton DAG driver for egg-n-bacon-housing pipeline.

This module builds and exposes the Hamilton Driver for the medallion pipeline.
It wires together all components as a directed acyclic graph where function
signatures define dependencies.

Usage:
    from egg_n_bacon_housing.pipeline import build_pipeline

    dr = build_pipeline()
    results = dr.execute(final_vars=["unified_dataset", "dashboard_json"])
    dr.visualize_execution(final_vars=["unified_dataset"], output_file_path="dag.png")
"""

import importlib
import logging

from hamilton import driver

logger = logging.getLogger(__name__)


def _load_components():
    """Load component modules dynamically (names can't start with digits normally)."""
    names = [
        "egg_n_bacon_housing.components.01_ingestion",
        "egg_n_bacon_housing.components.02_cleaning",
        "egg_n_bacon_housing.components.03_features",
        "egg_n_bacon_housing.components.04_export",
        "egg_n_bacon_housing.components.05_metrics",
        "egg_n_bacon_housing.components.06_analytics",
    ]
    return [importlib.import_module(n) for n in names]


COMPONENTS = _load_components()


def build_pipeline(
    data_path: str | None = None,
    cache_dir: str | None = None,
) -> driver.Driver:
    """Build the Hamilton pipeline driver.

    Args:
        data_path: Path to data directory (defaults to settings.data_path).
        cache_dir: Path to Hamilton cache directory.

    Returns:
        Configured Hamilton Driver instance.
    """
    from egg_n_bacon_housing.config import settings

    if data_path is None:
        data_path = str(settings.data_path)

    config = {
        "data_path": data_path,
    }

    builder = driver.Builder().with_modules(*COMPONENTS).with_config(config)

    if cache_dir:
        builder = builder.with_cache(path=cache_dir)
    elif settings.pipeline.use_caching:
        cache_path = str(settings.data_dir / "cache" / "hamilton")
        builder = builder.with_cache(path=cache_path)

    dr = builder.build()
    logger.info("Hamilton pipeline driver built successfully")
    return dr


def run_full_pipeline(
    data_path: str | None = None,
    final_vars: list[str] | None = None,
) -> dict:
    """Run the full pipeline and return results.

    Args:
        data_path: Path to data directory.
        final_vars: List of final variable names to return.

    Returns:
        Dictionary of results keyed by variable name.
    """
    if final_vars is None:
        final_vars = [
            "unified_dataset",
            "dashboard_json",
            "segments_data",
            "price_metrics_by_area",
        ]

    dr = build_pipeline(data_path=data_path)
    results = dr.execute(final_vars=final_vars)
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    dr = build_pipeline()
    print("Available nodes:", dr.list_available_variables()[:10])

    results = run_full_pipeline()
    for name, value in results.items():
        if hasattr(value, "shape"):
            print(f"  {name}: {value.shape}")
        elif isinstance(value, (int, float)):
            print(f"  {name}: {value}")
        elif isinstance(value, dict):
            print(f"  {name}: dict with {len(value)} keys")
