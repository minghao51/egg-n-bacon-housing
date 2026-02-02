# Architecture

**Analysis Date:** 2026-02-02

## Pattern Overview

**Overall:** Layered Data Pipeline with Multi-Tier Analysis

**Key Characteristics:**
- Sequential pipeline architecture with clear data flow from L0 to L5
- Modular design with separation of concerns between data processing and analysis
- Event-driven dashboard applications with real-time data updates
- Multi-paradigm approach combining ETL, ML, and AI-powered analytics
- Hybrid Python/JavaScript stack with Streamlit UI components

## Layers

**L0: Data Collection Layer:**
- Purpose: Raw data acquisition from government APIs and external sources
- Location: `scripts/core/stages/L0_collect.py`, `scripts/data/download/`
- Contains: API clients, data scrapers, download scripts
- Depends on: OneMap API, data.gov.sg, external datasets
- Used by: L1 processing pipeline

**L1: Data Processing Layer:**
- Purpose: Data cleaning, validation, and geocoding
- Location: `scripts/core/stages/L1_process.py`, `scripts/core/geocoding.py`
- Contains: Transaction processing, address geocoding, data validation
- Depends on: L0 outputs, pandas, geocoding APIs
- Used by: L2 feature engineering

**L2: Feature Engineering Layer:**
- Purpose: Feature creation and spatial analysis
- Location: `scripts/core/stages/L2_features.py`, `scripts/core/stages/L2_rental.py`
- Contains: H3 grid processing, amenity distance calculations, rental yield features
- Depends on: L1 outputs, geopandas, spatial libraries
- Used by: L3 export and analysis

**L3: Export Layer:**
- Purpose: Unified dataset creation and analysis preparation
- Location: `scripts/core/stages/L3_export.py`
- Contains: Dataset consolidation, summary statistics, market segmentation
- Depends on: L2 outputs, pandas, analysis modules
- Used by: L4 analysis, L5 metrics, dashboard apps

**L4: Analysis Layer:**
- Purpose: Advanced analytics and ML model preparation
- Location: `scripts/core/stages/L4_analysis.py`, `scripts/analytics/`
- Contains: Market analysis, feature importance, trend analysis
- Depends on: L3 outputs, ML libraries, statistical packages
- Used by: Dashboard applications, reporting

**L5: Metrics Layer:**
- Purpose: Planning area-level metrics calculation
- Location: `scripts/core/stages/L5_metrics.py`
- Contains: Area-level aggregations, performance metrics
- Depends on: L3 outputs, geographic data
- Used by: Dashboard applications, data exports

**Web Application Layer:**
- Purpose: Interactive data visualization and exploration
- Location: `apps/`, `scripts/dashboard/`
- Contains: Streamlit dashboards, UI components, webapp data preparation
- Depends on: L3/L5 outputs, streamlit, plotly
- Used by: End users, stakeholders

## Data Flow

**Primary Data Pipeline:**
1. L0: Collect URA/HDB transaction data, external datasets, and geographic information
2. L1: Process transactions, clean data, geocode addresses using OneMap API
3. L2: Engineer features including spatial amenities, H3 grids, rental yields, and school distances
4. L3: Create unified dataset with all features, generate summary statistics and market segments
5. L4: Perform advanced analysis, calculate feature importance, create ML-ready datasets
6. L5: Calculate planning area-level metrics for geographic analysis
7. Webapp: Prepare lightweight JSON exports for dashboard consumption

**State Management:**
- Data persistence through parquet files in `data/pipeline/` directory
- File-based caching for API responses in `data/cache/`
- Metadata tracking in `data/metadata.json`
- Temporary storage in `data/archive/` for historical data

## Key Abstractions

**PipelineStage:**
- Purpose: Abstract base class for data processing stages
- Examples: `L0_collect.py`, `L1_process.py`, `L2_features.py`
- Pattern: Template method with common setup/teardown

**DataPipeline:**
- Purpose: Orchestration of multiple processing stages
- Examples: `scripts/run_pipeline.py`, `L3_export.py`
- Pattern: Command pattern with parameterized execution

**GeocodingService:**
- Purpose: Address-to-coordinate conversion with caching
- Examples: `scripts/core/geocoding.py`
- Pattern: Adapter pattern for OneMap API integration

**FeatureEngine:**
- Purpose: Spatial and temporal feature calculation
- Examples: `scripts/core/stages/L2_features.py`, feature_helpers.py
- Pattern: Strategy pattern with pluggable feature calculators

**DataLoader:**
- Purpose: Unified data loading with automatic caching
- Examples: `scripts/core/data_loader.py`
- Pattern: Repository pattern with lazy loading

## Entry Points

**Pipeline Runner:**
- Location: `scripts/run_pipeline.py`
- Triggers: Command line arguments (`--stage L0`, `--stage all`, etc.)
- Responsibilities: Orchestrates entire data pipeline stages

**Market Overview Dashboard:**
- Location: `apps/1_market_overview.py`
- Triggers: Streamlit web server
- Responsibilities: Displays market statistics and trends with L3 features

**Price Map Dashboard:**
- Location: `apps/2_price_map.py`
- Triggers: Streamlit web server
- Responsibilities: Interactive price mapping with heatmap and scatter views

**Trends Analytics Dashboard:**
- Location: `apps/3_trends_analytics.py`
- Triggers: Streamlit web server
- Responsibilities: Time-series analysis and trend visualization

**Main Dashboard:**
- Location: `apps/dashboard.py`
- Triggers: Streamlit web server
- Responsibilities: Multi-page application entry point with navigation

## Error Handling

**Strategy:** Layered error handling with graceful degradation

**Patterns:**
- Retry mechanism for API calls with exponential backoff
- Failed address logging and manual retry workflows
- Data validation with schema enforcement at each pipeline stage
- Exception handling with context-specific error messages
- Cache fallback for failed API responses

## Cross-Cutting Concerns

**Logging:**
- Structured logging with timestamps and stages
- Different log levels for development and production
- File-based logging with rotation capabilities

**Validation:**
- Data schema validation at each pipeline stage
- Input parameter validation for configuration
- Output quality checks and anomaly detection

**Authentication:**
- API key management through environment variables
- Secure credential handling without hardcoding
- Rate limit awareness and respectful API usage

---

*Architecture analysis: 2026-02-02*
