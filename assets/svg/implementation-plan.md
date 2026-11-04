# Implementation plan / revision 2

**Status: slices S0–S6 (including S5c) are implemented in the working tree; S7–S10 are not started.** Live status, commands and the slice ledger are in [`docs/implementation/README.md`](../../docs/implementation/README.md); per-slice reports are in the same directory. Nothing is committed. No deployment, model rerun or pipeline refresh is authorized implicitly.

## 1. Decision and scope

Substantially redesign within **Astro + React islands**, retaining static hosting, Bun, Recharts, Leaflet, article content and catalog. A framework rebuild has no verified benefit for the principal problems: mismatched metric scopes, opaque evidence status and fragmented workflows.

Normative design inputs: [asset index](README.md), [audit](audit-review.md), [feature specifications](feature-specifications.md), [interaction contract](interaction-spec.md), [screen/data mapping](screen-data-map.md). These describe 21 proposed SVGs, not existing new functionality.

Implementation outcome: observed transactions are directly comparable; research is discoverable but honestly dated/gated; map, segment, tool, article and catalog journeys survive migration; mobile/keyboard users obtain equivalent information.

### Verified baseline that changes sequencing

- National/Tampines HDB 2025 medians/counts independently reconcile to one local platinum frame. The production cross-file generation identity is still absent.
- Spatial Hotspots tab crashes on `data.clusters.flatMap`; actual asset provides towns[]. Runtime reproduced.
- Research overlay code uses lowercase area key while served geometry uses uppercase; models include uniform default-like values and historical forecasts.
- Current `/dashboard/trends` is Decision Tools, not time-series charts. Price/volume charts are currently in the overview.
- Segment discovery has a real two-to-four comparison set and URL state. Do not replace it with a static card gallery.
- Catalog row count is from a different snapshot than current platinum.
- `cd app && bun run astro check`: **109 errors / 0 warnings / 45 hints / 112 files**. No production code changed in the design phase. Establish attributable test gates rather than reporting this as passed.

## 2. Routing and architecture decisions

| Destination                                    | Decision                                                            | Migration acceptance                                                                                        |
| ---------------------------------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `/`                                            | New editorial annual overview                                       | All three type medians/counts from one overview asset; safe without cross-file compatibility                |
| `/dashboard`                                   | Compatibility entry to Overview                                     | Preserve base path and useful navigation; move old trend capability to a named destination                  |
| `/explore`                                     | One joint-selection React workspace with list/map/table             | Type × period shared across representations; no leaderboard fallback metrics                                |
| `/dashboard/leaderboard`                       | Compatibility wrapper/translation to observed explorer              | Map only understood settings; explicitly notify unsupported legacy metric rather than replacing it silently |
| `/areas/[slug]`                                | New static area route, shared approved adapter                      | Canonical slug map; correct unavailable states; return context preserved                                    |
| `/research/trends`                             | New home for monthly price/volume charts                            | Do not alias this to the existing tools component by name alone                                             |
| `/research/segments` and `/dashboard/segments` | Same segment workspace and state parser under new shell             | Preserve persona/tab/segment/segments/area; add constraint URL state with versioned parsing                 |
| `/research/tools` and `/dashboard/trends`      | Same four-tool workspace                                            | Legacy route stays valid. Isolate broken/unavailable tool, preserve working siblings                        |
| `/research/map` and `/dashboard/map`           | Same legacy research-map workspace, explicitly archived/model-gated | Preserve metric/timeBasis/propertyType/area/layers query; normalize IDs without losing valid state          |
| `/analytics/*` and persona children            | Existing URLs retained                                              | No content-route churn; improve library/article shell and evidence notes                                    |
| `/data`                                        | New methods/source guide                                            | Link to catalog; not a duplicate raw-download endpoint                                                      |
| `/catalog/*`                                   | Existing routes/slug conversion retained                            | Schema, DAG and dependency links remain usable, including external nested IDs                               |

All links and fetches resolve with `import.meta.env.BASE_URL`. Static compatibility must work under root and `/egg-n-bacon-housing/`. Prefer shared rendering/wrappers over server-only redirects or two separate state implementations. Do not embed arbitrary return URLs; serialize validated internal state only.

### Proposed module seams

Exact names may be refined after inspecting current conventions; avoid a second generic framework.

- `app/src/components/shell/`: semantic header/nav/footer, research secondary nav, mobile menu dialog.
- `app/src/components/evidence/`: SourceNote, EvidenceStatus, MetricDefinition, AssetCompatibilityNotice, reusable unavailable/error UI.
- `app/src/utils/observed-data.ts`: section selection, nullable approved fields, canonical area IDs/slugs, national baseline resolution; no DOM or fetch side effects.
- `app/src/utils/evidence-contracts.ts`: minimal runtime validation for consumed fields/provenance, not a broad new registry.
- `app/src/hooks/useExplorerState.ts`: validated query ↔ committed state, mobile draft state kept separate.
- `app/src/components/explorer/`: settings, plot/list, semantic table, lazy map, selected area and pager.
- `app/src/components/research/`: explicit trends, segment and tool shells, using existing domain components where safe.
- Preserve `DATA_URLS`, gzip fetch utility, catalog slug conversion, content collection, inline chart-marker behavior and existing chart mount boundary.

## 3. Data contracts and publication safety

### 3.1 Observed adapter

Approved fields: median price, median PSF, count. Joint section keys come from `map_metrics[era_property]`; national values come from matching `dashboard_overview.stats[era_property]`. Never mix leaderboard property-only and era-only blocks.

Keep period/property/source-section identity with each observation. Missing section, null field and exporter empty-block zero are separate states. Never substitute all-history values. Maintain uppercase canonical planning-area IDs independently from display names/slugs.

Literal era labels: all history; through 2021; 2022 onward through actual coverage; 2025 complete year. Initially retain verified fixed 2025 and current sections. Dynamic newest-year generation is a separate contract migration, not a UI date calculation.

### 3.2 Compatibility manifest

Extend the **existing maintenance exporter**, not Hamilton, with publication metadata for its seven dashboard assets. Suggested new static `data/dashboard-release.json` contract:

- schema/version and generation identity;
- each asset path, content hash, export time, observation range and approved metric scopes;
- source platinum snapshot identities/hashes and period definitions;
- national vs area inclusion/exclusion rules;
- source publication timestamps nullable when not known.

Do not call file mtime or export time source freshness. Do not attach one dashboard generation to unrelated research/catalog assets.

Keep current payload filenames/shapes compatible initially; the new metadata is additive. Stage all seven files and validate contents, then publish a metadata index last. Because fixed paths can still produce mixed reads during replacement, clients/build loaders must check expected hashes (or use immutable generation-addressed paths if later approved). An index-last swap alone is **not** a transaction guarantee.

For initial release, compatibility can be checked server-side during static build and conveyed through validated props, with a browser validation path for independently fetched assets. Cache keys must include release identity/hash. A mixed or unverifiable pair withholds national difference/reference, while preserving area-owned data. Overview comparisons within one asset remain usable.

Research/catalog need independent evidence records and validity status; no current owner/generator is assumed. Record `unverified-archive` until reproducibility and units are established.

### 3.3 Financial/model separation

Financing uses ordinary amortization plus explicit hypothetical inputs. It is not an eligibility engine, predictive income model or loan recommendation. Income stays local and is excluded from URLs/telemetry by default. No CPF/MSR/TDSR decision or “safe” borrowing category is inferred.

MRT/lease/spatial/forecast results must not become current analytical overlays just because the component now renders. Preserve archive inspection and inputs; gate unsupported numeric recommendations until their definition/model work is approved.

## 4. Implementation slices, file ownership and acceptance

Assign exclusive ownership per slice. A coordinator integrates shared files (`Layout.astro`, route wrappers, DATA_URLS, contracts, package scripts and tests) serially; do not let parallel agents edit them independently.

### S0 — Reproduce baseline and inventory route/state contracts

**Owner:** integration/test investigator. **Depends:** none. **Production edits:** none except approved focused tests in a subsequent implementation branch.

Inspect `app/src/pages`, `constants/dashboard-nav.ts`, `Sidebar.astro`, PriceMap, SegmentsDashboard, InteractiveToolsPanel, useLeaderboardData/useGzipJson, public manifest/assets, export tests and E2E suite. Read AGENTS and skills before any Python/persistence edit.

Deliver a baseline report: exact current revision/data hashes, type-check diagnostics grouped by file, route/query inventory, working and failing tool cases, root/Pages behavior, data sizes. Do not regenerate data. Reproduce PriceMap.tsx:156–220 initial URL serialization-before-hydration: incoming metric/timeBasis/propertyType/area can be overwritten with defaults before parsing.

**Exit:** reproduce joint-filter precedence, hotspot crash, overlay key issue; record pre-existing failures; map every existing workflow to a retained/new route.

### S1 — Runtime evidence boundary and focused regression tests

**Owner:** frontend data adapter. **Depends:** S0. **Likely files:** new observed/evidence utils; `types/leaderboard.ts`, `constants/data-urls.ts` only through coordinator; tests near chosen frontend test conventions.

Fix URL initialization before serialization: parse the entire legacy map selection once before any replaceState effect; retain valid layer IDs, and handle popstate/back/forward deliberately. Add a first-load test covering all five legacy parameter groups.

Implement pure joint-subset adapter with null/empty handling and source labels. Add geometry key normalization and runtime guards for tool/research inputs. Add a per-tool error boundary/unavailable panel so one invalid asset cannot unmount the whole workspace. Do not manufacture clusters or forecasts to satisfy a TypeScript cast.

Refactor `useGzipJson.ts` explicitly: foreground retry vs forced background refresh; preserve previous data on refresh failure; bypass fresh cache when checking the asset; abort superseded requests; include generation identity in cache keys. Ensure old callers preserve behavior until migrated.

**Tests:** missing section never falls back; EC area absent remains unavailable; national median is not mean of area medians; stale retry preserves data; forced refresh performs fetch; initial failure has no zero-valued market; broken spatial tool is contained.

**Exit:** exact known source values render with evidence identity and predictable unavailable states. No new type errors in touched modules; baseline-wide debt reported separately.

### S2 — Dashboard publication compatibility metadata

**Owner:** Python/export boundary. **Depends:** S0; coordinates contract with S1. **Likely files:** `scripts/export_app_data.py`, `tests/test_export_app_data.py`, `app/public/data/manifest.json` contract, `app/scripts/validate-data.mjs`, provenance docs; coordinator owns final shared integration.

Read both repository skill checklists when the work touches ingestion/DAG/persistence; this slice should not require modifying Hamilton. Keep supported CLI, export workflow and existing seven-file ownership. Add source identities, asset hashes, generation and approved scopes; test staged failure and mixed-release behavior in temporary directories. Repair missing provenance pointer.

**Tests:** metadata matches content; failed stage leaves old published release intact to the extent guaranteed; fixed-path mixed pair is detected; independent research/catalog timestamps remain unknown/separate; completed-month/year tests retained.

**Exit:** production cross-file comparisons have an enforceable proof, not timestamp text. If S2 is deferred, release S1/S3+ with national baselines withheld outside a single compatible asset.

### S3 — Tokens, semantic shell and route-compatible research navigation

**Owner:** UI shell. **Depends:** S0; can run parallel to S1/S2 with exclusive ownership. **Files:** `styles/globals.css`, `layouts/Layout.astro`, Sidebar replacement/wrapper, new shell components, route-level integration by coordinator.

Implement Fieldnotes tokens, local font stacks, contrast/focus boundaries, primary nav plus explicit research subnav. Mobile menu must trap/restore focus, close on Escape and expose all destinations. Preserve dark mode only if independently tokenized/verified; otherwise keep current dark behavior isolated until supported, rather than claiming light SVGs validate it.

**Exit:** keyboard navigation, aria-current, skip link, one H1, 320/390/768/1440 widths and 200% text reflow; root/base-path links work; no dropped article/catalog/persona path.

### S4 — Overview and explicit time-series destination

**Owner:** editorial/trends. **Depends:** S1+S3. **Files:** `pages/index.astro`, compatibility `pages/dashboard/index.astro`, new `pages/research/trends.astro`, existing PriceTrendsChart/TransactionVolumeChart adaptations and new reading/source components.

Build SVGs01/04 and10/16 with actual data; retain complete monthly table. Type/range selection does not imply coverage before a series starts. Exact calendar-lag comparisons only; no mislabeled average or all-history “today” summary. Overview exposes segments/tools/trends paths explicitly.

**Exit:** 78,796 2025 total and three type medians/counts correct; monthly 2025 HDB count sums25,084; Dec price635,000/count2,024; null gaps retained; volume axis starts0; zoomed price axis disclosed; legacy tools route unchanged.

### S5 — Joint explorer, responsive controls and observed map

**Owner:** explorer. **Depends:** S1+S3; S2 needed only to enable compatible baseline. **Files:** new explore route/workspace; safe reuse of table/map primitives; `pages/dashboard/leaderboard.astro` compatibility coordinated separately.

Build SVGs02/05/09. Shared committed settings, filter sheet draft/apply/cancel, sort/search, selected-area state, pagination and actual geometry. Desktop12 rows, mobile4; preserve first-visible area anchor on viewport changes. Plot/map/table must consume one derived dataset. Lazy map; geometry-only mode and accessible table stay useful when tiles fail.

**Exit:** 31 2025 HDB areas, 25 above threshold,6 thin; Ang Mo Kio499,000/971, Marine Parade539,750/162, Tampines710,000/1,921; shared bins/scales; correct null/excluded distinctions; URL round trip, back/forward, direct deep links; no overlay state erased by treating legacy map as this new map.

### S6 — Area fieldnote and incompatible-generation UI

**Owner:** detail/evidence. **Depends:** S1+S3+S5; S2 for enabled comparison. **Files:** new static `pages/areas/[slug].astro`, shared adapter/source components.

Build SVG03/06. Canonical slug lookup; query-selected type/period; direct-route fallback return; independently computed price/PSF medians. With matching publication, show S$82,000 /13.1% level difference and the two-record Sungei Kadut national/map inclusion difference. Without matching publication, omit baseline and difference and explain.

**Exit:** correct values and inclusion notes, no “premium/growth” claim; compatible/incompatible/unknown/empty paths tested; return state preserved; no raw addresses or valuation promise.

### S7 — Segment discovery, investigation and comparison migration

**Owner:** segment workflow. **Depends:** S1+S3. **Files:** existing segment components, `useFilterState.ts`, `useSegmentMatching.ts`, `buildSegmentAreaRows.ts`, new research alias and legacy route wrapper via coordinator.

Implement SVG11/12/20 visual structure without rewriting scoring silently. Expose weighted-fit explanation and source status. Preserve existing two/four shortlist semantics, selected segment/area and URL IDs. Extend serialization of visible constraints deliberately. Compare archived stored averages, not new annual medians. Gates prevent unverified research growth/yield/forecast recommendations.

**Exit:** all six segments discoverable; each investigation links only declared areas; Bishan644 storedPSF context explicit; selected segment independent from comparison set; min2/max4, remove/replace/fifth-limit/unknown-ID/no-result paths and keyboard behavior tested; no summed overlapping cohort claim.

### S8 — Four-tool workspace with safe output states

**Owner:** tools. **Depends:** S1+S3; chosen observed reference via S5/S6. **Files:** InteractiveToolsPanel and four tool components, new research tools alias, legacy `dashboard/trends` wrapper.

Build SVG13/18/19. Financing gets explicit hypothetical assumptions and standard amortization including zero-interest branch; reference price import is named and source-bound. Keep inputs local. Lease retains dated lookup with signed values, endpoint policy surfaced for approval. MRT output gate exposes units/direction/cap issues. Spatial uses schema-checked label inspection/unavailable state until a valid model contract exists. Tool-specific failures remain contained.

**Exit:** example497,000 principal/25yr/3%=2356.830…; rounding2357, payment/income23.6%, ratio5.92; rate sensitivity values match specification; invalid/blank/zero-income inputs withhold outputs; no loan-approval advice, undefined-period compounding or hidden floor-area scaling.

**Separate approval required:** regenerating lease/MRT/spatial models, setting new financial eligibility policies, or promoting recommendations. A UI implementer cannot invent these fixes.

### S9 — Research-map archive, studies and catalog detail

**Owner:** research publishing (split into parallel subowners only with disjoint components). **Depends:** S1+S3; retain legacy workspaces until replacement tested.

Map: SVG17; normalize geometry, preserve nine layer IDs/query, per-layer source/status and selected area; historical forecasts never relabeled current; choose one active polygon fill when quantities compete. Archived fields inspectable; analytical fill remains gated.

Studies: SVG14; retain content/math/TOC/chart-marker processing, add library search/category/persona filters and evidence notes. Correct duplicate H1 rendering; remove undefined11Years KPI. Do not chart lease PSM as PSF until source repair approved.

Catalog: SVG15; preserve existing IDs/slugs/schema/DAG/dependency links; source-label artifact counts and requiredness vs observed nullness. Display discrepancy rather than replacing catalog metadata with unrelated current count.

**Exit:** all article/persona/catalog links and exact map query IDs survive; invalid layer/source failure isolated; required chart markers remain opt-in; schema search and dependency links keyboard usable; differing vintages visible.

### S10 — Integration, regression and release readiness

**Owner:** integration/test coordinator. **Depends:** all shipping slices. Complete only after approval of preceding changes.

Run production build/static preview and E2E at root and Pages base. Add route/query compatibility, keyboard/dialog, no-results/error, model-gate, source-compatibility and mobile tests. Include the Spatial Hotspots tab explicitly. Test network failure with data already displayed, fresh-cache revalidation and mixed-generation assets. Validate hashes/schema/units and exclude sensitive user input from telemetry.

Run relevant Python focused exporter tests and Ruff/type checks only if those files change, following skills. Run frontend type-check and distinguish old baseline diagnostics from touched-file failures; target full recovery where feasible without unrelated refactoring. Do not weaken existing smoke assertions merely to rename a button.

**Exit:** no new attributable failures, all critical data/runtime defects in shipping paths fixed or explicitly gated, no lost capability/URL, accessible/mobile journeys verified, measured payload/hydration costs recorded. Remaining global debt has an explicit owner; no unverified “all checks pass” claim.

## 5. Dependencies and parallelism

`S0 → {S1, S2, S3}; {S1,S3} → {S4,S5,S7,S8,S9}; S5 → S6; S2 → enable cross-file baselines; all shipping work → S10`.

Parallel owners must not edit shared route/navigation/contracts at once. Use an integration queue or separate worktrees and focused patches; never reset/stash another owner's work. No commits unless explicitly requested. Prefer incremental capability slices over a big-bang app replacement.

## 6. Decision register / safe defaults

| Decision            | Safe default now                                                        | Requires owner confirmation before expansion                                   |
| ------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Complete year       | Fixed verified2025                                                      | Source-specific completeness rules and dynamic periods                         |
| Comparison identity | Withhold incompatible baseline                                          | Additive publication manifest or immutable-generation strategy                 |
| 150-sale rule       | Explicit proposed selected-subset caution, user can reveal thin samples | Product validation; not a confidence threshold                                 |
| Research numerics   | Archive inspection, no current recommendation/fill                      | Reproducible model/generator, units and approved validity status               |
| Lease bins          | Preserve archival first-match with warning until repaired               | Half-open canonical bands and reconciled insights                              |
| MRT units/direction | Withhold total-dollar estimate                                          | Coefficients, baseline, distance cap and area scaling                          |
| Financial scenario  | Deterministic arithmetic, no approval classifications                   | Financial/regulatory advice or policy claims                                   |
| Geography           | Planning areas for observed comparison                                  | Validated market-segment taxonomy; never equate CCR with administrative region |
| Catalog             | Keep source-snapshot metadata and flag discrepancy                      | Approved refresh/release workflow                                              |
| Dark mode           | No claim of validation from light specs                                 | Separate accessible palette/chart test matrix                                  |

## 7. Immediate starting point

Start **S0**, then implement the **S1 data/runtime seam before visual migration**. The existing hotspot crash and mixed-scope adapter are concrete blockers; a polished shell must not amplify them. S3 can proceed independently once route ownership is reserved. Do not begin by replacing every dashboard or introducing a new framework.

The user has authorized audit improvements and proceeding to this planning step. Review/approve this production plan before implementing it; no production application changes were made while drafting it.
