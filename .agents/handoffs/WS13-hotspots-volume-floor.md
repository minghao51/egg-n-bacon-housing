# WS13 — Appreciation Hotspots Volume Floor (B3, Batch 3 — WAVE 2: run AFTER WS11/WS12/WS14 are merged)

## Context

`components/metrics.py` `appreciation_hotspots` (~:130-182): monthly medians, `ffill` prices, `pct_change(3)`/`pct_change(12)`, then `sort_values(...).head(20)` (:182). `transaction_count` is aggregated (:80) but never used as a filter — single-transaction months can top the "top 20 hotspots" as noise.

DECISIONS LOCKED:

- Minimum `transaction_count >= 5` per source month, **configured in `Settings.MetricsConfig`** (user decision #3) and injected into the node via the existing metrics-params injection — NOT a bare node default.
- Filter placement: floor applies to BOTH the ranked month and the pct_change comparison base (a 1-txn spike month must neither rank nor distort another month's baseline).

NOTE (wave 2): WS11 already completed the materializer migration in pipeline.py — re-verify pipeline.py's current injection dict and materializer wiring before editing; mirror the existing pattern for `median_household_income`/affordability params exactly.

## Read first

- `.agents/skills/change-hamilton-pipeline/SKILL.md` (mandatory)
- `pipeline.py` layer_inputs/metrics injection region + `components/metrics.py` current state (Batch 1 platinum validation + Batch 3 materializer migration — preserve both)

## Owned files (EXCLUSIVE)

- `src/egg_n_bacon_housing/config.py` (MetricsConfig only — minimal diff)
- `src/egg_n_bacon_housing/pipeline.py` (injection line(s) only — minimal diff)
- `src/egg_n_bacon_housing/components/metrics.py`
- `.env.example` (only if it documents metrics settings — check consistency first)
- `tests/test_metrics.py`, `tests/test_config.py` (extend)

## Forbidden

Everything else, incl. `schemas/platinum_models.py` (REPORT if a field becomes dead), `components/materialization.py`, `components/export.py`, `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. Config — `config.py` `MetricsConfig`

- `min_transactions_for_hotspot: int = Field(default=5, ge=1)` with a one-line comment (volume floor for appreciation hotspot ranking; env-overridable via `METRICS__MIN_TRANSACTIONS_FOR_HOTSPOT`).
- If `MetricsConfig` has a validator pattern (e.g. threshold ordering), follow it; otherwise no extra validation.

### 2. Injection — `pipeline.py`

- In the metrics-params injection region, add `min_transactions_for_hotspot=settings.metrics.min_transactions_for_hotspot` next to the existing metrics params (mirror naming/style exactly).

### 3. Floor — `components/metrics.py` `appreciation_hotspots`

- New node param `min_transactions_for_hotspot: int = 5` (Hamilton default keeps the node testable standalone; pipeline injects the configured value).
- Filter the monthly-median frame to `transaction_count >= min_transactions_for_hotspot` BEFORE ffill/pct_change (floors both ranked and base months).
- `logger.info` once: how many (planning_area, month) rows floored out.
- Empty-after-floor → empty frame, no raise (established 0-row parquet path handles persistence).
- Node docstring: floor rationale + default + config key.

### 4. Tests

- Noise floor: <5-txn spike month excluded despite extreme pct_change.
- Floored BASE month cannot distort another month's 3m appreciation (1-txn outlier base case).
- Boundary: exactly 5 → included. `min_transactions_for_hotspot=1` → pre-floor behavior (regression guard).
- Config: field default 5, `ge=1` enforced, env override `METRICS__MIN_TRANSACTIONS_FOR_HOTSPOT` works (pydantic-settings `__` delimiter — mirror an existing config override test if one exists).
- Injection: pipeline passes configured value (spy/assert on node input or driver inputs — mirror how existing metrics params are tested, if at all; else unit-test the injection dict construction if feasible, keep minimal).
- Empty-after-floor → empty result, no raise.

## Verification

```
uv run pytest tests/test_metrics.py tests/test_config.py tests/test_export.py tests/test_pipeline.py -x -q
uv run ruff check src/egg_n_bacon_housing/config.py src/egg_n_bacon_housing/pipeline.py src/egg_n_bacon_housing/components/metrics.py
uv run ruff format --check <same + tests>
uv run mypy src/egg_n_bacon_housing/config.py src/egg_n_bacon_housing/pipeline.py src/egg_n_bacon_housing/components/metrics.py
uv run python scripts/tools/check_catalog.py
```

## Constraints

- NO commits. Owned files only; config.py/pipeline.py diffs must be the minimal lines described (other workstreams' concurrent history is NOT yours to touch).
- Do not alter `pa_monthly_metrics` semantics, ffill logic beyond floor placement, validation calls, or materializer wiring.

## Definition of done

Configured + injected + applied floor (ranked AND base months); observable; tests incl. config-override green.

## Report back

Edits (file:line), filter placement rationale, test delta, verification tail.
