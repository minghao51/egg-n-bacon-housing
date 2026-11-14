# Reporting refresh — full implementation map

- **Date:** 2026-11-12
- **Status:** Draft — proposed execution contract, not implementation approval or completion evidence.
- **Scope:** Correctness, current observed metrics, historical report editions, and transparent area activity.
- **Inputs:** [Audit](../implementation/2026-reporting-refresh-audit.md), [existing implementation ledger](../implementation/README.md).
- **Execution:** [Slice handoffs](2026-11-12-reporting-refresh-handoffs.md).
- **Research work list:** [Study and asset register](2026-11-12-reporting-refresh-research-register.md).

## 1. Outcome and non-goals

Deliver a coherent path: **current observed snapshot → comparable areas → area fieldnote → dated research**. Readers must know which population, property type, months, source release and method support every figure.

Success means:

1. No selected property/year label can conceal numbers from a different population.
2. Latest completed observations are prominent without deleting 2025 or calling partial 2026 a full year.
3. Historical research remains accessible with original results, figures and dates; approved new editions are distinguishable from editorial updates.
4. Area activity shows observed sales and price movements with coverage/sample caveats, not fabricated buyer demand or investment advice.
5. Exporter, frontend, tests and deployment agree on one verified release per comparison.

**Not included by default:** portal scraping or challenge bypass; listing/enquiry/days-on-market feeds; investment/BUY scores; segment-weight changes; new loan-eligibility policy; automatic lease/MRT/forecast model promotion; broad refactoring; a replacement production pipeline. No downloads, source refresh, model fitting, deployment or commits are authorized by this planning document alone.

## 2. Starting evidence and constraints

The audit measured dashboard generation `0e1013ee485f…`, exported 2026-11-03, monthly series through **2026-10**, and last completed year **2025**. Overview full-history aggregates also contain a partial November bucket. These scopes are intentionally different.

Current local platinum inputs and manual-source GeoJSON are absent. The published planning-area assets exist. New observations cannot be certified merely by changing an export cutoff or the browser's date. Large published private/EC count differences require reconciliation before market-growth headlines.

Existing baseline: 334 frontend unit tests; Astro 0 errors / 0 warnings / 22 hints; 19 required data assets validated and seven v1 dashboard assets generation-verified. These are historical audit observations to remeasure at RF00, not promised counts after implementation.

Binding rules:

- Follow `AGENTS.md` and applicable `.agents/skills/` checklists. Python execution is `uv run …`; Bun is pinned to 1.2.23.
- Production pipeline remains `main.py → build_pipeline() → run_pipeline()` with dependency injection. New silver/gold/platinum outputs use `LayerWriter` companions and registry/stage alignment.
- The app exporter remains the supported maintenance boundary over platinum outputs. Do not create an ad-hoc source-fetching frontend generator.
- Keep missing values distinct from zero; never synthesize unavailable estimates or average medians into a different population.
- Preserve archive/model gates, financing privacy, base-path links, failure/retry semantics and keyboard accessibility.
- No commits without explicit instruction. Do not print `.env`, tokens or credentials. Do not erase caches to make a refresh appear fresh.

## 3. Decisions to ratify at RF00

Recommended defaults are specified so workers do not invent policy. Record approval or a replacement in the [decision ledger](2026-11-12-reporting-refresh-decisions.md) before the affected slice starts; this section defines the decisions, the ledger holds the signatures.

| Decision                      | Recommended direction                                                                                                                                                            | Approval/stop rule                                                                                                                            |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| D01 publication migration     | Separate **v2 sidecar**, immutable generation-specific payload paths; retain v1 seven-file/schema contract and old URLs                                                          | Coordinator ratifies before RF04; no in-place `1.0.0` reinterpretation                                                                        |
| D02 initial cutoff            | Start from audited **2026-10**, advance only on measured source-completeness evidence                                                                                            | Data owner approves per scope; missing inputs/unknown coverage block promotion, not fixture-based development                                 |
| D03 period defaults           | Dashboard snapshot: YTD; trends: trailing 12 completed months; explorer/rankings: trailing 12 completed months. All resolved from selected release                               | Product/coordinator ratifies; explicit old bookmarks remain pinned                                                                            |
| D04 geography                 | Use five actual planning regions in observed rankings; keep CCR/RCR/OCR out unless an authoritative crosswalk is separately adopted                                              | RF01 uses its own type; do not redefine archived segment geography                                                                            |
| D05 ranking and samples       | Raw count/median rankings use a 150-sale caution threshold in the selected window; change rankings require both compared windows to qualify. Thin rows remain viewable, unranked | Ratify as a product caution rule, not significance/confidence. RF09 labels/threshold calibration can tighten it; do not silently relax for EC |
| D06 supported current metrics | Initially transaction count, transaction median price and median per-transaction PSF; scoped comparisons only when comparator coverage qualifies                                 | Other legacy rank IDs remain link-compatible but unavailable until their joint contract is supplied; no mixed-window fallback                 |
| D07 research archives         | Publication edition and observed period are separate. Keep stable series URLs plus immutable explicit archive routes                                                             | RF07 must preserve verbatim historical material and review gates before replacing any results                                                 |
| D08 area fieldnotes           | Keep static/no-JS fixed-scope fieldnotes; add a small accessible selector over verified embedded per-area sections to honor query selection                                      | Ratify before RF06; no claim that a static query string changes build-time numbers                                                            |
| D09 activity MVP              | Separate count/price signals and numeric comparisons; no composite hotness score or BUY label                                                                                    | Direction labels only after RF09 calibration/review; stock normalization needs a validated stock/geography source                             |
| D10 acquisition/publication   | Separate permission for R2/source access, a refresh run, research reruns and deployment                                                                                          | Owner records allowed operations. Never infer access from configured environment variables                                                    |
| D11 coverage acceptance       | Source-specific evidence policies and a per-scope publish/limited-display/withhold ledger, defined in §5.6                                                                       | Ratify policy IDs at RF00; data steward signs actual RF03 evidence before current-use promotion                                               |
| D12 research sign-offs        | Separate source/cutoff, independent scientific and release approvals, defined in §7                                                                                              | No author self-approval or automatic approved-edition pointer change                                                                          |

## 4. Slice map and dependencies

**Current state:** RF00 is complete — [baseline report](../implementation/2026-11-12-rf00-baseline.md) — and D01–D12 are **accepted** in the [decision ledger](2026-11-12-reporting-refresh-decisions.md). **RF01** ([report](../implementation/2026-11-12-rf01-leaderboard-report.md)) and **RF02** ([erratum](../implementation/2026-11-12-rf02-errata.md)) are complete in code and verified, not deployed. **RF03** ([report](../implementation/2026-11-13-rf03-source-reconciliation.md)) completed source restoration and a candidate release; nothing is published, and private/EC 2026 scopes are withheld pending one reconciliation question. **RF04 is complete** ([report](../implementation/2026-11-13-rf04-v2-period-pack.md)): pipeline emitter, client resolver, verified-byte loader, `validate-data` v2 checks and the rollout switch. **The v2 pack is now published** (republished by RF09 as generation `2c30e2aa…`, cutoff 2026-10; the RF04 generation `6cd4510f…` is retained) next to the untouched v1 release. **RF09 is complete** ([report](../implementation/2026-11-14-rf09-area-type-month-history.md)): `rolling3` periods plus one verified monthly-history payload per property type in that single generation, schema `2.1.0`, with the activity calibration recorded and no directional label shipped. **RF05 is complete in code:** the dashboard overview renders the verified YTD/latest-month strip, `/research/trends` + `/explore` render published windows, both the explorer's list/map/table and Compare Areas read the pack for a concrete published period (legacy eras kept as a labelled group, limited-display scopes unranked), and D03's bare-URL defaults + migration notice ship behind `PUBLIC_OBSERVED_RELEASE` in [report](../implementation/2026-11-13-rf05-current-periods.md) §9. The switch flip itself is a release action gated on RF06 (fieldnotes/tools still read v1 periods). RF03 and research publication additionally have known external/data/approval gates. Dependencies below distinguish implementation with fixtures from real-data promotion.
**RF06 is complete for the fieldnote scope** ([report](../implementation/2026-11-13-rf06-fieldnotes.md)): `/areas/<slug>` selects among its published joint sections in place, states its fixed no-JS scope, keeps the historical ∪ current identity union with a build-time slug-collision guard, and shares one explorer return-link allow-list that now carries concrete published periods. Tools/archived model contracts unchanged; the pack's per-area activity slices remain RF10.
**RF11 is complete** ([report](../implementation/2026-11-13-rf11-catalog-report.md)): the catalog was regenerated from the current platinum build and the recorded audit reconciled, with the earlier S0 discrepancy preserved in `CATALOG_AUDIT_HISTORY`; the asset-disposition table (v1 frozen, v2 published, catalog regenerated, unused affordability extract retained) is ready for RF12.
**RF07's core is complete** ([report](../implementation/2026-11-13-rf07-editions.md)): RF00's frozen sources are now a separate collection behind a validated register, `/analytics/archive/<year>/<edition>/<slug>` renders 15 editions with their own identity/evidence status (withheld-chart gates carried over), and each series entry says no approved refreshed edition exists. RF08 remains blocked on the three recorded sign-offs.
**RF05 is complete** ([report](../implementation/2026-11-13-rf05-current-periods.md) §10): `PUBLIC_OBSERVED_RELEASE=v2` ships, `/explore` adopts the published window with the migration notice, Compare Areas keeps its ranked default (the `all` scope is still limited-display), and the URL serialiser pins concrete windows. **RF08 is blocked by its own approval rule** ([readiness](../implementation/2026-11-13-rf08-readiness.md)): the independent scientific reviewer is not available here, so no refreshed edition was invented.

| ID   | Deliverable / accountable role                                                                     | Requires                                                   | Ready-to-exit evidence                                                                                                                                                                                                                                                                                                                    |
| ---- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RF00 | Baseline preservation, contract ratification, ownership — coordinator                              | None                                                       | **Preservation done:** [baseline report](../implementation/2026-11-12-rf00-baseline.md), frozen edition manifest and verifier, joint-metric fixture. **Outstanding:** D01–D12 ratification and named owners                                                                                                                               |
| RF01 | Correct scoped area rankings and geography — observed frontend owner                               | RF00                                                       | **Done:** [report](../implementation/2026-11-12-rf01-leaderboard-report.md) — Punggol reads S$672,000/1,538 from the joint section, five planning regions, 150-sale caution, unsupported metrics report a reason                                                                                                                          |
| RF02 | Editorial safety and study chart repair — content/chart owner                                      | RF00                                                       | **Done:** [erratum](../implementation/2026-11-12-rf02-errata.md) — unsupported 79%/15×/4×/35% claims removed, charts render (bars verified in DOM), unit-split axes, missing series explained, lease gate intact                                                                                                                          |
| RF03 | Source restoration and reconciliation evidence — data owner                                        | RF00; acquisition permission                               | **Done:** [report](../implementation/2026-11-13-rf03-source-reconciliation.md) — 18,084 objects restored, pipeline green, candidate `9605fceca35c…`; HDB approved, EC/condo limited-display pending URA grain question                                                                                                                    |
| RF04 | V2 periods, exporter and verified-byte adapters — data-contract owner                              | RF00 for code; RF03 for real publication                   | **Pipeline side done:** [report](../implementation/2026-11-13-rf04-v2-period-pack.md) — 8 periods, 1,472 observations, generation `6cd4510f…`, 30 tests, v1 untouched. Complete: emitter + resolver + verified loader + `validate-data` v2 + `PUBLIC_OBSERVED_RELEASE` switch; pack unpublished                                           |
| RF05 | Current dashboard, trends and explorer — observed frontend owner                                   | RF01, RF02, RF04                                           | **Complete** ([report](../implementation/2026-11-13-rf05-current-periods.md)): v2 is the shipped mode; explorer opens on the published window with the migration notice; Compare Areas keeps its ranked default until `all` is publishable; concrete windows are pinned in URLs                                                           |
| RF06 | Fieldnotes, tool references and route compatibility — area/tools owner                             | RF05                                                       | **Fieldnote scope complete** ([report](../implementation/2026-11-13-rf06-fieldnotes.md)): query-selected sections update values/labels/provenance together, no-JS scope stated, route union keeps historical + current identities with collision detection, one return-link allow-list. Pack per-area slices defer to RF10                |
| RF07 | Publish immutable research editions and archive routes — research frontend owner                   | RF00, RF02                                                 | **Core complete** ([report](../implementation/2026-11-13-rf07-editions.md)): separate frozen-edition collection, validated register (identity/evidence status/publication year), 15 archive routes with gate carry-over, series entries state `no approved current edition`. RF08 needs independent sign-offs                             |
| RF08 | Refresh research one registered job at a time — named researcher + independent scientific reviewer | RF03, RF07, per-job method approval                        | **Blocked (by design)** ([readiness](../implementation/2026-11-13-rf08-readiness.md)): gates and the three sign-offs are documented per job; no refreshed edition was produced or promoted without the independent reviewer                                                                                                               |
| RF09 | Area-type-month data and activity mathematics — data-contract owner                                | RF04; RF03 for promotion                                   | Dense monthly publication, true-zero/missing distinction, scoped comparisons and sample/coverage gates; manifest hashes verified                                                                                                                                                                                                          |
| RF10 | Area activity map/list/fieldnote UI — observed frontend owner                                      | RF05, RF06, RF09                                           | Map/table/detail parity, preserved scope, clear denominators and no unsupported demand/score claims                                                                                                                                                                                                                                       |
| RF11 | Catalog/reference reconciliation and asset disposition — catalog/data owner                        | RF03; archive preservation from RF00                       | **Complete** ([report](../implementation/2026-11-13-rf11-catalog-report.md)): catalog regenerated from the current platinum build (125 datasets, 2333 edges, `unified_dataset` 1,236,310 rows), audit reconciled with the S0 finding kept as history, asset disposition recorded for RF12. No geometry/reference change, no asset removal |
| RF12 | Integration, release gates and repeatable refresh operations — release owner                       | RF00 to build harness; target-specific completed set below | Root/Pages tests, candidate hashes, archive preservation, performance/security checks, rollback and release evidence                                                                                                                                                                                                                      |

### Execution graph

```text
RF00 ─┬─ RF01 ───────────┐
      ├─ RF02 ───────────┼─ RF05 ─ RF06 ──────────┐
      ├─ RF04 (fixtures) ┘                       ├─ RF10
      ├─ RF03 ─ RF04 (data candidate) ─ RF09 ───┘
      │       ├─ RF11
      │       └─────────────┐
      └─ RF02 ─ RF07 ──────┴─ RF08 (per-study approvals)
RF12: gate each milestone independently; no requirement to finish every model.
```

RF03 does not approve data simply because RF04 compiles. RF04/RF09 share an exporter owner and must serialize exporter changes. RF05/RF06/RF10 likewise sequence shared observed adapters and links. RF07 may run alongside observed UI after RF02; separate content loader/routes from observed-contract files.

### Independently shippable milestones

- **M0 — Correctness:** RF00–RF02 + RF12 M0 gate. Uses current assets. No source refresh needed.
- **M1 — Current observations:** M0 + RF03–RF06 + RF12 M1 gate. Publish only source-approved property scopes; unavailable scopes remain explicit. RF08 is not a prerequisite.
- **M2 — Research history:** RF07 + RF12 M2 gate; approved RF08 jobs may ship incrementally. Archive migration alone must not claim research was refreshed.
- **M3 — Area activity/reference update:** M1 + RF09–RF11 + RF12 M3 gate. Individual activity/reference changes can be gated separately; no unknown source scope may ride along.

M0 can proceed while RF03 is blocked. M2 can preserve historical research without current source inputs. No milestone requires reviving every retired study.

## 5. Data and compatibility contract

### 5.1 V1 remains a valid historical/compatibility experience

Keep `dashboard-release.json` at its existing schema and exactly seven exporter-owned payloads. Do not append research or v2 files to it. Keep `year_2025`, `whole`, `pre_covid` and `recent` meanings unchanged; `recent` must not become trailing 12 months.

Baseline historical files are pinned in RF00. Future approved source corrections may change a regenerated historical statistic, but that requires a visible revision and a preserved previous snapshot—not a promise that all re-exports are byte-identical forever.

### 5.2 Proposed v2 publication shape

Names below are **planned new artifacts**, not existing files:

- `app/public/data/dashboard-release-v2.json`: small discovery manifest/pointer.
- `app/public/data/observed/<generation>/periods.json.gz`: immutable descriptors, source coverage, units/method references and scope availability.
- `app/public/data/observed/<generation>/summary.json.gz`: national and area joint aggregates keyed by concrete period/property identity.
- RF09 publishes a **new complete pack**: periods, summary and every declared per-property `area-monthly-<property>.json.gz` payload, all under one new generation. Rebuild periods/summary from the same approved inputs, or copy their verified unchanged bytes into the new pack when inputs/semantics truly match. Never publish a monthly-only manifest or mutate an older pack. RF10 verifies this single complete release identity for summary, history, map, table, downloads and fieldnotes.

Use deterministic compressed/content hashes, relative safe paths, input identities, explicit inclusion/exclusion rules and one generation over the actual v2 artifacts. A `legacyGeneration` lineage reference does not authorize cross-generation arithmetic. If any v1 bytes are reused, their exact hashes and compatible semantics must be incorporated into the v2 contract.

Avoid a circular generation hash: deterministic payloads do not embed their own generation/path or export timestamp. Compute generation from schema/method/input/coverage identities and role-keyed payload content hashes, then assign immutable paths and record actual gzip/content hashes in the manifest. Consumers attach the verified manifest generation to observation objects. Specify one canonical serialization algorithm with Python/JS golden vectors; recomputation must detect payload, role, path and contract tampering.

No model/research files join this release merely because their extraction date is recent. `app/public/data/manifest.json` and `app/scripts/validate-data.mjs` need deliberate v2 validation support while retaining their v1 checks.

### 5.3 Period descriptors

Each concrete period has `id`, `kind`, `startMonth`, `endMonth` (inclusive), `label`, `comparatorId` or null, and declared availability by property/metric. IDs are opaque but validated; do not widen a union to unrestricted user strings.

Recommended concrete examples at the audited cutoff:

| Kind                    | Concrete example ID | Months          | Comparator                                                             |
| ----------------------- | ------------------- | --------------- | ---------------------------------------------------------------------- |
| Month                   | `month_2026_10`     | 2026-10         | `month_2025_10` for YoY; separately named September descriptor for MoM |
| YTD                     | `ytd_2026_10`       | 2026-01–2026-10 | `ytd_2025_10`                                                          |
| Trailing 12 months      | `ttm_2026_10`       | 2025-11–2026-10 | `ttm_2025_10` (2024-11–2025-10)                                        |
| Trailing quarter (RF09) | `rolling3_2026_10`  | 2026-08–2026-10 | `rolling3_2025_10`                                                     |
| Completed year          | `year_2025`         | 2025-01–2025-12 | `year_2024` if supported                                               |

Also retain explicitly labelled legacy historical windows. Friendly `latest`/`ytd`/`ttm` aliases may resolve through the loaded release, but written share links use the concrete resolved ID. Preserve explicit old periods and explain unavailable explicit requests instead of silently changing them.

**Bare-URL migration is intentional:** on v2 activation, bare observed routes adopt D03's defaults. Show the exact active window and an “updated default” notice with links to the route's previous explicit window (dashboard all-history, explorer/trends 2025, leaderboard 2022 onward). Previously omitted defaults cannot be recovered from a bookmark; do not pretend otherwise. Newly shared links always include the concrete period. Specialized archive/tool compatibility wrappers do not inherit a new observed default silently. Test this migration in both root and Pages builds.

All periods derive from the approved cutoff, not wall-clock time. At a December cutoff, that year may be complete; before a new approved January release, do not invent an empty new-year YTD. Twelve rows are not proof of completeness: source/type coverage is required. Reject invalid months, reversed bounds, duplicate IDs, unknown references and unsupported schema versions.

### 5.4 Observation values and metric dictionary

Each observation identifies `generation`, `periodId`, `propertyType`, geography (national or canonical area ID), metric, unit, value, sample/coverage status and provenance. Comparator values carry the same identity with their own period ID.

- `transactionCount`: count of approved deduplicated unit-sale records at the business grain settled in RF03. Do not mix aggregated multi-unit records with unit transactions or infer units from rows. Retain raw-record diagnostics separately.
- `medianPrice`: transaction-level median price in nominal SGD over the stated scope; publish the price-observation count.
- `medianPsf`: median of valid per-transaction price-per-square-foot observations; publish its own eligible count. Not median price divided by median floor area.
- Count/price/PSF change: `100 × (current / comparator − 1)`, only with compatible population/window/method and eligible nonzero comparator. No annualization or index/causal claim.
- Positive count growth means more included observed transactions, not proven buyer demand, liquidity or investment opportunity.

Use explicit states such as `available`, `no-sales`, `missing-source`, `partial-coverage`, `thin-sample`, `not-comparable`, `not-published`. Numeric null remains null. A verified complete zero-sales month can show **0 transactions** with null prices; an absent month cannot. Keep legacy v1 all-zero sentinel handling isolated in its adapter.

Separate source `observedThrough`, `sourcePublishedAt`, retrieval/export time, `completeThrough`, and code/method version. Unknown publication dates remain null. Enforce the source-specific publication dispositions in §5.6 for display, comparison and ranking; no UI may locally waive a coverage rejection.

### 5.5 Verified-byte loading, failure and staged rollout

Verification must cover the exact decoded bytes displayed, not an earlier request to the same mutable URL. Return parsed data from the verifier or use immutable generation paths and verify each consumed response. Include canonicalization tests for booleans, Unicode, nulls and Python/JS generation parity; the existing Python sanitizer currently treats booleans as integers.

Rollout:

1. Deploy v2 parsing and disabled/absent-v2 capability with fixtures; continue v1 safely.
2. Stage an approved v2 candidate outside the published directory and verify it.
3. Publish immutable generation paths, then discovery manifest last; verify deployed bytes/base path before enabling current views.
4. Select one observation version consistently across the observed surfaces in a build/release; no global default flip while fieldnotes/tools still silently use a conflicting period.
5. Missing v2 may offer the explicitly labelled v1 view. Invalid/mismatched v2 never silently replaces requested v2 values with v1. Retain the last verified displayed data after failed refresh, with error/retry.

Rollback selects the previous complete manifest/build and corresponding immutable assets; never overwrite only one member of a pack. Retain historical edition references and avoid deleting generations until reference/retention policy is verified.

### 5.6 Source completeness and publication disposition

RF00 ratifies source-specific acceptance policy IDs; RF03 records and obtains approval for actual evidence. There is no universal percentage threshold or inference that a quiet last month is complete. Each policy must specify required acquisition resources/batches/pages, authoritative cutoff/completeness evidence, business-key/overlap reconciliation, unit grain, quarantine/exclusion accounting and acceptable geographic assignment coverage. Record expected counts or source benchmarks where available; when unavailable, the policy must name the alternative authoritative evidence and its limitations. Unexplained private/EC count discontinuities do not pass by virtue of schema validation.

The required ledger key is `(source set, property type, geography/population, period)`; record policy ID, input hashes, evidence references, cutoff, unresolved discrepancies, allowed operations, named data-steward approval/date and limitations. Disposition is one of:

- **Publish current:** every source required for that scope passes its documented policy; dates/grain/overlaps/exclusions reconcile. Current KPI display is allowed. Comparison additionally requires both periods and metric-specific samples/denominators to qualify; ranking requires D05. A missing comparator withholds the change, not an otherwise verified current count.
- **Limited historical/diagnostic display:** coverage is partial or unknown but existing values are safe to inspect with explicit dates/missingness. No current KPI, comparative headline, activity colour or rank; link to a separately labelled historical/diagnostic view.
- **Withhold:** failed/missing inputs, invalid grain/units, unresolved empirical-versus-synthetic lineage or unverified bytes make numerical display unsafe. Show reason and, where available, a distinctly labelled previous verified release.

National **All** requires all constituent sources/property populations to pass. An independently approved HDB scope may publish while EC/condo remain limited/withheld; it cannot make the All scope complete. Local completeness also requires the policy's geography-assignment checks; national completeness does not prove all records mapped into every area. Source publication time may remain unknown only if the documented completeness policy has sufficient other evidence. RF04 exports these dispositions; RF05/RF09/RF10 enforce them rather than inferring confidence from row counts.

## 6. Surface-by-surface change and ownership map

| Surface                     | Planned change                                                                                                     | Primary slices / existing seams                                        |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| Home                        | Remove “live”/unsupported teasers; publish scoped latest-approved highlights and named change statistic            | RF02, RF05; `app/src/pages/index.astro`, persona content               |
| Dashboard                   | YTD default, latest completed month and freshness strip; distributions state whether they follow scope             | RF05; `MarketOverviewDashboard.tsx`, dashboard charts/page loader      |
| Monthly trends              | TTM default, month/YTD/year windows and matched prior-year count comparison; gap-preserving charts/table           | RF05; `trend-series.ts`, `TrendsWorkspace.tsx`                         |
| Explorer                    | Shared descriptors/verified values, scoped ranks, explicit URL IDs and accessible map/table                        | RF05/RF10; explorer workspace/selection/data adapters                  |
| Compare Areas               | Joint metrics, actual planning regions, scoped eligibility, null-last sorting; no mixed-window growth fallback     | RF01 then RF05; leaderboard hook/types/components                      |
| Area fieldnotes             | Preserve historical slug union; embed verified per-area slices, fixed-scope no-JS rendering and enhanced selection | RF06/RF10; `area-page.ts`, `area-links.ts`, `pages/areas/[slug].astro` |
| Financing reference         | Replace named 2025 reference only with explicitly selected supported period; user-edited price stays manual        | RF06; tool reference/draft/workspace modules; no new eligibility logic |
| Research segments/map/tools | Keep archive contracts and nine model-layer gates; observed fills can migrate independently                        | RF06/RF07; segment/tool evidence and map archive modules               |
| Studies/personas            | One series card, explicit editions, evidence status and observation cutoff; safe recommendations                   | RF02/RF07/RF08; collection/schema, study evidence and analytics routes |
| Catalog/reference           | Measured new snapshot plus old audit evidence, geometry/source vintage and documented asset disposition            | RF11; catalog generator/audit constants/tests                          |
| Compatibility routes        | Preserve `/dashboard/{leaderboard,map,segments,trends}` and all existing query dialects                            | RF06/RF12; page wrappers, nav, URL adapters                            |

**Shared-file rule:** coordinator assigns one writer at a time for `scripts/export_app_data.py`, `app/src/content.config.ts`, shared observed/release/URL types and utilities, data URL constants, manifests, navigation, package/config files and CI. A downstream worker requests a contract change instead of editing another slice's source of truth.

## 7. Research edition architecture

Maintain root `docs/analytics/*.md` as the current legacy/canonical source surface until explicit migration. Add a **separate edition collection**, not a recursive replacement of the existing glob. Reserve `archive` and `personas` route prefixes; reject duplicate or conflicting series/edition IDs.

Planned archive route: `/analytics/archive/<publication-year-or-undated>/<edition-id>/<series-slug>`. `/analytics/<slug>` remains the stable series entry and renders/links the explicitly selected approved edition. If none is currently validated, show historical/under-review status rather than selecting the newest timestamp automatically.

Preserve original root report bytes in a frozen edition source during RF00 before safety edits; pin existing referenced figure/data bytes and prohibit overwrites. RF07 gives these frozen sources a validated evidence registry/collection. New editions use new source/asset paths. Evidence metadata must have one authoritative registry/schema, with no competing hand-maintained dates in cards, persona copy and content adapters.

Required evidence fields: series/edition identity; declared publication versus known/unknown actual date; observation range; source cutoffs; method and data generation; unit/sample/limitations; review/validation state; model training/issue/target dates if applicable; source/figure hashes; supersedes/errata links. Keep legacy editorial `status` separate from evidence status so archive metadata does not bypass validators.

A new approved edition requires three recorded sign-offs: **source/cutoff** by the data steward under §5.6, **scientific validity** by a reviewer who did not author/fit the evaluated result, and **publication** by the release authority against the exact accepted artifacts. The analyst may prepare the source ledger but cannot approve their own cutoff; the source steward may also be release authority if documented. The scientific reviewer cannot be that edition's publication approver. Frontend/schema acceptance substitutes for none of these; absent independent review keeps the edition archived/under review.

Apply lease/unit/model gates by **series + edition evidence**, not a literal old slug alone. Archive rendering may retain original text with a prominent erratum/status panel; canonical/persona promotional copy must not repeat unresolved claims as current advice. See the research register for all RS/RA jobs.

## 8. Area activity product contract

RF09/RF10 extend the existing explorer and fieldnotes; do not create a competing “hotness dashboard.” Initial views show:

- Rolling-quarter count, same-quarter-prior-year change and both denominators.
- TTM count and coverage/sample status.
- Observed median PSF change with size/lease/location/mix caveats.
- Per-property monthly sparklines, table/download and links preserving the selected area/property/period.

Publish dense month grids with independent coverage status; zero-fill only proven complete no-sales scopes. Calculate period medians from underlying transactions, not a monthly-median average. Scope exclusions/national populations exactly as the release describes. A current area's absence does not delete its historical route.

Calibrate any directional label thresholds after examining distributions, source revisions and stability. Use neutral numeric labels until approval; no weights, investment recommendation or significance claim. Stock-normalized turnover needs a validated stock denominator and geography/property crosswalk and is deferred.

PropertyGuru/99.co access was blocked during the audit; EdgeProp's visible property/time/price/volume separation is design inspiration only. Portal data acquisition, partnerships or screenshots require a separate permitted-access task; no scraping dependency belongs on the MVP critical path.

## 9. Release acceptance and operations

RF12 owns the evidence per milestone, not a claim that every research job is complete.

### Common checks

- Frontend: pinned Bun install, unit tests, `astro check` (no added errors/warnings/hints in touched files), data validation and production build.
- Data boundary: exporter pytest, Ruff and format checks; deterministic fixture/export hashes, v1/v2 contract parity, source coverage/duplicates and cutoff evidence.
- Hamilton/ingestion changes: all skill-specific tests, registry/stage/schema/docs alignment, mypy as applicable; default tests mocked, never dependent on live services.
- Browser: root and GitHub Pages base, deep-link initial state/back-forward, missing/mixed release, offline/error/retry, keyboard/map-table parity and no-JS scope. Follow the Playwright skill and record actual console/network results.
- Research: archive source/asset hashes, route uniqueness, review gates and job-specific scientific acceptance. Schema tests alone do not certify a finding.
- Performance: baseline payload/props/islands before adding activity charts; lazy property-specific history, no new chart library by default. Measure changed routes and set explicit budgets at RF00 rather than silently increasing them.
- Operational: secrets absent, no income serialization/logging, dependency/lock changes justified, no accidental generated catalog diff, deployment/rollback evidence recorded.

### Refresh runbook to implement

1. Inspect supported CLI/help and source readiness; obtain required operation permission.
2. Restore documented manual/geocode inputs as authorized, without printing secrets or indiscriminately clearing caches.
3. Run supported pipeline with declared intended source refresh; preserve valid bronze caches on errors/empty responses.
4. Reconcile business grain, source coverage and completed-month boundary by property type; approve the release candidate's supported scopes.
5. Export to a temporary candidate directory using an explicit `--last-complete-month`; verify v1 compatibility, v2 hashes, source identities and scientific/report dependencies as relevant.
6. Review statistic changes and source/method revisions. Regenerate catalog/audit evidence only in its authorized slice; unapproved research remains archived.
7. Build/test root and Pages releases; restore incidental `app/public/data/catalog.jsonl.gz` changes from ordinary builds only when they are not the authorized catalog work.
8. Promote immutable payloads and manifest/build together, smoke deployed bytes, and record rollback target. Scheduling/cadence and automatic deployment require separate approval; this plan does not install recurring jobs.

## 10. Definition of done and next handoff

Each slice reports: exact scope/files, input generation, contract decisions, tests and counts, manual checks, changed assets/hashes, current blockers, approvals and next owner. A partial fixture implementation or blocked source run remains in progress/blocked; it is not “refreshed.”

**First execution assignment:** RF02 needs no decision and can start now. Record D01–D12 in the [decision ledger](2026-11-12-reporting-refresh-decisions.md) to open RF01 (D04, D05), RF04 (D01, D11), RF05 (D03, D06), RF06 (D08), RF07 (D07), RF10 (D09) and RF03/RF08/RF12 (D10, D12). RF00's preservation artifacts are in place; do not treat them as decision approval. Start RF03 only with acquisition permission. RF04 may proceed on approved synthetic fixtures while sources are restored; promote M1 only after RF03 and cross-surface integration pass. Use [the handoff pack](2026-11-12-reporting-refresh-handoffs.md) rather than implementing the entire program in one undifferentiated change.

## 11. Planning validation (2026-11-12)

Only planning documents/index links changed; no RF slice, source acquisition, pipeline/model run or deployment was executed.

- Documentation-layout and agent-skill validators, repository Ruff and `git diff --check`: passed.
- Planning link/anchor check: 41 local references passed; RF00–RF12 dependency graph is acyclic; 15 RS study jobs and 13 RA asset-family jobs accounted for.
- Active LSP check of the five changed/new planning/index documents: zero diagnostics.
- Pinned Bun install: no changes; existing frontend suite: 334 passed / 0 failed; Astro: 0 errors / 0 warnings / 22 existing hints.
- Independent planning review: initial execution ambiguities were amended; follow-up review found no remaining substantive blocker in the revised contract sections.
- These baseline checks do not demonstrate implementation of the proposed safeguards or resolution of the audit's existing defects. Actual slice acceptance remains future work.
