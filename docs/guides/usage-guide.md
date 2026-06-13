# Usage Guide

**Last Updated**: 2026-06-12 | **Status**: Active

## Overview

This guide covers the supported day-to-day workflow:

- set up the repo with `uv`
- run the Hamilton pipeline through `main.py`
- inspect pipeline outputs under `data/`
- run the Astro app from `app/`
- maintain published analytics through `docs/analytics/` and `app/public/data/`

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
dotenvx run -- uv run python main.py --help
```

## Run the Pipeline

Default end-to-end flow:

```bash
dotenvx run -- uv run python main.py --stage all
```

Single-stage runs:

```bash
dotenvx run -- uv run python main.py --stage ingest
dotenvx run -- uv run python main.py --stage clean
dotenvx run -- uv run python main.py --stage features
dotenvx run -- uv run python main.py --stage export
dotenvx run -- uv run python main.py --stage metrics
```

Generate a DAG image:

```bash
dotenvx run -- uv run python main.py --visualize
```

Run selected outputs only:

```bash
dotenvx run -- uv run python main.py --final-var unified_dataset --final-var dashboard_json
```

## Data Locations

| Layer    | Path                         |
| -------- | ---------------------------- |
| Bronze   | `data/pipeline/01_bronze/`   |
| Silver   | `data/pipeline/02_silver/`   |
| Gold     | `data/pipeline/03_gold/`     |
| Platinum | `data/pipeline/04_platinum/` |

App-facing assets:

| Content                            | Path                        |
| ---------------------------------- | --------------------------- |
| Analytics markdown source          | `docs/analytics/`           |
| Analytics images and static assets | `app/public/data/analysis/` |
| Dashboard JSON and gzipped data    | `app/public/data/`          |

## Load Data in Python

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
Use Bun as the only supported package manager for `app/`.

The supported analytics publishing surface is:

- markdown source in `docs/analytics/`
- app-consumed datasets in `app/public/data/`
- app-served analytics images in `app/public/data/analysis/`

Historical analysis outputs under `data/analytics/` and `data/analysis/` are not part of the supported runtime surface.

## Main Quality Checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
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
