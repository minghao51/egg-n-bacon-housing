# Usage Guide

**Last Updated**: 2026-09-04 | **Status**: Active

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
uv run python scripts/00_sync_data.py
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
uv run python main.py --final-var unified_dataset
```

## Refresh Data

Bronze parquets never expire on their own — ingestion nodes short-circuit when
the file exists. Use `--refresh` to force re-fetching:

```bash
# Full refresh: clear ALL bronze parquets + DAG + API caches, then run
uv run python main.py --refresh --stage all

# Re-fetch a specific dataset (glob matched against bronze paths)
uv run python main.py --refresh 'raw_hdb_*' --stage all
```

Note: targeted `--refresh <pattern>` clears bronze files only; the 24h API
response cache is only cleared by the full form.

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

Published outputs are parquet files — read them directly with pandas:

```python
import pandas as pd

unified = pd.read_parquet("data/pipeline/04_platinum/unified_dataset.parquet")
pa_metrics = pd.read_parquet("data/pipeline/04_platinum/metrics/pa_monthly_metrics.parquet")
print(unified.shape, pa_metrics.shape)
```

For planning-area spatial lookups (point-in-polygon assignment for arbitrary
coordinates), use the `SpatialReferenceRepository` in
[src/egg_n_bacon_housing/utils/data_loader.py](../../src/egg_n_bacon_housing/utils/data_loader.py):

```python
from pathlib import Path

from egg_n_bacon_housing.utils.data_loader import SpatialReferenceRepository

spatial = SpatialReferenceRepository(Path("data/manual/geojsons"))
planning_area = spatial.planning_areas_for_points(lat=pd.Series([1.3521]), lon=pd.Series([103.8198]))
```

## Run the App

```bash
cd app
bun install --frozen-lockfile
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
