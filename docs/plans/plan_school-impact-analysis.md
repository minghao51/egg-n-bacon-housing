---
title: School Features Impact Analysis
category: technical-reports
description: Investigation of school proximity and quality impact on Singapore housing prices and yields
status: published
---

# School Features Impact Analysis

**Created:** 2025-02-02

## Overview

This analysis pipeline investigates the impact of school proximity and quality on Singapore housing prices, rental yields, and appreciation rates. The analysis is structured into four complementary scripts that analyze school features from different perspectives.

## Research Questions

1. **What is the monetary value of school quality?** How much premium do buyers pay for properties near high-quality schools?
2. **Does school impact differ by property type?** Do HDB, Condominium, and EC buyers value schools differently?
3. **How has school premium evolved over time?** Has COVID-19 or other events changed the school premium?
4. **Are there heterogeneous effects?** Does school impact vary by flat type, town, or price tier?

## School Features

### Distance Features
- `school_within_500m`: Number of schools within 500m
- `school_within_1km`: Number of schools within 1km
- `school_within_2km`: Number of schools within 2km

### Accessibility & Quality Scores
- `school_accessibility_score`: Overall school accessibility (0-1 scale)
- `school_primary_dist_score`: Primary school distance score
- `school_primary_quality_score`: Primary school quality score (based on school awards/achievements)
- `school_secondary_dist_score`: Secondary school distance score
- `school_secondary_quality_score`: Secondary school quality score
- `school_density_score`: School density in surrounding area

## Pipeline Scripts

### 1. Main Impact Analysis (`analyze_school_impact.py`)

**Purpose:** Comprehensive analysis of school features on housing prices using multiple modeling approaches.

**Key Features:**
- Exploratory data analysis (correlations, distributions)
- OLS regression with multiple specifications (linear, log-transformed)
- XGBoost modeling with SHAP values
- Analysis across three target variables:
  - `price_psf`: Transaction price per square foot
  - `rental_yield_pct`: Rental yield percentage
  - `yoy_change_pct`: Year-over-year price appreciation

**Outputs:**
- `exploratory_analysis.png`: Visualization of school-price relationships
- `coefficients_*.csv`: OLS regression coefficients by target
- `importance_*_xgboost.csv`: Feature importance from XGBoost
- `shap_*.csv`: SHAP values for model interpretability
- `model_summary.csv`: Performance comparison across models

**Usage:**
```bash
uv run python scripts/analytics/analysis/school/analyze_school_impact.py
```

### 2. Property Type Comparison (`analyze_school_by_property_type.py`)

**Purpose:** Compare school impact across HDB, Condominium, and EC property types.

**Key Features:**
- Separate models for each property type
- Interaction models (property_type × school_features)
- Statistical significance testing of differences
- Feature importance comparison heatmap

**Research Questions:**
- Do private property buyers (Condo/EC) value schools more than HDB buyers?
- Are school quality premiums higher for premium properties?
- Should investment strategies vary by property type?

**Outputs:**
- `property_type_comparison.csv`: Comparison table with coefficients
- `property_type_comparison.png`: Visualization of differences
- `interaction_model_coefficients.csv`: Interaction model results
- `importance_*_xgboost.csv`: Feature importance by property type

**Usage:**
```bash
uv run python scripts/analytics/analysis/school/analyze_school_by_property_type.py
```

### 3. Temporal Evolution Analysis (`analyze_school_temporal_evolution.py`)

**Purpose:** Track how school premiums have changed over time (2017-2026).

**Key Features:**
- Year-by-year school coefficient calculation
- COVID-19 impact assessment (2020-2022)
- Planning area-level temporal trends
- Top/bottom areas by school premium evolution

**Research Questions:**
- Has the school premium increased or decreased over time?
- Did COVID-19 (remote learning) affect school premium?
- Which areas have seen the largest increases in school premium?
- Are school premiums cyclical or trending?

**Outputs:**
- `yearly_coefficients_*.csv`: Yearly coefficients by property type
- `area_yearly_coefficients_*.csv`: Area-year level analysis
- `covid_impact_analysis_*.csv`: COVID period comparison
- `temporal_evolution_overview.png`: 4-panel temporal visualization
- `top_areas_evolution_*.png`: Area-level evolution plots
- `temporal_summary.csv`: Summary statistics table

**Usage:**
```bash
uv run python scripts/analytics/analysis/school/analyze_school_temporal_evolution.py
```

### 4. Heterogeneous Effects Analysis (`analyze_school_heterogeneous.py`)

**Purpose:** Understand how school impact varies within HDB subgroups.

**Key Features:**
- Analysis by flat type (1 ROOM to EXECUTIVE)
- Analysis by town (26 HDB towns)
- Analysis by remaining lease (<60 to 90+ years)
- Analysis by price tier (budget to premium)

**Research Questions:**
- Do certain flat types value schools more?
- Which towns have the highest/lowest school premiums?
- Does remaining lease affect school premium?
- Do budget vs premium HDB buyers value schools differently?

**Outputs:**
- `heterogeneous_flat_type.csv`: School impact by flat type
- `heterogeneous_town.csv`: School impact by town
- `heterogeneous_lease.csv`: School impact by lease remaining
- `heterogeneous_price_tier.csv`: School impact by price tier
- `heterogeneous_effects.png`: 4-panel visualization

**Usage:**
```bash
uv run python scripts/analytics/analysis/school/analyze_school_heterogeneous.py
```

## Enhanced Analysis Modules

### 5. Spatial Cross-Validation (`analyze_school_spatial_cv.py`)

**Purpose:** Test whether school impact models generalize to new geographic areas, guarding against spatial autocorrelation bias.

**Key Features:**
- Compares standard KFold vs GroupKFold (spatial) cross-validation
- Calculates spatial generalization gap (R² drop when testing on new areas)
- Identifies which planning areas generalize well vs poorly
- Tests for spatial autocorrelation in residuals using Moran's I

**Research Questions:**
- Do school impact models overfit to specific neighborhoods?
- Which planning areas are hardest to predict?
- How much does spatial autocorrelation inflate performance metrics?

**Outputs:**
- `spatial_cv_performance.csv`: Performance comparison (OLS/RF/XGBoost)
- `planning_area_generalization.csv`: Area-by-area diagnostics
- `spatial_autocorrelation_test.csv`: Moran's I test results

**Usage:**
```bash
uv run python scripts/analytics/analysis/school/analyze_school_spatial_cv.py
```

**Interpretation:**
- **Generalization gap >10%**: Significant spatial autocorrelation, model needs spatial regularization
- **High gap area**: Model fails to generalize, may need area-specific features
- **Moran's I >0**: Residuals clustered spatially (violates independence assumption)

### 6. Causal Inference with RDD (`analyze_school_rdd.py`)

**Purpose:** Establish causal effect of school proximity using Regression Discontinuity Design at 1km admission boundary.

**Key Features:**
- Exploits Singapore's primary school 1km admission priority as natural experiment
- Compares properties just inside vs just outside 1km radius
- Bandwidth sensitivity testing (100m-300m)
- Placebo tests at fake cutoffs (800m, 1200m)
- Covariate balance validation

**Research Questions:**
- What is the **causal** effect of being within 1km of a top school?
- Do OLS coefficients suffer from selection bias?
- How robust is the causal estimate to bandwidth changes?

**Outputs:**
- `rdd_main_effect.csv`: Causal estimate (τ) with robust standard errors
- `rdd_bandwidth_sensitivity.csv`: Results across bandwidths
- `rdd_covariate_balance.csv`: Balance statistics for controls
- `rdd_placebo_tests.csv`: Fake cutoff results (should be null)
- `rdd_visualization.png`: Price discontinuity plot

**Usage:**
```bash
uv run python scripts/analytics/analysis/school/analyze_school_rdd.py
```

**Interpretation:**
- **τ = $25 PSF (p<0.05)**: Being within 1km causes $25 PSF premium
- **Covariates balanced**: No significant differences at cutoff (validation passed)
- **Placebo tests null**: No effect at fake cutoffs (RDD specification valid)
- **Bandwidth stable**: τ similar across 100-300m (robust estimate)

**Limitations:**
- Only estimates **local** effect (for properties near 1km boundary)
- Requires sufficient sample near boundary (may need to aggregate schools)
- Does not account for fuzzy eligibility (not all within 1km qualify)

### 7. Segmentation & Interaction Analysis (`analyze_school_segmentation.py`)

**Purpose:** Reveal how school premium varies across market segments and property characteristics.

**Key Features:**
- 9 market segments: property_type (HDB/Condo/EC) × region (CCR/RCR/OCR)
- Separate OLS models per segment
- Pooled interaction model with explicit interaction terms
- Tests for heterogeneous treatment effects

**Research Questions:**
- Do Condo buyers value schools more than HDB buyers?
- Does school premium vanish in CCR (international schools compete)?
- Do large luxury units discount school proximity?
- Is there synergy between school and MRT accessibility?

**Outputs:**
- `segment_coefficients.csv`: School premium by 9 market segments
- `interaction_model_results.csv`: All interaction coefficients
- `segment_r2_comparison.csv`: Model performance across segments

**Usage:**
```bash
uv run python scripts/analytics/analysis/school/analyze_school_segmentation.py
```

**Interpretation:**
- **Higher coefficient in OCR**: School premium larger outside central region
- **school_x_mrt negative**: School and MRT proximity substitute (not complement)
- **school_x_area negative**: Luxury buyers (large units) value schools less
- **Segment R² varies**: School features explain more variance in some segments

**Interaction Effects to Examine:**
- `school × Condominium`: Do private buyers value schools more?
- `school × CCR`: Does central location reduce school premium?
- `school × floor_area`: Do larger units discount school access?
- `school × MRT_distance`: Accessibility synergy or substitute?

## Data Requirements

All scripts require:
- **Unified dataset:** `data/pipeline/L3/housing_unified.parquet`
- **School features:** Must be calculated by `scripts/core/stages/L3_export.py`
- **Time period:** 2021+ for main analysis, 2017+ for temporal analysis

### Prerequisites

1. **Run L3 Export Pipeline:**
   ```bash
   # Ensure school features are calculated
   uv run python scripts/core/stages/L3_export.py
   ```

2. **Verify School Features:**
   ```python
   import pandas as pd
   df = pd.read_parquet("data/pipeline/L3/housing_unified.parquet")
   school_cols = [col for col in df.columns if 'school' in col.lower()]
   print(school_cols)
   ```

## Output Structure

All analysis outputs are saved to:
```
data/analysis/school_impact/
├── exploratory_analysis.png
├── coefficients_*.csv
├── importance_*_xgboost.csv
├── shap_*.csv
├── model_summary.csv
├── property_type_comparison.csv
├── property_type_comparison.png
├── interaction_model_coefficients.csv
└── heterogeneous_*.csv
```

Temporal evolution outputs:
```
data/analysis/school_temporal_evolution/
├── temporal_evolution_overview.png
├── top_areas_evolution_*.png
├── yearly_coefficients_*.csv
├── area_yearly_coefficients_*.csv
├── covid_impact_analysis_*.csv
└── temporal_summary.csv
```

## Key Metrics

### School Premium Definition
- **Metric:** Price premium per 0.1 point increase in school quality score
- **Interpretation:** How much buyers pay for better school accessibility/quality
- **Units:** $ per square foot (PSF)

### Model Performance
- **OLS R²:** typically 0.4-0.7 for price models
- **XGBoost R²:** typically 0.7-0.9 for price models
- **Primary feature:** `school_accessibility_score` or `school_primary_quality_score`

## Interpretation Guide

### Positive Coefficient
Properties near high-quality schools command a price premium. For example:
- Coefficient: 15.5
- Interpretation: Every 0.1 increase in school quality score = $15.5 PSF premium
- For a 1000 sqft apartment: $15,500 premium per 0.1 score point

### Negative Coefficient
Properties near schools have lower prices (unusual, may indicate confounding factors)

### Temporal Changes
- **Increasing premium:** Schools becoming more valuable over time
- **COVID impact:** Check if remote learning reduced school premium
- **Cyclical patterns:** May correlate with policy changes or market cycles

## Comparison with MRT Analysis

| Aspect | MRT Analysis | School Analysis |
|--------|--------------|-----------------|
| Primary Feature | Distance (meters) | Quality score (0-1) |
| Measurement | Continuous distance | Composite score |
| Key Finding | ~$5-15 PSF per 100m | ~$10-30 PSF per 0.1 score |
| Heterogeneity | Varies by town | Varies by town/flat type |
| Temporal Trend | Stable/increasing | Stable/increasing |

## Future Enhancements

1. **Causal Inference:** Use instrumental variables to address selection bias
2. **School-Specific Analysis:** Impact of being near specific top schools (e.g., Raffles, Nanyang)
3. **Rental Impact:** Does school quality affect rental yields?
4. **Capital Appreciation:** Do school-quality areas appreciate faster?
5. **Policy Analysis:** Impact of school zoning changes on prices

## References

- [Singapore School Information](https://www.moe.gov.sg/schoolfinder)
- [HDB Resale Prices](https://data.gov.sg/dataset/resale-flat-prices)
- [URA Private Property Transactions](https://www.ura.gov.sg/property-market-information/market-information/property-transaction-information)

## Changelog

- **2025-02-02:** Initial pipeline creation
  - Main impact analysis with OLS/XGBoost/SHAP
  - Property type comparison
  - Temporal evolution (2017-2026)
  - Heterogeneous effects within HDB

- **2025-02-05:** Enhanced analysis modules
  - Spatial cross-validation framework
  - Causal inference with RDD at 1km boundary
  - Segmentation and interaction effects analysis
  - Robustness validation suite
