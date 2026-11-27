Agent: fd3fdd08-2953-442
Type: Agent | Status: steered (wrapped up at the turn limit — output may be partial) | Tool uses: 89 | 164.2k token | Context: 30% | Duration: 200.7s
Model: openai-codex/gpt-6.1-sol, thinking: high
Description: Discover frontend contracts and tests

# Phase 1 discovery — frontend and documentation

**Revision:** `449b921d499a8c55ec1eacb1a423baa7632456d3`; working tree was clean. Read-only inspection: no edits, installs, builds, tests, browser activity, secret-file reads or delegation.

**Completion:** partial discovery, stopped at the turn limit. Route shells and shared loading infrastructure received the strongest inspection. Many component implementations and all test bodies remain unread. No findings or severity assessments are assigned.

## 1. Measured inventory

Tracked-file enumeration measured:

| Scope                                                                  |  Count |
| ---------------------------------------------------------------------- | -----: |
| `app/src/` files, including JSON/CSS                                   |    156 |
| Astro route source files                                               |     19 |
| Unit-test files matching `*.test.ts`                                   |     34 |
| E2E spec files                                                         |     24 |
| `app/public/data/` tracked files                                       |     86 |
| Lines across `app/src`, `app/tests`, `app/scripts`, including fixtures | 57,483 |

These are source inventory counts, **not executed-test counts or generated-route counts**.

### Astro routes

| Surface             | Route source inventory                                          | Main browser interface                                                                   |
| ------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Entry               | `/`                                                             | Static published statistics, navigation cards, animated counter                          |
| Observed comparison | `/explore`                                                      | Property/period/metric selection; list/map/table; search, threshold and pagination state |
| Overview            | `/dashboard`                                                    | SSR data passed to hydrated overview                                                     |
| Rankings            | `/dashboard/leaderboard`                                        | SSR initial leaderboard plus browser fetching                                            |
| Research            | `/research/{trends,map,segments,tools}`                         | Monthly trends, research map, segment workspace, four-tool workspace                     |
| Compatibility       | `/dashboard/{map,segments,trends}`                              | Shared research surfaces; `trends` means decision tools                                  |
| Studies             | `/analytics`, `/analytics/[slug]`                               | Searchable library; markdown article, evidence/edition panels, optional charts           |
| Editions            | `/analytics/archive/[year]/[edition]/[slug]`                    | Registered frozen markdown editions                                                      |
| Personas            | `/analytics/personas/[persona]`                                 | Three static personas; filtered article recommendations                                  |
| Catalog             | `/catalog`, `/catalog/[layer]`, `/catalog/[layer]/[...dataset]` | Lineage graph, searchable dataset tables, schema inspection                              |
| Area fieldnotes     | `/areas/[slug]`                                                 | Static area figures, hydrated section selection, on-demand monthly history               |

Evidence: `app/src/pages/index.astro:1`, `app/src/pages/explore.astro:1`, `app/src/pages/dashboard/index.astro:1`, `app/src/pages/dashboard/leaderboard.astro:1`, `app/src/pages/analytics/[slug].astro:14`, `app/src/pages/analytics/archive/[year]/[edition]/[slug].astro:30`, `app/src/pages/catalog/[layer].astro:9`, `app/src/pages/areas/[slug].astro:34`.

The inventory contained no API endpoint modules. Generated route totals were not measured.

## 2. Rendering and island boundaries

- Astro configuration uses React and Tailwind integrations, directory-format output, configurable GitHub Pages base, and viewport prefetching. No server adapter appears in the inspected configuration (`app/astro.config.mjs:51`).
- `client:only="react"`: explorer, monthly trends, research map, segments, tools and article chart enhancement (`app/src/pages/explore.astro:84`; `app/src/pages/research/trends.astro:76`; `app/src/components/research-map/ResearchMapSurface.astro:129`; `app/src/components/segments/SegmentsSurface.astro:78`; `app/src/components/tools/ToolsSurface.astro:143`; `app/src/pages/analytics/[slug].astro:214`).
- `client:load`: overview, leaderboard, studies library, catalog DAG, area section panel and two theme-toggle instances in the shell (`app/src/pages/dashboard/index.astro:98`; `app/src/pages/dashboard/leaderboard.astro:75`; `app/src/pages/analytics/index.astro:167`; `app/src/pages/catalog/index.astro:66`; `app/src/pages/areas/[slug].astro:213`; `app/src/components/Sidebar.astro:86`).
- `client:visible`: catalog dataset/schema tables; `client:idle`: area history panel (`app/src/pages/catalog/index.astro:77`; `app/src/pages/catalog/[layer]/[...dataset].astro:129`; `app/src/pages/areas/[slug].astro:393`).
- Non-island browser code includes the navigation drawer, article TOC observation and home counter animation (`app/src/components/Sidebar.astro:343`; `app/src/components/TableOfContents.astro:76`; `app/src/pages/index.astro:221`).

## 3. Runtime contracts and data flow

### Publishing/build boundary

- Supported app toolchain is Bun, Astro, React and Playwright. TypeScript extends Astro’s strict configuration (`app/package.json:1`; `app/tsconfig.json:1`).
- `build` explicitly selects observed v2; `build:base` validates data, synchronizes the catalog, then builds Astro. A separate legacy build exists (`app/package.json:13`).
- Markdown is loaded directly from `docs/analytics`: one collection for current series text and another for frozen editions. Shared Zod frontmatter permits optional metadata and enumerated categories/personas/technical levels (`app/src/content.config.ts:13`).
- Catalog, dashboard and tool shells read local public assets during builds. Browser data URLs incorporate `BASE_URL` (`app/src/utils/catalog.ts:8`; `app/src/pages/dashboard/index.astro:18`; `app/src/components/tools/ToolsSurface.astro:43`; `app/src/constants/data-urls.ts:7`).

### Legacy dashboard release

`release-manifest.ts` defines runtime parsing and verification, separate from TypeScript interfaces:

- Schema `1.0.0`; generation identity; observation range; period definitions; inclusion rules; provenance; per-asset digest, bytes, shape and metric scopes.
- Generation is recomputed from canonical JSON excluding generation/export-time fields.
- Verification distinguishes `verified`, `mismatch`, `unverified` and `absent`.
- Supports raw gzip hashes and optional decompressed-content hashes.
- Manifest/network/parse/hash failures are translated to explicit states.

Evidence: `app/src/utils/release-manifest.ts:1`.

### Observed v2 pack

- Schema `2.1.0`; core roles are `periods` and `summary`, with four monthly-history roles required by manifest parsing.
- Browser loading fetches the manifest with `no-store`, recomputes generation, verifies compressed byte lengths and hashes, then decodes the same responses.
- Core loading skips monthly histories; history loading verifies one requested property payload.
- States are `ready`, `absent`, `invalid`. Transport-decoded gzip receives an explanatory invalid-state message.
- Build-time loading shares manifest/period parsers but reads and hashes disk bytes.

Evidence: `app/src/utils/observed-pack-loader.ts:1`, `app/src/utils/observed-pack-build.ts:1`.

### Observation semantics

- Legacy adapter resolves joint era/property sections, canonicalizes planning-area identities and represents available/missing/exporter-empty values. Zero-valued legacy fields become null-valued `empty` observations (`app/src/utils/observed-data.ts:1`).
- V2 parser indexes periods and observations; validates duplicate identities, comparator references, month grids, property types, status/disposition and finite metric values. Dispositions are `publish`, `limited-display`, `withhold`; observation statuses are `available`, `no-sales` (`app/src/utils/observed-periods.ts:1`).
- Aliases resolve from published descriptors, not browser time. Comparator arithmetic reports unavailable values, unit differences and zero denominators (`app/src/utils/observed-periods.ts:490`).
- `PUBLIC_OBSERVED_RELEASE` defaults to legacy unless exactly `v2`; build scripts provide the production v2 selection (`app/src/config/observed-release.ts:21`; `app/package.json:13`).

### Surface-specific flows

- Explorer verifies a legacy release pair, then loads displayed legacy assets through the generic hook; concrete periods use the separately verified pack. Its national summary can also arrive as build-time props. Selection and view are written using `replaceState`; popstate reparses the URL (`app/src/components/explorer/ExplorerWorkspace.tsx:1`).
- Monthly trends fetches one legacy asset and separately renders build-time v2 window summaries. It exposes `series`/`window`, loading/retry/unusable-shape states, SVG price/volume charts and a complete monthly table (`app/src/components/trends/TrendsWorkspace.tsx:1`).
- Tools load three archive assets plus observed reference prices at build time; the financing asset named `affordability_metrics` is deliberately not read by that shell (`app/src/components/tools/ToolsSurface.astro:1`).
- Catalog parsing dispatches JSONL records into metadata/layers/datasets/edges and Maps; malformed JSON lines are logged and skipped. Dataset props are projected into smaller table/DAG shapes (`app/src/types/catalog.ts:107`; `app/src/utils/catalog-payload.ts:1`).
- Archive routes validate registry entries, verify pinned artifacts, reject unregistered frozen sources and throw on registry/artifact failures. Series pages still render series text while linking approved editions (`app/src/pages/analytics/archive/[year]/[edition]/[slug].astro:30`; `app/src/pages/analytics/[slug].astro:123`).

## 4. Inputs, outputs, failure handling and logging

### Shared request lifecycle

`useGzipJson` provides a module-memory cache with a five-minute TTL, optional generation-qualified keys, abort controllers and stale-request tokens. Initial/retry failures can clear data; refresh failures retain displayed data and populate `refreshError` (`app/src/hooks/useGzipJson.ts:1`; `app/src/utils/request-state.ts:1`).

The gzip utility accepts already-decoded JSON-looking text, otherwise attempts `DecompressionStream`, then returns decoded text for JSON parsing. HTTP and JSON failures propagate to consumers (`app/src/utils/gzip.ts:17`).

### Error-path map and test leads

**Test links below are inventory-based leads only: test bodies were not read, so coverage is not established.**

| Critical path                            | Inspected error boundary                                               | Candidate tests                                                                                                                  |
| ---------------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Fetch/cache/retry/refresh                | `hooks/useGzipJson.ts:146`; `utils/request-state.ts:1`                 | `tests/unit/request-state.test.ts`                                                                                               |
| Legacy generation verification           | `utils/release-manifest.ts:395`                                        | `tests/unit/release-manifest.test.ts`; `tests/e2e/s1-evidence-boundary.spec.ts`                                                  |
| V2 manifest/payload/history verification | `utils/observed-pack-loader.ts:303`; `utils/observed-pack-build.ts:67` | `tests/unit/observed-pack-loader.test.ts`; `observed-pack-build.test.ts`; `observed-periods.test.ts`; `observed-monthly.test.ts` |
| Explorer selection/data availability     | `components/explorer/ExplorerWorkspace.tsx:172`                        | `tests/unit/explorer-selection.test.ts`; `explorer-pack-rows.test.ts`; `tests/e2e/explore.spec.ts`                               |
| Monthly trend loading/shape              | `components/trends/TrendsWorkspace.tsx:280`                            | `tests/unit/trend-series.test.ts`; `tests/e2e/trends.spec.ts`                                                                    |
| Build-time dashboard reads               | `pages/dashboard/index.astro:26`; `leaderboard.astro:26`               | `tests/e2e/dashboard-overview.spec.ts`; `dashboard/leaderboard.spec.ts`                                                          |
| Catalog load/parse                       | `utils/catalog.ts:16`; `types/catalog.ts:114`                          | `tests/unit/catalog-payload.test.ts`; `catalog-audit.test.ts`; `tests/e2e/catalog.spec.ts`                                       |
| Edition publication gate                 | Archive route throws at registry/artifact checks                       | `tests/unit/edition-registry.test.ts`; `tests/e2e/analytics/archive.spec.ts`                                                     |

A source-text scan also located catches/logging in map implementations, area loaders/history and math rendering. Those map/area implementations were not fully inspected.

Observed logging is primarily `console.error` with asset/error context. No telemetry implementation was established; that is **not** a comprehensive absence claim.

## 5. Accessibility, persistence and privacy

### Inspected mechanisms

- English document language, viewport metadata and first-focusable skip link (`app/src/layouts/Layout.astro:16`).
- Mobile drawer: focus movement/trapping, Escape, focus restoration, background/drawer `inert`, breakpoint synchronization and scroll locking (`app/src/components/Sidebar.astro:343`).
- Shared modal hook: nested-dialog stack, topmost Escape/Tab handling and focus/scroll restoration (`app/src/hooks/useModalDialog.ts:1`).
- Global focus-visible outlines and reduced-motion rules for drawer/main transitions (`app/src/styles/globals.css:130`).
- Explorer tabs implement arrow/Home/End navigation and roving tab index; table has captions and scoped headers (`app/src/components/explorer/ExplorerView.tsx:1`).
- Trend SVGs expose titles/descriptions and reference the monthly table; price axes disclose zoom and missing observations remain gaps (`app/src/components/trends/TrendsChart.tsx:1`; `TrendsTable.tsx:1`).
- Multiple client-only shells provide no-JavaScript explanations; studies additionally list article links without filtering (`app/src/pages/analytics/index.astro:169`).

### Browser-held data

- Theme uses `localStorage["theme"]` and system color preference (`app/src/components/DarkModeToggle.tsx:8`).
- Generic fetched-data cache is module memory (`app/src/hooks/useGzipJson.ts:34`).
- Explorer and trend choices persist in URL parameters/history, not inspected storage (`ExplorerWorkspace.tsx:1`; `TrendsWorkspace.tsx:1`).
- Tools shell states that financing inputs remain local and are not serialized/logged. **The financing implementation and privacy tests remain unread**, so this is recorded as a declared contract, not verified behavior (`app/src/components/tools/ToolsSurface.astro:160`).
- External resource interfaces include jsDelivr KaTeX CSS; the Plotly component exposes a lazy iframe interface (`app/src/layouts/Layout.astro:26`; `app/src/components/PlotlyEmbed.astro:16`).

## 6. Documentation comparison — observed contradictions, without judgment

Read: root/app READMEs, architecture, quick-start, E2E guide and implementation README. Historical audit statements were not treated as implementation evidence.

1. **Bun-only setup versus E2E default:** app documentation specifies Bun-only usage; Playwright’s default server command is `npm run dev` (`app/README.md:17`; `app/playwright.config.ts:5`).
2. **Implementation status chronology:** the ledger contains RF05 both “in progress” and “complete,” plus a later paragraph saying RF00–RF12 are not started (`docs/implementation/README.md:7`, `:8`, `:47`). Current code contains the v2 loaders, defaults and edition route.
3. **Catalog discrepancy copy:** ledger shipped-surface text says the catalog discrepancy is shown; current audit constants record equal current row counts, and the page conditionally displays the discrepancy only when counts differ (`docs/implementation/README.md:79`; `app/src/constants/catalog-audit.ts:40`; `app/src/pages/catalog/[layer]/[...dataset].astro:35`).
4. **Area-page introductory comment versus implementation:** comment says there is no client island and only a return-link enhancer; markup includes section and history islands (`app/src/pages/areas/[slug].astro:5`, `:213`, `:393`).
5. **Edition narrative chronology:** ledger records all fifteen series approved alongside older statements that thirteen remain historical. The series route explicitly distinguishes its rendered series narrative from signed edition text (`docs/implementation/README.md:26`, `:32`; `app/src/pages/analytics/[slug].astro:160`).
6. **Historical verification counts:** ledger records earlier Astro/Playwright counts; these were not rerun or adopted as current evidence (`docs/implementation/README.md:103`, `:145`, `:220`).

## 7. Valuable later-analysis targets and unread scope

### Later-analysis targets

- Follow verified bytes through actual rendered legacy values, including the separate verification/fetch requests.
- Exercise v2 malformed manifests, disposition handling, unavailable periods, transport decoding and hashing failures.
- Trace financing arithmetic, URL allowlists and privacy assertions through implementations and tests.
- Inspect map geometry, third-party tile requests, tooltip construction and independent layer failures.
- Reconcile series/approved-edition presentation, chart gates and registry/artifact validation.
- Validate keyboard/no-JavaScript behavior and request lifecycle with the existing E2E suites.

### Explicitly unread or incomplete

- **All test bodies and fixtures**, including privacy/accessibility/failure assertions; no tests executed.
- Primary overview, leaderboard, map, segment and tool implementations; most explorer child components.
- Area loader/selection/activity/monthly-history implementations.
- Edition registry, study helpers, chart parser/renderers and most remaining utilities/types.
- Six thin research/compatibility route wrappers were inventoried, not read.
- `app/scripts/*`, CI/deploy workflows, lockfile and publishing/exporter implementations.
- Public payload bodies and analytics article/edition contents.
- Remaining guides, plans, implementation reports and historical audits.
- A few batched outputs were truncated; their omitted portions were not counted as inspected evidence.
