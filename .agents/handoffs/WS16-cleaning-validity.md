# WS16 — Cleaning Validity: Per-Type Coverage + Column Contracts + Quarantine Tracking (B5+B6+C4+C1-tail, Batch 4 Wave 1)

## Context

1. **B5**: `geocoded_validated` (`components/cleaning.py` ~:177-252) applies ONE coverage threshold across a mixed HDB+condo population; condo addresses are street-only (weaker geocode substrate) and can drag the aggregate toward the hard-fail threshold for reasons the policy can't distinguish. DECISION LOCKED (#4): per-property-type thresholds — HDB strict, condo lenient.
2. **B6**: silver `require_columns` sets are minimal (`{"month"}` at cleaning.py:47, `{"price"}` at :115) — losing `floor_area_sqm` etc. silently degrades derived features (all-NaN psf).
3. **C4**: quarantine writes flow through `TrackedWriter` → quality DB gets unique `_quarantine/<entity>_<ts>` dataset names → `sample_count=1` baselines forever (anomaly detection dead for them).
4. **C1-tail**: `cleaning.py:53` still hardcodes `* 10.764`; `SQFT_PER_SQM = 10.7639` now lives in `utils/hdb_lookups.py` (WS14).

NOTE: Batch 3 (WS11) migrated cleaning nodes to `persist=False` + materializers — re-verify current state.

## Read first

- `.agents/skills/change-hamilton-pipeline/SKILL.md` (mandatory)

## Owned files (EXCLUSIVE)

- `src/egg_n_bacon_housing/components/cleaning.py`
- `src/egg_n_bacon_housing/utils/validation_gateway.py`
- `src/egg_n_bacon_housing/utils/layer_writer.py`
- `src/egg_n_bacon_housing/config.py` (GeocodingConfig only — minimal diff)
- `tests/test_cleaning_validation.py`, `tests/test_validation_gateway.py`, `tests/test_pipeline.py`, `tests/test_config.py`

## Forbidden

Everything else, incl. `pipeline.py`, `components/ingestion/*` (WS15 this wave), `utils/validation.py`, `schemas/*`, `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. Per-type coverage policy — `config.py` + `cleaning.py`

- `GeocodingConfig`: add `min_coordinate_coverage_hdb: float = 0.7` and `min_coordinate_coverage_condo: float = 0.3` (keep the existing `min_coordinate_coverage` as the fallback/default for other types — document it; do not remove the old field).
- `cleaning.py` `geocoded_validated`: compute coverage PER `property_type` segment (hdb vs condo; others use the legacy default), apply each threshold, then aggregate per the existing `coordinate_coverage_policy` (fail → raise listing each failing segment with its coverage; warn → warn per segment). Include the aggregate coverage in the log line. Behavior for an all-HDB or all-condo frame must equal the per-type numbers.
- Inject the two new settings through `pipeline.py`?? — NO: pipeline.py is WS15's this wave. Instead accept them as node params with defaults; wire injection in WS17 (report this as a wiring follow-up so WS17's spec includes it).

### 2. Column contracts — `cleaning.py`

- Extend `require_columns` to derivation-critical sets based on what each cleaning node actually derives: HDB (~:41-85): at minimum `{"month","price","floor_area_sqm","town","flat_type"}`; condo (~:100-161): at minimum `{"price","transaction_date"}` + the address field actually used. Read both nodes and pick columns that are structurally guaranteed by the source contracts (docs/guides/data-ingestion-development.md documents them) — do NOT require columns that legitimately vary.
- Add explicit dropped-row count logging wherever rows are silently filtered today (grep for bare `dropna`/boolean filters in the two cleaning nodes).

### 3. Quarantine tracking opt-out — `layer_writer.py` + `validation_gateway.py`

- `LayerWriter.write(..., track_quality: bool = True)`; `TrackedWriter` skips `record_dataframe_quality` when False. `SimpleWriter` ignores it.
- `validation_gateway`: all `_quarantine/...` writes pass `track_quality=False`.

### 4. sqft constant — `cleaning.py:53`

- `df["floor_area_sqft"] = df["floor_area_sqm"] * SQFT_PER_SQM` importing from `utils.hdb_lookups`. (Values shift by ~1e-4 relative — intended unification.)

## Tests required

- Per-type coverage: HDB 0.95/condo 0.2 → condo fails its 0.3 threshold, HDB passes; policy=fail raises naming the condo segment; policy=warn warns per segment; old single-threshold behavior for unknown property types via legacy field.
- Column contracts: missing `floor_area_sqm` → loud `ValueError` (not silent NaN psf); dropped-row counts logged.
- Quarantine: `_quarantine/` writes produce NO quality snapshot rows (query the sqlite db in tmp); normal writes still do.
- Constant: HDB sqft equals sqm × 10.7639.

## Verification

```
uv run pytest tests/test_cleaning_validation.py tests/test_validation_gateway.py tests/test_pipeline.py tests/test_config.py -x -q
uv run pytest tests/test_features.py tests/test_export.py tests/test_metrics.py -q   # neighbors, run-only
uv run ruff check <owned src files> && uv run ruff format --check <owned src + tests>
uv run mypy <owned src files>
```

## Constraints

- NO commits. Owned files only. config.py diff = GeocodingConfig fields only. No gateway validation-semantics changes beyond the tracking flag.

## Definition of done

Per-type coverage live; loud column contracts; quarantine excluded from quality DB; constant unified; tests green.

## Report back

Edits (file:line), the exact require_columns sets chosen + justification, wiring follow-ups for WS17 (per-type config injection), verification tail.
