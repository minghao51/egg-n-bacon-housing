# WS14 — Time-Index Transparency + Unified sqft Constant (B4 + C1, Batch 3)

## Context

1. **`utils/time_index.py` `ensure_month_column` still silently drops NaT rows** (:41 and :53 boolean filters — `return result[result[month_column].notna() & (result[month_column] != "NaT")]`). Callers: `components/metrics.py`, `components/feature_rental.py`, `components/feature_transactions.py`. Unparseable dates silently shrink rental-yield/median aggregations with zero evidence. (The missing-column case already logs an error and returns an empty frame — that part was improved.)
2. **sqft constant split**: `components/ingestion/ura_csv.py:34` `_SQFT_PER_SQM = 10.7639` vs `components/cleaning.py:53` hardcoded `* 10.764` (~9.3e-5 relative inconsistency + maintenance smell).

DECISIONS LOCKED:

- NaT drops become loud (count warnings). Missing-date-column behavior: raise IF AND ONLY IF all current call sites structurally guarantee the column (verify first); otherwise keep the logged empty-frame return.
- Single constant `SQFT_PER_SQM = 10.7639` lives in `utils/hdb_lookups.py`. NOTE: `cleaning.py` adoption is DEFERRED to Batch 4 (owned by WS11 this batch) — do NOT touch cleaning.py.

## Read first

- `.agents/skills/change-hamilton-pipeline/SKILL.md` (mandatory)

## Owned files (EXCLUSIVE)

- `src/egg_n_bacon_housing/utils/time_index.py`
- `src/egg_n_bacon_housing/utils/hdb_lookups.py`
- `src/egg_n_bacon_housing/components/ingestion/ura_csv.py`
- `tests/test_time_index.py` (create if absent), `tests/test_hdb_lookups.py`, `tests/test_ura.py`

## Forbidden

Everything else, incl. `components/cleaning.py`, `components/metrics.py`, `components/feature_rental.py`, `components/feature_transactions.py` (callers — read-only analysis allowed, no edits), `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. `utils/time_index.py`

- Both filter branches: count dropped rows; `logger.warning` when > 0 with column name, dropped count, and kept count (e.g. `"month derivation dropped 12/345 rows (unparseable dates)"`).
- Caller audit (grep + read the three callers): if every call site guarantees the date/month column exists by construction, change the missing-column branch from `logger.error` + empty frame to `raise ValueError` (schema break, not data sparsity). If any caller can legitimately pass a frame without the column, KEEP the logged empty-frame return and document why. State your audit conclusion in the report.
- No behavior change to the derivation itself (Period format, "NaT" literal guard preserved).

### 2. Unified constant — `utils/hdb_lookups.py` + `ura_csv.py`

- Add `SQFT_PER_SQM: float = 10.7639` to `utils/hdb_lookups.py` with a one-line comment (1 sqm = 10.7639 sqft, exact factor).
- `ura_csv.py:34`: replace the local `_SQFT_PER_SQM` with an import from `hdb_lookups` (keep any local aliasing minimal; update internal references).
- Do NOT touch `cleaning.py` (Batch 4 will adopt the constant there).

## Tests required

- `tests/test_time_index.py` (create): month present + some NaT → warning with exact counts, correct rows kept; all-parseable → silent; missing date column → the audited behavior pinned (raise OR logged-empty) with a comment referencing the audit; existing period/string passthrough behaviors preserved (port/cover the cases the module docstring promises).
- `tests/test_hdb_lookups.py`: constant exists and equals 10.7639.
- `tests/test_ura.py`: existing sqft conversions still pass (import path change only — fix any direct `_SQFT_PER_SQM` references in tests).

## Verification

```
uv run pytest tests/test_time_index.py tests/test_hdb_lookups.py tests/test_ura.py -x -q
uv run pytest tests/test_features.py tests/test_rental_yield_metrics.py -q   # callers, run-only
uv run ruff check <owned src files> && uv run ruff format --check <owned src + tests>
uv run mypy <owned src files>
```

## Constraints

- NO commits. Owned files only. The raise-vs-return decision must follow the audit, not preference.

## Definition of done

NaT drops observable; missing-column behavior audited + pinned by test; single sqft constant adopted on the URA side; tests/lint/mypy green.

## Report back

Edits (file:line), the caller-audit conclusion (raise or return + evidence), test delta, verification tail.
