# Architecture

**Last Updated**: 2026-06-12 | **Status**: Active

## Overview

`egg-n-bacon-housing` is a Python-first Singapore housing data platform with two distinct supported surfaces:

- a Hamilton pipeline that moves data through bronze, silver, gold, and platinum layers
- an Astro publishing layer that serves analytics markdown and precomputed app artifacts

The Hamilton DAG is the automated system of record. Published analytics are maintained as markdown plus precomputed app assets; the old standalone Python analytics package has been retired.

## System Shape

```text
External APIs / manual files
        |
        v
src/egg_n_bacon_housing/components/
        |
        v
data/pipeline/01_bronze -> 02_silver -> 03_gold -> 04_platinum
        |
        +--> app/public/data/
        |
        +--> docs/analytics/ (loaded directly by Astro)
```

## Repository Layout

```text
egg-n-bacon-housing/
├── app/                              # Astro web app
├── data/
│   ├── analytics/                    # Analysis artifacts and charts
│   ├── manual/                       # Manual source files synced from R2
│   └── pipeline/
│       ├── 01_bronze/
│       ├── 02_silver/
│       ├── 03_gold/
│       └── 04_platinum/
├── docs/
│   ├── analytics/                    # Analytics markdown loaded by Astro
│   ├── guides/                       # Operational guides
│   ├── plans/                        # Design and implementation plans
│   └── archive/                      # Historical docs
├── scripts/
│   ├── 00_sync_data.py               # R2 manual-data sync
│   ├── 99_cleanup.py
│   └── tools/validate_docs_layout.py
├── src/egg_n_bacon_housing/
│   ├── adapters/                     # External clients and integrations
│   ├── components/                   # Hamilton DAG nodes
│   ├── schemas/                      # Pydantic models
│   ├── utils/                        # Loaders, caching, metrics, helpers
│   ├── config.py                     # Pydantic settings
│   └── pipeline.py                   # Hamilton driver builder
├── tests/
├── main.py                           # CLI entry point
└── pyproject.toml
```

## Core Runtime Flow

### Configuration

[src/egg_n_bacon_housing/config.py](../src/egg_n_bacon_housing/config.py) loads:

- environment variables from `.env`
- defaults and nested settings from pydantic-settings models
- normalized accessors for `data/` and medallion-layer directories

Key path properties:

- `settings.data_dir`
- `settings.bronze_dir`
- `settings.silver_dir`
- `settings.gold_dir`
- `settings.platinum_dir`

### Pipeline Construction

[src/egg_n_bacon_housing/pipeline.py](../src/egg_n_bacon_housing/pipeline.py) imports the numbered component modules dynamically and builds a Hamilton `Driver`.

Execution entrypoint:

- [main.py](../main.py)

### Downstream Consumers

| Consumer        | Reads from                            | Purpose                                       |
| --------------- | ------------------------------------- | --------------------------------------------- |
| Astro app       | `app/public/data/`, `docs/analytics/` | Dashboard and analytics publishing            |
| Utility loaders | `src/egg_n_bacon_housing/utils/`      | Reusable access patterns for Python workflows |

## Pipeline Stages

| Stage     | Module family                | Typical outputs                                           |
| --------- | ---------------------------- | --------------------------------------------------------- |
| Ingestion | `components/01_ingestion.py` | raw transactions, rental data, schools, malls, macro data |
| Cleaning  | `components/02_cleaning.py`  | cleaned transaction sets, validation artifacts, geocoding |
| Features  | `components/03_features.py`  | rental yield and amenity-enriched features                |
| Export    | `components/04_export.py`    | unified dataset, dashboard JSON, app exports              |
| Metrics   | `components/05_metrics.py`   | area metrics, affordability, hotspots                     |

## Content Publishing Flow

Analytics content is authored in `docs/analytics/` and loaded by Astro through [app/src/content.config.ts](../app/src/content.config.ts). App-consumed analytics data lives under `app/public/data/`. There is no supported Python script runner or generated intermediate content-copy step in the current repo shape.

## Important Boundaries

- `src/egg_n_bacon_housing/components/` is supported pipeline code.
- `docs/analytics/` and `app/public/data/` are the supported analytics publishing surface.
- Historical analysis outputs under `data/analytics/` and `data/analysis/` were retired from the tracked supported surface and should be treated as reproducible archive material, not runtime inputs.
- Medallion outputs live under `data/pipeline/01_bronze/` through `data/pipeline/04_platinum/`.

## Developer Workflow

```bash
uv run python main.py
uv run python main.py --stage features
uv run python scripts/tools/validate_docs_layout.py
uv run pytest --no-cov
uv run ruff check .
```
