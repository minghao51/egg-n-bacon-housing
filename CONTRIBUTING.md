# Contributing to Egg-n-Bacon-Housing

Thank you for your interest in contributing! This guide will help you get started.

## Quick Start for Contributors

```bash
# 1. Fork and clone the repository
git clone https://github.com/your-username/egg-n-bacon-housing.git
cd egg-n-bacon-housing

# 2. Install dependencies
uv sync

# 3. Create a feature branch
git checkout -b feature/your-feature-name

# 4. Make your changes and test
uv run pytest
uv run ruff check .

# 5. Commit and push
git add .
git commit -m "feat: description of your changes"
git push origin feature/your-feature-name

# 6. Open a pull request
```

---

## Development Workflow

### Setting Up Your Environment

**Prerequisites:**
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- OneMap API account (for geocoding)

**One-time setup:**

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Verify setup
uv run pytest
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/core/test_config.py

# Run by marker
uv run pytest -m unit           # Fast unit tests only
uv run pytest -m integration    # Integration tests
uv run pytest -m "not slow"     # Skip slow tests

# With coverage
uv run pytest --cov=scripts/core --cov-report=html
open htmlcov/index.html
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix
```

**Code Style:**
- Line length: 100 characters
- Python 3.11+ type hints required
- Google-style docstrings
- Absolute imports from project root

### Running the Pipeline

```bash
# Run all stages
uv run python scripts/run_pipeline.py --stage all --parallel

# Run specific stage
uv run python scripts/run_pipeline.py --stage L0    # Data collection
uv run python scripts/run_pipeline.py --stage L1    # Processing
uv run python scripts/run_pipeline.py --stage L2    # Features
uv run python scripts/run_pipeline.py --stage L3    # Metrics
uv run python scripts/run_pipeline.py --stage L5    # Dashboard data
```

---

## Making Changes

### What to Work On

**Good first issues:**
- Look for issues labeled `good first issue`
- Improve test coverage
- Update documentation
- Fix bugs

**Areas needing attention:**
- `scripts/analytics/` - Missing test coverage
- `scripts/data/` - Missing test coverage
- Performance optimizations (geocoding, data loading)

### Code Conventions

**Imports:** Always use absolute imports from project root

```python
# ✅ Correct
from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet

# ❌ Wrong
from ..core.config import Config
from .core.data_helpers import load_parquet
```

**Data Loading:** Use `data_helpers` module

```python
from scripts.core.data_helpers import load_parquet, save_parquet

# Load by dataset name (uses metadata.json)
df = load_parquet("L2_hdb_with_features")

# Save with automatic metadata tracking
save_parquet(df, dataset_name="L3_my_analysis", source="L2_hdb_with_features")
```

**Error Handling:** Use try-except-log-raise pattern

```python
try:
    df = pd.read_parquet(parquet_path)
except Exception as e:
    logger.error(f"Failed to load {parquet_path}: {e}")
    raise RuntimeError(f"Parquet read failed: {e}") from e
```

**Logging:** Use structured logging

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Loading {dataset_name}")
logger.info(f"✅ Saved {len(df)} rows to {parquet_path}")
logger.warning(f"No geocoding results for {address}")
logger.error(f"API request failed: {status_code}")
```

### Dataset Naming Convention

**Pattern:** `L{stage}_{entity}_{type}.parquet`

- `L0_hdb_resale.parquet` - Raw HDB data
- `L1_hdb_transaction.parquet` - Cleaned transactions
- `L2_hdb_with_features.parquet` - Feature-enriched data
- `L3_unified_dataset.parquet` - Combined dataset

### Adding New Features

**For new pipeline stages:**
1. Create file in `scripts/core/stages/` (e.g., `L6_my_feature.py`)
2. Add stage to `scripts/run_pipeline.py`
3. Update `docs/architecture.md`
4. Add tests in `tests/core/stages/`
5. Update `CLAUDE.md` if conventions change

**For new analyses:**
1. Create script in `scripts/analytics/analysis/{category}/`
2. Save output to `data/analysis/`
3. Document findings in `docs/analytics/`
4. Add to relevant pipeline if reusable

---

## Testing Strategy

### Test Structure

```
tests/
├── core/                   # Core module tests
│   ├── test_config.py
│   ├── test_data_helpers.py
│   └── test_geocoding.py
├── analytics/              # Analysis tests (TODO)
└── conftest.py            # Shared fixtures
```

### Test Markers

```python
@pytest.mark.unit           # Fast, isolated tests
@pytest.mark.integration    # Component interaction tests
@pytest.mark.slow           # Full pipeline tests (run infrequently)
@pytest.mark.api            # Tests that make API calls
```

### Writing Tests

```python
import pytest
from scripts.core.config import Config

class TestConfigPaths:
    @pytest.mark.unit
    def test_base_dir_exists(self):
        """Test that base directory exists."""
        assert Config.DATA_DIR.exists()
```

### E2E Tests

For webapp changes, also run E2E tests:

```bash
cd app
npm install
npm run test:e2e
```

---

## Pull Request Process

### Before Submitting

1. **Update tests** - Ensure all tests pass
2. **Update docs** - Update relevant documentation
3. **Format code** - Run `uv run ruff format .`
4. **Check linting** - Run `uv run ruff check .`

### Pull Request Checklist

- [ ] Tests pass locally (`uv run pytest`)
- [ ] Code is formatted (`uv run ruff format .`)
- [ ] No linting errors (`uv run ruff check .`)
- [ ] Documentation updated (if applicable)
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)

### Commit Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `test` - Adding/updating tests
- `refactor` - Code refactoring
- `chore` - Maintenance tasks

**Examples:**
```
feat(pipeline): add parallel geocoding support
fix(geocoding): handle OneMap token expiry
docs(guide): update L2 pipeline documentation
test(geocoding): add batch geocoding tests
```

### Review Process

1. Automated checks must pass (tests, linting)
2. At least one maintainer approval required
3. Address review comments
4. Squash commits if needed
5. Merge after approval

---

## Project Structure

```
egg-n-bacon-housing/
├── scripts/
│   ├── core/                 # Shared utilities and pipeline stages
│   │   ├── config.py         # Centralized configuration
│   │   ├── data_helpers.py   # Parquet I/O with metadata
│   │   ├── geocoding.py      # OneMap/Google geocoding
│   │   └── stages/           # Pipeline stages (L0-L5)
│   ├── analytics/            # Analysis scripts
│   │   ├── analysis/         # Analysis implementations
│   │   ├── models/           # ML models
│   │   └── pipelines/        # Analysis pipelines
│   ├── data/                 # Data processing
│   │   ├── download/         # External data fetchers
│   │   └── process/          # Data transformers
│   └── run_pipeline.py       # Main pipeline entry point
├── tests/                    # Test suite
├── notebooks/                # Jupyter notebooks (Jupytext paired)
├── app/                      # Astro web application
├── docs/                     # Documentation
├── data/                     # Pipeline outputs
│   ├── parquets/             # All parquet files
│   ├── metadata.json         # Dataset registry
│   └── logs/                 # Application logs
├── CLAUDE.md                 # Project instructions
├── CONTRIBUTING.md           # This file
├── README.md                 # Project overview
└── pyproject.toml            # Python configuration
```

---

## Getting Help

**Resources:**
- [Documentation](docs/README.md) - Complete documentation hub
- [Architecture](docs/architecture.md) - System design
- [CLAUDE.md](CLAUDE.md) - Detailed project conventions
- [GitHub Issues](https://github.com/your-org/egg-n-bacon-housing/issues) - Bug reports and feature requests

**Asking questions:**
1. Search existing issues and docs first
2. Include error messages, steps to reproduce
3. Specify your environment (OS, Python version, uv version)
4. Be patient - maintainers volunteer their time

---

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to build something useful together.

**Guidelines:**
- Use inclusive language
- Provide constructive feedback
- Accept feedback gracefully
- Focus on what is best for the community
- Show empathy towards other community members

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

**Thank you for contributing! 🎉**
