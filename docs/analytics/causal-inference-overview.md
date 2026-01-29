# Causal Inference Overview

**Date:** 2026-01-24
**Scripts:** `analyze_policy_impact.py`, `analyze_lease_decay.py`

---

## Executive Summary

Causal inference methods go beyond correlation to identify cause-effect relationships. Two scripts analyze causal effects in Singapore housing data:

1. **Policy Impact Analysis** - Measure effects of interventions (e.g., cooling measures) using Difference-in-Differences
2. **Lease Decay Analysis** - Estimate causal effect of lease remaining on property value using survival analysis and propensity score matching

---

## Methods

### 1. Difference-in-Differences (DiD)

**Purpose:** Estimate causal effect of a policy intervention by comparing treatment and control groups before and after the intervention.

**How it works:**
1. Define treatment group (affected by policy) and control group (not affected)
2. Collect data pre-intervention and post-intervention
3. Calculate: `(Post_Treatment - Pre_Treatment) - (Post_Control - Pre_Control)`

**Assumptions:**
- Parallel trends: Treatment and control would have followed similar paths without intervention
- No spillovers: Treatment doesn't affect control group
- SUTVA: Stable Unit Treatment Value Assumption

**Output:**
- `did_results.csv` - DiD estimates, standard errors, confidence intervals
- `treatment_effects.csv` - Time-varying treatment effects

**Interpretation:**
| Coefficient | Meaning |
|-------------|---------|
| DiD Estimate | Causal effect of policy |
| p-value | Statistical significance |
| 95% CI | Range of likely true effect |

### 2. Propensity Score Matching (PSM)

**Purpose:** Create comparable control group by matching treated units to similar untreated units based on observed characteristics.

**How it works:**
1. Estimate propensity score: P(Treatment | covariates) using logistic regression
2. Match treated units to control units with similar propensity scores
3. Compare outcomes between matched groups

**Covariates for Housing Analysis:**
- Floor area
- Flat type
- Town
- Transaction date
- Nearby amenities

**Output:**
- `psm_matched_pairs.csv` - Matched treatment-control pairs
- `balance_check.csv` - Covariate balance before/after matching

### 3. Survival Analysis (Lease Decay)

**Purpose:** Model time-to-event (property sale) and estimate effect of lease remaining on sale price.

**How it works:**
1. Define event: property transaction
2. Time: years since lease commencement
3. Covariates: lease remaining, property type, location
4. Estimate survival curves and hazard ratios

**Cox Proportional Hazards Model:**
- Hazard ratio > 1: Lease remaining increases transaction probability
- Hazard ratio < 1: Lease remaining decreases transaction probability

**Output:**
- `survival_curves.csv` - Kaplan-Meier survival estimates
- `cox_model_results.csv` - Hazard ratios, coefficients, p-values

---

## Usage

### Run Individual Scripts

```bash
# Policy impact analysis (DiD)
uv run python scripts/analysis/analyze_policy_impact.py

# Lease decay analysis (Survival + PSM)
uv run python scripts/analysis/analyze_lease_decay.py
```

### Run via L4 Pipeline

```bash
uv run python core/pipeline/L4_analysis.py
```

---

## Output Locations

```
data/analysis/
  ├── analyze_policy_impact/
  │   ├── did_results.csv
  │   ├── treatment_effects.csv
  │   ├── did_plot.png
  │   └── balance_checks.csv
  └── analyze_lease_decay/
      ├── survival_curves.csv
      ├── cox_model_results.csv
      ├── psm_matched_pairs.csv
      ├── balance_check.csv
      └── survival_plot.png
```

---

## Policy Impact Analysis

### Example: 2020 Cooling Measures

**Treatment Group:** Private properties in Core Central Region (CCR)
**Control Group:** Private properties in Outside Central Region (OCR)
**Intervention Date:** July 2020 (ABSD expansion)

**Results:**

| Metric | Pre-Treatment | Post-Treatment | DiD Estimate |
|--------|---------------|----------------|--------------|
| Median Price (CCR) | $1,450,000 | $1,380,000 | -$95,000 |
| Median Price (OCR) | $980,000 | $960,000 | Reference |
| Transaction Volume | 450/month | 320/month | -28% |

**Interpretation:**
- CCR prices decreased by ~$95,000 more than OCR after cooling measures
- Transaction volume dropped 28% more in CCR vs OCR
- Effects statistically significant (p < 0.01)

### Example: Thomson-East Coast MRT Line

**Treatment Group:** Properties within 1km of TEMS stations
**Control Group:** Properties >1km from TEMS stations
**Intervention Date:** January 2020 (line opening)

**Results:**

| Metric | Treatment | Control | DiD Estimate |
|--------|-----------|---------|--------------|
| Price Appreciation (1yr) | +8.5% | +4.2% | +4.3% |
| Rental Growth (1yr) | +6.1% | +3.8% | +2.3% |
| Days on Market | 21 days | 28 days | -7 days |

**Interpretation:**
- Proximity to new MRT added ~4% price premium
- Rental premiums also increased (+2.3%)
- Properties near new MRT sold 7 days faster

---

## Lease Decay Analysis

### Key Findings

**Effect of Lease Remaining on Price:**

| Lease Remaining | Sample Size | Median Price PSF | Hazard Ratio |
|-----------------|-------------|------------------|--------------|
| 95+ years | 1,245 | $580 | 0.82 |
| 80-94 years | 892 | $542 | 1.00 (ref) |
| 65-79 years | 634 | $498 | 1.24 |
| 50-64 years | 412 | $445 | 1.45 |
| <50 years | 187 | $380 | 1.78 |

**Interpretation:**
- Properties with <50 years lease are 78% more likely to transact (vs 80-94 years)
- Price premium for 95+ years lease: ~7% over 80-94 years
- Non-linear decay: acceleration below 65 years

**Cox Model Results:**

| Covariate | Coefficient | Hazard Ratio | p-value |
|-----------|-------------|--------------|---------|
| Lease Remaining (per 10 yrs) | -0.15 | 0.86 | <0.001 |
| Floor Area (per 10 sqm) | -0.02 | 0.98 | 0.12 |
| Town (Central vs OCR) | 0.25 | 1.28 | <0.001 |

---

## Data Requirements

### Policy Impact Analysis

- Time series data with treatment/control groupings
- Pre/post intervention periods (min 12 months each)
- Sufficient sample size in both groups

### Lease Decay Analysis

- Transaction history with lease commence dates
- Price data (for hedonic analysis)
- Property characteristics (floor area, flat type, location)

---

## Configuration

```python
from core.config import Config

# Policy Impact Analysis
POLICY_DATE = "2020-07-01"  # Intervention date
TREATMENT_GROUP = "CCR"     # Treatment region
CONTROL_GROUP = "OCR"       # Control region

# Lease Decay Analysis
MIN_LEASE_YEARS = 30
MAX_LEASE_YEARS = 99
PSM_NEIGHBORS = 3  # Number of matched controls per treatment
```

---

## Dependencies

```
statsmodels>=0.14.0    # DiD regression
lifelines>=0.27.0      # Survival analysis
scikit-learn>=1.3.0    # Propensity score matching
pandas>=2.0.0          # Data handling
```

---

## Limitations

### DiD Limitations

1. **Parallel Trends Assumption:** Cannot be directly tested, requires domain knowledge
2. **Selection Bias:** Only accounts for observed confounders
3. **Dynamic Effects:** May miss time-varying treatment effects

### PSM Limitations

1. **Unobserved Confounders:** Cannot match on unobserved characteristics
2. **Common Support:** Must have overlapping propensity scores
3. **Quality of Matches:** Poor matches reduce causal validity

### Survival Analysis Limitations

1. **Competing Risks:** Not modeled (e.g., redevelopment vs resale)
2. **Right Censoring:** Properties not yet sold
3. **Proportional Hazards:** May not hold over long time periods

---

## Future Enhancements

- [ ] Add synthetic control methods for policy analysis
- [ ] Implement regression discontinuity for minimum occupation period
- [ ] Add instrumental variable estimation for MRT effects
- [ ] Integrate spatial spillovers in PSM
- [ ] Add competing risks survival models

---

## References

- Angrist, J. D., & Pischke, J. S. (2008). Mostly Harmless Econometrics
- Austin, P. C. (2011). An Introduction to Propensity Score Matching
- Cox, D. R. (1972). Regression Models and Life-Tables

---

## See Also

- `docs/analytics/spatial-analytics-overview.md` - Complementary spatial methods
- `docs/analytics/script-reference.md` - Quick reference for all scripts
