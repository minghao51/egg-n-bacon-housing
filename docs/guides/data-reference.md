# Data Reference

**Status**: Production Ready

---

## Overview

This document provides a quick reference for the housing data available in the pipeline.

---

## Datasets

### L0: Raw Data

| Dataset | Source | Records |
|---------|--------|---------|
| `raw_datagov_*` | data.gov.sg API | ~100K |
| `raw_onemap_*` | OneMap API | ~50 |
| `raw_wiki_shopping_mall` | Wikipedia | ~200 |

### L1: Processed

| Dataset | Description | Records |
|---------|-------------|---------|
| `housing_hdb_transaction` | HDB resale transactions | 969,748 |
| `housing_condo_transaction` | Condo transactions | 49,052 |
| `amenity_v2` | Amenities (6 categories) | 5,569 |

### L2: Feature Engineered

| Dataset | Description |
|---------|-------------|
| `housing_multi_amenity_features` | Distance features to amenities |
| `rental_yield` | Rental yield calculations |

### L3: Precomputed

| Dataset | Description |
|---------|-------------|
| `metrics_monthly` | Monthly market metrics |
| `market_summary` | Aggregated stats by property_type/period/tier |

---

## Analysis Results (Unified Storage)

Results from L4 analysis pipeline are stored in `data/analysis/results/`:

| Category | Description |
|----------|-------------|
| `eda/` | EDA outputs (appreciation, yields, scores) |
| `market/` | Market analysis (rental trends) |
| `amenity/` | Amenity impact analysis |
| `spatial/` | Spatial analysis results |

### Using Results

```python
from scripts.core.stages.helpers.analysis_helpers import (
    save_analysis_result,
    load_analysis_result,
    list_analysis_results,
)

# Load a result
df = load_analysis_result("eda", "investment_scores")

# List all available results
results = list_analysis_results()
```

See **[L4 Analysis Pipeline](./l4-analysis-pipeline.md)** for details.

---

## Loading Data

```python
from scripts.core.data_helpers import load_parquet

# Load any dataset
df = load_parquet("L1_housing_hdb_transaction")
df = load_parquet("L2_rental_yield")
```

---

## Date Ranges

- **HDB Transactions**: 1990-01 to 2026-01 (36 years)
- **Condo Transactions**: ~2000-2026
- **Rental Data**: 2021-01 to 2025-12

---

## Key Fields

### HDB Transactions
- `month`, `town`, `flat_type`, `floor_area_sqm`, `resale_price`, `remaining_lease_months`

### Condo Transactions
- `Project Name`, `Transacted Price`, `Area (SQM)`, `Sale Date`, `Postal District`

### Amenities
- `name`, `type`, `lat`, `lon`

---
