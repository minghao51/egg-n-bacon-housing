---
title: "Spatial hotspots: rental re-measurement"
category: market-analysis
description: A bounded re-measurement of historical rental hotspots and their evidential limits.
status: draft
date: 2026-11-20
personas: [investor, first-time-buyer, upgrader]
technicalLevel: intermediate
---

# Spatial hotspots: rental re-measurement

Edition id: RS12 `spatial-hotspots` · Measured date: 2026-11-20 · Observation cutoff: 2026-09 (`cutoff.lastCompleteMonth`).

This text replaces the frozen source `docs/analytics/editions/legacy/2026-11-12/spatial-hotspots.md` (SHA-256 `c13717fde829aaf8d1193d4f5bb66f1c61e8d397e30bd2e7ee134963828d596c`; recorded at `legacyQuoteCheck.legacyFileSha256` and `inputs.docs/analytics/editions/legacy/2026-11-12/spatial-hotspots.md`). This is a re-measurement of the stated rental hotspot method accompanied by a withdrawal-led audit of claims that are unsupported or not reproducible from the measured population; it is not a finding about the origin of historical values.

## Gate disposition

The gate is: “Retain January 2024-January 2025 as its own historical window. Rerun the stated hotspot method, disclose persistence/instability and sample changes. Keep rental hotspot results separate from the transaction-activity product.” Its clauses are handled separately below.

| Gate clause | Disposition | Evidence fields |
|---|---|---|
| Retain January 2024-January 2025 as its own historical window. | Kept as an independent historical period from 2024-01 through 2025-01. It contains 39,478 rental-file rows; 39,385 join and 93 do not. The unmatched population is reported rather than silently discarded. The period ends before the measured cutoff. | `gateWindow.first`, `gateWindow.last`, `gateWindow.monthCount`, `gateWindow.rowsInFile`, `joinMeasure.window.matchedRows`, `joinMeasure.window.unmatchedRows`, `gateWindow.endsBeforeCutoff` |
| Rerun the stated hotspot method, disclose persistence/instability and sample changes. | Re-measured on joined rows using H3 resolution 8, cell-level median monthly rent, Getis-Ord Gi* and seeded permutation inference with KNN weights. The claim’s threshold variable is underspecified: both analytic and simulation z outputs are retained and neither is selected as the historical interpretation. Persistence is not measurable from a single pinned period. Joinable and unmatched populations describe sample change; a separate H3-neighbour sensitivity records instability to the available spatial-weight analogue. | `hotspotStatistic.method`, `hotspotStatistic.analyticZ`, `hotspotStatistic.simulationZ`, `hotspotStatistic.cellCounts`, `hotspotStatistic.hexAdjacencySensitivity`, `notMeasurable.persistence`, `joinMeasure.window`, `joinMeasure.unmatchedPopulation` |
| Keep rental hotspot results separate from the transaction-activity product. | The rental output is a separate rental-only asset. The transaction-activity file is read-only and receives no rental payload or write. A file not linked to the described run adjudicates neither for nor against a historical result; the transaction product’s labels are not a link to the historical run. | `rentalAsset.path`, `shippedAssetSeparation.spatialAnalysis`, `shippedAssetSeparation.separationStatement` |

## What these numbers are and are not
The terminal month is 2026-10 and has 2,819 transactions against a 3,135.5 trailing-12-month median; the last complete month is 2026-09 under the recorded share test (`cutoff.terminalMonth`, `cutoff.terminalMonthTransactions`, `cutoff.trailing12MedianTransactions`, `cutoff.terminalMonthShareOfTrailingMedian`, `cutoff.lastCompleteMonth`). All rental outcome aggregations, including the rent distribution, stop there (`cutoff.meaning`, `populations.rentalPopulation.rentRangeObserved.meaning`). The parquet schemas were read from metadata before describing columns (`sourceSchema.rental`, `sourceSchema.geocode`). The rental schema has no coordinates; the geocode schema has no `search_result` column (`sourceSchema.rental.columns`, `sourceSchema.geocode.columns`).


This edition re-runs the declared method against frozen inputs. Counts refer only to the named population—file, window, key, join, unmatched row, cell, or town—and file rows are not the denominator for every statistic. Results characterize joinable rental records, not all rental activity.





The join uses uppercased `(block, street_name)` keys and one geocode row per key (`joinMeasure.keyDefinition`). Through `cutoff.lastCompleteMonth`, the recorded null count for each rental column is zero; the count of recorded zero rents is zero, and the count of nonnumeric rent strings is zero (`populations.rentalPopulation.missingnessStates.throughMonth`, `.nullValuesPerColumn`, `.recordedZeroRents`, `.nonNumericRentStrings`). In the geocode population, 11,805 rows have both coordinates null, zero rows have exactly one coordinate null, and 137 distinct keys have null coordinates on every row; 11,500 distinct keys are joinable from 11,637 distinct keys overall. The joinable-key count and full geocode row count are different populations and are not combined. Within the historical window, 93 unmatched rows remain an explicit population and are excluded from the spatial statistic because they lack coordinates in this checkout (`populations.geocodePopulation`, `joinMeasure.window`, `joinMeasure.unmatchedPopulation`).



## Measured method and results

The population is the rental rows in the gate window that obtain coordinates through the join, not the sale transactions themselves. Coordinates are assigned by matched block and street. The cell statistic is the median of `monthly_rent` in each H3 cell; it is not adjusted for flat-type mix (`hotspotStatistic.method.cellValue`). The recorded method uses H3 resolution 8, `esda.getisord.G_Local(star=True)`, 99 permutations, seed 99, one worker, and KNN k=8 on cell centroids with row-standardised weights. The recorded software versions are esda 2.8.1, h3 4.1.0b2, libpysal 4.14.1, numpy 2.4.1 and pandas 2.3.3 (`hotspotStatistic.method.h3Resolution`, `.statistic`, `.permutations`, `.seed`, `.nJobs`, `.primaryWeights`, `.libraryVersions`). The self-weight convention is also recorded: with an empty diagonal, esda infers the Gi* self-weight as each row’s maximum weight (`hotspotStatistic.method.starInference`).

The gate window holds 39,478 rows, of which 39,385 join, with a measured match share of 0.997644; 93 are unmatched (`gateWindow.rowsInFile`, `joinMeasure.window.matchedRows`, `joinMeasure.window.matchShare`, `joinMeasure.window.unmatchedRows`). The window’s joined-rent median is 3,100, with observed joined rent percentiles 1,400 and 4,800 at the 1st and 99th percentile (`joinMeasure.window.joinedRentMedian`, `.joinedRentP01`, `.joinedRentP99`). There are 26 joined towns (`joinMeasure.window.joinedDistinctTowns`).

There are 269 cells in the historical joined population. Three cells contain one row; the measured candidate floors are 266 cells with at least two rows, 266 with at least three, 263 with at least five, and 253 with at least ten. The legacy text does not define “sufficient data”, so none of those floors is adopted as its intended threshold (`hotspotStatistic.cellCounts.totalCells`, `.cellsOneRow`, `.cellsAtLeast2Rows`, `.cellsAtLeast3Rows`, `.cellsAtLeast5Rows`, `.cellsAtLeast10Rows`, `notMeasurable.sufficientDataFloor`). The legacy cell total of 847 is not produced by this measured population; its population and floor are undefined and there is no linked artifact to adjudicate its origin (`notMeasurable.legacyTotalCells847`).

The threshold basis is another material ambiguity. The legacy calls its threshold variable “z” without naming whether it is analytic Z or simulation z_sim. Under the stated thresholds (hotspot 2.58, weak hotspot 1.96, coldspot -2.58, weak coldspot -1.96), the analytic series has zero cells on either side at both levels, with maximum 1.6536 and minimum -0.9179. The simulation series has 12 above the upper 2.58 threshold, 30 above 1.96, one below -2.58, and 15 below -1.96, with maximum 5.0023 and minimum -2.7754. Both bases have zero non-finite values (`hotspotStatistic.method.thresholds`, `hotspotStatistic.analyticZ`, `hotspotStatistic.simulationZ`). These alternatives are both evidence about this rerun; neither is represented as the historical reading.

With 99 permutations the recorded p_sim floor is 0.01: 9 cells reach that floor in the hot direction, 5 in the cold direction, and 14 in total (`hotspotStatistic.pSimFloor.floor`, `.cellsAtFloorHotDirection`, `.cellsAtFloorColdDirection`, `.cellsAtFloorTotal`). The ledger records the esda two-tail and plus-one convention, and the attainable floor; a p_sim floor count is not interchangeable with a selected z-score interpretation (`hotspotStatistic.pSimFloor.semantics`).

The simulation-z cells passing the upper 99% threshold are reported individually below. Values in each row are measurements of the indicated cell, with the corresponding ledger-array field stated in the table headings; this is a candidate reading under simulation z, not an attribution to the legacy figures. The single lower-threshold cell is included in the same table.

| Cell identifier (`hotspotStatistic.extremes.simulationHot99Cells[].cell` or `simulationCold99Cells[].cell`) | Town (`...town`) | Joined rows (`...rows`) | Median monthly rent (`...medianMonthlyRent`) | Analytic Z (`...analyticZ`) | Simulation z (`...simulationZ`) | p_sim (`...pSim`) | Direction |
|---|---|---:|---:|---:|---:|---:|---|
| 886520d80dfffff | BUKIT MERAH | 319 | 2900 | 0.9769 | 3.1554 | 0.01 | Hot |
| 886520d829fffff | BUKIT MERAH | 179 | 3200 | 1.6536 | 5.0023 | 0.01 | Hot |
| 886520d82bfffff | BUKIT MERAH | 175 | 4000 | 1.2555 | 3.1131 | 0.01 | Hot |
| 886520d839fffff | BUKIT MERAH | 5 | 2600 | 1.0565 | 3.8641 | 0.01 | Hot |
| 886520d83dfffff | QUEENSTOWN | 351 | 3250 | 0.9371 | 2.8533 | 0.01 | Hot |
| 886520d847fffff | BUKIT MERAH | 46 | 3000 | 0.9769 | 3.214 | 0.01 | Hot |
| 886520d863fffff | BUKIT MERAH | 485 | 3800 | 1.3909 | 3.5511 | 0.01 | Hot |
| 886520d865fffff | CENTRAL | 57 | 2700 | 1.1361 | 3.8272 | 0.01 | Hot |
| 886520d867fffff | BUKIT MERAH | 198 | 3300 | 1.0724 | 3.1044 | 0.03 | Hot |
| 886520d86bfffff | BUKIT MERAH | 78 | 3000 | 1.0724 | 3.3924 | 0.02 | Hot |
| 886520d86dfffff | CENTRAL | 79 | 3200 | 1.1361 | 3.3989 | 0.02 | Hot |
| 886520d991fffff | CLEMENTI | 25 | 3200 | 0.8495 | 2.7925 | 0.02 | Hot |
| 886526349bfffff | WOODLANDS | 45 | 3200 | -0.902 | -2.7754 | 0.01 | Cold |



For context on the full cell statistic rather than a chosen tail, the top ten entries by analytic Z are retained at `hotspotStatistic.extremes.topCellsByAnalyticZ`, with the same ten entries also recorded at `hotspotStatistic.extremes.bottomCellsByAnalyticZ`. Each of those ten has a simulation-z value above the stated 2.58 threshold while the analytic series crosses no threshold on either side (`hotspotStatistic.method.thresholds`, `hotspotStatistic.analyticZ`, `hotspotStatistic.extremes.topCellsByAnalyticZ`), so the two outputs classify these cells differently. The ledger table `hotspotStatistic.cellsTable` contains the entire cell-level result, including identifier, town, row count, median rent, both z outputs and p_sim. A sample of that complete table is not substituted for the recorded full result.

### Town-level rental summaries

Town is the only area column in the rental input. The legacy’s named neighbourhoods are not given reproducible geographic boundaries, so town medians below are measured town-level summaries and candidates for comparison, not replacements for neighbourhood-specific amounts (`townMedians.basis`). Every town listed has its window joined-row count and median monthly rent.

| Town | Window rows (`townMedians.windowByTown.<town>.rows`) | Median monthly rent (`townMedians.windowByTown.<town>.median`) |
|---|---:|---:|
| ANG MO KIO | 2168 | 2900 |
| BEDOK | 2319 | 2900 |
| BISHAN | 842 | 3500 |
| BUKIT BATOK | 1589 | 2900 |
| BUKIT MERAH | 2221 | 3400 |
| BUKIT PANJANG | 947 | 3000 |
| BUKIT TIMAH | 102 | 3400 |
| CENTRAL | 586 | 3400 |
| CHOA CHU KANG | 1373 | 3100 |
| CLEMENTI | 1459 | 3200 |
| GEYLANG | 1122 | 3000 |
| HOUGANG | 1845 | 3000 |
| JURONG EAST | 1042 | 3200 |
| JURONG WEST | 2752 | 3300 |
| KALLANG/WHAMPOA | 1510 | 3200 |
| MARINE PARADE | 439 | 3000 |
| PASIR RIS | 991 | 3400 |
| PUNGGOL | 1848 | 3200 |
| QUEENSTOWN | 1710 | 3200 |
| SEMBAWANG | 944 | 3125 |
| SENGKANG | 2595 | 3200 |
| SERANGOON | 875 | 3200 |
| TAMPINES | 2539 | 3250 |
| TOA PAYOH | 1570 | 3000 |
| WOODLANDS | 1957 | 3000 |
| YISHUN | 2040 | 2900 |



### Weight sensitivity and instability

The primary weights are KNN k=8, row-standardised. The legacy also refers to Queen contiguity but does not specify how that construction was realised for spatial cells. The measured alternative is H3 k-ring-1 adjacency, a choice of this pack rather than recovery of the historical weighting. Under binary adjacency, the sensitivity has three cells above the 95% threshold, none above the 99% threshold, one below the 95% cold threshold and one below the 99% cold threshold; the measured maximum is 2.4099 and minimum -2.6057. Four islands are recorded. Under row-standardised hex weights, the analytic variance collapses toward zero, with four zero-variance island cells, four non-finite Z values, and a recorded maximum variance of 1.68567e-07. That branch is marked degenerate and unusable for analytic Z (`hotspotStatistic.hexAdjacencySensitivity.binary`, `.islands`, `.rowStandardised`). This is method sensitivity evidence for the present rerun, not evidence about the legacy’s own implementation.

Persistence cannot be estimated from a single historical period. A transition requires multiple observed periods; this edition has the gate-pinned period only, and the bounded search screened the transition implementation as absent and found no stored transition-probability table. Thus the stated persistence and transition rates are not measurable here (`notMeasurable.persistence`, `hotspotStatistic.persistenceDisclosure`, `methodRecovery.transitionProbabilities`). This boundary does not imply that the legacy rates were either valid or invalid; the origin of those values is unverified.

## Superseded figures

The table below preserves every claim entered in the ledger’s frozen-text inventory. Phrases are copied verbatim; status definitions are at `statusMeaning`. “Re-measured” means the cited quantity or method has a measured counterpart, not that every legacy interpretation is validated. “Withdrawn” means the legacy assertion is not carried forward as a result. “Not-reproducible” means the claim lacks a uniquely specified population, threshold basis, time transition, or other required definition. Each ledger key is the recorded machine-checked address; key resolution is syntactic and does not establish evidential support (`claimKeyCheck.resolutionIsSyntactic`).

| ID | Frozen phrase (verbatim) | Status | Measured reason / limit | Ledger key |
|---|---|---|---|---|
| C01 | `` - **Rental data**: `data/parquets/L1/housing_hdb_rental.parquet` `` | withdrawn | the cited path does not exist in this checkout (data/parquets/L1 is empty); the measured stand-in is the bronze rental file at inputs.data/pipeline/01_bronze/raw_hdb_rental.parquet (215,469 rows, sha-pinned) | `inputs.data/pipeline/01_bronze/raw_hdb_rental.parquet` |
| C02 | `` - **Geocoding data**: `data/parquets/L2/housing_unique_searched.parquet` (lat/lon) `` | withdrawn | the cited path does not exist; the measured stand-in is the sale-side geocode table at inputs.data/pipeline/02_silver/geocoded_validated.parquet (1,236,515 rows, lat/lon columns confirmed in sourceSchema) | `inputs.data/pipeline/02_silver/geocoded_validated.parquet` |
| C03 | `` - **Join key**: `block_street_name`, filtered to successfully geocoded records (`search_result == 0`) `` | not-reproducible | the stated filter cannot be recomputed: the present geocode table has no search_result column (an absent column, not a null). Its measured replacement — the join on uppercased (block, street_name) keys carrying non-null lat/lon — is at joinMeasure.window (39,385 of 39,478 rows, 99.7644%), and the unmatched rows are reported as a population | `populations.geocodePopulation` |
| C04 | `**Data Period**: 2024-01 to 2025-01` | re-measured | the window is present and populated: 39,478 rental rows in-file, 39,385 joined (gateWindow, joinMeasure.window); the gate pins it as its own historical window and it ends before the measured cutoff | `gateWindow` |
| C05 | `- **Date range**: 2024-01 to 2025-01` | re-measured | same measurement as C04, stated twice in the legacy text | `gateWindow` |
| C06 | `` - **Getis-Ord Gi\*** local statistic via `esda.getisord.G_Local` `` | re-measured | implemented as stated: esda.getisord.G_Local(star=True) on the joined window population; library versions pinned at hotspotStatistic.method.libraryVersions. That the legacy's own run used this call is origin-unverified — no artefact links to it | `hotspotStatistic.method` |
| C07 | `- **Spatial weights**: KNN (k=8) and Queen contiguity` | re-measured | KNN k=8 row-standardised is implemented as the primary weights; the legacy does not state how 'Queen contiguity' is realised for point/cell data, so a hex-adjacency (H3 k-ring-1) sensitivity is recorded as THIS PACK's choice at hotspotStatistic.hexAdjacencySensitivity (row-standardised variant degenerate; binary variant reported) | `hotspotStatistic.method` |
| C08 | `` - **Spatial aggregation**: H3 resolution 8, median `monthly_rent` per cell `` | re-measured | implemented as stated: 269 H3 resolution-8 cells from 39,385 joined rows; cell medians are unadjusted for flat-type mix because the legacy states no adjustment | `hotspotStatistic.cellCounts` |
| C09 | `- **Coverage**: 847 total cells, 623 with sufficient data for analysis` | re-measured | disagrees: the measured window population has 269 cells (hotspotStatistic.cellCounts.totalCells) — no measured reading approaches 847; the 'sufficient data' floor is unstated in the legacy and is recorded as underspecified, so the 623 figure has no measurable reading (floors at n>=2/3/5/10 are candidates at hotspotStatistic.cellCounts) | `hotspotStatistic.cellCounts` |
| C10 | `  - Hotspot: z > 2.58 (99% confidence)` | re-measured | threshold implemented; measured counts recorded per basis — analytic z: 0 cells (hotspotStatistic.analyticZ), simulation z: 12 (hotspotStatistic.simulationZ), p_sim floor: 9 hot-direction (hotspotStatistic.pSimFloor). The legacy does not state which z its threshold applies to | `hotspotStatistic.analyticZ` |
| C11 | `  - Weak hotspot: z > 1.96 (95% confidence)` | re-measured | same threshold scheme; analytic 0 cells, simulation 30 cells (hotspotStatistic.simulationZ.cellsAbove95) | `hotspotStatistic.simulationZ` |
| C12 | `  - Coldspot: z < -2.58 (99% confidence)` | re-measured | analytic 0 cells (hotspotStatistic.analyticZ.cellsBelowCold99), simulation 1 cell (hotspotStatistic.simulationZ.cellsBelowCold99), p_sim floor 5 cold-direction (hotspotStatistic.pSimFloor) | `hotspotStatistic.analyticZ` |
| C13 | `  - Weak coldspot: z < -1.96 (95% confidence)` | re-measured | analytic 0 cells, simulation 15 cells (hotspotStatistic.simulationZ.cellsBelowCold95) | `hotspotStatistic.simulationZ` |
| C14 | `- **Permutations**: 99 for significance testing` | re-measured | implemented with 99 permutations, seed 99, n_jobs=1, pinned at hotspotStatistic.method | `hotspotStatistic.method` |
| C15 | `\| Orchard      \| 4.21           \| $3,200              \| Strong hotspot  \|` | withdrawn | the area has zero rows in the population (no town value, no street-name substring — legacyAreaChecks.orchard), so neither the $3,200 median nor the 4.21 Gi* value can refer to this population; no artefact carries either number (methodRecovery.tokens) | `legacyAreaChecks.orchard` |
| C16 | `\| Marina South \| 3.89           \| $3,450              \| Strong hotspot  \|` | withdrawn | same shape as C15: zero rows for the area, no artefact for either number | `legacyAreaChecks.marinaSouth` |
| C17 | `\| Bukit Timah  \| 3.45           \| $3,100              \| Strong hotspot  \|` | re-measured | the town exists (102 window rows); the measured window median is 3,400 against the claimed $3,100 (townMedians.windowByTown, legacyAreaChecks.bukitTimah), and the claimed Gi* value has no artefact and no area definition that would reproduce it | `legacyAreaChecks.bukitTimah` |
| C18 | `\| Woodlands    \| -3.21          \| $2,100              \| Strong coldspot \|` | re-measured | the town exists (1,957 window rows); the measured window median is 3,000 against the claimed $2,100; the analytic z minimum over all cells is -0.9179 (hotspotStatistic.analyticZ.minZ) and no artefact carries -3.21 | `legacyAreaChecks.woodlands` |
| C19 | `\| Yishun       \| -2.98          \| $2,050              \| Strong coldspot \|` | re-measured | the town exists (2,040 window rows); measured window median 2,900 against the claimed $2,050; claimed Gi* value has no artefact | `legacyAreaChecks.yishun` |
| C20 | `\| Sembawang    \| -2.67          \| $2,000              \| Strong coldspot \|` | re-measured | the town exists (944 window rows); measured window median 3,125 against the claimed $2,000; claimed Gi* value has no artefact | `legacyAreaChecks.sembawang` |
| C21 | `Only **12 H3 cells** qualified as 99% confidence hotspots` | not-reproducible | the legacy's threshold basis (which z output) is unstated, so the claim has no single measurable reading; measured candidate counts are 0 under the analytic z, 12 under the simulation z (coincidence of the seed and implementation, recorded as such at hotspotStatistic.simulationZ.cellsAbove99), and 9 hot-direction cells at the p_sim floor. None is promoted to the legacy reading | `hotspotStatistic.thresholdBasisNote` |
| C22 | `- **12 H3 cells** qualified as 99% confidence hotspots` | not-reproducible | same measurement as C21, restated in the legacy's Technical Findings | `hotspotStatistic.thresholdBasisNote` |
| C23 | `- **Top hotspots**: Orchard Gi* = 4.21, Marina South Gi* = 3.89, Bukit Timah Gi\* = 3.45` | withdrawn | two of the three areas have zero rows in the population (legacyAreaChecks.orchard, legacyAreaChecks.marinaSouth); no artefact carries any of the three values; the measured analytic z maximum over all 269 cells is 1.6536, below every claimed hotspot value | `hotspotStatistic.analyticZ` |
| C24 | `- **Top coldspots**: Woodlands Gi* = -3.21, Yishun Gi* = -2.98, Sembawang Gi\* = -2.67` | withdrawn | no artefact carries any of the three values; the measured analytic z minimum is -0.9179 and the simulation-z reading yields exactly 1 cell below -2.58 (hotspotStatistic.simulationZ), so no claimed coldspot value is reachable on this population | `hotspotStatistic.analyticZ` |
| C25 | `\| Hotspot median rent  \| $3,200                       \|` | not-reproducible | the legacy's hotspot population is undefined (threshold basis unstated), so the level cannot be recomputed as stated; the candidate value under the simulation-z reading is a median-of-medians of 3,200 across 12 cells (hotspotStatistic.extremes.candidateRentLevels.hotMedianOfMedians) — recorded as a candidate, not a confirmation, and coincidentally equal to the Orchard row's level | `hotspotStatistic.extremes.candidateRentLevels` |
| C26 | `\| Coldspot median rent \| about 1,850 to 2,100 dollars \|` | not-reproducible | same undefined population; the simulation-z reading yields exactly 1 cold cell whose median (3,200) lies OUTSIDE the claimed band, and the town-level candidate medians for the legacy's own coldspot towns are 2,900-3,125 (townMedians.windowByTown) — also outside the band | `hotspotStatistic.extremes.candidateRentLevels` |
| C27 | `\| Typical gap          \| about $1,350 per month       \|` | not-reproducible | the gap inherits the undefined populations; the candidate gap under the simulation-z reading is 3,200 - 3,200 = 0.0 (exact arithmetic on candidateRentLevels.hotMedianOfMedians and candidateRentLevels.coldMedianOfMedians), and under the analytic reading no gap exists because no cell passes any threshold | `hotspotStatistic.extremes.candidateRentLevels` |
| C28 | `\| Hotspot remains hotspot    \| 58-62%      \|` | not-reproducible | a transition needs at least two periods; the gate pins ONE window (2024-01..2025-01), the scan found no transition implementation (methodRecovery.transitionProbabilities) and no stored probability table, so no persistence estimate is measurable in this checkout | `hotspotStatistic.persistenceDisclosure` |
| C29 | `\| Coldspot remains coldspot  \| 55-60%      \|` | not-reproducible | same as C28 | `hotspotStatistic.persistenceDisclosure` |
| C30 | `\| Non-significant to hotspot \| 8-10%       \|` | not-reproducible | same as C28 | `hotspotStatistic.persistenceDisclosure` |
| C31 | `- **Rent gap**: hotspot median $3,200 vs coldspot median ~$1,850-$2,100 ≈ $1,350/month` | not-reproducible | restates C25-C27 in one line; same undefined populations and same candidates | `hotspotStatistic.extremes.candidateRentLevels` |
| C32 | `- **Persistence rates**: hotspot remains hotspot 58-62%, coldspot remains coldspot 55-60%` | not-reproducible | restates C28-C29; same single-period limit | `hotspotStatistic.persistenceDisclosure` |
| C33 | `- **Transition rate**: non-significant → hotspot only 8-10%, confirming true hotspots are limited` | not-reproducible | same as C28, and the word 'confirming' is the legacy's own: a screened-as-absent transition statistic can neither confirm nor refute the narrative — origin unverified in both directions | `hotspotStatistic.persistenceDisclosure` |
| C34 | `Persistence is moderate (58-62%), meaning hotspot status is sticky but not permanent` | not-reproducible | interpretation built on C28's unmeasurable quantity | `hotspotStatistic.persistenceDisclosure` |
| C35 | `The ~$1,350/month rent gap between hotspots and coldspots is economically significant.` | not-reproducible | significance judgement on C27's unmeasurable quantity; the candidate measured gap under the simulation-z reading is 0.0 | `hotspotStatistic.extremes.candidateRentLevels` |
| C36 | "The low non-significant→hotspot transition rate (8-10%) confirms that emerging hotspot narratives require strong fundamental evidence." | not-reproducible | same unmeasurable quantity as C30; 'confirms' is the legacy's word and cannot be inherited by this pack | `hotspotStatistic.persistenceDisclosure` |
| C37 | `Rental premiums cluster geographically rather than appearing randomly` | withdrawn | interpretive summary, not a measurement; the measured counts are recorded per basis (analytic 0 cells above any threshold, simulation 12) and neither adjudicates 'random' without the legacy's unstated threshold basis | `hotspotStatistic.analyticZ` |
| C38 | `- For rental investors, location selection can dominate small property-level differences.` | withdrawn | investment advice; carries no measured value in this pack (the exemplar's rule: advice is recorded, not re-measured) | `notMeasurable.advice` |
| C39 | `Coldspots can still be attractive when commute, amenities, and own-stay needs line up.` | withdrawn | purchase advice; no measured value | `notMeasurable.advice` |
| C40 | `` the canonical assets for this page now live under `app/public/data/analysis/` `` | withdrawn | the cited directory app/public/data/analysis/ does not exist; the shipped analytics assets live under app/public/data/analytics/ (three transaction-side files, sha-pinned at shippedAssetSeparation), plus this study's new rental-only asset at rentalAsset.path | `shippedAssetSeparation.spatialAnalysis` |



## Bounded absence findings

The scan was a case-insensitive substring count, with every matched path and per-file occurrence count retained in `methodRecovery.tokens`; a text match is not an origin finding. Roots were `docs`, `scripts`, `src`, `assets`, `app/src`, `app/public`, `data/analysis`, `notebooks`, `tests`, and `.claude`; suffixes were `.md`, `.py`, `.ts`, `.tsx`, `.json`, `.csv`, `.txt`, and `.ipynb`. The number of files the scan covered is `methodRecovery.scan.filesScanned`, as recorded in the ledger. Exclusions were `scripts/tools/`, `prompts/`, `docs/implementation/`, and `docs/analytics/editions/` except `docs/analytics/editions/legacy/`; the latter remained in the scan. Also excluded was `docs/plans/2026-11-12-reporting-refresh-decisions.md` (`methodRecovery.scan.roots`, `.suffixes`, `.filesScanned`, `.excludedPrefixes`, `.excludedPaths`, `.retainedEditionPrefix`, `.retainedEditionNote`).

For each searched token, the ledger's `methodRecovery.tokens.<token>` record carries every matched path with its per-file occurrence count (`matchedFiles`), the matched-file count (`files`) and the total occurrences (`occurrences`); this prose cites that record instead of restating its counts. A count describes string matches only. In particular, a matching path does not identify an implementation, table, or historical run.

| Token | Ledger record |
|---|---|
| `1,350` | `methodRecovery.tokens.1,350` |
| `1,850` | `methodRecovery.tokens.1,850` |
| `1.96` | `methodRecovery.tokens.1.96` |
| `12 h3` | `methodRecovery.tokens.12 h3` |
| `2,000` | `methodRecovery.tokens.2,000` |
| `2,050` | `methodRecovery.tokens.2,050` |
| `2,100` | `methodRecovery.tokens.2,100` |
| `2.58` | `methodRecovery.tokens.2.58` |
| `2.67` | `methodRecovery.tokens.2.67` |
| `2.98` | `methodRecovery.tokens.2.98` |
| `3,100` | `methodRecovery.tokens.3,100` |
| `3,200` | `methodRecovery.tokens.3,200` |
| `3,450` | `methodRecovery.tokens.3,450` |
| `3.21` | `methodRecovery.tokens.3.21` |
| `3.45` | `methodRecovery.tokens.3.45` |
| `3.89` | `methodRecovery.tokens.3.89` |
| `4.21` | `methodRecovery.tokens.4.21` |
| `55-60` | `methodRecovery.tokens.55-60` |
| `58-62` | `methodRecovery.tokens.58-62` |
| `623` | `methodRecovery.tokens.623` |
| `8-10` | `methodRecovery.tokens.8-10` |
| `847` | `methodRecovery.tokens.847` |
| `esda` | `methodRecovery.tokens.esda` |
| `g_local` | `methodRecovery.tokens.g_local` |
| `getis` | `methodRecovery.tokens.getis` |
| `h3 resolution` | `methodRecovery.tokens.h3 resolution` |
| `hotspot` | `methodRecovery.tokens.hotspot` |
| `knn` | `methodRecovery.tokens.knn` |
| `libpysal` | `methodRecovery.tokens.libpysal` |
| `persistence of hotspot` | `methodRecovery.tokens.persistence of hotspot` |
| `queen` | `methodRecovery.tokens.queen` |
| `transition matrix` | `methodRecovery.tokens.transition matrix` (no match recorded) |
| `transition probabilit` | `methodRecovery.tokens.transition probabilit` |

Within these declared roots, suffixes, and exclusions, the producer screened Gi* implementation as absent: the relevant code-token hits, with every matched path and its per-file count, are recorded in `methodRecovery.tokens`, and identified hits may be coincidental strings, labels or prose. This does not establish where the legacy values came from. H3 cell tables were screened as absent within the same boundary; each token's matched paths are at `methodRecovery.tokens.<token>.matchedFiles`, and this is not a complete inventory outside the scan. Transition probability artefacts were likewise screened as absent within the declared boundary; the transition-probability token matches the frozen legacy text, while the transition-matrix token has no matches. No transition probability is measured. These statements are bounded to `methodRecovery.scan`; they do not assert repository-wide absence. (`methodRecovery.giStarImplementation`, `.h3CellTables`, `.transitionProbabilities`, `.tokens`)

An unlinked artefact adjudicates nothing in either direction: its lack of a link is evidence neither for nor against a historical result. No plot, panel, or file is attributed to the historical run without such a link. Historical-value origin remains unverified (`methodRecovery.giStarImplementation.conclusion`, `notMeasurable.persistence.meaning`).

## What this edition does not establish

- It does not establish the origin of any legacy number. No artifact is linked to those values in either direction; unmatched or unrelated files do not resolve that gap (`methodRecovery.giStarImplementation.conclusion`, `legacyClaims`).

- It does not measure persistence or transition probabilities. The edition has one gate-pinned period, and the bounded scan found no transition implementation or stored probability table. The conclusion is limited to the declared scan roots, suffixes and exclusions (`notMeasurable.persistence`, `methodRecovery.scan`, `methodRecovery.transitionProbabilities`).

- It does not determine which esda z output the legacy thresholds meant, nor what “sufficient data” meant. Both current z bases and candidate cell floors are reported without selecting a historical meaning (`notMeasurable.legacyThresholdBasis`, `.sufficientDataFloor`, `hotspotStatistic.analyticZ`, `.simulationZ`, `.cellCounts`).

- It does not reproduce the undocumented geographic boundaries of named legacy areas. Rental town values permit town-level summaries only; empty areas remain empty, and the boundaries of other named areas remain unspecified (`townMedians.basis`, `legacyAreaChecks`).

- It does not generalise the joined sample to unmatched records or to rental transactions outside the observed file. The unmatched population is explicitly counted, but cannot enter the spatial statistic without coordinates (`joinMeasure.unmatchedPopulation.disclosure`, `populations.rentalPopulation.monthRange`).

- It does not validate a counterfactual, causal effect, investor strategy, or purchase decision. Rental hotspots describe this cell statistic and this input population only (`scope`, `definition`).

- It does not combine rental hotspot output with the transaction-activity product. The products have different populations, purposes and destination files (`shippedAssetSeparation.separationStatement`, `.spatialAnalysis.role`, `rentalAsset.path`).

- It does not inventory files outside the bounded scan or excluded programme surfaces. Absence statements above remain confined to the measured search boundary (`methodRecovery.scan`).

## Reading by persona

**Investor.** These results describe rents among joined rental observations; they do not forecast returns or recommend a location. Weight sensitivity and town/cell geography constrain comparisons (`hotspotStatistic.method`, `.hexAdjacencySensitivity`, `townMedians.basis`, `legacyAreaChecks`). Cell rent is not adjusted for flat-type mix (`hotspotStatistic.method.cellValue`).

**First-time buyer.** This rental study does not measure purchase prices or affordability. Its output is separate from transaction activity, and its historical period is not a statement of current availability (`shippedAssetSeparation.spatialAnalysis.role`, `rentalAsset.path`, `gateWindow`, `cutoff.lastCompleteMonth`).

**Upgrader.** Town medians are descriptive, not estimates of a causal premium or within-town variation. The cell median is unadjusted for flat-type mix, and unmatched records constrain local interpretation (`townMedians.basis`, `hotspotStatistic.method.cellValue`, `joinMeasure.window.unmatchedRows`). The product does not measure changes in sale activity (`shippedAssetSeparation.spatialAnalysis.role`).

## Inputs

The following source inputs are pinned by SHA-256. Parquet rows and bytes describe the source file; compressed analytics inputs have byte counts and no row count recorded in the input inventory. The frozen legacy input is identified by the recorded path, SHA-256, and byte count (`legacyQuoteCheck.legacyFile`, `inputs.docs/analytics/editions/legacy/2026-11-12/spatial-hotspots.md`).

| Input | SHA-256 | Rows | Bytes | Ledger fields |
|---|---|---:|---:|---|
| `app/public/data/analytics/feature_impact.json.gz` | `69b5e85dc451b2be5d7efa472e66ac213288206095e1e9cd8d6984fb413eb579` | — | 958 | `inputs.app/public/data/analytics/feature_impact.json.gz` |
| `app/public/data/analytics/predictive_analytics.json.gz` | `14a8ae6f0ce503e10068a491940cc78e2ad0ae77afa3dbe67b2096a73f3e3c06` | — | 1804 | `inputs.app/public/data/analytics/predictive_analytics.json.gz` |
| `app/public/data/analytics/spatial_analysis.json.gz` | `e3ff620242187ba93f09986f313b3261c63df2cc6b333cce460c63fe227c2d54` | — | 1156 | `inputs.app/public/data/analytics/spatial_analysis.json.gz` |
| `data/pipeline/01_bronze/raw_hdb_rental.parquet` | `960691dbdcbcd1f0df18b7ad719f19994e3b43baad788c5a3410b32c9527d13d` | 215469 | 2127570 | `inputs.data/pipeline/01_bronze/raw_hdb_rental.parquet` |
| `data/pipeline/02_silver/geocoded_validated.parquet` | `bac69a0494d384551ca39e3cbb55525f41a7683a73ac3cef2fee16e3f35b828f` | 1236515 | 19071873 | `inputs.data/pipeline/02_silver/geocoded_validated.parquet` |
| `docs/analytics/editions/legacy/2026-11-12/spatial-hotspots.md` | `c13717fde829aaf8d1193d4f5bb66f1c61e8d397e30bd2e7ee134963828d596c` | — | 6072 | `inputs.docs/analytics/editions/legacy/2026-11-12/spatial-hotspots.md` |

The sale-side geocode table is used only as a source of matching coordinates; it is not the measured rental outcome. The transaction activity asset is read-only and its pinned hash/bytes are shown above (`inputs.app/public/data/analytics/spatial_analysis.json.gz`, `shippedAssetSeparation.spatialAnalysis`). The new rental result is separately written to `app/public/data/analytics/rental_hotspots_2024-01_2025-01.json.gz`; its hash and byte count are `rentalAsset.sha256` and `rentalAsset.bytes`, and it is not part of the source-input inventory.

## Provenance

Prepared by `repo-agent/session-2026-11-20`. The evidence pack is `docs/implementation/2026-11-20-rs12-spatial-hotspots-evidence.md`. Its machine-readable ledger is `docs/implementation/artifacts/rs12-spatial-hotspots-evidence.json`, SHA-256 `6c4027340264cdc079dd19a2a5040b4c34e4f4059d53236f313c1ac56b86beab`, 202,191 bytes (measured from this checkout). The pack describes the bounded method, measured inputs, quote and claim-key checks, and rental/transaction output separation. The deterministic producer reports a byte-identical re-measurement under `--check` (`rentalAsset.determinism`). This text is a draft awaiting review and asserts no sign-off record.
