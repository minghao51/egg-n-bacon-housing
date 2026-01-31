# L2 Data Pipeline Guide

**Last Updated:** 2026-01-22

---

## Overview

The L2 Data Pipeline automates the download and processing of rental data from Singapore government sources (data.gov.sg). It integrates both HDB and URA rental data and calculates rental yields for housing market analysis.

---

## Pipeline Steps

### Step 1: Download HDB Rental Data
- **Source:** HDB "Renting Out of Flats from Jan 2021" dataset
- **Records:** 184,915 rental transactions
- **Frequency:** Updates monthly
- **Freshness Threshold:** 30 days (skips download if data is < 30 days old)
- **Output:** `data/parquets/L1/housing_hdb_rental.parquet`

### Step 2: Download URA Rental Index
- **Source:** URA "Private Residential Property Rental Index" dataset
- **Records:** 505 index values
- **Frequency:** Updates quarterly
- **Freshness Threshold:** 90 days (skips download if data is < 90 days old)
- **Output:** `data/parquets/L1/housing_ura_rental_index.parquet`

### Step 3: Calculate Rental Yields
- **Input:** HDB rentals, URA index, transaction data
- **Processing:**
  - HDB: Direct calculation from rental/transaction prices
  - Condo: Index-based estimation using region mapping
- **Output:** `data/parquets/L2/rental_yield.parquet`
- **Records:** 1,526 yield calculations

---

## Usage

### Basic Execution

```bash
# Run pipeline (skips downloads if data is fresh)
PYTHONPATH=. uv run python scripts/run_l2_pipeline.py
```

### Force Re-download

```bash
# Force re-download even if data is fresh
PYTHONPATH=. uv run python scripts/run_l2_pipeline.py --force
```

### Expected Output

```
============================================================
L2 Data Pipeline
============================================================
Started at: 2026-01-22 13:42:35

============================================================
Step 1: HDB Rental Data
============================================================
✓ HDB rental data is fresh (< 30 days old)
  Skipping download. Use --force to re-download.

============================================================
Step 2: URA Rental Index
============================================================
✓ URA rental index is fresh (< 90 days old)
  Skipping download. Use --force to re-download.

============================================================
Step 3: Calculate Rental Yields
============================================================
Loading HDB rental and transaction data...
✅ Calculated 1,499 HDB rental yields
✅ Calculated 27 Condo rental yields
✅ Saved 1,526 total records to data/parquets/L2/rental_yield.parquet

Summary:
  HDB: 1,499 records, 5.93% avg yield
  Condo: 27 records, 3.85% avg yield

============================================================
Pipeline Summary
============================================================
  hdb_rental: ✅ SUCCESS
  ura_rental: ✅ SUCCESS
  rental_yields: ✅ SUCCESS

✅ All pipeline steps completed successfully!
Finished at: 2026-01-22 13:42:35
============================================================
```

---

## Pipeline Features

### ✅ Smart Caching

The pipeline automatically checks data freshness:
- **HDB data:** Skips download if < 30 days old
- **URA data:** Skips download if < 90 days old

This prevents unnecessary API calls and speeds up execution.

### ✅ Error Handling

Each step is independent:
- Failures in one step don't prevent others from running
- Clear error messages with status indicators (✅/❌)
- Graceful degradation with warnings

### ✅ Data Validation

- Checks for required input files
- Validates data types and conversions
- Logs summary statistics after each step
- Returns success/failure status for each step

### ✅ Progress Logging

Detailed logging at each stage:
- Start/end timestamps
- Record counts
- Data quality metrics
- Success/failure indicators

---

## Data Outputs

### L1 Raw Data

**HDB Rental Data:**
```
data/parquets/L1/housing_hdb_rental.parquet
- 184,915 records
- Columns: rent_approval_date, town, block, street_name, flat_type, monthly_rent
- Date range: 2021-01 to 2025-12
- Size: ~2 MB
```

**URA Rental Index:**
```
data/parquets/L1/housing_ura_rental_index.parquet
- 505 records
- Columns: quarter, property_type, locality, index
- Date range: 2004Q1 to 2025Q3
- Size: ~20 KB
```

### L2 Processed Data

**Rental Yields:**
```
data/parquets/L2/rental_yield.parquet
- 1,526 records
- Columns: town, month, property_type, rental_yield_pct
- HDB: 1,499 records, 5.93% avg yield
- Condo: 27 records, 3.85% avg yield
- Size: ~50 KB
```

---

## Integration with ROI Score

The rental yield data from this pipeline is used by the enhanced ROI score calculation:

```python
from scripts.core.metrics import calculate_roi_score
import pandas as pd

# Load rental yields from L2 pipeline
rental_yield_df = pd.read_parquet('data/parquets/L2/rental_yield.parquet')

# Calculate ROI score with rental yield
roi_scores = calculate_roi_score(
    feature_df=feature_df,
    rental_yield_df=rental_yield_df  # ← Uses L2 output
)
```

**Weight in ROI Score:** 25%
- Price momentum: 30%
- **Rental yield: 25%** ← From L2 pipeline
- Infrastructure: 20%
- Amenities: 15%

---

## Troubleshooting

### Issue: Pipeline fails with "ModuleNotFoundError"

**Solution:**
```bash
# Make sure to include PYTHONPATH
PYTHONPATH=. uv run python scripts/run_l2_pipeline.py
```

### Issue: Downloads take too long

**Solution:**
The HDB download processes 184,915 records in batches of 10,000. This takes ~30-60 seconds depending on network speed. This is normal.

### Issue: "File is fresh" message but data is outdated

**Solution:**
```bash
# Force re-download to update data
PYTHONPATH=. uv run python scripts/run_l2_pipeline.py --force
```

### Issue: Rental yield calculation returns 0 records

**Solution:**
This usually means:
1. Transaction data is missing (check L1 files exist)
2. Date ranges don't overlap (check transaction dates)
3. Merge keys don't match (check town names, date formats)

Run with verbose logging to debug:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Scheduling

### Recommended Schedule

**Weekly:**
```bash
# Check for HDB rental updates (monthly dataset)
PYTHONPATH=. uv run python scripts/run_l2_pipeline.py
```

**Quarterly:**
```bash
# Force refresh all data after URA quarterly release
PYTHONPATH=. uv run python scripts/run_l2_pipeline.py --force
```

### Cron Job Example

```bash
# Run weekly on Sundays at 2 AM
0 2 * * 0 cd /path/to/egg-n-bacon-housing && PYTHONPATH=. uv run python scripts/run_l2_pipeline.py >> logs/l2_pipeline.log 2>&1
```

---

## Individual Scripts

The pipeline orchestrates three scripts that can also be run independently:

### Download HDB Rental Data

```bash
PYTHONPATH=. uv run python scripts/download_hdb_rental_data.py
```

**Function:** Downloads 184,915 HDB rental transactions in batches
**Runtime:** ~30 seconds
**Output:** `data/parquets/L1/housing_hdb_rental.parquet`

### Download URA Rental Index

```bash
PYTHONPATH=. uv run python scripts/download_ura_rental_index.py
```

**Function:** Downloads 505 URA rental index values
**Runtime:** ~2 seconds
**Output:** `data/parquets/L1/housing_ura_rental_index.parquet`

### Calculate Rental Yields

```bash
PYTHONPATH=. uv run python scripts/calculate_rental_yield.py
```

**Function:** Calculates rental yields from downloaded data
**Runtime:** ~5 seconds
**Output:** `data/parquets/L2/rental_yield.parquet`

---

## Code Reference

### Pipeline Script

**File:** `scripts/run_l2_pipeline.py`

**Main Function:**
```python
def main(force: bool = False):
    """Main pipeline execution.

    Args:
        force: Force re-download even if data is fresh
    """
```

**Key Functions:**
- `check_file_freshness()` - Checks if file is fresh enough
- `download_hdb_rental_data()` - Downloads HDB rentals
- `download_ura_rental_index()` - Downloads URA index
- `calculate_rental_yields()` - Calculates yields

### Individual Download Scripts

**HDB:** `scripts/download_hdb_rental_data.py`
- `download_hdb_rental_data()` - Main download function
- Batch processing: 10,000 records per batch
- API: data.gov.sg datastore_search

**URA:** `scripts/download_ura_rental_index.py`
- `download_ura_rental_index()` - Main download function
- Batch processing: 10,000 records per batch
- API: data.gov.sg datastore_search

### Yield Calculation Script

**File:** `scripts/calculate_rental_yield.py`

**Functions:**
- `calculate_hdb_rental_yield()` - Direct calculation from transactions
- `calculate_condo_rental_yield()` - Index-based estimation
- District-to-region mapping for condos

---

## Dependencies

### Python Packages
- `pandas` - Data manipulation
- `requests` - API calls
- `pyarrow` - Parquet I/O
- `numpy` - Numerical operations

### External APIs
- **data.gov.sg API:** Public API (no authentication required)
- **Dataset IDs:**
  - HDB: `d_c9f57187485a850908655db0e8cfe651`
  - URA: `d_8e4c50283fb7052a391dfb746a05c853`

### Internal Data Dependencies
- `data/parquets/L1/housing_hdb_transaction.parquet` (for yield calculation)
- `data/parquets/L1/housing_condo_transaction.parquet` (for yield calculation)

---

## Performance

### Execution Time

**With Fresh Data (cached):**
- Total: ~5 seconds
- Mostly yield calculation

**Force Re-download (cold start):**
- HDB download: ~30-60 seconds (185K records)
- URA download: ~2 seconds (505 records)
- Yield calculation: ~5 seconds
- **Total: ~40-70 seconds**

### Data Transfer

- **HDB:** ~8.5 MB (184K records × 6 columns)
- **URA:** ~15 KB (505 records × 4 columns)
- **Total download:** ~8.5 MB per full refresh

---

## Future Enhancements

### Planned Improvements

**Data Quality:**
- [ ] Add data validation checks (outliers, duplicates)
- [ ] Implement data versioning
- [ ] Add checksums for downloaded files

**Error Recovery:**
- [ ] Retry logic for failed downloads
- [ ] Partial download resume capability
- [ ] Fallback to cached data on API failure

**Monitoring:**
- [ ] Email notifications on pipeline failure
- [ ] Metrics dashboard (execution time, data quality)
- [ ] Automatic stale data alerts

**Features:**
- [ ] Add more data sources (commercial rentals)
- [ ] Historical backfilling for pre-2021 HDB data
- [ ] Condo actual rental transactions (vs index-based)

---

## Related Documentation

- **Rental Yield Integration:** `docs/20260122-rental-yield-integration.md`
- **Rental Data Summary:** `docs/20260122-rental-data-summary.md`
- **ROI Score Function:** `core/metrics.py:calculate_roi_score()`

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `PYTHONPATH=. uv run python scripts/run_l2_pipeline.py` | Run pipeline (use cached data if fresh) |
| `PYTHONPATH=. uv run python scripts/run_l2_pipeline.py --force` | Force re-download all data |
| `PYTHONPATH=. uv run python scripts/download_hdb_rental_data.py` | Download only HDB rentals |
| `PYTHONPATH=. uv run python scripts/download_ura_rental_index.py` | Download only URA index |
| `PYTHONPATH=. uv run python scripts/calculate_rental_yield.py` | Calculate only yields |

---

## Status

✅ **Production Ready**

The L2 Data Pipeline is fully operational and integrated into the housing market metrics system. It automatically downloads, processes, and calculates rental yields for enhanced ROI scoring.

**Last Run:** 2026-01-22
**Status:** All steps successful
**Output:** 1,526 rental yield records
