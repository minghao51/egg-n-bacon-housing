---
title: H3 Clusters Analysis Script
category: technical-reports
description: Discover natural property clusters using DBSCAN on H3 hex grid with spatial and attribute features
status: published
---

# H3 Clusters Analysis Script

**Script:** `scripts/analysis/analyze_h3_clusters.py`
**Purpose:** Discover natural property clusters using DBSCAN on H3 hex grid with spatial and attribute features

---

## Description

This script identifies natural market segments by clustering properties based on their geographic location and key attributes (price, yield, size, lease). It uses DBSCAN (Density-Based Spatial Clustering of Applications with Noise) to discover clusters of varying shapes and sizes, rather than imposing predefined segments.

---

## Usage

```bash
# Run with default settings
uv run python scripts/analysis/analyze_h3_clusters.py

# Run with custom parameters
uv run python scripts/analysis/analyze_h3_clusters.py --eps 0.5 --min-samples 10

# Run with custom features
uv run python scripts/analysis/analyze_h3_clusters.py --features price_psf,rental_yield,floor_area
```

### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--resolution` | int | 8 | H3 resolution |
| `--eps` | float | 0.5 | DBSCAN eps (neighborhood radius) |
| `--min-samples` | int | 10 | Minimum samples per cluster |
| `--features` | str | `price_psf,floor_area_sqm,rental_yield_pct,remaining_lease_months` | Features for clustering |

---

## Output

### Files Created

| File | Description |
|------|-------------|
| `data/analysis/analyze_h3_clusters/property_clusters.csv` | Each property with cluster assignment |
| `data/analysis/analyze_h3_clusters/cluster_profiles.csv` | Statistical profile per cluster |
| `data/analysis/analyze_h3_clusters/cluster_map.png` | Geographic cluster map |
| `data/analysis/analyze_h3_clusters/silhouette_plot.png` | Cluster quality assessment |

### Property Clusters Schema

```csv
property_id,lat,lon,cluster_id,cluster_name,price_psf,floor_area_sqm,rental_yield_pct,remaining_lease_months
HDB_001,1.3521,103.8198,0,Premium Central,580,75,4.2,85
HDB_002,1.4382,103.7890,1,Suburban Value,380,90,6.1,72
```

### Cluster Profiles Schema

```csv
cluster_id,cluster_name,count,percentage,mean_price_psf,mean_floor_area,mean_yield,mean_lease
0,Premium Central,145,8.2%,$520,68sqm,4.5%,82
1,Suburban Value,892,50.3%,$380,85sqm,6.2%,68
```

---

## Methodology

### H3 Aggregation

Properties are mapped to H3 hex cells at specified resolution, then aggregated to cell-level statistics (mean, median, count).

### DBSCAN Clustering

```
DBSCAN(eps, min_samples)

Parameters:
- eps: Maximum distance between two samples to be in the same cluster
- min_samples: Minimum samples within eps radius to form a core point
```

### Feature Scaling

Features are standardized before clustering:

```
z = (x - mean) / std
```

### Cluster Naming

Clusters are automatically named based on characteristics:

| Pattern | Name Template |
|---------|---------------|
| High price, high yield | "{Location} Premium" |
| Low price, high yield | "{Location} Value" |
| High price, low yield | "{Location} Luxury" |
| Low price, low yield | "{Location} Budget" |

---

## Example Results

### Sample Output

```
================================================================================
H3 CLUSTER ANALYSIS
================================================================================

H3 Resolution: 8
DBSCAN eps: 0.5
min_samples: 10
Features: price_psf, floor_area_sqm, rental_yield_pct, remaining_lease_months
Properties: 2,847
Cells: 623

--------------------------------------------------------------------------------
CLUSTERING RESULTS
--------------------------------------------------------------------------------
Clusters Found: 5
Noise Points: 89 (3.1%)

Cluster Sizes:
  Cluster 0 (Premium Central):    312 properties (11.0%)
  Cluster 1 (Suburban Value):     892 properties (31.3%)
  Cluster 2 (Urban Mid-Tier):     634 properties (22.3%)
  Cluster 3 (Luxury Core):        145 properties (5.1%)
  Cluster 4 (Budget Suburban):    775 properties (27.2%)

Silhouette Score: 0.67 (Good cluster separation)

--------------------------------------------------------------------------------
CLUSTER PROFILES
--------------------------------------------------------------------------------

Cluster 0: Premium Central
  Location: Orchard, Marina, Bukit Timah
  Mean Price PSF: $520 (±$45)
  Mean Floor Area: 68 sqm (±15)
  Mean Rental Yield: 4.5% (±0.8%)
  Mean Lease Remaining: 82 months (±12)

Cluster 1: Suburban Value
  Location: Woodlands, Yishun, Jurong West
  Mean Price PSF: $380 (±$32)
  Mean Floor Area: 85 sqm (±20)
  Mean Rental Yield: 6.2% (±1.1%)
  Mean Lease Remaining: 68 months (±18)

Cluster 2: Urban Mid-Tier
  Location: Toa Payoh, Bishan, Ang Mo Kio
  Mean Price PSF: $445 (±$38)
  Mean Floor Area: 75 sqm (±18)
  Mean Rental Yield: 5.4% (±0.9%)
  Mean Lease Remaining: 72 months (±15)

...

================================================================================
```

---

## Integration

### With L4 Pipeline

```json
{
  "script": "analyze_h3_clusters",
  "status": "success",
  "key_findings": [
    "5 natural market clusters identified",
    "Cluster 1 (Suburban Value): 892 properties, 6.2% avg yield",
    "Cluster 3 (Luxury Core): 145 properties, $520/sqf avg price",
    "Silhouette score: 0.67 (good separation)"
  ],
  "outputs": [
    "data/analysis/analyze_h3_clusters/property_clusters.csv",
    "data/analysis/analyze_h3_clusters/cluster_profiles.csv"
  ],
  "duration_seconds": 23.4
}
```

### With Other Scripts

- **Uses:** `analyze_spatial_hotspots.py` results (hotspot overlays)
- **Complements:** `market_segmentation_advanced.py` (k-means alternative)
- **Input to:** `analyze_policy_impact.py` (cluster-based treatment groups)

---

## Configuration

```python
# In core/config.py
ANALYSIS_H3_CLUSTERS_RESOLUTION = 8
ANALYSIS_H3_CLUSTERS_EPS = 0.5
ANALYSIS_H3_CLUSTERS_MIN_SAMPLES = 10
ANALYSIS_H3_CLUSTERS_FEATURES = [
    "price_psf",
    "floor_area_sqm",
    "rental_yield_pct",
    "remaining_lease_months"
]
```

---

## Dependencies

```
scikit-learn>=1.3.0    # DBSCAN, silhouette score
h3>=3.7.0              # H3 grid
pandas>=2.0.0
numpy>=1.24.0
geopandas>=0.14.0
matplotlib>=3.7.0
seaborn>=0.12.0
```

---

## Choosing Parameters

### EPS Selection

The optimal eps can be found using the k-distance graph:

```python
from sklearn.neighbors import NearestNeighbors
import numpy as np

k = 4  # min_samples - 1
nn = NearestNeighbors(n_neighbors=k)
nn.fit(X_scaled)
distances, indices = nn.kneighbors(X_scaled)

# Plot k-distances and find elbow
distances = np.sort(distances[:, k-1])
```

### Min Samples

| Min Samples | Effect |
|-------------|--------|
| 5-10 | More clusters, more noise |
| 10-20 | Conservative clustering |
| 20+ | Only dense regions form clusters |

---

## Troubleshooting

### Too Many Clusters

Increase eps or decrease min_samples:

```bash
uv run python scripts/analysis/analyze_h3_clusters.py --eps 0.7 --min-samples 5
```

### Too Few Clusters (All Noise)

Decrease eps or decrease min_samples:

```bash
uv run python scripts/analysis/analyze_h3_clusters.py --eps 0.3 --min-samples 5
```

### Low Silhouette Score (<0.5)

- Add more distinguishing features
- Increase eps to merge similar clusters
- Remove outlier-prone features (floor_area)

---

## See Also

- `docs/analytics/spatial-analytics-overview.md` - Method background
- `scripts/analysis/analyze_spatial_hotspots.py` - Hotspot analysis
- `scripts/market_segmentation_advanced.py` - K-means alternative
