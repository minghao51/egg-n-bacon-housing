# Egg-n-Bacon-Housing

Singapore housing data pipeline and ML analysis platform.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/uv-0.1.0+-brightgreen.svg)](https://github.com/astral-sh/uv)

## Overview

Collects, processes, and analyzes Singapore housing data from government APIs.

**Medallion Pipeline Layers**:
```
01_bronze  → 02_silver  → 03_gold  → 04_platinum
  raw         validated    features    predictions
```

**Features**:
- Hamilton DAG orchestration (lineage tracking, caching, parallel execution)
- Pydantic schema validation at layer boundaries
- Market Overview, Price Map, Trends & Analytics
- Parallel geocoding (OneMap API)
- ML market segmentation and forecasting

## Quick Start

```bash
# Setup
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone <repo-url>
cd egg-n-bacon-housing
uv sync

# Configure API keys
cp .env.example .env
# Edit .env with your OneMap and Google AI keys

# Run full pipeline
uv run python main.py --stage all

# Or run stage-by-stage
uv run python scripts/01_ingest.py   # Bronze layer
uv run python scripts/02_clean.py   # Silver layer
uv run python scripts/03_features.py # Gold layer
uv run python scripts/04_export.py  # Platinum export
uv run python scripts/05_metrics.py # Metrics
```

## Setup

### Prerequisites
- Python 3.12+
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

### CLI Entry Point

```bash
# Run all stages
uv run python main.py --stage all

# Run specific stage
uv run python main.py --stage ingest    # Bronze: raw data collection
uv run python main.py --stage clean     # Silver: validation & cleaning
uv run python main.py --stage features  # Gold: feature engineering
uv run python main.py --stage export    # Platinum: export & webapp data
uv run python main.py --stage metrics   # Planning area metrics

# Generate DAG visualization
uv run python main.py --stage export --visualize
```

### Python API

```python
from egg_n_bacon_housing.pipeline import build_pipeline, run_full_pipeline
from egg_n_bacon_housing.config import settings

# Build and run pipeline
dr = build_pipeline()
results = dr.execute(final_vars=["unified_dataset", "dashboard_json"])

# Inspect DAG
dr.visualize_execution(final_vars=["unified_dataset"], output_file_path="dag.png")
```

### Documentation Site

```bash
cd app
bun install
bun run dev
# Visit http://localhost:4321
```

## Project Structure

```
egg-n-bacon-housing/
├── src/egg_n_bacon_housing/   # Source package
│   ├── config.py              # pydantic-settings config
│   ├── pipeline.py           # Hamilton DAG driver
│   ├── components/           # Hamilton modules (01_ingestion → 06_analytics) — core pipeline
│   ├── schemas/               # Pydantic models (raw, clean, feature)
│   ├── adapters/              # External API adapters (onemap, datagovsg, geocoding)
│   ├── utils/                 # Utilities (cache, data_helpers, metrics, etc.)
│   └── analytics/             # Analysis modules (market, mrt, school, spatial...) — exploratory, not wired to DAG
├── scripts/                   # Stage entry points (01_ingest.py, etc.)
├── main.py                    # CLI entry point
├── config.yaml                # Pipeline configuration
├── app/                       # Astro documentation site
├── tests/                     # Test suite
├── docs/                      # Architecture & guides
└── data/                      # Pipeline data (pipeline/01_bronze → 04_platinum)
```

**Note**: The Hamilton DAG (`components/`) runs the core pipeline from bronze to platinum. Analytics modules (`analytics/`) are standalone exploratory scripts that consume exported datasets from the platinum layer. They are run on-demand for specific analyses and are not wired into the automated pipeline.

## Configuration

Configuration is managed via `config.yaml` with pydantic-settings:

```yaml
app_name: "egg-n-bacon-housing"
data_path: "./data"
pipeline:
  parquet_compression: "snappy"
  use_caching: true
geocoding:
  max_workers: 5
  api_delay_seconds: 1.2
```

Environment variables and `.env` take priority over `config.yaml`.

## Contributing

```bash
# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint
uv run ruff check .
```

## License

[Add your license here]

## Acknowledgments

- [data.gov.sg](https://data.gov.sg) - Open housing data
- [OneMap](https://www.onemap.gov.sg) - Geospatial APIs
- [LangChain](https://github.com/langchain-ai/langchain) - Agent framework
