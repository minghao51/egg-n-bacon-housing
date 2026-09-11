# WS11 — Complete the Materializer Migration (A1, Batch 3)

## Context

The pipeline has TWO persistence regimes:

1. **Companion materializers** (`_MATERIALIZER_MAP`, pipeline.py ~:66-76): 6 nodes (unified_dataset, pa_monthly_metrics, appreciation_hotspots, planning_area_360, town_360, block_profile) validate with `persist=False` and are written by `components/materialization.py` — explicit, non-cached.
2. **Inline gateway persistence** (`_PERSISTED_VARS`, pipeline.py:68 + `:186` `recompute=` override): the remaining published nodes persist inside their own bodies via `validate_and_quarantine(..., persist=True)`. Because a Hamilton cache hit would skip those side effects, the cache adapter is forced to recompute them EVERY run — defeating caching for the whole silver path.

`_PERSISTED_VARS = tuple(name for name in _PUBLISHED_LAYERS if name not in _MATERIALIZER_MAP)` — the inline six are the silver-layer nodes in `components/cleaning.py` (cleaned_hdb_transactions, hdb_validated, cleaned_condo_transactions, condo_validated, geocoded_validated) plus `rental_yield` (`components/feature_rental.py`). `geocoded_properties` is an in-memory intermediate — NOT published, leave as-is.

This migration is the skill-documented "dedicated migration" that retires the legacy exception. NOTE: batches 1-2 changed these files (validation gateway semantics, sentinel fix in feature_transactions, schemas) — re-verify everything.

## Read first

- `.agents/skills/change-hamilton-pipeline/SKILL.md` (mandatory — note its bronze/gateway-legacy wording; you are completing that migration and will update the skill text accordingly)

## Owned files (EXCLUSIVE)

- `src/egg_n_bacon_housing/pipeline.py`
- `src/egg_n_bacon_housing/components/materialization.py`
- `src/egg_n_bacon_housing/components/cleaning.py`
- `src/egg_n_bacon_housing/components/feature_rental.py`
- `docs/guides/pipeline-development.md`
- `.agents/skills/change-hamilton-pipeline/SKILL.md`
- `tests/test_cleaning_validation.py`, `tests/test_rental_yield_metrics.py`, `tests/test_pipeline.py`, `tests/test_materialization.py` (create if absent)

## Forbidden

Everything else, incl. `components/feature_transactions.py`, `components/features.py`, `metrics.py`, `export.py`, `utils/validation_gateway.py` (consume its CURRENT API only), `utils/time_index.py`, `utils/hdb_lookups.py`, `config.py`, `tests/conftest.py`, `pyproject.toml`.

## Changes

### 1. Flip inline nodes to pure validate — `cleaning.py` (5 nodes), `feature_rental.py` (rental_yield)

- Each `validate_and_quarantine(..., persist=True, writer=writer, ...)` → `persist=False` (keep model, name, layer, sampling params identical). Keep quarantine-count `logger.warning` when > 0 (mirror the platinum-nodes pattern from `components/metrics.py`/`export.py`).
- Node signatures keep `writer` param ONLY if still needed (gateway `persist=False` may not need a writer — check current gateway signature; if unused, drop the param and note it).

### 2. Add 6 companion materializers — `components/materialization.py`

- `materialize_cleaned_hdb_transactions`, `materialize_hdb_validated`, `materialize_cleaned_condo_transactions`, `materialize_condo_validated`, `materialize_geocoded_validated`, `materialize_rental_yield` — each takes the node's output + `writer` and calls `writer.write(df, <name>, <layer>)` with the exact `_PUBLISHED_LAYERS` name/layer values. Follow the existing 6 materializers' style exactly (incl. any docstring convention).

### 3. Retire the recompute hack — `pipeline.py`

- Register the 6 new entries in `_MATERIALIZER_MAP`.
- `_PERSISTED_VARS` becomes empty → DELETE it and the `recompute=_PERSISTED_VARS` override in the cache adapter config (~:186). Nodes are now side-effect-free → cacheable; materializers keep their explicit caching-disable.
- Add a wiring invariant test: `_MATERIALIZED_NAMES == set(_PUBLISHED_LAYERS)` (every published output has exactly one materializer; the legacy inline path is gone).

### 4. Docs + skill sync

- `docs/guides/pipeline-development.md`: update the persistence section — single regime (nodes validate `persist=False`; ALL published outputs written by `materialization.py` companions); remove `_PERSISTED_VARS`/recompute mentions if present.
- `.agents/skills/change-hamilton-pipeline/SKILL.md`: update the "validation gateway persistence legacy exception" wording — gateway persistence via `persist=True` is now retired in production code (keep the param documented as available-but-unused, or note removal path). Keep the bronze exception wording (untouched, Batch 4).
- Both validators must pass: `uv run python scripts/tools/validate_docs_layout.py`, `uv run python scripts/tools/validate_agent_skills.py`.

## Tests required

- Each migrated node: validates + warns quarantine count, writes NOTHING itself (no file).
- Each new materializer: writes the right name/layer (tmp dir), empty frame → 0-row parquet (established writer behavior).
- Pipeline invariant: every `_PUBLISHED_LAYERS` key has a materializer; `_PERSISTED_VARS` gone.
- Silver path end-to-end-ish: gateway persist=False + materializer reproduces the same file content the old inline path wrote (same name/layer).

## Verification

```
uv run pytest tests/test_cleaning_validation.py tests/test_rental_yield_metrics.py tests/test_pipeline.py tests/test_materialization.py -x -q
uv run pytest tests/test_export.py tests/test_metrics.py tests/test_validation_gateway.py -q   # neighbors, run-only
uv run ruff check <owned src files> && uv run ruff format --check <owned src + test files>
uv run mypy <owned src files>
uv run python scripts/tools/validate_docs_layout.py && uv run python scripts/tools/validate_agent_skills.py
```

## Constraints

- NO commits. Owned files only. Do not change validation semantics, schemas, STAGE_VARS, or bronze paths.
- If any test outside ownership fails because of the persist flip, REPORT precisely (do not edit).

## Definition of done

One persistence regime; recompute hack deleted; invariant test in place; docs+skill accurate; all tests green.

## Report back

Edits (file:line), node→materializer table, test delta, verification tail, out-of-ownership failures if any.
