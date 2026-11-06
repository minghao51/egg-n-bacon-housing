# S7 implementation report — segment discovery, investigation, comparison

`/research/segments` is the research destination for the six stored segment archetypes; `/dashboard/segments` stays as a compatibility wrapper over the same island. The archive is now labelled as an archive everywhere it is read, and the cross-asset boundary (it is **not** in `dashboard-release.json`) is enforced by a test rather than a comment. **No commit**; no published asset modified; no scoring change.

## 1. What shipped

**New route + wrapper**

- `app/src/pages/research/segments.astro` — Fieldnotes shell, one `h1`, the observation-period disclaimer, a JS-off block and the asset name.
- `app/src/pages/dashboard/segments.astro` — three-line wrapper over the shared shell with an explicit compatibility note. Every pre-S7 query ID still works (`persona`, `tab`, `segment`, `segments`, `area`).
- `app/src/components/segments/SegmentsSurface.astro` — the shared shell: resolves `BASE_URL` and the archive URL once (Astro side) and owns the Leaflet stylesheet import, so the island carries no `import.meta` usage.
- `app/src/constants/dashboard-nav.ts` — the `segments` nav item now points at `research/segments` (matching the S4 trends pattern); the legacy route stays reachable and keeps `?area=` handoffs from `/dashboard/map` and `/dashboard/leaderboard` working.

**Pure modules (unit-tested)**

- `lib/segment-url-state.ts` — parse/serialise for the five legacy IDs plus versioned constraints (`fv=1&psf=&types=&regions=&hotspot=`). Unknown IDs, malformed values and stale keys are handled explicitly; `applySegmentQuery` deletes only keys this workspace owns.
- `lib/segment-evidence.ts` — the single evidence contract: asset filename, status (`unverified-archive` vs `share-verified-generation`), per-field `stored-average` / `definition-unverified` status, caveats, formatters, and the two shared notes. `formatSegmentMetric` returns `N/A`, never `0`, for a missing value.
- `lib/segment-presets.ts` — `INITIAL_FILTERS` / `PERSONA_PRESETS` / `filtersDifferFromPreset`, moved out of the hook so the URL parser and the hook share one definition. Values unchanged.
- `hooks/useSegmentMatching.ts` — weights and rule notes exported (`SEGMENT_MATCH_WEIGHTS`, `SEGMENT_MATCH_RULE_NOTES`) and used by the scoring itself, so the UI explains the real numbers instead of restating them. **Scoring is unchanged** (30/25/20/15/10, hard spatial filter, percentage rounding).

**Workspace**

- `SegmentsDashboard.tsx` — state is now IDs, not stale segment objects; the address bar is read **once before the first commit** (the island is `client:only`) and written back only after the archive loads, which fixes the pre-existing cold-deep-link bug where the defaults erased `tab`/`segment`/`segments`/`area` before the data arrived.
- Discover — `SegmentCard` shows stored average PSF, declared cohort size and property types, with "weighted fit, not a return probability"; the compare button is `aria-pressed` and disabled (with an explanation) at 4/4. `InsightCard` is labelled "Archive note · model definition not verified" and links through the base path.
- Investigate — the lens lists stored PSF plus gated fields marked `†`; selecting a gated field surfaces its caveat (`SEGMENT_GATED_NOTE`) instead of presenting it as current. The table shows area / market segment / stored PSF (plus the selected field) and states "Showing N of M" against the declared cohort. The area panel shows the stored PSF (Bishan `S$644`), the stored confidence label, the missing sample/period, and an explicit "Open observed comparison →" link that says it does **not** reinterpret the stored value as a 2025 median.
- Compare — a stored-field table (average PSF, linked areas, property types, reported cohort count, observation period "Not supplied", stored risk/volatility), an overlap/non-additivity note, per-segment remove buttons, an in-tab add control, and explicit 2-minimum / 4-maximum copy. No "best value" highlighting.
- Filter panel — "Price PSF range" (not budget), no unverified model claims (the old "15x MRT sensitive", "$5/100m" and "58–62% persistence" copy is gone), and an "Explain match calculation" disclosure driven by the exported weights.

**One adjacent change (disclosed).** `MarketOverviewDashboard.tsx` now receives its base path as a `baseUrl` prop from `pages/dashboard/index.astro` instead of reading `import.meta.env` itself. This is behaviour-preserving (the value is identical), it is covered by the 26 existing dashboard-overview/cross-page tests, and it was the last file in the workspace still tripping the tooling note in §6. Revert it if the coordinator prefers the original.

**Removed deliberately** (`lib/segment-evidence.ts` rationale): `compare/ComparisonCharts.tsx` (bar chart of yield/YoY — both gated fields), `compare/InvestmentImplications.tsx` (stored "target 5.5% yield" advice), and the metrics guide's invented formulas. The replacement guide states field status and the real scoring rules only.

## 2. Evidence boundary

`app/public/data/dashboard-release.json` lists seven dashboard assets; `segments_enhanced.json.gz` is not one of them. `tests/unit/segment-evidence.test.ts` reads the **published** manifest and asserts the archive is absent, that its status is `unverified-archive`, and that adding it to the manifest would flip the status (so a future cross-asset comparison has to be a deliberate, test-visible decision). The UI therefore never compares archive numbers with dashboard medians; the only bridge is an explicit navigation link.

## 3. Verification

| Check                                                     | Result                                                                                                                                                                                   |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bun run test:unit`                                       | **233 pass, 0 fail** (32 new: URL contract 18, evidence boundary 10, row builder 6 — baseline was 201)                                                                                   |
| `bun run astro check`                                     | **26 errors / 0 warnings / 35 hints / 158 files** — errors unchanged from the baseline and none in a segment file; hints dropped 41 → 35 (two deleted chart components, one unused type) |
| `bun run validate-data`                                   | passes: 19 assets, release `0e1013ee485f` (7 assets)                                                                                                                                     |
| `bun run build`                                           | passes: **199 pages**, including `/research/segments` and `/dashboard/segments`; `catalog.jsonl.gz` restored afterwards                                                                  |
| Playwright (preview, full suite)                          | **151 pass, 0 fail** (15 new: 11 research + 4 wrapper; baseline was 136)                                                                                                                 |
| `uv run pytest tests/test_export_app_data.py --no-cov -q` | **44 pass** (no exporter change)                                                                                                                                                         |
| `uv run ruff check` / `ruff format --check`               | clean / 2 files already formatted                                                                                                                                                        |
| `git status` after build                                  | no published asset modified; `bun.lock` unchanged; `app/public/data/catalog.jsonl.gz` restored                                                                                           |

Behaviour proven in the browser: cold deep link `?persona=investor&tab=investigate&segment=large_size_stable&segments=…&area=bishan` keeps all five IDs and re-serialises the area as `BISHAN`; unknown IDs are dropped without breaking the tab; 4/4 is explained and a removal re-opens a slot; one segment explains the two-segment minimum; Bishan shows `S$644`, "stored confidence label 99%", the missing sample/period and a `/explore?area=BISHAN` handoff; constraint changes round-trip through `fv=1` and survive a reload; the nav link points at `/research/segments` with `aria-current="page"`; no console or page errors on either route; 390px has no horizontal overflow.

## 4. Gaps deliberately left open

- **No pagination** on the investigation table: all declared rows that fit the constraints are listed ("Showing N of M") rather than the design's five-at-a-time pager. Paging needs a viewport-aware page size and anchor preservation.
- **Map** keeps all archive rows and colours by the selected stored field; it is labelled as archive fill, not observed transactions. No new geometry work.
- **Compare** no longer charts anything; the stored-field table replaced the yield/growth bars so a gated field cannot be read as a ranking.
- **Constraints URL state is additive-only**: `investmentGoal` and `timeHorizon` are not exposed by the filter panel, so they are never serialised (they follow the persona preset).
- **`details/` components** (`DetailsTab`, `SegmentOverview`, `RiskFactors`, `GeographicDistribution`) remain unreferenced pre-existing files; they were left untouched rather than deleted in this slice.
- **Segment scoring, cohort counts and confidence labels are unchanged** — changing them stays in the decision register.

## 5. Next

**S8** (four-tool workspace) is next per the plan; it depends on the same query-state pattern (`parse before serialise`, versioned constraints) and on the containment boundary S1 shipped. S8 must still withhold MRT totals and keep the lease endpoint policy explicit; model regeneration remains unauthorised.

## 6. Environment note (not an S7 change)

`pi-lens`'s `typescript` server starts without a resolvable project in this checkout: it reports 0 tsconfig files, so `import.meta.env` and `clsx` default-import errors appear on **unmodified** files (for example `MarketOverviewDashboard.tsx:198`, `PriceMap.tsx`) that `bun run astro check` accepts. Evidence: `bunx tsc -p tsconfig.json --noEmit` reports 0 `import.meta` errors project-wide, and the same 2 errors show up on every pre-existing file using `import.meta.env`. Restarting the session after `bun install` populates `app/node_modules` clears it. The S7 files avoid the pattern anyway (base path is passed from the Astro shell), so the slice itself is clean under either checker.
