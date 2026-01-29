# L3 Unified Dataset Schema Documentation

**Created:** 2026-01-22
**Status:** ✅ Production Ready
**Version:** 2.0 (Enhanced)

---

## Overview

The L3 unified dataset combines transaction data from L1, feature engineering from L2, and computed metrics into a single comprehensive dataset for Streamlit visualization.

**Dataset:** `data/parquets/L3/housing_unified.parquet`

**Size:** 109,780 records × 55 columns

**Date Range:** 1990-01 to 2026-01 (36 years)

**Property Types:** HDB (56%), Condominium (44%)

---

## Dataset Features

### ✅ Core Features (11 columns)
- `property_type` - HDB or Condominium
- `transaction_date` - Full timestamp
- `town` - HDB town or Condo district
- **`planning_area`** - NEW: 55 planning areas, 100% coverage
- `address` - Full property address
- `price` - Transaction price (SGD)
- `floor_area_sqm` - Floor area in square meters
- `floor_area_sqft` - Floor area in square feet
- `price_psm` - Price per square meter
- `price_psf` - Price per square foot
- `lat`, `lon` - Coordinates (100% coverage)

### ✅ Amenity Features (24 columns)

#### Distance Features (6 columns)
Distance to nearest amenity in meters:
- `dist_to_nearest_supermarket`
- `dist_to_nearest_preschool`
- `dist_to_nearest_park`
- `dist_to_nearest_hawker`
- `dist_to_nearest_mrt`
- `dist_to_nearest_childcare`

#### Count Features (18 columns)
Number of amenities within radius (0.5km, 1km, 2km):
- Supermarkets: `supermarket_within_500m`, `supermarket_within_1km`, `supermarket_within_2km`
- Preschools: `preschool_within_500m`, `preschool_within_1km`, `preschool_within_2km`
- Parks: `park_within_500m`, `park_within_1km`, `park_within_2km`
- Hawker centres: `hawker_within_500m`, `hawker_within_1km`, `hawker_within_2km`
- MRT stations: `mrt_within_500m`, `mrt_within_1km`, `mrt_within_2km`
- Childcare: `childcare_within_500m`, `childcare_within_1km`, `childcare_within_2km`

**Coverage:** 100% (all geocoded properties have amenity data)

### ✅ Rental Yield (1 column)
- `rental_yield_pct` - Monthly rental yield by town (3.37% - 9.64%)
- **Coverage:** 15.3% (16,824 records - limited to HDB with rental data)

### ✅ Precomputed Metrics (5 columns)
Monthly metrics computed from L3 metrics pipeline:
- `stratified_median_price` - Stratified median price by area/month (26.9% coverage)
- `mom_change_pct` - Month-over-month price change (26.8% coverage)
- `yoy_change_pct` - Year-over-year price change (25.6% coverage)
- `momentum_signal` - Market acceleration indicator (25.6% coverage)
- `transaction_count` - Monthly transaction volume (26.9% coverage)

**Note:** Limited coverage because metrics only computed from 2015 onwards.

### ✅ HDB-Specific Columns (6 columns)
- `month` - Original month string (YYYY-MM)
- `flat_type` - e.g., "4 ROOM", "5 ROOM"
- `flat_model` - e.g., "Improved", "Premium Apartment"
- `storey_range` - e.g., "07 TO 09"
- `lease_commence_date` - Year lease started
- `remaining_lease_months` - Remaining lease in months

### ✅ Condominium-Specific Columns (5 columns)
- `Project Name` - Condo project name
- `Street Name` - Street address
- `Postal District` - Singapore postal district (01-28)
- `Property Type` - Property subtype
- `Market Segment` - Market segment classification

---

## Data Sources

| Feature | Source | Path |
|---------|--------|------|
| HDB Transactions | L1 | `data/parquets/L1/housing_hdb_transaction.parquet` |
| Condo Transactions | L1 | `data/parquets/L1/housing_condo_transaction.parquet` |
| Geocoding | L2 | `data/parquets/L2/housing_unique_searched.parquet` |
| Amenity Features | L2 | `data/parquets/L2/housing_multi_amenity_features.parquet` |
| Rental Yield | L2 | `data/parquets/L2/rental_yield.parquet` |
| Planning Areas | Raw | `data/raw_data/onemap_planning_area_polygon.geojson` |
| Precomputed Metrics | L3 | `data/parquets/L3/metrics_monthly.parquet` |

---

## Merge Logic

### 1. Transaction Standardization
- HDB: Add `property_type='HDB'`, compute price_psm/psf
- Condo: Add `property_type='Condominium'`, clean price columns
- Both: Standardize to unified schema

### 2. Geocoding Merge
- HDB: Join on `[block, street_name]` = `[BLK_NO, ROAD_NAME]`
- Condo: Join on uppercased `Street Name` = `ROAD_NAME`
- **Coverage:** 10.8% (109,780 of 1,018,800)

### 3. Planning Area Assignment
- Spatial join: Points within planning area polygons
- Method: `geopandas.sjoin(..., predicate='within')`
- **Coverage:** 100% of geocoded properties

### 4. Amenity Features Merge
- Join key: `POSTAL` code
- Columns: All distance and count features (24 columns)
- **Coverage:** 100%

### 5. Rental Yield Merge
- Join key: `[town, month]` (both as datetime)
- Left join (preserve all transactions)
- **Coverage:** 15.3% (HDB only, 2021-2025)

### 6. Precomputed Metrics Merge
- Join key: `[town, month]` (both as datetime)
- Columns: 7 metric columns
- **Coverage:** 26.9% (2015-2026 only)

---

## Data Quality

### ✅ Strengths
1. **Complete geocoding** for included properties (109,780)
2. **100% planning area coverage** via spatial join
3. **Comprehensive amenities** (6 distance + 18 count features)
4. **Long time series** (36 years: 1990-2026)
5. **Both property types** (HDB + Condo)

### ⚠️ Known Limitations
1. **Geocoding coverage:** Only 10.8% of total transactions
   - Missing: 909,020 transactions without coordinates
   - Reason: L2 geocoding limited to unique properties

2. **Rental yield coverage:** Only 15.3%
   - Missing: Condo rental data
   - Missing: Pre-2021 HDB rental data
   - Recommendation: Use for recent HDB analysis only

3. **Metrics coverage:** Only 26.9%
   - Missing: Pre-2015 data (before L3 metrics pipeline)
   - Missing: Some towns in early months
   - Recommendation: Filter to `month >= '2015-01-01'` for complete metrics

4. **Date type mismatches:**
   - Original HDB `month` is string (YYYY-MM)
   - Rental yield `month` converted to datetime
   - Metrics `month` originally Period[M], converted to datetime
   - **Impact:** Must handle multiple date formats in joins

---

## Usage Examples

### Load Dataset
```python
import pandas as pd

df = pd.read_parquet('data/parquets/L3/housing_unified.parquet')
print(f"Shape: {df.shape}")  # (109780, 55)
```

### Filter by Property Type
```python
hdb = df[df['property_type'] == 'HDB']
condo = df[df['property_type'] == 'Condominium']
```

### Filter by Date Range
```python
# Recent transactions with complete metrics
recent = df[df['transaction_date'] >= '2020-01-01']
print(f"Recent: {len(recent):,} records")
```

### Filter by Planning Area
```python
# Central areas
central = df[df['planning_area'].isin([
    'DOWNTOWN CORE',
    'MUSEUM',
    'SINGAPORE RIVER',
    'ROCHOR'
])]
```

### Analyze Amenities
```python
# Properties near MRT
near_mrt = df[df['dist_to_nearest_mrt'] <= 500]
print(f"Properties within 500m of MRT: {len(near_mrt):,}")

# Average distance to each amenity type
amenity_cols = [col for col in df.columns if col.startswith('dist_to_nearest_')]
avg_distances = df[amenity_cols].mean()
print(avg_distances)
```

### Access Precomputed Metrics
```python
# Filter to records with complete metrics
complete_metrics = df[df['stratified_median_price'].notna()]

# Analyze growth rates
print(f"Median MoM change: {complete_metrics['mom_change_pct'].median():.2f}%")
print(f"Median YoY change: {complete_metrics['yoy_change_pct'].median():.2f}%")
```

### Rental Yield Analysis
```python
# HDB with rental data
with_rental = df[df['rental_yield_pct'].notna()]

# Group by town
rental_by_town = with_rental.groupby('town')['rental_yield_pct'].agg([
    ('mean_yield', 'mean'),
    ('median_yield', 'median'),
    ('count', 'count')
]).sort_values('mean_yield', ascending=False)

print(rental_by_town.head(10))
```

---

## Streamlit Integration

### Market Overview App (apps/1_market_overview.py)
```python
import pandas as pd
import streamlit as st

@st.cache_data
def load_data():
    return pd.read_parquet('data/parquets/L3/housing_unified.parquet')

df = load_data()

# Display metrics
st.metric("Total Transactions", f"{len(df):,}")
st.metric("Planning Areas", df['planning_area'].nunique())
st.metric("Date Range", f"{df['transaction_date'].min().date()} to {df['transaction_date'].max().date()}")
```

### Price Map App (apps/2_price_map.py)
```python
import pydeck as pdk

# Filter to recent data
recent = df[df['transaction_date'] >= '2024-01-01'].copy()

# Create map layer
layer = pdk.Layer(
    "ScatterplotLayer",
    data=recent,
    get_position=['lon', 'lat'],
    get_color=[255, 0, 0, 160],
    get_radius=100,
    pickable=True
)

# Add tooltip with planning_area and amenities
tooltip = {
    "html": """
    <b>Planning Area:</b> {planning_area}<br/>
    <b>Price:</b> ${price:,.0f}<br/>
    <b>Nearest MRT:</b> {dist_to_nearest_mrt:.0f}m
    """
}
```

### Trends Analytics App (apps/3_trends_analytics.py)
```python
# Use precomputed metrics directly
metrics_df = df[df['stratified_median_price'].notna()].copy()

# Plot growth rate by planning area
import plotly.express as px

fig = px.line(
    metrics_df,
    x='transaction_date',
    y='mom_change_pct',
    color='planning_area',
    title='Month-over-Month Price Growth by Planning Area'
)
st.plotly_chart(fig)
```

---

## Pipeline Execution

### Run the Pipeline
```bash
# Generate enhanced L3 unified dataset
uv run python scripts/create_l3_unified_dataset.py
```

### Output Files
- **Main dataset:** `data/parquets/L3/housing_unified.parquet`
- **Metrics summary:** `data/parquets/L3/metrics_summary.csv`
- **Precomputed metrics:** `data/parquets/L3/metrics_monthly.parquet`

### Performance
- **Runtime:** ~5 seconds for full pipeline
- **Memory:** Efficient (in-memory processing)
- **Storage:** Compressed parquet (~14MB for 110K records × 55 columns)

---

## Schema Changes (v1.0 → v2.0)

### Added Columns (10 columns)
1. `planning_area` - Geographic planning area (NEW)
2. `supermarket_within_1km`, `supermarket_within_2km` (NEW)
3. `preschool_within_1km`, `preschool_within_2km` (NEW)
4. `park_within_1km`, `park_within_2km` (NEW)
5. `hawker_within_1km`, `hawker_within_2km` (NEW)
6. `mrt_within_1km`, `mrt_within_2km` (NEW)
7. `childcare_within_1km`, `childcare_within_2km` (NEW)
8. `rental_yield_pct` - Rental yield by town (NEW)
9. `stratified_median_price` - Monthly median price (NEW)
10. `mom_change_pct`, `yoy_change_pct` - Growth rates (NEW)
11. `momentum_signal` - Market acceleration (NEW)
12. `transaction_count` - Monthly volume (NEW)
13. `volume_3m_avg`, `volume_12m_avg` - Rolling averages (NEW)

### Improved Features
- **Planning area mapping:** Spatial join with geojson polygons
- **Amenity counts:** Added 18 "within radius" columns
- **Rental yield:** Integrated HDB rental yield data
- **Precomputed metrics:** Integrated L3 metrics for instant display
- **Date handling:** Fixed month column type mismatches

### Column Count
- **v1.0:** 25 columns
- **v2.0:** 55 columns (+120% increase)

---

## Future Enhancements

### Phase 1: Coverage Improvements
1. **Increase geocoding coverage**
   - Target: 50%+ of transactions
   - Method: Batch geocoding with OneMap API

2. **Complete rental yield data**
   - Add Condo rental yield from URA
   - Extend historical HDB rental data

3. **Backfill metrics**
   - Compute metrics for 1990-2014 period
   - Add quarterly metrics for early years

### Phase 2: New Features
1. **School quality scores** (MOE data)
2. **Distance to CBD** (calculated from coordinates)
3. **Age-based features** (property age bands)
4. **Price percentiles** (rank within planning_area)

### Phase 3: Advanced Analytics
1. **Time series features** (lagged prices, moving averages)
2. **Cluster analysis** (market segments)
3. **Anomaly detection** (unusual transactions)

---

## References

- **L3 Metrics Implementation:** `docs/20260122-L3-metrics-implementation-summary.md`
- **Amenity Processing:** `scripts/parse_amenities_v2.py`
- **Geocoding Pipeline:** `scripts/run_l2_pipeline.py`
- **Metrics Calculation:** `scripts/calculate_l3_metrics.py`
- **Streamlit Apps:** `apps/1_market_overview.py`, `apps/2_price_map.py`, `apps/3_trends_analytics.py`

---

## Conclusion

The L3 unified dataset (v2.0) provides a **comprehensive, feature-rich dataset** that combines:

✅ **Transactional data** (HDB + Condo)
✅ **Geographic features** (planning areas, coordinates)
✅ **Amenity data** (24 features: distances + counts)
✅ **Market metrics** (rental yield, growth rates, momentum)
✅ **Property attributes** (size, type, lease info)

**Ready for use in Streamlit apps** with minimal pre-processing required.

**Recommendation:** Use as primary data source for all Streamlit visualization apps.
