# Runtime Dependency Injection Handoff

**Date:** 2026-09-03
**Status:** Core migration landed; historical proposal retained for context
**Priority:** Medium — architectural hardening after the Hamilton DAG correctness work
**Scope:** Replace mutable process-global runtime configuration in cache, spatial data loading, school features, and MRT mapping with injected immutable dependencies.

> The production path now constructs the Hamilton driver before run-scoped
> services and injects explicit cache, reference, geocoding, writer, and
> `pipeline_as_of_date` dependencies. Compatibility-surface cleanup and the
> remaining verification work are tracked in
> `docs/plans/2026-09-10-hamilton-dag-next-thread-handoff.md`.

## Goal

Make each pipeline run self-contained and deterministic. A run using a custom
`data_path` must not alter hidden module state that can leak into another run,
test, notebook, or concurrent execution.

The supported production path remains:

```text
main.py -> build_pipeline() -> run_pipeline() -> Hamilton Driver
```

Do not add another runner, import global `Settings` inside DAG nodes, or change
existing CLI stages and final-variable names.

## Current State

`run_pipeline()` resolves the correct runtime paths and then calls
`_configure_runtime()`. That function centralizes four compatibility APIs:

- `utils.cache.configure(...)`
- `utils.data_loader.configure(data_dir)`
- `utils.mrt_line_mapping.configure(config_dir)`
- `utils.school_features.configure(bronze_dir, data_dir)`

Centralization makes the coupling visible, but each utility still stores
mutable module-level state. Reconfiguration is process-wide, and correctness
depends on call order.

Current test baseline at handoff: **376 passed**, with Ruff, format, mypy,
documentation validation, skill validation, and `git diff --check` clean.

## Risks Being Addressed

1. Two pipeline runs with different `data_path` values can overwrite each
   other's utility configuration.
2. Tests must reset or replace private globals such as `_paths`, `_config_dir`,
   `_MRT_LINES`, `_STATION_LINES`, and `_cache_manager`.
3. Utility behavior cannot be understood from a Hamilton node's signature.
4. Concurrent or embedded execution is unsafe even though ordinary sequential
   CLI execution works.
5. Cached reference data may survive a path change unless every configure
   function correctly resets every related global.

## Target Design

Introduce small immutable runtime services, constructed once per run and passed
through Hamilton inputs only to nodes that consume them.

Suggested contracts:

```python
@dataclass(frozen=True)
class RuntimePaths:
    data_dir: Path
    bronze_dir: Path
    external_dir: Path
    api_cache_dir: Path


@dataclass(frozen=True)
class ReferenceDataRepository:
    paths: RuntimePaths

    def planning_areas_for_points(...) -> pd.Series: ...
    def load_school_tiers(...) -> tuple[pd.DataFrame, pd.DataFrame]: ...
    def mrt_lines(...) -> Mapping[str, MrtLine]: ...
    def station_lines(...) -> Mapping[str, tuple[str, ...]]: ...
```

The exact class boundaries may change after call-site analysis. Prefer narrow
protocols over a single large service container. Immutable objects may own
thread-safe internal caches where profiling proves useful, but paths and policy
must not mutate after construction.

## Compatibility Requirements

- Keep `configure()` wrappers during migration for notebooks, tests, and any
  non-DAG callers. Mark them as compatibility APIs in docstrings.
- A wrapper may install a module-local default service, but production DAG
  nodes must receive their service explicitly.
- Preserve existing utility functions while adding an optional explicit
  repository/service parameter where practical.
- Preserve current dataframe schemas, persisted filenames, medallion paths,
  `STAGE_VARS`, and Hamilton variable names.
- `data_path` overrides must continue to isolate layer outputs, bronze seeds,
  API caches, Hamilton caches, and `quality_metrics.db`.
- Do not move bronze persistence into `LayerWriter` as part of this migration.
- Do not remove compatibility wrappers until repository references and
  documented/public consumers have been audited in a later release.

## Phased Implementation

### Phase 1 — Inventory and contracts

1. Trace every caller of the four `configure()` functions and every read of
   their private globals.
2. Record which Hamilton nodes consume each capability.
3. Add immutable path and protocol types in a neutral runtime module.
4. Build the runtime services in `run_pipeline()` and add graph-contract tests
   for their exact external-input names.

Deliverable: types and factories only; behavior remains unchanged.

### Phase 2 — MRT mapping

Migrate MRT first because it has a small, read-only surface.

1. Replace `_config_dir`, `_MRT_LINES`, and `_STATION_LINES` with an immutable
   `MrtReferenceRepository` instance.
2. Pass it into the proximity/location feature path.
3. Retain `configure()` and zero-argument getters as compatibility wrappers.
4. Prove reusing two repositories with different roots does not cross-contaminate
   cached results.

### Phase 3 — School and spatial reference data

1. Replace `school_features._paths` with explicit repository/path arguments.
2. Move planning-area file lookup and point-in-polygon loading out of
   `data_loader` globals and into a spatial repository.
3. Inject the repositories into the spatial/location feature module.
4. Keep expensive reference frames cached per repository instance, not per
   process.

### Phase 4 — API cache service

This phase has the widest ingestion impact and must also follow
`.agents/skills/change-data-ingestion/SKILL.md`.

1. Convert `CacheManager` into the explicit dependency at adapter and bronze
   loader boundaries.
2. Pass it only to nodes/adapters that cache external calls.
3. Keep `cached_call()` and `configure()` wrappers backed by a compatibility
   default for non-production callers.
4. Preserve cache-key formats and legacy-pickle policy unless a separately
   documented migration is approved.
5. Verify targeted refresh clears the same cache scopes after injection.

### Phase 5 — Remove production global setup

1. Delete `_configure_runtime()` calls once all production consumers use
   injected services.
2. Keep compatibility defaults outside the production execution path.
3. Add a test that fails if `run_pipeline()` invokes any compatibility
   `configure()` wrapper.
4. Update the pipeline development and ingestion development guides.

## Test Plan

Add focused tests for:

- two sequential runs with different roots;
- two service instances used concurrently without state leakage;
- custom nested and absolute layer paths;
- reference-data cache invalidation by constructing a new service;
- identical MRT, school, planning-area, and proximity outputs before/after;
- API cache hit, miss, expiry, corrupt entry, disabled caching, and legacy
  pickle behavior;
- targeted and full refresh behavior;
- exact Hamilton external inputs and discoverable stage targets;
- compatibility wrapper behavior for existing direct utility callers;
- production execution without invoking compatibility globals.

Run focused tests first, then:

```bash
UV_CACHE_DIR=/tmp/egg-n-bacon-uv-cache uv run pytest --no-cov -q
UV_CACHE_DIR=/tmp/egg-n-bacon-uv-cache uv run ruff check .
UV_CACHE_DIR=/tmp/egg-n-bacon-uv-cache uv run ruff format --check .
UV_CACHE_DIR=/tmp/egg-n-bacon-uv-cache uv run mypy
UV_CACHE_DIR=/tmp/egg-n-bacon-uv-cache uv run python scripts/generate_catalog.py
UV_CACHE_DIR=/tmp/egg-n-bacon-uv-cache uv run python scripts/tools/validate_docs_layout.py
UV_CACHE_DIR=/tmp/egg-n-bacon-uv-cache uv run python scripts/tools/validate_agent_skills.py
git diff --check
```

For cache/adapter changes, also run the focused ingestion suites required by
the ingestion skill.

## Definition of Done

- Production `run_pipeline()` performs no mutation of cache, data-loader,
  school-feature, or MRT-mapping module globals.
- All runtime paths and policies are visible in immutable injected objects.
- Separate runs and concurrent service instances cannot contaminate one
  another.
- Compatibility wrappers remain tested and clearly documented as transitional.
- No changes to CLI stage names, final-variable names, published schemas, or
  output paths.
- Cold and warm pipeline outputs are equivalent to the pre-migration baseline.
- Full repository verification passes.

## Explicit Non-Goals

- Replacing Hamilton or introducing a second orchestration path.
- Reworking source-specific ingestion semantics merely to share an abstraction.
- Changing cache formats, refresh semantics, output schemas, or medallion
  ownership without a separate migration decision.
- Removing all module-level constants; immutable static lookup tables are not
  runtime configuration.

## Recommended First Slice

Start with MRT mapping only. It offers a narrow proof of the repository pattern,
exercises dependency injection through the location feature path, and avoids
combining the architectural migration with external API/cache behavior.
