# S9 implementation report — research map, studies and catalog detail

> **Historical record.** This report describes the tree at S9 completion. S10 subsequently cleared the remaining `astro check` errors, deleted `PersonaHeader.tsx`, and delivered the integration/deploy checks. Current status lives in `README.md` and `s10-report.md`.

Three surfaces now state their evidence contract instead of implying one: `/research/map` archives nine model layers for inspection while the observed transaction fill stays the only polygon shading, the studies library is searchable and the lease study withholds its mislabelled chart, and the catalog separates its snapshot vintage from an inspected artifact and separates declared requiredness from observed nullness. **No commit**; no published asset modified; no model, content or catalog regeneration.

## 1. Research map

**Routes**

- `app/src/pages/research/map.astro` (new) — research destination.
- `app/src/pages/dashboard/map.astro` — compatibility wrapper over the same shell; the five legacy query groups (`metric`, `timeBasis`, `propertyType`, `area`, `layers`) and all nine layer IDs are unchanged.
- `app/src/components/research-map/ResearchMapSurface.astro` — shared shell; reads the archive generation date at build time for the vintage label and passes one `baseUrl` to the island.
- `app/src/constants/dashboard-nav.ts` — map nav item now says “Research map” and points at `research/map`; the overview capability strip follows the constant.

**Archive gate**

- `app/src/utils/map-archive.ts` (pure, unit-tested) — the nine retained IDs with asset, unit and gate text; per-layer status from independent group load states; area inspection; uniform-placeholder and historical-forecast warnings; observed legend units. A group failure marks only its own three layers.
- `ArchiveLayerControl.tsx` replaces `LayerControl.tsx`: nine checkboxes, each with source asset, units and Ready/Loading/Unavailable status, plus the explicit “Output gate — not validated for current use” notice and a Clear action. The former five-layer limit and its `alert()` are gone because layers no longer paint.
- `ArchiveInspector.tsx` replaces the three overlay components: stored fields for the selected area, coverage (`41 archived areas` vs `55 planning-area polygons`), a data-driven warning when all areas share one stored pattern, an explicit “target predates this extract” warning for the archived forecast, source metadata (`generated_at`, `data_version`, training date) and a link back to `/explore`.
- `PriceMap.tsx` now draws exactly one fill (the observed metric). `analytics/*` values are never shaded; a failing archive source cannot blank the observed map; missing/empty metric values use a neutral grey rather than the lowest colour bin; the legend names quantity, unit, period, evidence status and asset; the observed data load failure now has a retry instead of hanging on “Loading”.
- Deleted: `map/LayerControl.tsx` and `map/overlays/{SpatialAnalysis,FeatureImpact,PredictiveAnalytics}Overlay.tsx`.

Behaviour verified: Bishan shows stored LISA `STABLE`, z `0.00`, p `1.00` and the uniform-pattern warning; `predictive.forecast` shows target `2025-07-01`, the training date and “archive, not advice” on the stored signal; aborting `spatial_analysis.json.gz` leaves feature layers Ready and the observed map painted; no `#fee090` analytical fill appears; 390 px has no horizontal overflow.

## 2. Studies

- `app/astro.config.mjs` — `remarkStripLeadingH1` removes each study’s leading markdown `# Title` before rendering, so the article shell owns the only `<h1>`. The TOC also drops depth-1 entries.
- `app/src/components/studies/lib/studies.ts` (pure, unit-tested) — study card type, category/persona labels, text/topic/audience filtering and the per-study evidence decision.
- `app/src/components/studies/StudiesLibrary.tsx` — search by title/description/slug, topic filter, audience filter based on published persona frontmatter, result count (`N of 15 studies`) and a no-match state; no readership or coverage score.
- `app/src/pages/analytics/index.astro` — the invented **“11 Years” Data Coverage KPI is gone**; counts are derived from the collection (15 studies, present topics, studies under unit review). Persona cards, every article URL and the research cross-links remain.
- `app/src/pages/analytics/[slug].astro` — publication date, reading time, technical level and category; an evidence panel; the lease study gets “Unit review required” and **no chart is drawn** from its PSM/PSF tables (the tables stay readable); other studies keep their opt-in chart markers. Footer links to the observed explorer and catalog.

Verified: one level-1 heading inside `main` and none inside `article`; `findings` still renders its opted-in chart; `lease-decay` renders zero `.chart-container` elements and states the unit review.

## 3. Catalog

- `app/src/constants/catalog-audit.ts` — the S0-audited platinum row count as a **recorded observation**, not a live parquet read (a static build must not require local platinum files). Provenance: `docs/implementation/s0-baseline.md`.
- `app/src/pages/catalog/index.astro` — “Catalog snapshot, not a live run”, generation date and pipeline version; “available” is labelled as artifact presence, not correctness or freshness.
- `app/src/pages/catalog/[layer]/[...dataset].astro` — publication-vintage section on every dataset page, plus a discrepancy banner on `unified_dataset`: catalog `1,233,405 rows` beside inspected `1,234,928 rows`, both labelled, neither rewritten.
- `SchemaTable.tsx` — declared columns (schema nullable/constraints) are visually and semantically separate from observed columns (null count, null %, requiredness check); a `required · observed nulls` badge and a summary count surface the two `lat`/`lon` mismatches; table search has a real label; sorting is a `<button>` with `aria-sort`.
- `DatasetTable.tsx` — rows/columns/size are labelled “snapshot”, artifact presence replaces “status”, search has a label and sort headers are keyboard buttons.
- `DatasetHeader.astro` — row/column counts say “catalog snapshot”.

Unchanged deliberately: catalog IDs, nested external slug conversion (`external__BusStops` → `/catalog/bronze/external/BusStops`), DAG, dataset routes, upstream/downstream link targets and the absence of any raw-record download.

## 4. Verification

| Check                                                     | Result                                                                                                                                                                                                                                                  |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bun run test:unit`                                       | **306 pass, 0 fail, 20 files** (+20: studies filters 8, map archive 12 — baseline 286)                                                                                                                                                                  |
| `bun run astro check`                                     | **3 errors / 0 warnings / 24 hints / 182 files** — no finding in an S9 file. Errors fell 20 → 3 (deleted overlay components, rewritten analytics index, fixed `PriceMap` style typing); the 3 are pre-existing `PersonaHeader`/`leaderboard.astro` debt |
| `bun run validate-data`                                   | passes: 19 assets, release `0e1013ee485f` (7 assets)                                                                                                                                                                                                    |
| `bun run build`                                           | passes: **201 pages** (was 200; `/research/map` added); `catalog.jsonl.gz` restored afterwards                                                                                                                                                          |
| Playwright (preview, full suite)                          | **182 pass, 0 fail** (baseline 163: +9 research-map, +6 catalog, +3 studies/article assertions; the old overlay test was rewritten deliberately)                                                                                                        |
| `uv run pytest tests/test_export_app_data.py --no-cov -q` | **44 pass** (no exporter change)                                                                                                                                                                                                                        |
| `uv run ruff check`                                       | clean                                                                                                                                                                                                                                                   |
| Prettier                                                  | `bunx prettier@3.4.2 --write` on changed JS/TS/JSON/markdown (`.astro` is outside the hook’s `types_or`)                                                                                                                                                |
| `git status` after verification                           | no published asset modified; no `bun.lock` change; catalog restored                                                                                                                                                                                     |

## 5. Gaps deliberately left open

- **The catalog audit count is a recorded observation**, not a build-time parquet read, so it does not update automatically. Regenerating the catalog should update both numbers and the audit constant together.
- **`unified_dataset.lineage.upstream` contains a self-edge** in the generated catalog (`unified_dataset` → `unified_dataset`); the page displays the catalog as generated. This is a catalog-generator issue, not a UI one.
- **The lease study’s tables are unchanged.** S9 withholds the chart and states the unit review; repairing the PSM/PSF values is an owner decision.
- **The research map still needs map tiles** for its base layer; no geometry-only mode was added. Observed geometry and archive inspection work independently of tile availability.
- **DAG keyboard access** relies on focusable node links and the React Flow zoom controls; node dragging has no keyboard equivalent. Full graph keyboard navigation belongs to S10.
- **`PersonaHeader.tsx`** remains the two-error pre-existing dead file recorded as S8-F5.

## 6. Next

**S10** (integration and release readiness) is next: full build/preview/E2E at root and Pages base, route/query compatibility, keyboard/dialog and mixed-generation tests, payload/hydration measurements and the final debt report. No S9 surface changed a published data asset, so S10 can test the current release generation as-is.
