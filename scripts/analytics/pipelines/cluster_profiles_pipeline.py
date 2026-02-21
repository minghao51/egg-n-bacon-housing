"""Quick cluster profile generation - streamlined version for dashboard data."""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler

DATA_DIR = Path("data/analytics/market_segmentation")
OUTPUT_DIR = Path("data/analytics/market_segmentation_2.0")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

print("="*60)
print("QUICK CLUSTER PROFILE GENERATION")
print("="*60)

print("\nLoading dataset...")
df = pd.read_parquet(DATA_DIR / "housing_unified_segmented.parquet")
print(f"Loaded {len(df):,} records")

df_recent = df[df['year'] >= 2021].copy()
print(f"Recent records (2021+): {len(df_recent):,}")

clustering_features = [
    'price_psf',
    'floor_area_sqft',
    'remaining_lease_months',
    'rental_yield_pct',
    'yoy_change_pct',
    'mom_change_pct',
    'transaction_count',
    'stratified_median_price'
]

clustering_features = [f for f in clustering_features if f in df_recent.columns]
df_cluster = df_recent.dropna(subset=clustering_features).copy()
print(f"Records for clustering: {len(df_cluster):,}")

X = df_cluster[clustering_features].copy()

print("\nPreparing features...")
X_log = X.copy()
for feat in ['price_psf', 'floor_area_sqft', 'transaction_count', 'stratified_median_price']:
    if feat in X_log.columns:
        X_log[f'{feat}_log'] = np.log1p(X_log[feat])
        clustering_features.append(f'{feat}_log')

all_features = [f for f in X_log.columns]
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_log[all_features])

print(f"Features: {len(all_features)}")

print("\nPerforming K-Means clustering (K=6)...")
kmeans = MiniBatchKMeans(n_clusters=6, random_state=42, batch_size=1000, n_init=10)
df_cluster['cluster_kmeans'] = kmeans.fit_predict(X_scaled)

print("\nCluster sizes:")
print(df_cluster['cluster_kmeans'].value_counts().sort_index())

print("\nGenerating cluster profiles...")
profile_cols = [
    'cluster_kmeans', 'price_psf', 'rental_yield_pct', 'yoy_change_pct',
    'floor_area_sqft', 'transaction_count', 'remaining_lease_months'
]
available_cols = [c for c in profile_cols if c in df_cluster.columns]

cluster_profiles = df_cluster.groupby('cluster_kmeans')[available_cols].agg(['mean', 'std', 'count', 'min', 'max'])
cluster_profiles.columns = ['_'.join(col).strip() for col in cluster_profiles.columns.values]

cluster_sizes = df_cluster['cluster_kmeans'].value_counts().sort_index()
cluster_profiles['cluster_size'] = cluster_sizes.values
cluster_profiles['cluster_percentage'] = (cluster_sizes / len(df_cluster) * 100).values

cluster_names = {
    0: "Large Size Stable",  # Large properties (1328 sqft), high PSF due to size, stable growth
    1: "High Growth Recent",  # Very high growth (24%), newer leases (80 yrs), moderate PSF
    2: "Speculator Hotspots",  # Extremely high growth (84%), shorter leases, highest appreciation
    3: "Declining Areas",  # Negative growth (-3.6%), shortest leases (54 yrs), declining value
    4: "Mid-Tier Value",  # Lowest PSF ($463), good value, moderate growth
    5: "Premium New Units",  # Highest PSF ($826), newest leases (89 yrs), premium pricing
}

cluster_profiles['segment_name'] = cluster_profiles.index.map(lambda x: cluster_names.get(x, f"Segment {x}"))

print("\nCluster Profiles:")
print(cluster_profiles[['segment_name', 'cluster_size', 'cluster_percentage', 'price_psf_mean', 'rental_yield_pct_mean', 'yoy_change_pct_mean']].to_string())

cluster_profiles.to_csv(OUTPUT_DIR / 'cluster_profiles.csv')
print(f"\nSaved: {OUTPUT_DIR / 'cluster_profiles.csv'}")

print("\nGenerating investment strategies...")
strategies = []

for cluster_id in sorted(df_cluster['cluster_kmeans'].unique()):
    cluster_data = df_cluster[df_cluster['cluster_kmeans'] == cluster_id]

    avg_yield = cluster_data['rental_yield_pct'].mean() if 'rental_yield_pct' in cluster_data.columns else 0
    avg_growth = cluster_data['yoy_change_pct'].mean() if 'yoy_change_pct' in cluster_data.columns else 0
    avg_price = cluster_data['price_psf'].mean() if 'price_psf' in cluster_data.columns else 0

    if avg_yield > 6 and avg_growth > 10:
        strategy = "HOLD & GROW - High yield + strong appreciation. Ideal for long-term buy-and-hold investors."
    elif avg_yield > 6:
        strategy = "YIELD PLAY - High rental yield. Focus on cash flow rather than appreciation."
    elif avg_growth > 15:
        strategy = "GROWTH PLAY - High appreciation potential. Consider for capital gains."
    elif avg_price < 500:
        strategy = "VALUE INVESTING - Affordable entry point. Good for first-time buyers or budget investors."
    elif avg_price > 1500:
        strategy = "LUXURY SEGMENT - Premium properties. Focus on location and exclusivity."
    else:
        strategy = "BALANCED APPROACH - Moderate yield and growth. Balanced investment strategy."

    strategies.append({
        'cluster_id': cluster_id,
        'segment_name': cluster_names.get(cluster_id, f"Segment {cluster_id}"),
        'strategy': strategy,
        'avg_yield_pct': round(avg_yield, 2),
        'avg_growth_pct': round(avg_growth, 2),
        'avg_price_psf': round(avg_price, 0)
    })

strategies_df = pd.DataFrame(strategies)
strategies_df.to_csv(OUTPUT_DIR / 'investment_strategies.csv', index=False)
print(f"Saved: {OUTPUT_DIR / 'investment_strategies.csv'}")

print("\n" + "="*60)
print("CLUSTER PROFILE GENERATION COMPLETE")
print("="*60)
print(f"\nOutput: {OUTPUT_DIR}")
print("Segments: 6")
