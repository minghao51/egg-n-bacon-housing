# Pipeline Refresh Handoff

**Date:** 2026-09-01
**Status:** Historical refresh record — superseded by the current continuation handoff
(`docs/plans/2026-09-10-hamilton-dag-next-thread-handoff.md`)
**Scope:** Audit-driven fixes, refresh infra, live data sources, OneMap hardening, and the full data refresh (executed 2026-09-01)

> This document preserves the September 1 refresh evidence and source-history
> details. The Hamilton registry, quarantine, cache-injection, app-data, and CI
> work completed afterward is tracked in the current handoff linked above.

## Goal

Refresh all data retrieval and processing. Work was sequenced as phases:

1. ✅ Correctness fixes (macro empty-cache poisoning, NaN planning-area leak, broken cleanup script, data-quality verification)
2. ✅ Refresh infrastructure (`main.py --refresh`, bronze seeding, persistence unification)
3. ✅ Close dataset gaps (missing amenity GeoJSONs sourced, malls source replaced, MRT stations upgraded to live LTA sources)
4. ⏳ **The refresh run itself** (blocked on user creds / commit, see Next Steps)
5. ⏳ Phase 3 DRY refactor (deliberately deferred until after a successful refresh run)

## Refresh Run (executed 2026-09-01, 20:04→22:31)

- R2 round-trip verified: 5 files uploaded (4 staged GeoJSONs + methodology md), 47 downloaded, 52/52 parity.
- Cold full refresh: 2h15m (geocoding ~13.3k lookups dominated); warm re-run after fixes: 2.5min. OneMap token lasted the whole run; only transient failures hit (1 connection reset, absorbed by the new retry policy; zero 429s).
- Final outputs: `unified_dataset` (1,095,759 × 139), `planning_area_360` (43×27), `town_360` (28×13), `block_profile` (10,002×6), `pa_monthly_metrics` (13,104×11), `appreciation_hotspots` (20×6). Transactions span 1990-01 → 2026-08; geocode coverage 98.9% (HDB 98.8% / condo 100%).
- Fresh-source verification: 111 locations nearest to NEW TEL stations (Bayshore/Napier/Marine Terrace… — impossible with 2019 data); `mrt_stations.json` regenerated (181 entries); MP25 malls live.
- Catalog regenerated (`app/public/data/catalog.jsonl.gz`).

### Production bugs found BY the refresh (both fixed + tested)

1. **Condo rows had no `month`** (all 110,089 condo transactions null) — monthly aggregations silently ran HDB-only. Fix: `cleaned_condo_transactions` derives `month` from `transaction_date` (`%Y-%m`). pa_monthly_metrics 12,441 → 13,104 rows.
2. **`nearest_mrt_tier` was always all-None and `nearest_mrt_is_interchange` always False** (pre-existing since proximity.py was written — bronze MRT frames never carried the columns and the lookups were guarded). Fix: `_compute_mrt_proximity` derives both via `get_station_tier`/`get_station_lines`. Now {t1:7233, t2:1583, t3:1898}, 11.1% interchange. Scores were never affected (computed internally).

## What Changed (all uncommitted — see file list below)

### Correctness fixes

- `components/ingestion/macro.py` — unified bronze-cache policy via `_read_bronze_cache` / `_write_bronze_cache`; empty fetches are never cached and empty cache files are treated as misses (was 3 inconsistent policies; empty caches permanently poisoned CPI/unemployment/GDP/bank_rates/supply_pipeline).
- `components/features.py` — NaN planning areas no longer become literal `"NAN"` and leak into `pa_monthly_metrics` / `planning_area_360`; `rental_yield` no longer crashes (`KeyError`) when the rental index filters to zero rows.
- `scripts/99_cleanup.py` — no longer crashes (cache manager is now configured from `Settings`); `sys.path` bootstrap restored.
- `utils/data_quality.py` — docstring-only change: the stored `std_rows`/`std_null_pct` columns are sample **variance**; the Welford math was verified numerically correct (reviewer claim was a false positive — do not "fix" it).

### Refresh infrastructure

- **New `utils/bronze.py`** — `EXPECTED_EXTERNAL_FILES`, `seed_bronze_external()` (auto-seeds `01_bronze/external/` from `data/manual/` and git-tracked `data/raw/` at pipeline startup, loud error listing missing files), `clear_bronze(pattern)` (fnmatch on bronze-relative stems), `refresh_all(settings)` (bronze + Hamilton DAG cache + API cache).
- **`main.py --refresh [PATTERN]`** — no value = everything; glob for targeted bronze invalidation (e.g. `raw_mrt_stations`, `raw_mp25_malls`, `external/*`).
- **Gateway → LayerWriter migration** — `validate_and_quarantine(writer, name, layer)` now routes all 9 validated silver/gold outputs + quarantine files through `LayerWriter` (compression + quality tracking parity). Duplicate unvalidated `geocoded_properties.parquet` removed; dead `silver_dir`/`gold_dir` node params and injections deleted.

### OneMap adapter hardening (DONE 2026-09-01)

- `adapters/onemap.py`: retries only transient failures (429/5xx/network; 4xx and auth errors fail fast); 429 honors `Retry-After` (delta-seconds or HTTP-date, capped 60s); 401/403 raise typed `OneMapAuthError`; `CredentialError` no longer retried 3x.
- `utils/geocoding.py`: thread-safe `_RateLimiter` paces API misses in BOTH sequential and parallel paths (was sequential-only; cache hits never paced); `OneMapGeocoder(on_auth_expired=...)` refreshes expired JWTs mid-run once per address and retries — previously a long run crossing token expiry silently nulled every remaining address. `build_default_geocoder` wires the refresh callback.
- Tests: `tests/test_onemap.py` 11→18, `tests/test_geocoding.py` +7 (auth refresh, pacing). The 4 "pre-existing" onemap failures are FIXED (root cause: tests lacked cred stubs + `CredentialError` was retried 3x ~20s).
- Full suite: **317 passed, 0 failed**; ruff/format/mypy/validators clean. Source-onboarding record for the OneMap policy added to `docs/guides/data-ingestion-development.md`.

### Dataset gaps closed

- **4 missing amenity GeoJSONs found on data.gov.sg and staged** into `data/manual/csv/datagov/` (gitignored; awaiting R2 `--upload`):
  - BusStops `d_3f172c6feb3f4f92a2f47d93eed2908a` (LTA, 5,205)
  - CHASClinics `d_548c33ea2d99e29ec63a7cc9edcccedc` (MOH, 1,193)
  - SportSGFacilities `d_9b87bab59d036a60fad2a91530e10773` (45, excludes DUS)
  - CommunityClubs `d_9de02d3fb33d96da1855f4fbef549a0f` (PA, 128)
- **Malls**: `raw_shopping_malls` now pulls the URA MP25 mall layer `d_65a0bf22c15ef49e9a21b8bcf8c04c87` via new adapter `fetch_datagovsg_geojson()` (initiate/poll/presigned-URL flow, `adapters/datagovsg.py`); filters `CLASSIFCTN == "MALL"`; bronze-caches `raw_mp25_malls.parquet`; empty never cached. Legacy wiki notebook parquets are a deprecated fallback. Caveat: MP25 has no names (`nearest_mall` stays empty; distances fine). URA SPACE eservice is a ToS-gated JS app with no exposed REST API — do not scrape it.
- **MRT stations (critical upgrade)**: `raw_mrt_stations` now prefers live LTA sources over the 2019 seeds:
  - coordinates: "MRT Station Exit (GEOJSON)" `d_b39d3a0871985372d7e1637193335da5` (613 exits → 190 station centroids, `FMEL_UPD_D` Dec 2025+)
  - lines: "Train Station Chinese Names" `d_d312a5b127e1ae74299b8ae664cedd4e` (datastore) — **but this LTA dataset is stale (no TEL rows)**, so a static supplement `_STATION_LINE_SUPPLEMENT` in `geojson.py` fills all TEL stations + Punggol Coast. Trim it once LTA catches up.
  - fetched mapping is written to `bronze/external/mrt_stations.json`, which `utils/mrt_line_mapping.py` reads first — tier/interchange/score features upgrade automatically (181 entries vs. 48 hardcoded fallback).
  - fallback chain: bronze cache → live fetch → legacy 2019 seeds → empty. Live-verified: 190/190 fresh coords, 180/190 line-mapped (unmapped = Changi Airport Branch/CLE, whose codes aren't in the tier map).
- Amenity name fixes: SportSG `VENUE` fallback; CHAS real clinic names parsed from KML Description HTML (`HCI_NAME`), with a `kml_<n>` placeholder guard.

### Docs

- `docs/guides/pipeline-development.md` — layer invariants updated (gateway on LayerWriter, seeding, refresh)
- `docs/guides/usage-guide.md` — `--refresh` section
- `docs/guides/r2-sync-guide.md` — bronze seeding note
- `docs/guides/data-ingestion-development.md` — source-onboarding records for all adopted sources

## Verification State

- Full suite: **300 passed**; the 4 `tests/test_onemap.py` failures are **pre-existing** (reproduced on a clean stash; JWT-handling tests). Do not treat as regression.
- `ruff check` / `ruff format` / `mypy` (48 files) / docs + skills validators / `git diff --check`: all clean.
- Live smoke-tested (one-off, real API): MP25 malls (294 sites, cache hit), MRT stations (190 stations, mapping JSON written).
- New/updated tests: `tests/test_bronze.py` (new), `test_ingestion.py` (macro cache policy, malls MP25, MRT live+legacy, name extraction), `test_datagovsg.py` (geojson download flow), `test_features.py`, `test_validation_gateway.py`, `test_cleaning_validation.py`, `test_pipeline_integration.py`.

## Uncommitted Files

Modified: `main.py`, `scripts/99_cleanup.py`, `src/egg_n_bacon_housing/components/cleaning.py`, `components/features.py`, `components/ingestion/macro.py`, `components/ingestion/datagov.py`, `components/ingestion/geojson.py`, `pipeline.py`, `utils/data_quality.py`, `utils/validation_gateway.py`, `utils/bronze.py` (new), plus docs listed above and the test files. Staged (gitignored) data: `data/manual/csv/datagov/*.geojson` (4 files).

## Next Steps (in order)

### 0. URA live adapter — ✅ DONE 2026-09-02 (user registered AccessKey)

- `adapters/ura.py`: token (8h cache) + `PMI_Resi_Transaction` batches 1–4, browser-like session headers (Layer7 bot wall), exponential retry on 429/5xx/network, one token-refresh retry on auth failure, typed `URAAuthError`/`CredentialError`/`DatasetFetchError`
- `config.py`: optional `URA_API_ACCESS_KEY` (absent → CSV-only fallback); wired into pipeline `layer_inputs`
- Node `raw_condo_transactions`: bronze cache → API(5y window) merged with CSV history (dedupe on natural key, CSV wins overlap) → CSV-only fallback; empty/partial never replaces a valid cache
- Live-verified E2E: 110,089 CSV + 133,942 API → 231,639 merged rows through 2026-08 (12,392 overlaps deduped)
- 28 new tests (`tests/test_ura.py`); docs updated (`data-sources.md`, `data-ingestion-development.md`, `.env.example`)
- **To promote**: `main.py --refresh raw_condo_transactions` then a warm run rebuilds downstream through Aug 2026; R2 sync picks up the new bronze cache

### 1. User: commit (agent must not commit per AGENTS.md)

Working tree holds the audit fixes + new sources + hardening + the two refresh-surfaced bug fixes. Suggested split: (a) correctness+infra, (b) new sources (malls/MRT/amenities), (c) OneMap hardening, (d) month/tier fixes + handoff/docs.

### 2. Optional follow-ups

- **Condo automation path identified (2026-09-01)**: URA Data Service API `service=PMI_Resi_Transaction` — row-level private transactions, rolling 5-year window, batches 1–4; token via free AccessKey from https://eservice.ura.gov.sg/maps/api/reg.html; endpoint live-verified. To adopt: register AccessKey → `URA_API_ACCESS_KEY` env var → new `ura` adapter → incremental bronze upsert (pre-window history stays in R2 CSVs). Quarterly data.gov.sg aggregates are NOT a substitute (unit counts only). Details in `docs/data-sources.md`.
- Verify the app renders the refreshed catalog (analytics serve precomputed assets from `app/public/data/`).
- Consider a data-quality gate on `month` nulls (this bug was invisible for years).
- Small hardening: datagovsg adapter retries 5× on datastore flows but NOT on the initiate/poll download flow (a 429 there fell back gracefully during the refresh — malls recovered on re-run).
- SportSG DUS dataset `d_7ff555dfb7104533494b23a60188a044` (excluded facilities) still not ingested.

### 3. OneMap adapter hardening — ✅ DONE 2026-09-01 (see What Changed)

### 4. Small debt sweep — ✅ DONE 2026-09-01

- ✅ 4 pre-existing onemap test failures — fixed (cred stubbing + no-retry on CredentialError)
- ✅ `run_pipeline` raises `ValueError` on unknown stage (CLI was already argparse-guarded; programmatic path was silent) + test
- ✅ datagovsg initiate-download now retries transient 429/5xx (4×, exponential cap 30s, `reraise=True`) — the exact failure mode the refresh hit on MP25; +2 tests
- ✅ Stale guides removed: `external-data-setup.md` (referenced deleted scripts), `csv-download-guide.md` (one-off Jan log), `mrt-features-guide.md` (documented a never-built 8-column schema); cross-refs updated to `../data-sources.md`

### 5. Phase 3 DRY refactor — ✅ DONE 2026-09-02

- ✅ **macro.py collapsed (2026-09-01)**: 8 copy-pasted fetch blocks → declarative `_MACRO_SOURCES` spec tuple + `_load_macro_source()` helper; transforms extracted as named pure functions (incl. GDP first-series fallback, wage empty-guard). Spec-table coverage test added.
- ✅ **datagov.py collapsed (2026-09-02)**: 6 cache-first/fetch/write nodes → `_load_or_fetch_dataset()` helper (`key/resource_id/display_name` + optional `cache_filenames`/`cache_id`/`transform`/`required`). `raw_dataset` (@parameterize, hard-fail) delegates with legacy filenames + `cached_call`; green-mark + income become pure `_transform_*` functions; hdb_resale (CSV merge) intentionally stays bespoke.
- ✅ **features.py dedup (2026-09-02)**: `_dwelling_units_lookup` / `_population_lookup` / `_annual_value_lookup` builders shared by `transactions_enriched` (keyed `_town_upper`, MAV via `_av_type`) and `town_360` (renamed to `town`, MAV exploded to per-type columns). ~120 duplicated lines gone; latest-year/numeric-coercion logic now single-sourced.
- ✅ **proximity.py consolidation (2026-09-02)**: `_compute_mall_proximity` delegates to `_compute_generic_proximity(label="mall", name_candidates=("shopping_mall","name","mall_name"))`. Verified **0.000000 m max distance diff** vs pre-refactor logic on the real MP25 frame (2k locations).
- ✅ **Behavior proof**: warm pipeline re-run 2026-09-02 reproduces identical outputs — unified_dataset (1,095,759×139), planning_area_360 (43×27), town_360 (28×13), block_profile (10,002×6), pa_monthly_metrics (13,104×11), appreciation_hotspots (20×6); month nulls 0.00%, tier non-null 98.9%, interchange 10.7% of tiered rows.
- 📝 **Observation (pre-existing, documented)**: `nearest_mall` is empty-string by design — the URA MP25 MALL-classified layer carries no names (294 sites; wiki parquets with real names are deprecated). Distances are correct for that POI set but sparse outside the core (Orchard 96 m, Punggol 9.5 km). If named malls are ever wanted, a OneMap SEARCHVAL mall-address source or SLA POI layer would restore names + density.

## Known Debt (audit findings, not yet scheduled)

- OneMap: no pagination (`pageNum=1` fixed — accepted: first search hit is the match), JWT base64 padding nit (`onemap.py:57`).
- `validation_gateway.py` sample validation uses fixed seed-42 sample; precheck issues only log.
- `min_coordinate_coverage` is warn-only despite gate-like name (`cleaning.py`).
- `LAYER_PATH_MAP` (layer_writer) vs `LayerDirs` (config) are two sources of truth; `Settings.layer_dir()` silently drops custom dir components.
- `metrics.py` duplicates config defaults; `L5_appreciation_hotspots.parquet` legacy filename; `HRentalYieldRecord.flat_type` never populated; Hamilton tracker hardcodes `project_id=1`/`env=dev`.
- `ura_csv.py` hardcodes `property_type="condo"` for all URA rows; EC CSVs not globbed.
- `data/metadata.json` contains absolute `/Users/minghao` paths; `metadata.json.bak2` not gitignored.
- `_town_upper` astype(str) "NAN" pattern in `features.py` (temp column, dropped — cosmetic).
- datagovsg adapter: no `requests.Session` reuse; `Retry-After` HTTP-date form raises inside handler.

## Key Decisions Made

- Refresh-first ordering: validate the stack end-to-end before refactoring; refactor re-runs are cheap (bronze seeds + OneMap address cache persist).
- URA data comes via data.gov.sg (official channel), not eservice scraping.
- Bronze seeder warns loudly but does not hard-fail on missing external files (R2 set was incomplete; hard fail would brick fresh clones). Revisit once R2 is complete.
- `--refresh` full form clears API cache; targeted form clears bronze only (API cache TTL 24h limits staleness).
