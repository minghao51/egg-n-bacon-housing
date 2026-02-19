---
title: Spatial Analytics Overview
category: technical-reports
description: Spatial analytics methods for identifying patterns in geographic housing data
status: draft
---

# Spatial Analytics Overview

**Date:** 2026-01-24
**Scripts:** `analyze_spatial_hotspots.py`, `analyze_spatial_autocorrelation.py`, `analyze_h3_clusters.py`

---

## Executive Summary

Spatial analytics methods identify statistically significant patterns in geographic data. Three complementary scripts analyze spatial relationships in Singapore housing data:

1. **Hotspot Analysis** - Find high/low value clusters using Getis-Ord Gi*
2. **Spatial Autocorrelation** - Measure overall clustering strength with Moran's I
3. **H3 Clustering** - Discover natural property groups using DBSCAN on hex grids

### 🎯 Why This Matters

**In Plain English:** Imagine you're house hunting. Spatial analytics answers questions like:
- *"Where are the expensive neighborhoods clustered?"* (Hotspots)
- *"Are nearby properties more similar than distant ones?"* (Spatial Autocorrelation)
- *"What are the natural market segments across Singapore?"* (H3 Clustering)

**Practical Applications:**
- **Homebuyers:** Identify up-and-coming areas before prices spike
- **Investors:** Spot undervalued clusters with appreciation potential
- **Policy Makers:** Target cooling measures where they'll be most effective
- **Researchers:** Understand how location affects property values

---

## Methods

### 1. Getis-Ord Gi* (Hotspot Analysis)

#### 🎯 What It Does (Plain English)
Identifies neighborhoods where prices are **consistently higher** (hotspots) or **consistently lower** (coldspots) than surrounding areas, with statistical confidence.

**Real-World Analogy:** Like finding "hot neighborhoods" where every street seems expensive, but with mathematical rigor that proves it's not just random chance.

#### 💡 Practical Interpretation

| Your Situation | How to Use Hotspot Analysis |
|---------------|---------------------------|
| **Homebuyer** | Focus on emerging hotspots (95% confidence) for appreciation potential, avoid overpriced established hotspots |
| **Investor** | Target coldspots near future infrastructure for turnaround opportunities |
| **Policy Maker** | Monitor hotspots for cooling measure effectiveness |

#### 📊 Interactive Plotly Visualization

```python
import plotly.graph_objects as go
import plotly.express as px
import geopandas as gpd

# Load hotspot data
hotspots_gdf = gpd.read_file('data/analysis/analyze_spatial_hotspots/hotspots.geojson')

# Create interactive choropleth map
fig = go.Figure(data=go.Choroplethmapbox(
    geojson=hotspots_gdf.geometry.__geo_interface__,
    locations=hotspots_gdf.index,
    z=hotspots_gdf['gi_zscore'],
    colorscale='RdBu_r',  # Red for hotspots, Blue for coldspots
    reversescale=False,
    marker_opacity=0.7,
    marker_line_width=1,
    colorbar=dict(title="Gi* Z-Score")
))

fig.update_layout(
    mapbox=dict(
        style="carto-positron",
        zoom=10,
        center={"lat": 1.3521, "lon": 103.8198}
    ),
    title="Singapore Property Price Hotspots (Getis-Ord Gi*)",
    height=600
)

fig.show()
```

**Interactive Features:**
- Hover over cells to see Z-scores and confidence levels
- Zoom into specific neighborhoods
- Filter by confidence level (95% vs 99%)

#### 🔬 How It Works (Technical)
- Calculates local Getis-Ord statistics for each H3 hex cell
- Z-score indicates significance: |Z| > 1.96 for 95% confidence, |Z| > 2.58 for 99% confidence
- Accounts for spatial dependency (nearby cells influence each other)

**Output:**
- `hotspots.geojson` - Hex cells with hotspot/coldspot classifications
- `hotspot_stats.csv` - Gi* Z-scores and p-values per cell

**Interpretation:**
| Gi* Z-score | Classification | Confidence |
|-------------|----------------|------------|
| > 2.58 | Hotspot | 99% |
| 1.96 - 2.58 | Hotspot | 95% |
| -1.96 - 1.96 | Not significant | - |
| -2.58 - -1.96 | Coldspot | 95% |
| < -2.58 | Coldspot | 99% |

### 2. Moran's I (Global Spatial Autocorrelation)

#### 🎯 What It Does (Plain English)
Measures whether **similar property prices tend to cluster together** across the entire country. Answers: *"Is location destiny in Singapore's housing market?"*

**Real-World Analogy:** Like measuring how "cliquish" high school is - do popular kids hang out together, or is everyone randomly mixed?

#### 💡 Practical Interpretation

| Moran's I Value | What It Means for You |
|----------------|---------------------|
| **0.5 - 1.0 (Strong)** | Location matters A LOT. Neighborhood defines price. Focus on area, not individual property. |
| **0.3 - 0.5 (Moderate)** | Location matters, but individual property differences also important. |
| **0 - 0.3 (Weak)** | Property-specific features (size, condition, floor) matter more than location. |

#### 📊 Interactive Plotly Visualization

```python
import plotly.graph_objects as go
from scipy import stats

# Load Moran's I results
moran_df = pd.read_csv('data/analysis/analyze_spatial_autocorrelation/moran_results.csv')

# Create Moran's I scatter plot with confidence interval
fig = go.Figure()

# Add reference distribution (permutation test)
fig.add_trace(go.Histogram(
    x=moran_df['permutation_results'],
    name='Random Distribution',
    nbinsx=50,
    opacity=0.7,
    marker_color='lightblue'
))

# Add observed Moran's I
fig.add_vline(
    x=moran_df['moran_i'].iloc[0],
    line_dash="dash",
    line_color="red",
    annotation_text=f"Observed I = {moran_df['moran_i'].iloc[0]:.3f}"
)

fig.update_layout(
    title=f"Moran's I Test: {moran_df['interpretation'].iloc[0]} Clustering (p < {moran_df['p_value'].iloc[0]:.4f})",
    xaxis_title="Moran's I Statistic",
    yaxis_title="Frequency",
    height=500
)

fig.show()
```

#### 🔬 How It Works (Technical)
- Computes correlation between nearby values
- I > 0: Positive autocorrelation (similar values cluster)
- I = 0: Random spatial distribution
- I < 0: Negative autocorrelation (dissimilar values near each other)

**Output:**
- `moran_results.csv` - Moran's I statistic, p-value, permutation test results

**Interpretation:**
| Moran's I | Interpretation |
|-----------|----------------|
| 0 - 0.3 | Weak clustering |
| 0.3 - 0.5 | Moderate clustering |
| 0.5 - 1.0 | Strong clustering |

### 3. Local Indicators of Spatial Association (LISA)

#### 🎯 What It Does (Plain English)
Identifies **specific cluster types** at the local level. Goes beyond "hotspot/coldspot" to classify four types of spatial relationships.

**Real-World Analogy:** Like labeling each property based on its neighborhood context:
- **HH (High-High):** "Luxury enclave" - expensive home in expensive area
- **LL (Low-Low):** "Affordable pocket" - budget home in budget area
- **HL (High-Low):** "Overpriced outlier" - mansion in modest neighborhood
- **LH (Low-High):** "Underpriced deal" - modest home in luxury area

#### 💡 Practical Interpretation

| LISA Cluster | Investment Strategy |
|--------------|-------------------|
| **HH (Hotspot)** | Safe bet, established area. Low risk, lower appreciation potential. |
| **LL (Coldspot)** | Stable rental market. Look for turnaround catalysts (new MRT, amenities). |
| **HL (Outlier)** **⚠️** | Risky. Either overpriced or special feature (penthouse, corner unit). |
| **LH (Deal)** **✨** | Potential bargain. Undervalued relative to neighbors. |

#### 📊 Interactive Plotly Visualization

```python
import plotly.express as px

# Load LISA results
lisa_gdf = gpd.read_file('data/analysis/analyze_spatial_autocorrelation/lisa_clusters.geojson')

# Define colors for clusters
color_map = {
    'HH': '#d73027',  # Red - hotspot
    'LL': '#313695',  # Blue - coldspot
    'HL': '#fee08b',  # Yellow - high outlier
    'LH': '#abd9e9',  # Light blue - low outlier
    'Not Significant': 'lightgrey'
}

fig = px.choropleth_mapbox(
    lisa_gdf,
    geojson=lisa_gdf.geometry.__geo_interface__,
    locations=lisa_gdf.index,
    color='lisa_cluster',
    color_discrete_map=color_map,
    category_orders={'lisa_cluster': ['HH', 'LL', 'HL', 'LH', 'Not Significant']},
    mapbox_style="carto-positron",
    zoom=10,
    center={"lat": 1.3521, "lon": 103.8198},
    title="LISA Clusters: Local Spatial Patterns",
    opacity=0.7
)

fig.update_layout(height=600)
fig.show()
```

#### 🔬 How It Works (Technical)
- Decomposes global Moran's I into local contributions
- Four classifications:
  - **HH:** High value surrounded by high values (hotspot)
  - **LL:** Low value surrounded by low values (coldspot)
  - **HL:** High value surrounded by low values (outlier)
  - **LH:** Low value surrounded by high values (outlier)

**Output:**
- `lisa_clusters.geojson` - Cluster map with HH/LH/HL/LL classifications

### 4. H3 Clustering with DBSCAN

#### 🎯 What It Does (Plain English)
Groups properties into **natural market segments** based on location AND characteristics (price, size, rental yield). Unlike administrative boundaries, these clusters emerge from the data itself.

**Real-World Analogy:** Like grouping students by study habits AND grades, not just by classroom. Finds "hidden" neighborhoods that cross town boundaries.

#### 💡 Practical Interpretation

| Cluster Type | What It Represents | Investment Strategy |
|--------------|-------------------|-------------------|
| **Core Cluster** | Well-defined market segment (e.g., "luxury condos near MRT") | Understand pricing norms, fair comparison |
| **Edge Cluster** | Transitional areas, changing character | Speculative, higher risk/reward |
| **Noise** | Unique properties (penthouse, shophouse) | Harder to value, specialist market |

#### 📊 Interactive Plotly Visualization

```python
import plotly.express as px
import plotly.graph_objects as go

# Load cluster data
clusters_df = pd.read_csv('data/analysis/analyze_h3_clusters/property_clusters.csv')
cluster_profiles = pd.read_csv('data/analysis/analyze_h3_clusters/cluster_profiles.csv')

# 3D scatter plot: Price vs Size vs Rental Yield
fig = px.scatter_3d(
    clusters_df,
    x='price_psf',
    y='floor_area',
    z='rental_yield',
    color='cluster',
    hover_data=['town', 'address'],
    title='Property Clusters in 3D Space',
    labels={
        'price_psf': 'Price PSF ($)',
        'floor_area': 'Floor Area (sqm)',
        'rental_yield': 'Rental Yield (%)'
    }
)

fig.update_layout(height=700)
fig.show()

# Parallel coordinates plot for cluster profiles
fig_parallel = px.parallel_coordinates(
    cluster_profiles,
    color='cluster_id',
    labels={
        'median_price_psf': 'Price PSF',
        'median_rental_yield': 'Yield %',
        'median_floor_area': 'Size (sqm)',
        'n_properties': 'Count'
    },
    title='Cluster Characteristics Comparison'
)

fig_parallel.show()
```

#### 🔬 How It Works (Technical)
- Maps properties to H3 hex grid (resolution 8-10)
- Uses DBSCAN clustering on hex cells with feature vectors
- Feature vector includes: price_psf, rental_yield, floor_area, remaining_lease
- Only dense regions (eps threshold) become clusters; sparse cells are noise

**Output:**
- `property_clusters.csv` - Each property with cluster assignment
- `cluster_profiles.csv` - Statistical profile per cluster

**Interpretation:**
| Cluster Type | Description |
|--------------|-------------|
| Core Cluster | High density, well-defined market segment |
| Edge Cluster | Lower density, transitional area |
| Noise | Isolated properties (unique characteristics) |

---

## Usage

### Run Individual Scripts

```bash
# Hotspot analysis
uv run python scripts/analysis/analyze_spatial_hotspots.py

# Spatial autocorrelation
uv run python scripts/analysis/analyze_spatial_autocorrelation.py

# H3 clustering
uv run python scripts/analysis/analyze_h3_clusters.py
```

### Run via L4 Pipeline

```bash
uv run python core/pipeline/L4_analysis.py
```

---

## Output Locations

```
data/analysis/
  ├── analyze_spatial_hotspots/
  │   ├── hotspots.geojson
  │   ├── hotspot_stats.csv
  │   └── visualizations/
  ├── analyze_spatial_autocorrelation/
  │   ├── moran_results.csv
  │   ├── lisa_clusters.geojson
  │   └── moran_scatter.png
  └── analyze_h3_clusters/
      ├── property_clusters.csv
      ├── cluster_profiles.csv
      └── cluster_map.png
```

---

## Key Findings (Example)

### Hotspot Analysis Results

| Region | Gi* Z-score | Classification | Confidence |
|--------|-------------|----------------|------------|
| Orchard | 3.42 | Hotspot | 99% |
| Marina South | 2.89 | Hotspot | 99% |
| Bukit Timah | 2.15 | Hotspot | 95% |
| Woodlands | -2.34 | Coldspot | 95% |
| Yishun | -2.67 | Coldspot | 99% |

### Spatial Autocorrelation Results

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Moran's I | 0.342 | Moderate clustering |
| p-value | < 0.001 | Statistically significant |
| Z-score | 8.45 | Strong evidence of clustering |

---

## Data Requirements

### Input Data

- **Primary:** `data/parquets/L3/housing_unified.parquet`
- **Features used:** `lat`, `lon`, `price_psf`, `monthly_rent`, `town`

### H3 Resolution

| Resolution | Cell Area | Use Case |
|------------|-----------|----------|
| 7 | ~4 km² | Regional analysis |
| 8 | ~0.5 km² | Town-level (default) |
| 9 | ~0.07 km² | Neighborhood-level |
| 10 | ~0.01 km² | Street-level |

---

## Configuration

```python
from scripts.core.config import Config

# Output directory
Config.ANALYSIS_OUTPUT_DIR  # data/analysis

# H3 resolution
H3_RESOLUTION = 8  # Default

# Spatial weights
WEIGHTS_TYPE = 'knn'  # K-nearest neighbors
K_NEIGHBORS = 8  # Number of neighbors
```

---

## Dependencies

```
libpysal>=4.6.0    # Spatial weights and statistics
esda>=1.5.0        # Spatial autocorrelation
h3>=3.7.0          # H3 hex grid
geopandas>=0.14.0  # GeoJSON handling
```

---

## Limitations

1. **Edge Effects:** Cells at data boundary may have fewer neighbors
2. **MAUP:** Modifiable Areal Unit Problem - results depend on H3 resolution
3. **Temporal Dimension:** Static analysis (time series not modeled)
4. **Data Coverage:** Sparse areas may show false coldspots

---

## 🚀 Machine Learning Enhancements

### Advanced Methods Beyond Basic Spatial Analytics

While the methods above provide powerful insights, modern ML techniques can enhance spatial analysis:

#### 1. Spatially-Explicit ML Models

**Geographically Weighted Regression (GWR)**
- **What:** Local regression model where coefficients vary by location
- **Why:** Captures spatial heterogeneity - relationships change across space
- **Example:** MRT proximity effect might be +15% in OCR but only +5% in CCR
- **Implementation:** Use `mgwr` package in Python

```python
from mgwr.sel_bw import Sel_BW
from mgwr.gwr import GWR

# Prepare data with coordinates
coords = list(zip(df['lat'], df['lon']))
X = df[['mrt_distance', 'floor_area', 'age']]
y = df['price_psf']

# Select optimal bandwidth
bw = Sel_BW(coords, X.values, y.values).search()

# Fit GWR model
gwr = GWR(coords, X.values, y.values, bw).fit()

# Visualize spatially-varying coefficients
gwr_results = gdf.merge(
    pd.DataFrame(gwr.params, columns=['intercept', 'mrt_coef', 'area_coef', 'age_coef']),
    left_index=True, right_index=True
)

fig = px.choropleth_mapbox(
    gwr_results,
    geojson=gwr_results.geometry.__geo_interface__,
    locations=gwr_results.index,
    color='mrt_coef',
    title='GWR: Spatially-Varying MRT Price Premium',
    mapbox_style="carto-positron",
    zoom=10,
    center={"lat": 1.3521, "lon": 103.8198},
)
```

**Random Forest with Spatial Features**
- **What:** Ensemble decision trees with engineered spatial features
- **Why:** Captures non-linear relationships and interactions
- **Spatial Features:** Distance to CBD, MRT, schools, amenities; neighborhood medians; spatial lag features
- **Interpretation:** Use SHAP values to explain spatial effects

```python
from sklearn.ensemble import RandomForestRegressor
import shap

# Engineer spatial features
df['dist_cbd'] = haversine(df['lat'], df['lon'], 1.2839, 103.8513)
df['spatial_lag_price'] = df.groupby('planning_area')['price_psf'].transform('median')

# Train model
rf = RandomForestRegressor(n_estimators=200, max_depth=15)
X = df[['dist_cbd', 'mrt_distance', 'spatial_lag_price', 'floor_area']]
y = df['price_psf']
rf.fit(X, y)

# Explain with SHAP
explainer = shap.TreeExplainer(rf)
shap_values = explainer.shap_values(X)

# Plot: How MRT distance affects price predictions
shap.dependence_plot('mrt_distance', shap_values, X)
```

#### 2. Clustering Enhancements

**HDBSCAN (Hierarchical DBSCAN)**
- **What:** Extension of DBSCAN that finds clusters of varying density
- **Why:** More robust than DBSCAN, provides cluster probability scores
- **Benefit:** Softer cluster assignments (can belong to multiple clusters)

```python
import hdbscan

# Fit HDBSCAN
clusterer = hdbscan.HDBSCAN(min_cluster_size=50, prediction_data=True)
cluster_labels = clusterer.fit_predict(X_spatial)

# Get probability scores (soft clustering)
strengths = clusterer.probabilities_

# Visualize cluster confidence
fig = px.scatter(
    df, x='lon', y='lat',
    color=cluster_labels,
    size=strengths,
    title='HDBSCAN Clusters with Confidence Scores',
    hover_data=['price_psf', 'town']
)
```

**Gaussian Mixture Models (GMM)**
- **What:** Probabilistic clustering assuming Gaussian distributions
- **Why:** Provides probability of belonging to each cluster
- **Use Case:** Market segmentation with "fuzzy" boundaries

```python
from sklearn.mixture import GaussianMixture

# Fit GMM
gmm = GaussianMixture(n_components=8, covariance_type='full')
gmm.fit(X_spatial)

# Get probabilistic assignments
probabilities = gmm.predict_proba(X_spatial)

# For each property, show top 3 likely clusters with probabilities
df['cluster_0_prob'] = probabilities[:, 0]
df['cluster_1_prob'] = probabilities[:, 1]
# ...
```

#### 3. Deep Learning for Spatial Data

**Graph Neural Networks (GNN)**
- **What:** Neural networks that operate on graph structures
- **Why:** Naturally captures spatial dependencies as graph edges
- **Architecture:** Properties = nodes, spatial proximity = edges
- **Library:** PyTorch Geometric or DGL

```python
import torch
from torch_geometric.nn import GCNConv

# Build spatial graph (k-nearest neighbors)
# Nodes: properties, Edges: spatial connections
edge_index = knn_graph(df[['lat', 'lon']], k=8)

# Define GNN
class SpatialGNN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = GCNConv(num_features, 64)
        self.conv2 = GCNConv(64, 32)
        self.fc = torch.nn.Linear(32, 1)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index).relu()
        return self.fc(x)

# Train and predict prices
model = SpatialGNN()
predictions = model(features, edge_index)
```

**Spatial Autoencoders**
- **What:** Neural networks for dimensionality reduction with spatial structure
- **Why:** Learn compressed representations preserving spatial relationships
- **Use Case:** Visualization, anomaly detection, feature engineering

#### 4. Spatial-Temporal Analysis

**Spatio-Temporal Clustering**
- **What:** Cluster properties considering both location AND time
- **Why:** Markets evolve - hotspots shift over time
- **Method:** ST-DBSCAN (spatio-temporal DBSCAN)

```python
# Add temporal dimension
df['datetime_numeric'] = pd.to_datetime(df['month']).astype(int) / 10**9

# 3D clustering: lat, lon, time
st_coords = df[['lat', 'lon', 'datetime_numeric']].values
st_clusterer = hdbscan.HDBSCAN(min_cluster_size=100)
st_labels = st_clusterer.fit_predict(st_coords)

# Visualize hotspot evolution over time
fig = px.scatter_3d(
    df, x='lon', y='lat', z='month',
    color=st_labels,
    title='Spatio-Temporal Hotspot Evolution',
    animation_frame='month'
)
```

**Predictive Hotspot Detection**
- **What:** Forecast where hotspots will emerge
- **Why:** Get ahead of market trends
- **Method:** LSTM + spatial lag features

```python
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# Create spatio-temporal features
df['spatial_lag_1m'] = df.groupby('planning_area')['price_psf'].shift(1)
df['spatial_lag_3m'] = df.groupby('planning_area')['price_psf'].shift(3)

# Train LSTM to predict future hotspot status
model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(12, n_features)),
    LSTM(32),
    Dense(1, activation='sigmoid')  # Probability of becoming hotspot
])

# Forecast hotspot probability 6 months ahead
future_hotspots = model.predict(future_features)
```

#### 5. Explainable AI (XAI) for Spatial Insights

**SHAP for Spatial Feature Importance**
- **What:** Quantifies how much each spatial feature contributes to predictions
- **Why:** Understand what drives prices in different areas
- **Visualization:** Spatial maps of SHAP values

```python
# Calculate SHAP values for each planning area
shap_maps = {}

for area in df['planning_area'].unique():
    area_data = df[df['planning_area'] == area]
    area_shap = explainer.shap_values(area_data[features])

    # Aggregate SHAP by feature
    shap_maps[area] = {
        'mrt_importance': area_shap[:, 0].mean(),
        'cbd_importance': area_shap[:, 1].mean(),
        # ...
    }

# Map: Which areas care most about MRT proximity?
fig = px.choropleth_mapbox(
    shap_df,
    geojson=areas_geojson,
    locations='planning_area',
    color='mrt_importance',
    title='Spatial Variation in MRT Importance (SHAP)',
    mapbox_style="carto-positron"
)
```

---

## Future Enhancements

- [ ] Add temporal LISA for changing hotspots over time
- [ ] Integrate transportation accessibility into clustering
- [ ] Add space-time pattern mining for trend detection
- [ ] Implement multiscale analysis (multiple H3 resolutions)

---

## References

- Getis, A., & Ord, J. K. (1992). The Analysis of Spatial Association by Use of Distance Statistics
- Anselin, L. (1995). Local Indicators of Spatial Association (LISA)
- H3: https://h3geo.org/

---

## See Also

- `docs/analytics/causal-inference-overview.md` - Complementary causal analysis methods
