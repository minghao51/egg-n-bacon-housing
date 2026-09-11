# WS3 — Platinum Contract: Schemas + Validation (Batch 1)

## Context

Platinum — the published surface — is the ONLY unvalidated medallion layer:

- `components/export.py:25` — `unified_dataset` has only `require_columns`.
- `components/metrics.py:54-163` — `pa_monthly_metrics`, `appreciation_hotspots` validate nothing.
- No platinum pydantic models exist in `schemas/`.
- Vestigial `writer` params on `unified_dataset` (export.py:11), `pa_monthly_metrics`/`appreciation_hotspots` (metrics.py:42,106) — accepted but unused.

## Read first

- `.agents/skills/change-hamilton-pipeline/SKILL.md` (mandatory)
- `components/feature_profiles.py:265-313` — the `persist=False` validation pattern to mirror
- `schemas/feature_models.py` + `schemas/clean_models.py` — model conventions (`catalog_dataset_id` ClassVar, Field constraints)

## Decision locked (D3a)

Full pydantic validation on all three platinum outputs, respecting the injected `large_table_validation_policy` (same mechanism as gold's fact table). Metrics tables are small → always full. `unified_dataset` is ~1M rows, same grain as `transactions_enriched`.

## Owned files (EXCLUSIVE)

- `src/egg_n_bacon_housing/schemas/platinum_models.py` (NEW)
- `src/egg_n_bacon_housing/schemas/__init__.py`
- `src/egg_n_bacon_housing/components/export.py`
- `src/egg_n_bacon_housing/components/metrics.py`
- `src/egg_n_bacon_housing/components/materialization.py`
- `tests/test_export.py`, `tests/test_metrics.py` (create or extend)

## Forbidden

Everything else, incl. `utils/validation_gateway.py`, `schemas/feature_models.py` (Batch 2 owns it), `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. New `schemas/platinum_models.py`

- `class HUnifiedRecord(HFeatureTransaction)` — thin subclass, `catalog_dataset_id: ClassVar = "unified_dataset"`. Same grain as the gold fact table; separate name so the platinum contract can diverge later.
- `PaMonthlyMetric` — enumerate ACTUAL output columns by reading `metrics.py:54-127` (planning_area, month, median price/psf, counts, affordability fields, etc.). Constraints: counts `ge=0`, prices/psf `gt=0` where NaN not expected (use `float | None = None` when nulls legitimately occur — check the node logic first), `month: str` format consistent with gold models.
- `AppreciationHotspot` — from `metrics.py:130-163`.
- Register in `schemas/__init__.py` following existing convention (check what it currently exports).

### 2. `components/export.py` — `unified_dataset`

- Keep `require_columns` as fast precheck.
- Add validation mirroring the feature_profiles pattern:
  `validate_and_quarantine(df, HUnifiedRecord, "unified_dataset", writer=writer, name="unified_dataset", layer="platinum", persist=False, sample_validation_size=10_000, large_table_policy=<injected policy>)`.
- First CHECK how `feature_transactions.py` receives `large_table_validation_policy` (injected param) — accept the same param here with the same default; confirm no `pipeline.py` edit is needed (it injects the policy as a global input — verify in `pipeline.py:236-252`; if a name mismatch would occur, use the exact injected name; do NOT edit pipeline.py — if wiring is impossible without it, STOP and report).
- Check gateway behavior when `persist=False` + writer provided: whether quarantine frames are written. Mirror feature_profiles exactly; additionally `logger.warning` the quarantine count when > 0.
- The `writer` param is now USED (passed to gateway) — no longer vestigial. Keep the param.

### 3. `components/metrics.py` — both nodes

- Same pattern, `layer="platinum_metrics"` name matching `_PUBLISHED_LAYERS` values (check `pipeline.py:52-65` for the exact layer strings).
- Both metrics tables are small → no sampling; full validation, `persist=False`, writer used for quarantine path per gateway semantics.
- `writer` params now used — keep.

### 4. `components/materialization.py`

- `materialize_appreciation_hotspots` (:18-23): keep the `L5_appreciation_hotspots` legacy alias write, add `logger.warning("L5_appreciation_hotspots is a deprecated alias; consumers should migrate to appreciation_hotspots")` each run.

## Tests required

- Each platinum node: valid frame passes; a poisoned row (bad price / missing key) is quarantined (or count warned, per gateway persist=False semantics) and the node still returns the valid frame.
- Schema constraint sanity: negative price rejected, bad month format rejected.
- `unified_dataset` with sample policy path exercised (set small `sample_validation_size`).

## Verification

```
dotenvx run -- uv run pytest tests/test_export.py tests/test_metrics.py -x -q
uv run ruff check src/egg_n_bacon_housing/schemas/ src/egg_n_bacon_housing/components/export.py src/egg_n_bacon_housing/components/metrics.py src/egg_n_bacon_housing/components/materialization.py
uv run ruff format --check <same files>
uv run mypy src/egg_n_bacon_housing/schemas/platinum_models.py src/egg_n_bacon_housing/components/export.py src/egg_n_bacon_housing/components/metrics.py src/egg_n_bacon_housing/components/materialization.py
```

## Constraints

- NO commits. Owned files only. No changes to gateway/validation internals (WS1 owns them concurrently — code against their CURRENT signatures).
- If gateway persist=False semantics make quarantine un-testable, report; don't hack around.

## Definition of done

All three platinum outputs validated; tests green; lint/mypy clean.

## Report back

Edits (file:line), new model field lists, verification output tail, any pipeline.py wiring gaps found (report-only).
