# WS5 — Pipeline Core: Invalidation, Empty Writes, final_vars (Batch 1)

## Context
Three confirmed pipeline-core defects:
1. **CLI bypasses the cache-invalidation safety net** — `main.py:78` always builds the driver, then calls `run_pipeline(..., dr=dr)`; `pipeline.py:235-237` runs `_invalidate_cache_when_outputs_missing` ONLY when `dr is None`. Production never invalidates.
2. **Empty-output → cache-nuke loop** — `utils/layer_writer.py:98-99` (and `:65-66` SimpleWriter) return early for empty frames WITHOUT writing; a legitimately empty published output reads as "missing" → `pipeline.py:193-202` `shutil.rmtree`'s the ENTIRE Hamilton cache → permanent full-recompute loop incl. OneMap quota burn.
3. **Silent final_vars drop** — `pipeline.py:276` filters results by membership; missing outputs vanish with a green run.

Plus: `data/cache/hamilton` path hardcoded twice (`pipeline.py:166` and `:199`).

## Read first
- `.agents/skills/change-hamilton-pipeline/SKILL.md` (mandatory — the entrypoint contract `main.py → build_pipeline() → run_pipeline()` is sacred; do not add a parallel runner)

## Decision locked (D2a)
Empty DataFrames are persisted as 0-row schema-only parquet files. No marker files, no skip-and-log.

## Owned files (EXCLUSIVE)
- `src/egg_n_bacon_housing/pipeline.py`
- `main.py`
- `src/egg_n_bacon_housing/utils/layer_writer.py`
- `tests/test_pipeline.py` (extend; create if absent)

## Forbidden
Everything else, incl. `components/*`, `utils/validation*` (WS1), `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. Empty-frame writes — `utils/layer_writer.py`
- `SimpleWriter.write` (:63-70) and `TrackedWriter.write` (:82-120): remove the early return for `df.empty`; write the 0-row parquet normally. Verify `df.to_parquet` handles: (a) 0-row WITH columns → writes schema-only file ✓; (b) completely column-less `pd.DataFrame()` → if pyarrow errors, write an empty table via `pyarrow.parquet.write_table(pq.ParquetFile(...))` equivalent or `df.astype({...})` — pick the minimal robust approach and TEST both cases.
- `TrackedWriter`: still record the quality snapshot for empty writes (0 rows) so anomaly detection sees the collapse-to-zero. Keep compression setting behavior.

### 2. Cache-dir helper — `pipeline.py`
Extract `def _hamilton_cache_dir(data_dir: Path) -> Path: return data_dir / "cache" / "hamilton"`; use at both `:166` and `:199`. Single source of truth.

### 3. Public invalidation, hoisted before build — `pipeline.py` + `main.py`
- Rename `_invalidate_cache_when_outputs_missing` → `ensure_published_outputs_or_invalidate` (keep underscore-free, add docstring: checks requested published output files exist; if any missing, clears the Hamilton cache so stale caches can't mask absent outputs).
- `run_pipeline`: keep calling it exactly when `dr is None` (current semantics — it must run BEFORE the driver opens its sqlite cache).
- `main.py`: call `ensure_published_outputs_or_invalidate(...)` BEFORE `build_pipeline` (:78) with the same final_vars the run will request (derive from CLI args the same way `run_pipeline` derives them — factor the resolution if it's duplicated, without changing behavior). Ensure the pre-built-driver path now gets the same guarantee as the `dr=None` path, and that the check cannot run twice destructively (it's idempotent — deleting an already-deleted dir is fine; but ordering with the sqlite open is the reason it must precede `build_pipeline`).

### 4. Raise on missing final_vars — `pipeline.py:276`
Replace the silent filter:
```python
missing = [name for name in final_vars if name not in results]
if missing:
    raise RuntimeError(f"Pipeline did not produce requested final_vars: {missing}")
return {name: results[name] for name in final_vars}
```

## Tests required
- Empty df (with columns) → parquet file exists, readable, 0 rows (both writers). Column-less df → does not crash.
- `ensure_published_outputs_or_invalidate`: (a) all outputs present → cache dir untouched; (b) one output file missing → cache dir removed; (c) output present-but-0-rows (post-fix-1 file) → cache NOT removed.
- Missing final_var → RuntimeError naming it.
- Ordering guarantee: main.py path can be asserted at function level (mock/spy that invalidation runs before driver build if feasible; else document in test docstring and test the function directly).

## Verification
```
dotenvx run -- uv run pytest tests/test_pipeline.py tests/test_layer_writer.py -x -q
uv run ruff check src/egg_n_bacon_housing/pipeline.py main.py src/egg_n_bacon_housing/utils/layer_writer.py
uv run ruff format --check <same>
uv run mypy src/egg_n_bacon_housing/pipeline.py src/egg_n_bacon_housing/utils/layer_writer.py main.py
```
(`tests/test_layer_writer.py` if it exists — check `ls tests/`; if owned-by-nobody test files need updating because of the empty-write behavior change, update the minimal assertions and REPORT it.)

## Constraints
- NO commits. Owned files only (+minimal necessary assertion updates in existing layer_writer/pipeline tests — report any such edits).
- Do NOT change `STAGE_VARS`, `_PUBLISHED_LAYERS`, materializer wiring, or cache semantics beyond the above.

## Definition of done
Empty outputs persist as 0-row parquet; invalidation runs on the production CLI path before driver build; missing final_vars raises; tests/lint/mypy green.

## Report back
Edits (file:line), any out-of-ownership test assertion updates, verification tail.
