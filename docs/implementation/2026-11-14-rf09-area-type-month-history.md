# RF09 report — area-type-month history and activity statistics

- **Date:** 2026-11-14
- **Status:** **Complete for the RF09 data contract.** The exporter publishes `rolling3` periods and one monthly-history payload per property type in a **new complete pack** (schema `2.1.0`, method `observed-aggregates-2`, generation `2c30e2aa836c…`). Activity thresholds are calibrated and recorded here; **no directional label ships** (neutral numeric only), pending owner approval. An independent review (§5) found one real defect — the calibration population counted the unassigned-geography bucket as a planning area — which is fixed here and now declared in the payloads.
- **Parent:** [implementation map](../plans/2026-11-12-reporting-refresh-implementation-map.md) §5.2/§5.3/§8 · [handoff](../plans/2026-11-12-reporting-refresh-handoffs.md) RF09
- **Decisions:** D02 (cutoff 2026-10), D05 (150-sale caution, both windows for change), D09 (no composite score / BUY label), D11 (coverage disposition)
- **Upstream:** [RF04 v2 pack](2026-11-13-rf04-v2-period-pack.md) · [RF03 sources](2026-11-13-rf03-source-reconciliation.md) · [RF05 periods](2026-11-13-rf05-current-periods.md)

## 1. What exists now

| Piece                     | Behaviour                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rolling3` period kind    | `rolling3_<YYYY_MM>`, inclusive 3-month window ending at the cutoff, comparator `rolling3_<prior year>` published only when all three comparator months are covered. Same code path as `month`/`ytd`/`ttm`, so an exact edge is three months, never three observed rows.                                                                                         |
| `build_monthly_history()` | One payload per property type at grain `(canonical area, property type, month)`. Coverage is declared **per property type** from the bounded input, so private types do not inherit HDB's 1990 start.                                                                                                                                                            |
| Cell encoding             | Positional arrays aligned to the payload's `months` grid, with `cellFields = ["transactionCount","medianPrice","priceObservations","medianPsf","psfObservations"]` declared in the payload. This keeps the assets lazy-loadable (see §2); the parser rejects any other field order.                                                                              |
| Zero vs missing           | A month **in** `months` is covered; zero transactions there is a verified `no-sales` cell with null medians. A month **outside** `months` is `missing-source` and must never render as 0.                                                                                                                                                                        |
| Geography declaration     | Every payload declares `geographies: {national: "SG", unassigned: ["NONE"], areaCount: N}`. `NONE` holds real transactions that no planning area claimed (11,600 rows, all HDB, 1990-01 → 2023-03); they stay in the national scope and get their own series, but they are **not** a planning area. `areaSeries()` is the only supported way to enumerate areas. |
| Complete pack             | `periods`, `summary` and the four `area-monthly-*` payloads share one generation; `verify_pack` re-hashes every asset and rejects a payload that embeds its own generation.                                                                                                                                                                                      |
| Manifest contract         | `schemaVersion: 2.1.0`; all six roles are required. There is no monthly-only manifest and no cross-generation merge.                                                                                                                                                                                                                                             |
| Client contract           | `app/src/utils/observed-monthly.ts` — pure parser plus `readMonth`/`coveredHistoryMonths`. `loadObservedHistory` (browser) and `readMonthlyHistoryFromDir` (build) verify **the one property payload they return** against the loaded manifest.                                                                                                                  |

CLI (unchanged apart from the output):

```bash
uv run python scripts/v2_observed.py --last-complete-month 2026-10 \
  --output-dir app/public/data --scope-status hdb=publish \
  --scope-status ec=limited-display --scope-status condo=limited-display
uv run python scripts/v2_observed.py --output-dir app/public/data --verify-only
```

## 2. Published artifacts

Generation `2c30e2aa836c140a619883c94a0eb8b54d8812f931380b40426b9bf4c82a6fb6`, cutoff `2026-10`, 10 periods, 1,840 observations, 570,224 bytes.

| Role                 |   Bytes | sha256 (first 16)  |
| -------------------- | ------: | ------------------ |
| `periods`            |     560 | `fac8170fd9e73217` |
| `summary`            |  49,635 | `e1abd607d6846a0b` |
| `area-monthly-all`   | 233,722 | `6cb06163009aa858` |
| `area-monthly-condo` |  49,887 | `ac743afd5c098f51` |
| `area-monthly-ec`    |  19,100 | `22ef2c8108ae64c6` |
| `area-monthly-hdb`   | 217,320 | `8d9bd5af61ae2098` |

- Periods added beside the RF04 set: `rolling3_2026_10` (2026-08 → 2026-10, comparator `rolling3_2025_10`).
- Month grids: HDB and `all` 442 months (1990-01 → 2026-10); EC and condo 70 months (2021-01 → 2026-10) — that is the observed private-source start, recorded as coverage rather than back-filled.
- **46 geographies per payload** = national `SG` + the unassigned bucket `NONE` + **44 planning areas**; 47,104 month cells across the four payloads.
- **Chunking / lazy loading:** the eager loader and the build-time reader verify only `periods` + `summary`; a surface fetches one property payload through the manifest, so a map or sparkline never pulls 570 KB.
- **Old generation untouched:** `observed/6cd4510f26ec…/` (48 KB) remains on disk. Only the discovery manifest was replaced (published last, as the contract requires); nothing under the RF04 generation was modified. An intermediate generation from this session's first attempt (`2e3de617…`) never shipped and was removed once superseded, so exactly one current generation plus the RF04 generation remain.

Spot checks against the same bytes (taken from the published payloads):

| Check                          | Value                                                                                 |
| ------------------------------ | ------------------------------------------------------------------------------------- |
| `SG/hdb/rolling3_2026_10`      | 6,930 sales = sum of the 2026-08/09/10 monthly cells                                  |
| `SG/hdb/rolling3_2025_10`      | 5,714 sales                                                                           |
| `SG/hdb/ttm_2026_10`           | 25,483 sales                                                                          |
| `SG/hdb/month_2026_10`         | 2,173 sales, S$650,000, 600.77 psf — identical to the same cell in `area-monthly-hdb` |
| `PUNGGOL/hdb/ttm_2026_10`      | 1,702 sales (RF05 fixture figure)                                                     |
| `PUNGGOL/hdb/rolling3_2026_10` | 488 sales, prior-year quarter 370                                                     |

## 3. Calibration (recorded before any label ships)

Measured from the published pack at cutoff 2026-10 over the **44 planning areas** (`SG` and the unassigned bucket `NONE` excluded — see §5 for why that distinction is now enforced in the payload). Quantiles are linear-interpolated; counts are exact. These numbers are the decision input, not a claim about demand.

### 3.1 Rolling-quarter sample sizes per area

| Scope | min |   p25 | median |   p75 |   max | areas ≥150 current | both windows ≥150 | both ≥38 |
| ----- | --: | ----: | -----: | ----: | ----: | -----------------: | ----------------: | -------: |
| HDB   |   0 |     0 |    121 | 247.5 |   610 |                 19 |                16 |       24 |
| All   |   0 |  42.5 |  293.5 | 433.5 | 1,001 |                 26 |                26 |       33 |
| EC    |   0 |     0 |      0 |   2.5 |    81 |              **0** |             **0** |        6 |
| Condo |   0 | 25.25 |   90.5 | 159.5 |   851 |                 13 |                12 |       28 |

Consequences, applied as ratified rather than re-tuned:

- **D05 (150-sale caution) is the floor for a rolling-quarter ranking.** Only 19 of 44 areas clear it for HDB and 16 clear it in both windows, so most areas are viewable but unranked. A quarter holds roughly a quarter of a year's sales, so the same floor is ~4× stricter at quarter scale; the tighter outcome is allowed by the map ("calibration can tighten it"), the looser one is not.
- **EC stays non-rankable at every plausible threshold**: zero areas reach 150 in a quarter and 29 of 44 areas have no EC sales at all in the quarter. This is the RF03 volume discontinuity, not a quiet market, so no activity colour may be attached to EC (and `all` inherits its weakest constituent).
- 13 of 44 areas have **zero HDB sales in the quarter**: a verified zero, not missing data, and not a cold-market signal.

### 3.2 Same-quarter-prior-year change and stability

| Scope | n (both ≥150) |    min | median |     max | \|change\| > 50% |
| ----- | ------------: | -----: | -----: | ------: | ---------------: |
| HDB   |            16 |  −8.9% | +13.9% |  +51.0% |                2 |
| All   |            26 | −84.5% | −22.9% | +226.1% |                8 |
| Condo |            12 | −92.6% | −51.9% | +311.1% |                7 |

Quarter-end stability (HDB, areas with both windows ≥38 at each quarter end, 12 quarter ends 2024-01 → 2026-10): **every one of the 25 qualifying areas changes the sign of its year-on-year change at least twice**, and the median range of that change across quarter ends is **64 percentage points**. A quarter-on-quarter comparison of the same area is therefore dominated by timing and mix, not by a level shift.

### 3.3 Monthly thinness (last 24 months × 44 areas = 1,056 cells per type)

| Scope | zero-sale area-months | thin (1–9 sales) |
| ----- | --------------------: | ---------------: |
| HDB   |           358 (33.9%) |        96 (9.1%) |
| EC    |           716 (67.8%) |       101 (9.6%) |
| Condo |           109 (10.3%) |      139 (13.2%) |

A zero HDB area-month is usually an area with little or no HDB stock, not a cold market: it must render as "no observed sales", never as a low-activity colour.

### 3.4 Recommendation to the decision owner (not adopted here)

1. **Ship neutral numbers only** — rolling-quarter count, prior-year quarter count, the two denominators and the TTM count, with no directional label, no score, no colour by change. D09 is satisfied and §3.2 shows why.
2. **Keep D05 as ratified** for ranking and for change eligibility (150 in both windows). Do not adopt the 38-sale quarter-scaled floor without an explicit decision; it currently exists only as evidence in the table above.
3. If a directional label is ever wanted, the smallest honest form is a _stability-gated_ one: require ≥150 sales in both windows **and** no sign change across the last four quarter ends. On this data that leaves very few areas — which is the honest answer, not a reason to loosen the rule.
4. EC/condo: no activity colour, no rank. `all` inherits `limited-display` because a constituent is.

Nothing above adds a weight, index, turnover ratio or BUY label. `hotspots.json.gz` keeps its historical method; its `years` field is legacy and is **not** a current activity statistic.

## 4. Verification

```bash
uv run pytest tests/test_v2_observed.py tests/test_reporting_baseline.py tests/test_export_app_data.py --no-cov -q   # 100 passed (46 in test_v2_observed)
uv run ruff check && uv run ruff format --check scripts/                       # clean
uv run mypy scripts/v2_observed.py                                             # clean
uv run python scripts/tools/verify_reporting_baseline.py --assets              # 72 pinned assets unchanged
cd app && bun run test:unit                                                   # 489 passed (32 files)
cd app && bun run astro check                                                 # 0 errors, 0 warnings, 22 hints
cd app && bun run validate-data                                               # 19 assets, v1 release, pack 2c30e2aa836c, 47,104 month cells
cd app && bun run build && bunx playwright test tests/e2e                      # 230 passed / 9 skipped
```

New tests (16 Python, 27 TypeScript):

- Python: rolling-quarter bounds and year-crossing edges, comparator-only-when-covered, transaction-count (not median-of-medians) semantics, month-cell alignment against the same window's observation, per-type coverage, covered zero vs missing source, national-series ordering, the geography declaration (`national`/`unassigned`/`areaCount`) and the unassigned bucket staying in the national scope, disposition propagation, deterministic bytes across all six roles, monthly-asset tamper detection, every history role published with a generation-scoped path.
- TypeScript: role⇄property mapping, fixture parse, grid/cell alignment, `readMonth` (`available`/`no-sales`/`missing-source`), `areaSeries` excluding national + unassigned, rejection of a reordered `cellFields`, short/unaligned cells, median without observations, observations > transactions, non-ascending months, coverage disagreement, `noSalesMonths` mismatch, missing national series, missing/inconsistent geography declaration, wrong type/cutoff, duplicate series; loader verifies one property payload, does not fetch the other three on the eager path, rejects altered bytes and reports a missing payload instead of a shorter series.
- One E2E assertion was de-pinned: Compare Areas matched a literal generation prefix (`6cd4510f`), which a republished pack legitimately changes; it now derives the prefix from the published manifest.

## 5. Independent review and the defect it found

An independent reviewer (not the author; model `openai-codex/gpt-6-luna`, high reasoning — the requested `gpt-6.1-sol` id was ambiguous across providers and fell back) was asked to falsify the slice: pack integrity, coverage semantics, cross-artifact arithmetic, the calibration tables, label smuggling and the RF04 generation. Verdict: **FAIL on one real defect**, everything else verified.

| Finding                                                                                                                                                                                                                                                            | Resolution                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The payloads carry a `NONE` geography; the calibration treated 45 series as 45 planning areas. `NONE` is the unassigned bucket (11,600 HDB rows, 1990-01 → 2023-03, no sales since), so every quantile and zero-cell share was computed over the wrong population. | Fixed twice over: the payload now **declares** `geographies: {national, unassigned, areaCount}` and the parser rejects a missing or inconsistent declaration; the calibration in §3 is recomputed over the 44 named areas. Median HDB quarter moves 118 → 121, zero HDB area-months 35.4% → 33.9%. Eligibility counts did not change (the bucket has no recent sales), so no conclusion in §3.4 rests on the error.                                                          |
| The month-grid parser enforces ascending months but not density, so a grid with an omitted interior month is accepted.                                                                                                                                             | Kept as designed: an absent month **is** missing source by contract, and density cannot be inferred from bounds. `readMonth` returns `missing-source` rather than 0, and RF10 must enumerate months through `history.months`/`readMonth` — recorded as a handoff trap.                                                                                                                                                                                                       |
| Verified independently                                                                                                                                                                                                                                             | Generation recomputes; six assets match byte length and sha256; no payload embeds the generation; grids aligned, medians consistent with observation counts, `noSalesMonths` correct; HDB/all start 1990-01, EC/condo 2021-01; quarterly counts equal the monthly sums for `SG`, Punggol, Tampines and Woodlands; `rolling3_YYYY_MM` accepted while arbitrary strings are rejected; no directional label or BUY score anywhere; RF04 generation unmodified and unreferenced. |

The reviewer could not establish the RF04 generation's historical byte identity from Git (the directory is untracked) — that is a limit of the working tree, not a finding, and RF12 owns pinning it.

## 6. Not done / next

| Item                                            | Why it is separate                                                                               |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Area-activity UI (map/list/sparkline/fieldnote) | RF10; it consumes these verified payloads and must carry the D05 gate and the neutral-label rule |
| Directional activity labels                     | Need owner approval; §3.4 is the proposal, not a decision                                        |
| Stock-normalised turnover                       | Needs a validated stock denominator and geography crosswalk (map §8 defers it)                   |
| Deleting the RF04 generation                    | Retention policy is unverified; the directory stays until RF12 decides                           |

Known risks: (a) 570 KB of history is fetched per property — RF10 must keep it out of SSR props and measure the route budget; (b) a host that re-labels `.gz` with `Content-Encoding: gzip` breaks the pinned bytes for monthly payloads exactly as it does for the core pair (documented handoff trap); (c) EC/condo coverage starting 2021-01 is an observation about the source, not a completeness certificate.
