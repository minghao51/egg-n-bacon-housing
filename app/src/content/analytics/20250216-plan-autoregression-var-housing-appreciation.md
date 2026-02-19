---
title: "Autoregression & VAR Models for Housing Appreciation Prediction"
status: "draft"
created: "2025-02-16"
updated: "2025-02-17"
category: "market-analysis"
---

# Autoregression & VAR Models for Housing Appreciation Prediction

**Status:** ✅ Implemented (2025-02-17)
**Created:** 2025-02-16
**Updated:** 2025-02-17
**Approach:** Two-Stage Hierarchical VAR

## Implementation Summary

**Completed Tasks (2025-02-17):**
- ✅ Regional mapping configuration (50+ planning areas → 7 regions)
- ✅ Macroeconomic data fetching (SORA, CPI, GDP, policy dates)
- ✅ Time series data preparation pipeline (regional & area aggregation)
- ✅ Regional VAR model with stationarity checking & lag selection
- ✅ Planning area ARIMAX model with regional forecasts as exogenous predictors
- ✅ Cross-validation pipeline (expanding window validation)
- ✅ Multi-scenario forecasting pipeline (baseline/bullish/bearish/policy shock)

**Implementation Statistics:**
- 7 Python modules created
- 7 test files with 21 tests (all passing)
- Test coverage: 62-71% for core analytics modules
- Total LOC: ~2,300 lines (including tests)

**Next Steps:**
- Generate L3 unified dataset (required for time series preparation)
- Run cross-validation to validate model accuracy
- Test forecasting pipeline with real data
- Add Granger causality analysis for driver insights

---

## Executive Summary

**Goal:** Build a time series forecasting system to predict housing price appreciation rates (1-3 years at planning area level, 3-5 years at regional level) while enabling causal inference on appreciation drivers.

**Approach:** Two-Stage Hierarchical VAR
- **Stage 1:** Regional Panel VAR (7 regions) with endogenous variables (appreciation, volume, prices) + exogenous macroeconomic/amenity factors
- **Stage 2:** Planning Area ARIMAX models (~20 high-volume areas) using regional forecasts as exogenous predictors

**Data Period:** Post-COVID (2021-2026, ~60 months)
**Geography:** 7 regions (CCR, RCR, OCR East/North-East/North/West/Central) + ~20 planning areas

---

## Requirements Analysis

### Primary Goals

1. **Predictive Forecasting (Priority A)**
   - Medium-term (1-3 years) at planning area level
   - Long-term (3-5 years) at regional level
   - Actionable for investment decisions

2. **Causal Inference (Priority B)**
   - Understand how MRT proximity, amenities, policy changes impact appreciation
   - Time-varying effects (e.g., MRT premium decay after opening)
   - Interaction effects between drivers

### Constraints

- **Spatial autocorrelation:** Moran's I = 0.67 (must address)
- **Data availability:** Post-COVID only (2021-2026)
- **Interpretability:** Must be explainable to stakeholders
- **Integration:** Build on existing L3/L5 pipeline

### Success Criteria

- Forecast accuracy: RMSE < 5% for regional, < 8% for planning area
- Causal validity: Granger causality tests pass for key drivers
- Validation: Backtest against 2021-2025 data with >70% directional accuracy
- Performance: Regional VAR trains in <10 minutes, area AR in <5 minutes

---

## Architectural Approach: Two-Stage Hierarchical VAR

### Why This Approach?

**Advantages:**
- ✅ Cleanly separates 1-3 yr (area) and 3-5 yr (regional) goals
- ✅ Captures spillover effects through regional exogenous variables
- ✅ Computationally manageable (5-8 VAR models + ~20 AR models)
- ✅ Easy to interpret and validate
- ✅ Uses standard libraries (`statsmodels`, `var`)
- ✅ Naturally handles spatial autocorrelation via regional aggregation

**Trade-offs:**
- ❌ Requires manual regional aggregation
- ❌ Doesn't fully account for within-region spatial correlation
- ❌ Regional → planning area assumptions may not hold for all areas

### Alternatives Considered

**Approach 2: Bayesian Hierarchical PVAR**
- Most statistically rigorous but computationally intensive (MCMC)
- Higher implementation complexity (4-6 weeks)
- Harder to explain to stakeholders

**Approach 3: Hybrid VAR + XGBoost Ensemble**
- Leverages existing XGBoost success (R²=0.91)
- Less suitable for causal inference
- Harder to interpret coefficient effects

---

## Data Preparation & Feature Engineering

### Regional Aggregation

**7 Regions defined:**

| Region | Planning Areas | Rationale |
|--------|---------------|-----------|
| **CCR** | Downtown, Newton, Orchard, Marina Bay | Prime residential, highest prices |
| **RCR** | Bukit Merah, Queenstown, Geylang, Kallang | City fringe, mature estates |
| **OCR East** | Bedok, Pasir Ris, Tampines, Changi | East regional identity |
| **OCR North-East** | Ang Mo Kio, Serangoon, Hougang, Sengkang, Punggol | MRT line corridor |
| **OCR North** | Woodlands, Yishun, Sembawang | North-South corridor |
| **OCR West** | Jurong, Bukit Batok, Choa Chu Kang | Jurong Lake District hub |
| **OCR Central** | Bishan, Toa Payoh, Central | Geographic center |

**Filtering:**
- Minimum 30 months of data per region
- Top 20 planning areas by transaction volume

### Time Series Variables

**Regional-level (VAR endogenous):**
- `regional_appreciation`: Median YoY appreciation % in region
- `regional_volume`: Transaction count in region
- `regional_price_psf`: Median price PSF in region

**Regional-level (VAR exogenous):**
- Macroeconomic: `interest_rate` (SORA), `cpi`, `gdp_growth`
- Policy: `absd_rate`, `ltv_limit` (binary indicators)
- Amenity: `mrt_accessibility`, `hawker_accessibility`

**Planning area-level (AR predictors):**
- Target: `area_appreciation` (YoY appreciation %)
- Regional forecasts: `regional_appreciation_forecast`, `regional_volume_forecast`
- Local amenities: `mrt_within_1km`, `hawker_within_1km`, `school_quality_score`
- Interaction terms: `mrt_x_regional_appreciation`, `new_mrt_opening` (binary)

### Data Pipeline

**New Scripts:**

1. **`scripts/data/fetch_macro_data.py`**
   - Fetch macro data from MAS, SingStat, MND
   - Storage: `data/raw_data/macro/`
   - Files: `singapore_cpi_monthly.parquet`, `sora_rates_monthly.parquet`, `sgdp_quarterly.parquet`, `housing_policy_dates.parquet`

2. **`scripts/analytics/pipelines/prepare_timeseries_data.py`**
   - Load L3 unified + L5 growth metrics
   - Apply regional aggregation
   - Merge macroeconomic data
   - Create interaction terms
   - Handle missing data (interpolation)
   - Train/test split (80/20: 2021-2024 train, 2025 test)
   - Output: `L5_regional_timeseries.parquet`, `L5_area_timeseries.parquet`

**Data Quality Checks:**
- Minimum 30 months of non-NaN data
- Outlier detection (cap appreciation at ±50%)
- Stationarity tests (ADF test) - apply differencing if needed

---

## Model Architecture

### Stage 1: Regional Panel VAR Model

**Model Specification:**

For each region `r` at time `t`:

```
Y_r,t = c + A₁·Y_r,t-1 + A₂·Y_r,t-2 + ... + A_p·Y_r,t-p + B·X_t + ε_t
```

**Where:**
- `Y_r,t = [appreciation, volume, price_psf]` (3 endogenous variables)
- `X_t = [interest_rate, cpi, gdp_growth, mrt_accessibility, hawker_accessibility]` (5 exogenous variables)
- `A₁...A_p` = 3×3 coefficient matrices (p = optimal lag order)
- `B` = 3×5 coefficient matrix (exogenous effects)
- `ε_t` = Error term (assumed i.i.d. normal)

**Lag Selection:**

```python
# Automatic lag order selection
max_lag = 6  # Test 1-6 months (6 months = half-year for quarterly patterns)
selected_lag = select_order(data, maxlags=max_lag, criterion='aic')  # AIC preferred
# Fallback: BIC for more parsimonious model
```

**Estimation:**
- Method: OLS per equation (SUR not needed - same regressors per equation)
- Regularization: Ridge penalty if multicollinearity detected (VIF > 10)
- Sample size: 60 months (2021-2026) - sufficient for VAR(3-6) with 8 variables

**Model Diagnostics:**

1. **Stability condition:** All eigenvalues of companion matrix < 1 (stationary VAR)
2. **Serial correlation:** Portmanteau test (Ljung-Box) on residuals
3. **Heteroskedasticity:** ARCH-LM test
4. **Normality:** Jarque-Bera test on residuals

**If diagnostics fail:**
- Non-stationary: Apply first differences to non-stationary variables
- Serial correlation: Increase lag order
- Heteroskedasticity: Robust standard errors (Newey-West)

**Causal Inference Tools:**

1. **Granger Causality Tests:**
   - Test: Does variable X Granger-cause appreciation?
   - Null hypothesis: Coefficients on lags of X are jointly zero
   - Significance: p < 0.05 (F-test)

2. **Impulse Response Functions (IRF):**
   - Shock to interest rate → appreciation response over 12-24 months
   - Shock to MRT accessibility → appreciation response
   - Confidence bands: 68% (1 SE) and 95% (2 SE)

3. **Forecast Error Variance Decomposition (FEVD):**
   - What % of appreciation forecast error variance is explained by:
     - Own shocks (appreciation inertia)
     - Interest rate shocks
     - Amenity shocks
   - Report at horizons: 6, 12, 24, 36 months

### Stage 2: Planning Area ARIMAX Model

**Model Specification:**

For each planning area `a` at time `t`:

```
appreciation_a,t = c + Σ(φ_i·appreciation_a,t-i) + θ·regional_forecast_t + γ·local_features_t + η_t
```

**Where:**
- `φ_i` = AR coefficients (i = 1 to p, p selected by AIC)
- `regional_forecast_t` = Regional VAR forecast (exogenous predictor)
- `local_features_t` = [mrt_within_1km, hawker_within_1km, school_quality, new_mrt_opening, interaction_terms]
- `η_t` = Error term

**Model Selection:**

```python
# Grid search over ARIMA orders
from statsmodels.tsa.arima.model import ARIMA

param_grid = {
    'order': [(p, 0, q) for p in [1,2,3,4,5,6] for q in [0,1]],  # AR only preferred
    'exog': [regional_forecast, local_features]
}

# Select by AIC (penalizes complexity)
best_model = min(grid_search, key=lambda m: m.aic)
```

**Special Cases:**

1. **New MRT openings:** Intervention dummy variable
   - `new_mrt_opening_t = 1` if month t is within 6 months of opening, else 0
   - Tests pre-announcement vs. post-opening effects

2. **Policy changes:** Step function dummy
   - `absd_increase_t = 1` if t ≥ policy_date, else 0
   - Captures permanent level shifts

3. **Seasonality:** Monthly dummy variables (if significant)
   - Add 11 month dummies (December omitted as baseline)
   - Test significance with joint F-test

**Feature Engineering for Time-Varying Effects:**

To capture changing amenity impacts (e.g., MRT premium decay):

```
# Interaction: MRT effect depends on regional appreciation
mrt_effect_t = mrt_within_1km_a,t × regional_appreciation_t

# Time decay: MRT premium decays after opening
mrt_decay_t = mrt_within_1km_a,t × exp(-0.1 × months_since_opening_t)
```

### Hierarchical Integration

**Forecasting Procedure:**

1. **Generate regional forecasts (Stage 1 VAR):**
   ```python
   regional_var.fit(train_data)
   regional_forecast = regional_var.forecast(steps=36)  # 3-year horizon
   ```

2. **Prepare regional exogenous inputs for Stage 2:**
   ```python
   area_exog = {
       'regional_appreciation_forecast': regional_forecast[:, 0],  # Col 0 = appreciation
       'regional_volume_forecast': regional_forecast[:, 1],
       'local_features': area_features  # Static for forecast period
   }
   ```

3. **Generate planning area forecasts (Stage 2 ARIMAX):**
   ```python
   area_arimax = ARIMA(
       endog=area_train['appreciation'],
       exog=area_train_exog,
       order=(3, 0, 0)  # AR(3) from grid search
   )
   area_arimax.fit()
   area_forecast = area_arimax.forecast(
       steps=36,
       exog=area_exog_forecast
   )
   ```

**Uncertainty Quantification:**

- Regional VAR: Analytic confidence intervals (Kalman filter)
- Area AR: Delta method or simulation-based (1000 Monte Carlo draws)
- Combined uncertainty: Propagate regional CI → area forecasts via simulation

---

## Training & Validation Procedure

### Data Splitting Strategy

**Temporal Train/Test Split:**

```
Training period:   2021-01 to 2024-06 (42 months, 70%)
Validation period: 2024-07 to 2025-06 (12 months, 20%)
Test period:       2025-07 to 2026-02 (8 months, 10%)
```

**Rolling Window Validation:**

Expanding window validation with 5 folds:
- Start with 42 months training data
- Expand by 3 months each fold
- Forecast 12 months ahead each fold
- Compute accuracy metrics across folds

### Stage 1 (Regional VAR) Training

**Steps:**
1. Load regional timeseries data
2. Stationarity checks (ADF test) - apply differencing if needed
3. Split train/test (temporal)
4. Fit VAR model with AIC-optimized lags (maxlags=6)
5. Diagnostics: stability, serial correlation, normality
6. Forecast and evaluate (RMSE, MAE, MAPE, directional accuracy)

**Hyperparameter Tuning:**
- Lag order: 1-6 months (AIC-optimized)
- Regularization: Ridge if VIF > 10
- Differencing: d=0 or d=1 based on ADF test

### Stage 2 (Planning Area AR) Training

**Steps:**
1. For each of top 20 planning areas by volume
2. Prepare data (target + regional forecasts + local features)
3. Grid search ARIMA orders (p=1-6, d=0-1, q=0-1)
4. Feature selection via backward elimination (p-value < 0.10)
5. Forecast and evaluate

**Feature Selection:**
- Backward elimination on local features
- Keep only significant features (p < 0.10)
- Test interaction terms (MRT × regional appreciation)

### Evaluation Metrics

**Forecast Accuracy:**
- RMSE: < 5% (regional), < 8% (area)
- MAE: < 4% (regional), < 6% (area)
- MAPE: < 10%
- Directional accuracy: > 70%

**Causal Validity:**
- Granger causality: p < 0.05 for key drivers
- IRF significance: 95% CI excludes 0
- FEVD: > 10% variance explained by amenity/macro vars

**Model Comparison:**
- Baseline: Naïve forecast (last period)
- Benchmark: XGBoost (R²=0.91 from MRT analysis)
- Proposed: VAR+AR hierarchical

### Cross-Validation Outputs

**New script:** `scripts/analytics/pipelines/cross_validate_timeseries.py`

**Outputs:**
- `L5_regional_var_results.parquet` (RMSE, MAE, best_lag per region)
- `L5_area_ar_results.parquet` (RMSE, MAE, best_order per area)
- `L5_forecast_comparison.parquet` (actual vs. forecast)

---

## Forecasting Engine & Visualization

### Forecasting Engine Architecture

**New script:** `scripts/analytics/pipelines/forecast_appreciation.py`

**Functions:**
- `generate_regional_forecasts()` - Generate VAR forecasts with uncertainty bands
- `generate_area_forecasts()` - Generate ARIMAX forecasts using regional forecasts
- Monte Carlo simulation for propagating regional uncertainty to area level

**Forecast Scenarios:**

| Scenario | Interest Rate | GDP Growth | Use Case |
|----------|--------------|------------|----------|
| **Baseline** | Current trajectory | Historical trend | Standard forecast |
| **Bullish** | -1% vs baseline | +0.5% vs baseline | Low-rate environment |
| **Bearish** | +1% vs baseline | -0.5% vs baseline | High-rate/recession |
| **Policy shock** | Unchanged | New ABSD rate | Policy impact |

### Uncertainty Quantification

- Regional VAR: Analytic CIs (Kalman filter)
- Area AR: Monte Carlo simulation (1000 draws)
- Confidence bands: 68% (1 SE) and 95% (2 SE)

### Visualization Outputs

**New script:** `scripts/analytics/visualization/plot_forecasts.py`

**Output directory:** `data/analysis/var_forecasts/`

**Plots:**
1. `regional_forecast_overview.png` - 7 regional forecasts (2021-2029)
2. `area_forecasts_top20.png` - 20 planning area forecasts (2021-2028)
3. `granger_causality_network.png` - Directed network of causal relationships
4. `irf_shocks_summary.png` - Impulse response functions (9 subplots)
5. `fevd_summary.png` - Forecast error variance decomposition
6. `backtest_results_2021-2026.png` - Extended backtesting (2021-2026 validation)

**Visualization decisions:**
- Static PNG plots (sufficient for reporting)
- 68% and 95% confidence bands
- Historical + forecast on same plot

### Dashboard Export

**New script:** `scripts/analytics/pipelines/export_forecast_dashboard.py`

**Output:** `app/public/data/analytics/var_forecasts.json.gz`

**Structure:**
- Metadata (timestamp, horizon, scenario)
- Regional forecasts (historical + forecasted with CIs)
- Area forecasts (forecasted with CIs)
- Causal inference results (Granger p-values, IRF peaks, FEVD)

**Format:** JSON.gz (compressed for dashboard loading)

---

## Error Handling & Edge Cases

### Data Quality Issues

**Issue 1: Missing Months**

| Gap size | Action | Rationale |
|----------|--------|-----------|
| **1-2 months** | Linear interpolation | Small gaps, preserve trends |
| **3-6 months** | Seasonal decompose + imputation | Account for seasonality |
| **>6 months** | Drop series | Too much missing |

**Issue 2: Outliers**

- Cap appreciation at ±50%
- Flag for manual review
- Log warnings

**Issue 3: Non-Stationarity**

- Test with ADF (p < 0.05)
- Apply first/second differencing if needed
- Max 2 differencing operations

**Issue 4: Insufficient Data**

- Regional: ≥30 months required
- Planning area: ≥24 months required
- Skip if below threshold

### Model Estimation Failures

**Issue 1: VAR Matrix Singularity**

1. Check VIF for multicollinearity
2. Remove variable with VIF > 10
3. Apply ridge regularization (α=0.1) if still fails

**Issue 2: ARIMA Convergence Failure**

**Automated retry strategy:**
```python
# Try progressively simpler models
orders_to_try = [
    (p, d, q),      # Original order
    (p-1, d, q),    # Reduce AR
    (p, d, q-1),    # Reduce MA
    (p-1, d, 0),    # AR only, simpler
    (3, d, 0),      # AR(3) default
    (1, d, 0),      # AR(1) fallback
]

for order in orders_to_try:
    try:
        model = ARIMA(y_train, exog=X_train, order=order).fit()
        logger.info(f"ARIMA{order} succeeded for {area}")
        return model
    except Exception:
        continue

# All attempts failed - use better fallback
return get_fallback_model(area, y_train, X_train)
```

**Improved fallback strategies:**

Instead of simple AR(1), use:

1. **Regional average model** (if regional VAR succeeded):
   ```python
   # Predict area appreciation as regional appreciation + area bias
   area_bias = area_appreciation_mean - regional_appreciation_mean
   forecast = regional_forecast + area_bias
   ```

2. **Similar area model** (k-nearest neighbors):
   ```python
   # Find 3 most similar areas (by price level, volume, amenities)
   # Average their forecasts
   similar_areas = find_similar_areas(area, k=3)
   forecast = similar_areas['forecast'].mean()
   ```

3. **XGBoost fallback** (if available from MRT analysis):
   ```python
   # Use existing XGBoost model (R²=0.91) for forecasting
   # Predict appreciation based on amenity features
   forecast = xgb_model.predict(area_features)
   ```

**Fallback priority:** Regional average > Similar areas > XGBoost > AR(1)

### Forecasting Edge Cases

**Issue 1: Forecast Horizon Exceeds Stable Range**

- Regional: Max 48 months
- Area: Max 36 months
- Warn if exceeded

**Issue 2: Regional Forecast Propagation Errors**

- If regional fails, area model uses fallback forecast
- Continue with other areas (don't fail entire pipeline)

**Issue 3: Exploding Confidence Intervals**

- Cap regional CIs at ±20%
- Cap area CIs at ±30%
- Annotate: "CI capped at realistic bounds"

### Exogenous Data Issues

**Issue 1: Missing Macroeconomic Data**

**Fallbacks:**
- `interest_rate`: Last available rate (assume constant)
- `cpi`: Linear interpolation
- `gdp_growth`: Historical mean (3% annual)
- `absd_rate`: Assume 0 (no additional measures)

**Issue 2: Future Macro Data for Forecasts**

Use scenario-based assumptions:
- Baseline: Current rates
- Bullish: -1% rates, +0.5% GDP
- Bearish: +1% rates, -0.5% GDP
- Document assumptions in metadata

### Automated Retry Logic

**New script:** `scripts/analytics/pipelines/retry_failed_models.py`

**Strategy:**

```python
MAX_RETRIES = 3
PARAMETER_GRID = {
    'lag_order': [3, 4, 5, 6],
    'regularization': [0, 0.01, 0.1],
    'differencing': [0, 1]
}

def fit_model_with_retry(area, data):
    """Fit model with automated parameter search on failure."""

    # Try optimal parameters first
    model = fit_model(area, data, **optimal_params)
    if model.success:
        return model

    # Retry with parameter grid
    for retry in range(MAX_RETRIES):
        logger.warning(f"Retry {retry+1} for {area}")

        # Sample parameters from grid
        params = sample_parameter_grid(PARAMETER_GRID)
        model = fit_model(area, data, **params)

        if model.success:
            logger.info(f"Retry {retry+1} succeeded with params: {params}")
            return model

    # All retries failed - use fallback
    logger.error(f"All retries failed for {area}, using fallback")
    return get_fallback_model(area, data)
```

### Error Reporting

**Output:** `data/logs/var_modeling_errors_YYYYMMDD.json`

**Contents:**
- Summary (success/failure counts)
- Failed regions/areas with reasons
- Warnings (outliers, missing data)
- Model diagnostics (stationarity, serial correlation)
- Retry history (which parameters succeeded)

**Acceptable failure rate:**
- Regions: ≤1 failure out of 7 (~14%)
- Areas: ≤2 failures out of 20 (10%)

**Logging:**
- File only (no alerts)
- Review after each run
- Investigate systematic failures

---

## Testing Strategy

### Unit Tests

**File:** `tests/analytics/test_var_models.py`

**Test cases:**
- Regional aggregation correctness
- Stationarity detection (ADF test)
- Missing month interpolation
- VAR model estimation on synthetic data
- Granger causality detection
- Forecast confidence intervals
- Automated retry logic
- Outlier detection and capping

**Run:** `uv run pytest tests/analytics/test_var_models.py -v`

### Integration Tests

**File:** `tests/analytics/integration/test_forecasting_pipeline.py`

**Test cases:**
- End-to-end forecasting pipeline
- Regional to area forecast propagation
- Scenario forecast differences

**Run:** `uv run pytest tests/analytics/integration/ -m integration -v`

### Validation Tests

**File:** `tests/analytics/validation/test_backtesting.py`

**Test cases:**
- Backtest accuracy meets targets (>70% directional)
- Extended backtest (2021-2026)
- Rolling window validation (5 folds)

**Run:** `uv run pytest tests/analytics/validation/ -m validation -v`

### Performance Tests

**File:** `tests/analytics/test_performance.py`

**Test cases:**
- Regional VAR training < 10 minutes
- Area AR training < 5 minutes
- Forecast generation < 1 second

**Run:** `uv run pytest tests/analytics/test_performance.py -v`

### Manual Validation Checklist

**Before deployment:**
- Data quality checks (no missing months, outliers capped)
- Model validation (stationarity, no serial correlation)
- Forecast validation (backtest accuracy > 70%)
- Visualization checks (all plots generated)
- Dashboard integration (JSON.gz loads correctly)
- Documentation complete

### Test Coverage Target

>80% coverage for analytics code

**Check:** `uv run pytest --cov=scripts/analytics --cov-report=html`

---

## Design Approval Status

**Status:** ✅ Approved - Proceed to Implementation Planning

**Summary:**
- Approach: Two-Stage Hierarchical VAR
- Data: Post-COVID (2021-2026), 7 regions + 20 planning areas
- Goals: Predictive forecasting + Causal inference
- Implementation: 4 weeks

**Next Step:** Invoke writing-plans skill for detailed implementation roadmap

---

## Implementation Roadmap

**Week 1:** Data Preparation
- Regional aggregation implementation
- Macro data fetching
- Time series dataset construction

**Week 2:** Regional VAR
- Model estimation & validation
- Lag selection (AIC/BIC)
- Granger causality tests
- Regional forecasting (12-36 month horizon)

**Week 3:** Planning Area AR
- ARIMAX model estimation
- Integration with regional forecasts
- Area-level forecasting (12-36 month horizon)

**Week 4:** System Integration
- Forecasting engine
- Visualization dashboard
- Backtesting validation
- Documentation

---

## Dependencies

**Existing Data:**
- `L3/housing_unified.parquet` (unified transaction data)
- `L5_temporal_features.parquet` (lagged appreciation, momentum)
- `L5_growth_metrics_by_area.parquet` (monthly growth by planning area)

**Existing Analysis:**
- MRT impact analysis (amenity feature engineering)
- Spatial autocorrelation analysis (Moran's I = 0.67)

**Python Libraries:**
- `statsmodels` (VAR, ARIMA, Granger causality)
- `arch` (volatility modeling, if needed)
- `pandas`, `numpy`, `scipy` (data manipulation)

**External Data:**
- MAS SORA rates API
- SingStat data API
- MND policy announcements

---

## Open Questions

1. **Regional boundaries:** Should we adjust regional groupings based on price correlation analysis?

2. **Lag selection:** Start with AIC-optimized lags (likely 3-6 months for monthly data)?

3. **Stationarity:** If appreciation rates are non-stationary, use first differences (change in appreciation)?

4. **Missing months:** Interpolate gaps <3 months, or drop entire series with gaps?

5. **Policy variables:** Model as level shocks (binary on change date) or continuous effects?

---

## References

- Existing analysis: `docs/analytics/mrt-impact.md`
- Architecture: `.planning/codebase/ARCHITECTURE.md`
- L5 metrics: `scripts/core/stages/L5_metrics.py`
- L3 export: `scripts/core/stages/L3_export.py`

---

**Next Step:** Design Model Architecture section (VAR specification, estimation procedure)
