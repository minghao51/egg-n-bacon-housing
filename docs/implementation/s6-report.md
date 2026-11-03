# S6 implementation report — area fieldnote route

`/areas/[slug]` renders one static page per published planning area from the same joint-section adapter as `/explore`, with a build-time generation gate in front of every cross-asset number. **No commit**; no published asset modified.

## 1. What shipped

- `app/src/utils/area-page.ts` (build-time only, Node built-ins) — loads `map_metrics` + `dashboard_overview`, derives the union of areas across **all 16 joint sections**, produces one page record per area with every combination's availability, and returns a baseline verdict by verifying the release manifest against the seven published files (`sha256`, `bytes`, `contentSha256`, generation, and a required-asset list so a manifest cannot pass by listing nothing).
- `app/src/utils/area-links.ts` — client-safe `areaHref()` and the single source of truth for the return-link keys; `area-page.ts` re-exports it, so no Node import reaches a React island.
- `app/src/pages/areas/[slug].astro` — static fieldnote: headline median/PSF/count for the area's anchor section, a national row **only** when the build-time verdict is `verified`, the unrounded difference and one-decimal percentage, an availability panel over the whole joint matrix, a "what this doesn't say" panel, source & method, and an inline return-link enhancer that echoes only allow-listed keys **and values**.
- `ExplorerList` rows now link to their fieldnote, preserving the selected property and period; the base path is applied for Pages deployments.

## 2. Verification

| Check | Result |
|---|---|
| `bun run test:unit` | **141 pass** (15 area-page tests + return-link contract test) |
| `bun run astro check` | **36 errors / 0 warnings / 43 hints / 141 files** — unchanged; none in the new files |
| `bun run build` | passes; **41** area pages generated (all areas published in any joint section, not just the 31 with 2025 HDB) |
| Playwright | **118 pass** (5 area tests added) |
| `/areas/tampines` | S$710,000 · S$620 psf · 1,921; `map_metrics.year_2025_hdb`; national withheld with `status: absent`; no `628,000`, no `82,000`, no `S$0` |
| `/areas/bedok` | 2025 EC row says "Not published — no transactions published in this joint section"; no zero |
| `/areas/lim-chu-kang` | anchored on `whole_hdb` (no 2025 block) and the headline says "HDB resale · All history", not "Jan–Dec 2025" |
| `/areas/newton`, `/areas/river-valley` | 200 — the areas that only appear for condominiums now have pages |
| Mobile | 390px, no horizontal overflow; the table becomes a stacked definition list below `sm` |
| Compatible path | proven with a throwaway copy of the app and a manifest computed from the real asset bytes: the built page renders `S$628,000`, `S$82,000`, `13.1%` and "verified at build time" |
| Client-injected manifest | the static page still withholds, because the verdict is build-time; asserted in `areas.spec.ts` |

## 3. Review-driven corrections

- **Dead links (blocker):** page set was 33, so condo-only areas (Newton, Orchard, River Valley, Marina South, Museum, Seletar, Singapore River, Southern Islands) were linked from `/explore` but had no page. Page set is now the union of all joint sections (**41**), and each page anchors on the first published combination for that area.
- **Weak verification:** a manifest with an empty or partial asset list could have passed; the build check now requires all seven published files.
- **Copy accuracy:** the headline scope, table scope and method sentence were hardcoded to "Jan–Dec 2025"; they now derive from the section actually read.
- **Difference copy:** equal medians no longer render "S$0 level".
- **Robustness:** a manifest entry pointing at a directory or unreadable file reports `unverified`/`mismatch` instead of throwing.
- **Return link:** keys *and* values are allow-listed; the Astro list is pinned to `AREA_RETURN_PARAMETERS` by a test.

## 4. Gaps

- The national comparison is never interactive on this page: it is decided at build time, so a deployment that publishes assets without re-running the exporter keeps the withheld state. That is intentional honesty, not a live check.
- No bar comparison chart (SVG03's S$0–1m axis), no "change property type" control (SVG06 state 03), and no scroll-position restoration on return.
- The trailing difference note does not repeat the Sungei Kadut inclusion count; the source block names the sections and the national-vs-area rule is documented in `app/public/data/README.md`.
- `baselineStatus` is shown as a short status word; the full mismatch list is not surfaced on the page.

## 5. Next

**S4** (overview + explicit trends destination) or the **map** remainder of S5. S4 should reuse `areaHref`/`release-manifest` rather than introducing a second evidence path.
