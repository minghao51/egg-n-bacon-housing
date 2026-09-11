# WS7 — Layer Registry Consolidation (Batch 2a)

## Context

Three sources of layer truth exist and can drift:

1. `Settings.layer_paths()` (`config.py`, ~:87-99)
2. `pipeline._PUBLISHED_LAYERS` node→layer map (~:52-65 post-Batch-1)
3. `LayerWriter.resolve_path` base impl — constructs a **fresh default `LayerDirs()`** at call time, ignoring the configured settings the writer was built with (`utils/layer_writer.py:41-43`)

Adding a published layer today requires touching `_PUBLISHED_LAYERS`, `_MATERIALIZER_MAP`/`_PERSISTED_VARS`, `STAGE_VARS`, and a materializer — none cross-checked.

NOTE: Batch 1 (WS5) already refactored `pipeline.py` (`_hamilton_cache_dir`, `resolve_final_vars`, `ensure_published_outputs_or_invalidate`) and `layer_writer.py` (empty writes persist). Re-verify current state before editing.

## Read first

- `.agents/skills/change-hamilton-pipeline/SKILL.md` (mandatory)

## Owned files (EXCLUSIVE)

- `src/egg_n_bacon_housing/config.py`
- `src/egg_n_bacon_housing/pipeline.py`
- `src/egg_n_bacon_housing/utils/layer_writer.py`
- `tests/test_pipeline.py`, `tests/test_config.py` (extend; create config tests if absent)

## Forbidden

Everything else, incl. `components/*`, `main.py`, `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. Single published-layer registry

- Move the node→layer mapping out of `pipeline.py` into `utils/layer_writer.py` as `PUBLISHED_LAYERS: dict[str, str]` (importable without pulling pipeline). `pipeline.py` imports it (keep the name `_PUBLISHED_LAYERS = PUBLISHED_LAYERS` alias or update internal references).
- `Settings.layer_paths()` stays the source for layer→directory resolution; add a module-level test (in test_pipeline or test_config) asserting every value in `PUBLISHED_LAYERS` is a key `Settings` can resolve — the cross-check that's missing today.

### 2. Thread configured `LayerDirs` through writers

- `LayerWriter` ABC: accept `layer_dirs: LayerDirs` (default `LayerDirs()`) in `__init__`; `resolve_path` uses the instance's `layer_dirs`, never a fresh default.
- `SimpleWriter`/`TrackedWriter`/`build_writer` thread it through; `build_writer(settings, data_dir)` passes `settings.layer_dirs` so production paths honor `LAYER_DIRS__*` env overrides. `SimpleWriter()` with no args must keep working for existing tests (default LayerDirs).
- Existing behavior for `platinum_metrics` → `04_platinum/metrics` must be preserved exactly.

### 3. `LayerDirs.relative_path` documentation + guard (`config.py:57-70`)

- Docstring: explain the `data/pipeline`-prefix strip + re-add round-trip and absolute-path bypass.
- Add a `logger.warning` (once) when a configured relative layer path does NOT start with `data/pipeline` — surfaces likely misconfigurations without breaking custom setups.

## Tests required

- Registry consistency: every `PUBLISHED_LAYERS` value resolves via `Settings.layer_paths()`.
- `TrackedWriter` built via `build_writer` with a custom `LayerDirs` (e.g. silver → `custom/silver`) writes to the configured path, not the default.
- `SimpleWriter()` default path behavior unchanged.
- Warning fires for non-`data/pipeline` relative paths; silent for standard ones.

## Verification

```
dotenvx run -- uv run pytest tests/test_pipeline.py tests/test_config.py -x -q
uv run ruff check src/egg_n_bacon_housing/config.py src/egg_n_bacon_housing/pipeline.py src/egg_n_bacon_housing/utils/layer_writer.py
uv run ruff format --check <same>
uv run mypy src/egg_n_bacon_housing/config.py src/egg_n_bacon_housing/pipeline.py src/egg_n_bacon_housing/utils/layer_writer.py
```

(dotenvx may be absent — plain `uv run` is fine; tests need no secrets.)

## Constraints

- NO commits. Owned files only. No behavior changes to `STAGE_VARS`, materializer wiring, or cache semantics.

## Definition of done

One registry; writers honor configured `LayerDirs`; cross-check test in place; tests/lint/mypy green.

## Report back

Edits (file:line), tests added, verification tail.
