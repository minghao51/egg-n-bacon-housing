# RF10 report — area activity

- **Date:** 2026-11-14
- **Status:** **Complete (slices 1, 2a, 2b).** `/areas/<slug>` now publishes observed transaction activity: the rolling quarter, its prior-year quarter, the year-on-year change, the trailing-twelve-month context and the D05 floor verdict per property type — all rendered from the **verified pack at build time**, so the block costs no new bytes and no browser fetch. The explorer list carries the same comparison through the same helper, so the two surfaces cannot disagree. Neutral numbers only: no directional label, score, colour-by-change or derived statistic. The fieldnote also loads a verified month-by-month history **on request** (the largest asset in the release), with explicit loading / missing / error / retry states and a verified zero kept distinct from missing source. Map colouring by activity is deliberately not built.
- **Parent:** [handoff](../plans/2026-11-12-reporting-refresh-handoffs.md) RF10 · [implementation map](../plans/2026-11-12-reporting-refresh-implementation-map.md) §5.2/§5.3
- **Decisions:** D05 (150-sale caution in both windows), D09 (no composite score / demand claim), D02 (cutoff 2026-10)
- **Upstream:** [RF09 history and calibration](2026-11-14-rf09-area-type-month-history.md) · [RF06 fieldnotes](2026-11-13-rf06-fieldnotes.md) · [RF05 periods](2026-11-13-rf05-current-periods.md)

## 1. What exists now

| Piece | Behaviour |
| --- | --- |
| `app/src/utils/area-activity.ts` | Pure, client-safe view model. `rollingQuarterPeriod(pack)` picks the newest published `rolling3` period; `buildAreaActivity(pack, areaId)` returns the quarter window, its prior-year comparator, one row per property type the quarter reports, the TTM context, an eligibility verdict and neutral notes. No `node:*`, no fetch. |
| Window semantics | A verified `no-sales` window yields `transactionCount: null` plus a stated reason — never `0`. A missing comparator, a missing prior-year observation or a zero prior denominator yields `changePercent: null` with the reason attached, instead of dropping the column. |
| D05 at quarter scale | `eligible` requires **at least 150 observed sales in both windows** (`ACTIVITY_SALE_FLOOR`). The looser 38-sale quarter-scaled alternative stays evidence in [RF09 §3.4](2026-11-14-rf09-area-type-month-history.md), not an adopted rule, so it is not implemented. |
| `/areas/[slug]` block | New "Observed transaction activity" section: quarter range in months, per-type rows (HDB, EC, condo, all), five numeric cells, a text eligibility verdict ("Yes" / "No — fewer than 150 observed sales in …"), the neutral notes, and an "Open this quarter in Explore" link to `?period=rolling3_<YYYY_MM>`. `data-area-activity`, `data-activity-table`, `data-activity-row`, `data-activity-eligible` hooks for tests. |
| Payload budget | Zero. `loadAreaPages()` already verifies the v2 pack for current-window identities, so the activity rows are computed from that same `summary` during the build. No monthly payload, no island, no client fetch — RF09 §6 risk (a) (570 KB per property) is not incurred. |
| No-JS | The block is static HTML, so it renders identically with JavaScript disabled; nothing is added to the fixed-scope `<noscript>` statement because activity does not depend on the address bar. |

## 2. What the block deliberately does not do

- No directional label, "hot/cold", score, rank or colour-by-change (D09; RF09 §3.2 shows the year-on-year change flips sign at least twice for every qualifying area across twelve quarter ends).
- No derived statistic: no turnover, no stock normalisation, no per-capita rate, no annualisation of a quarter. Every number is a published `transactionCount`.
- No ranking of thin areas: a row below the floor is visible with its numbers and stated as ineligible, matching the explorer rule that thin rows are visible but unranked.
- No claim about demand, liquidity, supply or expected return; the notes say what the counts are and are not.

## 3. Tests

Unit — `app/tests/unit/area-activity.test.ts` (13 tests) against the golden `tests/fixtures/v2-pack/` plus synthetic packs: newest-quarter selection, no-quarter pack, explicit ranges, both denominators (PUNGGOL HDB 488 vs 370, TTM 1,702 kept separate), thin type keeps its numbers and is ineligible (`ANG MO KIO` EC 2 vs 2), row order, no-sales as absence, missing comparator stated, floor boundary at exactly 150 vs 149, zero prior denominator, no row for an unreported type, unknown area, and a key-name check that no `score`/`hotness`/`turnover`/`demand`/`liquidity`/`ranking` field can be added silently.

E2E — `app/tests/e2e/areas.spec.ts` (+2): the Punggol block renders both quarter ranges, five cells per row, `data-activity-eligible` true for HDB and false for EC with the stated reason, the neutral notes, no cold/hot wording, and the Explore link pointing at `rolling3_<YYYY_MM>`; plus a 390-px viewport check that the table scrolls inside its own container and the document does not overflow.

One pre-existing assertion was **rescoped, not weakened**: `areas.spec.ts` counted `page.getByRole("table")` rows (3) for the national comparison, which now also matched the activity table (8 rows). It is scoped to `section[aria-labelledby="area-comparison-heading"]`.

## 4. Verification

```bash
cd app && bun run test:unit            534 passed (34 files; +26 over 508)
cd app && bun run astro check          0 errors, 0 warnings, 22 hints
cd app && bun run build                221 pages
cd app && bunx playwright test tests/e2e --workers=4   237 passed / 9 skipped (+6)
```

No Python-side change, so the pipeline/evidence checks are untouched by this slice.

## 5. Explorer parity (slice 2a)

The explorer now shows the same activity as the fieldnote, through the same code:
`activityForObservation(pack, observation)` in `area-activity.ts` owns the
quarter-to-quarter arithmetic and the D05 verdict, and **both** surfaces call it — the
fieldnote table via `buildAreaActivity()`, the explorer row via
`buildPackExplorerDataset()` (`toRowActivity`). A parity unit test pins the two against
each other for every published property type, so they cannot drift into two definitions
of "eligible".

| Piece | Behaviour |
| --- | --- |
| `ExplorerRow.activity` | Optional `{ priorCount, changePercent, reason, eligible }`. `null` means the window publishes no comparator — deliberately different from "no change". |
| Explorer list | One neutral sentence under the area name: `Prior-year same window: 370 sales (+31.9%)`, or `Prior-year comparison: <reason>` when it cannot be computed, with `· below the 150-sale floor` appended whenever the row fails D05. `data-explorer-activity` is `eligible` or `ineligible` for tests. |
| Ranking gate untouched | A `limited-display` scope (EC, condo, All) still shows the numbers and still refuses to rank: verified by a new unit test and an E2E test that the sort control is absent. |
| Neutral vocabulary | No up/down, hot/cold, score or colour-by-change; a thin row states its floor verdict in words instead of being greyed into a signal. |

Tests added: four unit tests on the row projection (eligible row carries both denominators
and the signed change; limited-display keeps activity but is unranked; a comparator-less
window carries `activity: null`; a missing prior observation states the reason), two
parity tests in `area-activity.test.ts`, and two E2E tests on `/explore` (rolling-quarter
sentence + limited-display unranked).

## 6. Monthly history on request (slice 2b)

| Piece | Behaviour |
| --- | --- |
| `app/src/utils/area-history.ts` | Pure view model: `buildAreaHistoryView(history, areaId, limit = 24)` enumerates **`history.months`** (never `coverage.firstMonth`/`lastMonth`), reads each month through `readMonth`, and reports `hasObservations` / `noSalesMonths` / the payload's own coverage rule. `monthStatusLabel()` turns a status into words. |
| `app/src/components/areas/AreaHistoryPanel.tsx` | Island (`client:idle`) that fetches **nothing** until the reader presses "Load monthly history". It fetches the manifest, runs `parseV2Manifest`, then `loadObservedHistory(manifest, property, { baseUrl })` — the payload is hashed against the manifest before a single number renders. |
| States | `idle` (button + explanation), `loading` (`role="status"`), `error` (message + **Retry**, keeps any already-verified table), `ready` (table), and an explicit empty state when the release carries no series for that area. A verified zero month renders "No observed sales", never `0`. |
| Payload budget | Nothing is requested on page load. The first fetch happens on click and is one property payload (≤233 KB) plus the ~2 KB manifest — the core pair is not re-fetched. Props carry identity only (`areaName`, `areaId`, `property`, `base`), so no history enters SSR HTML (RF09 §6 risk (a)). |
| Accessibility | Real `<table>` with a `<caption>`, month as a row header, status text instead of colour, and a native button for both load and retry. |

Tests: seven unit tests (`area-history.test.ts`) over the golden monthly fixture plus a synthetic history — ascending grid order, month limit, coverage passthrough, absent area as an empty view, verified zero counted but never valued, an all-zero area distinguished from a missing one, and the two status labels. Two E2E tests: the payload is **not** requested before the click and the table renders ascending after it; and an aborted payload request shows the error, then retry succeeds.

## 7. What RF10 still does not do

| Item | Why |
| --- | --- |
| Fieldnote per-area current slices (deferred from RF06) | The activity block and the monthly history cover the reader-facing need; a per-area `rolling3` slice would duplicate the activity table in another shape. |
| Directional labels | Blocked on the owner: RF09 §3.4 is a proposal, not a decision. |
| Map colouring by activity | Deliberately not built: RF09 §3.2 shows the change flips sign for every qualifying area across quarter ends, so colour-by-change would be a directional label in disguise. |
| Explorer monthly sparkline | The fieldnote owns the per-area history; adding a second surface would fetch the same payload again for the same numbers. |
