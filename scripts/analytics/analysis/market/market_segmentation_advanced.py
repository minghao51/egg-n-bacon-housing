"""
Market Segmentation 2.0 - Advanced Behavioral Clustering

Goes beyond basic "market_tier" to discover natural market segments using:
- K-means clustering on key behavioral metrics
- Hierarchical clustering for dendrogram analysis
- PCA for dimensionality reduction and visualization
- Segment profiling and characterization
- Investment strategies per segment

Identifies distinct market behaviors like "High-Growth HDBs", "Premium Condos with Low Yields", etc.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import MiniBatchKMeans, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

import matplotlib.pyplot as plt
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, linkage

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (14, 8)

# Paths
DATA_DIR = Path("data/analysis/market_segmentation")
OUTPUT_DIR = Path("data/analysis/market_segmentation_2.0")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

print("="*80)
print("MARKET SEGMENTATION 2.0 - ADVANCED BEHAVIORAL CLUSTERING")
print("="*80)

# ============================================================================
# 1. LOAD AND PREPARE DATA
# ============================================================================
print("\nLoading dataset...")

df = pd.read_parquet(DATA_DIR / "housing_unified_segmented.parquet")
print(f"Loaded {len(df):,} records")

# Focus on recent complete data (2021+)
df_recent = df[df['year'] >= 2021].copy()

# Key behavioral metrics for clustering
clustering_features = [
    'price_psm',           # Price level
    'floor_area_sqm',      # Size
    'remaining_lease_months',  # Lease remaining
    'rental_yield_pct',    # Yield (if available)
    'yoy_change_pct',      # Appreciation
    'mom_change_pct',      # Short-term momentum
    'transaction_count',   # Trading activity
    'stratified_median_price'  # Market benchmark
]

# Select features that exist
clustering_features = [f for f in clustering_features if f in df_recent.columns]

print(f"Clustering features: {clustering_features}")

# Drop rows with missing values in clustering features
df_cluster = df_recent.dropna(subset=clustering_features).copy()
print(f"Records after dropping missing values: {len(df_cluster):,}")

# ============================================================================
# 2. PREPARE FEATURES FOR CLUSTERING
# ============================================================================
print("\nPreparing features...")

X = df_cluster[clustering_features].copy()

# Log-transform skewed variables
skewed_features = ['price_psm', 'floor_area_sqm', 'transaction_count', 'stratified_median_price']
for feat in skewed_features:
    if feat in X.columns:
        X[f'{feat}_log'] = np.log1p(X[feat])
        clustering_features.append(f'{feat}_log')

# Standardize features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X[clustering_features])

print(f"  Features scaled: {len(clustering_features)}")
print(f"  Data shape: {X_scaled.shape}")

# ============================================================================
# 3. DETERMINE OPTIMAL NUMBER OF CLUSTERS
# ============================================================================
print("\nDetermining optimal number of clusters...")

# Test K from 2 to 10
inertias = []
silhouettes = []
K_range = range(2, 11)

for k in K_range:
    kmeans = MiniBatchKMeans(n_clusters=k, random_state=42, batch_size=1000, n_init=10)
    kmeans.fit(X_scaled)

    inertias.append(kmeans.inertia_)
    silhouettes.append(silhouette_score(X_scaled, kmeans.labels_))
    print(f"  K={k}: Inertia={kmeans.inertia_:.2f}, Silhouette={silhouettes[-1]:.4f}")

# Find optimal K (elbow method + silhouette)
optimal_k_inertia = K_range[np.argmin(np.diff(inertias, 2)) + 2]  # Elbow
optimal_k_silhouette = K_range[np.argmax(silhouettes)]  # Max silhouette

print(f"\nOptimal K (Inertia/Elbow): {optimal_k_inertia}")
print(f"Optimal K (Silhouette): {optimal_k_silhouette}")

# Use silhouette-based K (more interpretable)
optimal_k = optimal_k_silhouette

# Visualize cluster selection
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Elbow plot
ax1.plot(K_range, inertias, marker='o', linewidth=2, markersize=8, color='steelblue')
ax1.axvline(x=optimal_k_inertia, color='red', linestyle='--', linewidth=2, label=f'Elbow at K={optimal_k_inertia}')
ax1.set_xlabel('Number of Clusters (K)', fontsize=12, fontweight='bold')
ax1.set_ylabel('Inertia (Within-Cluster Sum of Squares)', fontsize=12, fontweight='bold')
ax1.set_title('Elbow Method for Optimal K', fontsize=14, fontweight='bold')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Silhouette plot
ax2.plot(K_range, silhouettes, marker='o', linewidth=2, markersize=8, color='coral')
ax2.axvline(x=optimal_k_silhouette, color='red', linestyle='--', linewidth=2, label=f'Max Silhouette at K={optimal_k_silhouette}')
ax2.set_xlabel('Number of Clusters (K)', fontsize=12, fontweight='bold')
ax2.set_ylabel('Silhouette Score', fontsize=12, fontweight='bold')
ax2.set_title('Silhouette Analysis for Optimal K', fontsize=14, fontweight='bold')
ax2.legend()
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'optimal_clusters.png', dpi=300, bbox_inches='tight')
plt.show()

print("  Saved: optimal_clusters.png")

# ============================================================================
# 4. PERFORM K-MEANS CLUSTERING
# ============================================================================
print(f"\nPerforming K-Means clustering with K={optimal_k}...")

kmeans = MiniBatchKMeans(n_clusters=optimal_k, random_state=42, batch_size=1000, n_init=10)
df_cluster['cluster_kmeans'] = kmeans.fit_predict(X_scaled)

print(f"  Cluster sizes:")
print(df_cluster['cluster_kmeans'].value_counts().sort_index())

# ============================================================================
# 5. PERFORM HIERARCHICAL CLUSTERING (for comparison)
# ============================================================================
print("\nPerforming Hierarchical clustering...")

hierarchical = AgglomerativeClustering(n_clusters=optimal_k, linkage='ward')
df_cluster['cluster_hierarchical'] = hierarchical.fit_predict(X_scaled)

print(f"  Cluster sizes:")
print(df_cluster['cluster_hierarchical'].value_counts().sort_index())

# ============================================================================
# 6. PCA VISUALIZATION
# ============================================================================
print("\nPerforming PCA for visualization...")

# Reduce to 2D for visualization
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)

df_cluster['pca_1'] = X_pca[:, 0]
df_cluster['pca_2'] = X_pca[:, 1]

print(f"  Explained variance ratio: {pca.explained_variance_ratio_}")
print(f"  Total explained variance: {sum(pca.explained_variance_ratio_):.2%}")

# Visualize clusters in 2D
plt.figure(figsize=(12, 8))
scatter = plt.scatter(df_cluster['pca_1'], df_cluster['pca_2'],
                      c=df_cluster['cluster_kmeans'],
                      cmap='tab10',
                      alpha=0.6,
                      s=20,
                      edgecolors='black',
                      linewidths=0.5)
plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)', fontsize=12, fontweight='bold')
plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)', fontsize=12, fontweight='bold')
plt.title(f'Market Segments - PCA Visualization (K={optimal_k})', fontsize=14, fontweight='bold')
plt.colorbar(scatter, label='Cluster')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'clusters_pca.png', dpi=300, bbox_inches='tight')
plt.show()

print("  Saved: clusters_pca.png")

# ============================================================================
# 7. PROFILE CLUSTERS
# ============================================================================
print("\n" + "="*80)
print("CLUSTER PROFILES")
print("="*80)

# Calculate cluster statistics
cluster_profiles = df_cluster.groupby('cluster_kmeans')[clustering_features].agg(['mean', 'std'])
cluster_profiles.columns = ['_'.join(col).strip() for col in cluster_profiles.columns.values]

# Add cluster sizes
cluster_sizes = df_cluster['cluster_kmeans'].value_counts().sort_index()
cluster_profiles['cluster_size'] = cluster_sizes.values
cluster_profiles['cluster_percentage'] = (cluster_sizes / len(df_cluster) * 100).values

# Rename clusters for interpretability
cluster_names = {
    0: "Segment 1",
    1: "Segment 2",
    2: "Segment 3",
    3: "Segment 4",
    4: "Segment 5",
    5: "Segment 6"
}

cluster_profiles['segment_name'] = cluster_profiles.index.map(lambda x: cluster_names.get(x, f"Segment {x}"))

print("\nCluster Summary:")
print(cluster_profiles[['segment_name', 'cluster_size', 'cluster_percentage',
                        'price_psm_mean', 'rental_yield_pct_mean',
                        'yoy_change_pct_mean', 'transaction_count_mean']].to_string(index=False))

# ============================================================================
# 8. CHARACTERIZE EACH SEGMENT
# ============================================================================
print("\n" + "="*80)
print("DETAILED SEGMENT CHARACTERIZATION")
print("="*80)

for cluster_id in sorted(df_cluster['cluster_kmeans'].unique()):
    print(f"\n{'='*80}")
    print(f"CLUSTER {cluster_id}: {cluster_names.get(cluster_id, f'Segment {cluster_id}')}")
    print(f"{'='*80}")

    cluster_data = df_cluster[df_cluster['cluster_kmeans'] == cluster_id]

    print(f"  Size: {len(cluster_data):,} properties ({len(cluster_data)/len(df_cluster)*100:.1f}%)")

    print(f"\n  Key Characteristics:")
    print(f"    • Average Price: ${cluster_data['price_psm'].mean():,.0f}/psm (±${cluster_data['price_psm'].std():.0f})")
    print(f"    • Average Size: {cluster_data['floor_area_sqm'].mean():.0f} sqm (±{cluster_data['floor_area_sqm'].std():.0f})")

    if 'rental_yield_pct' in cluster_data.columns:
        print(f"    • Average Yield: {cluster_data['rental_yield_pct'].mean():.2f}% (±{cluster_data['rental_yield_pct'].std():.2f}%)")

    if 'yoy_change_pct' in cluster_data.columns:
        print(f"    • YoY Appreciation: {cluster_data['yoy_change_pct'].mean():.2f}% (±{cluster_data['yoy_change_pct'].std():.2f}%)")

    if 'mom_change_pct' in cluster_data.columns:
        print(f"    • MoM Change: {cluster_data['mom_change_pct'].mean():.2f}% (±{cluster_data['mom_change_pct'].std():.2f}%)")

    print(f"    • Trading Activity: {cluster_data['transaction_count'].mean():.0f} transactions (±{cluster_data['transaction_count'].std():.0f})")

    # Top property types
    if 'property_type' in cluster_data.columns:
        print(f"\n  Property Type Distribution:")
        prop_type_dist = cluster_data['property_type'].value_counts(normalize=True) * 100
        for prop_type, pct in prop_type_dist.head(3).items():
            print(f"    • {prop_type}: {pct:.1f}%")

    # Top towns
    if 'town' in cluster_data.columns:
        print(f"\n  Top 5 Towns:")
        town_dist = cluster_data['town'].value_counts().head(5)
        for town, count in town_dist.items():
            print(f"    • {town}: {count} properties")

# ============================================================================
# 9. GENERATE INVESTMENT STRATEGIES PER SEGMENT
# ============================================================================
print("\n" + "="*80)
print("INVESTMENT STRATEGIES BY SEGMENT")
print("="*80)

strategies = {}

for cluster_id in sorted(df_cluster['cluster_kmeans'].unique()):
    cluster_data = df_cluster[df_cluster['cluster_kmeans'] == cluster_id]

    # Calculate segment metrics
    avg_yield = cluster_data['rental_yield_pct'].mean() if 'rental_yield_pct' in cluster_data.columns else 0
    avg_growth = cluster_data['yoy_change_pct'].mean() if 'yoy_change_pct' in cluster_data.columns else 0
    avg_price = cluster_data['price_psm'].mean()

    # Determine strategy
    if avg_yield > 6 and avg_growth > 10:
        strategy = "🌟 **HOLD & GROW** - High yield + strong appreciation. Ideal for long-term buy-and-hold investors."
    elif avg_yield > 6:
        strategy = "💰 **YIELD PLAY** - High rental yield. Focus on cash flow rather than appreciation."
    elif avg_growth > 15:
        strategy = "📈 **GROWTH PLAY** - High appreciation potential. Consider for capital gains."
    elif avg_price < 5000:
        strategy = "💵 **VALUE INVESTING** - Affordable entry point. Good for first-time buyers or budget investors."
    elif avg_price > 10000:
        strategy = "💎 **LUXURY SEGMENT** - Premium properties. Focus on location and exclusivity."
    else:
        strategy = "🔄 **BALANCED APPROACH** - Moderate yield and growth. Balanced investment strategy."

    strategies[cluster_id] = strategy
    print(f"\n{cluster_names.get(cluster_id, f'Segment {cluster_id}')}: {strategy}")

# ============================================================================
# 10. VISUALIZATION: SEGMENT COMPARISON
# ============================================================================
print("\nGenerating segment comparison visualizations...")

# Create a comparison heatmap
comparison_metrics = ['price_psm', 'rental_yield_pct', 'yoy_change_pct', 'transaction_count']
available_metrics = [m for m in comparison_metrics if m in df_cluster.columns]

if available_metrics:
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()

    for i, metric in enumerate(available_metrics):
        if i >= 4:
            break

        # Calculate mean by cluster
        cluster_means = df_cluster.groupby('cluster_kmeans')[metric].mean().sort_values(ascending=False)

        # Plot
        cluster_means.plot(kind='bar', ax=axes[i], color='steelblue')
        axes[i].set_title(f'{metric.replace("_", " ").title()} by Segment', fontsize=12, fontweight='bold')
        axes[i].set_ylabel(metric.replace("_", " ").title(), fontsize=10)
        axes[i].set_xlabel('Segment', fontsize=10)
        axes[i].tick_params(axis='x', rotation=45)
        axes[i].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'segment_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()

    print("  Saved: segment_comparison.png")

# ============================================================================
# 11. DENDROGRAM (HIERARCHICAL CLUSTERING)
# ============================================================================
print("\nGenerating hierarchical clustering dendrogram...")

# Create linkage matrix
linkage_matrix = linkage(X_scaled, method='ward')

plt.figure(figsize=(14, 8))
dendrogram(linkage_matrix, truncate_mode='lastp', p=optimal_k, show_leaf_counts=True)
plt.title(f'Hierarchical Clustering Dendrogram (K={optimal_k})', fontsize=14, fontweight='bold')
plt.xlabel('Cluster Size', fontsize=12, fontweight='bold')
plt.ylabel('Distance', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'dendrogram.png', dpi=300, bbox_inches='tight')
plt.show()

print("  Saved: dendrogram.png")

# ============================================================================
# 12. EXPORT RESULTS
# ============================================================================
print("\n" + "="*80)
print("EXPORTING RESULTS")
print("="*80)

# Export clustered data
df_cluster.to_csv(
    OUTPUT_DIR / 'property_segments.csv',
    index=False
)
print(f"  Saved: property_segments.csv ({len(df_cluster):,} properties)")

# Export cluster profiles
cluster_profiles.to_csv(
    OUTPUT_DIR / 'cluster_profiles.csv'
)
print(f"  Saved: cluster_profiles.csv ({optimal_k} segments)")

# Export strategies
strategies_df = pd.DataFrame([
    {'cluster_id': k, 'segment_name': cluster_names.get(k, f'Segment {k}'), 'strategy': v}
    for k, v in strategies.items()
])
strategies_df.to_csv(
    OUTPUT_DIR / 'investment_strategies.csv',
    index=False
)
print(f"  Saved: investment_strategies.csv")

print("\n" + "="*80)
print("MARKET SEGMENTATION 2.0 COMPLETE")
print("="*80)
print(f"\nResults saved to: {OUTPUT_DIR}")
print(f"\nKey Findings:")
print(f"  • Optimal segments: {optimal_k}")
print(f"  • Largest segment: {cluster_sizes.idxmax()} ({cluster_sizes.max():,} properties)")
print(f"  • Smallest segment: {cluster_sizes.idxmin()} ({cluster_sizes.min():,} properties)")
print(f"\nInvestment Strategy: See investment_strategies.csv for details")
