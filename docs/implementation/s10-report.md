# S10 implementation report — integration, regression and release readiness

S10 closes the shipping path: the Pages-base build is exercised under its real prefix, the remaining type debt is cleared, charts/tables that had no empty state do, modal dialogs share one keyboard contract, and a failed background refresh can no longer hide published data. An independent S8–S10 audit then tightened the evidence wording, the payload measurement and the release smoke checks. The work is committed and pushed to `main` (`52c901b`, ignore follow-up `6aef15a`); deployment/CDN verification was not performed from this environment.

## 1. Defects fixed

| Defect                                                                                                                                           | Fix                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Astro check ended with 3 errors (2 in dead `PersonaHeader.tsx`, 1 implicit `any` in `leaderboard.astro`)                                         | Deleted the unreferenced `PersonaHeader.tsx` (S8-F5) and typed the leaderboard `gunzip(data: Buffer)`. **0 errors / 0 warnings / 22 hints** on 187 files.                                                                                                                                                                              |
| Deploy smoke checks grepped headings removed in S7–S9 (`Explore Areas`, `Decision Tools`, `Discover Segments`)                                   | `.github/workflows/deploy.yml` now checks 17 route paths (including the lease article, investor persona, `unified_dataset` catalog page and Bishan fieldnote) and verifies a base-prefixed `_astro` asset. A Pages deployment would have failed before this.                                                                           |
| CI never ran the frontend checks                                                                                                                 | New `frontend` CI job: `bun run astro check`, `bun run test:unit`, `bun run validate-data` (with the pinned Bun 1.2.23 and frozen lockfile).                                                                                                                                                                                           |
| Dialogs were not all dialogs: the leaderboard metric guide had no dialog semantics, and none of the three overlays moved/trapped/restored focus  | Added `src/hooks/useModalDialog.ts` (focus into dialog, Tab trap, Escape, body-scroll lock, focus restore) and applied it to the metric guide, the segment evidence guide and the mobile leaderboard filters sheet. A module-level dialog stack makes Escape/Tab top-dialog-only and restores scroll only when the last dialog closes. |
| A failed background refresh of server-rendered data was silent (the intent matrix deliberately suppressed the error), so stale rows looked fresh | `useGzipJson` now exposes `refreshError` for a failed refresh while data remains. The leaderboard shows a labelled amber banner with a retry; a fatal error no longer replaces displayed rows (`error && data.length === 0`).                                                                                                          |
| Schema search with no matches rendered an empty table body                                                                                       | `SchemaTable` renders “No schema fields match … Clear the search to see all N fields.” The required-with-nulls summary now follows the filtered rows, and `aria-sort` is set only on the active sort column.                                                                                                                           |
| A missing/unreadable `map_metrics` asset looked identical to “no 2025 observation”                                                               | `referenceSourceStatus()` distinguishes an unreadable asset from a readable table with absent sections; the financing panel states that the published reference table could not be read.                                                                                                                                               |
| The MRT/CBD page disclosed only the MRT term while the report claimed the scenario formula was disclosed                                         | The CBD term is now shown separately with its supplied units (`(10 km × 15000 per km)`) and is never added to the MRT term. The wording is “both stored terms … total withheld”.                                                                                                                                                       |
| The uniform-spatial warning claimed z, p-value and LISA were shared while only checking z                                                        | The warning now requires all three fields to be uniform; a unit test mutates one p-value and asserts the warning disappears.                                                                                                                                                                                                           |
| The payload script counted UTF-16 units as bytes and measured only direct lazy imports                                                           | Props are measured with `Buffer.byteLength(..., "utf8")`; the lazy column is the transitive dynamic-import graph minus the static graph.                                                                                                                                                                                               |
| Deploy smoke omitted deep routes; the no-JS map link was root-relative; the local Pages server used a prefix check for containment               | Added the four deep routes, made the no-JS `/explore` link base-prefixed, and replaced the server prefix check with a `path.relative` boundary. Path-traversal probes return 404.                                                                                                                                                      |
| A zero metric was always treated as missing without documenting the ambiguity                                                                    | The `PriceMap` comment now states that exporter zeros are empty blocks, no separate empty marker exists, and a genuine zero cannot be distinguished in this asset.                                                                                                                                                                     |
| `remarkStripLeadingH1` removed the first H1 anywhere                                                                                             | It now strips only a genuinely leading depth-1 heading, preserving later H1 anchors and TOC entries.                                                                                                                                                                                                                                   |
| “Dated lookup” conflicted with the archive’s unknown extraction date                                                                             | Lease copy now says “stored-band lookup”.                                                                                                                                                                                                                                                                                              |

## 2. Pages-base verification

`ASTRO_PAGES=true bun run build` emits every URL and asset with `/egg-n-bacon-housing/`. `astro preview` cannot serve that layout, so S10 adds:

- `app/scripts/serve-pages-base.mjs` — static mount of `dist/` under the prefix; paths outside the prefix 404, `.gz` is served as raw `application/gzip`, and `/` redirects into the base.
- `app/scripts/measure-payload.mjs` — payload/hydration measurements (below).
- `tests/e2e/pages-base.spec.ts` — 8 tests, skipped in a normal root run and run explicitly with `PAGES_ORIGIN`.

The spec proves: HTML/CSS/JS all carry the prefix; an island hydrates and fetches `dashboard-release.json` under the prefix (release status becomes verified, not withheld); all 17 shipping route headings render; every root-relative internal link starts with the base and every same-origin home link resolves 200; deep links retain all five query groups; key routes produce no same-origin 4xx and no page error; a 390 px drawer navigates to `/research/map/` without horizontal overflow.

Local deploy-grep simulation against the Pages build passes for all 17 deploy-checked routes and for the base-prefixed CSS asset.

## 3. New regression coverage

`tests/e2e/integration.spec.ts` (13 tests):

- Mobile drawer: keyboard open, focus moves to the close button, `main` becomes `inert`, Tab stays inside, Escape closes and restores focus, navigation closes the drawer.
- Modals: metric guide (Tab trap, Escape, focus restore), segment evidence guide, mobile filters sheet.
- No-results: explorer search, studies library (0 of 15) with reset, catalog schema search with a filtered-zero row.
- Resilience: aborting `dashboard_leaderboard.json.gz` keeps the server-rendered ranking visible and shows the refresh banner; retry clears it. A separate test proves the island revalidates the SSR data (request count > 0) rather than trusting the HTML.
- Private input: financing income changes stay out of the URL, request URLs **and bodies**, console output and local/session storage; only `tool`/`ref`/`rt`/`rv` query keys are present. No fixed sleep is used.
- Spatial patterns tab: reached with `End` from the financing tab, 40 town rows, no allocation/BUY/SELL.
- Legacy routes: all four legacy URLs render their research equivalents.

`tests/e2e/research/tools.spec.ts` additions: keyboard Arrow/Home/End tab navigation, popstate tool switching, reference-import parity between `/research/tools` and `/dashboard/trends` (Queenstown condo S$2,088,000), and both MRT/CBD term disclosures.

## 4. Payload and hydration (gzip, root build)

Measured with `bun run measure:payload`. “JS gz” is the HTML-referenced static module graph (island components included). “Lazy extra” is the transitive dynamic-import graph minus the static graph, so the two columns are disjoint. SSR props are UTF-8 bytes of the `astro-island` attributes.

| Route                                | HTML gz | JS gz    | CSS gz  | Chunks | Lazy extra  | Islands (directive)   | SSR props |
| ------------------------------------ | ------- | -------- | ------- | ------ | ----------- | --------------------- | --------- |
| `/`                                  | 2.2 kB  | 1.0 kB   | 9.3 kB  | 1      | —           | 0                     | 0         |
| `/dashboard/`                        | 15.9 kB | 181.8 kB | 9.3 kB  | 13     | —           | 3 (load:3)            | 88.5 kB   |
| `/dashboard/map/`                    | 6.2 kB  | 118.8 kB | 15.5 kB | 12     | —           | 3 (load:2, only:1)    | 184 B     |
| `/dashboard/trends/`                 | 12.1 kB | 78.0 kB  | 9.3 kB  | 9      | —           | 3 (load:2, only:1)    | 38.2 kB   |
| `/dashboard/segments/`               | 5.9 kB  | 82.1 kB  | 15.5 kB | 12     | 3 / 46.5 kB | 3 (load:2, only:1)    | 91 B      |
| `/dashboard/leaderboard/`            | 15.4 kB | 76.2 kB  | 15.5 kB | 11     | 3 / 46.5 kB | 3 (load:3)            | 34.5 kB   |
| `/explore/`                          | 5.7 kB  | 78.5 kB  | 9.3 kB  | 11     | —           | 3 (load:2, only:1)    | 223 B     |
| `/research/trends/`                  | 5.8 kB  | 70.8 kB  | 9.3 kB  | 9      | —           | 3 (load:2, only:1)    | 122 B     |
| `/research/map/`                     | 6.2 kB  | 118.8 kB | 15.5 kB | 12     | —           | 3 (load:2, only:1)    | 184 B     |
| `/research/tools/`                   | 12.0 kB | 78.0 kB  | 9.3 kB  | 9      | —           | 3 (load:2, only:1)    | 38.2 kB   |
| `/research/segments/`                | 5.8 kB  | 82.1 kB  | 15.5 kB | 12     | 3 / 46.5 kB | 3 (load:2, only:1)    | 91 B      |
| `/analytics/`                        | 8.9 kB  | 65.1 kB  | 9.3 kB  | 8      | —           | 3 (load:3)            | 6.5 kB    |
| `/analytics/lease-decay/`            | 10.2 kB | 63.2 kB  | 9.3 kB  | 7      | —           | 2 (load:2)            | 72 B      |
| `/catalog/`                          | 31.5 kB | 137.3 kB | 11.9 kB | 13     | —           | 4 (load:3, visible:1) | 186.8 kB  |
| `/catalog/platinum/unified_dataset/` | 14.5 kB | 79.3 kB  | 9.3 kB  | 9      | —           | 3 (load:2, visible:1) | 22.6 kB   |
| `/areas/bishan/`                     | 8.0 kB  | 63.2 kB  | 9.3 kB  | 7      | —           | 2 (load:2)            | 72 B      |

The catalog index was the outlier: its table island received every dataset row as SSR props (**825 kB** uncompressed; 81.1 kB after gzip) because the table is client-rendered. **S10-F1** replaced that transport with per-island projections, so the same route now ships **186.8 kB** of props (31.5 kB gzip); the numbers above are the post-projection build and §8 records the before/after split. The dashboard still embeds 88.5 kB of overview/trends props and its 181.8 kB JS graph includes the charting dependencies. Segments and leaderboard add 46.5 kB of lazy map/chart code that is not part of the initial graph. These are recorded as debt, not regressions.

## 5. Verification matrix

| Check                                                      | Result                                                                                              |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `bun run test:unit`                                        | **310 pass, 0 fail** (21 files)                                                                     |
| `bun run astro check`                                      | **0 errors / 0 warnings / 22 hints / 187 files**                                                    |
| `bun run validate-data`                                    | passes: 19 assets, release `0e1013ee485f` (7 assets)                                                |
| `bun run build`                                            | **201 pages**; catalog asset restored afterwards                                                    |
| `bunx playwright test` (root preview)                      | **198 passed, 8 skipped, 0 failed** (the 8 are the Pages-base spec, skipped without `PAGES_ORIGIN`) |
| `bun run build:pages` + `bun run serve:pages` + Pages spec | **8 passed**                                                                                        |
| `bun run measure:payload`                                  | recorded above                                                                                      |
| `uv run pytest tests/test_export_app_data.py --no-cov -q`  | **44 passed** (no exporter change)                                                                  |
| `uv run ruff check`                                        | clean                                                                                               |
| Prettier                                                   | applied to every changed JS/TS/TSX/JSON/Markdown/workflow file; `.astro` remains outside the hook   |
| `git status`                                               | no published asset or `bun.lock` change; work committed and pushed, worktree clean                  |

Deliberate non-claims: the production GitHub Pages CDN, live map-tile availability and the deployed workflow itself were not exercised from this environment. Their local prerequisites (Pages build, prefixed assets, deploy greps) were verified. The report's pass counts are local run results, not committed logs.

## 6. Remaining debt and owners

| ID     | Item                                                                               | Suggested owner   | Notes                                                                                                                                            |
| ------ | ---------------------------------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| S10-F1 | ~~Catalog index ships 825 kB of SSR island props (all dataset rows)~~ **Resolved** | frontend          | Per-island projections (`utils/catalog-payload.ts`): 825.0 kB → 186.8 kB. The remaining cost is the lineage edge list (~153 kB), recorded in §8. |
| S10-F2 | No JS payload budget; `/dashboard` graph is 181.8 kB gzip                          | performance       | Establish per-route budgets before adding another chart library or island.                                                                       |
| S10-F3 | Full Playwright suite is not run under the Pages base                              | integration       | The focused 8-test spec covers assets, hydration, links and deep links; a base-aware `goto` fixture would allow the full run.                    |
| S10-F4 | Workflows use mutable action tags (`actions/checkout@v4`, `setup-bun@v2`, …)       | CI / supply chain | Pin to full commit SHAs; not done here because the SHAs must be fetched and reviewed, not invented.                                              |
| S10-F5 | `refreshError` is surfaced by the leaderboard only                                 | frontend          | It is the only surface that revalidates server-rendered data; new SSR-backed islands must adopt the same banner.                                 |
| S10-F6 | The deployed Pages smoke step cannot run locally                                   | release owner     | The same greps and the base-asset check pass against the local Pages build; the workflow runs them after deployment.                             |
| S10-F7 | Catalog audit observation is a recorded constant                                   | data boundary     | `catalog-audit.test.ts` now pins both visible counts, so regenerating either side fails until the constant and copy are updated.                 |

Resolved by S10 and its audit pass: the remaining `astro check` debt, S8-F5 (`PersonaHeader.tsx`), reference-asset failure conflation, MRT/CBD term disclosure, the spatial-warning predicate, payload byte/lazy accuracy, deep-route smoke coverage, the root-relative no-JS link, server path containment, filtered schema state and sort ARIA.

## 7. Release stance

- All planned slices (S0–S10) are implemented and pushed to `main` (`52c901b`, ignore follow-up `6aef15a`).
- No deployment/CDN verification and no data/model regeneration were performed from this environment.
- No scoring, eligibility, recommendation or model-definition boundary changed.
- The next actions require explicit approval: GitHub Pages deployment verification, or a data/model refresh.

## 8. Follow-up — S10-F1 catalog payload (resolved)

Branch `feat/s10-f1-s8-f1` (S10-F1 + S8-F1, no data/model/scoring change). `/catalog/` now projects the parsed catalog once, in `app/src/utils/catalog-payload.ts`, and passes each island only the fields it renders:

- `tableRows(datasets)` → `{ id, label, layer, status, rowCount, columnCount, bytes, hasSchema }` for `DatasetTable`; `hasSchema` replaces the `schema` object, so schema fields never reach the island.
- `dagNodes(datasets)` → `{ id, layer, label }`; `dagEdges(edges)` → `[from, to]` tuples.
- `catalog/[layer].astro` uses the same table projection. Dataset routes, slugs, ordering, labels, search, sorting and links are unchanged.

Measured with `bun run measure:payload` on a full root build (UTF-8 bytes of the decoded `astro-island` props):

| Island                | Before                   | After                    | Change     | Per-island split after                          |
| --------------------- | ------------------------ | ------------------------ | ---------- | ----------------------------------------------- |
| `DagGraph`            | 533,956 B                | 165,600 B                | −69.0%     | nodes 12,409 B + edges 153,146 B + baseUrl 15 B |
| `DatasetTable`        | 310,811 B                | 25,543 B                 | −91.8%     | rows 25,543 B + baseUrl 15 B                    |
| **`/catalog/` total** | **844,839 B (825.0 kB)** | **191,250 B (186.8 kB)** | **−77.4%** | —                                               |

- Route-level: HTML gzip **81.1 kB → 31.5 kB**; JS/CSS/islands unchanged (13 chunks, 137.3 kB JS gz).
- The four layer pages (`/catalog/{bronze,silver,gold,platinum}/`) now use the same table projection; bronze ships 21,598 B of props instead of 149,345 B of full dataset records.
- JSON-level projections over the committed snapshot (125 datasets, 2,333 edges): rows 21,039 B, nodes 10,405 B, edges 125,146 B — 156,590 B against 452,032 B of full dataset+edge records (**−65.4%**).
- **Residual cost:** the lineage edge list is now 153 kB of the 187 kB total (82%). It is a genuine 2,333-row graph the DAG must draw, not an accidental payload; removing it would mean server-rendering or paginating the graph, which changes capability and was not done. Tuples replaced `{from,to}` objects to keep it at this level.
- Regression cover: `tests/unit/catalog-payload.test.ts` (7 tests — field shape, order, null parquet, no source mutation, and size bounds <40 kB / <25 kB / <160 kB); `tests/e2e/catalog.spec.ts` gained a filtered-table keyboard-sort test (waiting on island hydration before typing) and a graph node-link test.

Re-verified after the change: `test:unit` **334 pass** (23 files), `astro check` **0/0/22 on 191 files**, `validate-data` passes (19 assets, release `0e1013ee485f`), `build` 201 pages, root Playwright **204 passed / 8 skipped / 0 failed**, Pages-base spec **8 passed**, payload table above. No `bun.lock` or published-data change; `catalog.jsonl.gz` restored after each build.
