# Usage Guide - Egg-n-Bacon-Housing

**Last Updated**: 2025-01-20
**Status**: ✅ Production Ready

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Environment Setup](#environment-setup)
3. [Running Tests](#running-tests)
4. [Running the Data Pipeline](#running-the-data-pipeline)
5. [Working with Notebooks](#working-with-notebooks)
6. [Using the Data](#using-the-data)
7. [Running Applications](#running-applications)
8. [Common Tasks](#common-tasks)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### For New Users

```bash
# 1. Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys (see below)

# 4. Verify setup
uv run pytest

# 5. Run the pipeline (when ready)
uv run python run_real_pipeline.py
```

### Estimated Setup Time: 5-10 minutes

---

## Environment Setup

### 1. Install uv

**macOS/Linux**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows**:
```bash
powershell -c "irm https://astral.sh/uv/install.sh | iex"
```

### 2. Get API Keys

#### OneMap API (Required)
- **URL**: https://www.onemap.gov.sg/apidocs/register
- **Cost**: Free
- **Purpose**: Geocoding, planning areas, amenities data
- **Fields needed**:
  - `ONEMAP_EMAIL`
  - `ONEMAP_EMAIL_PASSWORD`

#### Google AI API (Optional)
- **URL**: https://makersuite.google.com/app/apikey
- **Cost**: Free tier available
- **Purpose**: LangChain agents
- **Fields needed**:
  - `GOOGLE_API_KEY`

#### Supabase (Optional)
- **URL**: https://supabase.com/
- **Cost**: Free tier available
- **Purpose**: Database export
- **Fields needed**:
  - `SUPABASE_URL`
  - `SUPABASE_KEY`

### 3. Configure .env File

```bash
# Create from template
cp .env.example .env

# Edit with your editor
nano .env  # or code .env, vim .env, etc.
```

Add your credentials:
```bash
# Required for L1 processing
ONEMAP_EMAIL=your_email@example.com
ONEMAP_EMAIL_PASSWORD=your_password

# Optional (for agents)
GOOGLE_API_KEY=your_google_api_key

# Optional (for database export)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Optional (for web scraping)
JINA_AI=your_jina_ai_key
```

**Security Note**: `.env` is git-ignored and never committed.

---

## Running Tests

### Unit Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_data_helpers.py

# Run with coverage
uv run pytest --cov=src
```

### Pipeline Tests

```bash
# Test pipeline infrastructure
uv run python test_pipeline_setup.py

# Run demo pipeline (no API calls)
uv run python demo_pipeline.py
```

### Linting

```bash
# Check code quality
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

---

## Running the Data Pipeline

### Option 1: Interactive Guide (Recommended)

```bash
uv run python run_real_pipeline.py
```

**Features**:
- ✅ Checks if .env is configured
- ✅ Guides you through L0 → L1 → L2
- ✅ Runs notebooks in correct order
- ✅ Shows results when complete
- ✅ Handles errors gracefully

### Option 2: Manual Execution

#### L0: Data Collection (10-15 minutes)

Collects raw data from external APIs:

```bash
# data.gov.sg API
uv run python notebooks/L0_datagovsg.py

# OneMap API
uv run python notebooks/L0_onemap.py

# Wikipedia scraping
uv run python notebooks/L0_wiki.py
```

**Expected Output**: 12+ raw datasets (~100K rows)

#### L1: Data Processing (10-15 minutes)

Processes and cleans data:

```bash
# URA transaction processing
uv run python notebooks/L1_ura_transactions_processing.py

# Utilities processing (geocoding, amenities)
uv run python notebooks/L1_utilities_processing.py
```

**Expected Output**: 9 processed datasets with geocoded locations

**Rate Limiting**: OneMap API allows ~1 request/second (built-in delays)

#### L2: Feature Engineering (5 minutes)

Creates features for ML/analysis:

```bash
# Feature engineering
uv run python notebooks/L2_sales_facilities.py
```

**Expected Output**: 5 feature-rich datasets

#### L3: Export (Optional)

Exports to S3/Supabase:

```bash
# Export to S3 and/or Supabase
uv run python notebooks/L3_upload_s3.py
```

### Monitoring Progress

```python
# Check current datasets
from core.data_helpers import list_datasets

datasets = list_datasets()
for name, info in datasets.items():
    print(f"{name}: {info['rows']} rows")
```

---

## Working with Notebooks

### Using Jupytext (Recommended)

All notebooks are paired with `.py` files for better version control.

#### Edit .py Files (Best Practice)

```bash
# Edit in VS Code
code notebooks/L0_datagovsg.py

# Run the file
uv run python notebooks/L0_datagovsg.py

# Sync back to .ipynb
cd notebooks
uv run jupytext --sync L0_datagovsg.ipynb
```

**Benefits**:
- ✅ Full IDE support (autocomplete, linting)
- ✅ Clean git diffs
- ✅ Better refactoring tools
- ✅ Faster editing experience

#### Use Jupyter Notebooks

```bash
# Start Jupyter
uv run jupyter notebook

# Open notebook in browser
# Edit cells, run them, etc.
```

**Best for**:
- Exploratory data analysis
- Visualization
- Debugging
- Interactive development

### Syncing Notebooks

```bash
# Manual sync (if automatic doesn't work)
cd notebooks
uv run jupytext --sync notebook_name.ipynb

# Sync all notebooks
cd notebooks
uv run jupytext --sync *.ipynb
```

---

## Using the Data

### Loading Datasets

```python
from core.data_helpers import load_parquet

# Load a dataset
df = load_parquet("L1_housing_condo_transaction")

# Load specific version (if available)
df = load_parquet("L1_housing_condo_transaction", version="2025-01-20")

# Load with pandas directly (for performance)
import pandas as pd
df = pd.read_parquet("data/parquets/L1/housing_condo_transaction.parquet")
```

### Saving Datasets

```python
from core.data_helpers import save_parquet
import pandas as pd

# Create or process data
df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})

# Save with metadata
save_parquet(
    df,
    "my_processed_data",
    source="L1_housing_condo_transaction"
)
```

### Listing Datasets

```python
from core.data_helpers import list_datasets

# Get all datasets
datasets = list_datasets()

# Print summary
for name, info in datasets.items():
    print(f"{name}:")
    print(f"  Rows: {info['rows']}")
    print(f"  Version: {info['version']}")
    print(f"  Source: {info['source']}")
    print()
```

### Verifying Data Integrity

```python
from core.data_helpers import verify_metadata

# Verify all checksums
is_valid = verify_metadata()
print(f"All datasets valid: {is_valid}")
```

---

## Running Applications

### Streamlit Apps

```bash
# Agent chat interface
uv run streamlit run apps/single_agent.py

# Enhanced agent with memory
uv run streamlit run apps/single_agent2.py

# Data visualization dashboard
uv run streamlit run apps/spiral.py

# Alternative dashboard
uv run streamlit run apps/spiral3.py
```

### Custom Scripts

```bash
# Run any Python script with uv
uv run python my_script.py
```

---

## Common Tasks

### Task 1: Check What Data Exists

```python
from core.data_helpers import list_datasets

datasets = list_datasets()
print(f"Total datasets: {len(datasets)}")
for name in datasets.keys():
    print(f"  - {name}")
```

### Task 2: Load and Explore Data

```python
from core.data_helpers import load_parquet
import pandas as pd

# Load data
df = load_parquet("L3_property")

# Basic exploration
print(df.head())
print(df.describe())
print(df.info())

# Check columns
print(df.columns.tolist())
```

### Task 3: Filter Data

```python
import pandas as pd
from core.data_helpers import load_parquet

df = load_parquet("L1_housing_condo_transaction")

# Filter by price
expensive = df[df['price_sgd'] > 1000000]

# Filter by type
condos = df[df['property_type'] == 'CONDO']

# Filter by year
recent = df[df['year'] >= 2020]
```

### Task 4: Calculate Statistics

```python
import pandas as pd
from core.data_helpers import load_parquet

df = load_parquet("L1_housing_condo_transaction")

# Average price
avg_price = df['price_sgd'].mean()

# Price by type
price_by_type = df.groupby('property_type')['price_sgd'].mean()

# Count by planning area
count_by_area = df['planning_area'].value_counts()
```

### Task 5: Merge Datasets

```python
import pandas as pd
from core.data_helpers import load_parquet

# Load two datasets
transactions = load_parquet("L1_housing_condo_transaction")
amenities = load_parquet("L1_mall_queried")

# Merge on postal code
merged = transactions.merge(
    amenities,
    on='postal_code',
    how='left'
)
```

### Task 6: Export to CSV

```python
import pandas as pd
from core.data_helpers import load_parquet

df = load_parquet("L3_property")
df.to_csv("output.csv", index=False)
```

### Task 7: Create a Simple Plot

```python
import pandas as pd
import matplotlib.pyplot as plt
from core.data_helpers import load_parquet

df = load_parquet("L1_housing_condo_transaction")

# Price distribution
plt.figure(figsize=(10, 6))
df['price_sgd'].hist(bins=50)
plt.title('Property Price Distribution')
plt.xlabel('Price (SGD)')
plt.ylabel('Count')
plt.show()

# Price over time
df.groupby('year')['price_sgd'].mean().plot()
plt.title('Average Price Over Time')
plt.xlabel('Year')
plt.ylabel('Average Price (SGD)')
plt.show()
```

---

## Troubleshooting

### Issue: Module Not Found

**Error**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_helpers import load_parquet
```

Or use from notebooks:
```python
import sys
sys.path.append('../src')

from core.data_helpers import load_parquet
```

### Issue: Dataset Not Found

**Error**: `Dataset 'xxx' not found in metadata`

**Solution**:
1. Run the preceding notebooks first
2. Check `data/metadata.json` for dependencies
3. Verify the dataset was created

```python
from core.data_helpers import list_datasets
datasets = list_datasets()
print(list(datasets.keys()))
```

### Issue: API Rate Limiting

**Error**: `429 Too Many Requests`

**Solution**:
1. Wait a few minutes
2. The pipeline has built-in delays
3. Check API quota limits

### Issue: .env File Not Loading

**Error**: API keys are None/empty

**Solution**:
```bash
# Check .env exists
ls -la .env

# Verify it's not empty
cat .env

# Restart your Python process (environment variables loaded at import)
```

### Issue: Jupytext Sync Problems

**Error**: .ipynb and .py files out of sync

**Solution**:
```bash
cd notebooks
uv run jupytext --sync notebook_name.ipynb
```

### Issue: Tests Failing

**Error**: pytest failures

**Solution**:
```bash
# Reinstall dependencies
uv sync

# Run with verbose output
uv run pytest -v

# Check specific test
uv run pytest tests/test_config.py -v
```

### Issue: Git Conflicts with Jupytext

**Error**: Merge conflicts in .ipynb files

**Solution**:
```bash
# Resolve conflicts in .py file instead
# Then sync back to .ipynb
uv run jupytext --sync notebook_name.ipynb
```

---

## Performance Tips

### 1. Use Column Pruning

```python
# Only load needed columns
import pandas as pd
df = pd.read_parquet(
    "data/parquets/L1/housing_condo_transaction.parquet",
    columns=['property_id', 'price_sgd', 'floor_size_sqft']
)
```

### 2. Use Filtering

```python
# Filter before loading
import pandas as pd
df = pd.read_parquet(
    "data/parquets/L1/housing_condo_transaction.parquet",
    filters=[('year', '>=', 2020)]
)
```

### 3. Cache Results

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def expensive_operation(param):
    # Cached result
    return result
```

### 4. Use Chunking for Large Data

```python
# Process in chunks
chunk_size = 10000
for chunk in pd.read_parquet('large_file.parquet', chunksize=chunk_size):
    process(chunk)
```

---

## Best Practices

### 1. Always Use `uv run`

```bash
# Good
uv run python script.py
uv run pytest
uv run jupyter notebook

# Bad (activates venv manually)
source .venv/bin/activate
python script.py
```

### 2. Edit .py Files, Not .ipynb

- Better version control
- Full IDE support
- Easier code review
- Clean git diffs

### 3. Check Metadata Before Using Data

```python
from core.data_helpers import list_datasets, verify_metadata

# Verify integrity
assert verify_metadata(), "Some datasets corrupted!"

# Check what's available
datasets = list_datasets()
```

### 4. Use Config Module

```python
# Good
from core.config import Config
data_dir = Config.DATA_DIR

# Bad (hardcoded paths)
data_dir = "../data"
```

### 5. Run Tests Before Committing

```bash
uv run pytest
uv run ruff check .
```

---

## Learning Resources

### For New Users

1. **Read First**: [CLAUDE.md](../CLAUDE.md) - Development principles
2. **Then**: [docs/20250120-architecture.md](20250120-architecture.md) - System design
3. **Then**: [docs/20250120-data-pipeline.md](20250120-data-pipeline.md) - Pipeline details
4. **Finally**: [docs/20250120-running-real-pipeline.md](20250120-running-real-pipeline.md) - Execution guide

### Quick Reference

| Task | Command | File |
|------|---------|------|
| Setup | `uv sync` | pyproject.toml |
| Test | `uv run pytest` | tests/ |
| Pipeline | `uv run python run_real_pipeline.py` | run_real_pipeline.py |
| Load data | `load_parquet("name")` | core/data_helpers.py |
| Config | `Config.DATA_DIR` | core/config.py |

---

## Getting Help

### Documentation

- **Architecture**: [docs/20250120-architecture.md](20250120-architecture.md)
- **Pipeline**: [docs/20250120-data-pipeline.md](20250120-data-pipeline.md)
- **Migration**: [docs/20250120-migration-summary.md](20250120-migration-summary.md)
- **Test Results**: [docs/20250120-pipeline-test-results.md](20250120-pipeline-test-results.md)

### Troubleshooting

1. Check [docs/20250120-running-real-pipeline.md](20250120-running-real-pipeline.md)
2. Run `uv run pytest` to verify setup
3. Check `data/metadata.json` for dataset status
4. Review error messages carefully

### Support

- **Issues**: Create a GitHub issue
- **Questions**: Check documentation first
- **Notion**: [Internal docs (invite only)](https://www.notion.so/Housing-Agents-App-0c4bdd40940542b2bcd366207428e517?pvs=4)

---

## Summary

**Key Commands**:
```bash
uv sync                          # Install dependencies
uv run pytest                    # Run tests
uv run python run_real_pipeline.py  # Run pipeline
uv run jupyter notebook          # Start Jupyter
uv run streamlit run apps/*.py   # Run apps
```

**Key Modules**:
```python
from core.config import Config           # Configuration
from core.data_helpers import (          # Data management
    load_parquet,
    save_parquet,
    list_datasets,
    verify_metadata
)
```

**Ready to use!** 🚀

---

**Last Updated**: 2025-01-20
**Maintained By**: Development Team
