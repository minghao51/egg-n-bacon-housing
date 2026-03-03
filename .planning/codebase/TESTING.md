# Testing Strategy

**Generated**: 2026-02-28

## Overview

This project uses a **multi-layered testing approach**:

1. **Python Unit Tests** - Fast, isolated tests for core logic
2. **Python Integration Tests** - Component interaction tests
3. **E2E Tests** - Frontend functionality testing with Playwright

---

## Testing Frameworks

### Python: pytest

**Framework**: pytest
**Coverage**: pytest-cov
**Configuration**: `pyproject.toml`

**Why pytest**:
- Simple, Pythonic syntax
- Powerful fixtures
- Parallel execution support
- Excellent plugin ecosystem

### Frontend: Playwright

**Framework**: Playwright
**Configuration**: `app/playwright.config.ts`
**Language**: TypeScript

**Why Playwright**:
- Auto-waiting for elements
- Multi-browser support
- Network interception
- Excellent debugging tools

---

## Python Tests

### Running Tests

**From project root**:

```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest -m unit

# Run integration tests only
uv run pytest -m integration

# Skip slow tests
uv run pytest -m "not slow"

# Run with coverage
uv run pytest --cov=scripts/core

# Run specific file
uv run pytest tests/test_core/test_config.py

# Run with verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x
```

### Test Structure

**Location**: `tests/`

**Pattern**: Mirrors `/scripts` structure

```
tests/
├── test_core/                   # Core module tests
│   ├── test_config.py
│   ├── test_data_helpers.py
│   ├── test_geocoding.py
│   └── conftest.py              # Core fixtures
├── test_integration/            # Integration tests
│   ├── test_pipeline_stages.py
│   └── conftest.py              # Integration fixtures
├── conftest.py                  # Shared fixtures
└── __init__.py
```

### Test Naming

**Files**: `test_*.py` or `*_test.py`

**Classes**: `Test*`

**Functions**: `test_*`

**Examples**:
```python
# test_config.py

def test_config_has_data_dir():
    """Test that Config has DATA_DIR attribute."""
    assert Config.DATA_DIR is not None

class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_fails_without_env_vars(self, monkeypatch):
        """Test validation fails without env vars."""
        monkeypatch.delenv("ONEMAP_EMAIL", raising=False)
        with pytest.raises(ValueError):
            Config.validate()
```

### Test Markers

**Markers are used to categorize tests**:

```python
import pytest

@pytest.mark.unit
def test_load_parquet():
    """Unit test - fast, isolated."""
    pass

@pytest.mark.integration
def test_pipeline_stage():
    """Integration test - component interaction."""
    pass

@pytest.mark.slow
def test_full_pipeline():
    """Slow test - full pipeline run."""
    pass

@pytest.mark.api
def test_onemap_api():
    """API test - makes external API call."""
    pass
```

**Running marked tests**:
```bash
# Unit only
uv run pytest -m unit

# Integration only
uv run pytest -m integration

# Skip slow
uv run pytest -m "not slow"

# API tests only
uv run pytest -m api
```

### Fixtures

**Shared fixtures in `conftest.py`**:

```python
import pytest
import pandas as pd
from pathlib import Path

@pytest.fixture
def project_root_path():
    """Return absolute path to project root."""
    return Path(__file__).parent.parent

@pytest.fixture
def temp_dir(tmp_path):
    """Return temporary directory for test files."""
    return tmp_path

@pytest.fixture
def sample_dataframe():
    """Return sample DataFrame for testing."""
    return pd.DataFrame({
        "address": ["1 Orchard Road", "2 Marina Bay"],
        "price": [1000000, 2000000],
    })

@pytest.fixture
def mock_config(monkeypatch):
    """Return mocked configuration with test paths."""
    monkeypatch.setenv("ONEMAP_EMAIL", "test@example.com")
    return Config

@pytest.fixture
def mock_onemap_response():
    """Return mock OneMap API response."""
    return {
        "found": 1,
        "results": [{
            "LATITUDE": 1.3048,
            "LONGITUDE": 103.8318,
        }]
    }
```

**Using fixtures**:
```python
def test_load_parquet(sample_dataframe):
    """Test using sample_dataframe fixture."""
    result = process_data(sample_dataframe)
    assert not result.empty
```

### Test Coverage

**Generate coverage report**:

```bash
# Terminal report
uv run pytest --cov=scripts/core --cov-report=term

# HTML report
uv run pytest --cov=scripts/core --cov-report=html

# XML report (for CI)
uv run pytest --cov=scripts/core --cov-report=xml
```

**Configuration** (`pyproject.toml`):

```toml
[tool.coverage.run]
source = ["scripts"]
omit = [
    "tests/*",
    "__pycache__/*",
    "site-packages/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == "__main__":",
]
```

**View HTML report**:
```bash
open htmlcov/index.html
```

### Testing Patterns

#### 1. Arrange-Act-Assert

```python
def test_process_transactions(sample_dataframe):
    # Arrange
    input_data = sample_dataframe
    expected_cols = ["address", "price", "processed"]

    # Act
    result = process_transactions(input_data)

    # Assert
    assert list(result.columns) == expected_cols
    assert len(result) == len(input_data)
```

#### 2. Parametrized Tests

```python
@pytest.mark.parametrize("address,expected", [
    ("1 Orchard Road, Singapore", True),
    ("", False),
    (None, False),
])
def test_validate_address(address, expected):
    """Test address validation with multiple inputs."""
    result = validate_address(address)
    assert result == expected
```

#### 3. Exception Testing

```python
def test_load_parquet_raises_value_error():
    """Test that ValueError is raised for invalid dataset."""
    with pytest.raises(ValueError, match="Dataset.*not found"):
        load_parquet("nonexistent_dataset")
```

#### 4. Mocking

```python
from unittest.mock import patch

def test_geocode_with_mock():
    """Test geocoding with mocked API."""
    with patch('scripts.core.geocoding.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            "found": 1,
            "results": [{"LATITUDE": 1.0, "LONGITUDE": 103.0}]
        }

        result = geocode_address("Test Address")

        assert result == (1.0, 103.0)
        mock_get.assert_called_once()
```

### Known Test Gaps

**Missing test coverage**:

1. **Analytics Module**:
   - 49 scripts vs 1 test file
   - Need tests for ML models, analysis scripts

2. **Data Module**:
   - 44 scripts vs 3 test files
   - Need tests for download scripts, processing utilities

**Priority**:
- High: Core utilities (`data_helpers.py`, `geocoding.py`)
- Medium: Pipeline stages
- Low: Notebooks, exploratory scripts

---

## E2E Tests (Playwright)

### Running E2E Tests

**From `app/` directory**:

```bash
cd app

# Install dependencies (first time)
npm install
npx playwright install chromium

# Run all E2E tests
npm run test:e2e

# Run in headed mode (visible browser)
npm run test:e2e:headed

# Run in UI mode (interactive)
npm run test:e2e:ui

# Run in debug mode
npm run test:e2e:debug

# View HTML report
npm run test:e2e:report
```

### Test Structure

**Location**: `app/tests/e2e/`

**Coverage**: 97 tests covering:
- Home page navigation
- Dashboard pages (overview, map, trends, leaderboard, segments)
- Analytics pages (index, personas, articles)
- Cross-page navigation
- Accessibility

### Test Configuration

**File**: `app/playwright.config.ts`

```typescript
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:4321',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
});
```

### Test Example

```typescript
import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load the home page without errors', async ({ page }) => {
    await expect(page).toHaveTitle(/Egg n Bacon Housing/);
  });

  test('should have navigation links', async ({ page }) => {
    const dashboardLink = page.getByRole('link', { name: 'Dashboard' });
    await expect(dashboardLink).toBeVisible();
  });

  test('should navigate to dashboard on click', async ({ page }) => {
    await page.click('text=Dashboard');
    await expect(page).toHaveURL(/\/dashboard/);
  });
});
```

### Page Object Model

**Organize tests with page objects**:

```typescript
// tests/pages/DashboardPage.ts
export class DashboardPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/dashboard');
  }

  async getMetricValue(metricName: string) {
    return this.page.getByText(metricName).locator('..').textContent();
  }

  async clickTab(tabName: string) {
    await this.page.click(`button:has-text("${tabName}")`);
  }
}

// tests/e2e/dashboard.spec.ts
test('dashboard shows metrics', async ({ page }) => {
  const dashboard = new DashboardPage(page);
  await dashboard.goto();

  const value = await dashboard.getMetricValue('Total Properties');
  expect(value).toBeTruthy();
});
```

### Accessibility Testing

**Playwright has built-in accessibility support**:

```typescript
test('dashboard is accessible', async ({ page }) => {
  await page.goto('/dashboard');

  // Check for accessibility violations
  const violations = await page.accessibility.snapshot();
  expect(violations).toHaveLength(0);
});
```

### Network Interception

**Mock API calls if needed**:

```typescript
test('dashboard with mocked data', async ({ page }) => {
  // Intercept data fetch
  await page.route('**/data/metrics.json', route => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({ total: 100, growth: 5 }),
    });
  });

  await page.goto('/dashboard');
  await expect(page.getByText('100')).toBeVisible();
});
```

### Debugging

**UI Mode** (interactive debugging):
```bash
npm run test:e2e:ui
```

**Debug Mode** (step through tests):
```bash
npm run test:e2e:debug
```

**Trace Viewer** (after test failure):
```bash
npx playwright show-trace trace.zip
```

---

## Test Environment Setup

### Python Environment

**Always use `uv run`**:

```bash
# Ensure correct environment
uv run pytest

# Not just
pytest  # ✗ Wrong - might use system Python
```

### Frontend Environment

**Install dependencies**:

```bash
cd app
npm install
npx playwright install chromium
```

**Start dev server** (for local testing):
```bash
npm run dev
```

---

## Continuous Integration

### GitHub Actions

**Workflow**: `.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  python-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v1
      - run: uv sync
      - run: uv run pytest --cov

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: cd app && npm install
      - run: cd app && npx playwright install chromium
      - run: cd app && npm run build
      - run: cd app && npm run test:e2e
```

---

## Testing Best Practices

### Python Tests

1. **Fast Unit Tests**: Keep unit tests < 0.1s each
2. **Isolation**: Tests should not depend on each other
3. **Deterministic**: Same result every run
4. **Clear Names**: Test names should explain what is tested
5. **AAA Pattern**: Arrange-Act-Assert
6. **Mock External Services**: Don't make real API calls

### E2E Tests

1. **User Perspective**: Test what users see and do
2. **Stable Selectors**: Use data-testid or aria labels
3. **Wait Properly**: Use auto-waiting, not fixed timeouts
4. **Independent**: Tests should run in any order
5. **Fast**: Avoid unnecessary sleeps

---

## Common Testing Commands

### Python

```bash
# Quick check (unit only)
uv run pytest -m unit -q

# Full test suite
uv run pytest -v

# With coverage
uv run pytest --cov=scripts/core --cov-report=html

# Debug specific test
uv run pytest tests/test_core/test_config.py::test_config_has_data_dir -v
```

### E2E

```bash
cd app

# Quick check
npm run test:e2e

# Debug mode
npm run test:e2e:debug

# Specific test file
npx playwright test home.spec.ts

# Specific test
npx playwright test -g "should load home page"
```

---

## Summary

**Python Tests**:
- Framework: pytest
- Location: `tests/`
- Run with: `uv run pytest`
- Markers: unit, integration, slow, api
- Coverage: `--cov` flag

**E2E Tests**:
- Framework: Playwright
- Location: `app/tests/e2e/`
- Run from: `app/` directory
- Commands: `npm run test:e2e`
- Coverage: 97 tests

**CI/CD**:
- GitHub Actions
- Separate jobs for Python and E2E
- Coverage reporting

**Gaps**:
- Analytics: 48 missing test files
- Data module: 41 missing test files
- Priority: Core utilities first
