# WS15 — Bronze Cache Centralization + manual_dir Injection (A2 first step, Batch 4 Wave 1)

## Context

Bronze nodes still write their own parquets via scattered inline `cache_path.exists()` / `to_parquet` patterns (the skill's "legacy exception"), and derive the manual-CSV directory by filesystem traversal: `bronze_dir.parent.parent / "manual"` at `datagov.py:169` and `ura_csv.py:120` (post-batch-3 line numbers approximate — re-verify). `RuntimePaths` already resolves a manual dir; `pipeline.py` doesn't inject it.

DECISION LOCKED: this WS centralizes bronze cache I/O through one helper and injects `manual_dir`. It does NOT route bronze through `LayerWriter`/quality snapshots (bronze is raw; quality tracking starts at silver) — full writer routing stays deferred.

NOTE: Batches 1-3 changed all owned files (manifest wiring in WS10, transform hardening in WS12, time-index/constant in WS14, materializer migration in WS11). Re-verify everything; preserve manifest calls + all warnings.

## Read first

- `.agents/skills/change-data-ingestion/SKILL.md` (mandatory — bronze immutability, cache-never-replaced-by-partial rules)

## Owned files (EXCLUSIVE)

- `src/egg_n_bacon_housing/utils/bronze.py`
- `src/egg_n_bacon_housing/components/ingestion/datagov.py`
- `src/egg_n_bacon_housing/components/ingestion/geojson.py`
- `src/egg_n_bacon_housing/components/ingestion/macro.py`
- `src/egg_n_bacon_housing/components/ingestion/ura_csv.py`
- `src/egg_n_bacon_housing/pipeline.py` (manual_dir injection ONLY — minimal diff)
- `src/egg_n_bacon_housing/utils/runtime.py` (verify/extend manual dir resolution)
- `tests/test_bronze.py`, `tests/test_ingestion.py`, `tests/test_ura.py`, `tests/test_pipeline.py`

## Forbidden

Everything else, incl. `components/cleaning.py`, `utils/layer_writer.py`, `utils/validation_gateway.py`, `config.py` (WS16 owns them this wave), `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. Shared cache helpers — `utils/bronze.py`

- `read_bronze_cache(bronze_dir: Path, name: str) -> pd.DataFrame | None` — parquet exists → read + return; else None.
- `write_bronze_cache(bronze_dir: Path, df: pd.DataFrame, name: str, source: str, *, allow_empty: bool = False) -> bool` — empty-guard (never cache empty/degenerate frames unless explicitly allowed), atomic write, `record_bronze_fetch` integrated, returns whether written.
- Migrate ALL ingestion modules' inline cache read/write patterns to these helpers (datagov incl. `@parameterize` base + green-mark geocode + malls; geojson amenities + MRT; macro; ura_csv). Behavior must be identical: cache-first, empty-never-cached, manifest recorded, existing filenames unchanged (they ARE the cache contract + `clear_bronze` targets).

### 2. `manual_dir` injection

- Verify `RuntimePaths` exposes the manual dir; extend if needed.
- `pipeline.py`: inject `manual_dir=...` into `layer_inputs` (one line, mirror existing style).
- `datagov.py:169` + `ura_csv.py:120`: replace `bronze_dir.parent.parent / "manual"` with an injected `manual_dir: Path` node parameter (update node signatures; Hamilton discovers params automatically).
- Add a grep-style test: no `parent.parent` remains under `components/`.

### 3. Unify empty/degenerate guards

- Where nodes write caches, use the helper's guard — notably the green-mark geocoded cache gets the same empty-guard semantics as macro (all-NA-coordinate frames must not be cached as valid).

## Tests required

- Helper round-trip; empty-guard (`allow_empty=False` → no file, `True` → 0-row file); manifest entry created.
- One representative node per module uses helpers (spy/patch `write_bronze_cache`): fetch path writes + records; cache-hit path reads only.
- `manual_dir` respected by HDB-resale CSV lookup + URA CSV lookup (tmp-dir fixture).
- No `parent.parent` in `components/` (test asserts).

## Verification

```
uv run pytest tests/test_bronze.py tests/test_ingestion.py tests/test_ura.py tests/test_pipeline.py -x -q
uv run ruff check <owned src files> && uv run ruff format --check <owned src + tests>
uv run mypy <owned src files>
```

## Constraints

- NO commits. Owned files only. Do not rename any bronze parquet filename. Do not alter transform logic (WS12's) or manifest semantics (WS10's).

## Definition of done

One cache I/O choke point; `manual_dir` injected; traversal gone; guards unified; tests/lint/mypy green.

## Report back

Edits (file:line), helper API summary, node signature changes, test delta, verification tail.
