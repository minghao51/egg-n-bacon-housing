# Egg-n-Bacon-Housing Architecture

**Last Updated**: 2025-01-20
**Status**: ✅ Phases 1-3 Complete

---

## Overview

Egg-n-Bacon-Housing is a Singapore housing data pipeline and ML analysis platform. The project collects raw data from multiple government APIs, processes and engineers features, and provides analysis tools through Streamlit apps and LangChain agents.

### Tech Stack

- **Language**: Python 3.11+
- **Package Manager**: uv (modern, fast Python package manager)
- **Data Storage**: Local parquet files with metadata tracking
- **Notebooks**: Jupyter with Jupytext (paired .py files for version control)
- **Testing**: pytest + ruff
- **Configuration**: Centralized in `src/config.py`
- **Apps**: Streamlit (multi-page)
- **ML/Agents**: LangChain + LangGraph + Google Gemini

---

## Directory Structure

```
egg-n-bacon-housing/
├── .venv/                          # Virtual environment (managed by uv)
├── .gitignore
├── uv.lock                         # Dependency lock file
├── pyproject.toml                  # Project dependencies and config
├── jupytext.toml                   # Notebook-script pairing config
├── environment.yml                 # Legacy conda env (deprecated)
├── CLAUDE.md                       # Development principles and workflow
├── README.md
│
├── data/                           # Data directory
│   ├── parquets/                  # All parquet files (gitignored)
│   │   ├── raw_data/
│   │   ├── L1/
│   │   ├── L2/
│   │   └── L3/
│   ├── metadata.json              # Dataset registry (git-tracked)
│   └── raw_documents/             # Source markdown docs
│
├── notebooks/                      # Jupyter notebooks (paired with .py)
│   ├── L0_*.ipynb                 # Data collection
│   ├── L1_*.ipynb                 # Data processing
│   ├── L2_*.ipynb                 # Feature engineering
│   ├── L3_*.ipynb                 # Export
│   └── *.py                       # Paired Python scripts
│
├── src/                           # Source code
│   ├── __init__.py
│   ├── config.py                  # Centralized configuration
│   ├── data_helpers.py            # Parquet management
│   ├── agent/                     # LangChain agents
│   │   └── general_agent.py
│   └── pipeline/                  # Extracted pipeline logic (WIP)
│       ├── __init__.py
│       ├── L0_collect.py
│       ├── L1_process.py
│       ├── L2_features.py
│       └── L3_export.py
│
├── apps/                          # Streamlit applications
│   ├── single_agent.py
│   ├── single_agent2.py
│   ├── spiral.py
│   └── spiral3.py
│
├── tests/                         # Test suite
│   ├── test_config.py
│   └── test_data_helpers.py
│
└── docs/                          # Documentation
    ├── 20250120-parquet-migration-design.md
    ├── 20250120-migration-summary.md
    ├── 20250120-architecture.md          # This file
    └── progress/                         # Progress tracking
        └── 20250120-dvc-to-parquet-migration-progress.md
```

---

## Data Pipeline Architecture

### Pipeline Levels

The data pipeline is organized into 4 levels:

#### L0: Data Collection
- **Purpose**: Collect raw data from external sources
- **Sources**:
  - data.gov.sg API (resale flats, rental index, price index)
  - OneMap API (planning areas, household income)
  - Wikipedia scraping (shopping malls)
- **Output**: Raw parquet files (prefix: `raw_`)
- **Notebooks**: `L0_datagovsg.ipynb`, `L0_onemap.ipynb`, `L0_wiki.ipynb`

#### L1: Data Processing
- **Purpose**: Clean, transform, and standardize data
- **Processing**:
  - URA transaction data (condo, EC, HDB)
  - Utilities data (schools, malls, water bodies, amenities)
  - Geospatial queries and matching
- **Output**: Processed parquet files (prefix: `L1_`)
- **Notebooks**: `L1_ura_transactions_processing.ipynb`, `L1_utilities_processing.ipynb`

#### L2: Feature Engineering
- **Purpose**: Create features for ML/analysis
- **Features**:
  - Property facilities
  - Nearby amenities counts
  - Sales and transaction metrics
  - Listings data integration
- **Output**: Feature-engineered parquet files (prefix: `L2_`, `L3_`)
- **Notebooks**: `L2_sales_facilities.ipynb`

#### L3: Export
- **Purpose**: Export data for analysis/applications
- **Destinations**:
  - S3 (backup)
  - Supabase (production database)
- **Output**: Final datasets
- **Notebooks**: `L3_upload_s3.ipynb`

### Data Flow

```
External APIs (L0)
    ↓
Raw Data (parquet + metadata)
    ↓
Processing (L1)
    ↓
Cleaned Data (parquet + metadata)
    ↓
Feature Engineering (L2)
    ↓
Feature-Rich Data (parquet + metadata)
    ↓
Export (L3)
    ↓
S3 / Supabase / Streamlit Apps
```

---

## Core Components

### 1. Data Management (`src/data_helpers.py`)

**Purpose**: Centralized parquet file management with metadata tracking

**Key Functions**:
- `load_parquet(dataset_name, version=None)` - Load datasets
- `save_parquet(df, dataset_name, source, version, mode)` - Save with metadata
- `list_datasets()` - List all tracked datasets
- `verify_metadata()` - Validate checksums

**Benefits**:
- Simple, consistent API
- Automatic metadata tracking (versions, checksums, lineage)
- Error handling and validation
- Git-friendly (metadata.json is small and tracked)

### 2. Configuration (`src/config.py`)

**Purpose**: Centralized configuration management

**Features**:
- Path management (BASE_DIR, DATA_DIR, PARQUETS_DIR, etc.)
- API keys (ONEMAP, GOOGLE, SUPABASE, JINA_AI)
- Feature flags (USE_CACHING, VERBOSE_LOGGING)
- Validation methods

**Usage**:
```python
from src.config import Config

# Access paths
data_dir = Config.DATA_DIR

# Access API keys
api_key = Config.GOOGLE_API_KEY

# Validate configuration
Config.validate()
```

### 3. Pipeline Modules (`src/pipeline/`)

**Purpose**: Extracted pipeline logic for reusability and testing

**Structure**:
- `L0_collect.py` - Data collection functions
- `L1_process.py` - Data processing functions
- `L2_features.py` - Feature engineering functions
- `L3_export.py` - Export functions

**Status**: Placeholder modules created, ready for logic extraction from notebooks

### 4. Agents (`src/agent/`)

**Purpose**: LangChain agents for querying and analyzing housing data

**Features**:
- General agent with tool use
- Integration with Google Gemini
- Context-aware queries
- RAG (Retrieval Augmented Generation) capabilities

### 5. Streamlit Apps (`apps/`)

**Purpose**: Interactive web applications for data exploration

**Apps**:
- `single_agent.py` - Basic agent chat interface
- `single_agent2.py` - Enhanced agent with memory
- `spiral.py`, `spiral3.py` - Data visualization dashboards

**Future**: Consolidate into multi-page app

---

## Development Workflow

### Environment Setup

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Running Code

**Always use `uv run`**:
```bash
# Python scripts
uv run python script.py

# Jupyter notebooks
uv run jupyter notebook

# Tests
uv run pytest

# Linting
uv run ruff check .
```

### Working with Notebooks

**Jupytext is configured** - notebooks are paired with Python scripts:

1. **All notebooks have paired .py files**:
   - `notebooks/L0_datagovsg.ipynb` ↔ `notebooks/L0_datagovsg.py`
   - Edit the .py file, the .ipynb updates automatically
   - Edit the .ipynb file, the .py updates automatically

2. **Recommended workflow**:
   - Edit .py files in VS Code for code changes (better IDE support)
   - Use .ipynb files for visualization and exploration in Jupyter
   - Cell markers in .py files use `#%%` format

3. **To sync manually**:
   ```bash
   cd notebooks
   uv run jupytext --sync notebook_name.ipynb
   ```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_data_helpers.py

# Run with verbose output
uv run pytest -v

# Check linting
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .
```

---

## Key Design Decisions

### 1. Local Parquet Files (Not DVC/S3)

**Decision**: Use local parquet files with metadata tracking instead of DVC + S3

**Rationale**:
- Data size is small (GB range), making local storage practical
- Faster access (no network overhead)
- Simpler workflow (no DVC commands, no S3 setup for local dev)
- Infrequent updates (weekly/monthly) reduce need for complex versioning

**Benefits**:
- 10-100x faster data access
- Simpler onboarding for new developers
- Git-friendly metadata tracking
- Easier debugging and inspection

### 2. Jupytext for Notebook-Script Pairing

**Decision**: Pair all Jupyter notebooks with Python scripts using Jupytext

**Rationale**:
- Notebooks are great for exploration but poor for version control
- JSON format makes git diffs unreadable
- Scripts have better IDE support (autocomplete, refactoring)

**Benefits**:
- Clean git diffs for code reviews
- Edit scripts in VS Code with full Python tooling
- Notebooks preserve outputs and visualizations
- Automatic two-way sync

### 3. Centralized Configuration

**Decision**: Single `config.py` file for all configuration

**Rationale**:
- Scattered configuration is hard to maintain
- Environment variables should be loaded in one place
- Paths should be managed centrally

**Benefits**:
- Single source of truth
- Validation prevents runtime errors
- Easy to test with different configs
- Clear documentation of all settings

### 4. uv Package Manager

**Decision**: Use uv instead of conda/pip

**Rationale**:
- 10-100x faster than pip/conda
- Modern Python packaging standards
- Built-in lockfile support
- No environment activation needed

**Benefits**:
- Faster dependency installation
- Simpler commands (`uv run` vs `conda activate && python`)
- Better reproducibility with lockfiles

---

## Technology Choices

| Component | Technology | Why |
|-----------|-----------|-----|
| Package Manager | uv | Fast, modern, simple |
| Data Storage | Parquet | Columnar, fast, compression |
| Notebook Sync | Jupytext | Git-friendly, IDE support |
| Testing | pytest | Industry standard, powerful |
| Linting | ruff | Fast, modern, comprehensive |
| Configuration | python-dotenv | Simple, secure |
| ML/AI | LangChain + LangGraph | Flexible, agentic |
| LLM | Google Gemini | Good performance, API |
| Apps | Streamlit | Fast to build, Python-native |
| Database | Supabase | Postgres + API + Auth |

---

## Performance Considerations

### Data Access
- Local parquet files are 10-100x faster than S3/DVC
- Columnar format enables fast partial reads
- Snappy compression balances speed and size

### Dependency Management
- uv installs dependencies in seconds, not minutes
- Lockfile ensures reproducibility
- Parallel downloads speed up installation

### Notebook Performance
- Jupytext sync is nearly instantaneous
- Script editing in VS Code is faster than Jupyter
- Pytest runs tests in parallel by default

---

## Security

### API Keys
- Stored in `.env` file (git-ignored)
- Loaded via `python-dotenv`
- Template provided in `.env.example`
- Validation in `Config.validate()`

### Data
- No sensitive data in repository
- Only metadata.json tracks datasets (not the data itself)
- Parquet files are git-ignored

---

## Future Improvements

### High Priority (Done ✅)
- ✅ Migrate to uv
- ✅ Setup Jupytext
- ✅ Create centralized config
- ✅ Add basic tests
- ✅ Configure ruff

### Medium Priority (Done ✅)
- ✅ Restructure src/ directory
- ✅ Create pipeline modules
- ✅ Add test coverage

### Low Priority (Optional)
- 🔄 Extract notebook logic to pipeline scripts
- 🔄 Consolidate Streamlit apps into multi-page app
- 🔄 Add comprehensive docs (architecture, data pipeline)
- 🔄 Add more tests (integration tests, agent tests)
- 🔄 Setup CI/CD pipeline

---

## Related Documentation

- **Migration Design**: `docs/20250120-parquet-migration-design.md`
- **Migration Summary**: `docs/20250120-migration-summary.md`
- **Progress Tracking**: `docs/progress/20250120-dvc-to-parquet-migration-progress.md`
- **Development Workflow**: `CLAUDE.md`

---

## Contributing

See `CLAUDE.md` for development principles and workflow.

### Quick Start
1. Read `CLAUDE.md` for development guidelines
2. Run `uv sync` to install dependencies
3. Run `uv run pytest` to verify setup
4. Check `docs/` for detailed documentation

---

## License

[Add your license here]
