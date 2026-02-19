1. First think through the problem, read the codebase for relevant files.
2. Before you make any major changes, check in with me and I will verify the plan.
3. Please every step of the way just give me a high level explanation of what changes you made
4. Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity.
5. Maintain a documentation file that describes how the architecture of the app works inside and out.
6. Never speculate about code you have not opened. If the user references a specific file, you MUST read the file before answering. Make sure to investigate and read relevant files BEFORE answering questions about the codebase. Never make any claims about code before investigating unless you are certain of the correct answer - give grounded and hallucination-free answers.
7. Python environment
    - "Use uv for Python package management and to create a .venv if it is not present."
    - "IMPORTANT: Always use uv run for all Python commands. Never use plain python or python3."
    - Use uv commands in your project's workflow. Common commands include:
    - uv sync to install/sync all dependencies.
    - uv run <command> (e.g., uv run pytest, uv run ruff check .) to execute commands within the managed environment.
    - uv add <package> to add a dependency to your pyproject.toml file.
8. When creating or generating Markdown (.md) files, you must strict adhere to the following naming convention: YYYYMMDD-filename.md
---

## Development Workflow

### Environment Setup

1. **Install uv** (one-time):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

### Running Code

**Always use `uv run`**:
```bash
# Python scripts
uv run python script.py

# Jupyter notebooks
uv run jupyter notebook

# Tests
uv run pytest

# Linting
uv run ruff check .
```

### Working with Notebooks

**Jupytext is configured** - notebooks are paired with Python scripts:

1. **All notebooks have paired .py files**:
   - `notebooks/L0_datagovsg.ipynb` ↔ `notebooks/L0_datagovsg.py`
   - When you edit the .py file, the .ipynb updates automatically
   - When you edit the .ipynb file, the .py updates automatically

2. **Recommended workflow**:
   - Edit .py files in VS Code for code changes (better IDE support)
   - Use .ipynb files for visualization and exploration in Jupyter
   - Cell markers in .py files use `#%%` format

3. **To sync notebooks manually**:
   ```bash
   cd notebooks
   uv run jupytext --sync notebook_name.ipynb
   ```

4. **Git tracking**:
   - Both .ipynb and .py files are tracked
   - .py files provide clean diffs for code reviews
   - .ipynb files preserve outputs and visualizations

### Common Commands

```bash
# Install new dependency
uv add pandas

# Install dev dependency
uv add --dev pytest

# Update dependencies
uv sync --upgrade

# Run specific notebook
uv run jupyter notebook notebooks/L0_datagovsg.ipynb

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Check linting
uv run ruff check .
```

### Configuration

All configuration is centralized in `core/config.py`:
- Paths (DATA_DIR, PARQUETS_DIR, etc.)
- API keys (loaded from .env)
- Feature flags (USE_CACHING, VERBOSE_LOGGING)

Usage:
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

---

## Project Architecture

This is a **stage-based ETL pipeline** (L0-L5) for processing Singapore housing data:

- **L0 (Collection)**: Fetch HDB/URA transactions from data.gov.sg
- **L0_macro (Macro Data)**: Fetch CPI, GDP, SORA, unemployment, PPI from SingStat API
- **L1 (Processing)**: Clean data, geocode addresses (OneMap → Google fallback)
- **L2 (Features)**: Add MRT distances, CBD distance, school tiers, amenities
- **L3 (Export)**: Create unified dataset, export JSONs for webapp
- **L4 (Analysis)**: Run ML models, spatial analysis, forecasting
- **L5 (Metrics)**: Calculate dashboard metrics

**Main Entry Point**: `scripts/run_pipeline.py`

**Key Files**:
- `scripts/core/config.py` - Centralized configuration
- `scripts/core/data_helpers.py` - Parquet I/O with metadata tracking
- `scripts/core/geocoding.py` - OneMap/Google geocoding
- `scripts/prepare_webapp_data.py` - Generate dashboard JSONs

---

## Dataset Naming Convention

**Pattern**: `L{stage}_{entity}_{type}.parquet`

**Examples**:
- `L0_hdb_resale.parquet` - Raw HDB data from data.gov.sg
- `L1_hdb_transaction.parquet` - Cleaned, geocoded HDB transactions
- `L2_hdb_with_features.parquet` - Feature-enriched HDB data
- `L3_unified_dataset.parquet` - Combined all property types
- `analysis_mrt_heterogeneous_effects.parquet` - Analysis results

**Storage**: All parquets in `data/parquets/`
**Metadata**: Tracked in `data/metadata.json`

---

## Import Path Conventions

**ALWAYS use absolute imports from project root**:

```python
# ✓ Correct - Absolute from project root
from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet
from scripts.core.stages.L1_process import process_transactions

# ✗ Wrong - Relative imports
from ..core.config import Config
from .stages.L1_process import process_transactions
```

**Why**: Relative imports break when scripts run from different directories.

---

## Code Style

**Line Length**: 100 characters (enforced by Ruff)

**Python Version**: 3.11+

**Formatter/Linter**: Ruff
```bash
uv run ruff format .     # Format code
uv run ruff check .      # Lint code
uv run ruff check . --fix # Auto-fix issues
```

**Docstring Style**: Google style
```python
def load_parquet(dataset_name: str) -> pd.DataFrame:
    """
    Load a parquet file by dataset name with error handling.

    Args:
        dataset_name: Key from metadata.json

    Returns:
        pandas DataFrame with the requested data

    Raises:
        ValueError: If dataset not found
        FileNotFoundError: If parquet file missing
    """
```

**Type Hints**: Required for all public functions

---

## Error Handling

**Exception Hierarchy**:
- `ValueError` - Invalid input, configuration issues
- `FileNotFoundError` - Missing files
- `RuntimeError` - API failures, general errors

**Pattern**: Try-Except-Log-Raise
```python
try:
    df = pd.read_parquet(parquet_path)
except Exception as e:
    logger.error(f"Failed to load {parquet_path}: {e}")
    raise RuntimeError(f"Parquet read failed: {e}") from e
```

**Comprehensive Error Messages**:
```python
if dataset_name not in metadata["datasets"]:
    available = list(metadata["datasets"].keys())
    raise ValueError(f"Dataset '{dataset_name}' not found. Available: {available}")
```

---

## Logging

**Setup** (each module):
```python
import logging
logger = logging.getLogger(__name__)
```

**Log Levels**:
- `logger.debug()` - Detailed debug information
- `logger.info()` - General information (most common)
- `logger.warning()` - Warnings (non-critical)
- `logger.error()` - Errors (exceptions)

**Structured Logging**:
```python
logger.info(f"Loading {dataset_name}")
logger.info(f"✅ Saved {len(df)} rows to {parquet_path}")
logger.warning(f"No geocoding results found for {address}")
logger.error(f"API request failed: {status_code}")
```

**Output**: `data/logs/` with timestamps

---

## Testing

**Framework**: pytest
```bash
uv run pytest                    # Run all tests
uv run pytest -m unit            # Unit tests only
uv run pytest -m integration     # Integration tests only
uv run pytest -m "not slow"      # Skip slow tests
uv run pytest --cov=scripts/core # With coverage
```

**Markers**:
- `@pytest.mark.unit` - Fast, isolated tests
- `@pytest.mark.integration` - Component interaction tests
- `@pytest.mark.slow` - Full pipeline tests (run infrequently)
- `@pytest.mark.api` - Tests that make API calls

**Test Structure**: Mirrors `/scripts` structure
**See**: `.planning/codebase/TESTING.md` for comprehensive testing strategy

---

## Known Issues to Avoid

**Large Files**:
- `L3_export.py` (1632 lines) - Avoid adding more complexity
- `create_l3_unified_dataset.py` (1443 lines) - Has duplicate logic with L3_export.py

**Hardcoded Data** (avoid adding more):
- `mrt_line_mapping.py` (534 lines of hardcoded stations)
- `school_features.py` (hardcoded school tiers)

**Geocoding Performance**:
- Sequential API calls with 1 second delay
- Consider parallel workers for large batches

**Memory Usage**:
- Full datasets loaded into memory
- Consider chunked processing for large files

**Missing Test Coverage**:
- `scripts/analytics/` - No tests yet
- `scripts/data/` - No tests yet

**See**: `.planning/codebase/CONCERNS.md` for complete technical debt tracking

---

## External Services

**Required API Keys**:
- `ONEMAP_EMAIL` - Singapore geocoding (token auto-generated)
- `GOOGLE_API_KEY` - Geocoding fallback

**Data Sources**:
- data.gov.sg - HDB/URA transactions (no API key needed)
- OneMap API - Singapore geocoding
- Google Maps - Geocoding fallback

**Rate Limiting**:
- OneMap: 1 second delay between calls
- Token expiry: ~3 days (auto-refresh on 401/403)

**Caching**: TTL-based (24 hours default) for API responses

**See**: `.planning/codebase/INTEGRATIONS.md` for complete integration details

---

## Data Processing Patterns

**Loading Data**:
```python
from scripts.core.data_helpers import load_parquet

df = load_parquet("L2_hdb_with_features")  # Uses metadata.json
```

**Saving Data**:
```python
from scripts.core.data_helpers import save_parquet

save_parquet(
    df,
    dataset_name="L3_unified_dataset",
    source="L2_hdb_with_features + L2_ura_with_features"
)
# Automatically updates metadata.json
```

**DataFrame Operations**:
- Always validate non-empty: `if df.empty: raise ValueError(...)`
- Use method chaining for readability
- Type hint all functions: `def process(df: pd.DataFrame) -> pd.DataFrame`

---

## Frontend/Backend Separation

**Data Processing** (Python):
- Location: `scripts/`
- Output: Parquet files → `data/parquets/`

**Dashboard** (Astro/React):
- Location: `app/`
- Data source: JSON files in `app/public/data/`
- Generated by: `scripts/prepare_webapp_data.py`

**Analytics Webapp**:
- Location: `backend/`
- Data source: JSON files in `backend/public/data/`

**Key Principle**: Python scripts process data and export JSONs; frontend only reads JSONs (no backend API).

---

## Critical Files Reference

| Purpose | File |
|---------|------|
| **Main Pipeline** | `scripts/run_pipeline.py` |
| **Configuration** | `scripts/core/config.py` |
| **Data I/O** | `scripts/core/data_helpers.py` |
| **Geocoding** | `scripts/core/geocoding.py` |
| **Webapp Data** | `scripts/prepare_webapp_data.py` |
| **Metadata** | `data/metadata.json` |
| **Environment** | `.env` (from `.env.example`) |
| **Test Config** | `pyproject.toml` |
| **Planning Docs** | `.planning/codebase/*.md` |

**Planning Documentation** (detailed reference):
- `.planning/codebase/ARCHITECTURE.md` - System architecture
- `.planning/codebase/CONVENTIONS.md` - Coding patterns
- `.planning/codebase/CONCERNS.md` - Known issues
- `.planning/codebase/TESTING.md` - Testing strategy
- `.planning/codebase/INTEGRATIONS.md` - External services
- `.planning/codebase/STACK.md` - Technology stack
- `.planning/codebase/STRUCTURE.md` - Directory structure
