---
title: "Price forecasts: a bounded re-measurement and withdrawal-led audit"
category: "market-analysis"
description: "A measured review of archived housing forecasts, their lineage, and their limits."
status: draft
date: 2026-11-20
personas: [investor, first-time-buyer, upgrader]
readingTime: "18 min read"
technicalLevel: intermediate
---

# Price forecasts: a bounded re-measurement and withdrawal-led audit

Edition id: `price-forecasts/2026-11-20` · Measured date: 2026-11-20 · Observation cutoff: 2026-10 (`cutoff.lastCompleteMonth`)

This edition supersedes the frozen legacy file `docs/analytics/editions/legacy/2026-11-12/price-forecasts.md` (SHA-256 `0bebf7307907002449571441af7308ba1cbf0c40622be415572bec4f112839ee`, `inputs.docs/analytics/editions/legacy/2026-11-12/price-forecasts.md.sha256`). This is a withdrawal-led audit with a re-measurement of the expired archived forecast where comparable outcomes are available, not a re-run or re-creation of the legacy model. The legacy wording is preserved in the source record; its unsupported figures do not carry forward as findings.

## Gate and clause-by-clause answer

> Reconcile article and predictive asset lineage first. Use rolling-origin validation, leakage checks, naive trend/seasonal baselines, error metrics and empirical prediction-interval coverage. Name R-squared correctly. Score expired 2025 forecasts where comparable outcomes exist. Never advance a stored forecast date or reuse BUY/SELL prompts as current advice.

| Gate clause | Disposition | Evidence boundary |
|---|---|---|
| Reconcile article and predictive asset lineage first. | The archived article, stored predictive asset, 2026 forecast files, feature-importance files, comparison file, and image panels are inventoried separately. No cross-lineage link is asserted. An unlinked artefact is evidence neither for nor against the run described by another artefact family. | `lineage`, `predictiveAsset`, `featureImportanceArtefacts`, `articleVsAsset`, `inputs` |
| Use rolling-origin validation, leakage checks, naive trend/seasonal baselines, error metrics and empirical prediction-interval coverage. | Rolling-origin results are reported for naive baselines only; the stored model has a single origin in its asset and cannot be rolling-origin validated from that record. Leakage screens record training preceding forecast issue by 181 days, a generated timestamp 49 days after the target, and 0 hindsight matches among 35 comparisons at one decimal under the primary convention. These are screens, not findings about origin. Error measures and empirical interval coverage are reported below with population and convention limits. | `rollingOrigin`, `forecastScoring.leakageChecks`, `forecastScoring.primary`, `forecastScoring.primary.coverage`, `notMeasurable.modelRollingOrigin` |
| Name R-squared correctly. | The archived metadata field `model_r2` is an R-squared fit statistic, not forecast accuracy. The legacy per-segment rows label R-squared as accuracy and are withdrawn; no linked segment output exists to re-measure them. | `predictiveAsset.metadataModelR2`, `articleVsAsset.reliabilityTable`, `articleVsAsset.perSegmentModelOutputs` |
| Score expired 2025 forecasts where comparable outcomes exist. | The stored forecasts are scored against observed planning-area medians under the explicit primary anchor convention. The convention is a scoring choice because the asset defines no anchor. Alternative readings and basis sensitivities remain documented rather than resolved by assumption. | `forecastScoring.primary`, `forecastScoring.conventions`, `forecastScoring.basisSensitivity` |
| Never advance a stored forecast date or reuse BUY/SELL prompts as current advice. | The archived date remains the date recorded in the asset. BUY signals are withdrawn as advice and are not repeated as recommendations. The application labels the archived signal as historical/not advice and the tools surface withholds prompts. | `predictiveAsset.distinctForecastDates`, `appConsumption.forecastLayer`, `appConsumption.signalPresentation`, `appConsumption.withheldPrompts`, `articleVsAsset.buySignals` |

## What the numbers are and are not

The evidence ledger distinguishes observations in the stored file from independently computed scores. An asset field describes what was stored; a frame-derived score describes a particular comparison under declared selection rules. Neither establishes how an unlinked legacy run was produced. The dated forecast object is an archive. Its fields are not a current view of market conditions, and no date was moved forward in this edition (`predictiveAsset.meaning`).

The archived metadata reports `model_r2` as a fit statistic. R-squared expresses fit under the model’s own fitting/evaluation context, as recorded by the asset; it is not an out-of-sample forecast error and cannot replace MAE, RMSE, bias, or MAPE calculated against later realised outcomes (`predictiveAsset.metadataModelR2`, `articleVsAsset.rSquaredNaming`). The old table’s terminology is therefore not retained. An unavailable segment result cannot be repaired by assigning a different interpretation to the stored statistic.

The observed comparison has a chosen basis and a chosen anchor. The primary basis is each planning area’s median transaction price across all property types, not a reconstructed property segment (`forecastScoring.basis.definition`). The primary anchor month is 2025-06 and target month is 2025-12 (`forecastScoring.primary.anchorMonth`, `forecastScoring.primary.targetMonth`). Since the asset does not define the reference point for its projected percentage, this anchor is a transparent scoring convention and not a recovered model contract (`forecastScoring.conventions`). A property-tag basis and a price-per-square-foot basis appear as sensitivities, not substitutes for the declared primary comparison (`forecastScoring.basisSensitivity`).

## Measured content

### Observation boundary and archive

The measured frame’s last complete month is 2026-10 (`cutoff.lastCompleteMonth`). The transaction counts and shares that follow are measured on the private (condo) rows, not on all property types (`cutoff.basis`). The cutoff’s terminal month is 2026-11 (`cutoff.terminalMonth`), with 421 transactions (`cutoff.terminalMonthTransactions`), compared with a trailing-twelve-month median of 2133.0 (`cutoff.trailing12MedianTransactions`); its terminal share is 0.1974 (`cutoff.terminalMonthShareOfTrailingMedian`). The last complete month has 2546 transactions (`cutoff.lastCompleteMonthTransactions`) and a share of 1.1936 (`cutoff.lastCompleteMonthShareOfTrailingMedian`). On the all-property-types scope the same terminal month has 1211 transactions (`cutoff.allPropertyTypesTerminalMonthTransactions`), so 421 is the private-row count, not a frame-wide total. Every frame aggregation in the ledger observes this cutoff (`cutoff.meaning`).

The stored asset records its forecast date and training date, and those fields are quoted as stored rather than interpreted as evidence of a linkage to a particular historical article (`predictiveAsset.distinctForecastDates`, `predictiveAsset.lastTrainingDate`). Its area-level structure is not a collection of property-type forecasts. The inventory records the asset’s planning-area count and tag counts, while the article’s per-segment outputs have no stored counterpart (`predictiveAsset.areaCount`, `predictiveAsset.policyMarketSegmentTags`, `articleVsAsset.perSegmentModelOutputs`).

### Expired forecast scoring

The outcome is the change in the planning-area all-property median between the declared anchor and target months. A producer-selected transaction floor applies in both months; areas below that floor or without a median are excluded from the primary population (`forecastScoring.basis.floor`, `forecastScoring.primary.excludedAreas`). The chosen population is available-case by method, so sample sizes are shown for each row. MAE, RMSE, and bias are in percentage points of change. MAPE is calculated from implied price levels, not from percentage-change errors (`forecastScoring.primary.methods.storedForecasts.mapeDefinition`).

| Comparison | MAE (percentage points) | RMSE (percentage points) | MAPE on implied levels (%) | Bias (percentage points) | Available N | Ledger fields |
|---|---:|---:|---:|---:|---:|---|
| Archived forecast | 65.0086 | 92.6605 | 68.3145 | 64.4953 | 35 | `forecastScoring.primary.methods.storedForecasts` |
| Last-value / zero-change baseline | 13.2765 | 19.2557 | 13.454 | -2.0218 | 35 | `forecastScoring.primary.methods.zeroChange` |
| Six-month trend-persistence baseline | 25.2692 | 38.7189 | 29.7472 | 3.1562 | 34 | `forecastScoring.primary.methods.trend6m` |
| Seasonal-naive baseline | 20.4372 | 26.6611 | 33.0995 | 6.4634 | 33 | `forecastScoring.primary.methods.seasonalNaive` |

The scores describe this comparison only. They do not imply that the legacy ensemble or its per-segment versions were the model stored in the asset. The asset and article are not joined by a provenance record, so this score neither verifies nor refutes the legacy model’s origin (`lineage`, `articleVsAsset`). The anchor is explicit precisely because the source leaves the projected-change reference point unstated; alternative conventions are retained in the evidence record (`forecastScoring.conventions`, `forecastScoring.conventionSensitivity`).

Interval coverage is evaluated across areas for this single stored forecast period, not across repeated time origins. One of 35 scored areas (2.8571%) falls within the stored bounds, against an assumed nominal level of 0.95 (`forecastScoring.primary.coverage.nWithin`, `.nScored`, `.empiricalCoverage`, `.nominalLevel`). The nominal level is assumed, not supplied by the asset; this empirical fraction is descriptive and is not a calibration guarantee. Width summaries characterize the stored bounds and do not establish their calibration (`forecastScoring.primary.coverage`).

### Baseline rolling-origin results

Naive comparators were evaluated across rolling monthly origins with the six-month horizon, subject to the cutoff. The ledger records 23 origins from 2024-06 through 2026-04; the mean of per-origin MAE is shown below (`rollingOrigin.originCount`, `rollingOrigin.firstOrigin`, `rollingOrigin.lastOrigin`, `rollingOrigin.meanOfPerOriginMae`). These results contextualise baseline behavior and do not validate the stored model, which has one forecast origin (`rollingOrigin.meaning`, `notMeasurable.modelRollingOrigin`).

| Baseline | Mean of per-origin MAE (percentage points) | Ledger key |
|---|---:|---|
| Zero change | 16.9752 | `rollingOrigin.meanOfPerOriginMae.zeroChange` |
| Six-month trend persistence | 28.3879 | `rollingOrigin.meanOfPerOriginMae.trend6m` |
| Seasonal naive | 27.2795 | `rollingOrigin.meanOfPerOriginMae.seasonalNaive` |

### Lineage, absence boundaries, and missingness

The legacy primary-input claim names a path for which the whole-checkout filename scan recorded no match. The declared boundary excludes `.git/`, dependency trees, virtual environments, programme-owned surfaces, the named plan, and published editions except the legacy corpus. The scan covers filenames on disk, not archive contents or off-checkout sources. Its empty match list is not evidence about an alternative input or an earlier run (`absenceScans.primaryInputPath.filenameMatches`, `absenceScans.primaryInputPath.filenameMatchCount`, `absenceScans.trainTestSplitFiles.roots`, `absenceScans.trainTestSplitFiles.boundaryNote`).

The split-file search reports the searched roots and each matched file, with an empty matches list. This is an absent-file result within that bounded filename scan. The comparison file containing train/test metrics belongs to an unlinked run; those metrics without split files are distinct evidence states and cannot be joined to the legacy article (`absenceScans.trainTestSplitFiles.matches`, `absenceScans.trainTestSplitFiles.matchCount`, `featureImportanceArtefacts.modelComparison`).

The producer-reference count searches the `scripts/` subset of the hash-pinned corroboration scan, while `filesScanned` records all files across the corroboration scan roots, not just scripts. The `scripts/` subset's scanned-file count is `absenceScans.producerScripts.filesScanned` and its matching references are counted at `absenceScans.producerScripts.predictiveAnalyticsReferencesInScripts`. This only says no matching reference was found in that bounded subset and does not establish that a producer never existed (`absenceScans.producerScripts.root`, `absenceScans.producerScripts.filesScanned`, `absenceScans.producerScripts.predictiveAnalyticsReferencesInScripts`, `corroborationScan.filesScanned`, `corroborationScan.roots`).

The target name `yoy_change_pct` is an absent column in the metadata schema of the shipped platinum parquet. Null-value and recorded-zero counts for that target are inapplicable because the column is absent; no absent-row count for that target is measured. The split-file scan finds no files with the two claimed split filenames; it is an absent-file result, not a count of absent data rows (`absenceScans.trainTestSplitFiles.matches`, `.matchCount`). These are distinct missingness states: a null, a recorded zero, an absent row, an absent file, and an absent column are not interchangeable. The schema scan records the column count and explicit presence flag (`absenceScans.yoyChangePctColumn.state`, `.frameColumnCount`, `.columnPresent`).

The stored asset inventory has no segment-keyed output fields, and its recorded policy tags are HDB/PRIVATE; this is a bounded finding about that asset only. No checkout-wide search for all possible segment-output or grouping artefacts is claimed. A plot or panel without a link to the run at issue is evidence neither for nor against that run. No origin conclusion is drawn from a structural pattern or from an unlinked file (`articleVsAsset.perSegmentModelOutputs`, `predictiveAsset.policyMarketSegmentTags`, `corroborationScan`).

### Leakage screens and method limits

The gate requests leakage checks. The measured screens record that training precedes forecast issue by 181 days, the asset generated timestamp is 49 days after the target, and the hindsight screen has 0 matches among 35 comparisons at one decimal under the primary convention (`forecastScoring.leakageChecks.trainingToForecastDays`, `.generatedAtDaysAfterTarget`, `.hindsightScreen.primaryAnchor.matchesAtOneDecimal`, `.hindsightScreen.primaryAnchor.nCompared`). These are screens only: they do not establish when the forecasts were computed relative to the data, and origin remains unverified. The absence of a reproducible model pipeline means that feature timing, split boundaries, transformations, target construction, and any selection performed in the retired workflow cannot be independently reconstructed from that workflow’s code (`notMeasurable`).

The article’s described annual ensemble, model parameter settings, data split, feature selection, and ARIMA specification are individually adjudicated in the superseded-figures table. A specification printed in prose is not equivalent to a saved fitted object, a reproducible transformation, or a split manifest. The edition does not use absent implementation detail as a reason to invent the retired process (`notMeasurable.xgboostParameters`, `notMeasurable.featureSelectionRule`, `notMeasurable.arimaSpec`, `notMeasurable.smartEnsemble`).

### Superseded figures

Each phrase below is reproduced exactly from the frozen legacy source, as checked by the ledger. Status distinguishes direct re-measurement of an asset fact, withdrawal of a claim whose evidentiary basis is inadequate, and claims that remain not reproducible because the relevant definition or provenance is unavailable. Reasons are bounded to the cited ledger field; they do not claim to establish origin.

| ID | Verbatim legacy claim | Status | Measured reason / ledger key |
|---|---|---|---|
| C01 | **Analysis Date**: 2026-02-17 | not-reproducible | the article's analysis date has no artefact behind it; the stored asset's generated_at (2026-02-19) is a different, later timestamp recorded at predictiveAsset.generatedAt — two dates, no linkage (`lineage.vintages.0.meaning`) |
| C02 | **Data Period**: 2021-2026 | not-reproducible | the window selection of the retired run is unrecorded; recording a 2021-2026 slice of the frame would prescribe what the source does not state (`notMeasurable.analysisWindow`) |
| C03 | **Coverage**: HDB, condo, and EC segments | not-reproducible | the stored asset tags its 41 areas HDB(24)/PRIVATE(17) with no EC grouping; the article's three-segment coverage has no stored counterpart and the retired run's coverage is unverifiable (`predictiveAsset.policyMarketSegmentTags`) |
| C04 | \| HDB flats          \| 79.8%         \| ±18.58%      \| 99.4%           \| Strong                       \| | withdrawn | per-segment table row: withdrawn per the gate; R-squared is a fit statistic, not forecast accuracy, and no train/test or holdout artefact for these five segment models exists in this checkout, so there is nothing to re-measure the row against (`articleVsAsset.reliabilityTable.rows.hdb`, `articleVsAsset.reliabilityTable.meaning`). The values do recur outside the article — in the sibling findings articles (`corroborationScan.ownCopies.\`79.8%\`.outsideFiles`) and in a source comment describing an uncertainty column (`corroborationScan.valueTokens.\`±18.58%\`.allMatches`) — so recurrence is recorded, not read as corroboration (`corroborationScan.independentMatchFiles`) |
| C05 | \| Executive Condos   \| 98.5%         \| ±50.15%      \| 97.1%           \| Strong but wider uncertainty \| | withdrawn | per-segment table row: withdrawn; the values recur outside the article only in its own copies, in the sibling legacy articles that quote the same numbers, and in a source comment describing an uncertainty column — cross-citation inside documents, never a train/test or holdout artefact, and so not corroboration in either direction (`articleVsAsset.reliabilityTable.rows.ec`, `corroborationScan.independentMatchFiles`) |
| C06 | \| Mass Market Condos \| 85.6%         \| ±40.48%      \| 96.4%           \| Useful with caution          \| | withdrawn | per-segment table row: withdrawn (`articleVsAsset.reliabilityTable.rows.mass`) |
| C07 | \| Mid Market Condos  \| 72.6%         \| ±1877.88%    \| 94.2%           \| Direction only               \| | withdrawn | per-segment table row: withdrawn; the ±1877.88% width is itself a red flag no artefact explains (`articleVsAsset.reliabilityTable.rows.mid`) |
| C08 | \| Luxury Condos      \| 30.1%         \| ±1076.24%    \| 92.3%           \| Magnitude unusable           \| | withdrawn | per-segment table row: withdrawn (`articleVsAsset.reliabilityTable.rows.lux`) |
| C09 | \| HDB               \| 2-year YoY appreciation \| 51.14%     \| | withdrawn | per-segment feature-importance claim: withdrawn; no checkout feature list contains such a feature name (featureImportanceArtefacts.featuresNamedLikeYoyLag) (`articleVsAsset.featureClaims.hdbFeature`) |
| C10 | \| Mass market condo \| 2-year YoY appreciation \| 65.50%     \| | withdrawn | per-segment feature-importance claim: withdrawn (`articleVsAsset.featureClaims.massFeature`) |
| C11 | - **Primary input**: `data/parquets/L3/housing_unified.parquet` (2021-2026) | not-reproducible | the named path does not exist in this checkout (no filename match recorded, `absenceScans.primaryInputPath.filenameMatchCount`); which input the retired run used is unverifiable (`absenceScans.primaryInputPath`) |
| C12 | - **Train/test split**: `price_appreciation_train.parquet` / `price_appreciation_test.parquet` | not-reproducible | no filename match in the whole tree (`absenceScans.trainTestSplitFiles.matchCount`); train/test metrics exist only in an unlinked comparison file (`absenceScans.trainTestSplitFiles`) |
| C13 | - **Forecast horizon**: 6 months (ARIMA), annual (XGBoost ensemble) | not-reproducible | the horizon and model labels describe the retired article workflow; separate stored vintages are unlinked and cannot re-measure that workflow. The asset’s own stored horizon is independently inventoried (`lineage`, `notMeasurable.smartEnsemble`) |
| C14 | - **Feature selection**: numeric only, max 20% missing values allowed | not-reproducible | no preprocessing artefact states the rule as applied (`notMeasurable.featureSelectionRule`) |
| C15 | - **XGBoost models** were trained per property type (HDB, Condo, EC) in the historical research workflow | not-reproducible | the stored asset has no segment-keyed outputs; no checkout-wide search for every possible per-property-type model artefact was performed (`articleVsAsset.perSegmentModelOutputs`) |
| C16 |   - Parameters: n_estimators=100, max_depth=6, learning_rate=0.1, subsample=0.8 | not-reproducible | the parameter string exists only in article copies and a sibling legacy article; no run artefact (`notMeasurable.xgboostParameters`) |
| C17 | - **Target variable**: `yoy_change_pct` (year-over-year appreciation) | not-reproducible | the stated target is an ABSENT COLUMN of the shipped platinum frame; the name survives only in unlinked importance artefacts (`absenceScans.yoyChangePctColumn`) |
| C18 | - **Smart ensemble**: stacked model combining segment-specific predictions | not-reproducible | no ensemble artefact exists (`notMeasurable.smartEnsemble`) |
| C19 | - **Confidence intervals**: calibrated per segment using residual distributions | not-reproducible | the calibration procedure is unrecorded; for the distinct stored asset, empirical coverage is 1 of 35 areas (2.8571%) against an assumed 0.95 nominal level (`forecastScoring.primary.coverage`) |
| C20 | - **ARIMA(1,1,1)** for time-series forecasting per planning area | not-reproducible | the order string appears in article copies and one plan document; no fitted output exists (`notMeasurable.arimaSpec`) |
| C21 | for time-series forecasting per planning area | not-reproducible | this phrase describes the retired time-series workflow; the stored asset’s planning-area granularity is separately inventoried but is unlinked and cannot re-measure the legacy method claim (`lineage`, `predictiveAsset.areaCount`) |
| C22 | - **Condo sub-segmentation**: mass market, mid market, luxury | not-reproducible | the stored asset’s recorded policy tags are HDB/PRIVATE; this asset inventory does not establish whether other grouping artefacts exist elsewhere in the checkout (`predictiveAsset.policyMarketSegmentTags`) |
| C23 | \| HDB                \| 79.8% \| 99.4%                \| ±18.58%      \| | withdrawn | appendix repeat of the segment table: withdrawn (`articleVsAsset.technicalTable.rows.hdb`) |
| C24 | \| Executive Condos   \| 98.5% \| 97.1%                \| ±50.15%      \| | withdrawn | appendix repeat: withdrawn (`articleVsAsset.technicalTable.rows.ec`) |
| C25 | \| Mass Market Condos \| 85.6% \| 96.4%                \| ±40.48%      \| | withdrawn | appendix repeat: withdrawn (`articleVsAsset.technicalTable.rows.mass`) |
| C26 | \| Mid Market Condos  \| 72.6% \| 94.2%                \| ±1877.88%    \| | withdrawn | appendix repeat: withdrawn (`articleVsAsset.technicalTable.rows.mid`) |
| C27 | \| Luxury Condos      \| 30.1% \| 92.3%                \| ±1076.24%    \| | withdrawn | appendix repeat: withdrawn (`articleVsAsset.technicalTable.rows.lux`) |
| C28 | - **Top feature**: 2-year YoY appreciation (51.14% importance for HDB, 65.50% for mass-market condo) | withdrawn | combined feature-importance claim: withdrawn (`articleVsAsset.featureClaims.combined`) |
| C29 | - **ARIMA**: 20 planning areas with ≥12 months of data, 6-month forecast horizon | not-reproducible | the retired run's input coverage is unverifiable; the stored asset covers 41 areas (predictiveAsset.areaCount) with a 6-month horizon (predictiveAsset.horizonMonths) — recorded, not adjudicated (`notMeasurable.arimaCoverage`) |
| C30 | - **Ensemble accuracy**: 74% vs 47% for a unified one-size-fits-all model | withdrawn | 'accuracy' is undefined (metric, population, window all unstated): withdrawn, not re-measured (`articleVsAsset.ensembleAccuracyClaim`) |
| C31 | Segment-specific modeling dramatically outperforms unified approaches (74% vs 47% accuracy). | withdrawn | conclusion repeat of C30: withdrawn (`articleVsAsset.ensembleAccuracyClaim`) |
| C32 | luxury condos are essentially unpredictable in magnitude (R²=30.1%, CI width ±1076%). | withdrawn | conclusion repeat of the luxury row (C08): withdrawn (`articleVsAsset.reliabilityTable.rows.lux`) |

The repetition of values in appendices or conclusions does not create a separate measurement. Where the same per-segment table is repeated, the disposition applies to each quoted instance and its claim identifier. A withdrawn value is retained here only to make the replacement auditable; its presence is not endorsement, recalculation, or advice (`legacyClaims`).

The article’s statements about analysis date and data period remain unsupported as claims about the retired workflow. Dates present in a different asset are recorded independently and do not link the artefacts. The edition uses the measured observation cutoff only for calculations from the shipped frame, and does not reinterpret an old stated data window as a frame selection rule (`legacyClaims`, `lineage.vintages`, `cutoff`).

The legacy segment accuracy and interval-width rows are withdrawn, including the luxury and middle-market rows. No corresponding per-segment output or split provenance was found in the bounded asset and scan records. This treatment does not imply that a row is inaccurate; it records that the asserted result is not supported as a reproducible measurement by the available linked evidence (`articleVsAsset.reliabilityTable`, `articleVsAsset.perSegmentModelOutputs`, `absenceScans.trainTestSplitFiles`).

Likewise, the feature-importance values and the combined-model accuracy comparison are not carried forward. The surviving feature-importance files concern separately inventoried targets and models; absent a provenance link, they neither authenticate nor disprove the legacy table. Their structural contents can be described only as inventoried, not as the source of the article’s figures (`featureImportanceArtefacts`, `articleVsAsset.featureClaims`, `articleVsAsset.ensembleAccuracyClaim`).

## What this edition does not establish

- It does not establish that the stored asset and the legacy article came from the same run, code, data vintage, or modelling contract. Unlinked artefacts adjudicate neither in support nor against one another (`lineage`, `corroborationScan`).
- It does not establish how any screened series was produced. The date-ordering and hindsight screens are recorded in `forecastScoring.leakageChecks`; they flag observable patterns only, and origin remains unverified.
- It does not provide rolling-origin performance for the stored model. Its single stored origin is the boundary, while the rolling-origin results apply only to naive comparators (`notMeasurable.modelRollingOrigin`, `rollingOrigin`).
- It does not establish interval calibration or a supplied nominal confidence level. The empirical coverage is cross-sectional for the one stored period, and the nominal level is an explicit assumption (`forecastScoring.coverageSummary`).
- It does not resolve the asset’s missing projected-change anchor. The scoring convention and sensitivity readings are disclosed rather than attributed to the source (`forecastScoring.conventions`, `forecastScoring.conventionSensitivity`).
- It does not recover definitions omitted from the legacy text. Units, windows, populations, training rules, and accuracy metrics that are absent remain underspecified and not reproducible (`notMeasurable`, `legacyClaims`).
- It does not treat missingness states as equivalent: the target is an absent schema column, so null/zero counts for that target are inapplicable; no target absent-row count was measured. The split filename scan found no files, which is an absent-file result, not an absent-row count (`absenceScans.yoyChangePctColumn`, `absenceScans.trainTestSplitFiles`).
- It does not treat filenames or file-row counts as counts of observations in a time series. Each scan boundary and each table’s population must be read from its own ledger field (`absenceScans`, `forecastScoring.primary`).
- It does not present BUY/SELL prompts as current advice, update an archive date, or infer a current market direction from expired predictions (`appConsumption`, `predictiveAsset.distinctForecastDates`).
- It does not turn a missing producer reference in the scanned `scripts/` root into a claim that no producer ever existed (`absenceScans.producerScripts`).

## Reading this edition by persona

### Investor

For an investor, the central distinction is between an archived prediction and a measured comparison with realised prices. The comparison here tests only one stored forecast period under the stated all-property median convention. The naive baselines provide context for that comparison, while the repeated-origin baseline results are not evidence of repeated model performance. Neither the old segment table nor archived BUY labels provide a current action signal (`forecastScoring.primary`, `rollingOrigin`, `appConsumption.signalPresentation`).

A cautious reading keeps outcome definition and population together. The all-property median makes the score inspectable but does not make it equivalent to a segment-specific result. Any strategy, risk tolerance, financing conditions, holding period, and transaction costs are outside this evidence record. This edition therefore supplies no investment recommendation (`forecastScoring.basis.definition`, `notMeasurable`).

### First-time buyer

For a first-time buyer, the archived forecast should be treated as a historical research object rather than an indication of what a home will cost now. Its date remains unchanged, and the edition’s outcome comparison is bounded to the selected historic months. Area medians summarize transactions and do not describe the price, condition, financing, or suitability of an individual home (`predictiveAsset.distinctForecastDates`, `forecastScoring.primary`).

The withdrawn rows should not be read as confidence ratings for a particular property category. The asset does not provide the corresponding segment predictions, and the legacy definitions do not supply a reproducible basis for those rows. A buyer can use this page to understand the evidence boundary, not to infer an affordability forecast or a purchase timing signal (`articleVsAsset.perSegmentModelOutputs`, `legacyClaims`).

### Upgrader

For an upgrader, the comparison may be useful as a historical stress test of a stored area-level projection against later medians, but it is not a model of a household’s sale and replacement transaction. The asset’s area granularity, the scoring population, and the chosen anchor convention are explicit; they do not represent individual resale outcomes or the timing gap between two transactions (`predictiveAsset.areaCount`, `forecastScoring.primary`, `forecastScoring.conventions`).

Comparing two homes, loan structures, or transaction sequences requires evidence not included here. The archived signal and unsupported segment tables should not be repurposed as personal advice. The safe interpretive use is limited to the recorded historical comparison and its documented limitations (`appConsumption.withheldPrompts`, `articleVsAsset.reliabilityTable`).

## Reading the comparison without over-reading it

The reported measures answer distinct questions. MAE averages the absolute difference between predicted and observed percentage changes for the scored areas. RMSE gives larger residuals greater influence through squaring before aggregation. Bias preserves the sign of the average error, so it signals systematic over- or under-prediction under the chosen error convention. MAPE here is deliberately evaluated on implied price levels; dividing by realised percentage changes could behave badly when those changes are close to zero. These definitions accompany the actual methods in the evidence ledger, not an inferred definition of the legacy article’s word “accuracy” (`forecastScoring.primary.methods`).

The scored population is defined by availability under the declared floor. Exclusions are not interchangeable with missing outcomes for every area in the dataset, and they are not a claim that those places have no housing activity. They mean that the specified month/basis comparison did not meet the producer-selected threshold or did not yield a median in the primary scoring frame (`forecastScoring.basis.floor`, `forecastScoring.primary.excludedAreas`). The ledger preserves excluded-area identifiers and per-month counts; the summary table does not turn the exclusions into forecasts.

The baseline comparison is a reference, not a claim that a baseline is a complete market model. Zero-change holds the anchor level fixed; trend persistence carries forward a recent six-month change; and seasonal naive reuses a change from a corresponding prior-year window. The definitions are operational conventions in the producer’s scoring code and are recorded alongside the results (`forecastScoring.primary.baselineDefinitions`). A baseline’s performance can vary with the selected anchor, outcome basis, available observations, and horizon. This comparison does not assert that any comparator would have been selected for deployment.

For the same reason, baseline rolling-origin validation and stored forecast scoring must remain separate. The recurring origins test how the defined baselines behave over multiple historical windows; they do not add origins to the stored predictive object. A single stored vintage can be evaluated against a later outcome, but it cannot reveal how the model would have behaved at other origins absent archived forecasts for those origins (`rollingOrigin.meaning`, `predictiveAsset.distinctForecastDates`, `notMeasurable.modelRollingOrigin`). The observed baseline record is useful context, but it does not supply model validation for the missing historical workflow.

An empirical interval inclusion fraction is also narrower than a calibration claim. Here the unit of aggregation is areas for one stored forecast period. Repeated-period coverage would require stored forecasts and outcomes over repeated origins under a defined interval procedure; those records are not present for this model. Further, the data object does not state the nominal interval level. The reported nominal comparison is therefore labelled as an assumption in the ledger, not a source-supplied probability (`forecastScoring.coverageSummary`, `notMeasurable.ciCalibration`).

## Reading the comparison with its provenance intact

A measurement’s usefulness depends on keeping its provenance attached. The ledger distinguishes the archived asset itself, the frame used for scoring, the ancillary forecast files, the feature-importance files, and plot inputs. Their shared subject matter is not a join key. Unless a run identifier or documented lineage connects an artefact to a claim, their contents remain separate evidence objects (`inputs`, `lineage`, `corroborationScan`). Consequently, an image that appears visually compatible with a narrative cannot bridge the missing lineage, and an image that appears inconsistent cannot adjudicate against the narrative either.

The same constraint applies to the comparison file containing training and testing metrics. A metrics row is not a dataset split, and the split filenames are not found in the stated scan boundary. The comparison file’s presence is recorded, but no assertion is made that its entries belong to the legacy article or to the stored forecast asset (`featureImportanceArtefacts.modelComparison`, `absenceScans.trainTestSplitFiles`). No split population, preprocessing history, or test period is inferred from those detached metrics.

The target-schema observation is similarly specific. The shipped platinum schema was inspected as metadata. The named target does not appear as a schema column there; this does not mean that rows have a null for that target, nor that a numeric value equals zero, nor that some other dataset could not have had a similarly named field. It states only what the declared schema scan found (`absenceScans.yoyChangePctColumn`). This distinction matters because missing columns and missing values require different evidence and support different conclusions.

The producer-reference scan has a different scope again. It is limited to the scripts root and its stated supported files; it does not inspect every historical machine, external repository, or former workflow. Therefore an empty result supports only a bounded statement about that scan. It cannot be elevated into a universal account of whether a producer existed (`absenceScans.producerScripts`). File-level search boundaries are stated wherever absence is material, and no count of scanned files is offered as a count of observations.

## How to use the supersession record

The table records each quantitative or method claim that the legacy source identified, including repeated appendix rows and repeated conclusion wording. Its verbatim phrase is included so a reviewer can trace the disposition back to the fixed source. Status is claim-specific: a directly measured asset property can be re-measured without validating other clauses in the same legacy sentence, while a withdrawn figure is deliberately not promoted to a new result. Not-reproducible means that a necessary definition, source, provenance link, or method record is missing from this evidence boundary; it does not mean that the historical claim has been empirically disproved (`legacyClaims`, `claimKeyCheck`).

Where a phrase combines a measurable archive property with an unsupported historical method, the table’s ledger key and note preserve that distinction. For example, stored horizon or area granularity can be measured from the asset while the claimed model family or annual ensemble remains unverified. The re-measurement status must not be read as validating every adjacent clause in the legacy phrase (`legacyClaims`, `predictiveAsset`).

Claim-key resolution is an automated syntactic walk: it checks that each key locates a field or identified list item in the evidence document. The verbatim quote check likewise verifies that recorded phrases occur in the frozen file. Neither mechanism certifies the factual quality of a measurement or the correctness of its disposition. Human review must still assess whether each reason respects the field’s scope and whether a status accurately reflects the available evidence (`claimKeyCheck.method`, `legacyQuoteCheck.method`).

## Inputs

The following hashes identify the inputs measured by the producer. Byte counts describe input files, not observations. Row and column counts appear only where the ledger supplies them. The paths and metadata below are reproduced from `inputs`; the archived legacy source is included as an input and has its own fixed file hash.

| Input path | SHA-256 | Bytes | Rows / columns when recorded | Ledger key |
|---|---|---:|---|---|
| `app/public/data/analysis/price_forecasts/planning_area_forecasts.png` | `92050b3e22cdf890ad08c32c515ee167c8532edf5396a9ae211856d3ed8b9df1` | 329781 | not recorded  `inputs.app/public/data/analysis/price_forecasts/planning_area_forecasts.png` |
| `app/public/data/analysis/price_forecasts/price_vs_forecast_scatter.png` | `713fc86d0621c26041b7fadc2de4792eda26e477d43c1f237093dbe26c5f19d8` | 344605 | not recorded  `inputs.app/public/data/analysis/price_forecasts/price_vs_forecast_scatter.png` |
| `app/public/data/analytics/predictive_analytics.json.gz` | `14a8ae6f0ce503e10068a491940cc78e2ad0ae77afa3dbe67b2096a73f3e3c06` | 1804 | not recorded  `inputs.app/public/data/analytics/predictive_analytics.json.gz` |
| `app/src/components/tools/lib/tool-evidence.ts` | `2db0deaf69ccb07e88b3a78e9d6bd455bbe71fb0a567b10a2c7e55832caa9e63` | 14991 | not recorded  `inputs.app/src/components/tools/lib/tool-evidence.ts` |
| `app/src/constants/data-urls.ts` | `1bf90653e2afcfb889ac0ea63303a1ff46d79746c1bbffc667dcbc48a354abdd` | 1220 | not recorded  `inputs.app/src/constants/data-urls.ts` |
| `app/src/utils/map-archive.ts` | `e23de6c83877e7598a1e9961b7e5f53c9e97a2aed1892a89c8406e9921853c27` | 23716 | not recorded  `inputs.app/src/utils/map-archive.ts` |
| `data/analysis/feature_importance/feature_importance_price_psm_random_forest.csv` | `d89a7be2cc90e539fc06534a64089dc234c8114b31411cb60a929c232748f7ef` | 8070 | not recorded  `inputs.data/analysis/feature_importance/feature_importance_price_psm_random_forest.csv` |
| `data/analysis/feature_importance/feature_importance_price_psm_xgboost.csv` | `7864979c99ba4c2ec22c142bd4429d94803419f537dd520b28009f077b8df2f4` | 6279 | not recorded  `inputs.data/analysis/feature_importance/feature_importance_price_psm_xgboost.csv` |
| `data/analysis/feature_importance/feature_importance_rental_yield_pct_random_forest.csv` | `a2244fddf01be07cb572b3fd4eb7b5c7c32d71d188ef255f23eee7cf608576dc` | 7618 | not recorded  `inputs.data/analysis/feature_importance/feature_importance_rental_yield_pct_random_forest.csv` |
| `data/analysis/feature_importance/feature_importance_rental_yield_pct_xgboost.csv` | `0aafc146740e61479ca648fd9334d7a0ea27e90ee3dd317474c91dd076b06e6b` | 5857 | not recorded  `inputs.data/analysis/feature_importance/feature_importance_rental_yield_pct_xgboost.csv` |
| `data/analysis/feature_importance/feature_importance_yoy_change_pct_random_forest.csv` | `7952713db5acdf1c77f7713ecfa55a47d0dd0e3a3d7146c7ed326cfc46705fa2` | 7626 | not recorded  `inputs.data/analysis/feature_importance/feature_importance_yoy_change_pct_random_forest.csv` |
| `data/analysis/feature_importance/feature_importance_yoy_change_pct_xgboost.csv` | `4dadafd391960a7ed5b5bb8e279ce783e20964e97e577fa68af6feaa991fc34c` | 5766 | not recorded  `inputs.data/analysis/feature_importance/feature_importance_yoy_change_pct_xgboost.csv` |
| `data/analysis/feature_importance/model_comparison.csv` | `3ae305054c392db84289a47380ef8fbb712f0576c14b7f9a0470b122e2d6e962` | 2061 | not recorded  `inputs.data/analysis/feature_importance/model_comparison.csv` |
| `data/forecasts/hdb_price_forecasts.csv` | `b63c842d4f8514ca42ccc9df943f5bcf3f9db38c571ed9e68fa8aeb61b64dce0` | 5847 | not recorded  `inputs.data/forecasts/hdb_price_forecasts.csv` |
| `data/forecasts/hdb_price_forecasts.parquet` | `29ccd3cf4060aef90842e2d08bb21c2116174914fd1827756a5344c0e7714c5e` | 9664 | 60 rows, 11 columns  `inputs.data/forecasts/hdb_price_forecasts.parquet` |
| `data/forecasts/hdb_yield_forecasts.csv` | `b02f7676e21216c1f4221094131b7ae50f0cc62a1ce61de73df6c31a1b3eb2a5` | 3899 | not recorded  `inputs.data/forecasts/hdb_yield_forecasts.csv` |
| `data/forecasts/hdb_yield_forecasts.parquet` | `b1ddc91ef45da91f4b74da0bfa57630bd06c2061a45d7dfe6c6b71077d4084dd` | 8431 | 56 rows, 9 columns  `inputs.data/forecasts/hdb_yield_forecasts.parquet` |
| `data/pipeline/04_platinum/unified_dataset.parquet` | `39d234f703c9d6e098acc885eaadfdc965a6ac217189277c066676b3b117cefe` | 78381526 | 1236310 rows, 97 columns  `inputs.data/pipeline/04_platinum/unified_dataset.parquet` |
| `docs/analytics/editions/legacy/2026-11-12/price-forecasts.md` | `0bebf7307907002449571441af7308ba1cbf0c40622be415572bec4f112839ee` | 6117 | not recorded  `inputs.docs/analytics/editions/legacy/2026-11-12/price-forecasts.md` |
| `docs/analytics/price-forecasts.md` | `82f3890030dbaf994ac8131e8a3c845a16bd9f70288056f297de35c03373d24e` | 6144 | not recorded  `inputs.docs/analytics/price-forecasts.md` |
| `docs/archive/20260124-data-reorganization-complete.md` | `e92d12741eedad918c0a44aaf074cb5ea83a21cfaf7062d2b34ce321233c72a1` | 6235 | not recorded  `inputs.docs/archive/20260124-data-reorganization-complete.md` |

## Provenance

Prepared by `repo-agent/session-2026-11-20`. Evidence pack: `docs/implementation/2026-11-20-rs14-price-forecasts-evidence.md`. Machine-readable ledger: `docs/implementation/artifacts/rs14-price-forecasts-evidence.json`, SHA-256 `8a7234723fc5d34ce741c99df9b22dfb2d6f2b740f407518c29e53846836b6dc`. The ledger records a syntactic claim-key resolution check and verbatim quote check; those checks establish addressability and literal presence, not substantive truth (`claimKeyCheck.method`, `legacyQuoteCheck.method`). This text is a draft awaiting review and asserts no sign-off record.
