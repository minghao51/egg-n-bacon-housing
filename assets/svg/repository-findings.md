# Repository investigation

## Evidence labels and delegation

- **Verified** = inspected code, aggregate files, or local runtime. Paths/line anchors refer to the investigation checkout and may move.
- **Inference** = interpretation of that evidence, not a proven product/user outcome.
- **Proposal** = future work; not functionality that currently exists.
- Sol coordinated, independently checked public values and platinum missingness, researched references, ran the local app, and authored every final design file.
- No matching OpenCode/Codex MCP tools were exposed by tool discovery. The first investigation used installed CLIs. Revision 2 also checked the available harness subagent integration.
- `opencode models` lists `opencode-go/deepseek-v4.1-flash` and `opencode/deepseek-v4.1-flash-free`. Paid invocation failed with an expired-key error. **Backend investigation completed using the same DeepSeek V4.1 Flash model via the free OpenCode endpoint.**
- Codex's local model cache did not list Luna 6.0. Explicit `codex exec -m gpt-6-luna` failed: unsupported for this ChatGPT account. **Frontend investigation completed with explicitly disclosed fallback `gpt-5.6-luna` through Codex.**
- Revision 2 correction: the configured `luna-reviewer` successfully completed the audit with `openai-codex/gpt-6-luna:xhigh`. Standalone Codex account rejection did not establish global model unavailability. See [audit-review.md](audit-review.md).
- Investigations ran independently in parallel, read-only, with scopes backend/data vs frontend/routes/accessibility/tests. Neither investigator owned design files. Sol checked key conclusions rather than treating agent output as ground truth.
- Initial working tree was clean; an isolated design branch was created. Repository skills were read; no DAG/ingestion changes were made. Local ignored data was inspected in aggregate only. No credentials or transaction records are included.

## Product and audiences

**Verified:** Singapore housing pipeline plus a static analytics publishing application. It combines HDB resale, private/EC transactions, geography, amenities, rentals and macro context. See [root README](../../README.md), [app package](../../app/package.json), [data provenance](../../app/public/data/README.md).

**Inference:** likely audiences are buyers/upgraders comparing places, researchers auditing housing claims, and investors exploring price/yield tradeoffs. Persona pages exist, but no user interviews, usage analytics or conversion research were available. Treat audience prioritization as a product hypothesis.

**Proposal:** prioritize understanding and comparison over automated investment recommendations. A planning-area aggregate cannot answer whether a particular flat is fairly priced.

## Architecture and actual routes

| Layer             | Verified implementation                                                                                             | Important constraint                                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Python runtime    | `main.py` → `build_pipeline` / `run_pipeline`, [pipeline.py](../../src/egg_n_bacon_housing/pipeline.py):101,163,215 | Hamilton stages ingest/clean/features/export/metrics; dependency injection                                                       |
| Persistence       | [output_registry.py](../../src/egg_n_bacon_housing/utils/output_registry.py):23,54; companion materializers         | Bronze exceptions and validation boundaries must follow repository skills; no second runner                                      |
| Published dataset | [export.py](../../src/egg_n_bacon_housing/components/export.py):21,27                                               | Unified platinum validation defaults to sampling 10,000 rows; schema ≠ complete validation guarantee                             |
| App export        | [export_app_data.py](../../scripts/export_app_data.py):224,536,563,622,763                                          | Separate maintenance step reads platinum; seven gzipped dashboard outputs; per-file atomic swaps, not a release-wide transaction |
| Site              | [astro.config.mjs](../../app/astro.config.mjs), [content.config.ts](../../app/src/content.config.ts):6              | Static Astro, React 19 islands, Tailwind 3; Bun 1.2.23; GitHub Pages base path supported                                         |
| Interactive UI    | Recharts, Leaflet/react-leaflet, TanStack Table; [useGzipJson.ts](../../app/src/hooks/useGzipJson.ts):1–124         | Browser decompression, abort/reload, five-minute memory cache; compile-time types are not runtime validation                     |
| Research          | Markdown in [docs/analytics](../../docs/analytics), precomputed research assets                                     | Separate generation/vintage; retired standalone analytics package is unsupported                                                 |

Routes verified in source:

- `/`: marketing entry, animated transaction count, hardcoded milestones and highlighted research.
- `/dashboard`: overview; `/dashboard/map`: area maps/tools; `/dashboard/trends`: trends/tools.
- `/dashboard/leaderboard`: area comparison/ranking, map + table, search, filters, mobile drawer.
- `/dashboard/segments`: discover → select → investigate → area evidence.
- `/analytics`, `/analytics/[slug]`, `/analytics/personas/[persona]`: articles and persona recommendations.
- `/catalog`, `/catalog/[layer]`, `/catalog/[layer]/[...dataset]`: medallion inventory, DAG/schema details.

References: [app pages](../../app/src/pages), [SegmentsDashboard.tsx](../../app/src/components/dashboard/segments/SegmentsDashboard.tsx):1–250, [LeaderboardDashboard.tsx](../../app/src/components/dashboard/leaderboard/LeaderboardDashboard.tsx):230–540.

## Actual data inventory

Counts are local artifacts at inspection, not promises of complete market coverage. Public snapshot checksums and exact representative values are in [data-evidence.json](data-evidence.json).

| Data                          | Verified local coverage / grain                                             | Source / use                                                                                                                   |
| ----------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| HDB resale bronze             | 989,703 rows; Jan 1990–Oct 2026; transaction                                | data.gov.sg/manual acquisition, then cleaning/geocoding                                                                        |
| Private/EC bronze             | 245,393 rows; Jan 2021–Oct 2026; transaction                                | manual URA extracts; different start date from HDB                                                                             |
| HDB rental bronze             | 212,597 rows; Jan 2021–Sep 2026; approved rental                            | Rental-yield construction, not a private-property rental source                                                                |
| Unified platinum              | 1,234,928 rows, 97 columns                                                  | `data/pipeline/04_platinum/unified_dataset.parquet`                                                                            |
| Planning-area monthly metrics | 13,201 area × month rows through Oct 2026                                   | `data/pipeline/04_platinum/metrics/pa_monthly_metrics.parquet`                                                                 |
| National overview             | 1,234,928 rows summarized; generated 2026-10-24T21:26:26; Jan 1990–Oct 2026 | [dashboard_overview](../../app/public/data/dashboard_overview.json.gz); era × property aggregate blocks                        |
| National trends               | 441 monthly rows, Jan 1990–Sep 2026                                         | [dashboard_trends](../../app/public/data/dashboard_trends.json.gz); median price and count per property; nulls before coverage |
| Area map metrics              | 19 sections; 41 areas in whole view; 31 in 2025 HDB                         | [map_metrics](../../app/public/data/map_metrics.json.gz); exact joint era/type subsets                                         |
| Leaderboard                   | 40 planning areas, mixed breakdowns                                         | [dashboard_leaderboard](../../app/public/data/dashboard_leaderboard.json.gz); not a reliable joint year/type source            |
| Segments                      | dashboard scatter + separate enhanced research extract                      | Observed and modeled yields must be distinguished                                                                              |
| Geography/amenities           | planning-area polygons, centroids, mean amenity distances                   | GeoJSON keys join uppercase planning-area names; preserve attribution                                                          |
| Research                      | spatial, feature-impact, predictive JSON; interactive tools                 | Analytics JSON generated 19 Feb 2026; predictive training date field is 1 Jan 2025; not refreshed by seven-file exporter       |
| Catalog                       | compressed JSONL plus generated reference assets                            | Independent generation; contains metadata, not necessarily public raw downloads                                                |

Sources and adapters live under [adapters](../../src/egg_n_bacon_housing/adapters) and [ingestion](../../src/egg_n_bacon_housing/components/ingestion). Manual files are R2-managed, ignored, and must not be embedded in the redesign.

Additional macro series exist (not new UI promises): CPI through Jul 2026, GDP through Q1 2026, unemployment through Q2 2026, SORA through Dec 2025, SORA 3M through Jun 2026, HDB/URA indices through Q2 2026, wage growth through Q4 2025. Each has its own cadence; do not combine these into one freshness badge.

## Schemas, entities, units and joins

- [clean_models.py](../../src/egg_n_bacon_housing/schemas/clean_models.py):10–53: 1990 transaction floor, HDB/private contracts.
- [feature_models.py](../../src/egg_n_bacon_housing/schemas/feature_models.py):68–79 and [platinum_models.py](../../src/egg_n_bacon_housing/schemas/platinum_models.py):13: required coordinates in the enriched/unified schema.
- Transaction is a sale observation, not a unique property or household. No verified durable cross-source property ID should be assumed.
- HDB town ≠ URA planning area ≠ CCR/RCR/OCR market segment. Do not rename one to another. Explorer uses planning areas and omits the current problematic region shortcut.
- Currency = SGD; nominal transaction price. HDB area starts in square metres, converts using `SQFT_PER_SQM = 10.7639` ([hdb_lookups.py](../../src/egg_n_bacon_housing/utils/hdb_lookups.py):13). PSF = price / square feet. Medians of price and PSF are independent, not a representative flat size.
- Distances = metres, haversine/proximity calculations; not walking travel times.
- Location dimension joins exact lat/lon; point-in-polygon produces planning areas. Coordinate array in leaderboard is longitude, latitude; Leaflet usually expects latitude, longitude.
- [feature_rental.py](../../src/egg_n_bacon_housing/components/feature_rental.py):80–133 groups sales/rents by town + normalized flat type + month, calculates annualized rent/sale ratios, weights by sale samples to town/month.
- [feature_transactions.py](../../src/egg_n_bacon_housing/components/feature_transactions.py):193,260 joins rental town/month and monthly/quarterly macro context.
- `pre_covid` actually means **year ≤2021**, `recent` **year ≥2022**, `year_2025` **year =2025** ([export_app_data.py](../../scripts/export_app_data.py):78–82). Designs replace misleading era labels with literal dates; do not silently alter the stored selection.

## Data quality and metric risks

### Independently checked by Sol

- 11,637 unified rows (0.94%) have missing coordinates and planning area. All-history national totals include rows that cannot appear in area comparisons. Revision 2 isolated 2025 HDB: zero missing areas, but national 25,084 versus area-map 25,082 because 2 Sungei Kadut records are excluded. Do not apply the all-history missingness rate to this year. This is a **local artifact/schema discrepancy**, not proof of the exact upstream failure mechanism.
- Only 152,951 rows (12.4%) have non-null rental yield; all are HDB. No observed private/EC yields are present in this platinum snapshot.
- 2025 national figures: HDB S$628,000 / 25,084 sales; EC S$1,578,000 / 6,209; condominium S$1,938,952 / 47,503. Sum = 78,796.
- Tampines HDB 2025: S$710,000, S$620/sq ft, 1,921 sales. Difference from national HDB = S$82,000 / 13.0573%, rounded 13.1%; **not a location premium or growth rate**.
- 2025 HDB area data: 31 areas; 25 have ≥150 included sales, 6 have fewer. The proposed sample gate uses the selected subset, unlike the current exporter's trailing-12-month ranking rule.
- Joint period/type values exist in map metrics, while [useLeaderboardData.ts](../../app/src/hooks/useLeaderboardData.ts):25–105 prefers property-only values over period-only values; other metrics fall back to top-level entries. Selecting both does not establish a joint sample.
- The same adapter maps region labels to CCR/RCR/OCR, but exported values include EAST REGION/NORTH REGION/WEST REGION etc. Partial region filtering can wrongly drop areas. Redesign omits regional filtering until a proper taxonomy is specified.
- [export_app_data.py](../../scripts/export_app_data.py):428,622–673 computes affordability from all-history prices/configured national income and enriches multiple filtered sections with shared yields/affordability. Do not interpret the enriched values as selected-year/type estimates.
- [export_app_data.py](../../scripts/export_app_data.py):693–704 supplies formula-based private/EC scatter yields when observed yields are unavailable. They must never be styled as measured income returns.
- [manifest.json](../../app/public/data/manifest.json) references `docs/analytics/README.md`, which is missing. Validation passes despite this unresolved provenance pointer.

### DeepSeek investigation; recheck before remediation

- Raw HDB contains 1,929 exact duplicate rows; identical transaction attributes are not sufficient evidence that sales should be deleted. Define natural-key semantics first.
- Geocoded coverage ≈99.04%; gold/platinum quarantine counts vary by run. Do not present one run's row loss as a stable validation rate.
- `appreciation_hotspots` sorts all months then takes 20, not the latest-month top 20 ([metrics.py](../../src/egg_n_bacon_housing/components/metrics.py):233).
- Exported hotspot `years` counts monthly observations ([export_app_data.py](../../scripts/export_app_data.py):480–514).
- Mixed-property area growth can reflect composition changes; the backend investigator traced Tampines' +71.71% ranking value to changing transaction mix. Do not promote it as HDB appreciation. Primary designs deliberately avoid growth claims.
- Research docs contain retired paths and counts. Reproducibility of research figures is not established by an article rendering successfully.

## What works vs what is not established

**Runtime verified:** local Astro server returned HTTP 200 for /, /dashboard, /dashboard/leaderboard, /dashboard/map, /analytics/lease-decay and /catalog. Chromium loaded them without captured page exceptions; the 390px leaderboard document had no horizontal overflow. Visually inspected the existing full desktop leaderboard. Its external basemap displayed “API KEY REQUIRED”; no provider keys were inspected. This is not a full end-to-end interaction audit.

**Existing capability, code inspected:** filter/search/sort, map selection, segment investigation, article table/chart opt-in, catalog schemas/DAG, cached gzip fetching.

**Not established:** correctness of every filter combination; research model accuracy; live source availability; complete-market capture; full test/build health; property-level valuations; live listings; current private rental yields; complete source freshness; full keyboard/screen-reader access.

## Reusable vs problematic

Retain Astro static publishing, BASE_URL handling, article collection/math/table chart opt-ins, catalog slug handling, endpoint registry, loader lifecycle, Leaflet polygons and Recharts primitives. Reuse matching logic only after data semantics review.

Replace the sidebar-heavy IA, marketing/dashboard split, sprawling map-first comparison, unlabeled model fallbacks, misleading period labels, mixed-grain rankings and fragmented metric help.

Accessibility gaps from frontend inspection:

- Sidebar mobile script lacks evident focus trap/restore/Escape and active links lack consistent aria-current ([Sidebar.astro](../../app/src/components/Sidebar.astro):108–118,275–300).
- Clickable table rows and metric-help dialogs need keyboard/focus checks.
- Charts/maps lack a uniform text/table alternative.
- [cross-page.spec.ts](../../app/tests/e2e/cross-page.spec.ts):116–148 asserts headings/titles/link text, not comprehensive accessibility.

## Tests and unknowns

[Playwright configuration](../../app/playwright.config.ts):1–35 and [E2E directory](../../app/tests/e2e) cover route/navigation/filter smoke behavior. [test_export_app_data.py](../../tests/test_export_app_data.py) tests completed months, year pairs, exclusions and ranking gates with synthetic frames. Existing manifest validation is shape-level, not proof of temporal/metric correctness.

Unknowns for planning: agreed primary audience, source refresh SLA, newest fully covered year per type, cross-asset generation consistency, treatment of duplicate observations, research generator ownership, tiles/licensing/provider configuration, and desired long-term URL compatibility.

## Revision 2: deeper feature audit

See [audit-review.md](audit-review.md) for runtime-confirmed Spatial Hotspots failure, overlay geometry-key mismatch, incomplete research/model contracts, median-definition corrections, exact 2025 cohort reconciliation and catalog-generation discrepancy. `bun run astro check` baseline: 109 errors, 0 warnings, 45 hints across 112 files; no application code was changed.
