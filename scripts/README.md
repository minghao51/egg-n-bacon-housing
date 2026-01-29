# Scripts Directory

Comprehensive collection of Python scripts for Singapore housing market analysis, data processing, and pipeline operations.

## 📁 Directory Structure

```
scripts/
├── analytics/              # Analytics and modeling scripts
│   ├── calculate/         # Metrics calculation
│   ├── forecast/          # Time-series forecasting
│   ├── segmentation/      # Market segmentation
│   └── analysis/          # In-depth analysis (organized by topic)
│       ├── spatial/       # Geospatial analysis
│       ├── amenity/       # Amenity impact
│       ├── market/        # Market trends
│       └── mrt/           # MRT proximity analysis
│
├── pipeline/              # Pipeline orchestration
│   ├── run_pipeline.py
│   └── create_l3_unified_dataset.py
│
├── data/                  # Data operations
│   ├── download/          # External data downloads
│   └── process/           # Data processing & transformation
│       ├── geocode/       # Geocoding operations
│       ├── amenities/     # Amenity data processing
│       └── planning_area/ # Geographic processing
│
└── utils/                 # Utility scripts
    ├── Validation
    ├── Progress monitoring
    └── Quality checks
```

## 🚀 Quick Start

### Run Pipeline
```bash
# Complete data pipeline
uv run python scripts/pipeline/run_pipeline.py

# Specific stages
uv run python scripts/pipeline/run_pipeline.py --stages L0,L1
```

### Calculate Metrics
```bash
# Market metrics
uv run python scripts/analytics/calculate/calculate_l3_metrics.py

# Affordability
uv run python scripts/analytics/calculate/calculate_affordability.py
```

### Create Analysis
```bash
# Spatial hotspots
uv run python scripts/analytics/analysis/spatial/analyze_spatial_hotspots.py

# Amenity impact
uv run python scripts/analytics/analysis/amenity/analyze_amenity_impact.py
```

### Generate Forecasts
```bash
# Price forecasts
uv run python scripts/analytics/forecast/forecast_prices.py

# Yield forecasts
uv run python scripts/analytics/forecast/forecast_yields.py
```

## 📊 Script Categories

### Analytics (36 scripts)
**Calculate Metrics** (5)
- L3 market metrics, affordability, income estimates, coming soon metrics, condo amenities

**Forecast** (2)
- Price forecasts, yield forecasts

**Segmentation** (3)
- Market segmentation, period segmentation, cluster profiles

**Analysis** (12)
- Spatial (3): Hotspots, autocorrelation, H3 clusters
- Amenity (2): Impact analysis, feature importance
- Market (4): Rental market, lease decay, policy impact, advanced segmentation
- MRT (3): Impact, heterogeneous effects, by property type

### Pipeline (2 scripts)
- Main pipeline orchestration
- L3 unified dataset creation

### Data Operations (12 scripts)
**Download** (4)
- Amenity data, phase 2 amenities, URA rental index, HDB rental data

**Processing** (8)
- Geocode (3): Address geocoding, batched, enhancement
- Amenities (3): Processing, parsing, grid creation
- Planning Area (2): Add to data, create crosswalk

### Utilities (4 scripts)
- Geocoding progress check
- URA data validation
- Anomaly detection
- Town leaderboards

## 📖 Usage Patterns

### Common Import Pattern
All scripts use consistent imports:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Config
```

### Standard CLI Interface
Scripts accept command-line arguments:

```bash
uv run python scripts/path/script.py --input file.csv --output results/
```

### Logging Configuration
Consistent logging across all scripts:

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

## 🔄 Data Flow

```
External APIs
    ↓
scripts/data/download/
    ↓
data/manual/, data/raw_data/
    ↓
scripts/data/process/
    ↓
data/pipeline/L0/, L1/, L2/
    ↓
scripts/analytics/
    ↓
data/analysis/, data/forecasts/
```

## 📚 Detailed Documentation

- **[Analytics](./analytics/README.md)** - Metrics, forecasting, segmentation, analysis
- **[Pipeline](./pipeline/README.md)** - Pipeline orchestration and L3 dataset creation
- **[Data Operations](./data/README.md)** - Download and processing scripts
- **[Utilities](./utils/README.md)** - Validation and monitoring tools

## 🛠️ Development Guidelines

### Adding New Scripts

1. **Choose appropriate directory** based on script purpose
2. **Follow naming conventions**: `verb_noun.py` (e.g., `calculate_metrics.py`)
3. **Include docstring** with usage examples
4. **Use argument parser** for CLI interface
5. **Add logging** for operations
6. **Update relevant README** with script details

### Code Style
- Follow PEP 8 guidelines
- Use type hints for function signatures
- Include error handling
- Add progress bars for long operations
- Validate inputs before processing

### Testing
- Test with sample data before full runs
- Validate outputs
- Check for edge cases
- Monitor performance

## ⚙️ Configuration

Script behavior controlled by:
- **Environment variables**: `.env` file
- **Config module**: `core/config.py`
- **Command-line arguments**: Script-specific
- **Feature flags**: Enable/disable functionality

## 🔍 Monitoring & Debugging

### Check Script Status
```bash
# Geocoding progress
uv run python scripts/utils/check_geocoding_progress.py

# Validate data
uv run python scripts/utils/validate_ura_data.py

# Detect anomalies
uv run python scripts/utils/detect_anomalies.py
```

### View Logs
```bash
# Recent logs
tail -f data/logs/*.log

# Search for errors
grep "ERROR" data/logs/*.log
```

### Performance Profiling
```bash
# Profile script execution
uv run python -m cProfile -o profile.stats scripts/path/script.py
```

## 📋 Requirements

### Core Dependencies
- `pandas` - Data manipulation
- `numpy` - Numerical operations
- `geopandas` - Spatial data
- `prophet` - Time-series forecasting
- `scikit-learn` - Machine learning

### API Access
- OneMap API (geocoding)
- Data.gov.sg API (amenities)
- URA API (rental index)

### System Requirements
- Python 3.11+
- 8GB RAM minimum (16GB recommended for large datasets)
- 10GB free disk space

## 🐛 Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure running from project root
cd /path/to/egg-n-bacon-housing
uv run python scripts/...
```

**API Failures**
```bash
# Refresh OneMap token
uv run python refresh_onemap_token.py
```

**Memory Issues**
```bash
# Process data in chunks
uv run python scripts/analytics/calculate/calculate_l3_metrics.py --batch-size 1000
```

## 📞 Support

For issues or questions:
1. Check script README files
2. Review logs in `data/logs/`
3. Consult main documentation
4. Check existing GitHub issues

## 📈 Script Usage Statistics

| Category | Scripts | Most Used |
|----------|---------|-----------|
| Calculate | 5 | calculate_l3_metrics.py |
| Forecast | 2 | forecast_prices.py |
| Segmentation | 3 | create_market_segmentation.py |
| Analysis | 12 | analyze_amenity_impact.py |
| Pipeline | 2 | run_pipeline.py |
| Data Download | 4 | download_amenity_data.py |
| Data Process | 8 | geocode_addresses.py |
| Utilities | 4 | check_geocoding_progress.py |

---

**Last Updated**: 2026-01-28
**Total Scripts**: 41
**Maintained By**: Data Team
