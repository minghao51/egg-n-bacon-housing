# VAR Housing Appreciation Forecasting System - Implementation Report

**Date:** 2025-02-17
**Status:** ✅ Implementation Complete
**Branch:** `feature/var-housing-forecast`

---
category: "technical-reports"
description: Implementation report for VAR-based housing appreciation forecasting system
status: draft
---

## Overview

Successfully implemented a two-stage hierarchical VAR (Vector Autoregression) system for forecasting Singapore housing price appreciation rates at regional and planning area levels.

**Architecture:**
- **Stage 1:** Regional VAR models (7 regions) with endogenous variables (appreciation, volume, price) + exogenous macroeconomic factors
- **Stage 2:** Planning area ARIMAX models (~20 high-volume areas) using regional forecasts as exogenous predictors

---

## Implementation Details

### 1. Regional Mapping Configuration
**File:** `scripts/core/regional_mapping.py`

Maps 50+ planning areas to 7 Singapore regions:
- CCR (Core Central Region)
- RCR (Rest of Central Region)
- OCR East, North-East, North, West, Central

**Usage:**
```python
from scripts.core.regional_mapping import get_region_for_planning_area

region = get_region_for_planning_area('Downtown')  # Returns 'CCR'
```

### 2. Macroeconomic Data Fetching
**File:** `scripts/data/fetch_macro_data.py`

Fetches Singapore macroeconomic indicators:
- SORA rates (Singapore Overnight Rate Average)
- CPI (Consumer Price Index)
- GDP growth (quarterly)
- Housing policy dates (ABSD, LTV, TDSR changes)

**Note:** Currently uses mock data for MVP. TODO: Integrate MAS/SingStat APIs.

**Usage:**
```python
from scripts.data.fetch_macro_data import fetch_all_macro_data

macro_data = fetch_all_macro_data(start_date='2021-01', end_date='2026-02')
```

### 3. Time Series Data Preparation
**File:** `scripts/analytics/pipelines/prepare_timeseries_data.py`

Transforms L3 unified data into time series datasets:
- Aggregates transactions to regional monthly time series
- Creates planning area time series for top 20 areas by volume
- Merges macroeconomic data (SORA, CPI, GDP)
- Handles missing months via interpolation
- Caps outliers at ±50% appreciation

**Outputs:**
- `L5_regional_timeseries.parquet`
- `L5_area_timeseries.parquet`

**Usage:**
```python
from scripts.analytics.pipelines.prepare_timeseries_data import run_preparation_pipeline

regional_data, area_data = run_preparation_pipeline(
    start_date='2021-01',
    end_date='2026-02'
)
```

### 4. Regional VAR Model
**File:** `scripts/analytics/models/regional_var.py`

Implements VAR models for regional forecasting:
- Stationarity checking via Augmented Dickey-Fuller test
- Automatic lag order selection (AIC-optimized, 1-6 lags)
- Granger causality testing for causal inference
- Forecast generation with 95% confidence intervals
- Model evaluation (RMSE, MAE, MAPE)

**Usage:**
```python
from scripts.analytics.models.regional_var import RegionalVARModel

model = RegionalVARModel(region='CCR')
model.fit(regional_data)
forecast = model.forecast(horizon=36)

# Causal inference
granger_results = model.granger_causality_tests()
```

### 5. Planning Area ARIMAX Model
**File:** `scripts/analytics/models/area_arimax.py`

Implements ARIMAX models for planning area forecasting:
- Uses regional VAR forecasts as exogenous predictors
- Includes local amenity features (MRT, hawker, school proximity)
- Automatic ARIMA order selection via grid search (AIC-optimized)
- Forecast generation with 95% confidence intervals
- Model evaluation metrics

**Usage:**
```python
from scripts.analytics.models.area_arimax import AreaARIMAXModel

model = AreaARIMAXModel(area='Downtown', region='CCR')
model.fit(area_data, exog_vars=['regional_appreciation', 'mrt_within_1km_mean'])
forecast = model.forecast(horizon=12, exog_future=regional_forecast)
```

### 6. Cross-Validation Pipeline
**File:** `scripts/analytics/pipelines/cross_validate_timeseries.py`

Expanding window cross-validation for robust performance estimation:
- 5-fold expanding window validation
- Evaluates regional VAR and area ARIMAX models
- Calculates RMSE, MAE, MAPE, directional accuracy
- Handles model failures gracefully

**Usage:**
```python
from scripts.analytics.pipelines.cross_validate_timeseries import run_cross_validation

results = run_cross_validation(
    regional_data=regional_df,
    area_data=area_df,
    n_folds=5
)
```

### 7. Forecasting Pipeline
**File:** `scripts/analytics/pipelines/forecast_appreciation.py`

Multi-scenario forecasting pipeline:
- **Scenarios:** baseline, bullish, bearish, policy_shock
- Regional VAR forecasts (36-month horizon)
- Area ARIMAX forecasts (24-month horizon)
- Scenario adjustments (interest rates, policy shocks)
- Robust error handling

**Usage:**
```python
from scripts.analytics.pipelines.forecast_appreciation import run_forecasting_pipeline

forecasts = run_forecasting_pipeline(
    scenario='baseline',
    horizon_months=36
)
```

---

## Data Requirements

### Required Datasets
1. **L3 unified dataset** - Transaction-level data with planning areas
   - Currently needs to be created
   - Location: `data/pipeline/L3/housing_unified.parquet`

2. **L5 growth metrics** - Monthly growth metrics by planning area
   - Already exists in project
   - Location: `data/pipeline/L5_growth_metrics_by_area.parquet`

3. **Macroeconomic data** - SORA, CPI, GDP, policies
   - Generated by `fetch_all_macro_data()`
   - Location: `data/raw_data/macro/`

### Output Datasets
1. **L5_regional_timeseries.parquet** - Regional monthly time series
2. **L5_area_timeseries.parquet** - Planning area monthly time series

---

## Testing

**Test Statistics:**
- 21 tests across 7 test files
- All tests passing ✅
- Test coverage: 62-71% for core modules

**Run Tests:**
```bash
# Run all analytics tests
uv run pytest tests/analytics/ tests/core/test_regional_mapping.py tests/data/ -v

# Run with coverage
uv run pytest tests/analytics/ --cov=scripts/analytics --cov-report=html
```

**View Coverage Report:**
Open `htmlcov/index.html` in browser

---

## Usage Workflow

### Complete Pipeline Execution

1. **Fetch macroeconomic data:**
   ```bash
   uv run python scripts/data/fetch_macro_data.py
   ```

2. **Prepare time series data:**
   ```bash
   uv run python scripts/analytics/pipelines/prepare_timeseries_data.py
   ```

3. **Run cross-validation:**
   ```python
   from scripts.analytics.pipelines.cross_validate_timeseries import run_cross_validation
   from scripts.core.data_helpers import load_parquet

   regional_data = load_parquet("L5_regional_timeseries")
   area_data = load_parquet("L5_area_timeseries")

   results = run_cross_validation(regional_data, area_data, n_folds=5)
   ```

4. **Generate forecasts:**
   ```python
   from scripts.analytics.pipelines.forecast_appreciation import run_forecasting_pipeline

   forecasts = run_forecasting_pipeline(
       scenario='baseline',
       horizon_months=36
   )
   ```

---

## Technical Specifications

**Dependencies:**
- Python 3.11+
- pandas, numpy
- statsmodels (VAR, ARIMA, stationarity tests, Granger causality)
- pytest (testing)

**Model Configuration:**
- **VAR Endogenous Variables:** regional_appreciation, regional_volume, regional_price_psf
- **VAR Exogenous Variables:** sora_rate, cpi, gdp_growth
- **ARIMAX Endogenous:** area_appreciation
- **ARIMAX Exogenous:** regional_appreciation, mrt_within_1km_mean, hawker_within_1km_mean

**Performance Targets (from design doc):**
- RMSE < 5% for regional forecasts
- RMSE < 8% for planning area forecasts
- Backtest directional accuracy > 70%

---

## Known Limitations

1. **L3 Unified Dataset** - Not yet created, needs to be generated from existing L1/L2 data
2. **Macroeconomic Data** - Using mock data; MAS/SingStat API integration needed
3. **Test Coverage** - Currently 62-71%; goal is 80%+
4. **Backtesting** - Not yet validated against 2021-2025 data

---

## Next Steps

### Immediate (Required for Production)
1. **Generate L3 unified dataset** from existing transaction data
2. **Run full pipeline** with real data
3. **Validate forecasts** via backtesting (2021-2025)
4. **Improve test coverage** to 80%+

### Future Enhancements
1. **Integrate MAS/SingStat APIs** for real macroeconomic data
2. **Add IRF (Impulse Response Functions)** for causal analysis
3. **Add FEVD (Forecast Error Variance Decomposition)** for variable importance
4. **Implement scenario probability weights** (Monte Carlo scenarios)
5. **Build forecasting dashboard** for visualizing predictions

---

## Files Created

**Core Modules:**
- `scripts/core/regional_mapping.py` (180 lines)
- `scripts/data/fetch_macro_data.py` (269 lines)
- `scripts/analytics/pipelines/prepare_timeseries_data.py` (410 lines)

**Models:**
- `scripts/analytics/models/regional_var.py` (349 lines)
- `scripts/analytics/models/area_arimax.py` (308 lines)

**Pipelines:**
- `scripts/analytics/pipelines/cross_validate_timeseries.py` (243 lines)
- `scripts/analytics/pipelines/forecast_appreciation.py` (329 lines)

**Tests:**
- `tests/core/test_regional_mapping.py` (30 lines)
- `tests/data/test_fetch_macro_data.py` (33 lines)
- `tests/analytics/test_prepare_timeseries_data.py` (54 lines)
- `tests/analytics/models/test_regional_var.py` (68 lines)
- `tests/analytics/models/test_area_arimax.py` (57 lines)
- `tests/analytics/pipelines/test_cross_validate.py` (50 lines)
- `tests/analytics/pipelines/test_forecast_appreciation.py` (53 lines)

**Total:** ~2,400 lines of code (including tests)

---

## References

**Design Document:** `docs/plans/20250216-plan-autoregression-var-housing-appreciation.md`
**Implementation Plan:** `docs/plans/2025-02-16-var-housing-appreciation-implementation.md`

---

## Git History

**Commits on `feature/var-housing-forecast`:**
1. `0a2af0d` - feat(analytics): add regional mapping for 7 Singapore regions
2. `d292d57` - feat(data): add macroeconomic data fetching module
3. `3483f14` - feat(analytics): add time series data preparation pipeline
4. `99c7d1f` - feat(analytics): implement regional VAR model
5. `e00edcd` - feat(analytics): implement planning area ARIMAX model
6. `abaafec` - feat(analytics): implement cross-validation pipeline
7. `c24ebbb` - feat(analytics): implement forecasting pipeline

**Branch Status:** Ready for merge to `main` after L3 unified dataset is created.
