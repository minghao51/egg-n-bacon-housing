# Data Operations Scripts

This directory contains scripts for downloading and processing external data sources.

## 🚀 Quick Start

**Automated Data Refresh:**
```bash
# Check what data is missing
uv run python scripts/data/download/refresh_external_data.py --dry-run

# Download all missing automated data
uv run python scripts/data/download/refresh_external_data.py
```

**Manual Setup Required:** See [External Data Setup Guide](../../../docs/guides/external-data-setup.md) for complete setup instructions including manual downloads.

## Structure

### `download/`
Scripts for downloading data from external APIs and sources.

#### Scripts

- **download_datagov_datasets.py** - Unified amenity data downloader (Phase 1 & 2)
- **download_ura_rental_index.py** - Download URA rental index data
- **download_hdb_rental_data.py** - Download HDB rental transactions
- **refresh_external_data.py** - 🆕 Unified refresh pipeline for all automated downloads

**Usage:**
```bash
# Download amenity datasets (all phases)
uv run python scripts/data/download/download_datagov_datasets.py --phase all

# Download specific phase
uv run python scripts/data/download/download_datagov_datasets.py --phase 2

# Download rental index
uv run python scripts/data/download/download_ura_rental_index.py

# Refresh all automated data (recommended)
uv run python scripts/data/download/refresh_external_data.py
```

**Data Sources:**
- Data.gov.sg API (amenities, rental data)
- URA (Urban Redevelopment Authority) rental index
- HDB (Housing & Development Board) rental data

**Output:**
- Downloaded files saved to `data/raw/external/` 
- Processed data saved to `data/pipeline/L1/` and `data/pipeline/L2/`

### `process/`
Scripts for processing and transforming raw data into analysis-ready formats.

#### `process/geocode/`
Geocoding and address processing scripts.

- **geocode_addresses.py** - 🆕 Unified geocoding (sequential + parallel modes)
- **enhance_geocoding.py** - Improve existing geocoding with fuzzy matching

**Usage:**
```bash
# Sequential geocoding (slower, safer)
uv run python scripts/data/process/geocode/geocode_addresses.py

# Parallel geocoding (faster, 3-5x speedup)
uv run python scripts/data/process/geocode/geocode_addresses.py --parallel

# Specify workers
uv run python scripts/data/process/geocode/geocode_addresses.py --parallel --workers 10
```

**Requirements:**
- Valid OneMap API credentials in `.env`
- Token refresh with `refresh_onemap_token.py`

#### `process/amenities/`
Amenity data processing scripts.

- **process_amenities.py** - Process raw amenity geojson files
- **parse_amenities_v2.py** - Enhanced amenity parsing with categorization
- **quick_amenity_grid.py** - Create amenity proximity grids

**Usage:**
```bash
# Process amenities
uv run python scripts/data/process/amenities/process_amenities.py

# Parse amenities
uv run python scripts/data/process/amenities/parse_amenities_v2.py
```

**Output:**
- Processed amenities saved to `data/manual/geojsons/`
- Amenity features in `data/pipeline/L2/`

#### `process/planning_area/`
Planning area and geographic boundary processing.

- **add_planning_area_to_data.py** - Add planning areas to property data
- **create_planning_area_crosswalk.py** - Create planning area mapping tables

**Usage:**
```bash
# Add planning areas
uv run python scripts/data/process/planning_area/add_planning_area_to_data.py

# Create crosswalk
uv run python scripts/data/process/planning_area/create_planning_area_crosswalk.py
```

**Output:**
- Planning area features added to transaction data
- Crosswalk tables saved to `data/manual/crosswalks/`

## Common Patterns

### API Configuration
All download scripts use environment variables for API keys:

```python
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')
```

### Error Handling
Robust error handling for network issues:

```python
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def download_with_retry(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response
```

### Progress Tracking
Use `tqdm` for long-running operations:

```python
from tqdm import tqdm

for item in tqdm(items, desc="Processing"):
    process_item(item)
```

## Data Flow

```
External APIs
    ↓
download/
    ↓
data/raw/
    ↓
process/
    ↓
data/pipeline/L0/, L1/, L2/
```

## Dependencies

### Download Scripts
- `requests` - HTTP client
- `beautifulsoup4` - HTML parsing
- `pandas` - Data manipulation

### Processing Scripts
- `geopandas` - Spatial data processing
- `shapely` - Geometric operations
- `h3` - H3 grid operations
- `fuzzywuzzy` - String matching

## File Formats

### Input Formats
- **CSV** - Transaction data, reference tables
- **GeoJSON** - Geographic boundaries, amenities
- **JSON** - API responses

### Output Formats
- **Parquet** - Optimized columnar storage (primary)
- **GeoJSON** - Geographic data
- **CSV** - Human-readable exports

## Scheduling

Recommended automation schedules:

| Script | Frequency | Timing |
|--------|-----------|--------|
| download_hdb_rental_data | Monthly | First week of month |
| download_ura_rental_index | Quarterly | Quarter start |
| download_amenity_data | As needed | When data updates |
| geocode_addresses | One-time | Initial setup |
| process_amenities | As needed | When amenity data updates |

## Monitoring

Track data operations with:
1. **Log files**: Check `data/logs/` for execution logs
2. **File timestamps**: Verify recent downloads
3. **Data validation**: Use `scripts/utils/validate_*.py` scripts
4. **Error alerts**: Monitor for API rate limits

## Troubleshooting

### Download Failures
- Check API credentials in `.env`
- Verify API rate limits not exceeded
- Check network connectivity
- Review API documentation for changes

### Geocoding Errors
- Refresh OneMap token: `uv run python refresh_onemap_token.py`
- Check API quota: OneMap has daily limits
- Verify address formats match expected patterns
- Use batched version for large datasets

### Processing Errors
- Validate input data formats
- Check for missing required columns
- Verify coordinate systems (EPSG:4326)
- Ensure sufficient disk space

## Best Practices

1. **API Rate Limiting**: Always respect API rate limits
2. **Data Validation**: Validate downloaded data before use
3. **Backup Raw Data**: Keep original downloads in `data/manual/`
4. **Incremental Processing**: Process data in chunks for large datasets
5. **Error Logging**: Log all errors for troubleshooting
6. **Documentation**: Document data sources and update schedules

## Related Documentation

- [Architecture Documentation](../../docs/architecture.md)
- [Data Reference](../../docs/guides/data-reference.md)
- [Configuration Reference](../../core/config.py)
