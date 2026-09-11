# Pipeline Development Guide

**Status**: Active

This guide defines the supported Hamilton pipeline contract. Production runs
start at `main.py` and use `build_pipeline()` and `run_pipeline()` from
`src/egg_n_bacon_housing/pipeline.py`.

## Stages and ownership

| CLI stage  | Component                | Responsibility                                   | Output boundary                                         |
| ---------- | ------------------------ | ------------------------------------------------ | ------------------------------------------------------- |
| `ingest`   | `components/ingestion/`  | Acquire source data and normalize it into bronze | `data/pipeline/01_bronze/`                              |
| `clean`    | `components/cleaning.py` | Clean, validate, and quarantine invalid records  | `data/pipeline/02_silver/`                              |
| `features` | `components/feature_*.py` | Build reusable entities and derived features     | `data/pipeline/03_gold/`                                |
| `export`   | `components/export.py`   | Produce stable and app-facing datasets           | `data/pipeline/04_platinum/` and configured app outputs |
| `metrics`  | `components/metrics.py`  | Produce analytical metrics and summaries         | `data/pipeline/04_platinum/metrics/`                    |

The published contract is declared once in `utils/output_registry.py` via
`PublishedOutputSpec`. The registry drives stage selection, layer ownership,
materializer names, and terminal-result selection. The `all` stage materializes
all 12 registered outputs and returns only the six terminal frames. Use
`--final-var` for a deliberate narrower execution.

## Layer invariants

- Bronze is source-owned and reproducible. Do not apply business rules or
  silently overwrite a valid cache with an empty response.
- Silver is the primary validation boundary.
  `pipeline.large_table_validation_policy` (default `full`) selects the
  behavior: `full` validates every row in deterministic chunks and quarantines
  schema failures, including rows failing required-field checks (they are
  quarantined with a per-row reason, never silently dropped); `fail` runs the
  same full validation and raises instead of persisting when any row is
  invalid; `sample` is a diagnostic compatibility option that validates a
  random sample, persists the entire frame, and logs the exact unvalidated row
  count. Quarantine files are written once per run under
  `<layer>/_quarantine/<dataset>/<UTC-timestamp>_<uuid>.parquet` with
  `track_quality=False`, keeping their timestamped names out of the quality
  baselines. `scripts/99_cleanup.py` removes only files older than
  `pipeline.quarantine_retention_days` (90 days by default).
- Coordinate coverage is a production quality gate applied per property-type
  segment: `geocoding.min_coordinate_coverage_hdb` (0.7) for HDB,
  `geocoding.min_coordinate_coverage_condo` (0.3) for condo, and the legacy
  `geocoding.min_coordinate_coverage` for any other segment. Under the default
  `fail` policy a run raises naming each failing segment and its coverage;
  the explicit `warn` policy (`geocoding.coordinate_coverage_policy`) warns
  per segment instead.
- Gold transactions require a valid `transaction_date` and canonical `month`
  (`YYYY-MM`) that agree. Production also rejects outputs whose latest
  transaction exceeds `pipeline.max_transaction_age_days` (120 by default).
  Freshness is evaluated against the explicitly injected Singapore
  `pipeline_as_of_date`, which callers can provide to `run_pipeline()` for
  deterministic reruns.
- Transaction grain is one source transaction. HDB and URA have different
  composite business keys and neither exposes a universal transaction ID, so
  coincident sales are not rejected by a speculative cross-source uniqueness
  key; source-specific deduplication is performed during ingestion.
- Gold contains reusable entities and features, not app-specific presentation
  artifacts.
- Platinum contains stable exports, app-facing data, and analytical metrics,
  all validated against pydantic contracts (`HUnifiedRecord`,
  `PaMonthlyMetric`, `AppreciationHotspot`) under the same large-table
  policy. Rejected rows are written by run-specific quarantine materializers
  under each layer's `_quarantine/<dataset>/<run_id>.parquet` path.
- Tracking is opt-in. Install `uv sync --extra tracking` before enabling it;
  enabled tracking without the extra fails immediately with an actionable
  installation message.
- Nodes receive settings, paths, geocoders, and writers through dependency
  injection. Published outputs are persisted in exactly one place: a companion
  `materialize_<node>` node in `components/materialization.py` writes each
  registry entry through `LayerWriter`, so every layer output gets
  the same compression and quality tracking. Computing nodes are
  side-effect-free — validation-gateway calls run with `persist=False` — and
  are therefore safely cacheable; the companion materializers are excluded
  from the Hamilton cache so a cache hit can never skip a write. Bronze source
  caches retain their established self-managed paths through the shared
  `utils/bronze` cache helpers (`read_bronze_cache` / `write_bronze_cache`):
  cache-first, atomic, and empty-guarded so an empty or partial source
  response never replaces a valid cache. Ingestion nodes receive `manual_dir`
  as an injected input and never derive source paths from `bronze_dir`
  traversal.
- Missing published files are recreated by cache-disabled materializers from
  cached computation; the pipeline does not clear the entire Hamilton cache.
  Legitimately empty outputs persist as 0-row parquets, so they never read as
  "missing".
- Runtime reference data and API caching are isolated per execution. `run_pipeline()`
  constructs only the runtime services required by the selected dependency
  graph. Cache and reference services are explicit inputs; no module-global
  configuration is used.
- `RuntimePaths` is the authoritative per-run root contract. It derives the
  configured bronze/external path and the manual/API-cache roots from the
  resolved `data_path`, including nested or absolute layer overrides.
- Bronze static reference files (amenity GeoJSONs, MRT config JSONs, school
  tiers, SORA parquet) are seeded into `01_bronze/external/` at startup from
  `data/manual/` and `data/raw/` by `utils/bronze.seed_bronze_external`.
  Missing files are logged loudly; affected nodes degrade to empty data.
- Every bronze fetch-and-write upserts `01_bronze/bronze_manifest.json`
  (`fetched_at`, `source`, row count), and the rolling-window datasets
  `raw_condo_transactions` and `raw_hdb_resale` log a stale warning on cache
  hits past `utils.bronze.STALE_WARN_DAYS` (35 days). Freshness metadata is
  observability only; `--refresh` remains the only invalidation.
- Bronze transforms embed documented conventions: income medians use
  grouped-median interpolation inside the median bracket (the open top
  bracket assumes the previous bracket's width, with a per-run log line
  reporting how many planning areas needed that assumption), so
  `median_monthly_income` values intentionally differ from older
  midpoint-based runs.
- Month derivation (`utils.time_index.ensure_month_column`) warns with
  dropped/kept counts when unparseable dates shrink a frame; a frame with
  neither a month nor a date column raises `ValueError` (a schema break, not
  data sparsity).
- `appreciation_hotspots` applies a volume floor
  (`metrics.min_transactions_for_hotspot`, default 5, env
  `METRICS__MIN_TRANSACTIONS_FOR_HOTSPOT`) before ranking: months below the
  floor can neither rank nor distort another month's appreciation baseline.
- Bronze parquets never expire on their own. Use `main.py --refresh` (all
  caches) or `main.py --refresh <glob>` (specific bronze outputs) to force
  re-fetching. Rolling sources can also be refreshed on a schedule — see
  `docs/guides/ops-scheduling.md`.
- Every layer write records a quality snapshot (`data/quality_metrics.db`);
  `_quarantine/` writes are excluded. `scripts/tools/quality_report.py`
  surfaces snapshot trends, anomaly flags, row-count deltas, quarantine
  summaries, and bronze freshness (`--json` for machine use); it is read-only
  and not a gate.

## Adding or changing a node

1. Identify the owning stage and its layer contract.
2. Add the node in the owning component module; gold feature nodes are split by
   rental, spatial/location, transaction enrichment, and profile entity domain.
   For ingestion, place source
   transport in an adapter and DAG assembly in `components/ingestion/`.
3. Trace Hamilton dependencies and confirm the module is included by
   `pipeline.py`.
4. Add the output to the registry when it is a supported published output;
   `PublishedOutputSpec` supplies its stage, layer, terminal status, and
   companion materializer. Computing nodes never write layer files themselves.
5. Update schemas, source/lineage documentation, and downstream readers.
6. Add focused tests for the node contract, failure behavior, and persistence.
7. Run the pipeline, ingestion, docs, lint, formatting, type, and agent-skill
   checks listed below.

Do not add a parallel runner, new ad-hoc persistence, or retired standalone
analytics scripts to execute DAG work.

## Definition of done

A pipeline change is complete when its node is reachable through the supported
runner, its layer and schema contracts are documented, its tests cover the
changed behavior, its stage outputs are registered, and focused plus repository
quality checks pass.

```bash
uv run pytest tests/test_pipeline.py tests/test_pipeline_integration.py --no-cov -q
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python scripts/tools/validate_docs_layout.py
uv run python scripts/tools/validate_agent_skills.py
git diff --check
```
