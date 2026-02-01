# Lease Decay Analysis Script

**Script:** `scripts/analysis/analyze_lease_decay.py`
**Purpose:** Estimate causal effect of lease remaining on property value using survival analysis and propensity score matching

---

## Description

This script analyzes the relationship between lease remaining and property transactions. It uses two complementary methods:

1. **Survival Analysis:** Model time-to-sale and estimate hazard ratios
2. **Propensity Score Matching:** Match properties with different lease remaining for causal comparison

---

## Usage

```bash
# Run with default settings
uv run python scripts/analysis/analyze_lease_decay.py

# Run with custom parameters
uv run python scripts/analysis/analyze_lease_decay.py \
    --lease-groups "95plus,80-94,65-79,50-64,below50" \
    --match-ratio 3

# Run Cox model only
uv run python scripts/analysis/analyze_lease_decay.py --method cox
```

### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--method` | str | `both` | Analysis method: `survival`, `psm`, or `both` |
| `--lease-groups` | str | `95plus,80-94,65-79,50-64,below50` | Lease groups to compare |
| `--match-ratio` | int | 3 | Controls per treated unit |
| `--min-lease` | int | 30 | Minimum lease years |
| `--max-lease` | int | 99 | Maximum lease years |

---

## Output

### Files Created

| File | Description |
|------|-------------|
| `data/analysis/analyze_lease_decay/survival_curves.csv` | Kaplan-Meier survival estimates |
| `data/analysis/analyze_lease_decay/cox_model_results.csv` | Cox PH model coefficients |
| `data/analysis/analyze_lease_decay/psm_matched_pairs.csv` | Matched treatment-control pairs |
| `data/analysis/analyze_lease_decay/balance_check.csv` | Covariate balance statistics |
| `data/analysis/analyze_lease_decay/survival_plot.png` | Survival curves visualization |
| `data/analysis/analyze_lease_decay/lease_decay_plot.png` | Price vs lease remaining |

### Cox Model Results Schema

```csv
covariate,coefficient,hazard_ratio,std_error,z_stat,p_value,ci_lower,ci_upper
lease_remaining,-0.15,0.86,0.02,-7.5,<0.001,-0.19,-0.11
floor_area,0.02,1.02,0.01,2.0,0.046,0.001,0.04
town_Central,0.25,1.28,0.05,5.0,<0.001,0.15,0.35
```

### Survival Curves Schema

```csv
lease_group,time_years,survival_probability,lower_ci,upper_ci,n_at_risk
95plus,1,0.92,0.91,0.93,1000
95plus,5,0.65,0.63,0.67,800
...
below50,1,0.78,0.75,0.81,150
```

---

## Methodology

### Survival Analysis (Cox PH Model)

The Cox proportional hazards model:

```
h(t) = h0(t) * exp(β1 * lease_remaining + β2 * covariates)
```

Where:
- h(t) = hazard rate at time t
- h0(t) = baseline hazard
- β = coefficients
- Hazard ratio > 1: increases transaction probability
- Hazard ratio < 1: decreases transaction probability

### Propensity Score Matching

1. **Estimate Propensity Score:** Logistic regression of treatment (lease group) on covariates
2. **Match:** Nearest-neighbor matching with caliper
3. **Assess Balance:** Compare covariate distributions before/after matching
4. **Estimate Effect:** Compare outcomes between matched groups

### Covariates for Matching

- Floor area
- Flat type
- Town
- Transaction year
- Floor level

---

## Example Results

### Sample Output

```
================================================================================
LEASE DECAY ANALYSIS
================================================================================

Analysis Period: 2015-2025
Total Properties: 3,847
Lease Groups: 95plus, 80-94, 65-79, 50-64, below50

--------------------------------------------------------------------------------
SURVIVAL ANALYSIS (Cox PH Model)
--------------------------------------------------------------------------------
Dependent Variable: Time to transaction
Censoring: Right-censored (still held)

Variables:
  - lease_remaining (per 10 years)
  - floor_area_sqm
  - town (Central vs Non-Central)
  - flat_type

Cox Model Results:
  Lease Remaining:     β = -0.15, HR = 0.86, p < 0.001 ***
  Floor Area:          β = 0.02, HR = 1.02, p = 0.046 *
  Town (Central):      β = 0.25, HR = 1.28, p < 0.001 ***
  Flat Type (4-room):  β = -0.05, HR = 0.95, p = 0.12

Interpretation:
  - Each 10-year increase in lease remaining reduces transaction
    hazard by 14% (HR = 0.86)
  - Properties with 99-year lease are less likely to transact
    than properties with 60-year lease

--------------------------------------------------------------------------------
SURVIVAL PROBABILITIES BY LEASE GROUP
--------------------------------------------------------------------------------
                    1-Year    3-Year    5-Year    10-Year
95+ years lease:    92%       78%       65%       42%
80-94 years lease:  90%       75%       60%       38%
65-79 years lease:  85%       68%       52%       30%
50-64 years lease:  80%       60%       45%       24%
<50 years lease:    72%       50%       35%       15%

--------------------------------------------------------------------------------
PROPENSITY SCORE MATCHING
--------------------------------------------------------------------------------
Reference Group: 80-94 years lease
Matching Ratio: 3:1

Matched Pairs: 1,245
Balance Improvement:
                    Before Matching    After Matching
  Std Diff (Floor Area): 0.35              0.05
  Std Diff (Town):       0.28              0.03
  Std Diff (Flat Type):  0.22              0.04

Price Comparison (Matched Sample):
  95+ years:  $580 PSF (n=312)
  80-94 years: $542 PSF (reference)
  65-79 years: $498 PSF (-8.1%)
  50-64 years: $445 PSF (-17.9%)
  <50 years:   $380 PSF (-29.9%)

================================================================================
```

---

## Integration

### With L4 Pipeline

```json
{
  "script": "analyze_lease_decay",
  "status": "success",
  "key_findings": [
    "Cox HR = 0.86 per 10-year lease increase (p < 0.001)",
    "Properties with <50 years lease transact 78% more often",
    "PSM matched 1,245 property pairs",
    "Price premium for 95+ years lease: +7.0% over 80-94 years"
  ],
  "outputs": [
    "data/analysis/analyze_lease_decay/cox_model_results.csv",
    "data/analysis/analyze_lease_decay/survival_curves.csv",
    "data/analysis/analyze_lease_decay/psm_matched_pairs.csv"
  ],
  "duration_seconds": 31.5
}
```

### With Other Scripts

- **Complements:** `analyze_policy_impact.py` (causal effects)
- **Uses:** `analyze_feature_importance.py` (feature correlations)

---

## Configuration

```python
# In core/config.py
ANALYSIS_LEASE_DECAY_LEASE_GROUPS = ["95plus", "80-94", "65-79", "50-64", "below50"]
ANALYSIS_LEASE_DECAY_MATCH_RATIO = 3
ANALYSIS_LEASE_DECAY_MIN_LEASE = 30
ANALYSIS_LEASE_DECAY_MAX_LEASE = 99
```

---

## Dependencies

```
lifelines>=0.27.0      # Survival analysis
scikit-learn>=1.3.0    # Propensity score matching
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
statsmodels>=0.14.0
```

---

## Interpreting Results

### Hazard Ratios

| Hazard Ratio | Meaning |
|--------------|---------|
| HR = 1.0 | No effect |
| HR < 1.0 | Decreases transaction probability |
| HR > 1.0 | Increases transaction probability |

### Lease Decay Curve

The relationship between lease remaining and price is typically non-linear:

```
Price |
  $600 |       *
  $500 |    *     *
  $400 | *           *
  $300 |                 *
  $200 |___________________________
       30    50    70    90    99
            Lease Remaining (years)
```

---

## Troubleshooting

### Small Sample in Low Lease Groups

Increase min-lease threshold or aggregate groups:

```bash
uv run python scripts/analysis/analyze_lease_decay.py \
    --lease-groups "95plus,80-94,65-79,below65" \
    --min-lease 40
```

### Poor Match Quality

Increase match ratio or adjust caliper:

```bash
uv run python scripts/analysis/analyze_lease_decay.py \
    --match-ratio 5 \
    --caliper 0.1
```

---

## See Also

- `docs/analytics/causal-inference-overview.md` - Method background
- `scripts/analysis/analyze_policy_impact.py` - DiD analysis
- `scripts/analyze_feature_importance.py` - Feature correlations
