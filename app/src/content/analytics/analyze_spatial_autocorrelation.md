# Spatial Autocorrelation Analysis Script

**Script:** `scripts/analysis/analyze_spatial_autocorrelation.py`
**Purpose:** Quantify spatial clustering strength using Moran's I and identify local clusters using LISA

---

## Description

This script measures global and local spatial autocorrelation in Singapore housing data. The global Moran's I statistic quantifies overall clustering strength, while Local Indicators of Spatial Association (LISA) identify specific clusters and outliers.

---

## Usage

```bash
# Run the script
uv run python scripts/analysis/analyze_spatial_autocorrelation.py

# Run with custom variable
uv run python scripts/analysis/analyze_spatial_autocorrelation.py --variable price_psf

# Run permutation test
uv run python scripts/analysis/analyze_spatial_autocorrelation.py --permutations 999
```

### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--variable` | str | `monthly_rent` | Variable to analyze |
| `--permutations` | int | 99 | Number of permutations for significance test |
| `--significance` | float | 0.05 | Significance level (p-value threshold) |

---

## Output

### Files Created

| File | Description |
|------|-------------|
| `data/analysis/analyze_spatial_autocorrelation/moran_results.csv` | Global Moran's I results |
| `data/analysis/analyze_spatial_autocorrelation/lisa_clusters.geojson` | LISA cluster map |
| `data/analysis/analyze_spatial_autocorrelation/lisa_results.csv` | LISA statistics per cell |
| `data/analysis/analyze_spatial_autocorrelation/moran_scatter.png` | Moran scatter plot |

### Moran Results Schema

```csv
variable,morans_i,expected_i,variance,z_score,p_value,significance
monthly_rent,0.342,-0.0016,0.0028,8.45,<0.001,***
```

### LISA Results Schema

```csv
h3_index,lisa_cluster,lisa_z,p_value,local_moran,median_rent
8a2831a0a6bfff3,HH,3.21,0.001,0.045,3200
```

### LISA Cluster Values

| Value | Meaning | Description |
|-------|---------|-------------|
| `HH` | High-High | High value surrounded by high values |
| `LH` | Low-High | Low value surrounded by high values |
| `HL` | High-Low | High value surrounded by low values |
| `LL` | Low-Low | Low value surrounded by low values |
| `NS` | Not Significant | No spatial pattern |

---

## Methodology

### Global Moran's I

```
I = (N / W) * ΣΣ(w_ij * (x_i - x̄) * (x_j - x̄)) / Σ(x_i - x̄)²
```

Where:
- N = number of observations
- W = sum of all weights
- w_ij = spatial weight between i and j
- x = variable value
- x̄ = mean of x

### Interpretation

| Moran's I | Interpretation |
|-----------|----------------|
| 0.5 - 1.0 | Strong positive clustering |
| 0.3 - 0.5 | Moderate positive clustering |
| 0.1 - 0.3 | Weak positive clustering |
| -0.1 - 0.1 | Random (no spatial pattern) |
| -0.3 - -0.1 | Weak negative clustering |
| -0.5 - -0.3 | Moderate negative clustering |
| -1.0 - -0.5 | Strong negative clustering |

### LISA Statistics

Local Moran's I for each location:

```
I_i = (x_i - x̄) * Σ(w_ij * (x_j - x̄))
```

High positive values indicate clusters (HH or LL); negative values indicate outliers (HL or LH).

---

## Example Results

### Sample Output

```
================================================================================
SPATIAL AUTOCORRELATION ANALYSIS
================================================================================

Variable: monthly_rent
Date Range: 2024-01 to 2025-01
H3 Resolution: 8
Total Cells: 847
Cells with Data: 623

--------------------------------------------------------------------------------
GLOBAL MORAN'S I
--------------------------------------------------------------------------------
Moran's I:              0.342
Expected I:            -0.0016
Variance:               0.0028
Z-Score:                8.45
P-Value:               <0.001
Significance:          ***

Interpretation: Moderate positive spatial autocorrelation

--------------------------------------------------------------------------------
LISA CLUSTER SUMMARY
--------------------------------------------------------------------------------
HH Clusters (Hotspots):      18 cells (2.9%)
LH Clusters (Outliers):       7 cells (1.1%)
HL Clusters (Outliers):       5 cells (0.8%)
LL Clusters (Coldspots):     15 cells (2.4%)
Not Significant:            578 cells (92.7%)

Top HH Clusters:
  1. Orchard - Marina (Gi* = 3.89, p < 0.001)
  2. Bukit Timah (Gi* = 3.12, p < 0.01)
  3. River Valley (Gi* = 2.87, p < 0.01)

Top LL Clusters:
  1. Woodlands North (Gi* = -3.21, p < 0.01)
  2. Yishun Central (Gi* = -2.98, p < 0.01)
  3. Sembawang (Gi* = -2.67, p < 0.01)

================================================================================
```

---

## Integration

### With L4 Pipeline

```json
{
  "script": "analyze_spatial_autocorrelation",
  "status": "success",
  "key_findings": [
    "Moran's I = 0.342 (p < 0.001)",
    "Significant spatial clustering detected",
    "18 HH clusters (hotspots) identified",
    "15 LL clusters (coldspots) identified"
  ],
  "outputs": [
    "data/analysis/analyze_spatial_autocorrelation/moran_results.csv",
    "data/analysis/analyze_spatial_autocorrelation/lisa_clusters.geojson"
  ],
  "duration_seconds": 12.7
}
```

### With Other Scripts

- **Complements:** `analyze_spatial_hotspots.py` (same methods, different outputs)
- **Input to:** `analyze_policy_impact.py` (identify treatment/control areas)

---

## Configuration

```python
# In core/config.py
ANALYSIS_SPATIAL_AUTOCORRELATION_VARIABLE = "monthly_rent"
ANALYSIS_SPATIAL_AUTOCORRELATION_PERMUTATIONS = 99
ANALYSIS_SPATIAL_AUTOCORRELATION_SIGNIFICANCE = 0.05
```

---

## Dependencies

```
libpysal>=4.6.0    # Spatial weights
esda>=1.5.0        # Moran's I and LISA
h3>=3.7.0          # H3 grid
geopandas>=0.14.0  # GeoJSON handling
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
```

---

## Moran Scatter Plot

The Moran scatter plot shows the relationship between a variable and its spatial lag:

```
    High Values
        ^
        |    HH (hotspots)
        |   /|
        |  / |
        | /  |
        |/   |
  -----+-----+-----> Spatial Lag
        |   /|       (neighboring values)
        |  / |
        | /  |
        |/   |
        |    LL (coldspots)
        |
     Low Values
```

Quadrants:
- **Upper-Right (HH):** High values surrounded by high values
- **Lower-Left (LL):** Low values surrounded by low values
- **Lower-Right (HL):** High values surrounded by low values
- **Upper-Left (LH):** Low values surrounded by high values

---

## Troubleshooting

### Low Significance

Increase permutations for more precise p-values:

```bash
uv run python scripts/analysis/analyze_spatial_autocorrelation.py --permutations 999
```

### No Spatial Pattern Detected

- Check data coverage (sparse areas reduce power)
- Try different variable (price_psf vs monthly_rent)
- Lower H3 resolution for more neighbors per cell

---

## See Also

- `docs/analytics/spatial-analytics-overview.md` - Method background
- `scripts/analysis/analyze_spatial_hotspots.py` - Getis-Ord Gi* method
- `scripts/analysis/analyze_h3_clusters.py` - DBSCAN clustering
