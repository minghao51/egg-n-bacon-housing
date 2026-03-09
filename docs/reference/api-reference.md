# API Reference

**Last Updated:** 2026-02-28

---

## Overview

This reference documents the core utility APIs available in `scripts/core/`. These modules provide shared functionality for data loading, configuration, geocoding, and metrics calculation.

---

## Table of Contents

1. [Configuration API (`config.py`)](#configuration-api-configpy)
2. [Data Helpers API (`data_helpers.py`)](#data-helpers-api-data_helperspy)
3. [Geocoding API (`geocoding.py`)](#geocoding-api-geocodingpy)
4. [Metrics API (`metrics.py`)](#metrics-api-metricspy)
5. [Cache API (`cache.py`)](#cache-api-cachepy)
6. [MRT Distance API (`mrt_distance.py`)](#mrt-distance-api-mrt_distancepy)

---

## Configuration API (`config.py`)

**Module:** `scripts.core.config`

Centralized configuration management for all project settings.

---

### Config Class

#### Class Properties

```python
from scripts.core.config import Config

# Path Configuration
Config.BASE_DIR              # Path: Project root directory
Config.DATA_DIR              # Path: data/
Config.PIPELINE_DIR          # Path: data/pipeline/ (alias for PARQUETS_DIR)
Config.PARQUETS_DIR          # Path: data/pipeline/
Config.MANUAL_DIR            # Path: data/manual/
Config.ANALYTICS_DIR         # Path: data/analytics/

# Pipeline Stage Directories
Config.L0_DIR                # Path: data/pipeline/L0/
Config.L1_DIR                # Path: data/pipeline/L1/
Config.L2_DIR                # Path: data/pipeline/L2/
Config.L3_DIR                # Path: data/pipeline/L3/

# Manual Data Subdirectories
Config.CSV_DIR               # Path: data/manual/csv/
Config.GEOJSON_DIR           # Path: data/manual/geojsons/
Config.CROSSWALK_DIR         # Path: data/manual/crosswalks/
Config.URA_DIR               # Path: data/manual/csv/ura/
Config.HDB_RESALE_DIR        # Path: data/manual/csv/ResaleFlatPrices/

# API Keys (from .env file)
Config.ONEMAP_EMAIL          # str: OneMap API email
Config.ONEMAP_PASSWORD       # str: OneMap API password (optional)
Config.GOOGLE_API_KEY        # str: Google Maps API key
Config.SUPABASE_URL          # str: Supabase URL (optional)
Config.SUPABASE_KEY          # str: Supabase key (optional)
Config.JINA_AI              # str: Jina AI API key (optional)

# Parquet Settings
Config.PARQUET_COMPRESSION   # str: "snappy" (compression codec)
Config.PARQUET_INDEX         # bool: False (include index in files)
Config.PARQUET_ENGINE        # str: "pyarrow" (parquet engine)

# Feature Flags
Config.USE_CACHING          # bool: True (enable caching)
Config.CACHE_DIR            # Path: data/cache/
Config.CACHE_DURATION_HOURS # int: 24 (default cache TTL)
Config.VERBOSE_LOGGING      # bool: True (verbose log output)

# Geocoding Settings
Config.GEOCODING_MAX_WORKERS     # int: 5 (parallel workers)
Config.GEOCODING_API_DELAY       # float: 1.2 (delay between calls)
Config.GEOCODING_TIMEOUT         # int: 30 (request timeout)
```

#### Methods

##### `Config.validate()`

Validate that required configuration is present and directories exist.

```python
Config.validate() -> None
```

**Raises:**
- `ValueError`: If required API keys missing or directories don't exist

**Side Effects:**
- Creates all required directories if they don't exist

**Example:**
```python
from scripts.core.config import Config

try:
    Config.validate()
    print("Configuration valid")
except ValueError as e:
    print(f"Configuration error: {e}")
```

---

##### `Config.print_config()`

Print current configuration (safe for logging).

```python
Config.print_config() -> None
```

**Example:**
```python
from scripts.core.config import Config

Config.print_config()
# Output:
# BASE_DIR: /path/to/project
# DATA_DIR: /path/to/project/data
# PIPELINE_DIR: /path/to/project/data/pipeline
# ...
```

---

## Data Helpers API (`data_helpers.py`)

**Module:** `scripts.core.data_helpers`

Parquet file I/O with automatic metadata tracking.

---

### Functions

#### `load_parquet()`

Load a parquet file by dataset name with error handling.

```python
load_parquet(
    dataset_name: str,
    version: str | None = None,
    columns: list[str] | None = None
) -> pd.DataFrame
```

**Parameters:**
- `dataset_name` (str): Key from metadata.json (e.g., `'L1_hdb_transaction'`)
- `version` (str, optional): Specific version to load (defaults to latest)
- `columns` (list[str], optional): Specific columns to load (None = all columns)

**Returns:**
- `pd.DataFrame`: Loaded data

**Raises:**
- `ValueError`: If dataset not found in metadata
- `FileNotFoundError`: If parquet file missing
- `RuntimeError`: If file read fails

**Example:**
```python
from scripts.core.data_helpers import load_parquet

# Load full dataset
df = load_parquet("L2_hdb_with_features")

# Load specific columns
df = load_parquet("L2_hdb_with_features", columns=["town", "price_psf"])

# Load specific version
df = load_parquet("L2_hdb_with_features", version="2026-01-15")
```

---

#### `save_parquet()`

Save DataFrame to parquet with validation and error handling.

```python
save_parquet(
    df: pd.DataFrame,
    dataset_name: str,
    source: str | None = None,
    version: str | None = None,
    mode: str = "overwrite",
    partition_cols: list[str] | None = None,
    compression: str | None = None,
    calculate_checksum: bool = False
) -> None
```

**Parameters:**
- `df` (pd.DataFrame): DataFrame to save
- `dataset_name` (str): Unique identifier for this dataset
- `source` (str, optional): Source dataset or description (for lineage)
- `version` (str, optional): Version string (defaults to current date)
- `mode` (str): `'overwrite'` or `'append'` (default: `'overwrite'`)
- `partition_cols` (list[str], optional): Columns to partition by (e.g., `['year', 'month']`)
- `compression` (str, optional): Compression codec (defaults to `Config.PARQUET_COMPRESSION`)
- `calculate_checksum` (bool): Calculate MD5 checksum (default: False for performance)

**Raises:**
- `ValueError`: If df is empty or invalid mode
- `RuntimeError`: If save operation fails

**Side Effects:**
- Updates `data/metadata.json`
- Creates parent directories if needed
- Overwrites existing data if `mode='overwrite'`

**Example:**
```python
from scripts.core.data_helpers import save_parquet

# Save with lineage tracking
save_parquet(
    df,
    dataset_name="L3_unified_dataset",
    source="L2_hdb_with_features + L2_ura_with_features"
)

# Append to existing dataset
save_parquet(
    new_df,
    dataset_name="L1_hdb_transaction",
    mode="append"
)

# Partitioned dataset
save_parquet(
    df,
    dataset_name="L1_hdb_transaction",
    partition_cols=["year", "month"]
)
```

---

#### `list_datasets()`

Return all datasets from metadata.

```python
list_datasets(refresh_rows: bool = False) -> dict
```

**Parameters:**
- `refresh_rows` (bool): If True, recalculate row counts from disk (slower but accurate)

**Returns:**
- `dict`: Dictionary of dataset information

**Example:**
```python
from scripts.core.data_helpers import list_datasets

# Get metadata
datasets = list_datasets()

for name, info in datasets.items():
    print(f"{name}: {info['rows']} rows, version {info['version']}")

# Refresh row counts from disk
datasets = list_datasets(refresh_rows=True)
```

---

#### `verify_metadata()`

Verify all datasets in metadata actually exist and checksums match.

```python
verify_metadata() -> bool
```

**Returns:**
- `bool`: True if all datasets valid, False otherwise

**Side Effects:**
- Logs errors for invalid datasets

**Example:**
```python
from scripts.core.data_helpers import verify_metadata

if verify_metadata():
    print("All datasets valid")
else:
    print("Some datasets are corrupted or missing")
```

---

## Geocoding API (`geocoding.py`)

**Module:** `scripts.core.geocoding`

Address → coordinate conversion with intelligent fallback.

---

### Functions

#### `setup_onemap_headers()`

Setup OneMap API authentication headers.

```python
setup_onemap_headers() -> dict[str, str]
```

**Returns:**
- `dict[str, str]`: Headers with `Authorization` key containing valid JWT token

**Raises:**
- `Exception`: If token cannot be obtained or is invalid

**Behavior:**
1. Checks for existing `ONEMAP_TOKEN` in environment
2. Validates token expiration
3. Falls back to email/password authentication if token expired
4. Returns headers with valid token

**Example:**
```python
from scripts.core.geocoding import setup_onemap_headers

headers = setup_onemap_headers()
# {'Authorization': 'eyJhbGciOiJIUzI1NiIs...'}
```

---

#### `fetch_data()`

Fetch geocoding data from OneMap API for a given address.

```python
fetch_data(
    search_string: str,
    headers: dict[str, str],
    timeout: int = 30
) -> pd.DataFrame
```

**Parameters:**
- `search_string` (str): Address to search for
- `headers` (dict): Authentication headers from `setup_onemap_headers()`
- `timeout` (int): Request timeout in seconds (default: 30)

**Returns:**
- `pd.DataFrame`: Search results with columns:
  - `search_result`: Result index
  - `SEARCHVAL`: Search value
  - `LAT`: Latitude
  - `LNG`: Longitude
  - `address`: Full address
  - And other OneMap fields

**Raises:**
- `requests.RequestException`: If API call fails after retries
- `requests.Timeout`: If request times out

**Retry Behavior:**
- Up to 3 attempts with exponential backoff
- 1 second initial backoff, max 32 seconds

**Example:**
```python
from scripts.core.geocoding import fetch_data, setup_onemap_headers

headers = setup_onemap_headers()
results = fetch_data("123 Ang Mo Kio Avenue 3", headers)

if not results.empty:
    lat = results.iloc[0]['LAT']
    lng = results.iloc[0]['LNG']
    print(f"Coordinates: {lat}, {lng}")
```

---

#### `load_ura_files()`

Load all URA transaction CSV files.

```python
load_ura_files(base_path: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
```

**Parameters:**
- `base_path` (Path, optional): Base path to data directory (defaults to `Config.CSV_DIR`)

**Returns:**
- `tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]`: (ec_df, condo_df, hdb_df)
  - `ec_df`: Executive Condo transactions
  - `condo_df`: Condominium transactions
  - `hdb_df`: HDB transactions

**Example:**
```python
from scripts.core.geocoding import load_ura_files

ec_df, condo_df, hdb_df = load_ura_files()

print(f"EC transactions: {len(ec_df)}")
print(f"Condo transactions: {len(condo_df)}")
print(f"HDB transactions: {len(hdb_df)}")
```

---

## Metrics API (`metrics.py`)

**Module:** `scripts.core.metrics`

Market metrics calculations for investment analysis.

---

### Key Functions

#### `calculate_roi_score()`

Calculate ROI score for a property.

```python
calculate_roi_score(
    feature_df: pd.DataFrame,
    rental_yield_df: pd.DataFrame
) -> dict
```

**Parameters:**
- `feature_df` (pd.DataFrame): Property features
- `rental_yield_df` (pd.DataFrame): Rental yield data

**Returns:**
- `dict`: ROI score information with keys:
  - `roi_score`: Overall ROI score (0-100)
  - `rank`: Percentile rank (e.g., `'top_10%'`)
  - Additional metrics depending on implementation

**Example:**
```python
from scripts.core.metrics import calculate_roi_score

roi = calculate_roi_score(feature_df, rental_yield_df)
print(f"ROI Score: {roi['roi_score']}")
print(f"Rank: {roi['rank']}")
```

---

#### `compute_monthly_metrics()`

Compute monthly market metrics.

```python
compute_monthly_metrics(
    start_date: str,
    end_date: str
) -> pd.DataFrame
```

**Parameters:**
- `start_date` (str): Start date in format `'YYYY-MM'`
- `end_date` (str): End date in format `'YYYY-MM'`

**Returns:**
- `pd.DataFrame`: Monthly metrics with columns:
  - `month`: Month identifier
  - `median_price`: Median transaction price
  - `transaction_count`: Number of transactions
  - `median_yield`: Median rental yield
  - And other calculated metrics

**Example:**
```python
from scripts.core.metrics import compute_monthly_metrics

metrics = compute_monthly_metrics('2020-01', '2025-12')

# Plot price trends
import matplotlib.pyplot as plt
plt.plot(metrics['month'], metrics['median_price'])
plt.show()
```

---

## Cache API (`cache.py`)

**Module:** `scripts.core.cache`

Caching system for API responses and expensive computations.

---

### Key Functions

#### `cached_call()`

Decorator or function to cache function results.

```python
@cached_call(ttl_hours=24)
def expensive_function(param):
    # Expensive computation
    return result
```

**Parameters:**
- `ttl_hours` (int): Time-to-live in hours (default: 24)
- `cache_dir` (Path, optional): Custom cache directory

**Behavior:**
- Caches function results based on arguments
- Returns cached result if available and not expired
- Stores results as compressed pickle files

**Example:**
```python
from scripts.core.cache import cached_call

@cached_call(ttl_hours=24)
def fetch_api_data(query):
    # Expensive API call
    return response

# First call: fetches from API
data1 = fetch_api_data("query")

# Second call within 24 hours: returns cached result
data2 = fetch_api_data("query")
```

---

## MRT Distance API (`mrt_distance.py`)

**Module:** `scripts.core.mrt_distance`

Calculate distances between properties and MRT stations.

---

### Key Functions

#### `calculate_distance_to_mrt()`

Calculate distance from property to nearest MRT station.

```python
calculate_distance_to_mrt(
    lat: float,
    lng: float,
    mrt_stations_df: pd.DataFrame
) -> float
```

**Parameters:**
- `lat` (float): Property latitude
- `lng` (float): Property longitude
- `mrt_stations_df` (pd.DataFrame): MRT station data with `lat` and `lng` columns

**Returns:**
- `float`: Distance in meters to nearest MRT station

**Example:**
```python
from scripts.core.mrt_distance import calculate_distance_to_mrt

dist = calculate_distance_to_mrt(1.3691, 103.8492, mrt_stations_df)
print(f"Distance to nearest MRT: {dist:.0f} meters")
```

---

#### `find_nearest_mrt_station()`

Find the nearest MRT station to a property.

```python
find_nearest_mrt_station(
    lat: float,
    lng: float,
    mrt_stations_df: pd.DataFrame
) -> pd.Series
```

**Parameters:**
- `lat` (float): Property latitude
- `lng` (float): Property longitude
- `mrt_stations_df` (pd.DataFrame): MRT station data

**Returns:**
- `pd.Series`: Nearest station information with keys:
  - `station_name`: MRT station name
  - `line`: MRT line
  - `distance_m`: Distance in meters
  - And other station attributes

**Example:**
```python
from scripts.core.mrt_distance import find_nearest_mrt_station

station = find_nearest_mrt_station(1.3691, 103.8492, mrt_stations_df)
print(f"Nearest station: {station['station_name']}")
print(f"Line: {station['line']}")
print(f"Distance: {station['distance_m']:.0f}m")
```

---

## Common Patterns

### Loading Data with Error Handling

```python
from scripts.core.data_helpers import load_parquet
from scripts.core.config import Config

try:
    Config.validate()
    df = load_parquet("L2_hdb_with_features")
    print(f"Loaded {len(df)} rows")
except ValueError as e:
    print(f"Configuration error: {e}")
except FileNotFoundError as e:
    print(f"Data not found: {e}")
```

### Saving Data with Lineage

```python
from scripts.core.data_helpers import save_parquet
from datetime import datetime

save_parquet(
    processed_df,
    dataset_name="L2_hdb_with_features",
    source="L1_hdb_transaction + geocoding + feature_engineering",
    version=datetime.now().strftime("%Y-%m-%d")
)
```

### Geocoding with Retry

```python
from scripts.core.geocoding import setup_onemap_headers, fetch_data

headers = setup_onemap_headers()

try:
    results = fetch_data("123 Ang Mo Kio Avenue 3", headers)
    if not results.empty:
        lat = results.iloc[0]['LAT']
        lng = results.iloc[0]['LNG']
        print(f"Found: {lat}, {lng}")
    else:
        print("No results found")
except Exception as e:
    print(f"Geocoding failed: {e}")
```

---

## Type Hints Summary

All API functions use Python type hints:

```python
# Basic types
str     # String
int     # Integer
float   # Floating point number
bool    # Boolean

# Collections
list[T]      # List of type T
dict[K, V]   # Dictionary with key type K, value type V
tuple[T, U]  # Fixed-size tuple

# Special types
pd.DataFrame   # Pandas DataFrame
pd.Series      # Pandas Series
Path           # Pathlib Path object

# Optional types
T | None       # T or None (Python 3.10+)
Optional[T]    # T or None (older Python)
```

---

## Error Handling Best Practices

### Always validate configuration:

```python
from scripts.core.config import Config

try:
    Config.validate()
except ValueError as e:
    logger.error(f"Configuration invalid: {e}")
    sys.exit(1)
```

### Handle missing datasets gracefully:

```python
from scripts.core.data_helpers import load_parquet, list_datasets

try:
    df = load_parquet("L3_unified_dataset")
except ValueError:
    available = list(list_datasets().keys())
    print(f"Dataset not found. Available: {available}")
```

### Use retries for API calls:

```python
from scripts.core.geocoding import fetch_data, setup_onemap_headers
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def geocode_with_retry(address):
    headers = setup_onemap_headers()
    return fetch_data(address, headers)
```

---

## Related Documentation

- [Configuration Guide](./configuration.md) - Detailed setup instructions
- [Architecture](../architecture.md) - System design overview
- [Testing Guide](./testing-guide.md) - Testing patterns
- [Geocoding Guide](./onemap-auth-fix.md) - OneMap authentication

---

**Need Help?**
- Check module docstrings: `help(module_name)`
- Review code in `scripts/core/`
- Open an issue for API questions
