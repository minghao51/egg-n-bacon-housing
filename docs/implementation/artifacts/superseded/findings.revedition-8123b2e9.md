---
title: "Key investment findings: a measured register of the fifteen series"
category: "technical-reports"
description: "A register of the fifteen housing-analysis series: which editions are signed, what each one owns, and what a summary page cannot say."
status: draft
date: 2026-11-20
personas: [first-time-buyer, investor, upgrader]
readingTime: "12 min read"
technicalLevel: intermediate
---

# Key investment findings: a measured register of the fifteen series

Edition id: `findings/2026-11-20` · Measured date: 2026-11-20 · Observation cutoff: 2026-10 (`cutoff.lastCompleteMonth`)

This edition supersedes the frozen legacy file `docs/analytics/editions/legacy/2026-11-12/findings.md` (`inputs.docs/analytics/editions/legacy/2026-11-12/findings.md.sha256`). It is not a re-analysis and not a copy of anyone's results. It is a register: for each of the fifteen series it records which edition exists, whether that edition is signed, whether the text and ledger on disk are the bytes the record pins, what that edition says it did with its own claims, and where the evidence stops. Every number below is a field of an evidence ledger, named beside it.

## What this edition can and cannot say

A findings page is the one page in the programme whose subject is the other pages. That is also why it is the page most able to mislead: a summary that repeats a sibling's coefficient inherits every defect that coefficient carries, and it does so without the sibling's stated population, window and unit. So this edition states its own subjects instead — editions, pins, claim dispositions, windows — and points to the edition that owns each substantive measurement rather than restating it.

The consequence is a narrower page than the one it supersedes. The frozen text asserted thirteen analysis domains, a corpus of 911,797 transactions, a set of per-segment forecast accuracies, a policy-effect table and a segment taxonomy. None of those sentences survives here as a finding. Each one is instead named, given the edition that owns it, and disposed by that edition's own ledger record.

## The register in numbers

Every row of this table is one field of the machine-readable ledger. The population, window and unit are stated for each, because a count without them is the defect this page exists to avoid.

| Question | Measured | Population · window · unit | Ledger field |
| --- | --- | --- | --- |
| How many series are registered? | 15 | the series list in `app/src/components/studies/lib/edition-registry.ts` · the registry as measured 2026-11-20 · series | `seriesRegister.summary.seriesCount` |
| How many carry a signed edition? | 14 | those fifteen series · 2026-11-20 · edition | `seriesRegister.summary.signedCount` |
| Which series does not? | `findings` | those fifteen series · 2026-11-20 · series | `seriesRegister.summary.unsignedSeries` |
| Do the frozen texts hash to the pin their entry records? | 14 checked, 14 matched, 0 differed | the fourteen signed editions · the bytes on disk at measurement · frozen text file | `seriesRegister.summary.textPinChecks` |
| Do the ledgers hash to the pin the three attestations share? | 14 matched on canonical content, 14 checked, 13 also matched on raw bytes | the fourteen attestation pin sets · the bytes on disk at measurement · ledger JSON file | `seriesRegister.summary.ledgerPinChecks` |
| How many attestations does a signed edition carry? | 14 with the three roles present, 0 partial, 1 series with none | the fifteen registered editions · as registered · attestation | `seriesRegister.summary.attestationRoleStates` |
| How many ledgers record claim dispositions? | 12 measured, 2 with no claims block, 1 series with no ledger | the fourteen signed editions' ledgers · as each ledger records · ledger | `seriesRegister.summary.claimSplitStates` |
| How many claim items does the `status` vocabulary dispose? | 310 items across 9 ledgers: 63 re-measured, 85 withdrawn, 162 not reproducible | those nine ledgers' own claim items · each ledger's own measured window · claim item | `seriesRegister.summary.claimStatusValues.byStatusKey.status` |
| How many claim items does the separate `disposition` vocabulary dispose? | 74 items across 3 ledgers: 10 superseded, 3 re-cut, 2 re-measured descriptively, 59 withdrawn as not measurable | those three ledgers' own claim items · each ledger's own measured window · claim item | `seriesRegister.summary.claimStatusValues.byStatusKey.disposition` |
| Which last-complete months do the signed ledgers record? | 12 record one: 11 at 2026-10, 1 at 2026-09 | the fourteen signed editions' ledgers · the month each ledger records · ledger | `seriesRegister.summary.ledgerCutoffValues` |
| What is this page's own measured bound? | 2026-10, with the terminal 2026-11 month carrying 421 private transactions, 0.1974 of the trailing-twelve-month median of 2133.0 | the condominium rows of the shipped frame · 1990-01 to 2026-11 as filed, bounded at 2026-10 · transaction month | `cutoff` |
| How large is the shipped frame? | 1,236,310 rows and 97 columns | the shipped `unified_dataset` file · every row it holds · row and column | `inputs.data/pipeline/04_platinum/unified_dataset.parquet` |
| How many files does this ledger hash? | 46 inputs | every file this measurement reads · 2026-11-20 · file | `inputs` |
| How many frozen sentences are quoted verbatim? | 15, all found | the fifteen selected claims · the frozen 2026-11-12 text · sentence | `legacyQuoteCheck` |
| How many dispositions are re-read from the owning ledger? | 13 | the fifteen selected claims · the dependent ledgers as recorded · claim disposition | `crossLedgerCheck` |
| Does a joint model exist for a cross-series ranking? | a bounded scan read 326 files and matched 2 lines | the disclosed scan boundary · this checkout at measurement · file and line | `absenceScans.jointModel` |
| Do any fields this register reads carry placeholder strings? | 0 of the cited fields; 85 ledger-wide, of which 59 sit in one field path of one ledger's per-source acquisition status and 26 in four other studies' ledgers — 22 `notRecorded` status fields and 4 ordinary `none`/`-`/`None` values | the string fields of the fourteen sibling ledgers · as read · field | `sentinelScan.citedFields.matchCount`, `sentinelScan.ledgerWide.split.registerField`, `sentinelScan.ledgerWide.split.otherFields` |

Two of those rows need their limits stated in words rather than numbers. The claim-item totals under `status` and under `disposition` describe different ledgers using different vocabularies, so they are reported apart and are not added together — `seriesRegister.summary.claimStatusValues.meaning`. And the two scan matches are both pool-model notes inside `docs/plans/` for a single study; neither is a model over the series, and the scan's exclusions are listed in the field.

## The fifteen series

Evidence status is the registry's own `evidenceStatus`, rendered in the table below as `signed`: the registry's raw token for that status is carried unchanged in `seriesRegister.rows[].currentEdition.evidenceStatus`, so the rendering is checkable against the record and is not this page's opinion. "Text = pin" is the measured test that caught a stale signature earlier in the programme: the frozen text on disk against the sha256 the entry records. "Ledger = pin" is the same test against the sha256 all three attestations share. A row reading "no" is not smoothed.

| Series | Current edition | Evidence status | Text = pin | Ledger content = pin | Ledger window | Ledger claims |
| --- | --- | --- | --- | --- | --- | --- |
| `data-sources` | `data-sources-2026-11-14` | signed | yes | yes (raw bytes: no) | no `cutoff` block | no `legacyClaims` block |
| `rental-yields` | `rental-yields-2026-11-14` | signed | yes | yes | no `cutoff` block | no `legacyClaims` block |
| `temporal-evolution` | `temporal-evolution-2026-11-15` | signed | yes | yes | 2026-10 | 9 items |
| `amenity-impact` | `amenity-impact-2026-11-16` | signed | yes | yes | 2026-10 | 19 items |
| `facility-premiums` | `facility-premiums-2026-11-17` | signed | yes | yes | 2026-10 | 46 items |
| `macro-sensitivity` | `macro-sensitivity-2026-11-18` | signed | yes | yes | 2026-10 | 35 items |
| `market-segments` | `market-segments-2026-11-20` | signed | yes | yes | 2026-10 | 36 items |
| `price-forecasts` | `price-forecasts-2026-11-20` | signed | yes | yes | 2026-10 | 32 items |
| `lease-decay` | `lease-decay-2026-11-20` | signed | yes | yes | 2026-10 | 36 items |
| `mrt-impact` | `mrt-impact-2026-11-20` | signed | yes | yes | 2026-10 | 28 items |
| `school-quality` | `school-quality-2026-11-20` | signed | yes | yes | 2026-10 | 36 items |
| `spatial-autocorrelation` | `spatial-autocorrelation-2026-11-20` | signed | yes | yes | 2026-10 | 28 items |
| `spatial-hotspots` | `spatial-hotspots-2026-11-20` | signed | yes | yes | 2026-09 | 40 items |
| `causal-inference-overview` | `causal-inference-overview-2026-11-20` | signed | yes | yes | 2026-10 | 39 items |
| `findings` | `legacy-2026-11-12` (this series' only registered edition) | historical | no pin recorded | no ledger | no ledger | no signed edition |

`findings` is the one series without a refreshed edition, and that is why this page is a register rather than a summary of itself: its registered edition is the frozen 2026-11-12 text (`seriesRegister.rows.findings`). Nothing in this edition promotes that frozen text to a current finding, and no figure from it is restated below as a measurement.

### The one row whose bytes moved after its signature

`data-sources` records a real mismatch, and it is disclosed instead of waived. Its ledger's raw sha256 is `21d74a7f…` while the three attestations pin `65ce7a10…`; canonical re-serialisation of the same parsed file reproduces the pin exactly. The recorded reason is a post-signature formatter run that collapsed arrays onto single lines without changing the JSON content — `seriesRegister.rows.data-sources.ledger.serialisationDrift`. The register therefore records two booleans for that row and no third: content matching, bytes not. It does not regenerate another study's signed artefact to make the pair agree, and the producer fails the build if either hash moves from the declared values.

## What each of the frozen sentences became

The frozen page's quantitative sentences are quoted verbatim and traced to the edition that owns each one. For a `referred-*` disposition the producer re-reads the owning ledger at the named claim id and fails the build when the recorded disposition does not match (`crossLedgerCheck`). A disposition says who owns the sentence and what that edition recorded; it validates neither the figure nor the owning edition's reasoning, and it does not carry from one sentence to another.

| Frozen sentence (verbatim) | Disposition | Owning edition and claim |
| --- | --- | --- |
| "**Data Coverage**: 911,797 transactions (2017-2026)" | not measurable as stated: no vintage in this checkout carries that corpus | `notMeasurable.legacyCorpusAggregates` |
| "CBD distance explains **22.6%** of price variation on its own, while adding MRT access increases explanatory power by only **0.78 percentage points**." | ownership transferred; the owning edition records the literals as not reproducible | `mrt-impact` / `hierarchical-r2` |
| "Condo prices are roughly **15x** more MRT-sensitive than HDB prices." | withdrawn by the owning edition as a raw-coefficient multiple | `mrt-impact` / `condo-15x-table` |
| "| 70-80 years | -21.9%              | 47,044       |" | re-measured by the owning edition on its own stated response and window | `lease-decay` / `C4` |
| "| HDB               | 79.8% | 99.4%                | Useful for timing and trend direction |" | withdrawn: no artefact carries the per-segment figures | `price-forecasts` / `C23` |
| "about **-$137,743** relative effect vs OCR" | withdrawn as unreconstructable identification | `causal-inference-overview` / `C03` |
| "**hawker centre proximity** (27.4% feature importance vs 5.5% for MRT)" | withdrawn: the ranking is an output of a model family no artefact here carries | `mrt-impact` / `importance-table-core` |
| "Clustering reveals five behavioral segments" | withdrawn: the stored asset holds a different count and the five names do not appear in it | `market-segments` / `C1` |
| "SORA changes have an immediate correlation with housing affordability and a 1-quarter lag with price trends." | the lag clause is withdrawn: no lead-lag implementation exists to measure it | `macro-sensitivity` / `C35` |
| "Real (inflation-adjusted) returns are approximately 2% above CPI across all segments" | withdrawn: no segment index exists, so the cross-segment spread is not reproducible | `macro-sensitivity` / `C8` |
| "| Spatial clustering                | Moran's I / z-score               | 0.766 / 9.91     | High — p < 0.001                         |" | not reproducible: the statistic's variable is unstated and its named input is absent | `spatial-autocorrelation` / `C01` |
| "| Rental hotspot selectivity        | 99% confidence cells              | 12 of 847        | High — Gi\* statistic                    |" | re-measured by the owning edition inside its gate-pinned window | `spatial-hotspots` / `C09` |
| "| Pure lease effect                 | Per extra year (after controls)   | +$54.75 PSF      | Moderate — hedonic regression            |" | withdrawn: a coefficient is not converted without its original response and unit | `lease-decay` / `C9` |
| "| School quality OLS                | Coefficient                       | +$9.66 PSF       | High — predictive                        |" | not reproducible: the feature it names exists in no shipped schema | `school-quality` / `C4` |
| "Across all thirteen analysis domains, the most decision-useful findings share a common pattern: segment-level specificity matters far more than model sophistication." | not measurable: a cross-series ranking needs a joint model no checkout artefact provides | `notMeasurable.jointModelAcrossStudies` |

## Populations, windows and units the editions record

The gate asks for an exact population, window and unit on every quantitative sentence. This page's quantitative sentences count editions, files, claim items and months, and each one states those three in the table above. For the subject matter itself, the population and unit belong to the owning edition, so they are quoted from that edition's own ledger rather than written here — and the producer fails the build if a quote is not a literal substring of the field it cites (`seriesRegister.rows.<series>.descriptors`).

| Series | Population and unit as that edition records them |
| --- | --- |
| `data-sources` | "One row per acquisition file" |
| `rental-yields` | "two independent transaction populations"; "median_rent x 12 / median_sale_price x 100" |
| `temporal-evolution` | "transaction counts, sample composition"; "nominal and CPI-deflated median prices per (property type, window)" |
| `amenity-impact` | "log(HDB resale price in SGD)"; "shipped distance <= 1000 m" |
| `facility-premiums` | "log condo price-psf"; "project-clustered standard errors" |
| `lease-decay` | "exact on every HDB row"; "psf, $ per square foot" |
| `mrt-impact` | no scope or definition prose is recorded in that ledger: its window is at `studyWindow` and its unit at `responses.responseDefinition` |
| `school-quality` | "descriptive OLS association of ln(psf)"; "the shipped school-distance columns" |
| `macro-sensitivity` | "macro-housing association"; "in levels and in first differences" |
| `market-segments` | "the stored research segment asset"; "its six segments, their stored metrics" |
| `spatial-autocorrelation` | "The unit that carries reproducible memberships is the planning area"; "median-psf ratio of the trailing 12 completed months" |
| `spatial-hotspots` | "median monthly_rent per cell"; "Retain January 2024-January 2025 as its own historical window" |
| `causal-inference-overview` | "the frame the two cohorts would be drawn from"; "cohort-size screens inside the measured cutoff" |
| `price-forecasts` | "realised area median prices"; "MAE, RMSE, bias, MAPE on implied levels" |
| `findings` | none: this series has no signed edition, so no population and unit are recorded for it anywhere in this checkout |

Two of those rows are deliberately uneven, and both are worth a reader's attention. `mrt-impact` publishes no population or unit prose in its ledger, so this page cites its fields instead of composing a sentence the source does not contain. And the two spatial editions do not share a unit — one carries planning areas, the other H3 cells — which is one measured reason a cross-study ranking is not available here.

## What this edition does not establish

- **It re-measures no study's subject.** Every figure above counts editions, files, claim items, months or rows of the register. No coefficient, band, premium or accuracy figure from a sibling edition appears here as a finding.
- **A matching hash is not a verdict.** A row reading "yes" says the frozen text and the ledger on disk are the bytes the record covers. It says nothing about whether the reasoning in that text holds, and nothing beyond the existence of the record about the review it received.
- **It does not resolve the one byte-level mismatch.** It measures both hashes, reproduces the pin from canonical serialisation and records the reason; whether a signature continues to cover a reformatted file is a decision for that record's owner.
- **It does not rank the series.** The register permits an honest narrower summary, and a ranking is exactly what it forbids: the editions measure different populations, windows and units, and no joint model exists to make their coefficients commensurable (`notMeasurable.jointModelAcrossStudies`).
- **It does not make the persona pages measurable.** The persona content file carries no quantitative token to bind to an edition, so nothing there is promoted or corrected here (`notMeasurable.personaContentPromises`).
- **Its absence scan is bounded.** The joint-model scan's roots, suffixes, exclusions and file count are fields; a file outside them is outside the measurement, not established absent. A screen is not a finding about origin, and an unlinked artefact adjudicates nothing in either direction.

## Provenance

Prepared by `repo-agent/session-2026-11-20`. Evidence pack: `docs/implementation/2026-11-20-rs15-findings-evidence.md`. Machine-readable ledger: `docs/implementation/artifacts/rs15-findings-evidence.json`, SHA-256 `dd6328eba82236703074bc1e2e0500086388a2a9d6530af0d5b279fa150e801e`, 132,827 bytes. The ledger records all 46 inputs it read with their hashes and byte counts, the register of the fifteen series as the app registry states it and as the files on disk measure it, the claim dispositions traced to the owning ledgers, and the bounded scans behind every absence it reports. Its `--check` mode re-measures the whole ledger from this checkout and fails on any drift, including a moved pin.

This text is a draft. It records no attestation, carries no signature, and asserts no sign-off record. A reviewer reading it should treat every number as a pointer into the ledger, and the ledger as the authority.
