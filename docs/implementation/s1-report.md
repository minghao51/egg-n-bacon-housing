# S1 implementation report — runtime evidence boundary

Branch `design/sol-editorial-spec`, base commit `a881ec0fa3f018db220b791d59e76a8edaa526e2`. S1 is implemented; **no commit was made** and no production data was regenerated. The design assets in `assets/` and the baseline in [s0-baseline.md](s0-baseline.md) remain the normative inputs.

## 1. What now behaves differently

| Defect (from [s0-baseline.md](s0-baseline.md) §4) | Before | After |
|---|---|---|
| 4.1 Legacy map deep link | First commit rewrote the query with defaults; `area`/`layers` lost, `metric`/`timeBasis`/`propertyType` reset | Parsed once from `window.location.search` during render; writer is a no-op when the URL already matches; `popstate` re-applies the URL |
| 4.1 `layers` support | Never parsed | Validates against real `LAYER_METADATA` ids, drops unknown/duplicate ids, preserves order |
| 4.2 Spatial Hotspots | `data.clusters.flatMap` threw and unmounted the whole tools workspace | Reads the published `towns`/`town_clusters`/`cluster_descriptions`/`portfolio_allocation`; absent cluster aggregates render an explicit unavailable state; a per-tool error boundary contains any tool failure |
| 4.3 Overlay keys | Overlays read lowercase `pln_area_n` only; every feature silently fell back to "no record" | `planningAreaName()` resolves `PLN_AREA_N`/`pln_area_n`; browser check now paints 41 analytic fills + 14 no-record fills instead of 55 no-record fills |
| 4.4 Joint metric scope | Leaderboard-style resolution mixes property-only and period-only blocks | New pure adapter resolves joint `era_property` sections or returns `null`; no fallback to `whole`, `hdb` or `recent` keys (**not yet consumed by UI — see §5**) |
| 4.5 Fetch lifecycle | Retry could serve stale cache; foreground failure blanked the page; superseded request cleared the newest loading state; cache key had no generation | Pure intent model (`initial`/`retry`/`refresh`), retry always bypasses cache, refresh preserves displayed data, request tokens make superseded results inert, generation-aware cache keys available via `setDataGeneration()` |
| 4.6 Missing→zero rendering | `(x * 100).toFixed(1) || "N/A"` rendered `0.0%` for null; `|| -20`/`|| -5` invented sensitivity; `|| 5` invented school/amenity scores; `|| 0` rendered `S$0` | `formatNumber`/`formatPercent` return `"N/A"` for null/undefined/NaN while keeping a real `0`; color scales receive nullable values and paint the documented no-record grey |

## 2. Files

New frontend modules (all pure, no DOM at module scope, no new dependencies):

- `app/src/utils/observed-data.ts` — era/property section keys, canonical area ids/slugs, area + national observation readers with `available`/`missing`/`empty` status, baseline comparison.
- `app/src/utils/request-state.ts` — load-intent table, cache freshness, generation-aware cache keys, request tokens.
- `app/src/utils/map-url-state.ts` — legacy map parse/serialize/merge/equality.
- `app/src/utils/geometry.ts` — planning-area name normalisation.
- `app/src/utils/format.ts` — null-safe number/percent formatting.
- `app/src/types/spatial-hotspots.ts` — the real published hotspot asset shape.

Changed: `app/src/hooks/useGzipJson.ts`, `app/src/components/dashboard/PriceMap.tsx` (URL/state only), `app/src/components/dashboard/tools/SpatialHotspotExplorer.tsx`, `app/src/components/dashboard/InteractiveToolsPanel.tsx`, the three `map/overlays/*.tsx`, `app/src/utils/colorScales.ts` (nullable signatures only), `app/package.json` (adds `test:unit`).

Tests: `app/tests/unit/{observed-data,request-state,map-url-state,geometry,format}.test.ts`, `app/tests/unit/bun-test.d.ts` (ambient `bun:test` types, because no test-type dependency exists and adding one is out of scope), `app/tests/e2e/s1-evidence-boundary.spec.ts`.

Docs: [s0-baseline.md](s0-baseline.md), this report.

## 3. Verification

| Check | Result |
|---|---|
| `cd app && bun run astro check` | **36 errors / 0 warnings / 43 hints / 125 files**. Baseline was 109/0/45/112. Net −73, **no new diagnostic inside a changed file**; remaining errors are the recorded pre-existing Leaflet `PathOptions`, `.astro` implicit-`any` and persona-index debt. |
| `cd app && bun run test:unit` | **74 pass / 0 fail / 605 assertions** across 5 files. |
| `cd app && bunx playwright test` (clean dev server) | **103 pass / 0 fail**. |
| `cd app && bun run validate-data` | passed, 19 assets (unchanged). |
| Runtime deep link | `?metric=median_psf&timeBasis=year_2025&propertyType=hdb&area=TAMPINES&layers=spatial.lisa` survives hydration and is applied to the controls (asserted in the e2e spec). |
| Runtime overlay | 55 base polygons + 55 overlay polygons; fills `#fee090`×41, `#cccccc`×14 — proves geometry keys now join. |
| Runtime hotspot tool | 40 towns + "All Towns" in the town selector, published count line `4 cluster types across 40 published town records`, no page error, no alert. |
| Regression suite | Full Playwright suite green after restarting the dev server; an earlier run with 16 failures was traced to Vite dev-server module-fetch errors (`Failed to fetch dynamically imported module …`) while the server recompiled, not to app logic. |

An independent read-only review confirmed: joint-section-only resolution, `0` vs `empty` separation, national baseline read from the overview block (not averaged), cache/abort semantics, URL ordering, overlay key coverage, published-asset hotspot shape, and that the new e2e assertions fail if the corresponding fix is reverted.

## 4. Deliberate non-goals

- No data regeneration, no new publication metadata (S2), no pipeline/Hamilton change, no dependency or lockfile change.
- No visual restyle, no route renames, no replacement of the leaderboard table or map rendering (S3–S9).
- The 150-sale caution rule, era labels and evidence surfaces are specified in the design docs but are not wired into UI yet.
- `formatNumber`/`formatPercent` were applied where a null could have become `0`; the remaining `x?.toFixed(n) || "N/A"` sites were left as-is because `toFixed` never returns a falsy string, so `0` renders as `0.0` and `null` as `N/A`. They are a consistency follow-up, not a data-honesty bug.

## 5. Open items handed to later slices

1. **Observed adapter is not yet consumed (S4/S5/S6).** `observed-data.ts` is tested but unused in production, so the S1 exit line "known source values render with evidence identity" is met only for the defects that were fixed in place (map URL, overlays, hotspot tool). Wiring it into the explorer, area page and overview is the first task of S4–S6; until then the leaderboard still resolves the old mixed blocks and must not be presented as joint evidence.
2. **Generation identity is inert (S2).** `setDataGeneration()` exists and cache keys include a generation, but nothing sets it because publication metadata does not exist yet. Cross-file baselines must stay withheld until S2 lands.
3. **Failed revalidation is silent by design (S3/S4).** A refresh failure with displayed data preserves data and surfaces nothing; the UI needs a stale/retry affordance before this counts as "failures visible".
4. **Invalid `layers` values are ignored but not removed from the URL.** Harmless (`?layers=bogus` parses to none), unlike the previous loss of valid state; normalising it is cosmetic.
5. **Test infrastructure.** `tests/unit/bun-test.d.ts` is a hand-written ambient module; replacing it with `bun-types` requires a dependency change and approval. Unit tests are logic-level only — hook effect ordering is covered by the e2e spec, not by a DOM harness.

## 6. Recommended next slice

**S2 (publication compatibility metadata)** unblocks every cross-file number, and **S3 (shell/tokens)** can run in parallel with disjoint ownership. S4/S5/S6 must not enable national baselines or the observed explorer before S2's compatibility check exists.
