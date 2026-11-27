# WS-D1 — Type-coverage scope and ledger sync (ARCH-1, ARCH-2, DOC-1)

**Severity:** MEDIUM 6 + LOW 4 + MEDIUM 6. **Effort:** M. **Wave:** 1.

## Problem

1. **Type checking covers 11 entries.** `pyproject.toml:149-161` lists `components/`, `adapters/`, a handful of `utils/` modules, `pipeline.py`, `config.py`. Measured against `src/egg_n_bacon_housing/**`, **19 modules are outside it**, including every `schemas/*`, `utils/validation.py`, `utils/bronze.py`, `utils/output_registry.py`, `utils/data_loader.py`, `utils/school_features.py`. `mypy` prints "Success: no issues found in 29 source files", which can be read as whole-project coverage. `# strict = true` is still commented (`:162`).
2. **Duplicate layer-path resolution.** `src/egg_n_bacon_housing/config.py:178-194` (`layer_dir`, `layer_paths`) and `src/egg_n_bacon_housing/utils/layer_writer.py:49-59` (`resolve_layer_paths`, docstring says it "mirrors `Settings.layer_paths`").
3. **Ledger contradicts shipped code.** `docs/implementation/README.md:7-8` (RF05 both in progress and complete), `:47` (RF00–RF12 "not started" while v2 loaders/defaults and the archive route ship), `:79` (catalog discrepancy described as always shown while `app/src/pages/catalog/[layer]/[...dataset].astro:35` renders it conditionally); `app/src/pages/areas/[slug].astro:5` comment claims no client island while `:213`/`:393` mount two.

## Required change

### A — Extend type checking (ARCH-1)

Add modules in batches, keeping `mypy` green after each batch:

1. `src/egg_n_bacon_housing/schemas/` (all four files).
2. `utils/validation.py`, `utils/validation_gateway.py` (already included), `utils/bronze.py`, `utils/output_registry.py`.
3. Remaining `utils/*` (`data_loader`, `school_features`, `mrt_line_mapping`, `hdb_lookups`, `regional_mapping`, `geo`, `logging_config`, `runtime`, `cache_fingerprints`, `data_quality`).

Rules: fix real annotations, do not blanket-ignore, do not add `# type: ignore` without a one-line reason. Do **not** enable `strict = true` in this order.

Add a guard test (e.g. `tests/test_type_scope.py`) that walks `src/egg_n_bacon_housing/**/*.py`, reads `[tool.mypy].files`, and fails when a module is neither listed nor in an explicit, commented exemption list. This prevents the scope silently shrinking again.

### B — Single layer-path resolver (ARCH-2)

Make one implementation authoritative. `Settings.layer_paths` owns the configured semantics; `resolve_layer_paths` delegates to it (or the reverse) — pick one and delete the other. Keep the `LayerDirs` relative/absolute behaviour. Add an equivalence test over every `_LAYER_KEYS` entry with both a relative and an absolute override.

### C — Ledger reconciliation (DOC-1)

1. Rewrite the status chronology so it states what the code does now; keep historical entries in a dated "history" section rather than as current status.
2. Fix the catalog-discrepancy sentence to match the conditional render.
3. Fix the area-page comment (or delete it) so it matches the two islands.
4. Add a short header rule: status statements must cite a file:line or a test, and superseded statements move to history rather than being edited in place.

Do not rewrite analytics study prose or editions.

## Verification

```bash
uv run mypy
uv run pytest tests/ -q --no-cov
uv run ruff check . && uv run ruff format --check .
uv run python scripts/tools/validate_docs_layout.py
```

## Owns

`pyproject.toml`, `src/egg_n_bacon_housing/config.py`, `src/egg_n_bacon_housing/utils/layer_writer.py`, `src/egg_n_bacon_housing/schemas/*` (annotations only), `src/egg_n_bacon_housing/utils/*` (annotations only), `tests/test_type_scope.py`, `docs/implementation/README.md`, `app/src/pages/areas/[slug].astro` (comment only).

## Do not touch

Runtime behaviour of any component or node. No schema field changes. No frontend logic. `uv.lock` (see WS-D2).

## Done when

`mypy` covers every `src/` module or an explicitly justified exemption, exactly one layer-path resolver exists with an equivalence test, the ledger matches the code, and the full gate passes.
