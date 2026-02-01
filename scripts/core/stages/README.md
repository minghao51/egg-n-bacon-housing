# Data Pipeline Stages

This directory contains the core data processing pipeline for Singapore housing analytics. Each stage transforms data and outputs to `data/pipeline/L{stage}/`.

---

## Pipeline Architecture

```
L0 (Collection) → L1 (Processing) → L2 (Features) → L3 (Export) → L4 (Analysis) → L5 (Metrics)
                    ↓
                  Webapp
```

---

## L0: Data Collection (`L0_collect.py`)

**Purpose:** Fetch raw data from data.gov.sg API and load CSV files

**Inputs:**
- data.gov.sg API endpoints (private property transactions, rental indices, price indices)
- Manual CSV files: `data/manual/csv/ResaleFlatPrices/*.csv`

**Outputs:** `data/pipeline/L0/`
- `raw_datagov_general_sale.parquet` - Private property transactions (rest of central region)
- `raw_datagov_rental_index.parquet` - Private residential property rental index
- `raw_datagov_median_price_via_property_type.parquet` - Median annual value and property tax
- `raw_datagov_private_transactions_property_type.parquet` - Private transactions (whole SG)
- `raw_datagov_resale_flat_all.parquet` - HDB resale flat prices (all CSV files combined)

**Key Functions:**
- `collect_all_datagovsg()` - Main entry point, fetches all datasets
- `fetch_datagovsg_dataset()` - Generic API fetcher with pagination support
- `load_resale_flat_prices()` - Loads and combines HDB resale CSV files

---

## L1: Data Processing (`L1_process.py`)

**Purpose:** Load transactions, extract addresses, geocode using OneMap API

**Inputs:**
- URA CSV files: `data/manual/csv/*.csv` (EC, condo transactions)
- HDB transactions: `data/pipeline/L0/raw_datagov_resale_flat_all.parquet`
- OneMap geocoding API (requires credentials in `.env`)

**Outputs:** `data/pipeline/L1/`
- `L1_housing_ec_transaction.parquet` - EC transactions
- `L1_housing_condo_transaction.parquet` - Condo transactions
- `L1_housing_hdb_transaction.parquet` - HDB transactions

**Outputs:** `data/pipeline/L2/`
- `L2_housing_unique_full_searched.parquet` - All geocoding results (including fuzzy matches)
- `L2_housing_unique_searched.parquet` - Filtered to best matches only (search_result == 0)

**Key Functions:**
- `run_processing_pipeline()` - Main entry point
- `load_and_save_transaction_data()` - Loads URA/HDB CSV files
- `prepare_unique_addresses()` - Extracts unique property addresses
- `geocode_addresses()` - Batch geocoding with OneMap API (parallel or sequential)
- `process_geocoded_results()` - Filters and saves geocoded data

**Note:** Uses caching and checkpointing to avoid re-geocoding known addresses

---

## L2: Feature Engineering (`L2_features.py`)

**Purpose:** Generate spatial features, compute amenity distances, create property tables

**Inputs:**
- `data/pipeline/L1/L1_housing_*_transaction.parquet` - Transaction data
- `data/pipeline/L2/L2_housing_unique_searched.parquet` - Geocoded addresses
- `data/pipeline/L1/L1_amenity.parquet` - Amenity locations
- `data/manual/geojsons/onemap_planning_area_polygon.shp` - Planning area boundaries

**Outputs:** `data/pipeline/L3/`
- `L3_property.parquet` - Standardized property table (ID, address, location, type)
- `L3_private_property_facilities.parquet` - Private property facilities (randomly assigned)
- `L3_property_nearby_facilities.parquet` - Property-amenity distances from spatial join
- `L3_property_transactions_sales.parquet` - Combined HDB + private transaction sales
- `L3_property_listing_sales.parquet` - Derived listings (room counts, bathrooms, floor)

**Key Functions:**
- `run_features_pipeline()` - Main entry point
- `create_property_geodataframe()` - Generates H3 polygons for properties
- `compute_amenity_distances()` - Spatial join to find nearest amenities
- `compute_planning_area()` - Assigns planning areas via spatial join
- `process_private_transactions()` / `process_hdb_transactions()` - Normalize transaction data
- `create_property_table()` - Standardized property reference table
- `create_listing_sales()` - Generate synthetic listings from transactions

**Features Generated:**
- H3 grid polygons (resolution=8, k=3)
- Distance to nearest amenities
- Amenity counts within 500m/1km/2km
- Planning area assignments
- Floor level ranges (low/high)
- Room and bathroom counts

---

## L2: Rental Yield (`L2_rental.py`)

**Purpose:** Download rental data and calculate rental yields

**Inputs:**
- data.gov.sg API (HDB rental, URA rental index)
- Transaction data: `data/pipeline/L1/L1_housing_*_transaction.parquet`

**Outputs:** `data/pipeline/L1/`
- `housing_hdb_rental.parquet` - HDB rental contracts (downloaded)
- `housing_ura_rental_index.parquet` - URA rental index by region (downloaded)

**Outputs:** `data/pipeline/L2/`
- `rental_yield.parquet` - Combined HDB + Condo rental yields by town/month

**Key Functions:**
- `run_rental_pipeline()` - Main entry point
- `download_hdb_rental_data()` - Downloads from data.gov.sg (cached 30 days)
- `download_ura_rental_index()` - Downloads URA index (cached 90 days)
- `calculate_hdb_rental_yield()` - Median rent × 12 / median resale price
- `calculate_condo_rental_yield()` - Using URA rental index

**Note:** Uses file freshness checks to avoid re-downloading (use `--force` to override)

---

## L3: Export Pipeline (`L3_export.py`)

**Purpose:** Create unified dataset and export to S3/CSV

**Inputs:**
- `data/pipeline/L3/L3_property.parquet` - Property table
- `data/pipeline/L3/L3_property_transactions_sales.parquet` - Transaction sales
- `data/pipeline/L3/L3_property_listing_sales.parquet` - Listing sales

**Outputs:** `data/pipeline/L3/`
- `L3_unified.parquet` - Unified dataset (property + transactions + listings + MRT)

**Optional Outputs:**
- S3: `s3://{bucket}/unified/l3_unified.parquet` (if `--upload-s3` flag)
- CSV: `data/exports/l3_*.csv` (if `--export-csv` flag)

**Key Functions:**
- `run_export_pipeline()` - Main entry point
- `create_unified_dataset()` - Joins property + transactions + listings
- `upload_to_s3()` - Uploads parquet to S3
- `export_to_csv()` - Exports to CSV files

**Note:** Adds nearest MRT station information to unified dataset

---

## L4: Analysis Pipeline (`L4_analysis.py`)

**Purpose:** Orchestrate execution of all analysis scripts

**Inputs:**
- All analysis scripts in `scripts/analytics/analysis/` (auto-discovered)

**Outputs:** `data/analysis/`
- `L4_analysis_report.md` - Summary report of all analysis results

**Analysis Scripts (executed in order):**
1. `analyze_spatial_hotspots` - Identify spatial clusters of high/low prices
2. `analyze_spatial_autocorrelation` - Moran's I spatial autocorrelation
3. `analyze_h3_clusters` - H3 grid-based clustering analysis
4. `analyze_hdb_rental_market` - HDB rental market trends
5. `analyze_amenity_impact` - Amenity proximity impact on prices
6. `analyze_policy_impact` - Cooling measures impact analysis
7. `analyze_lease_decay` - Lease decay analysis for HDB
8. `analyze_feature_importance` - Feature importance for price prediction
9. `market_segmentation_advanced` - Advanced market segmentation

**Key Functions:**
- `main()` - Discovers and runs all analysis scripts
- `run_script()` - Executes individual script with timeout (300s)
- `generate_report()` - Creates markdown summary report

**Note:** Each analysis script should output JSON summary with `key_findings` and `outputs`

---

## L5: Metrics Pipeline (`L5_metrics.py`)

**Purpose:** Calculate all market metrics at planning area level for dashboard and analysis

**Inputs:**
- `data/pipeline/L3/housing_unified.parquet` - Unified dataset
- (Optional) `data/pipeline/L3/L3_income_estimates.parquet` - Estimated income by area

**Outputs:** `data/pipeline/L5/`
- `L5_price_metrics_by_area.parquet` - Median price, PSF by planning area/month/type
- `L5_volume_metrics_by_area.parquet` - Transaction counts with rolling averages
- `L5_growth_metrics_by_area.parquet` - MoM, YoY growth with momentum signals
- `L5_rental_yield_by_area.parquet` - Rental yield statistics by planning area
- `L5_affordability_by_area.parquet` - Affordability ratios, mortgage metrics
- `L5_appreciation_hotspots.parquet` - Consistent high-appreciation areas

**Key Functions:**
- `run_metrics_pipeline()` - Main entry point, orchestrates all metric calculations
- `calculate_price_metrics_by_area()` - Median price and PSF aggregations
- `calculate_volume_metrics_by_area()` - Transaction counts with 3m/12m rolling averages
- `calculate_growth_metrics_by_area()` - MoM/YoY growth with momentum classification
- `calculate_rental_yield_by_area()` - Yield statistics (mean, median, min, max)
- `calculate_affordability_by_area()` - Price-to-income ratios, mortgage calculations
- `identify_appreciation_hotspots()` - Areas with consistently high YoY growth

**Metrics Calculated:**
- **Price Metrics**: Median price, median PSF (by planning area/month/property type)
- **Volume Metrics**: Transaction count, 3-month rolling avg, 12-month rolling avg
- **Growth Metrics**: Month-over-Month % change, Year-over-Year % change
- **Momentum Signals**: Strong/Moderate Acceleration/Deceleration, Stable
- **Rental Yield**: Mean, median, std, min, max (for areas with ≥10 records)
- **Affordability**: Price-to-income ratio, monthly mortgage, mortgage-to-income %
- **Hotspots**: Elite (70%+ consistency), High Growth (50%+ consistency)

**Usage:**
```bash
# Calculate all metrics (including affordability, requires income data)
uv run python -m scripts.core.stages.L5_metrics

# Skip affordability calculations (no income data required)
uv run python -m scripts.core.stages.L5_metrics --skip-affordability
```

**Note:** Consolidates metrics logic from dashboard pages into centralized pipeline stage

---

## Spatial Utilities (`spatial_h3.py`)

**Purpose:** Distance calculations and H3 grid operations

**Key Functions:**
- `haversine_distance()` - Great circle distance between coordinates
- `generate_h3_grid_cell()` - Convert lat/lon to H3 cell
- `generate_grid_disk()` - Generate H3 grid disk around a cell
- `generate_polygons()` - Create Shapely polygons from H3 cells
- `calculate_amenity_distances()` - KD-tree based nearest amenity search

**Used by:** L2 features pipeline for efficient spatial operations

---

## Webapp Data Export (`webapp_data_preparation.py`)

**Purpose:** Export lightweight JSON files for static web dashboard

**Inputs:**
- `data/pipeline/L3/L3_unified.parquet` - Unified dataset (via `load_unified_data()`)
- `data/manual/geojsons/onemap_planning_area_polygon.geojson` - Planning area boundaries

**Outputs:** `backend/public/data/`
- `dashboard_overview.json` - Overview statistics (whole, pre-covid, recent)
- `dashboard_trends.json` - Monthly price and volume trends
- `map_metrics.json` - Metrics by planning area (whole, pre-covid, recent)
- `dashboard_segments.json` - Scatter plot data (price psf vs yield)
- `dashboard_leaderboard.json` - Town leaderboard rankings
- `planning_areas.geojson` - Copied from source

**Key Functions:**
- `export_dashboard_data()` - Main entry point
- `generate_overview_data()` - Statistics and distributions
- `generate_trends_data()` - Time series trends
- `generate_map_data()` - Spatially aggregated metrics
- `generate_segments_data()` - Market segments scatter data
- `generate_leaderboard_data()` - Town performance rankings

**Note:** Output location is different from other stages (uses `backend/public/data/` for web serving)

---

## Data Flow Summary

```
Raw Data (APIs + CSVs)
         ↓
    L0: Collection → Raw parquet files
         ↓
    L1: Processing → Transaction files + Geocoded addresses
         ↓
    L2: Features → Property tables + Spatial features + Rental yields
         ↓
    L3: Export → Unified dataset + S3/CSV exports
         ↓
    L4: Analysis → Analytical reports
         ↓
    L5: Metrics → Planning area aggregated metrics
         ↓
  Webapp Export → JSON for dashboard
```

---

## Usage Examples

```bash
# Run complete pipeline
uv run python -m scripts.core.stages.L0_collect
uv run python -m scripts.core.stages.L1_process
uv run python -m scripts.core.stages.L2_features
uv run python -m scripts.core.stages.L2_rental
uv run python -m scripts.core.stages.L3_export
uv run python -m scripts.core.stages.L4_analysis
uv run python -m scripts.core.stages.L5_metrics

# Export webapp data
uv run python -m scripts.core.stages.webapp_data_preparation
```

---

## Configuration

All paths and settings are centralized in `scripts/core/config.py`:
- `Config.PIPELINE_DIR` - Base directory for pipeline outputs (`data/pipeline/`)
- `Config.MANUAL_DIR` - Manual data files (`data/manual/`)
- `Config.ANALYSIS_SCRIPTS_DIR` - Analysis scripts (`scripts/analytics/analysis/`)
- `Config.L4_REPORT_PATH` - L4 report output (`data/analysis/L4_analysis_report.md`)

---

## Dependencies

- **Required:** `pandas`, `geopandas`, `h3`, `requests`, `shapely`
- **Optional:** `boto3` (for S3 uploads)
- **APIs:** OneMap geocoding (requires `.env` credentials)
- **Data:** Manual CSV files in `data/manual/csv/`

---

## File Naming Convention

Pipeline outputs follow this pattern:
- Input layers: `{source}_{dataset}.parquet` (e.g., `raw_datagov_resale_flat_all.parquet`)
- Processed layers: `L{stage}_{table}.parquet` (e.g., `L1_housing_condo_transaction.parquet`)

---

*Last updated: 2026-02-01*
