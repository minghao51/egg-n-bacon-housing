# WS1 — Validation Integrity (Batch 1)

## Context
Hamilton DAG pipeline (uv, pandas, pydantic v2). Medallion: bronze→silver→gold→platinum.
Every silver/gold table flows through `validate_schema` → `validate_and_quarantine` → `LayerWriter`.
Two integrity holes confirmed at this boundary plus a memory bug.

## Read first
- `.agents/skills/change-hamilton-pipeline/SKILL.md` (mandatory, follow its checklist)

## Decisions locked (do not relitigate)
- D4a: `large_table_policy="fail"` must run FULL validation on the entire frame and raise on any quarantine. `"sample"` keeps persisting the full frame but must log the unvalidated row count.

## Owned files (EXCLUSIVE — edit nothing else)
- `src/egg_n_bacon_housing/utils/validation.py`
- `src/egg_n_bacon_housing/utils/validation_gateway.py`
- `tests/test_validation.py`, `tests/test_validation_gateway.py` (create if absent; else extend)

## Forbidden
- `tests/conftest.py`, `pyproject.toml`, `utils/layer_writer.py` (another WS owns it), any file outside ownership.

## Changes

### 1. Stop silent NaN-required-row drops — `utils/validation.py:33-38`
Current: `df.dropna(subset=existing_required)` silently discards rows BEFORE pydantic validation; they never reach quarantine.
Required: route those rows into `quarantine_records` with `_rejection_reason = "missing required field(s): <comma-joined fields>"` (per-row field list where cheap; else the row's missing fields). They must appear in the returned quarantine frame, not vanish.
Keep: pydantic can't catch `float('nan')` as missing (NaN is a valid float) — that's why the prefilter exists. Preserve that semantics; only the destination changes.

### 2. Chunked dict materialization — `utils/validation.py:52`
Current: `df_validate.to_dict(orient="records")` materializes the WHOLE frame (~1M rows, 5-10× memory) before chunking.
Required: build records per chunk inside the loop (`df_validate.iloc[i:i+chunk].to_dict(orient="records")`). Never whole-frame `to_dict`.

### 3. NaN conversion handles pandas/numpy nulls — `utils/validation.py:57-60`
Current: `isinstance(value, float)` misses `np.float32` NaN and `pd.NA`.
Required: use `pd.isna(value)` (guard: skip lists/arrays — `pd.isna` vectorizes on them; only convert scalars).

### 4. Gateway fail-policy + sample transparency — `utils/validation_gateway.py:129-163`
Current: under BOTH `"sample"` and `"fail"`, the entire df is persisted after only precheck + sample validation (`:163`).
Required:
- `"fail"`: after a clean precheck, run FULL `validate_schema` on the whole frame; if quarantine is non-empty → `raise ValueError` (include counts). Do not persist.
- `"sample"`: unchanged persistence, but `logger.warning` the exact count of unvalidated rows (`len(df) - sample_size`) with dataset name.
- Fix the docstring (`:75-77`) to state actual semantics precisely.
- Preserve the non-obvious precedence: `sample_validation_size` set + `large_table_policy="full"` → full validation (`:108-112`). Add a comment there.

## Tests required
- NaN-in-required-field rows → present in quarantine with reason (no silent drop); all-NaN frame → 100% quarantine + explicit log.
- `"fail"` policy raises on a frame with 1 bad row among many; passes on fully-valid frame.
- `"sample"` policy logs unvalidated-row count (caplog).
- `pd.NA` / `np.float32(np.nan)` in nullable columns → treated as None, not pydantic type errors.
- Whole-frame `to_dict` no longer called (monkeypatch/spy or memory-shape assertion via small chunk size).

## Verification (run, fix until green)
```
dotenvx run -- uv run pytest tests/test_validation.py tests/test_validation_gateway.py -x -q
uv run ruff check src/egg_n_bacon_housing/utils/validation.py src/egg_n_bacon_housing/utils/validation_gateway.py
uv run ruff format --check src/egg_n_bacon_housing/utils/validation_gateway.py src/egg_n_bacon_housing/utils/validation.py
uv run mypy src/egg_n_bacon_housing/utils/validation.py src/egg_n_bacon_housing/utils/validation_gateway.py
```

## Constraints
- NO commits. NO files outside ownership. Focused tests only — do not run the full suite.
- Line numbers are anchors from review; re-verify against current code before editing.

## Definition of done
All changes + tests green + lint/mypy clean on owned files.

## Report back
Summary of edits (file:line), tests added, verification output tail.
