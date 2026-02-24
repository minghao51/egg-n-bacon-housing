# Enhanced School Impact Analysis Design

**Created:** 2025-02-05
**Status:** Design Approved

## Overview

Enhances the existing school impact analysis pipeline with three advanced analytical modules to address spatial autocorrelation, establish causal claims, and reveal market heterogeneity.

## Problem Statement

The current school impact analysis (`analyze_school_impact.py`) has three key limitations:

1. **Spatial Autocorrelation Bias:** Standard random cross-validation allows properties from the same planning area in both train and test sets, inflating performance metrics and failing to test geographic generalization.

2. **Correlation ≠ Causation:** OLS coefficients show association but cannot establish that school proximity *causes* higher prices. Selection bias (families choosing good areas) confounds estimates.

3. **Heterogeneity Masked:** Pooled models average across diverse market segments (HDB vs Condo, CCR vs OCR), hiding critical differences in how buyers value schools.

## Proposed Solution

### Module 1: Spatial Cross-Validation Framework

**Objective:** Test whether models generalize to new geographic areas, not just random properties.

**Approach:**
- Use `sklearn.model_selection.GroupKFold` with `planning_area` as grouping variable
- Compare standard KFold R² vs spatial GroupKFold R²
- Calculate spatial generalization gap: `gap = R²_standard - R²_spatial`
- Identify planning areas where model fails to generalize

**Validation Criteria:**
- If gap > 0.10 (10% R² drop): Significant spatial autocorrelation detected
- Model requires spatial blocking or regularization by region
- Report which planning areas are "hard to predict" (high test error)

**Key Outputs:**
- `spatial_cv_performance.csv`: Performance comparison table
- `planning_area_generalization.csv`: Area-by-area diagnostics
- `spatial_autocorrelation_test.csv`: Moran's I statistic on residuals

### Module 2: Regression Discontinuity Design (RDD)

**Objective:** Establish causal effect of school proximity on property prices.

**Natural Experiment:** Singapore's primary school admission system gives priority to students living within 1km radius. This creates a sharp discontinuity at exactly 1km.

**Approach:**
- Define treatment: Properties within 1km of top-tier primary school
- Define control: Properties just outside 1km (1000-1200m)
- Optimal bandwidth: 200m on each side of boundary
- Running variable: `distance_to_primary - 1000` (centered at cutoff)

**RDD Specification:**
```
price_psf = α + τ·treated + β·running_var + γ·(treated×running_var) + controls + ε

Where τ = Local Average Treatment Effect (causal estimate)
```

**Validation Tests:**
1. **Covariate Balance:** Floor area, lease, MRT distance vary smoothly at 1km
2. **Bandwidth Sensitivity:** Test 100m, 200m, 300m bandwidths
3. **Placebo Tests:** Fake cutoffs at 800m and 1200m (should show null effect)
4. **Density Test:** McCrary test for manipulation of running variable

**Interpretation:**
- If τ = $25 PSF (p<0.01): Causal premium for school access
- Compare τ to OLS coefficient: Similar = minimal selection bias
- If τ > OLS: OLS underestimates (negative selection bias)

**Key Outputs:**
- `rdd_main_effect.csv`: Causal estimate with robust SE
- `rdd_bandwidth_sensitivity.csv`: Results across bandwidths
- `rdd_covariate_balance.csv`: Balance statistics
- `rdd_placebo_tests.csv`: Fake cutoff results
- `rdd_visualization.png`: Price jump at 1km boundary

### Module 3: Segmentation & Interaction Effects

**Objective:** Reveal how school premium varies across market segments and property characteristics.

**Two-Stage Analysis:**

**Stage 1: Hierarchical Segmentation**
- Create 9 market segments: `property_type × market_region`
  - HDB × {CCR, RCR, OCR} = 3 segments
  - Condominium × {CCR, RCR, OCR} = 3 segments
  - EC × {CCR, RCR, OCR} = 3 segments
- Run separate OLS/XGBoost models per segment
- Extract and compare school coefficients across segments
- Test for significant differences using Wald tests

**Stage 2: Pooled Interaction Model**
```
price_psf = α + β₁·school_quality + β₂·property_type + β₃·region
           + β₄·(school_quality × property_type)
           + β₅·(school_quality × region)
           + β₆·(school_quality × floor_area)
           + β₇·(school_quality × mrt_distance)
           + controls + ε
```

**Key Research Questions:**
1. **Property Type:** Do Condo buyers value schools more than HDB buyers?
2. **Region:** Does school premium vanish in CCR (international schools)?
3. **Size:** Do luxury units (large floor_area) discount school proximity?
4. **Accessibility:** Is there synergy between school and MRT proximity?

**Validation:**
- Joint F-test for interaction terms significance
- Chow test for structural breaks between segments
- Compare pooled R² vs segmented R² (prefer segmented if ΔR² > 0.05)

**Key Outputs:**
- `segment_coefficients.csv`: School premium by 9 segments
- `interaction_model_results.csv`: All interaction coefficients with p-values
- `segment_r2_comparison.csv`: Model performance comparison
- `regional_heterogeneity_map.png`: Geographic visualization
- `interaction_surface_plots.png`: 3D interaction effect plots

## Implementation Architecture

### File Structure

```
scripts/analytics/analysis/school/
├── analyze_school_impact.py              # EXISTING (minor enhancements)
├── analyze_school_spatial_cv.py          # NEW - Module 1
├── analyze_school_rdd.py                 # NEW - Module 2
├── analyze_school_segmentation.py        # NEW - Module 3
└── utils/
    ├── __init__.py
    ├── spatial_validation.py             # Shared CV utilities
    ├── rdd_estimators.py                 # Shared RDD utilities
    └── interaction_models.py             # Shared segmentation utilities
```

### Data Dependencies

**Input:**
- `data/pipeline/L3/housing_unified.parquet` (111万+ records, 110 columns)
- Required columns: `planning_area`, `property_type`, `school_*`, `nearest_schoolPRIMARY_*`

**Output:**
- `data/analysis/school_spatial_cv/` (Module 1)
- `data/analysis/school_rdd/` (Module 2)
- `data/analysis/school_segmentation/` (Module 3)

### New Dependencies

```toml
[project.dependencies]
scipy = "*"           # For McCrary density test
statsmodels = "*"     # For RDD robust standard errors
```

## Implementation Order

1. **Phase 1: Infrastructure** (~2 hours)
   - Create `utils/` directory structure
   - Implement shared utility functions
   - Add scipy and statsmodels dependencies

2. **Phase 2: Spatial CV** (~3 hours)
   - Implement `analyze_school_spatial_cv.py`
   - Add GroupKFold wrapper functions
   - Create spatial performance comparison logic
   - Generate diagnostic visualizations

3. **Phase 3: RDD Causal Inference** (~4 hours)
   - Implement `analyze_school_rdd.py`
   - Build RDD dataset creator (1km boundary logic)
   - Implement bandwidth sensitivity testing
   - Create validation tests (placebo, balance, density)
   - Generate discontinuity visualization

4. **Phase 4: Segmentation** (~3 hours)
   - Implement `analyze_school_segmentation.py`
   - Build 9-segment grouping logic
   - Implement separate model estimation per segment
   - Build pooled interaction model
   - Generate heterogeneity visualizations

5. **Phase 5: Integration & Testing** (~2 hours)
   - Run all three modules on full dataset
   - Verify results align with expectations
   - Cross-validate findings across modules
   - Update documentation

6. **Phase 6: Documentation** (~1 hour)
   - Update `docs/analytics/school-impact-analysis.md`
   - Add new sections for each module
   - Update usage examples and interpretation guide
   - Add changelog entry

**Total Estimated Time:** ~15 hours

## Success Criteria

### Module 1 Success
- Spatial CV R² at least 5% lower than standard CV (confirms spatial autocorrelation exists)
- Identify at least 3 planning areas with poor generalization
- Moran's I test significant (p < 0.05) on OLS residuals

### Module 2 Success
- RDD estimate τ statistically significant (p < 0.05)
- Covariate balance test passes (no significant jumps at 1km)
- Placebo tests show null effects at fake cutoffs
- Bandwidth sensitivity shows stable estimates across 100-300m

### Module 3 Success
- At least 2 interaction terms significant (p < 0.05)
- Segmented models outperform pooled by ΔR² > 0.05
- Clear heterogeneity pattern: e.g., school premium higher in OCR than CCR
- Visualization reveals interpretable patterns

### Overall Validation
- All three modules run end-to-end without errors
- Results are consistent across modules (e.g., RDD causal effect ≈ average segmented coefficient)
- Findings align with economic intuition (e.g., families with children value schools)
- Documentation clear enough for non-technical stakeholders

## Risks & Mitigations

### Risk 1: Insufficient Data at 1km Boundary
- **Mitigation:** If RDD sample < 1000 properties, expand bandwidth to 300m or aggregate across schools

### Risk 2: Small Planning Areas Break GroupKFold
- **Mitigation:** Merge areas with <500 records with neighbors, or reduce n_splits to 3

### Risk 3: High Multicollinearity in Interaction Model
- **Mitigation:** Center features before interaction, use ridge regression, drop insignificant terms

### Risk 4: SHAP/Visualization Failures
- **Mitigation:** Graceful degradation with warnings, output CSVs always generated

## Future Enhancements

1. **Fuzzy RDD:** Account for imperfect compliance (not all within 1km get priority)
2. **School-Specific RDD:** Separate RDD for each top-tier school
3. **Instrumental Variables:** Use school opening dates as instruments
4. **Spatiotemporal Models:** Add time dimension to segmentation
5. **Causal Forests:** Machine learning approach to heterogeneous treatment effects

## References

- **Singapore Primary School Admission:** [MOE School Finder](https://www.moe.gov.sg/schoolfinder)
- **RDD Methodology:** Cunningham (2021), "Causal Inference: The Mixtape"
- **Spatial CV:** Roberts et al. (2017), "Cross-validation strategies for spatial data"
- **Singapore Property Regions:** URA market segment definitions (CCR/RCR/OCR)

## Changelog

- **2025-02-05:** Initial design approved
  - Three-module architecture defined
  - Implementation plan outlined
  - Success criteria established
