# WS20 — Hermetic DAG Smoke Test (D4, Batch 5)

## Context
The rental-yield join bug (Batch 1 WS2) was a GRAPH-LEVEL defect: every unit test passed because fixtures exercised node-shapes production never produces. No test today runs `build_pipeline()` → `run_pipeline()` end-to-end. This WS adds a hermetic, mocked-transport, full-graph smoke test — the regression net for wiring/contract drift.

## Read first
- `.agents/skills/change-hamilton-pipeline/SKILL.md` + `.agents/skills/change-data-ingestion/SKILL.md` (both mandatory — mocked transport, no live services)
- `pipeline.py` (`build_pipeline`, `run_pipeline`, `STAGE_VARS`, injection params incl. `geocoder`), `main.py`
- `tests/test_pipeline_integration.py` (existing integration style — do not duplicate; smoke goes further: full DAG, tiny data)

## Owned files (EXCLUSIVE)
- `tests/test_dag_smoke.py` (NEW)

## Forbidden
Everything else — this WS edits NO production code. `tests/conftest.py`, `pyproject.toml` included.

## Changes

### 1. `tests/test_dag_smoke.py`
- One (maybe two) pytest test(s) running the FULL DAG in a tmp data tree:
  - **Fixtures (tmp)**: minimal manual CSVs (HDB resale pre-2017 + URA condo history — read `components/ingestion/datagov.py`/`ura_csv.py` for the exact expected schemas/paths incl. injected `manual_dir` from WS15); minimal `bronze/external/*.geojson` seeds (see `utils/bronze.EXPECTED_EXTERNAL_FILES` + the registry test's list); tiny school/MRT reference JSONs where the fallback path would otherwise warn.
  - **Transport mocks**: patch at the `requests.Session` level (adapters now use module/thread-local sessions — patch `requests.Session.request` or the session objects' `get/post`) to serve canned data.gov.sg / OneMap / URA / LTA responses. Keep payloads MINIMAL but schema-faithful (a few rows each).
  - **Geocoder**: inject the `InMemoryGeocoder` (utils/geocoding.py) via `run_pipeline(..., geocoder=...)` — do not mock OneMap for geocoding paths that use the injected geocoder.
  - **Config**: `Settings` with tmp `data_path`, `use_caching` on (exercise the cache adapter), `large_table_validation_policy="full"`, small thresholds so the tiny data passes coverage gates (per-type thresholds from WS16 — set condo threshold low).
- **Assertions**:
  - `run_pipeline(stage="all")` returns all 5 published final vars (no missing).
  - Every `_PUBLISHED_LAYERS`/`PUBLISHED_LAYERS` output file exists in the right layer dir (incl. platinum + metrics + the `L5_` alias).
  - `rental_yield_pct` is NON-NULL on at least one `transactions_enriched` row — pin the original critical bug at graph level.
  - `unified_dataset` row count == `transactions_enriched` row count (pass-through contract).
  - No quarantine files produced by the happy-path fixtures (quarantine presence = fixture bug, fail loudly with path listing).
  - `bronze_manifest.json` exists with ≥1 entry.
- Mark `@pytest.mark.slow`-style only if the repo has such a marker (check `pyproject.toml` `[tool.pytest.ini_options]`; if none, leave unmarked but keep runtime < ~60s — if impossible, report and we add a marker decision).

### 2. Fixture payloads as inline dicts/JSON strings in the test file (no new data files in the repo).

## Verification
```
uv run pytest tests/test_dag_smoke.py -x -q
uv run ruff check tests/test_dag_smoke.py && uv run ruff format --check tests/test_dag_smoke.py
uv run pytest tests/test_pipeline_integration.py -q   # no interference
```

## Constraints
- NO commits. NO production-code edits — if the DAG cannot be made hermetic without a code change (e.g., a hardcoded path), STOP and report the exact blocker; do not hack around by editing owned-by-others files.
- Hermetic: no network, no `data/` dependency, no dotenvx requirement.

## Definition of done
Full-graph smoke test green, hermetic, pins the rental-join + pass-through + published-files contracts; runs in the normal suite.

## Report back
Test structure, fixture inventory (which sources mocked how), runtime, any hermeticity blockers found (report-only), verification tail.
