# Egg-n-Bacon-Housing

A Singapore housing data pipeline and ML analysis platform with AI-powered agent assistance.

> The project(data pipeline) started with manual coding, although the current additional bulk of the codes and exploration are heavily assisted with Claude Code and GLM.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-0.1.0+-brightgreen.svg)](https://github.com/astral-sh/uv)

## Quick Start

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone <repo-url>
cd egg-n-bacon-housing
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the complete pipeline
uv run python scripts/run_pipeline.py --stage all --parallel
```

## Overview

Egg-n-Bacon-Housing collects, processes, and analyzes Singapore housing data from government APIs.

- **Data Pipeline**: Automated ETL from data.gov.sg and OneMap
- **Feature Engineering**: Rich features for ML models and analysis
- **AI Agents**: LangChain-powered agents for querying housing data

## Key Features (v0.4.0)

**Performance**:
- 5x faster geocoding with parallel processing (16min -> 3.2min per 1000 addresses)
- 30-40x faster development with API caching (30 sec -> 1 sec re-runs)
- 10-100x faster queries with parquet partitioning

**Architecture**:
- Extracted pipeline logic to reusable modules (`core/pipeline/`)
- Command-line pipeline runner (`scripts/run_pipeline.py`)
- Comprehensive test suite (32 tests)
- File-based caching layer for API responses

## Architecture

```
L0: Data Collection (data.gov.sg, OneMap)
    ↓
L1: Data Processing (Cleaning, Geocoding)
    ↓
L2: Feature Engineering (Distance, Aggregation)
    ↓
L3: Export (Analysis, Apps)
```

**Key Technologies**: uv, pandas, parquet, Jupytext, pytest, LangChain, OneMap API

## Installation

### Prerequisites
- Python 3.11+
- uv package manager
- OneMap API account (free)

### Setup

1. **Install uv** (one-time):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

### API Keys Required

Create a `.env` file in the project root:

```bash
# OneMap API (free registration required)
ONEMAP_EMAIL=your_email@example.com
ONEMAP_EMAIL_PASSWORD=your_password

# Google AI (for LangChain agents)
GOOGLE_API_KEY=your_google_api_key
```

**Register for APIs**:
- [OneMap API](https://www.onemap.gov.sg/apidocs/register) - Free
- [Google AI Studio](https://makersuite.google.com/app/apikey) - Free tier available

## Usage

### Streamlit Dashboard

Launch the interactive housing visualization dashboard:

```bash
# Main unified dashboard
uv run streamlit run apps/dashboard.py

# Or run individual apps
uv run streamlit run apps/1_market_overview.py
uv run streamlit run apps/2_price_map.py
uv run streamlit run apps/3_trends_analytics.py
```

Access at: http://localhost:8501

**Features**:
- Market Overview - Key statistics and market summary
- Price Map - Interactive map with heatmap/scatter views, amenity overlays
- Trends & Analytics - Time-series analysis, comparisons, correlations
- Market Insights - Advanced analytics features

See [apps/README.md](apps/README.md) for full documentation.

### Command-Line Pipeline Runner (Recommended)

```bash
# Run all stages with parallel geocoding (5x faster)
uv run python scripts/run_pipeline.py --stage all --parallel

# Run only L0 (data collection)
uv run python scripts/run_pipeline.py --stage L0

# Run only L1 (processing with geocoding)
uv run python scripts/run_pipeline.py --stage L1 --parallel
```

### Marimo Notebooks (Reactive Python)

Reactive notebooks for exploratory analysis:

```bash
# Edit notebooks
uv run marimo edit marimo/analytics/

# Run as app
uv run marimo run marimo/analytics/your_notebook.py --port 8080
```

See [marimo/README.md](marimo/README.md) for details.

### Backend Documentation Site

Static Astro documentation site:

```bash
cd backend
bun install
bun run dev
```

Access at: http://localhost:4321

See [backend/README.md](backend/README.md) for details.

### Use Pipeline Modules in Python Code

```python
# L0: Data collection with automatic caching
from scripts.core.pipeline.L0_collect import run_all_datagovsg_collection
results = run_all_datagovsg_collection()

# L1: Processing with parallel geocoding
from scripts.core.pipeline.L1_process import run_full_l1_pipeline
results = run_full_l1_pipeline(use_parallel_geocoding=True)
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

### Code Quality

```bash
# Check linting
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .
```

## Project Structure

```
egg-n-bacon-housing/
├── README.md              # Main project README
├── CLAUDE.md              # Development guidelines
├── pyproject.toml         # Python dependencies (uv)
├── jupytext.toml          # Jupyter config
├── .env.example           # Environment template
│
├── scripts/               # Python scripts & core modules
│   ├── pipeline/          # Pipeline orchestration
│   ├── analytics/         # Analytics scripts
│   ├── data/              # Data operations
│   ├── utils/             # Utility scripts
│   ├── core/              # Core modules (moved from root)
│   │   ├── config.py      # Centralized configuration
│   │   ├── data_helpers.py # Parquet management
│   │   ├── geocoding.py   # OneMap API utilities
│   │   ├── cache.py       # API response caching
│   │   ├── agent/         # LangChain agents
│   │   └── pipeline/      # Pipeline logic (L0-L4)
│   └── README.md          # Scripts documentation
│
├── apps/                  # Streamlit dashboards
│   ├── dashboard.py       # Main unified dashboard (moved from root)
│   ├── 1_market_overview.py
│   ├── 2_price_map.py
│   ├── 3_trends_analytics.py
│   └── market_insights/   # Advanced analytics apps
│   └── README.md          # Apps documentation
│
├── notebooks/             # Jupyter notebooks (paired with .py)
│   └── exploration/       # Exploratory analysis
│
├── marimo/                # Marimo reactive notebooks
│   └── analytics/         # Reactive analytics notebooks
│   └── README.md          # Marimo documentation
│
├── backend/               # Astro documentation site
│   ├── README.md          # Backend overview
│   ├── CHANGELOG.md       # Development changelog
│   ├── src/               # Astro source code
│   ├── public/            # Static assets
│   └── package.json       # Node dependencies
│
├── docs/                  # Documentation
│   ├── analytics/         # Analytics documentation
│   ├── guides/            # User guides
│   ├── archive/           # Historical docs
│   └── architecture.md    # System architecture
│
├── tests/                 # Test suite
│   ├── test_cache.py
│   ├── test_geocoding.py
│   ├── test_pipeline.py
│   └── ...
│
└── data/                  # Data directory
    ├── metadata.json      # Dataset registry (git-tracked)
    ├── pipeline/          # L0-L3 pipeline outputs (gitignored)
    ├── analysis/          # Analytics outputs (gitignored)
    ├── cache/             # API cache (gitignored)
    └── logs/              # Runtime logs (gitignored)
```

## Documentation

- **[Architecture](docs/architecture.md)** - System architecture and design
- **[Development Workflow](CLAUDE.md)** - Development principles and guidelines
- **[Optimization Guide](docs/pipeline/20260122-optimization-implementation.md)** - v0.4.0 implementation details
- **[Analytics Findings](docs/analytics-findings.md)** - ML analysis and feature importance
- **[Metrics Design](docs/metrics-design.md)** - L3 housing market metrics
- **[Rental Yield](docs/rental-yield.md)** - Rental data analysis

## Recent Changes

### v0.4.0 (2026-01-22) - Major Performance & Architecture Improvements

**Performance**:
- 5x faster geocoding with parallel processing
- 30-40x faster API calls with caching
- 10-100x faster queries with partitioning

**Features**:
- Caching layer for API responses
- Parallel geocoding (configurable workers)
- Pipeline extraction (L0, L1 modules)
- Command-line pipeline runner
- Comprehensive test suite (32 tests)
- Parquet optimization (partitioning, compression)

**Architecture**:
- Reusable, testable pipeline modules
- Better separation of concerns (notebooks for exploration, modules for logic)
- CI/CD ready code

## Future Improvements

- [ ] Fix 6 failing tests (minor mock adjustments)
- [ ] Extract L2 processing logic
- [ ] Add data quality checks
- [ ] Setup CI/CD pipeline
- [ ] Add pre-commit hooks

## Contributing

See [CLAUDE.md](CLAUDE.md) for development principles.

**Quick Start**:
1. Read `CLAUDE.md`
2. Run `uv sync`
3. Run `uv run pytest`
4. Check `docs/` for details

## Support

- **Issues**: Create a GitHub issue
- **Questions**: Check `docs/` first

## License

[Add your license here]

## Acknowledgments

- data.gov.sg for open housing data
- OneMap for excellent geospatial APIs
- LangChain team for the framework
