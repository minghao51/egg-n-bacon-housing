# Code Conventions

**Generated**: 2026-02-28

## Code Style

### Python Style

**Line Length**: 100 characters (enforced by Ruff)

**Python Version**: 3.11+ (minimum requirement)

**Formatter/Linter**: Ruff
```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix
```

**Configuration**: `pyproject.toml`

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4"]
ignore = ["E501"]  # Line length handled by formatter
```

---

### TypeScript/React Style

**Formatter**: Biome or ESLint (configured in `app/`)

**Configuration**: `app/biome.json` or `app/.eslintrc.js`

**Commands**:
```bash
cd app
npm run lint        # Check linting
npm run lint:fix    # Auto-fix issues
npm run format      # Format code
```

---

## Import Path Conventions

### Absolute Imports Only

**ALWAYS use absolute imports from project root**

```python
# ✓ Correct - Absolute from project root
from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet
from scripts.core.stages.L1_process import process_transactions

# ✗ Wrong - Relative imports
from ..core.config import Config
from .stages.L1_process import process_transactions
```

**Reason**: Relative imports break when scripts run from different directories

### Import Organization

**Order**: Standard library → Third-party → Local imports

```python
# 1. Standard library
import logging
from pathlib import Path

# 2. Third-party
import pandas as pd
from dotenv import load_dotenv

# 3. Local imports
from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet
```

### Import Aliases

**Standard aliases**:
```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scripts.core import config as cfg
```

---

## Error Handling

### Exception Hierarchy

**Use specific exceptions for different error types**:

- `ValueError` - Invalid input, configuration issues
- `FileNotFoundError` - Missing files
- `RuntimeError` - API failures, general errors
- `KeyError` - Missing data keys (with context)

### Pattern: Try-Except-Log-Raise

**Standard error handling pattern**:

```python
import logging
logger = logging.getLogger(__name__)

try:
    df = pd.read_parquet(parquet_path)
except Exception as e:
    logger.error(f"Failed to load {parquet_path}: {e}")
    raise RuntimeError(f"Parquet read failed: {e}") from e
```

### Comprehensive Error Messages

**Provide context and available options**:

```python
if dataset_name not in metadata["datasets"]:
    available = list(metadata["datasets"].keys())
    raise ValueError(
        f"Dataset '{dataset_name}' not found. "
        f"Available: {', '.join(available)}"
    )
```

### Validation First

**Validate inputs before processing**:

```python
def process_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Process transaction data."""
    if df.empty:
        raise ValueError("DataFrame is empty")

    required_cols = ["address", "price", "date"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Process...
    return df
```

---

## Logging

### Setup

**Each module should set up logging**:

```python
import logging

logger = logging.getLogger(__name__)
```

### Log Levels

**When to use each level**:

```python
logger.debug("Detailed debug information")  # Development only
logger.info("General information")          # Most common
logger.warning("Warning (non-critical)")    # Potential issues
logger.error("Error (exception)")           # Failures
```

### Structured Logging

**Use descriptive messages with context**:

```python
# Success
logger.info(f"Loading {dataset_name}")
logger.info(f"✅ Saved {len(df)} rows to {parquet_path}")

# Warnings
logger.warning(f"No geocoding results found for {address}")
logger.warning(f"Missing coordinates for {count} addresses")

# Errors
logger.error(f"API request failed: {status_code}")
logger.error(f"Failed to geocode after 3 attempts: {address}")
```

### Output Location

**Log files**: `data/logs/`

**Format**: Timestamped log files
- `pipeline_20260228.log`
- `geocoding_20260228.log`

---

## Type Hints

### Required for Public Functions

**All public functions must have type hints**:

```python
def load_parquet(
    dataset_name: str,
    version: str | None = None
) -> pd.DataFrame:
    """Load a parquet file by dataset name."""
    pass

def save_parquet(
    df: pd.DataFrame,
    dataset_name: str,
    source: str,
    description: str | None = None,
) -> None:
    """Save DataFrame to parquet with metadata."""
    pass
```

### Type Hints for Returns

**Always specify return type**:

```python
def process_address(address: str) -> tuple[str, str, int]:
    """Process address into components.

    Returns:
        Tuple of (block, street, postal_code)
    """
    pass
```

### Union Types

**Use modern syntax (Python 3.10+)**:

```python
# ✓ Modern syntax
def process(data: str | None) -> pd.DataFrame | None:
    pass

# ✗ Old syntax (avoid)
from typing import Union
def process(data: Union[str, None]) -> Union[pd.DataFrame, None]:
    pass
```

### Type Aliases

**For complex types**:

```python
from typing import TypeAlias

Coordinates: TypeAlias = tuple[float, float]

def geocode(address: str) -> Coordinates | None:
    """Geocode address to lat/lon."""
    pass
```

---

## Docstrings

### Google Style

**Use Google style docstrings**:

```python
def load_parquet(dataset_name: str) -> pd.DataFrame:
    """Load a parquet file by dataset name with error handling.

    Args:
        dataset_name: Key from metadata.json

    Returns:
        pandas DataFrame with the requested data

    Raises:
        ValueError: If dataset not found
        FileNotFoundError: If parquet file missing
    """
    pass
```

### Module Docstrings

**Each module should have a docstring**:

```python
"""HDB resale transaction processing.

This module handles the processing of HDB resale transaction data,
including address cleaning, validation, and geocoding.

 typical usage example:
    df = load_parquet("L0_hdb_resale")
    processed = process_hdb_transactions(df)
    save_parquet(processed, "L1_hdb_transaction")
"""
```

### Function Docstrings

**Include**:
- Brief description
- Args (if parameters)
- Returns (if returns value)
- Raises (if exceptions)
- Example (if complex)

---

## Code Organization

### Function Length

**Keep functions short and focused**:
- **Target**: < 50 lines
- **Maximum**: < 100 lines (with good reason)

**Extract helper functions for complex logic**:

```python
# ✓ Good - Delegated to helpers
def process_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df = clean_addresses(df)
    df = geocode_addresses(df)
    df = add_features(df)
    return df

# ✗ Bad - Too long, does too much
def process_transactions(df: pd.DataFrame) -> pd.DataFrame:
    # 200 lines of processing...
    pass
```

### Module Organization

**Order of elements**:
1. Module docstring
2. Imports (standard → third → local)
3. Module-level constants
4. Helper functions (private, prefixed with `_`)
5. Public functions
6. Classes (if any)
7. `if __name__ == "__main__"` block

**Example**:
```python
"""Module docstring."""

import logging
import pandas as pd

from scripts.core.config import Config

logger = logging.getLogger(__name__)
CONSTANT_VALUE = "value"

def _helper_function():
    """Private helper."""
    pass

def public_function():
    """Public function."""
    pass

if __name__ == "__main__":
    # CLI logic
    pass
```

### Class Organization

**Use classes for stateful operations**:
- Geocoding service
- API client
- Configuration manager

**Prefer functions for stateless operations**:
- Data transformations
- Calculations
- Pure functions

---

## Naming Conventions

### Python

**Variables and functions**: `snake_case`
```python
address_cleaner = AddressCleaner()
def process_data():
    pass
```

**Classes**: `PascalCase`
```python
class GeocodingService:
    pass
```

**Constants**: `UPPER_SNAKE_CASE`
```python
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
```

**Private members**: Prefix with `_`
```python
def _internal_helper():
    pass

class MyClass:
    def __init__(self):
        self._private_var = None
```

### TypeScript/React

**Components**: `PascalCase`
```typescript
export function DashboardMap() {
  return <div>...</div>
}
```

**Utilities**: `camelCase`
```typescript
export function formatDate(date: Date): string {
  return ...
}
```

**Files**:
- Components: `PascalCase.tsx`
- Pages: `kebab-case.astro`
- Utils: `camelCase.ts`

---

## Configuration Management

### Centralized Configuration

**All configuration in `scripts/core/config.py`**:

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

### Environment Variables

**Use `.env` file (from `.env.example`)**:

```bash
# .env
ONEMAP_EMAIL=your@email.com
GOOGLE_API_KEY=your_api_key_here
```

**Never hardcode secrets**:
```python
# ✗ Wrong - Hardcoded secret
API_KEY = "abc123"

# ✓ Correct - From environment
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY not set")
```

---

## Data Processing Patterns

### Loading Data

**Use metadata-based loading**:

```python
from scripts.core.data_helpers import load_parquet

# Uses metadata.json
df = load_parquet("L2_hdb_with_features")

# Validate
if df.empty:
    raise ValueError("Dataset is empty")
```

### Saving Data

**Use metadata-based saving**:

```python
from scripts.core.data_helpers import save_parquet

save_parquet(
    df,
    dataset_name="L3_unified_dataset",
    source="L2_hdb_with_features + L2_ura_with_features"
)
# Automatically updates metadata.json
```

### DataFrame Operations

**Validate non-empty**:
```python
def process(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("Input DataFrame is empty")

    # Process...
    return df
```

**Use method chaining for readability**:
```python
df = (
    df
    .dropna(subset=["price"])
    .assign(price_per_sqft=lambda x: x["price"] / x["floor_area"])
    .sort_values("date")
)
```

---

## Commenting Guidelines

### When to Comment

**Good comments explain WHY, not WHAT**:

```python
# ✓ Good - Explains why
# Delay 1.2s to respect OneMap rate limits
time.sleep(1.2)

# ✗ Bad - Restates obvious
# Sleep for 1.2 seconds
time.sleep(1.2)
```

### When NOT to Comment

**Don't comment obvious code**:
```python
# ✗ Useless comment
# Increment counter
count += 1

# ✓ Self-explanatory, no comment needed
count += 1
```

### TODO Comments

**Format**: `TODO: description - @username (optional)`

```python
# TODO: Implement caching for API responses
# TODO: Refactor into smaller functions - @dev
# FIXME: This breaks for edge case X
```

---

## Testing Conventions

### Test Structure

**Follow the Arrange-Act-Assert pattern**:

```python
def test_load_parquet():
    # Arrange
    dataset_name = "test_dataset"
    expected_rows = 100

    # Act
    df = load_parquet(dataset_name)

    # Assert
    assert len(df) == expected_rows
    assert not df.empty
```

### Test Naming

**Descriptive names that explain what is being tested**:

```python
# ✓ Good
def test_geocode_address_returns_coordinates_for_valid_address():
    pass

def test_geocode_address_returns_none_for_invalid_address():
    pass

# ✗ Bad
def test_geocode():
    pass
def test_geocode_fail():
    pass
```

### Test Fixtures

**Use fixtures for common test data**:

```python
import pytest

@pytest.fixture
def sample_dataframe():
    """Return a sample DataFrame for testing."""
    return pd.DataFrame({
        "address": ["1 Orchard Road"],
        "price": [1000000],
    })

def test_process(sample_dataframe):
    result = process(sample_dataframe)
    assert not result.empty
```

---

## Jupyter Notebook Conventions

### Jupytext Pairing

**All notebooks have paired .py files**:
- `notebooks/L0_datagovsg.ipynb` ↔ `notebooks/L0_datagovsg.py`

### Editing Workflow

**Edit .py files in VS Code** (better IDE support)
**Use .ipynb files in Jupyter** (visualization and exploration)

### Cell Markers

**Use `#%%` format** for cell markers in .py files:

```python
# %%
import pandas as pd

# %%
df = pd.read_csv("data.csv")
df.head()
```

### Syncing

**Manual sync** (if needed):
```bash
cd notebooks
uv run jupytext --sync notebook_name.ipynb
```

---

## Git Conventions

### Commit Messages

**Format**: `type(scope): description`

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks

**Examples**:
```bash
git commit -m "feat(geocoding): add fallback to Google Maps"
git commit -m "fix(pipeline): handle missing address field"
git commit -m "docs: update README with setup instructions"
```

---

## Summary

**Code Style**:
- Python: Ruff formatter, 100 char line length
- Type hints required for public functions
- Google style docstrings

**Import Paths**:
- Absolute imports only (from project root)

**Error Handling**:
- Try-Except-Log-Raise pattern
- Comprehensive error messages
- Validate inputs first

**Logging**:
- Structured messages with context
- Appropriate log levels
- Output to `data/logs/`

**Data Processing**:
- Use metadata-based load/save
- Validate non-empty DataFrames
- Method chaining for readability

**Testing**:
- Arrange-Act-Assert pattern
- Descriptive test names
- Use fixtures for common data

**Notebooks**:
- Paired .ipynb + .py files (Jupytext)
- Edit .py in VS Code
- Use .ipynb in Jupyter
