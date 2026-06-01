# Egg-n-Bacon Housing — Current State

Last updated: 2026-05-31

## What's Implemented

| Feature                                                           | Status | Location                                                      |
| ----------------------------------------------------------------- | ------ | ------------------------------------------------------------- |
| Bronze ingestion (HDB resale, condo, rental, schools, macro data) | Full   | `components/01_ingestion.py`                                  |
| Data.gov.sg API adapter with pagination + retry                   | Full   | `adapters/datagovsg.py`                                       |
| OneMap geocoding adapter with JWT auth + retry                    | Full   | `adapters/onemap.py`                                          |
| URA CSV file loading (EC, condo, HDB)                             | Full   | `adapters/geocoding.py`                                       |
| Silver cleaning: HDB, condo, EC transactions                      | Full   | `components/02_cleaning.py`                                   |
| Pydantic schema validation at silver boundary                     | Full   | `components/02_cleaning.py:87-146`, `schemas/clean_models.py` |
| Geocoded property merging with coverage check                     | Full   | `components/02_cleaning.py:234-275`                           |
| Gold feature engineering (PSF, lease, amenities)                  | Full   | `components/03_features.py`                                   |
| Rental yield computation (town/flat_type/month)                   | Full   | `components/03_features.py:91-201`                            |
| School distance features with KDTree + quality tiers              | Full   | `utils/school_features.py`                                    |
| MRT distance features with KDTree + line info                     | Full   | `utils/mrt_distance.py`                                       |
| Mall distance features with BallTree                              | Full   | `components/03_features.py:47-88`                             |
| Unified feature merging (rental yield join)                       | Full   | `components/03_features.py:276-339`                           |
| Platinum export (unified dataset, JSON, segments)                 | Full   | `components/04_export.py`                                     |
| CSV export for external use                                       | Full   | `components/04_export.py:159-180`                             |
| Price metrics by planning area                                    | Full   | `components/05_metrics.py:35-71`                              |
| Rental yield metrics by area                                      | Full   | `components/05_metrics.py:74-112`                             |
| Affordability metrics with classification                         | Full   | `components/05_metrics.py:115-164`                            |
| Appreciation hotspot detection                                    | Full   | `components/05_metrics.py:167-223`                            |
| Analytics orchestration (market, spatial, appreciation)           | Full   | `components/06_analytics.py`                                  |
| Hamilton DAG pipeline driver with caching                         | Full   | `pipeline.py`                                                 |
| pydantic-settings configuration with secrets                      | Full   | `config.py`                                                   |
| File-based cache manager (JSON/parquet)                           | Full   | `utils/cache.py`                                              |
| Data quality monitoring with SQLite baselines                     | Full   | `utils/data_quality.py`                                       |
| Data contract helpers (column checks)                             | Full   | `utils/contracts.py`                                          |
| Planning area polygon lookup                                      | Full   | `utils/data_loader.py:36-102`                                 |
| Regional mapping (CCR/RCR/OCR)                                    | Full   | `utils/regional_mapping.py`                                   |
| Network availability checks                                       | Full   | `utils/network_check.py`                                      |
| Standalone analytics scripts (~30+)                               | Full   | `analytics/`                                                  |
| Raw/clean/feature Pydantic schemas                                | Full   | `schemas/`                                                    |
| Typed adapter exceptions                                          | Full   | `adapters/exceptions.py`                                      |
| Mortgage, affordability, ROI, forecast metric utils               | Full   | `utils/metrics.py`                                            |

## Stubbed / Unimplemented

- `analytics/amenity/__init__.py` — Empty package init (no amenity analytics submodule)
- `analytics/appreciation/__init__.py` — Empty package init
- `analytics/causal/__init__.py` — Empty package init (causal inference analytics not started)
- `analytics/market/__init__.py` — Empty package init
- `analytics/models/__init__.py` — Empty package init
- `analytics/mrt/__init__.py` — Empty package init
- `analytics/pipelines/__init__.py` — Empty package init
- `analytics/policy/__init__.py` — Empty package init
- `analytics/price_modeling/__init__.py` — Empty package init
- `analytics/school/__init__.py` — Empty package init (only `special/__init__.py`)
- `analytics/segmentation/__init__.py` — Empty package init
- `analytics/spatial/__init__.py` — Empty package init
- `analytics/viz/__init__.py` — Empty package init
- `analytics/pipelines/calculate_l3_metrics_pipeline.py:12` — TODO: affordability index needs income data
- `analytics/pipelines/calculate_l3_metrics_pipeline.py:13` — TODO: ROI potential score needs rental data

## Known Bugs

| Severity | Issue                                                                                                                                                                                                                                                                                                                                                                                        | Location                                        |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| High     | Unreachable code: `raise OneMapAuthError` at line 79 never executes because lines 76-77 return first when `access_token` is falsy, but if `access_token` is still truthy after the JWT decode failure branch, it falls through to the raise. The actual path when token is valid returns at line 65, and when invalid sets `access_token = None` then returns at 77. The raise is dead code. | `adapters/onemap.py:79`                         |
| Medium   | `geocoded_properties` requires `lat`/`lon` columns but neither `cleaned_hdb_transactions` nor `cleaned_condo_transactions` produce them — geocoding must happen externally before validation or the pipeline will always fail with `ValueError`                                                                                                                                              | `components/02_cleaning.py:258-261`             |
| Medium   | `classify_affordability` thresholds differ between `utils/metrics.py` (3/5/7) and `config.py` MetricsConfig (5/7/9) — two conflicting classification schemes                                                                                                                                                                                                                                 | `utils/metrics.py:100-107` vs `config.py:27-31` |
| Low      | `load_ura_files` reads with `encoding="latin1"` but never validates CSV existence before `pd.read_csv`, will raise `FileNotFoundError` not a clean error                                                                                                                                                                                                                                     | `adapters/geocoding.py:41-45`                   |
| Low      | `cleaned_ec_transactions` filters for "ec" in `property_type` but raw condo data may not have this column, silently returning empty                                                                                                                                                                                                                                                          | `components/02_cleaning.py:209-210`             |
| Low      | `_nearest_mall_features` uses BallTree with radians but mall coordinates from `_standardize_geocoded_mall_columns` are in degrees — mixed units produce incorrect distances                                                                                                                                                                                                                  | `components/03_features.py:78-83`               |

## Security Concerns

| Severity | Issue                                                                                                                                                | Location                           |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| Medium   | OneMap token logged with remaining hours but `access_token` variable retains the JWT value in memory for full process lifetime                       | `adapters/onemap.py:60-64`         |
| Medium   | `fetch_dataset_with_download_api` catches bare `Exception` and returns `None`, silently swallowing auth/network errors                               | `adapters/datagovsg.py:208-210`    |
| Low      | `_get_required_secret` uses `get_secret_value()` which strips protection — the raw credential is then in a local variable and passed to the API call | `adapters/onemap.py:82-86`         |
| Low      | Cache files written as plain JSON/parquet with no access controls — cached API responses may contain sensitive geocoding data                        | `utils/cache.py:143-149`           |
| Low      | `_geocode_schools` makes unauthenticated OneMap calls without rate-limit handling beyond `time.sleep(0.1)`, risking IP ban                           | `utils/school_features.py:293-318` |
| Low      | Hardcoded URA file names in config — if these contain timestamps or identifiers, they could leak data pipeline run schedules                         | `config.py:70-87`                  |

## Performance Issues

| Issue                                                                                                                                                   | Location                            |
| ------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| Row-by-row Pydantic validation with `to_dict("records")` + loop is O(n) with high constant — slow for 100k+ record datasets                             | `components/02_cleaning.py:117-138` |
| `calculate_school_features` uses iterrows for unique location processing — O(n) per unique location × O(k) KDTree queries per level per distance radius | `utils/school_features.py:609-685`  |
| `get_planning_area_for_point` does linear scan over all planning area polygons — O(n) per point, no spatial index                                       | `utils/data_loader.py:80-102`       |
| `load_planning_areas` uses module-level mutable global `_planning_areas` — not thread-safe, and the geometry objects are kept in memory forever         | `utils/data_loader.py:24,43-77`     |
| `haversine_distance` in `mrt_distance.py` computed via Python loop instead of vectorized NumPy — called once per property                               | `utils/mrt_distance.py:183-191`     |
| `regional_mapping.py` duplicates all entries in uppercase and lowercase variants instead of normalizing at lookup time — dict is ~2x larger than needed | `utils/regional_mapping.py:12-119`  |
| `data_helpers.py:save_parquet` reads the entire existing parquet into memory for append mode, then concatenates                                         | `utils/data_helpers.py:134-144`     |
| `list_datasets(refresh_rows=True)` reads every parquet file from disk just to count rows                                                                | `utils/data_helpers.py:222-225`     |
| `_geocode_schools` makes sequential HTTP requests with 0.1s sleep — no concurrency                                                                      | `utils/school_features.py:278-321`  |

## Maintenance Issues

| Issue                                                                                                                                                | Detail                                                                                                                                                                                        |
| ---------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 64 bare `except Exception` blocks across codebase                                                                                                    | Silently swallows errors; makes debugging difficult. Worst in `analytics/` (40+ instances) and `utils/cache.py:123,151`                                                                       |
| `utils/mrt_distance.py` and `utils/school_features.py` both define their own `haversine_distance` with different signatures (lon-first vs lat-first) | `utils/mrt_distance.py:29` vs `utils/school_features.py:26` — easy to mix up                                                                                                                  |
| 13 empty `analytics/__init__.py` packages                                                                                                            | `analytics/amenity/`, `appreciation/`, `causal/`, `market/`, `models/`, `mrt/`, `pipelines/`, `policy/`, `price_modeling/`, `school/`, `segmentation/`, `spatial/`, `viz/` — all 1-line inits |
| Analytics scripts are standalone and not wired to Hamilton DAG                                                                                       | `AGENTS.md` documents this as intentional, but the `components/06_analytics.py` DAG node is a lightweight stub compared to the 30+ standalone scripts                                         |
| Mixed DataFrame engines: pipeline uses pandas, but `utils/mrt_distance.py` imports geopandas, and `AGENTS.md` mentions Polars/DuckDB                 | No Polars or DuckDB usage found in source — documentation is aspirational                                                                                                                     |
| `utils/data_loader.py:20-21` computes `DATA_DIR` and `RAW_DATA_DIR` at import time from settings singleton                                           | Breaks if settings are overridden after import (e.g., in tests)                                                                                                                               |
| `utils/data_quality.py:20` uses module-level mutable `_collector = None` singleton                                                                   | Same issue as `data_loader.py` — not reset between test runs without explicit `reset_collector()`                                                                                             |
| `config.py:114` instantiates `settings = Settings()` at module import time                                                                           | Reads `.env` on import — any missing env var silently defaults to empty string for secrets                                                                                                    |
| `pipeline.py:62` eagerly imports all 6 component modules at module load time                                                                         | `COMPONENTS = [importlib.import_module(m) for m in _STAGE_MODULES]` — unnecessary if only running a single stage                                                                              |
| Inconsistent column naming: `storey_min`/`storey_max` (int) vs `storey_range` (str) vs `nearest_mrt_name`/`nearest_mrt_station` (aliased)            | Feature schema in `schemas/feature_models.py` uses `nearest_mrt_station` but the actual column in the pipeline is `nearest_mrt_name` with an alias at `components/03_features.py:259-260`     |
