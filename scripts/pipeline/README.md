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
uv run python scripts/pipeline/run_pipeline.py

# Run specific stages
uv run python scripts/pipeline/run_pipeline.py --stages L0,L1,L2

# Skip caching
uv run python scripts/pipeline/run_pipeline.py --no-cache
```

**Options:**
- `--stages`: Comma-separated list of stages to run (default: all)
- `--no-cache`: Disable caching and force recalculation
- `--verbose`: Enable detailed logging

### `create_l3_unified_dataset.py` (located at `scripts/`)
Creates the comprehensive L3 unified housing dataset.

**Note:** This script is now located at `scripts/create_l3_unified_dataset.py` for convenient access from the project root. It imports the implementation from `scripts/dashboard/create_l3_unified_dataset.py`.

**Features:**
- Combines HDB, Condo, and EC transactions
- Adds geocoding and amenity features
- Includes planning areas and rental yields
- Generates precomputed summary tables

**Usage:**
```bash
# Create unified dataset
uv run python scripts/create_l3_unified_dataset.py
```

**Output:**
- `data/pipeline/L3/housing_unified.parquet` - Main unified dataset
- `data/pipeline/L3/market_summary.parquet` - Aggregated market statistics
- `data/pipeline/L3/tier_thresholds_evolution.parquet` - Tier thresholds over time
- `data/pipeline/L3/planning_area_metrics.parquet` - Planning area metrics
- `data/pipeline/L3/lease_decay_stats.parquet` - Lease decay statistics
- `data/pipeline/L3/rental_yield_top_combos.parquet` - Top rental yield combinations

## Pipeline Stages

### L0: Data Collection
- Download raw data from government sources
- Extract and format raw datasets
- **Location**: `core/pipeline/L0_collect.py`

### L1: Data Processing
- Clean and standardize transaction data
- Merge HDB, Condo, and EC data
- **Location**: `core/pipeline/L1_process.py`

### L2: Feature Engineering
- Geocode properties
- Calculate amenity distances
- Create spatial features
- **Location**: `core/pipeline/L2_features.py`, `core/pipeline/L2_rental.py`

### L3: Export & Analysis
- Create unified dataset
- Calculate metrics
- Generate summary tables
- **Location**: `core/pipeline/L3_export.py`

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
