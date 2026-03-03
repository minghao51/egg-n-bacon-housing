# Architecture - Egg-n-Bacon-Housing

**Status**: Phase 2 Complete | **Last Updated**: 2026-02-28

---

## 📋 Overview

Singapore housing data pipeline and ML analysis platform that:

1. **Collects** housing transaction data from Singapore government APIs
2. **Processes** and enriches data with geographic and demographic features
3. **Analyzes** market trends, price appreciation, and investment metrics
4. **Presents** insights through interactive analytics dashboards

### Why This Project Exists

Singapore's property market is complex with multiple factors affecting prices:
- Government policies (ABSD, TDSR, cooling measures)
- Location characteristics (MRT access, CBD proximity, amenities)
- Property characteristics (lease remaining, size, type)
- Market cycles and economic indicators

This platform provides data-driven insights to help investors and buyers make informed decisions.

### Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Language** | Python 3.11+ | Modern type hints, performance |
| **Package Manager** | uv | 10-100x faster than pip/conda |
| **Data Storage** | Local parquet files | Fast columnar access, version control friendly |
| **Notebooks** | Jupyter + Jupytext | Paired .py/.ipynb for git-friendly workflow |
| **ML/AI** | LangChain + LangGraph + Google Gemini | Agent-powered analysis |
| **Testing** | pytest | Comprehensive test coverage |
| **Linting** | ruff | Ultra-fast Python linter |

---

## 📁 Directory Structure

```
egg-n-bacon-housing/
├── app/                          # Astro web application
│   ├── public/                   # Static assets + exported data
│   │   └── data/                 # Analytics JSON exports for dashboard
│   └── src/                      # React components, pages
├── data/
│   ├── analysis/                 # Analysis outputs (charts, CSVs)
│   ├── analytics/                # Compressed analytics JSON
│   ├── logs/                     # Application logs
│   ├── metadata.json             # Dataset registry & versioning
│   ├── parquets/                 # All parquet files (gitignored)
│   │   ├── raw_data/             # L0: Raw API responses
│   │   ├── L1/                   # L1: Cleaned transactions
│   │   ├── L2/                   # L2: Feature-enriched data
│   │   └── L3/                   # L3: Aggregated metrics
│   └── raw/                      # Manual data uploads
├── docs/                         # Documentation
│   ├── analytics/                # Investor-focused analysis reports
│   ├── guides/                   # How-to guides
│   ├── plans/                    # Design documents & implementation plans
│   ├── architecture.md           # This file
│   ├── testing-guide.md          # Testing practices
│   └── usage-guide.md            # Getting started
├── notebooks/                    # Jupyter notebooks (paired with .py)
│   ├── L0_*.py                   # Data collection
│   ├── L1_*.py                   # Data processing
│   └── L2_*.py                   # Feature engineering
├── scripts/
│   ├── core/                     # Core utilities
│   │   ├── config.py             # Centralized configuration
│   │   ├── data_helpers.py       # Parquet I/O with metadata
│   │   └── geocoding.py          # OneMap/Google geocoding
│   ├── analytics/                # Analysis scripts
│   │   ├── analysis/             # Analysis implementations
│   │   ├── models/               # ML models
│   │   ├── pipelines/            # Analysis pipelines
│   │   ├── price_appreciation_modeling/
│   │   └── viz/                  # Visualization scripts
│   ├── data/                     # Data processing
│   │   ├── download/             # External data fetchers
│   │   └── process/              # Data transformers
│   └── run_pipeline.py           # Main pipeline entry point
├── tests/                        # Test suite
│   ├── core/                     # Core module tests
│   └── conftest.py               # Shared fixtures
├── .env.example                  # Environment variables template
├── CLAUDE.md                     # Project instructions for Claude
├── pyproject.toml                # Python project configuration
└── README.md                     # Project overview
```

### Key Directories Explained

| Directory | Purpose | When You'll Use It |
|-----------|---------|-------------------|
| **`data/parquets/`** | All processed data storage | Loading data for analysis |
| **`scripts/core/`** | Shared utilities & config | Understanding system behavior |
| **`scripts/analytics/`** | Analysis & ML scripts | Running market analysis |
| **`notebooks/`** | Exploratory data analysis | Prototyping features |
| **`docs/analytics/`** | Published findings | Understanding market insights |
| **`tests/`** | Test suite | Verifying code changes |

---

## 🔄 Data Pipeline Stages

The pipeline follows a staged approach (L0 → L1 → L2 → L3 → L4) where each stage builds on the previous one.

### Stage Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  L0 (Collection)      L1 (Processing)      L2 (Features)           │
│  ──────────────      ──────────────      ──────────────           │
│  • API calls          • Cleaning           • MRT distances         │
│  • Raw data           • Geocoding          • CBD distance          │
│  • Validation         • Standardization    • Amenities             │
│                                                                     │
│         │                    │                    │                │
│         ▼                    ▼                    ▼                │
│                                                                     │
│  L3 (Metrics)         L4 (Analysis)        Webapp                   │
│  ──────────────      ──────────────      ──────────────           │
│  • Aggregations       • ML models          • JSON exports          │
│  • Summary tables     • Forecasts          • Dashboard             │
│  • KPIs               • Reports            • Interactive UI        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### L0: Data Collection

**Purpose**: Fetch raw data from external APIs and store it without modification.

**Data Sources**:

| Source | Data Collected | Frequency | Script |
|--------|---------------|-----------|--------|
| **data.gov.sg API** | HDB resale prices, rental indices, price indices | Monthly | `L0_datagovsg.py` |
| **OneMap API** | Planning areas, household income by district | One-time | `L0_onemap.py` |
| **Wikipedia** | Shopping mall locations | One-time | `L0_wiki.py` |

**Output**: Raw parquet files in `data/parquets/raw_data/`
- `hdb_resale_raw.parquet`
- `ura_rental_raw.parquet`
- `shopping_malls_raw.parquet`

**Key Features**:
- Automatic retry on API failures
- Rate limiting to respect API quotas
- Data validation before saving
- Metadata tracking in `data/metadata.json`

---

### L0_macro: Macroeconomic Data

**Purpose**: Collect macroeconomic indicators for VAR modeling and market analysis.

**Data Sources**:

| Indicator | Source | Frequency | File |
|-----------|--------|-----------|------|
| **SORA** | MAS (Monetary Authority of Singapore) | Monthly | `sora_rates_monthly.parquet` |
| **CPI** | SingStat Table Builder | Monthly | `singapore_cpi_monthly.parquet` |
| **GDP** | SingStat Table Builder | Quarterly | `sgdp_quarterly.parquet` |
| **Unemployment** | SingStat Table Builder | Monthly | `unemployment_rate_monthly.parquet` |
| **Property Price Index** | SingStat Table Builder | Quarterly | `property_price_index_quarterly.parquet` |
| **Housing Policies** | Manual curation | Event-based | `housing_policy_dates.parquet` |

**Usage**: VAR models, policy impact analysis, market cycle detection

---

### L1: Data Processing

**Purpose**: Clean, standardize, and geocode transaction data.

**Transformations**:

1. **Data Cleaning**
   - Remove duplicates
   - Handle missing values
   - Standardize column names
   - Validate data types

2. **Geocoding** (via OneMap API)
   - Address → coordinates (lat, lng)
   - Address → planning area
   - Fallback to Google Maps API if OneMap fails

3. **Data Integration**
   - Merge HDB and URA datasets
   - Standardize property types
   - Add metadata columns

**Output**: Processed parquet files in `data/parquets/L1/`
- `L1_hdb_transaction.parquet`
- `L1_ura_transaction.parquet`
- `L1_utility_transaction.parquet`

**Key Features**:
- Batch geocoding with automatic retry
- Caching to reduce API calls
- Progress tracking for large datasets
- Error logging for failed geocodes

---

### L2: Feature Engineering

**Purpose**: Create features for ML models and analysis.

**Feature Categories**:

| Category | Features | Example |
|----------|----------|---------|
| **Distance Features** | MRT, CBD, amenities | `distance_to_mrt_m`, `distance_to_cbd_km` |
| **Aggregation Features** | Counts within radius | `mrt_count_1km`, `mall_count_2km` |
| **Demographic Features** | Area-level metrics | `median_household_income`, `school_tier` |
| **Temporal Features** | Time-based metrics | `age_years`, `transaction_quarter` |
| **Calculated Metrics** | Derived values | `price_psf`, `rental_yield_pct` |

**Output**: Feature-rich parquet files in `data/parquets/L2/`
- `L2_hdb_with_features.parquet`
- `L2_ura_with_features.parquet`
- `L2_rental_yield.parquet`

**Key Features**:
- H3 hex grid spatial indexing
- Walking distance calculations (not just straight-line)
- School tier assignment (based on MOE rankings)
- MRT line and distance bands

---

### L3: Metrics & Aggregations

**Purpose**: Create optimized summary tables for dashboards and analysis.

**Output Tables**:

| Table | Description | Use Case |
|-------|-------------|----------|
| `market_summary.parquet` | Aggregated stats by property_type/period/tier | Dashboard metrics |
| `planning_area_metrics.parquet` | Metrics by planning area | Regional comparisons |
| `rental_yield_top_combos.parquet` | Top rental yield combinations | Investment screening |

**Aggregations**:
- Median prices by town/property type/month
- Year-over-year appreciation rates
- Rental yield percentiles
- Market volume statistics

**Output**: `data/parquets/L3/` directory

---

### L4: Analysis Pipeline

**Purpose**: Run ML models, forecasts, and generate insights.

**Analysis Categories**:

| Category | Analyses | Output |
|----------|----------|--------|
| **Market Analysis** | Appreciation, yields, segmentation | Charts, CSVs, reports |
| **Amenity Analysis** | MRT impact, school quality, CBD access | Feature importance, coefficients |
| **Spatial Analysis** | Hotspots, autocorrelation, clusters | Maps, LISA clusters |
| **Causal Analysis** | Policy impact, lease decay | DiD estimates, RDD results |

**Scripts**: Located in `scripts/analytics/analysis/`
- `market/` - Market trend analysis
- `amenity/` - Amenity impact analysis
- `spatial/` - Spatial statistics
- `causal/` - Causal inference

**Output**: `data/analysis/` with visualizations and CSVs

**See**: [L4 Analysis Pipeline Guide](./guides/l4-analysis-pipeline.md) for details.

---

## 🧩 Core Components

### Configuration (`scripts/core/config.py`)

**Purpose**: Centralized configuration management for the entire project.

**What It Provides**:
```python
from scripts.core.config import Config

# Access paths
data_dir = Config.DATA_DIR           # → /path/to/project/data
parquets_dir = Config.PARQUETS_DIR   # → /path/to/project/data/parquets

# Access API keys (loaded from .env)
api_key = Config.GOOGLE_API_KEY
onemap_email = Config.ONEMAP_EMAIL

# Validate configuration
Config.validate()  # Raises ValueError if misconfigured
```

**Key Configuration Items**:
- Paths to data directories
- API keys (from environment variables)
- Feature flags (caching, verbose logging)
- Database connection strings (if needed)

**Why Centralized?**:
- Single source of truth for all paths
- Easy to mock for testing
- Consistent across all modules
- Environment-aware (dev vs production)

---

### Data Helpers (`scripts/core/data_helpers.py`)

**Purpose**: Parquet file I/O with automatic metadata tracking.

**What It Provides**:
```python
from scripts.core.data_helpers import load_parquet, save_parquet, list_datasets

# Load a dataset by name
df = load_parquet("L2_hdb_with_features")

# Save a dataset with metadata
save_parquet(
    df,
    dataset_name="L3_unified_dataset",
    source="L2_hdb_with_features + L2_ura_with_features"
)

# List all available datasets
datasets = list_datasets()
# → {"L2_hdb_with_features": {...}, "L3_unified_dataset": {...}}
```

**Key Features**:
1. **Automatic Metadata Tracking**: Every save operation updates `data/metadata.json`
2. **Path Resolution**: Use dataset names, not full paths
3. **Error Handling**: Clear error messages if datasets don't exist
4. **Version Control Friendly**: Uses relative paths

**Metadata Schema**:
```json
{
  "datasets": {
    "L2_hdb_with_features": {
      "path": "data/parquets/L2/L2_hdb_with_features.parquet",
      "rows": 150000,
      "columns": 45,
      "created_at": "2026-01-15T10:30:00",
      "source": "L1_hdb_transaction + feature engineering"
    }
  },
  "last_updated": "2026-01-15T10:30:00"
}
```

---

### Geocoding (`scripts/core/geocoding.py`)

**Purpose**: Address → coordinate conversion with intelligent fallback.

**What It Provides**:
```python
from scripts.core.geocoding import Geocoder

# Initialize geocoder
geocoder = Geocoder()

# Geocode single address
result = geocoder.geocode("123 Ang Mo Kio Avenue 3")
# → {"lat": 1.3691, "lng": 103.8492, "address": "..."}

# Geocode batch
addresses = ["123 Ang Mo Kio", "456 Tampines"]
results = geocoder.geocode_batch(addresses)
```

**Geocoding Strategy**:
1. **Primary**: OneMap API (Singapore-specific, free)
2. **Fallback**: Google Maps API (global, requires API key)
3. **Caching**: Results cached for 24 hours

**Rate Limiting**:
- OneMap: 1 request/second (to respect quotas)
- Token auto-refresh on 401/403 errors

---

### Metrics (`scripts/core/metrics.py`)

**Purpose**: Market metrics calculations for investment analysis.

**What It Provides**:
```python
from scripts.core.metrics import calculate_roi_score, compute_monthly_metrics

# Calculate ROI score for a property
roi = calculate_roi_score(
    feature_df,        # Property features
    rental_yield_df    # Rental yield data
)
# → {"roi_score": 75, "rank": "top_10%"}

# Compute monthly market metrics
metrics = compute_monthly_metrics('2020-01', '2025-12')
# → DataFrame with monthly median prices, volumes, yields
```

---

## 🛠️ Development Workflow

### Initial Setup

**One-Time Setup** (5-10 minutes):
```bash
# 1. Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone repository (if not already done)
git clone <repo-url>
cd egg-n-bacon-housing

# 3. Install dependencies
uv sync

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Verify installation
uv run pytest
```

**Required API Keys**:
- `ONEMAP_EMAIL` - Singapore geocoding (register at onemap.gov.sg)
- `GOOGLE_API_KEY` - Optional, for geocoding fallback

---

### Running Code

**Always use `uv run`** to execute commands within the managed environment:

```bash
# Run Python scripts
uv run python script.py

# Run tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix
```

**Why `uv run`?**
- Ensures correct Python environment
- Faster than activating venv manually
- Works consistently across machines

---

### Working with Notebooks

**Jupytext Pairing**: All notebooks have paired `.py` files for git-friendly version control.

**Recommended Workflow**:
```bash
# 1. Edit the .py file in your IDE
code notebooks/L0_datagovsg.py

# 2. Run the .py file directly
uv run python notebooks/L0_datagovsg.py

# 3. Sync to .ipynb if needed for visualization
cd notebooks
uv run jupytext --sync L0_datagovsg.ipynb

# 4. Launch Jupyter for interactive work
uv run jupyter notebook
```

**Why Paired Files?**
- `.py` files: Clean diffs, easy code review, IDE support
- `.ipynb` files: Interactive visualization, exploratory analysis
- Jupytext keeps them in sync automatically

---

### Common Development Tasks

**Add a new dependency**:
```bash
uv add pandas
uv add --dev pytest  # Development dependency
```

**Update all dependencies**:
```bash
uv sync --upgrade
```

**Run specific test**:
```bash
uv run pytest tests/core/test_config.py::TestConfigPaths::test_base_dir_exists
```

**Run tests by category**:
```bash
uv run pytest -m unit          # Fast unit tests only
uv run pytest -m integration   # Integration tests
uv run pytest -m "not slow"    # Skip slow tests
```

**Generate coverage report**:
```bash
uv run pytest --cov=scripts/core --cov-report=html
open htmlcov/index.html
```

---

## 💡 Key Design Decisions

### 1. Local Parquet Files (Not DVC/S3)

**Decision**: Store all data in local parquet files instead of using DVC or cloud storage.

**Rationale**:
- ✅ **Faster access**: No network latency, no download wait times
- ✅ **Simpler workflow**: Just read from disk, no auth or sync issues
- ✅ **Version control friendly**: Parquet files are gitignored, metadata is tracked
- ✅ **Sufficient scale**: Dataset size (~1GB) fits comfortably on local disk

**Trade-off**: Not suitable for very large datasets (>10GB) or team collaboration.

**When to reconsider**: If dataset grows beyond 10GB or team needs shared data.

---

### 2. Jupytext Pairing (Not .ipynb Only)

**Decision**: Use Jupytext to pair all `.ipynb` files with `.py` files.

**Rationale**:
- ✅ **Git-friendly**: `.py` files show clean diffs, `.ipynb` files are binary
- ✅ **IDE support**: Full VS Code features (autocomplete, refactoring)
- ✅ **Code review**: Easy to review changes in pull requests
- ✅ **Execution flexibility**: Run `.py` files directly or use Jupyter interactively

**Trade-off**: Requires sync step when switching between file types.

**When to reconsider**: If you only use Jupyter and never need git history.

---

### 3. uv Package Manager (Not pip/conda)

**Decision**: Use uv for all Python package management.

**Rationale**:
- ✅ **Speed**: 10-100x faster than pip, much faster than conda
- ✅ **Compatibility**: Drop-in replacement for pip, works with existing tools
- ✅ **Reliability**: Better dependency resolution, fewer conflicts
- ✅ **Modern**: Written in Rust, actively maintained

**Trade-off**: Newer tool, less widely adopted than pip.

**When to reconsider**: If you need conda's non-Python package management.

---

### 4. Centralized Configuration (Not Environment Variables Everywhere)

**Decision**: Use `scripts/core/config.py` as single source of truth.

**Rationale**:
- ✅ **Consistency**: All paths/keys in one place
- ✅ **Testability**: Easy to mock config in tests
- ✅ **Type safety**: Type hints on all config values
- ✅ **Validation**: Centralized validation logic

**Trade-off**: Single import dependency for all modules.

**When to reconsider**: If you have multiple isolated services.

---

### 5. Staged Pipeline (Not Monolithic Script)

**Decision**: Organize pipeline into L0 → L1 → L2 → L3 → L4 stages.

**Rationale**:
- ✅ **Modularity**: Each stage can run independently
- ✅ **Debugging**: Easy to isolate issues to specific stage
- ✅ **Reproducibility**: Clear data lineage through metadata
- ✅ **Flexibility**: Can skip stages if data hasn't changed

**Trade-off**: More files to manage compared to single script.

**When to reconsider**: If pipeline is very simple (2-3 steps).

---

### 6. H3 Hex Grid (Not Arbitrary Boundaries)

**Decision**: Use H3 hexagonal grid for spatial analysis.

**Rationale**:
- ✅ **Consistent scale**: Each hex cell covers same area (~0.5 km² at res 8)
- ✅ **Neighbor definition**: Each cell has 6 adjacent neighbors
- ✅ **Hierarchical**: Can aggregate to coarser resolutions
- ✅ **Spatial analysis**: Built-in support for spatial statistics

**Trade-off**: Less intuitive than planning areas for non-technical users.

**When to reconsider**: If presenting to general public (use planning areas instead).

---

## 📚 Related Documentation

| Document | Description | For You If... |
|----------|-------------|---------------|
| **[Usage Guide](./usage-guide.md)** | Getting started, common tasks | You're new to the project |
| **[Testing Guide](./testing-guide.md)** | Testing practices and patterns | You're writing tests |
| **[Data Reference](./guides/data-reference.md)** | Complete dataset catalog | You need to understand data schema |
| **[L4 Analysis Pipeline](./guides/l4-analysis-pipeline.md)** | Analysis pipeline details | You're running market analysis |
| **[Quick Start](./guides/quick-start.md)** | 5-minute setup guide | You want to start quickly |
| **[External Data Setup](./guides/external-data-setup.md)** | API key configuration | You need to configure data sources |
| **[Configuration Guide](./guides/20260228-configuration.md)** | Environment variables & settings | You need to configure the project |
| **[CI/CD Pipeline Guide](./guides/20260228-ci-cd-pipeline.md)** | GitHub Actions workflows | You need to understand CI/CD |
| **[API Reference](./reference/20260228-api-reference.md)** | Core utilities API documentation | You need to use core functions |

---

## 🆘 Troubleshooting

| Issue | Symptom | Solution |
|-------|---------|----------|
| **ModuleNotFoundError** | `No module named 'scripts'` | Run from project root with `uv run` |
| **Dataset not found** | `Dataset 'X' not found` | Run preceding pipeline stages first |
| **API rate limit** | `429 Too Many Requests` | Wait (built-in delays) or check API quota |
| **Geocoding fails** | All addresses return `None` | Check OneMap credentials in `.env` |
| **Metadata outdated** | Old datasets in `list_datasets()` | Run `scripts/prepare_analytics_json.py` |
| **Tests fail locally** | Tests pass in CI but fail locally | Check your `.env` file, update dependencies |

---

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Total Lines of Code** | ~25,000 Python |
| **Test Coverage** | 70% (core modules) |
| **Number of Datasets** | 50+ parquet files |
| **Analysis Scripts** | 40+ analysis scripts |
| **Documentation Pages** | 15+ guides & reports |
| **Supported Property Types** | HDB, Condo, EC |
| **Data Period** | 2017-2026 (10 years) |
| **Total Transactions** | ~500,000+ records |
