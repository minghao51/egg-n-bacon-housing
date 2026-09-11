# Data Sources

**Last Updated**: 2026-09-01 (post full-refresh) | **Status**: Active

A complete inventory of every dataset, API, and manual file that powers the Egg-n-Bacon Housing platform. Numbers reflect the 2026-09-01 full pipeline refresh.

---

## Transaction Data

The core of the platform — historical property transactions across HDB and private residential markets.

| Dataset                              | Source                                   | Coverage            | Records    | Automation                                    |
| ------------------------------------ | ---------------------------------------- | ------------------- | ---------- | --------------------------------------------- |
| HDB Resale Transactions              | data.gov.sg API + historical CSVs        | Jan 1990 – Aug 2026 | 985,670    | API (2017+, automated) + manual CSVs (1990–2016) |
| URA Private Residential Transactions | **Live URA Data Service API** + R2 CSV history | through Aug 2026 | ~225K merged | Automated — API (rolling 5y) merged with pre-window CSVs |
| HDB Rental Median                    | data.gov.sg API                          | rolling             | automated  | Fully automated                               |
| URA Rental Index                     | data.gov.sg API                          | through 2026-Q1     | 515        | Fully automated                               |

**HDB Resale**: The data.gov.sg API covers January 2017 onwards (239,467 records fetched per refresh). Pre-2017 records (1990–2016) are loaded from historical CSV files stored in Cloudflare R2 and merged at ingestion, producing a continuous 36-year transaction history.

**URA Private Transactions (current state)**: Row-level private residential transactions come from manual CSV exports of the URA bulk-download portal, synced via R2 (`data/manual/csv/ura/ResidentialTransaction*.csv` and `ECResidentialTransaction*.csv`). Both private-residential and Executive Condominium files are ingested. The stable `property_type="condo"` asset class is retained for downstream compatibility, while URA's actual type is preserved in `property_subtype`.

### URA Data Service API — WIRED (live since 2026-09-02)

URA operates an official REST API that returns **row-level** private residential transactions — the same data as the manual CSVs, without CAPTCHA:

| Item        | Detail                                                                                                       |
| ----------- | ------------------------------------------------------------------------------------------------------------ |
| Token       | `GET https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1` with `AccessKey` header (daily token)      |
| Transactions | `invokeUraDS?service=PMI_Resi_Transaction` — row-level sales incl. sale type; **rolling 5-year window**; `batch=1..4` (postal-district split) |
| Rental contracts | `service=PMI_Resi_Rental` with `refPeriod` (qqyy)                                                       |
| Registration | Free at https://eservice.ura.gov.sg/maps/api/reg.html — AccessKey sent by email                              |
| Verified    | Token endpoint live as of 2026-09-01 (rejects invalid keys with `{"Status":"Error","Message":"Invalid Access Key"}`); full adapter + bronze node live-verified 2026-09-02 (133,942 API rows, window 2021-08 → 2026-08) |

Live notes: the Layer7 bot wall requires browser-like ``User-Agent``/``Accept``/``Referer`` on a session (else an HTML JS challenge is served); the token lives under ``Result``; ``contractDate`` is MMYY; ``area`` is sqft for Strata and sqm for Land; API ``propertyType`` is preserved as ``property_subtype``. Adapter: ``adapters/ura.py`` (token cached 8h, one refresh-retry on auth failure); node: ``raw_condo_transactions`` merges API rows plus Residential and EC CSV history, deduped on the natural key (CSV rows win in the overlap). Quarterly aggregates on data.gov.sg (`d_7c69c943d5f0d89d6a9a773d2b51f337`, `d_1a7823f3d31e7db4b426833833762bab`) are **not** a substitute — they are pre-aggregated unit counts, not row-level records.

---

## Amenity & Spatial Data

Proximity to amenities is computed for every transaction using haversine distance via BallTree/cKDTree.

### Core Amenities

| Amenity                    | Source (dataset ID)                                              | Locations | Automation                        |
| -------------------------- | ---------------------------------------------------------------- | --------- | --------------------------------- |
| MRT/LRT Stations           | LTA "MRT Station Exit (GEOJSON)" `d_b39d3a0871985372d7e1637193335da5` + "Train Station Chinese Names" `d_d312a5b127e1ae74299b8ae664cedd4e` | 190 stations | **Live fetch** per bronze miss; station→line mapping auto-refreshed (`mrt_stations.json`, 181 entries) |
| Shopping Malls             | URA MP25 layer `d_65a0bf22c15ef49e9a21b8bcf8c04c87` (CLASSIFCTN = MALL) | 294 sites | **Live fetch** per bronze miss    |
| Bus Stops                  | LTA `d_3f172c6feb3f4f92a2f47d93eed2908a`                          | 5,205     | R2-seeded (auto-uploaded)         |
| CHAS Clinics               | MOH `d_548c33ea2d99e29ec63a7cc9edcccedc`                          | 1,193     | R2-seeded; names parsed from KML Description HTML |
| SportSG Facilities         | SportSG `d_9b87bab59d036a60fad2a91530e10773`                      | 45        | R2-seeded                         |
| Community Clubs            | PA `d_9de02d3fb33d96da1855f4fbef549a0f`                           | 128       | R2-seeded                         |
| Hawker Centres             | `HawkerCentresGEOJSON.geojson` (manual bundle)                     | 129       | Manual bundle                     |
| Supermarkets               | `SupermarketsGEOJSON.geojson` (manual bundle)                      | 526       | Manual bundle                     |
| Parks & Nature Reserves    | `NParksParksandNatureReserves.geojson` (manual bundle)             | 450       | Manual bundle                     |
| Childcare Centres          | `ChildCareServices.geojson` (manual bundle)                        | 1,925     | Manual bundle                     |
| Preschools / Kindergartens | `PreSchoolsLocation.geojson` (manual bundle)                       | 2,290     | Manual bundle                     |

Notes:

- MP25 mall polygons are centroid-ed to points; the layer carries **no mall names** (`nearest_mall` stays empty — distances are correct). The legacy Wikipedia-scrape mall list (`notebooks/L0_wiki.ipynb`) is a deprecated fallback.
- LTA's station-codes dataset has no Thomson-East Coast Line rows yet; a static supplement in `components/ingestion/geojson.py` (`_STATION_LINE_SUPPLEMENT`) fills TEL + Punggol Coast until LTA catches up. Trim it when the live data covers them.
- The 2019 static `MRTStations.geojson` seed remains only as an offline fallback.

### Green Mark Buildings

| Dataset                  | Source                                                 | Records | Geocoding                    |
| ------------------------ | ------------------------------------------------------ | ------- | ---------------------------- |
| BCA Green Mark Buildings | data.gov.sg API (`d_c4bd082b48fa7611713f39e23d250c27`) | 3,941   | OneMap postal code → lat/lon |

---

## Macro Economic Indicators

All fetched live from data.gov.sg on each refresh (2026-09-01 verified record counts in parentheses).

| Indicator                       | Frequency | Records (2026-09-01) |
| ------------------------------- | --------- | -------------------- |
| Consumer Price Index (CPI)      | Monthly   | 787                  |
| GDP (Chained 2015 Dollars)      | Quarterly | 201                  |
| Unemployment Rate               | Quarterly | 138                  |
| SORA 3M (Compounded, bank rates)| Monthly   | 462                  |
| HDB Resale Price Index          | Quarterly | 146                  |
| URA Property Price Index        | Quarterly | automated            |
| Private Housing Supply Pipeline | Quarterly | automated            |
| SORA (pre-built parquet, R2)    | Monthly   | 60 (static seed)     |

**SORA 3M** is the primary mortgage benchmark; **HDB RPI / URA PPI** are official price benchmarks used for model validation; **Supply Pipeline** is a forward supply-pressure indicator.

---

## Block-Level Property Metadata

| Dataset                  | Source                                                 | Records       | Key Fields                                                                 |
| ------------------------ | ------------------------------------------------------ | ------------- | -------------------------------------------------------------------------- |
| HDB Property Information | data.gov.sg API (`d_17f5382f26140b1fdae0ba2ef6239d2f`) | ~13k blocks   | max_floor_lvl, year_completed, total_dwelling_units, flat types, mixed-use |
| Dwelling Units by Town   | data.gov.sg API (HDB)                                  | 4,940         | financial_year through 2021 (HDB census-type snapshot)                     |

---

## School Data

| Dataset                | Source          | Records      | Notes                                             |
| ---------------------- | --------------- | ------------ | ------------------------------------------------- |
| School Directory       | data.gov.sg API | 337 schools  | Names, addresses, postal codes (no coordinates)   |
| School Geocoding       | OneMap API      | cached       | OneMap on first run, cached thereafter            |
| Primary/Secondary Tiers| Manual + CSV    | tier data    | In-code fallbacks + R2 CSVs                       |

---

## Demographic & Income Data

| Dataset                              | Source                                                 | Records            | Key Fields                                          |
| ------------------------------------ | ------------------------------------------------------ | ------------------ | --------------------------------------------------- |
| Income Distribution by Planning Area | data.gov.sg API (`d_bb771c5189ce18007621533dd36142bb`) | ~30 planning areas | 15 income brackets → weighted median income per area |

Source: General Household Survey 2015 (SingStat) — static snapshot by design.

---

## Reference Geographies

| Dataset                    | Source      | Purpose                                                            |
| -------------------------- | ----------- | ------------------------------------------------------------------ |
| Planning Area Polygons     | OneMap API (R2 bundle) | Point-in-polygon planning-area assignment               |
| MRT Station → Line Mapping | Live LTA + static supplement | `bronze/external/mrt_stations.json` auto-refreshed by the MRT node; consumed by `utils/mrt_line_mapping.py` |

---

## Geocoding

All address-to-coordinate conversion uses the **OneMap API** (`adapters/onemap.py` + `utils/geocoding.py`).

- ~13.3k unique addresses/postals geocoded per full refresh; 98.9% coverage (HDB 98.8%, condo 100%).
- Hardened 2026-09-01: 429/`Retry-After` honored, transient-only retries (3×), typed auth errors with **mid-run token refresh**, thread-safe global rate limiting (`api_delay_seconds`) across sequential and parallel paths; cache hits are never paced.
- Credentials via `ONEMAP_EMAIL` / `ONEMAP_EMAIL_PASSWORD` (or pre-issued `ONEMAP_TOKEN`); failures are never cached.

---

## Unstructured / Potential Sources (not wired)

| Source                               | Potential Use                                  | Status     |
| ------------------------------------ | ---------------------------------------------- | ---------- |
| PropertyGuru / 99.co listings        | Asking prices, days-on-market                  | Not integrated |
| Reddit / news feeds / Google reviews | Sentiment, POI quality                         | Not integrated |
| URA GLS tender results               | Developer land-bid sentiment                   | Not integrated |
| SportSG DUS `d_7ff555dfb7104533494b23a60188a044` | Dual-use school sport facilities    | Not integrated (deliberate) |

The Wikipedia mall-scrape notebook is deprecated (superseded by the live URA MP25 layer).

---

## Data Storage

| Layer               | Location                                 | Content                                       |
| ------------------- | ---------------------------------------- | --------------------------------------------- |
| Manual source files | Cloudflare R2 (`egg-bacon-housing-data`) | ~124 MB CSVs/GeoJSONs (gitignored)            |
| Bronze (raw)        | `data/pipeline/01_bronze/`               | Immutable raw data; external seeds auto-copied |
| Silver (cleaned)    | `data/pipeline/02_silver/`               | Validated, type-checked, deduplicated         |
| Gold (features)     | `data/pipeline/03_gold/`                 | Proximity + macro features                    |
| Platinum (outputs)  | `data/pipeline/04_platinum/`             | Unified dataset (1,095,759 × 139), metrics    |

Sync via `scripts/00_sync_data.py` (see the [R2 sync guide](guides/r2-sync-guide.md)). `main.py --refresh --stage all` clears bronze + DAG + API caches and re-fetches everything (cold ≈ 2¼ h, dominated by OneMap geocoding; warm ≈ minutes).

---

## Refresh Cadence

| Data Source                      | Frequency | Automation                              |
| -------------------------------- | --------- | --------------------------------------- |
| HDB Resale (2017+)               | Monthly   | Automated — data.gov.sg API             |
| HDB Resale (1990–2016 CSVs)      | Static    | One-time manual load (R2)               |
| URA Private Transactions         | On refresh| **Automated — URA Data Service API** + CSV history merge |
| HDB Rental / Rental Index        | M / Q     | Automated                               |
| Macro indicators (CPI, GDP, unemployment, SORA 3M, RPI, PPI, supply) | M / Q | Automated — data.gov.sg API |
| MRT stations + line mapping      | On refresh| Automated — LTA live sources            |
| Shopping malls                   | On refresh| Automated — URA MP25 via data.gov.sg    |
| Green Mark / Property Info       | On demand | Automated — data.gov.sg API             |
| Bus stops / CHAS / SportSG / CC  | On demand | R2-seeded (upload once, auto-seed)      |
| Other amenity GeoJSONs           | On demand | Manual bundle (slow-changing)           |
| Income by planning area          | Static    | GHS 2015 snapshot                       |
| Planning area polygons           | Static    | One-time OneMap fetch (R2)              |

---

## Further Reading

- [Source onboarding records](guides/data-ingestion-development.md) — per-source contracts, cache & failure policy
- [data.gov.sg Resource Migration Guide](guides/datagovsg-resource-migration.md) — Resource IDs, schema changes
- [Singapore Open Datasets Research](research/singapore-open-datasets.md) — Catalog of 150+ scanned datasets
- [Architecture Overview](architecture.md) — Pipeline structure and medallion layers
- [Pipeline refresh handoff](plans/2026-09-01-pipeline-refresh-handoff.md) — 2026-09-01 refresh run log
