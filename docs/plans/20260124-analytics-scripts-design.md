# Analytics Scripts Design Plan

**Date:** 2026-01-24
**Status:** Ready for Implementation

---

## Executive Summary

This plan documents the design for new spatial analytics and causal inference scripts, reorganization of existing analysis scripts into `scripts/analysis/`, and creation of an L4 pipeline to orchestrate all analysis scripts with a summary report.

---

## 1. New Analytics Scripts

### 1.1 Spatial Analytics Scripts

| Script | Method | Dependencies |
|--------|--------|--------------|
| `analyze_spatial_hotspots.py` | Getis-Ord Gi* statistic | H3, pandas, libpysal, esda |
| `analyze_spatial_autocorrelation.py` | Moran's I + LISA | H3, pandas, libpysal, esda |
| `analyze_h3_clusters.py` | DBSCAN on H3 grid + hotspot overlay | H3, pandas, scikit-learn |

### 1.2 Causal Inference Scripts

| Script | Method | Dependencies |
|--------|--------|--------------|
| `analyze_policy_impact.py` | Difference-in-Differences (DiD) | pandas, statsmodels |
| `analyze_lease_decay.py` (enhanced) | Survival analysis + PSM | pandas, lifelines, scikit-learn |

---

## 2. Script Reorganization

### 2.1 Move Existing Scripts

```
scripts/analyze_hdb_rental_market.py    → scripts/analysis/
scripts/analyze_feature_importance.py    → scripts/analysis/
scripts/analyze_amenity_impact.py       → scripts/analysis/
scripts/analyze_lease_decay.py          → scripts/analysis/
scripts/market_segmentation_advanced.py → scripts/analysis/
```

### 2.2 New Directory Structure

```
scripts/analysis/
  ├── analyze_hdb_rental_market.py       (moved)
  ├── analyze_feature_importance.py      (moved)
  ├── analyze_amenity_impact.py          (moved)
  ├── analyze_lease_decay.py             (moved, enhanced)
  ├── market_segmentation_advanced.py    (moved)
  ├── analyze_spatial_hotspots.py        (new)
  ├── analyze_spatial_autocorrelation.py (new)
  ├── analyze_h3_clusters.py             (new)
  └── analyze_policy_impact.py           (new)
```

### 2.3 Standard Script Pattern

All scripts must follow this pattern:

```python
#!/usr/bin/env python3
"""Short description of what this script does."""

import logging
import sys
from pathlib import Path

import pandas as pd

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main execution."""
    # ... script logic ...

    # Output summary JSON for L4 pipeline
    import json
    print(json.dumps({
        "script": "script_name",
        "status": "success",
        "key_findings": ["finding 1", "finding 2"],
        "outputs": ["path/to/output1.csv"],
        "duration_seconds": 45.2
    }))


if __name__ == "__main__":
    main()
```

---

## 3. L4 Pipeline Design

### 3.1 Location

`core/pipeline/L4_analysis.py`

### 3.2 Configuration

Add to `core/config.py`:

```python
class Config:
    # ... existing config ...

    # Analysis pipeline
    ANALYSIS_SCRIPTS_DIR = DATA_DIR.parent / "scripts" / "analysis"
    ANALYSIS_OUTPUT_DIR = DATA_DIR / "analysis"
    L4_REPORT_PATH = ANALYSIS_OUTPUT_DIR / "L4_summary_report.md"
```

### 3.3 Pipeline Workflow

```
L4_analysis.py
    │
    ├── Discover all *.py in scripts/analysis/
    ├── Filter: only scripts starting with "analyze_"
    ├── Sort: spatial scripts first, causal scripts second
    │
    ├── For each script:
    │   ├── Execute: uv run python <script>
    │   ├── Capture: stdout/stderr
    │   ├── Parse: JSON summary from script output
    │   ├── Log: success/failure with duration
    │   └── Collect: key findings and output paths
    │
    └── Generate summary report: data/analysis/L4_summary_report.md
        ├── Execution summary (scripts run, succeeded, failed)
        ├── Timing breakdown per script
        ├── Key findings from each script
        ├── Output file locations
        └── Error details (if any failed)
```

### 3.4 Script Execution Order

**Tier 1: Spatial Analytics** (need raw spatial data)
1. `analyze_spatial_hotspots.py`
2. `analyze_spatial_autocorrelation.py`
3. `analyze_h3_clusters.py`

**Tier 2: Market Analysis** (need aggregated metrics)
4. `analyze_hdb_rental_market.py`
5. `analyze_amenity_impact.py`

**Tier 3: Causal Inference** (need spatial outputs + metrics)
6. `analyze_policy_impact.py`
7. `analyze_lease_decay.py`

**Tier 4: ML/Modeling** (need full feature set)
8. `analyze_feature_importance.py`
9. `market_segmentation_advanced.py`

### 3.5 Summary Report Template

```markdown
# L4 Analysis Pipeline Summary Report

**Generated:** 2026-01-24 14:30:00
**Duration:** 127.5 seconds

## Execution Summary

| Metric | Value |
|--------|-------|
| Scripts Discovered | 9 |
| Scripts Executed | 9 |
| Succeeded | 9 |
| Failed | 0 |

## Script Results

### analyze_spatial_hotspots.py
- **Status:** ✅ Success
- **Duration:** 12.3s
- **Key Findings:**
  - 3 hotspots identified in Central region
  - Orchard: Gi* = 3.42, p < 0.01
  - 2 coldspots in Northern region
- **Outputs:** `data/analysis/analyze_spatial_hotspots/hotspots.geojson`

### analyze_spatial_autocorrelation.py
- **Status:** ✅ Success
- **Duration:** 8.7s
- **Key Findings:**
  - Moran's I = 0.342 (p < 0.001)
  - Significant spatial clustering present
- **Outputs:** `data/analysis/analyze_spatial_autocorrelation/moran_results.csv`

...

## Aggregate Insights

- **Strong spatial autocorrelation** detected across all regions
- **High-yield clusters** concentrated in Central area
- **Policy impact** shows significant effect post-2020 cooling measures

---

*Report generated by L4_analysis.py*
```

---

## 4. Output Directory Structure

```
data/analysis/
  ├── L4_summary_report.md
  ├── analyze_spatial_hotspots/
  │   ├── hotspots.geojson
  │   └── hotspot_stats.csv
  ├── analyze_spatial_autocorrelation/
  │   ├── moran_results.csv
  │   └── lisa_clusters.geojson
  ├── analyze_h3_clusters/
  │   ├── property_clusters.csv
  │   └── cluster_profiles.csv
  ├── analyze_policy_impact/
  │   ├── did_results.csv
  │   └── treatment_effects.csv
  ├── analyze_lease_decay/
  │   ├── survival_curves.csv
  │   └── psm_matched_pairs.csv
  ├── analyze_hdb_rental_market/
  ├── analyze_amenity_impact/
  ├── analyze_feature_importance/
  └── market_segmentation_advanced/
```

---

## 5. Dependencies

### New Python Packages

```toml
# Add to pyproject.toml
libpysal = ">=4.6.0"      # Spatial statistics
esda = ">=1.5.0"          # Spatial autocorrelation
lifelines = ">=0.27.0"    # Survival analysis
```

### Existing Packages Used

- pandas, numpy
- sklearn (clustering, matching)
- matplotlib, seaborn (visualization)
- geopandas, h3 (spatial)

---

## 6. Implementation Order

1. Create `scripts/analysis/` directory
2. Move existing analyze scripts to new location
3. Update imports in moved scripts (if needed)
4. Create new spatial analytics scripts
5. Enhance `analyze_lease_decay.py` with PSM
6. Create `analyze_policy_impact.py`
7. Update `core/config.py` with analysis paths
8. Create `core/pipeline/L4_analysis.py`
9. Create documentation files in `docs/analytics/`
10. Test L4 pipeline end-to-end

---

## 7. Documentation Files

Create the following in `docs/analytics/`:

- `spatial-analytics-overview.md` - Overview of spatial analysis methods
- `causal-inference-overview.md` - Overview of causal inference methods
- `script-reference.md` - Quick reference for all analysis scripts
- `l4-pipeline-usage.md` - How to run the L4 pipeline

Individual script docs:
- `analyze_spatial_hotspots.md`
- `analyze_spatial_autocorrelation.md`
- `analyze_h3_clusters.md`
- `analyze_policy_impact.md`
- `analyze_lease_decay.md`

---

## 8. Success Criteria

- [ ] All existing analyze scripts moved to `scripts/analysis/`
- [ ] 4 new analysis scripts created
- [ ] All scripts output JSON summary for L4 pipeline
- [ ] L4 pipeline runs all scripts sequentially
- [ ] L4 pipeline generates summary report
- [ ] All documentation files created in `docs/analytics/`

---

## 9. References

- **Getis-Ord Gi*:** https://pysal.org/libpysal/generated/libpysal.weights.G_Local.html
- **Moran's I:** https://pysal.org/esda/generated/esda.Moran.html
- **DBSCAN:** https://scikit-learn.org/stable/modules/clustering.html#dbscan
- **DiD:** https://statsmodels.org/stable/generated/statsmodels.regression.diff_diff.html
- **Survival Analysis:** https://lifelines.readthedocs.io/
- **PSM:** https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KernelDensity.html
