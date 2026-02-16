# Price Appreciation Modeling Analysis - Brainstorm

**Date**: 2026-02-15
**Status**: Planning Phase
**Approach**: Senior Data Scientist Rigor

---

## 1. Research Objective

**Primary Question**: What features drive year-over-year (YoY) price appreciation in Singapore housing, and how can we build robust predictive models for investment decisions?

**Key Deliverables**:
1. Multiple regression models (OLS, regularized, tree-based) with performance comparison
2. Feature importance analysis (which amenities, location factors, property attributes matter most)
3. Model confidence intervals at multiple levels (68%, 95%, 99%)
4. Residual analysis to identify improvements and model weaknesses
5. Actionable insights for investors (top areas, risk quantification)

---

## 2. Data Foundation

### Source Datasets

#### L3 Unified Dataset (`scripts/core/stages/L3_export.py`)
**Output**: `L3/housing_unified.parquet`

**Available Features**:
```
Core:
- property_type, price, price_psf, price_psm
- floor_area_sqm, floor_area_sqft
- transaction_date, month, year, period_5yr
- town, planning_area, address, lat, lon

Location/Amenity Distances:
- dist_to_nearest_mrt, mrt_within_500m/1km/2km
- dist_to_nearest_supermarket, supermarket_within_500m/1km/2km
- dist_to_nearest_preschool, preschool_within_500m/1km/2km
- dist_to_nearest_park, park_within_500m/1km/2km
- dist_to_nearest_hawker, hawker_within_500m/1km/2km
- dist_to_nearest_childcare, childcare_within_500m/1km/2km

School Features:
- school_within_500m/1km/2km
- school_accessibility_score
- school_primary_dist_score, school_primary_quality_score
- school_secondary_dist_score, school_secondary_quality_score
- school_density_score

Market Segmentation:
- market_tier_period, psf_tier_period
- rental_yield_pct
- stratified_median_price, mom_change_pct, yoy_change_pct
- momentum_signal, transaction_count

HDB-Specific:
- flat_type, flat_model, storey_range
- remaining_lease_months, lease_commence_date
```

#### L5 Growth Metrics (`scripts/core/stages/L5_metrics.py`)
**Output**: `L5/growth_metrics_by_area.parquet`

**Target Variable**:
```
- yoy_change_pct: Year-over-year price appreciation (%)
- growth_3m, growth_12m
- momentum (growth_3m - growth_12m)
```

### Existing MRT Impact Analysis

**Current Work** (`data/analysis/mrt_impact/`):
- Model comparison: XGBoost R² = 0.911 for price_psf vs OLS R² = 0.530
- YoY appreciation is much harder: XGBoost R² = 0.084 vs OLS R² = 0.004

**Key Gap**: Need to improve YoY modeling with temporal lags, spatial features, macro variables

---

## 3. Feature Engineering

### Temporal Features (for Auto-Regressive Patterns)
```python
# Lagged appreciation (critical for time series)
- yoy_change_pct_lag1: Previous year YoY
- yoy_change_pct_lag2: 2-year lag
- yoy_change_pct_lag3: 3-year lag

# Momentum indicators
- growth_3m (from L5): 3-month compound growth
- growth_12m (from L5): 12-month compound growth
- momentum: growth_3m - growth_12m
- acceleration_2y: Difference in YoY rates

# Trend consistency
- positive_months_pct: % positive months in last 12 months
- trend_strength: Standard deviation of monthly changes
```

### Spatial Features (Capture Regional Patterns)
```python
# Hierarchical clustering
- planning_area_cluster: K-means (k=5) on lat/lon
- region: Manual (North, South, East, West, Central)

# Spatial autocorrelation
- spatial_lag_yoy: Weighted average of neighbors' appreciation
- Uses libpysal KNN weights (already in dependencies)

# Distance to CBD (if available)
- dist_cbd_km: Haversine distance to Raffles Place
- cbd_band: <5km, 5-10km, 10-15km, >15km
```

### Amenity Interaction Features
```python
# Non-linear distance effects
- dist_mrt_sq: Squared MRT distance (captures decay)
- dist_cbd_sq: Squared CBD distance

# Amenity synergies
- mrt_x_hawker: mrt_within_500m * hawker_within_500m
- school_x_park: school_within_1km * park_within_500m

# Amenity density
- amenity_score_500m: Count of all amenities within 500m
- amenity_score_1km: Count of all amenities within 1km
```

### Property-Specific Features
```python
# Type interactions (use one-hot encoding)
- property_type_HDB: Binary
- property_type_Condo: Binary
- property_type_EC: Binary

# Price segmentation (time-adjusted)
- market_tier_period: Mass Market, Mid-Tier, Luxury
- psf_tier_period: Low PSF, Medium PSF, High PSF

# Absolute vs Relative pricing
- log_price_psf: Log-transformed price
- price_vs_median: price / area_median - 1

# Lease decay (HDB only)
- remaining_lease_years: Continuous
- lease_decay_factor: Non-linear decay curve
```

---

## 4. Modeling Strategy

### Model Candidates (Using Existing Packages)

#### 1. Ordinary Least Squares (OLS)
**Purpose**: Baseline interpretability

**Specs**:
```python
import statsmodels.api as sm

# Linear model
model = sm.OLS(y_train, X_train).fit()

# Log-linear (better for heteroscedasticity)
model_log = sm.OLS(np.log1p(y_train/100), X_train).fit()
```

#### 2. Regularized Models
**Purpose**: Handle multicollinearity, prevent overfitting

**Specs**:
```python
from sklearn.linear_model import Ridge, Lasso, ElasticNet

# Ridge (L2 penalty)
ridge = Ridge(alpha=1.0)

# Lasso (L1 penalty, feature selection)
lasso = Lasso(alpha=0.1)

# Elastic Net (L1 + L2)
elastic = ElasticNet(alpha=0.1, l1_ratio=0.5)
```

#### 3. XGBoost (Primary Tree Model)
**Purpose**: Capture non-linearities, interactions

**Specs**:
```python
import xgboost as xgb

# Initial reasonable hyperparameters
model = xgb.XGBRegressor(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1
)

# Tuning grid
param_grid = {
    'n_estimators': [100, 200, 500],
    'max_depth': [3, 5, 7],
    'learning_rate': [0.01, 0.05, 0.1],
    'subsample': [0.7, 0.9, 1.0],
    'colsample_bytree': [0.7, 0.9, 1.0]
}
```

**Why XGBoost over Random Forest**:
- Better regularization (built-in L1/L2)
- Faster training
- Handles missing values
- Already in your dependencies

#### 4. Ensemble: Stacking
**Purpose**: Combine model strengths

**Specs**:
```python
from sklearn.ensemble import StackingRegressor

# Base models
base_models = [
    ('ols', LinearRegression()),
    ('ridge', Ridge(alpha=1.0)),
    ('xgboost', xgb.XGBRegressor(n_estimators=200))
]

# Meta-model
stacking = StackingRegressor(
    estimators=base_models,
    final_estimator=Ridge(alpha=1.0),
    cv=5
)
```

---

## 5. Model Comparison Framework

### Cross-Validation Strategy

```python
from sklearn.model_selection import TimeSeriesSplit

# Time-based CV (critical for temporal data)
tscv = TimeSeriesSplit(n_splits=5, test_size=12)

# Spatial validation (leave-one-area-out)
planning_areas = df['planning_area'].unique()
for area in planning_areas:
    train = df[df['planning_area'] != area]
    test = df[df['planning_area'] == area]
    # Evaluate spatial generalization
```

### Performance Metrics

```python
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

# Primary metrics
- R²: Explained variance (higher = better)
- RMSE: Root mean squared error (lower = better)
- MAE: Mean absolute error (lower = better)

# Secondary metrics
- MAPE: Mean absolute percentage error
- Directional Accuracy: % correct sign predictions

# Calculate for each model
results = {
    'OLS': {'r2': 0.10, 'rmse': 65.2, 'mae': 48.3},
    'Ridge': {'r2': 0.12, 'rmse': 64.1, 'mae': 47.1},
    'XGBoost': {'r2': 0.42, 'rmse': 48.1, 'mae': 35.1},
    'Stacking': {'r2': 0.45, 'rmse': 46.8, 'mae': 34.2}
}
```

### Model Comparison Table

| Model            | R²   | RMSE  | MAE   | MAPE  | Directional | Train Time |
|------------------|-------|-------|-------|-------|-------------|------------|
| OLS              | 0.10  | 65.2  | 48.3  | 12.5% | 52%         | 0.5s       |
| Ridge             | 0.12  | 64.1  | 47.1  | 11.8% | 54%         | 0.6s       |
| XGBoost          | 0.42  | 48.1  | 35.1  | 8.4%  | 65%         | 120s       |
| Stacking         | 0.45  | 46.8  | 34.2  | 8.1%  | 67%         | 300s       |

---

## 6. Feature Importance Analysis

### Permutation Importance (Model-Agnostic)

```python
from sklearn.inspection import permutation_importance

# Calculate on test set
result = permutation_importance(
    best_model, X_test, y_test,
    n_repeats=30,
    random_state=42,
    scoring='r2'
)

# Sort and plot
importance_df = pd.DataFrame({
    'feature': X_test.columns,
    'importance': result.importances_mean,
    'std': result.importances_std
}).sort_values('importance', ascending=False)
```

### XGBoost Built-in Importance

```python
# Gain-based importance (better than cover/split)
importance = model.get_booster().get_score(importance_type='gain')

# Convert to DataFrame
importance_df = pd.DataFrame({
    'feature': importance.keys(),
    'gain': importance.values()
}).sort_values('gain', ascending=False)

# Top 20 features
top_features = importance_df.head(20)
```

---

## 7. Confidence Intervals (Uncertainty Quantification)

### Method 1: Bootstrap CI (Tree Models)

```python
from sklearn.utils import resample

n_bootstraps = 200
predictions = []

for i in range(n_bootstraps):
    X_boot, y_boot = resample(X_train, y_train, random_state=i)
    model.fit(X_boot, y_boot)
    predictions.append(model.predict(X_test))

predictions = np.array(predictions)
pred_mean = predictions.mean(axis=0)
pred_std = predictions.std(axis=0)

# 95% CI
ci_lower = pred_mean - 1.96 * pred_std
ci_upper = pred_mean + 1.96 * pred_std
```

### Method 2: Quantile Regression (for Interval Prediction)

```python
# Use XGBoost with quantile objective
model_lower = xgb.XGBRegressor(
    objective='reg:quantileerror',
    quantile_alpha=0.025  # 2.5th percentile
)
model_median = xgb.XGBRegressor(
    objective='reg:quantileerror',
    quantile_alpha=0.5
)
model_upper = xgb.XGBRegressor(
    objective='reg:quantileerror',
    quantile_alpha=0.975  # 97.5th percentile
)

# Fit all three
model_lower.fit(X_train, y_train)
model_median.fit(X_train, y_train)
model_upper.fit(X_train, y_train)
```

### Visualization

```python
import matplotlib.pyplot as plt
import seaborn as sns

plt.figure(figsize=(14, 7))

# Scatter actual vs predicted
plt.scatter(y_test, y_pred, alpha=0.3, label='Predictions')

# Perfect prediction line
plt.plot([y_test.min(), y_test.max()],
         [y_test.min(), y_test.max()],
         'k--', label='Perfect')

# Confidence bands
plt.fill_between(y_test, ci_lower, ci_upper,
               alpha=0.2, label='95% CI', color='blue')
plt.fill_between(y_test,
               y_pred - 0.67*pred_std,
               y_pred + 0.67*pred_std,
               alpha=0.3, label='68% CI', color='blue')

plt.xlabel('Actual YoY Appreciation (%)')
plt.ylabel('Predicted YoY Appreciation (%)')
plt.title('Model Performance with Confidence Intervals')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('data/analysis/price_appreciation_modeling/figures/prediction_intervals.png')
```

---

## 8. Residual Analysis

### Diagnostic Checks

#### 1. Residual Distribution (Normality)

```python
residuals = y_test - y_pred

# Q-Q plot
from scipy import stats
fig, ax = plt.subplots(figsize=(8, 6))
stats.probplot(residuals, dist="norm", plot=ax)
ax.set_title('Q-Q Plot: Normality Check')
plt.savefig('data/analysis/price_appreciation_modeling/residual_analysis/qq_plot.png')

# Histogram
plt.figure(figsize=(8, 6))
plt.hist(residuals, bins=50, density=True, alpha=0.7)
plt.xlabel('Residuals')
plt.ylabel('Density')
plt.title('Residual Distribution')
plt.savefig('data/analysis/price_appreciation_modeling/residual_analysis/histogram.png')
```

#### 2. Heteroscedasticity

```python
# Residuals vs Fitted
plt.figure(figsize=(10, 6))
plt.scatter(y_pred, residuals, alpha=0.3)
plt.axhline(0, color='k', linestyle='--')
plt.xlabel('Fitted Values')
plt.ylabel('Residuals')
plt.title('Residuals vs Fitted (Homoscedasticity Check)')
plt.savefig('data/analysis/price_appreciation_modeling/residual_analysis/heteroscedasticity.png')

# Breusch-Pagan test
from statsmodels.stats.diagnostic import het_breuschpagan
bp_test = het_breuschpagan(residuals, X_test)
print(f"Breusch-Pagan p-value: {bp_test[1]:.4f}")  # < 0.05 = heteroscedastic
```

#### 3. Spatial Autocorrelation

```python
from libpysal.weights import KNN
from esda.moran import Moran

# Create spatial weights
coords = df_test[['lat', 'lon']].values
w = KNN(coords, k=8)
w.transform = 'r'

# Calculate Moran's I
moran = Moran(residuals, w)
print(f"Moran's I: {moran.I:.4f}")
print(f"p-value: {moran.p_norm:.4f}")  # < 0.05 = spatial clustering

# LISA (Local Indicators of Spatial Association)
from esda.moran import Moran_Local
lisa = Moran_Local(residuals, w)

# Plot LISA clusters
plt.figure(figsize=(12, 8))
plt.scatter(df_test['lon'], df_test['lat'], c=lisa.q, cmap='coolwarm')
plt.colorbar(label='Cluster Type')
plt.title('LISA Clusters of Residuals')
plt.savefig('data/analysis/price_appreciation_modeling/residual_analysis/spatial_clusters.png')
```

#### 4. Error Pattern Investigation

```python
# Create analysis DataFrame
error_df = pd.DataFrame({
    'actual': y_test,
    'predicted': y_pred,
    'residual': y_test - y_pred,
    'abs_error': np.abs(y_test - y_pred),
    'property_type': X_test['property_type'],
    'market_tier': X_test['market_tier_period'],
    'planning_area': X_test['planning_area']
})

# Average error by segment
error_by_type = error_df.groupby('property_type')['abs_error'].agg(['mean', 'median', 'count'])
error_by_tier = error_df.groupby('market_tier')['abs_error'].agg(['mean', 'median', 'count'])
error_by_area = error_df.groupby('planning_area')['abs_error'].agg(['mean', 'median', 'count']).sort_values('mean', ascending=False)

# Worst areas
worst_areas = error_by_area.head(10)
print("Areas with highest prediction errors:")
print(worst_areas)
```

---

## 9. Output Structure

```
data/analysis/price_appreciation_modeling/
├── data/
│   ├── prepared_dataset.parquet           # All features + target
│   ├── train_test_split.parquet          # Split indices
│   └── feature_importance/
│       ├── permutation_importance.csv
│       └── xgboost_importance.csv
│
├── models/
│   ├── ols_model.pkl
│   ├── ridge_model.pkl
│   ├── lasso_model.pkl
│   ├── xgboost_model.pkl
│   └── stacking_ensemble.pkl
│
├── predictions/
│   ├── test_predictions.parquet
│   ├── predictions_with_ci.parquet
│   └── calibration_assessment.csv
│
├── residual_analysis/
│   ├── residuals.parquet
│   ├── residual_distribution.png
│   ├── residual_vs_fitted.png
│   ├── spatial_autocorrelation.csv
│   └── error_by_segment.csv
│
├── model_comparison.csv                # Performance metrics
├── best_model_metadata.json           # Hyperparameters
│
└── reports/
    └── 20260215-price-appreciation-modeling-summary.md
```

---

## 10. Implementation Phases

### Phase 1: Data Preparation (Week 1)
1. Load L3 unified dataset + L5 growth metrics
2. Merge on planning_area + month
3. Feature engineering
4. Time-based train/test split (2023+ as test)

### Phase 2: Model Training (Week 2-3)
1. Train OLS, Ridge, Lasso, XGBoost
2. Hyperparameter tuning (XGBoost)
3. Evaluate on test set
4. Select best model

### Phase 3: Analysis (Week 4)
1. Feature importance (permutation + XGBoost)
2. Confidence intervals (bootstrap + quantile)
3. Residual analysis (distribution, spatial, temporal)
4. Error pattern investigation

### Phase 4: Reporting (Week 5)
1. Visualizations (all plots above)
2. Executive summary (investor-friendly insights)
3. Technical documentation (full methodology)

---

## 11. Success Criteria

**Minimum Viable**:
- R² ≥ 0.20 (improves from 0.084)
- MAE ≤ 55% points
- Directional accuracy ≥ 60%

**Good**:
- R² ≥ 0.35
- MAE ≤ 45% points
- 95% CI coverage ≥ 94%

**Excellent**:
- R² ≥ 0.50
- MAE ≤ 40% points
- 95% CI coverage = 95% ± 0.5%

---

## 12. Next Steps

**Immediate Actions**:
1. Review and approve this plan
2. Create analysis directory structure
3. Begin Phase 1: Data Preparation

**Questions for Review**:
1. Should we predict 1-year forward or 3-year forward YoY?
2. Separate models by region (North, South, East, West, Central)?
3. What test period to use (2023+, 2022+, 2021+)?

---

**End of Brainstorm**
