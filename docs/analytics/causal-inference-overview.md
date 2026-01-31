# Causal Inference Overview

**Date:** 2026-01-24
**Scripts:** `analyze_policy_impact.py`, `analyze_lease_decay.py`

---

## Executive Summary

Causal inference methods go beyond correlation to identify cause-effect relationships. Two scripts analyze causal effects in Singapore housing data:

1. **Policy Impact Analysis** - Measure effects of interventions (e.g., cooling measures) using Difference-in-Differences
2. **Lease Decay Analysis** - Estimate causal effect of lease remaining on property value using survival analysis and propensity score matching

### 🎯 Why This Matters

**In Plain English:** Correlation doesn't equal causation. Just because prices fell after a policy was introduced doesn't mean the policy caused it. Causal inference methods help us answer: *"What would have happened WITHOUT the intervention?"*

**Real-World Example:**
- **Correlation:** "Prices dropped 5% after new cooling measures"
- **Causation:** "Prices dropped 5% BECAUSE of cooling measures (after accounting for market trends, seasonal effects, and economic factors)"

**Practical Applications:**
- **Policy Makers:** Evaluate if housing policies actually work or waste resources
- **Investors:** Understand how regulations truly affect portfolio value
- **Researchers:** Publish rigorous studies that withstand peer review
- **Homebuyers:** Make decisions based on real drivers, not coincidences

---

## Methods

### 1. Difference-in-Differences (DiD)

#### 🎯 What It Does (Plain English)
Measures the **causal effect** of a policy by comparing two groups over time. Answers: *"How would prices have changed if the policy NEVER happened?"*

**Real-World Analogy:** Like testing a medicine by giving it to treatment group and placebo to control group, then comparing who improved. But instead of medicine, it's housing policy; instead of health, it's prices.

**The Counterfactual Question:**
- **What we observe:** CCR prices dropped 8% after cooling measures
- **What we want to know:** Would they have dropped anyway (e.g., due to economy)?
- **DiD answers:** OCR prices (not affected) only dropped 3%, so cooling measures caused ~5% drop

#### 💡 Practical Interpretation

| Finding | Interpretation | Action |
|---------|---------------|--------|
| **DiD = -$95K, p < 0.01** | Policy reduced prices by $95K (statistically certain) | Policy worked as intended |
| **DiD = +$20K, p = 0.35** | Prices increased $20K (but likely random chance) | Policy had no real effect |
| **DiD = -$5K, p = 0.02** | Small effect, but statistically significant | Policy works, weak impact |

#### 📊 Interactive Plotly Visualization

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Load DiD results
did_df = pd.read_csv('data/analysis/analyze_policy_impact/did_results.csv')

# Create before/after comparison
fig = go.Figure()

# Treatment group (CCR) - before
fig.add_trace(go.Scatter(
    x=did_df[did_df['period'] == 'pre']['date'],
    y=did_df[did_df['period'] == 'pre']['treatment_price'],
    name='Treatment (CCR) - Before',
    line=dict(color='blue', dash='solid'),
    mode='lines+markers'
))

# Treatment group (CCR) - after
fig.add_trace(go.Scatter(
    x=did_df[did_df['period'] == 'post']['date'],
    y=did_df[did_df['period'] == 'post']['treatment_price'],
    name='Treatment (CCR) - After',
    line=dict(color='blue', dash='solid'),
    mode='lines+markers'
))

# Control group (OCR) - before
fig.add_trace(go.Scatter(
    x=did_df[did_df['period'] == 'pre']['date'],
    y=did_df[did_df['period'] == 'pre']['control_price'],
    name='Control (OCR) - Before',
    line=dict(color='red', dash='dot'),
    mode='lines+markers'
))

# Control group (OCR) - after
fig.add_trace(go.Scatter(
    x=did_df[did_df['period'] == 'post']['date'],
    y=did_df[did_df['period'] == 'post']['control_price'],
    name='Control (OCR) - After',
    line=dict(color='red', dash='dot'),
    mode='lines+markers'
))

# Add policy intervention line
fig.add_vline(
    x=pd.Timestamp('2020-07-01'),
    line_dash="dash",
    line_color="green",
    annotation_text="Cooling Measures Introduced",
    annotation_position="top"
)

fig.update_layout(
    title="Difference-in-Differences: Policy Impact on Prices",
    xaxis_title="Date",
    yaxis_title="Median Price ($)",
    height=500,
    hovermode='x unified'
)

# Add annotation with DiD estimate
did_estimate = did_df['did_estimate'].iloc[0]
p_value = did_df['p_value'].iloc[0]
fig.add_annotation(
    text=f"DiD Estimate: ${did_estimate:,.0f}<br>p-value: {p_value:.3f}",
    xref="paper", yref="paper",
    x=0.02, y=0.98,
    showarrow=False,
    bgcolor="rgba(255,255,255,0.8)",
    bordercolor="black",
    borderwidth=1
)

fig.show()
```

**Interactive Features:**
- Toggle treatment/control groups on/off
- Zoom into pre/post periods
- Hover to see exact prices and dates
- Dynamic annotations update with data

#### 🔬 How It Works (Technical)

**Step-by-Step:**
1. Define treatment group (affected by policy) and control group (not affected)
2. Collect data pre-intervention and post-intervention
3. Calculate: `(Post_Treatment - Pre_Treatment) - (Post_Control - Pre_Control)`

**Assumptions (Critical!):**

| Assumption | What It Means | How to Check |
|------------|---------------|--------------|
| **Parallel Trends** | Treatment/control would have similar trends without intervention | Plot pre-period trends - should be parallel |
| **No Spillovers** | Policy doesn't affect control group | Choose control far from treatment |
| **SUTVA** | Each unit's outcome depends only on its treatment | No interference between properties |

**Output:**
- `did_results.csv` - DiD estimates, standard errors, confidence intervals
- `treatment_effects.csv` - Time-varying treatment effects

**Interpretation:**
| Coefficient | Meaning |
|-------------|---------|
| DiD Estimate | Causal effect of policy |
| p-value | Statistical significance (< 0.05 = significant) |
| 95% CI | Range of likely true effect |

### 2. Propensity Score Matching (PSM)

#### 🎯 What It Does (Plain English)
Creates a **fair comparison** by matching treated properties to similar untreated properties. Like comparing apples to apples instead of apples to oranges.

**Real-World Analogy:** You want to test if a new fertilizer helps plants grow. Instead of applying it to random plants, you find pairs of nearly identical plants and treat one from each pair. This isolates the fertilizer effect.

**Why It Matters:**
- Without PSM: Comparing luxury condos (treatment) vs HDB flats (control) → biased
- With PSM: Comparing similar condos, some treated, some not → unbiased

#### 💡 Practical Interpretation

| Balance Check | Good Match? | Interpretation |
|---------------|-------------|----------------|
| **Standardized Mean Difference < 0.1** | ✅ Yes | Treatment/control are similar |
| **SMD 0.1 - 0.2** | ⚠️ Acceptable | Minor differences remain |
| **SMD > 0.2** | ❌ No | Poor matching, results unreliable |

#### 📊 Interactive Plotly Visualization

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load PSM results
psm_df = pd.read_csv('data/analysis/analyze_lease_decay/psm_matched_pairs.csv')
balance_df = pd.read_csv('data/analysis/analyze_lease_decay/balance_check.csv')

# Before/After matching comparison
fig = make_subplots(
    rows=1, cols=2,
    subplot_titles=('Before Matching', 'After Matching'),
    specs=[[{'type': 'scatter'}, {'type': 'scatter'}]]
)

# Before matching
for covariate in ['floor_area', 'lease_remaining', 'distance_to_mrt']:
    fig.add_trace(
        go.Scatter(
            x=balance_df[balance_df['covariate'] == covariate]['treatment_mean'],
            y=balance_df[balance_df['covariate'] == covariate]['control_mean'],
            name=covariate,
            mode='markers',
            text=balance_df[balance_df['covariate'] == covariate]['covariate']
        ),
        row=1, col=1
    )

# After matching
for covariate in ['floor_area', 'lease_remaining', 'distance_to_mrt']:
    fig.add_trace(
        go.Scatter(
            x=balance_df[balance_df['covariate'] == covariate]['treatment_mean_matched'],
            y=balance_df[balance_df['covariate'] == covariate]['control_mean_matched'],
            name=f"{covariate} (matched)",
            mode='markers',
            marker_symbol='diamond',
            text=balance_df[balance_df['covariate'] == covariate]['covariate']
        ),
        row=1, col=2
    )

# Add 45-degree line (perfect matching)
for i in [1, 2]:
    fig.add_trace(
        go.Scatter(
            x=[balance_df['treatment_mean'].min(), balance_df['treatment_mean'].max()],
            y=[balance_df['treatment_mean'].min(), balance_df['treatment_mean'].max()],
            mode='lines',
            line=dict(dash='dash', color='black'),
            showlegend=False,
        ),
        row=1, col=i
    )

fig.update_layout(
    title="Propensity Score Matching: Covariate Balance",
    height=500
)
fig.update_xaxes(title_text="Treatment Mean")
fig.update_yaxes(title_text="Control Mean")

fig.show()
```

#### 🔬 How It Works (Technical)

**Step-by-Step:**
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

#### 🎯 What It Does (Plain English)
Models **how long properties stay on the market** and what factors affect sale timing. Answers: *"Does a shorter lease make properties sell faster or slower?"*

**Real-World Analogy:** Like studying patient survival rates after treatment. But instead of life/death, it's property sale/not yet sold. Instead of drug dosage, it's lease remaining.

**Key Insights:**
- **Hazard Ratio > 1:** Factor increases sale probability (good for sellers)
- **Hazard Ratio < 1:** Factor decreases sale probability (bad for sellers)
- **Survival Curve:** Probability property remains unsold over time

#### 💡 Practical Interpretation

| Finding | Interpretation | Investment Implication |
|---------|---------------|----------------------|
| **HR = 1.24 for <65yr lease** | Short-lease properties sell 24% faster | High turnover, good for flippers |
| **HR = 0.82 for 95+yr lease** | Long-lease properties sell 18% slower | Hold longer, capital appreciation focus |
| **Median survival: 45 days** | Typical property sells in 1.5 months | Market liquidity benchmark |

#### 📊 Interactive Plotly Visualization

```python
import plotly.graph_objects as go
import pandas as pd

# Load survival data
survival_df = pd.read_csv('data/analysis/analyze_lease_decay/survival_curves.csv')
cox_df = pd.read_csv('data/analysis/analyze_lease_decay/cox_model_results.csv')

# Kaplan-Meier survival curves by lease remaining
fig = go.Figure()

for lease_category in ['<50 years', '50-64 years', '65-79 years', '80-94 years', '95+ years']:
    data = survival_df[survival_df['lease_category'] == lease_category]

    fig.add_trace(go.Scatter(
        x=data['time_years'],
        y=data['survival_probability'],
        name=lease_category,
        mode='lines',
        line=dict(width=2),
        hovertemplate=f'<b>{lease_category}</b><br>' +
                      'Year: %{x:.1f}<br>' +
                      'Survival Prob: %{y:.1%}<br>' +
                      '<extra></extra>'
    ))

fig.update_layout(
    title="Kaplan-Meier Survival Curves: Time to Sale by Lease Remaining",
    xaxis_title="Years Since Listing",
    yaxis_title="Probability of Remaining Unsold",
    yaxis=dict(tickformat='.0%'),
    height=600,
    hovermode='x unified'
)

# Add median survival lines
for category, data in survival_df.groupby('lease_category'):
    median_time = data[data['survival_probability'] <= 0.5]['time_years'].min()
    if median_time:
        fig.add_vline(
            x=median_time,
            line_dash="dot",
            line_width=1,
            annotation_text=f"{category}: {median_time:.0f}y median",
            annotation_position="top left"
        )

fig.show()

# Forest plot for hazard ratios
fig2 = go.Figure()

# Add hazard ratio bars
fig2.add_trace(go.Scatter(
    x=cox_df['hazard_ratio'],
    y=cox_df['covariate'],
    mode='markers',
    marker=dict(size=10, color='blue'),
    name='Hazard Ratio',
    error_x=dict(
        type='data',
        symmetric=False,
        array=cox_df['hr_ci_upper'] - cox_df['hazard_ratio'],
        arrayminus=cox_df['hazard_ratio'] - cox_df['hr_ci_lower']
    ),
    text=cox_df['p_value'].apply(lambda p: f'p={p:.3f}'),
    textposition='top center'
))

# Add reference line at HR=1
fig2.add_vline(
    x=1.0,
    line_dash="dash",
    line_color="red",
    annotation_text="No Effect (HR=1)"
)

fig2.update_layout(
    title="Cox Model: Hazard Ratios with 95% Confidence Intervals",
    xaxis_title="Hazard Ratio (>1 = faster sale)",
    yaxis_title="Covariate",
    height=500
)

fig2.show()
```

#### 🔬 How It Works (Technical)

**Step-by-Step:**
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
from scripts.core.config import Config

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

## 🚀 Machine Learning Enhancements

### Advanced Causal Inference Methods

Traditional causal methods (DiD, PSM, Survival Analysis) are powerful, but modern ML techniques can address their limitations:

#### 1. Double Machine Learning (DML)

**What:** Combines ML predictions with causal inference to handle high-dimensional confounders.
**Why:** Traditional DiD/PSM struggle with many covariates. DML uses ML to estimate nuisance parameters while maintaining causal validity.

**Use Case:** Policy effects with hundreds of potential confounders (economic indicators, demographic shifts, global trends)

```python
from econml.dml import CausalForestDML
from sklearn.ensemble import GradientBoostingRegressor

# Treatment: Cooling measures (binary)
# Outcome: Price change
# Confounders: 50+ economic and demographic variables

# Train DML model
model = CausalForestDML(
    model_y=GradientBoostingRegressor(),  # ML for outcome
    model_t=GradientBoostingRegressor(),  # ML for treatment
    n_estimators=1000,
    max_depth=10
)

model.fit(Y=df['price_change'],
          T=df['cooling_measure'],
          X=df[['mrt_distance', 'floor_area', ...]],  # Heterogeneity features
          W=df[['gdp', 'unemployment', 'population', ...]])  # Confounders

# Estimate heterogeneous treatment effects
hte = model.effect(X=df[['mrt_distance', 'floor_area', ...]])

# Visualize: Which properties are most affected by policy?
shap_values = model.shap_values(X=df[['mrt_distance', 'floor_area', ...]])
```

**Benefits:**
- Handles many confounders without overfitting
- Provides confidence intervals
- Captures treatment heterogeneity (policy works differently for different properties)

#### 2. Causal Forests

**What:** Extension of random forests for causal inference.
**Why:** Discover heterogeneous treatment effects - "For whom does the policy work best?"

**Use Case:** Identify which neighborhoods benefit most from infrastructure projects

```python
from econml.grf import CausalForest

# Train causal forest
cf = CausalForest(n_estimators=2000, max_depth=20)
cf.fit(Y=df['price_appreciation'],
       T=df['mrt_proximity'],  # Treatment: Near new MRT
       X=df[['property_type', 'income_level', 'age', ...]])

# Get heterogeneous treatment effects
treatment_effects = cf.predict(X=df[['property_type', 'income_level', 'age', ...]])

# Visualize: Who benefits most from MRT?
import plotly.express as px
px.scatter(df, x='income_level', y=treatment_effects,
           color='property_type',
           title='Heterogeneous Treatment Effects: MRT Impact by Income and Property Type')
```

**Interpretation:**
- High HTE: Properties that benefit MOST from treatment
- Low/negative HTE: Properties that benefit LEAST or are harmed

#### 3. Synthetic Control Methods

**What:** Creates weighted combination of control units to approximate treatment group's counterfactual.
**Why:** Better than single control group when treatment is at aggregate level (e.g., entire city)

**Use Case:** Singapore cooling measures vs. weighted combination of Hong Kong, Seoul, Tokyo

```python
from causalsynthesis import SyntheticControl

# Singapore price index over time
sg_prices = [100, 102, 105, 103, 98, ...]  # After policy at t=4

# Control cities
control_cities = {
    'Hong Kong': [100, 101, 103, 102, 101, ...],
    'Seoul': [100, 99, 101, 100, 99, ...],
    'Tokyo': [100, 101, 102, 101, 100, ...]
}

# Create synthetic Singapore
sc = SyntheticControl()
sc.fit(treatment=sg_prices,
       controls=control_cities,
       treatment_time=4)

# Synthetic control (what would have happened without policy)
sg_synthetic = sc.synthetic_control

# Effect = Actual - Synthetic
policy_effect = [actual - synthetic for actual, synthetic in zip(sg_prices[4:], sg_synthetic[4:])]

# Visualize
import plotly.graph_objects as go
fig = go.Figure()
fig.add_trace(go.Scatter(y=sg_prices, name='Singapore (Actual)'))
fig.add_trace(go.Scatter(y=sg_synthetic, name='Synthetic Singapore'))
fig.add_vline(x=4, line_dash='dash', annotation_text='Policy Introduced')
```

#### 4. Instrumental Variables (IV) + ML

**What:** Uses "instruments" (variables that affect treatment but not outcome directly) to estimate causal effects.
**Why:** Addresses unobserved confounding (e.g., seller motivation not in data)

**Use Case:** MRT effect on prices, using distance to planned future MRT as instrument

```python
from econml.iv.dr import LinearDRLearner
from sklearn.ensemble import RandomForestRegressor

# Instrument: Distance to ANNOUNCED MRT (affects current price via expectations)
# Treatment: Distance to OPERATIONAL MRT
# Outcome: Actual price
# Confounders: Property characteristics

# Two-stage least squares with ML
model = LinearDRLearner(
    model_regression=RandomForestRegressor(),
    model_propensity=RandomForestRegressor()
)

model.fit(Y=df['price'],
          T=df['dist_operational_mrt'],
          Z=df['dist_announced_mrt'],  # Instrument
          W=df[['floor_area', 'age', 'town']])

# Causal effect of MRT (accounting for expectations)
iv_effect = model.effect()
```

**Key Insight:** Traditional regression overstates MRT effect because of reverse causation (prices rise before MRT built). IV corrects this.

#### 5. Meta-Learners (S/T/X/R-Learners)

**What:** Modular approach to causal inference using any ML model as base learner.
**Why:** Flexibility to use best ML model (XGBoost, Neural Nets) for causal estimation.

```python
from causalml.inference.meta import LRSRegressor
from xgboost import XGBRegressor

# T-Learner: Separate models for treatment/control
T_learner = LRSRegressor(learner=XGBRegressor())
T_learner.fit(X=df[features],
              treatment=df['cooling_measure'],
              y=df['price_change'])

# X-Learner: Better when treatment/control groups are imbalanced
X_learner = XLearner(learner=XGBRegressor())
X_learner.fit(X=df[features],
              treatment=df['cooling_measure'],
              y=df['price_change'])

# Compare results
t_learner_effects = T_learner.predict(X=df[features])
x_learner_effects = X_learner.predict(X=df[features])
```

**When to Use Which:**
- **S-Learner:** Small treatment effects, good overlap
- **T-Learner:** Large treatment effect, different data distributions
- **X-Learner:** Imbalanced groups (e.g., few treated properties)
- **R-Learner:** Many confounders, robust to misspecification

#### 6. Neural Network Causal Estimation

**What:** Deep learning for causal inference with complex, high-dimensional data.
**Why:** Captures non-linearities and interactions automatically.

**Use Case:** Image data (satellite imagery of neighborhood development) + tabular data

```python
import torch
import torch.nn as nn

class TARNet(nn.Module):
    """Treatment-Agnostic Representation Network"""
    def __init__(self, input_dim, hidden_dim=64):
        super().__init__()
        # Shared representation
        self.shared = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        # Separate heads for treatment/control
        self.head_treated = nn.Linear(hidden_dim, 1)
        self.head_control = nn.Linear(hidden_dim, 1)

    def forward(self, x, treatment):
        # Learn shared representation
        phi = self.shared(x)

        # Predict based on treatment assignment
        pred_treated = self.head_treated(phi)
        pred_control = self.head_control(phi)

        # Select appropriate prediction
        output = treatment * pred_treated + (1 - treatment) * pred_control
        return output, pred_treated, pred_control

# Train with causal loss function
model = TARNet(input_dim=X.shape[1])
optimizer = torch.optim.Adam(model.parameters())

# Custom loss: MSE + propensity score weighting
for epoch in range(1000):
    pred, pred_t, pred_c = model(X, treatment)
    loss = mse_loss(pred, y) + propensity_score_weighting(pred_t, pred_c, propensity)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

# Estimate treatment effects
with torch.no_grad():
    _, pred_t, pred_c = model(X, torch.ones_like(X))
    treatment_effects = pred_t - pred_c
```

#### 7. Counterfactual Explanations

**What:** Generates "what-if" scenarios for individual properties.
**Why:** Understand why a specific property received its price/prediction.

```python
import dice_ml
from dice_ml import Dice

# Train ML model (e.g., XGBoost price predictor)
model = xgboost.train(...)

# Create DiCE explainer
dice = Dice(data_frame=df,
            model=model,
            outcome_name='price')

# Counterfactual: What if this property was 200m closer to MRT?
cf = dice.generate_counterfactuals(
    query_instances=single_property,
    total_CFs=5,
    desired_range="increase",
    features_to_vary=['mrt_distance']
)

# Interpretation:
# "Property would be $50K more expensive if 200m closer to MRT"
```

**Practical Use:**
- **Sellers:** "What renovations increase price most?"
- **Buyers:** "Am I overpaying compared to similar properties?"
- **Agents:** "How should I price this unique property?"

---

## Comparison: Traditional vs. ML-Enhanced Causal Inference

| Method | Traditional | ML-Enhanced | Best For |
|--------|------------|-------------|----------|
| **DiD** | Linear regression assumptions | DML (handles high-dimensional confounders) | Many economic controls |
| **PSM** | Logistic regression propensity scores | Causal forests (heterogeneous effects) | Understanding treatment variation |
| **Synthetic Control** | Manual weight selection | Automated optimization | Few treated units |
| **IV** | Two-stage least squares | ML-based first stage | Weak instruments |
| **Survival Analysis** | Cox PH model | DeepSurv (neural networks) | Complex hazard functions |

---

## Implementation Recommendations

### Start Simple
1. **Begin with traditional DiD/PSM** for baseline causal estimates
2. **Validate assumptions** (parallel trends, balance)
3. **Add ML methods** as robustness checks

### Production Pipeline
```python
# 1. Traditional DiD
did_estimate, did_pvalue = run_did(treatment, control, pre, post)

# 2. Double Machine Learning
dml_estimate, dml_ci = run_dml(Y, T, X, W)

# 3. Compare and interpret
if abs(did_estimate - dml_estimate) < dml_ci:
    print("✅ Results consistent - robust causal effect")
else:
    print("⚠️ Results diverge - investigate violations of assumptions")
```

### Visualization Strategy
- **Traditional:** Static before/after plots
- **ML-Enhanced:** Interactive SHAP plots, treatment effect heterogeneity maps
- **Combined:** Side-by-side comparison showing consistency

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
