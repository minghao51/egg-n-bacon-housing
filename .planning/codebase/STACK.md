# Technology Stack

**Generated**: 2026-02-28

## Core Languages

### Python
- **Version**: 3.11+ (minimum requirement)
- **Package Manager**: uv (fast Python package manager)
- **Virtual Environment**: `.venv/` (managed by uv)

### TypeScript
- **Version**: Latest (managed by Astro)
- **Runtime**: Node.js (for frontend build process)

## Python Packages

### Data Processing
- **pandas** - DataFrame manipulation and analysis
- **numpy** - Numerical computing
- **geopandas** - Spatial data operations
- **pyarrow** - Parquet file format support

### Machine Learning & Analytics
- **scikit-learn** - Machine learning algorithms
- **xgboost** - Gradient boosting models
- **statsmodels** - Statistical analysis
- **scipy** - Scientific computing
- **langchain** - LLM integration for analytics agents

### Spatial Analysis
- **h3** - Uber's hexagonal spatial indexing
- **shapely** - Geometric operations
- **libpysal** - Spatial econometrics
- **spreg** - Spatial regression models
- **esda** - Spatial autocorrelation statistics

### Data Visualization
- **matplotlib** - Plotting and charts
- **seaborn** - Statistical visualizations
- **plotly** - Interactive plots

### API & Cloud
- **boto3** - AWS SDK for Python
- **supabase** - Database and authentication client
- **requests** - HTTP client
- **httpx** - Async HTTP client

### Web Scraping
- **beautifulsoup4** - HTML parsing
- **jina-reader** - AI-powered web scraping

### Development Tools
- **pytest** - Testing framework
- **pytest-cov** - Coverage reporting
- **ruff** - Linting and formatting (configured in pyproject.toml)
- **ipykernel** - Jupyter notebook support
- **jupytext** - Notebook ↔ Python script pairing

## Frontend Stack

### Framework
- **Astro** 5.16.16 - Modern static site generator
  - File-based routing
  - Content collections
  - Build optimization

### UI Library
- **React** 19.2.4 - Component framework
- **React DOM** 19.2.4 - DOM rendering
- **TypeScript** - Type-safe React components

### Styling
- **Tailwind CSS** - Utility-first CSS framework
- **Leaflet** - Interactive maps
- **Recharts** - Chart library for data visualization

### Development
- **Playwright** - E2E testing framework
- **Vite** - Build tool (via Astro)
- **TypeScript ESLint** - Linting for TypeScript

## Data Formats

### Primary Storage
- **Parquet** (.parquet) - Columnar storage format
  - Efficient compression
  - Fast query performance
  - Schema preservation
  - Used for all processed datasets

### Metadata
- **JSON** (.json) - Configuration, metadata, API responses
- **TOML** (pyproject.toml) - Python project configuration

### Frontend Data
- **JSON** - Export format for webapp consumption

## Development Tools

### Code Quality
- **Ruff** (Python)
  - Linter: `uv run ruff check .`
  - Formatter: `uv run ruff format .`
  - Configuration: `pyproject.toml`
  - Line length: 100 characters

- **Biome/ESLint** (TypeScript)
  - Located in `app/`
  - Configuration for TypeScript/React

### Version Control
- **Git** - Source code control
- **GitHub** - Hosting, CI/CD, issue tracking

### Testing
- **pytest** - Python unit/integration tests
- **Playwright** - Frontend E2E tests
- **Coverage** - `pytest-cov` for test coverage reports

## Deployment

### Frontend
- **GitHub Pages** - Static site hosting
- **Build Output**: `app/dist/`
- **Deployment**: GitHub Actions workflow

### Backend
- **None** - Python scripts run locally or in CI
- **Data**: Generated locally, committed to repo or stored in data/

## Environment Configuration

### Environment Variables
- **File**: `.env` (from `.env.example`)
- **Loading**: `python-dotenv` in `scripts/core/config.py`
- **Required Keys**:
  - `ONEMAP_EMAIL` - Singapore geocoding API
  - `GOOGLE_API_KEY` - Google Maps geocoding fallback
  - `AWS_*` - Optional AWS credentials
  - `SUPABASE_*` - Optional Supabase credentials

### Configuration Management
- **Central Config**: `scripts/core/config.py`
- **Validation**: `Config.validate()` method
- **Feature Flags**: `USE_CACHING`, `VERBOSE_LOGGING`

## Jupyter Stack

### Notebooks
- **Jupyter** - Interactive notebook environment
- **Jupytext** - Notebook ↔ Python script pairing
  - Format: `.ipynb` + `.py` (paired)
  - Cell markers: `#%%`
  - Sync: `jupytext --sync notebook.ipynb`

### Notebook Organization
- **Location**: `notebooks/`
- **Levels**:
  - `L0_*` - Data collection notebooks
  - `L1_*` - Data processing notebooks
  - `L2_*` - Feature engineering notebooks
  - `exploration/` - Experimental analysis

## CI/CD

### GitHub Actions
- **Python Tests**: `pytest` with coverage
- **Linting**: `ruff check`
- **E2E Tests**: Playwright
- **Deployment**: Auto-deploy to GitHub Pages

## Summary

**Primary Language**: Python 3.11+
**Frontend**: Astro + React + TypeScript
**Data**: Parquet + JSON
**Testing**: pytest + Playwright
**Package Manager**: uv (Python), npm (Node)
**Deployment**: GitHub Pages
