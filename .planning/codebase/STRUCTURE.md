# Directory Structure

**Generated**: 2026-02-28

## Project Root Layout

```
egg-n-bacon-housing/
├── app/                          # Astro/React dashboard (frontend)
├── data/                         # Data storage
├── docs/                         # Documentation
├── notebooks/                    # Jupyter notebooks (exploration)
├── scripts/                      # Python scripts (main logic)
├── tests/                        # Python tests
├── .planning/                    # Planning and codebase docs
├── .venv/                        # Python virtual environment
├── pyproject.toml                # Python project config
├── package.json                  # Root package.json
├── .env.example                  # Environment variables template
├── CLAUDE.md                     # Project instructions
└── README.md                     # Project overview
```

---

## Top-Level Directories

### `/app` - Frontend Dashboard

**Purpose**: Astro + React dashboard for data visualization

**Structure**:
```
app/
├── public/
│   └── data/                    # JSON files for dashboard (generated)
│       ├── metrics.json
│       ├── planning-areas.json
│       └── trends.json
├── src/
│   ├── components/              # React components
│   ├── layouts/                 # Astro layouts
│   ├── pages/                   # Route pages
│   └── styles/                  # Global styles
├── tests/
│   └── e2e/                     # Playwright E2E tests
│       ├── home.spec.ts
│       ├── dashboard.spec.ts
│       └── analytics.spec.ts
├── astro.config.mjs             # Astro configuration
├── package.json                 # Node dependencies
├── playwright.config.ts         # Playwright test config
└── tsconfig.json                # TypeScript config
```

**Key Files**:
- `src/pages/index.astro` - Home page
- `src/pages/dashboard/*.astro` - Dashboard pages
- `src/components/*.tsx` - React components

---

### `/data` - Data Storage

**Purpose**: Store raw data, processed parquet files, logs, and exports

**Structure**:
```
data/
├── raw/                         # Raw downloaded data
├── parquets/                    # Processed parquet files by stage
│   ├── L0_hdb_resale.parquet
│   ├── L1_hdb_transaction.parquet
│   ├── L2_hdb_with_features.parquet
│   ├── L3_unified_dataset.parquet
│   └── ...
├── pipeline/                    # Pipeline-specific data
├── analytics/                   # Analysis outputs
├── exports/                     # Exported files
├── logs/                        # Application logs
├── cache/                       # API response cache
├── metadata.json                # Dataset registry
└── .gitkeep                     # Preserve directory structure
```

**Key Files**:
- `metadata.json` - Central registry of all datasets
- `parquets/*.parquet` - Stage-based data files
- `logs/*.log` - Timestamped log files

---

### `/scripts` - Main Python Codebase

**Purpose**: Core data processing, analysis, and pipeline scripts

**Structure**:
```
scripts/
├── core/                        # Core abstractions and utilities
│   ├── config.py                # Centralized configuration
│   ├── data_helpers.py          # Parquet I/O with metadata
│   ├── geocoding.py             # Geocoding engine
│   ├── mrt_line_mapping.py      # MRT line/station data
│   ├── school_features.py       # School tier assignments
│   └── stages/                  # Pipeline stages (L0-L5)
│       ├── L0_collect.py        # Data collection
│       ├── L0_macro.py          # Macro data collection
│       ├── L1_process.py        # Data processing
│       ├── L2_features.py       # Feature engineering
│       ├── L3_export.py         # Export for webapp
│       └── ...
│
├── analytics/                   # Analytics and modeling
│   ├── models/                  # ML models
│   │   ├── area_arimax.py       # ARIMAX time series
│   │   └── regional_var.py      # Regional variance models
│   ├── analysis/                # Analysis scripts
│   │   ├── market/              # Market analysis
│   │   ├── mrt/                 # MRT impact analysis
│   │   ├── school/              # School impact analysis
│   │   ├── spatial/             # Spatial analysis
│   │   ├── causal/              # Causal inference
│   │   ├── appreciation/        # Appreciation analysis
│   │   ├── amenity/             # Amenity analysis
│   │   └── policy/              # Policy impact analysis
│   ├── pipelines/               # Analytics pipelines
│   ├── price_appreciation_modeling/  # Appreciation models
│   ├── segmentation/            # Market segmentation
│   ├── viz/                     # Visualization scripts
│   └── run_backtesting.py       # Backtesting framework
│
├── data/                        # Data processing scripts
│   ├── download/                # Data fetching
│   │   ├── download_hdb_rental_data.py
│   │   ├── download_ura_rental_index.py
│   │   └── refresh_external_data.py
│   ├── process/                 # Data processing utilities
│   │   ├── amenities/           # Amenity features
│   │   ├── geocode/             # Geocoding utilities
│   │   └── planning_area/       # Planning area assignments
│   ├── fetch_macro_data.py      # Macro data fetching
│   └── create_l3_unified_dataset.py  # Unified dataset
│
├── utils/                       # Utility scripts
│   ├── refresh_onemap_token.py  # Token management
│   ├── check_geocoding_progress.py
│   ├── detect_anomalies.py
│   └── town_leaderboard.py
│
├── webapp/                      # Webapp-specific scripts
│   ├── prepare_webapp_data.py   # Main export script
│   ├── prepare_analytics_json.py
│   └── transform_spatial_hotspots.py
│
├── tools/                       # Developer tools
│   ├── validate_docs_layout.py
│   └── verify_imports.py
│
└── run_pipeline.py              # Main pipeline entry point
```

**Key Files**:
- `run_pipeline.py` - Main pipeline orchestrator
- `core/config.py` - Configuration management
- `core/data_helpers.py` - Data I/O utilities
- `core/geocoding.py` - Geocoding engine
- `prepare_webapp_data.py` - Dashboard data export

---

### `/notebooks` - Jupyter Notebooks

**Purpose**: Data exploration, analysis, and prototyping

**Structure**:
```
notebooks/
├── L0_datagovsg.ipynb           # Data.gov.sg exploration
├── L0_datagovsg.py              # Paired Python script
├── L0_onemap.ipynb              # OneMap API exploration
├── L0_onemap.py                 # Paired Python script
├── L0_image_gen.ipynb           # Image generation
├── L0_webscrap_jina.ipynb       # Web scraping
├── L0_wiki.ipynb                # Wikipedia data
├── L1_ura_transactions_processing.ipynb
├── L1_utilities_processing.ipynb
├── L2_sales_facilities.ipynb    # Sales facilities analysis
├── exploration/                 # Experimental notebooks
│   ├── gemini-simple-call.ipynb
│   ├── pandas_agent.ipynb
│   └── spark-dataframe-agent-langchain.py
├── visualize_feature_importance.ipynb
└── 20260123_hdb_eda_investment_analysis.py
```

**Key Convention**:
- All `.ipynb` files have paired `.py` files (Jupytext)
- Edit `.py` in VS Code for code changes
- Use `.ipynb` in Jupyter for visualization
- Sync with: `jupytext --sync notebook.ipynb`

**Naming**:
- `L0_*` - Data collection notebooks
- `L1_*` - Data processing notebooks
- `L2_*` - Feature engineering notebooks
- `exploration/` - Experimental analysis

---

### `/tests` - Python Tests

**Purpose**: Unit and integration tests for Python code

**Structure**:
```
tests/
├── test_core/                   # Core module tests
│   ├── test_config.py
│   ├── test_data_helpers.py
│   ├── test_geocoding.py
│   └── conftest.py              # Core fixtures
├── test_integration/            # Integration tests
│   ├── test_pipeline_stages.py
│   └── conftest.py              # Integration fixtures
├── conftest.py                  # Shared fixtures
└── __init__.py
```

**Test Structure**:
- Mirrors `/scripts` structure
- `test_*.py` or `*_test.py` naming
- `Test*` classes
- `test_*` functions

**Markers**:
- `@pytest.mark.unit` - Fast, isolated tests
- `@pytest.mark.integration` - Component interaction tests
- `@pytest.mark.slow` - Full pipeline tests
- `@pytest.mark.api` - Tests that make API calls

---

### `/docs` - Documentation

**Purpose**: Project documentation, guides, and reference

**Structure**:
```
docs/
├── guides/                      # How-to guides
│   ├── ci-cd-pipeline.md
│   ├── configuration.md
│   └── e2e-testing.md
├── reference/                   # Reference documentation
├── architecture.md              # System architecture
└── README.md                    # Docs overview
```

**Naming Convention**:
- Guides: `YYYYMMDD-name.md`
- Reference files: Descriptive names

---

### `/.planning` - Planning Documentation

**Purpose**: Codebase analysis, planning docs, and technical debt tracking

**Structure**:
```
.planning/
└── codebase/                    # Codebase documentation
    ├── ARCHITECTURE.md          # System architecture
    ├── CONCERNS.md              # Tech debt and issues
    ├── CONVENTIONS.md           # Code conventions
    ├── INTEGRATIONS.md          # External integrations
    ├── STACK.md                 # Technology stack
    ├── STRUCTURE.md             # Directory structure
    └── TESTING.md               # Testing strategy
```

---

## Configuration Files

### Root Level

```
├── pyproject.toml               # Python project configuration
│   ├── [project]                # Project metadata
│   ├── [tool.ruff]              # Ruff linting/formatting
│   ├── [tool.pytest]            # Pytest configuration
│   └── [tool.coverage]          # Coverage settings
│
├── package.json                 # Root package.json (scripts)
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
├── CLAUDE.md                    # Claude Code instructions
└── README.md                    # Project overview
```

### App Level

```
app/
├── package.json                 # Node dependencies
├── astro.config.mjs             # Astro configuration
├── tsconfig.json                # TypeScript configuration
├── playwright.config.ts         # Playwright test configuration
└── .eslintrc.js                 # ESLint rules (if using ESLint)
```

---

## Naming Conventions

### Datasets (Parquet Files)

**Pattern**: `L{stage}_{entity}_{type}.parquet`

**Examples**:
- `L0_hdb_resale.parquet` - Raw HDB resale data
- `L1_hdb_transaction.parquet` - Cleaned HDB transactions
- `L2_hdb_with_features.parquet` - HDB with features
- `L3_unified_dataset.parquet` - All property types combined
- `analysis_mrt_impact.parquet` - Analysis output

**Stages**:
- `L0` - Raw data collection
- `L1` - Processing and geocoding
- `L2` - Feature engineering
- `L3` - Unified dataset
- `L4` - Analytics output
- `L5` - Dashboard metrics

**Entities**:
- `hdb` - HDB resale properties
- `ura` - URA private property transactions
- `condo` - Condominium data
- `unified` - Combined dataset
- `macro` - Macroeconomic indicators

**Types**:
- `resale` - Resale transactions
- `rental` - Rental data
- `transaction` - Generic transactions
- `with_features` - Feature-enriched data

---

### Documentation Files

**Pattern**: `YYYYMMDD-filename.md`

**Examples**:
- `20260228-ci-cd-pipeline.md`
- `20260228-configuration.md`
- `20260123-hdb-eda-investment-analysis.py`

**Reason**: Chronological organization, easy sorting

---

### Script Files

**Python Scripts**:
- `snake_case.py` - Module and script names
- `run_pipeline.py` - Entry point scripts
- `test_*.py` - Test files

**Notebooks**:
- `L0_*.ipynb` - Level 0 notebooks
- `L1_*.ipynb` - Level 1 notebooks
- `exploration/*.ipynb` - Experimental notebooks

**TypeScript/React**:
- `PascalCase.tsx` - React components
- `kebab-case.astro` - Astro pages
- `camelCase.ts` - Utility files

---

### Test Files

**Python**:
- `test_*.py` - Test modules
- `*_test.py` - Alternative test naming
- `conftest.py` - Shared fixtures

**E2E (Playwright)**:
- `*.spec.ts` - Test specs
- `home.spec.ts` - Home page tests
- `dashboard.spec.ts` - Dashboard tests

---

## Key Locations Summary

| Purpose | Location |
|---------|----------|
| **Main Pipeline** | `scripts/run_pipeline.py` |
| **Configuration** | `scripts/core/config.py` |
| **Data I/O** | `scripts/core/data_helpers.py` |
| **Geocoding** | `scripts/core/geocoding.py` |
| **Webapp Export** | `scripts/prepare_webapp_data.py` |
| **Metadata** | `data/metadata.json` |
| **Parquet Files** | `data/parquets/` |
| **Dashboard JSONs** | `app/public/data/` |
| **Notebooks** | `notebooks/` |
| **Python Tests** | `tests/` |
| **E2E Tests** | `app/tests/e2e/` |
| **Environment** | `.env` (from `.env.example`) |
| **Python Config** | `pyproject.toml` |
| **Frontend Config** | `app/astro.config.mjs` |
| **Planning Docs** | `.planning/codebase/` |

---

## File Size Guidelines

### Large Files (Warning)

**Known Large Files**:
- `scripts/core/stages/L3_export.py` - 1,879 lines ⚠️
- `scripts/analytics/analysis/market/analyze_lease_decay_advanced.py` - 838 lines
- `scripts/analytics/analysis/mrt/analyze_mrt_impact.py` - 837 lines

**Guideline**: Consider refactoring files > 500 lines

### Hardcoded Data Files

**Known Hardcoded Files**:
- `scripts/core/mrt_line_mapping.py` - 407 lines (MRT stations)
- `scripts/core/school_features.py` - 726 lines (school tiers)

**Guideline**: Externalize to JSON/CSV if possible

---

## Import Path Conventions

**Always use absolute imports from project root**:

```python
# ✓ Correct
from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet

# ✗ Wrong
from ..core.config import Config
from .stages.L1_process import process_transactions
```

**Reason**: Relative imports break when scripts run from different directories

---

## Git Organization

### Tracked Files

- Source code (all `.py`, `.ts`, `.tsx`, `.astro`)
- Configuration files
- Documentation (`.md`)
- Test files
- `.gitkeep` files (preserve empty directories)

### Not Tracked (Gitignored)

- `.venv/` - Virtual environment
- `.env` - Environment variables (use `.env.example`)
- `__pycache__/` - Python cache
- `*.pyc` - Compiled Python
- `node_modules/` - Node dependencies
- `data/raw/` - Large raw data files
- `data/cache/` - API cache
- `data/logs/` - Log files
- `.pytest_cache/` - Pytest cache
- `app/dist/` - Astro build output
- `.coverage` - Coverage reports
- `htmlcov/` - Coverage HTML

---

## Summary

**Top-Level Directories**: 7 main directories
  - `app/` - Frontend
  - `data/` - Data storage
  - `docs/` - Documentation
  - `notebooks/` - Exploration
  - `scripts/` - Main codebase
  - `tests/` - Tests
  - `.planning/` - Planning docs

**Total Python Files**: 144+ in `/scripts`
**Total Notebooks**: 12+ in `/notebooks`
**Total Test Files**: 8+ in `/tests`

**Key Conventions**:
- Dataset naming: `L{stage}_{entity}_{type}.parquet`
- Documentation: `YYYYMMDD-name.md`
- Absolute imports only
- Paired notebooks (`.ipynb` + `.py`)
