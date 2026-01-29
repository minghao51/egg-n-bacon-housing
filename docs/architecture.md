# Architecture - Egg-n-Bacon-Housing

**Status**: Phase 2 Complete

---

## Overview

Singapore housing data pipeline and ML analysis platform. Collects data from government APIs, processes it, and provides analysis tools via Streamlit apps and LangChain agents.

### Tech Stack

- **Language**: Python 3.11+
- **Package Manager**: uv
- **Data Storage**: Local parquet files with metadata
- **Notebooks**: Jupyter + Jupytext (paired .py files)
- **Apps**: Streamlit
- **ML/Agents**: LangChain + LangGraph + Google Gemini

---

## Directory Structure

```
egg-n-bacon-housing/
├── data/
│   ├── parquets/          # All parquet files (gitignored)
│   │   ├── raw_data/
│   │   ├── L1/
│   │   ├── L2/
│   │   └── L3/
│   └── metadata.json      # Dataset registry
├── notebooks/             # Jupyter notebooks + paired .py
├── core/                   # Source code
│   ├── config.py          # Centralized configuration
│   ├── data_helpers.py    # Parquet management
│   ├── data_loader.py     # Streamlit loaders with caching
│   ├── metrics.py         # Market metrics calculations
│   ├── pipeline/          # Pipeline modules (WIP)
│   └── agent/             # LangChain agents
├── apps/                  # Streamlit applications
├── scripts/               # Standalone scripts
└── tests/                 # Test suite
```

---

## Data Pipeline

### L0: Data Collection

Collects raw data from external sources:
- **data.gov.sg API**: HDB resale, rental indices, price indices
- **OneMap API**: Planning areas, household income
- **Wikipedia**: Shopping malls

**Output**: Raw parquet files (`raw_*`)

### L1: Data Processing

Cleans and transforms data:
- URA transaction data (condo, EC, HDB)
- Geocoding via OneMap API
- Amenity data enrichment

**Output**: Processed parquet files (`L1_*`)

### L2: Feature Engineering

Creates features for ML/analysis:
- Distance features (MRT, CBD, amenities)
- Aggregation features (counts within 1km, 2km)
- Rental yields

**Output**: Feature-rich parquet files (`L2_*`)

### L3: Precomputed Summary Tables

Optimized tables for Streamlit apps:

| Table | Description |
|-------|-------------|
| `market_summary.parquet` | Aggregated stats by property_type/period/tier |
| `planning_area_metrics.parquet` | Metrics by planning area |
| `rental_yield_top_combos.parquet` | Top rental yield combinations |

---

## Core Components

### Data Management (`core/data_helpers.py`)

```python
from core.data_helpers import load_parquet, save_parquet, list_datasets

df = load_parquet("L1_housing_hdb_transaction")
datasets = list_datasets()
```

### Configuration (`core/config.py`)

```python
from core.config import Config

data_dir = Config.DATA_DIR
api_key = Config.GOOGLE_API_KEY
Config.validate()
```

### Metrics (`core/metrics.py`)

```python
from core.metrics import calculate_roi_score, compute_monthly_metrics

roi = calculate_roi_score(feature_df, rental_yield_df)
metrics = compute_monthly_metrics('2020-01', '2025-12')
```

---

## Development

### Setup

```bash
uv sync
cp .env.example .env
uv run pytest
```

### Running Code

```bash
uv run python script.py
uv run pytest
uv run ruff check .
uv run jupyter notebook
```

### Notebooks

Edit `.py` files for version control, use `.ipynb` for visualization:

```bash
code notebooks/L0_datagovsg.py
uv run python notebooks/L0_datagovsg.py
cd notebooks && uv run jupytext --sync L0_datagovsg.ipynb
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Local parquet | Faster access, simpler workflow than DVC/S3 |
| Jupytext pairing | Git-friendly, full IDE support |
| uv package manager | 10-100x faster than pip/conda |
| Centralized config | Single source of truth |

---

## Related Documentation

- [usage-guide.md](usage-guide.md) - Getting started
- [data-reference.md](guides/data-reference.md) - Dataset catalog
