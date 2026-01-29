"""
Anomaly Detection - Find Undervalued Properties

Identifies properties that are priced significantly below their predicted market value,
using the trained Random Forest model to estimate expected prices.

Methods:
1. Prediction-based: Compare actual vs predicted prices
2. Isolation Forest: Unsupervised anomaly detection
3. Local Outlier Factor: Density-based anomaly detection

Outputs:
- List of potentially undervalued properties
- Anomaly scores
- Visualizations
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.neighbors import LocalOutlierFactor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

import matplotlib.pyplot as plt
import seaborn as sns

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (14, 8)

# Paths
DATA_DIR = Path("data/analysis/market_segmentation")
OUTPUT_DIR = Path("data/analysis/anomaly_detection")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

print("="*80)
print("ANOMALY DETECTION - SINGAPORE HOUSING MARKET")
print("="*80)

# ============================================================================
# 1. LOAD DATA
# ============================================================================
print("\nLoading dataset...")

df = pd.read_parquet(DATA_DIR / "housing_unified_segmented.parquet")
print(f"Loaded {len(df):,} records")

# Filter for recent transactions (2021+) for actionable insights
df_recent = df[df['year'] >= 2021].copy()
print(f"Recent transactions (2021+): {len(df_recent):,} records")

# ============================================================================
# 2. PREPARE FEATURES
# ============================================================================
print("\nPreparing features...")

# Drop columns with excessive missingness
high_missing = [
    'Project Name', 'Street Name', 'Postal District',
    'Property Type', 'Market Segment'
]
df_recent = df_recent.drop(columns=high_missing, errors='ignore')

# Select features (same as feature importance analysis)
location_cols = [
    'dist_to_nearest_mrt', 'dist_to_nearest_hawker',
    'dist_to_nearest_supermarket', 'dist_to_nearest_park',
    'dist_to_nearest_preschool', 'dist_to_nearest_childcare',
    'mrt_within_500m', 'mrt_within_1km', 'mrt_within_2km',
    'hawker_within_500m', 'hawker_within_1km', 'hawker_within_2km',
    'supermarket_within_500m', 'supermarket_within_1km', 'supermarket_within_2km',
    'park_within_500m', 'park_within_1km', 'park_within_2km',
    'preschool_within_500m', 'preschool_within_1km', 'preschool_within_2km',
    'childcare_within_500m', 'childcare_within_1km', 'childcare_within_2km'
]

property_cols = ['floor_area_sqm', 'remaining_lease_months']

market_cols = [
    'transaction_count', 'volume_3m_avg', 'volume_12m_avg',
    'stratified_median_price'
]

temporal_cols = ['year', 'month']

categorical_cols = ['town', 'flat_type', 'flat_model', 'storey_range',
                   'market_tier', 'psm_tier', 'property_type', 'momentum_signal']

# Build feature list
feature_cols = []
for col_list in [location_cols, property_cols, market_cols, temporal_cols]:
    feature_cols.extend([c for c in col_list if c in df_recent.columns])

for col in categorical_cols:
    if col in df_recent.columns and col not in feature_cols:
        feature_cols.append(col)

# Remove non-feature columns
exclude_cols = ['price', 'price_psm', 'price_psf', 'rental_yield_pct',
               'mom_change_pct', 'yoy_change_pct', 'transaction_date',
               'month', 'planning_area', 'address', 'lat', 'lon',
               'lease_commence_date']

feature_cols = [c for c in feature_cols if c not in exclude_cols]

# Separate numeric and categorical
numeric_features = df_recent[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
categorical_features = df_recent[feature_cols].select_dtypes(include=['object', 'category']).columns.tolist()

print(f"  Numeric features: {len(numeric_features)}")
print(f"  Categorical features: {len(categorical_features)}")

# Remove rows with missing target or key features
df_recent = df_recent.dropna(subset=['price_psm'] + numeric_features[:5])
print(f"  After dropping missing values: {len(df_recent):,} records")

# Prepare X and y
X = df_recent[feature_cols].copy()
y = df_recent['price_psm'].copy()

# Remove year from features
X = X.drop(columns=['year'], errors='ignore')
numeric_features_clean = [f for f in numeric_features if f != 'year']

print(f"\nFinal dataset: {len(X):,} records, {len(X.columns)} features")

# ============================================================================
# 3. TRAIN RANDOM FOREST MODEL
# ============================================================================
print("\nTraining Random Forest model...")

# Create preprocessing pipeline
numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric_features_clean),
        ('cat', categorical_transformer, categorical_features)
    ]
)

# Create Random Forest pipeline
rf_pipeline = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('model', RandomForestRegressor(
        n_estimators=100,
        max_depth=15,
        min_samples_split=10,
        n_jobs=-1,
        random_state=42
    ))
])

# Train model
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

rf_pipeline.fit(X_train, y_train)

# Evaluate
train_r2 = rf_pipeline.score(X_train, y_train)
test_r2 = rf_pipeline.score(X_test, y_test)

print(f"  Train R²: {train_r2:.4f}")
print(f"  Test R²: {test_r2:.4f}")

# ============================================================================
# 4. METHOD 1: PREDICTION-BASED ANOMALIES
# ============================================================================
print("\n" + "="*80)
print("METHOD 1: PREDICTION-BASED ANOMALY DETECTION")
print("="*80)

# Predict prices for all data
df_recent['predicted_price_psm'] = rf_pipeline.predict(X)

# Calculate residuals (actual - predicted)
df_recent['residual'] = df_recent['price_psm'] - df_recent['predicted_price_psm']
df_recent['residual_pct'] = (df_recent['residual'] / df_recent['predicted_price_psm']) * 100

print(f"\nResidual Statistics:")
print(f"  Mean: ${df_recent['residual'].mean():.2f}/psm")
print(f"  Std: ${df_recent['residual'].std():.2f}/psm")
print(f"  Min: ${df_recent['residual'].min():.2f}/psm ({df_recent['residual_pct'].min():.1f}%)")
print(f"  Max: ${df_recent['residual'].max():.2f}/psm ({df_recent['residual_pct'].max():.1f}%)")

# Define undervalued properties (residual < -2 * std)
threshold = -2 * df_recent['residual'].std()
undervalued_pred = df_recent[df_recent['residual'] < threshold].copy()

print(f"\nUndervalued Properties (Prediction-based):")
print(f"  Threshold: < ${threshold:.2f}/psm")
print(f"  Count: {len(undervalued_pred)} properties")
print(f"  Percentage: {len(undervalued_pred)/len(df_recent)*100:.2f}%")

# Calculate savings (add to main dataframe first)
df_recent['potential_savings'] = df_recent['residual'] * df_recent['floor_area_sqm']
df_recent['potential_savings_pct'] = df_recent['residual_pct']

undervalued_pred['potential_savings'] = undervalued_pred['residual'] * undervalued_pred['floor_area_sqm']
undervalued_pred['potential_savings_pct'] = undervalued_pred['residual_pct']

print(f"\nPotential Savings:")
print(f"  Mean: ${undervalued_pred['potential_savings'].mean():,.0f}")
print(f"  Median: ${undervalued_pred['potential_savings'].median():,.0f}")
print(f"  Total: ${undervalued_pred['potential_savings'].sum():,.0f}")

# ============================================================================
# 5. METHOD 2: ISOLATION FOREST
# ============================================================================
print("\n" + "="*80)
print("METHOD 2: ISOLATION FOREST (UNSUPERVISED)")
print("="*80)

# Get preprocessed features
X_processed = rf_pipeline.named_steps['preprocessor'].transform(X)

# Fit Isolation Forest
iso_forest = IsolationForest(
    contamination=0.05,  # Expect 5% anomalies
    random_state=42,
    n_jobs=-1
)

df_recent['iso_anomaly_score'] = iso_forest.fit_predict(X_processed)
df_recent['iso_anomaly'] = df_recent['iso_anomaly_score'].apply(lambda x: 'Anomaly' if x == -1 else 'Normal')

# Also get anomaly scores (lower = more anomalous)
df_recent['iso_score'] = iso_forest.score_samples(X_processed)

anomalies_iso = df_recent[df_recent['iso_anomaly'] == 'Anomaly']
print(f"\nAnomalies detected: {len(anomalies_iso)} ({len(anomalies_iso)/len(df_recent)*100:.1f}%)")

# ============================================================================
# 6. METHOD 3: LOCAL OUTLIER FACTOR
# ============================================================================
print("\n" + "="*80)
print("METHOD 3: LOCAL OUTLIER FACTOR (DENSITY-BASED)")
print("="*80)

# Fit LOF (use smaller sample for efficiency)
sample_size = min(50000, len(X_processed))
lof = LocalOutlierFactor(
    n_neighbors=20,
    contamination=0.05,
    n_jobs=-1
)

# Use positional indices to sample
np.random.seed(42)
sample_indices = np.random.choice(len(X_processed), size=sample_size, replace=False)
X_sample = X_processed[sample_indices]

# Create a sampled dataframe with matching indices
df_recent_sample = df_recent.iloc[sample_indices].copy()
df_recent_sample['lof_anomaly_score'] = lof.fit_predict(X_sample)
df_recent_sample['lof_anomaly'] = df_recent_sample['lof_anomaly_score'].apply(lambda x: 'Anomaly' if x == -1 else 'Normal')

# Merge back
df_recent = df_recent.join(df_recent_sample[['lof_anomaly', 'lof_anomaly_score']], how='left')

anomalies_lof = df_recent[df_recent['lof_anomaly'] == 'Anomaly']
print(f"\nAnomalies detected: {len(anomalies_lof)} ({len(anomalies_lof)/len(df_recent)*100:.1f}%)")

# ============================================================================
# 7. COMBINE METHODS & IDENTIFY TOP OPPORTUNITIES
# ============================================================================
print("\n" + "="*80)
print("COMBINING METHODS - TOP INVESTMENT OPPORTUNITIES")
print("="*80)

# Create composite anomaly score
# Anomaly if: Undervalued by prediction OR detected by 2+ methods
df_recent['anomaly_methods'] = 0
df_recent.loc[df_recent['residual'] < threshold, 'anomaly_methods'] += 1  # Prediction-based
df_recent.loc[df_recent['iso_anomaly'] == 'Anomaly', 'anomaly_methods'] += 1  # Isolation Forest
df_recent.loc[df_recent['lof_anomaly'] == 'Anomaly', 'anomaly_methods'] += 1  # LOF

# Top opportunities: Undervalued by prediction AND detected by another method
top_opportunities = df_recent[
    (df_recent['residual'] < threshold) &
    (df_recent['anomaly_methods'] >= 2)
].copy()

print(f"\nTop Investment Opportunities (Multiple Methods):")
print(f"  Count: {len(top_opportunities)} properties")
print(f"  Criteria: Undervalued by prediction AND detected by 2+ methods")

if len(top_opportunities) > 0:
    print(f"\nTop 20 Opportunities:")

    # Select relevant columns for display
    display_cols = [
        'address', 'town', 'flat_type', 'floor_area_sqm',
        'price_psm', 'predicted_price_psm', 'residual', 'residual_pct',
        'potential_savings', 'potential_savings_pct', 'year', 'month'
    ]

    # Sort by potential savings
    top_opportunities_sorted = top_opportunities.sort_values('potential_savings', ascending=False)

    # Format for display
    display_df = top_opportunities_sorted.head(20)[display_cols].copy()
    display_df['potential_savings'] = display_df['potential_savings'].apply(lambda x: f"${x:,.0f}")
    display_df['potential_savings_pct'] = display_df['potential_savings_pct'].apply(lambda x: f"{x:.1f}%")
    display_df['price_psm'] = display_df['price_psm'].apply(lambda x: f"${x:,.0f}")
    display_df['predicted_price_psm'] = display_df['predicted_price_psm'].apply(lambda x: f"${x:,.0f}")
    display_df['residual'] = display_df['residual'].apply(lambda x: f"${x:.0f}")

    print(display_df.to_string(index=False))

# ============================================================================
# 8. VISUALIZATIONS
# ============================================================================
print("\n" + "="*80)
print("GENERATING VISUALIZATIONS")
print("="*80)

# Visualization 1: Residual Distribution
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Histogram of residuals
axes[0, 0].hist(df_recent['residual'], bins=50, color='steelblue', edgecolor='black', alpha=0.7)
axes[0, 0].axvline(x=threshold, color='red', linestyle='--', linewidth=2, label=f'Undervalued Threshold (${threshold:.0f})')
axes[0, 0].axvline(x=0, color='black', linestyle='-', linewidth=1, label='Fair Value')
axes[0, 0].set_xlabel('Price Residual ($/psm)', fontsize=12, fontweight='bold')
axes[0, 0].set_ylabel('Frequency', fontsize=12, fontweight='bold')
axes[0, 0].set_title('Distribution of Price Residuals', fontsize=14, fontweight='bold')
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# Scatter: Actual vs Predicted
axes[0, 1].scatter(df_recent['predicted_price_psm'], df_recent['price_psm'],
                   alpha=0.3, s=10, color='steelblue', label='Normal')
axes[0, 1].scatter(undervalued_pred['predicted_price_psm'], undervalued_pred['price_psm'],
                   alpha=0.6, s=20, color='red', label='Undervalued')
axes[0, 1].plot([df_recent['price_psm'].min(), df_recent['price_psm'].max()],
                [df_recent['price_psm'].min(), df_recent['price_psm'].max()],
                'k--', linewidth=1, label='Perfect Prediction')
axes[0, 1].set_xlabel('Predicted Price ($/psm)', fontsize=12, fontweight='bold')
axes[0, 1].set_ylabel('Actual Price ($/psm)', fontsize=12, fontweight='bold')
axes[0, 1].set_title('Actual vs Predicted Prices', fontsize=14, fontweight='bold')
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

# Residual vs Predicted
axes[1, 0].scatter(df_recent['predicted_price_psm'], df_recent['residual'],
                   alpha=0.3, s=10, color='steelblue', label='Normal')
axes[1, 0].scatter(undervalued_pred['predicted_price_psm'], undervalued_pred['residual'],
                   alpha=0.6, s=20, color='red', label='Undervalued')
axes[1, 0].axhline(y=0, color='black', linestyle='-', linewidth=1)
axes[1, 0].axhline(y=threshold, color='red', linestyle='--', linewidth=2)
axes[1, 0].set_xlabel('Predicted Price ($/psm)', fontsize=12, fontweight='bold')
axes[1, 0].set_ylabel('Residual ($/psm)', fontsize=12, fontweight='bold')
axes[1, 0].set_title('Residual Plot (Homoscedasticity Check)', fontsize=14, fontweight='bold')
axes[1, 0].legend()
axes[1, 0].grid(True, alpha=0.3)

# Residual % by Town
town_residuals = df_recent.groupby('town')['residual_pct'].agg(['mean', 'count'])
town_residuals = town_residuals[town_residuals['count'] >= 100]  # At least 100 transactions
town_residuals = town_residuals.sort_values('mean', ascending=True).head(15)

axes[1, 1].barh(range(len(town_residuals)), town_residuals['mean'], color='coral')
axes[1, 1].set_yticks(range(len(town_residuals)))
axes[1, 1].set_yticklabels(town_residuals.index)
axes[1, 1].set_xlabel('Average Residual (%)', fontsize=12, fontweight='bold')
axes[1, 1].set_title('Towns with Most Undervalued Properties (Average)', fontsize=14, fontweight='bold')
axes[1, 1].axvline(x=0, color='black', linestyle='-', linewidth=1)
axes[1, 1].grid(True, alpha=0.3, axis='x')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'anomaly_detection_overview.png', dpi=300, bbox_inches='tight')
plt.show()

print("  Saved: anomaly_detection_overview.png")

# Visualization 2: Top Opportunities Map
if len(top_opportunities) > 0:
    fig, ax = plt.subplots(figsize=(14, 8))

    top_20 = top_opportunities_sorted.head(20)

    ax.barh(range(len(top_20)), top_20['potential_savings'].values, color='steelblue')
    ax.set_yticks(range(len(top_20)))
    ax.set_yticklabels([f"{row['town']} - {row['flat_type']}" for _, row in top_20.iterrows()], fontsize=9)
    ax.set_xlabel('Potential Savings ($)', fontsize=12, fontweight='bold')
    ax.set_title('Top 20 Undervalued Properties by Potential Savings', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')

    # Add value labels
    for i, (_, row) in enumerate(top_20.iterrows()):
        ax.text(row['potential_savings'], i, f" ${row['potential_savings']:,.0f}",
                va='center', fontsize=8)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'top_opportunities.png', dpi=300, bbox_inches='tight')
    plt.show()

    print("  Saved: top_opportunities.png")

# ============================================================================
# 9. EXPORT RESULTS
# ============================================================================
print("\n" + "="*80)
print("EXPORTING RESULTS")
print("="*80)

# Export all anomalies
all_anomalies = df_recent[df_recent['anomaly_methods'] >= 1].copy()

export_cols = [
    'address', 'town', 'flat_type', 'flat_model', 'floor_area_sqm',
    'price_psm', 'predicted_price_psm', 'residual', 'residual_pct',
    'potential_savings', 'potential_savings_pct',
    'iso_anomaly', 'lof_anomaly', 'anomaly_methods',
    'year', 'month'
]

all_anomalies[export_cols].to_csv(
    OUTPUT_DIR / 'all_anomalies.csv',
    index=False
)
print(f"  Saved: all_anomalies.csv ({len(all_anomalies)} properties)")

# Export top opportunities
if len(top_opportunities) > 0:
    top_opportunities[export_cols].to_csv(
        OUTPUT_DIR / 'top_opportunities.csv',
        index=False
    )
    print(f"  Saved: top_opportunities.csv ({len(top_opportunities)} properties)")

# Export summary statistics
summary_stats = {
    'total_properties': len(df_recent),
    'undervalued_by_prediction': len(undervalued_pred),
    'isolation_forest_anomalies': len(anomalies_iso),
    'lof_anomalies': len(anomalies_lof),
    'top_opportunities_multi_method': len(top_opportunities),
    'mean_residual': df_recent['residual'].mean(),
    'std_residual': df_recent['residual'].std(),
    'threshold_undervalued': threshold,
    'total_potential_savings': undervalued_pred['potential_savings'].sum()
}

summary_df = pd.DataFrame([summary_stats])
summary_df.to_csv(OUTPUT_DIR / 'anomaly_summary.csv', index=False)
print(f"  Saved: anomaly_summary.csv")

print(f"\n{summary_stats}")

print("\n" + "="*80)
print("ANOMALY DETECTION COMPLETE")
print("="*80)
print(f"\nResults saved to: {OUTPUT_DIR}")
print("\nKey Findings:")
print(f"  • {len(undervalued_pred)} properties undervalued by prediction")
print(f"  • {len(top_opportunities)} top opportunities (multiple methods)")
print(f"  • ${undervalued_pred['potential_savings'].sum():,.0f} total potential savings")
