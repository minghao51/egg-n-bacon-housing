# Feature Importance Analysis - Singapore Housing Market

**Date:** 2026-01-22
**Dataset:** `data/analysis/market_segmentation/housing_unified_segmented.parquet`
**Records:** 850,872 transactions (1990-2026)

## Overview

This analysis explores feature importance for predicting housing prices, rental yields, and appreciation rates using multiple regression models:
- Linear Regression (baseline)
- Ridge Regression (regularized)
- XGBoost (gradient boosting)
- Random Forest (ensemble trees)

## Methodology

### Data Preparation
- **Features Used:** 39 features total
  - **Location (24):** Distances to MRT, hawker, supermarket, park, preschool, childcare (6 continuous + 18 binary indicators within 500m/1km/2km)
  - **Property (2):** Floor area (sqm), remaining lease months
  - **Market (4):** Transaction count, volume averages, stratified median price
  - **Categorical (8):** Town, flat type, flat model, storey range, market tier, PSM tier, property type, momentum signal
- **Temporal Split:** Train on pre-2020 data, test on 2020+ data
- **Missing Values:** Dropped columns with >80% missing (Project Name, Street Name, etc.)

### Targets Analyzed
1. **Transaction Price (PSM)** - Price per square meter
2. **Rental Yield (%)** - Annual rental yield percentage (skipped due to data constraints)
3. **Year-over-Year Appreciation (%)** - Annual price appreciation rate

## Results

### 1. Transaction Price (PSM) Prediction

| Model | Train R² | Test R² | Test MAE | Test RMSE |
|-------|----------|---------|----------|-----------|
| Linear Regression | 0.8618 | **-0.497** | 4,893 | 8,324 |
| Ridge Regression | 0.8618 | **-0.505** | 4,908 | 8,347 |
| XGBoost | 0.9115 | **-0.813** | 5,579 | 9,161 |
| Random Forest | 0.9203 | **-0.813** | 5,609 | 9,161 |

**Key Observations:**
- **Severe overfitting:** All models show negative R² on test set
- **Temporal mismatch:** Models trained on pre-2020 data fail to generalize to 2020+ market
- **Tree models worse:** XGBoost and Random Forest overfit more than linear models
- **Possible causes:**
  - COVID-19 pandemic impact (2020-2022)
  - Interest rate changes
  - Cooling measures introduced post-2020
  - Structural market shifts

### 2. Year-over-Year Appreciation (%) Prediction

| Model | Train R² | Test R² | Test MAE | Test RMSE |
|-------|----------|---------|----------|-----------|
| Linear Regression | 0.2008 | **0.0125** | 39.85 | 102.21 |
| Ridge Regression | 0.2008 | **0.0126** | 39.84 | 102.20 |
| XGBoost | 0.9127 | **-0.0032** | 42.69 | 103.02 |
| Random Forest | 0.9785 | **-0.0103** | 43.78 | 103.38 |

**Key Observations:**
- **Poor predictability:** Appreciation rates are inherently difficult to predict
- **Linear models slightly better:** Less overfitting than tree models
- **High error:** MAE of ~40% on appreciation prediction
- **Expected result:** Appreciation depends on macroeconomic factors not in the dataset

### 3. Rental Yield (%)
- **Skipped:** All rental yield data is from 2020+, causing empty training set
- **Recommendation:** Need historical rental data or use random split instead of temporal

## Key Findings

### What Worked
1. **Feature Engineering:** Successfully created 39 features from raw dataset
2. **Pipeline:** Robust preprocessing with imputation and one-hot encoding
3. **Linear Models:** More stable than tree models for temporal prediction

### What Didn't Work
1. **Temporal Generalization:** Models fail to predict future prices
2. **Tree Models:** Severe overfitting (Train R² > 0.90, Test R² < -0.80)
3. **Appreciation Prediction:** Very low R² (~0.01) indicates missing features

### Feature Insights
**Note:** Due to overfitting, feature importance rankings are not reliable. However, the framework is in place to extract:
- Coefficient magnitudes (linear models)
- Feature importances (tree models)
- SHAP values (if installed)

## Recommendations

### Immediate Improvements
1. **Fix Temporal Split:** Use 80/20 random split OR ensure sufficient data across all time periods
2. **Add Time Features:** Include year, month as features (not just for splitting)
3. **Regularization:** Increase regularization strength for tree models
4. **Cross-Validation:** Use time-series cross-validation instead of single split

### Feature Engineering
1. **Macro Economic Features:** Interest rates, GDP growth, unemployment
2. **Policy Features:** Cooling measures, loan-to-value limits
3. **Market Sentiment:** Search volume, news sentiment
4. **Interaction Features:** Distance × property type, lease × year

### Modeling Improvements
1. **Ensemble Methods:** Blend linear and tree models
2. **Time-Series Models:** ARIMA, Prophet for appreciation
3. **Hierarchical Models:** Mixed-effects models for town/area clustering
4. **Causal Inference:** Use causal forests to estimate treatment effects

### Next Steps
1. **Re-run with random split** to establish baseline performance
2. **Extract feature importance** from best-performing model
3. **Create visualization notebook** with partial dependence plots
4. **Panel regression** for appreciation with town fixed effects
5. **Install SHAP** (compatible with Python 3.13) for detailed interpretation

## Files Created

```
scripts/analyze_feature_importance.py          # Main analysis script
data/analysis/feature_importance/
  ├── model_comparison.csv                    # Model performance metrics
  └── [future] shap_*.csv                     # SHAP values (if SHAP installed)
docs/20260122-feature-importance-analysis-summary.md  # This document
```

## Technical Notes

### Dependencies Installed
- `xgboost` - Gradient boosting (requires OpenMP runtime)
- `libomp` - OpenMP runtime for XGBoost (installed via brew)

### SHAP Installation
SHAP was not installed due to Python 3.13 compatibility issues with numba. To install:
```bash
# Option 1: Use Python 3.11 or 3.12
# Option 2: Install SHAP without numba (limited functionality)
uv pip install shap --no-deps
pip install numba==0.60.0
```

### Environment Variables Required
```bash
export LDFLAGS="-L/opt/homebrew/opt/libomp/lib"
export CPPFLAGS="-I/opt/homebrew/opt/libomp/include"
export DYLD_LIBRARY_PATH="/opt/homebrew/opt/libomp/lib:$DYLD_LIBRARY_PATH"
```

## Conclusion

The feature importance analysis framework is **successfully implemented** but results show **severe overfitting** due to temporal mismatch between training and test periods. This is actually an important finding:

> **Pre-2020 housing market patterns do not generalize to post-2020 market**

This suggests structural breaks in the market, likely due to:
- COVID-19 pandemic effects
- Monetary policy changes
- Government cooling measures
- Shift in buyer preferences

**Next priority:** Re-run analysis with random train/test split to establish feature importance baseline, then explore time-series models for forecasting.
