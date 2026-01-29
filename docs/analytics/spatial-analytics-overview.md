# Spatial Analytics Overview

**Date:** 2026-01-24
**Scripts:** `analyze_spatial_hotspots.py`, `analyze_spatial_autocorrelation.py`, `analyze_h3_clusters.py`

---

## Executive Summary

Spatial analytics methods identify statistically significant patterns in geographic data. Three complementary scripts analyze spatial relationships in Singapore housing data:

1. **Hotspot Analysis** - Find high/low value clusters using Getis-Ord Gi*
2. **Spatial Autocorrelation** - Measure overall clustering strength with Moran's I
3. **H3 Clustering** - Discover natural property groups using DBSCAN on hex grids

---

## Methods

### 1. Getis-Ord Gi* (Hotspot Analysis)

**Purpose:** Identify statistically significant hot spots (high values) and cold spots (low values).

**How it works:**
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

**Purpose:** Quantify overall spatial clustering strength (are similar values near each other?).

**How it works:**
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

**Purpose:** Identify local clusters (HH, LH, HL, LL) and spatial outliers.

**How it works:**
- Decomposes global Moran's I into local contributions
- Four classifications:
  - **HH:** High value surrounded by high values (hotspot)
  - **LL:** Low value surrounded by low values (coldspot)
  - **HL:** High value surrounded by low values (outlier)
  - **LH:** Low value surrounded by high values (outlier)

**Output:**
- `lisa_clusters.geojson` - Cluster map with HH/LH/HL/LL classifications

### 4. H3 Clustering with DBSCAN

**Purpose:** Discover natural property clusters based on location and attributes.

**How it works:**
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
from core.config import Config

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
- `docs/analytics/script-reference.md` - Quick reference for all scripts
