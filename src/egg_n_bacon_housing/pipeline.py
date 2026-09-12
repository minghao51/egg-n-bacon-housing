"""Hamilton DAG driver for egg-n-bacon-housing medallion pipeline."""

import logging
from datetime import UTC, date, datetime
from pathlib import Path
from types import UnionType
from typing import Any, Union, get_args, get_origin
from uuid import uuid4
from zoneinfo import ZoneInfo

from hamilton import driver, htypes
from hamilton.lifecycle import base as lifecycle_base

from egg_n_bacon_housing.components import (
    cleaning,
    export,
    feature_profiles,
    feature_rental,
    feature_transactions,
    features,
    ingestion,
    materialization,
    metrics,
)
from egg_n_bacon_housing.config import Settings
from egg_n_bacon_housing.utils.cache import CacheManager
from egg_n_bacon_housing.utils.cache_fingerprints import register_cache_fingerprints
from egg_n_bacon_housing.utils.data_loader import SpatialReferenceRepository
from egg_n_bacon_housing.utils.geocoding import Geocoder, build_default_geocoder
from egg_n_bacon_housing.utils.layer_writer import build_writer
from egg_n_bacon_housing.utils.mrt_line_mapping import MrtReferenceRepository
from egg_n_bacon_housing.utils.output_registry import (
    MATERIALIZER_MAP,
    PUBLISHED_LAYERS,
    PUBLISHED_NAMES,
    QUARANTINE_MATERIALIZER_MAP,
    TERMINAL_OUTPUTS,
    outputs_for_stage,
)
from egg_n_bacon_housing.utils.runtime import RuntimePaths
from egg_n_bacon_housing.utils.school_features import SchoolReferenceRepository

logger = logging.getLogger(__name__)
register_cache_fingerprints()


class _ProtocolUnionInputValidator(lifecycle_base.BaseDoValidateInput):
    """Input validator that understands ``Protocol | None`` runtime services.

    sf-hamilton's default ``htypes.check_input_type`` skips its ``isinstance``
    branch for Protocol classes (``typing_inspect.is_generic_type(Protocol)``
    is True), so a ``MrtReference | None``-style annotation always rejects a
    valid repository instance injected at runtime. This adapter restores
    isinstance semantics for ``@runtime_checkable`` protocols (see
    ``utils.runtime``) and delegates every other type to the default Hamilton
    checker, so validation behavior is unchanged elsewhere.
    """

    @staticmethod
    def _union_members(node_type: Any) -> tuple[Any, ...]:
        if get_origin(node_type) in (Union, UnionType):
            return get_args(node_type)
        return (node_type,)

    def do_validate_input(self, *, node_type: type, input_value: Any) -> bool:
        for member in self._union_members(node_type):
            if isinstance(member, type) and getattr(member, "_is_runtime_protocol", False):
                if isinstance(input_value, member):
                    return True
            elif htypes.check_input_type(member, input_value):
                return True
        return False


try:
    from hamilton_sdk import adapters as _sdk_adapters

    _HAS_TRACKER = True
except ImportError:
    _sdk_adapters = None
    _HAS_TRACKER = False

_STAGE_MODULES = [
    ingestion,
    cleaning,
    feature_rental,
    features,
    feature_transactions,
    feature_profiles,
    export,
    metrics,
    materialization,
]

_MATERIALIZER_MAP = MATERIALIZER_MAP

# Every published output is persisted by exactly one companion materializer
# node; the computing nodes themselves are side-effect-free and cacheable.
_QUARANTINE_MAP = QUARANTINE_MATERIALIZER_MAP

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
        "geocoded_green_mark_buildings",
    ],
    "clean": [
        "cleaned_hdb_transactions",
        "cleaned_condo_transactions",
        "geocoded_properties",
        *outputs_for_stage("clean"),
    ],
    "features": outputs_for_stage("features"),
    "export": outputs_for_stage("export"),
    "metrics": outputs_for_stage("metrics"),
    "all": list(TERMINAL_OUTPUTS),
}

_INGEST_CACHE_DISABLED = tuple(STAGE_VARS["ingest"])


def _hamilton_cache_dir(data_dir: Path) -> Path:
    """Single source of truth for the Hamilton sqlite cache location."""
    return data_dir / "cache" / "hamilton"


def resolve_final_vars(final_vars: list[str] | None, stage: str | None = None) -> list[str]:
    """Resolve requested outputs from explicit vars or a named stage.

    Mirrors the CLI contract: explicit ``final_vars`` override ``stage``, and
    an omitted stage defaults to "all".
    """
    if final_vars is not None:
        return final_vars
    if stage:
        if stage not in STAGE_VARS:
            raise ValueError(f"Unknown stage {stage!r}; valid stages: {sorted(STAGE_VARS)}")
        return STAGE_VARS[stage]
    return STAGE_VARS["all"]


def build_pipeline(
    settings: Settings,
    data_path: str | None = None,
    cache_dir: str | None = None,
) -> driver.Driver:
    """Build and return a configured Hamilton Driver."""
    resolved_data_path = settings.resolve_data_path(data_path)

    builder = driver.Builder().with_modules(*_STAGE_MODULES).with_config({})
    builder = builder.with_adapters(_ProtocolUnionInputValidator())

    if settings.tracking_enabled and not _HAS_TRACKER:
        raise RuntimeError(
            "Hamilton tracking is enabled but sf-hamilton-sdk is not installed; "
            "install the tracking extra with `uv sync --extra tracking`."
        )

    if settings.tracking_enabled:
        assert settings.tracking_project_id is not None
        assert settings.tracking_username is not None
        assert settings.tracking_environment is not None
        tracker = _sdk_adapters.HamiltonTracker(
            project_id=settings.tracking_project_id,
            username=settings.tracking_username,
            dag_name="medallion_pipeline",
            tags={"env": settings.tracking_environment},
        )
        builder = builder.with_adapters(tracker)

    if cache_dir:
        cache_path: Path | None = Path(cache_dir)
    elif settings.pipeline.use_caching:
        cache_path = _hamilton_cache_dir(resolved_data_path)
    else:
        cache_path = None

    if cache_path is not None:
        # Hamilton's sqlite result store cannot create missing parent dirs
        # (fails with sqlite3.OperationalError: readonly database).
        cache_path.mkdir(parents=True, exist_ok=True)
        builder = builder.with_cache(
            path=str(cache_path),
            disable=tuple(
                (*_MATERIALIZER_MAP.values(), *_QUARANTINE_MAP.values(), *_INGEST_CACHE_DISABLED)
            ),
        )

    dr = builder.build()
    logger.info("Hamilton pipeline driver built successfully")
    return dr


def run_pipeline(
    settings: Settings,
    data_path: str | None = None,
    final_vars: list[str] | None = None,
    stage: str | None = None,
    dr: driver.Driver | None = None,
    geocoder: Geocoder | None = None,
    pipeline_as_of_date: date | None = None,
) -> dict:
    """Run pipeline and return results.

    Args:
        data_path: Path to data directory (used for layer path resolution
            and injected inputs, even when ``dr`` is provided).
        final_vars: Variable names to compute. Overrides stage.
        stage: Named stage key from STAGE_VARS. Defaults to "all".
        dr: Pre-built driver (avoids double-build when also visualizing).

    Returns:
        Dict of results keyed by variable name.
    """
    explicit_final_vars = final_vars is not None
    final_vars = resolve_final_vars(final_vars, stage)

    paths = RuntimePaths.from_settings(settings, data_path)
    if dr is None:
        dr = build_pipeline(settings, data_path=data_path)

    from egg_n_bacon_housing.utils.bronze import seed_bronze_external

    seed_bronze_external(paths.bronze_dir, paths.data_dir)
    pipeline_run_id = f"{datetime.now(tz=UTC).strftime('%Y%m%dT%H%M%S%fZ')}_{uuid4().hex}"
    pipeline_as_of_date = pipeline_as_of_date or datetime.now(ZoneInfo("Asia/Singapore")).date()
    materialization_targets = (
        list(PUBLISHED_LAYERS)
        if not explicit_final_vars and stage in (None, "all")
        else [name for name in final_vars if name in PUBLISHED_NAMES]
    )
    # Build the graph before constructing run-scoped services, and construct a
    # writer only when the requested subgraph contains published materializers.
    writer = (
        build_writer(settings, paths.data_dir / "pipeline") if materialization_targets else None
    )
    layer_inputs: dict[str, Any] = {
        "bronze_dir": paths.bronze_dir,
        "manual_dir": paths.manual_dir,
        "min_coordinate_coverage": settings.geocoding.min_coordinate_coverage,
        "min_coordinate_coverage_hdb": settings.geocoding.min_coordinate_coverage_hdb,
        "min_coordinate_coverage_condo": settings.geocoding.min_coordinate_coverage_condo,
        "coordinate_coverage_policy": settings.geocoding.coordinate_coverage_policy,
        "median_household_income": settings.metrics.median_household_income,
        "affordability_thresholds": settings.metrics.affordability_thresholds,
        "min_transactions_for_hotspot": settings.metrics.min_transactions_for_hotspot,
        "large_table_validation_policy": settings.pipeline.large_table_validation_policy,
        "max_transaction_age_days": settings.pipeline.max_transaction_age_days,
        "pipeline_as_of_date": pipeline_as_of_date,
        "pipeline_run_id": pipeline_run_id,
    }
    if writer is not None:
        layer_inputs["writer"] = writer
    execution_vars = list(final_vars)
    # Custom test/integration drivers may not expose the Hamilton graph. The
    # production Driver does, and only it can execute companion materializers.
    if hasattr(dr, "list_available_variables"):
        execution_vars.extend(_MATERIALIZER_MAP[name] for name in materialization_targets)
        upstream = {node.name for node in dr.what_is_upstream_of(*final_vars)}
        # Quarantine companions persist rejected rows through the writer. A
        # narrow --final-var execution that materializes no published output
        # has no writer, so it must not request them.
        if writer is not None:
            for name in PUBLISHED_NAMES:
                if name in upstream:
                    execution_vars.append(_QUARANTINE_MAP[name])

        required = upstream | set(execution_vars)
        cache_manager = CacheManager(
            cache_dir=paths.api_cache_dir,
            use_caching=settings.pipeline.use_caching,
            cache_duration_hours=settings.pipeline.cache_duration_hours,
        )
        factories: dict[str, Any] = {
            "cache_manager": lambda: cache_manager,
            "geocoder": lambda: geocoder or build_default_geocoder(settings, cache_manager),
            "mrt_reference": lambda: MrtReferenceRepository(paths.external_dir),
            "spatial_reference": lambda: SpatialReferenceRepository(paths.manual_dir / "geojsons"),
            "school_reference": lambda: SchoolReferenceRepository(paths.bronze_dir, paths.data_dir),
        }
        for name, factory in factories.items():
            if name in required:
                layer_inputs[name] = factory()
        # Credential materialization is lazy as well: narrow local/reference
        # executions must not read or expose the URA secret at all.
        if "raw_condo_transactions" in required:
            layer_inputs["ura_api_access_key"] = settings.ura_api_access_key.get_secret_value()
    results = dr.execute(final_vars=list(dict.fromkeys(execution_vars)), inputs=layer_inputs)
    missing = [name for name in final_vars if name not in results]
    if missing:
        raise RuntimeError(f"Pipeline did not produce requested final_vars: {missing}")
    return {name: results[name] for name in final_vars}
