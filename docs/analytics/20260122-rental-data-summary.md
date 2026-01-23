# Rental Data Integration - Project Summary

**Date:** 2026-01-22
**Status:** ✅ Complete

---

## What Was Accomplished

Successfully downloaded, processed, and integrated rental transaction data from data.gov.sg to enhance the ROI score calculation in the housing market metrics pipeline.

---

## Deliverables

### 1. Data Downloads (3 scripts created)

**HDB Rental Data** (`scripts/download_hdb_rental_data.py`)
- Downloaded 184,915 HDB rental transactions
- Date range: 2021-01 to 2025-12
- Coverage: 26 HDB towns, 6 flat types
- Output: `data/parquets/L1/housing_hdb_rental.parquet`
- Average monthly rent: $2,794

**URA Rental Index** (`scripts/download_ura_rental_index.py`)
- Downloaded 505 URA rental index values
- Date range: 2004Q1 to 2025Q3
- Coverage: 3 property types, 4 regions
- Output: `data/parquets/L1/housing_ura_rental_index.parquet`
- Base quarter: 2009Q1 = 100

### 2. Rental Yield Processing

**Rental Yield Calculator** (`scripts/calculate_rental_yield.py`)
- **HDB Yields:** 1,499 records calculated
  - Method: Direct calculation from rental/transaction prices
  - Average: 5.93% (range: 2.92% - 9.64%)
  - Formula: `(monthly_rent × 12 / resale_price) × 100`

- **Condo Yields:** 27 records estimated
  - Method: Index-based estimation using URA rental index
  - Average: 3.85% (range: 3.13% - 4.97%)
  - Assumption: 3% base yield at index 100

- **Output:** `data/parquets/L2/rental_yield.parquet`
- **Total Records:** 1,526

### 3. Enhanced ROI Score Calculation

**Updated Function:** `src/metrics.py:calculate_roi_score()`

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

### 4. Documentation (2 files created)

**Rental Yield Integration Guide** (`docs/20260122-rental-yield-integration.md`)
- Complete usage guide
- Methodology explanation
- Code examples
- Data quality assessment

**This Summary** (`docs/20260122-rental-data-summary.md`)
- Project overview
- Technical implementation details
- File locations

---

## Technical Implementation

### Data Flow

```
data.gov.sg APIs
    ↓
Download Scripts (batch processing with offset)
    ↓
L1 Parquet Files (raw data)
    ↓
Processing Script (aggregation & calculation)
    ↓
L2 Parquet File (rental_yield.parquet)
    ↓
ROI Score Function (enhanced with rental data)
    ↓
Enhanced Investment Analysis
```

### Key Features

**Robust Download:**
- Batch processing (10,000 records per batch)
- Error handling and retry logic
- Progress logging
- Data type validation and conversion

**Smart Yield Calculation:**
- HDB: Direct calculation from actual transactions
- Condo: Index-based estimation with region mapping
- Inner join ensures data quality
- Median aggregation for stability

**Flexible Integration:**
- Optional rental_yield parameter
- Automatic weight normalization
- Missing value handling
- Backward compatibility maintained

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
src/metrics.py:calculate_roi_score()     # Enhanced with rental yield
```

### Documentation
```
docs/20260122-rental-yield-integration.md   # Complete guide
docs/20260122-rental-data-summary.md        # This file
```

---

## Usage Example

```python
import pandas as pd
from src.config import Config
from src.metrics import calculate_roi_score

# 1. Load rental yield data
rental_yield_df = pd.read_parquet(Config.PARQUETS_DIR / "L2" / "rental_yield.parquet")

# 2. Load feature data
feature_df = pd.read_parquet(Config.PARQUETS_DIR / "L2" / "housing_multi_amenity_features.parquet")

# 3. Calculate enhanced ROI score
roi_scores = calculate_roi_score(
    feature_df=feature_df,
    rental_yield_df=rental_yield_df  # ← NEW PARAMETER
)

# 4. Analyze results
print(f"Average ROI Score: {roi_scores.mean():.2f}")
print(f"Highest ROI Areas: {roi_scores.nlargest(5)}")
```

---

## Quality Metrics

### HDB Rental Yields
- **Coverage:** 1,499 town-month combinations
- **Data Quality:** High (actual transaction data)
- **Realism:** 5.93% average matches Singapore market norms
- **Reliability:** Direct calculation (no assumptions)

### Condo Rental Yields
- **Coverage:** 27 region-quarter combinations
- **Data Quality:** Medium (index-based estimation)
- **Realism:** 3.85% reasonable for private property
- **Reliability:** Dependent on index accuracy

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
- [ ] Implement yield forecasting models
- [ ] Add yield trend indicators
- [ ] Create yield heatmaps by location

---

## Impact

### Before Integration
- ROI score used only 3 components (momentum, infrastructure, amenities)
- Weights: 30%, 20%, 15% (total: 65%)
- Missing 35% of score (rental + economic)

### After Integration
- ROI score uses 4 components (added rental yield)
- Weights: 30%, 25%, 20%, 15% (total: 90%)
- Only 10% missing (economic indicators)
- **38% improvement in score completeness** (25% / 65%)

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

## Conclusion

The rental data integration is **complete and production-ready**. The enhanced ROI score calculation now incorporates actual rental yields from HDB transactions and estimated yields from URA indices, providing a 38% improvement in score completeness.

**Next Steps:**
1. Use the enhanced ROI score in investment analysis
2. Create visualizations of rental yield trends
3. Acquire additional economic data to complete the remaining 10%

**Status:** ✅ Ready for deployment!
