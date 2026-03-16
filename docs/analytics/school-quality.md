---
title: School Quality Impact on Singapore Property Prices
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

## Appendix A: Technical Summary

- Sample: **194,165 transactions** after filtering.
- OLS and XGBoost both found school-related variables to be meaningful predictors.
- Spatial validation showed large generalization gaps, implying neighborhood-specific learning.
- RDD around the 1km cutoff exposed selection bias and assumption violations.

## Appendix B: Caveats

- School quality is entangled with neighborhood reputation, amenity mix, and household sorting.
- Admission-policy relevance may vary by buyer type and child age.
- Predictive importance should not be read as proof of a clean, stable causal premium.
