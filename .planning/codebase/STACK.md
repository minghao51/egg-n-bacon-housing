# Egg-n-Bacon-Housing: Technology Stack

## Overview

This document outlines the complete technology stack used in the egg-n-bacon-housing project - a Singapore housing data pipeline with ML analysis and interactive web visualization.

**Project Type**: Data Science + Web Application
**Primary Languages**: Python, TypeScript
**Deployment**: GitHub Pages (static site)

---

## Core Technologies

### Backend/Data Pipeline (Python)

**Runtime**:
- Python 3.11+ (specified in pyproject.toml)
- uv package manager for fast dependency management

**Key Libraries**:

| Category | Libraries | Purpose |
|----------|-----------|---------|
| **Data Processing** | pandas>=2.0.0, pyarrow>=15.0.0, numpy>=1.24.0 | DataFrame operations, parquet I/O |
| **Geospatial** | geopandas, h3==4.1.0b2, pyproj | Spatial analysis, hexagon grids |
| **ML/Analytics** | scikit-learn, xgboost>=3.1.3, prophet>=1.2.1 | Modeling, forecasting |
| **Statistics** | statsmodels>=0.14.0, libpysal>=4.6.0, esda>=1.5.0, lifelines>=0.27.0 | Statistical analysis, spatial stats, survival analysis |
| **Visualization** | plotly>=6.5.2, seaborn, pygwalker | Interactive charts |
| **API/Network** | requests, beautifulsoup4, boto3 | HTTP requests, web scraping, AWS S3 |
| **Caching** | cachetools>=6.2.4 | API response caching |
| **Fuzzy Matching** | rapidfuzz>=3.14.3 | String matching |
| **AI/LLM** | langchain>=0.3.0, langchain-google-genai==2.0.0, langgraph==0.2.32 | LLM integration |
| **Database** | supabase | Database client |
| **Notebooks** | marimo>=0.19.6, jupyter>=1.0.0, ipykernel>=6.0.0 | Interactive analysis |
| **Utilities** | python-dotenv, ipywidgets, tabulate==0.9.0 | Config, widgets, formatting |

### Frontend (TypeScript/React)

**Framework**:
- Astro 5.16.16 (static site generator)
- React 19.2.4 (UI components)
- TypeScript 5 (type safety)

**UI Libraries**:
- Tailwind CSS 3 (styling)
- @tailwindcss/postcss 4.1.18 (PostCSS integration)
- clsx, tailwind-merge (className utilities)

**Visualization**:
- Leaflet 1.9.4 (maps)
- react-leaflet 5.0.0 (React Leaflet integration)
- Recharts 3.7.0 (charts)
- KaTeX 0.16.28 (math rendering)

**Other**:
- lucide-react 0.563.0 (icons)
- @tanstack/react-table 8.21.3 (tables)
- shiki 3.21.0 (syntax highlighting)
- remark-math, rehype-katex (math in markdown)

---

## Development Tools

### Code Quality

**Python**:
- Ruff (linting + formatting)
  - Line length: 100 characters
  - Target: Python 3.11
  - Rules: E, F, W, I, N, UP (ignore E501)

**Testing**:
- pytest 7.0+ (test framework)
- pytest-cov 4.0+ (coverage)
- pytest-mock 3.10+ (mocking)
- pytest-asyncio 0.21.0+ (async tests)
- coverage[toml] 7.0+ (coverage reporting)

**Type Checking**:
- Python type hints (not enforced by mypy/pyright yet)
- TypeScript 5 for frontend

### Documentation

- Jupytext 1.16.0+ (notebook ↔ script pairing)
- Markdown with math support (KaTeX)

---

## Configuration

### Python Project Structure (pyproject.toml)

**Project Metadata**:
```toml
[project]
name = "egg-n-bacon-housing"
version = "0.1.0"
requires-python = ">=3.11"
```

**Dev Dependencies** (managed via uv):
- jupyter, ipykernel, jupytext
- pytest, pytest-cov, pytest-mock, pytest-asyncio
- coverage, ruff

### Linting/Formatting Configuration

**Ruff** (`.py`):
- Line length: 100
- Target: py311
- Notebook imports: E402 allowed
- Stage file names: N999 allowed (e.g., `L0_collect.py`)

### Test Configuration

**Pytest** (`pyproject.toml`):
- Test paths: `tests/`
- Verbose output
- Short tracebacks
- Coverage on `scripts/core`
- HTML coverage in `htmlcov/`
- Markers: unit, integration, slow, api

---

## Data Storage

### File Formats

- **Parquet**: Primary data storage (compressed with snappy)
- **CSV**: Manual data input, export
- **JSON**: Metadata, webapp data, configuration

### Directory Structure

```
data/
├── manual/           # Manually downloaded data
│   └── csv/         # CSV input files
├── parquets/        # Processed parquet datasets
├── logs/            # Pipeline logs
└── metadata.json    # Dataset lineage tracking
```

---

## Deployment

### Frontend (GitHub Pages)

- **Static Site**: Built with Astro
- **Base URL**: Configured for GitHub Pages
- **Build Output**: `app/dist/` and `backend/dist/`

### Python Scripts

- **Local Execution**: Run with `uv run`
- **Notebooks**: Jupyter with Jupytext pairing

---

## Infrastructure

### External Services

| Service | Purpose | Environment Variable |
|---------|---------|---------------------|
| **OneMap API** | Singapore geocoding | `ONEMAP_EMAIL`, `ONEMAP_TOKEN` |
| **Google Maps** | Geocoding fallback | `GOOGLE_API_KEY` |
| **data.gov.sg** | HDB/URA transactions | None (public API) |
| **AWS S3** | Data storage (optional) | AWS credentials via boto3 |
| **Supabase** | Database (optional) | `SUPABASE_URL`, `SUPABASE_KEY` |

### API Rate Limiting

- OneMap: Configurable delay (default: 1 second)
- Google Maps: Timeout and retry handling
- Caching: TTL-based (24 hours default)

---

## Version Control

**Git Repository**:
- Main branch: `main`
- CI/CD: GitHub Actions
  - Test workflow: `pytest` with coverage
  - Deploy workflow: Build and deploy to GitHub Pages

---

## Summary

**Backend Stack**: Python 3.11+, pandas, geopandas, scikit-learn, xgboost, plotly
**Frontend Stack**: Astro, React 19, TypeScript, Tailwind CSS, Leaflet, Recharts
**Development**: uv, pytest, ruff, jupyter/jupytext
**Deployment**: GitHub Pages (static hosting)

This stack prioritizes:
- **Data processing speed** (pandas, pyarrow, uv)
- **Geospatial analysis** (geopandas, h3)
- **ML/AI capabilities** (scikit-learn, xgboost, langchain)
- **Interactive visualization** (plotly, react-leaflet, recharts)
- **Developer experience** (ruff, pytest, jupytext)
