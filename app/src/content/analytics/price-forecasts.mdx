---
title: Price Forecasts
category: "market-analysis"
description: Which price forecasts are decision-useful, which are too noisy, and how to interpret segment-level prediction quality
status: published
date: 2026-02-17
personas:
  - investor
  - first-time-buyer
  - upgrader
readingTime: "8 min read"
technicalLevel: intermediate
---

# Price Appreciation Prediction

**Analysis Date**: 2026-02-17  
**Data Period**: 2021-2026  
**Coverage**: HDB, condo, and EC segments

## Key Takeaways

### The clearest finding

Forecast quality depends far more on **market segment** than on having a single “best model.” HDB, EC, and mass-market condos are reasonably forecastable; luxury condos are not forecastable with enough precision for valuation use.

### What this means in practice

- **HDB buyers and upgraders** can use forecasts as a timing aid.
- **Mass-market condo buyers** can use them as directional support, but should still expect wider error bands.
- **Luxury condo buyers and investors** should treat forecast outputs as weak signals, not pricing anchors.

## Core Findings

### 1. Reliability differs sharply across segments

<div data-chart-metadata="true" data-chart="comparison" data-chart-title="Forecast reliability by property segment" data-chart-columns="Accuracy (R²),95% CI Width,Directional Acc"></div>

| Segment | Accuracy (R²) | 95% CI Width | Directional Acc | Practical read |
|---------|---------------|--------------|-----------------|----------------|
| HDB flats | 79.8% | ±18.58% | 99.4% | Strong |
| Executive Condos | 98.5% | ±50.15% | 97.1% | Strong but wider uncertainty |
| Mass Market Condos | 85.6% | ±40.48% | 96.4% | Useful with caution |
| Mid Market Condos | 72.6% | ±1877.88% | 94.2% | Direction only |
| Luxury Condos | 30.1% | ±1076.24% | 92.3% | Magnitude unusable |

### 2. Direction is often easier to predict than magnitude

The directional hit rate remains high even when confidence intervals are too wide for precise action.

**Impact**

- If the question is “up or down?”, some segments are usable.
- If the question is “how much?”, only the stronger segments deserve much trust.

### 3. Momentum is the dominant forecast driver

| Segment | Top feature | Importance |
|--------|-------------|------------|
| HDB | 2-year YoY appreciation | 51.14% |
| Mass market condo | 2-year YoY appreciation | 65.50% |

**Impact**

- Short- to medium-term price forecasting is still driven mainly by recent trend persistence.
- Amenities and local features matter, but they are not the main short-horizon forecasting signal.

## How To Use These Forecasts

### For investors

- Use HDB and mass-market condo forecasts to support entry and exit timing.
- Treat wide confidence intervals as a stop signal, not a footnote.
- Ignore precise appreciation percentages in luxury segments.

### For first-time buyers

- HDB forecasts can help with timing if your move window is flexible.
- Avoid making affordability decisions based on aggressive upside forecasts.

### For upgraders

- A forecast is most useful when both the sell-side and buy-side segments are forecastable.
- If upgrading into a noisy condo tier, do not assume your next purchase has the same predictability as your current HDB.

## Technical Appendix

### Data Used

- **Primary input**: `data/parquets/L3/housing_unified.parquet` (2021-2026)
- **Train/test split**: `L5_price_appreciation_train.parquet` / `L5_price_appreciation_test.parquet`
- **Forecast horizon**: 6 months (ARIMA), annual (XGBoost ensemble)
- **Feature selection**: numeric only, max 20% missing values allowed

### Methodology

- **XGBoost models** trained per property type (HDB, Condo, EC) in `scripts/analytics/price_appreciation_modeling/train_by_property_type.py`
  - Parameters: n_estimators=100, max_depth=6, learning_rate=0.1, subsample=0.8
- **Target variable**: `yoy_change_pct` (year-over-year appreciation)
- **Smart ensemble**: stacked model combining segment-specific predictions via `scripts/analytics/price_appreciation_modeling/create_smart_ensemble.py`
- **Confidence intervals**: calibrated per segment using residual distribution in `scripts/analytics/price_appreciation_modeling/generate_confidence_intervals.py`
- **ARIMA(1,1,1)** for time-series forecasting per planning area via `scripts/analytics/analysis/market/forecast_prices.py`
- **Condo sub-segmentation**: mass market, mid market, luxury in `scripts/analytics/price_appreciation_modeling/train_condo_by_segment.py`

### Technical Findings

| Segment | R² | Directional Accuracy | 95% CI Width |
|---------|-----|---------------------|--------------|
| HDB | 79.8% | 99.4% | ±18.58% |
| Executive Condos | 98.5% | 97.1% | ±50.15% |
| Mass Market Condos | 85.6% | 96.4% | ±40.48% |
| Mid Market Condos | 72.6% | 94.2% | ±1877.88% |
| Luxury Condos | 30.1% | 92.3% | ±1076.24% |

- **Top feature**: 2-year YoY appreciation (51.14% importance for HDB, 65.50% for mass-market condo)
- **Ensemble accuracy**: 74% vs 47% for a unified one-size-fits-all model
- **ARIMA**: 20 planning areas with ≥12 months of data, 6-month forecast horizon

### Conclusion

Segment-specific modeling dramatically outperforms unified approaches (74% vs 47% accuracy). HDB and EC segments are the most forecastable; luxury condos are essentially unpredictable in magnitude (R²=30.1%, CI width ±1076%). Momentum (recent 2-year appreciation) dominates feature importance, which means these models are vulnerable to regime changes and policy shocks. High directional accuracy can coexist with impractically wide error bands, especially in mid/luxury condo segments. Key limitations: momentum-heavy models assume trend persistence, and the luxury segment lacks sufficient signal for reliable magnitude forecasts.

### Scripts

- `scripts/analytics/analysis/market/forecast_prices.py` — ARIMA(1,1,1) per planning area
- `scripts/analytics/price_appreciation_modeling/train_by_property_type.py` — Segmented XGBoost
- `scripts/analytics/price_appreciation_modeling/create_smart_ensemble.py` — Ensemble stacking
- `scripts/analytics/price_appreciation_modeling/generate_confidence_intervals.py` — CI calibration
