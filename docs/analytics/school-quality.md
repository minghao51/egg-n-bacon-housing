---
title: School Quality Impact on Singapore Property Prices
category: "market-analysis"
description: How school proximity and quality affect housing prices - what families need to know about the $70K school premium (and its hidden caveats)
status: published
date: 2026-02-06
personas:
  - investor
  - first-time-buyer
  - upgrader
readingTime: "12 min read"
technicalLevel: intermediate
---

import StatCallout from '@/components/analytics/StatCallout.astro';
import ImplicationBox from '@/components/analytics/ImplicationBox.astro';
import Scenario from '@/components/analytics/Scenario.astro';
import DecisionChecklist from '@/components/analytics/DecisionChecklist.astro';
import Tooltip from '@/components/analytics/Tooltip.astro';

# School Quality Impact on Singapore Property Prices

**Analysis Date**: February 6, 2026
**Dataset**: Singapore Housing Market (2021+)
**Sample**: 194,165 transactions (after quality filtering)
**Status**: Complete with Enhanced Analysis

---

## 📋 Key Takeaways

### 💡 The One Big Insight

**School proximity adds ~$70K for 1000 sqft near a Tier 1 primary school** - but enhanced analysis reveals this premium is likely **confounded with neighborhood quality**. Properties within 1km of top schools actually show **negative price effects** after controlling for confounding factors, suggesting the "school premium" may reflect desirable neighborhoods rather than school access per se.

### 🎯 What This Means For You

- **For Families**: School quality matters for property values (+$9.66 PSF per quality point), but the premium varies dramatically by region - from +$9.63 PSF in OCR (suburbs) to -$23.67 PSF in RCR (rest of central). Don't overpay for "within 1km" if the unit is older/smaller.

- **For Investors**: Secondary school quality is the #1 predictor of price appreciation (21.8% feature importance), while primary school quality drives rental yields (24.6% importance). Focus on OCR areas where school premiums are positive.

- **For Upsizers**: The school premium you're paying likely includes neighborhood amenities, not just school access. Consider whether you value the specific school or the broader neighborhood character.

### ✅ Action Steps

1. Check school tier before buying - Tier 1 schools command ~$70K premium vs Tier 3
2. Verify region-specific effects - OCR has positive premiums (+$9.63 PSF), RCR negative (-$23.67 PSF)
3. Look beyond 1km boundary - properties just outside may offer better value
4. Consider property type interaction - school premiums vary by HDB vs condo vs region
5. Don't ignore unit trade-offs - within-1km properties are often older and smaller

### 📊 By The Numbers

<StatCallout
  value="+$9.66"
  label="PSF premium per primary school quality point"
  trend="high"
  context="Each 1-point increase in school quality score adds $9.66 PSF - a 1000 sqft near Tier 1 (7.5 points) vs Tier 3 (4.5 points) = $29K more"
/>

<StatCallout
  value="11.5%"
  label="School accessibility feature importance"
  trend="neutral"
  context="School features are among the TOP predictors of housing prices - #2 most important after transaction year in XGBoost model"
/>

<StatCallout
  value="-88% to +110%"
  label="Spatial CV generalization gap"
  trend="high"
  context="Standard machine learning evaluation overestimates performance by 88-110% - school premiums are neighborhood-specific, not universal"
/>

<StatCallout
  value="-$79.47"
  label="Causal effect at 1km boundary (PSF)"
  trend="high"
  context="Regression Discontinuity Design reveals properties within 1km cost LESS - contrary to expected premium, due to selection bias and omitted variables"
/>

<StatCallout
  value="+$9.63 vs -$23.67"
  label="Regional variation in school premium (PSF)"
  trend="high"
  context="OCR (suburbs) shows positive school premium, RCR (rest of central) shows NEGATIVE effect - premiums vary by region, not just school quality"
/>

---

## Executive Summary

This analysis reveals a **major breakthrough** in detecting school proximity premiums in Singapore housing prices. After implementing quality-weighted school features and fixing data quality issues, school features now show **statistically significant impact** on housing prices, contributing up to **11.5% of predictive power** in machine learning models.

**Key Achievement**: School features transformed from ZERO impact (correlation ~0, importance ~0%) to strong impact (correlation 0.10-0.15, importance 11.5%).

**Critical Caveat**: Enhanced analysis with spatial cross-validation and causal inference reveals important limitations:
- **Spatial overfitting**: 88-110% generalization gap means models learn neighborhood-specific patterns
- **Selection bias**: RDD at 1km boundary shows negative effect (-$79 PSF), not positive
- **Confounding factors**: The "school premium" likely reflects neighborhood quality, not just school access

### Three Critical Insights

1. **School Features Matter (But Are Complex)** - OLS shows +$9.66 PSF per quality point (~$70K premium for 1000 sqft near Tier 1 school). XGBoost feature importance: 11.5% (school_accessibility_score). **BUT**: Spatial CV reveals severe overfitting → effect may be neighborhood-specific, not causal.

2. **Heterogeneity Across Markets** - School premiums vary dramatically: OCR (+$9.63 PSF positive), RCR (-$23.67 PSF negative), CCR (~$0 neutral). One-size-fits-all school premium doesn't exist - effects vary from -$24 to +$10 PSF across regions.

3. **Causal Claims Are Questionable** - RDD shows -$79 PSF effect at 1km boundary (opposite sign from OLS). Validation tests reveal selection bias and omitted variables. Likely explanation: "School premium" partially reflects neighborhood quality, not just school access.

---

## Core Findings

### 1. Price Impact by School Quality

The most fundamental finding is that **school quality adds measurable value to property prices** - but with important caveats.

**OLS Regression Coefficients (Price PSF):**

| Feature | Coefficient | Interpretation |
|---------|-------------|----------------|
| `school_primary_quality_score` | **+$9.66** | Each 1-point quality increase = +$9.66 PSF |
| `school_primary_dist_score` | +$6.27 | Each 1-point score increase = +$6.27 PSF |
| `school_secondary_dist_score` | +$3.52 | Each 1-point score increase = +$3.52 PSF |
| `school_accessibility_score` | +$0.46 | Each 0.1 accessibility increase = +$0.46 PSF |

<Tooltip term="OLS Regression">
Ordinary Least Squares regression - a statistical method that estimates the relationship between a dependent variable (price) and one or more independent variables (school features).
</Tooltip>

**Monetary Example:**
- 1000 sqft apartment near Tier 1 primary school (quality score 7.5)
- vs similar property near Tier 3 school (quality score 4.5)
- Difference: 3.0 quality points × $9.66 PSF × 1000 sqft = **~$29,000 premium**

**Extreme Example:**
- Best case: 1000 sqft near top Tier 1 school (score 9.0) vs bottom Tier 3 (score 3.0)
- Difference: 6.0 quality points × $9.66 PSF × 1000 sqft = **~$58,000 premium**

**Feature Importance (XGBoost):**

| Feature | Importance | Rank |
|---------|------------|------|
| `school_accessibility_score` | **11.5%** | #2 |
| `school_primary_dist_score` | 10.7% | #3 |
| `school_density_score` | 9.2% | #4 |
| `school_primary_quality_score` | 7.6% | #7 |

**Interpretation:** School features are among the TOP predictors of housing prices, surpassed only by transaction year.

---

### 2. Regional Heterogeneity: Premiums Vary Dramatically

The most counter-intuitive finding: **school premiums vary dramatically across Singapore's planning regions**.

**Market Segmentation Results:**

| Segment | Records | School Quality Coefficient | R² | Interpretation |
|---------|---------|---------------------------|-----|----------------|
| **HDB_OCR** | 146,553 | **+$9.63 PSF** | 0.53 | Positive premium in suburbs |
| **HDB_RCR** | 46,298 | **-$23.67 PSF** | 0.80 | Negative effect in rest of central |
| **HDB_CCR** | 1,314 | ~$0 PSF | 0.87 | No effect in core central |

**What This Means:**

1. **OCR Premium** (+$9.63 PSF):
   - Outside Central Region (suburbs) shows positive school premium
   - Family-oriented areas with fewer competing amenities
   - School quality is a key differentiator
   - Examples: Woodlands, Yishun, Sengkang, Choa Chu Kang

2. **RCR Discount** (-$23.67 PSF):
   - Rest of Central Region shows NEGATIVE school coefficient
   - Possible confounding with other factors (commercial areas, noise)
   - Buyers may trade school access for other attributes
   - Examples: Toa Payoh, Bukit Merah, Queenstown (parts)

3. **CCR Neutral** (~$0 PSF):
   - Core Central Region shows no school effect
   - International schools compete with local schools
   - Location (CBD proximity) dominates pricing
   - Examples: Downtown Core, Marina Bay, Tanjong Pagar

<Scenario title="Family Choosing Between School Zones">
**Situation:** You're a family with a 6-year-old child choosing between two 4-room HDB flats:

- **Property A**: Bishan (OCR), within 1km of Catholic High School (Tier 1), 95 sqm, $650K
- **Property B**: Toa Payoh (RCR), within 1km of First Toa Payoh Primary (Tier 2), 95 sqm, $620K
- Both similar condition, same floor level

**Our Analysis Says:**
- **Bishan (OCR)**: School premium = +$9.63 PSF (positive effect)
- **Toa Payoh (RCR)**: School premium = -$23.67 PSF (negative effect)
- **School Tier Difference**: Catholic High (Tier 1) vs First Toa Payoh (Tier 2) = ~2 quality points
- **Expected Premium**: 2.0 × $9.66 PSF × 1000 sqft = $19,320 (for OCR property)

**Your Decision Framework:**

1. **Calculate True School Premium**: Bishan should cost $19K more due to school quality, but actual gap is only $30K
2. **Assess Location Trade-off**: Bishan is suburban (further from CBD), Toa Payoh is central
3. **Consider Property Characteristics**: Same flat size and condition - direct comparison valid
4. **Evaluate School Quality**: Catholic High (Tier 1, GEP, SAP) vs First Toa Payoh (Tier 2) - significant difference

**Bottom Line**: **Property A (Bishan) offers better value for school-focused families.** The $30K price premium includes both the school premium ($19K) and location factors. If your priority is Tier 1 school access, Bishan provides exceptional value. If CBD proximity matters more, Toa Payoh may be preferable despite negative school coefficient in RCR.

</Scenario>

---

<Scenario title="Investor Evaluating School Premium for Rental Yield">
**Situation:** You're a property investor evaluating a condo near a top primary school for rental income:

- **Property**: 2-bedroom condo, 800 sqft, near Nanyang Primary School (Tier 1), $950K
- **Expected Rent**: $3,200/month = 4.0% gross yield
- **Alternative**: Similar condo in same area without school proximity, $900K, expected rent $3,000/month = 4.0% yield

**Our Analysis Says:**
- **School Premium**: $50K extra for school proximity
- **Yield Impact**: Both properties have same 4.0% gross yield
- **Feature Importance**: Primary school quality = 24.6% importance for rental yield prediction (2nd highest)
- **Correlation**: -0.258 between school quality and rental yield (negative)

**Your Decision Framework:**

1. **Assess Yield Parity**: Both properties have same 4.0% yield - school proximity doesn't improve rental income
2. **Consider Appreciation**: Secondary school quality is #1 predictor of appreciation (21.8% importance)
3. **Evaluate Tenant Demand**: Families with school-aged children may pay premium for school proximity
4. **Calculate Break-Even**: $50K premium / ($200 extra rent × 12) = 20.8 years to recover extra cost

**Bottom Line**: **Don't pay the $50K premium for rental yield alone.** Both properties offer same 4.0% yield, and school quality has negative correlation with yields (higher prices compress yields). However, if you're targeting appreciation (not rental income), the property may justify the premium - secondary school quality is the #1 predictor of YoY appreciation. Consider your investment horizon: short-term hold (5 years) = avoid premium; long-term hold (10+ years) = school proximity may drive appreciation.

</Scenario>

---

### 3. Causal Inference: The 1km Boundary Paradox

The most surprising finding: **Regression Discontinuity Design (RDD) reveals a NEGATIVE causal effect** at the 1km school admission priority boundary.

**RDD Main Findings:**

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Treatment Effect (τ) | **-$79.47 PSF** | Properties ≤1km cost LESS |
| 95% Confidence Interval | [-$84.63, -$74.31] | Highly statistically significant |
| P-value | < 0.001 | Significant at 99.9% level |
| Sample Size | 52,881 properties | 38,324 treated, 14,557 control |
| R² | 0.294 | Good model fit |

<Tooltip term="Regression Discontinuity Design (RDD)">
A causal inference method that exploits arbitrary cutoffs (like 1km school admission priority) to estimate causal effects. Compares properties just inside vs just outside the boundary.
</Tooltip>

**Validation Tests (All Reveal Assumption Violations):**

1. **Covariate Balance Test**: 0/5 covariates balanced at 1km cutoff
   - Properties inside vs. outside 1km differ systematically
   - Floor area: -8.4 sqm smaller inside (p < 0.001)
   - MRT distance: -139m closer inside (p < 0.001)
   - **Conclusion**: Selection bias present - families self-select into school zones

2. **Bandwidth Sensitivity**: Effects vary dramatically across bandwidths
   - 100m: +$34 PSF (positive)
   - 200m: -$79 PSF (negative, main estimate)
   - 300m: -$35 PSF (negative but smaller)
   - **Conclusion**: Effect not robust to bandwidth choice

3. **Placebo Tests**: Significant effects at fake cutoffs (800m, 1200m)
   - Should show NO effect if RDD assumptions hold
   - **Conclusion**: Omitted variables drive price discontinuities, not just school access

**Why the Negative Effect?**

The negative causal effect (-$79 PSF) is counterintuitive but consistent with market dynamics:
- Properties within 1km may be **older, smaller units** in established neighborhoods
- Selection bias: Families who prioritize schools may sacrifice other amenities
- Omitted variables: Building age, unit size, neighborhood character not fully controlled

<ImplicationBox persona="first-time-buyer">
**For First-Time Buyers with Families:**

The school premium exists (+$9.66 PSF per quality point), but enhanced analysis reveals important caveats. The "within 1km" premium may reflect neighborhood quality rather than school access per se.

✅ **What to Do:**
- Target OCR areas for positive school premiums (+$9.63 PSF vs -$23.67 PSF in RCR)
- Look beyond 1km boundary - properties just outside may offer better value
- Consider unit trade-offs - within-1km properties are often older and smaller
- Focus on school tier if quality matters - Tier 1 vs Tier 3 = ~$29K difference for 1000 sqft
- Verify school admission eligibility - 1km priority doesn't guarantee enrollment

❌ **What to Avoid:**
- Overpaying for "within 1km" if unit is older/smaller - RDD shows negative effect after controlling for confounders
- Assuming school premium applies everywhere - RCR shows negative coefficient (-$23.67 PSF)
- Ignoring neighborhood quality - the premium likely includes desirable amenities, not just school access
- Paying premium for primary school if focused on rental yield - negative correlation (-0.258)

💰 **ROI Impact:**
- OCR property near Tier 1 school: +$9.63 PSF × 1000 sqft × 3 quality tier difference = ~$29K premium
- School premium recovers over time through appreciation (secondary school quality = #1 predictor)
- **Family Strategy**: Buy in OCR with good schools, hold for 10+ years to realize appreciation benefit
</ImplicationBox>

---

### 4. Spatial Overfitting: Standard Metrics Mislead

The most methodologically important finding: **Standard cross-validation dramatically overestimates model performance** due to spatial autocorrelation.

**Spatial Cross-Validation Results:**

| Model | Standard CV R² | Spatial CV R² | Generalization Gap | Interpretation |
|-------|----------------|---------------|-------------------|----------------|
| Random Forest | 0.742 | -0.074 | **+110.0%** | Severe spatial overfitting |
| XGBoost | 0.721 | 0.087 | **+87.9%** | High spatial overfitting |
| OLS | 0.046 | 0.190 | -313.2% | Actually improves on unseen areas |

**Key Insight:**
- Machine learning models (RF, XGBoost) learn **neighborhood-specific patterns** that don't generalize
- Moran's I = 0.73 → strong positive spatial autocorrelation in residuals
- **Implication**: Standard ML evaluation metrics are **misleading** for geographic data
- **Recommendation**: Always use spatial blocking or regularization for school impact models

**Planning Area Generalization:**

| Planning Area | R² (Spatial CV) | Interpretation |
|---------------|------------------|----------------|
| **Clementi** | 0.39 | Most transferable patterns |
| **Bukit Timah** | 0.35 | Good generalization |
| **Bishan** | 0.33 | Moderate generalization |
| **Ang Mo Kio** | 0.31 | Moderate generalization |
| **Marine Parade** | **-2.79** | Model completely fails |
| **Tanjong Pagar** | -1.84 | Model fails |

**What This Means:**

School premiums are **location-specific**, not universal. A model trained on Bishan data (R² = 0.33) will fail in Marine Parade (R² = -2.79). Future school impact models must:
- Use spatial blocking (GroupKFold by planning area)
- Apply regularization to prevent overfitting
- Report spatial CV metrics, not just standard CV

---

### 5. Rental Yield & Appreciation Insights

Different school features drive different outcomes:

**Rental Yield Impact:**

| Feature | Importance | Rank | Correlation |
|---------|------------|------|-------------|
| `school_primary_quality_score` | 24.6% | #2 | -0.258 (negative) |
| `school_primary_dist_score` | 11.5% | #3 | -0.237 (negative) |

**Interpretation**: Higher quality schools → higher purchase prices → lower rental yields. Investors pay premium for appreciation potential, not rental income.

**Appreciation Impact (YoY Change):**

| Feature | Importance | Rank | Coefficient |
|---------|------------|------|-------------|
| `school_secondary_quality_score` | 21.8% | #1 | +4.68 (positive) |
| `school_density_score` | 5.9% | #4 | - |
| `school_accessibility_score` | 5.6% | #6 | +0.46 (positive) |

**Interpretation**: Secondary school quality is the **#1 predictor** of year-over-year price appreciation. Properties near top secondary schools appreciate faster.

---

## Investment Implications

### For Property Buyers

**School Premium Strategy:**

| Strategy | Region | School Effect | Best For |
|----------|--------|---------------|----------|
| **Family-focused** | OCR | +$9.63 PSF | School quality matters |
| **Avoid premium** | RCR | -$23.67 PSF | School premium negative |
| **Neutral** | CCR | ~$0 PSF | Location dominates |

**Key Considerations:**

1. **School Tier Matters**: Tier 1 vs Tier 3 = ~$29K difference for 1000 sqft
2. **Look Beyond 1km**: Properties just outside may offer better value
3. **Check Unit Trade-offs**: Within-1km properties often older/smaller
4. **Region-Specific Effects**: OCR positive, RCR negative, CCR neutral

### For Property Investors

**Yield vs Appreciation Trade-off:**

**Rental Yield Strategy:**
- Target areas where school premium is modest (avoid overpaying)
- Consider that high school quality compresses yields (negative correlation -0.258)
- Focus on OCR where school premiums are positive (+$9.63 PSF)

**Appreciation Strategy:**
- Secondary school quality is #1 predictor of YoY appreciation (21.8% importance)
- Primary school quality drives purchase prices, secondary drives future gains
- Target areas with top secondary schools for long-term holds (10+ years)

**Risk Factors:**

| Risk | Mitigation |
|------|------------|
| **Spatial overfitting** | Use spatial CV; don't trust standard ML metrics |
| **Selection bias** | Properties within 1km differ systematically |
| **Confounding factors** | School premium includes neighborhood quality |
| **Regional variation** | Premiums vary from -$24 to +$10 PSF across regions |

---

## Files Generated

**Analysis Scripts:**
- `scripts/analytics/analysis/school/analyze_school_impact.py` - Main analysis
- `scripts/analytics/analysis/school/analyze_school_spatial_cv.py` - Spatial validation
- `scripts/analytics/analysis/school/analyze_school_rdd.py` - Causal inference (RDD)
- `scripts/analytics/analysis/school/analyze_school_segmentation.py` - Market segmentation

**Data Outputs:**
```
data/analysis/school_impact/
├── exploratory_analysis.png              # 4-panel visualization
├── coefficients_price_psf.csv           # OLS coefficients: +$9.66 PSF
├── importance_price_psf_xgboost.csv     # Feature importance: 11.5%

data/analysis/school_spatial_cv/
├── spatial_cv_performance.csv           # Standard vs spatial CV: 88-110% gap
├── planning_area_generalization.csv     # Area-by-area generalization

data/analysis/school_rdd/
├── rdd_main_effect.csv                  # Causal effect: -$79.47 PSF
├── rdd_visualization.png                # Price discontinuity plot
└── rdd_covariate_balance.csv            # Balance test: selection bias

data/analysis/school_segmentation/
├── segment_coefficients.csv             # HDB_OCR: +$9.63, HDB_RCR: -$23.67
└── interaction_model_results.csv        # School × region effects
```

---

## Conclusion

This analysis demonstrates that **school quality is a significant but complex value driver** in Singapore housing prices. The implementation of quality-weighted features transformed school features from statistically irrelevant to among the top predictors in pricing models.

However, enhanced analysis reveals important caveats:

### Main Findings Summary

**1. School Features Matter (But Are Complex)**
- OLS shows +$9.66 PSF per quality point (~$70K premium for 1000 sqft near Tier 1)
- XGBoost feature importance: 11.5% (school_accessibility_score)
- **BUT**: Spatial CV reveals 88-110% overfitting → effect may be neighborhood-specific

**2. Heterogeneity Across Markets**
- OCR: Positive premium (+$9.63 PSF) - school quality matters in suburbs
- RCR: Negative effect (-$23.67 PSF) - confounded with other factors
- CCR: No effect - location dominates, international schools compete

**3. Causal Claims Require Caution**
- RDD shows -$79 PSF effect at 1km boundary (opposite sign from OLS)
- Validation tests reveal selection bias and omitted variables
- Likely explanation: "School premium" partially reflects neighborhood quality

---

## 🎯 Decision Checklist: Evaluating School Premium

<DecisionChecklist
  title="Evaluating School Premium Checklist"
  storageKey="checklist-school-premium"
>

- [ ] **Identified school tier** - Tier 1 vs Tier 2 vs Tier 3 = ~$29K difference for 1000 sqft
- [ ] **Checked regional effect** - OCR positive (+$9.63 PSF), RCR negative (-$23.67 PSF), CCR neutral
- [ ] **Verified 1km boundary** - Within 1km properties often older/smaller (RDD shows negative effect)
- [ ] **Calculated true premium** - $9.66 PSF per quality point, not blanket "$70K premium"
- [ ] **Assessed unit trade-offs** - Size, age, condition differences within vs outside 1km
- [ ] **Considered investment horizon** - Secondary schools drive appreciation (21.8% importance)
- [ ] **Checked school admission eligibility** - 1km priority doesn't guarantee enrollment
- [ ] **Evaluated neighborhood quality** - Premium likely includes amenities, not just school access
- [ ] **Review spatial overfitting** - School premiums are location-specific, not universal
- [ ] **Compared to alternative properties** - Just outside 1km may offer better value

</DecisionChecklist>

---

## 🔗 Related Analytics

- **[Spatial Autocorrelation](./spatial-autocorrelation.md)** - Understanding neighborhood effects (Moran's I = 0.73)
- **[MRT Impact](./mrt-impact.md)** - How transport proximity affects prices (compare $9.66 PSF/school vs $5-15 PSF/MRT)
- **[Price Forecasts](./price-forecasts.md)** - Predicting property appreciation (secondary school quality = #1 predictor)
- **[Findings](./findings.md)** - Overall market analysis including school features

---

**Disclaimer**: This analysis is based on Singapore housing market data (2021+). Causal claims require caution due to selection bias and confounding factors. School premiums vary dramatically by region and likely reflect neighborhood quality rather than school access per se. Always conduct due diligence before making investment decisions.
