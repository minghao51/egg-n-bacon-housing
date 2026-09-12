# Code Audit Remediation Roadmap

**Date:** 2026-09-10
**Status:** Completed (2026-09-12) — all items landed and verified; closeout evidence appended to `docs/plans/2026-09-11-hamilton-dag-e2e-evidence.md`
**Scope:** Phased remediation of the 2026-09 scout/reviewer code audit (1 critical, dead code, DRY, optimization, gaps/hygiene), extended with test/CI hardening, docs/plans bookkeeping, and a final end-to-end validation pass.

> **Completed 2026-09-12.** The four-work-order Hamilton sequence plus every
> audit follow-up below landed and verified. Handoff doc:
> `docs/plans/2026-09-11-code-audit-remediation-handoff.md`; closeout
> evidence: `docs/plans/2026-09-11-hamilton-dag-e2e-evidence.md` (final
> section).
> point — it lists the items verified done on 2026-09-11 (e.g. items 8, 14,
> 25, 26, the Phase 6 renames, and the Phase 7 validation runs) plus
> subagent-ready briefs for the rest;
> treat the phases below as the detailed spec for those briefs.

## Relationship to Prior Plans

Already done — do NOT re-plan (verified against `2026-09-07-src-audit-improvement-program.md` status block and current code):

- Gateway `persist=False`, annual-value join, datagovsg Retry-After/regional mapping, empty-bronze-cache=miss at the 3 datagov sites, token/auth repairs, silent-loss logging, proximity hardening, validation vectorization (owner decision: **keep FULL per-row pydantic** — WO-9), macro/datagov/features/proximity DRY collapse, school-tier rewiring via `school_reference` DI, `DATAGOVSG_BASE_URL` constant import (WO-12).
- DI repositories (`MrtReferenceRepository`, `SpatialReferenceRepository`, `SchoolReferenceRepository`) are wired as Hamilton factories in `pipeline.py` — the audit's "repository shims" are the compatibility leftovers the 2026-09-03 handoff deferred to a later release; **this roadmap is that release**.

Everything below is new work surfaced by the 2026-09 audit.

## Verification Shorthands

- **V-pipe** = `uv run pytest tests/test_pipeline.py tests/test_pipeline_integration.py tests/test_materialization.py --no-cov -q && uv run ruff check . && uv run ruff format --check . && uv run mypy`
- **V-ing** = `uv run pytest tests/test_ingestion.py tests/test_datagovsg.py tests/test_onemap.py tests/test_ura.py --no-cov -q && uv run ruff check . && uv run ruff format --check . && uv run mypy`
- **V-all** = `dotenvx run -- uv run pytest -q` + ruff/format/mypy + `uv run python scripts/tools/validate_docs_layout.py` + `uv run python scripts/tools/validate_agent_skills.py` + `git diff --check`
- Steps touching published schemas/bronze artifacts also run `uv run python scripts/generate_catalog.py` + `uv run python scripts/tools/check_catalog.py`.

Effort: S ≤2h · M half-day · L 1day+.

---

## Phase 0 — Plan bookkeeping (S)

1. This document. · no skill · S.
2. Mark `docs/plans/2026-04-28-code-audit-findings.md` `Status: Superseded` (→ src-audit program; modules it cites no longer exist) and `docs/plans/2026-09-07-src-audit-improvement-program.md` `Status: Completed` (note the one deferred item: quarantine-only persist mode). · no skill · S.
3. Add a status note to `docs/plans/2026-09-03-runtime-dependency-injection-handoff.md`: repository injection landed; compatibility-wrapper removal is scheduled here (Phases 2–3). · no skill · S.
4. **Capture pre-Phase-1 baseline** of published output row counts × columns for the Phase 7 equivalence check. · no skill · S. ✅ **DONE 2026-09-11:** baseline captured in `docs/plans/2026-09-11-hamilton-dag-e2e-evidence.md`.

## Phase 1 — Critical correctness: `--final-var` subset crash (S)

5. **Fix** `src/egg_n_bacon_housing/pipeline.py:278-286`: gate the upstream quarantine-companion loop (`execution_vars.append(_QUARANTINE_MAP[name])`) on `writer is not None` — when no published output is requested (e.g. `--final-var geocoded_properties`), `writer` is `None` and quarantine materializers requiring `writer` must not be appended. The materializer extension for `materialization_targets` already implies `writer` exists — leave as-is. · skill: change-hamilton-pipeline · S · V-pipe. ✅ **DONE 2026-09-11 (Wave 1):** gated on `writer is not None`; live repro `--final-var geocoded_properties` exits 0.
6. **Un-hide the branch**: in `tests/test_pipeline.py`, give `DummyDriver` `list_available_variables()` + `what_is_upstream_of()` stubs so the companion-append block is exercised; add a test asserting `run_pipeline(..., final_vars=["geocoded_properties"])` executes with no `writer` input and writes no parquet; add one real-driver integration test in `tests/test_pipeline_integration.py`. · skill: change-hamilton-pipeline · S · V-pipe. ✅ **DONE 2026-09-11 (Wave 1):** `GraphStubDriver` + 3 unit tests + real-driver integration test.

## Phase 2 — Dead code removal (M)

7. Delete test-legacy repo shims: `utils/mrt_line_mapping.py:302-366` (`_repository` + 5 wrappers; move `get_station_score`'s test to the repository), `utils/school_features.py:99-123` (`_repository` shim, `_load_reference_data`, `load_school_tiers`). Update tests to construct repositories directly. · skills: both · M · V-ing + V-pipe. ✅ **DONE 2026-09-11 (Wave 1).**
8. Delete component facades with `kwargs.pop("writer")`: `components/cleaning.py:31`, `feature_rental.py:23`, `features.py:36`, `feature_transactions.py:33`, `feature_profiles.py:27`, `export.py:24`, `metrics.py:27-45,142-144` — remove the `writer` parameter from computing-node signatures; `writer` is passed only to `materialize_*` companions. · skill: change-hamilton-pipeline · M · V-pipe. ✅ **DONE 2026-09-11:** writer= facades removed from all six compute-node modules + tests.
9. Remove `supply_pipeline` from `components/ingestion/macro.py:134-141,207-210` (`_MACRO_SOURCES` entry + transform): stop fetching/writing; retire its bronze artifact + catalog row; check `docs/data-sources.md`. · skill: change-data-ingestion · S · V-ing + catalog regen/check. ✅ **DONE 2026-09-11 (Wave 1):** source, tests, bronze artifact (`01_bronze/external/`), catalog row retired; docs updated.
10. Remove remaining dead symbols: `utils/validation.py:17-29` (`_is_null_scalar`), `pipeline.py:97` `_PUBLISHED_LAYERS` alias, `components/ingestion/ura_csv.py:90-91,138-139` (`unit_price_psf`/`unit_price_psm`; verify catalog/docs don't document them). `geo.haversine_distance` folds into Phase 3 step 12. · skills: both · S · V-all. ✅ **DONE 2026-09-11 (Wave 1)** except the haversine fold (deferred to step 12 as planned); generated catalog rows still list `unit_price_psf/psm` until the next pipeline run + regen.
11. Purge stale bytecode: orphaned `tests/__pycache__/*.pyc` for deleted sources; root `__pycache__/` (coordinate with Phase 6 `.gitignore`). · no skill · S. ✅ **DONE 2026-09-11 (Wave 1).**

## Phase 3 — DRY consolidation (L)

12. **Shared retry policy** (skill: change-data-ingestion): extend `adapters/_http.py` with one transient-only retry policy (429/5xx/network), Retry-After honored (delta-seconds + HTTP-date), single `MAX_RETRY_AFTER_WAIT`; refactor `adapters/ura.py:71-79` (currently retries permanent 4xx, ignores Retry-After) + `adapters/datagovsg.py:47-61` + `adapters/onemap.py:155` onto it. Add `resource_url()` to `adapters/datagovsg.py`; use at `datagov.py:36`, `macro.py:40`, `geojson.py:394`. Mocked-transport tests: URA permanent-4xx fail-fast + Retry-After. Update failure-policy records in `docs/guides/data-ingestion-development.md`. · M · V-ing. ✅ **DONE 2026-09-11 (Wave 2):** shared `_http` policy (`is_retryable_exception`/`retry_after_wait`/`is_transient_status`, single `MAX_RETRY_AFTER_WAIT`); URA/datagovsg/onemap adopted; `resource_url()` used at datagov/macro/geojson; `tests/test_http.py` + URA fail-fast/Retry-After tests; failure-policy records updated.
13. **Shared geo/quarter helpers**: consolidate `_haversine_metres` (`utils/proximity.py:23-33` vs `utils/school_features.py:457-470`) into `utils/geo.py` (single public `haversine_metres`); unify macro quarter parsing (`macro.py:295-311` lenient `"2024Q"→year 202` vs `macro.py:322-352` strict) onto the strict parser with a malformed-quarter regression fixture; extract point/centroid helper inside `geojson.py:112-125,156-168`. · skills: both · M · V-ing. ✅ **DONE 2026-09-11 (Wave 2):** public `haversine_metres` in `utils/geo.py` (scalar folded); strict `_parse_datagov_quarter` everywhere + malformed-quarter fixtures (`"2024Q"`→NaT); `_point_or_centroid` helper in geojson.py.
14. **Bronze cache helper**: add `read_bronze_cache(..., treat_empty_as_miss=True)` in `utils/bronze.py`; replace the ~7 boilerplate sites (`datagov.py:87-91,183-187,507-510,562-573`, `macro.py:263-267`, `geojson.py:486-488`). Preserve the invariant: empty cache never satisfies, empty fetch never overwrites. Update the bronze-cache sentence in `.agents/skills/change-data-ingestion/SKILL.md`; re-run `validate_agent_skills.py`. Extract `manifest_age_days()` shared by `bronze.py:148-170` and `scripts/40_refresh_rolling.py:73-99`. · skill: change-data-ingestion · M · V-ing. ✅ **DONE 2026-09-11:** `read_bronze_cache` (Wave 1-verified); `manifest_age_days()` extracted + shared by `utils/bronze.py` and `scripts/40_refresh_rolling.py`, bronze-cache sentence updated in the ingestion skill (Wave 3).
15. **Town-merge orchestration**: add `merge_town_context()` to `utils/hdb_lookups.py`; refactor `feature_transactions.py:287-314` and `feature_profiles.py:171-201` onto it; equivalence test on a fixture. · skill: change-hamilton-pipeline · S · V-pipe. ✅ **DONE 2026-09-11 (Wave 2):** `merge_town_context()` + fixture equivalence tests (values + row order).
16. **Materialization via `@parameterize`**: replace the 24 hand-written nodes in `components/materialization.py:11-196` with parameterized node families driven by `utils/output_registry.PUBLISHED_OUTPUTS`. Constraint: emitted Hamilton variable names byte-identical to today's `materialize_*` names; `MATERIALIZER_MAP`/`QUARANTINE_MATERIALIZER_MAP`/`STAGE_VARS` unchanged; warm-run output equivalence check. Update `docs/guides/pipeline-development.md`. · skill: change-hamilton-pipeline · M · V-pipe. ✅ **DONE 2026-09-11 (Wave 3):** both node families expand via `@parameterize` from `PUBLISHED_OUTPUTS`; emitted names byte-identical (pinned by test); maps + `STAGE_VARS` unchanged; PEP 562 `__getattr__` compat for direct calls; guide updated.
17. **Public import**: replace `features.py:21` private `_geocode_schools` cross-module import with a public API in its home module. · skill: change-hamilton-pipeline · S · V-pipe. ✅ **DONE 2026-09-11 (Wave 2):** public `geocode_schools` in `utils/school_features.py`.

## Phase 4 — Test & coverage hardening (M)

18. New `tests/test_cache_fingerprints.py`: cache_fingerprints governs DAG cache identity — key stability, input-sensitivity, serialization round-trip. · skill: change-hamilton-pipeline · S. ✅ **DONE 2026-09-11 (Wave 2).**
19. Tests for load-bearing untested utilities: `utils/contracts.py:4` `require_columns` (miss/all-hit/error cases); `utils/data_loader.py:110-127` polygon-overlap `keep="first"` semantics. · skill: change-hamilton-pipeline · S. ✅ **DONE 2026-09-11 (Wave 2):** `tests/test_contracts.py` + recreated `tests/test_data_loader.py`.
20. **Bronze staleness gates**: extend `utils/bronze.py:77-81` coverage to `raw_hdb_rental` + `raw_rental_index` (currently freeze silently); fix overstated docstrings at `bronze.py:344-352`. Per-dataset stale-gate tests. · skill: change-data-ingestion · M · V-ing. ✅ **DONE 2026-09-11 (Wave 2):** gates 35d/100d with cadence rationale; `clear_bronze` docstring corrected; per-dataset stale-gate tests.
21. Raise CI coverage floor (`.github/workflows/ci.yml`, `check_core_coverage.py --min-coverage 60` → 70) once Phases 1–3 tests land. · no skill · S. ✅ **DONE 2026-09-11 (Wave 3):** measured 95% total, core gate green at 70; CI floor raised 60→70.

## Phase 5 — Optimization (M/L) — one decision gate

22. **Decision made 2026-09-10 (owner): sampled validation for speed.** `large_table_validation_policy` default flips `"full"` → `"sample"` (config.py:23; also feature_transactions.py:137, export.py:31). Parquet is typed storage only — the pydantic boundary enforces semantic constraints parquet cannot (price>0, lat/lon bounds, date>=1990, min_length, required fields) and produces the quarantine trail; sampling keeps a spot-check while going fast. Implementation requirements: ✅ **DONE 2026-09-11 (Wave 3):** precheck covers datetime bounds + `min_length` (model-derived); sample double-count fixed (rejects dropped from valid); default `sample` at config/nodes; full/fail env-selectable; platinum re-validation kept (copy removed); `.env.example` + runbook + guide updated.
    a. Extend `vectorized_precheck` (validation_gateway.py:66-105) to cover datetime bounds (`transaction_date ge 1990`) and string `min_length` — today it only checks numeric-dtype bounds, so sample mode currently loses those constraints entirely. After this, sample mode = 100% vectorized constraint coverage + 10k pydantic spot-check.
    b. Fix the sample-mode double-count: `validation_gateway.py:124` returns `valid=df` including the sample's rejected rows — they appear in BOTH the published frame and quarantine. Drop sampled rejects from `valid`.
    c. Keep `full`/`fail` selectable via env for cold runs/CI.
    d. Resolve `export.py:29-64` `unified_dataset` re-validation: drop it (rows already gold-validated) or route through the same gate.
    e. Update `.env.example`/docs for the new default. Supersedes WO-9's keep-FULL decision (owner override).
    · skill: change-hamilton-pipeline · M · V-pipe.
23. `feature_transactions.py:108,188,224-226`: derive `month` once; eliminate 2 full ~1M-row copies and the no-op round trip at 224-227. Equivalence test (values + row order). · skill: change-hamilton-pipeline · S · V-pipe. ✅ **DONE 2026-09-11 (Wave 3):** month derived once; 2 full-frame copies + round trip removed (~1.1s/run); equivalence tests (values + row order).
24. `geojson.py:509-528`: parse the 9 amenity GeoJSONs once into bronze parquet; raw JSON stays the immutable source of truth; document normalization in the source record. · skill: change-data-ingestion · M · V-ing. ✅ **DONE 2026-09-11 (Wave 3):** 9 amenity parse caches under `external/` (raw JSON immutable); mtime invalidation; never-poison invariants tested; catalog regenerated (+9 rows); source record updated.
25. `utils/cache.py`: unique `.tmp` names (uuid/pid suffix) at 170-174; `clear()` sweeps `*.json.tmp` orphans (196-236); drop double `stat()`. Concurrency test. · skill: change-data-ingestion · S · V-ing. ✅ **DONE 2026-09-11:** `.tmp` names pid+thread-unique + miss-on-vanish, tests in `tests/test_cache.py`; legacy `*.json.tmp` `clear()` sweep done 2026-09-12 (final wave: full clear sweeps all `*.tmp` orphans, test in `tests/test_cache.py`).

## Phase 6 — Docs & repo hygiene (S)

> ✅ Docs renames verified done 2026-09-11 — docs-layout validator passes with zero findings. Items 26 (partial) and 27 remain open.

26. `.gitignore`: add `coverage.xml`, `htmlcov/`, `refresh_*.log`, `__pycache__/`; `git rm --cached` committed artifacts (`coverage.xml`, `htmlcov/`, `refresh_run.log`, `refresh_rerun.log`); delete root `__pycache__/`. · no skill · S. ✅ **DONE 2026-09-11:** `.gitignore` rules present, no committed artifacts; root `__pycache__/` deleted in Wave 1.
27. Docs sweep: `docs/guides/pipeline-development.md` (Phases 3/5), `docs/guides/data-ingestion-development.md` (retry policy, supply_pipeline retirement, amenity parquet), `docs/data-sources.md`. · skills: both · S. ✅ **DONE 2026-09-12:** all three updated across Waves 2–3 (validation-policy text, parameterized materialization, unified retry policy, retirements, amenity parse caches); docs-layout validator clean.

## Phase 7 — Final validation pass (M)

> ✅ Validation runs (warm full run, catalog regen + check, V-all, `pre-commit run --all-files`, pip-audit) done 2026-09-11 — evidence: `docs/plans/2026-09-11-hamilton-dag-e2e-evidence.md`. Final flip to Completed is gated on the remaining phases.

28. Full warm pipeline run: `dotenvx run -- uv run python main.py --stage all`; compare published outputs against the Phase 0 baseline (row counts × columns); targeted `--refresh` smoke for one bronze + one rolling source (`scripts/40_refresh_rolling.py`). · skills: both · M. ✅ **DONE 2026-09-11:** warm full run + baseline comparison complete (`dotenvx` wrapper removed — plain `uv run python main.py --stage all`); baseline + evidence: `docs/plans/2026-09-11-hamilton-dag-e2e-evidence.md`. Targeted `--refresh` smoke done 2026-09-12: `--refresh external/BusStops` (ingest re-parse) + `40_refresh_rolling.py --dry-run`/`--stale-only --run` (all four rolling sources refreshed for real — pre-manifest bronze counted stale, refetched fresh).
29. Regen catalog, run `check_catalog.py`, full **V-all**, `pre-commit run --all-files`, `uv run pip-audit --skip-editable`. Flip this doc to `Status: Completed`; refresh `docs/plans/README.md` audit index. · no skill · S. ✅ **DONE 2026-09-11 + 2026-09-12 closeout:** re-run on the final tree — full recompute run 1:22:53 exit 0 with fresh rolling data; published-output deltas documented (data freshness + sample-mode quarantine); catalog regen (125 datasets) + check; V-all 994 tests; `pre-commit run --all-files`; pip-audit clean. Roadmap flipped to `Status: Completed`; README index refreshed; evidence appended to the evidence doc.

---

## Files to Modify

- `src/egg_n_bacon_housing/pipeline.py` — gate quarantine companions on writer (P1); drop `_PUBLISHED_LAYERS` alias (P2)
- `src/egg_n_bacon_housing/components/materialization.py` — @parameterize from `PUBLISHED_OUTPUTS` (P3)
- `src/egg_n_bacon_housing/components/{cleaning,features,feature_rental,feature_transactions,feature_profiles,export,metrics}.py` — remove `writer` facades (P2); month derivation fix (P5)
- `src/egg_n_bacon_housing/components/ingestion/{macro,datagov,geojson,ura_csv}.py` — supply_pipeline removal, bronze-cache helper, resource_url, quarter parsing, amenity parquet, dead columns (P2/P3/P5)
- `src/egg_n_bacon_housing/adapters/{ura,datagovsg,onemap}.py` — shared retry policy, `resource_url()` (P3)
- `src/egg_n_bacon_housing/utils/{bronze,mrt_line_mapping,school_features,geo,proximity,hdb_lookups,cache,validation,contracts,data_loader}.py` — per phases
- `src/egg_n_bacon_housing/config.py` — resolve inert `sample_validation_size` per decision gate (P5)
- `tests/test_pipeline.py`, `tests/test_pipeline_integration.py`, `tests/test_materialization.py`, ingestion test files — companion test updates
- `.github/workflows/ci.yml` — coverage floor bump (P4)
- `.gitignore` — artifacts (P6)
- `docs/guides/{pipeline-development,data-ingestion-development}.md`, `docs/data-sources.md`, `.agents/skills/change-data-ingestion/SKILL.md` — doc alignment
- `docs/plans/{2026-04-28-code-audit-findings.md, 2026-09-07-src-audit-improvement-program.md, 2026-09-03-runtime-dependency-injection-handoff.md, README.md}` — status bookkeeping (P0/P7)

## New Files

- `src/egg_n_bacon_housing/adapters/_http.py` extensions — shared transient-retry policy (may already exist in part; extend rather than duplicate)
- `tests/test_cache_fingerprints.py`, contracts/data_loader overlap tests — Phase 4 coverage

## Risks

- **Behavior changes masquerading as DRY**: strict quarter parsing (year-202 bug) and URA permanent-4xx fail-fast change runtime behavior — land with regression fixtures, after Phase 1.
- **@parameterize materializers**: variable-name drift breaks `MATERIALIZER_MAP`/`STAGE_VARS`/Hamilton cache keys — byte-identical names + warm-run equivalence check mandatory.
- **Skill/doc contracts**: empty-cache=miss semantics and the ingestion skill text must stay in lockstep (`validate_agent_skills.py`); wrapper removal contradicts the DI handoff unless its status note lands first (Phase 0 step 3).
- **Validation downgrade is intentional**: Phase 5 step 22 flips the default to sampled validation (owner decision 2026-09-10, superseding WO-9). Non-sampled bad rows flow to platinum unflagged — the extended vectorized precheck (step 22a) and the double-count fix (22b) are mandatory parts of that change, not optional polish; keep `full`/`fail` selectable for cold runs.
- **Catalog/CI coupling**: bronze/schema-touching steps require catalog regen or `check_catalog.py` fails; committed-artifact removal must coincide with `.gitignore` or pre-commit re-adds them.
- **Final run needs credentials** (`dotenvx`) and the Phase 0 baseline — baseline captured in `docs/plans/2026-09-11-hamilton-dag-e2e-evidence.md`.
