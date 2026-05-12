# Architecture

## Overview

Dual-stack project: **Python data pipeline** (Hamilton DAG) + **Astro webapp**.

## Python Pipeline: Hamilton DAG + Medallion Architecture

Directed acyclic graph orchestrated by Hamilton (`sf-hamilton`). Function signatures define dependencies — each function is a DAG node producing exactly one variable.

### Medallion Layers

| Layer    | Directory           | Component                    | Purpose                           |
| -------- | ------------------- | ---------------------------- | --------------------------------- |
| Bronze   | `data/01_bronze/`   | `components/01_ingestion.py` | Raw immutable data from APIs      |
| Silver   | `data/02_silver/`   | `components/02_cleaning.py`  | Validated, cleaned data           |
| Gold     | `data/03_gold/`     | `components/03_features.py`  | Feature-enriched data             |
| Platinum | `data/04_platinum/` | `components/04_export.py`    | Exports, dashboard JSON, segments |
| Platinum | `data/04_platinum/` | `components/05_metrics.py`   | Planning area metrics, hotspots   |
| —        | —                   | `components/06_analytics.py` | Analytics integration             |

### Entry Points

| Component       | Entry Point                                                      |
| --------------- | ---------------------------------------------------------------- |
| Pipeline CLI    | `main.py` (`--stage {ingest,clean,features,export,metrics,all}`) |
| Pipeline driver | `src/egg_n_bacon_housing/pipeline.py`                            |
| Configuration   | `src/egg_n_bacon_housing/config.py` (pydantic-settings)          |
| Webapp          | `app/src/pages/index.astro`                                      |

### Data Flow

```
APIs (data.gov.sg, OneMap, URA)
        ↓
Bronze → Silver → Gold → Platinum
(ingest) (clean)  (features) (export + metrics)
        ↓
  dashboard JSON → Astro webapp
  analytics modules → standalone analysis
```

## Astro Webapp

File-based routing (`app/src/pages/`), React islands for interactive components, MDX content collections for analytics pages.

### Routing

- `/` → landing page
- `/dashboard` → market overview
- `/dashboard/map` → price map
- `/dashboard/trends` → trends
- `/dashboard/segments` → market segments
- `/dashboard/leaderboard` → town rankings
- `/analytics` → analytics overview
- `/analytics/[slug]` → dynamic analytics pages
