Agent: b926e1db-82b8-4d0
Type: scout | Status: steered (wrapped up at the turn limit — output may be partial) | Tool uses: 36 | 101.2k token | Context: 10% | Duration: 106.9s
Model: opencode-go/deepseek-v4.1-flash, thinking: high
Description: Discover pipeline operational boundaries

> **Correction (added by the lead auditor):** this is raw scout output, retained unedited for provenance. Two claims were verified wrong and are not to be reused: (1) `TERMINAL_OUTPUTS` has **six** names, not five (`src/egg_n_bacon_housing/utils/output_registry.py:23-60`); (2) the coverage figure quoted elsewhere in scout output is superseded by the fresh measured run (3,894/4,076 = 95.53 %). Authoritative numbers live in [execution-provenance.md](execution-provenance.md) and [01-discovery.md](../01-discovery.md).

## Phase 1 discovery — egg-n-bacon-housing @ 449b921 (read-only)

Coverage limits: I read in full `main.py`, all of `src/egg_n_bacon_housing/{config,pipeline,components/{cleaning,export,metrics,materialization},schemas/*,utils/{output_registry,validation,validation_gateway,layer_writer,logging_config,runtime,data_quality,contracts,_http via adapters}}`, key regions of `features.py`, `feature_transactions.py`, `bronze.py`/`ingestion/datagov.py` (function maps only), full `scripts/00_sync_data.py`, `99_cleanup.py`, `40_refresh_rolling.py`, and outlines of `export_app_data.py`, `generate_catalog.py`, `v2_observed.py`, `check_catalog.py`, `check_core_coverage.py`, `ci.yml`, `pyproject.toml`. I did **not** read `ingestion/{geojson,macro,ura_csv}.py` bodies, `feature_{rental,profiles}.py`, `adapters/{onemap,ura,datagovsg}.py` bodies, `utils/{geocoding,cache,proximity,school_features,hdb_lookups,mrt_line_mapping,cache_fingerprints}.py` bodies, the 20+ `scripts/tools/*_evidence.py`, or any test bodies (only sizes/names). No `.env`/secret files read; no scripts executed. Counts below are `wc -l`/grep-measured only.

## Files Retrieved

1. `main.py` (1–109) — sole CLI: `--stage`, `--final-var`, `--refresh`, `--log-level`, `--visualize`.
2. `src/egg_n_bacon_housing/pipeline.py` (1–313) — `STAGE_VARS`, `resolve_final_vars`, `build_pipeline`, `run_pipeline`, DI factories, cache-disable tuple.
3. `src/egg_n_bacon_housing/config.py` (1–230) — pydantic-settings `Settings`, `LayerDirs`, `PipelineConfig`, `GeocodingConfig`, `MetricsConfig`, module-level `settings = Settings()` (230).
4. `src/egg_n_bacon_housing/utils/output_registry.py` (1–65) — 12 `PublishedOutputSpec` entries; `MATERIALIZER_MAP`, `TERMINAL_OUTPUTS`, `outputs_for_stage`.
5. `src/egg_n_bacon_housing/components/materialization.py` (1–170) — `@parameterize` families + PEP 562 `__getattr__` direct-call surface.
6. `src/egg_n_bacon_housing/utils/validation_gateway.py` (1–183) — `validate_and_quarantine`, `vectorized_precheck`, `empty_extracted`, `extracted_validation`.
7. `src/egg_n_bacon_housing/utils/validation.py` (1–135) — `validate_schema` (chunked TypeAdapter, required-field prefilter, null scrub).
8. `src/egg_n_bacon_housing/utils/layer_writer.py` (1–181) — `LayerWriter`/`SimpleWriter`/`TrackedWriter`, `_atomic_parquet_write`, `build_writer`.
9. `src/egg_n_bacon_housing/schemas/{clean_models,feature_models,platinum_models}.py` (93/248/58) — full contract set.
10. `src/egg_n_bacon_housing/components/cleaning.py` (1–220 of 526) — silver boundary, coverage gates, `require_columns`.
11. `src/egg_n_bacon_housing/components/features.py` (95–340) — `validate_location_dim`, proximity degrade path.
12. `src/egg_n_bacon_housing/components/feature_transactions.py` (80–180, 320–356) — `_enforce_transaction_time_contract`, gold validation.
13. `src/egg_n_bacon_housing/components/{export,metrics}.py` (75/241) — platinum boundaries.
14. `src/egg_n_bacon_housing/utils/data_quality.py` (1–403) — SQLite snapshots, Welford baselines, 3σ anomaly.
15. `src/egg_n_bacon_housing/utils/logging_config.py` (1–147) — `setup_logging`, `LEVEL_MAP`, `setup_logging_from_env`.
16. `src/egg_n_bacon_housing/utils/runtime.py` (1–63) — `RuntimePaths`, runtime-checkable Protocols.
17. `scripts/00_sync_data.py` (1–277), `99_cleanup.py` (1–42), `40_refresh_rolling.py` (1–253) — full.
18. `scripts/{export_app_data,v2_observed,generate_catalog}.py` — module docstrings + symbol outlines.
19. `.github/workflows/ci.yml` (1–159), `pyproject.toml` (1–170).
20. Prior state: `docs/plans/{2026-04-28-code-audit-findings,2026-09-07-src-audit-improvement-program,2026-09-10-code-audit-remediation-roadmap,2026-09-11-code-audit-remediation-handoff}.md`, `docs/implementation/2026-reporting-refresh-audit.md`, `docs/implementation/2026-11-22-dependency-audit.md`.

## Key Code

**Schema/registry co-location.** Schemas live in one package; the published-output registry is the single cross-cutting index:

```python
# output_registry.py:23
PUBLISHED_OUTPUTS: tuple[PublishedOutputSpec, ...] = (
    PublishedOutputSpec("hdb_validated", "silver", "clean", "materialize_hdb_validated", False),
    ...
    PublishedOutputSpec("pa_monthly_metrics", "platinum_metrics", "metrics", "materialize_pa_monthly_metrics", True),
)
PUBLISHED_LAYERS = {spec.name: spec.layer for spec in PUBLISHED_OUTPUTS}
TERMINAL_OUTPUTS = tuple(spec.name for spec in PUBLISHED_OUTPUTS if spec.terminal)
```

`catalog_dataset_id` ClassVars (`clean_models.py:39,56,77`; `feature_models.py:18,71,160,177,216,239`; `platinum_models.py:21,27,49`) are the schema-side IDs consumed by `scripts/generate_catalog.py:114 _discover_catalog_models`. Note `schemas/__init__.py` re-exports **only** the three platinum models (`__all__`, lines 3–9), so clean/feature models are imported by direct module path.

**Contract versioning.** Only the publication manifests carry explicit schema versions: `export_app_data.py:155 RELEASE_SCHEMA_VERSION = "1.0.0"`; `v2_observed.py:58-59 SCHEMA_VERSION = "2.1.0"`, `METHOD_VERSION = "observed-aggregates-2"`. No version field exists on `Settings`, schemas, or bronze manifests — `record_bronze_fetch` stores `source`/`rows`/`fetched_at` only (`bronze.py:118-128`).

**Runtime validation.** Single gateway; policy is a settings literal:

```python
# config.py:27
large_table_validation_policy: Literal["sample", "full", "fail"] = "sample"
# validation_gateway.py:156
if (large_table_policy == "sample" and sample_validation_size is not None
        and len(df) > sample_validation_size):
    issues = vectorized_precheck(df, model_cls, entity_name)
    if issues: logger.warning(...)            # warn-only in sample mode
    sample = df.sample(n=sample_validation_size, random_state=42)
```

Only two nodes pass `sample_validation_size=10_000`: `export.py:69` and `feature_transactions.py:344`. Because the gateway's default is `full` (`:116`) and `metrics.py:133` calls it with no policy/size, gold/platinum small tables validate fully. `validate_schema` prefilter sends required-field nulls to quarantine, not deletion (`validation.py:53-73`).

**Persistence ownership.** Every published output has exactly one `materialize_*` node plus a `materialize_*_quarantine` companion generated from the registry (`materialization.py:40-59`). `pipeline.py:204-208` disables the Hamilton sqlite cache for all materializers, quarantine materializers, and the 24 `ingest` outputs.

**Failure/exit surfaces.** `main.py` has **no** try/except around `run_pipeline`; exceptions propagate as tracebacks and `main()` returns `None`, so a failed run exits 0 only if the exception is swallowed — it is not, so Python exits 1 on uncaught. The only deliberate handlers in `main.py` are `--visualize` (`:89-96`, warn-and-continue) and the optional SDK import (`pipeline.py:75-81`). Hard failures inside the DAG: `pipeline.py:174-178` (tracking enabled without SDK), `:311-312` (`RuntimeError` for missing final_vars), `pipeline.py:158` (`ValueError` unknown stage), `config.py:69` and `:203` (pydantic `ValueError` at import time), `feature_transactions.py:99,107,120` (`ValueError` on date/month/freshness contract), `contracts.py:11` (`ValueError` missing columns), `validation_gateway.py:147,150` (`fail` policy), `cleaning.py` coverage gate (per `SegmentCoverage` thresholds, `config.py:46-53`).

Scripts do declare exit codes: `export_app_data.py:68` (0/1/2), `40_refresh_rolling.py:32` (0/1/2, `main() -> int`, blanket `except Exception: logger.exception(...); return 1` at `:247-249`), `00_sync_data.py:258-263` (`sys.exit(1)` for missing R2 creds), `v2_observed.py:990 sys.exit(main())`, `check_core_coverage.py:82 raise SystemExit(main())`, `generate_catalog.py:608 sys.exit(1)`.

**Observability.** Structured-ish stdlib logging only: `setup_logging` routes ≤INFO to stdout and ≥WARNING to both (`logging_config.py:74-93`). No metrics endpoint, no health check, no Prometheus/OTel. The sole numeric telemetry is the SQLite quality DB (`data/pipeline/quality_metrics.db` via `layer_writer.py:103`), written per published output with duplicate/null/row counts (`data_quality.py:82-127`) and 3σ / 50%-change anomaly detection (`:206-244`). Hamilton tracking is an opt-in adapter (`pipeline.py:180-190`).

**Ingestion failure policy.** `components/ingestion/datagov.py:115` raises `RuntimeError("Core dataset fetch failed: …")` for required sources and `:116` warns + returns empty for optional ones; empty bronze cache is treated as a miss at `:105`, `:175`, `:502`. Manifests are observability-only (`bronze.py:15-16`, `warn_if_stale` at `:164`).

**CLI/entry points.** Supported production path is `main.py → build_pipeline() → run_pipeline()` (skill: change-hamilton-pipeline, "Runtime contract"). `run_pipeline` accepts `settings, data_path, final_vars, stage, dr, geocoder, pipeline_as_of_date` and returns `{name: result}` for exactly the requested `final_vars` (`pipeline.py:309-313`). `main.py:83` computes `final_vars` for logging but passes the raw `args.final_vars` down (`:102`) — deliberate per the inline comment at `:98-101`.

## Architecture

Three concentric surfaces:

- **Pipeline (supported):** `main.py` → `pipeline.build_pipeline/run_pipeline` → Hamilton driver over 9 modules (`pipeline.py:83-93`). Five stages (`STAGE_VARS:101-138`): `ingest` (24 raw nodes, hard-coded list), `clean`/`features`/`export`/`metrics` (registry-derived via `outputs_for_stage`), `all` (= `TERMINAL_OUTPUTS`, 5 names). DI values are injected as Hamilton inputs, lazily materialized only if upstream-required (`pipeline.py:289-308`), including the URA secret (`:307-308`).
- **Persistence:** computing nodes are pure; `materialization.py` writes via injected `LayerWriter` (`TrackedWriter` in prod, `SimpleWriter` in tests) with atomic tmp+`os.replace` (`layer_writer.py:36-46`). Path resolution has two parallel implementations: `Settings.layer_paths`/`layer_dir` (`config.py:178-194`) and `resolve_layer_paths` (`layer_writer.py:49-59`), the latter documented as "mirrors" the former.
- **Publication:** `scripts/export_app_data.py` → 7 gzipped JSON assets + `dashboard-release.json` (sha256 per asset, staged `.tmp` then `os.replace`, `:301-320`, `:600-680`); `scripts/v2_observed.py` → immutable observed pack + `dashboard-release-v2.json`; both read only `04_platinum/unified_dataset.parquet` and `04_platinum/metrics/pa_monthly_metrics.parquet`. `scripts/generate_catalog.py` → `data/catalog/catalog.jsonl`, gated in CI by `scripts/tools/check_catalog.py`.

Operational scripts: `00_sync_data.py` (R2, two prefixes `manual/` and flat `geocache/*` excluding `cache/hamilton/`, size-tolerance 100 B idempotency, 16-way thread pool), `99_cleanup.py` (`CacheManager.clear()` + quarantine retention by mtime vs `quarantine_retention_days`), `40_refresh_rolling.py` (patterns derived from `STALE_WARN_DAYS`, `--stale-only/--all/--run/--dry-run`, in-process `run_pipeline`).

Tests/CI: 48 test modules (20,277 lines) covering adapters, ingestion, schemas/gateway, DAG smoke, materialization, export, scripts (`test_sync_data.py`, `test_refresh_rolling.py`, `test_catalog_generator.py`, `test_quality_report.py`, `test_v2_observed.py`, `test_export_app_data.py`). CI (`ci.yml:55-95`) runs full `pytest` with coverage, then `check_core_coverage.py --min-coverage 70` over 15 named core modules (`check_core_coverage.py:11-27`). `pip-audit --skip-editable` is its own job (`:42`). `mypy` file list (`pyproject.toml:149-161`) excludes `schemas/`, `utils/{bronze,data_quality,validation?}` — `validation.py` is absent from the mypy list though it is in the coverage list.

Prior audit state is stale/superseded and must not be inherited: `2026-04-28-code-audit-findings.md:3` marks itself superseded and notes "the modules cited below no longer exist"; the 2026-09-07 program and 2026-09-10 roadmap both report complete (2026-09-11/12) with 793 tests; the 2026-09-11 handoff lists remaining items at baseline `4eeda3f`, far behind `449b921`.

## Highest-value paths for later analysis

1. `src/egg_n_bacon_housing/utils/validation_gateway.py:111-183` — policy semantics, sample-mode warn-vs-fail asymmetry, `_source_index` masking, `empty_extracted` shape (`:30-38`).
2. `src/egg_n_bacon_housing/utils/validation.py:36-135` — non-unique index reset, required-field prefilter divergence from pydantic, chunk fallback loop.
3. `src/egg_n_bacon_housing/pipeline.py:215-313` — stage/materialization target resolution, `execution_vars` dedupe, `hasattr(dr, "list_available_variables")` branch for test drivers (`:278`), `upstream` computation.
4. `src/egg_n_bacon_housing/components/materialization.py:131-170` — duplicate persistence surface (DAG nodes vs `__getattr__` direct calls).
5. `src/egg_n_bacon_housing/utils/layer_writer.py:49-59` vs `config.py:178-194` — duplicated layer-path resolution.
6. `src/egg_n_bacon_housing/components/features.py:226-247` — broad `except (ValueError, KeyError)` degrade-to-NA.
7. `src/egg_n_bacon_housing/components/feature_transactions.py:83-126` — hard-fail time/freshness contract.
8. `src/egg_n_bacon_housing/components/metrics.py:26-35, 130-139` — `isinstance(result, pd.DataFrame)` compatibility branches.
9. `scripts/export_app_data.py:1638-1780` — export orchestration, manifest/index consistency, atomic-swap ordering.
10. `scripts/00_sync_data.py:113-202` — R2 transfer paths, `future.result()` propagation, no checksum verification (size-only).
11. `scripts/40_refresh_rolling.py:228-249` — blanket `except Exception` → exit 1.
12. `scripts/99_cleanup.py:28-38` — mtime-based quarantine deletion, no dry-run.
13. `.github/workflows/ci.yml:55-95` + `scripts/tools/check_core_coverage.py:11-27` — coverage gate scope vs mypy scope.
14. `src/egg_n_bacon_housing/utils/data_quality.py:98-127, 206-244` — sampled duplicate counts, Welford update.
15. `src/egg_n_bacon_housing/components/ingestion/datagov.py:64-125, 167-222` — required vs optional source failure policy, empty-cache-as-miss.

Measured counts: 50 modules under `src/` (10,248 lines), 30 under `scripts/` (33,699, of which 19,899 are `scripts/tools/*_evidence.py`), 48 test modules (20,277); 12 published outputs, 5 stages, 24 ingest-stage nodes, 9 DAG modules, 15 core-coverage modules, 7 app JSON assets.
