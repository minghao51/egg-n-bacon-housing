# WS2 — Rental-Yield Join Fix (Batch 1)

## Context
CONFIRMED CRITICAL: `rental_yield_pct` is 100% NULL in production.
- `components/feature_rental.py:158` intentionally emits `flat_type="ALL"` (constant, aggregated grain).
- `components/feature_transactions.py:116-121` picks the FIRST merge candidate whose keys exist on both frames: `merge_priority = [["town","month","flat_type"], ["town","month"]]`. Production always has `flat_type` on both sides → 3-key candidate wins → `"4 ROOM" != "ALL"` → zero matches. The `(town, month)` fallback is unreachable.
- Existing test passes only because its fixture uses `flat_type="4 ROOM"` (tests/test_features.py:477) — a shape production can never produce.

## Read first
- `.agents/skills/change-hamilton-pipeline/SKILL.md` (mandatory, follow its checklist)

## Decision locked (D1a)
Sentinel-aware: when the rental frame's `flat_type` is a constant sentinel (`"ALL"` / single unique value), drop `flat_type` from the rental frame before the merge-priority loop → the 3-key candidate fails the key-presence check → falls to `(town, month)`. Future per-flat-type rental data keeps working unchanged. Do NOT touch `feature_rental.py` — its `"ALL"` emission is intentional and correctly documented.

## Owned files (EXCLUSIVE)
- `src/egg_n_bacon_housing/components/feature_transactions.py`
- `tests/test_features.py`

## Forbidden
Everything else, incl. `components/feature_rental.py`, `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. Sentinel-aware merge — `components/feature_transactions.py` (~:105-131)
Inside the rental-yield block, after normalizing `rental_df["flat_type"]` and BEFORE the `merge_priority` loop:
```python
# rental_yield is aggregated across flat types (flat_type == "ALL" sentinel).
# A constant sentinel can never match transaction-level flat_type values, so
# drop it and let merge_priority fall through to (town, month). If rental
# data ever becomes per-flat-type, the 3-key merge re-engages automatically.
if "flat_type" in rental_df.columns and rental_df["flat_type"].nunique(dropna=True) <= 1:
    rental_df = rental_df.drop(columns=["flat_type"])
```
(Exact placement: before `merge_priority = ...`. Keep all downstream logic — dedupe/sort/`keep="last"` — unchanged.)

### 2. Regression tests — `tests/test_features.py`
- Test A (production shape): transactions with `flat_type` in {"4 ROOM","5 ROOM"}, rental frame with `flat_type="ALL"` and overlapping `(town, month)` → assert `rental_yield_pct` is non-null for matching rows.
- Test B (future per-type shape): rental frame with real `flat_type` values matching transactions → assert the 3-key merge still wins (per-type values joined).
- Test C (no rental keys): rental frame without `town` → merge skipped, no crash (existing behavior preserved).
Update the existing misleading fixture (:477 area) to the production shape or leave it as the per-type case — ensure both shapes are covered after your change.

## Verification
```
dotenvx run -- uv run pytest tests/test_features.py -x -q
uv run ruff check src/egg_n_bacon_housing/components/feature_transactions.py
uv run ruff format --check src/egg_n_bacon_housing/components/feature_transactions.py
uv run mypy src/egg_n_bacon_housing/components/feature_transactions.py
```

## Constraints
- NO commits. Owned files only. Do not "fix" anything else you notice in the file — report it instead.
- Re-verify line anchors against current code first.

## Definition of done
Test A fails on the pre-fix code (verify mentally or via stash) and passes post-fix; B and C green; lint/mypy clean.

## Report back
Edits (file:line), tests added, verification output tail, any other issues noticed (report-only).
