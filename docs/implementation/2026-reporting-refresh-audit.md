# Web app reporting audit and 2026 refresh proposal

Audit date: **2026-11-12**. Status: **recommendations, not an implemented refresh**.

## Executive decision

Refresh the observed dashboard first, but fix metric scope before promoting newer numbers. Keep historical research as dated editions; do not bulk-replace `2025` with `2026`.

- The published dashboard already contains monthly data through **October 2026**. The release was exported on **2026-11-03**; 2025 is its last completed calendar year.
- The interface largely defaults to, or only offers, an explicit **2025** year slice. This is partly a presentation/period-contract limitation, not simply missing 2026 observations.
- Research articles, models, interactive extracts, static figures and catalog snapshots have **separate vintages**. The dashboard exporter does not refresh them.
- Add **2026 YTD through October**, **latest completed month**, and **trailing 12 completed months**. Keep **2025 full year**. Never label January–October 2026 a complete year, or compare its volume directly with all twelve months of 2025.
- For area “hotness,” start with transparent **observed transaction activity**, not a BUY score, portal popularity, or rental hotspot label.

## 1. Scout: current web app structure

| Surface | Role and evidence boundary | Recommendation |
| --- | --- | --- |
| `/` | Landing page; reads overview/trends, but hardcodes 2024/2025 comparisons and research teasers | Replace stale promotional claims with scoped latest-observed highlights and a visible cutoff |
| `/dashboard` | Overview cards, period/type controls, distributions and monthly charts | Make the latest completed observation prominent; retain the full-year comparison |
| `/research/trends` | Monthly price and volume charts/table; defaults to 2025 even though data extends to 2026-10 | Default to latest 12 completed months; add YTD and same-month prior-year comparisons |
| `/explore` | Joint period × property-type area comparison, list/map/table; minimum-sale caution threshold; verified national comparison | Reuse this joint-section contract for all current area metrics |
| `/areas/[slug]` | 41 static area fieldnotes; build-time generation verification | Add current activity, trend and report links with the same selected scope |
| `/dashboard/leaderboard` | Area rankings and geographic view; independent property/time breakdowns | Repair incorrect joint filtering and regional taxonomy before extending it |
| `/research/map` | Observed fill plus nine archived model layers; models do not paint analytical polygon fills | Keep archive inspection separate from a new current-activity map |
| `/research/segments` | Six stored research segments; investigation/comparison; separate archive evidence contract | Preserve current archive; only publish refreshed segmentation after revalidation |
| `/research/tools` | Illustrative financing, archived lease bands, MRT/CBD inspection and spatial labels | Keep financial/model gates; separately update the observed reference period when supported |
| `/analytics` and `/analytics/[slug]` | Searchable library and 15 published markdown studies, opt-in table charts | Add edition, observation cutoff, validation status and current/archive filters |
| `/analytics/personas/[persona]` | Three persona landing pages backed by `persona-content.json` | Remove unsupported gain/timing promises and inherit report freshness/status |
| `/catalog`, layer and dataset pages | Separate generated catalog snapshot, not live source availability | Regenerate with a new audit observation; keep both historical counts until reconciled |

Compatibility routes remain important: `/dashboard/map`, `/dashboard/segments` and `/dashboard/trends` wrap research surfaces. **`/dashboard/trends` is Decision Tools**, not monthly trends. Keep existing links working; make canonical destinations clear.

Key seams:

- Export ownership and periods: `scripts/export_app_data.py:99-104`, `:1624-1759`; `app/public/data/README.md:9-87`.
- Overview year controls/cards: `app/src/components/dashboard/MarketOverviewDashboard.tsx:63-100`.
- Shared observed period contract: `app/src/utils/observed-data.ts`; explorer defaults: `app/src/utils/explorer-selection.ts`.
- Trend windows: `app/src/utils/trend-series.ts`; area periods: `app/src/utils/area-page.ts`.
- Tools' observed reference: `app/src/components/tools/lib/tool-reference.ts:24`.
- Research loader: `app/src/content.config.ts:5-28`; archive/model invariants: `docs/implementation/README.md`.

## 2. What the published data actually supports

### Dashboard release

Read-only decompression of checked-in assets found:

- Release generation: `0e1013ee485f…`; seven hashed dashboard assets.
- Manifest completed-month boundary: **2026-10**, explicitly declared; completed year: **2025**.
- Trends: **442 monthly rows, 1990-01 through 2026-10**. Property-type coverage is not necessarily identical across that whole history.
- Overview: **1,234,854 records**, transaction-date range **1990-01-01 to 2026-11-01**. Full-history aggregates intentionally include a partial trailing month; the monthly charts exclude it. These are different scopes, not evidence of a complete November.
- Latest published month, October 2026: HDB median **S$650,000 / 2,176 sales**; EC **S$1,618,000 / 116 sales**; condominium **S$2,190,000 / 1,303 sales**.

Monthly count sums, not independently verified national market totals:

| Property type | Jan–Oct 2025 | Jan–Oct 2026 | Published count change |
| --- | ---: | ---: | ---: |
| HDB | 21,402 | 21,808 | +1.90% |
| EC | 5,560 | 2,313 | −58.40% |
| Condominium | 42,414 | 17,363 | −59.06% |

The large private/EC differences are a **source coverage/grain reconciliation priority**, not an established market-collapse finding. Check source completeness by property type, overlap/deduplication, sales categories and unit-versus-record grain before promoting those changes into headlines. No specific cause was established in this audit.

A YTD sales count can be summed from monthly counts. A **YTD transaction median cannot be reconstructed by averaging monthly medians**; it requires transaction-level aggregation or an explicitly published YTD statistic.

### Refresh ownership and blockers

The supported dashboard exporter owns only:

`dashboard_overview`, `dashboard_trends`, `dashboard_segments`, `dashboard_leaderboard`, `map_metrics`, `hotspots`, `amenity_summary` (all `.json.gz`), plus its release manifest.

It does **not** refresh `analytics/*`, `interactive_tools/*`, `segments_enhanced`, PNG figures, planning-area references or the catalog.

Locally absent: `data/pipeline/04_platinum/` and the exporter's manual source GeoJSON directory `data/manual/geojsons/`. Published `app/public/data/planning_areas.geojson` and its gzip copy **do exist**; that is not the same as having the pipeline/export source inputs. Therefore upstream completeness, duplication and a new end-to-end release could not be verified here. Source fetches, R2 synchronization, pipeline runs and model retraining were not performed.

## 3. Correctness findings to address before refresh

### P1 — Compare Areas does not honor the claimed joint scope

**Reproduction:** `/dashboard/leaderboard?propertyType=hdb&timeBasis=year_2025&metric=median_price`.

- UI says “using 2025 data”; Punggol displays **S$500,000**, volume **24,854**.
- Those are the property-only, all-history HDB values in the leaderboard payload.
- The verified joint section `map_metrics.year_2025_hdb.PUNGGOL` instead publishes **S$672,000**, volume **1,538**.
- `resolveMetricValue` prefers property-only price over the selected period; volume ignores period. Other fields remain top-level mixed scopes. See `app/src/hooks/useLeaderboardData.ts:45-129` and `scripts/export_app_data.py:1223-1319`.

**Fix direction:** derive every displayed/ranked field from an explicit joint property × period section. Withhold unavailable metrics rather than falling back to another population. Reuse the explorer's generation verification and missing-data semantics.

The same hook re-sorts all filtered rows (`:178-192`), bypassing the exporter's thin-sample-last ordering. Publish scoped sample eligibility and enforce it during UI sorting, not only during export.

### P1 — Region filtering conflates different geographic taxonomies

`app/src/hooks/useLeaderboardData.ts:12-23` maps `CENTRAL REGION` to CCR and recognizes only `REST OF CENTRAL REGION` / `OUTSIDE CENTRAL REGION` for RCR/OCR. Published rows instead include `EAST REGION`, `NORTH REGION`, `NORTH-EAST REGION`, `WEST REGION` and `CENTRAL REGION`.

All-three-selected bypasses this mismatch; individual selections can exclude valid areas. Planning regions are not the CCR/RCR/OCR market-segment taxonomy. Use a verified crosswalk or expose the actual planning regions.

### P1 — Research promotion is stronger than its evidence contract

- Investor persona recommends “6-month price forecasts with up to 79% expected gains” (`app/src/data/persona-content.json:43-50`). The predictive asset says training date **2025-01-01**, with forecast targets **2025-07-01**. These are historical outputs, not current expected gains. The asset and article may represent different research products; their lineage must be reconciled, not assumed identical.
- Forecast article labels R² as “Accuracy” and recommends timing decisions (`docs/analytics/price-forecasts.md:37-45,68-79`). R² is not the probability of a correct forecast. Require temporal holdouts, naïve baselines, error metrics and calibrated interval coverage before current-use promotion.
- Macro article acknowledges generated-data fallback without identifying which published estimates used real observations (`docs/analytics/macro-sensitivity.md:152`). Identify/exclude synthetic inputs before presenting empirical findings as current evidence.
- Lease article's PSF labels conflict with its stated `price_per_sqm` method (`docs/analytics/lease-decay.md:39-62,117-132`). The app already flags unit review and withholds its chart; keep that gate until the underlying estimates are checked.
- Rental article's median-rent/median-sale-price proxy is not a matched-unit net yield and does not establish a downside floor or investment viability (`docs/analytics/rental-yields.md:111-120,136,154`). Label gross proxy, geography/date matching and excluded costs prominently.
- Homepage promotes a lease “myth busted” and CBD/MRT multiplier without current validated provenance (`app/src/pages/index.astro:57-69`), and calls a static snapshot “Live Dashboard” (`:184`). Align landing/persona copy with the more cautious tools/map surfaces.

Existing archive gates are useful, but **do not automatically gate markdown or persona recommendations**. Do not remove those gates as part of a date refresh.

### P2 — Opt-in study charts can render misleadingly empty

On `/analytics/price-forecasts`, the comparison chart rendered its axes/legend but **zero bar rectangles**, despite numeric R²/directional-accuracy table entries. `ComparisonChart.tsx:52-70` sets a horizontal Recharts layout while assigning a numeric X and categorical Y; those axes require the corresponding vertical layout convention.

The table parser also returns `null` for every `±…%` interval cell (`app/src/utils/data-parser.ts:143-191`), while the chart still includes that series. A read-only Bun invocation confirmed all five interval values become null.

**Fix direction:** test rendered marks and table/chart parity; use explicit chart unit/series contracts, omit all-missing series with an explanation, and chart uncertainty as intervals rather than ordinary comparable bars. Audit every opted-in chart, not just whether a chart container exists.

### P2 — Existing hotspot labels are not current area hotness

`build_hotspots` summarizes historical monthly YoY changes, not recent demand (`scripts/export_app_data.py:925-976`). In the published payload, **33 of 40 areas are High Growth**, seven Moderate Growth. Its `years` field is actually a count of monthly YoY observations, reaching **430**.

Leaderboard fields also mix windows: headline price/volume aggregate 2022 onward, annual YoY uses the latest completed-year pair, and MoM/momentum use completed monthly buckets. Label or redesign these before combining them into any score. Growth calculation uses row offsets (`pct_change(12)`, `:820-840`); verify dense calendar-month indexing before interpreting that as twelve calendar months for sparse areas.

### P2 — Freshness and price-change labels need precision

Homepage “2025 growth” is change between unweighted averages of monthly HDB medians (`app/src/pages/index.astro:34-55,124`). It is neither annual transaction-median growth nor an adjusted price index. Name the statistic exactly or replace it with an approved metric. Do not average area medians into a national value.

Expose **source data through**, **completed month through**, **exported at**, and, where relevant, **trained through** separately. `sourcePublishedAt` is null for both source identities in the dashboard release, so export time alone cannot establish upstream freshness.

## 4. Inventory of all 15 studies and three persona pages

Dates below are **claims in the documents**, not independently validated transaction coverage. Most research generation scripts are explicitly retired from the supported repository surface.

| Study (`docs/analytics/`) | Declared observation window / vintage | Recommended treatment |
| --- | --- | --- |
| `findings.md` | 2017–2026; body updated March 2026, frontmatter February | Rebuild last, after dependencies; distinguish editorial from data dates |
| `data-sources.md` | Inventory June 2026; HDB to June, rentals to May, some macro to Q1; SORA to 2025 | Reconcile actual source cutoffs and publish a coverage matrix |
| `amenity-impact.md` | 2015–2026; March 2026 analysis | Keep historical edition; rerun associations/models for a new edition |
| `causal-inference-overview.md` | 2017–2026; February 2026 | New edition only after treatment/control and causal-design validation |
| `facility-premiums.md` | 2017–2026; March 2026, cross-sectional facilities | Verify facility snapshot and refit; do not assume 2026 freshness |
| `lease-decay.md` | 2017–2026; February 2026 | Unit repair first, then refit; preserve review warning |
| `macro-sensitivity.md` | Housing 2017–2026; macro 2021–2026; March analysis | Real/synthetic lineage audit and lag-aware rerun |
| `market-segments.md` | 2017–2026, emphasis 2021 onward; March analysis | Recluster/revalidate; retain mapping to old segment identities |
| `mrt-impact.md` | 2021–2026; February 2026 | Refit with station-status/date and distance/unit checks |
| `price-forecasts.md` | 2021–2026; February 2026 | Archive historical outputs; reconcile assets, retrain and backtest |
| `rental-yields.md` | 2017–2026; March 2026 | Refresh aligned rental/sale inputs; distinguish proxy gross from net yield |
| `school-quality.md` | 2021 onward; February 2026 | Revalidate sample, school data and RDD/causal caveats |
| `spatial-autocorrelation.md` | 2021–2026; February 2026 | Rerun spatial analysis; record boundaries, weights and significance policy |
| `spatial-hotspots.md` | **January 2024–January 2025**, analysis February 2026 | Archive as historical rental study; generate a separate current edition |
| `temporal-evolution.md` | 2017–2026; March 2026 | Recompute comparable period estimates and figures |

Persona pages: **first-time buyer, investor, upgrader**, all from `app/src/data/persona-content.json`. They are recommendation/navigation surfaces, not independent analytical results. Update them after correcting report status; avoid current-opportunity/gain claims from archived studies.

Other published evidence families:

- `analytics/{predictive_analytics,feature_impact,spatial_analysis}.json.gz`: February 2026 extraction timestamps; predictive training/targets remain in 2025. No common verified dashboard generation.
- `segments_enhanced.json.gz`: April 2026 update label; separate archived research, not a freshly recomputed dashboard segment model.
- `interactive_tools/*`: observation periods/source freshness incomplete. Keep stored-band/model-inspection contracts; the unused affordability extract should be deliberately retired or justified, not silently promoted.
- `analysis/**/*.png`: static figures without machine-readable observation cutoffs. Inventory and regenerate/version with each report; do not infer freshness from a filename.
- `catalog.jsonl.gz`: September 2026 snapshot; UI already discloses the historical audited/published unified-dataset count discrepancy. Update catalog and audit evidence together, not just the displayed constant.
- `planning_areas*`: reference geometry with a separate vintage. A current transaction release does not imply current boundary/amenity reference data.

## 5. Proposed current-data experience

### Shared period controls

One central period descriptor should drive exporter sections, manifest, types, URL parsing, labels and tests:

- Latest completed month: **October 2026**.
- Current year to completed month: **January–October 2026 (YTD)**.
- Same months previous year: **January–October 2025**.
- Trailing 12 completed months: **November 2025–October 2026**.
- Completed calendar years: **2025**, then earlier published years.

Keep old `year_2025` URLs and assets compatible. Add new periods rather than changing their meaning. Derive labels/defaults from the release metadata; the UI must not invent a new period merely because the wall clock rolls over. Add full-year 2026 only after verified December coverage is released.

### Dashboard hierarchy

1. **Freshness strip:** completed-month cutoff, source-specific coverage and quality alerts.
2. **Property-specific snapshot:** transaction median, median PSF, sales count; explicit selected window and comparator.
3. **Volume/activity panel:** latest month and rolling quarter, same months last year, count denominator, missing-month disclosure.
4. **Area activity map + accessible ranking table:** click through to the area fieldnote with property/window preserved.
5. **Research:** clearly dated current/archived/under-review studies, not mixed into current market KPIs.

Avoid defaulting market intelligence to all-history medians or all-history top-volume areas. Those remain useful as historical views, not today's area activity.

## 6. Area hotness and portal structure

### External observation, not inferred access

Attempted public browser visits:

- `https://www.propertyguru.com.sg/area-insights` — **403 challenge**.
- `https://www.99.co/singapore/neighbourhoods` — **403 challenge**.
- `https://www.edgeprop.sg/analytic/heatmap` — accessible. Observed property-type selector, separate **Price (S$ psf) / Price (S$) / Volume** modes, visible **November 2023–October 2026** window, legend and a prompt to click hotspots for transaction breakdowns. Exercised property type and Volume controls; did not verify every hotspot drill-down.

Do not claim to have audited PropertyGuru/99.co internals or current page structure beyond these blocked requests. Do not bypass challenges. A later comparison can use permitted access or user-provided screenshots. Portal content is inspiration, not a licensed data source.

Useful structure to adopt: **discover area → choose property/time → inspect map/list → area profile → comparable observations → methodology**. Existing explorer, fieldnotes and trends already supply much of this; extend them rather than adding another disconnected dashboard.

### MVP: “Area activity,” not an opaque hotness score

Show separately, for each area and property type:

- Completed rolling-quarter sale count and same-quarter-prior-year volume change.
- Trailing-12-month count, with small-sample and source-coverage status.
- Observed median PSF change with mix/lease/size caveats; no adjusted-index claim.
- A short sparkline and precise start/end months, plus accessible table/download.

A new **area × property type × calendar month** publication is needed for consistent scoped trends; current national monthly series and static area slices are not enough. Export under the supported data boundary, with a versioned manifest/schema and parity tests.

Prefer separate labels such as **More transactions**, **Higher observed PSF**, **Mixed signals**, **Insufficient evidence**. Choose thresholds after inspecting distributions/backtesting; 150 sales is an existing caution rule, not a universal significance/confidence guarantee. Missing months are not zero sales. Suppress percentage changes on zero/insufficient denominators.

Do not equate raw volume with liquidity: big areas naturally transact more. Normalize by comparable housing stock only after obtaining current stock and a defensible geography/property-type crosswalk. Separate HDB, EC, condo and, where supported, primary/resale activity to reduce launch/mix effects.

**Not available from these assets:** listing stock, unique listing views, enquiries, days on market, absorption or listing-to-sale conversion. Those require authorized feeds/partnerships and appropriate deduplication/licensing. Until then call the feature an observed transaction-activity indicator, not buyer demand or portal popularity. Statistical rental hotspots/LISA and historical appreciation classes remain separate concepts.

## 7. Archive/year-series design

Use two independent axes: **publication edition** and **observation window**. A report published in February 2026 using 2025 data is not automatically a “2025 report,” nor a current full-year 2026 analysis.

Proposed report metadata: `seriesId`, `editionId`, `publishedAt`, `revisedAt`, `observedFrom`, `observedThrough`, `completeThrough`, per-source cutoffs, `releaseGeneration`, `methodVersion`, units, quality/review status and, for models, `trainedThrough` and forecast target interval.

- Preserve each historical markdown body, figure set and data snapshot immutably; corrections get a visible revision/erratum.
- Keep `/analytics/<slug>` as a stable series/current-approved-edition entry, with explicit links to edition URLs such as `/analytics/archive/2026/<edition>/<slug>`.
- Show “2025 full year” and “2026 YTD through October” as data windows, not interchangeable edition names.
- Give each edition a source/model manifest. A “latest” page must not silently resolve an unvalidated forecast or a cross-generation mixture.
- Current content loader uses only `docs/analytics/*.md` (`app/src/content.config.ts:6`); moving files into year folders alone will **not** publish archives. Implement collection/routing changes and link migrations explicitly.
- Keep old query IDs and compatibility routes. Forecast archives should compare expired predictions with realized outcomes when lineage allows, rather than shifting forecast dates forward.

## 8. Recommended implementation order and acceptance gates

| Priority | Slice | Exit condition |
| --- | --- | --- |
| 1 | Correctness and trust | Leaderboard matches joint explorer values; region filters use a valid taxonomy; missing values stay unavailable; unsafe persona/homepage promotion removed; chart marks match tables |
| 2 | Source reconciliation and period contract | Restore inputs via documented acquisition; validate cutoff/coverage/deduplication by property type; publish YTD/rolling periods reproducibly without altering 2025 semantics |
| 3 | Current observed dashboard | Dashboard/trends/explorer/area pages agree on property, window, sample and generation; matched YTD/rolling comparisons; no annualized partial-year headlines |
| 4 | Research editions | Metadata/archive routes shipped; historical assets preserved; rental/temporal descriptive reports refreshed before summaries; model/causal reports separately validated |
| 5 | Area activity MVP | Area-type-month contract, sample/coverage gates, map/table parity, transparent labels; no unsupported demand or investment claims |

Research regeneration must remain behind explicit methodological approval where existing decision registers require it (lease/MRT models, segment scoring and recommendation promotion). This audit is not authorization to replace archived model outputs.

Verification for implementation: exporter unit tests and Ruff; frontend unit tests and `astro check`; data-manifest validation; route/base-path and keyboard E2E checks. Add focused tests for:

- Punggol HDB/2025 and every supported joint metric; no independent-margin fallback.
- Region selections, thin-sample sorting, null/empty metrics and rank-direction semantics.
- December/January rollover, explicit cutoff, incomplete source months, dense monthly gaps and absent previous-year periods.
- Count sums versus transaction-level medians; no median-of-medians; source-specific coverage and duplicate keys.
- Actual chart marks, uncertainty handling and table parity, not just mount presence.
- Year-edition URLs, canonical/legacy links, previous report assets and hashes.
- Archive/forecast expiry gates and model status propagation into persona/landing pages.

## 9. Audit verification and limits

- Read-only route/source inspection and gzip JSON summaries; source parquets unavailable, so no upstream/model recomputation was verified.
- `bun install --frozen-lockfile` on pinned Bun 1.2.23: no dependency/lock changes.
- Existing frontend baseline: **334 unit tests passed**, zero failed; `astro check`: **0 errors / 0 warnings / 22 hints** on 191 files. These tests do not cover all analytical defects identified above.
- Repository Ruff, documentation-layout validation and `git diff --check`: passed.
- `bun run validate-data`: **19 assets validated**, dashboard release **0e1013ee485f** verified across **seven** assets. This verifies publication consistency, not source truth or analytical correctness.
- Browser checks on current local dev app: dashboard period control, trends switching from 2025 to the window ending October 2026, explorer map tab, studies search/article, and leaderboard HDB/2025 reproduction. No browser console errors on those current-dev observations; dashboard initially emitted four chart sizing warnings. Leaderboard geometry/data requests returned 200. Not an exhaustive visual/E2E sweep of all generated routes or a deployed-production audit.
- A pre-existing prefix preview had root-asset 404s from a build/base mismatch; it was discarded as acceptance evidence. Current-dev observations above were taken on a separate correctly served instance.
- EdgeProp interaction worked with advertising/analytics resource failures and some console errors; it was not a clean end-to-end portal validation. PropertyGuru/99.co remained blocked.
- Browser snapshots/logs are outside the repository under `~/.cache/pi/playwright/pi-01a1d014-f164-76db-890f-474cb4b82c1c/`; no private browser profile or saved credentials used. The audit browser and temporary dev listener were closed.
- No production code, published data, report contents or model outputs were modified by this audit. This document is the deliverable.
