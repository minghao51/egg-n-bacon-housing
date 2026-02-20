# Usage Guide

**Last Updated**: 2026-02-20 | **Status**: Production Ready

---

## 📋 Overview

This guide helps you get started with the egg-n-bacon-housing project.

**What You'll Learn**:
- How to set up the development environment
- How to run the data pipeline
- How to work with notebooks and data
- Common workflows and tasks

**Prerequisites**:
- Basic Python knowledge
- Command line familiarity
- 5-10 minutes for initial setup

---

## 🚀 Quick Start

### Step 1: Install uv (One-Time)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**What is uv?**: A fast Python package manager (10-100x faster than pip)

---

### Step 2: Install Dependencies

```bash
# Clone repository (if not already done)
git clone <repo-url>
cd egg-n-bacon-housing

# Install all dependencies
uv sync
```

**This installs**:
- Python 3.11+
- Data science libraries (pandas, geopandas, etc.)
- Testing framework (pytest)
- Jupyter notebooks
- All project dependencies

---

### Step 3: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: ONEMAP_EMAIL
# Optional: GOOGLE_API_KEY
```

**Required API Keys**:

| API Key | Required? | Purpose | How to Get |
|---------|-----------|---------|------------|
| **ONEMAP_EMAIL** | ✅ Yes | Geocoding addresses | Register at [onemap.gov.sg](https://www.onemap.gov.sg/apidocs/register) |
| **GOOGLE_API_KEY** | Optional | Geocoding fallback | [Google Cloud Console](https://makersuite.google.com/app/apikey) |

**Why OneMap?**: Singapore-specific geocoding service, free, more accurate than Google for local addresses

---

### Step 4: Verify Setup

```bash
# Run tests to verify installation
uv run pytest

# Expected output: All tests pass ✓
```

**If tests fail**:
- Check Python version: `python --version` (should be 3.11+)
- Check `.env` file exists and is configured
- Try `uv sync --upgrade` to update dependencies

---

### Step 5: Run the Pipeline

```bash
# Run the full pipeline (L0 → L1 → L2)
uv run python scripts/run_pipeline.py
```

**Expected runtime**: 20-30 minutes (depends on data size)

**What this does**:
1. Fetches data from Singapore government APIs
2. Geocodes addresses
3. Calculates distances and features
4. Generates summary metrics

---

## 🔄 Running the Pipeline

### Full Pipeline (Recommended)

```bash
uv run python scripts/run_pipeline.py
```

**Stages**: L0 (Collection) → L1 (Processing) → L2 (Features) → L3 (Metrics)

**Runtime**: 20-30 minutes

**Output**: Data in `data/parquets/` directory

---

### Individual Stages

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

### Skip Completed Stages

The pipeline automatically skips completed stages. To force re-run:

```bash
# Remove specific output
rm data/parquets/L1/L1_hdb_transaction.parquet

# Re-run pipeline (will only re-run L1)
uv run python scripts/run_pipeline.py
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

## 📓 Working with Notebooks

### Jupytext Pairing

All notebooks are paired with `.py` files via Jupytext for git-friendly version control.

```
notebooks/
├── L0_datagovsg.ipynb    # Jupyter notebook (for visualization)
├── L0_datagovsg.py       # Paired Python file (for editing)
├── L1_ura_transactions_processing.ipynb
├── L1_ura_transactions_processing.py
└── ...
```

---

### Recommended Workflow

**1. Edit .py file in your IDE** (recommended)
```bash
# Open in VS Code
code notebooks/L0_datagovsg.py

# Run directly
uv run python notebooks/L0_datagovsg.py
```

**2. Sync to .ipynb if needed** (for visualization)
```bash
cd notebooks
uv run jupytext --sync L0_datagovsg.ipynb
```

**3. Launch Jupyter for interactive work**
```bash
uv run jupyter notebook
# or
uv run jupyter lab
```

**Why This Workflow?**
- ✅ `.py` files show clean diffs in git
- ✅ IDE support (autocomplete, refactoring)
- ✅ Easy code review
- ✅ Can run without Jupyter installed
- ✅ `.ipynb` for visualizations and exploratory analysis

---

## 📊 Loading Data

### Load a Dataset

```python
from scripts.core.data_helpers import load_parquet

# Load by dataset name (not full path)
df = load_parquet("L2_hdb_with_features")

# Inspect the data
print(df.head())
print(df.info())
print(df.describe())
```

---

### List Available Datasets

```python
from scripts.core.data_helpers import list_datasets

# Get all datasets
datasets = list_datasets()

# Print summary
for name, metadata in datasets.items():
    print(f"{name}: {metadata['rows']:,} rows, {metadata['columns']} cols")
```

---

### Common Datasets

| Dataset Name | Description | Rows | Columns |
|--------------|-------------|------|---------|
| `L2_hdb_with_features` | HDB transactions with features | ~150K | 45 |
| `L2_ura_with_features` | Private property with features | ~80K | 50 |
| `L3_market_summary` | Aggregated market metrics | ~5K | 20 |
| `L2_rental_yield` | Rental yield calculations | ~10K | 15 |

---

### Filter and Query Data

```python
# Filter by property type
hdb = df[df['property_type'] == 'HDB']

# Filter by date range
recent = df[df['transaction_date'] >= '2024-01-01']

# Filter by town
btoan = df[df['town'] == 'Bishan']

# Calculate median price by town
median_prices = df.groupby('town')['resale_price'].median()
```

---

## 🧪 Testing & Quality

### Run Tests

```bash
# All tests
uv run pytest

# Verbose output
uv run pytest -v

# Unit tests only (fast)
uv run pytest -m unit

# Skip slow tests
uv run pytest -m "not slow"

# With coverage
uv run pytest --cov=scripts/core
```

---

### Code Quality

```bash
# Check linting
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix

# Format code
uv run ruff format .

# Check formatting without making changes
uv run ruff format --check .
```

---

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Wrong directory | Run from project root with `uv run` |
| `Dataset 'X' not found` | Missing data | Run preceding pipeline stages |
| `429 Too Many Requests` | API rate limit | Wait (built-in delays) |
| `.env not loading` | Environment issues | Restart Python process |
| `ImportError` | Missing dependency | Run `uv sync` |

---

## 🛠️ Common Workflows

### Workflow 1: Add a New Feature

```bash
# 1. Create feature branch
git checkout -b feature/new-analysis

# 2. Make changes
code scripts/analytics/analysis/market/new_analysis.py

# 3. Test changes
uv run pytest tests/analytics/

# 4. Format code
uv run ruff format .
uv run ruff check .

# 5. Commit changes
git add .
git commit -m "feat: add new market analysis"

# 6. Push and create PR
git push origin feature/new-analysis
```

---

### Workflow 2: Update Data

```bash
# 1. Pull latest changes
git pull origin main

# 2. Run pipeline
uv run python scripts/run_pipeline.py

# 3. Verify outputs
uv run pytest tests/

# 4. Commit updated data (if manual data added)
git add data/manual/
git commit -m "data: update manual data"
```

---

### Workflow 3: Run Analysis

```bash
# 1. Load data
python -c "from scripts.core.data_helpers import load_parquet; df = load_parquet('L2_hdb_with_features'); print(df.info())"

# 2. Run analysis script
uv run python scripts/analytics/analysis/market/analyze_appreciation_patterns.py

# 3. View results
open data/analysis/appreciation_patterns/overview.png
```

---

### Workflow 4: Debug Test Failure

```bash
# 1. Run with verbose output
uv run pytest -v tests/core/test_config.py

# 2. Run specific test
uv run pytest tests/core/test_config.py::TestConfigPaths::test_base_dir_exists

# 3. Drop into debugger
uv run pytest --pdb

# 4. Show print statements
uv run pytest -v -s
```

---

## 📚 Quick Reference

### Essential Commands

| Task | Command |
|------|---------|
| **Install deps** | `uv sync` |
| **Run tests** | `uv run pytest` |
| **Run pipeline** | `uv run python scripts/run_pipeline.py` |
| **Load data** | `load_parquet("dataset_name")` |
| **Linting** | `uv run ruff check .` |
| **Format** | `uv run ruff format .` |
| **Jupyter** | `uv run jupyter notebook` |

---

### File Locations

| What | Where |
|------|--------|
| **Raw data** | `data/parquets/raw_data/` |
| **Processed data** | `data/parquets/L1/`, `L2/`, `L3/` |
| **Analysis outputs** | `data/analysis/` |
| **Configuration** | `scripts/core/config.py` |
| **Environment** | `.env` |
| **Tests** | `tests/` |

---

### Getting Help

| Issue | See |
|-------|-----|
| **System design** | [Architecture Guide](./architecture.md) |
| **Testing** | [Testing Guide](./testing-guide.md) |
| **Data schema** | [Data Reference](./guides/data-reference.md) |
| **Analysis** | [Analytics Docs](./analytics/) |
| **Pipeline stages** | [L4 Analysis Pipeline](./guides/l4-analysis-pipeline.md) |

---

## 🎯 Next Steps

1. **Explore the data**: Use `load_parquet()` to inspect available datasets
2. **Read analytics docs**: Check `docs/analytics/` for market insights
3. **Run analysis scripts**: Try scripts in `scripts/analytics/analysis/`
4. **Customize**: Add your own analysis or features

**Happy analyzing! 📊**
