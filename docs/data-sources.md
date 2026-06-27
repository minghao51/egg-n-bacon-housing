# Data Sources

**Last Updated**: 2026-06-15 | **Status**: Active

A complete inventory of every dataset, API, and manual file that powers the Egg-n-Bacon Housing platform.

---

## Transaction Data

The core of the platform — historical property transactions across HDB and private residential markets.

| Dataset                              | Source                            | Coverage            | Records  | Automation                            |
| ------------------------------------ | --------------------------------- | ------------------- | -------- | ------------------------------------- |
| HDB Resale Transactions              | data.gov.sg API + historical CSVs | Jan 1990 – Jun 2026 | ~970,000 | API (2017+) + manual CSVs (1990–2016) |
| HDB Rental Median                    | data.gov.sg API                   | Jan 2021 – May 2026 | 200,000+ | Fully automated                       |
| URA Private Residential Transactions | URA website (manual download)     | Quarterly batches   | ~40,000  | Manual — CAPTCHA-gated                |
| URA Rental Index                     | data.gov.sg API                   | 2004-Q1 – 2026-Q1   | 515      | Fully automated                       |

**HDB Resale**: The data.gov.sg API covers January 2017 onwards. Pre-2017 records (1990–2016) are loaded from five historical CSV files stored in Cloudflare R2 and merged at ingestion time, producing a continuous 36-year transaction history.

**URA Transactions**: URA requires CAPTCHA verification for bulk downloads, so these CSVs are fetched manually from the [URA bulk download portal](https://www.ura.gov.sg/property-market-information/transaction-bulk-download) on a quarterly cadence.

---

## Amenity & Spatial Data

Proximity to amenities is computed for every transaction record using haversine distance via BallTree.

### Core Amenities (GeoJSON)

| Amenity                    | Source File                          | Locations | Median Distance | Automation                                 |
| -------------------------- | ------------------------------------ | --------- | --------------- | ------------------------------------------ |
| MRT Stations               | MRTStations.geojson                  | 180+      | 513 m           | Manual download                            |
| Hawker Centres             | HawkerCentresGEOJSON.geojson         | 129       | 596 m           | Manual download                            |
| Supermarkets               | SupermarketsGEOJSON.geojson          | 526       | 290 m           | Manual download                            |
| Parks & Nature Reserves    | NParksParksandNatureReserves.geojson | 450       | 622 m           | Manual download                            |
| Childcare Centres          | ChildCareServices.geojson            | 1,925     | 126 m           | Manual download                            |
| Preschools / Kindergartens | PreSchoolsLocation.geojson           | 2,290     | 125 m           | Manual download                            |
| Shopping Malls             | Wikipedia + OneMap geocoding         | 112       | —               | Semi-automated (notebook scrape → geocode) |
| Bus Stops                  | BusStops.geojson                     | —         | —               | Manual download (LTA)                      |
| CHAS Clinics               | CHASClinics.geojson                  | —         | —               | Manual download                            |
| SportSG Facilities         | SportSGFacilities.geojson            | —         | —               | Manual download                            |
| Community Clubs            | CommunityClubs.geojson               | —         | —               | Manual download                            |

All amenity GeoJSON files originate from data.gov.sg and are stored in Cloudflare R2. Shopping mall names are scraped from Wikipedia and then geocoded via OneMap to obtain coordinates.

### Green Mark Buildings (CSV + geocoding)

| Amenity                  | Source                                                 | Records                   | Geocoding                    | Automation                           |
| ------------------------ | ------------------------------------------------------ | ------------------------- | ---------------------------- | ------------------------------------ |
| BCA Green Mark Buildings | data.gov.sg API (`d_c4bd082b48fa7611713f39e23d250c27`) | 3,941 (with postal codes) | OneMap postal code → lat/lon | API fetch + features-layer geocoding |

Green Mark buildings include commercial, residential, institutional, and industrial properties certified under BCA's Green Mark scheme (Platinum, Gold, GoldPlus, Certified). Postal codes are geocoded via OneMap in the features layer on first pipeline run, then cached.

---

## Macro Economic Indicators

Macroeconomic context is merged into the unified dataset at the feature engineering stage.

### Core Indicators

| Indicator                       | Source            | Frequency | Coverage          | Records |
| ------------------------------- | ----------------- | --------- | ----------------- | ------- |
| Consumer Price Index (CPI)      | data.gov.sg API   | Monthly   | 1961 – Apr 2026   | 784     |
| GDP (Chained 2015 Dollars)      | data.gov.sg API   | Quarterly | 1976 – 2026-Q1    | 201     |
| Unemployment Rate               | data.gov.sg API   | Quarterly | 1992 – 2026-Q1    | 137     |
| SORA (Swap Offer Rate)          | Pre-built parquet | Monthly   | 2021 – 2025       | 60      |
| SORA 3M (Compounded)            | data.gov.sg API   | Monthly   | 2007 – Apr 2026   | ~200    |
| HDB Resale Price Index          | data.gov.sg API   | Quarterly | 1990-Q1 – 2026-Q1 | 145     |
| URA Property Price Index        | data.gov.sg API   | Quarterly | 1975-Q1 – 2026-Q1 | 615     |
| Private Housing Supply Pipeline | data.gov.sg API   | Quarterly | 2014-Q1 – 2026-Q1 | 152     |

CPI, GDP, unemployment, SORA 3M, and bank rates arrive as wide pivot tables from data.gov.sg and are melted into long-format time series at ingestion. SORA rates are a pre-built dataset. HDB RPI and URA PPI are quarterly time series with quarter + index columns.

**SORA 3M** (3-month compounded SORA) is the primary mortgage benchmark rate in Singapore, directly determining floating-rate home loan pricing.

**HDB RPI** and **URA PPI** provide official government price benchmarks for model validation — our model's price predictions can be compared against these indices.

**Supply Pipeline** tracks private residential units by development status (Under Construction, Planned — Written Permission, Planned — Provisional Permission) — useful as a forward supply pressure indicator.

---

## Block-Level Property Metadata

| Dataset                  | Source                                                 | Records       | Key Fields                                                                                |
| ------------------------ | ------------------------------------------------------ | ------------- | ----------------------------------------------------------------------------------------- |
| HDB Property Information | data.gov.sg API (`d_17f5382f26140b1fdae0ba2ef6239d2f`) | 13,289 blocks | max_floor_lvl, year_completed, total_dwelling_units, flat type breakdown, mixed-use flags |

Block-level metadata is merged onto transactions by matching block number + street name, adding building age, floor count, dwelling density, and mixed-use indicators.

---

## School Data

School proximity and quality tier features are computed for every transaction.

| Dataset                | Source                | Records      | Notes                                                |
| ---------------------- | --------------------- | ------------ | ---------------------------------------------------- |
| School Directory       | data.gov.sg API       | 337 schools  | Current snapshot with names, addresses, postal codes |
| School Geocoding       | OneMap API            | 261 geocoded | Postal code → lat/lon via sequential OneMap lookup   |
| Primary School Tiers   | Manual classification | Tier data    | JSON file in bronze/external                         |
| Secondary School Tiers | Manual classification | Tier data    | JSON file in bronze/external                         |

The school directory from data.gov.sg does not include coordinates. Schools are geocoded via OneMap on first pipeline run and cached — subsequent runs skip re-geocoding.

---

## Demographic & Income Data

| Dataset                              | Source                                                 | Records            | Key Fields                                                    |
| ------------------------------------ | ------------------------------------------------------ | ------------------ | ------------------------------------------------------------- |
| Income Distribution by Planning Area | data.gov.sg API (`d_bb771c5189ce18007621533dd36142bb`) | ~30 planning areas | Income bracket distribution (15 brackets, Below $1K to $12K+) |

Source: General Household Survey 2015 (SingStat). The pipeline computes a weighted median monthly income per planning area from 15 income brackets. This replaces a previously hardcoded $85,000/year affordability assumption with data-driven, area-specific income levels.

---

## Reference Geographies

| Dataset                    | Source      | Purpose                                                            |
| -------------------------- | ----------- | ------------------------------------------------------------------ |
| Planning Area Polygons     | OneMap API  | Point-in-polygon assignment of each transaction to a planning area |
| MRT Station → Line Mapping | Manual JSON | Maps each station to its MRT line(s) (NSL, EWL, CCL, etc.)         |

---

## Geocoding

All address-to-coordinate conversion uses the **OneMap API** — Singapore's official geospatial service.

| What                 | Method                               | Records Geocoded           |
| -------------------- | ------------------------------------ | -------------------------- |
| HDB Blocks           | OneMap search by block + street name | ~12,000 unique blocks      |
| Schools              | OneMap search by postal code         | 261 of 337 schools         |
| Shopping Malls       | OneMap search by mall name           | 112 malls                  |
| Green Mark Buildings | OneMap search by postal code         | ~3,900 unique postal codes |

OneMap credentials (email + password) are managed via encrypted environment variables. API rate limiting (429) is handled with sequential requests and exponential backoff.

---

## Unstructured Data

### Scraped Property Articles (not wired to pipeline)

| Location              | Content                                   | Status                                               |
| --------------------- | ----------------------------------------- | ---------------------------------------------------- |
| `data/raw/documents/` | 26 markdown articles + `master_index.csv` | **Orphaned** — not consumed by pipeline or analytics |

These articles were likely scraped from property portals (99.co, StackedHomes, PropertyReviewSG, etc.) and cover condo reviews and property-buying guides. These files represent an unrealised NLP/sentiment analysis capability.

### Wikipedia Shopping Mall Scrape (active)

| Location                  | Content                                            | Status                                       |
| ------------------------- | -------------------------------------------------- | -------------------------------------------- |
| `notebooks/L0_wiki.ipynb` | Scrapes Wikipedia list of Singapore shopping malls | **Active** — feeds `raw_shopping_malls` node |

The notebook scrapes mall names via BeautifulSoup, then the pipeline geocodes them via OneMap. Output is immediately structured into a parquet — this is the only active web-scraping workflow.

### Potential Unstructured Sources (not yet integrated)

| Source                               | Potential Use                                  | Access Method         |
| ------------------------------------ | ---------------------------------------------- | --------------------- |
| PropertyGuru / 99.co listings        | Asking prices, days-on-market, listing volume  | Web scraping or API   |
| Reddit r/singaporefi, r/askSingapore | Buyer sentiment, area preferences              | Reddit API            |
| Google Maps reviews                  | POI quality scores, amenity ratings            | Google Places API     |
| ST/CNA property news articles        | Market sentiment, policy event detection       | RSS feeds or news API |
| HDB BTO launch announcements         | Future supply at specific locations            | HDB website scraping  |
| MAS cooling measures timeline        | Policy event features for price shock analysis | MAS website           |
| URA GLS tender results               | Developer land bid sentiment                   | URA website scraping  |

---

## Data Storage

| Layer               | Location                                 | Content                                                    |
| ------------------- | ---------------------------------------- | ---------------------------------------------------------- |
| Manual source files | Cloudflare R2 (`egg-bacon-housing-data`) | ~100 MB of CSVs and GeoJSONs (gitignored)                  |
| Bronze (raw)        | `data/pipeline/01_bronze/`               | Immutable raw data from APIs and manual files              |
| Silver (cleaned)    | `data/pipeline/02_silver/`               | Validated, type-checked, deduplicated                      |
| Gold (features)     | `data/pipeline/03_gold/`                 | Feature-enriched with amenity proximity + macro indicators |
| Platinum (outputs)  | `data/pipeline/04_platinum/`             | Unified dataset, metrics, dashboard exports                |

Manual source files are synced from R2 via:

```bash
dotenvx run -- uv run python scripts/00_sync_data.py
```

See the [R2 sync guide](guides/r2-sync-guide.md) for details.

---

## Refresh Cadence

| Data Source                                     | Frequency | Automation                            |
| ----------------------------------------------- | --------- | ------------------------------------- |
| HDB Resale (API)                                | Monthly   | Automated — data.gov.sg API           |
| HDB Resale (historical CSVs)                    | Static    | One-time manual load                  |
| HDB Rental                                      | Monthly   | Automated — data.gov.sg API           |
| URA Rental Index                                | Quarterly | Automated — data.gov.sg API           |
| URA Transactions                                | Quarterly | **Manual** — URA website CAPTCHA      |
| CPI / SORA 3M                                   | Monthly   | Automated — data.gov.sg API           |
| GDP / Unemployment / HDB RPI / URA PPI / Supply | Quarterly | Automated — data.gov.sg API           |
| SORA                                            | Static    | Pre-built parquet                     |
| HDB Property Info                               | On demand | Automated — data.gov.sg API           |
| Income by Planning Area                         | Static    | GHS 2015 snapshot                     |
| Green Mark Buildings                            | On demand | Automated — data.gov.sg API           |
| Amenity GeoJSONs                                | On demand | Manual — re-download from data.gov.sg |
| School Directory                                | On demand | Automated — data.gov.sg API           |
| Planning Area Polygons                          | Static    | One-time fetch from OneMap            |

---

## Further Reading

- [data.gov.sg Resource Migration Guide](guides/datagovsg-resource-migration.md) — Resource IDs, schema changes, and API details
- [Singapore Open Datasets Research](research/singapore-open-datasets.md) — Full catalog of 150+ datasets scanned from data.gov.sg
- [External Data Setup Guide](guides/external-data-setup.md) — Manual download instructions for URA and amenity files
- [Architecture Overview](architecture.md) — Pipeline structure and medallion layers
- [Troubleshooting](TROUBLESHOOTING.md) — Common data source issues and fixes
