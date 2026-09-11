# WS17 — Contract & Perf Tail (C5+C6+C7+C8 + known follow-ups, Batch 4 WAVE 2 — run AFTER WS15+WS16 merge)

## Context

Remaining small contract/perf items + the two standing follow-ups. NOTE: run only after Batch 4 Wave 1 (WS15 bronze centralization, WS16 cleaning validity) is merged — this WS owns `pipeline.py` (freed by WS15) and consumes WS16's config fields + WS14's constant.

Items:

- **C5**: proximity MRT branch still uses a per-row Python haversine loop (`utils/proximity.py` ~:144) after the KDTree query — vectorize (school_features post-prune is the in-repo pattern).
- **C6**: `utils/validation.py` `df.loc[valid_indices]` multiplies rows if the frame index is non-unique — guard.
- **C7**: `nearest_mrt_distance` is a duplicate of `dist_to_nearest_mrt` (emitted by proximity, unvalidated pass-through) — remove the duplicate.
- **C8 + follow-ups #1/#2**: dead `HFeatureTransaction.nearest_school` field (no producer); reserved `repository` param on `calculate_school_features` now unused; `pipeline.py` still constructs/injects `SchoolReferenceRepository` (+ `data_loader.configure()` module globals exist for a features.py fallback path).

## Read first

- `.agents/skills/change-hamilton-pipeline/SKILL.md` (mandatory)

## Owned files (EXCLUSIVE)

- `src/egg_n_bacon_housing/utils/proximity.py`
- `src/egg_n_bacon_housing/utils/validation.py`
- `src/egg_n_bacon_housing/utils/school_features.py`
- `src/egg_n_bacon_housing/utils/mrt_line_mapping.py` (verify-only unless vectorization touches it)
- `src/egg_n_bacon_housing/schemas/feature_models.py`
- `src/egg_n_bacon_housing/components/features.py`
- `src/egg_n_bacon_housing/pipeline.py`
- `tests/test_proximity.py`, `tests/test_validation.py`, `tests/test_school_features.py`, `tests/test_features.py`, `tests/test_pipeline.py`

## Forbidden

Everything else, incl. `schemas/platinum_models.py` (HUnifiedRecord inherits feature_models changes — RUN its tests; edit only if an assertion names a removed field, then report), `components/cleaning.py`, `components/ingestion/*`, `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. Vectorize MRT proximity — `proximity.py`

- Replace the per-row loop (~:144) with array math: gather `lat1/lon1` arrays for property rows + matched station coords from the KDTree indices, compute haversine vectorized (numpy, same formula/earth radius as `utils.geo`), assign once. Results must be bit-comparable (tolerance 1e-9) — pin with a test against the current scalar outputs on a fixture BEFORE refactoring.
- While there: verify `mrt_line_mapping` no longer deep-copies per call (earlier fix may have removed it); if copies remain on the hot path, cache once per frame call.

### 2. Index guard — `validation.py`

- On entry to `validate_schema`: if `not df.index.is_unique` → `df = df.reset_index(drop=True)` (log at debug) so `df.loc[valid_indices]` can never multiply rows. Row ORDER relative to input must be preserved for unique-index frames (existing behavior).

### 3. Drop `nearest_mrt_distance` — `proximity.py` (+ grep)

- Stop emitting the alias column; keep `dist_to_nearest_mrt`. Grep `src/`, `app/` (excl. public/data), `docs/` for consumers first — REPORT any found before removing (app parquet consumers read files, not columns we control — column removal changes future parquet schema only).

### 4. Dead-field + unused-DI cleanup

- `schemas/feature_models.py`: remove `HFeatureTransaction.nearest_school` (grep first: no producer, app verified non-consuming).
- `utils/school_features.py` + `components/features.py`: remove the reserved `repository` param from `calculate_school_features` and its pass-through in `location_dim` IF nothing else uses it (grep tests too — update owned tests).
- `pipeline.py`: remove the now-unused `SchoolReferenceRepository` construction + `school_reference` injection (verify no node declares it after the param removal); keep the `SchoolReference` Protocol in `utils/runtime.py` untouched (read-only file — report if it should be retired later).
- `pipeline.py` ALSO (rider from WS16): inject `min_coordinate_coverage_hdb`/`min_coordinate_coverage_condo` from `settings.geocoding` into `layer_inputs` next to the existing geocoding policy params (WS16's nodes accept them with defaults — wire the configured values through, mirroring existing style).
- `components/features.py` `data_loader.configure()` fallback: if tests can inject the spatial repository directly, remove the module-global configure path; if removal ripples beyond owned files, LEAVE it and report.

## Tests required

- Vectorized MRT distances == scalar reference (pre-refactor fixture); interchange/tier columns unchanged.
- Non-unique index input → correct row count out (no multiplication); unique index → order preserved.
- `nearest_mrt_distance` absent; `dist_to_nearest_mrt` present.
- `nearest_school` removed from model; platinum neighbor tests still green.
- `school_reference` no longer injected; `location_dim` computes school distances unchanged.
- Per-type coverage params injected (assert via driver inputs or node param test).

## Verification

```
uv run pytest tests/test_proximity.py tests/test_validation.py tests/test_school_features.py tests/test_features.py tests/test_pipeline.py tests/test_export.py tests/test_metrics.py -x -q
uv run ruff check <owned src files> && uv run ruff format --check <owned src + tests>
uv run mypy <owned src files>
uv run python scripts/tools/check_catalog.py
```

## Constraints

- NO commits. Owned files only. No behavior changes beyond the listed removals/vectorization (bit-comparable outputs).

## Definition of done

Vectorized MRT math; index-safe validation; duplicate + dead fields gone; unused DI unwired; WS16 rider injection done; all tests green.

## Report back

Edits (file:line), pre/post vectorization equivalence evidence, removals list, consumers found (if any) for `nearest_mrt_distance`/`nearest_school`, verification tail.
