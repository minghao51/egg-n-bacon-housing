# Handoff — 2026 reporting refresh (RF05 → RF12)

- **Written:** 2026-11-13
- **For:** the next agent picking up this program
- **Program contract:** [implementation map](../docs/plans/2026-11-12-reporting-refresh-implementation-map.md) · [slice handoffs](../docs/plans/2026-11-12-reporting-refresh-handoffs.md) · [decision ledger](../docs/plans/2026-11-12-reporting-refresh-decisions.md) · [research register](../docs/plans/2026-11-12-reporting-refresh-research-register.md)
- **Evidence:** [audit](../docs/implementation/2026-reporting-refresh-audit.md) · [RF00](../docs/implementation/2026-11-12-rf00-baseline.md) · [RF01](../docs/implementation/2026-11-12-rf01-leaderboard-report.md) · [RF02](../docs/implementation/2026-11-12-rf02-errata.md) · [RF03](../docs/implementation/2026-11-13-rf03-source-reconciliation.md) · [RF04](../docs/implementation/2026-11-13-rf04-v2-period-pack.md) · [RF05](../docs/implementation/2026-11-13-rf05-current-periods.md) · [RF06](../docs/implementation/2026-11-13-rf06-fieldnotes.md) · [RF07](../docs/implementation/2026-11-13-rf07-editions.md) · [RF08 readiness](../docs/implementation/2026-11-13-rf08-readiness.md) · [RF09](../docs/implementation/2026-11-14-rf09-area-type-month-history.md) · [RF11](../docs/implementation/2026-11-13-rf11-catalog-report.md)

## 0. Resume here

**Done and verified (local, uncommitted):** RF00–RF07 (RF07 = archive/edition architecture), RF09 (rolling-quarter periods + per-property monthly history, new pack generation), RF11.
**Next, in order:** RF08 (RS01/RS02), RF10 and RF12 evidence are closed for the scope recorded below. Two things are left, and both are now written down for a fresh agent: (a) **the deploy gate** — needs the owner's permission, see [RF12 §6](../docs/implementation/2026-11-14-rf12-release-evidence.md); (b) **RF08 for the other 13 studies** — start from the [continuation brief](../docs/implementation/2026-11-14-rf08-continuation-brief.md), which carries the proven gate sequence, the mechanics and the traps.
**RF12 evidence done (2026-11-14):** [release evidence](../docs/implementation/2026-11-14-rf12-release-evidence.md) — candidate identity (v1 `0e1013ee485f…` frozen, v2 `2c30e2aa836c…` at 570,224 bytes over 6 roles, cutoff 2026-10), asset disposition, post-build catalog pin `a67f2f6807f32c31…`, the two approved editions with their text hashes, local + Pages verification and a rollback table. **Nothing is deployed.** Three things block a deployed release and all three need you: the host `Content-Encoding` check for `observed/**/*.json.gz`, a real rollback rehearsal, and a decision on `interactive_tools/affordability_metrics.json.gz` (retained, unused, outside every manifest).
**RF10 complete (2026-11-14):** [area activity](2026-11-14-rf10-area-activity.md) — `/areas/<slug>` now shows the rolling quarter (`rolling3_2026_10`), its prior-year quarter, the change in observed sales, the TTM context and the per-property D05 verdict, **all from the pack the page already verifies at build time** (no monthly payload, no island). Neutral numbers only; `no-sales` renders as an absence, never `0`. Two E2E tests were added and one pre-existing row count was rescoped to the comparison panel (the activity table is a second table). Explorer parity landed in slice 2a: `activityForObservation()` owns the comparison and the D05 verdict for both the fieldnote table and the explorer row (a parity test fails if they diverge), each row states `Prior-year same window: N sales (+x.x%)` or the reason it cannot be computed, thin rows say `· below the 150-sale floor` in words, and a limited-display scope still shows numbers while refusing to rank. Slice 2b adds the monthly history **on request**: `AreaHistoryPanel` fetches nothing until the reader asks, then verifies the manifest and the one `area-monthly-<property>` payload before rendering a table whose months come from `history.months` (a grid gap is `missing-source`, never `0`) with loading/error/retry states. Map colouring by activity is deliberately not built — RF09 §3.2 shows the change flips sign for every qualifying area across quarter ends, so it would be a directional label in disguise.
**RF08 closed for RS01 + RS02 (2026-11-14):** both series now have a **signed, approved edition**. The gate sequence is in the [RF08 sign-off record](../docs/implementation/2026-11-14-rf08-editions-signoff.md): owner source/cutoff signature on the two evidence ledgers, refreshed text authored as **new** frozen sources (`docs/analytics/editions/{data-sources,rental-yields}/2026-11-14/`) with the RF00 originals untouched, an independent `openai-codex/gpt-6-luna` xhigh review of that text (it opened **FAIL** with three real defects — a unit/block contradiction, a false "attestations are recorded" claim, and an absent-asset claim the ledger cannot make — all fixed before **PASS**), then the owner's publication signature. The registry entries are `approved`/`published` with three attestations on one evidence hash plus `editionSha256` of the text, which the archive route re-verifies on every build. The other thirteen studies stay `historical` and still say "No approved current edition".
**One RF05 item left:** confirm the deploy host serves `observed/**/*.json.gz` without `Content-Encoding` (the Pages server does) — an RF12 check.

**RF09 decision still open:** activity thresholds are calibrated and published in the report, but no directional label ships. Adopting the quarter-scaled 38-sale floor or any label needs the owner's decision; neutral numeric display is what is implemented.

The shipped build mode is **v2** (`bun run build`), with `bun run build:legacy` retained for verification. Start by running §6.

## 1. What this program is

The app (`/home/howt/work/egg-n-bacon-housing`, Astro + React islands over a Python/Hamilton pipeline) publishes Singapore housing observations. Reports and dashboards were pinned to 2025-era data and, in places, displayed the wrong population. The program refreshes them onto 2026 observations **without** silently replacing history: v1 stays served, a v2 period pack was added beside it, and each surface migrates explicitly.

## 2. State snapshot

| Slice | State | Evidence |
| --- | --- | --- |
| RF00 baseline | done | 15 frozen studies + 72 pinned assets, verifier, fixtures |
| RF01 rankings | done | joint `map_metrics` sections, 5 planning regions, 150-sale rule |
| RF02 reports/charts | done | unsupported claims removed, charts render, lease gate intact |
| RF03 sources | done | 18,084 objects restored, pipeline rerun, candidate + corrections |
| RF04 v2 contract | done | emitter, resolver, verified loader, `validate-data`, switch |
| **RF05 current periods** | **complete** | dashboard + trends + explore panels render verified windows; the explorer list/map/table and Compare Areas read the pack for a concrete published period (T1, T2); D03 defaults + migration notice, and **the switch is flipped** (v2 builds); Compare Areas keeps its ranked default until `all` is publishable |
| **RF06 fieldnotes/tools** | **fieldnote scope done** | identity union + slug-collision guard, query-selected sections, no-JS fixed-scope statement, single return-link allow-list; pack per-area slices defer to RF10 |
| **RF11 catalog** | **done** | regenerated from the current platinum build; audit reconciled with history preserved; disposition table for RF12 |
| **RF07 editions/archive** | **core done** | separate frozen collection, validated register, 15 archive routes, series `no approved current edition`; RF08 gated on sign-offs |
| **RF08 refreshed studies** | **2 of 15 approved** | approval record (`signoffs` + `editionSha256`, validator- and build-enforced); [RS01](../docs/implementation/2026-11-14-rs01-source-inventory.md) + [RS02](../docs/implementation/2026-11-14-rs02-rental-yield-evidence.md) evidence packs signed; editions `data-sources-2026-11-14` and `rental-yields-2026-11-14` published; the other 13 studies stay historical — hand them to a fresh agent via the [continuation brief](../docs/implementation/2026-11-14-rf08-continuation-brief.md) |
| **RF09 area-type-month history** | **complete** | `rolling3` periods + 4 monthly payloads in one new generation (`2c30e2aa836c…`, schema `2.1.0`, method `observed-aggregates-2`); calibration recorded, no directional labels |
| **RF10 area activity** | **complete** | rolling quarter + prior-year quarter + change + TTM + D05 verdict on `/areas/<slug>` (zero new bytes) and in the explorer list through one shared helper; neutral numbers only, limited-display never ranked. Monthly history on request (verified, retryable). Per-area slices deferred from RF06 and directional labels remain open |
| **RF12 release evidence** | **evidence done, deploy gated** | [candidate identity, disposition, rollback](../docs/implementation/2026-11-14-rf12-release-evidence.md); deployment needs the owner's grant plus the host `Content-Encoding` check |

### Published artifacts (in the working tree, not committed, not deployed)

- v1 release: `app/public/data/dashboard-release.json`, generation `0e1013ee485f…` — **unchanged**, 7 assets
- v2 pack: `app/public/data/dashboard-release-v2.json` + `app/public/data/observed/2c30e2aa836c…/{periods,summary,area-monthly-all,area-monthly-hdb,area-monthly-ec,area-monthly-condo}.json.gz` — cutoff `2026-10`, 10 periods, 1,840 observations, 570 KB total
- The RF04 generation `observed/6cd4510f26ec…/` (48 KB) is **retained and unmodified**; only the discovery manifest was replaced
- `PUBLIC_OBSERVED_RELEASE=v2` is the shipped build (`build` → `build:base`); `bun run build:legacy` reproduces the previous mode for verification
- catalog regenerated by RF11 (`data/catalog/catalog.jsonl`, `app/public/data/catalog.jsonl.gz`) — this diff is **authorized output**, not build noise
- RF08 evidence ledgers (measured, reproducible): `docs/implementation/artifacts/rs01-source-inventory.json` (`65ce7a10…`) and `docs/implementation/artifacts/rs02-rental-yield-evidence.json` (`db134525…`). Both series carry an **approved** edition (`data-sources-2026-11-14`, `rental-yields-2026-11-14`) with three attestations each; the other thirteen studies carry none, so they still say no approved edition

### Data on disk

`data/manual` (124 MB) and `data/cache` (18,032 geocache parquets) are restored and verified against R2 (`00_sync_data.py --verify` → 18,084 OK). `data/pipeline/04_platinum/` holds a full build: `unified_dataset` 1,236,310 × 97, `pa_monthly_metrics` 13,236.

## 3. Hard rules

1. **No commits, no deployment, no publication** unless the user asks in that turn. Nothing here is committed.
2. **Never open or print `.env`.** It exists and holds `R2_*`, `URA_API_ACCESS_KEY`, `ONEMAP_*`; scripts load it themselves. Print variable *names* only.
3. **No portal scraping or 403 bypass.** PropertyGuru/99.co were blocked during the audit; that is not a task.
4. **v1 is frozen.** New data goes to new paths. `scripts/tools/verify_reporting_baseline.py --assets` must keep passing (72 pinned files).
5. **Fixtures ≠ refresh.** A fixture-complete slice is not a data refresh; say which one you did.
6. Follow `AGENTS.md`, both `.agents/skills/` checklists for pipeline/ingestion work, and the Playwright skill for browser checks.
7. **Missing ≠ zero.** Null stays null; `no-sales` is not `missing-source`.

## 4. Next tasks, in order

### T1 — Explorer rows + map on v2 periods — **DONE (2026-11-13)**

Shipped as one slice with `astro check` green after the row-shape step. Read [RF05 report §7](../docs/implementation/2026-11-13-rf05-current-periods.md) for the design actually implemented — it replaced the earlier reverted attempt.

What now exists:

- `ExplorerPeriod = ExplorerLegacyPeriod | ExplorerPackPeriod`; concrete ids are regex-validated (`month|ytd|ttm_YYYY_MM`, `year_YYYY`) and written to the URL verbatim. **A legacy id always reads the legacy era**, even where the pack publishes the same id (`year_2025`), so old links keep their meaning and a pack-less build still renders the default.
- `app/src/utils/explorer-pack-rows.ts` builds rows and the national baseline from the verified pack; `observed-rows.ts` owns the shared ordering/threshold/search and a discriminated `ExplorerDataset` (`kind: "legacy" | "pack"`).
- Limited-display scopes (EC, condo, All) are **not ranked**: name order, no sort control, no map colour, coverage note shown. HDB pack windows are ranked normally.
- Unpublished/malformed concrete ids show a message listing the published ids; nothing falls back to another window.

Acceptance evidence: `bun run test:unit` 436 pass; `astro check` 0/0/22; explore E2E 13 pass; dashboard+explore+explorer-map+trends E2E 73 pass; Pages E2E 9 pass including the pack under the repository prefix.

### T2 — Compare Areas onto the pack — **DONE (2026-11-13)**

Read [RF05 report §8](../docs/implementation/2026-11-13-rf05-current-periods.md) for the design as implemented.

What now exists:

- `LeaderboardTimeBasis = LeaderboardLegacyTimeBasis | ObservedPeriodId`, parsed by `parseLeaderboardTimeBasis()`; `?timeBasis=recent|whole|year_2025` keep their exact meaning, a concrete id is kept verbatim, anything else falls back to `recent`. The concrete-id shape now lives in `observed-periods.ts` (shared with `/explore`).
- `buildRankRows()` owns the RF01 semantics (region/price/search filters, 150-sale rule, null-last ordering, `rank: null` for unranked) and both sources only supply `readMetrics`/`readMix`; `buildPackScopedRows()` returns `ok: false` + the published id list for an unpublished window.
- `limited-display` scopes (All, EC, condo) are readable but **never ranked**: name order, `data-ranked="false"` on every row, coverage note in the summary, and the map is not colour-coded.
- Both surfaces verify through one hook, `app/src/hooks/useObservedPack.ts`; the summary names the window and its source (`map_metrics.recent_hdb` or `observed pack · ttm_2026_10 · 6cd4510f…`).
- E2E: `tests/e2e/dashboard/leaderboard.spec.ts` gained 4 pack tests and shares `tests/e2e/utils/servePackBytes.ts` with the explore suite.

Do **not** re-add a ranking path for a limited-display scope to make the page look livelier; §5.6 forbids it.

### T3 — Bare-URL migration notice + switch — **DONE (2026-11-13, flipped)**

The switch is on: `build` = `PUBLIC_OBSERVED_RELEASE=v2 bun run build:base`; `build:legacy` remains for verification. Read [RF05 report §10](../docs/implementation/2026-11-13-rf05-current-periods.md).

- `/explore` opens on `ttm_2026_10` with the updated-default notice; `/areas/*` keeps its fixed build-time section.
- **Compare Areas deliberately keeps `recent`**: D03's ranking default is adopted only when the page's default scope (`all`) is `publish`. It is `limited-display` today, so a bare URL stays ranked; when coverage clears, the same code adopts the window automatically.
- `serializeExplorerSelection()` takes the route's **active** defaults and always writes a concrete published id, so an explicit legacy era is no longer canonicalised away (that was a real defect the flip exposed).
- Verified: root E2E 230 passed / 9 skipped, Pages 9 passed, legacy build clean; legacy-data tests pin `?period=year_2025` and pack tests use `tests/e2e/utils/servePackBytes.ts`.

Pre-flip design and the runtime rules live in [RF05 report §9](../docs/implementation/2026-11-13-rf05-current-periods.md); the flip record, the Compare Areas guard and the serialiser fix are in [§10](../docs/implementation/2026-11-13-rf05-current-periods.md). `tests/e2e/observed-defaults.spec.ts` is part of the root suite now (it is no longer gated on `OBSERVED_V2_ORIGIN`); legacy-mode behaviour is verified with `bun run build:legacy` plus the era-pinned tests.

### T4 — RF06 fieldnotes, tools, route compatibility — **FIELDNOTE SCOPE DONE (2026-11-13)**

Read [RF06 report](../docs/implementation/2026-11-13-rf06-fieldnotes.md). What now exists:

- `loadAreaPages()` unions the historical `map_metrics` identities with the pack's current ones, excludes `SG`/`NONE`, and **throws** when two identities slug to the same path.
- The headline block is one island (`app/src/components/areas/AreaSectionPanel.tsx`) that SSR-renders the fixed default and, after hydration, swaps values/label/scope/provenance together for a valid `?property=`/`?period=`; a concrete v2 id is reported with a link to Explore instead of being substituted.
- `<noscript>` states the fixed build-time scope; the availability panel rows are real section links.
- `area-selection.ts` is the client-safe half — never import `area-page.ts` (Node `fs`) from an island; the build fails with `createHash is not exported by __vite-browser-external`, which is the symptom.
- `area-links.ts` owns `AREA_RETURN_PARAMETERS` + `explorerReturnHref()`; the inline copy in `[slug].astro` is gone and the period vocabulary accepts concrete ids.
- Tools: the financing reference period was already explicit (`REFERENCE_ERA = "year_2025"`), per-entry `section` identity, generation shown; archived model gates untouched.

**Still open for RF06's wider card:** nothing blocking. The pack's per-area current-window slices belong with RF10 (they need the RF09 activity work). Two stale E2E tests were corrected: `cross-page.spec.ts` clicked the RF02-removed "Live Dashboard" teaser, and the leaderboard summary assertions now match the established "Showing N areas ranked by …" copy.

### T6 — RF07 editions/archive — **CORE DONE (2026-11-13)**

Read [RF07 report](../docs/implementation/2026-11-13-rf07-editions.md).

- `analyticsEditions` collection globs `editions/*/*/*.md`; the live `analytics` glob stays single-segment so an edition can never be emitted at `/analytics/<slug>`.
- `src/components/studies/lib/edition-registry.ts` is the single register: identity, `evidenceStatus` (`approved|historical|withheld`), `editorialStatus`, publication year, frozen path, pinned-asset count. `validateEditionRegistry()` rejects reserved slugs, duplicates and malformed identities, and the archive route refuses to build when it fails.
- `/analytics/archive/<year>/<edition>/<slug>` (15 routes) renders the frozen original with its own status panel, frozen source path and a link back to the series; withheld-chart gates carry over (no chart island on an archive URL).
- `approvedEditionFor()` picks the newest **approved** edition, never the newest date; today that is none, so series entries say "No approved current edition" and link the archive.
- Gotchas: Astro extracts `getStaticPaths` into its own module (frontmatter helpers are not in scope there), and the glob id includes the `editions/` prefix — parse the last three segments.

**RF08 is closed for RS01/RS02 only** (see §4a); the remaining studies each need their own evidence, text and independent reviewer (D12). Do not invent refreshed editions or promote the historical ones.

### T7 — RF11 catalog — **DONE (2026-11-13)**

Read [RF11 report](../docs/implementation/2026-11-13-rf11-catalog-report.md). What now exists:

- Catalog regenerated from the current platinum build (`uv run python scripts/generate_catalog.py`): 4 layers, 125 datasets, 2333 edges, `unified_dataset` 1,236,310 rows — no structural drift.
- `CATALOG_AUDIT.unified_dataset` records the new observation **with the artifact sha256 and the catalog generation**; `CATALOG_AUDIT_HISTORY` keeps the S0 finding (1,234,928 vs 1,233,405). The page's discrepancy banner is gone because the counts agree; the history is not deleted.
- Asset disposition for RF12: v1 frozen, v2 republished by RF09 (`2c30e2aa836c…`, RF04's `6cd4510f…` retained), catalog regenerated (`7f75527f…`), `interactive_tools/affordability_metrics.json.gz` **retained** (unused, outside the manifest — removal needs data-boundary approval).
- Note for RF12: `generate_catalog.py` and `app/scripts/sync-catalog.mjs` both write `catalog.jsonl.gz` with different gzip encoders, so pin the **post-build** artefact in release evidence.

Do not "clean up" a catalog diff after an ordinary build without checking whether RF11 output is the intended change.

### Next actions (not started)

| # | Slice | First step | Gate |
| --- | --- | --- | --- |
| N1 | ~~**RF09** area-type-month history + activity stats~~ — **DONE 2026-11-14** | read [the report](../docs/implementation/2026-11-14-rf09-area-type-month-history.md); the pack is republished as generation `2c30e2aa836c…` | done: v1 untouched, RF04 generation retained, calibration recorded |
| N2 | ~~**RF10** area-activity UI~~ — **DONE 2026-11-14** | read the [RF10 report](../docs/implementation/2026-11-14-rf10-area-activity.md): fieldnote numbers, explorer parity and the on-request monthly history all ship | done; directional labels still need an owner decision |
| N3 | ~~**RF12** release evidence~~ — **DONE 2026-11-14** (evidence only) | read the [release evidence](../docs/implementation/2026-11-14-rf12-release-evidence.md); remaining: host `Content-Encoding` check, rollback rehearsal, `affordability_metrics` disposition | deployment is a separate user-authorised action |
| **N0** | ~~**RF08 / RS01 + RS02**~~ — **DONE 2026-11-14** | read the [sign-off record](../docs/implementation/2026-11-14-rf08-editions-signoff.md); both editions are approved and published | done: three attestations per edition, text hash pinned and build-verified |
| N4 | **RF08** other 13 studies | open the [continuation brief](../docs/implementation/2026-11-14-rf08-continuation-brief.md) and pick one whose extra gate is smallest (`temporal-evolution`, then `amenity-impact`) | each needs its own evidence pack, text, reviewer and three signatures; model/causal studies wait for their named reviewer |

Each slice has a card in the [slice handoffs](../docs/plans/2026-11-12-reporting-refresh-handoffs.md). Do not start RF08 without the per-job scientific reviewer named in the [register](../docs/plans/2026-11-12-reporting-refresh-research-register.md).

### 4a. RF08 — closed for RS01 + RS02 (2026-11-14)

**Done, in the order the brief required. Full record:** [RF08 sign-off](../docs/implementation/2026-11-14-rf08-editions-signoff.md).

1. **Source/cutoff signature** — owner (`howt`) on both evidence ledger hashes; recorded in the [decision ledger](../docs/plans/2026-11-12-reporting-refresh-decisions.md) under D12 because `validateEditionRegistry()` rejects a sign-off on a non-approved edition (a partial registry record is what D12 forbids).
2. **Refreshed text authored as new frozen sources** — `docs/analytics/editions/data-sources/2026-11-14/data-sources.md` and `…/rental-yields/2026-11-14/rental-yields.md`. The legacy originals were never edited (`verify_reporting_baseline.py --assets` proves it: 15 frozen sources, 72 assets). RS01 replaces inferred ranges with the measured ledger and withdraws the unmeasured median-distance column and column/amenity/macro roll-ups; RS02 states the gross proxy, the 86.6–95.6% matched-group share and the 1,749 town-month denominators, and withdraws the per-flat-type bands, the yield-vs-appreciation claim, the league table, the affordability ratio and the downside-floor claim.
3. **Scientific re-review of the text** — `openai-codex/gpt-6-luna` xhigh. First verdict **FAIL** (3 hard defects + 1 note, all real), then **PASS** with a verbatim attestation stored in the sign-off record. The pack attestations do **not** cover these sentences; this review does.
4. **Publication signature** — owner (`howt`) on the two text hashes: `data-sources-2026-11-14` = `bde11c61b720c2504cdf78bde9238c5e57925e319457d52356cde0bcdeeafb81`, `rental-yields-2026-11-14` = `f6b0bd9d811bb9b348b0e897b66a482add281e38f2803c61193978c97ca0ab67`. Both registry entries are `approved`/`published`; the series entries render "Approved edition …" and link it, and state that the narrative below may predate it.

**New contract (option B, owner-approved):** `AnalyticsEdition.editionSha256` pins the reviewed **text**, separate from the evidence hash every sign-off carries. `validateEditionRegistry()` requires it on an approved edition and forbids it elsewhere; `verifyEditionArtifacts()` (injected hasher) is called from the archive route's `getStaticPaths`, so **a drifted frozen edition fails the build** with both hashes named. Proven by deliberately pinning a wrong hash.

**What is still open:** the other thirteen studies need their own evidence pack, text and reviewer (see the [readiness doc](../docs/implementation/2026-11-13-rf08-readiness.md)); RF10 and RF12 are untouched. Nothing is committed or deployed.

Older state (kept for context): the D12 approval record was built by RF07 (`preparedBy` + `signoffs`, validator-enforced, rendered on the archive route), and RS02's rental-index fan-out defect was fixed at source and regenerated (`rental_yield.parquet` 1,749 rows, zero duplicates; `unified_dataset` byte-identical, so the v2 pack did not change).

## 5. Traps that already cost time

1. **RF03 window correction.** Full-year 2025 HDB is 25,084; Jan–Oct 2025 is **21,402**. Comparing 12 months against 10 produced a false "−13.1%" HDB figure. Like-for-like: HDB **+1.9%**, EC −57.7%, condo −56.4%. Use the v2 comparator windows, never eyeballed date ranges.
2. **EC/condo stay `limited-display`.** The gap survives the correction and is unresolved (launch cycle vs grain). No growth headline, no ranking, no activity colour for private types.
3. **Determinism.** v2 payloads are canonical JSON + gzip `mtime=0`; the generation hashes schema + method + cutoff + inputs + role hashes, and payloads must not embed it (`verify_pack` enforces). The Python and TS hashers are pinned by a golden vector test in `app/tests/unit/observed-pack-loader.test.ts` — if you touch either, keep that vector.
4. **importlib + dataclasses.** Tests load scripts by path; register the module in `sys.modules` before `exec_module`, or `@dataclass` raises `AttributeError: 'NoneType' object has no attribute '__dict__'`.
5. **`astro check` baseline is `0 errors / 0 warnings / 22 hints`.** New hints in touched files are a regression. Unused imports are the usual cause; renames collide with existing helpers (`formatSgd`/`formatSales` already exist in `MarketOverviewDashboard.tsx`).
6. **`bun test` alone collects E2E specs** and fails with "Playwright Test did not expect test.describe()". Use `bun run test:unit`.
7. **A build rewrites `app/public/data/catalog.jsonl.gz`** (and `data/catalog/catalog.jsonl` if you run the generator). The current diff is **RF11 authorized output** — keep it. For an ordinary unrelated build, restore with `git checkout --`. Note `generate_catalog.py` and `sync-catalog.mjs` use different gzip encoders, so pin the *post-build* bytes in release evidence.
8. **Exporter needs `--last-complete-month`.** Without it the boundary comes from the UTC clock and the same parquet publishes a different month after rollover.
9. **Cold pipeline run is ~55 minutes**, almost entirely `condo_validated` (validation gateway, 3,214 s). The warm rerun takes ~4 minutes. Budget for it; don't kill it early.
10. **Playwright preview needs a matching port** via `PLAYWRIGHT_SERVER_COMMAND='bun run preview -- --host 127.0.0.1 --port <p>' PLAYWRIGHT_BASE_URL='http://127.0.0.1:<p>'`. Mismatched ports hang for 120 s and then fail.
11. **`generate_catalog.py` ignores `--help`** and runs the generator. Use `--dry-run` equivalents or read the source first.
12. **Vite dev/preview re-labels every `.gz` with `Content-Encoding: gzip`.** Measured 2026-11-14: preview sends `Content-Type: application/json` + `Content-Encoding: gzip`, so the browser inflates `periods.json.gz` to 2,465 bytes hashing to `58e4b4dcc11b…` instead of the pinned `fac8170fd9e7…` (560 bytes), and `/explore` shows the correct fail-closed "did not verify" message. `scripts/serve-pages-base.mjs` sends `application/gzip` with **no** `Content-Encoding` and verifies. `curl` without `--compressed` hides the whole difference — compare the two fetch modes, not the file name. Whether the **deploy host** re-labels is still unmeasured (RF12 §4a). **v2 is now the shipped mode, so this bites every pack-path test**: specs that open bare `/explore` or `/dashboard/leaderboard` must register `tests/e2e/utils/servePackBytes.ts` (file-wide `beforeEach` is simplest). Do not "fix" this by loosening the hash — the real fix is a decoded-payload hash in the v2 manifest (RF04/RF12 contract change) or an extension no server re-labels.
13. **A legacy period id beats a pack id of the same name.** `year_2025` reads `map_metrics.year_2025_*`; the pack's own `year_2025` descriptor is deliberately not offered. Do not add a second control for it.
14. **Astro extracts `getStaticPaths` into its own module.** Frontmatter helpers are *not* in scope there (`X is not defined` at build). Inline the logic or move it into the function. Also: a collection's glob id includes its base, e.g. `editions/legacy/2026-11-12/slug` — parse from the end.
15. **Explorer URL serialisation compares against the route's ACTIVE defaults.** `serializeExplorerSelection(selection, activeDefaults)`; a concrete published id is always written. Comparing to the legacy constant dropped an explicit `?period=year_2025` on a v2 page, so a reload silently switched windows. Do not "simplify" this back.
16. **Compare Areas must not open unranked.** D03's ranking default is adopted only when the default scope (`all`) is `publish`; it is `limited-display` today, so the bare URL keeps `recent`. If you flip that guard, the default page becomes a name-ordered list.
17. **Legacy-data E2E assertions are era-pinned on purpose.** With v2 shipped, tests that assert 2025 values pass `?period=year_2025` (or open the map with it). Do not rewrite them to pack values — add a pack-path test instead.
18. **Plan-image / island boundary.** Build-time modules (`area-page.ts`, `observed-pack-build.ts`) import `node:*`; importing one from an island fails the build with `createHash is not exported by "__vite-browser-external"`. Keep client-safe logic in `area-selection.ts` / `observed-periods.ts` / `observed-monthly.ts`.
19. **The v2 pack is republished per release, so never pin a generation literal in a test.** RF09 moved it from `6cd4510f…` to `2c30e2aa…`; the Compare Areas spec now derives the summary prefix from `public/data/dashboard-release-v2.json`. Match the manifest, not a hex string.
20. **Monthly history is lazy by design.** `loadObservedPack` and `loadObservedPackFromDir` verify only `periods` + `summary`; a property payload is fetched, hashed and parsed on demand (`loadObservedHistory`, `readMonthlyHistoryFromDir`). Do not restore an eager loop over every asset — it would download 570 KB per page for numbers it does not render.
21. **A zero cell inside the month grid is a verified `no-sales` month; a month outside the grid is `missing-source`.** `readMonth` returns `missing-source` with null values rather than 0, and EC/condo grids start at 2021-01 (the observed private start). Never back-fill a missing month to zero, and never infer coverage from `coverage.firstMonth`/`lastMonth` — the grid may contain a gap, so enumerate `history.months`.
22. **An approval record is three attestations on ONE artifact hash.** `validateEditionRegistry()` rejects `approved` unless source/scientific/publication exist, are distinct, are not `preparedBy`, and pin the same `artifactSha256`; it also rejects any sign-off on a non-approved edition. Do not add a fourth "review" field or flip `evidenceStatus` without the record — the archive route renders the attestations, so a bare flag would be a claim with nothing behind it. An automated review must set `automated: true` and carry `evidencePath`.
23. **Evidence ledgers drift.** `uv run python scripts/tools/source_inventory.py --check` re-hashes every recorded source and fails on drift; re-run `rental_yield_evidence.py` and diff before citing RS02 numbers. A signature pins a hash, so regenerating a ledger without re-signing silently invalidates the approval.
24. **The rental-index fan-out is fixed; do not reintroduce it.** `raw_rental_index.parquet` carries three property-type series per quarter, so filtering on `locality` and merging on `month` alone multiplied every town-month row 2–3× (the 3,623-rows-for-1,749-pairs defect RS02 found). `_whole_island_rental_index()` now selects **one** series (`Non-Landed`, falling back to `All Residential`) and the merge is `validate="m:1"`; `rental_yield.parquet` is 1,749 rows with zero duplicates. Note `All Residential` stops at 2021-Q2 — it must not be preferred. `transactions_enriched`/`unified_dataset` were byte-identical after the rerun, so the v2 pack did not change.
25. **`NONE` is not a planning area.** Each monthly payload declares `geographies: {national: "SG", unassigned: ["NONE"], areaCount: 44}`. `NONE` holds ~11.6k HDB rows (1990-01 → 2023-03) that the pipeline could not assign to an area: they stay in the national scope and get a series, but any area list, distribution, rank or map must use `areaSeries(history)`. An independent review caught a calibration that counted it as an area; the same mistake would shift every RF10 distribution.

## 6. Verification

```bash
# Docs / boundary
uv run python scripts/tools/validate_docs_layout.py
uv run python scripts/tools/verify_reporting_baseline.py --assets    # 72 pinned files
uv run ruff check && uv run ruff format --check scripts/
uv run mypy scripts/v2_observed.py
uv run pytest tests/test_research_evidence_tools.py tests/test_v2_observed.py tests/test_reporting_baseline.py tests/test_export_app_data.py --no-cov -q
# RF08 evidence: re-measure the ledgers (fails on drift)
uv run python scripts/tools/source_inventory.py --check
uv run python scripts/tools/rental_yield_evidence.py

# App
cd app
PATH="$HOME/.bun/bin:$PATH" bun --version          # must be 1.2.23
PATH="$HOME/.bun/bin:$PATH" bun run test:unit     # 489 passing at RF09 (32 files)
PATH="$HOME/.bun/bin:$PATH" bun run astro check   # 0 errors, 0 warnings, 22 hints
PATH="$HOME/.bun/bin:$PATH" bun run validate-data # v1 release + v2 pack (6 roles, monthly grid)

# Browser — `bun run build` is v2 mode now (the shipped default).
# It rewrites catalog.jsonl.gz; that diff is RF11 output, keep it.
PATH="$HOME/.bun/bin:$PATH" bun run build                # 219 pages
PLAYWRIGHT_SERVER_COMMAND='bun run preview -- --host 127.0.0.1 --port 4419' \
  PLAYWRIGHT_BASE_URL='http://127.0.0.1:4419' bunx playwright test tests/e2e
                                                  # 230 passed / 9 skipped at handoff
# NOTE: the full suite intermittently times out under default parallelism on a
# busy machine (different tests each run, each passes standalone). Run it with
# `--workers=4` for a stable 230 passed / 9 skipped.
# Legacy-mode verification (no notice, historical defaults):
PATH="$HOME/.bun/bin:$PATH" bun run build:legacy

# Pages build (raw .gz bytes, repository prefix)
PATH="$HOME/.bun/bin:$PATH" bun run build:pages
PLAYWRIGHT_PAGES_PORT=4402 node scripts/serve-pages-base.mjs &
PAGES_ORIGIN=http://127.0.0.1:4402 PAGES_BASE_PATH=/egg-n-bacon-housing \
  PLAYWRIGHT_BASE_URL=http://127.0.0.1:4402/egg-n-bacon-housing/ \
  PLAYWRIGHT_PAGES_PORT=4402 bunx playwright test tests/e2e/pages-base.spec.ts  # 9 passing
```

Do not report a command you did not run. If a step is blocked, say which and why.

## 7. Reporting back

```text
Slice / task:
State: done | partial | blocked
Files changed (and whether shared contracts moved):
Checks run (exact commands, counts, failures):
What is published vs still local:
Corrections or reversions made, and why:
Known risks / next smallest action:
```

A slice is not done because the UI renders or a schema validates. It is done when the numbers shown come from bytes that were verified in the same request, the baseline checks pass, and any unverified scope is labelled rather than rounded into a headline.
