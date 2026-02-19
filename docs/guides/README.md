# Documentation Index

Comprehensive guides and documentation for the Egg-n-Bacon Housing project.

## 🚀 Quick Start Guides

| Guide | Description | For You If... |
|-------|-------------|---------------|
| **[Quick Start](./quick-start.md)** | Get up and running in 5 minutes | You're new to the project |
| **[External Data Setup](./external-data-setup.md)** | Download and configure external data sources | You need to set up data sources |
| **[L2 Pipeline](./l2-pipeline.md)** | Data processing pipeline guide | You want to understand data flow |

## 📚 Reference Guides

### Data Management

| Guide | Description |
|-------|-------------|
| **[Data Reference](./data-reference.md)** | Complete data schema and field definitions |
| **[MRT Features Guide](./mrt-features-guide.md)** | MRT proximity features and metrics |

### Architecture

| Document | Description |
|----------|-------------|
| **[Architecture](../architecture.md)** | System architecture and design decisions |

## 🛠️ Operational Guides

### Running the Pipeline

```bash
# Complete data pipeline
uv run python scripts/pipeline/run_pipeline.py --stage all

# Specific stages
uv run python scripts/pipeline/run_pipeline.py --stage L0
uv run python scripts/pipeline/run_pipeline.py --stage L1
uv run python scripts/pipeline/run_pipeline.py --stage L2
uv run python scripts/pipeline/run_pipeline.py --stage L3
uv run python scripts/pipeline/run_pipeline.py --stage L4
uv run python scripts/pipeline/run_pipeline.py --stage L5
```

### L4 Analysis Pipeline

```bash
# Run full L4 (EDA + analysis scripts)
uv run python scripts/core/stages/L4_analysis.py

# Run EDA only
uv run python scripts/analytics/analysis/market/analyze_investment_eda.py
```

See **[L4 Analysis Pipeline](./l4-analysis-pipeline.md)** for details.

### Data Refresh

```bash
# Check and refresh external data
uv run python scripts/data/download/refresh_external_data.py --dry-run
uv run python scripts/data/download/refresh_external_data.py

# Refresh specific categories
uv run python scripts/data/download/refresh_external_data.py --amenities --ura
```

### Geocoding

```bash
# Sequential geocoding (slower, safer)
uv run python scripts/data/process/geocode/geocode_addresses.py

# Parallel geocoding (faster)
uv run python scripts/data/process/geocode/geocode_addresses.py --parallel --workers 10
```

## 📊 Analytics

### Running Analytics Scripts

```bash
# Calculate L3 metrics
uv run python scripts/analytics/calculate/calculate_l3_metrics.py

# Analyze MRT impact
uv run python scripts/analytics/analysis/mrt/analyze_mrt_impact.py

# Market segmentation
uv run python scripts/analytics/segmentation/create_market_segmentation.py
```

### Available Analyses

| Category | Scripts | Location |
|----------|---------|----------|
| **Market Trends** | Rental market, lease decay, policy impact | `scripts/analytics/analysis/market/` |
| **Spatial Analysis** | Hotspots, autocorrelation, H3 clusters | `scripts/analytics/analysis/spatial/` |
| **Amenity Impact** | Feature importance, amenity effects | `scripts/analytics/analysis/amenity/` |
| **MRT Analysis** | Impact, heterogeneous effects, property type comparison | `scripts/analytics/analysis/mrt/` |
| **Forecasting** | Price forecasts, yield forecasts | `scripts/analytics/forecast/` |

## 🔧 Utilities

### Validation and Monitoring

```bash
# Validate URA data
uv run python scripts/utils/validate_ura_data.py

# Check geocoding progress
uv run python scripts/utils/check_geocoding_progress.py

# Detect anomalies
uv run python scripts/utils/detect_anomalies.py

# Generate town leaderboards
uv run python scripts/utils/town_leaderboard.py
```

### Token Management

```bash
# Refresh OneMap API token
uv run python scripts/utils/refresh_onemap_token.py
```

## 📁 Directory Structure

```
egg-n-bacon-housing/
├── docs/                      # Documentation
│   ├── guides/               # This directory
│   ├── analytics/            # Analysis documentation
│   └── architecture.md       # System architecture
├── scripts/                   # Processing and analysis scripts
│   ├── analytics/            # Analysis scripts
│   ├── data/                 # Data download/processing
│   ├── pipeline/             # Pipeline orchestration
│   └── utils/                # Utility scripts
├── core/                       # Core modules
│   ├── config.py             # Configuration
│   ├── pipeline/             # Pipeline modules (L0-L4)
│   └── ...
└── data/                      # Data directory
    ├── manual/               # Manually downloaded data
    ├── raw_data/             # Raw downloaded data
    ├── logs/                 # Pipeline logs
    └── parquets/             # Processed parquet files
        ├── L0/               # Raw data
        ├── L1/               # Processed transactions
        ├── L2/               # Features & geocoding
        └── L3/               # Unified dataset
```

## 🔍 Quick Reference

### Configuration

All configuration is centralized in `core/config.py`:

```python
from scripts.core.config import Config

# Access paths
data_dir = Config.DATA_DIR
parquets_dir = Config.PARQUETS_DIR

# Access API keys
api_key = Config.GOOGLE_API_KEY

# Validate configuration
Config.validate()
```

### Common Issues

**Problem:** Import errors
```bash
# Solution: Always use uv run
uv run python scripts/your_script.py
```

**Problem:** API failures
```bash
# Solution: Refresh OneMap token
uv run python scripts/utils/refresh_onemap_token.py
```

**Problem:** Missing data files
```bash
# Solution: Run refresh pipeline
uv run python scripts/data/download/refresh_external_data.py
```

**Problem:** Pipeline errors
```bash
# Solution: Check logs
tail -f data/logs/*.log
```

## 📖 Additional Resources

- **[Project README](../../README.md)** - Project overview and goals
- **[Scripts README](../../scripts/README.md)** - Complete scripts documentation
- **[Data Operations](../../scripts/data/README.md)** - Data download and processing
- **[Analytics Scripts](../../scripts/analytics/README.md)** - Analysis scripts guide

## 🆘 Getting Help

1. **Check documentation** - Start with the relevant guide above
2. **Review logs** - Check `data/logs/` for error messages
3. **Validate data** - Run validation scripts to check data integrity
4. **Check issues** - Review GitHub issues for known problems

---

**Last Updated:** 2026-01-28
**Maintained By:** Data Team
