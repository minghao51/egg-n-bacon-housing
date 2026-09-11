# WS8 — Dead Surface Removal + Shared Lookups (Batch 2a)

## Context
~1/3 of `utils/` is dead or legacy (retired L0-L5 naming era), and the gold feature modules share logic via PRIVATE cross-module imports that have already diverged.

Confirmed dead:
- `utils/data_loader.py:221-256` — `load_market_summary`/`load_planning_area_metrics`/`load_unified_data` + `L3/*` fallback paths: zero non-test callers.
- `utils/data_loader.py:96-141` — STRtree/shapely-prep machinery built and cached but NEVER queried (lookup is a geopandas sjoin path).
- `utils/data_quality.py:24-39` — `DATASET_DUPLICATE_POLICIES` keys are retired names matching nothing written; `infer_quality_stage` (~:90-99) dead in prod path.
- `utils/data_quality.py:302-311, 335-389` — Welford variance stored in columns named `std_rows`/`std_null_pct` (sqrt applied at read in 2 places, `:396`,`:409`).
- `utils/proximity.py:32` + docstring `:59` — documented `schools` parameter is ignored; no caller passes it.

Private coupling:
- `components/feature_transactions.py:13-17` imports `_annual_value_lookup`, `_dwelling_units_lookup`, `_population_lookup` from `feature_profiles`, and `_normalize_hdb_flat_type` from `feature_rental`.
- Duplicated + diverged: income merge (`feature_profiles.py:147-154` unguarded vs `feature_transactions.py:196-215` NaN-guarded — `.astype(str)` turns NaN into literal `"NAN"` key in the profiles copy); `population_per_dwelling` duplicated verbatim.
- `_population_lookup` uses `keep="first"` (`feature_profiles.py:81-84`) while sibling `_dwelling_units_lookup` sums — arbitrary-row selection if multi-row towns exist.

NOTE: Batch 1 already modified `feature_transactions.py` (rental-yield sentinel fix ~:116-121) — preserve it.

## Read first
- `.agents/skills/change-hamilton-pipeline/SKILL.md` (mandatory)

## Owned files (EXCLUSIVE)
- `src/egg_n_bacon_housing/utils/data_loader.py`
- `src/egg_n_bacon_housing/utils/data_quality.py`
- `src/egg_n_bacon_housing/utils/proximity.py`
- `src/egg_n_bacon_housing/utils/hdb_lookups.py` (NEW)
- `src/egg_n_bacon_housing/components/feature_profiles.py`
- `src/egg_n_bacon_housing/components/feature_transactions.py`
- `src/egg_n_bacon_housing/components/feature_rental.py`
- `tests/test_data_loader.py`, `tests/test_data_loader_extended.py`, `tests/test_data_quality.py`, `tests/test_proximity*.py`, `tests/test_feature_profiles.py`, `tests/test_feature_transactions.py`, `tests/test_rental_yield_metrics.py` (extend/prune as described)

## Forbidden
`schemas/*`, `components/features.py`, `utils/school_features.py`, `pipeline.py`, `config.py` (other WS own these concurrently). `tests/test_features.py` (WS9' owns it next batch — if your changes break it, REPORT, do not edit). `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. `utils/data_loader.py`
- Delete `load_market_summary`, `load_planning_area_metrics`, `load_unified_data`, their `L3/` fallbacks, and the unused STRtree/prepared-geometry machinery (keep the `SpatialReferenceRepository` + geopandas sjoin lookup — that's live).
- Keep/trim the test-only `configure()`/`_get()` globals only if remaining code needs them; prefer deleting with the loaders.

### 2. `utils/data_quality.py`
- Delete `DATASET_DUPLICATE_POLICIES`, `get_duplicate_status`, `infer_quality_stage` (and their call sites in `record_dataframe_quality` — duplicate-status logging collapses to the strict default behavior that already effectively applies).
- Fix the std/variance trap: store `sqrt(value)` when writing the Welford result so the `std_*` columns actually contain standard deviation; remove the sqrt-at-read in `check_anomaly` (`:396`,`:409`); update the misleading docstring (`:302-311`).

### 3. `utils/proximity.py`
- Remove the ignored `schools` parameter and its docstring block. Verify no caller passes it first (grep `components/`).

### 4. NEW `utils/hdb_lookups.py` — promote + unify
- Public functions: `annual_value_lookup`, `dwelling_units_lookup`, `population_lookup`, `population_per_dwelling`, `merge_median_income`, `normalize_hdb_flat_type` (moved from `feature_profiles.py:19-113`, `feature_rental.py` flat-type normalizer; drop the leading underscores).
- `population_lookup`: aggregate multi-row towns with `groupby(...).sum()` (consistent with dwelling units) instead of `keep="first"` — add a comment noting the previous arbitrary-row behavior.
- `merge_median_income`: single NaN-guarded implementation (the `feature_transactions.py:196-215` variant) used by BOTH `planning_area_360` and `transactions_enriched`.
- Update imports in `feature_profiles.py`, `feature_transactions.py`, `feature_rental.py`; remove the now-private copies. No behavior change beyond the two unifications above.

### 5. Tests
- Delete tests covering removed loaders/STRtree/duplicate-policies; keep/adapt SpatialReferenceRepository tests.
- New `tests/test_hdb_lookups.py` (or extend feature tests): lookups, unified income merge (NaN planning area guarded), population sum aggregation, flat-type normalization incl. `"ALL"` sentinel pass-through.

## Verification
```
uv run pytest tests/test_data_loader.py tests/test_data_loader_extended.py tests/test_data_quality.py tests/test_feature_profiles.py tests/test_rental_yield_metrics.py tests/test_hdb_lookups.py -x -q
uv run ruff check <owned src files>
uv run ruff format --check <owned src + test files>
uv run mypy <owned src files>
```
Also RUN (do not edit): `uv run pytest tests/test_features.py tests/test_export.py tests/test_metrics.py -q` — if failures, report them precisely.

## Constraints
- NO commits. Owned files only. If `feature_rental.py`'s normalizer move breaks its existing tests, fix within owned test files.

## Definition of done
Dead code gone; one shared lookup module; divergences unified; tests/lint/mypy green; neighbor suites verified.

## Report back
Edits (file:line), deletions list, test delta (removed/added), neighbor-suite results, verification tail.
