# Egg-n-Bacon-Housing: Directory Structure

## Overview

This document outlines the complete directory structure of the egg-n-bacon-housing project, including key locations, naming conventions, and file purposes.

---

## Root Directory

```
egg-n-bacon-housing/
├── .github/                    # GitHub-specific files
│   └── workflows/             # CI/CD workflows
│       ├── deploy-app.yml     # Deploy frontend to GitHub Pages
│       └── test.yml           # Run tests on push
│
├── .planning/                 # Planning and documentation
│   └── codebase/             # This codebase map
│
├── app/                      # Frontend web application (Astro)
│   ├── public/               # Static assets
│   │   └── data/            # Dashboard data (JSON)
│   ├── src/                  # Source code
│   │   ├── components/      # React components
│   │   ├── layouts/         # Astro layouts
│   │   └── pages/           # Route pages
│   ├── package.json         # Frontend dependencies
│   └── astro.config.mjs     # Astro configuration
│
├── backend/                  # Analytics web application
│   ├── public/              # Static assets
│   │   └── data/           # Analytics data (JSON)
│   ├── src/                 # Source code (minimal)
│   └── dist/                # Build output
│
├── data/                     # All data storage
│   ├── manual/              # Manually uploaded data
│   │   └── csv/            # CSV input files
│   ├── parquets/            # Processed parquet datasets
│   ├── logs/                # Pipeline and API logs
│   └── metadata.json        # Dataset lineage tracking
│
├── docs/                     # Documentation
│   └── analytics/           # Analysis findings
│       └── findings.md      # Executive summary
│
├── notebooks/               # Jupyter notebooks (paired with .py)
│   ├── L0_*.py             # Data collection notebooks
│   ├── L1_*.py             # Data processing notebooks
│   └── exploration/        # Exploratory analysis
│
├── scripts/                 # Main Python code
│   ├── analytics/          # Analysis modules
│   ├── core/               # Core services
│   ├── data/               # Data download/processing
│   ├── dashboard/          # Dashboard utilities
│   ├── utils/              # Utility scripts
│   └── run_pipeline.py     # Main pipeline entry point
│
├── tests/                   # Test suite
│   └── core/               # Core module tests
│
├── .env.example             # Environment variable template
├── .gitignore              # Git ignore rules
├── CLAUDE.md               # Claude AI instructions
├── jupytext.toml           # Jupytext configuration
├── pyproject.toml          # Python project configuration
├── README.md               # Project overview
└── package.json            # Root package.json (math rendering)
```

---

## Key Directories

### `/scripts` - Main Python Code

**Purpose**: All data processing, analysis, and pipeline code

**Subdirectories**:

```
scripts/
├── analytics/               # Analysis modules
│   ├── analysis/           # Individual analysis scripts
│   │   ├── amenity/        # Amenity impact analysis
│   │   ├── appreciation/   # Price appreciation analysis
│   │   ├── market/         # Market dynamics analysis
│   │   ├── mrt/            # MRT impact analysis
│   │   ├── policy/         # Policy impact analysis
│   │   ├── school/         # School impact analysis
│   │   └── spatial/        # Spatial analysis (H3, autocorrelation)
│   ├── pipelines/          # Orchestration scripts
│   │   ├── calculate_*_pipeline.py
│   │   └── forecast_*_pipeline.py
│   └── segmentation/       # Clustering & segmentation
│
├── core/                   # Core services (reusable)
│   ├── stages/             # Pipeline stages (L0-L5)
│   │   ├── helpers/        # Stage helper modules
│   │   ├── L0_collect.py   # Data collection
│   │   ├── L1_process.py   # Data processing & geocoding
│   │   ├── L2_features.py  # Feature engineering
│   │   ├── L2_rental.py    # Rental data
│   │   ├── L3_export.py    # Data export
│   │   ├── L4_analysis.py  # Analytics orchestration
│   │   ├── L5_metrics.py   # Dashboard metrics
│   │   └── webapp_data_preparation.py
│   ├── cache.py            # Caching utilities
│   ├── config.py           # Centralized configuration
│   ├── data_helpers.py     # Parquet I/O with metadata
│   ├── data_loader.py      # High-level data loading
│   ├── geocoding.py        # OneMap/Google geocoding
│   ├── logging_config.py   # Logging setup
│   ├── metrics.py          # Statistical calculations
│   ├── mrt_distance.py     # MRT distance calculations
│   ├── mrt_line_mapping.py # MRT line mapping
│   ├── network_check.py    # API availability checking
│   ├── school_features.py  # School tier assignment
│   └── utils.py            # General utilities
│
├── data/                   # Data download/processing scripts
│   ├── download/           # Download external data
│   │   ├── download_datagov_datasets.py
│   │   ├── download_hdb_rental_data.py
│   │   ├── download_ura_rental_index.py
│   │   └── refresh_external_data.py
│   └── process/            # Process specific data types
│       ├── amenities/      # Process amenities data
│       ├── geocode/        # Geocoding utilities
│       └── planning_area/  # Planning area mapping
│
├── utils/                  # Utility scripts
│   ├── check_geocoding_progress.py
│   ├── detect_anomalies.py
│   ├── refresh_onemap_token.py
│   ├── town_leaderboard.py
│   ├── validate_ura_data.py
│   └── verify_psf_conversion.py
│
├── dashboard/              # Dashboard-specific utilities
│   └── create_l3_unified_dataset.py
│
├── prepare_webapp_data.py  # Generate webapp JSON files
├── run_pipeline.py         # Main pipeline entry point
└── verify_imports.py       # Verify Python imports
```

### `/data` - Data Storage

**Purpose**: All data files, processed and raw

```
data/
├── manual/                 # Manually uploaded data
│   └── csv/               # CSV input files
│       ├── datagovsg/     # data.gov.sg downloads
│       └── crosswalks/    # Mapping files (planning areas, etc.)
│
├── parquets/              # Processed parquet datasets
│   ├── L0_*.parquet      # Raw data
│   ├── L1_*.parquet      # Geocoded data
│   ├── L2_*.parquet      # Feature-enriched data
│   ├── L3_*.parquet      # Unified dataset
│   └── analysis_*.parquet # Analysis results
│
├── logs/                  # Pipeline and API logs
│   ├── geocoding_*.log   # Geocoding batch logs
│   └── pipeline_*.log    # Pipeline execution logs
│
└── metadata.json          # Dataset lineage tracking
```

**Naming Conventions**:
- `L{stage}_{entity}_{type}.parquet`
  - Example: `L2_hdb_with_features.parquet`
- `analysis_{topic}_{detail}.parquet`
  - Example: `analysis_mrt_heterogeneous_effects.parquet`

### `/app` - Frontend Web Application

**Purpose**: Interactive dashboard built with Astro

```
app/
├── public/                # Static assets (served as-is)
│   └── data/             # Dashboard data (JSON)
│       ├── dashboard_overview.json
│       ├── dashboard_trends.json
│       ├── dashboard_segments.json
│       ├── dashboard_leaderboard.json
│       ├── map_metrics.json
│       └── hotspots.json
│
├── src/                   # Source code
│   ├── components/        # React components
│   │   ├── charts/       # Chart components
│   │   │   ├── ChartRenderer.tsx
│   │   │   ├── TimeSeriesChart.tsx
│   │   │   ├── ComparisonChart.tsx
│   │   │   ├── StatisticalPlot.tsx
│   │   │   ├── InteractiveTable.tsx
│   │   │   └── InlineChartRenderer.tsx
│   │   ├── dashboard/   # Dashboard-specific components
│   │   │   ├── MarketOverviewDashboard.tsx
│   │   │   ├── PriceMap.tsx
│   │   │   ├── TrendsDashboard.tsx
│   │   │   ├── TownLeaderboard.tsx
│   │   │   └── SegmentsAnalysis.tsx
│   │   ├── DarkModeToggle.tsx
│   │   ├── MarkdownContent.tsx
│   │   ├── MathFormula.tsx
│   │   ├── PlotlyEmbed.astro
│   │   ├── Sidebar.astro
│   │   └── TableOfContents.astro
│   │
│   ├── layouts/          # Astro layouts
│   │   └── Layout.astro
│   │
│   └── pages/            # Route pages
│       ├── index.astro              # Home page
│       ├── dashboard/               # Dashboard routes
│       │   ├── index.astro          # Overview
│       │   ├── trends.astro         # Trends page
│       │   ├── segments.astro       # Segments page
│       │   ├── leaderboard.astro    # Leaderboard page
│       │   └── map.astro            # Map page
│       └── analytics/               # Analytics routes
│           ├── index.astro          # Analytics index
│           └── [slug].astro         # Individual analytics pages
│
├── package.json          # Frontend dependencies
├── tsconfig.json         # TypeScript configuration
└── astro.config.mjs      # Astro configuration
```

### `/backend` - Analytics Web Application

**Purpose**: Secondary webapp for detailed analytics

```
backend/
├── public/               # Static assets
│   └── data/            # Analytics data (JSON)
│       └── hotspots.json
│
├── src/                  # Source code (minimal)
│   └── components/      # Shared components
│
└── dist/                 # Build output (deployed)
```

### `/tests` - Test Suite

**Purpose**: Comprehensive testing

```
tests/
├── conftest.py           # Shared fixtures
│
├── test_pipeline.py      # Pipeline stage tests
├── test_geocoding.py     # Geocoding tests
├── test_mrt_integration.py  # MRT integration tests
├── test_mrt_enhanced.py  # Enhanced MRT tests
├── test_pipeline_setup.py # Pipeline setup tests
│
└── core/                 # Core module tests
    ├── test_config.py       # Configuration tests
    ├── test_cache.py        # Cache tests
    └── test_data_helpers.py # Data helper tests
```

### `/notebooks` - Jupyter Notebooks

**Purpose**: Exploratory analysis and documentation

**Note**: All notebooks have paired `.py` files via Jupytext

```
notebooks/
├── L0_datagovsg.py              # Data collection from data.gov.sg
├── L0_onemap.py                 # OneMap API exploration
├── L0_wiki.py                   # Wikipedia data scraping
├── L1_ura_transactions_processing.py  # URA data processing
├── L1_utilities_processing.py   # Utilities data processing
├── L2_sales_facilities.py       # Sales facilities analysis
├── 20260123_hdb_eda_investment_analysis.py  # HDB investment analysis
├── visualize_feature_importance.py  # Feature importance visualization
│
└── exploration/                 # Exploratory notebooks
    ├── gemini-simple-call.py
    ├── pandas_agent.py
    └── ZZ_spark-dataframe-agent-langchain.py
```

---

## Naming Conventions

### Python Files

**Pattern**: `snake_case.py`

**Examples**:
- `data_helpers.py` - Module
- `test_geocoding.py` - Test file
- `run_pipeline.py` - Executable script

**Stage Files**: `L{number}_{description}.py`
- `L0_collect.py` - Stage 0: Collection
- `L1_process.py` - Stage 1: Processing

### TypeScript/React Files

**Components**: `PascalCase.tsx` or `.astro`
- `PriceMap.tsx`
- `Layout.astro`

**Utilities**: `snake_case.ts`
- (none currently, all in components)

### Data Files

**Parquet**: `{stage}_{entity}_{type}.parquet`
- `L2_hdb_with_features.parquet`
- `analysis_mrt_heterogeneous_effects.parquet`

**JSON**: `{description}.json`
- `dashboard_overview.json`
- `map_metrics.json`

**CSV**: `{source}_{description}.csv`
- `datagovsg_resale_flat_prices.csv`

### Test Files

**Pattern**: `test_{module}.py`

**Examples**:
- `test_geocoding.py`
- `test_config.py`
- `test_data_helpers.py`

---

## Key Locations

| Purpose | Location |
|---------|----------|
| **Main Pipeline** | `scripts/run_pipeline.py` |
| **Configuration** | `scripts/core/config.py` |
| **Data I/O** | `scripts/core/data_helpers.py` |
| **Geocoding** | `scripts/core/geocoding.py` |
| **Webapp Data** | `scripts/prepare_webapp_data.py` |
| **Test Suite** | `tests/` |
| **Notebooks** | `notebooks/` |
| **Parquet Storage** | `data/parquets/` |
| **Manual Data** | `data/manual/csv/` |
| **Logs** | `data/logs/` |
| **Dashboard JSONs** | `app/public/data/` |
| **Analytics JSONs** | `backend/public/data/` |
| **Metadata** | `data/metadata.json` |
| **Environment Variables** | `.env` (from `.env.example`) |

---

## Summary

**Root Structure**: 9 main directories
- `/scripts` - Python pipeline & analytics (80%+ of code)
- `/app` - Frontend dashboard (Astro/React)
- `/backend` - Analytics webapp
- `/data` - All data storage
- `/tests` - Comprehensive test suite
- `/notebooks` - Jupyter notebooks with .py pairing
- `/docs` - Analysis findings
- `/.github` - CI/CD workflows
- `/.planning` - Project documentation

**Key Patterns**:
- Stage-based pipeline (L0-L5)
- Modular core services
- Separated frontend/backend
- Data lineage via metadata.json
- Test files mirror structure of `/scripts`
