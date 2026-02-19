# Architecture

## Overview

This is a **stage-based ETL pipeline** for processing Singapore housing data, with a separate **Astro/React dashboard frontend**.

## Pattern

**Pipeline Pattern (L0-L5 Stages)**

| Stage | Purpose |
|-------|---------|
| **L0 (Collection)** | Fetch HDB/URA transactions from data.gov.sg |
| **L1 (Processing)** | Clean data, geocode addresses (OneMap → Google fallback) |
| **L2 (Features)** | Add MRT distances, CBD distance, school tiers, amenities |
| **L3 (Export)** | Create unified dataset, export JSONs for webapp |
| **L4 (Analysis)** | Run ML models, spatial analysis, forecasting |
| **L5 (Metrics)** | Calculate dashboard metrics |

## Layers

### 1. Data Layer (`scripts/core/data_helpers.py`)
- Parquet file I/O with metadata tracking
- `load_parquet(dataset_name)` / `save_parquet(df, dataset_name)`
- Metadata stored in `data/metadata.json`

### 2. Configuration Layer (`scripts/core/config.py`)
- Centralized Config class with all paths and settings
- Environment variables loaded from `.env`
- Feature flags (USE_CACHING, VERBOSE_LOGGING)

### 3. Processing Layer (`scripts/core/stages/`)
- L0_collect.py - Data collection from APIs
- L1_process.py - Data cleaning, geocoding
- L2_features.py / L2_rental.py - Feature engineering
- L3_export.py - Data export (largest file: 1632 lines)
- L4_analysis.py - ML/analytics
- L5_metrics.py - Dashboard metrics

### 4. External Services Layer
- OneMap API - Singapore geocoding (primary)
- Google Maps API - Geocoding fallback
- data.gov.sg - HDB/URA transaction data

### 5. Frontend Layer (`app/`)
- Astro static site generator
- React components for interactive dashboards
- Data read from JSON files only (no API)

## Data Flow

```
data.gov.sg → L0 (collect) → L1 (process/geocode) → L2 (features)
                                                              ↓
                                            L3 (unified export) → JSONs
                                                              ↓
                                            L5 (metrics) → dashboard metrics
                                                              ↓
                                            L4 (analysis) → ML models
                                                              ↓
                                            app/public/data/ → Dashboard reads JSONs
```

## Entry Points

| Component | Entry Point | Purpose |
|-----------|-------------|---------|
| **Pipeline** | `scripts/run_pipeline.py` | Main CLI orchestrator |
| **Webapp** | `app/astro.config.mjs` | Astro configuration |
| **Config** | `scripts/core/config.py` | Centralized settings |

## Routing/Initialization

**Python Pipeline** (`scripts/run_pipeline.py:47-50`):
```python
from scripts.core.stages.L0_collect import collect_all_datagovsg
from scripts.core.stages.L1_process import run_processing_pipeline
from scripts.core.stages.L2_rental import run_rental_pipeline
```

**Frontend** (`app/astro.config.mjs`):
- Astro + React + MDX + Tailwind integrations
- Vite alias: `@` → `app/src/`
- Pages in `app/src/pages/` (dashboard/, analytics/, index.astro)

## Key Abstractions

- **DataHelpers**: Load/save parquets with metadata lineage
- **Config**: Singleton-style config class
- **Geocoder**: OneMap→Google fallback chain
- **Stages**: Modular pipeline stages (L0-L5)

## Frontend/Backend Separation

- **Data Processing** (Python): `scripts/` → Parquet files → `data/parquets/`
- **Dashboard** (Astro/React): `app/` → Reads JSONs from `app/public/data/`
- **Key Principle**: Python exports JSONs; frontend only reads (no backend API)
