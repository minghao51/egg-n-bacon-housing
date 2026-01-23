# Rental Yield Integration Guide

**Created:** 2026-01-22
**Status:** ✅ Complete

---

## Overview

Successfully integrated rental yield data into the housing market metrics pipeline. This enhancement enables more accurate ROI potential scoring by incorporating actual rental yields from HDB and URA data.

---

## Data Sources

### HDB Rental Data
- **Source:** HDB Renting Out of Flats (data.gov.sg)
- **Dataset ID:** `d_c9f57187485a850908655db0e8cfe651`
- **Records:** 184,915 rental transactions
- **Date Range:** 2021-01 to 2025-12
- **File:** `data/parquets/L1/housing_hdb_rental.parquet`

**Columns:**
- `rent_approval_date`: Approval date
- `town`: HDB town (26 towns)
- `block`, `street_name`: Location details
- `flat_type`: Flat type (e.g., 4-ROOM, 5-ROOM)
- `monthly_rent`: Monthly rent in SGD

### URA Rental Index
- **Source:** URA Private Residential Property Rental Index (data.gov.sg)
- **Dataset ID:** `d_8e4c50283fb7052a391dfb746a05c853`
- **Records:** 505 index values
- **Date Range:** 2004Q1 to 2025Q3
- **File:** `data/parquets/L1/housing_ura_rental_index.parquet`

**Columns:**
- `quarter`: Quarter period
- `property_type`: Property type (All Residential, Landed, Non-Landed)
- `locality`: Geographic region (Whole Island, Core Central, Rest of Central, Outside Central)
- `index`: Rental index value (base 2009Q1 = 100)

---

## Rental Yield Calculations

### Output File
**Location:** `data/parquets/L2/rental_yield.parquet`
**Total Records:** 1,526

### HDB Rental Yields
- **Records:** 1,499
- **Average Yield:** 5.93%
- **Range:** 2.92% to 9.64%
- **Calculation:** `(monthly_rent × 12 / resale_price) × 100`

**Methodology:**
1. Aggregate rental data by town and month (median rent)
2. Aggregate transaction data by town and month (median price)
3. Calculate yield: `(annual_rent / property_price) × 100`
4. Match rental and transaction periods (inner join)

### Condo Rental Yields
- **Records:** 27
- **Average Yield:** 3.85%
- **Range:** 3.13% to 4.97%
- **Calculation:** Index-based estimation

**Methodology:**
1. Filter URA rental index for "Non-Landed" properties
2. Map condo postal districts to regions (CCR/RCR/OCR)
3. Aggregate transaction prices by region and quarter
4. Estimate yield using rental index (base 3% at index 100)

**District to Region Mapping:**
- **Core Central Region (CCR):** Districts 1-11
- **Rest of Central Region (RCR):** Districts 12-15, 19-20
- **Outside Central Region (OCR):** Districts 16-18, 21-28

---

## Usage

### 1. Load Rental Yield Data

```python
import pandas as pd
from src.config import Config

# Load rental yield data
rental_yield_path = Config.PARQUETS_DIR / "L2" / "rental_yield.parquet"
rental_yield_df = pd.read_parquet(rental_yield_path)

print(rental_yield_df.head())
```

**Output columns:**
- `town`: Geographic area (town for HDB, region for Condo)
- `month`: Period (YYYY-MM format)
- `property_type`: 'HDB' or 'Condo'
- `rental_yield_pct`: Rental yield percentage

### 2. Enhanced ROI Score Calculation

The `calculate_roi_score()` function in `src/metrics.py` has been enhanced to include rental yield:

```python
from src.metrics import calculate_roi_score
import pandas as pd

# Load feature data with price_momentum, infrastructure_score, amenities_score
feature_df = pd.read_parquet('data/parquets/L2/housing_multi_amenity_features.parquet')

# Load rental yield data
rental_yield_df = pd.read_parquet('data/parquets/L2/rental_yield.parquet')

# Calculate ROI score with rental yield
roi_scores = calculate_roi_score(
    feature_df=feature_df,
    rental_yield_df=rental_yield_df,
    weights=None  # Use default weights
)

print(f"ROI Scores: {roi_scores.describe()}")
```

**Default Weights:**
```python
{
    'price_momentum': 0.30,
    'rental_yield': 0.25,      # ← NEW
    'infrastructure': 0.20,
    'amenities': 0.15,
    # Missing: economic_indicators (0.10)
}
```

### 3. Calculate Rental Yields Manually

```python
import pandas as pd
from src.config import Config

# Load data
rental_df = pd.read_parquet(Config.PARQUETS_DIR / "L1" / "housing_hdb_rental.parquet")
trans_df = pd.read_parquet(Config.PARQUETS_DIR / "L1" / "housing_hdb_transaction.parquet")

# Prepare rental data
rental_df['month'] = pd.to_datetime(rental_df['rent_approval_date']).dt.to_period('M')
rental_agg = rental_df.groupby(['town', 'month'])['monthly_rent'].median().reset_index()

# Prepare transaction data
trans_df['month'] = pd.to_datetime(trans_df['month'], format='%Y-%m').dt.to_period('M')
trans_agg = trans_df.groupby(['town', 'month'])['resale_price'].median().reset_index()

# Calculate yield
merged = rental_agg.merge(trans_agg, on=['town', 'month'])
merged['rental_yield_pct'] = (merged['monthly_rent'] * 12 / merged['resale_price']) * 100

print(merged[['town', 'month', 'rental_yield_pct']].head(10))
```

---

## Scripts

### Download Scripts

**Download HDB Rental Data:**
```bash
PYTHONPATH=. uv run python scripts/download_hdb_rental_data.py
```

**Download URA Rental Index:**
```bash
PYTHONPATH=. uv run python scripts/download_ura_rental_index.py
```

### Processing Script

**Calculate Rental Yields:**
```bash
PYTHONPATH=. uv run python scripts/calculate_rental_yield.py
```

This script:
1. Loads HDB rental and transaction data
2. Calculates HDB rental yields by town and month
3. Loads URA rental index and condo transaction data
4. Estimates condo rental yields by region and quarter
5. Merges both datasets and saves to `data/parquets/L2/rental_yield.parquet`

---

## Data Quality

### HDB Rental Yield
- **Coverage:** 27 towns × 59 months (2021-2025)
- **Data Quality:** High (owner-declared, but verified by HDB)
- **Limitations:**
  - Only covers 2021 onwards (pre-2021 data not available)
  - Rental amounts are owner-declared (may not be fully accurate)

### Condo Rental Yield
- **Coverage:** 3 regions × multiple quarters
- **Data Quality:** Medium (index-based estimation)
- **Limitations:**
  - Index-based (not actual rental transactions)
  - Requires assumption of base yield (3% used)
  - Less granular (region-level vs district-level)

---

## Integration with L3 Pipeline

The rental yield data can be integrated into the L3 metrics pipeline in several ways:

### Option 1: Add as New Metric Column

```python
# In compute_monthly_metrics(), after calculating other metrics
metrics_df = metrics_df.merge(
    rental_yield_df[['town', 'month', 'property_type', 'rental_yield_pct']],
    on=['town', 'month', 'property_type'],
    how='left'
)
```

### Option 2: Use in ROI Score Calculation

The `calculate_roi_score()` function now accepts `rental_yield_df` parameter and automatically:
- Merges rental yield data by town, month, and property type
- Fills missing values with median yield
- Includes rental yield in weighted score calculation (25% weight)
- Normalizes yield to 0-1 scale (assuming 0-15% range)

---

## Next Steps

### Immediate Enhancements
- [ ] Add rental_yield_pct to L3 metrics output
- [ ] Create rental yield trend visualizations
- [ ] Add yield-based filtering in analysis tools

### Future Improvements
- [ ] Acquire actual condo rental transaction data (vs index-based)
- [ ] Integrate household income data for affordability metrics
- [ ] Add economic indicators (GDP, employment) for ROI score
- [ ] Implement forecasting models for rental yields

---

## References

- **HDB Rental Data:** [data.gov.sg - Renting Out of Flats](https://data.gov.sg/datasets/d_c9f57187485a850908655db0e8cfe651/view)
- **URA Rental Index:** [data.gov.sg - Private Residential Property Rental Index](https://data.gov.sg/datasets/d_8e4c50283fb7052a391dfb746a05c853/view)
- **ROI Score Function:** `src/metrics.py:calculate_roi_score()`

---

## Summary

**Achievement:** Successfully integrated rental yield data from both HDB and URA sources, enabling more accurate ROI potential calculations.

**Key Metrics:**
- HDB average yield: **5.93%** (realistic range for Singapore)
- Condo average yield: **3.85%** (estimated from index)
- Total rental yield records: **1,526**

**Status:** Ready for analysis! 🎉

The rental yield data is now available for:
- ROI score calculations
- Investment property analysis
- Market comparison studies
- Yield trend monitoring
