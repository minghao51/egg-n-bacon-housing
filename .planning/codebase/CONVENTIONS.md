# Code Conventions

## Python Code Style

### Linting & Formatting

**Tool:** Ruff (fast Python linter and formatter)

**Configuration:** `pyproject.toml`
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP"]
ignore = ["E501"]  # Line length handled by formatter

[tool.ruff.lint.per-file-ignores]
"notebooks/*.py" = ["E402"]  # Allow imports anywhere in notebooks
"scripts/core/stages/*.py" = ["N999"]  # Allow stage file names
```

**Line Length:** 100 characters (strictly enforced)

**Python Version:** 3.11+

### Formatting Commands

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix
```

---

### Naming Conventions

**Files:** snake_case
- `data_helpers.py`
- `geocoding.py`
- `fetch_macro_data.py`

**Classes:** PascalCase
- `Config`
- `TestL0Collect`
- `GeocodingService`

**Functions:** snake_case
- `load_parquet()`
- `process_transactions()`
- `calculate_metrics()`

**Variables:** snake_case
- `dataset_name`
- `api_response`
- `geo_coordinates`

**Constants:** UPPER_SNAKE_CASE
- `DATA_DIR`
- `ONEMAP_EMAIL`
- `DEFAULT_TIMEOUT`

**Exceptions:** PascalCase with "Error" suffix
- `ValueError`
- `RuntimeError`
- `FileNotFoundError`

---

### Import Conventions

**ALWAYS use absolute imports from project root:**

```python
# ✓ Correct - Absolute from project root
from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet
from scripts.core.stages.L1_process import process_transactions

# ✗ Wrong - Relative imports
from ..core.config import Config
from .stages.L1_process import process_transactions
```

**Reason:** Relative imports break when scripts run from different directories.

**Import Order:** Standard library → Third-party → Local
```python
import logging
from pathlib import Path

import pandas as pd
import requests

from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet
```

---

### Type Hints

**Required for all public functions:**

```python
def load_parquet(
    dataset_name: str,
    version: str | None = None,
    columns: list[str] | None = None
) -> pd.DataFrame:
    """
    Load a parquet file by dataset name.

    Args:
        dataset_name: Key from metadata.json
        version: Optional version string
        columns: Optional list of columns to load

    Returns:
        pandas DataFrame

    Raises:
        ValueError: If dataset not found
        FileNotFoundError: If parquet file missing
    """
```

**Type Hint Style:**
- Use `X | Y` syntax (Python 3.10+) instead of `Optional[X]` or `Union[X, Y]`
- Use `list[str]` instead of `List[str]` (from `typing` module)
- Required for all public APIs
- Optional for private functions (but recommended)

---

### Documentation Style

**Google-style docstrings:**

```python
def process_transactions(
    ec_df: pd.DataFrame,
    condo_df: pd.DataFrame,
    hdb_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Process and combine transaction data from multiple sources.

    This function standardizes column names, removes duplicates, and
    merges EC, condo, and HDB transaction data into a unified dataset.

    Args:
        ec_df: Executive condo transactions DataFrame
        condo_df: Private condo transactions DataFrame
        hdb_df: HDB resale transactions DataFrame

    Returns:
        Unified DataFrame with standardized columns

    Raises:
        ValueError: If any input DataFrame is empty
        RuntimeError: If merge fails due to column mismatch
    """
```

**Docstring Sections:**
- Brief description (first line)
- Extended description (if needed)
- Args: (parameter descriptions)
- Returns: (return value description)
- Raises: (exceptions that may be raised)

---

### Error Handling Patterns

**Consistent error handling across codebase:**

#### Input Validation
```python
if df.empty:
    raise ValueError(f"Cannot save empty DataFrame for {dataset_name}")

if mode not in ["overwrite", "append"]:
    raise ValueError(f"mode must be 'overwrite' or 'append', got '{mode}'")

if dataset_name not in metadata["datasets"]:
    available = list(metadata["datasets"].keys())
    raise ValueError(f"Dataset '{dataset_name}' not found. Available: {available}")
```

#### File Operations
```python
if not parquet_path.exists():
    raise FileNotFoundError(
        f"Parquet file not found: {parquet_path}\n"
        f"Dataset may have been deleted. Run data pipeline to regenerate."
    )
```

#### API Calls
```python
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()
except requests.HTTPError as e:
    logger.error(f"API request failed: {e}")
    raise RuntimeError(f"Failed to fetch data from {url}: {e}") from e
except requests.Timeout as e:
    logger.error(f"API request timed out: {e}")
    raise RuntimeError(f"Timeout fetching data from {url}: {e}") from e
```

#### Data Operations
```python
try:
    df = pd.read_parquet(parquet_path, columns=columns)
    logger.info(f"Loaded {dataset_name}: {len(df)} rows from {parquet_path}")
    return df
except Exception as e:
    raise RuntimeError(f"Failed to load parquet {parquet_path}: {e}") from e
```

**Error Handling Principles:**
1. Validate inputs early
2. Use specific exception types
3. Provide descriptive error messages
4. Include context in error messages
5. Chain exceptions with `raise ... from e`
6. Log errors before re-raising

---

### Logging Patterns

**Setup (each module):**
```python
import logging

logger = logging.getLogger(__name__)
```

**Log Levels:**
```python
logger.debug()     # Detailed debug information (rarely used)
logger.info()      # General information (most common)
logger.warning()   # Warnings (non-critical issues)
logger.error()     # Errors (exceptions)
```

**Structured Logging with Emojis:**
```python
# Success/completion
logger.info(f"✅ Saved {len(df)} rows to {parquet_path}")
logger.info(f"✅ Completed geocoding: {len(results)}/{total} successful")

# Progress
logger.info(f"🔄 Processing batch {batch_num}/{total_batches}")
logger.info(f"📦 Loaded {dataset_name}: {len(df)} rows")

# Warnings
logger.warning(f"⚠️  Failed to geocode '{address}': {e}")
logger.warning(f"⚠️  No data found for {region}, using fallback")

# Errors
logger.error(f"❌ API request failed: {status_code}")
logger.error(f"❌ Unexpected error for '{address}': {e}")
```

**Logging Best Practices:**
1. Use structured messages (not print statements)
2. Include context in messages (dataset name, row count, etc.)
3. Use emojis for visual scanning
4. Log at appropriate levels
5. Log before raising exceptions

---

### Code Patterns

#### DataFrame Operations

**Vectorized Operations (preferred):**
```python
# ✓ Good - Vectorized
df['price_per_sqft'] = df['price'] / df['floor_area']

# ✗ Bad - iterrows (anti-pattern)
for idx, row in df.iterrows():
    df.loc[idx, 'price_per_sqft'] = row['price'] / row['floor_area']
```

**Method Chaining:**
```python
df = (df
    .dropna(subset=['price', 'floor_area'])
    .assign(price_per_sqft=lambda x: x['price'] / x['floor_area'])
    .sort_values('date')
    .reset_index(drop=True)
)
```

**Input Validation:**
```python
if df.empty:
    raise ValueError(f"Cannot process empty DataFrame")

required_cols = ['price', 'date', 'town']
missing = [col for col in required_cols if col not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")
```

#### API Calls

**Caching Pattern:**
```python
@cached_call(ttl=86400)  # 24 hours
def fetch_api_data(url: str) -> dict:
    """Fetch data from API with caching."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()
```

**Retry Pattern:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def fetch_with_retry(url: str) -> dict:
    """Fetch data with retry logic."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()
```

---

## Frontend Code Style

### TypeScript Configuration

**Extends Astro strict mode:**
```json
{
  "extends": "astro/tsconfigs/strict",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@components/*": ["./src/components/*"],
      "@hooks/*": ["./src/hooks/*"],
      "@types/*": ["./src/types/*"],
      "@utils/*": ["./src/utils/*"]
    }
  }
}
```

### Component Patterns

**Interface Definitions:**
```typescript
interface TrendRecord {
  date: string;
  [key: string]: number | string;
}

interface OverviewData {
  metadata: {
    generated_at: string;
    total_records: number;
    date_range: { start: string; end: string };
  };
  metrics: MetricData[];
}
```

**Custom Hooks Pattern:**
```typescript
export function useAnalyticsData<T>(type: AnalyticsType): UseAnalyticsDataResult<T> {
  const { data, isLoading, error } = useGzipJson<T>(
    getAnalyticsUrl(type),
    `analytics-${type}`,
    true
  );

  return {
    data,
    isLoading,
    error,
    refetch: () => refetch()
  };
}
```

**Error Handling:**
```typescript
const { data, error, isLoading } = useGzipJson(url);

if (error) return <ErrorDisplay error={error} />;
if (isLoading) return <LoadingSpinner />;
return <Component data={data} />;
```

---

## Testing Conventions

### Test Organization

**Mirrors production code structure:**
```
tests/
├── core/test_config.py         # Tests for scripts/core/config.py
├── core/test_data_helpers.py   # Tests for scripts/core/data_helpers.py
└── analytics/
    ├── models/test_area_arimax.py
    └── pipelines/test_cross_validate.py
```

### Test Structure

**Class-based organization:**
```python
@pytest.mark.unit
class TestL0Collect:
    """Test L0 collection functions."""

    @patch("scripts.core.stages.L0_collect.requests.get")
    def test_fetch_datagovsg_dataset(self, mock_get):
        """Test fetching data from data.gov.sg API."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {"result": {"records": []}}
        mock_get.return_value = mock_response

        # Test function
        result = fetch_datagovsg_dataset("https://api.test.com/", "test_id")

        # Assertions
        assert len(result) == 0
        mock_get.assert_called_once()
```

### Test Markers

**Use pytest markers:**
```python
@pytest.mark.unit              # Fast, isolated tests
@pytest.mark.integration       # Component interaction tests
@pytest.mark.slow             # Full pipeline tests (run infrequently)
@pytest.mark.api              # Tests that make API calls
```

**Run by marker:**
```bash
uv run pytest -m unit            # Unit tests only
uv run pytest -m integration     # Integration tests only
uv run pytest -m "not slow"      # Skip slow tests
```

---

## Shared Utilities

### Configuration

**Centralized in `scripts/core/config.py`:**
```python
from scripts.core.config import Config

# Access paths
data_dir = Config.DATA_DIR
parquets_dir = Config.PARQUETS_DIR

# Access API keys
api_key = Config.ONEMAP_EMAIL

# Validate configuration
Config.validate()
```

### Data Management

**`scripts/core/data_helpers.py`:**
```python
from scripts.core.data_helpers import load_parquet, save_parquet

# Load data
df = load_parquet("L1_hdb_transactions")

# Save data
save_parquet(
    df,
    dataset_name="L2_hdb_with_features",
    source="L1_hdb_transactions + features"
)
```

---

## Code Quality Standards

### Python

1. **Type Hints:** Required for all public functions
2. **Docstrings:** Google-style, required for all public APIs
3. **Error Handling:** Specific exceptions with descriptive messages
4. **Logging:** Structured with emojis for visual scanning
5. **Imports:** Absolute only, no relative imports
6. **Line Length:** 100 characters (strict)

### Frontend

1. **TypeScript:** Strict mode, no `any` types
2. **Interfaces:** Define all data structures
3. **Components:** Functional components with hooks
4. **Error Boundaries:** Handle errors gracefully
5. **Path Aliases:** Use `@/` prefix for all imports

---

## Anti-Patterns to Avoid

### Python

1. **No iterrows():** Use vectorized operations
2. **No print() for logging:** Use logger
3. **No hardcoded paths:** Use Config class
4. **No relative imports:** Use absolute imports
5. **No bare except:** Catch specific exceptions
6. **No mutable default arguments:** Use None and document

### Frontend

1. **No any types:** Use proper TypeScript types
2. **No prop drilling:** Use context or hooks
3. **No inline styles:** Use Tailwind classes
4. **No missing error handling:** Always handle errors
5. **No untyped data:** Define interfaces first

---

## Code Review Checklist

### Python Code

- [ ] Type hints present
- [ ] Google-style docstring
- [ ] Error handling with specific exceptions
- [ ] Logging with appropriate level
- [ ] Absolute imports from project root
- [ ] Line length ≤ 100 characters
- [ ] No use of `iterrows()`
- [ ] Input validation

### Frontend Code

- [ ] TypeScript interfaces defined
- [ ] Error handling present
- [ ] Loading states handled
- [ ] Path aliases used (@/)
- [ ] No `any` types
- [ ] Component composition clean

---

## Summary of Key Conventions

| Aspect | Convention |
|--------|-----------|
| **Line Length** | 100 characters |
| **Python Version** | 3.11+ |
| **Type Hints** | Required for public APIs |
| **Docstrings** | Google-style |
| **Imports** | Absolute from project root |
| **Logging** | Structured with emojis |
| **Error Handling** | Specific exceptions, chain with `from e` |
| **Testing** | Class-based, pytest markers |
| **Frontend Types** | TypeScript strict mode |
| **Path Aliases** | Use @/ prefix |
