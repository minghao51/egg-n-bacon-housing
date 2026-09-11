# WS9' — Schema Tightening + School Feature Prune + Shim Removal (Batch 2b — run AFTER Batch 2a integration)

## Context

Three related contract problems around gold schemas and `school_features`:

1. **Silver contract is fictional**: `GeocodedProperty` (`schemas/clean_models.py:81-97` post-Batch-1 — re-verify) omits columns gold depends on (`block`, `street_name`, `town`, `flat_type`, `floor_area_sqm/sqft`, `month`); they survive only via `validate_schema`'s pass-through side effect.
2. **Gold schema gaps**: `HFeatureTransaction.school_tier` and `mrt_line` have NO producer (always None — verified; app consumes neither). Proximity emits `nearest_mrt_tier`/`nearest_mrt_is_interchange`/`nearest_mrt_score` on `location_dim` but they're unvalidated pass-throughs (not in `LocationDimRecord`). Missing constraints: `property_type` lacks `min_length=1`; `transaction_date` has no plausibility bound; `median_price`/`median_psf` in `PlanningArea360`/`Town360`/`BlockProfile` lack `gt=0` (sibling `HRentalYieldRecord` has it); `HRentalYieldRecord.sample_size` lacks `ge=1`.
3. **`utils/school_features.py` (706 lines)**: ~70% of computed columns reach no schema or consumer — only the three `nearest_school{PRIMARY,SECONDARY,JUNIOR}_dist` columns are consumed by `components/features.py` (~:129-145, min → `dist_to_nearest_school`). Column-init literal lists duplicated 3× (:357, :411-420, :427-460 pre-Batch-1). Row-by-row Python loop over unique locations (~:555-640). NOTE: analytics-doc-cited score columns are NOT a constraint — docs are out of scope; prune to pipeline consumption only.
4. **`components/features.py:25-41`** legacy `__getattr__` shim re-exporting other modules' nodes — only test consumers.

## Read first

- `.agents/skills/change-hamilton-pipeline/SKILL.md` (mandatory)

## Owned files (EXCLUSIVE)

- `src/egg_n_bacon_housing/schemas/clean_models.py`
- `src/egg_n_bacon_housing/schemas/feature_models.py`
- `src/egg_n_bacon_housing/utils/school_features.py`
- `src/egg_n_bacon_housing/components/features.py`
- `tests/test_features.py`, `tests/test_school_features.py` (create if absent), `tests/test_cleaning_validation.py`, schema-related tests as needed

## Forbidden

`schemas/platinum_models.py` (subclass `HUnifiedRecord(HFeatureTransaction)` inherits your changes — do NOT edit it, but RUN its tests), `components/feature_*.py`, `pipeline.py`, `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. `schemas/clean_models.py` — real silver contract

- `GeocodedProperty`: add the pass-through fields gold consumes as Optional validated fields (`block`, `street_name`, `town`, `flat_type`, `floor_area_sqm`, `floor_area_sqft`, `month` — check `components/features.py:120` carry_cols + `feature_transactions.py` usage for the exact set).
- `HCleanTransactionBase.property_type`: `min_length=1`; `transaction_date`: plausibility bound `ge=date(1990,1,1)` (dataset floor) — use pydantic v2 `Field(ge=...)` on datetime or a validator; pick the idiom already used in the codebase.

### 2. `schemas/feature_models.py` — dead fields out, real fields in, constraints

- Remove `HFeatureTransaction.school_tier` and `mrt_line` (no producer; app verified not consuming).
- Add Optional `nearest_mrt_tier`, `nearest_mrt_is_interchange`, `nearest_mrt_score` to `LocationDimRecord` (produced by proximity; currently unvalidated pass-through). Keep them `| None` — degraded MRT paths can omit them.
- Add `gt=0` to `median_price`/`median_psf` in `PlanningArea360`/`Town360`/`BlockProfile` ONLY where NaN/nulls aren't legitimate — check the producing nodes (`feature_profiles.py` — do not edit, read only) for whether these can be null; use `float | None = Field(default=None, gt=0)` if nullable.
- `HRentalYieldRecord.sample_size`: `ge=1`.

### 3. `utils/school_features.py` — prune + vectorize

- First VERIFY consumption with grep (`components/features.py` + schemas): expected keep-set = `nearest_school_primary_dist`, `nearest_school_secondary_dist`, `nearest_school_junior_college_dist` (check exact level names) + whatever `features.py` derives. Everything else goes: attribute columns, per-level counts (500m/1km/2km), `school_within_*`, accessibility/quality/density/dist scores.
- Delete now-orphaned scoring/matching machinery (`calculate_primary_quality_score`, `calculate_secondary_quality_score`, `calculate_accessibility_score`, `fuzzy_match_schools`) IF no other consumers (grep src+scripts first; report if scripts use them).
- Single column-init (one literal list, used once).
- Vectorize the per-row loop: compute nearest per level via batched `tree.query(unique_coords, k=1)`, then map back through the unique-location index with vectorized assignment (no `iterrows`, no `at[]` in a loop). Keep the `SchoolReferenceRepository` DI shape intact.
- If the `repository` param becomes unused after pruning: KEEP the parameter (documented as reserved), do NOT edit `pipeline.py` (out of ownership) — report for follow-up.

### 4. `components/features.py` — remove the shim

- Delete the `__getattr__` re-export block (~:25-41); update `tests/test_features.py` imports to the real modules (`feature_rental`, `feature_transactions`, `feature_profiles`).

## Tests required

- Schema: pass-through fields validated (null OK, wrong type quarantined); dead-field removal doesn't break model round-trips; new constraints reject empty `property_type`, pre-1990 dates, non-positive medians, `sample_size=0`.
- School: pruned output has exactly the keep-set of columns; vectorized results match a brute-force expectation on a small fixture; unique-location mapping correct for duplicated coords.
- Shim: `features.rental_yield` etc. no longer resolvable; real-module imports work.
- RUN (may edit only if failures are caused by your schema changes): `tests/test_export.py`, `tests/test_metrics.py` (platinum subclass), `tests/test_property_based.py`.

## Verification

```
uv run pytest tests/test_features.py tests/test_school_features.py tests/test_cleaning_validation.py tests/test_export.py tests/test_metrics.py tests/test_property_based.py -x -q
uv run ruff check <owned src files>
uv run ruff format --check <owned src + test files>
uv run mypy <owned src files>
```

## Constraints

- NO commits. Owned files only. Parquet content must not change for valid rows (this is contract + compute pruning, not data transformation) — except removed dead columns, which is intended.

## Definition of done

Schemas match reality; school module computes only what's consumed, vectorized; shim gone; all tests incl. platinum neighbors green.

## Report back

Edits (file:line), kept vs dropped school columns, orphaned-machinery deletion list, verification tail, any reserved-param follow-ups.
