# Pipeline Scripts

This directory contains scripts for running and managing the data processing pipeline.

## Scripts

### `run_pipeline.py`
Main entry point for running the complete L0-L3 data pipeline.

**Features:**
- Orchestrates all pipeline stages (L0 → L1 → L2 → L3)
- Configurable stage selection
- Progress tracking and error handling
- Comprehensive logging

**Usage:**
```bash
# Run complete pipeline
uv run python scripts/run_pipeline.py

# Run specific stages
uv run python scripts/run_pipeline.py --stages L0,L1,L2

# Skip caching
uv run python scripts/run_pipeline.py --no-cache
```

**Options:**
- `--stages`: Comma-separated list of stages to run (default: all)
- `--no-cache`: Disable caching and force recalculation
- `--verbose`: Enable detailed logging

### `analytics/` Directory
Analytics pipeline scripts for computing metrics, forecasts, and analysis results.

All analytics pipelines follow the naming convention: `*_pipeline.py`

#### Forecasting Pipelines

**`forecast_prices_pipeline.py`** - Forecast housing prices using Prophet
```bash
uv run python scripts/analytics/pipelines/forecast_prices_pipeline.py
```
- Generates 6-month and 1-year price forecasts by planning area
- Uses Facebook Prophet time-series models
- Outputs to `data/forecasts/hdb_price_forecasts.parquet`

**`forecast_yields_pipeline.py`** - Forecast rental yields
```bash
uv run python scripts/analytics/pipelines/forecast_yields_pipeline.py
```
- Forecasts rental yields for different planning areas
- Outputs to `data/forecasts/hdb_yield_forecasts.parquet`

#### Metrics Calculation Pipelines

**`calculate_l3_metrics_pipeline.py`** - Calculate L3 housing market metrics
```bash
uv run python scripts/analytics/pipelines/calculate_l3_metrics_pipeline.py
```
- Computes price growth, PSF, transaction volume, momentum
- Outputs to `data/parquets/L3/metrics_monthly.parquet`

**`calculate_affordability_pipeline.py`** - Affordability index calculation
```bash
uv run python scripts/analytics/pipelines/calculate_affordability_pipeline.py
```
- Calculates affordability ratios by planning area
- Mortgage payment analysis
- Outputs to `data/parquets/L3/affordability_by_pa.parquet`

**`calculate_income_estimates_pipeline.py`** - Household income estimation
```bash
uv run python scripts/analytics/pipelines/calculate_income_estimates_pipeline.py
```
- Estimates median household income by planning area
- Based on HDB loan eligibility data

**`calculate_coming_soon_pipeline.py`** - Upcoming launches metrics
```bash
uv run python scripts/analytics/pipelines/calculate_coming_soon_pipeline.py
```
- Calculates metrics for upcoming property launches

**`calculate_condo_amenities_pipeline.py`** - Condo amenity features
```bash
uv run python scripts/analytics/pipelines/calculate_condo_amenities_pipeline.py
```
- Computes amenity distance features for condos

#### Segmentation Pipelines

**`cluster_profiles_pipeline.py`** - Market cluster profiles
```bash
uv run python scripts/analytics/pipelines/cluster_profiles_pipeline.py
```
- Generates K-means cluster profiles for market segments
- Creates investment strategies per segment
- Outputs to `data/analysis/market_segmentation_2.0/`

### `create_l3_unified_dataset.py` (located at `scripts/`)
Creates the L3 unified housing dataset for analytics.

**Note:** This script is a convenience wrapper at `scripts/create_l3_unified_dataset.py` that imports from `scripts/data/create_l3_unified_dataset.py`.

**Features:**
- Loads data from preprocessed source
- Filters by date range
- Selects columns for VAR/ARIMAX modeling
- Saves to unified parquet

**Usage:**
```bash
# Create unified dataset
uv run python scripts/create_l3_unified_dataset.py
```

**Output:**
- `data/pipeline/L3/housing_unified.parquet` - Main unified dataset

## Pipeline Stages

### L0: Data Collection
- Download raw data from government sources
- Extract and format raw datasets
- **Location**: `core/stages/L0_collect.py`

### L1: Data Processing
- Clean and standardize transaction data
- Merge HDB, Condo, and EC data
- **Location**: `core/stages/L1_process.py`

### L2: Feature Engineering
- Geocode properties
- Calculate amenity distances
- Create spatial features
- **Location**: `core/stages/L2_features.py`, `core/stages/L2_rental.py`

### L3: Export & Analysis
- Create unified dataset
- Calculate metrics
- Generate summary tables
- **Location**: `core/stages/L3_export.py`

## Configuration

Pipeline behavior is controlled by `core/config.py`:

```python
# Feature flags
USE_CACHING = True
CACHE_DURATION_HOURS = 24
VERBOSE_LOGGING = True

# Paths
DATA_DIR = BASE_DIR / "data"
PIPELINE_DIR = DATA_DIR / "pipeline"
PARQUETS_DIR = PIPELINE_DIR
```

## Error Handling

The pipeline includes comprehensive error handling:
- Automatic retry for transient errors
- Graceful handling of missing data
- Detailed error logging
- Progress checkpointing

## Monitoring

Pipeline execution can be monitored through:
1. **Console logs**: Real-time progress updates
2. **Log files**: `data/logs/` directory with timestamps
3. **Metadata**: `data/metadata.json` tracks pipeline runs

## Best Practices

1. **Run from project root** - Always execute pipeline scripts from the project root directory
2. **Check dependencies** - Ensure all required data files exist before running
3. **Use caching** - Enable caching for faster development iterations
4. **Monitor logs** - Check log files for warnings and errors
5. **Validate outputs** - Inspect generated parquet files after runs

## Troubleshooting

**Issue: Pipeline fails at L0**
- Check internet connection for data downloads
- Verify API keys in `.env` file
- Ensure data directories have write permissions

**Issue: L2 geocoding fails**
- Check OneMap token is valid
- Verify geocoding quota not exceeded
- Refresh token with `refresh_onemap_token.py`

**Issue: L3 export fails**
- Ensure L2 features are computed
- Check disk space for output files
- Verify all required columns exist

## Related Documentation

- [Pipeline Documentation](../../docs/architecture.md)
- [L2 Pipeline Guide](../../docs/guides/l2-pipeline.md)
- [Configuration Reference](../../core/config.py)
