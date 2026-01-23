# Pipeline Consolidation Summary

**Date:** 2026-01-23
**Objective:** Consolidate redundant scripts and move notebook logic to `src/pipeline/`

## Overview

This document describes the structural changes made to consolidate the data pipeline codebase, eliminating redundancy and establishing a clean module hierarchy in `src/pipeline/`.

## Changes Made

### New Files Created (4)

| File | Lines | Purpose |
|------|-------|---------|
| `src/pipeline/_distance.py` | 180 | Shared distance utilities (haversine, H3 grid, KD-tree amenity calculations) |
| `src/pipeline/L2_rental.py` | 215 | Rental yield pipeline (HDB + Condo yields) |
| `src/pipeline/L2_features.py` | 540 | Feature engineering pipeline (properties, transactions, facilities) |
| `src/pipeline/L3_export.py` | 140 | Export pipeline (S3 upload, CSV export, unified dataset) |

### Files Modified (2)

| File | Change |
|------|--------|
| `scripts/run_pipeline.py` | Added L2, L2_rental, L2_features, L3 stage options |
| `notebooks/L2_sales_facilities.py` | Reduced from 554 lines to ~50 lines; now calls `run_l2_features_pipeline()` |

### Files Deleted (11)

```
scripts/run_l1_pipeline.py                    # Duplicates run_pipeline.py --stage L1
scripts/run_l2_features.py                    # Merged into L2_features.py
scripts/run_l2_features_multi_amenity.py      # Merged into L2_features.py
scripts/test_l1_minimal.py                    # Test script removed
scripts/test_logging_fix.py                   # Test script removed
scripts/test_geocoding.py                     # Test script removed
scripts/test_geocoding_checkpoint.py          # Test script removed
scripts/test_api_small.py                     # Test script removed
scripts/test_merge_scenario.py                # Test script removed
scripts/diagnose_l1_hang.py                   # Diagnostic script removed
scripts/reproduce_hang.py                     # Diagnostic script removed
```

## Architecture After Consolidation

```
src/pipeline/
├── __init__.py
├── L0_collect.py           # [EXISTING] Data collection from data.gov.sg
├── L1_process.py           # [EXISTING] Geocoding and transaction processing
├── L2_features.py          # [NEW] Property features from L2_sales_facilities
├── L2_rental.py            # [NEW] Rental yields from run_l2_pipeline.py
├── L3_export.py            # [NEW] Export and unified dataset creation
└── _distance.py            # [NEW] Shared spatial utilities

scripts/
├── run_pipeline.py         # [MODIFIED] Single entry point for all stages
├── download_hdb_rental_data.py     # [KEEP] Used by L2_rental
├── download_ura_rental_index.py    # [KEEP] Used by L2_rental
├── calculate_rental_yield.py       # [KEEP] Functions used by L2_rental
└── [other non-pipeline scripts]

notebooks/
├── L2_sales_facilities.py  # [MODIFIED] Now runs pipeline code
└── [other notebooks unchanged]
```

## New Pipeline Stages

### Stage: L2_rental
Downloads rental data and calculates rental yields for HDB and Condo properties.

```bash
uv run python scripts/run_pipeline.py --stage L2_rental --force
```

### Stage: L2_features
Creates property features including:
- Property table with planning areas
- Private property facilities (randomized amenities)
- Nearby facilities with distances
- Transaction sales
- Listing sales

```bash
uv run python scripts/run_pipeline.py --stage L2_features
```

### Stage: L2
Runs both L2_rental and L2_features pipelines.

```bash
uv run python scripts/run_pipeline.py --stage L2 --force
```

### Stage: L3
Exports L3 datasets to S3 and/or CSV.

```bash
uv run python scripts/run_pipeline.py --stage L3 --upload-s3 --export-csv
```

## Module Functions

### src/pipeline/_distance.py
- `haversine_distance()` - Calculate distance between two lat/lon points
- `generate_h3_grid_cell()` - Create H3 cell from coordinates
- `generate_grid_disk()` - Generate H3 grid disk
- `generate_polygon_from_cells()` - Create Shapely polygon from H3 cells
- `generate_polygons()` - Generate polygons for all properties
- `calculate_amenity_distances()` - Calculate distances and counts using KD-tree

### src/pipeline/L2_rental.py
- `download_hdb_rental_data()` - Download HDB rental data
- `download_ura_rental_index()` - Download URA rental index
- `calculate_hdb_rental_yield()` - Calculate HDB rental yields
- `calculate_condo_rental_yield()` - Calculate Condo rental yields
- `calculate_rental_yields()` - Combine and save yields
- `run_l2_rental_pipeline()` - Main entry point

### src/pipeline/L2_features.py
- `load_transaction_data()` - Load HDB/Condo/EC transactions
- `load_property_and_amenity_data()` - Load geocoded properties
- `load_planning_area()` - Load planning area shapefile
- `prepare_unique_properties()` - Filter and standardize properties
- `create_property_geodataframe()` - Create H3 polygons
- `create_amenity_geodataframe()` - Create point geometries
- `compute_amenity_distances()` - Spatial join for distances
- `compute_planning_area()` - Assign planning areas
- `extract_lease_info()` - Parse tenure strings
- `extract_two_digits()` - Parse floor ranges
- `process_private_transactions()` - Normalize Condo/EC data
- `process_hdb_transactions()` - Normalize HDB data
- `create_property_table()` - Create property master table
- `create_private_facilities()` - Generate facility assignments
- `create_nearby_facilities()` - Create nearby amenities table
- `create_transaction_sales()` - Combine transactions
- `create_listing_sales()` - Generate listing data
- `run_l2_features_pipeline()` - Main entry point

### src/pipeline/L3_export.py
- `load_l3_datasets()` - Load all L3 parquet files
- `create_unified_dataset()` - Join property with transactions/listings
- `upload_to_s3()` - Upload DataFrame to S3
- `export_to_csv()` - Export DataFrame to CSV
- `run_l3_export_pipeline()` - Main entry point

## Usage Examples

```bash
# Run L0 collection only
uv run python scripts/run_pipeline.py --stage L0

# Run L1 processing with parallel geocoding
uv run python scripts/run_pipeline.py --stage L1 --parallel

# Run L2 rental only (force re-download)
uv run python scripts/run_pipeline.py --stage L2_rental --force

# Run L2 features only
uv run python scripts/run_pipeline.py --stage L2_features

# Run full L2 pipeline
uv run python scripts/run_pipeline.py --stage L2 --force

# Run L3 export with S3 upload and CSV export
uv run python scripts/run_pipeline.py --stage L3 --upload-s3 --export-csv

# Run all stages
uv run python scripts/run_pipeline.py --stage all --force --parallel
```

## Benefits

1. **Reduced redundancy** - 2 L2 feature scripts merged into 1 module
2. **Clean architecture** - Pipeline logic in `src/pipeline/`, runners in `scripts/`
3. **Easier maintenance** - Single source of truth for each pipeline stage
4. **Better testability** - Functions can be imported and tested individually
5. **Notebook simplification** - L2_sales_facilities.py reduced from 554 to ~50 lines
6. **Consistent interface** - All stages use same patterns (run_X_pipeline functions)
