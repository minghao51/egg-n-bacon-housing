---
title: Temporal Evolution
category: "market-analysis"
description: What the current dataset can and cannot say about change over time — measured window coverage, sample composition and descriptive price medians, with the legacy premium-evolution claims withdrawn
status: draft
date: 2026-11-15
personas:
  - first-time-buyer
  - investor
  - upgrader
readingTime: "7 min read"
technicalLevel: intermediate
---

# Temporal Evolution

**Edition:** `temporal-evolution-2026-11-15` · **Measured:** 2026-11-15 · **Observation cutoff:** 2026-10 (last complete month)

This edition replaces the temporal-evolution text published 2026-03-31 (frozen in the archive as `legacy-2026-11-12`). The old text described how MRT, school and area premiums changed between 2017 and 2026. A claim about change needs two things for every period it compares: comparable transaction windows, and feature values as they stood at each period. Both were measured before any sentence below was written, by [`scripts/tools/temporal_evolution_evidence.py`](../../../../implementation/2026-11-15-rs03-temporal-evolution-evidence.md), whose canonical ledger is [`artifacts/rs03-temporal-evolution-evidence.json`](../../../../implementation/artifacts/rs03-temporal-evolution-evidence.json) — sha256 `1f0aef749b9f26b6f2f4a5f09cd472956080a413a11397c2160fd45759f71012`. Running `uv run python scripts/tools/temporal_evolution_evidence.py --check` re-measures this checkout and fails if it no longer matches that ledger.

What survives measurement is narrower than the old text: coverage of the three period windows the old text names, the composition of those windows, descriptive median prices per window, and a per-area year-over-year baseline with a stated sample floor. The premium-evolution claims are withdrawn (see [Superseded figures](#superseded-figures)): the only dated MRT snapshot in this checkout is a single 2019-12-09 legacy seed applied to every period alike, school scores carry no dates at all, and there is no feature vintage per window — so a premium compared across periods on one snapshot is not a measurement of change.

## Three states of absence, kept distinct

Every coverage row below says which of three states applies, because readers and downstream studies must not merge them:

- **Source-missing** — the source does not cover the period at all. The private-residential source in this checkout starts 2021-01; earlier months are a property of the acquisition, not of the market, and this checkout cannot observe whether transactions occurred in them.
- **No-sales observed** — the source covers the period and records zero transactions for that area or month. This is neither 0 growth nor a missing source.
- **Measured** — present, counted, and published with its `n`.

## The three legacy windows, re-measured

The old text compares Pre-COVID (2017-2019), COVID (2020-2022) and Post-COVID (2023-2026). Those labels are kept; the windows are re-cut on the current dataset and end at the measured cutoff, 2026-10 (the terminal month, 2026-11, holds 790 HDB transactions — 0.3718 of the trailing-12-month median of 2,125 — and is excluded as partial).

| Window (legacy label)  | Months                 | HDB transactions | HDB months observed |                                   Condo transactions | Condo months observed |
| ---------------------- | ---------------------- | ---------------: | ------------------: | ---------------------------------------------------: | --------------------: |
| Pre-COVID (2017-2019)  | 36                     |           64,256 |               36/36 |                **0 — source-missing (36/36 months)** |              **0/36** |
| COVID (2020-2022)      | 36                     |           79,140 |               36/36 | 83,412 (2021-01 onward; 12/36 months source-missing) |                 24/36 |
| Post-COVID (2023-2026) | 46 (2023-01 → 2026-10) |          100,471 |               46/46 |                                              161,822 |                 46/46 |

(ledger `windows.byPropertyType`)

One structural consequence follows immediately: **the condo side of the legacy comparison has no like-for-like baseline in this dataset**, so no condo change statement is made anywhere in this edition. The HDB side re-cuts cleanly — all 118 study-window months are observed, with no source-missing months and no zero-transaction months.

### Sample composition (HDB): the windows are not mix-identical

| Measure                        | Pre-COVID |  COVID | Post-COVID |
| ------------------------------ | --------: | -----: | ---------: |
| Transactions (n)               |    64,256 | 79,140 |    100,471 |
| Distinct towns                 |        26 |     26 |         26 |
| Median floor area (sqm)        |        95 |     93 |         93 |
| Median remaining lease (years) |        74 |     75 |         72 |
| 3-room share                   |     24.3% |  22.7% |      24.2% |
| 4-room share                   |     41.4% |  42.1% |      43.5% |
| 5-room share                   |     24.8% |  25.9% |      23.2% |
| Executive share                |      8.0% |   7.6% |       6.2% |

(ledger `sampleComposition.byPropertyType.hdb`)

A window median is **not mix-adjusted**: the windows measurably differ in flat-type mix, floor area and remaining lease, so a difference between medians describes these transaction populations, not identical dwellings.

### Median HDB resale price per window, with uncertainty

| Window                         |       n | Median price (nominal) | 95% bootstrap interval (nominal) | Median price (real, 2026-09 base) | Median psf (nominal) |
| ------------------------------ | ------: | ---------------------: | -------------------------------: | --------------------------------: | -------------------: |
| Pre-COVID (2017-2019)          |  64,256 |                408,000 |                  405,000–408,000 |                           492,968 |               392.26 |
| COVID (2020-2022)              |  79,140 |                480,000 |                  480,000–480,000 |                           559,167 |               459.41 |
| Post-COVID (2023-01 → 2026-10) | 100,471 |                598,000 |                  595,000–600,000 |                           617,324 |               575.11 |

(ledger `windowMedians.byPropertyType.hdb`; nominal medians with seeded 2,000-resample bootstrap intervals. Real figures deflate by the dataset's own CPI column to its last observed month, 2026-09; 2.16% of Post-COVID rows — those in 2026-10, for which no CPI observation exists yet — are excluded from the real figure only.)

What this table supports: median resale prices differ across the three windows, in nominal and in real terms, and the windows' compositions differ. What it does not support: any statement about why they differ, or about premiums.

### The condo side, stated exactly

| Window                                                  |                      n | Median price (nominal) | Median price (real, 2026-09 base) | Median psf (nominal) |
| ------------------------------------------------------- | ---------------------: | ---------------------: | --------------------------------: | -------------------: |
| Pre-COVID (2017-2019)                                   | **0 — source-missing** |           not measured |                      not measured |         not measured |
| COVID (months 2021-01 → 2022-12 of the 36-month window) |                 83,412 |              1,485,000 |                         1,691,748 |             1,549.62 |
| Post-COVID (2023-01 → 2026-10)                          |                161,822 |              1,775,089 |                         1,829,180 |             1,888.26 |

(ledger `windowMedians.byPropertyType.condo`)

These rows describe the URA private-residential ingest as it ships: Condominium 41.4–43.6% and Apartment 40.8–41.8% of rows across the two populated windows, Executive Condominium 12.3–12.6%, plus landed and strata-landed subtypes at 3.0–4.6% (`sampleComposition.byPropertyType.condo.subtypeMix`). A "condo" median here is therefore not a condominium-only statistic, and the two populated windows cover different month counts (24 and 46). With no pre-COVID rows, **no change statement is computable, and none is made**.

## Planning-area year-over-year baseline (descriptive, HDB)

For every HDB planning area and year from 2018 to 2025, the change in that area's median resale price is computed only when **both** years have at least `n = 30` transactions (ledger `planningAreaBaseline.floor`). That floor is a display rule for this baseline; it is not the old text's regression minimum ("minimum 300 transactions for HDB areas and 100 for condo areas"), which is not reproduced. 2026 is a partial year (Jan–Oct) and 2017 has no prior year inside the window, so neither gets a change computation. That leaves 224 computed area-year changes across 32 planning areas.

| Year | Areas computed (n = 30 floor) |    p10 |     p50 |     p90 |     Min |     Max |
| ---- | ----------------------------: | -----: | ------: | ------: | ------: | ------: |
| 2018 |                            28 | -3.89% |  -0.82% |  +5.70% |  -5.71% |  +7.58% |
| 2019 |                            28 | -7.91% |  -2.06% |  +6.45% | -20.82% | +18.33% |
| 2020 |                            28 | -5.59% |  +4.09% |  +9.92% | -11.37% | +21.10% |
| 2021 |                            28 | +7.02% | +12.22% | +25.98% |  +2.86% | +51.86% |
| 2022 |                            28 | -2.96% |  +7.31% | +13.62% |  -8.65% | +25.09% |
| 2023 |                            28 | -4.91% |  +5.52% | +10.40% | -32.08% | +19.87% |
| 2024 |                            28 | -0.93% |  +7.94% | +13.97% |  -4.99% | +25.13% |
| 2025 |                            28 | +3.20% |  +5.70% | +14.29% |  -0.44% | +29.28% |

(ledger `planningAreaBaseline.changeByYear`; nominal changes in median resale price, year over year)

Across all 224 computed changes, the median is +5.17%, with p10 at -4.41% and p90 at +14.52% (`planningAreaBaseline.changeOverall`). The old text claims "Most areas cluster in the 7-17% YoY range during strong years." Measured on this baseline, 30.8% of the computed area-year changes fall inside 7–17%. That share is measured on a _median-price change_, a different statistic from the old analysis' modelled appreciation figures; it does not reproduce, validate or refute the clustering claim, and this edition does not offer it as doing so.

Absence and thinness, named rather than smoothed:

- **Changi, Downtown Core and Tanglin sit below the n = 30 floor in every measured year** (2017–2026); their changes are excluded by the stated floor, not silently missing. **Sungei Kadut's changes are excluded for sets of reasons, not one**: every year in which it has sales is below the floor (its counts run n = 1–7), and two of its changes carry an absence as well — the 2024 change is excluded because 2024 has **no sales observed** (zero transactions in a covered year; `byYear["2024"]`: 31 areas observed, 3 below floor, 1 no-sales) **and** 2023 is below the floor (n = 6); the 2025 change is excluded because 2024 provides no baseline **and** 2025 itself is below the floor (n = 2). The ledger records every excluded change's full reason set (`planningAreaBaseline.excludedChanges`); no-sales-observed is never rendered as 0%.
- Both table extremes are the **same planning area, Outram**: the 2023 minimum of -32.08% is a median moving 876,044 (n = 130 in 2022) → 595,000 (n = 111 in 2023), and the 2021 maximum of +51.86% is 631,500 (n = 94 in 2020) → 959,000 (n = 172 in 2021). Neither cell is near the floor: the swing is a property of one small-base area's median across roughly 94–172 transactions a year, not a market fact.
- Of the old text's example areas, Jurong East, Punggol, Bishan, Ang Mo Kio and Queenstown exist in the measured baseline; **Bidadari does not** (`planningAreaBaseline.exampleAreasPresent`). Per-area medians are in the ledger (`planningAreaBaseline.perAreaYear`); no area is classified into any trajectory (accelerating / steady / decelerating / volatile), because that classification belonged to the retired model.

## Feature vintages: what this checkout does not have

The old text's methodology regressed prices on distance-to-MRT and school-quality features, year by year. Comparing those coefficients across periods requires each feature **as it stood in each period**. Measured:

| Source                                                                                                          |                            Rows | Temporal dimension                                                        | Opening / historical dates                    |
| --------------------------------------------------------------------------------------------------------------- | ------------------------------: | ------------------------------------------------------------------------- | --------------------------------------------- |
| `raw_mrt_stations.parquet`                                                                                      |                             188 | none (`name`, `lat`, `lon`, `line`)                                       | none                                          |
| `MRTStations.geojson` (manual, legacy seed)                                                                     | 257 features (212 MRT / 45 LRT) | one stamp, `FMEL_UPD_D` = 20191209180316 on all 257 features → 2019-12-09 | none (a dated snapshot, but no opening dates) |
| `mrt_lines_mapping.csv`                                                                                         |                             217 | line/tier mapping                                                         | none                                          |
| `raw_school_directory.parquet`                                                                                  |                             337 | none                                                                      | none                                          |
| School tiers / weights (`school_tiers_primary.csv`, `school_tiers_secondary.csv`, `school_quality_weights.csv`) |                    29 / 25 / 13 | one current scoring vintage                                               | none                                          |

(ledger `featureVintages`)

One dated MRT snapshot does exist, and this edition states it precisely: `MRTStations.geojson` carries the update stamp `FMEL_UPD_D` = 20191209180316 — 2019-12-09 — on **all 257 features** (`featureVintages.mrtStationsGeojson.updateStampValues`), and the ingestion code itself describes these files as what it falls back to when a live fetch fails, in its own words "the legacy static MRT seeds (MRTStations.geojson / mrt_stations.json, 2019 vintage)" (`src/egg_n_bacon_housing/components/ingestion/geojson.py:517`, quoted verbatim in the ledger at `featureVintages.mrtStationsGeojson.ingestionFallback`). What does not exist is a vintage **per window**: nothing dates the network for 2017–2018 or any year from 2020 onward, and no dated school series exists at all.

Which station input the shipped feature column consumed is itself measured (`featureVintages.shippedFeatureLineage`): recomputing the nearest-station distance over a seeded sample of n = 20,000 shipped transactions reproduces the shipped `dist_to_nearest_mrt` column from the 188-row bronze station frame — pinned by sha256 in the ledger and recorded in RS01 as fetched 2026-11-13 — with **zero deviation (20,000 of 20,000 within 1e-6 m)**, and produces **no match against the 2019 seed (0 of 20,000; deviations up to 1,702.6 m)**. The 188-vs-257 discrepancy is therefore meaningful and resolves in favour of the bronze frame: the seed holds 257 features (249 kept by its loader, 219 distinct names) while the bronze frame holds 188 rows (185 distinct names, 30 carrying an LRT line). The shipped features are one single-vintage join applied to every period alike — `dist_to_nearest_mrt` and `school_accessibility_score` are populated for **100% of transactions in all three windows**, including 2017-2019 (`featureVintages.featurePopulationByWindowHdb`) — and a 2017 transaction carries its distance to that one fixed network. How many of those distances are anachronistic is not measurable here, because no source records when a station or school entered the network: opening dates are absent from every source in the table above.

Consequence: the MRT-premium-evolution claim and the school-premium-resilience claim are **withdrawn as not measurable**, not restated in softer words. The withdrawal rests on the narrower, measured ground: a single 2019-12-09 station seed is not a vintage for any of the three windows, no station vintage exists for 2017–2018 or 2020 onward, and no dated school-quality series exists. Measuring premiums per window would require station and school vintages that match each period; acquiring them is a source-acquisition decision, not a wording change.

## Superseded figures

Every quantitative claim in the old text, and what happened to it. Quoted phrases are verbatim from `docs/analytics/editions/legacy/2026-11-12/temporal-evolution.md`.

| Legacy figure (as the old text states it)                                                                                                        | New measured value                                                                                                                                           | Why it changed                                                                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "2017-2026 (10 years of transaction data)"                                                                                                       | HDB: 2017-01 → 2026-10 (118 months); condo: 2021-01 → 2026-10 (70 months), measured                                                                          | The private-residential source in this checkout starts 2021-01; "2017-2026" holds only for HDB                                                                                                 |
| "MRT premiums declined during COVID for both HDB and condo segments, with only partial post-COVID recovery"                                      | not measured — withdrawn                                                                                                                                     | No station opening dates; the only dated snapshot is the single 2019-12-09 legacy seed (one vintage, not one per window); no dated school series; the condo pre-COVID window is source-missing |
| Pre-COVID (2017-2019): HDB MRT premium "Moderate", condo "High"                                                                                  | not measured — withdrawn                                                                                                                                     | Same missing vintages; no premium model is reproduced                                                                                                                                          |
| COVID (2020-2022): HDB "Reduced", condo "Reduced significantly"                                                                                  | not measured — withdrawn                                                                                                                                     | Same missing vintages                                                                                                                                                                          |
| Post-COVID (2023-2026): "Partially recovered" (HDB and condo)                                                                                    | not measured — withdrawn                                                                                                                                     | Same missing vintages                                                                                                                                                                          |
| "School proximity premiums remained stable through COVID"                                                                                        | not measured — withdrawn                                                                                                                                     | School tiers and scores are one current snapshot; no historical vintage                                                                                                                        |
| "K-means clustering of area-level appreciation time series identifies 5 distinct temporal patterns, with most areas in moderate growth clusters" | not measured — withdrawn                                                                                                                                     | Retired model not reproduced; the descriptive baseline does not cluster areas                                                                                                                  |
| Cluster bands: High Growth "31-51%", Moderate Growth 1 "9-17%", Moderate Growth 2 "~10%", Moderate Growth 3 "~14%", Low Growth "7-18%"           | not measured — withdrawn; the descriptive distribution is p50 +5.17%, p10 -4.41%, p90 +14.52% (n = 224 area-years, floor n = 30)                             | Different statistic (median-price change, not modelled appreciation); clustering not reproduced                                                                                                |
| "Most areas cluster in the 7-17% YoY range during strong years."                                                                                 | Re-measured descriptively: 30.8% of 224 computed area-year median-price changes fall inside 7–17%                                                            | A median-price change is not the modelled figure the sentence describes; the claim is not reproduced as stated                                                                                 |
| "Accelerating" — Jurong East, Punggol, Bidadari                                                                                                  | not measured — no trajectory classification; Jurong East and Punggol are present in the baseline, **Bidadari is absent** from the 32 measured planning areas | Trajectory labels are retired-model outputs                                                                                                                                                    |
| "Steady" — Bishan, Ang Mo Kio, Queenstown                                                                                                        | not measured — no trajectory classification; the three areas are present in the per-area baseline                                                            | Same                                                                                                                                                                                           |
| "Decelerating" — "Some mature CCR areas"                                                                                                         | not measured — withdrawn                                                                                                                                     | No trajectory classification; "CCR" is not a measured segmentation here                                                                                                                        |
| "Volatile" — "Luxury segments"                                                                                                                   | not measured — withdrawn                                                                                                                                     | No segment classification is reproduced; "luxury" is not a measured segment here                                                                                                               |
| "Recovery asymmetry: HDB recovered faster post-COVID than luxury condos, likely due to demand inelasticity"                                      | withdrawn                                                                                                                                                    | A causal claim with no identification strategy here, resting on a condo comparison whose pre-COVID window is source-missing                                                                    |
| "Static premium estimates go stale. … The market structure has shifted."                                                                         | withdrawn                                                                                                                                                    | Premium estimates are not reproduced (missing vintages), and no causal "structure" claim is supported by a descriptive baseline                                                                |
| Methodology floor: "minimum 300 transactions for HDB areas and 100 for condo areas"                                                              | Superseded for this edition: descriptive floor n = 30 in both years                                                                                          | No regression is reproduced; the descriptive baseline states and applies its own floor                                                                                                         |

## What this edition does not establish

- **No premium, and no premium change.** No regression is fitted and no premium is estimated anywhere in this edition.
- **No cause.** Window-to-window and year-over-year differences are descriptive of transaction populations whose composition measurably differs; nothing here attributes them to policy, the pandemic, work patterns or demand.
- **No condo change statement.** The condo pre-COVID window is source-missing and its COVID window covers 24 of 36 months.
- **No trajectory or cluster classification.** The per-area medians are in the ledger; the labels are not.
- **No completeness claim.** Inputs are hashed and counted; presence in this checkout is not evidence that nothing is missing elsewhere.

## Reading this edition

- **First-time buyers:** the window medians and the composition table describe resale transaction populations, not identical flats; two windows' medians differing does not tell you what the same flat would cost in each.
- **Investors:** the per-area table is in the evidence ledger with its n per area-year; every excluded change carries its full reason set (`planningAreaBaseline.excludedChanges`), and no-sales-observed is never rendered as zero. No area is labelled as improving or declining.
- **Upgraders:** the HDB windows re-cut cleanly and the medians are reproducible; the premium trajectory claims this page used to carry are withdrawn, and they can only return if station and school vintages that match each period are acquired first.

## Provenance

Prepared by `repo-agent/session-2026-11-15` and registered as `evidenceStatus: "historical"`, `editorialStatus: "draft"` with no sign-offs and no `editionSha256`: under the refresh rules (D12), those are recorded only by the owner and an independent reviewer, never by the preparer. Evidence pack: [RS03 temporal-evolution evidence](../../../../implementation/2026-11-15-rs03-temporal-evolution-evidence.md); ledger: [`artifacts/rs03-temporal-evolution-evidence.json`](../../../../implementation/artifacts/rs03-temporal-evolution-evidence.json) (sha256 `1f0aef749b9f26b6f2f4a5f09cd472956080a413a11397c2160fd45759f71012`), reproducible with `uv run python scripts/tools/temporal_evolution_evidence.py --check`.
