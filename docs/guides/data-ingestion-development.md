# Data Ingestion Development Guide

**Status**: Active

Data ingestion acquires external and manual sources into the bronze layer. The
supported path is a source adapter plus a Hamilton node under
`src/egg_n_bacon_housing/components/ingestion/`.

## Source-onboarding record

Before adding a source, record the following in this guide or the source's
documentation:

| Field      | Required detail                                                     |
| ---------- | ------------------------------------------------------------------- |
| Identity   | Owner, URL/resource ID, dataset name, and acquisition method        |
| Operations | Cadence, freshness expectation, and source grain                    |
| Access     | Authentication variables, rate limits, and request constraints      |
| Contract   | Schema, primary/business keys, join keys, and normalization         |
| Storage    | Bronze node/output name, cache path, and retention/freshness policy |
| Failure    | Required/optional status, retries, fallback, and error behavior     |
| Lineage    | Downstream silver/gold/platinum consumers                           |

Manual source bundles are synced from Cloudflare R2 with
`uv run python scripts/00_sync_data.py`; they are not committed
to the repository.

## Adopted sources

Records for the amenity/POI sources seeded into `bronze/external/` (all
DACA-compliant datagov.sg GeoJSON exports; no authentication; seed sources
listed in `utils/bronze.py`). Shared properties: row grain = one point per
facility; join key = coordinates only (features compute proximity); failure
policy = optional — missing file warns and degrades to empty proximity
features; freshness = agency-driven updates (check `FMEL_UPD_D` field).

| File (bronze/external)      | Dataset (data.gov.sg ID)                                                                  | Name column                      | Node                    | Consumers      |
| --------------------------- | ----------------------------------------------------------------------------------------- | -------------------------------- | ----------------------- | -------------- |
| `BusStops.geojson`          | Bus Stops (LTA) `d_3f172c6feb3f4f92a2f47d93eed2908a` (~5.2k stops)                        | `BUS_STOP_NUM`                   | `raw_bus_stops`         | `location_dim` |
| `CHASClinics.geojson`       | CHAS Clinics (MOH) `d_548c33ea2d99e29ec63a7cc9edcccedc` (~1.2k clinics)                   | `HCI_NAME` (in Description HTML) | `raw_chas_clinics`      | `location_dim` |
| `SportSGFacilities.geojson` | SportSG Sport Facilities `d_9b87bab59d036a60fad2a91530e10773` (~45; excludes DUS schools) | `VENUE`                          | `raw_sports_facilities` | `location_dim` |
| `CommunityClubs.geojson`    | Community Club / PAssion WaVe Outlet (PA) `d_9de02d3fb33d96da1855f4fbef549a0f` (~128)     | `NAME`                           | `raw_community_clubs`   | `location_dim` |

MRT station/line JSONs (`mrt_stations.json`, `mrt_lines.json`) and
`school_tiers.json` are not seed sources: they have in-code fallbacks, and
`mrt_stations.json` is now regenerated from the live LTA sources below.

### MRT/LRT stations (LTA live sources)

| Field      | Detail                                                                                                                                                                                                                                                                                                                                           |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Identity   | LTA, "MRT Station Exit (GEOJSON)" `d_b39d3a0871985372d7e1637193335da5` (613 exits, fresh coordinates; `FMEL_UPD_D` 2025-12+) + "Train Station Chinese Names" `d_d312a5b127e1ae74299b8ae664cedd4e` (station code/name + line, 184 rows)                                                                                                           |
| Operations | LTA-maintained; re-fetched per bronze miss; grain = one station row (centroid of exits) with line codes                                                                                                                                                                                                                                          |
| Access     | Unauthenticated; GeoJSON via the initiate/poll download flow, codes via the datastore API                                                                                                                                                                                                                                                        |
| Contract   | Station names normalized ("BAYSHORE MRT STATION" -> "BAYSHORE") to match `mrt_line_mapping` keys; line names matched to codes case/hyphen-insensitively. Known LTA gap: the codes dataset has no TEL rows — a static supplement in `components/ingestion/geojson.py` (`_STATION_LINE_SUPPLEMENT`) fills TEL + Punggol Coast until LTA catches up |
| Storage    | Node `raw_mrt_stations` → bronze `raw_mrt_stations.parquet`; also refreshes `bronze/external/mrt_stations.json` for `mrt_line_mapping`; empty fetch never cached                                                                                                                                                                                 |
| Failure    | Optional — live fetch failure falls back to the legacy 2019 static seeds (`MRTStations.geojson` + hardcoded fallbacks), then empty                                                                                                                                                                                                               |
| Lineage    | `location_dim` MRT proximity (dist, nearest station, tier, interchange, score) → transactions_enriched → analytics                                                                                                                                                                                                                               |

Superseded: the git-tracked `data/raw/external/datagov/MRTStations.geojson`
(2019-12 snapshot, pre-TEL) remains only as the offline fallback seed.

### Shopping malls (URA MP25 layer)

| Field      | Detail                                                                                                                                                                                                                |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Identity   | URA, "Master Plan 2025 SDCP Mall, Promenade and Thru-Block Link layer", data.gov.sg `d_65a0bf22c15ef49e9a21b8bcf8c04c87`, fetched via `adapters.datagovsg.fetch_datagovsg_geojson` (initiate/poll/presigned-URL flow) |
| Operations | Master Plan cadence (revised ~every 5 years); grain = one polygon per designated site                                                                                                                                 |
| Access     | Unauthenticated; presigned URL valid briefly; single download, no pagination                                                                                                                                          |
| Contract   | GeoJSON polygons; keep `CLASSIFCTN == "MALL"` only; centroid → `lat/lon`; **no names** (`nearest_mall` stays empty)                                                                                                   |
| Storage    | Node `raw_shopping_malls` → bronze `raw_mp25_malls.parquet`; empty fetch never cached                                                                                                                                 |
| Failure    | Optional — fetch/poll errors warn and degrade to empty proximity features; empty layer never cached                                                                                                                   |
| Lineage    | `location_dim.dist_to_nearest_mall` / `nearest_mall` → transactions_enriched → analytics                                                                                                                              |

Legacy wiki-sourced parquets (`raw_wiki_shopping_mall[_geocoded].parquet`,
produced by `notebooks/L0_wiki.ipynb`) still take precedence when present but
are deprecated — delete them (or run
`main.py --refresh 'raw_wiki_shopping_mall*'`, quoted so the shell does not
expand the glob; it clears both wiki parquets so the next run fetches the MP25
layer) to switch sources.

### URA private residential transactions (live API + CSV history)

| Field      | Detail                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Identity   | URA Data Service API, `https://eservice.ura.gov.sg/uraDataService` — `insertNewToken/v1` + `invokeUraDS/v1?service=PMI_Resi_Transaction&batch=1..4`, via `adapters.ura`                                                                                                                                                                                                                                                                                                                                                  |
| Operations | Rolling 5-year window, refreshed every pipeline run (data through the current month); grain = one transaction row                                                                                                                                                                                                                                                                                                                                                                                                        |
| Access     | `URA_API_ACCESS_KEY` (free registration at eservice.ura.gov.sg/maps/api/reg.html). Layer7 bot wall: browser-like `User-Agent`/`Accept`/`Referer` on a `requests.Session` required, else an HTML challenge is served. Token: daily validity, cached 8h under a per-access-key cache id (`ura_api_token:<key-hash>`); one refresh-retry on auth failure per fetch, and the force-refreshed token is written back to the token cache so the next run within the TTL reuses it instead of repeating the reject+refresh cycle |
| Contract   | Nested per-property rows (`project`/`street`/`marketSegment` + `transaction[]` list) are exploded; `contractDate` MMYY → `transaction_date`; `area` unit follows `typeOfArea` (Strata=sqft, Land=sqm); `typeOfSale` 1/2/3 → New/Sub Sale/Resale; `marketSegment` CCR/RCR/OCR → full region names; `property_type="condo"` is the normalized asset class while URA's actual `propertyType` is preserved as `property_subtype`                                                                                             |
| Storage    | Node `raw_condo_transactions` → bronze `raw_condo_transactions.parquet`; API rows merged with the manual R2 CSV history (pre-window years), deduped on the natural key (project, street, month, price, area, sale type, floor, units) — CSV rows win in the overlap. Fetches are recorded in `01_bronze/bronze_manifest.json` (source + timestamp + row count); rolling-window bronze caches (`raw_condo_transactions`, `raw_hdb_resale`) emit a stale warning past `STALE_WARN_DAYS` (see `utils/bronze.py`)            |
| Failure    | Optional — API failure (auth, rate limit, malformed) warns and falls back to CSVs-only; no CSVs and no usable API raises `RuntimeError` (core dataset); empty/partial API responses never replace a valid cache                                                                                                                                                                                                                                                                                                          |
| Lineage    | `cleaned_condo_transactions` → `condo_validated` → `geocoded_validated` → `transactions_enriched` → analytics                                                                                                                                                                                                                                                                                                                                                                                                            |

The manual CSV exports (`data/manual/csv/ura/ResidentialTransaction*.csv` and
`ECResidentialTransaction*.csv`, synced via R2) remain the pre-window history
and offline fallback. EC files are included explicitly and default to
`property_subtype="Executive Condominium"` when their export omits the source
property-type column.

At the silver boundary, `cleaned_condo_transactions` derives the stable
analytical `property_segment` (`condominium`, `apartment`, `ec`, landed-house
segments, or an explicit other/unspecified value) and `is_ec`. The original
`property_subtype` remains unchanged for source fidelity; pricing and market
analysis should use `property_segment` rather than the broad `property_type`.

### OneMap geocoding (auth/retry hardening)

| Field         | Detail                                                                                                                                                                                                                                                                                                                                                                            |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Identity      | SLA OneMap `https://www.onemap.gov.sg/api` (token endpoint + `/common/elastic/search`)                                                                                                                                                                                                                                                                                            |
| Auth          | JWT via `ONEMAP_EMAIL`/`ONEMAP_EMAIL_PASSWORD` (or a pre-issued `ONEMAP_TOKEN`); expired env tokens trigger a fresh token request; a mid-run 401/403 surfaces as `OneMapAuthError` and `OneMapGeocoder` refreshes headers once (`on_auth_expired` callback, thread-safe, single-flight — one network refresh per mid-run expiry even with concurrent workers) and retries         |
| Retry         | Only transient failures are retried (429/5xx/network), max 3 attempts; 429 honors the `Retry-After` header (delta-seconds or HTTP-date, capped at 60s); 4xx and `CredentialError` fail fast (missing creds are never retried)                                                                                                                                                     |
| Rate limiting | `geocoding.api_delay_seconds` paces actual API misses via a thread-safe `_RateLimiter` shared by the sequential and parallel paths; cache hits are never paced                                                                                                                                                                                                                    |
| Storage       | Responses cached per search string (`onemap_search:<address>`) via `utils/cache.py` under `geocoding.cache_duration_hours` for both reads and writes; failures are never cached. A 200 payload missing the `results` key is treated as malformed (`DatasetFetchError`, retried then surfaced — never cached), while `found: 0` with `results: []` is a valid cached empty success |
| Failure       | Addresses that still fail return null-coordinate rows (pipeline continues, coverage logged by the silver validation gateway)                                                                                                                                                                                                                                                      |

## Code placement

- `adapters/` owns HTTP/CSV transport, authentication, pagination, retries,
  response parsing, and source-specific exceptions. `adapters/_http.py` holds
  the shared `Retry-After` parser (delta-seconds or HTTP-date) used by the
  OneMap and data.gov.sg adapters.
- `components/ingestion/` owns Hamilton node signatures, source selection,
  bronze normalization, and output persistence.
- `utils/cache.py` owns reusable cache behavior. Existing valid caches take
  precedence when a source is unavailable; empty responses must not destroy a
  valid cache.
- Bronze parquets are the only cache layer under the datagov fetch nodes
  (`components/ingestion/datagov.py`): an empty (0-row) bronze cache is treated
  as a miss (warn + refetch) at `_load_or_fetch_dataset`, `raw_hdb_resale_transactions`,
  and the wiki-mall branch of `raw_shopping_malls` (macro and MP25 already held
  this contract), and the parameterized nodes (rental index, HDB rental, school
  directory) keep no `cached_call` API layer under bronze, so `main.py --refresh`
  re-fetches instead of re-serving a 24h API-cache payload.
- Cached adapters require an explicit `CacheManager`. Production receives the
  per-run `cache_manager` Hamilton input (or an injected geocoder that owns it);
  module-global cache configuration is not supported.
- MRT ingestion receives `mrt_reference` explicitly. Its line and station caches
  are independent so a live station fetch can refresh `mrt_stations.json` before
  downstream location features first read the station mapping.
- Macro ingestion (`components/ingestion/macro.py`) fetches its 8 data.gov.sg
  indicators through a bounded thread pool (4 workers; rate-limit safety —
  pagination within a source stays serial, see `adapters/datagovsg.py`). Results
  and the failure summary are ordered by source, and failure semantics match the
  serial loop: retrievable errors degrade only their source; programming defects
  re-raise after the pool drains. Concurrent fetch-and-write points serialize
  their manifest updates via a lock in `utils/bronze.py`.
- Cleaning, schema validation, and quarantine belong to the silver stage.

Keep source credentials in `Settings` and environment variables. The default
test suite must use mocked transport and deterministic fixtures rather than live
APIs.

## Minimum tests

Every new or changed source should cover, as applicable:

- successful fetch and response normalization;
- cache hit and cache preservation on empty/error responses;
- timeout, authentication, rate-limit, and malformed-response behavior;
- manual-file discovery and missing-file behavior;
- Hamilton node name, dependencies, bronze output, and empty-source policy.

Run the focused suite with:

```bash
uv run pytest tests/test_ingestion.py tests/test_datagovsg.py tests/test_onemap.py --no-cov -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/tools/validate_docs_layout.py
uv run python scripts/tools/validate_agent_skills.py
git diff --check
```
