# Codebase Structure

**Analysis Date:** 2026-02-02

## Directory Layout

```
[project-root]/
├── apps/ # Streamlit dashboard applications
│   ├── 1_market_overview.py # Market statistics dashboard
│   ├── 2_price_map.py # Interactive price mapping
│   ├── 3_trends_analytics.py # Time-series analysis
│   ├── dashboard.py # Main dashboard entry point
│   └── market_insights/ # Advanced analytics dashboards
├── scripts/ # Data processing pipeline
│   ├── core/ # Core pipeline modules
│   │   ├── stages/ # Pipeline stage implementations
│   │   │   ├── L0_collect.py # Data collection
│   │   │   ├── L1_process.py # Data processing
│   │   │   ├── L2_features.py # Feature engineering
│   │   │   ├── L2_rental.py # Rental features
│   │   │   ├── L3_export.py # Export pipeline
│   │   │   ├── L4_analysis.py # Analysis pipeline
│   │   │   ├── L5_metrics.py # Metrics calculation
│   │   │   ├── webapp_data_preparation.py # Webapp data
│   │   │   └── spatial_h3.py # Spatial utilities
│   │   │   └── helpers/ # Stage-specific helpers
│   │   ├── cache.py # Caching utilities
│   │   ├── config.py # Configuration management
│   │   ├── data_helpers.py # Data utilities
│   │   ├── data_loader.py # Data loading abstraction
│   │   ├── geocoding.py # Geocoding services
│   │   ├── metrics.py # Metrics calculations
│   │   └── ui_components.py # Dashboard UI components
│   ├── analytics/ # Analytics and ML scripts
│   │   ├── analysis/ # Specific analysis modules
│   │   ├── pipelines/ # Analytics pipelines
│   │   └── segmentation/ # Market segmentation
│   ├── dashboard/ # Dashboard-specific scripts
│   ├── data/ # Data processing scripts
│   │   ├── download/ # Data download scripts
│   │   └── process/ # Data processing scripts
│   └── utils/ # Utility scripts
├── notebooks/ # Jupyter notebooks with paired Python files
│   ├── L0_*.py # Level 0 notebooks
│   ├── L1_*.py # Level 1 notebooks
│   ├── L2_*.py # Level 2 notebooks
│   ├── exploration/ # Experimental notebooks
│   └── *.ipynb # Interactive notebooks
├── tests/ # Test suite
├── data/ # Data storage
│   ├── pipeline/ # Pipeline outputs (L0-L5)
│   ├── manual/ # Manual data uploads
│   ├── analysis/ # Analysis outputs
│   ├── cache/ # API response cache
│   ├── archive/ # Archived data
│   └── metadata.json # Data metadata
├── .planning/ # Planning documentation
│   └── codebase/ # Architecture docs
└── core/ # Legacy core directory (deprecated)
```

## Directory Purposes

**apps/:**
- Purpose: Interactive dashboard applications built with Streamlit
- Contains: Streamlit applications, UI components, data visualization
- Key files: `dashboard.py`, `1_market_overview.py`, `2_price_map.py`, `3_trends_analytics.py`

**scripts/core/:**
- Purpose: Core data processing pipeline logic
- Contains: Pipeline stages, configuration, utilities, caching
- Key files: `config.py`, `run_pipeline.py`, stage implementations

**scripts/analytics/:**
- Purpose: Advanced analytics and machine learning workflows
- Contains: Market analysis, feature importance, segmentation algorithms
- Key files: Analysis pipelines, segmentation scripts

**scripts/data/:**
- Purpose: Data collection and preprocessing utilities
- Contains: API download scripts, data cleaning utilities
- Key files: Download scripts, processing utilities

**notebooks/:**
- Purpose: Interactive data exploration and analysis
- Contains: Jupyter notebooks with paired Python files via Jupytext
- Key files: `L0_datagovsg.py`, `L1_ura_transactions_processing.py`

**tests/:**
- Purpose: Comprehensive test suite for validation
- Contains: Unit tests, integration tests, pipeline tests
- Key files: `test_pipeline.py`, `test_geocoding.py`

**data/:**
- Purpose: Data storage and outputs
- Contains: Pipeline outputs, cached data, manual uploads
- Key files: `metadata.json`, pipeline parquet files

## Key File Locations

**Entry Points:**
- `scripts/run_pipeline.py`: Main pipeline orchestration
- `apps/dashboard.py`: Main dashboard application
- `notebooks/L0_datagovsg.py`: Data collection notebook

**Configuration:**
- `scripts/core/config.py`: Centralized configuration management
- `.env`: Environment variables and API keys

**Core Logic:**
- `scripts/core/stages/L3_export.py`: Main export pipeline
- `scripts/core/data_loader.py`: Data loading abstraction
- `scripts/core/geocoding.py`: Geocoding services

**Testing:**
- `tests/test_pipeline.py`: Pipeline integration tests
- `tests/test_config.py`: Configuration tests

## Naming Conventions

**Files:**
- `L[0-5]_*.py`: Pipeline stage files (L0 to L5)
- `test_*.py`: Test files
- `*_pipeline.py`: Pipeline orchestration files
- `*_helpers.py`: Utility modules for specific stages

**Directories:**
- `L[0-5]/`: Pipeline stage output directories
- `*/helpers/`: Helper modules for specific stages
- `*/analysis/`: Analytics-specific modules
- `*/pipelines/`: Analytics pipeline implementations

## Where to Add New Code

**New Feature:**
- Primary code: `scripts/core/stages/L2_features.py`
- Tests: `tests/test_features.py`
- Configuration: `scripts/core/config.py`

**New Component/Module:**
- Implementation: `scripts/core/[module_name].py`
- Tests: `tests/test_[module_name].py`

**Utilities:**
- Shared helpers: `scripts/core/stages/helpers/[helper_name].py`
- Data utilities: `scripts/core/data_helpers.py`

## Special Directories

**data/pipeline/:**
- Purpose: Pipeline outputs for each stage (L0-L5)
- Generated: Yes (automatically by pipeline)
- Committed: Yes (version control for data artifacts)

**data/cache/:**
- Purpose: API response caching for performance
- Generated: Yes (automatically by caching system)
- Committed: No (excluded by .gitignore)

**notebooks/exploration/:**
- Purpose: Experimental and exploratory analysis
- Generated: Yes (manual creation)
- Committed: Yes (for knowledge sharing)

**tests/:**
- Purpose: Comprehensive test suite
- Generated: Yes (manual and automated test creation)
- Committed: Yes (quality assurance)

---

*Structure analysis: 2026-02-02*
