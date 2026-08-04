# Pipeline Development Guide

**Status**: Active

This guide defines the supported Hamilton pipeline contract. Production runs
start at `main.py` and use `build_pipeline()` and `run_pipeline()` from
`src/egg_n_bacon_housing/pipeline.py`.

## Stages and ownership

| CLI stage  | Component                | Responsibility                                   | Output boundary                                         |
| ---------- | ------------------------ | ------------------------------------------------ | ------------------------------------------------------- |
| `ingest`   | `components/ingestion/`  | Acquire source data and normalize it into bronze | `data/pipeline/01_bronze/`                              |
| `clean`    | `components/cleaning.py` | Clean, validate, and quarantine invalid records  | `data/pipeline/02_silver/`                              |
| `features` | `components/features.py` | Build reusable entities and derived features     | `data/pipeline/03_gold/`                                |
| `export`   | `components/export.py`   | Produce stable and app-facing datasets           | `data/pipeline/04_platinum/` and configured app outputs |
| `metrics`  | `components/metrics.py`  | Produce analytical metrics and summaries         | `data/pipeline/04_platinum/metrics/`                    |

The `all` stage selects the supported published outputs across the DAG. Use
`--final-var` for a deliberate narrower execution.

## Layer invariants

- Bronze is source-owned and reproducible. Do not apply business rules or
  silently overwrite a valid cache with an empty response.
- Silver is the primary validation boundary. Full validation quarantines schema
  failures and passes valid records forward. Current sample validation detects
  and quarantines invalid sampled rows but persists the full input; treat it as
  a diagnostic, not proof that every persisted row is valid.
- Gold contains reusable entities and features, not app-specific presentation
  artifacts.
- Platinum contains stable exports, app-facing data, and analytical metrics.
- Nodes receive settings, paths, geocoders, and writers through dependency
  injection. New silver/gold/platinum outputs use `LayerWriter`; existing bronze
  source caches and validation-gateway persistence retain their established
  paths pending a dedicated migration.

## Adding or changing a node

1. Identify the owning stage and its layer contract.
2. Add the node in the owning component module; for ingestion, place source
   transport in an adapter and DAG assembly in `components/ingestion/`.
3. Trace Hamilton dependencies and confirm the module is included by
   `pipeline.py`.
4. Add the output to `STAGE_VARS` when it is a supported stage output.
5. Update schemas, source/lineage documentation, and downstream readers.
6. Add focused tests for the node contract, failure behavior, and persistence.
7. Run the pipeline, ingestion, docs, lint, formatting, type, and agent-skill
   checks listed below.

Do not add a parallel runner, new ad-hoc persistence, or retired standalone
analytics scripts to execute DAG work.

## Definition of done

A pipeline change is complete when its node is reachable through the supported
runner, its layer and schema contracts are documented, its tests cover the
changed behavior, its stage outputs are registered, and focused plus repository
quality checks pass.

```bash
uv run pytest tests/test_pipeline.py tests/test_pipeline_integration.py --no-cov -q
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python scripts/tools/validate_docs_layout.py
uv run python scripts/tools/validate_agent_skills.py
git diff --check
```
