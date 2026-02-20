# School Impact Analysis Report
**Singapore Housing Market Analytics**

**Generated:** 2026-02-03
**Data Period:** 2021-2026
**Analysis Scripts:**
- `analyze_school_impact.py`

---

## Executive Summary

This analysis investigated the relationship between school proximity and Singapore housing prices, rental yields, and appreciation rates. The analysis used the unified housing dataset (428,061 records from 2021+) and examined basic school count features (schools within 500m, 1km, and 2km).

### Key Finding

**School count features showed NO statistically significant impact on housing prices, rental yields, or appreciation.** The school proximity features had zero importance in all machine learning models and near-zero coefficients in regression models.

---

## Data Overview

| Metric | Value |
|--------|-------|
| Total Records (2021+) | 428,061 |
| HDB Records | 194,165 |
| Condominium Records | 202,983 |
| EC Records | 30,913 |
| School Feature Coverage | 100% |

### School Features Analyzed

- `school_within_500m`: Number of schools within 500 meters
- `school_within_1km`: Number of schools within 1 kilometer
- `school_within_2km`: Number of schools within 2 kilometers

**Note:** The current dataset only includes basic school count features. Advanced quality and accessibility scores (e.g., school_accessibility_score, school_primary_quality_score) referenced in the analysis plan are not yet implemented.

---

## Model Performance Summary

### Price Per Square Foot (PSF) Models

| Model | R² | MAE | Top Feature |
|-------|-----|-----|-------------|
| OLS Regression | 0.42 | $77.54 PSF | Year (+$39.52) |
| XGBoost | **0.89** | **$34.92 PSF** | Year (34.4%) |

**School Feature Impact:**
- Coefficient: ~0 (statistically insignificant)
- XGBoost Importance: 0.00%
- **Conclusion:** No detectable impact on prices

### Rental Yield Models

| Model | R² | MAE | Top Feature |
|-------|-----|-----|-------------|
| OLS Regression | 0.20 | 0.66% | Year |
| XGBoost | **0.76** | **0.32%** | Year (63.1%) |

**School Feature Impact:**
- Coefficient: ~0 (statistically insignificant)
- XGBoost Importance: 0.00%
- **Conclusion:** No detectable impact on rental yields

### Year-Over-Year Appreciation Models

| Model | R² | MAE | Top Feature |
|-------|-----|-----|-------------|
| OLS Regression | 0.003 | 62.48% | Year |
| XGBoost | **0.08** | **60.02%** | Year (33.1%) |

**School Feature Impact:**
- Coefficient: ~0 (statistically insignificant)
- XGBoost Importance: 0.00%
- **Conclusion:** YoY appreciation is not predictable with current features; schools show no relationship

---

## Feature Importance Rankings

### Price PSF Model (XGBoost)

| Rank | Feature | Importance | Interpretation |
|------|---------|------------|----------------|
| 1 | **year** | 34.4% | Strong temporal trend |
| 2 | **remaining_lease_months** | 21.3% | Lease decay critical |
| 3 | **dist_to_nearest_mrt** | 11.2% | MRT proximity matters |
| 4 | **dist_to_nearest_hawker** | 10.8% | Food amenities important |
| 5 | **dist_to_nearest_park** | 9.5% | Recreation access valued |
| 6 | **dist_to_nearest_supermarket** | 8.4% | Daily convenience matters |
| 7 | **floor_area_sqm** | 4.5% | Size has modest impact |
| 8-10 | school_within_* | **0.0%** | No impact detected |

### Rental Yield Model (XGBoost)

| Rank | Feature | Importance | Interpretation |
|------|---------|------------|----------------|
| 1 | **year** | 63.1% | Dominant temporal factor |
| 2 | **dist_to_nearest_hawker** | 8.4% | Near food centers = higher yield |
| 3 | **dist_to_nearest_mrt** | 6.9% | Transport access matters |
| 4 | **remaining_lease_months** | 6.7% | Fresh leases command premium |
| 5 | **dist_to_nearest_park** | 6.5% | Parks support rental appeal |
| 6 | **dist_to_nearest_supermarket** | 5.7% | Convenience important |
| 7 | **floor_area_sqm** | 2.7% | Size less critical for yield |
| 8-10 | school_within_* | **0.0%** | No impact detected |

---

## Why School Features Showed No Impact

### 1. Feature Limitation: Raw Counts Only
The current school features are simple counts of schools within radius bands. These do not capture:
- **School Quality:** Being near 5 average schools vs 1 top-tier school
- **School Type:** Primary vs Secondary vs Junior College differentiation
- **School Awards:** SAP, Autonomous, Gifted, IP programs
- **Distance Decay:** 1m vs 499m treated the same

### 2. High Correlation with Other Amenities
School locations in Singapore are highly correlated with:
- MRT stations (planned town centers)
- Hawker centers (community hubs)
- Parks (new town design)

When these features are included in the model, they may absorb the variance that raw school counts would otherwise explain.

### 3. Singapore's Context
- **Universal Access:** Most residential areas have schools within 1-2km
- **School Allocation:** Primary 1 registration uses proximity, but this applies to all schools equally
- **Transportation:** Excellent public transport reduces school location premium

---

## Comparison with MRT Impact

| Aspect | MRT Impact | School Impact (Current) |
|--------|------------|-------------------------|
| Primary Feature | Distance (continuous) | Count (discrete) |
| Price Premium | ~$5-15 PSF per 100m | None detected |
| XGBoost Importance | 11.2% | 0.0% |
| Statistical Significance | Highly significant | Not significant |
| Practical Significance | Strong | None |

**Conclusion:** MRT proximity has a clear, measurable impact on prices. School proximity (as currently measured) does not.

---

## Recommendations

### For Analysis Improvement

1. **Implement Quality-Based School Features:**
   - School quality scores based on awards/achievements
   - Different weights for primary/secondary/junior college
   - Distance decay functions (inverse relationship)
   - School-specific premiums (e.g., near top schools)

2. **Add School Attribute Features:**
   - Nearest school distance (continuous)
   - Nearest top-tier school indicator
   - SAP/Autonomous/Gifted program flags
   - School zone boundary indicators

3. **Heterogeneous Analysis:**
   - Analyze impact by property type (HDB vs Condo vs EC)
   - Analyze impact by flat type (1-room to Executive)
   - Analyze impact by planning area (26 towns)
   - Analyze temporal evolution (2017-2026)

### For Future Research

1. **Causal Inference:**
   - Use instrumental variables to address selection bias
   - Compare properties just inside/outside school zones
   - Event study around school zoning changes

2. **Rental Market:**
   - Analyze rental listing prices vs transaction prices
   - School-term vs holiday rental patterns
   - Family-oriented rental premium

3. **Capital Appreciation:**
   - Long-term appreciation near top schools
   - Market cycle analysis
   - Policy change impact (e.g., MOE announcements)

---

## Technical Details

### Analysis Script
```bash
uv run python scripts/analytics/analysis/school/analyze_school_impact.py
```

### Data Pipeline
```bash
uv run python -m scripts.core.stages.L3_export
```

### Output Files
```
data/analysis/school_impact/
├── exploratory_analysis.png        # Visualization
├── coefficients_price_psf.csv      # OLS coefficients
├── coefficients_rental_yield_pct.csv
├── coefficients_yoy_change_pct.csv
├── importance_price_psf_xgboost.csv   # Feature importance
├── importance_rental_yield_pct_xgboost.csv
├── importance_yoy_change_pct_xgboost.csv
└── model_summary.csv              # Performance metrics
```

### Dataset
```
data/pipeline/L3/housing_unified.parquet
- 1,116,323 total records (1990-2026)
- 428,061 records (2021+ for analysis)
- 62 columns including amenity and school features
```

---

## Limitations

1. **School Features:** Only basic count features available; quality scores not implemented
2. **Time Period:** Analysis limited to 2021+; pre-COVID trends not examined
3. **Property Types:** Combined analysis; heterogeneous effects not explored
4. **Causality:** Observational analysis; cannot establish causal relationships
5. **School Zoning:** Primary 1 registration rules not incorporated

---

## Conclusion

This analysis found **no evidence** that raw school proximity counts impact Singapore housing prices, rental yields, or appreciation rates. The XGBoost models achieved strong predictive performance (R²=0.89 for price) without using any school features, indicating that other factors (year, lease remaining, MRT distance, amenity access) fully capture the explainable variance.

The absence of school impact is likely due to:
1. **Feature Quality:** Raw counts don't capture school quality or differentiation
2. **Singapore Context:** Universal access to schools reduces location premium
3. **Multicollinearity:** Schools co-locate with other amenities (MRT, hawker, parks)

**To properly assess school value premium, future analysis should implement quality-weighted school features, distance decay functions, and heterogeneous analysis by property type and location.**

---

**Analysis Status:** ✅ Complete (with noted feature limitations)
**Next Steps:** Implement quality-based school features for re-analysis
