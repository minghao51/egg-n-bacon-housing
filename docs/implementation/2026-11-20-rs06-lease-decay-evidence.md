# RS06 evidence pack — lease-decay: one stated response, lease age validated at transaction month, the article's own tables re-measured, and the unit contradiction left unconverted

- **Date:** 2026-11-20
- **Status:** **Prepared for review — round 1, pending review.** The ledger is measured and `--check`-able; nothing is fitted, no coefficient is restated in any unit, and no edition text is drafted. No signature in this pack is an approval. Register row: RS06, gate quoted verbatim in §0. This pack answers the gate's clauses; it does not clear the chart or model gates.
- **Prepared by:** `repo-agent/session-2026-11-20`.
- **Machine-readable ledger:** [`artifacts/rs06-lease-decay-evidence.json`](artifacts/rs06-lease-decay-evidence.json) — sha256 `f022f8c3babc8f603f91ae04b5b6e9791780900c3b9e157e7a07cae6cf555d27`, 197,825 bytes (canonical JSON, sorted keys, no timestamps, no absolute paths). The producer ran twice; the two outputs are byte-identical (`cmp` clean), and `uv run python scripts/tools/lease_decay_evidence.py --check` re-measures the checkout and passes. The ledger's scans exclude `docs/implementation/` and `scripts/tools/`, so this prose pack and the producer itself cannot drift the pinned counts.
- **Producer:** `scripts/tools/lease_decay_evidence.py`.
- **Frozen legacy text:** `docs/analytics/editions/legacy/2026-11-12/lease-decay.md` — sha256 `6aab72f046c4df45368843a3b1046e1165097aef22a5691e7231f1840464f1b4`, 7,740 bytes. All **36** quoted phrases verified verbatim (`legacyQuoteCheck`: 36 checked, 36 verified); the build fails on any zero-occurrence phrase.
- **Upstream conventions:** the measured cutoff rule from RS03/RS04/RS05/RS09/RS10; the claim-inventory, quote-check and build-time claim-key resolution pattern from RS05/RS09/RS10; the scan-boundary exclusion rule (the programme's own surfaces out of every hash-pinned scan) from RS10's round-15/16 fix. `unified_dataset.parquet` sha256 `39d234f703c9d6e098acc885eaadfdc965a6ac217189277c066676b3b117cefe` (1,236,310 × 97) is the same platinum dataset RS04/RS05/RS09/RS10 pinned.

## 0. The gate, quoted verbatim, and answered clause by clause

> "Resolve PSF/PSM and total-price versus per-area response before fitting. Validate lease age as of transaction date. Reconcile article versus interactive-band lineage. Keep chart/model gates until repaired coefficients and wording are reviewed. Never convert a coefficient without confirming its original response/unit."

The same string is machine-checked against the research register at build time (`gates.gateClauseSource`, `docs/plans/2026-11-12-reporting-refresh-research-register.md:39`).

1. **"Resolve PSF/PSM and total-price versus per-area response before fitting."** — Resolved as an explicit producer decision with measured evidence (§2, `responseDecision`), per the D12/RF08 disposition of 2026-11-18: _"RS06/RS07 unit-and-response choices are made by the producer from the measured columns and stated in the ledger as an explicit decision with its evidence, not escalated again."_ Decision: response = `psf` ($ per square foot, exact on all 990,655 HDB rows); secondary per-area measure = derived PSM = `price / floor_area_sqm`; total price used only where a field is named `medianPrice`. No model is fitted by this pack.
2. **"Validate lease age as of transaction date."** — Done, and the precision stated: the HDB resale source dates transactions to the month, so validation is as of transaction **month** (§3, `leaseAgeValidation`): 37,152 of 37,153 rows carrying a stored `remaining_lease` agree with 99 − derived age within 1.0 year; all exceptions counted, including 51 negative-age rows.
3. **"Reconcile article versus interactive-band lineage."** — Reconciled by measurement and stated symmetrically (§6, `interactiveAsset.lineage`): the article bands remaining years into five bands; the interactive asset bands lease age into thirteen five-year bins with a freshest-band baseline and seven absent age bins; two of three insight discounts equal the magnitudes of the article's published discounts and the third does not. Nothing in the checkout links either artefact's producer to the other, so each is evidence **neither for nor against** the other's numbers.
4. **"Keep chart/model gates until repaired coefficients and wording are reviewed."** — Both gates recorded as **in force** (§7, `gates`). The chart gate is already encoded in the app (`app/src/components/studies/lib/studies.ts`, sha-pinned, `unitReview: true`, `chartsWithheld: true`, quoted at line 130); the model gate holds because no repaired coefficient exists — none can, while the unit question of clause 5 stands. No edition text is written by this pack.
5. **"Never convert a coefficient without confirming its original response/unit."** — Not converted, and the reasons are fields, not prose: the frozen text's own appendix names `price_per_sqm` as the response while its coefficient sentence says PSF; the fitted model is absent (`absenceScans.fittedModel`); and the only unit label for the coefficient anywhere in the checkout is an unlinked chart axis reading "Coefficient (SGD/PSM per year)". The number +$54.75 is recorded as stored text and withdrawn in both sentences that state it (§8). `responseDecision.conversionPerformed: false`.

## 1. Cutoff

The same measured last-complete-month rule the sibling studies shipped, computed on the HDB rows this study analyses (`cutoff`):

| Field                                        |                                                     Value |
| -------------------------------------------- | --------------------------------------------------------: |
| `lastCompleteMonth`                          |                                               **2026-10** |
| Terminal month                               |                                                   2026-11 |
| Terminal transactions                        |                                                       790 |
| Trailing-12 median                           |                                                   2,125.0 |
| Terminal share of trailing median            |                                                    0.3718 |
| Last complete month transactions             |                                                     2,173 |
| Last complete month share of trailing median |                                                    1.0226 |
| Frame range                                  | 1990-01 → 2026-11 (443 distinct HDB months, 990,655 rows) |

Every window, count and share in this ledger that touches the frame stops at `lastCompleteMonth`. The bound matches the cutoff RS03's accepted attestation records (terminal 2026-11 at 790 transactions, 0.3718 of the trailing median, on the same HDB rows).

## 2. The response decision (gate clause 1) — `responseDecision`

What the frame actually holds for HDB rows, measured (`responseDecision.columnsExamined`):

| Column                  | Non-null on HDB rows | Note                                              |
| ----------------------- | -------------------: | ------------------------------------------------- |
| `price`                 |              990,655 | SGD total price                                   |
| `floor_area_sqm`        |              990,655 | square metres                                     |
| `psf`                   |              990,655 | measured $ per square foot — see identity check   |
| `area_sqm`, `area_sqft` |                0 / 0 | private rows only                                 |
| `Unit Price ($ PSF)`    |                    0 | 122,017 non-null **frame-wide**, all private rows |
| `Unit Price ($ PSM)`    |                    0 | 122,017 non-null **frame-wide**, all private rows |

The four-states rule applies to the per-area price columns: `Unit Price ($ PSM)` is a **present and populated** column — in the 97-column schema, non-null on 122,017 private rows and null on every HDB row — not an absent value and not an absent column. Both `Unit Price` columns are stored as strings with thousands separators, so a plain numeric read parses 7,093 of the `($ PSF)` values and 0 of the `($ PSM)` values; the ledger records `frameNonNull` and `numericParsedNonNull` separately. The absent-value state on HDB rows is `floor_level` (present column, all null there) (`responseDecision.columnsExamined`, `.fourStatesNote`).

**Identity check** (`responseDecision.identityCheck`): `psf == price / (floor_area_sqm × 10.7639104167)` holds on all 990,655 HDB rows (max absolute deviation 0.001503), so the `psf` column is exactly the per-square-foot price, and per-square-metre prices are derived, never read from a stored column.

**Decision** (`responseDecision.decision`, quoted from the ledger): _response = psf, the frame's measured $-per-square-foot column; secondary per-area measure = derivedPsm = price / floor_area_sqm; total-price measure = price, used only where a field is named medianPrice. Any future fitting uses one of these stated responses with its unit named in the same sentence. No coefficient is converted between units in this ledger, and no model is fitted by this pack._ `fitPerformed: false`, `conversionPerformed: false`.

**The legacy's own contradiction, recorded not resolved** (`responseDecision.legacyResponseStatement`): the frozen appendix states the fitted response as `price_per_sqm`; the frozen coefficient sentence states PSF. Both are quoted verbatim in the ledger; this pack does not choose which one the legacy author "meant".

**Unit invariance of the discounts** (`responseDecision.unitInvarianceOfBandDiscounts`, measured at `bandTable.unitInvarianceMaxAbsDiffPsmVsPsfDiscount` = 0.0): because `psf = derivedPsm / 10.7639104167` row-exactly, band discounts computed on PSF equal those computed on PSM to the recorded precision. The discounts are per-area whatever the table's price column suggests; the **levels** are where PSF and PSM differ by an order of magnitude.

## 3. Lease age validated as of transaction month (gate clause 2) — `leaseAgeValidation`

Derivation (`leaseAgeValidation.derivation`): `leaseAgeYears = (transactionYear + (transactionMonth−1)/12) − lease_commence_date`; `derivedRemainingYears = 99 − leaseAgeYears`. The 99-year tenure is an **assumption**, and it is what the validation below tests. Precision is month-level because the source is month-level.

The stored `remaining_lease` column (`leaseAgeValidation.storedColumn`):

| Measure            |                                                  Value |
| ------------------ | -----------------------------------------------------: |
| Non-null rows      | **37,153** — 2015: 17,780, 2016: 19,373; no other year |
| Null rows          |                            953,502 of 990,655 HDB rows |
| Numeric range      |                    48.0 – 97.0 → **years**, not months |
| Rows equal to zero |                                                      0 |

So the validation window is the stored column's own coverage (2015–2016), not the study window — recorded as such. The legacy methodology's `remaining_lease_months / 12` names a months-scale column of the retired L1 frame, which no shipped frame carries (§5); the archived L2/L3 schema documents record it for those retired frames, which is where the column's provenance stops.

Agreement (`leaseAgeValidation.agreement`): stored minus derived remaining lease — within 0.02 years: 2,511; within 0.5: 29,185; within 1.0: **37,152 of 37,153**; mean absolute deviation 0.345 y; max 1.0833 y. The single row over 1.0 is listed with its fields (`rowsOverOneYear`: month 2016-02, stored 77.0, derived 75.9167, commencement 1993.0).

Exceptions, counted not excluded (`leaseAgeValidation.exceptions`): **51 rows** (1991–2011) have a transaction month **before** `lease_commence_date` under the 99-year assumption, so their derived remaining lease exceeds 99 (max 100.6667). All sit outside the study window. Derived range: frame 38.25 – 100.6667 years; rows at or below zero: 0; below 30 years: 0.

## 4. The band table re-measured (gate clause 1's table half) — `bandTable`

Definition adopted verbatim from the frozen appendix (`bandTable.definition`): bins [0, 60, 70, 80, 90, 100], labels [<60, 60-70, 70-80, 80-90, 90+], right-closed (the legacy states bins but not edge handling — the convention is a stated field, and the window's rows sitting exactly on each interior edge are counted: 568 / 356 / 354 / 409). Band variable = derived remaining years (§3); the stored column cannot band the window. Window = 2017-01 (the article's stated data period start) through 2026-10 (the measured cutoff); **243,867** banded rows.

### 4a. Measured beside published — every article value (`bandTable.articleRowsVsMeasured`)

| Band  | Count (article) | Count (measured) | Δ count | Median price art/mine | Per-area art / measured PSM / measured PSF | Mean remaining art/mine |
| ----- | --------------: | ---------------: | ------: | --------------------- | ------------------------------------------ | ----------------------- |
| 90+   |          50,912 |           52,160 |  +1,248 | $558,000 / $565,000   | $6,205 / 6,309.73 / **586.19**             | 93.5 / 93.06            |
| 80-90 |          29,562 |           33,083 |  +3,521 | $520,000 / $550,000   | $5,389 / 6,236.96 / **579.43**             | 84.6 / 85.1             |
| 70-80 |          47,044 |           50,601 |  +3,557 | $548,000 / $550,000   | $4,845 / 4,939.13 / **458.86**             | 75.4 / 75.22            |
| 60-70 |          54,521 |           57,267 |  +2,746 | $446,000 / $463,000   | $4,730 / 4,782.61 / **444.32**             | 64.6 / 64.6             |
| <60   |          41,595 |           50,756 |  +9,161 | $390,000 / $405,000   | $5,274 / 5,384.62 / **500.25**             | 54.5 / 54.34            |

**Which unit the article's per-area column holds — measured, three independent ways** (`bandTable.unitIdentification`):

1. The measured nearest unit is `psm` for **all five rows** (`measuredNearestUnitByRow`): the article's values sit within 52.61–847.96 $/sqm of the measured median PSM but ~4,286–5,619 $/sqft from the measured median PSF.
2. The stored CSV `data/analysis/lease_decay/lease_decay_analysis.csv` names the same values **`median_psm`**, and they equal the article's column at integer rounding on all five bands (5,273.97→5,274; 4,729.73→4,730; 4,844.90→4,845; 5,388.62→5,389; 6,205.30→6,205), with counts 5/5 and median prices 5/5 (`storedCsvMatchesArticle`). Its five counts sum to **223,634 exactly** — the article's stated sample (`storedCsvCountSumMinusArticleSample` = 0).
3. The stored chart `lease_decay_psm_by_band.png` is titled **"Median Price per SQM by Remaining Lease Band"** with bars at the article's values (visual read, recorded in `storedArtefacts.pngs`).

Each is a **correspondence between stored artefacts, not a proven lineage** — no producer links them (§5) — so the identification is of the _values_ (they are per-square-metre): the article's own Technical Findings label the same numbers "median PSM" that its band table labels "Median PSF". The pack repairs the unit, not the label's history.

**The discount column mixes per-area discounts into a price-headed table** (`articleOwnArithmetic`): every published discount reproduces from the article's own per-area column — 15.0 / 23.77 / 21.92 / 13.15 / baseline against its stated −15.0% / −23.8% / −21.9% / −13.2% — and **not** from its own Median Price column (which gives 30.11 / 20.07 / 1.79 / 6.81 / baseline). Measured on the window, the same split: per-area discounts 14.66 / 24.2 / 21.72 / 1.15 / 0 vs median-price discounts 28.32 / 18.05 / 2.65 / 2.65 / 0. The trade-off row's −23.8% (claim C7) and the takeaway's "prices are about **21.9%** below the 90+ year baseline" (claim C1) are per-area discounts stated as price-level sentences; both readings are recorded rather than chosen.

**Measured facts** (`bandTable.measuredFacts`): highest-volume band 60-70 (57,267) — the takeaway's "highest transaction volume" holds; cheapest band by derived PSM is 60-70 (4,782.61) and <60 (5,384.62) is not the cheapest — the "<60 is not the cheapest on a PSF basis" claim's direction holds. Share arithmetic (`bandTable.shareArithmetic`): the article's 24.4% = 54,521 / 223,634 from its own table; the measured window share is 0.2348.

### 4b. The sample claim (`sampleClaim`)

Stated: 223,634 HDB transactions, 2017-2026, lease range 30-99 years. Measured: **243,867** window rows (+20,233); no month-capped window starting 2017-01 with a terminal month from 2025-01 through 2026-11 reproduces the stated sample — all 23 candidates recorded with their differences (`candidateCount`, `candidateWindows`, `anyCandidateEqualsStatedSample: false`; nearest: 2025-12 at 222,066, −1,568; 2026-01 at 224,404, +770). The window's measured remaining-lease range is 38.25 – 97.4167 years against the stated 30 – 99. The stated sample stands as the legacy's own figure, unreproduced.

## 5. What is absent, with its scan boundary — `absenceScans`

**The L1 frame the article names as primary input** (`absenceScans.l1Frame`): `data/parquets/L1/housing_hdb_transaction.parquet` does not exist; the `data/parquets` root does not exist; and a filename scan of `data/` for the labelled token `housing_hdb_transaction` records no match — `filenameMatchesUnderData` is the enumeration, and it is empty because that scan found nothing, not because the field is unpopulated. Boundary: the filename scan walks `data`, `app/public/data`, `scripts`, `src`, `docs` (excluding `docs/implementation/`, the programme's own records). The legacy producer that read it is retired — an absence with a boundary, not a claim about the source's history.

**The L3 frame the article names as advanced input** (`absenceScans.l3Frame`): does not exist; a filename scan of `data/` for the labelled token `housing_unified` finds only the two segmented panels under `data/analysis/market_segmentation*` (RS10's adjacent panels, a different subject), enumerated in `filenameMatchesUnderData`.

**The fitted model** (`absenceScans.fittedModel`): absent. The filename scan for `lease` records its matched-file count and its full match list as fields (`matchCount`, `matches`), and every match is listed there: the six series artefacts (two CSVs, four PNGs), the interactive JSON asset, the frozen and live article texts, and two `dashboard-release*.json` files whose names merely contain the substring "lease" (recorded, not filtered). No coefficient file, pickle, joblib or parameter artefact exists. `docs/implementation/` is excluded from the filename scan because it holds this programme's own records — including this ledger and this prose — and a hash-pinned scan cannot read its own output.

**The band definition as executed** (`absenceScans.bandDefinitionAsExecuted`): the stated bins literal matches **prose only** — the frozen legacy text and its live twin, and no code file on the scanned surface; the match's occurrence and file counts are the token's own fields (`absenceScans.tokenScan.tokens."bins [0, 60, 70, 80, 90, 100]".occurrences`, `.fileCount`). The definition this ledger uses is the stated bins re-implemented in the producer.

**Token scan** (`absenceScans.tokenScan`): roots `docs`, `scripts`, `src`, `app/src`; suffixes `.md/.py/.ts/.tsx`; the number of files scanned is `filesScanned`; excluded prefixes `docs/implementation/`, `scripts/tools/`, `prompts/`, published edition texts under `docs/analytics/editions/` **except** the frozen legacy originals (which stay in, because the article's own method claims are what the tokens are matched against), plus the producer itself and the D12 decision register by path. Every exclusion is disclosed in the ledger. Token results, none of which is a lease-decay implementation — each token's occurrence count, file count and file list are its own fields (`tokens.<token>.occurrences`, `.fileCount`, `.files`); the summary names what the matches are: `54.75` (the frozen and live article texts and both findings pages), `Mann-Whitney` (article texts only), `Bala` (prose, including causal-inference overviews), `remaining_lease_months` (prose and archive schema documents for the retired frames), `lease_decay` (prose plus the app's stored-asset wiring: `studies.ts`, `tool-assets.ts`, `tool-evidence.ts`). Hits are **not** claimed to be uniformly prose or false positives — the file lists record every one.

**The article-versus-interactive producers**: no script, notebook or artefact in the checkout links the interactive asset's producer to the article's computation; the article's own provenance section states the legacy Python scripts were retired. This is a screened boundary (`interactiveAsset.lineage.statement`), and it cuts both ways — recorded in §6.

**Stored artefacts that DO exist, sha-pinned** (`storedArtefacts`): `data/analysis/lease_decay/` (the five-band CSV with the `median_psm` column, 472 bytes; the rounded-statistics CSV whose `price_per_sqm_median` repeats the article's per-area values, 570 bytes; three PNGs) and `app/public/data/analysis/lease_decay_advanced/lease_decay_advanced_analysis.png` (538,069 bytes). Origin unverified — stored artefacts whose producer code is retired; their values are compared, not attributed. Each PNG carries a human visual read pinned by hash; each is an **unlinked** artefact: evidence neither for nor against the article's computation.

## 6. Article versus interactive-band lineage (gate clause 3) — `interactiveAsset`

`app/public/data/interactive_tools/lease_decay_analysis.json.gz` — sha256 `09da6d774759e1f25c44fd38d02d854e421130d7258a0c521e065fa6ee0aac69`, 1,164 bytes, keys `bands, insights, town_decay_rates`.

**The two bandings are different taxonomies** (`lineage.bandingIsADifferentTaxonomy`): the article bands **remaining years** into five bands [0,60,70,80,90,100] with a 90+ baseline; the asset bands **lease age** into thirteen five-year bins with a freshest-band baseline. Screened as — the only band storing discount 0.0 is the freshest age band 0-5, so the stored discounts are relative to the freshest band (`discountBaseline`; origin unverified). Two bands store negative discounts (5-10 at −11.02, 10-15 at −18.58 — above the stored baseline), and the 90-95 age band is the only one labelled `risk_zone: "safe"` (twelve store `"cliff"`).

**Coverage gap inside the asset** (`ageCoverage`): seven of the twenty five-year age bins are **absent rows** — 60-65 through 85-90 and 95-100 — i.e. remaining lease of roughly 4–39 years has no band row. An absence inside the asset, counted; not a claim about the market.

**Three populations, none equal** (`countSumVersus`): the asset's 13 band counts sum to 288,374 — **+64,740** against the article's stated 223,634 and **+44,507** against the measured window's 243,867.

**Insights block cross-checked both ways** (`insights`): `maturity_cliff` (70-80) stores discount 21.9 — equal to the magnitude of the article's published −21.9% — and annual rate 0.93, which **equals** the stored CSV's `annual_decay_pct` 0.93 for that band; `best_value` (60-70) stores discount 23.8 (equal to |−23.8%|) and annual rate 0.79, which **differs** from the CSV's 0.69 by 0.10; `safe_zone` (90+) stores discount 5.2, which **disagrees** with the article's own baseline convention (its table calls 90+ the baseline, 0.0) and with the CSV (0.0), with annual rate 0.52 against the CSV's 0.0. Summary (`lineage.insightsMatchArticleDiscounts`): matches `best_value`, `maturity_cliff`; disagreement `safe_zone`. A match of stored numbers is a **correspondence, not a proven lineage**.

**Town universes differ** (`townDecayRates`): the asset holds 30 towns, the frame 27 HDB towns; intersection 23; asset-only CHANGI, DOWNTOWN CORE, KALLANG, NOVENA, OUTRAM, ROCHOR, TANGLIN (not HDB resale towns in the frame); frame-only BUKIT BATOK, CENTRAL AREA, KALLANG/WHAMPOA, LIM CHU KANG — including the KALLANG naming split. The asset's town universe is not the frame's.

**Provenance path check** (`lineage.provenancePathCheck`): the article's provenance names `app/public/data/analysis/` as the served location; the interactive asset actually lives under `app/public/data/interactive_tools/`, and the analysis directory holds only the advanced PNG for this series. A location discrepancy between the article's sentence and the checkout, recorded as measured.

**Lineage statement, symmetric** (`lineage.statement`): screened as, origin unverified — nothing in this checkout links the asset's producer to the article's computation, and because the asset is unlinked it is evidence **neither for nor against** the article's numbers. The correspondences above are recorded in both directions and neither is promoted to derivation.

## 7. The gates (gate clause 4) — `gates`

- **Chart gate: in force.** Already encoded in the app — `app/src/components/studies/lib/studies.ts` (sha256 `0a05079c5b54015bbcfd151ac9ef3de7cedfae34824e8b32f1f5e8e227c4044f`), `unitReview: true`, `chartsWithheld: true`, line 130: _"Unit review required: one source table labels a per-square-metre statistic as “Median PSF”. The tables stay readable, but no chart is drawn from them until units and discount arithmetic are reconciled."_ This pack changes no app code; the gate stays until repaired tables are reviewed.
- **Model gate: in force.** `fitPerformed: false`; no repaired coefficient exists to review. The §2 decision binds any future fitting; the gate stays until a reviewed coefficient with a confirmed unit exists.
- **Edition text: not written by this pack.** Round 1 pending review; no wording is repaired until the review chain records it.

## 8. What the coefficient question leaves unmeasurable — `regressionInputs`

- **The coefficient +$54.75** (`regressionInputs.coefficient`): `unitConfirmable: false`, `conversionPerformed: false`, `fittedModelPresent: false`, status **withdrawn**. The frozen text contradicts itself (appendix response `price_per_sqm`, sentence PSF); the fitted model is absent (§5); the only unit label in the checkout is the unlinked chart axis "Coefficient (SGD/PSM per year)" (`storedArtefacts.coefficientAxisLabel`) — screened as, not confirmed. The number is not restated in any unit, in this pack or in any future edition, until a confirmed unit exists. Claims C9 and C36 (both sentences that state it) are withdrawn on exactly this record.
- **Floor level** (`regressionInputs.regressors.floorLevel`): the column exists in the schema and is null on **all 990,655 HDB rows** — the stated FloorLevel term is not measurable on HDB rows from this frame, so the hedonic specification (claim C31) is **withdrawn**: not runnable as stated, and no coefficients exist to convert.
- **Mann-Whitney policy threshold** (claims C20/C32): **not-reproducible** — no implementation or stored result on the shipping surface, and population, window and alternative unstated; underspecified, and not chosen for it.
- **Bala's curve** (claim C33) and **spline arbitrage** (claim C21): **not-reproducible** — parameters unstated, no implementation or stored result; the unlinked PNG's Bala panel is recorded symmetrically (neither for nor against).
- **Annual decay approximation** (claim C29): **not-reproducible** — no formula and no baseline band stated; the CSV's `annual_decay_pct` and the interactive asset's annual rates are unlinked to it and disagree with each other at two of three insight points (§6).
- Available regressors, for the record: lease term (derived, validated §3), MRT distance (979,056 non-null of 990,655), town (990,655 non-empty, 27 distinct).

## 9. The town table and the Pasir Ris inversion — `townTable`

Definition adopted verbatim: short lease (<70 derived remaining years) vs fresh lease (≥90) median PSM within the same town. The frozen text states **no window** for this table — recorded as underspecified and not chosen for it; the ledger re-measures under the article's stated data period start capped at the measured cutoff, and the window is a field. Per-area measure = derived PSM (§2).

| Town        | Short (n)        | Fresh (n)         | Measured discount | Article row              | Article's own arithmetic |
| ----------- | ---------------- | ----------------- | ----------------: | ------------------------ | -----------------------: |
| CLEMENTI    | 5,298.51 (3,716) | 8,979.17 (991)    |         **40.99** | $5,224 / $8,796 / 40.6%  |                    40.61 |
| TOA PAYOH   | 5,068.49 (5,005) | 10,588.24 (1,316) |         **52.13** | $4,939 / $8,182 / 39.6%  |                    39.64 |
| QUEENSTOWN  | 5,589.04 (2,951) | 9,734.94 (1,762)  |         **42.59** | $5,526 / $9,048 / 38.9%  |                    38.93 |
| WOODLANDS   | 4,725.27 (3,889) | 5,806.45 (2,776)  |         **18.62** | $4,262 / $4,544 / 6.2%   |                     6.21 |
| JURONG WEST | 4,368.93 (6,474) | 6,021.51 (1,686)  |         **27.44** | $4,496 / $4,516 / 0.4%   |                     0.44 |
| PASIR RIS   | 5,433.07 (3,063) | 5,967.74 (624)    |          **8.96** | $5,621 / $4,676 / −20.2% |               **−20.21** |

- Every published discount reproduces from its own row's values under (fresh − short)/fresh (`articleOwnArithmetic`), including PASIR RIS at −20.21.
- **The Pasir Ris inversion** (`townTable.pasirRisInversion`): the article's own row shows short-lease PSM **above** fresh-lease PSM; the table prints that as a −20.2% "Discount" and the Technical Findings print the same row as +20.2% "(inverted)" — exact sign flips of one quantity on the row's own values with the fresh PSM as denominator. The findings' four restatements are each the exact negative of the table's value (`signConventions.rows`, all four `findingsIsExactNegativeOfTable: true`) — the two surfaces disagree on convention, not magnitude.
- The measured window **does not reproduce the inversion**: Pasir Ris short-lease median PSM (5,433.07) sits **below** fresh-lease median PSM (5,967.74), a positive 8.96 discount (`measuredShortBelowFresh: true`). CLEMENTI's measured 40.99 is the closest of the six to the article's 40.6; TOA PAYOH, WOODLANDS, JURONG WEST and QUEENSTOWN measure far from their published rows. All differences are ledger fields (`measuredMinusArticleShort` / `measuredMinusArticleFresh`).

## 10. Every legacy claim, disposed (`legacyClaims`, 36 entries)

**36 claims, 36/36 verified verbatim** (`legacyQuoteCheck`): **25 re-measured, 5 withdrawn, 6 not-reproducible**, spanning the five-band table, the trade-off rows (−23.8%, 24.4%, +$54.75), the six town rows, the Technical Findings restatements, the appendix's ten method lines (two input paths, the bins, the months column, the price statistics, the discount formula, the decay approximation, the town comparison, the hedonic specification, the Mann-Whitney and Bala lines), the two takeaway sentences (highest volume; not cheapest per-area), the spline-arbitrage line, and the conclusion's coefficient sentence.

Every `ledgerKey` is resolved **at build time** (`claimKeyCheck`: 36 checked, 0 unresolved, and an unresolved key fails the build). The ledger states that resolution is **syntactic** — it checks the key exists, not that the resolved field supports the disposition.

## 11. What this pack does not establish

- **No model, no coefficient, no conversion.** Nothing is fitted; the +$54.75 coefficient is not restated in PSF, PSM, or any other unit; the response decision binds future fitting but no future fitting has happened.
- **No reproduction of the article's sample or its town rows.** The stated 223,634 equals no candidate window; five of six town discounts measure far from their published values (fields recorded), and the Pasir Ris inversion does not reproduce.
- **No proven lineage between any two stored artefacts.** The article ↔ CSV ↔ PNG correspondences (5/5 counts, 5/5 prices, 5/5 per-area at integer rounding) and the insights' two matching discounts are correspondences; every link statement in the ledger is symmetric — unlinked means neither for nor against.
- **No repair of the legacy's unit labels' history.** The per-area column is identified as per-square-metre by measurement; the pack does not adjudicate which historical label was "correct".
- **No claim about the market inside the asset's coverage gap** (ages 60–90 / remaining ≈ 4–39 years): the gap is an absence of rows in a stored asset, counted as such.
- **No edition text, no chart unlock, no model unlock.** All three gates remain exactly where the gate clause requires them to stay.

## 12. Review history

| Round | Verdict            | Record                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ----- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | **pending review** | This pack, as written. Ledger at `artifacts/rs06-lease-decay-evidence.json` sha256 `f022f8c3babc8f603f91ae04b5b6e9791780900c3b9e157e7a07cae6cf555d27`, 197,825 bytes; determinism verified (two runs byte-identical, `cmp` clean) and `--check` passing at these bytes. Awaiting the review chain: source/cutoff attestation, independent scientific review, publication signature — none given, none self-given.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 2     | **pending review** | Scan-stabilisation citation round (2026-11-22). This pack and the edition text stopped restating scan-scope counts — files scanned, files matched, occurrences per file — and now cite the ledger field that carries each (`absenceScans.fittedModel.filenameScan.matchCount`/`.matches`, `absenceScans.tokenScan.filesScanned`/`.scannedFiles`/`.scannedFilesManifestSha256`, `absenceScans.tokenScan.tokens.<token>.occurrences`/`.fileCount`). The earlier scan-stabilisation round was never logged here; it is recorded now, together with the producer change it exposed: `absenceScans.l1Frame.filenameMatchesUnderData` had been populated from the `lease` filename scan (five lease-decay artefacts under a label naming `housing_hdb_transaction`) and `absenceScans.l3Frame.filenameMatchesUnderData` was empty although two `housing_unified`-named panels exist under `data/`. Each field is now produced by a filename scan of `data/` for the token its label names (§5), and the superseded bytes are retained at `artifacts/superseded/rs06-lease-decay-evidence.pre-filename-field-fix.json`. Ledger at `artifacts/rs06-lease-decay-evidence.json` sha256 `f022f8c3babc8f603f91ae04b5b6e9791780900c3b9e157e7a07cae6cf555d27`, 197,825 bytes; `--check` green twice at these bytes. Awaiting the review chain; no verdict is claimed. |
