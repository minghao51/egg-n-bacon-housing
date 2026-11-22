# RS10 evidence pack — market-segments: the six segments are hand-written literals, the cohorts reproduce no population, and no membership joins

- **Date:** 2026-11-18
- **Status:** **Prepared for review, not signed off.** The ledger is measured and `--check`-able; nothing is fitted, no segment taxonomy is claimed, and every quantitative claim of the legacy article is disposed with a stated reason. No signature in this pack is an approval. Register row: RS10. Gate (research register, quoted): _"Recover feature scaling, clustering/model version and cohort counts; assess stability and map old/new segment identities. Do not reuse a segment ID for a different population. App matching weights remain unchanged unless separately approved."_
- **Prepared by:** `repo-agent/session-2026-11-18`.
- **Machine-readable ledger:** [`artifacts/rs10-market-segments-evidence.json`](artifacts/rs10-market-segments-evidence.json) — sha256 `d8f0658807b4864c049481d289f7dd1312be8fb052eeddcbdcdb5c6e0b0f8c56`, 102,883 bytes (canonical JSON, sorted keys, no timestamps, no absolute paths). Two superseded revisions are retained so each regeneration is a diff rather than a fresh audit: the round-14 bytes at [`artifacts/superseded/rs10-market-segments-evidence.round14.json`](artifacts/superseded/rs10-market-segments-evidence.round14.json) (`96054968…`) and the first signed bytes at [`artifacts/superseded/rs10-market-segments-evidence.signed-50fbe7e8.json`](artifacts/superseded/rs10-market-segments-evidence.signed-50fbe7e8.json) (`50fbe7e8…`) — see §6a and §6b.
- **Producer:** `scripts/tools/market_segments_evidence.py`. Run twice → byte-identical (`cmp` clean); `uv run python scripts/tools/market_segments_evidence.py --check` re-measures the checkout and passes.
- **Frozen legacy text:** `docs/analytics/editions/legacy/2026-11-12/market-segments.md` — sha256 `6813e4e121d8e1784f8a4605e8911ea26b634910cac02ce3702c1093d498e958`, 9,328 bytes. All **36** quoted phrases verified verbatim (`legacyQuoteCheck`).
- **Review history:** round 1 **FAIL** (claim inventory incomplete; the scan description over-claimed), round 2 **FAIL** (two dangling claim keys; a scan-location claim that was factually wrong; a composite-score absence that overreached; a missing momentum formula), round 3 **FAIL** (the archive precedent's normalisation was called "different" without evidence; the momentum entry denied per-area values the archive publishes), round 4 **PASS**, explicitly narrow — it attests the round-4 edits and their cited archive evidence, and says so. **The measurements themselves were independently re-derived in round 1**, and no measured value changed after it: rounds 2–4 changed only claims, statements about absences, and references.
- **Upstream:** the cutoff rule and "measured, never cited" lineage discipline from [RS03](2026-11-15-rs03-temporal-evolution-evidence.md); the claim-inventory and quote-check pattern from [RS05](2026-11-17-rs05-facility-premiums-evidence.md) and [RS09](2026-11-18-rs09-macro-sensitivity-evidence.md). `unified_dataset.parquet` sha256 `39d234f703c9d6e098acc885eaadfdc965a6ac217189277c066676b3b117cefe` (1,236,310 × 97) is the same platinum dataset RS04/RS05/RS09 pinned.

## 1. Cutoff

The same measured rule RS03/RS04/RS05/RS09 shipped, computed **on the private rows** so the bound is identical across studies, with an all-types cross-check (`cutoff`):

| Field                             |     Private-based | All types |
| --------------------------------- | ----------------: | --------: |
| `lastCompleteMonth`               |       **2026-10** |   2026-10 |
| Terminal month                    |           2026-11 |   2026-11 |
| Terminal transactions             |               421 |     1,211 |
| Trailing-12 median                |           2,133.0 |   4,587.5 |
| Terminal share of trailing median |        **0.1974** |     0.264 |
| Last complete month transactions  |             2,546 |         — |
| Trailing-12 months                | 2025-11 → 2026-10 |         — |

Every window, count and share in this ledger that touches the frame stops at `lastCompleteMonth`. The frame itself runs 1990-01 → 2026-11.

## 2. What the stored segment asset actually contains (`segmentAsset`)

`app/public/data/segments_enhanced.json.gz` — 3,432 bytes, sha256 `76979cc5fdc4e7fff27847147b70520f896c3f344d701f4ef702c252dd571d56`, `version "1.0.0"`, `lastUpdated 2026-04-19T23:23:07.521202`, top-level keys `insights, lastUpdated, planningAreas, segments, version`.

- **Six segments**, ids unique: `large_size_stable`, `high_growth_recent`, `speculator_hotspots`, `declining_areas`, `mid_tier_value`, `premium_new_units`. `metrics` present for every one.
- **31 planning areas** in a top-level `planningAreas` block, each carrying a `segments` name list; the two directions agree exactly (empty symmetric difference).
- Four insight cards. The article's heading says **five** segments; the asset holds six, and the article's five names do not appear in it.

### 2a. The cohort arithmetic is internally consistent and externally unreproducible (`cohortReconciliation`)

| Measure                                                 | Value              |
| ------------------------------------------------------- | ------------------ |
| Asset cohort total                                      | **911,454**        |
| Sum of `marketShare`                                    | 1.0 (residual 0.0) |
| Share rounding tolerance                                | 0.0005             |
| Any measured population equal to the total?             | **no**             |
| Any segment count reproduced by its own declared areas? | **no**             |

| Segment               | Stored count | Share | Rows in its declared areas |   Difference | Share residual |
| --------------------- | -----------: | ----: | -------------------------: | -----------: | -------------: |
| `declining_areas`     |      112,943 | 0.124 |                    577,562 |     +464,619 |      +0.000085 |
| `high_growth_recent`  |      300,872 | 0.330 |                    319,455 |      +18,583 |      −0.000101 |
| `large_size_stable`   |      114,700 | 0.126 |                    176,470 |      +61,770 |      +0.000157 |
| `mid_tier_value`      |      230,685 | 0.253 |                     **33** | **−230,652** |      −0.000096 |
| `premium_new_units`   |      100,297 | 0.110 |                    176,470 |      +76,173 |      −0.000041 |
| `speculator_hotspots` |       51,957 | 0.057 |                    176,470 |     +124,513 |      −0.000005 |

Every `marketShare` equals its count over the asset's own total to three-decimal rounding — the arithmetic closes on itself. It closes on nothing else:

| Candidate population                          |      Rows | Difference from 911,454 |
| --------------------------------------------- | --------: | ----------------------: |
| Full frame                                    | 1,236,310 |                +324,856 |
| Article's stated period (2017-01 → 2026-10)   |   489,101 |                −422,353 |
| Article's emphasis window (2021-01 → 2026-10) |   401,512 |                −509,942 |
| Asset's own last-updated month cap            |   376,256 |                −535,198 |
| Private rows only                             |   245,655 |                −665,799 |

The only recorded denominator for these counts is a comment beside a literal: `"transactionCount": 114700,  # 12.6% of ~910K` at `docs/plans/2026-02-22-interactive-market-segments-dashboard-implementation.md:457` (`cohortReconciliation.recordedDenominator`). **"~910K" is not an extraction of the frame**, and no measured population equals it.

## 3. Provenance: the "model" is a literal list in a plan document (`methodRecovery`)

This is the finding that decides what the gate can ever be satisfied by.

- **The generator does not exist.** `scripts/generate_segments_data.py` is absent (`generatorScriptExists: false`), and the producer cites the plan document's generator body verbatim, keyed to the `transactionCount` literals at **line 457**.
- A handoff records the generator being _run_ with hand-written loaders — `.claude/handoffs/2026-02-23-interactive-segments-dashboard-implementation.md:371`: _"Generated with 6 segments, 31 planning areas, 4 insight cards"_. The deliverables are **hand-authored constants**, not the output of a fitted model in this checkout.
- **`persistenceProbability` is a label lookup, not a measured transition rate** (`segmentAsset.persistenceByClassification`): HH **0.6** for four segments, LH **0.33** for one, LL **0.5** for one — constant within each `clusterClassification`, assigned from the label by the generator body.

Consequence: "recover the clustering/model version" has no object. There is no model version to recover, only a document revision; and `k` is recoverable only as the number of hard-coded list literals.

## 4. Membership: zero id matches, and only a many-to-many area block (`membershipRecovery`)

| Test                                                       | Result                                                                    |
| ---------------------------------------------------------- | ------------------------------------------------------------------------- |
| Segment ids found as values in `market_segment`            | **0**                                                                     |
| … in `property_segment`                                    | **0**                                                                     |
| … in `price_stratum`                                       | **0**                                                                     |
| Per-transaction membership **for the six stored segments** | **no** — 0 id matches                                                     |
| Per-transaction segmentation **anywhere in the checkout**  | **yes**, in a different taxonomy — see §4a                                |
| Area→segment pairs stored                                  | 51 across 31 areas                                                        |
| Segments per area (distribution)                           | 0 → 6 areas, 1 → 15 areas, 3 → 4 areas, 4 → 6 areas                       |
| Areas with no segment                                      | Bedok, Bukit Batok, Bukit Panjang, Geylang, Jurong East, Marine Parade    |
| Frame `planning_area` values                               | 44, of which **13** are absent from the asset; covered rows **1,185,397** |

Semantics, stated in the ledger and binding on the edition: the zero is a **count of matches**, not a claim that data is missing, and the area block is **many-to-many** — an area maps to zero to four segments — so it does not partition any population and assigns no transaction to one segment.

### 4a. A third directory the first draft never read (`adjacentSegmentedPanel`)

This pack's first version, and the ledger's, scanned `data/pipeline` and `app/public/data` and concluded that no per-transaction membership existed. **That boundary was wrong.** `data/analysis/market_segmentation/` holds:

| File                                | Measure                                                                                                                                                                                                                                |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `housing_unified_segmented.parquet` | **911,797 rows × 61 columns**, months **1990-01 → 2026-01**, with `price`, `planning_area`, and per-row labels `market_tier`, `psf_tier`, `market_tier_period`, `psf_tier_period` and a `Market Segment` region column (785,395 nulls) |
| `tier_performance.parquet`          | 139 rows of annual tier medians (`property_type, market_tier, year, median_price, transaction_count, median_psf`)                                                                                                                      |
| `tier_thresholds.csv`               | the cut points — `Condominium, 1306400.0, 2091000.0, 2091178.0`                                                                                                                                                                        |

What it means, measured rather than inferred: **every row carries a tier label**, which is what "no per-transaction membership" denied; the panel's **911,797 rows sit +343 against the asset's 911,454 cohort total**; and yet **none of the six asset ids appears anywhere among its 61 columns** (`assetIdMatchTotal` 0). The labels are **three price tiers**, not the asset's six behavioural segments, and the panel ends at 2026-01 rather than the 2026-10 cutoff.

So the finding narrows rather than collapses: _the six stored segments have no membership in this checkout_ — and a per-transaction segmented panel with a **different, three-tier taxonomy** does exist and must not be described as absent. The `notMeasurable` entry now says exactly that, and both panels plus the thresholds file are sha-pinned in `inputs`.

`market_segment` in the frame is a **region label, private rows only**: `Core Central Region 38,699 · Rest of Central Region 74,161 · Outside Central Region 132,795`, with **990,655 nulls** equal to the HDB row count and the non-null total equal to the private row count. It can never carry a behavioural segment.

## 5. Identity mapping: there is no legacy id set to map (`methodRecovery.legacyIdentityRecovery`)

The article's five names — `High-Growth HDB`, `Stable Mid-Tier`, `Premium Condo (Low Yield)`, `High-Yield Apartments`, `Luxury Segment` — occur only as prose and table text. **Zero lines** anywhere pair a name with an id field, and **none** of the five names appears in the six-id asset. So "do not reuse a segment ID for a different population" resolves to: there is no old id set to reuse, and the new ids have no predecessor. A taxonomy is either rebuilt under new ids or withdrawn — it cannot be _migrated_.

## 6. What of the method is recorded, and the scan (`methodRecovery.items`, `tokenScan`)

| Gate input                 | Status                                                                  |
| -------------------------- | ----------------------------------------------------------------------- |
| Feature scaling            | `notRecorded` — no scaler or preprocessing artefact                     |
| Log transform              | `notRecorded` — parameters nowhere                                      |
| Feature set / column list  | `notRecorded` for the stored segments                                   |
| `k`                        | recoverable only as six hard-coded literals, not a selected parameter   |
| Model version              | `notRecorded` — the asset's `version` is the payload's own schema label |
| Silhouette / elbow outputs | `notRecorded`                                                           |
| Composite investment score | `notRecorded` for the article's population — see below                  |
| Risk-adjusted momentum     | `notRecorded` for the article's population and undefined rolling window |

The token scan runs over the shipping roots with the legacy text and this artifact excluded, and its `meaning` states what it does and does not establish: **no RS10 implementation or evidence was found in the scanned roots**, while explicitly recording that a plan document _inside_ the scanned `docs` root contains a `KMeans`/`StandardScaler` code **example**, counted among the hits, with nothing connecting it to the shipped values.

Two absences are deliberately narrow, because the checkout does contain precedents:

- **Composite score.** `docs/archive/20260123-hdb-comprehensive-investment-analysis.md` records a 50/50 appreciation/yield composite with per-town vectors (`ANG MO KIO 100.0`, `PUNGGOL 94.3`) over **785,395 HDB transactions, 1990-2026, 2015-2025 focus**. It states the **same procedure** the article states (z-scores, 50/50 weights, scaled 0-100) and records too few parameters to establish equivalence — so the ledger claims **neither** equivalence **nor** difference in normalisation. What differs, measurably, is population and period.
- **Risk-adjusted momentum.** The same archive publishes a per-area Risk-Adjusted Score table — `TANGLIN 0.822` on a sample of **10**, `SEMBAWANG 0.526` on **1,457** — on HDB resale over 1990-2026, without recording its volatility window. Those values cannot stand in for the article's measure on its own population and undefined window.

### 6a. The scan boundary was widened at round 15, and no match changed

`uv run python scripts/tools/market_segments_evidence.py --check` failed on 2026-11-20 against the round-14 ledger, reporting drift in exactly one top-level key: `methodRecovery.tokenScan.filesScanned`, 348 → 349. The cause was a sibling instrument, not a measurement: `scripts/tools/check_edition_lexicon.py` was added to the checkout after the round-14 ledger was written, and `scripts/tools/` was inside the scan's roots.

The fix follows the rule RS09's producer already shipped — exclude the programme's own instruments from any scan whose result is hash-pinned — and widens it to every surface the RF08 programme itself writes, because each of those would have drifted this count the same way:

| Excluded surface                                                                        | Why it is an instrument, not evidence                                                                                                                                                     |
| --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/tools/`                                                                        | the evidence producers and QA utilities themselves                                                                                                                                        |
| `prompts/`                                                                              | the programme's handoffs, runbooks and worker prompts                                                                                                                                     |
| `docs/implementation/` (as before)                                                      | this programme's per-study records                                                                                                                                                        |
| published edition texts under `docs/analytics/editions/`, **except** `editions/legacy/` | a study that signs after RS10 must not move this count; the frozen legacy originals stay **in** the scan, because the article's own method claims are what the tokens are matched against |

The disclosure lives in the ledger (`tokenScan.excludedPrefixes`, `tokenScan.excludedPaths`, `tokenScan.excludedEditionTexts`). The evidence that this removed **nothing** is a field-by-field diff of the two ledgers: **three differences, all in the scan's own declaration** — `excludedEditionTexts` added, `excludedPrefixes` 1 → 3, `filesScanned` 348 → 326 — and **every token match block byte-identical**, including the seven token counts and their first-match lists. So no absence claim in this pack moved; only the statement of where the scan looked, and that statement is now narrower and is recorded rather than implied.

Two runs of the producer are byte-identical (`cmp` clean) and `--check` passes at the new hash. The scan still reports zero matches for `log1p` and the counts recorded in §6, and its `meaning` is unchanged in substance: a zero match is counter-evidence for "none was found", never for "none exists".

### 6b. The first fix was still one file short, and signing is what found it

After the owner signed at `50fbe7e8…`, `--check` failed **again** — and the cause was the signature record itself. The RS10 rows written into the [D12 decision register](../plans/2026-11-12-reporting-refresh-decisions.md) quote the reviewer's vocabulary ("elbow K=7", "silhouette maximum K=2"), that file sits under `docs/plans/`, and `docs/plans/` has to stay in the scan because the plan documents are load-bearing evidence here — the generator body that holds the six segment literals lives in one. So recording a verdict moved a pinned count: the ledger stopped re-measuring because the act of approving it was written down.

The register now joins the tool itself in `EXCLUDED_SCAN_PATHS`, on the same argument — a document that quotes the tokens it is scanned for cannot be evidence of the implementation those tokens index. The register is the only mutable prose file the programme writes outside `docs/implementation/` and `prompts/`, so this closes the class rather than today's instance.

The diff against the signed ledger is **two fields**: `excludedPaths` 1 → 2 and `filesScanned` 326 → 325, with every token match block byte-identical (the two counts that had drifted — `Silhouette` 4 → 5 files and `elbow` 3 → 4 — return to their signed values). The signed ledger is retained at `artifacts/superseded/rs10-market-segments-evidence.signed-50fbe7e8.json`.

**The lesson is worth more than the fix, and it belongs to the programme, not this study:** a hash-pinned scan that reads documentation is not stable under the act of recording a review, an approval or a handoff. Three rounds of this study's own artefacts caused three separate drifts. Any future producer that scans `.md` should expect it, and should exclude every surface the programme writes **before** the first signature — not after.

## 7. The CAGR table: the window is a property-type question (`cagrWindow`)

| Property type |    Rows | Distinct months | 2015-2025 window available? |            Months observed / expected |
| ------------- | ------: | --------------: | --------------------------- | ------------------------------------: |
| HDB           | 990,655 |             443 | **yes**                     | **132 / 132**, 259,219 rows in window |
| Condominium   | 245,655 |              71 | **no** — starts 2021-01     |      60 / 132, 224,404 rows in window |

Measured under the legacy's own **50-transactions-per-area-year** floor, for the six areas its table names (HDB only):

| Area        |  HDB CAGR | Legacy band | Within band? | Status                                                     |
| ----------- | --------: | ----------- | ------------ | ---------------------------------------------------------- |
| Queenstown  | **4.87%** | `~4-6%`     | **yes**      | measured                                                   |
| Jurong East |     2.97% | `~4-6%`     | no           | measured                                                   |
| Punggol     |     5.63% | `~3-5%`     | no           | measured                                                   |
| Sengkang    |     4.93% | `~2-4%`     | no           | measured                                                   |
| Woodlands   |     4.44% | `~1-3%`     | no           | measured                                                   |
| Bukit Timah |     **—** | `~5-7%`     | —            | `notMeasurableUnderLegacyFloor` (2015 endpoint n = **39**) |

Refusing Bukit Timah is the measurement, not a gap: its 2015 endpoint has 39 transactions, below the floor the legacy article itself declares. Five of six areas fall outside the band the article published, and the sixth is the only one inside.

## 8. App matching weights: recorded, pinned, unchanged (`appMatchingWeights`)

The gate says the app's matching weights stay unchanged unless separately approved. The ledger records them (`app/src/hooks/useSegmentMatching.ts`, 30/25/20/15/10 summing to 100, hard filter `spatialClassification`) and **sha256-pins the file**, so any later change shows up as drift. `changedByThisStudy: false`, and no approval for a change is recorded anywhere.

## 9. What the gate asks for and this checkout cannot supply (`notMeasurable`)

| Gate clause                                               | Id                                  | Status                                                                  |
| --------------------------------------------------------- | ----------------------------------- | ----------------------------------------------------------------------- |
| Recover feature scaling                                   | `featureScaling`                    | `notRecorded`                                                           |
| Recover clustering model version / K                      | `clusteringModelVersionAndK`        | `notRecorded`                                                           |
| Assess stability                                          | `stabilityEvidence`                 | `notRecorded` — the only stability-shaped field is a per-label constant |
| Recover cohort counts                                     | `cohortCountsAsVerifiedPopulations` | `notReproducible`                                                       |
| Map old/new segment identities                            | `perTransactionMembership`          | `notRecorded`                                                           |
| …do not reuse a segment ID for a different population     | `oldToNewIdentityMapping`           | `notReproducible` — no legacy id set exists                             |
| App matching weights unchanged unless separately approved | `appMatchingWeights`                | `notChangedByThisStudy`                                                 |

## 10. Every legacy claim, disposed (`legacyClaims`, 36 entries)

**36 claims, 36/36 verified verbatim**: **1 re-measured, 4 withdrawn, 31 not-reproducible**, spanning the five-segment profile table, the six planning-area CAGR rows, the five strategy rows, the four composite-score bands, the score formula, `>85%` hierarchical agreement, `r ~ -0.3`, the `~288K` transaction volume, the declared `2017-2026` period, the risk-adjusted momentum formula, and the `4-5% CAGR` recommendation.

Every `ledgerKey` is resolved **at build time** (`claimKeyCheck`, 36 checked, 0 unresolved) and an unresolved key fails the build. The ledger states plainly that resolution is **syntactic** and does not judge whether the resolved field supports the disposition.

## 11. What this pack does not establish

- **No clustering, segmentation, stability or score estimate of any kind.** The asset behind the article is a hand-written literal list; there is no model here to reproduce.
- **No cohort figure is verified.** The six counts close against their own shares and against nothing else; they stand only as the asset's own numbers.
- **No membership claim.** Zero id matches and a many-to-many area block; no transaction belongs to a segment.
- **No identity migration.** The legacy names have no ids, so no mapping exists to build or refuse.
- **No 2015-2025 CAGR for any property type except HDB**, and none at all for Bukit Timah under the legacy's own floor.
- **No claim that the archive precedents are or are not the same computation** — only that they cover a different population and period, and record too few parameters to decide.
- **No change to app matching weights**, and no approval for one.

## 12. Sign-off record

Signed on 2026-11-20. Full record, with the two pins, the gate sequence and the verbatim attestations: **[RS10 sign-off](2026-11-20-rs10-market-segments-editions-signoff.md)**.

| Role          | Signatory                                             | Pins                                | Recorded   |
| ------------- | ----------------------------------------------------- | ----------------------------------- | ---------- |
| source/cutoff | `howt`                                                | ledger `d8f06588…`                  | 2026-11-20 |
| scientific    | `openai-codex/gpt-6-luna (xhigh)` (`automated: true`) | ledger `d8f06588…`                  | 2026-11-20 |
| publication   | `howt`                                                | text `2cb19917…` as `editionSha256` | 2026-11-20 |

Both pins moved once after the owner's first signing act, because recording that act broke the ledger's `--check` (§6b). The movement is disclosed in the sign-off record with the field-level diffs; no measurement, disposition or absence claim changed.

## 13. Review history

| Round | Verdict                                     | What it found                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ----- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | FAIL                                        | claim inventory incomplete (10 quantitative claims missing); the scan description over-claimed that every hit was prose/plan/false-positive                                                                                                                                                                                                                                                                                                                   |
| 2     | FAIL                                        | two dangling claim keys; a scan-location claim that was factually wrong (the plan example is inside the scanned docs root and was counted); "no score vector anywhere" contradicted by the archive; the risk-adjusted momentum formula uncaptured                                                                                                                                                                                                             |
| 3     | FAIL                                        | the archive precedent's normalisation was called "different" with no evidence — the archive states the _same_ procedure; the momentum entry denied per-area values the archive publishes (TANGLIN 0.822, SEMBAWANG 0.526)                                                                                                                                                                                                                                     |
| 4     | **PASS**                                    | the four round-3 edits; narrow by its own statement — it attests those edits and their cited archive evidence, not a fresh audit of every measurement. The measurements were re-derived in round 1 and no measured value has changed since.                                                                                                                                                                                                                   |
| 5–13  | not tabulated here                          | this table was maintained through round 4 only; the later rounds' findings are not recorded in this pack, and reconstructing findings this table's author did not observe would be invention.                                                                                                                                                                                                                                                                 |
| 14    | **PASS**                                    | recorded in the session handoff, not in this pack: the ledger passed at round 14 with one non-blocking warning about `definition` wording. The ledger bytes it passed are retained at `artifacts/superseded/rs10-market-segments-evidence.round14.json` (`96054968…`).                                                                                                                                                                                        |
| 15    | **producer change, reviewed with the text** | scan-boundary fix (§6a): the programme's own instrument surfaces are excluded from the token scan, the count moves 348 → 326, and every token match block is byte-identical.                                                                                                                                                                                                                                                                                  |
| 16    | **FAIL**                                    | text review by `openai-codex/gpt-6-luna (xhigh)`, 2026-11-20, three findings — two blocking: a stated 25× count ratio where the ledger gives 9.54×, and "five of the six areas" where the ledger gives four of five measurable outside the band with Bukit Timah unmeasurable; one non-blocking: an unnamed "closest" candidate in the cohort comparison. **No ledger value was wrong** — all three were prose errors in the edition text.                    |
| 17    | **PASS**                                    | narrow re-review of the three fixes; confirmed the corrected sentences against `clusteringArtefacts.countRatios`, `cagrWindow.areaCagr.areas[].withinLegacyBand` and `cohortReconciliation.candidatePopulations`, and that nothing else changed.                                                                                                                                                                                                              |
| 18    | **PASS**                                    | final confirmation, after the reviewer's own non-blocking warning was taken: the cohort sentence now names the full-frame candidate (+324,856) beside the dated-window one (−422,353). Attested bytes: edition text sha256 `ad4ecebae6b2a4baccb5e79423cb7cda68fc30145f5b3b9c50dfdcf88666365a`, 47,257 bytes; ledger `50fbe7e8…`.                                                                                                                              |
| 19    | **PASS**                                    | re-attestation after the second scan-boundary change (§6b), which the signature record itself triggered. The ledger moved to `d8f06588…` on a **two-field** diff (`excludedPaths` 1 → 2, `filesScanned` 326 → 325) with token match blocks byte-identical, and the edition text moved to `2cb19917…` on two hash citations only. D12 trap #4 in its positive form: an attestation covers a pin, so a pin that must move is re-attested rather than inherited. |

The four rounds produced **no wrong measurement** — the defects were the claim inventory, statements about absences, and references. The study's measurements were right on their first audited pass; its prose about what was absent was not. The same held at rounds 16–18: every finding was a statement in the edition text, and no ledger value moved.
