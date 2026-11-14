# Reporting refresh — implementation handoff pack

- **Date:** 2026-11-12
- **Status:** Draft — assignments are prepared, not started or approved for execution.
- **Parent contract:** [Full implementation map](2026-11-12-reporting-refresh-implementation-map.md).
- **Evidence:** [Reporting audit](../implementation/2026-reporting-refresh-audit.md).
- **Research jobs:** [Study and asset register](2026-11-12-reporting-refresh-research-register.md).

## How to dispatch a handoff

Give the implementer **this common contract, one RF card, and the linked parent sections**. For RF08 also attach one RS/RA register row. Do not assign the whole program as one worker task. All RF slices are currently **Not started**; data/model publication has additional external gates.

### Common implementer contract

1. Read `AGENTS.md`, the audit, existing `docs/implementation/README.md`, the parent map, and this card. Check actual branch/status; do not assume historical ledger text matches the checkout. No commits unless explicitly requested.
2. Read the matching `.agents/skills/` instructions before pipeline/ingestion changes. For browser checks read the Playwright skill. Navigation/type checks should use project-aware tooling; an empty cached diagnostics list is not proof of a clean file.
3. Analyze imports/consumers before editing. Existing file paths below are entry points, not permission to rewrite every file. Paths labelled **proposed** do not yet exist. Ask the coordinator for shared-file changes outside your assignment.
4. Keep source/payload changes separate from UI corrections. Fixture-only completion must not be described as a real-data refresh. Obtain explicit permission for R2/API fetches, cache invalidation, pipeline runs, model fitting or deployment.
5. Preserve v1 period meanings, old URLs, archive/model gates, missing-data semantics, privacy and base-path handling. No fallback to unrelated property/time margins. No scientific or policy change disguised as label cleanup.
6. Work on one assigned slice at a time. Record partial work/blockers; never claim completion with failing tests, missing required input or an unresolved approval.
7. Return the completion form at the end of this document with exact commands/results and changed asset hashes. No secrets in logs, reports or fixtures.

### Common verification profiles

Run the applicable profile after focused tests; do not report future commands as executed.

### F — frontend

```bash
cd app
PATH="$HOME/.bun/bin:$PATH" bun --version     # required: 1.2.23
PATH="$HOME/.bun/bin:$PATH" bun install --frozen-lockfile
PATH="$HOME/.bun/bin:$PATH" bun run test:unit
PATH="$HOME/.bun/bin:$PATH" bun run astro check
PATH="$HOME/.bun/bin:$PATH" bun run validate-data
```

For changed TS/TSX files, probe active LSP diagnostics on the changed paths; report server/config limitations separately and use project checks as acceptance evidence. The audit baseline was 0 errors / 0 warnings / 22 existing hints; touched files add none. Install/project resolution comes before interpreting stale editor diagnostics.

**D — data/export boundary** (from repository root)

```bash
uv run pytest tests/test_export_app_data.py --no-cov -q
uv run ruff check
uv run ruff format --check scripts/export_app_data.py tests/test_export_app_data.py
```

Include every new/changed Python file in format checks. If production DAG or persistence changes, also run the Hamilton skill's tests/mypy/validators; if adapters/bronze change, also run the ingestion skill's tests and source-onboarding checks. Never weaken tests to accommodate a contract regression.

### B — build/browser integration

Use the commands in the existing implementation ledger: production root build/preview, focused/full root Playwright, then `build:pages`, prefix-mounted `serve:pages` and Pages-base tests. Check actual free ports and clean up only your own processes. A root test run's skipped Pages tests are not prefix coverage. Read the Playwright skill; record UI interaction, console/network results and artifact paths.

A normal build rewrites `app/public/data/catalog.jsonl.gz`; restore only incidental generated changes, not RF11's authorized catalog work or another worker's changes. Inspect the diff before any restore. Measure route payloads when new props/islands/charts are introduced.

### C — docs/common

```bash
uv run python scripts/tools/validate_docs_layout.py
uv run python scripts/tools/validate_agent_skills.py
git diff --check
git status --short
```

## RF00 — Freeze the baseline and ratify contracts

**Role:** coordinator. **Requires:** none. **Unblocks:** all other RF cards. **Scope:** preservation/fixtures/decisions, not source refresh or new analytics.

**Read first:** audit; parent map §§2–5; `app/public/data/README.md`; `app/public/data/dashboard-release.json`; current analytics sources and asset references; existing unit/E2E tests.

### Work sequence

1. Record branch/dirty tree, current route list, release hashes, metric reproductions and actual test/tool versions. Protect user changes; do not remove the uncommitted audit document.
2. Inventory all 15 root studies, persona promotions, model/tool extracts, static figure references, current catalog and geometry. Hash original bytes. Record unknown observation/source dates as unknown, not mtime-derived freshness.
3. Preserve original report bytes in a **proposed** frozen source area under `docs/analytics/editions/legacy/` before RF02 modifies current copy. Pin referenced existing asset paths/hashes and prohibit overwrites; new results must use new paths. Supply a documented hash-verification command and passing freeze report. Coordinator must not grant RF02 write ownership until this gate passes; subsequent checks verify the frozen originals/assets, not intentionally corrected root text. Do not copy manual source data or secrets into git. Archive routing/schema arrives in RF07.
4. Capture a small licensed/non-sensitive fixture for joint metrics, including Punggol HDB/2025, null/empty subsets, a thin sample, geography labels and sparse months. Mark synthetic fixtures as synthetic. Pin the known published fixture rather than assuming corrected future sources must reproduce it forever.
5. Ratify D01–D12 or record replacements. Define source-specific coverage policies/disposition fields and named data/scientific/release approvers; record permitted role combinations. Assign one owner per shared file group and record performance/props budgets for changed routes.
6. Write a short RF00 baseline/decision report and initialize milestone acceptance checklists. Preserve complete previous release artifacts through approved existing versioning/storage before later publication.

**Acceptance:** originals recoverable/hash-verified; all audit findings map to an RF slice; all publication/source/model permissions explicit; source absence is recorded as a blocker, not repaired by changing metadata.

**Checks:** F baseline, data manifest validation, C; no live source tests or build necessary merely to record preservation. **Stop:** unresolved storage/immutability or contract decisions that downstream code would have to guess.

## RF01 — Repair scoped rankings and planning-region filters

**Role:** observed frontend owner. **Requires:** RF00. **Can ship:** M0 on existing assets. **Does not require:** RF03 or new data.

### Existing entry files

- `app/src/hooks/useLeaderboardData.ts`, `app/src/types/leaderboard.ts`.
- `app/src/components/dashboard/leaderboard/LeaderboardDashboard.tsx`, `LeaderboardControls.tsx`, `LeaderboardTable.tsx`, `LeaderboardMap.tsx`, `MetricHelpModal.tsx` in the same directory.
- `app/src/utils/observed-data.ts`, `app/src/utils/release-manifest.ts`, explorer dataset/selection helpers; `app/tests/e2e/dashboard/leaderboard.spec.ts`.

### Work sequence

1. Add a failing regression for `propertyType=hdb&timeBasis=year_2025&metric=median_price`: Punggol must read the exact `map_metrics.year_2025_hdb` section, **S$672,000 / 1,538 sales** in the preserved fixture, not property-only **S$500,000 / 24,854**.
2. Resolve price/PSF/count from joint sections using pure adapters. For scoped growth/yield/affordability lacking a verified joint contract, show unavailable and explain why; preserve explicit metric URLs without silently substituting a different metric/population. Choose the ratified safe default.
3. If leaderboard metadata supplies region/coordinates, use it as reference metadata, not a competing numeric source. Verify consumed numeric bytes and any cross-asset comparison; do not double-fetch after verification and display unchecked responses.
4. Replace the false CCR/RCR/OCR mapping with actual planning-region controls and a local observed-geography type. Do not change archived segment region/scoring semantics. Handle unknown region explicitly.
5. Use selected-window counts for eligibility, null-last metric sorting, stable name tie-breaks and metric-appropriate direction. Thin rows are viewable but not ranked ahead of qualified rows; no rank number implies confidence.
6. Ensure map, table, summary, price filter, property mix and help text all describe the same scope. Handle initial deep links before URL writes, back/forward and unknown query keys.

**Tests:** proposed pure ranking-adapter unit tests; every property/legacy-period pair, absent joint block, no-sales/nulls, each region, no region, thin rows in both directions, unsupported metric URL, map/table parity and Punggol browser reproduction.

**Checks:** F + focused leaderboard E2E + C. **Stop:** needing a numeric metric absent from the joint contract; request RF04 instead of margin fallbacks. Shared adapters changed here must have an explicit RF04 transition note.

## RF02 — Correct promotional copy and chart rendering

**Role:** content/chart owner. **Requires:** RF00's hash-verified frozen originals and explicit write handover. **Can ship:** M0 independently of source restoration. Before editing, run RF00's preservation verifier; if it fails or no passing freeze report exists, stop. Do not begin report edits in parallel with the freeze.

**Existing entry files:** `app/src/pages/index.astro`; `app/src/data/persona-content.json`; analytics/persona templates; `app/src/components/charts/ComparisonChart.tsx`, `InlineChartRenderer.tsx`; `app/src/utils/data-parser.ts`; `app/src/components/studies/lib/studies.ts`; affected `docs/analytics/*.md` and article/persona E2E tests.

### Work sequence

1. Remove/qualify “up to 79% expected gains,” current market-timing recommendations, unsupported coefficient multipliers, “myth busted” certainty and the static snapshot's “Live Dashboard” wording. Use historical/review language; do not replace with invented results.
2. Relabel R² correctly and distinguish directional accuracy, error and interval measures. Any body correction gets an erratum/change record referencing the frozen original. Keep gross rental proxies and synthetic-input uncertainty visible before recommendations.
3. Repair Recharts layout/axis orientation; test rendered bars, not only chart mount presence. Inspect every opted-in chart for unit compatibility and table parity.
4. Handle `±`/range/unknown cells honestly. Do not strip uncertainty notation into a point estimate. Omit an all-missing series with an explanation or supply a separately reviewed interval renderer; do not plot interval width as if interchangeable with R².
5. Preserve author opt-in chart markers and the lease unit-review chart gate. Keep raw historical tables available with status/erratum; no blanket recharting or unverified PSF/PSM conversion.
6. Record a current-content review matrix for all 15 studies and three personas; hand unresolved scientific questions to RF08.

**Tests:** valid comparison marks, missing/interval/negative values, unit-heterogeneous selection, no chart for unmarked tables, lease chart withheld, sanitized persona/home copy and base-prefixed article/figure links.

**Checks:** F, focused analytics/home/persona E2E, C. **Stop:** scientific coefficient/unit changes or new policy/forecast conclusions without the research job's approval. RF07 later replaces slug-only evidence flags with edition-aware status.

## RF03 — Restore source readiness and reconcile coverage

**Role:** data owner. **Requires:** RF00 and explicit acquisition/run permission. **External blocker:** missing local platinum/manual source inputs. **Unblocks:** real-data publication for RF04/RF09, RF11 and relevant research jobs.

### Read/entry files

- Both repository skills; `docs/guides/r2-sync-guide.md`, pipeline/ingestion development guides, `docs/data-sources.md`.
- `main.py`, `src/egg_n_bacon_housing/pipeline.py`, source adapters and `components/ingestion/{datagov,ura_csv,macro,geojson}.py`.
- `scripts/00_sync_data.py`, `scripts/40_refresh_rolling.py`; bronze manifest/cache helpers; cleaning/schema/metrics code and focused tests.

### Work sequence

1. Produce a preflight: input identities/availability, required credential **names only**, intended sources, cache policy, network/time/storage implications and approved operations. Read CLI help before selecting flags. No broad `--refresh` or cleanup by default.
2. Restore documented manual/geocode data as authorized. Use supported CLI/DAG; don't construct an alternate runner or open/print secret files. Preserve valid caches on empty/partial/error responses.
3. Reconcile source/month/property counts, natural/business keys, overlaps between API/CSV history, unit versus record grain, price/area/PSF units, dates and quarantine/exclusion counts. Investigate the published private/EC Jan–Oct count differences without assuming their cause.
4. Validate rental/macro source lags, real versus generated/fallback values, geometry/crosswalk versions and historical coverage. Check whole-history and completed-month distinctions.
5. Apply the ratified source-specific policies in the parent map §5.6. Produce its required per-source-set/property/geography/period ledger with input hashes, acquisition/cutoff/key/overlap/unit/quarantine/geocoding evidence, benchmark discrepancies, disposition and permitted operations. Unknown source publication dates stay null; alternative completeness evidence must be documented, not assumed.
6. Obtain named data-steward approval for the actual cutoff/dispositions, or report blockers; the evidence preparer cannot self-approve their cutoff. Distinguish publish-current, limited historical/diagnostic display and withhold. A passing HDB scope may ship alone; national All needs all constituents to pass, and local areas need geography-coverage checks. A missing comparator withholds change/ranking, not a verified raw count.
7. If a defect is found, propose the smallest source/schema fix, add mocked regression tests and follow both skill checklists as applicable. Any new persisted DAG output uses the supported materializer/registry path.

**Checks:** relevant adapter/ingestion/cleaning/metrics tests; D and all applicable skill checks; C. Candidate source evidence is required in addition to passing tests.

**Deliverable:** RF03 source-reconciliation report and explicit approval/rejection per property/month. **Stop:** absent permission/credentials, unresolved business keys/coverage, synthetic input mixed into empirical results, or inability to preserve valid caches. Never “complete” RF03 by generating app assets from undocumented inputs.

## RF04 — Implement v2 periods, exporter and verified-byte adapters

**Role:** data-contract owner, one writer for exporter/shared observation contracts. **Requires:** RF00 decisions for code; RF03 for real-data candidate/publication. **Parent:** map §5 is the contract.

**Existing entry files:** `scripts/export_app_data.py`, `tests/test_export_app_data.py`; `app/public/data/README.md`, `manifest.json`; `app/scripts/validate-data.mjs`; `app/src/utils/release-manifest.ts`, `observed-data.ts`; `app/src/hooks/useGzipJson.ts`; data URL constants; build-time loaders and existing release/observed unit tests.

**Proposed additions:** client-safe v2 period/release/observation modules and corresponding Python/TS fixtures/tests; immutable `observed/<generation>/…` payloads and `dashboard-release-v2.json` as specified in the parent. Name actual modules in the RF04 contract report before RF05 starts.

### Work sequence

1. Define explicit schemas and pure resolver interfaces for periods, units, scope availability, values, comparators and failure reasons. Legacy adapters stay separate. Descriptors, not repeated year lists, drive new UI options.
2. Build transaction-level national and area aggregates for the same concrete property/period selections. Define excluded-area versus national inclusion explicitly; don't force area sums to equal a differently scoped national population.
3. Implement calendar-valid bound/comparator generation from the declared cutoff, including prior-year windows and missing comparator states. No current-date inference in published v2 identity or client labels.
4. Stage deterministic v2 data under immutable generation paths, validate all members, then publish the discovery manifest last. Preserve the v1 seven-file contract/period meanings; don't add a new file to its exact asset set.
5. Preserve nulls, true booleans and numeric units; add cross-language canonicalization/content-hash tests, including host-decoded gzip. Validate safe relative paths, duplicate IDs, wrong schema, altered bytes and mixed generations.
6. Return verified parsed payloads to consumers. Remove verification-then-unchecked-refetch hazards for migrated observations. Keep stale displayed data on failed refresh with explicit status/retry.
7. Add v2-aware build/data validation and a ratified rollout selector. No silent v1 substitution for invalid/explicit v2 selections; absent v2 may expose a labelled legacy mode.
8. Export real data only to an explicit temporary candidate directory after RF03. Record input identities, cutoff, supported scopes and output hashes. Fixtures alone satisfy the code gate, not the data publication gate.

**Tests:** October cutoff after January clock rollover; December/January publication; leap/calendar validation; missing source/month/comparator; sparse months; all property scopes; count/price/PSF denominators; no median-of-medians; zero/empty/null; bool/Unicode hash parity; generation corruption and fetch-race simulation; v1 fixture compatibility.

**Checks:** D + F + C; focused release/data-boundary E2E where consumed. **Stop:** unresolved RF03 scope quality for candidate publication, changed v1 meaning, unverified rendered bytes or source-fetching inside exporter/frontend.

## RF05 — Migrate dashboard, trends, explorer and rankings to current periods

**Role:** observed frontend owner. **Requires:** RF01, RF02, RF04's frozen interfaces. Real current release requires RF03. **Scope:** observations, not models.

**Existing entry files:** home and dashboard page loaders; `MarketOverviewDashboard.tsx`; dashboard price/volume charts; `app/src/components/trends/TrendsWorkspace.tsx`; `app/src/utils/trend-series.ts`; explorer workspace/selection/data/view modules; leaderboard components/hook; observed/release adapters and route E2E files.

### Work sequence

1. Consume RF04 interfaces directly and populate controls from verified descriptors/availability. Use ratified YTD/TTM defaults; no independent hardcoded 2026 lists.
2. Show selected property/window, completed cutoff, observed/source dates and comparison windows on every KPI/chart/table. Separate export time from source freshness and whole-history partial buckets from completed-window views.
3. Expose latest month, YTD, TTM and completed years; preserve legacy windows. Sum counts where valid; request transaction-level period medians rather than averaging monthly medians. Keep charts gap-preserving and volume axes zero-based.
4. Bring rankings onto the same v2 metric contract; do not restore unavailable yield/growth with top-level legacy enrichments. Label whether distributions follow controls or intentionally show historical context.
5. Apply the parent map's intentional bare-URL migration: visible updated-default notice/active window and links to prior explicit windows; new share links retain concrete periods. Translate existing query dialects (`property/period`, `series/window`, `propertyType/timeBasis`) explicitly. Parse before write; preserve unknown keys; support back/forward. Persist concrete selections even when equal to today's default; unsupported explicit periods produce a message, not silent fallback.
6. Use the same selected verified bytes for national/area comparisons. Keep failures local and already-published values visible; no invalid-generation comparison.
7. Update home highlights to accurately named observations with approved source scopes. No adjusted index, valuation, annualized partial-year growth or “live listings” language.

**Tests:** all property/period switches; default versus explicit 2025 URLs; unknown/unavailable periods; month gaps and source failures; same-month-prior-year volumes; price/count scope parity across overview/explorer/rankings; history navigation and root/Pages links.

**Checks:** F + B focused dashboard/trends/explore/leaderboard/home tests + payload measurement + C. **Stop:** an RF04 schema gap; request a contract revision, not a local untyped fallback. Pass RF06 a list of serialized selections and periods actually supported.

## RF06 — Honor area selections and preserve tool/legacy contracts

**Role:** area/tools owner. **Requires:** RF05. **Parent decisions:** D08 and v1 URL compatibility.

**Existing entry files:** `app/src/pages/areas/[slug].astro`; `app/src/utils/area-page.ts`, `area-links.ts`; `app/src/components/tools/ToolsSurface.astro`, tools workspace and `lib/{tool-reference,tool-evidence}.ts`; financing draft modules; research-map/segments surfaces; dashboard wrapper pages and navigation constants.

### Work sequence

1. Preserve the union of historical area identities and approved new identities in static route generation. Detect slug collisions; a missing current-period row must not delete an old area URL.
2. Embed only that area's verified sections and generation at build time, not the whole national/monthly payload on every fieldnote. Add an accessible small selector to honor property/period query parameters; update values, labels and provenance together.
3. No-JS HTML states its fixed default scope and exposes useful section links. Explicitly say a query-specific enhanced selection is unavailable without JS; do not suggest a query changed static metrics. Missing selections never use the preferred headline as a silent substitute.
4. Update `area-links.ts`, the inline return-parameter allow-list and URL tests together; retain explorer search/sort/page state and base-prefixed paths.
5. Make the financing observed reference's period explicit and verified. Preserve manual price edits, in-memory draft behavior and privacy. The period is part of reference identity; a price may import on an explicit reference selection, not an unrelated rerender.
6. Keep archived lease/MRT/spatial contracts, segment weights and nine model-layer gates unchanged. Migrating observed fill/reference does not promote a model.
7. Retain `/dashboard/{map,segments,trends}` wrappers and all compatible query IDs. `/dashboard/trends` stays tools; monthly trends remains `/research/trends`.

**Tests:** selected values versus fixed SSR/no-JS scope, unavailable period/type, old slug survival/collisions, base-prefixed return links, tool reference identity/manual override, private inputs absent from URL/storage/network/logs and compatibility deep links.

**Checks:** F + focused areas/tools/map/segments/Pages E2E + per-area props/payload check + C. **Stop:** needing a server to inspect query state at static build time or a model redefinition to display current observations.

## RF07 — Publish immutable research editions and archive routes

**Role:** research frontend owner. **Requires:** RF00 frozen sources/assets and RF02 safety changes. **Can ship:** M2 before research regeneration.

**Existing entry files:** `app/src/content.config.ts`; `app/src/pages/analytics/index.astro`, `[slug].astro`, `personas/[persona].astro`; studies library/evidence helpers; markdown/chart rendering; docs-layout validator and analytics/persona tests.

**Proposed additions:** separate edition collection/evidence registry and explicit archive route under `app/src/pages/analytics/archive/`; frozen edition sources under `docs/analytics/editions/`; edition-schema/route/hash tests. Keep proposed paths out of production links until generated and validated.

### Work sequence

1. Adopt RF00's originals without rewriting their text, dates or referenced assets. Give them explicit legacy edition identities and unknown-date fields where appropriate. Pin old data/figure paths; new editions use new asset paths.
2. Create a separate edition loader/registry and central validated evidence metadata. Do not make the existing `*.md` loader recursively emit nested IDs into the single-segment route.
3. Generate stable `/analytics/<slug>` series entries and explicit `/analytics/archive/<publication-year-or-undated>/<edition>/<slug>` routes. Reserve `archive`/`personas`; reject duplicate/colliding IDs and invalid current pointers.
4. Choose latest **approved**, not latest timestamp. If no current validated edition exists, show historical/review status and exact known/unknown observation scope. Editorial publication status remains distinct from scientific evidence status.
5. Keep one library card per series by default; add edition/year/evidence filters and explicit archive navigation. Persona recommendations inherit evidence status and cannot treat a blocked historical forecast as current opportunity advice.
6. Apply lease/model/unit gates by series+edition identity, including nested archive pages. Old body text can remain visible with prominent erratum/status; don't revive a withheld chart because its slug changed.
7. Update docs validation/route checks for the new explicit structure while retaining the root analytics source contract. Verify all old links and assets under Pages base.

**Tests:** fifteen series plus three personas; old/new/undated edition routes, asset hashes, no duplicates, reserved-name collisions, broken approved pointer, current versus archived filters, lease gate on archives, publication versus observation year, scientific-status propagation and one H1 per article.

**Checks:** F + analytics/persona/root/Pages B + C. **Stop:** historical bytes unavailable, unknown provenance being filled with assumed dates or archived model status being promoted without RF08 approval.

## RF08 — Refresh research one registered job at a time

**Role:** named researcher/data owner for one RS/RA job; scientific reviewer separate from frontend acceptance. **Requires:** RF03, RF07 and that job's explicit method approval. **Scope:** attach exactly one row from the research register.

**Read first:** [research register](2026-11-12-reporting-refresh-research-register.md), the complete target study, original edition/assets, relevant source/schema/metric code and applicable skills. Historical plan/notebook paths are leads, not supported runnable generators.

### Work sequence

1. Complete the register's input/method/provenance discovery for the assigned job. If its generator is absent, return a reconstruction proposal with exact inputs, method, publication boundary and approval needs; do not invent refreshed numbers.
2. Freeze input snapshots/identities and method/code versions. Define observation dates, units, sample, comparator/target, missingness and scientific review tests before generating outputs.
3. Execute only approved research work. Reusable production outputs go through supported Hamilton/materialization boundaries; notebooks are not automatically a parallel supported runner.
4. Produce a new edition, chart data, figures and validation evidence. Use new paths; compare with the historical edition and explain changed methods/populations/source revisions.
5. Obtain scientific sign-off from a reviewer who did not author/fit the evaluated result, covering the job's scientific claims (e.g. causal identification, temporal leakage, interval coverage, unit coherence). Separately obtain source/cutoff approval from a data steward other than the evidence preparer; frontend/schema checks substitute for neither. Keep tools/model overlays gated unless their own contract is approved.
6. Submit a proposed approved-edition pointer change to RF12, not an automatic “latest” update. Record researcher, data-steward, independent scientific-reviewer and release-approver identities/evidence. The data steward may also be release approver if documented; the scientific reviewer cannot be publication approver for that edition. Update summary/persona claims only when their actual cited dependencies are approved.

**Acceptance:** all shared and job-specific research criteria pass; reproducible generator or supported reconstruction is documented; old results/figures still available. RS15 synthesis runs after its cited dependencies, not before.

**Checks:** relevant Python/contract tests and skill checks; edition/hash/figure/table tests; F/B where rendering changes; C. **Stop:** missing lineage/input, unknown units, leakage/failed validation, unresolved synthetic input, absent model approval or inability to explain comparability. It is acceptable for a job to remain blocked/archived while M1 ships.

## RF09 — Publish area-type-month history and activity statistics

**Role:** data-contract owner (same exporter owner as RF04). **Requires:** RF04; RF03 for real-data promotion. **Scope:** observed transactions, not spatial research or demand data.
**State:** done 2026-11-14 — see the [RF09 report](../implementation/2026-11-14-rf09-area-type-month-history.md). Schema `2.1.0`, method `observed-aggregates-2`, generation `2c30e2aa836c…`; calibration recorded, no directional label shipped.

**Existing entry files:** exporter and tests; platinum transaction/schema/metrics definitions; v2 modules/validators introduced in RF04. **Proposed:** immutable per-property monthly payloads, activity comparison helpers and focused tests.

### Work sequence

1. Define grain `(canonical area, property type, calendar month)` and source coverage independently. Reindex calendars explicitly; don't let `pct_change(12)` mean twelve observed rows in sparse histories.
2. Publish count, valid price/PSF observation counts and medians, coverage/status and provenance. A known complete no-sales month has count zero and null medians; an absent/partial source stays unavailable.
3. Compute rolling-quarter/TTM aggregates from the underlying transaction records. Do not calculate period medians from monthly medians. Use the parent map's exact prior-year comparator windows.
4. Apply ratified selected-window and both-window eligibility/denominator rules. Keep numeric comparisons neutral; inspect distributions/revisions and propose any directional-label thresholds for approval. No opaque weights or BUY score.
5. Segment new-launch/resale only if source fields/grain support it with reviewed completeness; otherwise disclose mix effects. No stock turnover normalization without a validated denominator/crosswalk.
6. Publish a new **complete** immutable v2 pack containing periods, summary and every declared monthly payload under one generation. Rebuild periods/summary from the same approved inputs, or copy verified unchanged bytes into the new pack only when input/semantic identities match. Consumers verify one manifest for all these artifacts; a monthly-only pointer or cross-generation merge is invalid. Follow RF04's non-circular identity/hash algorithm, and don't mutate the RF04 generation. Chunk/lazy-load by property to limit payload. Keep the old `hotspots.json.gz` historical method separate; document its misleading `years` field as legacy, not a current activity statistic.
7. Produce an authorized temporary real-data candidate and source/aggregation reconciliation report. No portal APIs or scraping dependencies.

**Tests:** sparse calendar shifts, zero/missing/partial months, exact three/twelve-month edges, prior-year missing/zero denominator, counts versus transaction-level medians, property/geography separation, sample thresholds, national/area inclusion rules, deterministic hashes and corruption rejection.

**Checks:** D + RF04 v2 contract tests + F if shared client helpers change + C. **Stop:** promoting a source-rejected scope, publishing a change without an eligible comparator, mixed grain or any proposal to present historical appreciation classes as current demand. Representing a missing comparator explicitly and withholding its change is valid, not a blocker to verified raw observations.

## RF10 — Add area activity to explorer and fieldnotes

**Role:** observed frontend owner. **Requires:** RF05, RF06, RF09. **Scope:** existing discovery surfaces, no new competing dashboard or chart dependency by default.

**Existing entry files:** explorer list/map/table controls and adapters, fieldnotes and area links, dashboard capability/navigation panels; shared chart components. **Proposed:** small activity panel/sparkline and accessible download/table projections using RF09's verified data.

### Work sequence

1. Add explicit volume/activity modes with property and concrete period controls. Expose rolling-quarter count, same-quarter-prior-year change and both denominators; show TTM context separately.
2. Render neutral numeric signals until label thresholds are approved. Use “observed transaction activity,” not buyer demand/liquidity/expected return. Price/PSF movement retains mix/lease/size caveats.
3. Keep map, ranking table, download and fieldnote values sourced from the same generation/selection. Grey/annotate insufficient evidence rather than painting missing values as cold/zero; thin samples are visible but not misleadingly ranked.
4. Preserve scope across click-through and back/forward. Lazy-load selected property history, show explicit loading/missing/error/retry states, and retain already verified data after failed refresh.
5. Provide keyboard interaction, non-colour legends, text/table alternatives and mobile layout. Compare named property/time/price/volume portal patterns only where observed/authorized; no blocked-site bypass.

**Tests:** map/table/download parity, true zero versus unknown, small samples, missing comparator, unsupported property, selected period on fieldnotes, deep links/history, failure/retry, keyboard/mobile and payload budget.

**Checks:** F + focused explorer/map/areas/root/Pages B + payload measurement + C. **Stop:** an unsupported derived statistic or unsourced demand/stock field; request a data contract change, not frontend estimation.

## RF11 — Reconcile catalog, reference vintages and unused assets

**Role:** catalog/data owner. **Requires:** RF03's authorized input evidence and RF00 preservation. **Scope:** actual snapshot reconciliation, not silently changing count constants.

**Existing entry files:** `scripts/generate_catalog.py`, `scripts/tools/check_catalog.py`, `data/catalog/descriptions.yml`; `app/src/constants/catalog-audit.ts`, catalog loaders/components/payload helpers; `tests/test_catalog_generator.py`, catalog unit/E2E tests; geometry/reference assets and data manifests.

### Work sequence

1. Record the old catalog generation and historical inspected/published count discrepancy. Inspect the new platinum artifact directly and identify its hash; do not assume the app overview or catalog is the source of truth for this observation.
2. Regenerate catalog and the measured audit observation together as explicitly authorized. Keep previous evidence and label changes in population/generation; do not edit a constant merely to satisfy a pinned test.
3. Check lineage self-edges/reference paths, dataset requiredness versus observed nullness, snapshot availability labels and slim SSR props. Avoid broad lineage-layout refactoring.
4. Review geometry/reference provenance, canonical area IDs, region mappings, changed boundaries and historical route preservation before replacing reference assets. A transaction refresh does not authorize a boundary change.
5. Verify whether `interactive_tools/affordability_metrics.json.gz` remains unused; propose retain/deprecate/remove with consumer and required-file-contract evidence. Removal requires explicit data-boundary approval; no automatic purge.
6. Produce an asset-disposition table and new catalog/reference hashes for RF12. Keep authorized RF11 output when later builds rewrite catalog; restore only unintended changes after inspection.

**Tests/checks:** catalog generator/checker and audit/payload tests; data validation; focused catalog/root/Pages E2E; reference/slug/hash checks; F, relevant D/skill checks and C.

**Stop:** mismatched measured artifact identity, missing preservation of old evidence, unapproved reference change or remaining consumer of a proposed removed asset.

## RF12 — Gate milestone releases and document repeatable refresh

**Role:** release owner/integrator. **Requires:** RF00 for harness work; only the completed slice set for the chosen milestone (parent map §4). **Do not block M1 on every RF08 model.**

**Existing entry files:** `.github/workflows/ci.yml`, `deploy.yml`; app validation/build/Pages/payload scripts; root/Pages E2E setup/specs; implementation ledger and data provenance documentation. Coordinate package/config changes; do not edit shared files concurrently with data/UI workers.

### Work sequence

1. Build target-specific acceptance checklists: M0 correctness, M1 current observations, M2 archive infrastructure/approved editions, M3 activity/reference. Record explicitly omitted/blocked studies/scopes so partial delivery cannot look comprehensive.
2. Run all relevant unit/type/lint/data checks and production root/Pages browser suites. Test selected property/window across every observed route, legacy wrappers, no-JS fieldnotes, edition/figure links and exact consumed hash verification.
3. Simulate absent/invalid/mixed v2 releases, incomplete RF09 packs, fetch races, clock rollover, bare-default migration, missing comparators and failed background refresh. Verify no stale/incompatible data becomes a current comparison.
4. Compare changed-route payload/props/islands with RF00 budgets; keep financing inputs out of URLs, storage, requests and logs. Review dependency/lock/generated-data diffs and preserve archives.
5. Prepare a staged candidate with approved cutoff/scope/source identities, source-policy dispositions, v1/v2 and research/catalog manifests as relevant, approvals and exact output hashes. For each newly approved study, require separate data-steward, independent scientific-review and publication sign-offs under the parent map §7. Promote only with explicit deployment permission; stage immutable assets before pointers and verify deployed base-prefixed bytes/links.
6. Record rollback build/manifest/asset identities and exercise restoration in a non-production test. Keep old generations/editions referenced by bookmarks; don't delete assets without a reference/retention review.
7. Write a repeatable operational runbook: permission/preflight, source restoration, scoped supported pipeline refresh, business-grain/coverage approval, explicit-cutoff temporary export, validation/build/smoke, publication and rollback. Recurring execution/auto-deploy is a separate approval, not part of this handoff.
8. Update the implementation ledger with actual results and unresolved blockers; never rewrite old evidence as though it described the new generation.

**Checks:** F + D as relevant + full B for the target + C; applicable skill suites for changed pipeline/ingestion code; research scientific evidence for each newly approved edition. Skips/failures and environment limits are reported, not hidden.

**Stop:** any target-required failure, unapproved source/model scope, mixed/unverified publication, missing rollback, archive overwrite or deployment permission absent. Deployment blocked does not erase local verification, but it is not a completed deployed release.

## Completion / blocked handoff form

```text
RF/RS ID, owner, branch/base and state:
Target milestone / dependencies actually satisfied:
Scope implemented; exclusions and approvals:
Files changed; shared-contract owner/signoff:
Input source/release identities and declared cutoff:
Preserved historical hashes; new artifact/edition hashes:
Focused and full checks (exact commands, exit status, test counts/skips):
Browser flows, console/network result and artifact paths:
Payload/privacy/base-path evidence:
Known failures/blockers (cause, next action, responsible owner):
Publication status and rollback target (or not authorized/not attempted):
Next handoff and smallest safe next action:
```

No slice is complete merely because its UI renders, its schema passes, or its date labels now say 2026.
