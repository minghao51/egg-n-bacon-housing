# Analysis Pipeline (L4) - Data Architecture

**Status**: Active

---

## Overview

The L4 Analysis Pipeline runs exploratory data analysis (EDA) and deep-dive analysis scripts on pipeline outputs. It provides console summaries and saves standardized results to a unified storage location.

---

## Pipeline Stages

### L0: Data Collection
- **Source**: data.gov.sg API, OneMap API, Wikipedia
- **Output**: `data/pipeline/L0/`

### L1: Data Processing
- Geocoding, cleaning, amenity enrichment
- **Output**: `data/pipeline/L1/`

### L2: Feature Engineering
- MRT distances, rental yields, CBD distance
- **Output**: `data/pipeline/L2/`

### L3: Unified Dataset
- Combined HDB/Condo/EC transactions
- **Output**: `data/pipeline/L3/housing_unified.parquet`

### L4: Analysis Pipeline
- **Phase 1**: EDA (console summaries)
- **Phase 2**: Deep-dive analysis scripts
- **Phase 3**: Report generation

### L5: Metrics
- Planning area level aggregations

---

## L4 Analysis Pipeline

### Phase 1: Exploratory Data Analysis (EDA)

Runs at the start of L4 to provide quick data overviews:

**Script**: `scripts/analytics/analysis/market/analyze_investment_eda.py`

**Outputs (Console)**:
- Data quality overview (record counts, date ranges)
- Planning area transaction volumes
- Price appreciation (CAGR) by area
- Rental yield analysis
- Investment attractiveness scores
- Market momentum (YoY changes)
- Amenity impact correlations

### Phase 2: Deep-Dive Analysis

Runs analysis scripts from `scripts/analytics/analysis/`:

| Category | Scripts |
|----------|---------|
| Market | `analyze_hdb_rental_market.py`, `analyze_lease_decay.py`, `analyze_policy_impact.py` |
| Amenity | `analyze_amenity_impact.py`, `analyze_feature_importance.py` |
| Spatial | `analyze_spatial_hotspots.py`, `analyze_spatial_autocorrelation.py`, `analyze_h3_clusters.py` |
| Causal | `analyze_causal_did_enhanced.py`, `analyze_rd_policy_timing.py` |
| School | `analyze_school_impact.py`, `analyze_school_rdd.py` |
| MRT | `analyze_mrt_impact.py`, `analyze_mrt_heterogeneous.py` |

### Phase 3: Report Generation

Generates `data/analysis/L4_summary_report.md` with execution summary.

---

## Unified Results Storage

### Directory Structure

```
data/analysis/
├── results/                    # Unified results storage
│   ├── index.json            # Central index
│   ├── eda/                 # EDA outputs
│   ├── market/              # Market analysis outputs
│   ├── amenity/             # Amenity analysis outputs
│   ├── spatial/             # Spatial analysis outputs
│   └── ...                  # Other categories
└── L4_summary_report.md     # Pipeline execution report
```

### Using the Storage API

```python
from scripts.core.stages.helpers.analysis_helpers import (
    save_analysis_result,
    load_analysis_result,
    list_analysis_results,
)

# Save a result
save_analysis_result(
    df=result_df,
    category="market",
    name="rental_yield_by_area",
    description="Rental yield statistics by planning area"
)

# Load a result
df = load_analysis_result("market", "rental_yield_by_area")

# List all results
results = list_analysis_results()
# Returns: {"eda": [...], "market": [...], "amenity": [...]}
```

### Index Schema

`index.json` tracks all saved results:

```json
{
  "eda": [
    {
      "name": "price_appreciation_by_area",
      "file": "data/analysis/results/eda/price_appreciation_by_area.parquet",
      "row_count": 25,
      "updated_at": "2026-02-19T12:00:00",
      "description": "Price appreciation (CAGR) by planning area"
    }
  ],
  "market": [...]
}
```

---

## Available Results

### EDA Results

| Name | Description |
|------|-------------|
| `price_appreciation_by_area` | CAGR by planning area (2015-2025) |
| `rental_yield_by_area` | Rental yield statistics by area |
| `investment_scores` | Combined appreciation + yield scores |
| `market_momentum` | YoY changes by area |

### Market Results

| Name | Description |
|------|-------------|
| `rental_trends_by_year` | Median rent by year |
| `rental_by_town` | Rental stats by town (2024+) |
| `rental_by_flat_type` | Rental stats by flat type |
| `rental_vs_resale_comparison` | Yield by town + flat type |

### Amenity Results

| Name | Description |
|------|-------------|
| `temporal_comparison` | Feature importance by period |
| `within_town_effects` | MRT importance by town |
| `grid_analysis` | 500m x 500m grid analysis |
| `mrt_distance_stratification` | Price by MRT distance bands |
| `amenity_summary_stats` | Summary statistics |

---

## Running L4

### Full Pipeline

```bash
uv run python scripts/run_pipeline.py --stage L4
```

### Via L4_analysis.py directly

```bash
uv run python scripts/core/stages/L4_analysis.py
```

### Run EDA only

```bash
uv run python scripts/analytics/analysis/market/analyze_investment_eda.py
```

---

## Data Sources

| Source | Type | API/Location |
|--------|------|--------------|
| data.gov.sg | HDB transactions, rental data | REST API |
| OneMap | Geocoding, planning areas | REST API |
| Wikipedia | Shopping malls, schools | Web scraping |
| Google Maps | Geocoding fallback | API |

---

## Key Files

| Purpose | File |
|---------|------|
| Pipeline runner | `scripts/run_pipeline.py` |
| L4 orchestration | `scripts/core/stages/L4_analysis.py` |
| EDA script | `scripts/analytics/analysis/market/analyze_investment_eda.py` |
| Results helper | `scripts/core/stages/helpers/analysis_helpers.py` |
| Configuration | `scripts/core/config.py` |
