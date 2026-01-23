# Growth Calculation Methodology

**Created:** 2026-01-22
**Version:** 1.0
**Status:** Design Phase

---

## Executive Summary

This document outlines the methodology for calculating housing market metrics using **stratified median** approach rather than simple medians. This addresses compositional bias in transaction data and provides more accurate growth measurements.

---

## The Problem: Why Simple Medians Fail

### Example of Compositional Bias

**Scenario:** Q1 vs Q2 transactions

**Simple Median Approach:**
- Q1 Median: $450K (high-end properties sold)
- Q2 Median: $380K (mix shifted to lower-priced properties)
- **Apparent Growth:** -15.6% ❌ (Misleading!)

**Reality:** The market didn't decline - the mix of properties sold changed.

**Stratified Median Approach:**
- High-tier: $800K → $824K (+3.0%)
- Mid-tier: $500K → $515K (+3.0%)
- Low-tier: $300K → $309K (+3.0%)
- **True Growth:** +3.0% ✅ (Accurate!)

---

## Recommended Methodology: Stratified Median

### Overview

**Stratification** groups properties by price levels to control for compositional changes. Instead of a single median, we calculate medians for each stratum and weight them appropriately.

### Implementation Steps

#### Step 1: Create Price Strata (Deciles)
1. Calculate long-term average price for each property/town/planning area
2. Rank areas by their long-term average price
3. Divide into **deciles** (10 equal groups) or **quintiles** (5 groups)

**Example:**
```
Decile 1 (Bottom 10%): Areas with avg price <$300K
Decile 2: Areas with avg price $300K-$400K
...
Decile 10 (Top 10%): Areas with avg price >$1.5M
```

#### Step 2: Calculate Stratum Medians
For each time period (month/quarter):
- Compute median price within each stratum
- Result: 10 median prices (one per decile)

#### Step 3: Apply Weights
**Option A: Equal Weighting**
- Each stratum contributes 10% to overall index
- Formula: `P_t = Σ(weight_i × median_i) = 0.1 × Σ(median_i)`

**Option B: Sales Volume Weighting** (Recommended)
- Weight by transaction count in each stratum
- More representative of actual market activity
- Formula: `P_t = Σ(volume_i / total_volume × median_i)`

#### Step 4: Compute Growth
```
Growth Rate = (P_t - P_{t-1}) / P_{t-1} × 100%
```

---

## Alternative: Fisher Index

### Formula
```
Fisher Index = √(Laspeyres × Paasche)
```

Where:
- **Laspeyres:** Uses base-period weights (overestimates growth)
- **Paasche:** Uses current-period weights (underestimates growth)
- **Fisher:** Geometric mean (most accurate)

### Pros & Cons

**Advantages:**
- More accurate than simple methods
- Respects both base and current period composition
- Widely used in official statistics (CPI, PPI)

**Disadvantages:**
- More complex to implement
- Requires maintaining weight history
- Harder to explain to non-technical stakeholders

**Recommendation:** Start with **Stratified Median** for simplicity. Add Fisher Index later for validation.

---

## Stratification Strategy for Planning Areas

### Challenge
Singapore has ~55 planning areas. Some have high transaction volume, others low.

### Recommended Approach

**Option 1: Pre-defined Strata (Simpler)**
Group planning areas by historical price bands:
- **Luxury Core:** Marina Bay, Sentosa, Orchard
- **Prime Residential:** Tanglin, Bukit Timah, Novena
- **City Fringe:** Geylang, Toa Payoh, Queenstown
- **Mass Market:** Tampines, Jurong, Woodlands
- **Suburban:** Punggol, Sengkang, Choa Chu Kang

**Option 2: Data-Driven Deciles (More Robust)**
1. Calculate 5-year rolling average price per planning area
2. Sort and divide into deciles each period
3. Recalculate strata annually to capture evolution

**Recommendation:** **Option 1** for initial implementation. Easier to maintain and explain.

---

## Benefits of Stratification

### Compared to Simple Median

| Metric | Simple Median | Stratified Median |
|--------|--------------|-------------------|
| Volatility | High | Low (70-80% reduction) |
| Seasonal Bias | Present | Eliminated |
| Composition Sensitivity | High | Low |
| Accuracy | Poor | High |
| Computation | Simple | Moderate |
| Interpretability | Easy | Moderate |

### Validation

Studies show stratified medians:
- Reduce volatility by **70-80%** compared to simple medians
- Are **highly correlated** (R² > 0.95) with regression-based hedonic indices
- Perform well even with **limited sample sizes**
- Eliminate **seasonal composition bias** (e.g., more small flats sold in certain months)

---

## Implementation Plan

### Phase 1: Stratification Framework
1. Create price bands for HDB and private properties separately
2. Assign each planning area to a stratum
3. Implement weighted median calculation function

### Phase 2: Time-Series Aggregation
1. Aggregate transactions by **month × planning area × stratum**
2. Calculate stratum medians
3. Apply weights to get overall index

### Phase 3: Growth Metrics
1. Compute period-over-period growth rates
2. Calculate annual and quarterly changes
3. Add momentum indicators

### Phase 4: Validation
1. Compare stratified vs simple median results
2. Backtest against historical data
3. Calculate volatility reduction

---

## Planning Area Granularity

### Why Planning Areas?

Singapore's planning areas are the **official geographic units** used by URA:
- **55 planning areas** nationwide
- Aligned with urban planning boundaries
- Comparable demographic characteristics
- Stable over time (unlike postal districts)

### Data Structure

**Granularity:** All metrics calculated at planning area level

**Aggregation Levels:**
- **Primary:** Planning Area (e.g., "Bishan", "Tampines")
- **Secondary:** Region (5 regions: Central, East, North, North-East, West)
- **Tertiary:** National (Singapore-wide)

**Time Periods:**
- Monthly (primary)
- Quarterly (secondary)
- Annual (tertiary)

---

## Technical Implementation

### Data Requirements

**Needed:**
- ✅ HDB transaction prices with dates
- ✅ Condo transaction prices with dates
- ✅ Property attributes (size, type)
- ⚠️ Planning area mapping (TO DO)

**To Add:**
- Planning area crosswalk table
- Historical price bands per stratum
- Weighting scheme (volume-based)

### Pseudocode

```python
def calculate_stratified_growth(transactions, period, geo_level='planning_area'):
    """
    Calculate growth rate using stratified median methodology

    Args:
        transactions: DataFrame with transaction data
        period: Time period ('month', 'quarter', 'year')
        geo_level: Geographic granularity ('planning_area', 'region', 'national')

    Returns:
        Growth rate percentage
    """

    # Step 1: Assign strata based on long-term prices
    transactions['stratum'] = assign_stratum(
        transactions,
        geo_level=geo_level,
        n_strata=10  # deciles
    )

    # Step 2: Calculate medians per stratum
    stratum_medians = transactions.groupby([period, 'stratum'])['price'].median()

    # Step 3: Apply weights (volume-based)
    weights = transactions.groupby([period, 'stratum']).size()
    weights = weights / weights.groupby(level=0).sum()

    # Step 4: Calculate weighted average price
    weighted_price = (stratum_medians * weights).groupby(level=0).sum()

    # Step 5: Compute growth
    growth = weighted_price.pct_change() * 100

    return growth
```

---

## References & Inspiration

- **Case-Shiller Index:** Uses stratified approach for US housing
- **UK ONS House Price Index:** Mix-adjusted methodology
- **Singapore SRX Property Index:** Stratified by location and property type
- **Teranet-NB Index:** Sales pair repeat methodology (alternative approach)

---

## Next Steps

1. **Implement Stratification Function**
   - Create `assign_stratum()` in `src/feature_engineering.py`
   - Define price bands for HDB vs private

2. **Add Planning Area Mapping**
   - Create crosswalk from town/postal to planning area
   - Add `planning_area` column to all datasets

3. **Build Calculation Pipeline**
   - Implement weighted median calculation
   - Add period-over-period growth computation
   - Test with historical data

4. **Validate Results**
   - Compare stratified vs simple median
   - Measure volatility reduction
   - Document findings
