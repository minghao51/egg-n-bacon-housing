---
title: Macro Sensitivity
category: "market-analysis"
description: What this checkout can and cannot say about macro conditions and HDB resale activity — the SORA series screened for an annual-ramp pattern and excluded (origin unverified), gold-column lineage, stationarity, and thirty-five legacy claims disposed with measured reasons
status: draft
date: 2026-11-18
personas:
  - investor
  - first-time-buyer
  - upgrader
readingTime: "8 min read"
technicalLevel: intermediate
---

# Macro Sensitivity

**Edition:** `macro-sensitivity-2026-11-18` · **Measured:** 2026-11-18 · **Observation cutoff:** 2026-10 (last complete month)

This edition replaces the macro-sensitivity text dated 2026-03-31, frozen in the archive as [`legacy/2026-11-12/macro-sensitivity.md`](../../legacy/2026-11-12/macro-sensitivity.md) (157 lines, sha256 `8af923420706a072c1b8e6287b4d54b70bdfbad3afcd65dce1a9e7cce41a7a88` — `inputs`, `legacyQuoteCheck.legacyFileSha256`). It is a **re-measurement, not a re-publication**: the old text's rate narrative rested on a SORA series that this ledger screens as an annual-ramp fallback, its qualitative correlation labels carry no coefficient, and its regime and policy tables have no artefact in this checkout. What this edition does instead: screens every series for a generated/fallback pattern, reports the annual-ramp signature that `sora_rates` carries — its origin remaining unverified — and excludes it from every edition-facing figure, quantifying what the exclusion costs; re-measures the legacy article's four SORA rate bands on the source series, where two reproduce and two do not; measures the gold-column trap both series sit behind; reports stationarity and associations in levels **and** first differences with serial-adjusted uncertainty; and disposes all **35** registered legacy claims, **7 re-measured and 28 withdrawn** (`legacyClaims`). Every figure comes from the canonical ledger [`artifacts/rs09-macro-sensitivity-evidence.json`](../../../../implementation/artifacts/rs09-macro-sensitivity-evidence.json) — sha256 `ae403f11db8786e4258418d8791c6e0255fe2f4800d32e624f4014b6af629d7b`, 96,351 bytes — re-measured byte-identically from this checkout by `uv run python scripts/tools/macro_sensitivity_evidence.py --check`. The terminal month, 2026-11, holds 1,211 transactions — 0.264 of the trailing-12-month median of 4,587.5 (`cutoff`) — and is excluded as partial; housing-side figures end at 2026-10.

## The register gate, clause by clause

The gate RS09 is judged against (`docs/plans/2026-11-12-reporting-refresh-research-register.md`, RS09 row): *"Explicitly identify generated/fallback series and exclude them from empirical claims unless the entire result is a labelled simulation. Document release lag, revisions, missing periods, stationarity and uncertainty. No present-day timing regime claims from unknown source vintages."*

| Gate clause | Where it is answered | Outcome |
| --- | --- | --- |
| Identify generated/fallback series; exclude them from empirical claims | Structural screen for two fill patterns across all eight series (`fallbackAudit.signatures`), the two flagged series designated `audit-only` (`associations.series.<name>.designation`), exclusion recorded as a rule (`fallbackAudit.exclusionRule`) and quantified (`associations.soraFallbackContrast`) | `sora_rates` and `wage_growth` screened as ramp/tiling patterns and excluded from every edition-facing figure — a screen, not a provenance finding; this edition is not a labelled simulation |
| Document release lag, revisions, missing periods, stationarity and uncertainty | Release lag and revisions recorded as `notMeasurable` (`notMeasurable.releaseLag`, `notMeasurable.revisions`, `vintageAudit`); missing periods counted per series (`seriesInventory`); ADF in levels (`stationarity`); both interval variants on every pair (`associations.intervalCaveat`) | documented, two of five items documented as unmeasurable rather than approximated |
| No present-day timing regime claims from unknown source vintages | No regime, policy-date or lag-order claim appears in this edition; each is recorded `notMeasurable`/`notFitted` with its reason (`notMeasurable.regimes`, `notMeasurable.policyDates`, `notMeasurable.lagTesting`) | satisfied by absence of such claims |

## What the numbers in this edition are — and are not

Targets (`associations.targetDefinition`): **HDB resale median psf** (median resale price per square foot) and **HDB resale transaction count per month**, measured from `unified_dataset` and aggregated to each macro series' own frequency (monthly series: the month; quarterly series: the calendar quarter). Every association figure is same-period — no lag is applied anywhere (`notMeasurable.lagTesting`).

Three reading rules bind this edition (`associations.readingRules`): level figures are what the legacy article read, and two trending series correlate by construction, so a level coefficient is not evidence of sensitivity; the first-difference figures are the defensible statistic for the same pairs; no coefficient is a causal effect and none is a forecast.

**Units.** The ledger records no unit field. Its own prose states percent for the SORA series (`fallbackAudit.longSeriesVerdict` records a "3.19% mean in 2006"); `cpi`, `hdb_rpi` and `ura_ppi` are index levels (the `hdbResalePriceIndex` block records `firstIndex` 24.3 → `lastIndex` 202.5); `gdp`, `unemployment_rate` and `wage_growth` are reported below as recorded ranges only, with no unit asserted.

**Uncertainty.** Every interval quoted here is the **serial-adjusted** one (`pearsonCi95SerialAdjusted`) — the honest variant: the plain Fisher-z interval treats observations as independent, which time-series observations are not (`associations.intervalCaveat`). The adjusted form recomputes the interval at an AR(1) effective n = n(1 − ρx·ρy)/(1 + ρx·ρy), with the **product** of both sides' lag-1 autocorrelations entering the formula; the effective n is clamped to [4, n] **before** the interval is recomputed, which makes the adjustment asymmetric (`associations.intervalCaveat`). A **positive** product shrinks the effective n and widens the interval. A **negative** product does **not** narrow it: the raw effective n rises above the row count, the clamp returns n, and the adjusted interval is therefore unchanged from the unadjusted one — never narrower. The floor of 4 binds for the five level pairs whose housing side is near-integrated (`bank_rates`, `cpi`, `hdb_rpi`, `ura_ppi`, `sora_rates`): those pairs carry roughly four independent observations, which is a statement about information, not a promise of width.

**No chronology claim.** The measurement design is recorded in this ledger and its producer, with no dated prior protocol in this checkout, so specification search cannot be ruled out.

## The eight series: inventory and the three states of absence

All eight bronze macro series (`seriesInventory`; value ranges in source units). A **null value** (the period row exists, its value does not — missing-source), an **absent period** (no row at all), and a **recorded zero** are counted separately (`seriesInventory.<series>.semantics`) and are not interchangeable anywhere in this edition:

| Series (value column) | Unit as recorded | File rows | Rows with a value | Value span | Missing-source rows | Absent periods | Recorded zeros | Distinct values | Min–max |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| `bank_rates` (`sora_3m`) | percent (`longSeriesVerdict`) | 465 | 252 | 2005-10 → 2026-09 | 213 (1988-01 → 2005-09) | 0 | 0 | 245 | 0.0362 – 3.7527 |
| `sora_rates` (`sora_rate`) | percent (`longSeriesVerdict`) | 60 | 60 | 2021-01 → 2025-12 | 0 | 0 | 0 | 55 | 0.155 – 1.235 |
| `cpi` | index level | 789 | 789 | 1961-01 → 2026-09 | 0 | 0 | 0 | 780 | 20.655 – 103.551 |
| `gdp` | unlabelled in ledger | 202 | 202 | 1976Q1 → 2026Q2 | 0 | 0 | 0 | 109 | −11.7 – 18.9 |
| `hdb_rpi` | index level | 147 | 147 | 1990Q1 → 2026Q3 | 0 | 0 | 0 | 133 | 24.3 – 203.7 |
| `unemployment` | unlabelled in ledger | 139 | 139 | 1992Q1 → 2026Q3 | 0 | 0 | 0 | 31 | 1.0 – 4.5 |
| `ura_ppi` | index level | 207 | 207 | 1975Q1 → 2026Q3 | 0 | 0 | 0 | 177 | 8.9 – 222.5 |
| `wage_growth` | unlabelled in ledger | 100 | 100 | 2001Q1 → 2025Q4 | 0 | 0 | 0 | 19 | −2.6 – 6.8 |

Two facts change measurements:

- **`bank_rates` holds 465 file rows of which 252 carry a value.** The other **213 rows are missing-source**, spanning 1988-01 → 2005-09 — the period exists, the `sora_3m` value does not. It is not zero and not an absent period. The usable series span begins **2005-10** and runs to 2026-09; any statement that SORA observations run from 1988 describes the file's rows, not the series (`seriesInventory.bank_rates`).
- **No series has an interior gap.** Absent periods are 0 and recorded zeros are 0 for all eight; the differences between series are start and end dates, not holes (`seriesInventory`).

## Screened fill patterns: two series excluded, and the cost of excluding them measured

The legacy text states in its own conclusion that collection *"The macro data collection relies on SingStat API with fallback to generated data when API calls fail."* — so fallback behaviour was claimed by the old analysis. That quotation does **not** establish which shipped series, if any, it produced; what this edition can do is screen every series for a fill signature and report what the screen found. It answers structurally, not anecdotally, and it does not certify any series' origin.

### The structural screen (`fallbackAudit.signatures`)

Two fill patterns are measurable without provenance — **annual-resolution tiling** (each year carries one distinct value repeated across its periods) and an **annual ramp** (most variance between years, larger steps on year boundaries, monotone year-mean path):

| Series | Between-year variance share | Year-boundary step share | Monotone year-mean path | Tiled years | Screen result |
| --- | ---: | ---: | --- | ---: | --- |
| **`wage_growth`** | 1.0 | — (quarterly) | no | 25 of 25 (share 1.0) | **`annual-resolution-tiling-signature`** |
| **`sora_rates`** | 0.9939 | 0.3444 | **yes** | 0 of 5 | **`annual-ramp-signature`** |
| `bank_rates` | 0.9324 | 0.0945 | no | 0 of 22 | `no-fallback-signature-detected` |
| `cpi` | 0.9992 | 0.0939 | no | 0 of 66 | `no-fallback-signature-detected` |
| `hdb_rpi` | 0.9952 | — | no | 0 of 37 | `no-fallback-signature-detected` |
| `ura_ppi` | 0.9961 | — | no | 0 of 52 | `no-fallback-signature-detected` |
| `gdp` | 0.7547 | — | no | 0 of 51 | `no-fallback-signature-detected` |
| `unemployment` | 0.5722 | — | no | 0 of 35 | `no-fallback-signature-detected` |

What separates `sora_rates` is not the high between-year share alone — a trending index looks like that too — but the **0.3444 year-boundary step share** (4 boundaries carrying that share of all movement, against 0.0939/0.0945 for the two monthly trending series) **plus** a monotone year-mean path (`fallbackAudit.signatures.sora_rates.caveat`: "that is a screen for a generated ramp, not provenance proof, and the series is excluded from empirical claims on this evidence rather than on a certified statement about its origin"). What separates `wage_growth` is that every one of its 25 years holds exactly one distinct value across four quarterly rows, so its 100 rows carry 19 distinct values (`fallbackAudit.signatures.wage_growth.caveat`: "this is a screen for a fill pattern, not a statement about who produced the file"). For the six unflagged series the screen result means only that neither positive pattern was detected — it is not certification, and no series here carries a release or vintage stamp (`fallbackAudit.signatures.bank_rates.caveat`).

**Exclusion rule, inherited by this edition** (`fallbackAudit.exclusionRule`): no edition-facing claim may rest on `sora_rates` — every edition-facing SORA figure is measured from `bank_rates.sora_3m`. The ledger still records `sora_rates`-derived numbers on purpose, to quantify what the exclusion costs, and those three blocks (`fallbackAudit.soraYearMeans`, `fallbackAudit.soraConfrontation` and `associations.soraFallbackContrast`) each carry an explicit `designation: audit-only`, so none of them can be mistaken for an edition-facing figure. `sora_rates` is likewise `audit-only` at its association entry (`associations.series.sora_rates.designation`), and its numbers appear here only inside that quantified cost comparison, never as evidence. `wage_growth` carries the same designation (`associations.series.wage_growth.designation`), but the ledger holds **no exclusion-cost comparison for it** — so **no `wage_growth` figure is reproduced in this edition at all**; only its screen result appears, and nothing licenses its coefficients to be quoted merely by labelling them.

### The article's four rate bands, measured on the source series (`fallbackAudit.soraBandCheck`)

| Legacy band (verbatim) | Measured window | Months | Mean | Min | Max | Reproduces? |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| "0.1-0.2%" | 2021-01 → 2021-06 | 6 | 0.1796 | 0.1326 | 0.2216 | mean inside the band |
| "2.5-3.5%" | 2022-07 → 2022-12 | 6 | 2.2247 | 1.2712 | 3.0294 | **no** — mean below the band |
| "3.5-4.0%" | 2023-01 → 2023-12 | 12 | 3.5915 | 3.1419 | 3.7527 | mean inside the band |
| "3.0-3.5%" | 2024-01 → 2025-12 | 24 | 2.739 | 1.1857 | 3.6829 | **no** — mean below the band |
| (source-span variant) | 2024-01 → 2026-08 | 32 | 2.3303 | 1.0298 | 3.6829 | recorded separately, `soraBandCheck.sourceSpan2024to2026Aug` |

All values from `bank_rates.sora_3m` — the excluded series is not used. Two of the four bands reproduce as descriptions of the source series' mean; two sit below their quoted band. The 2024-2025 row is measured over the claim's own 24-month window; the source series' longer 2024-01 → 2026-08 span answers a different question and is recorded beside it (`legacyClaims` C15 note).

### The two candidates on their shared months (`fallbackAudit.soraConfrontation`, `soraYearMeans`)

On the **60 months they share (2021-01 → 2025-12)**:

| Year | `sora_rates` year mean (ramp) | `bank_rates` year mean (source) | Ratio long : short |
| --- | ---: | ---: | ---: |
| 2021 | 0.1953 | 0.1648 | 0.8441 |
| 2022 | 0.2914 | 1.3085 | 4.4902 |
| 2023 | 0.4957 | 3.5915 | 7.2459 |
| 2024 | 0.8037 | 3.5213 | 4.3811 |
| 2025 | 1.1953 | 1.9568 | 1.6371 |

Across the overlap: Pearson r 0.4067 between the two candidates, mean difference (short − long) −1.5123, maximum absolute difference 3.2704 (`soraConfrontation`). In 2023 the two series claiming to measure the same rate differ by a factor of 7.2459 (`soraYearMeans.years.2023.ratioLongToShort`). The rate band above — "3.5-4.0%" through 2023 — is reproducible from `bank_rates` (2023 mean 3.5915) and not from `sora_rates` (2023 mean 0.4957): the article's own narrative selects the source series, which is the screen's conclusion as well (`fallbackAudit.longSeriesVerdict`, `fallbackAudit.shortSeriesVerdict`).

### The gold-column trap (`goldColumnLineage`)

Both candidates ship into the gold layer as **separate columns**, each reproducing its bronze source exactly:

| Gold column | Reproduced by | Exact-month equality | Months compared | Null month-rows in gold | Distinct values |
| --- | --- | ---: | ---: | ---: | ---: |
| `sora_rate` | `sora_rates` (the ramp) | 1.0 | 60 | 383 | 55 |
| `sora_3m` | `bank_rates` (source candidate) | 1.0 | 252 | 191 | 245 |

(`goldColumnLineage.columns`; the other six columns reproduce their single sources at 1.0 as well.) The conclusion is recorded verbatim in the ledger: "gold carries both SORA candidates as separate columns; sora_rate reproduces sora_rates (1.0) and sora_3m reproduces bank_rates (1.0), so a query that picks the wrong column picks the screened-out series". The wrong column is one query away — and the friendlier name belongs to the excluded series.

### What the exclusion costs (`associations.soraFallbackContrast`)

Same 60 months, same target (monthly HDB resale median psf), both series:

| Statistic | `sora_rates` (ramp, audit-only) | `bank_rates.sora_3m` (source, measured) |
| --- | ---: | ---: |
| Levels: Pearson r, n = 60 | **0.9422** | **0.587** |
| Levels: serial-adjusted 95% CI | −0.2002 → 0.9988 | −0.8583 → 0.9897 |
| Levels: effective n | 4.0 | 4.0 |
| First differences: Pearson r, n = 59 | 0.0646 | 0.1445 |
| First differences: serial-adjusted 95% CI | −0.2067 → 0.3267 | −0.1159 → 0.3863 |

The level coefficient is 0.9422 where the ramp is used and 0.587 where the source series is used — the measured price of picking the wrong column. Neither level figure is evidence of anything: both adjusted intervals span nearly all of [−1, 1] at effective n 4.0. In first differences both collapse (0.0646 and 0.1445, intervals spanning zero). Over its full populated window the source series' level coefficient is 0.1014 (n = 252, 2005-10 → 2026-09, serial-adjusted CI −0.9525 → 0.9681 — `associations.series.bank_rates.levels.macroVsMedianPsf`).

## Stationarity and the level-versus-difference distinction (`stationarity`)

Augmented Dickey-Fuller on levels, constant only, AIC lag selection, one specification (`stationarity.caveat`: no trend term, no seasonal adjustment, no break test; monthly series tested unadjusted):

| Series | ADF statistic | p-value | Lags used | n | Rejects unit root at 5% |
| --- | ---: | ---: | ---: | ---: | --- |
| `gdp` | −3.4891 | 0.008271 | 8 | 193 | yes |
| `bank_rates` | −3.2502 | 0.017254 | 10 | 241 | yes |
| `unemployment` | −2.0353 | 0.271329 | 13 | 125 | no |
| `hdb_rpi` | −1.0193 | 0.746169 | 10 | 136 | no |
| `ura_ppi` | 0.0084 | 0.959223 | 2 | 204 | no |
| `cpi` | 0.6075 | 0.987799 | 21 | 767 | no |
| **`sora_rates`** | 5.1628 | 1.0 | 11 | 48 | no |

(`stationarity.series.<name>`; critical values per series in the ledger.) The reading the ledger records (`stationarity.interpretation`) is deliberately narrow: failing to reject the unit-root null is not evidence that a series is non-stationary — ADF is low-powered — but six of the eight series have no rejected unit root in levels, so a level correlation between them and housing cannot be read as sensitivity, and the first-difference figures are reported for that reason. `sora_rates` returns a **positive** ADF statistic with p = 1.0, the least stationary result in the set — consistent with the annual ramp above, though it does not by itself establish how the file was produced (`stationarity.soraNote`). Neither reading is causal.

## Measured associations (`associations`)

Six series passed the screen and are designated `measured`. `sora_rates` appears as an `audit-only` row because the ledger quantifies what excluding it costs (`associations.soraFallbackContrast`); **`wage_growth` is not tabulated at all** — the ledger holds no exclusion-cost comparison for it, and an `audit-only` label licenses a figure only as such a comparison. Windows are each series' own; n is the paired month/quarter count; intervals are serial-adjusted (`pearsonCi95SerialAdjusted`).

**First differences — the defensible statistic:**

| Series (designation) | Window | n | Pearson r vs Δ median psf | Serial-adjusted 95% CI | Effective n | Pearson r vs Δ volume |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| `bank_rates` (measured) | 2005-10 → 2026-09 | 251 | −0.0198 | −0.144 → 0.105 | 248.3 | 0.0668 |
| `cpi` (measured) | 1990-01 → 2026-09 | 440 | 0.1496 | 0.0569 → 0.2397 | 440.0 | −0.1771 |
| `gdp` (measured) | 1990Q1 → 2026Q2 | 145 | 0.1174 | −0.0513 → 0.2796 | 137.0 | 0.0777 |
| `hdb_rpi` (measured) | 1990Q1 → 2026Q3 | 146 | 0.9236 | 0.8497 → 0.9619 | 32.8 | −0.075 |
| `unemployment` (measured) | 1992Q1 → 2026Q3 | 138 | −0.0539 | −0.219 → 0.1143 | 138.0 | 0.048 |
| `ura_ppi` (measured) | 1990Q1 → 2026Q3 | 146 | 0.4965 | 0.241 → 0.6877 | 46.0 | −0.1013 |
| `sora_rates` (**audit-only**) | 2021-01 → 2025-12 | 59 | 0.0646 | −0.2067 → 0.3267 | 53.5 | 0.3285 |

**Levels — what the legacy article read (not sensitivity):**

| Series (designation) | n | Pearson r vs median psf | Serial-adjusted 95% CI | Effective n | Pearson r vs volume |
| --- | ---: | ---: | --- | ---: | ---: |
| `bank_rates` (measured) | 252 | 0.1014 | −0.9525 → 0.9681 | 4.0 | 0.2394 |
| `cpi` (measured) | 441 | 0.9713 | 0.1543 → 0.9994 | 4.0 | −0.1803 |
| `gdp` (measured) | 146 | −0.2636 | −0.6167 → 0.1777 | 22.1 | −0.0686 |
| `hdb_rpi` (measured) | 147 | 0.9991 | 0.9535 → 1.0 | 4.0 | −0.0743 |
| `unemployment` (measured) | 139 | −0.186 | −0.4368 → 0.0915 | 52.0 | 0.2927 |
| `ura_ppi` (measured) | 147 | 0.9697 | 0.1271 → 0.9994 | 4.0 | −0.0924 |
| `sora_rates` (**audit-only**) | 60 | 0.9422 | −0.2002 → 0.9988 | 4.0 | −0.2617 |

(`associations.series.<name>.firstDifferences.dMacroVsDMedianPsf` / `.dMacroVsDVolume` and `.levels.macroVsMedianPsf` / `.macroVsVolume`; Spearman coefficients and the unadjusted intervals are beside each pair in the ledger.)

What these figures carry, stated descriptively: the level column is trend-dominated by construction — `hdb_rpi` at 0.9991 is a price index against a price aggregate, and `cpi` (0.9713) and `ura_ppi` (0.9697) sit in the same register, all at effective n 4.0. In first differences the macro series proper sit between −0.0539 and 0.1496 against median psf and between −0.1771 and 0.0777 against volume; the two larger difference coefficients, `hdb_rpi` (0.9236) and `ura_ppi` (0.4965), are property price indices measured against a housing price aggregate. Nothing in this table reproduces the legacy article's qualitative labels or any lag order (`notMeasurable.lagTesting`: "every association figure in this ledger is same-period, not lagged").

## Real returns at the windows the ledger measured (`realReturns`)

| Measure | Window | n | Value |
| --- | --- | ---: | --- |
| HDB median psf, nominal CAGR | 1990-01 → 2026-10 | 36.75 years | 0.0624 (6.24%/yr) |
| HDB median psf, first → last | 1990-01 → 2026-10 | 989,865 transactions | 64.93 → 600.77 psf |
| HDB median psf, CPI-deflated CAGR | 1990-01 → 2026-09 | 36.667 years | 0.0433 (4.33%/yr) |
| HDB resale price index, nominal CAGR | 1990Q1 → 2026Q3 | 147 quarters | 0.0598 (5.98%/yr) |
| HDB resale price index, first → last | 1990Q1 → 2026Q3 | 147 quarters | 24.3 → 202.5 |
| Article's own window, median psf nominal CAGR | 2021-01 → 2026-10 | 70 months | 0.0601 (6.01%/yr) |
| Article's own window, price index nominal CAGR | 2021Q1 → 2026Q3 | 23 quarters | 0.0664 (6.64%/yr) |

(`realReturns.hdbMedianPsf`, `realReturns.hdbResalePriceIndex`, `realReturns.articleWindow2021To2026`.) Two disclosures bind this table. The deflated CAGR runs over **its own** window — the CPI series' last observed month is 2026-09, one month before the transaction cutoff — hence 36.667 years rather than the nominal 36.75, and its window is reported rather than extrapolated (`realReturns.hdbMedianPsf.cpiDeflationNote`). And the median is not a constant-quality index: the mix of towns, flat types and lease bands behind the monthly median changes across the window, so the figure describes the median's path; the `hdb_rpi` row is the constant-quality alternative on a different window (`realReturns.hdbMedianPsf.compositionCaveat`). On the article's own window the two available series re-measure at 0.0601 and 0.0664 — outside the quoted "~4-5%" band (see Superseded figures, C21). The four-segment nominal/real CAGR table cannot be re-derived: no segment-level price index exists here and the private source begins 2021-01 in the shipped frame (`realReturns.segmentsNotReproducible`, `notMeasurable.segmentCagr`).

## Release lag, revisions, and what is not measurable

No bronze macro file carries a release timestamp, extraction stamp or revision history — the only parquet metadata keys on all eight files are `ARROW:schema` and `pandas` — and no housing-policy-date artefact exists in the checkout (`vintageAudit`: `releaseOrVintageStampsFound: 0`, `releaseLagMeasurable: false`, `revisionHistoryMeasurable: false`, `policyDateArtefactFound: false`, `policyDateArtefactCandidates: []`). The gate's "document release lag, revisions" is therefore answered by measuring the absence, not by approximating it:

| Item | Status | Recorded reason |
| --- | --- | --- |
| Release lag | `notMeasurable` | no release timestamp or extraction stamp on any series, so the publication-to-observation lag is unrecoverable (`notMeasurable.releaseLag`) |
| Revisions | `notMeasurable` | one file per series, no vintage snapshots; published-versus-revised values cannot be compared (`notMeasurable.revisions`) |
| Policy dates | `notMeasurable` | the five-row policy table rests on `housing_policy_dates.parquet`, absent here; the article's policy dates also disagree with the causal-inference article's, and neither has an artefact (`notMeasurable.policyDates`) |
| Regimes | `notFitted` | the three-regime table is analyst-chosen period boundaries; no break-test implementation exists on the shipping Python surface and none was run (`notMeasurable.regimes`) |
| Lag orders | `notMeasurable` | no cross-correlation or lead-lag implementation exists there and this study ran none; every association figure is same-period (`notMeasurable.lagTesting`) |
| Affordability model | `notMeasurable` | a static export-time lookup **does** exist — `scripts/export_app_data.py` implements a fixed-assumption monthly mortgage payment (20% down, 3.5% interest, 25-year term) and bands price-to-income and mortgage-to-income against a flat national median household income; what does not exist is anything a rate-shock or borrower-specific claim could rest on: no rate sensitivity, no borrower eligibility test, no TDSR/MSR assessment (`notMeasurable.affordabilityModel`) |
| Segment CAGRs | `notMeasurable` | no segment-level price index in the checkout (`notMeasurable.segmentCagr`) |

## Superseded figures

Every registered claim in the old text, its status, and the measured reason. Quoted phrases are verbatim from [`legacy/2026-11-12/macro-sensitivity.md`](../../legacy/2026-11-12/macro-sensitivity.md), each machine-checked against the frozen file (`legacyQuoteCheck`: 35 of 35 found, `allQuotesFound: true`). Every claim's ledger key resolves against this ledger at build time (`claimKeyCheck`: 35 claims, 0 unresolved — resolution is syntactic and does not judge whether the resolved field supports the disposition). Statuses are the ledger's own (`legacyClaims.<id>.status`): **re-measured** means the claim was answered with a measurement of this checkout; it does not mean reproduced — three of the seven re-measured claims (C14, C15, C21) fall outside their quoted value.

| Legacy claim (as the old text states it) | Status | Measured reason |
| --- | --- | --- |
| "Interest rates (SORA) have the most direct impact on affordability" | withdrawn | a conditional correlation is not an affordability measure; the ledger records the association (r = −0.0198, n = 251 — `associations.series.bank_rates.firstDifferences.dMacroVsDMedianPsf`) and nothing beyond it |
| "This confirms that interest rates are the most actionable macro indicator for housing decisions." | withdrawn | the wording claims proof for a descriptive correlation and ranks indicators; the ledger records no ranking (`associations.readingRules`) |
| "3.5-4.0%" | re-measured | 2023 mean 3.5915, min 3.1419, max 3.7527 on `bank_rates.sora_3m` (`fallbackAudit.soraBandCheck.2023`) — mean inside the band; the excluded series gives 2023 a year mean of 0.4957 (`fallbackAudit.soraYearMeans.years.2023`) |
| "The macro data collection relies on SingStat API with fallback to generated data when API calls fail." | re-measured | the article names a fallback; the screen flags `sora_rates` as carrying the annual-ramp pattern (`fallbackAudit.signatures.sora_rates.screen`) without certifying its origin, and the series is excluded (`fallbackAudit.exclusionRule`) |
| "GDP growth is a leading indicator for transaction volume more than price level" | withdrawn | a timing claim; no lead-lag implementation exists and none was run (`notMeasurable.lagTesting`) — the same-period figures are r = 0.0777 vs Δvolume and 0.1174 vs Δpsf (`associations.series.gdp`) |
| "Unemployment is a lagging indicator that confirms weakness rather than predicting it." | withdrawn | the ordering is not measured; no lag test was run (`notMeasurable.lagTesting`) |
| "are identifiable in the 2021-2026 data: expansion, tightening, stabilization" | withdrawn | chosen period boundaries, not tested breaks; no break-test implementation exists and none was run (`notMeasurable.regimes`) |
| "is approximately 2% across all segments" | withdrawn | only the HDB rows are measurable; no segment price index exists here (`realReturns.segmentsNotReproducible`) |
| "60 monthly observations (2021-2025)" | re-measured | the count and span are correct and belong to the screened-out annual-ramp series (`seriesInventory.sora_rates`, 60 rows, all populated). The source candidate is not a 465-observation series: **465 file rows**, of which **213 are missing-source (1988-01 → 2005-09)** and **252 carry a value from 2005-10** — usable span 2005-10 → 2026-09 (`seriesInventory.bank_rates`) |
| "5 major policy events (2021-2023)" | withdrawn | the artefact behind the count is absent from this checkout (`notMeasurable.policyDates`; `vintageAudit.policyDateArtefactFound: false`) |
| "Visual and statistical identification of distinct macro periods" | withdrawn | no statistical identification exists here; the regimes are visual choices (`notMeasurable.regimes`) |
| "the 5-year macro data window covers only one full rate cycle, limiting generalizability" | withdrawn | the one-cycle window describes the excluded 60-row series; the source series' populated span is 2005-10 → 2026-09 (`seriesInventory.bank_rates`) |
| "0.1-0.2%" | re-measured | 2021 H1 mean 0.1796, min 0.1326, max 0.2216 over 6 months (`fallbackAudit.soraBandCheck.2021H1`) |
| "2.5-3.5%" | re-measured | 2022 H2 mean 2.2247, min 1.2712, max 3.0294 over 6 months (`fallbackAudit.soraBandCheck.2022H2`) — mean below the band |
| "3.0-3.5%" | re-measured | 2024-01 → 2025-12 mean 2.739, min 1.1857, max 3.6829 over 24 months (`fallbackAudit.soraBandCheck.2024to2025`) — mean below the band; the source-span variant over 2024-01 → 2026-08 gives mean 2.3303 |
| "21 quarterly observations (2021-2026)" | withdrawn | the shipped quarterly series are far longer — `gdp` 202 rows from 1976Q1, `ura_ppi` 207 from 1975Q1 (`seriesInventory`) |
| "1-2 quarters" | withdrawn | a lag order; none is measured (`notMeasurable.lagTesting`) |
| "rates +1%" | withdrawn | a borrower stress scenario offered as advice; the shipped affordability lookup is static and implements no rate sensitivity (`notMeasurable.affordabilityModel`) |
| "2021 - mid-2022" | withdrawn | a chosen regime boundary, not a tested break (`notMeasurable.regimes`) |
| "Mid-2022 - 2023" | withdrawn | a chosen regime boundary, not a tested break (`notMeasurable.regimes`) |
| "~4-5%" | re-measured | on the article's own window the two measurable series give 0.0601 (median psf, 70 months) and 0.0664 (price index, 23 quarters) — outside the quoted band (`realReturns.articleWindow2021To2026`) |
| "~5-6%" | withdrawn | a mass-market condo CAGR; no segment price index exists (`realReturns.segmentsNotReproducible`) |
| "~3-5%" | withdrawn | a premium condo CAGR; same reason |
| "~2-4%" | withdrawn | a luxury condo CAGR; same reason |
| "2021-2026 (macro data), 2017-2026 (housing data)" | withdrawn | the shipped transaction frame begins 1990-01 and each series carries its own measured span (`seriesInventory`, `realReturns`) |
| "Immediate to 1 quarter" | withdrawn | a lag order; none is measured (`notMeasurable.lagTesting`) |
| "A 1% rate difference on a large loan" | withdrawn | a borrower illustration offered as advice; no borrower eligibility or financing assessment is measured (`notMeasurable.affordabilityModel`) |
| "Dec 2021" · "Sep 2022" · "Apr 2023" · "Dec 2023" | withdrawn | the policy-date artefact is absent (`vintageAudit.policyDateArtefactFound: false`); the dates also disagree with the causal-inference article's and neither has an artefact (`notMeasurable.policyDates`) |
| "2024-2026" | withdrawn | the stabilization regime's declared window — a chosen boundary (`notMeasurable.regimes`) |
| "1-quarter lag with price trends" | withdrawn | a lag order; none is measured (`notMeasurable.lagTesting`) |
| "data/04_platinum/housing_unified.parquet" | withdrawn | the named path is absent from this checkout; the shipped frame is `data/pipeline/04_platinum/unified_dataset.parquet`, sha-pinned (`inputs`) |
| "data/raw_data/macro/" | withdrawn | the named directory is absent; the shipped series live in `data/pipeline/01_bronze/external/`, each sha-pinned (`inputs`) |

## What this edition does not establish

- **No causal claim.** No coefficient here is a causal effect and none is a forecast (`associations.readingRules`). No sentence of this edition's own findings attributes a price or volume difference to a macro series; the superseded-figures table below does reproduce legacy sentences that make such attributions, each marked withdrawn.
- **No timing, lag-order or regime claim.** Every association figure is same-period; the regime boundaries and the policy dates are unmeasured and unfitted (`notMeasurable.lagTesting`, `notMeasurable.regimes`, `notMeasurable.policyDates`). No unquoted, unwithdrawn timing, lag-order or regime claim appears in this edition; the only such sentences are verbatim legacy quotations in the superseded-figures table, marked withdrawn.
- **No level-coefficient sensitivity reading.** Level figures are reported because the legacy article read them; six of eight series have no rejected unit root in levels and the five near-integrated pairs carry effective n 4.0 (`stationarity`, `associations.intervalCaveat`).
- **No empirical claim resting on `sora_rates` or `wage_growth`.** `sora_rates` appears only inside the quantified exclusion-cost comparison; `wage_growth`'s figures are not reproduced at all. Both carry the `audit-only` designation (`associations.series.<name>.designation`), and neither is a labelled simulation, so the gate's simulation clause does not apply to them.
- **No provenance certification.** `no-fallback-signature-detected` records only that neither fill pattern was detected; no series carries a release or vintage stamp (`fallbackAudit.signatures.<series>.caveat`, `vintageAudit`), so none is certified as a primary release here.
- **No release-lag or revision statement.** Both are `notMeasurable` in this checkout — measured absences, not zeros.
- **No segment return comparison.** Only the HDB rows of the legacy CAGR table are measurable; the condo rows are withdrawn (`realReturns.segmentsNotReproducible`).
- **No rate-sensitivity, eligibility or TDSR/MSR measurement.** A static export-time affordability lookup exists (`scripts/export_app_data.py`, fixed 20% down / 3.5% / 25-year assumptions against a flat national median household income), but no rate sensitivity, borrower eligibility test or TDSR/MSR assessment is implemented; the stress-scenario claims are withdrawn for that narrower reason, not on the false ground that no affordability code exists (`notMeasurable.affordabilityModel`).
- **No present-day claim from an unknown source vintage** — the gate's third clause, satisfied by the absence of every timing claim.
- **No pre-emptive protocol claim.** The design is recorded, with no dated prior protocol in this checkout, so specification search cannot be ruled out.
- **No completeness claim beyond scope.** What was measured is the provenance screening of the eight bronze macro series, the two-SORA conflict the fill screen surfaced, gold-column lineage, ADF stationarity in levels, and the legacy correlation claims re-measured at the macro frequency in levels and first differences (`scope`) — nothing outside that surface is asserted.

## Reading this edition

- **Investors:** the only rate series behind any figure here is `bank_rates.sora_3m`, populated 2005-10 → 2026-09; the 60-row series the old article used is **screened as an annual-ramp pattern** — its origin remains unverified, since a structural screen is not provenance — and it is excluded from every edition-facing figure. In first differences the source series' coefficient against monthly median psf is −0.0198 (n = 251, serial-adjusted CI −0.144 → 0.105).
- **First-time buyers:** the affordability and stress-scenario guidance in the old text is withdrawn, not softened — the shipped affordability lookup is static (fixed 20% down / 3.5% / 25-year assumptions) and implements no rate sensitivity or eligibility test (`notMeasurable.affordabilityModel`). What is measured: HDB median psf re-measures at 0.0601 (6.01%/yr) over the article's own 2021-01 → 2026-10 window and 0.0433 (4.33%/yr) CPI-deflated over 1990-01 → 2026-09 — descriptive paths, with the median-composition caveat attached.
- **Upgraders:** the regime table, the policy-date table and every lag column are unmeasured here; the old text's strategy guidance rested on them and is withdrawn with that reason.

## Data and inputs (`inputs`, sha256-pinned)

| Path | Rows / lines | sha256 |
| --- | ---: | --- |
| `data/pipeline/01_bronze/external/bank_rates.parquet` | 465 | `9a4327bb154d70768f7fa7bd370d46638d65be5fd907e5e52623248fe98f176a` |
| `data/pipeline/01_bronze/external/cpi.parquet` | 789 | `ae065cecd81bd776a70da5af67949df79e2e451f588a9eb3994e90dd9f0ccc04` |
| `data/pipeline/01_bronze/external/gdp.parquet` | 202 | `b43fb19211da5c842943da948f1adbaac137ba2b15b04ca39e66496b064ac3d0` |
| `data/pipeline/01_bronze/external/hdb_rpi.parquet` | 147 | `57ddf2ae983e5f3798899fac2888b27e58c5e866c0ce88e44681dc4b9a4a8c4c` |
| `data/pipeline/01_bronze/external/sora_rates.parquet` | 60 | `c0323795d4e26023d03eec73d4a146565b301f9bdfbc4f5fd5a895a060201316` |
| `data/pipeline/01_bronze/external/unemployment.parquet` | 139 | `78b8cbbf55be52eba1891ea7b655ff4dc80b0ee0750eb986c6828a6d7d3ae260` |
| `data/pipeline/01_bronze/external/ura_ppi.parquet` | 207 | `a73cd16354629494e9c02da5c92251c2beff028eebad8c573e63210b34ed91b6` |
| `data/pipeline/01_bronze/external/wage_growth.parquet` | 100 | `2a47a4953ab2ee5188b46d6af83fcb0e0edbae725c4ca84641b7dcdca2bbe1a6` |
| `data/pipeline/04_platinum/unified_dataset.parquet` | 1,236,310 | `39d234f703c9d6e098acc885eaadfdc965a6ac217189277c066676b3b117cefe` |
| `docs/analytics/editions/legacy/2026-11-12/macro-sensitivity.md` | 157 | `8af923420706a072c1b8e6287b4d54b70bdfbad3afcd65dce1a9e7cce41a7a88` |

## Provenance

Prepared by `repo-agent/session-2026-11-18` as a **draft awaiting review**; its evidence status is `historical` and its editorial status is `draft`. Under the refresh rules (D12), the owner's and an independent reviewer's records are entered by them, never by the preparer — this document asserts no such record. Evidence pack: [RS09 macro-sensitivity evidence](../../../../implementation/2026-11-18-rs09-macro-sensitivity-evidence.md); ledger: [`artifacts/rs09-macro-sensitivity-evidence.json`](../../../../implementation/artifacts/rs09-macro-sensitivity-evidence.json) (sha256 `ae403f11db8786e4258418d8791c6e0255fe2f4800d32e624f4014b6af629d7b`, 96,351 bytes), reproducible with `uv run python scripts/tools/macro_sensitivity_evidence.py --check`. The producer measures this checkout only — it never runs the pipeline, never fits the legacy models, and never re-derives a housing aggregate past the 2026-10 cutoff.
