# Testing

## Python (Backend/Data Pipeline)

### Framework

- **Tool**: pytest
- **Plugins**: pytest-cov, pytest-mock, pytest-asyncio
- **Config**: `pyproject.toml` [lines 83-127]

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
]
```

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── core/
│   ├── test_utils.py     # Tests for scripts/core/utils.py
│   └── ...
├── unit/
│   └── ...
├── integration/
│   └── ...
└── analytics/
    └── ...
```

### Test Markers

- `@pytest.mark.unit` - Fast, isolated tests
- `@pytest.mark.integration` - Slower, may use external resources
- `@pytest.mark.slow` - Should run infrequently
- `@pytest.mark.api` - Tests that make API calls (may need mocking)

### Shared Fixtures (conftest.py)

| Fixture | Purpose |
|---------|---------|
| `project_root_path` | Project root Path |
| `temp_dir` | Temporary directory for test files |
| `temp_data_dir` | Mimics project data structure |
| `mock_config` | Mock Config with test paths |
| `sample_dataframe` | 100-row sample DataFrame |
| `sample_transactions` | Sample HDB transaction data |
| `mock_onemap_response` | Mock OneMap API response |
| `mock_env_vars` | Environment variables |

### Mocking Pattern

```python
from unittest.mock import MagicMock

@pytest.fixture
def mock_onemap_response():
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {
        "found": 1,
        "totalNumPages": 1,
        "results": [{ ... }]
    }
    return mock
```

### Running Tests

```bash
# All tests
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ -v --cov=scripts/core --cov-report=xml

# Specific marker
uv run pytest -v -m unit

# Specific file
uv run pytest tests/core/test_utils.py
```

---

## TypeScript/Astro (Frontend)

### Framework

- **Tool**: Playwright
- **Config**: `app/playwright.config.ts`

```typescript
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
```

### Test Structure

```
app/tests/e2e/
├── home.spec.ts
├── cross-page.spec.ts
├── dashboard/
│   ├── overview.spec.ts
│   ├── trends.spec.ts
│   └── ...
├── analytics/
│   ├── articles.spec.ts
│   └── ...
└── utils/
    └── pageHealth.ts      # Shared test utilities
```

### Test Patterns

**Basic page test**:
```typescript
test('should load page', async ({ page }) => {
  await page.goto('/analytics/lease-decay');
  await expect(page).toHaveURL(/analytics\/lease-decay/);
  await expect(page.locator('main')).toBeVisible();
});
```

**Health check pattern** (from `utils/pageHealth.ts`):
```typescript
import { expectPageToLoadWithoutErrors } from '../utils/pageHealth';

test('should not have critical errors', async ({ page }) => {
  await expectPageToLoadWithoutErrors(page, '/analytics/lease-decay');
});
```

**With console warning checks**:
```typescript
test('should not emit chart sizing warnings', async ({ page }) => {
  await expectPageToLoadWithoutErrors(page, '/analytics/lease-decay', {
    failOnConsoleWarnings: true,
  });
});
```

### PageHealth Utility

`app/tests/e2e/utils/pageHealth.ts` provides `expectPageToLoadWithoutErrors()`:

```typescript
interface PageHealthOptions {
  ignoreConsoleErrors?: RegExp | string[];
  ignoreConsoleWarnings?: RegExp | string[];
  ignorePageErrors?: RegExp | string[];
  ignoreFailedRequests?: RegExp | string[];
  failOnConsoleWarnings?: boolean;
}
```

Ignores by default:
- 404s for favicon and apple-touch-icon files
- "Failed to load resource" console errors

### Running Tests

```bash
# E2E tests
npm run test:e2e

# headed mode
npm run test:e2e:headed

# UI mode
npm run test:e2e:ui

# With production build
npm run test:e2e:prod

# Show report
npm run test:e2e:report
```

### CI Configuration

From `.github/workflows/e2e.yml`:
- Runs on push to main/develop
- Parallel execution
- 2 retries on CI
- HTML report generated

---

## Coverage

### Python

Coverage targets `scripts/core`:
```bash
uv run pytest tests/ -v --cov=scripts/core --cov-report=xml --cov-report=term-missing:skip-covered
```

Excluded from coverage:
- `tests/`
- `*/test_*.py`
- `__pycache__/`
- `site-packages/`

Coverage uploaded to Codecov on CI.
