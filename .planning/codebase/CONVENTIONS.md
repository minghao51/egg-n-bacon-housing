# Egg-n-Bacon-Housing: Coding Conventions

## Overview

This document outlines the coding conventions, patterns, and standards used in the egg-n-bacon-housing project.

---

## Code Style

### Python Style Guide

**Line Length**: 100 characters (enforced by Ruff)

**Python Version**: 3.11+ (specified in pyproject.toml)

**Formatter/Linter**: Ruff (unified tooling)

**Import Order**: Standard library → Third-party → Local

```python
# Standard library
import os
from pathlib import Path

# Third-party
import pandas as pd
from dotenv import load_dotenv

# Local
from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet
```

**Type Hints**: Used consistently for all functions

```python
def process_data(
    df: pd.DataFrame,
    options: dict[str, str | int] | None = None
) -> pd.DataFrame:
    ...
```

---

## Naming Conventions

### Files

**Python Modules**: `snake_case.py`
```python
data_helpers.py
geocoding.py
mrt_distance.py
```

**Test Files**: `test_{module}.py`
```python
test_geocoding.py
test_config.py
test_data_helpers.py
```

**Stage Files**: `L{number}_{topic}.py`
```python
L0_collect.py
L1_process.py
L2_features.py
```

**Pipeline Scripts**: `snake_case.py`
```python
run_pipeline.py
prepare_webapp_data.py
```

### Python Code

**Functions**: `snake_case`
```python
def load_parquet(...)
def calculate_distance(...)
def extract_unique_addresses(...)
```

**Classes**: `PascalCase`
```python
class Config:
class DataHelpers:
class GeocodingService:
```

**Constants**: `UPPER_SNAKE_CASE`
```python
PARQUET_COMPRESSION = "snappy"
CACHE_DURATION_HOURS = 24
MAX_RETRIES = 3
```

**Variables**: `snake_case`
```python
transaction_data
geocoded_addresses
mrt_distances
```

**Private Functions**: `_snake_case` (leading underscore)
```python
def _load_metadata():
def _convert_lease_to_months():
def _validate_address():
```

### TypeScript/React

**Components**: `PascalCase.tsx`
```typescript
PriceMap.tsx
MarketOverviewDashboard.tsx
TimeSeriesChart.tsx
```

**Utilities**: `camelCase.ts`
```typescript
// Currently not used (all in components)
```

**Functions/Variables**: `camelCase`
```typescript
const mapMetrics = ...
function loadData() { ... }
```

---

## Docstring Conventions

**Style**: Google Style (consistent across all modules)

**Required For**:
- All public functions
- All classes
- All modules

**Example**:
```python
def load_parquet(
    dataset_name: str,
    version: str | None = None,
    columns: list[str] | None = None
) -> pd.DataFrame:
    """
    Load a parquet file by dataset name with error handling.

    Args:
        dataset_name: Key from metadata.json (e.g., 'raw_data', 'L1_ura_transactions')
        version: Optional version string (defaults to latest)
        columns: Optional list of columns to load (defaults to all)

    Returns:
        pandas DataFrame with the requested data

    Raises:
        ValueError: If dataset not found or version mismatch
        FileNotFoundError: If parquet file missing
        RuntimeError: If file read fails

    Example:
        >>> df = load_parquet("L1_hdb_transaction", version="2024-01-01")
        >>> print(f"Loaded {len(df)} rows")
    """
```

---

## Error Handling Patterns

### Exception Hierarchy

```python
Exception
    ├── ValueError         # Invalid input, configuration issues
    ├── FileNotFoundError  # Missing files
    ├── RuntimeError       # API failures, general errors
    └── KeyError           # Missing dictionary keys (with validation)
```

### Error Handling Best Practices

**1. Comprehensive Error Messages**
```python
if not dataset_name:
    raise ValueError("dataset_name cannot be empty")

if dataset_name not in metadata["datasets"]:
    available = list(metadata["datasets"].keys())
    raise ValueError(f"Dataset '{dataset_name}' not found. Available: {available}")
```

**2. Try-Except-Log-Raise Pattern**
```python
try:
    df = pd.read_parquet(parquet_path)
except Exception as e:
    logger.error(f"Failed to load {parquet_path}: {e}")
    raise RuntimeError(f"Parquet read failed: {e}") from e
```

**3. Contextual Error Information**
```python
raise FileNotFoundError(
    f"Parquet file not found: {parquet_path}\n"
    f"Expected location: {Config.PARQUETS_DIR}\n"
    f"Check if pipeline L1 has been run."
)
```

---

## Logging Conventions

### Logger Setup

```python
import logging

logger = logging.getLogger(__name__)
```

**Note**: Each module uses `__name__` for hierarchical logging

### Log Levels

```python
logger.debug("Detailed debug information")    # Only when debugging
logger.info(f"Processing {len(df)} rows")    # General information
logger.warning(f"Overwriting {dataset_name}") # Warnings (non-critical)
logger.error(f"Failed to load {file}: {e}")  # Errors (exceptions)
```

### Structured Logging

```python
logger.info(f"Loading {dataset_name}")
logger.info(f"✅ Saved {len(df)} rows to {parquet_path}")
logger.info(f"Cache hit for {cache_key}")
logger.warning(f"No geocoding results found for {address}")
logger.error(f"API request failed: {status_code}")
```

**Emoji Usage**:
- `✅` - Success
- `⚠️` - Warning
- `❌` - Error

---

## Configuration Management

### Single Source of Truth

**Location**: `scripts/core/config.py`

**Pattern**: Class-based configuration with validation

```python
class Config:
    """Centralized configuration with validation."""

    # Paths
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    PARQUETS_DIR = DATA_DIR / "parquets"

    # Settings with defaults
    PARQUET_COMPRESSION = "snappy"
    USE_CACHING = True
    CACHE_DURATION_HOURS = 24

    @classmethod
    def validate(cls) -> None:
        """Validate configuration on import."""
        required_keys = {
            "ONEMAP_EMAIL": os.getenv("ONEMAP_EMAIL"),
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        }

        missing = [k for k, v in required_keys.items() if not v]
        if missing:
            raise ValueError(f"Missing required configuration: {missing}")
```

**Usage**:
```python
from scripts.core.config import Config

data_dir = Config.DATA_DIR
Config.validate()  # Check all required settings
```

---

## Data Processing Patterns

### DataFrame Operations

**1. Type Hints**
```python
def process_transactions(df: pd.DataFrame) -> pd.DataFrame:
    ...
```

**2. Validation**
```python
if df.empty:
    raise ValueError(f"Cannot process empty DataFrame")
```

**3. Chaining**
```python
result = (
    df.groupby("town")
    .agg({"price": "mean", "floor_area": "median"})
    .reset_index()
    .sort_values("price", ascending=False)
)
```

### Parquet File Management

**Pattern**: Metadata tracking on save

```python
def save_parquet(
    df: pd.DataFrame,
    dataset_name: str,
    source: str | None = None,
    version: str | None = None,
) -> None:
    """Save DataFrame with metadata tracking."""

    # Input validation
    if df.empty:
        raise ValueError(f"Cannot save empty DataFrame for {dataset_name}")

    # Save with compression
    df.to_parquet(
        parquet_path,
        compression=Config.PARQUET_COMPRESSION,
        index=False,
    )

    # Update metadata
    metadata = _load_metadata()
    metadata["datasets"][dataset_name] = {
        "path": str(parquet_path.relative_to(Config.PARQUETS_DIR)),
        "version": version,
        "rows": len(df),
        "created": datetime.now().isoformat(),
        "source": source or "unknown",
    }
    _save_metadata(metadata)
```

---

## API Integration Patterns

### External API Calls

**Pattern**: Caching + Rate Limiting + Error Handling

```python
import requests
from cachetools import TTLCache
import time

# Cache configuration
cache = TTLCache(maxsize=1000, ttl=Config.CACHE_DURATION_HOURS * 3600)

def cached_api_call(url: str, **kwargs) -> dict:
    """Make API call with caching."""

    # Check cache
    cache_key = f"{url}_{hash(str(kwargs))}"
    if cache_key in cache:
        logger.info(f"Cache hit for {url}")
        return cache[cache_key]

    # Rate limiting
    time.sleep(Config.API_DELAY)

    # Make request
    response = requests.get(
        url,
        timeout=Config.API_TIMEOUT,
        **kwargs
    )

    if response.status_code != 200:
        raise RuntimeError(f"API request failed: {response.status_code}")

    data = response.json()
    cache[cache_key] = data
    return data
```

---

## Testing Patterns

### Test Organization

**Structure**: Mirrors `/scripts` structure

```
tests/
├── test_pipeline.py      # Pipeline tests
├── test_geocoding.py     # Geocoding tests
└── core/                 # Core module tests
    ├── test_config.py
    ├── test_data_helpers.py
    └── test_cache.py
```

### Test Fixtures

**Location**: `tests/conftest.py`

```python
@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Create sample DataFrame for testing."""
    return pd.DataFrame({
        "id": range(100),
        "town": ["Bishan", "Toa Payoh"] * 50,
        "price": [500000 + i * 1000 for i in range(100)],
    })

@pytest.fixture
def mock_metadata() -> dict:
    """Mock metadata for testing."""
    return {
        "datasets": {
            "test_data": {
                "path": "test.parquet",
                "version": "2024-01-01"
            }
        }
    }
```

### Test Patterns

**1. Mocking External Dependencies**
```python
from unittest.mock import patch

@patch("scripts.core.data_helpers._load_metadata")
def test_load_parquet_success(self, mock_metadata):
    """Test successful parquet loading."""
    mock_metadata.return_value = {
        "datasets": {
            "test_data": {"path": "test.parquet", "version": "2024-01-01"}
        }
    }

    with patch("pandas.read_parquet") as mock_read:
        mock_read.return_value = sample_dataframe
        result = load_parquet("test_data")

        assert len(result) == 100
        assert "town" in result.columns
```

**2. Parametrized Tests**
```python
@pytest.mark.parametrize("lease_str,expected", [
    ("61 years 04 months", 736),
    ("60 years", 720),
    ("05 months", 5),
    (99, 99),  # Already numeric
    (None, None),
    ("", 0),
])
def test_convert_lease_to_months(self, lease_str, expected):
    """Test lease conversion."""
    assert _convert_lease_to_months(lease_str) == expected
```

**3. Markers**
```python
@pytest.mark.unit
def test_config_validation():
    """Unit test - fast, isolated."""
    ...

@pytest.mark.integration
def test_geocoding_api():
    """Integration test - slower, uses external API."""
    ...

@pytest.mark.slow
def test_full_pipeline():
    """Slow test - run infrequently."""
    ...

@pytest.mark.api
def test_onemap_api():
    """Test that makes API calls (may need mocking)."""
    ...
```

---

## Performance Patterns

### Caching

**TTL Cache**: Using `cachetools.TTLCache`

```python
from cachetools import TTLCache

cache = TTLCache(
    maxsize=1000,  # Maximum number of entries
    ttl=24*3600    # Time-to-live in seconds
)
```

### Parallel Processing

**Geocoding**: Parallel workers with rate limiting

```python
from multiprocessing.pool import ThreadPool

def geocode_parallel(
    addresses: list[str],
    workers: int = 4
) -> pd.DataFrame:
    """Geocode addresses in parallel."""

    with ThreadPool(workers=workers) as pool:
        results = pool.map(geocode_single, addresses)

    return pd.DataFrame(results)
```

### Memory Optimization

**Process Large Data in Chunks**

```python
def process_large_dataset(
    file_path: Path,
    chunksize: int = 10000
) -> None:
    """Process large dataset in chunks."""

    for chunk in pd.read_parquet(file_path, chunksize=chunksize):
        processed_chunk = process_chunk(chunk)
        save_parquet(processed_chunk, "output", mode="append")
```

---

## Security Patterns

### Environment Variables

**Storage**: `.env` file (not in git)

**Loading**: Via `python-dotenv` in `config.py`

```python
from dotenv import load_dotenv
import os

load_dotenv()

ONEMAP_EMAIL = os.getenv("ONEMAP_EMAIL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
```

**Validation**:
```python
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is required")
```

---

## Code Review Checklist

- [ ] Code follows Ruff guidelines (100 char line length)
- [ ] Type hints on all functions
- [ ] Comprehensive error handling (try-except-raise)
- [ ] Complete docstrings (Google style)
- [ ] Unit tests for new functions
- [ ] Logging at appropriate levels (info, warning, error)
- [ ] No hardcoded values (use Config)
- [ ] Security: API keys in environment variables
- [ ] Performance considerations (caching, chunking)

---

## Summary

**Code Style**: Ruff with 100 char line length
**Naming**: snake_case for functions/variables, PascalCase for classes
**Docstrings**: Google style
**Error Handling**: Comprehensive with contextual messages
**Logging**: Named loggers per module
**Configuration**: Centralized in `config.py`
**Testing**: pytest with fixtures, mocking, and markers
**Security**: Environment variables for secrets
**Performance**: Caching, parallel processing, chunking
