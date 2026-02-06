# Egg-n-Bacon-Housing: Testing Strategy

## Overview

This document outlines the testing framework, structure, mocking strategies, and coverage goals for the egg-n-bacon-housing project.

---

## Testing Framework

### Core Tools

**Framework**: pytest 7.0+

**Plugins**:
- `pytest-cov` 4.0+ - Coverage reporting
- `pytest-mock` 3.10+ - Mocking utilities
- `pytest-asyncio` 0.21.0+ - Async test support

**Configuration**: `pyproject.toml`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

addopts = [
    "--verbose",
    "--strict-markers",
    "--tb=short",
    "--cov=scripts/core",
    "--cov-report=term-missing:skip-covered",
    "--cov-report=html:htmlcov",
    "--cov-report=xml:coverage.xml",
]

markers = [
    "unit: Unit tests (fast, isolated)",
    "integration: Integration tests (slower, may use external resources)",
    "slow: Slow tests (should be run infrequently)",
    "api: Tests that make API calls (may need mocking)",
]
```

---

## Test Structure

### Directory Layout

```
tests/
├── conftest.py               # Shared fixtures
├── test_pipeline.py          # Pipeline stage tests
├── test_geocoding.py         # Geocoding tests
├── test_mrt_integration.py   # MRT integration tests
├── test_mrt_enhanced.py      # Enhanced MRT tests
├── test_pipeline_setup.py    # Pipeline setup tests
│
└── core/                     # Core module tests
    ├── test_config.py        # Configuration tests
    ├── test_cache.py         # Cache tests
    └── test_data_helpers.py  # Data helper tests
```

**Pattern**: Mirrors `/scripts` structure

### Test Organization

**By Module**:
- `test_{module}.py` for each module in `/scripts`
- Example: `test_geocoding.py` for `geocoding.py`

**By Feature**:
- `test_{feature}_{type}.py` for specific features
- Example: `test_mrt_integration.py` for MRT integration

---

## Test Fixtures

### Shared Fixtures (conftest.py)

**Location**: `tests/conftest.py`

**Available Fixtures**:

```python
@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Create sample DataFrame for testing."""
    return pd.DataFrame({
        "id": range(100),
        "town": ["Bishan", "Toa Payoh"] * 50,
        "price": [500000 + i * 1000 for i in range(100)],
        "floor_area_sqm": [80 + i for i in range(100)],
    })

@pytest.fixture
def sample_api_response() -> dict:
    """Sample data.gov.sg API response."""
    return {
        "result": {
            "records": [
                {"quarter": "2024-Q1", "value": 100},
                {"quarter": "2024-Q2", "value": 200}
            ],
            "total": 2,
            "_links": {},
        }
    }

@pytest.fixture
def mock_metadata() -> dict:
    """Mock metadata for testing."""
    return {
        "datasets": {
            "test_data": {
                "path": "test.parquet",
                "version": "2024-01-01",
                "rows": 100,
                "created": "2024-01-01T00:00:00",
                "source": "test"
            }
        }
    }

@pytest.fixture
def temp_parquet_file(tmp_path: Path) -> Path:
    """Create temporary parquet file for testing."""
    file_path = tmp_path / "test.parquet"
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    df.to_parquet(file_path)
    return file_path
```

---

## Test Types

### 1. Unit Tests

**Purpose**: Test individual functions in isolation

**Characteristics**:
- Fast (milliseconds)
- No external dependencies
- All dependencies mocked

**Example**:
```python
@pytest.mark.unit
def test_convert_lease_to_months():
    """Test lease conversion function."""
    assert _convert_lease_to_months("61 years 04 months") == 736
    assert _convert_lease_to_months("60 years") == 720
    assert _convert_lease_to_months("05 months") == 5
    assert _convert_lease_to_months(99) == 99  # Already numeric
    assert _convert_lease_to_months(None) is None
    assert _convert_lease_to_months("") == 0
```

**Running Unit Tests Only**:
```bash
uv run pytest -m unit
```

### 2. Integration Tests

**Purpose**: Test interaction between components

**Characteristics**:
- Slower (seconds)
- May use external resources (APIs, files)
- Some mocking

**Example**:
```python
@pytest.mark.integration
@patch("scripts.core.geocoding.requests.get")
def test_geocode_address_integration(mock_get):
    """Test geocoding with mocked API."""
    # Mock API response
    mock_response = Mock()
    mock_response.json.return_value = {
        "found": 1,
        "results": [{
            "SEARCHVAL": "SINGAPORE",
            "LATITUDE": "1.3521",
            "LONGITUDE": "103.8198"
        }]
    }
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    # Test geocoding
    result = fetch_data("Singapore")

    assert result is not None
    assert "latitude" in result
```

**Running Integration Tests**:
```bash
uv run pytest -m integration
```

### 3. API Tests

**Purpose**: Test external API interactions

**Characteristics**:
- Slower (seconds)
- Makes real API calls (or mocks)
- Tests rate limiting, error handling

**Example**:
```python
@pytest.mark.api
def test_onemap_api_with_real_call():
    """Test OneMap API with real call (requires ONEMAP_TOKEN)."""
    # This test requires real API credentials
    result = fetch_data("Bishan Street 13")

    assert result is not None
    assert "latitude" in result
    assert "longitude" in result
```

**Running API Tests**:
```bash
uv run pytest -m api
```

### 4. Slow Tests

**Purpose**: Full pipeline or large dataset tests

**Characteristics**:
- Very slow (minutes)
- Run infrequently (before releases)
- Tests end-to-end workflows

**Example**:
```python
@pytest.mark.slow
def test_full_pipeline():
    """Test complete pipeline execution."""
    # Run all stages
    run_pipeline(stages=["L0", "L1", "L2"])

    # Verify outputs
    assert (Config.PARQUETS_DIR / "L0_hdb_resale.parquet").exists()
    assert (Config.PARQUETS_DIR / "L1_hdb_transaction.parquet").exists()
    assert (Config.PARQUETS_DIR / "L2_hdb_with_features.parquet").exists()
```

**Running Slow Tests**:
```bash
uv run pytest -m slow
```

---

## Mocking Strategies

### 1. Mocking External APIs

**Pattern**: Patch at import location

```python
from unittest.mock import patch, Mock

@patch("scripts.core.geocoding.requests.get")
def test_geocode_with_mock_api(mock_get):
    """Test geocoding with mocked API."""

    # Setup mock
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "found": 1,
        "results": [{
            "LATITUDE": "1.3521",
            "LONGITUDE": "103.8198"
        }]
    }
    mock_get.return_value = mock_response

    # Test
    result = fetch_data("Singapore")

    # Assertions
    assert mock_get.called
    assert result["latitude"] == 1.3521
```

### 2. Mocking File I/O

**Pattern**: Use `tmp_path` fixture

```python
def test_save_and_load_parquet(tmp_path):
    """Test parquet save/load with temp file."""

    # Create temp file
    file_path = tmp_path / "test.parquet"

    # Save
    df = pd.DataFrame({"a": [1, 2, 3]})
    df.to_parquet(file_path)

    # Load
    loaded = pd.read_parquet(file_path)

    assert loaded.equals(df)
```

### 3. Mocking Configuration

**Pattern**: Patch Config class

```python
@patch("scripts.core.data_helpers.Config")
def test_load_with_custom_config(mock_config):
    """Test with custom configuration."""

    # Setup mock config
    mock_config.PARQUETS_DIR = Path("/custom/path")

    # Test
    result = load_parquet("test_data")

    # Verify custom path used
    mock_config.PARQUETS_DIR.mkdir.assert_called()
```

### 4. Mocking Cache

**Pattern**: Use mock_cache fixture

```python
@patch("scripts.core.geocoding.cache")
def test_cache_hit(mock_cache):
    """Test cache hit scenario."""

    # Setup cache hit
    mock_cache.__contains__ = Mock(return_value=True)
    mock_cache.__getitem__ = Mock(return_value={"latitude": 1.0})

    # Test
    result = fetch_data("Singapore")

    # Verify cache used, not API
    assert not mock_cache.__setitem__.called
```

---

## Parametrized Tests

**Purpose**: Test multiple inputs with same test logic

**Pattern**: Use `@pytest.mark.parametrize`

```python
@pytest.mark.parametrize("lease_str,expected", [
    ("61 years 04 months", 736),
    ("60 years", 720),
    ("05 months", 5),
    (99, 99),      # Already numeric
    (None, None),
    ("", 0),
])
def test_convert_lease_to_months(lease_str, expected):
    """Test lease conversion with various inputs."""
    assert _convert_lease_to_months(lease_str) == expected
```

**Benefits**:
- Less code duplication
- Clear test cases
- Easy to add new cases

---

## Test Class Structure

**Pattern**: Group related tests in classes

```python
class TestDataHelpers:
    """Test data helper functions."""

    @patch("scripts.core.data_helpers._load_metadata")
    def test_load_parquet_success(self, mock_metadata):
        """Test successful parquet loading."""
        # Setup
        mock_metadata.return_value = {
            "datasets": {
                "test_data": {"path": "test.parquet", "version": "2024-01-01"}
            }
        }

        # Test
        with patch("pandas.read_parquet") as mock_read:
            mock_read.return_value = sample_dataframe
            result = load_parquet("test_data")

            # Assertions
            assert len(result) == 100
            assert "town" in result.columns

    @patch("scripts.core.data_helpers._load_metadata")
    def test_load_parquet_not_found(self, mock_metadata):
        """Test loading non-existent dataset."""
        # Setup
        mock_metadata.return_value = {"datasets": {}}

        # Test & Assert
        with pytest.raises(ValueError, match="not found"):
            load_parquet("missing_data")
```

---

## Coverage Goals

### Current Configuration

**Target**: `scripts/core` (core services only)

**Reports**:
- Terminal: Missing lines only
- HTML: `htmlcov/` directory
- XML: `coverage.xml` (for CI)

**Exclusions** (pyproject.toml):
```toml
[[tool.coverage.run]]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
    "*/site-packages/*",
]

[[tool.coverage.report]]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod",
]
```

### Running Coverage

**Generate Report**:
```bash
uv run pytest --cov=scripts/core --cov-report=html
```

**View HTML Report**:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

**Minimum Coverage Goal**: 80% for core services

---

## Running Tests

### All Tests

```bash
uv run pytest
```

### Specific Test File

```bash
uv run pytest tests/test_geocoding.py
```

### Specific Test Function

```bash
uv run pytest tests/test_geocoding.py::test_fetch_data
```

### By Marker

```bash
# Unit tests only
uv run pytest -m unit

# Integration tests only
uv run pytest -m integration

# Skip slow tests
uv run pytest -m "not slow"
```

### With Verbose Output

```bash
uv run pytest -v
```

### With Coverage

```bash
uv run pytest --cov=scripts/core --cov-report=term-missing
```

### Stop on First Failure

```bash
uv run pytest -x
```

---

## CI/CD Integration

**GitHub Actions Workflow**: `.github/workflows/test.yml`

**Steps**:
1. Checkout code
2. Install uv
3. Install dependencies (`uv sync`)
4. Run tests with coverage
5. Upload coverage reports

**Example**:
```yaml
- name: Run tests
  run: uv run pytest --cov=scripts/core --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

---

## Testing Best Practices

### 1. Test Naming

**Descriptive Names**:
```python
def test_load_parquet_success()  # Good
def test_load_1()  # Bad
```

### 2. One Assertion Per Test

```python
# Good
def test_load_parquet_returns_data():
    assert result is not None

def test_load_parquet_has_correct_columns():
    assert "town" in result.columns

# Avoid
def test_load_parquet():
    assert result is not None
    assert "town" in result.columns
    assert len(result) > 0
    # Too many assertions!
```

### 3. Setup-Test-Assert Pattern

```python
def test_convert_lease_to_months():
    # Setup
    lease_str = "61 years 04 months"
    expected = 736

    # Test
    result = _convert_lease_to_months(lease_str)

    # Assert
    assert result == expected
```

### 4. Mock at Right Level

**Patch at import location, not definition**:
```python
# Correct
@patch("scripts.core.geocoding.requests.get")

# Wrong
@patch("requests.get")
```

### 5. Clean Up Resources

**Use fixtures for cleanup**:
```python
@pytest.fixture
def temp_file(tmp_path):
    """Create temp file and clean up."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test data")
    yield file_path
    # Auto cleanup by tmp_path
```

---

## Summary

**Framework**: pytest with plugins (cov, mock, asyncio)
**Structure**: Mirrors `/scripts` directory
**Fixtures**: Shared in `conftest.py`
**Markers**: unit, integration, slow, api
**Mocking**: unittest.mock with patch
**Coverage**: Target 80% for `scripts/core`
**CI**: GitHub Actions with coverage upload
