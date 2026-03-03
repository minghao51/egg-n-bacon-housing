# System Architecture

**Generated**: 2026-02-28

## Overview

This is a **stage-based ETL (Extract-Transform-Load) pipeline** for processing Singapore housing market data, combined with a static dashboard for visualization.

**Key Principle**: Python scripts process data and export JSON files; the frontend is a pure static application that reads these JSONs (no backend API).

---

## Core Architecture Pattern

### Stage-Based ETL Pipeline

The pipeline is organized into **6 sequential stages** (L0-L5), each with a specific purpose:

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│   L0    │ -> │   L1    │ -> │   L2    │ -> │   L3    │ -> │   L4    │ -> │   L5    │
│Collect  │    │Process  │    │Features │    │Unify    │    │Analyze  │    │Metrics  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
    ↓              ↓              ↓              ↓              ↓              ↓
Raw Data     Clean Data     Feature Rich    Unified       ML Models    Dashboard
from APIs    with Geo      with Spatial    Dataset       & Analytics   JSONs
```

**Benefits**:
- Clear separation of concerns
- Easy to debug (run specific stage)
- Parallel development possible
- Incremental updates

---

## Layer Architecture

### 1. Data Collection Layer (L0)

**Purpose**: Fetch raw data from external APIs

**Components**:
- `scripts/core/stages/L0_collect.py` - HDB/URA transaction data
- `scripts/core/stages/L0_macro.py` - SingStat macroeconomic data
- `scripts/data/download/` - Specialized download scripts

**Data Flow**:
```
data.gov.sg APIs -> L0_hdb_resale.parquet
                    L0_ura_rental.parquet
                    L0_price_indices.parquet
```

**Output**: Raw parquet files in `data/parquets/`

---

### 2. Data Processing Layer (L1)

**Purpose**: Clean, validate, and geocode data

**Components**:
- `scripts/core/stages/L1_process.py` - Transaction processing
- `scripts/core/geocoding.py` - Geocoding engine
- `scripts/utils/refresh_onemap_token.py` - Token management

**Data Flow**:
```
L0_hdb_resale.parquet -> Clean addresses -> Geocode (OneMap -> Google) -> L1_hdb_transaction.parquet
```

**Key Operations**:
- Address standardization
- OneMap geocoding (primary)
- Google Maps geocoding (fallback)
- Coordinate validation
- Data deduplication

---

### 3. Feature Engineering Layer (L2)

**Purpose**: Calculate spatial and market features

**Components**:
- `scripts/core/stages/L2_features.py` - Main feature pipeline
- `scripts/data/process/planning_area/` - Planning area assignments
- `scripts/data/process/amenities/parse_amenities_v2.py` - Amenity features

**Features Created**:
- **Distance Features**: CBD distance, MRT distance, school distance
- **Amenity Features**: Mall count, park area, hawker centers
- **Spatial Features**: H3 hexagon IDs, planning areas
- **Market Features**: Rental yields, price per sqft
- **School Features**: School tiers, distances to top schools

**Data Flow**:
```
L1_hdb_transaction.parquet -> Add features -> L2_hdb_with_features.parquet
```

---

### 4. Unified Dataset Layer (L3)

**Purpose**: Merge all property types into single dataset

**Components**:
- `scripts/create_l3_unified_dataset.py` - Main unified dataset creation
- `scripts/core/stages/L3_export.py` - Export for webapp

**Data Flow**:
```
L2_hdb_with_features.parquet ┐
L2_ura_with_features.parquet ├─> Merge -> L3_unified_dataset.parquet
L2_condo_with_features.parquet ┘                              ->
                                                      L3_dashboard_*.json
```

**Outputs**:
- Unified property dataset (all types)
- Dashboard JSON files (planning area metrics)
- Market summaries

---

### 5. Analytics Layer (L4)

**Purpose**: Run ML models and analysis

**Components**:
- `scripts/analytics/models/` - Price prediction, ARIMAX
- `scripts/analytics/analysis/` - Specialized analysis scripts
- `scripts/analytics/price_appreciation_modeling/` - Appreciation models

**Analysis Types**:
- **Price Prediction**: XGBoost models for property pricing
- **Market Segmentation**: Clustering property types
- **Causal Inference**: Impact of MRT/school openings
- **Spatial Analysis**: Hotspots, autocorrelation
- **Time Series**: ARIMAX, forecasting

**Data Flow**:
```
L3_unified_dataset.parquet -> Analysis Models -> analysis_*.parquet
                                                        ->
                                                L4_dashboard_*.json
```

---

### 6. Metrics Layer (L5)

**Purpose**: Calculate dashboard metrics

**Components**:
- `scripts/prepare_webapp_data.py` - Main export script
- `scripts/analytics/pipelines/` - Metric calculation pipelines

**Metrics Calculated**:
- Planning area summaries
- Price appreciation trends
- Rental yield distributions
- Affordability indices
- Growth metrics

**Data Flow**:
```
L3_unified_dataset.parquet + L4 analysis -> Metrics -> app/public/data/*.json
```

---

## Frontend/Backend Separation

### Architecture Pattern

**No Backend API**: The frontend is a **pure static application** that reads pre-generated JSON files.

```
┌─────────────────────────────┐
│   Python Scripts (scripts/)  │
│   - Process data             │
│   - Run models               │
│   - Export JSONs             │
└──────────┬──────────────────┘
           │ JSON files
           ↓
┌─────────────────────────────┐
│   app/public/data/          │  ← Static JSON files
│   - metrics.json            │
│   - planning-areas.json     │
│   - trends.json             │
└──────────┬──────────────────┘
           │ Read at build time
           ↓
┌─────────────────────────────┐
│   Astro/React Dashboard     │
│   - Static site generation  │
│   - Client-side rendering   │
│   - No API calls            │
└─────────────────────────────┘
```

**Benefits**:
- **Simplicity**: No backend server to manage
- **Performance**: Static files are fast
- **Hosting**: Can deploy to GitHub Pages
- **Cost**: Free hosting

**Trade-offs**:
- Data must be pre-generated
- No real-time queries
- Full rebuild for data updates

---

## Core Abstractions

### 1. Configuration Management

**File**: `scripts/core/config.py`

**Pattern**: Centralized configuration with environment-based secrets

```python
from scripts.core.config import Config

# Access paths
data_dir = Config.DATA_DIR
parquets_dir = Config.PARQUETS_DIR

# Access API keys
api_key = Config.GOOGLE_API_KEY

# Validate configuration
Config.validate()
```

**Why**:
- Single source of truth
- Environment-aware (dev/prod)
- Validation on startup

---

### 2. Data I/O Abstraction

**File**: `scripts/core/data_helpers.py`

**Pattern**: Metadata-based parquet loading with error handling

```python
from scripts.core.data_helpers import load_parquet, save_parquet

# Load (uses metadata.json)
df = load_parquet("L2_hdb_with_features")

# Save (updates metadata.json)
save_parquet(
    df,
    dataset_name="L3_unified_dataset",
    source="L2_hdb_with_features + L2_ura_with_features"
)
```

**Benefits**:
- Don't need to remember file paths
- Automatic metadata tracking
- Consistent error handling
- Version awareness

---

### 3. Geocoding Abstraction

**File**: `scripts/core/geocoding.py`

**Pattern**: Fallback chain with automatic token management

```python
from scripts.core.geocoding import geocode_address

# OneMap -> Google -> None
coordinates = geocode_address("123 Main Street, Singapore")
```

**Features**:
- Automatic token refresh (OneMap)
- Fallback to Google Maps
- Response caching
- Error logging

---

### 4. Pipeline Stage Abstraction

**Pattern**: Each stage is a standalone script with CLI interface

```bash
# Run specific stage
uv run python scripts/run_pipeline.py --stage L1

# Run all stages
uv run python scripts/run_pipeline.py --all

# Run with verbose logging
uv run python scripts/run_pipeline.py --all --verbose
```

**Benefits**:
- Modular development
- Easy debugging
- Incremental updates
- Parallel execution possible

---

## Data Flow Patterns

### 1. ETL Flow

```
External APIs → L0 (raw) → L1 (clean) → L2 (features) → L3 (unified) → L4 (models) → L5 (metrics)
```

**Characteristics**:
- **Sequential**: Each stage depends on previous
- **Idempotent**: Can re-run stages safely
- **Checkpointed**: Parquet files save progress
- **Observable**: Logging at each step

### 2. Export Flow

```
L3/L4 Data → Export Scripts → JSON Files → Dashboard Build → Static Site
```

**Characteristics**:
- **Batch**: All data exported at once
- **Atomic**: Either full export or fail
- **Versioned**: JSONs include timestamps
- **Optimized**: Minified for frontend

### 3. Development Flow

```
Notebooks (exploration) → Scripts (production) → Pipeline (scheduled)
```

**Characteristics**:
- **Iterative**: Notebooks for prototyping
- **Reusable**: Scripts for production
- **Automated**: Pipeline for updates

---

## Design Patterns

### 1. Stage Pattern

**Definition**: Each pipeline stage is a self-contained unit

**Implementation**:
- Input: Parquet file from previous stage
- Output: Parquet file for next stage
- Error handling: Fail fast, log errors
- Validation: Check row counts, schema

**Example**:
```python
# scripts/core/stages/L1_process.py
def run_L1_processing():
    # Load L0 data
    df = load_parquet("L0_hdb_resale")

    # Process
    df = clean_addresses(df)
    df = geocode_addresses(df)

    # Save L1 data
    save_parquet(df, "L1_hdb_transaction", source="L0_hdb_resale")
```

### 2. Metadata Pattern

**Definition**: All datasets tracked in central metadata file

**Implementation**: `data/metadata.json`

**Benefits**:
- Data lineage
- Version tracking
- Easy discovery
- Validation

### 3. Configuration-as-Code Pattern

**Definition**: All settings in code, not hardcode

**Implementation**: `scripts/core/config.py`

**Benefits**:
- Environment-aware
- Type-safe
- Documented
- Testable

### 4. Export-First Pattern

**Definition**: Frontend consumes exports, not live data

**Implementation**: JSON files in `app/public/data/`

**Benefits**:
- Simple deployment
- Fast page loads
- No backend complexity
- Version control for data

---

## Module Organization

### Core Modules (`scripts/core/`)

| Module | Purpose |
|--------|---------|
| `config.py` | Centralized configuration |
| `data_helpers.py` | Parquet I/O with metadata |
| `geocoding.py` | Geocoding engine |
| `stages/` | Pipeline stages (L0-L5) |

### Analytics Modules (`scripts/analytics/`)

| Subdirectory | Purpose |
|--------------|---------|
| `models/` | ML models (ARIMAX, prediction) |
| `analysis/` | Specialized analysis scripts |
| `pipelines/` | Metric calculation pipelines |
| `price_appreciation_modeling/` | Appreciation models |
| `segmentation/` | Market segmentation |
| `viz/` | Visualization generation |

### Data Modules (`scripts/data/`)

| Subdirectory | Purpose |
|--------------|---------|
| `download/` | Data fetching scripts |
| `process/` | Data processing utilities |
| `create_l3_unified_dataset.py` | Unified dataset creation |

---

## Entry Points

### 1. Main Pipeline

**File**: `scripts/run_pipeline.py`

**Usage**:
```bash
# Run all stages
uv run python scripts/run_pipeline.py --all

# Run specific stage
uv run python scripts/run_pipeline.py --stage L2

# Dry run
uv run python scripts/run_pipeline.py --all --dry-run
```

**Stages**: L0, L1, L2, L3, L4, L5

### 2. Webapp Data Export

**File**: `scripts/prepare_webapp_data.py`

**Usage**:
```bash
uv run python scripts/prepare_webapp_data.py
```

**Output**: `app/public/data/*.json`

### 3. Dashboard (Frontend)

**Directory**: `app/`

**Usage**:
```bash
cd app
npm install
npm run dev  # Development server
npm run build  # Production build
```

**Framework**: Astro + React

---

## Error Handling Strategy

### Exception Hierarchy

```python
try:
    df = load_parquet(dataset_name)
except ValueError as e:
    # Invalid input, configuration issues
    logger.error(f"Configuration error: {e}")
    raise
except FileNotFoundError as e:
    # Missing files
    logger.error(f"File not found: {e}")
    raise
except RuntimeError as e:
    # API failures, general errors
    logger.error(f"Runtime error: {e}")
    raise
```

### Logging Strategy

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Processing {len(df)} rows")
logger.warning(f"Missing coordinates for {count} addresses")
logger.error(f"Failed to geocode: {address}")
```

**Output**: `data/logs/` with timestamps

---

## Performance Considerations

### Current State
- **Sequential**: Each stage runs one at a time
- **In-Memory**: Full datasets loaded into RAM
- **API-Bound**: Geocoding is the bottleneck (1.2s delay)

### Optimization Opportunities
- **Parallel Processing**: Use multiprocessing for geocoding
- **Chunking**: Process large files in chunks
- **Caching**: Cache API responses (already implemented)
- **Incremental Updates**: Only process new data

---

## Testing Architecture

### Test Types

1. **Unit Tests** (`tests/test_core/`)
   - Fast, isolated
   - Mock external dependencies

2. **Integration Tests** (`tests/test_integration/`)
   - Component interaction
   - Real data files

3. **E2E Tests** (`app/tests/e2e/`)
   - Frontend functionality
   - Playwright framework

### Test Structure

```
tests/
├── test_core/           # Unit tests for core modules
├── test_integration/    # Integration tests
└── conftest.py          # Shared fixtures

app/tests/e2e/           # E2E tests
├── home.spec.ts
├── dashboard.spec.ts
└── analytics.spec.ts
```

---

## Deployment Architecture

### Frontend Deployment

```
GitHub Actions (CI/CD)
    ↓
Build Astro Site
    ↓
Deploy to GitHub Pages
    ↓
https://user.github.io/repo/
```

**Workflow**: `.github/workflows/deploy.yml`

### Data Updates

```
Manual trigger or scheduled cron
    ↓
Run Python pipeline
    ↓
Generate JSON files
    ↓
Commit JSONs to repo
    ↓
Trigger rebuild
```

---

## Summary

**Architecture Type**: Stage-based ETL pipeline with static frontend

**Key Patterns**:
- Stage-based ETL (L0-L5)
- Metadata-driven data I/O
- Export-first (no backend API)
- Configuration-as-code
- Fallback chain (geocoding)

**Entry Points**:
- `scripts/run_pipeline.py` - Main pipeline
- `scripts/prepare_webapp_data.py` - Export
- `app/` - Frontend dashboard

**Abstractions**:
- `Config` - Configuration
- `load_parquet/save_parquet` - Data I/O
- `geocode_address` - Geocoding
