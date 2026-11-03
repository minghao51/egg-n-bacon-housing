# S4 implementation report — honest overview and monthly trends

Two deliverables: the dashboard overview now reads its headline numbers from one published section with an explicit scope, and `/research/trends` is a real monthly destination. **No commit**; no published asset modified.

## 1. What shipped

**`/research/trends`**
- `app/src/utils/trend-series.ts` (pure) — builds one series from `dashboard_trends`, materialises an omitted month as an explicit `null` gap (so nothing can compress it), filters windows by calendar bounds, trims "all history" only to that series' published coverage (EC/condo start 2021-01), and refuses `yearSum` unless all twelve calendar keys are present.
- `app/src/components/trends/*` — two self-contained SVG charts (price line with break-on-gap and a disclosed 5% zoom; volume bars with a zero-based axis), an accessible monthly table with `N/A`, a latest-value summary that includes the 12-month sum for a complete year, and a source footer naming `dashboard_trends` and the actual last month (`2026-09`).
- `app/src/pages/research/trends.astro` — one H1, "not an adjusted price index" explanation, `<noscript>` that points at the catalogue (not the tools route), `client:only` island, `?series=&window=` state with validated fallbacks.

**Dashboard overview**
- Replaced the unscoped "What Changed Recently" block (mixed property types and unlabelled deltas) with three cards reading `dashboard_overview.stats.year_2025_hdb|ec|condo` — `S$628,000`/`25,084`, `S$1,578,000`/`6,209`, `S$1,938,952`/`47,503` — plus the all-type total (`78,796`, `S$1,465,000`) and a "2025 medians of observed sales, not an index or a forecast" note.
- Market Snapshot now states its scope line (`period · type · count · from dashboard_overview.stats.<section>`), uses literal era labels, degrades to "Not published" instead of zeros, and separates export time from source freshness.
- Capability strip links `/explore`, `/research/trends`, `/areas/tampines`, `/dashboard/leaderboard`, `/dashboard/trends`, `/dashboard/segments`. `/research/segments` was omitted because it does not exist.
- Both overview charts gained a "View as a table" disclosure with the actual plotted counts.

Navigation gained a **Monthly trends** item (`research/trends`), so the new page is reachable from every sidebar page.

## 2. Verification

| Check | Result |
|---|---|
| `bun run test:unit` | **169 pass** (26 trend-series tests, incl. gap materialisation and `yearSum` calendar integrity) |
| `bun run astro check` | **26 errors / 0 warnings / 41 hints / 149 files** — down from 36, no new diagnostic in touched files |
| `bun run build` | passes; `/research/trends` generated |
| Playwright | **133 pass** (8 trends + 7 overview tests added) |
| Browser, overview | the three medians and counts render; `from $1,230,000` / `from 5,577` gone; no "refreshed daily"; capability links resolve |
| Browser, trends | 2025 HDB table has 12 rows; `2025-12 = 635,000 / 2,024`; 12-month sum `25,084`; volume axis states it starts at zero; price chart states the zoom and real min/max |
| Browser, EC all-history | 69 rows starting `2021-01` (previously 441 rows of `N/A`, which implied coverage that does not exist) |
| Mobile | 390px, no horizontal overflow |

## 3. Review-driven corrections

- Missing calendar months were compressed instead of shown as gaps → now materialised as `null` points; test updated to require the gap.
- `yearSum` accepted an out-of-range month (twelve keys including `2025-13`) → now requires exactly `2025-01…2025-12`.
- Empty-window copy implied "no transactions" → now says the asset publishes no values there.
- Overview charts had no numeric text alternative → collapsible tables added.
- The no-JS fallback pointed at the tools route as a trends destination → now points at the catalogue.

## 4. Gaps and follow-ups

- The overview still renders the legacy monthly price/volume charts (now duplicated by `/research/trends`). Removing them from the overview would reduce duplication, but that is a product decision; they remain scoped and labelled.
- Chart series colours are still the legacy Recharts palette (blue/purple), not the Fieldnotes series colours; the pie reads poorly because one type dominates. Tokenising chart series is not part of S4.
- The overview's all-history `1,234,928` records may include the known duplicate HDB rows; the page lists records from the published distribution asset, not de-duplicated transactions, and does not claim otherwise.
- Trend chart accessibility is a textual description plus the table; no SVG focusable data points.
- Dark mode remains unreviewed.

## 5. Next

S5's remaining **map view** in `/explore` (the last large missing surface), or S7 segment migration. S4 deliberately did not touch `/dashboard/trends` (tools) so its behaviour and tests stay intact.
