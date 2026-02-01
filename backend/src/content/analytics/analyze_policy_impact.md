# Policy Impact Analysis Script

**Script:** `scripts/analysis/analyze_policy_impact.py`
**Purpose:** Estimate causal effects of policy interventions using Difference-in-Differences (DiD) analysis

---

## Description

This script measures the causal effect of policy interventions on housing market outcomes. It uses Difference-in-Differences (DiD) methodology to compare treatment and control groups before and after a policy change.

---

## Usage

```bash
# Run with default settings (2020 cooling measures)
uv run python scripts/analysis/analyze_policy_impact.py

# Run with custom policy
uv run python scripts/analysis/analyze_policy_impact.py \
    --policy-date 2020-07-01 \
    --treatment "CCR" \
    --control "OCR" \
    --variable resale_price

# Run for MRT line opening
uv run python scripts/analysis/analyze_policy_impact.py \
    --policy-date 2020-01-31 \
    --treatment "Within 1km of TEMS" \
    --control "Beyond 1km from TEMS" \
    --variable price_psf
```

### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--policy-date` | str | `2020-07-01` | Intervention date (YYYY-MM-DD) |
| `--treatment` | str | `CCR` | Treatment group identifier |
| `--control` | str | `OCR` | Control group identifier |
| `--variable` | str | `resale_price` | Outcome variable |
| `--pre-periods` | int | 12 | Months pre-intervention |
| `--post-periods` | int | 24 | Months post-intervention |

---

## Output

### Files Created

| File | Description |
|------|-------------|
| `data/analysis/analyze_policy_impact/did_results.csv` | DiD estimates with statistics |
| `data/analysis/analyze_policy_impact/treatment_effects.csv` | Time-varying treatment effects |
| `data/analysis/analyze_policy_impact/did_plot.png` | DiD visualization |
| `data/analysis/analyze_policy_impact/trend_comparison.png` | Pre/post trend plot |

### DiD Results Schema

```csv
variable,treatment_group,control_group,did_estimate,std_error,t_stat,p_value,ci_lower,ci_upper,significance
resale_price,CCR,OCR,-95000,12500,-7.6,<0.001,-119500,-70500,***
```

### Treatment Effects Schema

```csv
period,month,group,mean_value,did_effect,ci_lower,ci_upper
pre,-12,Treatment,1450000,0,,,
pre,-11,Treatment,1465000,0,,,
...
post,0,Treatment,1380000,-95000,-119500,-70500
post,1,Treatment,1395000,-92000,-116000,-68000
```

---

## Methodology

### Difference-in-Differences

```
DiD = (Y_treatment,post - Y_treatment,pre) - (Y_control,post - Y_control,pre)
```

### Regression Specification

```
Y_it = α + β1 * Treatment_i + β2 * Post_t + β3 * (Treatment_i × Post_t) + ε_it
```

Where:
- β3 = DiD estimate (treatment effect)

### Statistical Testing

- **t-test:** Tests if DiD estimate is significantly different from zero
- **Permutation test:** Robustness check by shuffling treatment assignment
- **Parallel trends test:** Pre-treatment trends should be parallel

---

## Built-in Policies

### 1. 2020 Cooling Measures (ABSD Expansion)

```bash
uv run python scripts/analysis/analyze_policy_impact.py \
    --policy-date 2020-07-01 \
    --treatment CCR \
    --control OCR
```

**Hypothesis:** ABSD expansion reduced CCR prices relative to OCR.

### 2. 2020 Cooling Measures (All Private)

```bash
uv run python scripts/analysis/analyze_policy_impact.py \
    --policy-date 2020-07-01 \
    --treatment Private \
    --control HDB
```

### 3. Thomson-East Coast MRT Line

```bash
uv run python scripts/analysis/analyze_policy_impact.py \
    --policy-date 2020-01-31 \
    --treatment "Within 1km TEMS" \
    --control "Beyond 1km TEMS"
```

---

## Example Results

### Sample Output (2020 Cooling Measures)

```
================================================================================
POLICY IMPACT ANALYSIS: 2020 Cooling Measures
================================================================================

Policy Date: 2020-07-01
Treatment: Core Central Region (CCR)
Control: Outside Central Region (OCR)
Variable: resale_price
Period: 2019-07-01 to 2022-07-01

--------------------------------------------------------------------------------
DESCRIPTIVE STATISTICS
--------------------------------------------------------------------------------
                    Pre-Period     Post-Period    Change
Treatment (CCR):    $1,450,000     $1,380,000     -$70,000
Control (OCR):      $980,000       $960,000       -$20,000

--------------------------------------------------------------------------------
DIFFERENCE-IN-DIFFERENCES RESULTS
--------------------------------------------------------------------------------
DiD Estimate:       -$95,000
Standard Error:     $12,500
95% CI:             [-$119,500, -$70,500]
t-statistic:        -7.60
P-value:            <0.001
Significance:       ***

Robustness Checks:
  Permutation Test: p = 0.002 (1000 permutations)
  Parallel Trends: F-statistic = 0.45 (p = 0.87) ✓

--------------------------------------------------------------------------------
INTERPRETATION
--------------------------------------------------------------------------------
The 2020 ABSD expansion reduced CCR resale prices by approximately $95,000
relative to OCR, a statistically significant effect (p < 0.001).

As a percentage of pre-treatment price:
  Treatment Change: -4.8%
  Control Change:   -2.0%
  Relative Effect:  -2.8 percentage points

================================================================================
```

---

## Integration

### With L4 Pipeline

```json
{
  "script": "analyze_policy_impact",
  "status": "success",
  "key_findings": [
    "DiD estimate: -$95,000 (p < 0.001)",
    "CCR prices decreased 2.8% more than OCR",
    "Effect statistically significant",
    "Parallel trends assumption verified (p = 0.87)"
  ],
  "outputs": [
    "data/analysis/analyze_policy_impact/did_results.csv",
    "data/analysis/analyze_policy_impact/treatment_effects.csv"
  ],
  "duration_seconds": 18.2
}
```

### With Other Scripts

- **Uses:** `analyze_spatial_hotspots.py` (define treatment areas)
- **Uses:** `analyze_h3_clusters.py` (cluster-based treatment groups)
- **Complements:** `analyze_lease_decay.py` (causal effects)

---

## Configuration

```python
# In core/config.py
ANALYSIS_POLICY_DEFAULT_DATE = "2020-07-01"
ANALYSIS_POLICY_TREATMENT = "CCR"
ANALYSIS_POLICY_CONTROL = "OCR"
ANALYSIS_POLICY_VARIABLE = "resale_price"
```

---

## Dependencies

```
statsmodels>=0.14.0    # Regression and DiD
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
```

---

## Troubleshooting

### Parallel Trends Violation

If pre-treatment trends are not parallel:

1. Add control variables (property characteristics)
2. Use propensity score matching
3. Consider different control group

```bash
uv run python scripts/analysis/analyze_policy_impact.py \
    --control "Jurong East" \
    --add-covariates
```

### Small Sample Size

Increase post-period or use quarterly aggregation:

```bash
uv run python scripts/analysis/analyze_policy_impact.py \
    --post-periods 36 \
    --frequency Q
```

---

## See Also

- `docs/analytics/causal-inference-overview.md` - Method background
- `scripts/analysis/analyze_lease_decay.py` - Survival analysis
- `docs/guides/data-reference.md` - Variable definitions
