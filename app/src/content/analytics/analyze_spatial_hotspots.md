---
title: Spatial Hotspots Analysis
category: advanced
description: Spatial clustering and hotspot identification
status: published
---

# Spatial Analytics Script

**Script:** `scripts/analysis/analyze_spatial_hotspots.py`
**Purpose:** Identify statistically significant high/low rental price clusters using Getis-Ord Gi* statistic

---

## Description

This script performs hotspot analysis on Singapore HDB rental data to identify geographic clusters of high and low rental prices. It uses the Getis-Ord Gi* statistic, which is a local spatial autocorrelation measure that identifies hot spots (high values surrounded by high values) and cold spots (low values surrounded by low values).

The analysis works at the H3 hex grid level, providing consistent spatial units for comparison across the island.

---

## Usage

```bash
# Run the script
uv run python scripts/analysis/analyze_spatial_hotspots.py

# Run with custom H3 resolution
uv run python scripts/analysis/analyze_spatial_hotspots.py --resolution 9
```

### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--resolution` | int | 8 | H3 resolution (7-10) |
| `--variable` | str | `monthly_rent` | Variable to analyze |
| `--min-neighbors` | int | 5 | Minimum neighbors for weights |

---

## Output

### Files Created

| File | Description |
|------|-------------|
| `data/analysis/analyze_spatial_hotspots/hotspots.geojson` | GeoJSON with hotspot classifications |
| `data/analysis/analyze_spatial_hotspots/hotspot_stats.csv` | Gi* statistics per hex cell |
| `data/analysis/analyze_spatial_hotspots/hotspot_map.png` | Visualization map |

### GeoJSON Schema

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "h3_index": "8a2831a0a6bfff3",
        "gi_star": 3.42,
        "p_value": 0.001,
        "classification": "hotspot",
        "confidence": "99%",
        "median_rent": 2800,
        "cell_count": 45
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [...]
      }
    }
  ]
}
```

### Classification Values

| Value | Meaning |
|-------|---------|
| `hotspot` | High rent cluster (Gi* > 2.58, p < 0.01) |
| `weak_hotspot` | Moderate high cluster (Gi* > 1.96, p < 0.05) |
| `not_significant` | No significant pattern |
| `weak_coldspot` | Moderate low cluster (Gi* < -1.96, p < 0.05) |
| `coldspot` | Low rent cluster (Gi* < -2.58, p < 0.01) |

---

## Methodology

### Getis-Ord Gi* Statistic

The Gi* statistic for location i is:

```
Gi* = Σ(w_ij * x_j) / Σ(x_j)
```

Where:
- w_ij is the spatial weight between locations i and j
- x_j is the value at location j

The statistic is normalized to produce a z-score:

```
Z(Gi*) = (Gi* - E[Gi*]) / √(Var(Gi*))
```

### H3 Grid

- **Resolution 8:** ~0.5 km² per hex cell
- **Recommended for:** Town-level analysis
- **Cell count:** ~500-1000 cells for Singapore

---

## Example Results

### Sample Output

```
================================================================================
SPATIAL HOTSPOT ANALYSIS RESULTS
================================================================================

Date Range: 2024-01 to 2025-01
H3 Resolution: 8
Total Cells: 847
Cells with Data: 623

Hotspot Summary:
  Hotspots (99% confidence): 12 cells
  Weak Hotspots (95% confidence): 23 cells
  Coldspots (99% confidence): 8 cells
  Weak Coldspots (95% confidence): 15 cells
  Not Significant: 565 cells

Top 5 Hotspots:
  1. Orchard (Gi* = 4.21, p < 0.001) - Median Rent: $3,200
  2. Marina South (Gi* = 3.89, p < 0.001) - Median Rent: $3,450
  3. Bukit Timah (Gi* = 3.45, p < 0.001) - Median Rent: $3,100
  4. River Valley (Gi* = 3.12, p < 0.01) - Median Rent: $3,050
  5. Newton (Gi* = 2.87, p < 0.01) - Median Rent: $2,950

Top 5 Coldspots:
  1. Woodlands (Gi* = -3.21, p < 0.01) - Median Rent: $2,100
  2. Yishun (Gi* = -2.98, p < 0.01) - Median Rent: $2,050
  3. Sembawang (Gi* = -2.67, p < 0.01) - Median Rent: $2,000
  4. Choa Chu Kang (Gi* = -2.34, p < 0.05) - Median Rent: $2,150
  5. Jurong West (Gi* = -2.12, p < 0.05) - Median Rent: $2,200

================================================================================
```

---

## Integration

### With L4 Pipeline

The script outputs a JSON summary for the L4 pipeline:

```json
{
  "script": "analyze_spatial_hotspots",
  "status": "success",
  "key_findings": [
    "3 hotspots identified in Central region",
    "Hotspot A: Orchard (Gi* = 4.21, p < 0.001)",
    "Hotspot B: Marina South (Gi* = 3.89, p < 0.001)",
    "5 coldspots identified in Northern region",
    "Coldspot A: Woodlands (Gi* = -3.21, p < 0.01)"
  ],
  "outputs": [
    "data/analysis/analyze_spatial_hotspots/hotspots.geojson",
    "data/analysis/analyze_spatial_hotspots/hotspot_stats.csv"
  ],
  "duration_seconds": 15.3
}
```

### With Other Scripts

- **Input to:** `analyze_h3_clusters.py` (clustering on hotspot results)
- **Complements:** `analyze_spatial_autocorrelation.py` (global Moran's I)

---

## Configuration

```python
# In core/config.py or .env
ANALYSIS_SPATIAL_HOTSPOTS_RESOLUTION = 8
ANALYSIS_SPATIAL_HOTSPOTS_MIN_NEIGHBORS = 5
```

---

## Dependencies

```
libpysal>=4.6.0    # Spatial weights
esda>=1.5.0        # Gi* statistic
h3>=3.7.0          # H3 grid
geopandas>=0.14.0  # GeoJSON handling
pandas>=2.0.0
numpy>=1.24.0
```

---

## Troubleshooting

### Low Neighbor Count

If cells have too few neighbors, increase `--min-neighbors`:

```bash
uv run python scripts/analysis/analyze_spatial_hotspots.py --min-neighbors 8
```

### Sparse Data Coverage

For sparse areas, use lower resolution:

```bash
uv run python scripts/analysis/analyze_spatial_hotspots.py --resolution 7
```

---

## See Also

- `docs/analytics/spatial-analytics-overview.md` - Method background
- `scripts/analysis/analyze_spatial_autocorrelation.py` - Complementary analysis
- `scripts/analysis/analyze_h3_clusters.py` - Cluster discovery
