# Usage Guide

**Last Updated**: 2026-06-12 | **Status**: Active

## Overview

This guide covers the supported day-to-day workflow:

- set up the repo with `uv`
- run the Hamilton pipeline through `main.py`
- inspect pipeline outputs under `data/`
- run the Astro app from `app/`
- use standalone analytics scripts only when you explicitly need exploratory analysis

## Setup

```bash
git clone <repo-url>
cd egg-n-bacon-housing
uv sync
cp .env.example .env
dotenvx run -- uv run python scripts/00_sync_data.py
```

Verification:

```bash
uv run pytest --no-cov
uv run python main.py --help
```

## Run the Pipeline

Default end-to-end flow:

```bash
uv run python main.py --stage all
```

Single-stage runs:

```bash
uv run python main.py --stage ingest
uv run python main.py --stage clean
uv run python main.py --stage features
uv run python main.py --stage export
uv run python main.py --stage metrics
```

Generate a DAG image:

```bash
uv run python main.py --visualize
```

Run selected outputs only:

```bash
uv run python main.py --final-var unified_dataset --final-var dashboard_json
```

## Data Locations

| Layer    | Path                |
| -------- | ------------------- |
| Bronze   | `data/01_bronze/`   |
| Silver   | `data/02_silver/`   |
| Gold     | `data/03_gold/`     |
| Platinum | `data/04_platinum/` |

App-facing assets:

| Content                            | Path                        |
| ---------------------------------- | --------------------------- |
| Analytics markdown source          | `docs/analytics/`           |
| Analytics images and static assets | `app/public/data/analysis/` |
| Dashboard JSON and gzipped data    | `app/public/data/`          |

## Load Data in Python

For metadata-backed parquet access, use [src/egg_n_bacon_housing/utils/data_helpers.py](../../src/egg_n_bacon_housing/utils/data_helpers.py).

```python
from egg_n_bacon_housing.utils.data_helpers import load_parquet

df = load_parquet("L3_housing_unified")
print(df.head())
```

For convenience loaders around common outputs, use [src/egg_n_bacon_housing/utils/data_loader.py](../../src/egg_n_bacon_housing/utils/data_loader.py).

```python
from egg_n_bacon_housing.utils.data_loader import (
    load_market_summary,
    load_planning_area_metrics,
)

market_summary = load_market_summary()
planning_area_metrics = load_planning_area_metrics()
print(market_summary.shape, planning_area_metrics.shape)
```

## Run the App

```bash
cd app
bun install
bun run dev
```

The Astro app loads analytics markdown directly from `docs/analytics/` through `app/src/content.config.ts`.

## Run Analytics Scripts

`src/egg_n_bacon_housing/analytics/` is exploratory, not part of the automated DAG. Use it when you intentionally want standalone analysis.

Examples:

```bash
uv run python src/egg_n_bacon_housing/analytics/analysis/market_analyze_lease_decay.py
uv run python src/egg_n_bacon_housing/analytics/analysis/spatial_analyze_spatial_hotspots.py
uv run python -m egg_n_bacon_housing.analytics.pipelines.forecast_prices_pipeline
```

## Main Quality Checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src/egg_n_bacon_housing/components src/egg_n_bacon_housing/adapters src/egg_n_bacon_housing/utils/cache.py src/egg_n_bacon_housing/utils/contracts.py src/egg_n_bacon_housing/pipeline.py src/egg_n_bacon_housing/config.py tests
uv run python scripts/tools/validate_docs_layout.py
```

## Troubleshooting

| Issue                                      | What to check                                                                  |
| ------------------------------------------ | ------------------------------------------------------------------------------ |
| `ModuleNotFoundError: egg_n_bacon_housing` | Run commands from the repo root with `uv run`                                  |
| Missing parquet outputs                    | Run the upstream stage again                                                   |
| OneMap authentication failures             | Confirm `ONEMAP_EMAIL` and `ONEMAP_EMAIL_PASSWORD` in `.env`                   |
| Analytics page missing from app            | Verify the markdown file exists in `docs/analytics/` and rerun `bun run build` |
| Docs validator failure                     | Fix the referenced path or update the active-doc contract                      |

## Related Docs

- [README.md](../../README.md)
- [Architecture](../architecture.md)
- [E2E Testing](./e2e-testing.md)
- [R2 Sync Guide](./r2-sync-guide.md)
