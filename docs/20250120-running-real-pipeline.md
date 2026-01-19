# Running the Real Data Pipeline - Quick Guide

**Date**: 2025-01-20
**Status**: Ready for execution

---

## Prerequisites

### 1. API Keys Required

You'll need to register for these free APIs:

#### OneMap API (Required for L1)
- **Register**: https://www.onemap.gov.sg/apidocs/register
- **Email**: Your email address
- **Password**: Choose a password
- **Free**: Yes, completely free

#### Google AI API (Optional, for agents)
- **Register**: https://makersuite.google.com/app/apikey
- **Purpose**: LangChain agents
- **Free tier**: Available

### 2. Setup .env File

```bash
# Create .env from example
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

Add your credentials:
```bash
ONEMAP_EMAIL=your_email@example.com
ONEMAP_EMAIL_PASSWORD=your_password
GOOGLE_API_KEY=your_google_api_key
```

---

## Running the Pipeline

### Option 1: Automated Guide (Recommended)

```bash
# Run the interactive guide
uv run python run_real_pipeline.py
```

This will:
- ✅ Check if .env is configured
- ✅ Guide you through each level (L0, L1, L2)
- ✅ Run notebooks in correct order
- ✅ Show results when complete

### Option 2: Manual Execution

#### L0: Data Collection

```bash
# Collect data from data.gov.sg
uv run python notebooks/L0_datagovsg.py

# Collect data from OneMap
uv run python notebooks/L0_onemap.py

# Collect data from Wikipedia
uv run python notebooks/L0_wiki.py
```

#### L1: Data Processing

```bash
# Process URA transactions
uv run python notebooks/L1_ura_transactions_processing.py

# Process utilities and amenities
uv run python notebooks/L1_utilities_processing.py
```

#### L2: Feature Engineering

```bash
# Engineer features
uv run python notebooks/L2_sales_facilities.py
```

---

## What Each Level Does

### L0: Data Collection (~10 minutes)

**Collects raw data from APIs:**

1. **data.gov.sg API**
   - General sale statistics
   - Rental indices
   - Price indices
   - HDB resale transactions (2015 onwards)
   - Private property transactions

2. **OneMap API**
   - Planning area names
   - Household income data

3. **Wikipedia**
   - Shopping mall list

**Output**: 12+ raw datasets (~100K rows total)

### L1: Data Processing (~10-15 minutes)

**Processes and cleans data:**

1. **URA Transactions**
   - Cleans transaction data
   - Calculates price per sqft
   - Standardizes property types
   - Removes duplicates

2. **Utilities & Amenities**
   - Geocodes addresses via OneMap
   - Queries nearby amenities
   - Calculates distances
   - Enriches with locations

**Rate Limiting**: OneMap API allows ~1 request/second

**Output**: 9 processed datasets with enriched data

### L2: Feature Engineering (~5 minutes)

**Creates features for analysis:**

- Distance features (MRT, CBD, amenities)
- Aggregation features (counts within 1km, 2km)
- Temporal features (month, year, day of week)
- Interaction features (price × distance, etc.)

**Output**: 5 feature-rich datasets

---

## Monitoring Progress

### Check Metadata

```python
from src.data_helpers import list_datasets

datasets = list_datasets()
for name, info in datasets.items():
    print(f"{name}: {info['rows']} rows")
```

### Verify Data Quality

```python
from src.data_helpers import load_parquet, verify_metadata

# Verify all checksums
is_valid = verify_metadata()
print(f"All datasets valid: {is_valid}")

# Load a dataset
df = load_parquet("L1_housing_condo_transaction")
print(df.head())
print(df.describe())
```

---

## Troubleshooting

### Issue: API Rate Limiting

**Error**: `429 Too Many Requests`

**Solution**:
- The pipeline has built-in delays
- Wait a few minutes and retry
- Check API quota limits

### Issue: OneMap Authentication Failed

**Error**: `Authentication failed`

**Solution**:
- Verify ONEMAP_EMAIL and ONEMAP_EMAIL_PASSWORD in .env
- Check you've registered at https://www.onemap.gov.sg/apidocs/register
- Try logging in via web interface first

### Issue: Dataset Not Found

**Error**: `Dataset 'xxx' not found in metadata`

**Solution**:
- Run preceding notebooks first
- Check data/metadata.json for dependencies
- Verify the dataset was created

### Issue: Geocoding Failures

**Error**: `Failed to geocode postal code`

**Solution**:
- Check OneMap API status
- Verify postal code format
- Some postal codes may not exist

---

## Expected Results

### After L0
- ~12 datasets in metadata
- ~100K rows total
- Files in `data/parquets/raw_data/`

### After L1
- ~9 additional datasets
- Cleaned, geocoded data
- Files in `data/parquets/L1/`

### After L2
- ~5 feature datasets
- ML-ready features
- Files in `data/parquets/L2/` and `L3/`

### Total
- **~26 datasets**
- **~100K+ rows**
- **Complete pipeline data**

---

## Pipeline Validation

### Run Tests

```bash
# Unit tests
uv run pytest

# Pipeline setup test
uv run python test_pipeline_setup.py

# Both should pass ✅
```

### Verify Integrity

```python
from src.data_helpers import verify_metadata

is_valid = verify_metadata()
assert is_valid, "Some datasets are corrupted!"
```

---

## Next Steps

After pipeline completes:

1. **Explore Data**
   ```python
   from src.data_helpers import load_parquet
   df = load_parquet("L3_property")
   ```

2. **Run Analysis**
   - Use Jupyter notebooks for exploration
   - Build ML models on features
   - Create visualizations

3. **Export Data** (Optional)
   ```bash
   uv run python notebooks/L3_upload_s3.py
   ```

4. **Use with Agents**
   - Run Streamlit apps
   - Query with LangChain agents
   - Build custom tools

---

## Performance Tips

### Speed Up Data Loading

```python
# Load only needed columns
from src.data_helpers import load_parquet
import pandas as pd

# Load specific columns
df = pd.read_parquet(
    "data/parquets/L1/housing_condo_transaction.parquet",
    columns=['property_id', 'price', 'floor_size']
)
```

### Cache API Responses

The pipeline caches geocoding results automatically. Subsequent runs will be much faster.

---

## Estimated Time

| Level | Time | Dependencies |
|-------|------|--------------|
| L0: Data Collection | 10-15 min | None |
| L1: Data Processing | 10-15 min | L0 |
| L2: Feature Engineering | 5 min | L1 |
| **Total** | **25-35 min** | |

**First run**: Slowest (API calls, geocoding)
**Subsequent runs**: Much faster (cached data)

---

## Support

### Issues?
1. Check [docs/20250120-data-pipeline.md](docs/20250120-data-pipeline.md)
2. Check [docs/20250120-pipeline-test-results.md](docs/20250120-pipeline-test-results.md)
3. Run `uv run pytest` to verify setup

### Logs
- Check console output for errors
- Pipeline logs INFO-level messages
- Check data/metadata.json for state

---

**Ready to run?**

```bash
uv run python run_real_pipeline.py
```

Good luck! 🚀
