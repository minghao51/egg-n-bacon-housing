# Phase 1 discovery — observations and measurements

Baseline `449b921d499a8c55ec1eacb1a423baa7632456d3` (2026-11-23 UTC, clean tree). This report records **observations and measurements only**: no severity, no findings, no remediation judgments. Status of every section is `CONFIRMED` measurement unless marked otherwise. Evidence lives in [`evidence/`](evidence/); commands and result logs are catalogued in [`evidence/execution-provenance.md`](evidence/execution-provenance.md).

**Method classes (kept distinct throughout):**

- **Automated census** — mechanical scans (`complexity.csv`, `public-entrypoints.csv`, `error-surfaces.csv`, `observability.csv`, `schema-declarations.csv`, `inventory.json`), explicitly `automated-scan; unreviewed`.
- **Bounded semantic reads** — [`evidence/discovery-core.md`](evidence/discovery-core.md) (full-read list + explicit unread list) and [`evidence/discovery-ui.md`](evidence/discovery-ui.md) (partial, stopped at turn limit).
- **Executed checks** — pytest, `bun run test:unit`, `validate-data`, `verify_reporting_baseline.py` (fresh runs, this audit).
- **Static checks** — ruff, mypy, `astro check` (analysis only; not test execution).

No full semantic completeness is asserted for any area. Absence of a row in a census is not proof of absence of behaviour (`evidence/discovery-inventory.md` §11). **Explicit gap:** exhaustive semantic per-entry behaviour review (every entrypoint/error row read individually) is not done and is deferred; the mechanical indexes plus the bounded semantic reads below are the Phase 1 record.

**Snapshot note:** the canonical tracked-file count is **820**. An interim figure of 821 counted one self-generated audit artifact; `inventory.json` `scope` now records `tracked_files_at_head: 820` with the audit-written artifacts listed under `self_excluded_audit_artifacts` and excluded from every statistic.

---

## 1. Structure, categories, LOC, module counts

Automated census: [`evidence/inventory.json`](evidence/inventory.json), [`evidence/full-file-tree.txt`](evidence/full-file-tree.txt), [`evidence/discovery-inventory.md`](evidence/discovery-inventory.md).

Category tree (820 tracked files):

| Category                    | Files |     | Category                                                                                    |  Files |
| --------------------------- | ----: | --- | ------------------------------------------------------------------------------------------- | -----: |
| docs:evidence-and-plans     |   270 |     | data:tracked-input                                                                          |     12 |
| web:source                  |   156 |     | web:config                                                                                  |      8 |
| artifact:published-web-data |    88 |     | notebook                                                                                    |      6 |
| web:test                    |    65 |     | docs:root                                                                                   |      5 |
| python:test                 |    49 |     | web:script                                                                                  |      4 |
| python:source               |    48 |     | config:repo                                                                                 |      3 |
| design-asset                |    34 |     | ci:workflow                                                                                 |      2 |
| docs:agent-context          |    32 |     | docs:web                                                                                    |      2 |
| python:script               |    30 |     | config:python-manifest                                                                      |      2 |
|                             |       |     | config:env-template / config:secret-scan-baseline / python:entrypoint / config:web-manifest | 1 each |

Source LOC (350 measured files; 6 notebooks separate):

| Area                                      |   Files |    Physical |       Code |
| ----------------------------------------- | ------: | ----------: | ---------: |
| Python `src/`                             |      48 |      10,248 |      8,181 |
| Python `tests/`                           |      49 |      20,277 |     15,830 |
| Python `scripts/` (incl. `scripts/tools`) |      30 |      33,699 |     30,404 |
| `main.py`                                 |       1 |         109 |         88 |
| Web `app/src`                             |     153 |      33,485 |     27,607 |
| Web `app/tests`                           |      61 |      15,889 |     13,124 |
| Web `app/scripts`                         |       4 |         891 |        758 |
| CSS                                       |       1 |         266 |        232 |
| **Total**                                 | **350** | **115,034** | **96,376** |

Test:source ratio — Python 1.94× by code lines (1.02× by files); web 0.48× (0.40× by files).

Top-level modules (code lines): Python `scripts/tools` 27,200 (24 files) · `tests` 15,830 (49) · `components` 3,356 (14) · `utils` 3,299 (21) · `scripts` 3,204 (6) · `adapters` 803 (6) · root 431 (3) · `schemas` 292 (4) · `main.py` 88. Web `components` 17,411 (86) · `tests/unit` 9,068 (35) · `utils` 6,419 (29) · `tests/e2e` 4,056 (26) · `pages` 2,168 (19) · `types` 720 (5) · `hooks` 662 (8).

Semantic-read structure (`evidence/discovery-core.md`): one entrypoint `main.py:1-109` → `src/egg_n_bacon_housing/pipeline.py:1-313` over a 9-module Hamilton DAG (`pipeline.py:83-93`); five stages (`pipeline.py:101-138`); publication scripts `scripts/export_app_data.py`, `scripts/v2_observed.py`, `scripts/generate_catalog.py`. Frontend: 19 Astro route sources (`evidence/discovery-ui.md` §1), `client:only`/`client:load` island split (`app/src/pages/explore.astro:84`, `app/src/pages/dashboard/index.astro:98`).

## 2. Per-file complexity (measurement only)

[`evidence/complexity.csv`](evidence/complexity.csv) — 350 rows, columns `path, lines, exported_public_symbols, external_imports, max_nesting_estimate, size_flag, ext, category, code/comment lines, internal/external imports, parse_ok`. Independent recount from the CSV: `size_flag` `>500` **62**, `>300` **54** (116 files over 300 lines total), 234 unflagged. Parse failures: **0** (Python `ast` 3.12; TS via repo `typescript@5.9.3`).

Threshold candidates (measurement, no judgment): largest files `scripts/tools/school_quality_evidence.py` 2,846 lines, `lease_decay_evidence.py` 2,681, `findings_evidence.py` 2,630; largest non-evidence script `scripts/export_app_data.py` 1,817; largest test `tests/test_ingestion.py` 2,026; largest web source `app/src/components/studies/lib/edition-registry.ts` 1,173.

`max_nesting_estimate` maxima = 7: `scripts/generate_catalog.py`, `app/src/components/explorer/ExplorerWorkspace.tsx`, `ExplorerMap.tsx`, `ExplorerList.tsx`; 6 in e.g. `src/egg_n_bacon_housing/utils/cache.py`, `components/ingestion/geojson.py`, `scripts/00_sync_data.py`. **Limitation (per CSV row text and `discovery-inventory.md` §6): block-nesting depth only — not cyclomatic complexity.** Notebooks measured separately in [`evidence/complexity-notebooks.csv`](evidence/complexity-notebooks.csv).

## 3. Manifests and direct dependencies

Manifest inventory (`inventory.json` `manifests`, 19 tracked): `pyproject.toml`, `uv.lock`, `package.json`, `app/package.json`, `app/bun.lock`, `app/tsconfig.json`, `app/astro.config.mjs`, `app/tailwind.config.mjs`, `app/playwright.config.ts`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`, `.secrets.baseline`, `.env.example`, `.bun-version`, `app/.bun-version`, `.gitignore`, `app/.gitignore`, `data/catalog/descriptions.yml`. `git ls-files` found no requirements/Pipfile/setup/Docker dependency manifests (`evidence/discovery-dependencies.md`).

Direct-dependency tables: **delivered** in [`evidence/discovery-dependencies.md`](evidence/discovery-dependencies.md) (agent self-reports `aborted` at turn limit; tables read in full here). Summary of its measurements, each row cited there to `pyproject.toml` line / `uv.lock` record / `app/package.json` line / `app/bun.lock` record:

- Python runtime+tracking: 15 direct deps (`pyproject.toml:8-26`), locked 308 lock records. Dev group 15, research group 25 (`pyproject.toml:31-74`); build backend `hatchling` (`pyproject.toml:78-79`) declared but **absent from `uv.lock`** (recorded there as observed, not judged).
- Frontend: 25 runtime deps (`app/package.json:36-61`), 1 dev (`@playwright/test`, `:30-31`), 1 peer (`typescript`, `:33-34`); `app/bun.lock` 671 records, all SHA-512 integrity. Root `package.json:1-6` declares no dependencies (verified: metadata only).
- Pins: Bun **1.2.23** in `.bun-version:1` and `app/.bun-version:1` (both tracked, both read, identical) and hard-coded `bun-version: "1.2.23"` at `.github/workflows/ci.yml:105,132`, `deploy.yml:27`. Python `>=3.12` (`pyproject.toml:6`), no exact interpreter pin.
- Lock/audit observations (fresh, 2026-11-23 04:08 UTC registry queries; raw records persisted in-repo as [`evidence/dependency-registry.jsonl`](evidence/dependency-registry.jsonl), [`evidence/dependency-pip-audit.txt`](evidence/dependency-pip-audit.txt), [`evidence/dependency-bun-audit.txt`](evidence/dependency-bun-audit.txt)): pip-audit frozen core+dev = 165 deps, no advisories (exit 0); all groups = 303 deps, 238 raw advisory records / 23 packages (exit 1); `bun audit` = 110 raw advisory records / 24 package names (exit 1). **Not unique CVE counts, not exploitability claims** — raw tool records with duplicate/alias representations. Packages with returned CVE aliases listed in `discovery-dependencies.md` (langchain, langchain-experimental, langgraph, langgraph-checkpoint, marimo; npm: astro, dompurify, katex).
- Usage census marks `rapidfuzz`, `pytest-mock`, `pytest-asyncio`, `cachetools`, `ipywidgets`, `kaleido`, `langchain*`, `langgraph*`, `lifelines`, `marimo`, `prophet`, `pygwalker`, `seaborn`, `supabase`, `tabulate`, `polars` (commented imports only) as N = "no executable import or CLI/config reference found in tracked-source scans" — **not proof of unusedness** (its §Scope).

**Dependency evidence boundary:** the per-dependency constraint/locked/latest/usage tables are delivered. Maintenance/ownership-health, complete transitive license review and other-platform applicability were not established (see the source report's §Evidence boundaries); these are audit gaps, not pending vulnerability conclusions. Separately, the pinned approved-editions gate vs semantic reproducibility of evidence producers is an open item for Phase 2 review (see §8), not decided here.

Historical context (not fresh repro): `docs/implementation/2026-11-22-dependency-audit.md:132-148` records six producer `--check` drifts already present at HEAD (`lease_decay`, `mrt_impact`, `school_quality`, `price_forecasts`, `spatial_hotspots`, `findings`), with causes measured from its ledger, and states nothing was regenerated. Recorded here as evidence-production contract documentation; not re-executed this audit.

## 4. Contracts, runtime validation, co-location, versioning

Bounded semantic read (`evidence/discovery-core.md`); spot-checked lines below verified against source.

- **Registry co-location.** Single published-output registry `src/egg_n_bacon_housing/utils/output_registry.py:23-54`: 12 `PublishedOutputSpec` entries; `PUBLISHED_LAYERS`/`MATERIALIZER_MAP`/`QUARANTINE_MATERIALIZER_MAP` derived (`:55-58`); `TERMINAL_OUTPUTS` at `:60`. Verified by AST count: **6** terminal (`unified_dataset`, `planning_area_360`, `town_360`, `block_profile`, `pa_monthly_metrics`, `appreciation_hotspots`). `outputs_for_stage` at `:63-65`.
- **Schema co-location.** `catalog_dataset_id` ClassVars at `src/egg_n_bacon_housing/schemas/clean_models.py:39,56,77`, `feature_models.py:18,71,160,177,216,239`, `platinum_models.py:21,27,49`; `schemas/__init__.py:3-9` re-exports only the three platinum models (per `discovery-core.md`).
- **Runtime validation gateway.** Policy literal `large_table_validation_policy: Literal["sample","full","fail"] = "sample"` at `src/egg_n_bacon_housing/config.py:27`; sample branch at `src/egg_n_bacon_housing/utils/validation_gateway.py:156` (warn-only precheck, seeded sample `n=sample_validation_size`). Only two call sites pass `sample_validation_size=10_000`: `components/export.py:66-70` (verified) and `components/feature_transactions.py:347-351` (verified); `components/metrics.py:133,238` call with no policy/size. Required-field nulls go to quarantine, not deletion (`utils/validation.py:53-73`, per `discovery-core.md`).
- **Persistence.** One `materialize_*` node + registry-generated quarantine companion per output (`components/materialization.py:40-59`); Hamilton sqlite cache disabled for materializers and the 24 `ingest` outputs (`pipeline.py:204-208`) (per `discovery-core.md`).
- **Versioning.** Only publication manifests carry schema versions: `scripts/export_app_data.py:155` `RELEASE_SCHEMA_VERSION = "1.0.0"` (verified; checked at `:626`); `scripts/v2_observed.py:58-59` `SCHEMA_VERSION = "2.1.0"`, `METHOD_VERSION = "observed-aggregates-2"` (verified; emitted `:588-589`). No version field on `Settings`, schemas, or bronze manifests — `record_bronze_fetch` stores `source`/`rows`/`fetched_at` only (`utils/bronze.py:118-128`, per `discovery-core.md`).
- **Frontend contracts.** Legacy manifest schema `1.0.0` with runtime verification (`app/src/utils/release-manifest.ts:1`); observed v2 schema `2.1.0`, states `ready|absent|invalid` (`app/src/utils/observed-pack-loader.ts:1`, `observed-pack-build.ts:1`); Zod frontmatter collections (`app/src/content.config.ts:13`); release selector defaults to legacy unless exactly `v2` (`app/src/config/observed-release.ts:21`) (`evidence/discovery-ui.md` §3).

## 5. Entrypoints, I/O, failure, dry-run, non-interactive

Census: [`evidence/public-entrypoints.csv`](evidence/public-entrypoints.csv) — 2,596 rows / 272 files, `automated-scan; unreviewed`; kinds include 31 `cli-main-guard`, 19 `route`, 3 `default-export`. Executed I/O checks (fresh, `evidence/execution-provenance.md`): `bun run validate-data` — **19 assets validated**, legacy release `0e1013ee485f`, v2 pack `2c30e2aa836c` (cutoff 2026-10, 10 periods, 1,840 observations, 47,104 month cells) (`evidence/data-validation.log`); `scripts/tools/verify_reporting_baseline.py --assets` — 15 frozen sources, 0 live sources, **72 pinned assets verified, bytes match** (`evidence/reporting-baseline.log`).

- **Main CLI.** `main.py:25` `def main()`; flags `--stage --final-var --refresh --log-level --visualize` (`main.py:1-109`). `final_vars` computed for logging at `main.py:83` but raw `args.final_vars` passed at `main.py:102` (deliberate; inline comment `:98-101`). **No try/except around `run_pipeline`** (verified: only handler is `--visualize` warn-and-continue at `main.py:89-96`); uncaught exceptions exit 1 via `if __name__ == "__main__": main()` (`main.py:107-108`).
- **Script exit surfaces** (per `discovery-core.md`): `scripts/export_app_data.py:68` (0/1/2), `scripts/40_refresh_rolling.py:32` (`main() -> int`) with blanket `except Exception` → 1 at `:247-249`, `scripts/00_sync_data.py:258-263` (`sys.exit(1)` missing R2 creds), `scripts/v2_observed.py:990`, `scripts/tools/check_core_coverage.py:82`, `scripts/generate_catalog.py:608`.
- **Dry-run.** `scripts/40_refresh_rolling.py` supports `--stale-only/--all/--run/--dry-run` (patterns from `STALE_WARN_DAYS`); `scripts/99_cleanup.py:28-38` deletes quarantine by mtime with **no dry-run** (per `discovery-core.md`).
- **Non-interactive.** No prompt/consent surface found in bounded reads; secrets injected as Hamilton inputs incl. URA secret (`pipeline.py:307-308`). Ingestion failure policy: required source raises `RuntimeError`, optional warns+empty (`components/ingestion/datagov.py:115-116`).
- **Web entry.** Route inventory (19 Astro routes) and island boundaries in `evidence/discovery-ui.md` §1–2; browser data URLs incorporate `BASE_URL` (`app/src/utils/catalog.ts:8`, `app/src/constants/data-urls.ts:7`).

## 6. Error and observability indexes (bounded)

Mechanical indexes (exhaustive over tracked source, **unreviewed**):

- [`evidence/error-surfaces.csv`](evidence/error-surfaces.csv) — 596 rows / 117 files: `raise` 217, `throw` 168, `except` 128, `catch` 56, `sys.exit` 26, `process.exit` 1. Every row `automated-scan; unreviewed`.
- [`evidence/observability.csv`](evidence/observability.csv) — 349 files: `logger` calls 292, `print` 277, `console` 33, `logging.*` module calls 0; 273 of 349 files have zero logging calls.
- [`evidence/schema-declarations.csv`](evidence/schema-declarations.csv) — 432 rows / 106 files: interface 263, type-alias 131, pydantic-model 21, dataclass 6, pydantic-settings 5, protocol 3, namedtuple 1, typeddict 1, zod-object 1.

Semantic-read coverage of error paths is **bounded**: `discovery-core.md` maps hard-failure sites (`pipeline.py:174-178,311-312`, `pipeline.py:158`, `config.py:69,203`, `feature_transactions.py:99,107,120`, `utils/contracts.py:11`, `validation_gateway.py:147,150` fail-policy) and `discovery-ui.md` §4 maps eight frontend error boundaries with candidate tests (leads only). Observability semantics: stdlib logging routing ≤INFO→stdout, ≥WARNING→both (`utils/logging_config.py:74-93`); SQLite quality metrics DB with 3σ anomaly detection (`utils/data_quality.py:82-127,206-244`); no metrics endpoint/health check found in bounded reads; frontend logging observed as `console.error` (`discovery-ui.md` §4) — **absence claims are bounded, not comprehensive**. No semantic read of all 596 error rows.

## 7. Tests: behavioral vs structural, fresh coverage

**Fresh executed results** (`evidence/execution-provenance.md`): pytest **1136 passed**, 177 warnings (`master-audit-pytest.log`); frontend `bun run test:unit` **534 passed, 0 failed, 34 files** (`master-audit-frontend.log:609-612`); `astro check` 222 files, 0 errors / 0 warnings / 22 hints; `validate-data` and `verify_reporting_baseline.py` pass (`data-validation.log`, `reporting-baseline.log`).

**Fresh coverage:** 3,894/4,076 statements, **95.53% line** (no branch coverage) — `fresh-coverage.log`, `/tmp/master-audit-coverage.xml` header `line-rate=0.9553` (recomputed matches). Core gate: 15 modules ≥70% (`core-coverage.log`). The ignored worktree `coverage.xml` genuinely records **96/4,076 = 2.36%** (`timestamp` 2026-11-22) — a stale earlier run of the same suite, not the current result (`inventory.json` `coverage_report`; `discovery-inventory.md` §7).

**Behavioral (direct-read verified this audit, not filename guesses):**

- `tests/test_sync_data.py:1-187` — 8 tests; mocked-transport unit tests, "no live S3/R2 access" (`:1-2`), fake boto3 paginator (`:30-40`); assertions on size-skip, prefix scoping, local byte counts.
- `tests/test_validation_gateway.py` — 16 test definitions in the full module; direct read of `:1-160` establishes preserved source values/columns (`:34-40`), rejected-row source identity + reason (`:43`ff), disjoint quarantine, policy equivalence, precheck + `fail` modes.
- `tests/test_property_based.py:1-190` — 8 Hypothesis tests (`:5-6` imports); haversine identity/symmetry/non-negativity, schema roundtrip, negative-price rejection.

**Structural / additional behavioral reads:** `tests/test_pipeline_integration.py:36-73` asserts cache policy, stage keys and graph wiring (structural); `:75-100` checks mocked-driver delegation. `tests/test_export_app_data.py:1-150` checks declared-month and rollover outcomes; `tests/test_v2_observed.py:1-100` checks period/comparator boundaries (behavioral). Remaining Python and frontend test bodies were not exhaustively reviewed. Web counts include helpers: 35 unit-path and 26 E2E-path source files, versus 34 unit-test files and 24 `*.spec.ts` files (`evidence/discovery-ui.md` §1). Playwright E2E was **not executed** this audit (no e2e run in `execution-provenance.md`). `discovery-ui.md`'s critical-path→test table is explicitly inventory-based leads only.

## 8. Documentation inventory and observed contradictions (evidence only)

Docs census: docs:evidence-and-plans 270 · docs:agent-context 32 · docs:root 5 · docs:web 2 (§1 table). Contradictions observed, without resolution or severity:

1. Bun-only setup vs Playwright default `npm run dev` (`app/README.md:17`; `app/playwright.config.ts:5`) — `discovery-ui.md` §6.1.
2. Implementation ledger chronology: RF05 both "in progress" and "complete", plus a later "RF00–RF12 not started" paragraph (`docs/implementation/README.md:7,8,47`) vs current code containing v2 loaders/defaults/edition route — §6.2.
3. Catalog discrepancy copy vs current equal row counts (`docs/implementation/README.md:79`; `app/src/constants/catalog-audit.ts:40`; `app/src/pages/catalog/[layer]/[...dataset].astro:35`) — §6.3.
4. Area-page comment ("no client island") vs section/history islands (`app/src/pages/areas/[slug].astro:5,213,393`) — §6.4.
5. Edition narrative chronology: 15 approved vs older 13-historical statements (`docs/implementation/README.md:26,32`; `app/src/pages/analytics/[slug].astro:160`) — §6.5.
6. Historical Astro/Playwright counts in the ledger not re-executed (`docs/implementation/README.md:103,145,220`) — §6.6.
7. **Terminal-output count:** `docs/guides/operations-runbook.md:108` "Exactly six terminal frames" and `docs/guides/pipeline-development.md:22` "six terminal frames" agree with the registry (verified: 6 terminal specs, `output_registry.py:23-54,60`); `evidence/discovery-core.md:83` parenthetical "`TERMINAL_OUTPUTS`, 5 names" contradicts code+docs — **reconciled as a scout evidence-report error**, not a code or documentation defect. The authoritative count is six.

Checked and **not** a contradiction: `docs/guides/operations-runbook.md:134` cites `app/.bun-version`; both `.bun-version:1` and `app/.bun-version:1` are tracked and both read `1.2.23` (verified). Consistent.

Prior audit documents (`docs/plans/2026-04-28-code-audit-findings.md`, 2026-09-07/10/11 programme docs) are self-marked superseded or far behind this baseline (`discovery-core.md` "Prior state"); **no historical finding is adopted as current** here.

Open item recorded for Phase 2 (not decided here): pinned approved-editions gate vs semantic reproducibility of evidence producers, alongside the 2026-11-22 drift record (`docs/implementation/2026-11-22-dependency-audit.md:132-148`; nothing regenerated).

---

## Evidence index

| Artifact                                                                                                                                                                                                                                       | Content                                                                               |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| [`evidence/execution-provenance.md`](evidence/execution-provenance.md)                                                                                                                                                                         | commands, results, log map, coverage XML headers                                      |
| [`evidence/inventory.json`](evidence/inventory.json) · [`full-file-tree.txt`](evidence/full-file-tree.txt) · [`raw-measurements.json`](evidence/raw-measurements.json)                                                                         | scope, categories, LOC, manifests, thresholds                                         |
| [`evidence/complexity.csv`](evidence/complexity.csv) · [`complexity-notebooks.csv`](evidence/complexity-notebooks.csv)                                                                                                                         | per-file size/nesting/imports                                                         |
| [`evidence/public-entrypoints.csv`](evidence/public-entrypoints.csv) · [`error-surfaces.csv`](evidence/error-surfaces.csv) · [`observability.csv`](evidence/observability.csv) · [`schema-declarations.csv`](evidence/schema-declarations.csv) | mechanical indexes (unreviewed)                                                       |
| [`evidence/discovery-core.md`](evidence/discovery-core.md) · [`discovery-ui.md`](evidence/discovery-ui.md) · [`discovery-inventory.md`](evidence/discovery-inventory.md) · [`discovery-dependencies.md`](evidence/discovery-dependencies.md)   | bounded semantic reads / worker reports                                               |
| `evidence/*.log`                                                                                                                                                                                                                               | fresh pytest, frontend, quality, coverage, data-validation, reporting-baseline output |
| [`evidence/measurement/`](evidence/measurement/)                                                                                                                                                                                               | re-runnable census tooling (`measure.py`, `indexes.py`, `ts_measure.mjs`)             |
