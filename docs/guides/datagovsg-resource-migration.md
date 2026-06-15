# data.gov.sg Resource ID Migration (June 2026)

## Summary

On June 13, 2026, a data freshness audit revealed that **all four** data.gov.sg API resource IDs used by `01_ingestion.py` are broken. Three were permanently deleted (404) and one was silently swapped to a different dataset. The pipeline continued to work only because bronze-layer parquet caches masked the problem.

## How the Issue Was Discovered

### Investigation steps

1. **Checked bronze-layer data freshness** — loaded each cached parquet and inspected row counts and date ranges. Found:

   - HDB Rental: only 3,271 rows (Dec 2025–Jan 2026) instead of expected multi-year coverage.
   - URA Rental Index: ended at **2016-Q2** — 10 years stale.
   - HDB Resale: up to Jan 2026, but not the latest.

2. **Queried data.gov.sg dataset pages** (`https://data.gov.sg/datasets/{id}/view`) for each resource ID via web fetch. Results:

   - `d_e03d53203e43c32df38b5123c9e1d2a4` (URA Rental Index) — "Dataset not found / unpublished"
   - `d_8b84f0dfe7acb6d6585a7d7e6e406b31` (HDB Rental) — "Dataset not found / unpublished"
   - `d_69d6a3ed8b3b1e19aa2e0d868b0f2c7` (School Directory) — "Dataset not found / unpublished"

3. **Called the data.gov.sg datastore_search API** for each resource:

   - `d_5785799d63a9da091f4e0b456291eeb8` (HDB Resale) — returned 356 rows of "Private Residential Property Transactions" (wrong dataset, resource was swapped).
   - `d_8b84f0dfe7acb6d6585a7d7e6e406b31` — HTTP 404.
   - `d_69d6a3ed8b3b1e19aa2e0d868b0f2c7` — HTTP 404.
   - `d_e03d53203e43c32df38b5123c9e1d2a4` — HTTP 404.

4. **Confirmed via the v2 metadata API** (`https://api-production.data.gov.sg/v2/public/api/datasets/{id}/metadata`):

   - The swapped HDB Resale ID now points to "Private Residential Property Transactions in Rest of Central Region, Quarterly" managed by URA.
   - The other three return `{"error": "No table found for dataset ID: ..."}`.

5. **Scanned all 4,410 datasets** on data.gov.sg (441 pages of the v2 listing API) to find replacement resource IDs matching the original datasets by name and content.

## Broken Resource IDs and Replacements

| Dataset                | Old ID (Broken)                      | Status                         | New ID (Working)                     | Coverage                       |
| ---------------------- | ------------------------------------ | ------------------------------ | ------------------------------------ | ------------------------------ |
| HDB Resale (Jan 2017+) | `d_5785799d63a9da091f4e0b456291eeb8` | Swapped to URA developer sales | `d_8b84c4ee58e3cfc0ece0d773c8ca6abc` | Jan 2017–Jun 2026              |
| HDB Rental             | `d_8b84f0dfe7acb6d6585a7d7e6e406b31` | 404 Deleted                    | `d_c9f57187485a850908655db0e8cfe651` | Jan 2021–May 2026              |
| URA Rental Index       | `d_e03d53203e43c32df38b5123c9e1d2a4` | 404 Deleted                    | `d_8e4c50283fb7052a391dfb746a05c853` | 2004-Q1–2026-Q1                |
| School Directory       | `d_69d6a3ed8b3b1e19aa2e0d868b0f2c7`  | 404 Deleted                    | `d_688b934f82c1059ed0a6993d2a829089` | 337 schools (updated Apr 2026) |

## Data Gaps Recovered

| Dataset          | Before (Bronze Cache)           | After (Fresh API Fetch)              | Gap Recovered               |
| ---------------- | ------------------------------- | ------------------------------------ | --------------------------- |
| HDB Resale       | Jan 1990–Jan 2026 (969K rows)   | Jan 1990–Jun 2026 (~970K rows)       | ~5 months of transactions   |
| HDB Rental       | Dec 2025–Jan 2026 (3,271 rows)  | Jan 2021–May 2026 (200K+ rows)       | **5+ years, ~197K records** |
| URA Rental Index | 2004-Q1–2016-Q2 (300 rows)      | 2004-Q1–2026-Q1 (515 rows)           | **10 years of index data**  |
| School Directory | 200 schools (Mar 2026 snapshot) | 337 schools (Apr 2026 snapshot)      | 137 more schools            |
| CPI              | Not wired                       | 784 monthly records (1961–Apr 2026)  | **New macro indicator**     |
| Unemployment     | Not wired                       | 137 quarterly records (1992–2026-Q1) | **New macro indicator**     |
| GDP              | Not wired                       | 201 quarterly records (1976–2026-Q1) | **New macro indicator**     |

## Amenity Proximity Features (New — June 2026)

Five new amenity GeoJSON sources were wired into the pipeline as bronze ingestion nodes and proximity feature computations:

| Amenity        | Source File                            | Locations | Median Distance |
| -------------- | -------------------------------------- | --------- | --------------- |
| Hawker Centres | `HawkerCentresGEOJSON.geojson`         | 129       | 596m            |
| Supermarkets   | `SupermarketsGEOJSON.geojson`          | 526       | 290m            |
| Parks          | `NParksParksandNatureReserves.geojson` | 450       | 622m            |
| Childcare      | `ChildCareServices.geojson`            | 1,925     | 126m            |
| Kindergartens  | `PreSchoolsLocation.geojson`           | 2,290     | 125m            |

All amenity GeoJSONs are loaded via `_load_geojson_amenities()` which handles both Point and Polygon geometries. Proximity is computed via `_compute_generic_proximity()` in `utils/proximity.py` using BallTree with haversine distance.

**Note**: `Kindergartens.geojson` in the manual data bundle is misnamed — it contains incidental charges data (CSV), not locations. The `raw_kindergartens` node uses `PreSchoolsLocation.geojson` instead.

## Pipeline Stage Coverage Fix

The `STAGE_VARS["all"]` list was missing 4 terminal output nodes that were only computed when explicitly running `--stage export` or `--stage metrics`:

| Node                     | Module          | Output                                 |
| ------------------------ | --------------- | -------------------------------------- |
| `interactive_tools_data` | `04_export.py`  | Planning-area aggregates for app tools |
| `rental_yield_by_area`   | `05_metrics.py` | Rental yield metrics by planning area  |
| `affordability_metrics`  | `05_metrics.py` | Affordability classifications          |
| `appreciation_hotspots`  | `05_metrics.py` | Price appreciation rankings            |

These are now included in `--stage all` so a full pipeline run produces all platinum artifacts.

## Schema Changes

### School Directory (New)

The new dataset (`d_688b934f82c1059ed0a6993d2a829089`) has the same field names as the old one **but no `latitude`/`longitude` columns**. The pipeline geocodes schools via OneMap postal code lookup in `features_with_amenities` (`03_features.py`). Geocoded results are cached back to the bronze parquet so subsequent runs skip re-geocoding.

**OneMap rate limiting**: OneMap aggressively returns 429 Too Many Requests. The `_geocode_schools()` function uses sequential requests with 0.3s delay. First-time geocoding of 337 schools takes ~5 minutes. If rate-limited, wait 60s and re-run — the cached parquet will have partial results and only missing schools are re-geocoded.

### URA Rental Index (New)

The new dataset (`d_8e4c50283fb7052a391dfb746a05c853`) has the same schema (`quarter`, `property_type`, `locality`, `index`) as the old one, but now covers 2004-Q1 through 2026-Q1 instead of stopping at 2016-Q2.

### HDB Resale (New)

The new dataset only covers Jan 2017+. Historical data (1990–2016) must be loaded from the CSVs in `data/manual/csv/ResaleFlatPrices/`. The ingestion function merges API data (2017+) with CSV data (1990–2016) to produce the full historical range.

### Macro Economic Indicators (New — June 2026)

Three new data.gov.sg datasets were wired into the pipeline for macro enrichment:

| Indicator    | Resource ID                          | Format                     | Filter                                          | Records |
| ------------ | ------------------------------------ | -------------------------- | ----------------------------------------------- | ------- |
| CPI          | `d_bdaff844e3ef89d39fceb962ff8f0791` | Monthly pivot (`2026Apr`)  | `DataSeries == "All Items"`                     | 784     |
| Unemployment | `d_b0da22a41f952764376a2b7b5b0f2533` | Quarterly pivot (`20261Q`) | `DataSeries == "Total Unemployment Rate"`       | 137     |
| GDP          | `d_a5ff719648a0e6d4b4c623ee383ab686` | Quarterly pivot (`20261Q`) | `DataSeries == "GDP In Chained (2015) Dollars"` | 201     |

These datasets arrive as **wide pivot tables** (DataSeries rows × time period columns). The `_melt_pivot_monthly()` and `_melt_pivot_quarterly()` helpers in `01_ingestion.py` melt them to long format with proper date parsing.

**Key implementation details:**

- The `DataSeries` column (not `_id`) is used as the melt label column — `_id` contains integers that never match string filters.
- Quarter period strings use `YYYY{Q}Q` format (e.g. `20261Q`). Year is `p[:-2]`, not `p[:-1]`.
- The GDP dataset contains GDP **levels** (chained dollars), not growth rates. The filter `"Growth Rate"` returns nothing.
- SORA rates are loaded from the pre-built `bronze/external/sora_rates.parquet` (60 monthly records from 2021-2025).

## How to Verify Resource IDs in the Future

```bash
# Check a single resource ID via the v2 metadata API
curl -s "https://api-production.data.gov.sg/v2/public/api/datasets/{datasetId}/metadata" | python3 -m json.tool

# Search for datasets by keyword (scan all pages)
curl -s "https://api-production.data.gov.sg/v2/public/api/datasets?page=1" | python3 -m json.tool

# Verify a resource returns the expected data
curl -s "https://data.gov.sg/api/action/datastore_search?resource_id={datasetId}&limit=1" | python3 -m json.tool
```

## Root Cause

data.gov.sg periodically restructures its datasets. Resource IDs are not permanent — agencies may unpublish old datasets and publish new ones with different IDs. The old comprehensive HDB resale dataset (`d_5785799d...`) was replaced by time-period-segmented datasets, and three other datasets were deprecated entirely.

## Prevention

1. **Never rely solely on bronze cache** — the cache masks broken API resources.
2. **Add a CI check** that validates each resource ID returns the expected number of columns and minimum row count.
3. **Log API metadata** (dataset name, total records) on each fetch so silent swaps are detectable.
4. **Review data.gov.sg datasets quarterly** using the v2 listing API to catch renamed/replaced resources.

## Related Docs

- [External Data Setup Guide](./external-data-setup.md)
- [CSV Download Guide](./csv-download-guide.md)
- [Troubleshooting Guide](../TROUBLESHOOTING.md)
