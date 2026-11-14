# RF06 report — area selections and tool/legacy contracts

- **Date:** 2026-11-13
- **Status:** **Complete for the fieldnote scope.** `/areas/<slug>` keeps its whole identity union, honours `?property=` / `?period=` for the sections it publishes, and states its fixed build-time scope without JavaScript. The financing reference already names and verifies its period; the archived lease/MRT/spatial and segment contracts were not touched. The pack's current-window slices are **not** embedded in fieldnotes — that is RF10's per-area work and is recorded in §8.
- **Parent:** [implementation map](../plans/2026-11-12-reporting-refresh-implementation-map.md) §6 · [handoff](../plans/2026-11-12-reporting-refresh-handoffs.md) RF06
- **Decisions:** D08 (financing reference), v1 URL compatibility
- **Upstream:** [RF05](2026-11-13-rf05-current-periods.md) · [RF01](2026-11-12-rf01-leaderboard-report.md)

## 1. Route union and collisions

`loadAreaPages()` builds the static route set from the union of:

- every planning area in any of the 16 joint `map_metrics` sections (the historical identities the page set already covered);
- every area the verified v2 pack publishes, so a current-only identity (Mandai, Sungei Kadut, Central Water Catchment) keeps a route instead of 404-ing.

Two exclusions and one assertion:

- `SG` and the exporter's `NONE` bucket are not planning areas and never become a page (`/areas/none` is a 404).
- Two identities that slug to one path stop the build (`two planning areas share the fieldnote slug …`) rather than silently overwriting a fieldnote. A unit test covers it with `TEST AREA` / `TEST-AREA`.

An area with no historical joint section still gets its page; the page says which combinations are missing instead of the route disappearing.

## 2. Selection honours the query

The headline block moved into one island, `app/src/components/areas/AreaSectionPanel.tsx`:

- **SSR renders the fixed default** (the same preference order as before: 2025 HDB, then 2025 condo/all/EC, then all-history), so a reader without JavaScript sees exactly the numbers, labels and provenance the page shipped with.
- After hydration it reads `?property=` / `?period=` and, when they name a section the fieldnote publishes, swaps **values, label, scope sentence and provenance together**; nothing is updated piecemeal.
- A concrete v2 period id (`ttm_2026_10`) is recognised but **not carried**: the reader gets an explicit notice naming the id, a link to Explore, and the fixed default stays on screen. Nothing is substituted silently (contract §5.3).
- An unknown property/period, or an empty combination, has its own message; a combination with nothing published keeps its "no transactions are published" note instead of a zero.
- The national comparison renders only when the build-time generation verdict says both assets agree — the verdict travels in props, never from the browser (the existing "ignores a client-injected manifest" E2E still passes).
- Changing the selector writes `property`/`period` into the address bar and refreshes the return link, so a chosen section survives a reload and the round trip.

The panel is a client component, so the selection logic had to leave the build-time module. `src/utils/area-page.ts` still owns the Node/`fs` loading and re-exports; the new **`src/utils/area-selection.ts`** holds the vocabulary, the option projection (`areaPageOptions`), the default (`areaPageDefaultOption`) and the resolver (`resolveAreaPageSelection`). It imports only pure, browser-safe modules — a build with `node:*` in the island bundle fails, which is exactly how the first attempt was caught.

## 3. No-JS HTML is honest

- A `<noscript>` block states the fixed build-time scope, names `map_metrics.<section>`, and says a property type or period in the address bar cannot change static figures.
- The availability panel's 16 rows are now real **section links** (`?property=…&period=…`) in the static HTML — useful without JavaScript and directly usable with it.
- The page never claims a query changed static metrics: the selector and the notice are the only things that speak about a selection, and only after hydration.

## 4. One return-link allow-list

- `area-links.ts` owns the allow-list (`AREA_RETURN_PARAMETERS`), the per-key vocabularies and `explorerReturnHref(base, search)`; the period vocabulary now accepts the legacy eras **and** concrete observed-period ids, so an explorer row on a published window round-trips.
- The inline `<script is-inline>` copy in `[slug].astro` is gone: the island points the return link at `explorerReturnHref(...)`, so there is one implementation instead of two that could drift. A unit test asserts the page no longer carries a second `const allowed = [` list.
- Base-prefixed paths are covered by unit tests and by the Pages E2E suite.

## 5. Tool and legacy contracts

- The financing reference was already explicit and verified: `REFERENCE_ERA = "year_2025"`, per-entry `section` identity (`year_2025_hdb`), a versioned reference identity in the URL (`ref`/`rt`/`rv`), and the release generation shown on the tools surface. No code change was needed; the existing unit tests pin the period and the explicit-import rule.
- A price imports only on an explicit reference selection (`ReferencePriceEntry` resolved by the workspace), never on an unrelated rerender; manual price edits stay in memory and out of the URL, storage and logs (`integration.spec.ts` pins that).
- The archived lease/MRT/spatial assets keep `unverified-archive` until an owner lists them in the release manifest; the nine model-layer gates and segment weights are untouched.

## 6. Payload measurement

Per fieldnote page in the built site: **51 KB HTML** total, of which **11.7 KB** is the island's props (16 sections of this area, with national baselines for the comparable ones). No national/monthly payload is embedded, and only the area's own values are serialised.

## 7. Verification

```bash
cd app && bun run test:unit        # 452 pass (30 files; 11 new fieldnote-selection tests)
cd app && bun run astro check      # 0 errors, 0 warnings, 22 hints
cd app && bun run validate-data    # v1 release + v2 pack both verified
cd app && bunx playwright test tests/e2e                          # 223 passed, 12 skipped
cd app && bunx playwright test tests/e2e/areas.spec.ts            # 12 passed (5 new)
cd app && bun run build:pages && bunx playwright test tests/e2e/pages-base.spec.ts  # 9 passed
```

Two stale tests were corrected rather than worked around: `cross-page.spec.ts` still clicked the removed "Live Dashboard" teaser (RF02), and the leaderboard summary assertions now match the established "Showing N areas ranked by …" copy (the singular/plural is handled).

## 8. Not in this slice

| Item                                        | Owner     | Why                                                                                                                                                                            |
| ------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Pack current-window slices on the fieldnote | RF10      | The fieldnote now _reports_ a published window instead of substituting one; embedding per-area rolling-quarter/TTM slices belongs with the area-activity UI, which needs RF09. |
| Editions and archive routes                 | RF07/RF08 | Requires the three recorded sign-offs; no self-approval.                                                                                                                       |
| `PUBLIC_OBSERVED_RELEASE=v2`                | RF05 tail | Now unblocked in the fieldnote/return-link sense — the remaining reason to hold is the v1-period tool reference, which is explicit and labelled.                               |
