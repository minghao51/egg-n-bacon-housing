# Egg-n-Bacon-Housing: External Integrations

## Overview

This document catalogs all external services, APIs, databases, and third-party integrations used in the egg-n-bacon-housing project.

---

## Data Sources

### Government APIs

#### data.gov.sg (Open Data)

**Purpose**: Primary source for Singapore housing transaction data

**Endpoints Used**:
- HDB resale flat prices (CSV downloads)
- URA private property transactions
- Rental index data

**Authentication**: None required (public API)

**Rate Limits**: Documented in API response headers

**Usage in Code**:
- `scripts/core/stages/L0_collect.py` - `fetch_datagovsg_dataset()`
- `scripts/data/download/download_datagov_datasets.py`

**Data Retrieved**:
- HDB resale transactions (2017-present)
- Private property transactions (condo, EC)
- Rental market indices

#### OneMap API (Singapore Land Authority)

**Purpose**: Geocoding addresses to coordinates, reverse geocoding

**Endpoints**:
- Search: `https://www.onemap.gov.sg/api/common/elastic/search`
- Reverse geocode: `https://www.onemap.gov.sg/api/public/revgeocode`

**Authentication**:
- Email-based token system
- Environment variables: `ONEMAP_EMAIL`, `ONEMAP_TOKEN`

**Rate Limits**:
- Configurable delay (default: 1 second between calls)
- Token expiry: ~3 days (auto-refresh)

**Usage in Code**:
- `scripts/core/geocoding.py` - `fetch_data()` with caching
- `scripts/utils/refresh_onemap_token.py` - Token refresh utility

**Error Handling**:
- Automatic token refresh on 401/403
- Fallback to Google Maps API

#### Google Maps Geocoding API

**Purpose**: Fallback geocoding when OneMap fails

**Endpoint**: `https://maps.googleapis.com/maps/api/geocode/json`

**Authentication**:
- API key via environment variable: `GOOGLE_API_KEY`

**Rate Limits**:
- Quota-based (Google Cloud Platform)
- Configurable timeout

**Usage in Code**:
- `scripts/core/geocoding.py` - Fallback in `fetch_data()`
- `scripts/data/process/geocode/enhance_geocoding.py`

**Cost**: Free tier with daily quota; pay-per-use beyond

---

## Third-Party Libraries

### Geospatial

#### H3 (Uber)

**Version**: 4.1.0b2 (beta)

**Purpose**: Hexagonal hierarchical spatial indexing

**Usage**:
- `scripts/core/stages/spatial_h3.py` - H3 grid generation
- `scripts/analytics/analysis/spatial/analyze_h3_clusters.py`

**Capabilities**:
- Convert lat/lon to H3 indexes
- Spatial aggregation
- Neighbor finding

#### GeoPandas + PyProj

**Purpose**: Geospatial data operations, coordinate transformations

**Usage**:
- CRS transformations (EPSG:4326 to EPSG:3414)
- Spatial joins
- Distance calculations

**Coordinate Reference Systems**:
- EPSG:4326 (WGS84 - GPS coordinates)
- EPSG:3414 (Singapore SVY21)

### Machine Learning

#### scikit-learn

**Purpose**: General ML algorithms

**Usage**:
- Clustering (KMeans, DBSCAN)
- Dimensionality reduction (PCA)
- Preprocessing (StandardScaler)

#### XGBoost

**Version**: >=3.1.3

**Purpose**: Gradient boosting for price prediction

**Usage**:
- `scripts/analytics/pipelines/forecast_prices_pipeline.py`
- Feature importance analysis

#### Prophet (Meta)

**Version**: >=1.2.1

**Purpose**: Time series forecasting

**Usage**:
- `scripts/analytics/pipelines/forecast_prices_pipeline.py`
- Price trend forecasting

### Spatial Statistics

#### PySAL (Python Spatial Analysis Library)

**Components**:
- `libpysal>=4.6.0` - Core spatial weights
- `esda>=1.5.0` - Exploratory spatial data analysis

**Purpose**: Spatial autocorrelation analysis

**Usage**:
- `scripts/analytics/analysis/spatial/analyze_spatial_autocorrelation.py`
- Moran's I, Local Indicators of Spatial Association (LISA)

---

## AI/LLM Integration

### Google Gemini (via LangChain)

**Version**: langchain-google-genai==2.0.0

**Purpose**: AI-powered analysis (optional feature)

**Authentication**:
- API key via `GOOGLE_API_KEY`

**Usage**:
- Document analysis (langchain)
- Experimental features (langchain-experimental)

**Note**: Core pipeline does NOT require LLM access

---

## Cloud Services

### AWS S3 (via Boto3)

**Purpose**: Optional cloud storage for parquet files

**Authentication**:
- AWS credentials via environment variables or `~/.aws/credentials`
- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`

**Usage**:
- Uploading processed data
- Cross-region data sharing

**Buckets**:
- Not hardcoded (configurable via environment)

### Supabase

**Purpose**: Optional database backend

**Authentication**:
- Environment variables: `SUPABASE_URL`, `SUPABASE_KEY`

**Usage**:
- Alternative to parquet files for data storage
- Real-time data updates (experimental)

**Note**: Currently unused; parquet files are primary storage

---

## Web Application Integrations

### GitHub Pages

**Purpose**: Static site hosting

**Configuration**:
- Base URL: Set in `app/astro.config.mjs`
- Build command: `npm run build`
- Output directory: `app/dist/`

**Deployment**:
- GitHub Actions workflow: `.github/workflows/deploy-app.yml`

### Map Tiles

**Source**: OpenStreetMap (via Leaflet)

**Purpose**: Base layer for interactive maps

**Usage**:
- `app/src/components/dashboard/PriceMap.tsx`
- No API key required

---

## Development Tools

### Jupytext

**Purpose**: Notebook ↔ script pairing for version control

**Configuration**: `jupytext.toml`

**Benefits**:
- Clean git diffs on `.py` files
- IDE support in VS Code
- Interactive execution in Jupyter

**Usage**:
- All notebooks have paired `.py` files
- Sync command: `uv run jupytext --sync notebook.ipynb`

---

## Authentication & Security

### Environment Variables

**Required** (for full pipeline):
```bash
ONEMAP_EMAIL=your@email.com
ONEMAP_TOKEN=auto-generated
GOOGLE_API_KEY=your-google-api-key
```

**Optional**:
```bash
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_REGION=us-east-1
SUPABASE_URL=xxx
SUPABASE_KEY=xxx
```

**Configuration**:
- Managed via `.env` file (not in git)
- Loaded via `python-dotenv` in `scripts/core/config.py`

### Token Management

**OneMap Token**:
- Auto-generated from email
- Validity: ~3 days
- Auto-refresh on expiry
- Cached in `data/logs/`

---

## Error Handling & Resilience

### API Failures

**OneMap**:
- Automatic retry with exponential backoff
- Fallback to Google Maps
- Failed addresses logged to `data/logs/geocoding_failed.csv`

**Google Maps**:
- Timeout handling (configurable)
- Quota management (stop before hitting limit)

### Data Validation

**Crosswalk Files**:
- Planning area mapping validated
- Town names checked against known list
- Manual override capability

**Geocoding Results**:
- Confidence threshold filtering
- Singapore bounds checking
- Duplicate detection and removal

---

## Summary

**Primary Data Sources**: data.gov.sg (HDB/URA), OneMap (geocoding)
**Fallback Services**: Google Maps Geocoding API
**ML Libraries**: scikit-learn, XGBoost, Prophet
**Spatial Libraries**: H3, GeoPandas, PySAL
**Cloud**: AWS S3 (optional), Supabase (optional)
**Deployment**: GitHub Pages
**Authentication**: Environment variables via .env

All integrations are designed with:
- Fallback mechanisms (OneMap → Google)
- Rate limiting and caching
- Comprehensive error handling
- No hard dependencies on paid services (free tier sufficient)
