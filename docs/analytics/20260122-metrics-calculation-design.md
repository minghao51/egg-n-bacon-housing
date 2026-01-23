# Housing Market Metrics - Calculation Design

**Created:** 2026-01-22
**Version:** 1.0
**Status:** Design Phase

---

## Overview

This document specifies the calculation methodology for 6 key housing market metrics that will be computed from L2 transaction data. All metrics maintain **planning area granularity** and use **stratified median** methodology where applicable.

---

## Metric 1: Price Growth Rate

### Definition
Annual/quarterly percentage change in median property prices using **stratified calculation** for accuracy.

### Formula
```
Growth (%) = (P_t - P_{t-1}) / P_{t-1} × 100

Where:
P_t = Stratified median price at time t
P_{t-1} = Stratified median price at previous period
```

### Stratification Methodology
1. Group planning areas into 5 price bands (Luxury, Prime, City Fringe, Mass Market, Suburban)
2. Calculate median price per stratum per period
3. Apply sales-volume-based weighting
4. Compute period-over-period change

### Granularity
- **Geographic:** Planning area level, aggregatable to region/national
- **Time:** Monthly, quarterly, annual
- **Property Type:** Separate for HDB vs Condo

### Output Schema
```python
{
    "planning_area": "Bishan",
    "period": "2025-12",
    "property_type": "HDB",
    "stratified_median_price": 650000,
    "previous_period_price": 630000,
    "growth_rate_pct": 3.17,
    "stratum_breakdown": {
        "mass_market": {"median": 550000, "weight": 0.6},
        "prime": {"median": 750000, "weight": 0.4}
    }
}
```

---

## Metric 2: Price per Square Meter (PSM)

### Definition
Standardized property value comparison essential for comparing different property sizes.

### Formula
```
PSM = Sale Price / Floor Area (SQM)

For HDB: Use floor_area_sqm field
For Condo: Use Area (SQM) field
```

### Aggregation
- Calculate PSM for each transaction
- Compute **median PSM** per planning area per period (not average - reduces outlier impact)
- Use stratified median for accuracy

### Use Cases
- Comparing value across different property types
- Identifying undervalued/overvalued areas
- Tracking price per unit of space over time

### Output Schema
```python
{
    "planning_area": "Bishan",
    "period": "2025-12",
    "property_type": "HDB",
    "median_psm": 6842,  # SGD per square meter
    "avg_psm": 7120,
    "psm_distribution": {
        "p25": 5800,
        "p50": 6842,
        "p75": 8100
    },
    "transaction_count": 156
}
```

---

## Metric 3: Transaction Volume

### Definition
Number of transactions over time, indicating market liquidity and buyer interest.

### Formula
```
Volume = Count of transactions in period

Volume Growth = (Volume_t - Volume_t-1) / Volume_t-1 × 100
```

### Market Interpretation
| Price Trend | Volume Trend | Interpretation |
|-------------|-------------|----------------|
| Rising | Rising | Strong bull market |
| Rising | Falling | Potential bubble (unsustainable) |
| Falling | Rising | Market correction/buying opportunity |
| Falling | Falling | Bear market, low demand |

### Granularity
- Count transactions per planning area per month
- Calculate 3-month and 12-month rolling averages
- Compute month-over-month and year-over-year changes

### Output Schema
```python
{
    "planning_area": "Bishan",
    "period": "2025-12",
    "property_type": "HDB",
    "transaction_count": 156,
    "volume_3m_avg": 142,
    "volume_12m_avg": 138,
    "mom_change_pct": 12.3,  # Month-over-month
    "yoy_change_pct": 15.4,   # Year-over-year
    "market_phase": "expansion"  # expansion, contraction, stable
}
```

---

## Metric 4: Affordability Index

### Definition
Ratio of median property price to median household income - critical for market sustainability assessment.

### Formula
```
Affordability Ratio = Median Property Price / Median Annual Household Income

Interpretation:
- < 3.0: Affordable
- 3.0 - 5.0: Moderate
- > 5.0: Expensive (Stretched)
```

### Data Requirements
- ✅ Median property price (from L2 data)
- ⚠️ Median income by planning area (NEEDS EXTERNAL DATA)
  - Source: Singapore Department of Statistics (DOS)
  - Alternative: Use national average with planning area adjustments

### Affordability Bands (Singapore Context)
| Ratio | Category | Description |
|-------|----------|-------------|
| < 2.5 | Highly Affordable | Price < 2.5× annual income |
| 2.5 - 3.5 | Affordable | Generally accessible to median household |
| 3.5 - 5.0 | Moderate | Stretch for median household |
| 5.0 - 7.0 | Expensive | Significant financial burden |
| \> 7.0 | Severely Unaffordable | Out of reach for most households |

### Output Schema
```python
{
    "planning_area": "Bishan",
    "period": "2025-12",
    "property_type": "HDB",
    "median_price": 650000,
    "median_household_income": 120000,  # Annual
    "affordability_ratio": 5.42,
    "category": "expensive",
    "months_of_income": 65,  # Price / monthly income
    "mortgage_payment_pct": 35,  # % of monthly income (estimate)
    "accessible_to": "top 40% of households"  # Income percentile needed
}
```

---

## Metric 5: ROI Potential Score

### Definition
Machine learning-based investment potential prediction combining multiple factors to score areas from 0-100.

### Components

**5.1 Price Momentum (30%)**
- Short-term price acceleration
- Consistency of growth over time
- Trend strength

**5.2 Rental Yield Potential (25%)**
- Estimated rental yield (need rental data)
- Historical yield trends
- Rental demand indicators

**5.3 Infrastructure Proximity (20%)**
- Access to MRT stations (from L2 features)
- Future MRT lines (planned infrastructure)
- Accessibility to CBD

**5.4 Amenities Score (15%)**
- Proximity to schools, parks, malls (from L2 features)
- Quality of amenities
- Amenity density

**5.5 Economic Indicators (10%)**
- Employment growth in area
- Development projects
- Urban planning trends

### Scoring Formula
```
ROI Score = 0.30×Momentum + 0.25×RentalYield + 0.20×Infra + 0.15×Amenities + 0.10×Economic

Score Interpretation:
- 80-100: Excellent investment potential
- 60-79: Good investment potential
- 40-59: Moderate potential
- 20-39: Weak potential
- 0-19: Poor investment outlook
```

### Data Requirements
- ✅ Price momentum (from growth rate metric)
- ✅ Infrastructure proximity (from L2 amenity features)
- ✅ Amenities score (from L2 features)
- ⚠️ Rental yield data (NEEDS EXTERNAL DATA - URA rental index)
- ⚠️ Economic indicators (NEEDS EXTERNAL DATA - MOM, MTI)

### Output Schema
```python
{
    "planning_area": "Bishan",
    "period": "2025-12",
    "roi_score": 72,
    "category": "good",
    "component_scores": {
        "price_momentum": 75,  # 30% weight
        "rental_yield": 68,    # 25% weight
        "infrastructure": 85,  # 20% weight
        "amenities": 65,       # 15% weight
        "economic_indicators": 70  # 10% weight
    },
    "rank_nationally": 15,  # Out of 55 planning areas
    "confidence": "high"  # Based on data quality
}
```

---

## Metric 6: Market Momentum

### Definition
Short-term price acceleration/deceleration to identify emerging trends before they show up in long-term growth rates.

### Formula
```
Momentum = Growth_3M - Growth_12M

Where:
Growth_3M = 3-month price growth rate
Growth_12M = 12-month price growth rate

Interpretation:
- Momentum > 0: Accelerating (bullish)
- Momentum < 0: Decelerating (bearish)
- Momentum ≈ 0: Stable trend
```

### Calculation Steps

1. **Calculate Short-Term Growth**
   - Compare current month to 3 months ago
   - Annualize: `Growth_3M = (P_t / P_{t-3} - 1) × 4 × 100`

2. **Calculate Long-Term Growth**
   - Compare current month to 12 months ago
   - `Growth_12M = (P_t / P_{t-12} - 1) × 100`

3. **Compute Momentum**
   - `Momentum = Growth_3M - Growth_12M`

### Momentum Signals
| Momentum | Signal | Action |
|----------|--------|--------|
| \> +5% | Strong Acceleration | Bullish, potential uptrend starting |
| +2% to +5% | Moderate Acceleration | Positive momentum building |
| -2% to +2% | Stable | No clear momentum signal |
| -5% to -2% | Moderate Deceleration | Momentum weakening |
| \< -5% | Strong Deceleration | Bearish, potential downtrend |

### Output Schema
```python
{
    "planning_area": "Bishan",
    "period": "2025-12",
    "property_type": "HDB",
    "price_t": 650000,
    "price_t_3m": 625000,
    "price_t_12m": 580000,
    "growth_3m_annualized": 16.0,
    "growth_12m": 12.1,
    "momentum": 3.9,  # percentage points
    "signal": "moderate_acceleration",
    "trend_direction": "up",
    "velocity": "increasing"
}
```

---

## Data Pipeline Design

### Input Data Sources

**Primary Sources:**
- ✅ `L1/housing_hdb_transaction.parquet` - HDB transactions
- ✅ `L1/housing_condo_transaction.parquet` - Condo transactions
- ✅ `L2/housing_multi_amenity_features.parquet` - Amenity distances

**External Data (To Be Added):**
- ⚠️ Household income by planning area (DOS)
- ⚠️ Rental index by area (URA)
- ⚠️ Future infrastructure plans (LTA, URA)

### Processing Flow

```
Raw Transactions
    ↓
[1] Clean & Standardize
    - Add planning_area mapping
    - Standardize date formats
    - Handle missing values
    ↓
[2] Add Amenity Features
    - Join with L2 features
    - Calculate proximity scores
    ↓
[3] Aggregate by Period & Area
    - Group by month × planning_area
    - Calculate stratum medians
    ↓
[4] Compute Metrics
    - Calculate all 6 metrics
    - Add historical context
    ↓
[5] Output & Validation
    - Save to parquet
    - Data quality checks
    - Anomaly detection
```

### File Structure

**Input:**
- `data/parquets/L1/housing_hdb_transaction.parquet`
- `data/parquets/L1/housing_condo_transaction.parquet`
- `data/parquets/L2/housing_multi_amenity_features.parquet`

**Output:**
- `data/parquets/L3/metrics_monthly.parquet` - All metrics, monthly
- `data/parquets/L3/metrics_quarterly.parquet` - All metrics, quarterly
- `data/parquets/L3/growth_rates.parquet` - Growth rates only
- `data/parquets/L3/affordability.parquet` - Affordability only
- `data/parquets/L3/roi_scores.parquet` - ROI scores only

---

## Implementation Priority

### Phase 1: Core Metrics (High Priority)
1. **Transaction Volume** (easiest, no external dependencies)
2. **Price Growth Rate** (core metric, uses stratified median)
3. **PSM** (straightforward calculation)

### Phase 2: Advanced Metrics (Medium Priority)
4. **Market Momentum** (builds on growth rate)
5. **ROI Score** (partial - use available components)

### Phase 3: External Dependencies (Low Priority)
6. **Affordability Index** (requires income data)
7. **Complete ROI Score** (requires rental & economic data)

---

## Function Signatures

### Core Calculation Functions

```python
def calculate_stratified_median(
    transactions: pd.DataFrame,
    geo_level: str = 'planning_area',
    property_type: str = 'HDB',
    n_strata: int = 5
) -> pd.Series:
    """Calculate stratified median price per area per period"""

def calculate_psm(
    transactions: pd.DataFrame,
    agg_method: str = 'median'
) -> pd.Series:
    """Calculate price per square meter"""

def calculate_volume(
    transactions: pd.DataFrame,
    rolling_windows: List[int] = [3, 12]
) -> pd.DataFrame:
    """Calculate transaction volume metrics"""

def calculate_growth_rate(
    prices: pd.Series,
    periods: int = 1
) -> pd.Series:
    """Calculate period-over-period growth rate"""

def calculate_momentum(
    prices: pd.Series
) -> pd.Series:
    """Calculate market momentum (3M - 12M growth)"""

def calculate_affordability(
    property_prices: pd.Series,
    income_data: pd.Series
) -> pd.Series:
    """Calculate affordability ratio"""

def calculate_roi_score(
    feature_df: pd.DataFrame,
    weights: Dict[str, float] = None
) -> pd.Series:
    """Calculate composite ROI potential score"""
```

### Pipeline Orchestration

```python
def compute_all_metrics(
    start_date: str,
    end_date: str,
    geo_level: str = 'planning_area',
    frequency: str = 'monthly'
) -> pd.DataFrame:
    """Main pipeline function to compute all metrics"""

def backtest_metrics(
    historical_data: pd.DataFrame,
    test_period: str
) -> Dict:
    """Validate metrics against historical trends"""
```

---

## Next Steps

1. **Implement Stratification Framework**
   - Create `src/feature_engineering.py` with stratum assignment
   - Define price bands for HDB and condo
   - Add planning area crosswalk

2. **Build Core Metrics Functions**
   - Implement functions in `src/metrics.py`
   - Add unit tests
   - Validate with sample data

3. **Create Pipeline Script**
   - `scripts/calculate_l3_metrics.py`
   - Orchestrate all metric calculations
   - Add error handling and logging

4. **Test & Validate**
   - Run on historical data
   - Compare with published indices (SRX, URA)
   - Document any discrepancies
