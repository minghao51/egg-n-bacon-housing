# Usage Guide

**Last Updated**: 2026-04-22 | **Status**: Active

## Overview

This guide covers the supported day-to-day workflow for the repository:

- Set up the local environment with `uv`
- Run the Hamilton pipeline through `main.py`
- Inspect pipeline outputs under `data/`
- Run standalone analytics scripts from `src/egg_n_bacon_housing/analytics/`

## Setup

```bash
git clone <repo-url>
cd egg-n-bacon-housing
uv sync
cp .env.example .env
dotenvx run -- uv run python scripts/00_sync_data.py
```

Required environment variables:

| Variable                | Required | Purpose               |
| ----------------------- | -------- | --------------------- |
| `ONEMAP_EMAIL`          | Yes      | OneMap authentication |
| `ONEMAP_EMAIL_PASSWORD` | Yes      | OneMap authentication |
| `GOOGLE_API_KEY`        | No       | Geocoding fallback    |
| `R2_ACCESS_KEY_ID`      | Yes      | Manual data sync      |
| `R2_SECRET_ACCESS_KEY`  | Yes      | Manual data sync      |
| `R2_BUCKET`             | Yes      | Manual data sync      |
| `R2_ENDPOINT`           | Yes      | Manual data sync      |

Verification:

```bash
uv run pytest
uv run python main.py --help
```

## Run The Pipeline

Run the default end-to-end flow:

```bash
uv run python main.py
```

Run a single stage:

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

Run only selected outputs:

```bash
uv run python main.py --final-var unified_dataset --final-var dashboard_json
```

## Stage Map

| Stage      | Purpose                                    | Main outputs                                                                    |
| ---------- | ------------------------------------------ | ------------------------------------------------------------------------------- |
| `ingest`   | Fetch raw source data                      | `raw_hdb_resale_transactions`, `raw_condo_transactions`, `raw_hdb_rental`       |
| `clean`    | Validate and standardize raw data          | `cleaned_hdb_transactions`, `cleaned_condo_transactions`, `geocoded_properties` |
| `features` | Build model and analytics features         | `rental_yield`, `features_with_amenities`, `unified_features`                   |
| `export`   | Produce app- and dashboard-facing datasets | `unified_dataset`, `dashboard_json`, `segments_data`                            |
| `metrics`  | Compute summary metrics and rankings       | `price_metrics_by_area`, `rental_yield_by_area`, `affordability_metrics`        |

## Data Locations

Pipeline outputs use a medallion layout rooted at `data/`:

| Layer    | Path                |
| -------- | ------------------- |
| Bronze   | `data/01_bronze/`   |
| Silver   | `data/02_silver/`   |
| Gold     | `data/03_gold/`     |
| Platinum | `data/04_platinum/` |

App-facing analytics content is synced to:

| Content               | Path                         |
| --------------------- | ---------------------------- |
| Analytics source docs | `docs/analytics/`            |
| Synced MDX copies     | `app/src/content/analytics/` |
| Analytics images      | `app/public/data/analysis/`  |

## Load Data In Python

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

## Run Analytics

Exploratory analytics are standalone scripts under `src/egg_n_bacon_housing/analytics/`. They are not wired into the automated Hamilton DAG.

Examples:

```bash
uv run python src/egg_n_bacon_housing/analytics/analysis/market/analyze_lease_decay.py
uv run python src/egg_n_bacon_housing/analytics/analysis/spatial/analyze_spatial_hotspots.py
uv run python src/egg_n_bacon_housing/analytics/pipelines/forecast_prices_pipeline.py
```

## Common Workflows

Rebuild a stage after deleting an output:

```bash
rm data/02_silver/cleaned_hdb_transactions.parquet
uv run python main.py --stage clean
```

Run the main quality checks:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python scripts/tools/validate_docs_layout.py
```

## Troubleshooting

| Issue                                      | What to check                                                                                     |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| `ModuleNotFoundError: egg_n_bacon_housing` | Run commands from the repo root with `uv run`                                                     |
| Missing parquet outputs                    | Run the upstream pipeline stage again                                                             |
| OneMap authentication failures             | Confirm `ONEMAP_EMAIL` and `ONEMAP_EMAIL_PASSWORD` in `.env`                                      |
| Analytics page missing from app            | Verify the slug exists in `app/src/content/analytics/` and rerun app build                        |
| Docs validator failure                     | Fix the referenced path or update the active-doc scope in `scripts/tools/validate_docs_layout.py` |

## Related Docs

- [README.md](../../README.md)
- [docs/architecture.md](../architecture.md)
- [docs/README.md](../README.md)
- [scripts/tools/validate_docs_layout.py](../../scripts/tools/validate_docs_layout.py)
