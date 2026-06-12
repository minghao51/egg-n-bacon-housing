# Troubleshooting Guide

Solutions for the supported pipeline and app workflows.

## Quick Fixes

| Issue                       | Quick Fix                                                  |
| --------------------------- | ---------------------------------------------------------- |
| `ModuleNotFoundError`       | Run from the repo root with `uv run`                       |
| Missing manual source files | Run `dotenvx run -- uv run python scripts/00_sync_data.py` |
| Pipeline stage failure      | Re-run the prerequisite stage with `main.py --stage ...`   |
| Docs validator failure      | Update the active docs path or remove stale references     |
| App test/build issue        | Reinstall in `app/` with `bun install`                     |

## Python Import Errors

Symptom:

```text
ModuleNotFoundError: No module named 'egg_n_bacon_housing'
```

Fix:

```bash
cd /path/to/egg-n-bacon-housing
uv run python main.py --stage all
```

## Missing Pipeline Outputs

If an expected dataset is not present, re-run the upstream stage:

```bash
uv run python main.py --stage ingest
uv run python main.py --stage clean
uv run python main.py --stage features
uv run python main.py --stage export
uv run python main.py --stage metrics
```

You can inspect the most common outputs with:

```python
from egg_n_bacon_housing.utils.data_loader import (
    load_market_summary,
    load_planning_area_metrics,
)

print(load_market_summary().shape)
print(load_planning_area_metrics().shape)
```

## OneMap Credential Problems

Check that `.env` contains the current credentials:

```bash
rg '^ONEMAP_' .env
```

If requests still fail, verify the account in the OneMap portal and re-run the failed stage.

## Manual Source Data Missing

The repo does not keep the full manual CSV and GeoJSON bundle in git.

Sync it with:

```bash
dotenvx run -- uv run python scripts/00_sync_data.py
```

## Docs Validator Failures

Run:

```bash
uv run python scripts/tools/validate_docs_layout.py
```

Typical causes:

- links to removed files from older pipeline workflows
- references to retired generated app-content copies
- app docs that still describe an outdated workflow

## App Build or E2E Failures

Run commands from `app/`:

```bash
cd app
bun install
bun run build
bun run test:e2e
```

If the preview-based suite fails, run:

```bash
cd app
bun run test:e2e:prod
```

## Large Dataset Memory Pressure

Read only the columns you need:

```python
import pandas as pd

df = pd.read_parquet(
    "data/04_platinum/unified_dataset.parquet",
    columns=["planning_area", "price_psf", "rental_yield_pct"],
)
```

## Jupyter Environment Drift

If notebooks cannot find project modules:

```bash
uv run jupyter notebook
uv run python -m ipykernel install --user --name=egg-n-bacon
```

## Related Docs

- [Quick Start](guides/quick-start.md)
- [Usage Guide](guides/usage-guide.md)
- [R2 Sync Guide](guides/r2-sync-guide.md)
