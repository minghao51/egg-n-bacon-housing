---
name: change-hamilton-pipeline
description: Safely change the Hamilton DAG, stage outputs, medallion boundaries, schemas, validation, persistence, or pipeline tests in egg-n-bacon-housing.
---

# Change the Hamilton pipeline

Use this skill for changes to Hamilton nodes, dependency wiring, `STAGE_VARS`,
CLI stages, Pydantic schemas, validation gateways, `LayerWriter`, pipeline
settings, or pipeline tests.

## Runtime contract

The supported production path is:

```text
main.py -> build_pipeline() -> run_pipeline() -> Hamilton Driver
```

Use the existing driver and inject runtime dependencies through Hamilton inputs.
Do not create a second production runner or import global settings into nodes.
Use `LayerWriter` for new silver, gold, and platinum outputs: every published
output is persisted by exactly one companion `materialize_<node>` node in
`components/materialization.py`, registered in `_MATERIALIZER_MAP`. Computing
nodes are side-effect-free — validation-gateway calls run with `persist=False`
— so the legacy `ValidationGateway` `persist=True` inline-persistence regime is
retired from production code; the parameter remains available-but-unused in the
gateway, and it must not be reintroduced into nodes without a dedicated
migration. Existing bronze source caches retain their established self-managed
paths as a legacy exception; do not extend that exception without a dedicated
migration.

The five stages and their module ownership are:

| Stage      | Modules                                                                                                                          | Layer responsibility                          |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| `ingest`   | `components/ingestion/`                                                                                                          | Acquire and normalize source data into bronze |
| `clean`    | `components/cleaning.py`                                                                                                         | Validate, clean, and quarantine into silver   |
| `features` | `components/features.py`, `components/feature_rental.py`, `components/feature_transactions.py`, `components/feature_profiles.py` | Build reusable entities and features in gold  |
| `export`   | `components/export.py`                                                                                                           | Write stable and app-facing platinum outputs  |
| `metrics`  | `components/metrics.py`                                                                                                          | Write analytical platinum metrics             |

## Required workflow

1. Read `docs/guides/pipeline-development.md`, the relevant component, its
   schemas and utilities, and the focused tests before editing.
2. Trace the Hamilton dependencies from the requested final variable. Confirm
   that new nodes are imported by the module package and are reachable from a
   named stage or an explicit `--final-var`.
3. Keep layer ownership explicit: bronze is source acquisition, silver is
   validated data, gold is reusable feature data, and platinum is published or
   analytical output.
4. Add or update `STAGE_VARS` when a stage's supported outputs change. Keep the
   CLI stage names and documentation synchronized.
5. Use injected `Settings`, directories, geocoders, and writers. Use Pydantic
   schemas and the validation gateway at validation boundaries.
6. Add focused tests for dependency wiring, output paths, empty/error behavior,
   and the changed node contract. Do not weaken existing tests to make a new
   implementation fit.

## Verification

Run the smallest relevant focused tests first, then:

```bash
uv run pytest tests/test_pipeline.py tests/test_pipeline_integration.py --no-cov -q
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python scripts/tools/validate_docs_layout.py
uv run python scripts/tools/validate_agent_skills.py
git diff --check
```

If a repository-wide check reports unrelated existing debt, report it separately
from failures in the touched slice.
