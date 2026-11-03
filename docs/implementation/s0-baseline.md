# S0 baseline report

Captured on branch `design/sol-editorial-spec`, commit `a881ec0fa3f018db220b791d59e76a8edaa526e2`. Working tree contained only untracked `assets/` (design deliverables). **No production file was modified for this report.** Values below were read from the checkout or reproduced in a local browser on the same commit.

## 1. Publication inputs

SHA-256 (first 16 hex characters) of the assets this slice touches:

| Asset | Hash prefix |
|---|---|
| `dashboard_overview.json.gz` | `b49a518d260d2db6` |
| `dashboard_leaderboard.json.gz` | `937a7db9e5216467` |
| `dashboard_trends.json.gz` | `2857e6247c449bab` |
| `dashboard_segments.json.gz` | `e19390376e5f14d1` |
| `map_metrics.json.gz` | `0a2b8a0de2274a9c` |
| `segments_enhanced.json.gz` | `76979cc5fdc4e7ff` |
| `interactive_tools/spatial_hotspots.json.gz` | `12ff7464b188e8bd` |
| `analytics/spatial_analysis.json.gz` | `e3ff620242187ba9` |
| `planning_areas.geojson` | `f23856251b467089` |

There is still **no manifest field that proves these nine files came from one exporter run**, so cross-file numeric comparison remains unproven in production. `manifest.json` does not contain per-asset hashes or a generation identity.

## 2. Type-check baseline (pre-existing)

`cd app && bun run astro check` → **109 errors, 0 warnings, 45 hints, 112 files** (exit 1). This is the recorded baseline, not a pass. Recurrent causes: implicit `any` in `.astro` script blocks (`src/pages/dashboard/leaderboard.astro:9`, `src/pages/dashboard/trends.astro:10`), Leaflet `PathOptions`/`StyleFunction` mismatches (`PriceMap.tsx:637,669`, `map/overlays/*`), and persona badge indexing (`PersonaHeader.tsx:35,50`).

Baseline error count must not increase. Touched files must reach zero new errors.

## 3. Route and query inventory

| Route | Component | Query/state read today |
|---|---|---|
| `/` | `pages/index.astro` | none |
| `/dashboard` | `dashboard/index.astro` | `?persona=` via persona header |
| `/dashboard/leaderboard` | `dashboard/leaderboard.astro` → `LeaderboardDashboard` | `propertyType`, `timeBasis`, `sort`, `search`, `area`, `minSales` |
| `/dashboard/map` | `dashboard/map.astro` → `PriceMap` | `metric`, `timeBasis`, `propertyType`, `area`, `layers` |
| `/dashboard/segments` | segment workspace | `persona`, `tab`, `segment`, `segments`, `area` |
| `/dashboard/trends` | `InteractiveToolsPanel` | `tool` (implied by tab state) |
| `/analytics`, `/analytics/[slug]`, `/analytics/personas/[persona]` | research pages | `persona` |
| `/catalog`, `/catalog/[layer]`, `/catalog/[layer]/[...dataset]` | catalog | path segments only |

`DASHBOARD_NAV_ITEMS` (`src/constants/dashboard-nav.ts`) defines five destinations; all exist. The label "Decision Tools" maps to path `dashboard/trends`, so route name and destination do not agree with user expectations.

## 4. Reproduced defects

### 4.1 Legacy map selection is overwritten before it is read (confirmed)

`PriceMap.tsx` declares the URL-sync effect (metrics/timeBasis/propertyType/layers/area → `replaceState`) at ~line 158 and the query-parsing effect at ~line 203. React runs effects in declaration order, so the first commit rewrites the URL with default state and the parser then reads the rewritten URL.

Reproduced in Chromium against the dev server: requesting

```
/dashboard/map?metric=median_psf&timeBasis=year_2025&propertyType=hdb&area=TAMPINES&layers=spatial.lisa
```

ended with `metric=median_price&timeBasis=whole&propertyType=all` and no `area`/`layers`. Four of five parameter groups are lost on first load; `layers` is absent from the parser entirely.

Root causes: state initialised to defaults instead of from `window.location.search`; parse effect gated by `[]` but ordered after the writer; `layers` never parsed.

### 4.2 Spatial Hotspots tab crashes (confirmed)

`SpatialHotspotExplorer` reads `data.clusters.flatMap(...)` and `c.towns`, but the served `interactive_tools/spatial_hotspots.json.gz` has top-level keys `towns` (array of 40 records), `town_clusters` (object keyed by planning area), `cluster_descriptions`, `portfolio_allocation`. There is no `clusters`.

Rendered result: `TypeError: Cannot read properties of undefined (reading 'flatMap')`, which unmounts the whole tools workspace instead of one tab.

### 4.3 Overlay geometry keys do not match the served GeoJSON (confirmed, silent)

`planning_areas.geojson` features carry uppercase `PLN_AREA_N` (and the exporter also writes `pln_area_n` into some properties). `PriceMap.tsx:342` tolerates both. `map/overlays/PredictiveAnalyticsOverlay.tsx` and `map/overlays/SpatialAnalysisOverlay.tsx` read only `feature.properties?.pln_area_n` (9 occurrences). When absent, the result is a silent unstyled/blank layer, not an error — the failure is invisible to a user but the layer is wrong.

### 4.4 Leaderboard mixes property-only and period-only metric blocks (confirmed)

`useLeaderboardData.ts` resolves `median_price` from the property block first, then the period block, then the top-level value; `volume` from the property block then top-level; `yoy_growth_pct` from the period block then top-level. `map_metrics[period][property]` joint sections exist but are not used here. A request for "pre-2021 condos" therefore returns a property-only median with a period-only growth, i.e. two different populations on one row.

### 4.5 `useGzipJson` lifecycle defects (confirmed by inspection)

- Cache is consulted on every call, including manual retry, so `reload()` can return stale data without any request.
- A foreground `reload()` failure clears previously displayed data (`if (!background || !hasExistingData) setData(null)`), so a transient network error blanks a working dashboard.
- `finally { setLoading(false) }` runs for aborted requests, so a superseded request clears the newest request's loading state.
- The cache key is the URL only; there is no generation/hash dimension, so a replaced asset can be served from a 5-minute stale copy.

### 4.6 Data-shape discrepancies already known

- `map_metrics` 2025 HDB area counts sum to 25,082; the national overview reports 25,084. The 2-row difference is Sungei Kadut, excluded by residential-area policy. This is a documented inclusion rule, not a rounding error.
- Catalog row count (1,233,405) belongs to a different snapshot than the current platinum (1,234,928); catalog metadata must keep its own vintage label.
- Research assets (`segments_enhanced`, `analytics/*`) have no reproducibility metadata proving generator, units or validity.

## 5. Existing runtime status

Local dev server returned HTTP 200 for `/`, `/dashboard`, `/dashboard/leaderboard`, `/dashboard/map`, `/analytics/lease-decay`, `/catalog`. At 390 px width the document `scrollWidth` was 390 (no horizontal overflow). `cd app && bun run validate-data` passed ("Validated 19 app data assets"), which is a shape/required-key gate only.

## 6. S1 entry decisions

1. **Test runner:** use Bun's built-in `bun test` (Bun 1.2.23 is the pinned engine) with specs under `app/tests/unit/`. This adds no dependency and does not collide with Playwright (`testDir: ./tests/e2e`, `*.spec.ts`). Add a `test:unit` script as a coordinator-owned change.
2. **Ownership:** four disjoint worker slices — observed-data adapter, fetch lifecycle, map URL state, overlay/tool containment. Coordinator owns `package.json`, `types/*`, `constants/data-urls.ts`, integration, runtime verification and docs.
3. **No behavior promises:** S1 makes known values render with their true scope and makes failures visible. It does not regenerate models, add publication metadata (S2), or restyle pages (S3+).
