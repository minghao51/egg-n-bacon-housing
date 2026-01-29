#!/usr/bin/env python3
"""Quick grid analysis and distance stratification for amenity impact."""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config import Config

OUTPUT_DIR = Config.DATA_DIR / "analysis" / "amenity_impact"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

print("="*60)
print("QUICK AMENITY GRID ANALYSIS")
print("="*60)

print("\nLoading L3 unified dataset...")
df = pd.read_parquet(Config.PARQUETS_DIR / "L3" / "housing_unified.parquet")
print(f"Loaded {len(df):,} records")

df = df.dropna(subset=['price_psm', 'dist_to_nearest_mrt', 'lat', 'lon'])

print("\n=== MRT DISTANCE STRATIFICATION ===")
dist_bands = [0, 200, 400, 600, 800, 1000, 1500, 2000, 3000]
labels = ['0-200m', '200-400m', '400-600m', '600-800m', '800-1000m',
          '1000-1500m', '1500-2000m', '2000m+']

df = df.copy()
df['dist_band'] = pd.cut(
    df['dist_to_nearest_mrt'],
    bins=dist_bands,
    labels=labels,
    include_lowest=True
)

band_stats = df.groupby('dist_band').agg({
    'price_psm': ['count', 'median', 'mean', 'std'],
    'dist_to_nearest_mrt': ['min', 'max', 'mean']
}).round(2)

band_stats.columns = ['_'.join(col).strip() for col in band_stats.columns.values]
band_stats = band_stats.reset_index()

print("\nPrice PSM by MRT distance band:")
for _, row in band_stats.iterrows():
    if row['price_psm_count'] > 0:
        print(f"  {row['dist_band']}: n={row['price_psm_count']:,}, "
              f"median=${row['price_psm_median']:,.0f}/psm")

band_stats.to_csv(OUTPUT_DIR / 'mrt_distance_stratification.csv', index=False)
print(f"\nSaved: {OUTPUT_DIR / 'mrt_distance_stratification.csv'}")

print("\n=== GRID ANALYSIS (500m x 500m) ===")

meters_per_degree_lat = 111320
meters_per_degree_lon = 111320 * np.cos(np.radians(1))

df['grid_lat'] = (df['lat'] * meters_per_degree_lat / 500).astype(int)
df['grid_lon'] = (df['lon'] * meters_per_degree_lon / 500).astype(int)
df['grid_id'] = df['grid_lat'].astype(str) + '_' + df['grid_lon'].astype(str)

grid_counts = df['grid_id'].value_counts()
valid_grids = grid_counts[grid_counts >= 10].index
df_grid = df[df['grid_id'].isin(valid_grids)]

print(f"Created {df_grid['grid_id'].nunique():,} grids with 10+ transactions")

amenity_features = [
    'dist_to_nearest_mrt', 'mrt_within_500m', 'mrt_within_1km', 'mrt_within_2km',
    'dist_to_nearest_hawker', 'dist_to_nearest_supermarket', 'dist_to_nearest_park'
]
property_features = ['floor_area_sqm', 'remaining_lease_months']
all_features = amenity_features + property_features

from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

grid_results = []
grids = df_grid['grid_id'].unique()
print(f"Processing {len(grids)} grids...")

for i, grid_id in enumerate(grids):
    if i % 500 == 0:
        print(f"  Progress: {i}/{len(grids)}")

    grid_df = df_grid[df_grid['grid_id'] == grid_id].copy()
    grid_df = grid_df.dropna(subset=['price_psm'] + all_features)

    if len(grid_df) < 10:
        continue

    X = grid_df[all_features]
    y = grid_df['price_psm']

    if len(grid_df) < 20:
        continue

    try:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.3, random_state=42
        )

        rf = RandomForestRegressor(n_estimators=20, max_depth=5, random_state=42, n_jobs=-1)
        rf.fit(X_train, y_test)

        mrt_dist_imp = rf.feature_importances_[all_features.index('dist_to_nearest_mrt')]
        mrt_500_imp = rf.feature_importances_[all_features.index('mrt_within_500m')]

        grid_results.append({
            'grid_id': grid_id,
            'n_transactions': len(grid_df),
            'mrt_distance_importance': mrt_dist_imp,
            'mrt_within_500m_importance': mrt_500_imp,
            'median_price_psm': grid_df['price_psm'].median(),
            'avg_mrt_distance': grid_df['dist_to_nearest_mrt'].mean(),
            'lat': grid_df['lat'].mean(),
            'lon': grid_df['lon'].mean()
        })
    except Exception:
        continue

results_df = pd.DataFrame(grid_results)
print(f"\nCompleted analysis for {len(results_df):,} grids")

print(f"\nGrid-level MRT impact statistics:")
print(f"  Mean mrt_distance importance: {results_df['mrt_distance_importance'].mean():.4f}")
print(f"  Median mrt_distance importance: {results_df['mrt_distance_importance'].median():.4f}")

results_df.to_csv(OUTPUT_DIR / 'grid_analysis.csv', index=False)
print(f"\nSaved: {OUTPUT_DIR / 'grid_analysis.csv'}")

print("\n=== GENERATING SUMMARY STATS ===")
summary = {}

temporal_df = pd.read_csv(OUTPUT_DIR / 'temporal_comparison.csv')
mrt_pre = temporal_df[(temporal_df['period'] == 'pre_covid') &
                      (temporal_df['feature'] == 'dist_to_nearest_mrt')]['importance'].values
mrt_covid = temporal_df[(temporal_df['period'] == 'covid') &
                        (temporal_df['feature'] == 'dist_to_nearest_mrt')]['importance'].values
mrt_post = temporal_df[(temporal_df['period'] == 'post_covid') &
                       (temporal_df['feature'] == 'dist_to_nearest_mrt')]['importance'].values

summary['mrt_importance_pre_covid'] = mrt_pre[0] if len(mrt_pre) > 0 else None
summary['mrt_importance_covid'] = mrt_covid[0] if len(mrt_covid) > 0 else None
summary['mrt_importance_post_covid'] = mrt_post[0] if len(mrt_post) > 0 else None

if summary['mrt_importance_pre_covid'] and summary['mrt_importance_post_covid']:
    change = ((summary['mrt_importance_post_covid'] - summary['mrt_importance_pre_covid'])
              / summary['mrt_importance_pre_covid'] * 100)
    summary['mrt_importance_change_pct'] = change

within_town_df = pd.read_csv(OUTPUT_DIR / 'within_town_effects.csv')
summary['avg_mrt_within_town_importance'] = within_town_df['mrt_distance_importance'].mean()
summary['top_mrt_sensitive_town'] = within_town_df.iloc[0]['town']
summary['top_mrt_sensitive_town_importance'] = within_town_df.iloc[0]['mrt_distance_importance']

summary['avg_grid_mrt_importance'] = results_df['mrt_distance_importance'].mean()
summary['grids_with_high_mrt_impact'] = int((results_df['mrt_distance_importance'] > 0.1).sum())

closest_band = band_stats.iloc[0]
farthest_band = band_stats.iloc[-1]
if closest_band['price_psm_median'] and farthest_band['price_psm_median']:
    premium = ((closest_band['price_psm_median'] - farthest_band['price_psm_median'])
               / farthest_band['price_psm_median'] * 100)
    summary['mrt_proximity_premium_pct'] = premium

summary_df = pd.DataFrame([summary])
summary_df.to_csv(OUTPUT_DIR / 'summary_stats.csv', index=False)
print(f"Saved: {OUTPUT_DIR / 'summary_stats.csv'}")

print("\n=== KEY FINDINGS ===")
print(f"MRT importance change (Pre-COVID to Post-COVID): {summary.get('mrt_importance_change_pct', 'N/A'):.1f}%")
print(f"MRT proximity premium (closest vs farthest band): {summary.get('mrt_proximity_premium_pct', 'N/A'):.1f}%")
print(f"Town with highest MRT sensitivity: {summary.get('top_mrt_sensitive_town', 'N/A')}")

print("\n" + "="*60)
print("ANALYSIS COMPLETE")
print("="*60)
