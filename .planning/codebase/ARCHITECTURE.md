# Egg-n-Bacon-Housing: System Architecture

## Overview

The egg-n-bacon-housing project is a **modular data pipeline** that processes Singapore housing transaction data, performs spatial/ML analysis, and serves results via an interactive web dashboard.

**Architecture Pattern**: ETL + Analytics + Visualization
**Data Flow**: Batch processing with scheduled updates
**Entry Points**: `scripts/run_pipeline.py`, individual stage scripts

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                                 │
│  data.gov.sg API  │  OneMap API  │  Manual CSV Uploads          │
└────────────────────┬────────────────┬────────────────────────────┘
                     │                │
                     ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  L0: DATA COLLECTION                            │
│  - Fetch HDB resale prices                                     │
│  - Fetch URA private property transactions                     │
│  - Download rental indices                                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  L1: DATA PROCESSING                            │
│  - Load and clean transaction data                             │
│  - Extract unique addresses                                    │
│  - Geocode addresses (OneMap → Google fallback)                │
│  - Filter and validate results                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  L2: FEATURE ENGINEERING                        │
│  - Add MRT distances (by line)                                 │
│  - Add CBD distance                                            │
│  - Add planning area                                          │
│  - Add school features (tier, distance)                        │
│  - Add amenities proximity                                     │
│  - Add rental rates                                            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  L3: DATA EXPORT                                │
│  - Create unified dataset for analysis                         │
│  - Export to parquet (optimized)                               │
│  - Generate webapp data JSONs                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  L4: ANALYTICS                                  │
│  - MRT impact analysis (heterogeneous, temporal)               │
│  - School impact analysis                                     │
│  - Spatial autocorrelation (Moran's I, LISA)                   │
│  - Market segmentation (clustering)                            │
│  - Price forecasting (Prophet, XGBoost)                        │
│  - Affordability metrics                                       │
│  - Cluster profiling                                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  L5: METRICS & DASHBOARD                        │
│  - Calculate leaderboard metrics                               │
│  - Generate trend data                                         │
│  - Create map hotspots                                         │
│  - Segment analysis data                                       │
│  - Export JSON for webapp                                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                 WEB APPLICATION                                 │
│  - Astro/React frontend                                        │
│  - Interactive Leaflet maps                                    │
│  - Plotly charts                                               │
│  - Markdown analytics reports                                  │
│  - Deployed to GitHub Pages                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Abstractions

### Pipeline Stages

**Location**: `scripts/core/stages/`

**Pattern**: Each stage is a module with clear input/output:

| Stage | Module | Input | Output |
|-------|--------|-------|--------|
| **L0** | `L0_collect.py` | API URLs | Raw CSV/parquet files |
| **L1** | `L1_process.py` | Transaction files | Geocoded parquet |
| **L2** | `L2_features.py` | Geocoded data | Feature-enriched parquet |
| **L2** | `L2_rental.py` | Geocoded data | Rental rates |
| **L3** | `L3_export.py` | Feature data | Unified dataset + webapp JSONs |
| **L4** | `L4_analysis.py` | Unified dataset | Analysis results (parquet + reports) |
| **L5** | `L5_metrics.py` | Analysis data | Dashboard metrics (JSON) |

**Helper Modules** (`scripts/core/stages/helpers/`):
- `collect_helpers.py` - API fetching utilities
- `feature_helpers.py` - Feature engineering utilities
- `geocoding_helpers.py` - Geocoding orchestration
- `spatial_helpers.py` - Spatial operations
- `export_helpers.py` - Data export utilities

### Core Services

**Location**: `scripts/core/`

| Service | Module | Responsibility |
|---------|--------|----------------|
| **Config** | `config.py` | Centralized configuration, path management |
| **Data Helpers** | `data_helpers.py` | Parquet I/O with metadata tracking |
| **Data Loader** | `data_loader.py` | High-level data loading utilities |
| **Geocoding** | `geocoding.py` | OneMap/Google geocoding with caching |
| **Cache** | `cache.py` | TTL-based caching for API calls |
| **MRT Distance** | `mrt_distance.py` | MRT station distance calculations |
| **MRT Mapping** | `mrt_line_mapping.py` | Station-to-line mapping |
| **School Features** | `school_features.py` | School tier assignment |
| **Metrics** | `metrics.py` | Statistical calculations |
| **Network Check** | `network_check.py` | API availability checking |
| **Logging** | `logging_config.py` | Structured logging setup |
| **Utils** | `utils.py` | General utilities |

---

## Data Flow Patterns

### 1. Pipeline Execution Flow

**Entry Point**: `scripts/run_pipeline.py`

```
run_pipeline.py
    ├── Setup logging
    ├── Check API availability
    ├── Run L0: Collect
    │   ├── Fetch HDB data
    │   ├── Fetch URA data (EC, condo)
    │   └── Save raw parquets
    ├── Run L1: Process
    │   ├── Load transaction files
    │   ├── Extract unique addresses
    │   ├── Geocode (parallel)
    │   └── Save geocoded parquets
    ├── Run L2: Features
    │   ├── Add MRT distances
    │   ├── Add CBD distance
    │   ├── Add planning areas
    │   ├── Add school features
    │   └── Add rental rates
    ├── Run L3: Export
    │   ├── Create unified dataset
    │   └── Export webapp JSONs
    ├── Run L4: Analysis (optional)
    │   ├── MRT impact models
    │   ├── School impact models
    │   ├── Spatial analysis
    │   └── Forecasting
    └── Run L5: Metrics (optional)
        ├── Leaderboard
        ├── Trends
        ├── Map hotspots
        └── Segments
```

### 2. Geocoding Flow

**Location**: `scripts/core/geocoding.py`, `scripts/core/stages/helpers/geocoding_helpers.py`

```
Address List
    │
    ▼
Check Cache ──► Hit ──► Return Cached
    │ Miss
    ▼
OneMap API Call
    │
    ├── Success ──► Cache Result ──► Return
    │
    └── Failure (401/403/timeout)
         │
         ▼
Refresh Token (if needed)
         │
         ▼
Retry OneMap
         │
         ├── Success ──► Cache & Return
         │
         └── Failure
              │
              ▼
Google Maps API (fallback)
              │
              └── Success ──► Return
              └── Failure ──► Log & Return None
```

### 3. Analytics Pipeline Flow

**Location**: `scripts/analytics/`

```
scripts/analytics/
    ├── analysis/          # Individual analysis scripts
    │   ├── mrt/          # MRT impact analyses
    │   ├── school/       # School impact analyses
    │   ├── spatial/      # Spatial statistics
    │   ├── market/       # Market analysis
    │   └── amenity/      # Amenity impact
    ├── pipelines/        # Orchestration scripts
    │   ├── calculate_*_pipeline.py
    │   └── forecast_*_pipeline.py
    └── segmentation/     # Clustering & segmentation
```

**Pattern**:
1. Load unified dataset from L3
2. Filter/subset data
3. Apply statistical model
4. Save results to parquet
5. Generate plots/reports

---

## Layered Architecture

### Presentation Layer

**Location**: `app/`, `backend/`

**Technologies**: Astro, React, TypeScript, Tailwind CSS

**Components**:
- Pages: `src/pages/` (dashboard, analytics)
- Components: `src/components/` (charts, maps)
- Layouts: `src/layouts/Layout.astro`

**Data Source**: JSON files in `app/public/data/`, `backend/public/data/`

### Application Layer

**Location**: `scripts/analytics/`, `scripts/core/stages/`

**Responsibilities**:
- Pipeline orchestration
- Data processing
- Analysis execution
- Metric calculation

### Data Access Layer

**Location**: `scripts/core/`

**Components**:
- `data_helpers.py` - Parquet I/O abstraction
- `data_loader.py` - High-level loading utilities
- `config.py` - Configuration management
- `cache.py` - Caching abstraction

### Infrastructure Layer

**Components**:
- File system (parquet storage)
- External APIs (OneMap, Google Maps, data.gov.sg)
- Logging system
- Error handling

---

## Key Design Patterns

### 1. Configuration as Code

**Single Source of Truth**: `scripts/core/config.py`

```python
class Config:
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    PARQUETS_DIR = DATA_DIR / "parquets"
    # ... all paths and settings
```

**Benefits**:
- Centralized path management
- Environment variable loading
- Validation on import

### 2. Metadata Tracking

**File**: `data/metadata.json`

**Purpose**: Track dataset lineage

```json
{
  "datasets": {
    "L1_hdb_transaction": {
      "path": "L1_hdb_transaction.parquet",
      "version": "2024-01-15",
      "rows": 500000,
      "created": "2024-01-15T10:30:00",
      "source": "data.gov.sg API"
    }
  }
}
```

**Updated by**: `data_helpers.py` on every save

### 3. Caching Strategy

**Implementation**: `scripts/core/cache.py`

**Pattern**: TTL cache with file-based persistence

```python
from cachetools import TTLCache
cache = TTLCache(maxsize=1000, ttl=24*3600)
```

**Used For**:
- API responses (OneMap, Google Maps)
- Expensive calculations
- Data.gov.sg dataset fetching

### 4. Error Handling Hierarchy

```
Exception
    ├── ValueError (invalid input, config issues)
    ├── FileNotFoundError (missing files)
    ├── RuntimeError (API failures, general errors)
    └── KeyError (missing data, with validation)
```

**Pattern**: Comprehensive error messages with context

### 5. Logging Strategy

**Configuration**: `scripts/core/logging_config.py`

**Pattern**: Named loggers per module

```python
logger = logging.getLogger(__name__)
logger.info("Processing {n} rows")
logger.error("Failed to load {file}: {error}")
```

**Output**: `data/logs/` with timestamps

### 6. Stage-Based Modularity

**Pattern**: Each pipeline stage is independent

**Benefits**:
- Run stages individually
- Skip completed stages
- Parallel execution (where safe)
- Easy testing

---

## Entry Points

### Main Pipeline

**Script**: `scripts/run_pipeline.py`

**Usage**:
```bash
uv run python scripts/run_pipeline.py
```

**Options**:
- `--stage L0,L1,L2` - Run specific stages
- `--skip-cache` - Disable caching
- `--verbose` - Extra logging

### Individual Stages

**Example**:
```bash
uv run python scripts/core/stages/L2_features.py
```

### Analytics Scripts

**Example**:
```bash
uv run python scripts/analytics/pipelines/forecast_prices_pipeline.py
```

### Webapp Data Generation

**Script**: `scripts/prepare_webapp_data.py`

**Usage**:
```bash
uv run python scripts/prepare_webapp_data.py
```

### Jupyter Notebooks

**Location**: `notebooks/`

**Usage**:
```bash
uv run jupyter notebook notebooks/L0_datagovsg.ipynb
```

---

## Data Abstractions

### Dataset Naming Convention

**Pattern**: `L{stage}_{entity}_{type}`

**Examples**:
- `L0_hdb_resale` - Raw HDB data
- `L1_hdb_transaction` - Processed HDB transactions
- `L2_hdb_with_features` - Feature-enriched HDB data
- `L3_unified_dataset` - Combined all property types

### Parquet Storage

**Directory**: `data/parquets/`

**Pattern**: One file per dataset

**Benefits**:
- Fast columnar reads
- Compression (snappy)
- Schema preservation

---

## Summary

**Architecture Type**: Layered ETL pipeline with modular stages
**Data Flow**: Batch processing with checkpointing
**Entry Points**: `run_pipeline.py`, individual stage scripts
**Abstractions**: Stages (L0-L5), Core Services, Helpers
**Key Patterns**: Config-as-code, metadata tracking, caching, comprehensive logging
**Separation of Concerns**: Data processing (Python) → Visualization (Astro/React)
