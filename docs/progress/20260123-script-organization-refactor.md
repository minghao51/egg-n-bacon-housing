# Progress Update: Script Organization Refactor

**Date**: 2026-01-23
**Status**: ✅ Complete

---

## Overview

Refactored the script organization to follow a cleaner architecture where:
- **Dashboard-specific scripts** live in `scripts/dashboard/` (used by Streamlit)
- **Pipeline scripts** live in `scripts/` (importable by pipeline modules)

---

## Changes Made

### Directory Structure

```
scripts/
├── dashboard/
│   └── create_l3_unified_dataset.py   # Streamlit dashboard script
├── download_hdb_rental_data.py        # Pipeline script (importable + runnable)
├── download_ura_rental_index.py       # Pipeline script (importable + runnable)
└── ...other pipeline scripts...
```

### Key Changes

1. **Created `scripts/dashboard/` directory**
   - Contains `create_l3_unified_dataset.py` - the main script for creating the L3 unified dataset
   - Referenced by Streamlit apps and documentation

2. **Updated `src/pipeline/L2_rental.py` imports**
   - Changed from `from scripts.download_hdb_rental_data import ...`
   - Pipeline modules can now import from `scripts.download_hdb_rental_data`

3. **Added `sys.path` setup to scripts**
   - All scripts in `scripts/` add project root to `sys.path` for `src` imports
   - Enables running scripts directly: `uv run python scripts/download_hdb_rental_data.py`

4. **Added precomputed summary tables** (2026-01-23)
   - `market_summary.parquet` - Aggregated stats by property_type/period/tier
   - `tier_thresholds_evolution.parquet` - Tier thresholds over time
   - `planning_area_metrics.parquet` - Planning area metrics
   - `lease_decay_stats.parquet` - HDB lease decay statistics
   - `rental_yield_top_combos.parquet` - Top rental yield combinations

5. **Added cached loaders to `src/data_loader.py`**
   - `load_market_summary()`
   - `load_tier_thresholds()`
   - `load_planning_area_metrics()`
   - `load_lease_decay_stats()`
   - `load_rental_yield_top_combos()`

---

## Benefits

1. **Cleaner architecture** - Dashboard scripts are separated from pipeline scripts
2. **Easier imports** - Pipeline modules use `scripts.xxx` syntax
3. **Precomputed tables** - Faster Streamlit app loading (36-114 rows vs 911K records)
4. **Consistent metrics** - All visualizations use precomputed aggregations

---

## Files Modified

- `scripts/dashboard/create_l3_unified_dataset.py` - Main L3 pipeline with precomputation
- `scripts/download_hdb_rental_data.py` - Updated with sys.path setup
- `scripts/download_ura_rental_index.py` - Updated with sys.path setup
- `src/pipeline/L2_rental.py` - Updated imports
- `src/data_loader.py` - Added cached loaders for precomputed tables
- `docs/guides/20250120-architecture.md` - Updated documentation

---

## Commands

```bash
# Run L3 unified dataset creation
uv run python scripts/create_l3_unified_dataset.py

# Run HDB rental data download
uv run python scripts/download_hdb_rental_data.py

# Run URA rental index download
uv run python scripts/download_ura_rental_index.py
```

---

## Related Documents

- `docs/guides/20250120-architecture.md` - Architecture documentation
- `docs/progress/20260122-L3-Integration-Complete.md` - L3 integration details
