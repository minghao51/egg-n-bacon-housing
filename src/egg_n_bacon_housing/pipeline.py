"""Hamilton DAG driver for egg-n-bacon-housing medallion pipeline."""

import importlib
import logging

from hamilton import driver

from egg_n_bacon_housing.config import settings

logger = logging.getLogger(__name__)

try:
    from hamilton_sdk import adapters as _sdk_adapters

    _HAS_TRACKER = True
except ImportError:
    _sdk_adapters = None
    _HAS_TRACKER = False

_STAGE_MODULES = [
    "egg_n_bacon_housing.components.01_ingestion",
    "egg_n_bacon_housing.components.02_cleaning",
    "egg_n_bacon_housing.components.03_features",
    "egg_n_bacon_housing.components.04_export",
    "egg_n_bacon_housing.components.05_metrics",
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
        "raw_mrt_stations",
        "raw_hawker_centres",
        "raw_supermarkets",
        "raw_parks",
        "raw_childcare",
        "raw_kindergartens",
        "raw_bus_stops",
        "raw_hdb_property_info",
        "raw_income_by_planning_area",
        "raw_green_mark_buildings",
        "raw_chas_clinics",
        "raw_sports_facilities",
        "raw_community_clubs",
        "raw_dwelling_units_by_town",
        "raw_median_annual_value",
        "raw_hdb_resident_population",
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
        "macro_enriched_features",
        "block_metadata_enriched",
        "income_enriched_features",
        "town_supply_enriched",
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
        "interactive_tools_data",
        "price_metrics_by_area",
        "rental_yield_by_area",
        "affordability_metrics",
        "appreciation_hotspots",
    ],
}


def _get_components() -> list:
    if not hasattr(_get_components, "_cache"):
        _get_components._cache = [importlib.import_module(m) for m in _STAGE_MODULES]  # type: ignore[attr-defined]
    return _get_components._cache  # type: ignore[attr-defined]


def build_pipeline(
    data_path: str | None = None,
    cache_dir: str | None = None,
) -> driver.Driver:
    """Build and return a configured Hamilton Driver."""
    resolved_data_path = settings.resolve_data_path(data_path)

    builder = (
        driver.Builder()
        .with_modules(*_get_components())
        .with_config({"data_path": str(resolved_data_path)})
    )

    if _HAS_TRACKER:
        tracker = _sdk_adapters.HamiltonTracker(
            project_id=1,
            username="pipeline@egg-n-bacon-housing",
            dag_name="medallion_pipeline",
            tags={"env": "dev"},
        )
        builder = builder.with_adapters(tracker)

    if cache_dir:
        builder = builder.with_cache(path=cache_dir)
    elif settings.pipeline.use_caching:
        builder = builder.with_cache(path=str(resolved_data_path / "cache" / "hamilton"))

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

    resolved_data_path = settings.resolve_data_path(data_path)
    layer_inputs = {
        "bronze_dir": settings.layer_dir("bronze", resolved_data_path),
        "silver_dir": settings.layer_dir("silver", resolved_data_path),
        "gold_dir": settings.layer_dir("gold", resolved_data_path),
        "platinum_dir": settings.layer_dir("platinum", resolved_data_path),
        "webapp_data_dir": settings.webapp_data_dir,
        "min_coordinate_coverage": settings.geocoding.min_coordinate_coverage,
        "median_household_income": settings.metrics.median_household_income,
    }
    return dr.execute(final_vars=final_vars, inputs=layer_inputs)
