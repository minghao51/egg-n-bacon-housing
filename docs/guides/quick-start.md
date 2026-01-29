# Quick Start Guide - L3 Housing Market Metrics

**Last Updated:** 2026-01-22

---

## 🚀 Quick Start

### Step 1: Update L2 Data (Rental Yields)
```bash
# Download rental data and calculate yields
PYTHONPATH=. uv run python scripts/run_l2_pipeline.py
```

### Step 2: Run L3 Metrics Pipeline
```bash
# Calculate market metrics
PYTHONPATH=. uv run python scripts/calculate_l3_metrics.py
```

### Step 3: Load Results
```python
import pandas as pd

# Load metrics
df = pd.read_parquet('data/parquets/L3/metrics_monthly.parquet')

# Load rental yields
rental_yields = pd.read_parquet('data/parquets/L2/rental_yield.parquet')

print(f"Total records: {len(df):,}")
print(f"Date range: {df['month'].min()} to {df['month'].max()}")
```

---

## 📊 What's Included

### 6 Core Metrics

| Metric | Column Name | Description |
|--------|-------------|-------------|
| **Price Growth Rate** | `growth_rate` | Month-over-month % change (stratified median) |
| **Price per SQM** | Not stored (computed) | Use resale_price / floor_area_sqm |
| **Transaction Volume** | `transaction_count` | Number of transactions |
| **Volume Trend** | `volume_3m_avg`, `volume_12m_avg` | Rolling averages |
| **Market Momentum** | `momentum` | 3M growth - 12M growth |
| **Momentum Signal** | `momentum_signal` | categorical (stable/acceleration/deceleration) |

### Additional Columns

- `month`: Period (YYYY-MM format)
- `town`: HDB town (26 towns)
- `Postal District`: Condo district (27 districts)
- `property_type`: 'HDB' or 'Condo'
- `stratified_median_price`: Weighted median price
- `growth_3m`, `growth_12m`: For momentum calculation
- `mom_change_pct`: Month-over-month volume change
- `yoy_change_pct`: Year-over-year volume change

---

## 🔍 Common Queries

### 1. National Average Growth Rate
```python
import pandas as pd

df = pd.read_parquet('data/parquets/L3/metrics_monthly.parquet')

# Group by month and property type
national_avg = df.groupby(['month', 'property_type'])['growth_rate'].mean()

# View recent months
print(national_avg.tail(12))
```

### 2. Top Performing Towns
```python
# Filter for recent month
recent = df[df['month'] == '2026-01']

# HDB towns with highest growth
hdb_growth = recent[recent['property_type'] == 'HDB'].sort_values('growth_rate', ascending=False)
print(hdb_growth[['town', 'growth_rate', 'stratified_median_price']].head(10))
```

### 3. Market Momentum Analysis
```python
# Find areas with strong acceleration
accelerating = df[df['momentum_signal'] == 'strong_acceleration']

print(f"Areas accelerating: {len(accelerating)}")
print()
print(accelerating[['month', 'town', 'momentum', 'growth_rate']].tail(10))
```

### 4. Transaction Volume Trends
```python
# National transaction volume
volume = df.groupby(['month', 'property_type'])['transaction_count'].sum()

# Plot volume trends
volume.unstack().plot(kind='line', title='Monthly Transaction Volume')
```

### 5. Filter by Time Range
```python
# Focus on post-COVID period
post_covid = df[df['month'] >= '2020-01']

# Calculate average growth during period
avg_growth = post_covid.groupby('town')['growth_rate'].mean()
print(avg_growth.sort_values(ascending=False).head(10))
```

---

## 📁 File Locations

### Input Data
```
data/parquets/L1/housing_hdb_transaction.parquet
data/parquets/L1/housing_condo_transaction.parquet
data/parquets/L2/housing_multi_amenity_features.parquet
```

### Output Data
```
data/parquets/L3/metrics_monthly.parquet          # Main metrics
data/parquets/L3/metrics_summary.csv              # Summary by area
```

### Documentation
```
docs/20260122-L2-data-reference.md                # Data catalog
docs/20260122-growth-calculation-methodology.md   # How metrics work
docs/20260122-metrics-calculation-design.md       # Technical specs
docs/20260122-L3-metrics-implementation-summary.md # Project summary
```

### Code
```
core/metrics.py                                    # Calculation functions
scripts/calculate_l3_metrics.py                   # Main pipeline
```

---

## ⚙️ Configuration

### Change Date Range
Edit `scripts/calculate_l3_metrics.py`:
```python
metrics_df = compute_monthly_metrics(
    hdf_df=hdb_df,
    condo_df=condo_df,
    start_date='2020-01',  # Change this
    end_date='2025-12'     # Change this
)
```

### Adjust Stratification Bands
Edit `core/metrics.py` in `assign_price_strata()`:
```python
if price_column == 'resale_price':  # HDB
    bins = [0, 300000, 450000, 600000, 800000, float('inf')]
    # Adjust these thresholds as needed
```

---

## 🐛 Troubleshooting

### Issue: Pipeline Fails
**Check:**
```bash
# Verify input files exist
ls -lh data/parquets/L1/*.parquet

# Check Python environment
uv run python -c "import pandas; print(pandas.__version__)"
```

### Issue: Missing Data
**Expected:** Some `momentum_signal` and `yoy_change_pct` values are null
**Reason:** Need 12 months of history for momentum calculation
**Solution:** Filter to periods after 2016-01

```python
df = df[df['month'] >= '2016-01']  # Remove early periods
```

### Issue: High Volatility in Condo Metrics
**Reason:** Fewer transactions per district
**Solution:** Aggregate to quarterly or regional level

```python
# Quarterly aggregation
df['quarter'] = df['month'].dt.to_period('Q')
quarterly = df.groupby(['quarter', 'property_type', 'town']).agg({
    'stratified_median_price': 'mean',
    'transaction_count': 'sum',
    'growth_rate': 'mean'
})
```

---

## 📈 Example Analysis Workflow

```python
import pandas as pd
import matplotlib.pyplot as plt

# 1. Load data
df = pd.read_parquet('data/parquets/L3/metrics_monthly.parquet')

# 2. Filter for HDB and recent period
hdb = df[(df['property_type'] == 'HDB') & (df['month'] >= '2020-01')]

# 3. Focus on specific town
yishun = hdb[hdb['town'] == 'YISHUN'].copy()

# 4. Create visualizations
fig, axes = plt.subplots(3, 1, figsize=(12, 10))

# Price trend
yishun.plot(x='month', y='stratified_median_price', ax=axes[0], title='Yishun Median Price')

# Growth rate
yishun.plot(x='month', y='growth_rate', ax=axes[1], title='Growth Rate (%)')

# Transaction volume
yishun.plot(x='month', y='transaction_count', ax=axes[2], title='Transaction Volume')

plt.tight_layout()
plt.savefig('yishun_analysis.png')
```

---

## 🎯 Next Steps

### 1. Planning Area Mapping (Priority)
- Currently using town/district
- Map to planning areas for unified analysis
- See: `docs/20260122-L3-metrics-implementation-summary.md`

### 2. Visualization Dashboard
- Build Streamlit app for interactive exploration
- Add choropleth maps
- Create time-series animations

### 3. Forecasting
- Implement ARIMA/Prophet models
- Predict future prices and momentum
- Build confidence intervals

### 4. Advanced Metrics
- Add affordability index (needs income data)
- Implement ROI score (needs rental data)
- Build composite health score

---

## 📞 Support

### Documentation
- L2 Data Reference: `docs/20260122-L2-data-reference.md`
- Methodology: `docs/20260122-growth-calculation-methodology.md`
- Implementation: `docs/20260122-L3-metrics-implementation-summary.md`

### Code
- Metrics functions: `core/metrics.py` (well-documented)
- Pipeline script: `scripts/calculate_l3_metrics.py`
- Type hints and docstrings throughout

### Validation
- Run validation after any changes:
```python
from core.metrics import validate_metrics
df = pd.read_parquet('data/parquets/L3/metrics_monthly.parquet')
results = validate_metrics(df)
print(results)
```

---

## ✅ Checklist

- [x] L2 data verified (HDB, condo, amenities)
- [x] Stratified median methodology implemented
- [x] 6 metrics designed (4 implemented, 2 need external data)
- [x] Pipeline automated
- [x] Documentation complete
- [x] Results validated
- [x] Quick start guide created
- [ ] Planning area mapping (TODO)
- [ ] Visualization dashboard (TODO)
- [ ] External data integration (TODO)

---

**Status:** Ready for analysis! 🎉

Run the pipeline, load the data, and start exploring Singapore's housing market trends.
