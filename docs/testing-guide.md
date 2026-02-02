# Testing Guide

This guide covers testing practices for the egg-n-bacon-housing project.

## Overview

The project uses **pytest** as the testing framework with comprehensive test coverage for core modules. Tests are organized by module and categorized by type (unit, integration, slow, API).

## Running Tests

### Run All Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest --cov=scripts/core --cov-report=html
```

### Run Specific Test Categories

```bash
# Run only unit tests (fast)
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Run slow tests (infrequent)
uv run pytest -m slow

# Skip slow tests
uv run pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Test specific module
uv run pytest tests/core/test_config.py

# Test specific class
uv run pytest tests/core/test_config.py::TestConfigPaths

# Test specific function
uv run pytest tests/core/test_config.py::TestConfigPaths::test_base_dir_exists
```

### Run with Different Verbosity

```bash
# Verbose output
uv run pytest -v

# Very verbose (show print statements)
uv run pytest -vv -s

# Short traceback format
uv run pytest --tb=short

# No traceback (just summary)
uv run pytest --tb=no
```

## Test Structure

### Directory Layout

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── core/
│   ├── test_config.py       # Configuration tests
│   ├── test_data_helpers.py # Data helper tests
│   ├── test_cache.py        # Caching tests
│   └── test_geocoding.py    # Geocoding tests (to be added)
└── analytics/
    ├── test_calculations.py # Calculation tests (to be added)
    └── test_forecasts.py    # Forecast tests (to be added)
```

### Test Categories

#### Unit Tests (`@pytest.mark.unit`)
- Fast tests that run in isolation
- No external dependencies (API calls, databases)
- Mock external resources
- Should run in < 1 second each

Example:
```python
@pytest.mark.unit
def test_config_base_dir():
    assert Config.BASE_DIR.exists()
```

#### Integration Tests (`@pytest.mark.integration`)
- Slower tests that may use external resources
- Test module interactions
- May use real filesystem
- Should run in < 10 seconds each

Example:
```python
@pytest.mark.integration
def test_full_config_validation(mock_env_vars):
    Config.validate()
```

#### Slow Tests (`@pytest.mark.slow`)
- Tests that take a long time to run
- Large dataset processing
- Complex computations
- Not run in normal CI workflow

Example:
```python
@pytest.mark.slow
def test_large_dataset_processing():
    process_large_dataset()
```

#### API Tests (`@pytest.mark.api`)
- Tests that make external API calls
- Usually mocked in CI/CD
- May require real API keys in local testing

Example:
```python
@pytest.mark.api
def test_onemap_api_call():
    response = fetch_onemap_data()
    assert response.status_code == 200
```

## Writing Tests

### Basic Test Structure

```python
import pytest
from scripts.core.config import Config

@pytest.mark.unit
class TestConfigPaths:
    """Test configuration path setup."""

    def test_base_dir_exists(self):
        """Test that BASE_DIR is correctly set."""
        assert Config.BASE_DIR is not None
        assert Config.BASE_DIR.exists()
```

### Using Fixtures

```python
def test_with_temp_dir(temp_dir):
    """Test using temporary directory fixture."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("content")
    assert test_file.exists()

def test_with_sample_data(sample_dataframe):
    """Test using sample DataFrame fixture."""
    assert len(sample_dataframe) == 100
    assert "price" in sample_dataframe.columns
```

### Mocking

```python
from unittest.mock import patch, MagicMock

def test_with_mock(mock_onemap_response):
    """Test using mocked API response."""
    response = mock_onemap_response
    assert response.status_code == 200

def test_with_patch(monkeypatch):
    """Test using monkeypatch to modify behavior."""
    monkeypatch.setenv("TEST_VAR", "test_value")
    assert os.getenv("TEST_VAR") == "test_value"
```

### Parameterized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("INFO", logging.INFO),
    ("DEBUG", logging.DEBUG),
    ("ERROR", logging.ERROR),
])
def test_log_level_mapping(input, expected):
    """Test log level string to int conversion."""
    assert get_log_level(input) == expected
```

## Common Fixtures

### `temp_dir`
Creates a temporary directory that is automatically cleaned up.

```python
def test_file_operations(temp_dir):
    file_path = temp_dir / "test.txt"
    file_path.write_text("content")
```

### `temp_data_dir`
Creates a temporary data directory structure (pipeline/, cache/, manual/).

```python
def test_pipeline_save(temp_data_dir):
    output_path = temp_data_dir / "pipeline" / "L0" / "test.parquet"
    save_data(output_path)
```

### `sample_dataframe`
Provides a sample DataFrame with 100 rows.

```python
def test_dataframe_analysis(sample_dataframe):
    result = analyze(sample_dataframe)
    assert result["count"] == 100
```

### `mock_config`
Provides mocked configuration with temporary directories.

```python
def test_with_mock_config(mock_config):
    assert mock_config.DATA_DIR.exists()
    assert Config.DATA_DIR == mock_config.DATA_DIR
```

### `mock_env_vars`
Sets up mock environment variables.

```python
def test_environment(mock_env_vars):
    assert os.getenv("ONEMAP_EMAIL") == "test@example.com"
```

## Best Practices

### 1. Test Naming

✅ Good:
```python
def test_config_base_dir_exists()
def test_cache_returns_none_on_miss()
def test_save_parquet_creates_metadata()
```

❌ Bad:
```python
def test1()
def test_config()
def test_it_works()
```

### 2. Use Descriptive Docstrings

```python
def test_cache_expiration_based_on_duration():
    """Test that cache entries expire after the specified duration."""
    # Arrange
    cache_mgr = CacheManager()
    cache_mgr.set("test", {"data": "value"})

    # Act
    result = cache_mgr.get("test", duration_hours=1)

    # Assert
    assert result is None
```

### 3. Follow AAA Pattern (Arrange-Act-Assert)

```python
def test_parquet_roundtrip():
    # Arrange
    df = pd.DataFrame({"a": [1, 2, 3]})
    path = temp_dir / "test.parquet"

    # Act
    save_parquet(df, "test", path)
    loaded = load_parquet("test")

    # Assert
    pd.testing.assert_frame_equal(loaded, df)
```

### 4. Test One Thing Per Test

✅ Good - Focused test:
```python
def test_save_creates_file():
    """Test that save_parquet creates the output file."""
    save_parquet(df, "test", path)
    assert path.exists()
```

❌ Bad - Multiple assertions:
```python
def test_save_and_load():
    save_parquet(df, "test", path)
    assert path.exists()
    loaded = load_parquet("test")
    assert len(loaded) == len(df)
    assert list(loaded.columns) == list(df.columns)
```

### 5. Use Appropriate Test Markers

```python
@pytest.mark.unit
def test_fast_calculation():
    """This test is fast and isolated."""
    result = calculate_sum(1, 2)
    assert result == 3

@pytest.mark.integration
def test_module_interaction():
    """This test integrates multiple modules."""
    result = complex_pipeline_operation()
    assert result is not None

@pytest.mark.slow
def test_large_dataset():
    """This test processes a large dataset."""
    result = process_million_rows()
    assert result > 0
```

### 6. Mock External Dependencies

```python
def test_api_call_with_mock(mock_onemap_response):
    """Test API call with mocked response."""
    with patch("requests.get", return_value=mock_onemap_response):
        result = fetch_onemap_data()
        assert result["found"] == 1
```

## Coverage Goals

Current targets:
- **Core modules**: 70-80% coverage
- **Pipeline stages**: 60-70% coverage
- **Analytics**: 50-60% coverage (more complex)

View coverage report:
```bash
uv run pytest --cov=scripts/core --cov-report=html
open htmlcov/index.html
```

## CI/CD Integration

Tests run automatically on:
- Every push to `main` or `develop` branches
- Every pull request

CI workflow:
1. Checkout code
2. Install dependencies with `uv`
3. Run unit tests
4. Run all tests with coverage
5. Upload coverage to Codecov
6. Run linting (ruff)

## Debugging Tests

### Run with pdb debugger

```bash
uv run pytest --pdb
```

### Drop into debugger on failure

```python
def test_with_debug():
    import pdb; pdb.set_trace()
    assert False
```

### View print statements

```bash
uv run pytest -v -s
```

### Run last failed tests

```bash
uv run pytest --lf
```

### Run tests until first failure

```bash
uv run pytest -x
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [pytest marks](https://docs.pytest.org/en/stable/mark.html)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
