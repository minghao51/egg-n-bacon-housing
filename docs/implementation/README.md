# Implementation progress

**Next agent:** start with [`prompts/handoffs.md`](../../prompts/handoffs.md) — state snapshot, task queue, traps and verification for RF05 onward.

**RF09 complete (2026-11-14):** [area-type-month history](2026-11-14-rf09-area-type-month-history.md) — `rolling3` periods plus one verified monthly-history payload per property type in a **new complete v2 pack** (schema `2.1.0`, method `observed-aggregates-2`, generation `2c30e2aa836c…`); cells are positional arrays aligned to a per-type month grid so they lazy-load by property. Activity thresholds are calibrated in the report; **no directional label ships** (neutral numeric only) pending owner approval. RF04's generation is untouched.

**RF05 in progress (2026-11-13):** [current periods](2026-11-13-rf05-current-periods.md) — v2 pack published beside v1 (generation `6cd4510f…`); dashboard overview, trends, explore and Compare Areas render verified windows via the shared panel, the explorer's list/map/table and the Compare Areas rankings read the pack for a concrete published period (legacy eras kept as a labelled group, limited-display scopes unranked). D03's bare-URL defaults and the migration notice ship behind `PUBLIC_OBSERVED_RELEASE`; only the switch flip remains, and it is gated on RF06.
**RF05 complete (2026-11-13):** [current periods](2026-11-13-rf05-current-periods.md) — `PUBLIC_OBSERVED_RELEASE=v2` is the shipped build; `/explore` opens on the published window with the updated-default notice, Compare Areas keeps its ranked `recent` default until the `all` scope is cleared to publish (data-driven, §10.2), and the address-bar serialiser pins concrete windows (§10.3).
**RF06 complete for the fieldnote scope (2026-11-13):** [area selections](2026-11-13-rf06-fieldnotes.md) — `/areas/<slug>` keeps the whole identity union (historical + current), honours `?property=`/`?period=` for the sections it publishes, states its fixed build-time scope without JavaScript, and hands the explorer one return-link allow-list that accepts concrete published periods. Tools and archived model contracts unchanged.
**RF11 complete (2026-11-13):** [catalog report](2026-11-13-rf11-catalog-report.md) — catalog regenerated from the current platinum build (125 datasets, 2333 edges, `unified_dataset` 1,236,310 rows), audit reconciled with the S0 finding preserved in history, asset-disposition table recorded for RF12; no boundary or reference asset replaced and `affordability_metrics.json.gz` retained as unused pending approval.
**RF08 continuation brief (2026-11-14):** [the 13 studies that are still historical](2026-11-14-rf08-continuation-brief.md) — the register rows, the extra model/causal gate each one needs, the gate sequence proven by RS01/RS02, the registry mechanics, the traps that cost time twice, and a per-study definition of done. Written so a fresh agent can take one study without re-deriving the process.

**RF12 release evidence prepared (2026-11-14):** [candidate, disposition and rollback](2026-11-14-rf12-release-evidence.md) — v1 frozen at `0e1013ee485f…` (7 assets), v2 published at `2c30e2aa836c…` (6 roles, 570,224 bytes, cutoff 2026-10), post-build catalog pinned (`a67f2f6807f32c31…`), both approved editions named with their text hashes, full local + Pages verification recorded. **Not deployed:** the host `Content-Encoding` check and a real rollback both need deployment permission, and `affordability_metrics.json.gz` stays until a data-boundary decision.

**RF10 complete (2026-11-14):** [area activity](2026-11-14-rf10-area-activity.md) — `/areas/<slug>` publishes the rolling quarter, its prior-year quarter, the year-on-year change, the TTM context and the D05 floor verdict per property type, computed from the already-verified pack at build time (zero new bytes, no client fetch). Neutral numbers only: no label, score, colour-by-change or derived statistic; a verified `no-sales` window is an absence, never `0`. Explorer parity shipped in slice 2a: `activityForObservation()` is the one implementation of the quarter-to-quarter arithmetic and the D05 floor, so the list and the fieldnote cannot disagree, and a limited-display scope still shows activity numbers without being ranked. The fieldnote also loads a manifest-verified month-by-month history **on request only** (one property payload plus the manifest, never the core pair), keeping verified zeros distinct from missing source and offering retry; map colouring by activity is deliberately not built.

**RF08 complete for RS01 + RS02 (2026-11-14):** [editions signed off](2026-11-14-rf08-editions-signoff.md) — the two evidence packs ([RS01 source inventory](2026-11-14-rs01-source-inventory.md), [RS02 rental yields](2026-11-14-rs02-rental-yield-evidence.md)) carry the owner's source/cutoff signature, the refreshed editions (`data-sources-2026-11-14`, `rental-yields-2026-11-14`) were authored as **new** frozen sources with the RF00 originals untouched, an independent `gpt-6-luna` xhigh review of that text closed **PASS** after one FAIL round, and the owner signed publication. Both registry entries are now `approved`/`published` with three attestations and a matching `editionSha256` that the archive route re-verifies at build time. The other thirteen studies stay `historical`. RS02's fan-out defect remains fixed at source (`rental_yield.parquet` 1,749 rows, zero duplicates; `unified_dataset` byte-identical, so the v2 pack did not change).
**RF08 blocked (2026-11-13):** [readiness](2026-11-13-rf08-readiness.md) — per-job reconstruction gates and the three sign-offs are documented; no refreshed edition was produced because the independent scientific reviewer cannot be supplied by this session. A 2026-11-14 independent review (§6 of that report) confirmed nothing is signable today, corrected the claim that RF03 already supplied RS01's inventory evidence, and recorded the RS01 evidence pack as the smallest safe next action — it is a review record, not a sign-off.

**RF07 core complete (2026-11-13):** [editions + archive](2026-11-13-rf07-editions.md) — frozen sources are a separate collection behind a validated register; `/analytics/archive/<year>/<edition>/<slug>` renders 15 frozen editions with their own identity, evidence status and withheld-chart gates, and series entries state that no approved refreshed edition exists. RF08 (refreshed studies) needs the three sign-offs.

**RF04 complete (2026-11-13):** [v2 observed period pack](2026-11-13-rf04-v2-period-pack.md) — `scripts/v2_observed.py`, client resolver, verified loader, `validate-data` v2 checks, `PUBLIC_OBSERVED_RELEASE` switch.

**RF03 complete (2026-11-13, nothing published):** [source restoration and reconciliation](2026-11-13-rf03-source-reconciliation.md) — R2 data restored, full pipeline rerun, candidate release built in `/tmp`; HDB publishable, EC/condo 2026 withheld.

**RF02 complete (2026-11-12, not deployed):** [corrections and chart repair](2026-11-12-rf02-errata.md) — unsupported claims removed, comparison charts fixed, lease gate intact.

**RF01 complete (2026-11-12, not deployed):** [scoped area rankings](../plans/2026-11-12-reporting-refresh-implementation-map.md) — [report](2026-11-12-rf01-leaderboard-report.md). Compare Areas now reads joint `map_metrics` sections, uses the five planning regions, and ranks only rows with ≥150 sales.

**RF00 baseline preserved (2026-11-12):** [frozen historical sources and pinned assets](2026-11-12-rf00-baseline.md), verifier `scripts/tools/verify_reporting_baseline.py`, regression fixture `app/tests/fixtures/rf00-observed-contract.json`. Decisions D01–D12 remain open in the [decision ledger](../plans/2026-11-12-reporting-refresh-decisions.md).

**Proposed follow-on program (2026-11-12, Draft):** [reporting refresh implementation map](../plans/2026-11-12-reporting-refresh-implementation-map.md), [slice handoffs](../plans/2026-11-12-reporting-refresh-handoffs.md) and [research register](../plans/2026-11-12-reporting-refresh-research-register.md), based on the [reporting audit](2026-reporting-refresh-audit.md). RF00–RF12 are not started; these planning documents do not change the delivered S0–S10 evidence or authorize a source/model refresh. Start with RF00 preservation/contract decisions, then RF01/RF02 correctness work.

Status of the redesign defined in [`assets/svg/implementation-plan.md`](../../assets/svg/implementation-plan.md). Read this first; the plan is the contract, this file is the ledger.

Branch: `main` — slices S0–S6 are merged (PR #2, merge commit `8ab248a`); S7–S10 are implemented and pushed (`52c901b`, ignore follow-up `6aef15a`). GitHub Pages deployment is triggered by the push but has not been independently verified from this environment. Release evidence is in [s10-report.md](s10-report.md). The post-S10 carry-forward work (S10-F1 catalog props, S8-F1 financing persistence) is on `feat/s10-f1-s8-f1`, uncommitted. Published data assets were regenerated through **2026-10** in that merge (`app/public/data/*.json.gz` plus `dashboard-release.json`, generation `0e1013ee485f`).

## Slice status

| Slice | Scope                                                                                                    | Status | Report                           |
| ----- | -------------------------------------------------------------------------------------------------------- | ------ | -------------------------------- |
| S0    | Baseline, reproductions, route/query inventory                                                           | done   | [s0-baseline.md](s0-baseline.md) |
| S1    | Evidence boundary: joint-section adapter, fetch lifecycle, map URL state, overlay keys, tool containment | done   | [s1-report.md](s1-report.md)     |
| S2    | Publication compatibility manifest (`dashboard-release.json`) + build verification                       | done   | [s2-report.md](s2-report.md)     |
| S3    | Fieldnotes tokens, skip link, `aria-current`, mobile drawer accessibility                                | done   | [s3-report.md](s3-report.md)     |
| S4    | Honest dashboard overview + `/research/trends` monthly destination                                       | done   | [s4-report.md](s4-report.md)     |
| S5    | `/explore`: joint selection, list, threshold, pagination, URL state                                      | done   | [s5-report.md](s5-report.md)     |
| S5c   | `/explore`: SVG choropleth map + table view                                                              | done   | [s5c-report.md](s5c-report.md)   |
| S6    | `/areas/[slug]` fieldnote with build-time generation gate                                                | done   | [s6-report.md](s6-report.md)     |
| S7    | Segment discovery/investigation/comparison migration                                                     | done   | [s7-report.md](s7-report.md)     |
| S8    | Four-tool workspace with safe output states                                                              | done   | [s8-report.md](s8-report.md)     |
| S9    | Research-map archive, studies, catalog detail                                                            | done   | [s9-report.md](s9-report.md)     |
| S10   | Integration, regression, release readiness                                                               | done   | [s10-report.md](s10-report.md)   |

## Shipped surfaces

- `/explore` — joint property × period comparison, 150-sale caution threshold, list/map/table, fieldnote links, release-gated national baseline.
- `/research/trends` — monthly medians and volumes with gap-preserving charts and a full table.
- `/research/segments` — six stored research segments with weighted-fit matching, declared-area investigation and a two-to-four comparison; `/dashboard/segments` is the compatibility wrapper.
- `/areas/[slug]` — 41 static fieldnotes; national comparison rendered only when the build-time manifest verification passes.
- `/research/tools` — four tools with four output contracts: an illustrative financing scenario with a named observed 2025 reference, stored lease bands with signed statistics and the endpoint policy surfaced, MRT/CBD model inspection with the total withheld, and spatial label inspection only. `/dashboard/trends` is the compatibility wrapper.
- `/research/map` — observed transaction fill plus nine archived model layers for inspection only; per-layer source/status, uniform-placeholder and historical-forecast warnings, and no analytical polygon fill. `/dashboard/map` is the compatibility wrapper.
- `/analytics` — searchable studies library (text/topic/audience), one H1 per article, an evidence panel, and the lease study's chart withheld pending unit repair.
- `/catalog` — snapshot-vintage labels, the catalog-vs-inspected row discrepancy shown with both counts, and declared-requiredness separated from observed nullness.
- `/dashboard` — scoped 2025 medians from one asset, capability strip.
- Shell — Fieldnotes tokens, skip link, one `aria-current` per route, mobile drawer with focus trap and `inert`.

Legacy routes preserved: `/dashboard/{leaderboard,map,segments,trends}`, `/analytics/*`, `/catalog/*`. `/dashboard/trends` is still **Decision Tools**, not trends; `/dashboard/segments` is a wrapper over the S7 workspace and keeps every query ID.

## Invariants future work must keep

1. **One generation or no comparison.** Cross-asset numbers require a verified `dashboard-release.json` (build-time for `/areas`, runtime for `/explore`). Never average area medians into a "national" figure.
2. **Joint sections only.** `map_metrics[era_property]`; never fall back to property-only (`hdb`) or period-only (`whole`) blocks.
3. **Missing ≠ zero.** `formatNumber`/`formatPercent` return `N/A`; exporter zeros are `empty`; charts break lines instead of filling.
4. **Absolute data claims.** Fixed 2025 where verified; literal era labels; export time is not source freshness.
5. **Base path.** All links/fetches use `import.meta.env.BASE_URL`; `Astro.url.pathname` includes it and must be normalised before matching nav state.
6. **No fabricated behaviour.** Gate unknown models (lease/MRT/spatial/forecast) behind explicit unavailable states rather than presenting them as current.
7. **Archive is not release.** `segments_enhanced.json.gz` and the three `interactive_tools/*` assets are not in `dashboard-release.json`; those surfaces must never compare their numbers with dashboard assets. Pinned by `app/tests/unit/segment-evidence.test.ts` and `app/tests/unit/tool-evidence.test.ts` — adding an archive to the manifest flips those tests first.
8. **Four tool contracts.** Financing is illustrative arithmetic over user inputs with a joint 2025 `map_metrics` reference price; lease is a dated stored-band lookup with signed statistics; MRT/CBD discloses coefficients and withholds the total; spatial is label inspection only. No tool may produce loan-eligibility advice, a hidden floor-area scaling, an undefined-period compounding or an allocation recommendation. Income is never serialised or logged.
9. **Archive layers are not current evidence.** The nine `analytics/*` research layers keep their IDs and query state but never paint an analytical polygon fill. Uniform stored values and past forecast targets are labelled from the data, one source failure disables only its own layers, and the observed fill uses `map_metrics` only. The catalog is a separate generation from the platinum artifact: both row counts stay visible and neither is rewritten.
10. **Dialogs and failed refreshes stay honest.** Every overlay is a real dialog: focus moves inside, Tab stays inside, Escape closes and focus returns to the trigger. A failed background refresh never hides or silently replaces already-published data; SSR-backed islands surface `refreshError` with a retry, and the fatal-error path applies only when nothing is displayed.

## Verification commands

```bash
# frontend
cd app && bun run test:unit                     # bun:test, hermetic
cd app && bun run astro check                   # 0 errors, 0 warnings, 22 hints on 191 files (S10 cleared the last 3 errors)
cd app && bun run validate-data                 # manifest contract + release warning
cd app && bun run build                         # regenerates catalog.jsonl.gz — restore it afterwards
cd app && LD_LIBRARY_PATH=/tmp/qna-browser-libs/root/usr/lib/x86_64-linux-gnu \
  PLAYWRIGHT_BASE_URL=http://127.0.0.1:4321 bunx playwright test   # 8 Pages-base tests skip without PAGES_ORIGIN
cd app && bun run measure:payload               # per-route gzip HTML/JS/CSS, islands, SSR props

# Pages base
cd app && bun run build:pages                   # ASTRO_PAGES=true, restores catalog afterwards
cd app && bun run serve:pages                   # http://127.0.0.1:4402/egg-n-bacon-housing/
PAGES_ORIGIN=http://127.0.0.1:4402 PAGES_BASE_PATH=/egg-n-bacon-housing \
  PLAYWRIGHT_BASE_URL=http://127.0.0.1:4402/egg-n-bacon-housing/ \
  bunx playwright test tests/e2e/pages-base.spec.ts

# exporter / data boundary
uv run pytest tests/test_export_app_data.py --no-cov -q
uv run ruff check scripts/export_app_data.py tests/test_export_app_data.py
uv run ruff format --check scripts/export_app_data.py tests/test_export_app_data.py
uv run python scripts/export_app_data.py --last-complete-month 2026-10 --output-dir /tmp/exp-check
```

## Published-month boundary

`--last-complete-month` is mandatory for a reproducible release: without it the
exporter's completed-bucket rules read the UTC clock, so the same parquet
publishes a different trailing month after a rollover. `2026-10` is the current
published boundary — `app/public/data/dashboard-release.json` records it under
`trailingMonth`. Raising it needs a pipeline refresh that actually contains the
complete month (`uv run python main.py --stage all`), not just a later export;
see [app/public/data/README.md](../../app/public/data/README.md).

## Known environment notes:

- `bun run build` rewrites `app/public/data/catalog.jsonl.gz` through `sync-catalog`; restore it (`git checkout -- app/public/data/catalog.jsonl.gz`) unless a data refresh is explicitly authorised.
- A cold Vite dev server can fail "no console errors" tests with `Failed to fetch dynamically imported module`; run against `bun run preview` after a fresh build, or restart the dev server.
- A fresh checkout has no `app/node_modules`: run `bun install` in `app/` first. Install bun standalone (`~/.bun/bin`, not `npm i -g bun`, which is bound to one nvm node version) and pin the version in `/.bun-version` (1.2.23, matching `app/package.json:engines` and the `oven-sh/setup-bun` pin in both workflows). With the pin, `bun install` leaves `app/bun.lock` untouched; a newer bun rewrites it — restore with `git checkout -- app/bun.lock`.
- `bunx playwright install chromium` is needed when the cached browser build does not match the installed `@playwright/test` (S7 needed build 1217). Then run e2e against `bun run preview` with `PLAYWRIGHT_SERVER_COMMAND='bun run preview -- --host 127.0.0.1'`.
- The Pages-base spec needs a prefix-mounted `dist`: run `bun run build:pages`, then `bun run serve:pages` (port 4402), and pass `PAGES_ORIGIN`/`PAGES_BASE_PATH` as in the verification block. It is skipped otherwise, so a root run's 8 skips are expected. `astro preview` cannot serve the prefixed build.
- CI now has a `frontend` job (`astro check`, `test:unit`, `validate-data`) in addition to the E2E job; the deploy workflow builds with `ASTRO_PAGES=true` and checks both headings and a base-prefixed asset.
- `uv run pre-commit run --all-files` currently dies in this environment: its prettier hook wants node `27.0.0-alpha.0.0.0` and `nodeenv` rejects the version string. Equivalent check: `cd app && bunx prettier@3.4.2 --write <changed files>` (the hook's `types_or` covers js/jsx/ts/tsx/css/json/markdown, **not** `.astro`).
- pi-lens's TypeScript server starts before `bun install` creates `node_modules`, so it resolves no project config and flags `import.meta.env`/`clsx` on files that `astro check` accepts. It also marks `MarketOverviewDashboard.tsx` with two such errors. Restart the session after installing; `bunx tsc -p tsconfig.json --noEmit` is the project-accurate signal. S7 avoids `import.meta` in islands by passing `baseUrl` from the Astro shell.
- Playwright Chromium needs `LD_LIBRARY_PATH=/tmp/qna-browser-libs/root/usr/lib/x86_64-linux-gnu` in this environment.
- `bun run astro check` is clean: **0 errors / 0 warnings / 22 hints** on 191 files (187 before the S10-F1/S8-F1 follow-up added four modules/tests). S10 deleted the dead `PersonaHeader.tsx` and typed the leaderboard `gunzip`, clearing the last 3 errors; touched files must keep the error count at zero.

## S7 carry-forward (deferred, not regressions)

The S7 implementation report lists these in `§4 Gaps`; they are recorded here as
tasks so a fresh session picks them up instead of re-deriving them. None blocked
S8.

| ID    | Task                                                                                       | Suggested slice | Notes                                                                                                        |
| ----- | ------------------------------------------------------------------------------------------ | --------------- | ------------------------------------------------------------------------------------------------------------ |
| S7-F1 | Investigation table pagination ("Showing 5 of 10" + next/previous, anchor preserved)       | S10 / S7b       | SVG12 shows a pager; S7 lists all rows that fit and says so. Needs viewport-aware page size.                 |
| S7-F2 | Compare view chart, stored PSF only                                                        | S7b / S10       | The old bars plotted yield/YoY (gated). A single stored-PSF series is honest; anything else is gated.        |
| S7-F3 | Decide `investmentGoal` / `timeHorizon`: serialise them, or drop them from `FilterState`   | S7b             | Not exposed by the filter panel, so never written to URLs. Touches scoring inputs — read the register.       |
| S7-F4 | Adopt or delete the unreferenced `segments/details/*` components (0 imports, pre-existing) | S10 cleanup     | `DetailsTab`, `SegmentOverview`, `RiskFactors`, `GeographicDistribution`.                                    |
| S7-F5 | Segment scoring, cohort counts, confidence labels                                          | owner decision  | Decision register: the UI may explain, not redefine. Enforced today by `SEGMENT_MATCH_WEIGHTS` being shared. |

## S8 carry-forward (deferred, not regressions)

The S8 implementation report lists these in `§4 Gaps`. None blocks S9.

| ID    | Task                                                                                       | Suggested slice | Notes                                                                                                         |
| ----- | ------------------------------------------------------------------------------------------ | --------------- | ------------------------------------------------------------------------------------------------------------- |
| S8-F2 | Retire or re-justify the now-unused `affordability_metrics.json.gz`                        | data boundary   | The S8 workspace no longer reads it. Removing it from the exporter/publish list needs data-boundary approval. |
| S8-F3 | Decide whether the lease input range should include the stored 4–9-year band               | product / S10   | The plan fixes 40–99 years; the chart and table already show every stored band.                               |
| S8-F4 | Surface `portfolio_allocation` (spatial)                                                   | owner decision  | The schema check discards it; an allocation view needs a reviewed model contract.                             |
| S8-F5 | Delete or adopt the unreferenced `PersonaHeader.tsx` (2 pre-existing `astro check` errors) | S10 cleanup     | Pre-existing dead file; it was already unreferenced before S8.                                                |

## S9 carry-forward (deferred, not regressions)

The S9 implementation report lists these in `§4 Gaps`. None blocks S10.

| ID    | Task                                                          | Suggested slice | Notes                                                                                                               |
| ----- | ------------------------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------- |
| S9-F1 | Regenerate the catalog and the S0 audit count together        | data boundary   | The audited `1,234,928` is a recorded observation, not a live parquet read; the banner shows both counts unchanged. |
| S9-F2 | Remove the `unified_dataset` self-edge from generated lineage | data boundary   | `unified_dataset` appears in its own upstream list; the page displays the catalog as generated.                     |
| S9-F3 | Repair the lease study's PSM/PSF tables                       | owner decision  | S9 withholds the chart and states the unit review; the published values are unchanged.                              |
| S9-F4 | Add a geometry-only mode to the research map                  | S10 / product   | The base tiles still need network; observed geometry and archive inspection do not.                                 |
| S9-F5 | Full keyboard navigation of the catalog DAG                   | S10             | Node links and zoom controls are keyboard reachable; drag positioning is not.                                       |

## S10 carry-forward (deferred, not regressions)

The S10 implementation report lists these in `§6`. None of them is a failing release check.

| ID     | Task                                                               | Suggested owner   | Notes                                                                                                                                       |
| ------ | ------------------------------------------------------------------ | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| S10-F2 | No per-route JS budget; `/dashboard` static graph is 181.8 kB gzip | performance       | Measure before adding another chart library or island.                                                                                      |
| S10-F3 | Full Playwright suite still runs only at the root base             | integration       | The Pages-base spec covers assets, hydration, links and deep links; a base-aware `goto` fixture would allow the full run.                   |
| S10-F4 | GitHub Actions are referenced by mutable tags                      | CI / supply chain | Pin to reviewed commit SHAs; do not invent them.                                                                                            |
| S10-F5 | `refreshError` is only rendered by the leaderboard                 | frontend          | It is the only SSR-backed fetching surface; new ones must adopt the same banner.                                                            |
| S10-F6 | The deployed Pages smoke step cannot be run locally                | release owner     | The workflow's greps and base-asset check pass against the local Pages build.                                                               |
| S10-F7 | The catalog audit observation is a recorded constant               | data boundary     | `app/tests/unit/catalog-audit.test.ts` pins both visible counts, so regenerating either side fails until the constant and copy are updated. |

Resolved by S10 and its audit pass: the 3 remaining `astro check` errors, S8-F5 (`PersonaHeader.tsx`), reference-asset failure conflation, MRT/CBD term disclosure, the spatial-warning predicate, payload byte/lazy accuracy, deep-route smoke coverage, the root-relative no-JS link, server path containment, filtered schema state and `aria-sort`.

## Resolved carry-forward (S10-F1, S8-F1)

Branch `feat/s10-f1-s8-f1`; no data, model, scoring or published-asset change.

| ID     | Resolution                                                                                                                                                                                                                                                                                                                                                                                                                               | Evidence                                                                                                                                                                                 |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S10-F1 | `/catalog/` projects the parsed catalog once (`utils/catalog-payload.ts`) and passes slim props: table rows `{id,label,layer,status,rowCount,columnCount,bytes,hasSchema}`, DAG nodes `{id,layer,label}`, edges as `[from,to]`. SSR props **825.0 kB → 186.8 kB** (−77.4%), HTML gzip **81.1 → 31.5 kB**. Residual: the 2,333-row lineage edge list is ~153 kB of the total — drawing it is the capability, so it was kept and recorded. | [s10-report.md](s10-report.md) §8; `tests/unit/catalog-payload.test.ts`; two new `tests/e2e/catalog.spec.ts` tests                                                                       |
| S8-F1  | Financing inputs moved to `ToolsWorkspace` via `lib/financing-draft.ts`, so a tool switch no longer resets them. The observed reference price is imported only when `referenceKey(area:property)` changes, so a manual price stays manual while a deep link or back/forward still imports the new median. Memory-only: no URL keys, storage, telemetry or console, and a reload still resets.                                            | [s8-report.md](s8-report.md) §7; `tests/unit/financing-draft.test.ts`; four new `tests/e2e/research/tools.spec.ts` tests and the widened privacy test in `tests/e2e/integration.spec.ts` |

## Remaining slices — entry points

### S8 — four-tool workspace (delivered)

Shipped as `/research/tools` + `/dashboard/trends` wrapper over `components/tools/ToolsSurface.astro`; pure contracts in `components/tools/lib/{tool-amortization,tool-url-state,tool-assets,tool-evidence,tool-reference}.ts`; report in [s8-report.md](s8-report.md). The old tool components, their panel/tabs, the pass-through `TrendsDashboard` and `TrendsMap` were deleted. The `tools` nav item now points at `research/tools`. Model regeneration, new eligibility policy and any recommendation promotion remain **separate approvals** and were not done.

### S9 — research map, studies, catalog (delivered)

Shipped as `/research/map` + `/dashboard/map` wrapper over `components/research-map/ResearchMapSurface.astro` (archive contract in `utils/map-archive.ts`; the analytical overlay components and old `LayerControl` were deleted), a filtered studies library with one H1 per article and the lease chart withheld (`components/studies/`), and catalog snapshot/discrepancy semantics (`constants/catalog-audit.ts`). Report in [s9-report.md](s9-report.md). The map nav item is now “Research map” at `research/map`. No asset was regenerated and no published content was edited.

### S10 — integration, regression and release readiness (delivered)

Root and Pages-base previews, the full root Playwright suite (198 pass, 8 Pages-base skips) and the focused Pages-base suite (8 pass). S10 cleared the remaining `astro check` errors (0/0/22), fixed stale deploy/CI smoke checks, added the frontend CI job, a shared modal keyboard contract with a dialog stack, a visible failed-refresh state for SSR-backed data, and a filtered-empty schema state. An independent S8–S10 audit then fixed reference-asset failure wording, the MRT/CBD CBD term, the spatial-warning predicate, payload byte/lazy accounting, deep-route smoke coverage, the no-JS base link and server path containment; tests now cover tool keyboard/popstate/reference parity, request bodies and console for private inputs, and catalog-audit drift. Payload/hydration measurements are recorded in [s10-report.md](s10-report.md). The work is committed and pushed to `main`; Pages deployment verification and any data/model refresh remain approval-gated. **No next slice.**

## Decision register (still open)

See [`assets/svg/implementation-plan.md` §6](../../assets/svg/implementation-plan.md). The ones that survive S10 and bind any future release:

- Segment scoring changes require an owner decision; the UI may explain, not redefine.
- Lease/MRT model repairs and any "recommendation" promotion require separate approval.
- Financial scenarios stay illustrative arithmetic; no CPF/MSR/TDSR or eligibility claims.

## How to continue in a fresh session

1. Read `AGENTS.md`, the two `.agents/skills/*` checklists (if touching ingestion/pipeline), this file, then the specific slice in `assets/svg/implementation-plan.md` plus its SVG.
2. Inspect `git log` and the working tree first: `git status`, `git diff --stat`, and the relevant files. Do not assume the slice status above matches the branch tip.
3. Keep slice ownership exclusive; the coordinator owns shared files (`Layout.astro`, nav, `package.json`, route wrappers, `types/*`, `constants/data-urls.ts`).
4. Verify with the commands above and record the exact counts; never report a fail-closed gate as "passed".
