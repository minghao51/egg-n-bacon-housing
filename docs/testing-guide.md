# Testing Guide

**Last Updated**: 2026-02-20 | **Status**: Active

---

## 📋 Overview

This guide covers testing practices for the egg-n-bacon-housing project.

**Testing Framework**: pytest with comprehensive test coverage for core modules

**Test Organization**:
- Tests organized by module (mirrors `/scripts` structure)
- Categorized by type (unit, integration, slow, API)
- Fast feedback loop for development

### Quick Reference

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `uv run pytest` | Run all tests | Before committing changes |
| `uv run pytest -v` | Verbose output | Debugging test failures |
| `uv run pytest -m unit` | Unit tests only | Fast feedback during development |
| `uv run pytest -m "not slow"` | Skip slow tests | Normal development workflow |
| `uv run pytest --cov` | With coverage | Checking coverage goals |
| `uv run pytest -x` | Stop on first failure | Quick debugging |
| `uv run pytest --lf` | Rerun failed tests | Fixing test failures |
| `uv run pytest -k "name"` | Filter by name | Running specific tests |

## 🚀 Running Tests

### Run All Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest --cov=scripts/core --cov-report=html

# Run with coverage for multiple modules
uv run pytest --cov=scripts/core --cov=scripts/analytics --cov-report=html
```

**Expected Output**:
```
========================= test session starts ==========================
collected 150 items

tests/core/test_config.py ....                               [ 2%]
tests/core/test_data_helpers.py ....................         [ 18%]
tests/core/test_cache.py ........                            [ 24%]
...

========================= 150 passed in 5.23s ==========================
```

---

### Run Specific Test Categories

```bash
# Run only unit tests (fast)
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Run slow tests (infrequent)
uv run pytest -m slow

# Skip slow tests (recommended for normal development)
uv run pytest -m "not slow"
```

**Why use categories?**
- **Unit tests**: Fast feedback during development (< 1 second each)
- **Integration tests**: Verify module interactions (< 10 seconds each)
- **Slow tests**: Large dataset processing (run infrequently)
- **API tests**: External API calls (usually mocked in CI)

---

### Run Specific Test Files

```bash
# Test specific module
uv run pytest tests/core/test_config.py

# Test specific class
uv run pytest tests/core/test_config.py::TestConfigPaths

# Test specific function
uv run pytest tests/core/test_config.py::TestConfigPaths::test_base_dir_exists

# Test multiple modules
uv run pytest tests/core/ tests/analytics/
```

---

### Run with Different Verbosity

```bash
# Verbose output (shows test names)
uv run pytest -v

# Very verbose (show print statements)
uv run pytest -vv -s

# Short traceback format
uv run pytest --tb=short

# No traceback (just summary)
uv run pytest --tb=no

# Show local variables on failure
uv run pytest -l
```

---

### Debugging Failed Tests

```bash
# Stop on first failure
uv run pytest -x

# Drop into debugger on failure
uv run pytest --pdb

# Drop into debugger on failure with ipdb
uv run pytest --pdb --pdbcls=IPython.terminal.debugger:TerminalPdb

# Rerun only failed tests
uv run pytest --lf

# Rerun failed tests first, then others
uv run pytest --ff

# Show print statements
uv run pytest -v -s
```

## 📂 Test Structure

### Directory Layout

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── core/                          # Core module tests
│   ├── test_config.py             # Configuration tests
│   ├── test_data_helpers.py       # Data helper tests
│   ├── test_cache.py              # Caching tests
│   └── test_geocoding.py          # Geocoding tests
└── analytics/                     # Analytics module tests (to be added)
    ├── test_calculations.py       # Calculation tests
    ├── test_forecasts.py          # Forecast tests
    └── test_models.py             # ML model tests
```

**Key Principle**: Test directory structure mirrors source code structure
- `tests/core/test_config.py` tests `scripts/core/config.py`
- `tests/analytics/` tests `scripts/analytics/`

---

### Test Categories

#### 🟢 Unit Tests (`@pytest.mark.unit`)

**Characteristics**:
- ✅ Fast (< 1 second each)
- ✅ Run in isolation
- ✅ No external dependencies (API calls, databases)
- ✅ Mock external resources
- ✅ Test single function/class

**When to Use**: Testing pure functions, logic, calculations

**Example**:
```python
@pytest.mark.unit
def test_config_base_dir():
    """Test that BASE_DIR is correctly set."""
    assert Config.BASE_DIR is not None
    assert Config.BASE_DIR.exists()

@pytest.mark.unit
def test_calculate_roi_score():
    """Test ROI score calculation."""
    result = calculate_roi_score(features, yields)
    assert 0 <= result <= 100
```

---

#### 🟡 Integration Tests (`@pytest.mark.integration`)

**Characteristics**:
- ⏱️ Slower (< 10 seconds each)
- ✅ Test module interactions
- ✅ May use real filesystem
- ⚠️ May use real data (not external APIs)
- ✅ Verify end-to-end workflows

**When to Use**: Testing data pipelines, file I/O, module interactions

**Example**:
```python
@pytest.mark.integration
def test_full_config_validation(mock_env_vars):
    """Test that config validation works end-to-end."""
    Config.validate()
    assert Config.is_valid()

@pytest.mark.integration
def test_save_and_load_parquet(temp_data_dir):
    """Test parquet roundtrip."""
    df = create_test_dataframe()
    save_parquet(df, "test")
    loaded = load_parquet("test")
    pd.testing.assert_frame_equal(loaded, df)
```

---

#### 🔴 Slow Tests (`@pytest.mark.slow`)

**Characteristics**:
- ⏱️ Take a long time (> 10 seconds)
- ⏱️ Large dataset processing
- ⏱️ Complex computations
- ❌ Not run in normal CI workflow

**When to Use**: Full pipeline runs, large dataset tests, complex ML models

**Example**:
```python
@pytest.mark.slow
def test_large_dataset_processing():
    """Test processing of full HDB dataset."""
    df = load_parquet("L2_hdb_with_features")
    result = analyze_appreciation(df)
    assert len(result) > 1000

@pytest.mark.slow
def test_full_pipeline_run():
    """Test complete L0→L1→L2 pipeline."""
    run_pipeline(stages=["L0", "L1", "L2"])
    assert load_parquet("L2_hdb_with_features") is not None
```

---

#### 🔵 API Tests (`@pytest.mark.api`)

**Characteristics**:
- 🌐 Make external API calls
- ⚠️ Usually mocked in CI/CD
- 🔑 May require real API keys in local testing
- ⚠️ Subject to rate limits

**When to Use**: Testing API integrations, geocoding, data fetching

**Example**:
```python
@pytest.mark.api
def test_onemap_api_call():
    """Test OneMap API integration (requires real API key)."""
    response = fetch_onemap_data("123 Ang Mo Kio")
    assert response.status_code == 200
    assert "latitude" in response.json()

@pytest.mark.api
@pytest.mark.skipif(os.getenv("CI") == "true", reason="Skip in CI")
def test_google_geocoding():
    """Test Google geocoding fallback (local only)."""
    result = geocode_with_google("Orchard Road, Singapore")
    assert result["lat"] is not None
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

## 🎯 Coverage Goals

**Current Targets**:

| Module Type | Coverage Target | Rationale |
|-------------|-----------------|-----------|
| **Core modules** | 70-80% | Critical infrastructure, stable codebase |
| **Pipeline stages** | 60-70% | Data processing logic, some external deps |
| **Analytics** | 50-60% | Complex ML models, harder to test |

**View Coverage Report**:
```bash
# Generate HTML coverage report
uv run pytest --cov=scripts/core --cov-report=html

# Open report in browser
open htmlcov/index.html

# View coverage in terminal
uv run pytest --cov=scripts/core --cov-report=term-missing
```

**Interpreting Coverage**:
- ✅ **Green**: 100% coverage (ideal)
- 🟡 **Yellow**: 80-99% coverage (good)
- 🟠 **Orange**: 60-79% coverage (acceptable)
- 🔴 **Red**: < 60% coverage (needs improvement)

---

## 🔄 CI/CD Integration

**When Tests Run Automatically**:
- ✅ Every push to `main` or `develop` branches
- ✅ Every pull request
- ✅ On manual trigger

**CI Workflow**:
```
1. Checkout code
2. Install dependencies with uv
3. Run unit tests (fast feedback)
4. Run all tests with coverage
5. Upload coverage to Codecov
6. Run linting (ruff check)
7. Run formatting check (ruff format --check)
```

**CI Test Commands**:
```bash
# CI runs this (you can too):
uv run pytest -m "not slow" --cov=scripts/core --cov-report=xml
uv run ruff check .
uv run ruff format --check .
```

---

## 🆘 Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| **ImportError** | Wrong directory or PYTHONPATH | Run from project root with `uv run pytest` |
| **Fixture not found** | Fixture defined in wrong place | Check fixture is in `conftest.py` or imported |
| **Tests hang** | Waiting for API or slow operation | Use `pytest -x` to stop early, add timeout |
| **Mock not working** | Wrong patch path | Use full import path: `patch('scripts.core.config.load')` |
| **Coverage low** | Missing tests | Add tests for uncovered lines |
| **Tests pass locally, fail in CI** | Environment differences | Check `.env` file, Python version, dependencies |

---

## 📚 Resources

**Official Documentation**:
- [pytest documentation](https://docs.pytest.org/)
- [pytest fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [pytest marks](https://docs.pytest.org/en/stable/mark.html)
- [pytest-cov](https://pytest-cov.readthedocs.io/)

**Related Guides**:
- [Architecture Guide](./architecture.md) - System design overview
- [Usage Guide](./usage-guide.md) - Getting started

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
