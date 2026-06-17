# Gold Layer Entity-Table Restructure

**Status**: Active | **Created**: 2026-06-15 | **Phases**: 3

## Problem

The gold layer computes ALL feature engineering (proximity, school scoring, Green Mark geocoding, block metadata) on **1,077,543 transaction rows**. But:

- Only **10,685 unique (lat, lon) pairs** exist — proximity is ~100x redundant
- Every downstream consumer (app, analytics, metrics) aggregates to **~43 planning areas**
- The pipeline **cannot complete** — Green Mark geocoding (~11 min) + school feature mapping hangs on 1M rows
- Gold/platinum files are **stale** (Jun 14, pre-Round 1-3 expansion, missing 15+ feature columns)
- App data generation scripts were **retired** — pipeline exports don't match what the app consumes

## Solution

Replace 6 transaction-level feature nodes with **entity dimension tables** + a fast transaction fact join.

### Current DAG (broken)

```
geocoded_validated (1M)
  → features_with_amenities (1M, proximity on 1M)     ← BOTTLENECK
  → unified_features (1M)
  → macro_enriched_features (1M)
  → block_metadata_enriched (1M)
  → income_enriched_features (1M)
  → town_supply_enriched (1M)
  → unified_dataset (1M)
```

### Target DAG

```
geocoded_validated (1M)
  ├─[extract unique coords]→ location_dim (10,685)     ← Block 360
  │    ├─[proximity: 14 POI types on 10K points]
  │    ├─[school features on 10K points]
  │    ├─[merge block metadata]
  │    ├─[green mark proximity]
  │    └─[derive planning_area: point-in-polygon on 10K]
  │         ↓
  │    planning_area_360 (43)                           ← PA 360
  │    town_360 (27)                                    ← Town 360
  │
  └─[join location_dim]→ transactions_enriched (1M)    ← fast merge
       ├─[merge rental yield by town/flat_type/month]
       ├─[merge macro indicators by month/quarter]
       └─[merge town supply by town/flat_type]
            ↓
       pa_monthly_metrics (5K)                          ← PA × month
       block_profile (10K)                              ← per-block history
            ↓
       Platinum exports
```

## Entity Cardinalities

| Entity                              | Rows   | Key                    |
| ----------------------------------- | ------ | ---------------------- |
| Unique blocks (block + street_name) | 10,696 | `(block, street_name)` |
| Unique (lat, lon) pairs             | 10,685 | `(lat, lon)`           |
| Unique towns                        | 27     | `town`                 |
| Unique planning areas               | 43     | `planning_area`        |
| Unique (town, flat_type)            | 134    | `(town, flat_type)`    |

## Nodes Added

| Node                            | File              | Rows    | Description                                                           |
| ------------------------------- | ----------------- | ------- | --------------------------------------------------------------------- |
| `geocoded_green_mark_buildings` | `01_ingestion.py` | ~3,941  | OneMap geocoding of Green Mark postal codes, cached as bronze parquet |
| `location_dim`                  | `03_features.py`  | ~10,685 | Unique locations + ALL proximity + block metadata + planning_area     |
| `transactions_enriched`         | `03_features.py`  | ~1M     | Join location_dim → transactions + macro + rental yield + town supply |
| `planning_area_360`             | `03_features.py`  | ~43     | PA profile: spatial medians + market stats + demographics + tax       |
| `town_360`                      | `03_features.py`  | ~27     | Town profile: supply + population + annual value + property tax       |
| `block_profile`                 | `03_features.py`  | ~10K    | Per-block median price, volume, trend, flat_type breakdown            |
| `pa_monthly_metrics`            | `05_metrics.py`   | ~5K     | PA × month time series (replaces 4 separate metrics functions)        |

## Nodes Removed

| Old Node                   | Replaced By                          |
| -------------------------- | ------------------------------------ |
| `features_with_amenities`  | `location_dim`                       |
| `unified_features`         | `transactions_enriched`              |
| `macro_enriched_features`  | `transactions_enriched`              |
| `block_metadata_enriched`  | `location_dim`                       |
| `income_enriched_features` | `planning_area_360`                  |
| `town_supply_enriched`     | `transactions_enriched` + `town_360` |

## location_dim Schema (Block 360)

~10,685 rows × ~100 columns.

| Category             | Columns                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Identity             | `_loc_key`, `lat`, `lon`, `block`, `street_name`, `town`                                                                                                                                                                                                                                                                                                                                                                                 |
| Proximity (14 types) | `dist_to_nearest_mrt`, `nearest_mrt_station`, `nearest_mrt_score`, `dist_to_nearest_school`, `dist_to_nearest_mall`, `dist_to_nearest_hawker`, `dist_to_nearest_supermarket`, `dist_to_nearest_park`, `dist_to_nearest_childcare`, `dist_to_nearest_kindergarten`, `dist_to_nearest_bus_stop`, `dist_to_nearest_chas_clinic`, `dist_to_nearest_sports_facility`, `dist_to_nearest_community_club`, `dist_to_nearest_green_mark_building` |
| School features      | `nearest_schoolPRIMARY_dist`, `nearest_schoolSECONDARY_dist`, `school_primary_quality_score`, `school_secondary_quality_score`, `school_within_1km`, `school_accessibility_score`, etc.                                                                                                                                                                                                                                                  |
| Block metadata       | `max_floor_lvl`, `year_completed`, `total_dwelling_units`, `residential`, `commercial`, `market_hawker`, `multistorey_carpark`                                                                                                                                                                                                                                                                                                           |
| Geography            | `planning_area`, `region`                                                                                                                                                                                                                                                                                                                                                                                                                |

## planning_area_360 Schema (PA 360)

~43 rows × ~50 columns.

| Category        | Columns                                                                            |
| --------------- | ---------------------------------------------------------------------------------- |
| Identity        | `planning_area`, `region`                                                          |
| Spatial medians | `median_dist_to_mrt`, `median_dist_to_school`, `median_dist_to_mall`, etc.         |
| Amenity access  | `mrt_within_500m_count`, `schools_within_1km_count`, etc.                          |
| Market stats    | `median_price`, `median_psf`, `price_growth_12m_pct`, `transaction_volume`         |
| Rental          | `median_rental_yield_pct`, `rental_yield_trend`                                    |
| Demographics    | `median_monthly_income`, `population`, `dwelling_units`, `population_per_dwelling` |
| Tax             | `annual_value_3room`, `annual_value_4room`, `annual_value_5room`, `property_tax`   |
| Macro (latest)  | `cpi`, `sora_3m`, `unemployment_rate`, `gdp`, `wage_growth`                        |

## Performance Impact

| Operation                | Before                            | After                        | Speedup       |
| ------------------------ | --------------------------------- | ---------------------------- | ------------- |
| Proximity (BallTree)     | 1,077,543 points                  | 10,685 points                | ~100x         |
| School features KDTree   | 10,685 unique (already optimized) | 10,685 (same, but persisted) | ~1x + caching |
| Green Mark geocoding     | Inline, re-runs every time        | Separate bronze node, cached | One-time      |
| Planning area derivation | Point-in-polygon on 1M            | Point-in-polygon on 10K      | ~100x         |
| Analytics queries        | Scan 1M rows                      | Scan 43-10K rows             | ~100x         |

---

## Phase 1 — Core (unblocks pipeline)

### Step 1: `geocoded_green_mark_buildings` in `01_ingestion.py`

Extract the inline geocoding loop from `features_with_amenities` into a standalone ingestion node.

```python
def geocoded_green_mark_buildings(
    bronze_dir: Path,
    raw_green_mark_buildings: pd.DataFrame,
) -> pd.DataFrame:
    """Geocode Green Mark buildings via OneMap, cache as bronze parquet."""
    cache_path = bronze_dir / "raw_green_mark_buildings_geocoded.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    # ... geocode unique postal codes ...
    df.to_parquet(cache_path, index=False)
    return df
```

### Step 2: `location_dim` in `03_features.py`

```python
def location_dim(
    geocoded_validated: pd.DataFrame,
    raw_mrt_stations: pd.DataFrame,
    raw_school_directory: pd.DataFrame,
    raw_shopping_malls: pd.DataFrame,
    raw_hawker_centres: pd.DataFrame,
    raw_supermarkets: pd.DataFrame,
    raw_parks: pd.DataFrame,
    raw_childcare: pd.DataFrame,
    raw_kindergartens: pd.DataFrame,
    raw_bus_stops: pd.DataFrame,
    raw_chas_clinics: pd.DataFrame,
    raw_sports_facilities: pd.DataFrame,
    raw_community_clubs: pd.DataFrame,
    geocoded_green_mark_buildings: pd.DataFrame,
    raw_hdb_property_info: pd.DataFrame,
    gold_dir: Path,
) -> pd.DataFrame:
    """Build the location dimension table — one row per unique (lat, lon).

    Computes ALL proximity features, school scores, and block metadata
    on ~10K unique locations instead of 1M transactions.
    """
```

**Logic:**

1. Extract unique (lat, lon) from `geocoded_validated` → ~10,685 rows
2. Carry `block`, `street_name`, `town` for the first occurrence of each coord
3. Call `compute_proximity_features()` on 10,685 rows (ALL 14 POI types)
4. Call `calculate_school_features()` on 10,685 rows
5. Merge `raw_hdb_property_info` by (block, street_name)
6. Derive `planning_area` via `_add_planning_area()` on 10,685 rows
7. Validate + save to gold as `location_dim.parquet`

### Step 3: `transactions_enriched` in `03_features.py`

```python
def transactions_enriched(
    geocoded_validated: pd.DataFrame,
    location_dim: pd.DataFrame,
    rental_yield: pd.DataFrame,
    raw_macro_data: dict[str, pd.DataFrame],
    raw_dwelling_units_by_town: pd.DataFrame,
    raw_hdb_resident_population: pd.DataFrame,
    raw_median_annual_value: pd.DataFrame,
    gold_dir: Path,
) -> pd.DataFrame:
    """Join location_dim onto transactions + merge macro + yield + supply."""
```

**Logic:**

1. Copy `geocoded_validated`
2. LEFT JOIN `location_dim` by (lat, lon) — brings all spatial features
3. Merge `rental_yield` by (town, flat_type, month)
4. Merge macro indicators (CPI, SORA, SORA 3M, unemployment, GDP, HDB RPI, URA PPI, wage_growth) by month/quarter
5. Merge town supply (dwelling_units, population, population_per_dwelling)
6. Merge annual value by flat type
7. Validate + save to gold as `transactions_enriched.parquet`

### Step 4: Remove old nodes

Delete from `03_features.py`:

- `features_with_amenities()`
- `unified_features()`
- `macro_enriched_features()`
- `block_metadata_enriched()`
- `income_enriched_features()`
- `town_supply_enriched()`
- `_map_flat_type_for_annual_value()` (moved into `transactions_enriched`)

### Step 5: Update `04_export.py`

```python
def unified_dataset(
    transactions_enriched: pd.DataFrame,  # was: town_supply_enriched
    platinum_dir: Path,
    writer: LayerWriter | None = None,
) -> pd.DataFrame:
```

### Step 6: Update `pipeline.py` STAGE_VARS

```python
"features": [
    "rental_yield",
    "location_dim",
    "transactions_enriched",
],
```

Add `geocoded_green_mark_buildings` to `"ingest"`.

### Step 7: Update `feature_models.py`

Add `LocationDimRecord` Pydantic model for validation at the location_dim boundary.

### Step 8: Run + verify

- Run full pipeline
- Verify `location_dim.parquet` in gold (~10K rows)
- Verify `transactions_enriched.parquet` in gold (~1M rows, 120+ columns)
- Verify `unified_dataset.parquet` in platinum (all Round 1-3 columns present)

---

## Phase 2 — Entity 360 Tables

### Step 9: `planning_area_360`

Aggregate `location_dim` by `planning_area`:

- Spatial medians: median distances to all amenities
- Amenity access: counts within 500m/1km/2km
- Block profile: avg year_completed, avg max_floor, total dwelling units

Aggregate `transactions_enriched` by `planning_area`:

- Market: median_price, median_psf, transaction_volume
- Growth: price_growth_3m, price_growth_12m
- Rental: median_rental_yield_pct

Merge external:

- Income from `raw_income_by_planning_area`
- Population from `raw_hdb_resident_population`

### Step 10: `town_360`

Aggregate by `town`:

- Supply: dwelling_units (from `raw_dwelling_units_by_town`)
- Demographics: population, population_per_dwelling
- Tax: annual_value, property_tax (by flat type)
- Market: median_price, median_psf, transaction_volume

### Step 11: `block_profile`

Aggregate `transactions_enriched` by (block, street_name):

- Median price, PSF by flat_type
- Transaction count, last sale date
- Price trend (3m, 12m growth)
- Flat type breakdown

### Step 12: Schemas

Add `PlanningArea360`, `Town360`, `BlockProfile` Pydantic models.

---

## Phase 3 — Metrics + Exports

### Step 13: Refactor `05_metrics.py`

Replace 4 functions with:

- `pa_monthly_metrics` — single PA × month time series from `transactions_enriched`
- Keep `appreciation_hotspots` but consume `pa_monthly_metrics`

### Step 14: Entity table exports

Add to `04_export.py`:

- Export `planning_area_360`, `town_360`, `block_profile` to platinum as parquet
- Generate dashboard JSON from `planning_area_360` (restores app data pipeline)

### Step 15: Final STAGE_VARS update

```python
"all": [
    "unified_dataset",
    "planning_area_360",
    "town_360",
    "block_profile",
    "pa_monthly_metrics",
    "appreciation_hotspots",
    "dashboard_json",
    "segments_data",
    "interactive_tools_data",
],
```

---

## Risk Mitigation

| Risk                                                 | Mitigation                                                              |
| ---------------------------------------------------- | ----------------------------------------------------------------------- |
| Location join misses (condo addresses without block) | LEFT JOIN; missing features = NA (existing behavior)                    |
| Planning area derivation fails for some coords       | Graceful NA fallback (existing pattern)                                 |
| Schema validation rejects entity tables              | Use `validate_and_quarantine` with loose schema initially               |
| Old caches cause stale results                       | Delete `data/pipeline/cache/hamilton/` before first run                 |
| Breaks downstream consumers                          | `unified_dataset` output shape unchanged — same columns, same row count |

## Verification Checklist

- [ ] Pipeline completes in <10 minutes
- [ ] `location_dim.parquet`: ~10,685 rows × ~100 columns
- [ ] `transactions_enriched.parquet`: ~1,077,543 rows × 120+ columns
- [ ] `unified_dataset.parquet` in platinum has all Round 1-3 columns
- [ ] `planning_area_360.parquet`: ~43 rows × ~50 columns
- [ ] `town_360.parquet`: ~27 rows
- [ ] `block_profile.parquet`: ~10K rows
- [ ] `pa_monthly_metrics`: ~5K rows
- [ ] All amenity proximity columns populated (non-null for HDB)
- [ ] All macro columns populated (CPI, SORA, GDP, etc.)
- [ ] All Round 3 columns populated (wage_growth, dwelling_units_in_town, etc.)
