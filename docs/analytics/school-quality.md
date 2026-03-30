---
title: School Quality Impact
category: "market-analysis"
description: What the data says about school-related housing premiums, where the effect is strongest, and why causal claims need caution
status: published
date: 2026-02-06
personas:
  - investor
  - first-time-buyer
  - upgrader
readingTime: "8 min read"
technicalLevel: intermediate
---

# School Quality Impact

**Analysis Date**: 2026-02-06  
**Sample**: 194,165 transactions  
**Primary Focus**: Post-2021 housing market

## Key Takeaways

### The clearest finding

Properties near stronger schools do appear to command higher prices in standard pricing models, but the premium is **not cleanly causal**. A meaningful share of the observed effect likely reflects broader neighborhood quality.

### What this means in practice

- **Families** should treat school access as one input, not a blank cheque for paying more.
- **Investors** should be careful about assuming the “school premium” will translate directly into rental or resale outperformance.
- **Analytically**, predictive importance is stronger than causal certainty.

## Core Findings

### 1. School quality shows up in pricing models

| Feature | Coefficient | Interpretation |
|---------|-------------|----------------|
| `school_primary_quality_score` | +$9.66 PSF | Higher quality is associated with higher prices |
| `school_primary_dist_score` | +$6.27 PSF | Better primary-school access adds value |
| `school_secondary_dist_score` | +$3.52 PSF | Secondary access also matters |

For a 1,000 sqft unit, a 3-point quality-score difference implies about **$29,000** in modeled price difference.

**Impact**

- This is a real enough market pattern to influence listings and buyer behavior.
- It is not strong evidence that school access alone caused the full premium.

### 2. The effect changes by region

<div data-chart-metadata="true" data-chart="comparison" data-chart-title="School quality effect by HDB region" data-chart-columns="Records,School Quality Coefficient,R²"></div>

| Segment | Records | School Quality Coefficient | R² |
|---------|---------|---------------------------|-----|
| HDB_OCR | 146,553 | +$9.63 PSF | 0.53 |
| HDB_RCR | 46,298 | -$23.67 PSF | 0.80 |
| HDB_CCR | 1,314 | about $0 PSF | 0.87 |

**What stands out**

- In **OCR**, school quality behaves like a positive differentiator.
- In **RCR**, the sign flips, which suggests other neighborhood forces dominate.
- In **CCR**, school access is largely drowned out by centrality and premium-location effects.

### 3. The causal read is much weaker than the predictive read

Regression discontinuity around the 1km admissions boundary does **not** support a clean positive premium.

| RDD metric | Value | Interpretation |
|-----------|-------|----------------|
| Treatment effect | -$79.47 PSF | Units within 1km were cheaper after controls |
| Sample size | 52,881 | Large enough to take seriously |
| Covariate balance | Failed | Boundary groups differ systematically |

**Impact**

- The headline “within 1km premium” is too simplistic.
- Buyers should expect school-zone properties to differ on age, size, MRT distance, and neighborhood profile.

## Decision Guide

### For families

- Pay for school access only when the school choice genuinely matters to your household.
- Compare unit age, size, and financing burden before accepting a school-related premium.
- Properties just outside key thresholds may offer better value if the neighborhood quality is similar.

### For investors

- Do not assume school access alone improves rental yield.
- The school signal looks stronger for price levels and some appreciation models than for immediate yield.

### For upgraders

- Distinguish between paying for a specific school and paying for a neighborhood that happens to contain strong schools.

## Technical Appendix

### Data Used

- **Primary input**: `data/parquets/L3/housing_unified.parquet`
- **Sample**: 194,165 transactions, 2021 onward, within 2 km of primary schools
- **RDD sub-sample**: 52,881 near-boundary transactions (800-1200 m from nearest school)

### Methodology

- **OLS and XGBoost** with school features (`school_primary_quality_score`, `school_primary_dist_score`, `school_secondary_dist_score`) plus controls (floor area, lease, amenities)
  - XGBoost parameters: n_estimators=100, max_depth=6, learning_rate=0.1
- **Regression discontinuity design (RDD)** at the 1 km cutoff (Singapore primary school admission boundary)
  - Bandwidth: 200 m on each side of boundary
  - Model: `price = α + τ·treated + β·running_var + γ·(treated × running_var) + controls`
  - Robust HC3 standard errors, 95% confidence intervals
- **Covariate balance testing**: t-tests at cutoff to check if boundary groups differ systematically
- **Bandwidth sensitivity**: tested at 100-300 m; placebo tests at 800 m and 1200 m fake cutoffs
- **Spatial cross-validation**: standard 5-fold CV vs GroupKFold by planning area, to measure generalization gaps

### Technical Findings

- **OLS coefficients**: `school_primary_quality_score` +$9.66 PSF, `school_primary_dist_score` +$6.27 PSF, `school_secondary_dist_score` +$3.52 PSF
- **Practical scale**: 1,000 sqft unit × 3-point quality score difference ≈ $29,000 modeled price difference
- **RDD treatment effect**: -$79.47 PSF (within 1 km cheaper after controls)
- **Covariate balance**: FAILED — boundary groups differ systematically on age, size, MRT distance, and neighborhood profile
- **Regional split (heterogeneous)**:
  - OCR: +$9.63 PSF (R²=0.53, n=146,553)
  - RCR: -$23.67 PSF (R²=0.80, n=46,298) — sign flips, neighborhood forces dominate
  - CCR: ~$0 PSF (R²=0.87, n=1,314) — school effect drowned out by centrality
- **Spatial CV**: large generalization gap between standard CV and spatial CV, implying neighborhood-specific learning

### Conclusion

School quality shows up clearly in predictive models (OLS and XGBoost agree on direction and magnitude), but the causal read is much weaker. The RDD at the 1 km boundary does NOT support a clean positive premium — if anything, the treatment effect is negative after controls, and covariate balance fails. This means properties near good schools differ systematically on many dimensions beyond school access. The predictive importance of school features is real and decision-useful, but should not be interpreted as proof of a stable, isolated causal premium. Key limitations: school quality is entangled with neighborhood reputation, amenity mix, and household sorting; admission-policy relevance varies by buyer type and child age.

### Scripts

- `scripts/analytics/analysis/school/analyze_school_impact.py` — OLS + XGBoost
- `scripts/analytics/analysis/school/analyze_school_rdd.py` — Regression discontinuity at 1 km boundary
- `scripts/analytics/analysis/school/analyze_school_heterogeneous.py` — By region (CCR/RCR/OCR)
- `scripts/analytics/analysis/school/analyze_school_spatial_cv.py` — Spatial cross-validation
