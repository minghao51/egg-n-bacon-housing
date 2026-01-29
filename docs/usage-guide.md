# Usage Guide - Egg-n-Bacon-Housing

**Status**: Production Ready

---

## Quick Start

```bash
# Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Verify setup
uv run pytest

# Run the pipeline
uv run python run_real_pipeline.py
```

Estimated setup time: 5-10 minutes

---

## Environment Setup

### API Keys Required

**OneMap API** (Required for L1 processing):
- Register: https://www.onemap.gov.sg/apidocs/register
- Fields: `ONEMAP_EMAIL`, `ONEMAP_EMAIL_PASSWORD`

**Google AI API** (Optional, for agents):
- Register: https://makersuite.google.com/app/apikey
- Field: `GOOGLE_API_KEY`

### Configure .env

```bash
cp .env.example .env
```

---

## Running the Pipeline

### Automated Guide (Recommended)

```bash
uv run python run_real_pipeline.py
```

This checks .env, runs L0→L1→L2 notebooks in order, and shows results.

### Manual Execution

**L0: Data Collection** (~10-15 min)
```bash
uv run python notebooks/L0_datagovsg.py
uv run python notebooks/L0_onemap.py
uv run python notebooks/L0_wiki.py
```

**L1: Data Processing** (~10-15 min)
```bash
uv run python notebooks/L1_ura_transactions_processing.py
uv run python notebooks/L1_utilities_processing.py
```

**L2: Feature Engineering** (~5 min)
```bash
uv run python notebooks/L2_sales_facilities.py
```

---

## Working with Notebooks

All notebooks are paired with `.py` files via Jupytext.

**Edit .py files** (recommended for version control):
```bash
code notebooks/L0_datagovsg.py
uv run python notebooks/L0_datagovsg.py
cd notebooks && uv run jupytext --sync L0_datagovsg.ipynb
```

**Use Jupyter** (for visualization):
```bash
uv run jupyter notebook
```

---

## Loading Data

```python
from core.data_helpers import load_parquet

# Load a dataset
df = load_parquet("L1_housing_condo_transaction")

# List all datasets
from core.data_helpers import list_datasets
datasets = list_datasets()
```

---

## Running Tests

```bash
uv run pytest           # All tests
uv run pytest -v        # Verbose output
uv run ruff check .     # Linting
uv run ruff format .    # Format code
```

---

## Running Apps

```bash
uv run streamlit run apps/single_agent.py   # Agent chat
uv run streamlit run apps/spiral.py         # Dashboard
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ModuleNotFoundError | Run from project root with `uv run` |
| 429 Too Many Requests | Wait, pipeline has built-in delays |
| Dataset not found | Run preceding notebooks first |
| .env not loading | Restart Python process |

---

## Key Commands Reference

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Run tests | `uv run pytest` |
| Run pipeline | `uv run python run_real_pipeline.py` |
| Load data | `load_parquet("name")` |
| Linting | `uv run ruff check .` |

---

**See also:** [architecture.md](architecture.md) for system design
