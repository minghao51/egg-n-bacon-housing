# Testing Strategy

## Testing Framework

### pytest

**Primary testing framework:** pytest 7.0.0+

**Configuration:** `pyproject.toml`
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
```

### Test Markers

**Categorize tests with decorators:**

```python
@pytest.mark.unit              # Fast, isolated tests (default)
@pytest.mark.integration       # Component interaction tests
@pytest.mark.slow             # Full pipeline tests (run infrequently)
@pytest.mark.api              # Tests that make API calls
```

**Run by marker:**
```bash
uv run pytest                    # All tests
uv run pytest -m unit            # Unit tests only
uv run pytest -m integration     # Integration tests only
uv run pytest -m "not slow"      # Skip slow tests
uv run pytest -m api             # API tests only
```

---

## Test Structure

### Directory Organization

**Mirrors production code structure:**
```
tests/
├── conftest.py                 # Shared fixtures
├── core/                       # Core functionality tests
│   ├── test_config.py
│   ├── test_data_helpers.py
│   ├── test_cache.py
│   └── test_regional_mapping.py
├── analytics/                  # Analytics tests
│   ├── models/
│   │   ├── test_area_arimax.py
│   │   └── test_regional_var.py
│   ├── pipelines/
│   │   ├── test_cross_validate.py
│   │   └── test_forecast_appreciation.py
│   └── test_prepare_timeseries_data.py
├── data/                       # Data processing tests
│   └── test_fetch_macro_data.py
└── integration/                # Integration tests
    ├── test_pipeline.py
    ├── test_geocoding.py
    ├── test_mrt_integration.py
    └── test_analytics_export.py
```

### Test Class Organization

**Group related tests in classes:**
```python
@pytest.mark.unit
class TestL0Collect:
    """Test L0 collection functions."""

    @patch("scripts.core.stages.L0_collect.requests.get")
    def test_fetch_datagovsg_dataset_success(self, mock_get):
        """Test successful data fetch."""
        # Test implementation
        pass

    @patch("scripts.core.stages.L0_collect.requests.get")
    def test_fetch_datagovsg_dataset_failure(self, mock_get):
        """Test API failure handling."""
        # Test implementation
        pass

@pytest.mark.integration
class TestGeocodingIntegration:
    """Integration tests for geocoding."""

    def test_onemap_geocoding(self):
        """Test OneMap geocoding with real API."""
        # Test implementation
        pass
```

---

## Fixtures

### Shared Fixtures (conftest.py)

**Sample DataFrame fixture:**
```python
@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        "id": range(100),
        "town": ["Bishan", "Toa Payoh", "Ang Mo Kio"] * 33 + ["Bishan"],
        "price": [500000 + i * 1000 for i in range(100)],
        "floor_area": [80 + i * 0.5 for i in range(100)],
        "date": pd.date_range("2020-01-01", periods=100, freq="ME")
    })
```

**Mock config fixture:**
```python
@pytest.fixture
def mock_config(monkeypatch, temp_data_dir):
    """Mock configuration for testing."""
    # Set up test environment
    monkeypatch.setenv("ONEMAP_EMAIL", "test@example.com")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")

    # Override paths
    from scripts.core.config import Config
    original_data_dir = Config.DATA_DIR
    Config.DATA_DIR = temp_data_dir

    yield Config

    # Restore original paths
    Config.DATA_DIR = original_data_dir
```

**Temp directory fixture:**
```python
@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "pipeline").mkdir()
    (data_dir / "manual").mkdir()
    return data_dir
```

---

## Mocking Strategy

### unittest.mock

**Patch external dependencies:**
```python
from unittest.mock import Mock, patch

@pytest.mark.unit
class TestAPIFetch:
    """Test API fetching functions."""

    @patch("scripts.core.stages.L0_collect.requests.get")
    def test_fetch_datagovsg_dataset(self, mock_get):
        """Test fetching data from data.gov.sg API."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "records": [{"a": 1}, {"b": 2}],
                "total": 2,
                "_links": {}
            }
        }
        mock_get.return_value = mock_response

        # Test the function
        result = fetch_datagovsg_dataset("https://api.test.com/", "test_id")

        # Verify results
        assert len(result) == 2
        mock_get.assert_called_once()

    @patch("scripts.core.stages.L0_collect.requests.get")
    def test_fetch_with_pagination(self, mock_get):
        """Test pagination handling."""
        # Setup mock for multiple pages
        mock_get.side_effect = [
            Mock(json=lambda: {"result": {"records": [1, 2], "total": 4, "_links": {"next": "page2"}}}),
            Mock(json=lambda: {"result": {"records": [3, 4], "total": 4, "_links": {}}})
        ]

        # Test function
        result = fetch_datagovsg_dataset("https://api.test.com/", "test_id")

        # Verify
        assert len(result) == 4
        assert mock_get.call_count == 2
```

### Mock File System

**Use pytest's tmp_path:**
```python
def test_save_parquet(tmp_path):
    """Test saving parquet file."""
    from scripts.core.data_helpers import save_parquet

    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

    # Use temp directory
    save_parquet(df, "test_dataset", base_path=tmp_path)

    # Verify file exists
    assert (tmp_path / "test_dataset.parquet").exists()

    # Verify contents
    result = pd.read_parquet(tmp_path / "test_dataset.parquet")
    pd.testing.assert_frame_equal(result, df)
```

---

## Test Patterns

### Unit Tests

**Characteristics:**
- Fast execution (< 1 second each)
- No external dependencies (all mocked)
- Test single function or class
- Isolated from other tests

**Example:**
```python
@pytest.mark.unit
class TestDataHelpers:
    """Test data helper functions."""

    def test_load_parquet_success(self, sample_parquet_file):
        """Test successful parquet loading."""
        from scripts.core.data_helpers import load_parquet

        result = load_parquet("test_dataset")

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert "price" in result.columns

    def test_load_parquet_file_not_found(self):
        """Test loading non-existent parquet."""
        from scripts.core.data_helpers import load_parquet

        with pytest.raises(FileNotFoundError):
            load_parquet("nonexistent_dataset")

    def test_load_parquet_empty_file(self, empty_parquet_file):
        """Test loading empty parquet file."""
        from scripts.core.data_helpers import load_parquet

        result = load_parquet("empty_dataset")

        assert result.empty
```

### Integration Tests

**Characteristics:**
- Slower execution (may use external resources)
- Test component interactions
- May use real APIs (with caution)
- Test workflows and pipelines

**Example:**
```python
@pytest.mark.integration
class TestPipelineIntegration:
    """Integration tests for pipeline."""

    def test_full_l0_collection_workflow(self):
        """Test complete L0 collection workflow."""
        from scripts.core.stages.L0_collect import fetch_all_l0_data

        # Test real API call (may be slow)
        result = fetch_all_l0_data()

        assert result is not None
        assert "hdb_resale" in result
        assert len(result["hdb_resale"]) > 0

    @pytest.mark.slow
    def test_full_pipeline_execution(self):
        """Test complete pipeline from L0 to L3."""
        from scripts.run_pipeline import run_pipeline

        # Run full pipeline (very slow)
        result = run_pipeline(stages=["L0", "L1", "L2"])

        assert result["L0"]["success"]
        assert result["L1"]["success"]
        assert result["L2"]["success"]
```

### API Tests

**Characteristics:**
- Test external API integration
- May use real API calls
- Handle rate limiting
- Test error scenarios

**Example:**
```python
@pytest.mark.api
@pytest.mark.slow
class TestGeocodingAPI:
    """Test geocoding API integration."""

    def test_onemap_real_geocoding(self):
        """Test OneMap geocoding with real API."""
        from scripts.core.geocoding import geocode_address_onemap

        # Real API call
        result = geocode_address_onemap("1 Bishan Street 12")

        assert result is not None
        assert "latitude" in result
        assert "longitude" in result

    def test_onemap_invalid_address(self):
        """Test OneMap with invalid address."""
        from scripts.core.geocoding import geocode_address_onemap

        result = geocode_address_onemap("Invalid Address That Does Not Exist")

        assert result is None or "latitude" not in result
```

---

## Test Coverage

### Coverage Configuration

**Settings in pyproject.toml:**
```toml
[tool.coverage.run]
source = ["scripts"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
    "*/site-packages/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

### Running Coverage

```bash
# Run tests with coverage
uv run pytest --cov=scripts/core

# Generate HTML coverage report
uv run pytest --cov=scripts/core --cov-report=html

# View coverage in browser
open htmlcov/index.html

# Generate XML coverage (for CI)
uv run pytest --cov=scripts/core --cov-report=xml:coverage.xml
```

### Coverage Goals

**Target Coverage:**
- **Core modules:** ≥ 80%
- **Pipeline stages:** ≥ 70%
- **Analytics:** ≥ 60% (newer code)

**Current Status:**
- `scripts/core/` - Good coverage
- `scripts/analytics/` - Needs improvement
- `scripts/data/` - Needs improvement

---

## Test Execution

### Running Tests

**All tests:**
```bash
uv run pytest
```

**Specific test file:**
```bash
uv run pytest tests/core/test_config.py
```

**Specific test class:**
```bash
uv run pytest tests/core/test_config.py::TestConfig
```

**Specific test function:**
```bash
uv run pytest tests/core/test_config.py::TestConfig::test_validate
```

**With markers:**
```bash
uv run pytest -m unit
uv run pytest -m "not slow"
uv run pytest -m "integration and not api"
```

**Verbose output:**
```bash
uv run pytest -v
```

**Stop on first failure:**
```bash
uv run pytest -x
```

**Show print statements:**
```bash
uv run pytest -s
```

---

## CI/CD Integration

### GitHub Actions (Recommended)

**Example workflow:**
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v1
      - run: uv sync
      - run: uv run pytest -m "not slow" --cov=scripts/core
      - uses: codecov/codecov-action@v3
```

### Pre-commit Hooks (Recommended)

**Setup:**
```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: Run unit tests
        entry: uv run pytest -m unit
        language: system
        pass_filenames: false
      - id: ruff-check
        name: Ruff lint
        entry: uv run ruff check .
        language: system
      - id: ruff-format
        name: Ruff format
        entry: uv run ruff format --check .
        language: system
EOF

# Install hooks
pre-commit install
```

---

## Testing Best Practices

### Test Naming

**Descriptive test names:**
```python
# ✓ Good - Descriptive
def test_load_parquet_with_valid_dataset_returns_dataframe():
    pass

# ✗ Bad - Vague
def test_load():
    pass
```

### Test Organization

**AAA Pattern (Arrange, Act, Assert):**
```python
def test_calculate_price_per_sqft():
    """Test price per square foot calculation."""
    # Arrange - Setup test data
    df = pd.DataFrame({
        "price": [500000, 600000],
        "floor_area": [100, 120]
    })

    # Act - Call function
    result = calculate_price_per_sqft(df)

    # Assert - Verify results
    assert result["price_per_sqft"].tolist() == [5000, 5000]
```

### Test Isolation

**Each test should be independent:**
```python
# ✓ Good - Isolated
def test_function_with_scenario_1():
    data = create_test_data(scenario=1)
    result = function(data)
    assert result == expected_1

def test_function_with_scenario_2():
    data = create_test_data(scenario=2)
    result = function(data)
    assert result == expected_2

# ✗ Bad - Shared state
shared_data = create_test_data()

def test_function_1():
    result = function(shared_data)  # May affect test_function_2

def test_function_2():
    result = function(shared_data)  # Depends on test_function_1
```

### Error Testing

**Test both success and failure cases:**
```python
# Success case
def test_load_parquet_success(self):
    result = load_parquet("valid_dataset")
    assert isinstance(result, pd.DataFrame)

# Failure case
def test_load_parquet_not_found(self):
    with pytest.raises(FileNotFoundError):
        load_parquet("nonexistent_dataset")

# Invalid input
def test_load_parquet_empty_name(self):
    with pytest.raises(ValueError):
        load_parquet("")
```

---

## Frontend Testing

### Playwright E2E Testing

**Configuration:** Playwright 1.58.0

**Example test:**
```typescript
import { test, expect } from '@playwright/test';

test('dashboard loads correctly', async ({ page }) => {
  await page.goto('http://localhost:4321/dashboard');
  await expect(page).toHaveTitle(/Dashboard/);
  await expect(page.locator('text=Overview')).toBeVisible();
});
```

**Run E2E tests:**
```bash
uv run playwright test
```

---

## Testing Checklist

### Before Committing Code

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] New tests added for new features
- [ ] Test coverage maintained or improved
- [ ] No tests skipped without reason
- [ ] Error cases tested
- [ ] Edge cases tested
- [ ] Tests are isolated (no shared state)

### Test Review Checklist

- [ ] Tests are readable and maintainable
- [ ] Test names are descriptive
- [ ] Fixtures used appropriately
- [ ] External dependencies mocked
- [ ] Assertions are specific
- [ ] Tests are fast (unit tests)
- [ ] Tests cover edge cases
- [ ] No hardcoded values that could change

---

## Testing Challenges & Solutions

### Challenge: Slow API Tests

**Solution:**
- Use extensive mocking for unit tests
- Separate API tests into `@pytest.mark.api` marker
- Run API tests infrequently (`@pytest.mark.slow`)
- Use caching for API responses

### Challenge: External Dependencies

**Solution:**
- Mock all external dependencies in unit tests
- Use fixtures for consistent test data
- Create integration tests for real API calls
- Use dependency injection for better testability

### Challenge: Large Data Files

**Solution:**
- Use small sample datasets for testing
- Create fixtures with sample data
- Use pytest's tmp_path for file operations
- Avoid loading full production datasets

---

## Summary

| Aspect | Standard |
|--------|----------|
| **Framework** | pytest 7.0.0+ |
| **Markers** | unit, integration, slow, api |
| **Coverage Goal** | ≥ 80% for core modules |
| **Structure** | Mirrors production code |
| **Fixtures** | Shared in conftest.py |
| **Mocking** | unittest.mock for external deps |
| **Execution** | `uv run pytest` |
| **CI/CD** | GitHub Actions + pre-commit hooks |
