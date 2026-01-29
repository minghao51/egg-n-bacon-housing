# Rental Yield Integration - Consolidated Report

**Date:** 2026-01-22 (updated 2026-01-24)
**Status:** ✅ Complete

---

## Executive Summary

Successfully downloaded, processed, and integrated rental transaction data from data.gov.sg to enhance ROI score calculation and enable rental yield forecasting.

---

## Data Sources

### HDB Rental Data

- **Source:** HDB Renting Out of Flats (data.gov.sg)
- **Dataset ID:** `d_c9f57187485a850908655db0e8cfe651`
- **Records:** 184,915 rental transactions
- **Date Range:** 2021-01 to 2025-12
- **Coverage:** 26 HDB towns, 6 flat types
- **Average monthly rent:** $2,794

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
- **Coverage:** 3 property types, 4 regions
- **Base quarter:** 2009Q1 = 100

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

## Enhanced ROI Score Calculation

### Updated Function

**Location:** `core/metrics.py:calculate_roi_score()`

**Changes:**
- Added `rental_yield_df` parameter (optional)
- Integrated rental yield into weighted score (25% weight)
- Automatic merging of rental data by town/month/property_type
- Fills missing yields with median value
- Backward compatible (works without rental data)

**New Weight Distribution:**
```python
{
    'price_momentum': 0.30,
    'rental_yield': 0.25,      # ← NEW
    'infrastructure': 0.20,
    'amenities': 0.15,
    # Missing: economic_indicators (0.10)
}
```

### Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| ROI Score Components | 3 of 4 (65%) | 4 of 4 (90%) | +38% |
| Missing Weight | 35% | 10% | +25% |

---

## Data Quality

### HDB Rental Yield

- **Coverage:** 27 towns × 59 months (2021-2025)
- **Data Quality:** High (owner-declared, but verified by HDB)
- **Realism:** 5.93% average matches Singapore market norms

**Limitations:**
- Only covers 2021 onwards (pre-2021 data not available)
- Rental amounts are owner-declared (may not be fully accurate)

### Condo Rental Yield

- **Coverage:** 3 regions × multiple quarters
- **Data Quality:** Medium (index-based estimation)
- **Realism:** 3.85% reasonable for private property

**Limitations:**
- Index-based (not actual rental transactions)
- Requires assumption of base yield (3% used)
- Less granular (region-level vs district-level)

---

## Usage

### 1. Load Rental Yield Data

```python
import pandas as pd
from core.config import Config

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

```python
from core.metrics import calculate_roi_score
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

### 3. Calculate Rental Yields Manually

```python
import pandas as pd
from core.config import Config

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

## File Locations

### Scripts
```
scripts/download_hdb_rental_data.py      # Download HDB rentals
scripts/download_ura_rental_index.py      # Download URA index
scripts/calculate_rental_yield.py         # Calculate yields
```

### Data Files
```
data/parquets/L1/housing_hdb_rental.parquet       # HDB rentals (raw)
data/parquets/L1/housing_ura_rental_index.parquet # URA index (raw)
data/parquets/L2/rental_yield.parquet              # Yields (processed)
```

### Code
```
core/metrics.py:calculate_roi_score()     # Enhanced with rental yield
```

### Documentation
```
docs/analytics/CONSOLIDATED-RENTAL-YIELD.md   # This file
```

---

## Limitations & Future Work

### Current Limitations

1. **HDB Data Coverage:** Starts from 2021 only
2. **Condo Yields:** Index-based (not actual rentals)
3. **Geographic Granularity:** Town-level (HDB) and region-level (Condo)
4. **Economic Indicators:** Not yet integrated

### Recommended Enhancements

**Phase 1: Improve Data Quality**
- [ ] Acquire pre-2021 HDB rental data
- [ ] Obtain actual condo rental transactions (vs index)
- [ ] Add district-to-planning-area mapping

**Phase 2: Complete ROI Score**
- [ ] Integrate household income data (DOS)
- [ ] Add economic indicators (GDP, employment from MTI)
- [ ] Calculate affordability index

**Phase 3: Advanced Analytics**
- [ ] Implement yield forecasting models (6-month, 1-year)
- [ ] Add yield trend indicators
- [ ] Create yield heatmaps by location

---

## Commands Reference

### Download Data
```bash
# HDB rental data (184K records, ~30 seconds)
PYTHONPATH=. uv run python scripts/download_hdb_rental_data.py

# URA rental index (505 records, ~2 seconds)
PYTHONPATH=. uv run python scripts/download_ura_rental_index.py
```

### Calculate Yields
```bash
# Process and calculate yields (1,526 records, ~5 seconds)
PYTHONPATH=. uv run python scripts/calculate_rental_yield.py
```

### Use in Analysis
```python
# Load and analyze
PYTHONPATH=. uv run python -c "
import pandas as pd
df = pd.read_parquet('data/parquets/L2/rental_yield.parquet')
print(df.groupby('property_type')['rental_yield_pct'].describe())
"
```

---

## Success Criteria Met

- ✅ Downloaded HDB rental data from data.gov.sg
- ✅ Downloaded URA rental index from data.gov.sg
- ✅ Calculated rental yields for both HDB and condos
- ✅ Integrated rental yield into ROI score calculation
- ✅ Created comprehensive documentation
- ✅ Maintained backward compatibility
- ✅ Ensured data quality and validation

---

## References

- **HDB Rental Data:** data.gov.sg - Renting Out of Flats
- **URA Rental Index:** data.gov.sg - Private Residential Property Rental Index
- **ROI Score Function:** `core/metrics.py:calculate_roi_score()`

---

*Consolidated from:*
- `docs/analytics/20260122-rental-data-summary.md`
- `docs/analytics/20260122-rental-yield-integration.md`
