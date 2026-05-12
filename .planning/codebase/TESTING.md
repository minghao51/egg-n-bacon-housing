# Testing

## Python

### Framework

- **Tool**: pytest
- **Plugins**: pytest-cov, pytest-mock, pytest-asyncio
- **Config**: `pyproject.toml` [tool.pytest.ini_options]

### Test Structure

```
tests/
├── conftest.py
├── test_cache.py
├── test_cleaning_validation.py
├── test_config.py
├── test_data_loader.py
├── test_datagovsg.py
├── test_export.py
├── test_features.py
├── test_ingestion.py
├── test_metrics.py
├── test_onemap.py
└── test_pipeline.py
```

### Test Markers

- `@pytest.mark.unit` — Fast, isolated
- `@pytest.mark.integration` — Slower, may use external resources
- `@pytest.mark.slow` — Infrequent
- `@pytest.mark.api` — API calls (may need mocking)

### Shared Fixtures (conftest.py)

| Fixture                | Purpose                            |
| ---------------------- | ---------------------------------- |
| `project_root_path`    | Project root Path                  |
| `temp_dir`             | Temporary directory for test files |
| `temp_data_dir`        | Mimics project data structure      |
| `mock_config`          | Mock Config with test paths        |
| `sample_dataframe`     | 100-row sample DataFrame           |
| `sample_transactions`  | Sample HDB transaction data        |
| `mock_onemap_response` | Mock OneMap API response           |
| `mock_env_vars`        | Environment variables              |

### Mocking Pattern

```python
from unittest.mock import MagicMock

@pytest.fixture
def mock_onemap_response():
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {"found": 1, "results": [{...}]}
    return mock
```

### Running Tests

```bash
uv run pytest tests/ -v                          # All tests
uv run pytest tests/ -v --cov=egg_n_bacon_housing  # With coverage
uv run pytest -v -m unit                          # Specific marker
uv run pytest tests/test_config.py                # Specific file
```

## TypeScript/Astro (E2E)

### Framework

- **Tool**: Playwright
- **Config**: `app/playwright.config.ts`

### Test Structure

```
app/tests/e2e/
├── home.spec.ts
├── cross-page.spec.ts
├── dashboard/
│   ├── overview.spec.ts
│   └── trends.spec.ts
├── analytics/
│   └── articles.spec.ts
└── utils/
    └── pageHealth.ts
```

### Running

```bash
npm run test:e2e           # Headless
npm run test:e2e:headed    # Visible browser
npm run test:e2e:ui        # Playwright UI mode
npm run test:e2e:prod      # Against production build
```

## Coverage

Python coverage targets `egg_n_bacon_housing`, excludes:

- `tests/`, `*/test_*.py`
- `__pycache__/`, `site-packages/`

CI gate: core pipeline components must maintain ≥60% line coverage (enforced by `scripts/tools/check_core_coverage.py`).
