# Era-Based Period Selection Enhancement

**Created:** 2026-01-24
**Status:** ✅ Complete
**Version:** 1.0
**Last Updated:** 2026-01-24 (Phase 4)

## Quick Start

```bash
# 1. Generate era segments
uv run python scripts/create_period_segmentation.py

# 2. Copy segmented data to L3 (dashboard will use this)
cp data/analysis/market_segmentation_period/housing_unified_period_segmented.parquet \
   data/parquets/L3/housing_unified.parquet

# 3. Run the dashboard
uv run streamlit run streamlit_app.py
```

Navigate to any dashboard page and use the "📅 Period Mode" sidebar filter.

---

## Features

### Phase 1-3: Era Selection

| Mode | Date Range | Description |
|------|------------|-------------|
| **Whole Period** | 1990-2026 | All historical data |
| **Pre-COVID** | 2015-2021 | Historical market including early COVID |
| **Recent** | 2022-2026 | Post-pandemic recovery period |

### Phase 4: Cross-Era Comparison

Compare metrics side-by-side between two eras:

| Page | Comparison Feature |
|------|-------------------|
| Market Overview | ✅ Side-by-side metrics |
| Price Map | ✅ Coming soon |
| Trends & Analytics | ✅ Full comparison with property breakdown |

### Phase 4: Custom Date Range

Override era selection with a specific date range slider.

---

## Dashboard Pages

| Page | Era Mode | Cross-Era Compare | Custom Range |
|------|----------|-------------------|--------------|
| Market Overview | ✅ Yes | ✅ Yes | ✅ Yes |
| Price Map | ✅ Yes | ✅ Yes (NEW) | ✅ Yes (NEW) |
| Trends & Analytics | ✅ Yes | ✅ Yes | ✅ Yes |

---

## Detailed Comparison Eras (Data Only)

| Era | Date Range | Transactions | Percentage |
|-----|------------|--------------|------------|
| pre_covid_strict | 2015-2019 | 671,732 | 73.7% |
| covid_period | 2020-2021 | 70,091 | 7.7% |
| post_covid | 2022-2026 | 169,974 | 18.6% |

---

## Modified Files

| File | Changes |
|------|---------|
| `scripts/create_period_segmentation.py` | Added `create_era_segments()` and `create_comparison_eras()` functions |
| `scripts/calculate_coming_soon_metrics.py` | NEW: Coming soon properties, forecasted metrics, era comparisons |
| `core/metrics.py` | Added `calculate_forecasted_metrics()`, `calculate_era_comparison()`, `identify_coming_soon()`, `calculate_coming_soon_score()` |
| `core/data_loader.py` | Added `filter_by_era()`, `get_era_summary()`, `era` parameter to `apply_unified_filters()` |
| `apps/1_market_overview.py` | Added Period Mode, Cross-Era Comparison, Custom Date Range |
| `apps/2_price_map.py` | Added Period Mode, Cross-Era Comparison ✅, Custom Date Range ✅, 3-Way Comparison ✅ |
| `apps/3_trends_analytics.py` | Added Period Mode, Cross-Era Comparison with property breakdown, Custom Date Range |
| `docs/20260124-era-period-selection.md` | Documentation |

---

## Era Distribution

| Era | Transactions | Percentage |
|-----|--------------|------------|
| pre_covid (2015-2021) | 741,823 | 81.4% |
| recent (2022-2026) | 169,974 | 18.6% |

---

## API Usage

```python
from core.data_loader import filter_by_era, get_era_summary, apply_unified_filters

import pandas as pd

df = pd.read_parquet('data/parquets/L3/housing_unified.parquet')

# Filter by era
pre_covid = filter_by_era(df, 'pre_covid')
recent = filter_by_era(df, 'recent')
whole = filter_by_era(df, 'whole')

# Get era summary
summary = get_era_summary(df)
# {'pre_covid': {'count': 741823, 'median_price': ..., 'date_range': ...}, ...}

# Use with apply_unified_filters
filtered = apply_unified_filters(df, era='pre_covid')
```

---

## Cross-Era Comparison Example

When enabled, the dashboard displays:

```
🔄 Cross-Era Comparison

Metric                      Pre-COVID (2015-2021)    Recent (2022-2026)    Change
───────────────────────────────────────────────────────────────────────────────
Median Price                $395,000                 $505,000              +27.8%
Transactions                741,823                  169,974               -77.1%
Price PSF                   $5,200                   $6,850                +31.7%
```

---

## Future Enhancements

| Feature | Status | Description |
|---------|--------|-------------|
| Cross-Era Comparison | ✅ Complete | Side-by-side metrics |
| Custom Date Range | ✅ Complete | Date slider |
| Price Map Era Filter | ✅ Complete | Apply to map visualizations |
| Comparison Era (3-way) | ✅ Complete | Compare pre_covid_strict, covid_period, post_covid |

---

## Overview

Added era-based period selection to the Singapore Housing Dashboard, enabling users to filter and analyze data by broader market eras:
- **Whole Period** - All data (1990-2026)
- **Pre-COVID (2015-2021)** - Historical market including early COVID years
- **Recent (2022-2026)** - Post-pandemic recovery period

---

## Implementation Details

### Data Pipeline

#### 1. `scripts/create_period_segmentation.py`

Added two new functions:

```python
def create_era_segments(df: pd.DataFrame) -> pd.DataFrame:
    """Create broader era segments for comparative analysis.
    
    - pre_covid: 2015-2021 (includes early COVID years 2020-2021)
    - recent: 2022-2026 (post-pandemic recovery)
    """
    
def create_comparison_eras(df: pd.DataFrame) -> pd.DataFrame:
    """Create detailed comparison eras for granular analysis.
    
    - pre_covid_strict: 2015-2019 (before pandemic)
    - covid_period: 2020-2021 (pandemic years)
    - post_covid: 2022-2026 (recovery period)
    """
```

**Output Files:**
- `data/analysis/market_segmentation_period/era_summary.csv`
- `data/analysis/market_segmentation_period/comparison_era_summary.csv`

#### 2. `core/data_loader.py`

Added filtering functions:

```python
def filter_by_era(df: pd.DataFrame, era: str) -> pd.DataFrame:
    """Filter data by era mode."""
    
def get_era_summary(df: pd.DataFrame) -> dict:
    """Get summary statistics by era."""
```

Extended `apply_unified_filters()` with `era` parameter.

### Dashboard Changes

#### `apps/3_trends_analytics.py`

**Sidebar Filter:**
```python
st.sidebar.subheader("📅 Period Mode")

period_mode = st.sidebar.radio(
    "Select Analysis Period",
    options=["whole", "pre_covid", "recent"],
    format_func=lambda x: {
        "whole": "Whole Period (All Data)",
        "pre_covid": "Pre-COVID (2015-2021)",
        "recent": "Recent (2022-2026)"
    }[x]
)
```

**Era Statistics Display:**
Shows transaction count and median price for selected era in sidebar.

**Visual Banner:**
Dynamic info banner at top of page showing current analysis mode.

---

## Data Distribution

After running `create_period_segmentation.py`:

| Era | Transactions | Percentage |
|-----|--------------|------------|
| pre_covid (2015-2021) | 741,823 | 81.4% |
| recent (2022-2026) | 169,974 | 18.6% |

| Comparison Era | Transactions | Percentage |
|----------------|--------------|------------|
| pre_covid_strict (2015-2019) | 671,732 | 73.7% |
| covid_period (2020-2021) | 70,091 | 7.7% |
| post_covid (2022-2026) | 169,974 | 18.6% |

---

## Usage

### Running the Pipeline

```bash
# Generate era segments
uv run python scripts/create_period_segmentation.py

# Copy segmented data to L3 (for dashboard use)
cp data/analysis/market_segmentation_period/housing_unified_period_segmented.parquet \
   data/parquets/L3/housing_unified.parquet
```

### Dashboard Usage

1. Open the Streamlit app
2. Navigate to "Trends & Analytics"
3. Use the "📅 Period Mode" radio button in sidebar to select:
   - **Whole Period**: All transactions
   - **Pre-COVID (2015-2021)**: Historical market analysis
   - **Recent (2022-2026)**: Current market trends

---

## Future Enhancements

1. **Cross-Era Comparison**: Add side-by-side comparison view for two eras
2. **Comparison Era Filter**: Expose `comparison_era` (pre_covid_strict, covid_period, post_covid) in UI
3. **Custom Date Range**: Allow users to define custom date ranges
4. **Era-Specific Metrics**: Precompute metrics separately for each era

---

## Related Documentation

- `docs/analytics/analytics-findings.md` - Consolidated findings with Pre-COVID/COVID/Post-COVID analysis
- `docs/analytics/metrics-design.md` - Metrics methodology
