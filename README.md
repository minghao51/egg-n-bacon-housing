# Egg-n-Bacon-Housing

Singapore housing data pipeline and ML analysis platform.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-0.1.0+-brightgreen.svg)](https://github.com/astral-sh/uv)

## Overview

Collects, processes, and analyzes Singapore housing data from government APIs.

**Pipeline Stages**:
```
L0: Data Collection (data.gov.sg)
L0_macro: Macro Economic Data (CPI, GDP, SORA, unemployment, PPI)
L1: Processing → L2: Features → L3: Export
L5: Metrics → Webapp: Dashboard
```

**Features**:
- Market Overview, Price Map, Trends & Analytics
- Parallel geocoding (5x faster with OneMap API)
- ML market segmentation and forecasting

## Quick Start

```bash
# Setup (one-time uv install)
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone <repo-url>
cd egg-n-bacon-housing
uv sync

# Configure API keys
cp .env.example .env
# Edit .env with your OneMap and Google AI keys

# Run pipeline
uv run python scripts/run_pipeline.py --stage all --parallel
```

## Setup

### Prerequisites
- Python 3.11+
- OneMap API account ([free registration](https://www.onemap.gov.sg/apidocs/register))
- Google AI API key ([free tier](https://makersuite.google.com/app/apikey))

### Environment Variables

Create `.env` in project root:
```bash
ONEMAP_EMAIL=your_email@example.com
ONEMAP_EMAIL_PASSWORD=your_password
GOOGLE_API_KEY=your_google_api_key
```

## Usage

### Pipeline Runner

```bash
# Run all stages
uv run python scripts/run_pipeline.py --stage all --parallel

# Run specific stage
uv run python scripts/run_pipeline.py --stage L0           # Data collection (data.gov.sg)
uv run python scripts/run_pipeline.py --stage L0_macro     # Macro data (CPI, GDP, SORA, unemployment, PPI)
uv run python scripts/run_pipeline.py --stage L1           # Processing with geocoding
uv run python scripts/run_pipeline.py --stage L2           # Rental yields & features
uv run python scripts/run_pipeline.py --stage L3           # Unified dataset export
uv run python scripts/run_pipeline.py --stage L5           # Metrics calculation
uv run python scripts/run_pipeline.py --stage webapp       # Dashboard JSON export
```

### Python API

```python
from scripts.core.pipeline.L0_collect import run_all_datagovsg_collection
from scripts.core.pipeline.L1_process import run_full_l1_pipeline

# Data collection
results = run_all_datagovsg_collection()

# Processing with parallel geocoding
results = run_full_l1_pipeline(use_parallel_geocoding=True)
```

### Documentation Site

```bash
cd app
bun install
bun run dev
# Visit http://localhost:4321
# Or view at: https://minghao51.github.io/egg-n-bacon-housing/
```

## Project Structure

```
egg-n-bacon-housing/
├── scripts/           # Core modules & analytics
│   ├── core/         # Config, geocoding, cache, pipeline stages
│   └── analytics/    # Analysis scripts
├── notebooks/        # Exploratory analysis (Jupytext paired)
├── app/          # Astro documentation site
├── tests/            # Test suite
├── docs/             # Architecture & guides
└── data/             # Pipeline outputs, cache, logs
```

**Key Files**:
- `pyproject.toml` - Dependencies (managed by uv)
- `core/config.py` - Centralized configuration
- `CLAUDE.md` - Development workflow & guidelines

## Documentation

**📚 [Complete Documentation](docs/README.md)** - Start here for full documentation index

**Getting Started**:
- [Quick Start Guide](docs/guides/quick-start.md) - 5-minute setup
- [Contributing Guide](CONTRIBUTING.md) - How to contribute
- [Usage Guide](docs/guides/usage-guide.md) - Common tasks & workflows

**Reference**:
- [Architecture](docs/architecture.md) - System design & data flow
- [Testing Guide](docs/guides/testing-guide.md) - Testing practices
- [Configuration](docs/guides/configuration.md) - Environment variables

**Analytics Reports**:
- [Key Findings](docs/analytics/findings.md) - Main ML insights
- [MRT Impact](docs/analytics/mrt-impact.md) - Distance to MRT effects
- [School Quality](docs/analytics/school-quality.md) - School tier analysis
- [Price Forecasts](docs/analytics/price-forecasts.md) - Time-series predictions
- [Spatial Hotspots](docs/analytics/spatial-hotspots.md) - Geographic clustering

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

**Quick setup for contributors:**
```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Format code
uv run ruff format .
```

## License

[Add your license here]

## Acknowledgments

- [data.gov.sg](https://data.gov.sg) - Open housing data
- [OneMap](https://www.onemap.gov.sg) - Geospatial APIs
- [LangChain](https://github.com/langchain-ai/langchain) - Agent framework
