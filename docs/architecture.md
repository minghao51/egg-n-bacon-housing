# Architecture

**Last Updated**: 2026-04-22 | **Status**: Active

## Overview

`egg-n-bacon-housing` is a Python-first Singapore housing data platform with two distinct execution modes:

- A Hamilton pipeline that moves data through bronze, silver, gold, and platinum layers
- Standalone analytics scripts that read exported datasets and produce reports, charts, and app content

The Hamilton DAG is the automated system of record. Analytics modules are intentionally separate so they can evolve independently without changing pipeline orchestration.

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
        +--> docs/analytics/ -> app/src/content/analytics/
        |
        +--> src/egg_n_bacon_housing/analytics/
```

## Repository Layout

```text
egg-n-bacon-housing/
├── app/                              # Astro web app
├── data/
│   ├── analytics/                    # Analysis artifacts and charts
│   ├── manual/                       # Manual source files and geojsons
│   └── pipeline/
│       ├── 01_bronze/
│       ├── 02_silver/
│       ├── 03_gold/
│       └── 04_platinum/
├── docs/
│   ├── analytics/                    # Human-authored analytics markdown
│   ├── guides/                       # Operational guides
│   ├── plans/                        # Design and implementation plans
│   └── archive/                      # Historical docs
├── scripts/
│   ├── 01_ingest.py
│   ├── 02_clean.py
│   ├── 03_features.py
│   ├── 04_export.py
│   ├── 05_metrics.py
│   ├── 99_cleanup.py
│   ├── sync-content.sh
│   └── tools/validate_docs_layout.py
├── src/egg_n_bacon_housing/
│   ├── adapters/                     # External clients and integrations
│   ├── analytics/                    # Standalone analysis scripts and pipelines
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

### 1. Configuration

[src/egg_n_bacon_housing/config.py](../src/egg_n_bacon_housing/config.py) loads:

- environment variables from `.env`
- defaults and nested settings from `config.yaml`
- normalized accessors for `data/` and medallion-layer directories

Key path properties:

- `settings.data_dir`
- `settings.bronze_dir`
- `settings.silver_dir`
- `settings.gold_dir`
- `settings.platinum_dir`

### 2. Pipeline Construction

[src/egg_n_bacon_housing/pipeline.py](../src/egg_n_bacon_housing/pipeline.py) imports the numbered component modules dynamically and builds a Hamilton `Driver`.

Execution entrypoints:

- [main.py](../main.py) for CLI-driven stage selection
- [scripts/01_ingest.py](../scripts/01_ingest.py) through [scripts/05_metrics.py](../scripts/05_metrics.py) for direct stage runs

### 3. Medallion Data Flow

| Layer | Path | Responsibility |
|-------|------|----------------|
| Bronze | `data/pipeline/01_bronze/` | Raw fetched source data |
| Silver | `data/pipeline/02_silver/` | Cleaned and validated datasets |
| Gold | `data/pipeline/03_gold/` | Enriched feature tables |
| Platinum | `data/pipeline/04_platinum/` | Dashboard exports, metrics, final datasets |

### 4. Downstream Consumers

| Consumer | Reads from | Purpose |
|----------|------------|---------|
| Astro app | `app/public/data/`, `app/src/content/analytics/` | Dashboard and analytics publishing |
| Analytics scripts | `data/pipeline/04_platinum/` and supporting layers | On-demand research and forecasting |
| Utility loaders | `src/egg_n_bacon_housing/utils/` | Reusable access patterns for Python workflows |

## Pipeline Stages

| Stage | Module family | Typical outputs |
|-------|---------------|-----------------|
| Ingestion | `components/01_ingestion.py` | raw transactions, rental data, schools, malls, macro data |
| Cleaning | `components/02_cleaning.py` | cleaned transaction sets, validation artifacts, geocoding |
| Features | `components/03_features.py` | rental yield and amenity-enriched features |
| Export | `components/04_export.py` | unified dataset, dashboard JSON, app exports |
| Metrics | `components/05_metrics.py` | area metrics, affordability, hotspots |
| Analytics | `components/06_analytics.py` | optional DAG-connected analytical outputs |

## Analytics Publishing Flow

Analytics content is authored in Markdown and then synced into the Astro app:

1. Write or update a document in `docs/analytics/`
2. Run [scripts/sync-content.sh](../scripts/sync-content.sh)
3. The script copies `.md` to `app/src/content/analytics/*.mdx`
4. Charts and images from `data/analytics/` are mirrored to `app/public/data/analysis/`
5. Astro renders the synced MDX through [app/src/content.config.ts](../app/src/content.config.ts)

The sync step is intentionally conservative: unsupported analytics-only MDX component markup should fail the sync rather than being dropped silently.

## Important Boundaries

### Pipeline vs Analytics

- `src/egg_n_bacon_housing/components/` is production pipeline code
- `src/egg_n_bacon_housing/analytics/` is exploratory and reporting code
- Analytics code may consume pipeline outputs, but the automated pipeline should not depend on notebook-era assumptions or ad hoc research scripts

### Docs Source vs App Copy

- `docs/analytics/*.md` is the editable source of truth
- `app/src/content/analytics/*.mdx` is generated content for the Astro app
- [scripts/tools/validate_docs_layout.py](../scripts/tools/validate_docs_layout.py) checks that those two sets stay aligned

## Developer Workflow

Common commands:

```bash
uv run python main.py
uv run python main.py --stage features
./scripts/sync-content.sh
uv run python scripts/tools/validate_docs_layout.py
uv run pytest
uv run ruff check .
```

## Related Docs

- [README.md](../README.md)
- [docs/guides/usage-guide.md](../docs/guides/usage-guide.md)
- [docs/README.md](../docs/README.md)
