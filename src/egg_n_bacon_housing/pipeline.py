"""Hamilton DAG driver for egg-n-bacon-housing medallion pipeline."""

import importlib
import logging

from hamilton import driver

logger = logging.getLogger(__name__)

_STAGE_MODULES = [
    "egg_n_bacon_housing.components.01_ingestion",
    "egg_n_bacon_housing.components.02_cleaning",
    "egg_n_bacon_housing.components.03_features",
    "egg_n_bacon_housing.components.04_export",
    "egg_n_bacon_housing.components.05_metrics",
    "egg_n_bacon_housing.components.06_analytics",
]

STAGE_VARS: dict[str, list[str]] = {
    "ingest": [
        "raw_hdb_resale_transactions",
        "raw_condo_transactions",
        "raw_hdb_rental",
        "raw_rental_index",
        "raw_school_directory",
        "raw_shopping_malls",
        "raw_macro_data",
    ],
    "clean": [
        "cleaned_hdb_transactions",
        "hdb_validated",
        "cleaned_condo_transactions",
        "condo_validated",
        "geocoded_properties",
        "geocoded_validated",
    ],
    "features": [
        "rental_yield",
        "features_with_amenities",
        "unified_features",
    ],
    "export": [
        "unified_dataset",
        "dashboard_json",
        "segments_data",
        "interactive_tools_data",
    ],
    "metrics": [
        "price_metrics_by_area",
        "rental_yield_by_area",
        "affordability_metrics",
        "appreciation_hotspots",
    ],
    "all": [
        "unified_dataset",
        "dashboard_json",
        "segments_data",
        "price_metrics_by_area",
    ],
}

COMPONENTS = [importlib.import_module(m) for m in _STAGE_MODULES]


def build_pipeline(
    data_path: str | None = None,
    cache_dir: str | None = None,
) -> driver.Driver:
    """Build and return a configured Hamilton Driver."""
    from egg_n_bacon_housing.config import settings

    if data_path is None:
        data_path = str(settings.data_path)

    builder = driver.Builder().with_modules(*COMPONENTS).with_config({"data_path": data_path})

    if cache_dir:
        builder = builder.with_cache(path=cache_dir)
    elif settings.pipeline.use_caching:
        builder = builder.with_cache(path=str(settings.data_dir / "cache" / "hamilton"))

    dr = builder.build()
    logger.info("Hamilton pipeline driver built successfully")
    return dr


def run_pipeline(
    data_path: str | None = None,
    final_vars: list[str] | None = None,
    stage: str | None = None,
    dr: driver.Driver | None = None,
) -> dict:
    """Run pipeline and return results.

    Args:
        data_path: Path to data directory. Ignored if dr is provided.
        final_vars: Variable names to compute. Overrides stage.
        stage: Named stage key from STAGE_VARS. Defaults to "all".
        dr: Pre-built driver (avoids double-build when also visualizing).

    Returns:
        Dict of results keyed by variable name.
    """
    if final_vars is None:
        final_vars = STAGE_VARS.get(stage) if stage else STAGE_VARS["all"]

    if dr is None:
        dr = build_pipeline(data_path=data_path)
    return dr.execute(final_vars=final_vars)
