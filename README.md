# Egg-n-Bacon-Housing

Singapore housing data pipeline and analytics publishing platform.

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
- Published analytics markdown and precomputed app assets

## Quick Start

```bash
# Setup
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone <repo-url>
cd egg-n-bacon-housing
uv sync

# Configure API keys (encrypted via dotenvx)
cp .env.example .env
# Edit .env with your OneMap, Google AI, and R2 keys

# Fetch manual data files from Cloudflare R2 (~100MB)
dotenvx run -- uv run python scripts/00_sync_data.py

# Run full pipeline
dotenvx run -- uv run python main.py --stage all

# Or run stage-by-stage
dotenvx run -- uv run python main.py --stage ingest
dotenvx run -- uv run python main.py --stage clean
dotenvx run -- uv run python main.py --stage features
dotenvx run -- uv run python main.py --stage export
dotenvx run -- uv run python main.py --stage metrics
```

> **Note on manual data**: ~100MB of CSV/GeoJSON source files (URA transactions, HDB resale, school directory, etc.) are stored in Cloudflare R2 rather than git. Run the sync script after cloning to populate `data/manual/`. See [R2 Sync Guide](docs/guides/r2-sync-guide.md) for details.

## Setup

### Prerequisites

- Python 3.12+
- OneMap API account ([free registration](https://www.onemap.gov.sg/apidocs/register))
- Google AI API key ([free tier](https://makersuite.google.com/app/apikey))

### Environment Variables

Create `.env` in project root (encrypted with dotenvx):

```bash
# Required for geocoding
ONEMAP_EMAIL=your_email@example.com
ONEMAP_EMAIL_PASSWORD=your_password
GOOGLE_API_KEY=your_google_api_key

# Required for R2 manual data sync
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_BUCKET=egg-bacon-housing-data
R2_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com
```

Run commands with `dotenvx run --` to decrypt and inject the env vars.

## Usage

### CLI Entry Point

```bash
# Run all stages
dotenvx run -- uv run python main.py --stage all

# Run specific stage
dotenvx run -- uv run python main.py --stage ingest    # Bronze: raw data collection
dotenvx run -- uv run python main.py --stage clean     # Silver: validation & cleaning
dotenvx run -- uv run python main.py --stage features  # Gold: feature engineering
dotenvx run -- uv run python main.py --stage export    # Platinum: export & webapp data
dotenvx run -- uv run python main.py --stage metrics   # Planning area metrics

# Generate DAG visualization
dotenvx run -- uv run python main.py --stage export --visualize
```

### Python API

```python
from egg_n_bacon_housing.pipeline import build_pipeline, run_pipeline
from egg_n_bacon_housing.config import settings

# Build and run pipeline
dr = build_pipeline(settings)
results = run_pipeline(settings, dr=dr, final_vars=["unified_dataset"])

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

Use Bun as the only supported package manager for `app/`.

## Project Structure

```
egg-n-bacon-housing/
├── src/egg_n_bacon_housing/   # Source package
│   ├── config.py              # pydantic-settings config
│   ├── pipeline.py           # Hamilton DAG driver
│   ├── components/           # Hamilton modules (01_ingestion → 05_metrics) — core pipeline
│   ├── schemas/               # Pydantic models (raw, clean, feature)
│   ├── adapters/              # External API adapters (onemap, datagovsg, geocoding)
│   └── utils/                 # Utilities (cache, loaders, metrics, etc.)
├── scripts/                   # Utility tools (coverage/docs checks)
├── main.py                    # CLI entry point
├── app/                       # Astro documentation site
├── tests/                     # Test suite
├── docs/                      # Architecture & guides
└── data/                      # Pipeline data (pipeline/01_bronze → 04_platinum)
```

**Note**: The supported Python surface is the Hamilton DAG plus shared loaders/config. Published analytics are authored in `docs/analytics/` and served from precomputed assets in `app/public/data/`. The old standalone Python analytics package has been retired from the supported repo surface.

## Configuration

Configuration is managed via `.env` / environment variables with pydantic-settings:

```yaml
PIPELINE__USE_CACHING=true
PIPELINE__CACHE_DURATION_HOURS=24
GEOCODING__MIN_COORDINATE_COVERAGE=0.7
```

Nested environment variables use `__` (double underscore), e.g. `PIPELINE__USE_CACHING=true`.

## Contributing

```bash
# Run tests
uv run pytest --no-cov

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
