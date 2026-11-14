# RF05 report — current periods in the app (slice 1)

- **Date:** 2026-11-13
- **Status:** **Complete for RF05 code.** The v2 pack is published; the dashboard overview, `/research/trends`, `/explore` and `/dashboard/leaderboard` (Compare Areas) render verified current windows. The explorer's list/map/table and the Compare Areas rankings read the pack for a concrete published period while the legacy eras stay selectable as a labelled historical group, and limited-display scopes are shown unranked. D03's bare-URL defaults plus the migration notice are implemented behind `PUBLIC_OBSERVED_RELEASE` (§9). The only remaining action is the release switch itself, which the contract ties to RF06 (fieldnotes and tools still read v1 periods).
- **Parent:** [implementation map](../plans/2026-11-12-reporting-refresh-implementation-map.md) §6 · [handoff](../plans/2026-11-12-reporting-refresh-handoffs.md) RF05
- **Decisions:** D01 (v2 sidecar), D02 (cutoff 2026-10), D03 (YTD/TTM defaults), D11 (coverage disposition)
- **Upstream:** [RF04 v2 pack](2026-11-13-rf04-v2-period-pack.md) · [RF03 sources](2026-11-13-rf03-source-reconciliation.md)

## 1. Publication

The v2 pack now lives beside the untouched v1 release:

```bash
uv run python scripts/v2_observed.py --last-complete-month 2026-10 \
  --output-dir app/public/data --scope-status hdb=publish \
  --scope-status ec=limited-display --scope-status condo=limited-display
```

- generation `6cd4510f26eca3fd…`, cutoff `2026-10`, 8 periods, 1,472 observations, 60 KB
- `app/public/data/dashboard-release-v2.json` + `app/public/data/observed/<generation>/{periods,summary}.json.gz`
- v1 assets untouched; `verify_reporting_baseline.py --assets` still passes for all 72 pinned files
- `bun run validate-data` now verifies both releases:

```text
Verified dashboard release 0e1013ee485f (7 assets)
Verified v2 observed pack 6cd4510f26ec (cutoff 2026-10, 8 periods, 1472 observations)
```

`PUBLIC_OBSERVED_RELEASE` still defaults to `legacy`; the dashboard strip reads the pack directly rather than switching the whole app.

## 2. Build-time reader

`app/src/utils/observed-pack-build.ts` — verifies the pack from disk with the same manifest parser, generation hash and period parser the browser uses, then extracts only what the page needs:

| Export | Behaviour |
| --- | --- |
| `loadObservedPackFromDir(dir)` | Reads `dashboard-release-v2.json`, checks generation, per-payload size + sha256, gunzips **those** bytes, parses. Returns `ready` / `absent` / `invalid` |
| `summariseForDashboard(pack, generation, type)` | YTD + latest-month windows with per-metric value, prior-year comparator, change and skip reason |

7 tests cover verification, absent, tampered payload, edited generation, and the HDB/condo summaries.

## 3. Dashboard strip

`app/src/pages/dashboard/index.astro` loads the pack at build time and passes a compact summary; `MarketOverviewDashboard` renders a "Current data" section:

> **Current data** · cutoff 2026-10 · generation `6cd4510f26ec`
> HDB sales, 2026 January to 2026-10 (partial year): **21,801 sales**, +1.9% vs prior year
> HDB median price, year to date: **S$633,999**, +1.0% vs prior year
> HDB sales, 2026-10 (one month): **2,173 sales**, +62.4% vs prior year
> *Condominium and EC 2026 counts are still under coverage review…*

The strip is absent when the pack is missing or fails verification — the page then keeps the legacy snapshot and logs the verification error at build time. No number is drawn from an unverified payload.

## 3b. Trends windows

`/research/trends` gains a **Published windows** panel above the monthly series:

- window buttons: latest month, year to date, trailing 12 months (default `ttm`, decision D03);
- each window shows sales and median price with the prior-year comparator, or `no comparison` when the comparator is not published;
- the panel follows the existing property-type choice (HDB/EC/Condo/All) without a fetch — the build-time reader pre-extracts all four types;
- private types keep the coverage-review note;
- the monthly chart and table are untouched and remain the v1 record, so nothing in the chart is silently re-derived from the pack.

Rendered on the built site (`data-observed-cutoff="2026-10"`):

```text
PUBLISHED WINDOWS   cutoff 2026-10 · generation 6cd4510f26ec
WINDOW  12 months to 2026-10
SALES   25,483   +0.2% vs prior year
MEDIAN PRICE  S$631,000  +1.0% vs prior year
```

`summariseWindows()` in `observed-pack-build.ts` builds the per-type window set once at build time.

## 3c. Explorer and shared panel

The window panel is now one component, `app/src/components/observed/PublishedWindowsPanel.tsx`, used by both `/research/trends` and `/explore`. It owns the window buttons, the comparator formatting and the coverage note; it never fetches and never decides publishability.

`/explore` gains the panel above the workspace, scoped to the selected property type. The caption follows the selected period: on a legacy era it says the area table "compares planning areas on the legacy era selection, which is labelled separately"; on a published window it says the table "reads the same verified pack for the window you select".

The area table, list and map are now on the pack for a published period (§7). The legacy eras remain a separate, labelled historical group in the period control, so a reader can still compare the historical windows — and a build with no pack still renders the default view from `map_metrics`.

## 3d. Correction to the RF03 report

Building the pack exposed an error in the RF03 comparison table: the 2025 column held **full-year** totals (25,084 / 6,209 / 47,504) while the 2026 column held **January–October**. Like-for-like:

| Label | Jan–Oct 2025 | Jan–Oct 2026 | Δ |
| --- | --- | --- | --- |
| HDB | 21,402 | 21,801 | **+1.9%** |
| EC | 5,560 | 2,353 | −57.7% |
| Condominium | 42,413 | 18,477 | −56.4% |

HDB is unchanged in disposition (publishable, now with the correct +1.9%). The EC/condo gap survives the correction, so that item stays open and those scopes stay `limited-display`. The [RF03 report](2026-11-13-rf03-source-reconciliation.md) carries the correction inline.

## 5. Verification

```bash
cd app && bun run test:unit        # 441 pass (30 files; 32 new period/pack/rank/default tests)
cd app && bun run astro check      # 0 errors, 0 warnings, 22 hints
cd app && bun run validate-data    # v1 release + v2 pack both verified
cd app && bunx playwright test tests/e2e/explore.spec.ts            # 13 passed
cd app && bunx playwright test tests/e2e/dashboard/leaderboard.spec.ts  # 14 passed
cd app && bunx playwright test tests/e2e/dashboard tests/e2e/explore.spec.ts \
  tests/e2e/explorer-map.spec.ts tests/e2e/trends.spec.ts          # 73 passed
# Pages build (own server, raw .gz bytes, repository prefix)
cd app && bun run build:pages && PLAYWRIGHT_PAGES_PORT=4402 node scripts/serve-pages-base.mjs
PAGES_ORIGIN=http://127.0.0.1:4402 PLAYWRIGHT_BASE_PATH=/egg-n-bacon-housing \
  bunx playwright test tests/e2e/pages-base.spec.ts                # 9 passed, incl. the pack under the prefix
uv run pytest tests/test_v2_observed.py tests/test_reporting_baseline.py \
  tests/test_export_app_data.py --no-cov -q                        # 84 passed
uv run ruff check && uv run ruff format --check scripts/           # pass
uv run python scripts/tools/validate_docs_layout.py                # pass
uv run python scripts/tools/verify_reporting_baseline.py --assets  # 72 pinned assets
```

The overview E2E still asserts the strip's cutoff, the 21,801-sales figure, the +1.9% comparison and the coverage-review note; the explorer specs assert the pack identity, an unpublished id's message and the limited-display ordering rule.

## 6. Remaining for RF05

| Surface | Work | Size |
| --- | --- | --- |
| `PUBLIC_OBSERVED_RELEASE=v2` | Flip for one build once RF06 has moved fieldnotes/tools; §9 is the staged check to run first | one config line, gated |
| Host contract | Confirm the deployment serves `observed/**/*.json.gz` without a `Content-Encoding` header (see §7.4) | small, blocks nothing |

## 7. Explorer rows and map on published periods (second pass)

An earlier attempt widened `ExplorerPeriod` and rewrote the row shape in one go; it cascaded through three modules and four type errors sat in the middle of the change, so it was reverted rather than left half-migrated. The second pass shipped in the dependency order that attempt lacked, with `astro check` green after the row-shape step.

### 7.1 Vocabulary (`explorer-selection.ts`)

- `ExplorerPeriod = ExplorerLegacyPeriod | ExplorerPackPeriod`. The legacy family is the four `map_metrics` eras; the pack family is a concrete id (`month_|ytd_|ttm_YYYY_MM`, `year_YYYY`), regex-validated with a real month range. No free-form string reaches a URL, and friendly aliases (`ttm`, `latest`) are never written.
- **Collision rule:** a legacy id always reads the legacy era, even where the pack publishes the same id (`year_2025`). That keeps existing links meaning what they meant, keeps the default view renderable in a build with no pack, and makes the settings list deterministic — the pack's `year_2025` descriptor is simply not offered as a separate option.
- The default period is still the legacy 2025 era. Moving the bare-URL default onto the pack is the migration step with its own notice, not a side effect of this one.

### 7.2 Rows (`explorer-pack-rows.ts`, shared in `observed-rows.ts`)

- `buildPackExplorerDataset()` reads the already-verified `PeriodPack`: area rows from every observation for the selected period and property type except `SG`, values from `transactionCount`/`medianPrice`/`medianPsf`, national from the pack's own `SG` observation. It returns `ok: false` with the published id list for an unpublished or malformed id — never an empty dataset that reads as "no areas match".
- Both sources share `finaliseExplorerRows()`: ordering, the 150-sale rule and the search filter are one implementation, so the list, the map and the table cannot disagree between sources. A pack row keeps its `Observation` (`no-sales` stays a real `0` count with null prices); `ExplorerRow.observation` became optional and every row carries a `sectionLabel`.
- `ExplorerDataset` is now a discriminated union (`kind: "legacy" | "pack"`) carrying `label`, `rankable` and a national value list with the source named per metric. The components branch on `kind`, so a pack footer cannot print a `map_metrics` section name.

### 7.3 The ranking gate, not just the numbers

The pack's ratified dispositions are per property type: HDB is `publish`; `all`, EC and condo are `limited-display`. Section 5.6 forbids a rank for a limited-display scope, so a pack window is `rankable` only when the scope observation says `publish`. Otherwise:

- rows are ordered by area name (the sample threshold and search still apply);
- the list shows the pack's coverage note and "Areas are listed by name, not ranked, for this scope";
- the sort control is replaced by a metric selector, and the "ascending/descending by …" line becomes "listed by name";
- the map does not colour areas (a quantile choropleth of values is a rank in colour) and says so, leaving the values in the list and the table.

The legacy eras keep their existing ordering; they are the labelled historical/diagnostic view this release still links to.

### 7.4 Finding: a transport header can defeat byte verification

`loadObservedPack()` hashes the payload bytes it receives against the manifest. Vite's dev and preview servers label every `.gz` response with `Content-Encoding: gzip`, so Chromium inflates the file before the loader sees it and the pinned sha256 can no longer match. The published GitHub Pages layout (`scripts/serve-pages-base.mjs`, and the Pages host itself) serves the same files as raw `application/gzip` bytes, so the deployed path verifies correctly.

- The loader now names the cause when the bytes are not gzip (`"… the response was transport-decoded, so its pinned bytes cannot be checked"`) instead of reporting a bare size mismatch, and it fails closed: no numbers from an unverified payload.
- The root E2E suite serves the pack payloads from disk through a route shim (documented in `explore.spec.ts`); the Pages suite exercises the real raw-byte path, including under the `/egg-n-bacon-housing/` prefix.
- Consequence: a reader on `bun run dev` sees the fail-closed message for a pack window. That is a development-server limitation, not a data problem. The robust fix is a decoded-payload hash in the v2 manifest beside the gzip hash (an RF04/RF12 contract addition) or a payload extension no server re-labels; both are cross-slice changes and are recorded in the handoff instead of being improvised here.

## 8. Compare Areas on published periods

`/dashboard/leaderboard` now accepts the same two period families as `/explore`, with the RF01 seam underneath rather than a second reader.

### 8.1 Vocabulary

- `LeaderboardTimeBasis = LeaderboardLegacyTimeBasis | ObservedPeriodId`, parsed by `parseLeaderboardTimeBasis()`: `recent` / `whole` / `year_2025` keep their exact meaning, a concrete id (`ttm_2026_10`) is kept verbatim, anything else falls back to the documented default (`recent`). The existing query dialect is unchanged, so old links keep working.
- The concrete-id shape moved to the pack contract module (`ObservedPeriodId`, `isObservedPeriodId` in `observed-periods.ts`) because both surfaces accept it; `explorer-selection.ts` re-exports it under its own name and the settings list helpers (`publishedPeriodOptions`, `packPeriodLabel`) live there too.
- The period control lists published windows first (when a verified pack is in hand) and the historical eras after, so the historical view never disappears.

### 8.2 One ranking loop, two sources

`buildRankRows()` in `leaderboard-observed.ts` owns the RF01 semantics — region/price/search filtering, the 150-sale caution threshold, null-last ordering and `rank: null` for unranked rows — and both sources supply only a `readMetrics` / `readMix` pair:

- legacy: `readScopedAreaMetrics()` over the joint `map_metrics[era_property]` section (unchanged);
- pack: `readPackAreaMetrics()` over the verified `PeriodPack`, with the same-window `hdb`/`ec`/`condo` counts as the property mix. A verified `no-sales` area keeps `0` sales with null prices.

`buildPackScopedRows()` returns `ok: false` with the published id list for an unpublished or malformed id, and otherwise the rows plus the period label, the scope's disposition and its coverage note.

### 8.3 Disposition gate

The scope's ratified disposition decides ranking: `publish` (HDB) ranks exactly as before; `limited-display` (`all`, EC, condo) is readable but never ranked. On a limited-display window:

- rows are ordered by area name, every `rank` is `null` and `data-ranked="false"` — the E2E suite pins that no row claims a rank;
- the summary says the areas are listed by name because coverage is limited, and shows the pack's coverage note;
- the map is not colour-coded (the choropleth is a rank in colour) and says so.

### 8.4 Shared verification, one identity line

Both surfaces verify through the same `useObservedPack()` hook, so there is one browser fetch/verify path, not two. The summary line names the window and its source — `map_metrics.recent_hdb` for an era, `observed pack · ttm_2026_10 · 6cd4510f26ec…` for a published window — and an unavailable window replaces the map and table with the reason instead of rendering an empty ranking.

The root E2E suite shares the pack-serving route shim (`tests/e2e/utils/servePackBytes.ts`) with `/explore`; the Pages suite still exercises the real raw-byte path.

## 9. Bare-URL defaults and the migration notice

D03 makes YTD/TTM the current windows, which changes what a bare observed URL opens on. Contract §5.3 requires that change to be explicit: the route shows the exact active window and offers a link to the window it used to open on. It is also tied to the release switch, so a staged build without it behaves exactly as before.

### 9.1 Resolution (build time)

`app/src/utils/observed-defaults.ts` resolves the default against the verified pack and the `PUBLIC_OBSERVED_RELEASE` switch:

- switch off (the shipped default) → `null`: every route keeps its historical default and no notice appears;
- switch on, no verified pack → `null`: no default is invented;
- switch on, pack present → D03's alias for the surface (`ttm` for `/explore` and Compare Areas) as a **concrete** id plus its label.

The two pages (`explore.astro`, `dashboard/leaderboard.astro`) compute that once, then hand the island the default and its own previous-window link (`?period=year_2025` and `?timeBasis=recent` respectively). Nothing consults the clock, and a stale pack cannot look fresher than its cutoff.

### 9.2 Behaviour in the island

- A **bare** URL adopts the default; an explicit `?period=` / `?timeBasis=` is never overridden, and it never shows the notice.
- The adopted window is a concrete id, so the existing serialisers write it into the address bar — newly shared links name the window, as the contract requires.
- The notice reads *"Updated default. This page now opens on 12 months to 2026-10. The earlier default was 2025 complete year — open that view."* (Compare Areas uses *2022 onward*), and the link resolves to the previous window with the notice absent.
- "Reset settings" returns to the route default, not to the historical era.

### 9.3 Verification

- Unit: `observed-defaults.test.ts` (switch off, no pack, resolved window, other aliases, a pack without that window).
- Default build: the root E2E asserts the notice is **absent** on both routes, so a legacy-mode build cannot drift.
- Staged build: `tests/e2e/observed-defaults.spec.ts` is skipped unless `OBSERVED_V2_ORIGIN` is set; run against `PUBLIC_OBSERVED_RELEASE=v2 bun run build`, it asserts the adopted window, the URL, the notice text and both links. Ran for this report: 3 passed.

**Do not flip the switch while fieldnotes and tools still read v1 periods** (RF06). The flip is one build-time env var plus this staged run, not a code change.

## 10. The switch, flipped (2026-11-13)

`PUBLIC_OBSERVED_RELEASE=v2` is now the shipped build mode:

```jsonc
"build":        "PUBLIC_OBSERVED_RELEASE=v2 bun run build:base",
"build:base":   "bun run validate-data && bun run sync-catalog && astro build",
"build:legacy": "PUBLIC_OBSERVED_RELEASE=legacy bun run build:base"   // verification only
```

`build:pages` inherits the v2 mode, so the deployed layout and the Pages E2E suite exercise the migrated defaults.

### 10.1 What moved, and what did not

| Surface | Bare-URL default | Notes |
| --- | --- | --- |
| `/explore` | `ttm_2026_10` (pack) | adopts D03; shows the updated-default notice and a link to `?period=year_2025` |
| `/research/trends` | `ttm` (unchanged) | the published-windows panel already defaulted to D03 |
| `/dashboard` | YTD strip (unchanged) | the legacy snapshot stays visible beside it |
| `/dashboard/leaderboard` | **`recent` (unchanged)** | see 10.2 |
| `/areas/<slug>` | fixed build-time section (unchanged) | specialised surface; does not inherit a new observed default (contract §5.3) |

### 10.2 Why Compare Areas keeps its ranked default

D03 says rankings default to the trailing-12-month window. In this release the pack's `all` scope is `limited-display`, and §5.6 forbids ranking such a scope — a bare Compare Areas URL would open as an unranked name-ordered list. That is a product regression, not a migration.

The page therefore adopts D03's default **only when its default scope is cleared to publish** (`allScopePublishable` in `leaderboard.astro`, read from the pack's `SG|all` disposition). Today that is false, so Compare Areas keeps "2022 onward" (ranked), offers every published window in the control, and shows no notice because no default moved. When EC/condo coverage clears, the same code adopts `ttm_2026_10` with the notice automatically — no second switch.

### 10.3 A defect the flip exposed, fixed

`serializeExplorerSelection()` compared against the *legacy* defaults. On a v2-default page that dropped an explicit `?period=year_2025` from the address bar, so a reload silently switched the reader to the pack window. The serialiser now takes the route's **active** defaults, and a concrete published id is always written even when it is the default — a shared link pins the window it showed, because the default is re-resolved from the pack on every build.

### 10.4 Verification

```bash
cd app && bun run build                # v2 mode, 219 pages
cd app && bun run build:legacy         # legacy mode still builds clean (0 notices)
cd app && bunx playwright test tests/e2e                    # 230 passed, 9 skipped
cd app && bun run build:pages && bunx playwright test tests/e2e/pages-base.spec.ts  # 9 passed
cd app && bun run test:unit            # 462 pass
cd app && bun run astro check          # 0 / 0 / 22
```

Tests were made mode-explicit rather than loosened: legacy-data assertions pin `?period=year_2025`, the pack path uses the raw-bytes route shim (`tests/e2e/utils/servePackBytes.ts`) where preview would otherwise inflate `.gz`, and `observed-defaults.spec.ts` now runs in the root suite because v2 is the shipped mode.

### 10.5 Remaining RF05 item

Only the **host contract** check (deploy serves `observed/**/*.json.gz` without a `Content-Encoding` header). The Pages server does; confirm on the real host at release time (RF12).
