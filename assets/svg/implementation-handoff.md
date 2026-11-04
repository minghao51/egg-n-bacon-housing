# Implementation handoff / brief for the next planning agent

## Revision 2 status

The user requested audit improvements and the next planning step. Audit completed with Luna 6.0; the detailed plan now exists at [implementation-plan.md](implementation-plan.md). Read [audit-review.md](audit-review.md) and [feature-specifications.md](feature-specifications.md) before implementing. This brief remains context; the plan resolves feature coverage and route ownership more specifically.

## Mandate

**Inspect the repository again before planning.** Read AGENTS.md, applicable skills, current source/tests, and the artifacts in this folder. Verify every assumption against the current checkout; paths, values and contracts may have changed. Then draft a detailed implementation plan using these designs. This handoff is a design brief and suggested slicing, **not authorization to begin a production rewrite or deploy**.

Start with [README.md](README.md), [repository-findings.md](repository-findings.md), SVGs 01–03, [screen-data-map.md](screen-data-map.md) and [interaction-spec.md](interaction-spec.md). Reproduce the joint period/type issue in useLeaderboardData and compare it with map_metrics sections before choosing component reuse.

## 1. Product outcomes and journeys

Outcomes:

- A reader understands the selected housing type, period, currency and included sample.
- The primary comparison never combines year-specific prices with property-only or all-history metrics without explicit labeling.
- Method/source caveats are close to each claim.
- Mobile and keyboard users can complete the same comparisons without a map.
- Existing research, tools and catalog capabilities remain discoverable.

Journeys:

1. Overview national comparison → HDB explorer → area fieldnote → limitations/source.
2. Direct explorer entry → period/type/sample → sort/search → map/table equivalent → area.
3. Research claim → report methodology → provenance guide → catalog/schema/lineage.

Proposed user validation: ask buyers/upgraders/researchers to identify what S$710,000 means and what it cannot establish, explain the hidden-area threshold, and return from detail to their original comparison. No analytics baseline or user research currently justifies numerical conversion targets.

## 2. Retain / refactor / replace / retire

| Action                        | Scope                                                                                                                                              |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Retain                        | Hamilton runtime, medallion persistence, supported CLI, maintenance export boundary; Astro static build; BASE_URL; React/Recharts/Leaflet; Bun     |
| Retain                        | Markdown reports/math, opt-in article charts, persona links, catalog nested routes and schema/DAG views                                            |
| Reuse with audit              | DATA_URLS and useGzipJson lifecycle; existing table/map primitives; segment matching/investigation and calculators                                 |
| Refactor                      | Joint-selection adapter; runtime contract checks; provenance metadata; nullable metrics; filter URL state; accessible dialogs and navigation       |
| Replace                       | Sidebar-dominated primary shell, separate marketing vs dashboard entry, giant map-first rankings, KPI/pie-card hierarchy                           |
| Retire only after replacement | Misleading “Pre-COVID” label for ≤2021; unqualified “best town”/growth/causal teasers; opaque private-yield fallbacks in primary decision surfaces |
| Do not retire silently        | Segment investigation, trends, interactive tools, persona pages, research URLs or catalog paths                                                    |

No evidence supports replacing Astro with another framework now. A rebuild would add migration cost without repairing data semantics.

## 3. Suggested page/component boundaries

- **SiteShell** (Astro): header, primary nav, skip link, footer, mobile navigation dialog.
- **OverviewPage** (Astro-first): national evidence chart, reading note, next-step link, research teaser, source strip. Small island only if interaction requires it.
- **ExplorerPage / ExplorerWorkspace** (React island): committed/draft URL state and one approved data adapter.
- **ComparisonSettings**, **MobileFilterSheet**, **ExplorerToolbar**, **AreaComparisonPlot**, **AreaResultsTable**, **AreaMapView**, **ResultStatus**.
- **AreaFieldnotePage** (static parameterized route): same-subset source values, baseline, caveat, underlying table and return context.
- **EvidenceMetadata / SourceNote / MetricDefinition**: shared semantic HTML components; do not bury essential caveats in hover popovers.
- **DataMethodsPage**: source/evidence ledger, definitions, clocks, catalog links.
- **ResearchIndex**: retain current article rendering and tools under the new shell; migrate tool-specific UI separately.

Data contracts are in screen-data-map.md. Keep canonical planningArea keys separate from display titles/slugs. Source-section identity travels with every metric. National baselines come from matching overview blocks, never an average of area medians.

## 4. Backend/data work to plan

### Required for a trustworthy initial release

- Validate joint subset sections and approved fields (price/PSF/count). Do not use property-first/period-second leaderboard fallback.
- Add compatibility metadata or a release manifest with generation ID, per-asset export timestamps, supported periods, observation ranges and evidence kinds. The existing manifest is shape-level only.
- Decide a safe behavior for mismatched generations; prefer omit difference over display an unverified baseline.
- Fix missing provenance pointer; document source refresh ownership/cadence separately from export time.
- Derive a supported complete-year choice rather than indefinitely hardcoding 2025. Do not choose the newest calendar year absent coverage validation.
- Audit missing-coordinate/schema discrepancy before labeling area comparisons representative of all records.
- Preserve matched metric nullability and forbid zero/fallback values from masquerading as observations.

### Required before promoting advanced claims

- Label/remove formula-generated private/EC yields, distinguish HDB observed town/month rent ratios from net investor returns.
- Separate time/property scopes of affordability and yields. Fixed national income, mortgage assumptions and all-time enrichment must remain visible.
- Resolve administrative-region vs CCR/RCR/OCR mapping.
- Audit property-mix growth, hotspot “years” units and all-history top-20 semantics.
- Establish research generation reproducibility, model dates and source provenance.
- Determine duplicate policy from source/business keys; do not delete identical observations without evidence.

If modifying DAG/ingestion/persistence, read the matching repository skills and linked guides/tests first. Use main.py/build_pipeline/run_pipeline, dependency injection, schemas and LayerWriter/materializers. No alternate runner or ad-hoc production persistence. Do not make live source calls or print credentials just to implement these screens.

## 5. Suggested implementation slices

| Slice                          | Dependencies / work                                                                          | Acceptance criteria                                                                                                                           |
| ------------------------------ | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| A. Revalidate evidence         | Current public assets, exporter, adapters, production build baseline; inventory routes/tests | Reproduce medians/counts/nulls and joint-filter issue; record baseline failures separately; approve metric contract                           |
| B. Data correctness seam       | A; typed joint-selection adapter, runtime checks, provenance/compatibility metadata          | 2025 HDB Tampines = 710000/620/1921; national = 628000/603/25084; missing subset never falls back; incompatible baseline omitted              |
| C. Tokens and shell            | A; shared HTML components, responsive accessible navigation                                  | 320/390/768/1440px usable; focus, skip link, aria-current, mobile dialog; existing deep links preserved                                       |
| D. Editorial overview          | B+C; SVG 01/04                                                                               | Exact three medians and counts, 78,796 total; source/period prominent; clear HDB action; no fake live state or hardcoded growth claim         |
| E. Explorer list/table         | B+C; SVG 02/05/06; URL filters/sort/pagination                                               | 31 HDB areas, 25 eligible at ≥150, 6 thin; correct ascending rows/ties; mobile draft/apply/cancel; keyboard area links; empty/error scenarios |
| F. Optional map integration    | E; existing polygons, audited joins/provider                                                 | Same subset/selection/scale as table; works when tiles fail; attribution; skip-map route; no client secret exposure                           |
| G. Area fieldnote              | B+E; SVG 03                                                                                  | Proposed route handles type/year, direct deep links and unavailable areas; 82000/13.1% arithmetic; no “premium” claim; back restores state    |
| H. Methods/research migration  | B+C; SVG 08/07                                                                               | Three clocks; unknown timestamps preserved; catalog/article/persona/tool URLs still work; modeled values labeled or withheld                  |
| I. Migration and release gates | All relevant slices                                                                          | Root and Pages BASE_URL, redirect compatibility, accessibility, mobile, data-contract and production smoke tests; no dropped workflow         |

Keep slices independently reviewable. The next planner should refine dependencies and file ownership; avoid editing all dashboards in one uncontrolled migration.

## 6. Validation priorities

1. **Data semantics:** price/PSF/count from same selection; null vs zero; missing geography; national denominator vs area totals; synthetic vs observed yields.
2. **Temporal compatibility:** completed month/year, per-type coverage, generation identity, source vs export time.
3. **Interaction correctness:** URL round trip, shared map/table selection, exact sort order, responsive page anchor, dialog draft behavior.
4. **Accessibility:** keyboard-only, focus restore/trap/Escape, semantic table/sort, chart text alternatives, 200% text, 320px, reduced motion, contrast.
5. **Regression:** reports/inline chart markers/math/catalog schemas/nested routes and legacy segment investigation/tools.
6. **Performance:** compressed bytes, decompression/hydration, lazy map imports; measure before changing transport/framework.

Existing commands: `cd app && bun run validate-data`, `bun run build`, `bun run test:e2e:prod`. Confirm with the user which lint/type-check commands to run; package.json lacks a dedicated lint/type-check script. Candidate `bun run astro check` requires baseline-debt separation. Python gates only when Python is changed, following skills. Never regenerate production data as an incidental frontend test.

## 7. Migration risks and unresolved decisions

- Same-shape assets may be from different generations; most lack embedded export time.
- 2025 is currently a fixed exporter contract. Dynamic periods need deliberate export/type/test migration.
- Current E2E tests depend on route labels/headings and must be updated without reducing behavioral coverage.
- Static hosting lacks arbitrary server redirects; test compatibility pages and base-aware links.
- New fieldnotes can explain aggregates but cannot supply absent flat/lease filters or individual valuation.
- Some advanced research claims remain unreproduced; do not restyle them into increased authority.
- Source freshness SLA, actual user priority, source-completeness criteria, duplicate policy, advanced tool ownership and map provider terms require owner decisions.
- No production browser/OS matrix, assistive-technology audit or user testing has been completed. Revision 2 ran the current Astro type-check baseline: 109 errors, 0 warnings, 45 hints. Spatial Hotspots tab was runtime-confirmed to crash; do not describe every retained tool as working.
- Light-mode visual specs only. Retaining dark mode requires new tokens and chart/contrast validation.

## Next planning deliverable

Reinspect, verify assumptions, identify affected files and exclusive ownership, propose detailed slice-by-slice changes/tests/migration, list decision blockers, and estimate the cost of provenance/data repairs separately from the UI. Use the SVGs as a visual specification, **not** as a mandate to reproduce SVG markup in the application. Request approval of that plan before production implementation.
