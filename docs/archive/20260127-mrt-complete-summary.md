# MRT Impact Analysis - Complete Summary & Next Steps

**Date**: 2026-01-27
**Status**: In Progress - calculating amenity distances for condos/ECs

---

## ✅ What We've Accomplished

### 1. Comprehensive MRT Impact Analysis (HDB-Only)

**Analysis**: Deep dive into MRT proximity impact on HDB prices (2021+ data)

**Key Findings**:
- **Overall effect**: Every 100m closer to MRT = **+$1.27 PSF premium** (OLS), **+$33.44 PSF** (H8 cell-level)
- **Model performance**: XGBoost dramatically outperforms OLS (R²=0.91 vs 0.52)
- **Feature importance**: MRT is important but not dominant
  - Hawker centers: 27.4% importance (TOP predictor)
  - Year: 18.2% (time trend)
  - MRT features: 5-9th place (3.4-5.5% each)

**Outputs**:
- `scripts/analysis/analyze_mrt_impact.py` - Main analysis script
- `data/analysis/mrt_impact/` - All results (CSVs, plots)
- `20260127-mrt-impact-analysis-report.md` - Comprehensive report

### 2. Heterogeneous Effects Analysis (Within HDB)

**Analysis**: How MRT impact varies across HDB sub-groups

**Key Findings**:
- **By flat type**: 4x variation
  - 2 ROOM: $4.24/100m premium (highest sensitivity)
  - EXECUTIVE: $1.04/100m premium (lowest sensitivity)

- **By town**: 100x variation!
  - CENTRAL AREA: +$59.19/100m (positive premium!)
  - MARINE PARADE: -$38.54/100m (negative effect!)
  - Most towns: ~$0/100m

- **By price tier**: Opposite effects
  - Premium HDB: +$6.03/100m
  - Budget HDB: -$0.73/100m

**Outputs**:
- `scripts/analysis/analyze_mrt_heterogeneous.py` - Heterogeneous effects script
- `data/analysis/mrt_impact/heterogeneous_*.csv` - Results by subgroup
- `20260127-mrt-heterogeneous-effects-addendum.md` - Detailed report

### 3. Root Cause Analysis for Missing Condo/EC Data

**Problem Identified**:
- Condos/ECs had 0% amenity feature coverage
- Only HDB had MRT distance data
- Pipeline limitation: geocoding only covered 17,720 unique properties
- 126,402 condo/EC transactions couldn't join with amenity features

**Solution Implemented**:
- Created `scripts/calculate_condo_amenities.py`
- Directly calculates amenity distances using lat/lon coordinates
- Uses scipy KDTree for performance (O(log n) queries)
- Calculates all 6 amenity types (MRT, hawker, supermarket, park, preschool, childcare)

**Status**: Currently running in background (~15 minutes)

---

## 🔄 In Progress

### Task: Calculate Amenity Distances for Condos/ECs

**Script**: `scripts/calculate_condo_amenities.py`

**What It Does**:
1. Loads 126,402 condo/EC transactions missing amenity data
2. Loads 5,569 amenity locations (249 MRT, 129 hawker, etc.)
3. Calculates nearest distances and counts within 500m/1km/2km
4. Updates unified dataset with complete coverage

**Monitor Progress**:
```bash
tail -f /tmp/condo_amenities.log
```

**Expected Runtime**: 15-20 minutes

---

## 📋 Next Steps (Once Script Completes)

### Step 1: Verify Amenity Coverage (2 min)

```bash
uv run python -c "
import pandas as pd
unified = pd.read_parquet('data/pipeline/L3/housing_unified.parquet')
for pt in ['HDB', 'Condominium', 'EC']:
    subset = unified[unified['property_type'] == pt]
    coverage = subset['dist_to_nearest_mrt'].notna().sum() / len(subset) * 100
    print(f'{pt}: {coverage:.1f}% coverage')
"
```

**Expected Output**:
```
HDB: 100.0% coverage
Condominium: >99.0% coverage
EC: >98.0% coverage
```

### Step 2: Run Cross-Property-Type Analysis (10 min)

Create new analysis script: `scripts/analysis/analyze_mrt_by_property_type.py`

```python
# Key analysis components:
for property_type in ['HDB', 'Condominium', 'EC']:
    # Filter data
    subset = df[df['property_type'] == property_type]

    # Run OLS regression
    # price_psf ~ dist_to_mrt + controls

    # Extract MRT coefficient
    # Calculate: $/100m premium

    # Run XGBoost + SHAP
    # Compare feature importance
```

**Expected Questions Answered**:
1. Does MRT matter more for HDB than condos?
2. Do ECs behave like HDB or condos?
3. What are the top predictors for each property type?

### Step 3: Create Comparison Report (20 min)

Document: `20260127-mrt-property-type-comparison-results.md`

**Sections**:
1. Executive Summary
2. MRT Impact Comparison Table
3. Statistical Significance Tests
4. Investment Implications by Property Type
5. Visualizations:
   - MRT premium by property type (bar chart)
   - Price distributions
   - Feature importance comparison

### Step 4: Update Streamlit Apps (Optional)

Add property type filter to existing apps:
- `apps/1_market_overview.py`
- `apps/2_price_map.py`
- `apps/3_trends_analytics.py`

Allow users to toggle between HDB/Condo/EC views.

---

## 📊 Anticipated Results (Hypotheses)

### Hypothesis 1: MRT Sensitivity Ranking

**Expected**:
```
HDB:         $2-4/100m premium  (HIGHEST)
EC:          $1-2/100m premium  (MEDIUM)
Condominium:  $0-1/100m premium  (LOWEST)
```

**Rationale**:
- HDB buyers: Public transport-dependent, budget-conscious
- EC buyers: Hybrid (HDB upgraders), mixed income
- Condo buyers: Higher income, higher car ownership

### Hypothesis 2: Feature Importance Differences

**Expected**:

**HDB Top Predictors**:
1. Hawker (27%)
2. MRT (5%)
3. Parks (7%)

**Condo Top Predictors**:
1. Year/time trend
2. Luxury amenities (pool, gym)
3. MRT (<3%)

### Hypothesis 3: Price Distribution Shifts

**Expected**:
- Condos: Higher baseline prices, smaller MRT premium %
- HDB: Lower baseline prices, larger MRT premium %
- EC: Middle ground

---

## 🎯 Investment Implications (Preliminary)

### For HDB Buyers/Investors
✅ **MRT proximity is IMPORTANT**
- Target: 200-500m from MRT (sweet spot)
- Avoid: >1km from MRT
- Premium: Up to $4/100m for 2-room flats

### For Condo Buyers/Investors
⚠️ **MRT proximity is LESS important**
- Focus on: In-condo amenities (pool, gym, security)
- Location: Neighborhood quality > MRT access
- MRT only matters if: Near CBD or business hubs

### For EC Buyers/Investors
🤔 **MRT proximity is MODERATELY important**
- Balance: HDB-like price sensitivity + condo-like amenities
- Strategy: ECs near MRT in up-and-coming areas

---

## 📁 Complete File Inventory

### Analysis Scripts
1. `scripts/analysis/analyze_mrt_impact.py` - Main MRT analysis (all HDB, 2021+)
2. `scripts/analysis/analyze_mrt_heterogeneous.py` - HDB sub-group analysis
3. `scripts/calculate_condo_amenities.py` - Calculate distances for condos/ECs
4. `scripts/analysis/analyze_mrt_by_property_type.py` - **TO BE CREATED** - Cross-type comparison

### Data Files
1. `data/analysis/mrt_impact/` - All MRT analysis outputs
2. `data/pipeline/L3/housing_unified.parquet` - Being updated with condo/EC amenities
3. `data/pipeline/L3/housing_unified_backup.parquet` - Backup before update

### Reports
1. `20260127-mrt-impact-analysis-report.md` - Main analysis findings
2. `20260127-mrt-heterogeneous-effects-addendum.md` - HDB sub-group findings
3. `20260127-property-type-mrt-impact-summary.md` - Quick summary of the problem
4. `20260127-property-type-comparison-implementation.md` - Implementation details
5. `20260127-mrt-complete-summary.md` - **THIS FILE** - Overall summary

---

## 🚀 Quick Start Guide (Once Script Completes)

### Verify Success
```bash
# Check amenity coverage
uv run python -c "
import pandas as pd
df = pd.read_parquet('data/pipeline/L3/housing_unified.parquet')
print(df.groupby('property_type')['dist_to_nearest_mrt'].apply(lambda x: x.notna().sum() / len(x) * 100))
"
```

### Run Cross-Property-Type Analysis
```bash
# Create and run the comparison script
# (This is the NEXT script to write)
uv run python scripts/analysis/analyze_mrt_by_property_type.py
```

### Generate Final Report
```bash
# The analysis will automatically generate:
# - CSV outputs with coefficients
# - PNG visualizations
# - Markdown report with findings
```

---

## ⏱️ Time Investment Summary

| Task | Time Spent | Status |
|------|------------|--------|
| Root cause analysis | 1 hour | ✅ Complete |
| Main MRT analysis (HDB) | 2 hours | ✅ Complete |
| Heterogeneous effects (HDB) | 1 hour | ✅ Complete |
| Create condo amenity calculation script | 1 hour | ✅ Complete |
| **Run condo amenity calculation** | **~15 min** | 🔄 **In Progress** |
| Cross-property-type analysis | ~30 min | ⏳ Pending |
| Final comparison report | ~20 min | ⏳ Pending |
| **TOTAL** | **~5 hours** | **~75% complete** |

---

## 💡 Key Insights So Far

1. **MRT matters, but context is king**
   - HDB 2-room: 4x more sensitive than executive flats
   - Central Area: MRT proximity = +$59/100m
   - Marine Parade: MRT proximity = -$39/100m

2. **One-size-fits-all valuations are wrong**
   - Uniform "$1.27/100m" rule masks massive heterogeneity
   - Need town-specific, property-type-specific models

3. **Other amenities dominate**
   - Hawker centers (27%) > MRT (5%)
   - Food access more important than transit for HDB

4. **Non-linear models vastly superior**
   - XGBoost R²=0.91 vs OLS R²=0.52
   - Complex interactions matter

---

## 🎓 What We've Learned

### Technical Skills
- Spatial analysis with H3 hexagonal grids
- Machine learning interpretation (XGBoost + SHAP)
- Heterogeneous treatment effects
- Pipeline debugging and data reconstruction

### Domain Knowledge
- Singapore housing market dynamics
- MRT impact varies dramatically by:
  - Property type (HDB vs condo)
  - Unit size (2-room vs executive)
  - Location (Central vs Marine Parade)
  - Price tier (premium vs budget)

### Data Science Best Practices
- Always validate data coverage (found 0% for condos!)
- Check for subgroup heterogeneity
- Use both simple (OLS) and complex (XGBoost) models
- Visualize results before drawing conclusions

---

## ❓ Questions We Can Now Answer (Soon)

1. ✅ What's the MRT premium for HDB properties? ($1.27-$4.24/100m)
2. ✅ How does MRT impact vary by flat type? (4x variation)
3. ✅ How does MRT impact vary by town? (100x variation!)
4. ⏳ **How does MRT impact vary by property type?** (Condo vs EC vs HDB)
5. ⏳ **Should investment strategies differ by property type?**

---

## 📞 Next Actions

**Immediate** (when script completes):
1. Verify amenity coverage for condos/ECs
2. Run cross-property-type MRT analysis
3. Generate final comparison report

**Future Enhancements**:
1. Panel data analysis (1990-2026 full history)
2. Spatial econometric models (SAR, CAR)
3. Causal inference (IV, DiD around MRT openings)
4. Interactive Streamlit dashboard with property type toggle

---

**End of Summary**

Last updated: 2026-01-27 23:45 SGT
Next update: After condo amenity calculation completes (~15 min)
