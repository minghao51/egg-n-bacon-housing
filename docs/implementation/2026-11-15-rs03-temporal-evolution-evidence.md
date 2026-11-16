# RS03 evidence pack — temporal evolution: comparable windows, sample composition and feature vintages

- **Date:** 2026-11-15
- **Status:** **Prepared for review, not signed off.** The window re-cut, the composition
  measurements, the like-window medians and the feature-vintage audit are measured from this
  checkout. Nothing in this pack is an approval: the source/cutoff and publication signatures
  below are **pending**, and no edition text carries a sign-off until an independent reviewer
  has read the refreshed text against this ledger. Register row: RS03 —
  `docs/analytics/temporal-evolution.md`. Gate: "comparable historical transactions and
  period-correct feature/reference vintages".
- **Prepared by:** `repo-agent/session-2026-11-15`.
- **Machine-readable ledger:**
  [`artifacts/rs03-temporal-evolution-evidence.json`](artifacts/rs03-temporal-evolution-evidence.json)
  — sha256 `1f0aef749b9f26b6f2f4a5f09cd472956080a413a11397c2160fd45759f71012`.
- **Producer:** `scripts/tools/temporal_evolution_evidence.py`
  (`uv run python scripts/tools/temporal_evolution_evidence.py --check` re-measures from the
  checkout and fails on drift; run twice, byte-identical).
- **Upstream:** [RS01 source inventory](2026-11-14-rs01-source-inventory.md) (source coverage
  and acquisition record), [RS02 rental-yield pack](2026-11-14-rs02-rental-yield-evidence.md)
  (cutoff convention: 2026-10 as the last complete month).

## 1. What was measured and how

The legacy text (`docs/analytics/editions/legacy/2026-11-12/temporal-evolution.md`, never
edited) claims premium _change over time_ across three period labels it names itself:
Pre-COVID (2017-2019), COVID (2020-2022) and Post-COVID (2023-2026). The RS03 gate asks whether
those windows can be re-measured **on one feature vintage** from the current dataset. This pack
measures exactly that, from `data/pipeline/04_platinum/unified_dataset.parquet` (1,236,310 rows,
sha256 in the ledger) and the reference files the features are built from, and nothing else:

1. **Window coverage** — for each legacy window label, per property type: transactions, months
   observed out of months expected, and _which_ kind of absence applies to a missing month
   (§2). Absence is never merged into a single number: a month before a source's measured
   coverage starts is **source-missing**; a month inside coverage with zero transactions is
   **no-sales observed**; neither is **0**.
2. **Sample composition** — per window, the mix that moves a median: flat-type shares, floor
   area, remaining lease, towns (HDB); EC share, subtype mix, planning areas (condo) (§3).
3. **Like-window medians with uncertainty** — nominal and CPI-deflated median resale price per
   window with a 95% bootstrap interval. The interval is seeded (`default_rng(20261115)`, 2,000
   resamples), so it is a function of the data, not of a run (§4).
4. **Planning-area year-over-year baseline** — per HDB planning-area-year counts and median
   prices, and the distribution of year-over-year median-price change where **both** years
   clear a stated floor of n = 30. Descriptive only: no trajectory classification, no
   clustering, no premium model is reproduced (§5).
5. **Feature-vintage audit** — what dated feature vintages the checkout holds (a single
   2019-dated MRT seed snapshot; nothing per window; no dated school series), and whether the
   shipped distance/quality features are populated for every window (§6).

Determinism: the ledger is canonical JSON (sorted keys, no timestamps, all floats rounded); the
tool was run twice and produced byte-identical files. The terminal month (2026-11) is measured
as partial, not assumed: 790 HDB transactions = 0.3718 of the trailing-12-month median of 2,125
(ledger `cutoff`), which is why every window ends at the last complete month, 2026-10.

## 2. The comparable-period gate: what re-cuts, and what cannot

| Window (legacy label)  | Months                 | HDB transactions | HDB months observed | Condo transactions | Condo months observed | Condo source-missing months |
| ---------------------- | ---------------------- | ---------------: | ------------------: | -----------------: | --------------------: | --------------------------: |
| Pre-COVID (2017-2019)  | 36                     |           64,256 |               36/36 |              **0** |              **0/36** |                   **36/36** |
| COVID (2020-2022)      | 36                     |           79,140 |               36/36 |             83,412 |                 24/36 |                       12/36 |
| Post-COVID (2023-2026) | 46 (2023-01 → 2026-10) |          100,471 |               46/46 |            161,822 |                 46/46 |                        0/46 |

(ledger `windows.byPropertyType`)

Two structural findings, both measured:

1. **The condo side of the legacy comparison does not exist in this checkout.** The URA private
   source covers 2021-01 onward (RS01); the Pre-COVID condo window is 36 of 36 months
   **source-missing**, and the COVID condo window is missing its first 12 months (2020) the same
   way. This is **source-missing**, not "no sales occurred" — this checkout cannot observe
   whether private transactions occurred before 2021, and the pack does not claim they did not.
   Every cross-period condo claim in the legacy text therefore has no like-for-like baseline
   here and is withdrawn (§7).
2. **The HDB side re-cuts cleanly.** All 118 study-window months are observed for HDB (no
   source-missing months, no zero-transaction months), so HDB window coverage, composition and
   medians are measured on one dataset with one collection boundary.

The Post-COVID window in this pack ends 2026-10 (46 months). The legacy text, dated 2026-03-31,
says only "2023-2026"; this pack does not guess at the exact months the retired analysis saw —
it states its own window and its own coverage instead.

## 3. Sample composition: the windows are not mix-identical

HDB (ledger `sampleComposition.byPropertyType.hdb`):

| Measure                        | Pre-COVID |  COVID | Post-COVID |
| ------------------------------ | --------: | -----: | ---------: |
| Transactions                   |    64,256 | 79,140 |    100,471 |
| Distinct towns                 |        26 |     26 |         26 |
| Median floor area (sqm)        |        95 |     93 |         93 |
| Median remaining lease (years) |        74 |     75 |         72 |
| 3-room share                   |     24.3% |  22.7% |      24.2% |
| 4-room share                   |     41.4% |  42.1% |      43.5% |
| 5-room share                   |     24.8% |  25.9% |      23.2% |
| Executive share                |      8.0% |   7.6% |       6.2% |

Condo (ledger `sampleComposition.byPropertyType.condo`):

| Measure                         |            Pre-COVID |          COVID |     Post-COVID |
| ------------------------------- | -------------------: | -------------: | -------------: |
| Transactions                    |   0 (source-missing) |         83,412 |        161,822 |
| Distinct planning areas         |                    0 |             41 |             43 |
| Median floor area (sqm)         | not measured (n = 0) |             94 |             92 |
| EC transactions (share)         | not measured (n = 0) | 10,538 (12.6%) | 19,847 (12.3%) |
| Strata-landed + landed subtypes | not measured (n = 0) |  ~3.0% of rows |  ~4.6% of rows |

Consequences, stated before any price is read:

- A window median is **not mix-adjusted**. The HDB windows differ measurably in flat-type mix,
  floor area and remaining lease, so a difference between window medians is a statement about
  _these transaction populations_, not about identical dwellings.
- The condo population is the URA private-residential ingest as it ships: Condominium 41.4–43.6%,
  Apartment 40.8–41.8%, Executive Condominium ~12.3–12.6%, plus landed and strata-landed
  subtypes (~3.0–4.6% of rows). A "condo" median in this dataset is therefore **not** a
  condominium-only statistic (RS01 records the same grain caveat).

## 4. Like-window price medians, with uncertainty

HDB median resale price (ledger `windowMedians.byPropertyType.hdb`; 95% bootstrap CI, seeded):

| Window                         |       n |    Median price (nominal) | Median price (real, 2026-09 base) | Median psf (nominal) |
| ------------------------------ | ------: | ------------------------: | --------------------------------: | -------------------: |
| Pre-COVID (2017-2019)          |  64,256 | 408,000 [405,000–408,000] |         492,968 [491,766–494,335] |               392.26 |
| COVID (2020-2022)              |  79,140 | 480,000 [480,000–480,000] |         559,167 [557,484–560,016] |               459.41 |
| Post-COVID (2023-01 → 2026-10) | 100,471 | 598,000 [595,000–600,000] |         617,324 [616,388–618,672] |               575.11 |

Real terms deflate by the dataset's own CPI column to its last observed month, 2026-09. The CPI
column has no 2026-09-or-later observation for 2026-10, so 2.16% of Post-COVID HDB rows (2,173)
are excluded from the real figure only (`cpiExcludedShare`); the excluded rows are stated, not
silently dropped.

Condo median price (ledger `windowMedians.byPropertyType.condo`):

| Window                                      |                      n |          Median price (nominal) | Median price (real, 2026-09 base) | Median psf (nominal) |
| ------------------------------------------- | ---------------------: | ------------------------------: | --------------------------------: | -------------------: |
| Pre-COVID (2017-2019)                       | **0 — source-missing** |                **not measured** |                  **not measured** |     **not measured** |
| COVID (2020-2022, months 2021-01 → 2022-12) |                 83,412 | 1,485,000 [1,480,000–1,490,000] |   1,691,748 [1,682,440–1,696,786] |             1,549.62 |
| Post-COVID (2023-01 → 2026-10)              |                161,822 | 1,775,089 [1,770,000–1,780,000] |   1,829,180 [1,822,975–1,834,525] |             1,888.26 |

These are descriptions of two transaction populations over different month counts (24 and 46).
The condo rows carry no pre-COVID baseline, so **no condo change statement is computable**, and
none is made. The HDB rows support only this: nominal and real median prices differ across the
three windows, and the windows' compositions differ (§3). Whether that reflects mix, market,
policy or all three is **not established** by this pack.

## 5. Planning-area year-over-year baseline (descriptive, HDB)

Floor: a year-over-year change is computed only when **both** years have ≥ 30 transactions in
that planning area (`planningAreaBaseline.floor`). This pack's floor is a descriptive-display
rule; the legacy text's regression minimum ("minimum 300 transactions for HDB areas and 100 for
condo areas") is not reproduced. 32 planning areas carry HDB transactions in the window. 2026 is
a partial year (Jan–Oct at this cutoff) and is excluded from change computation; 2017 has no
prior year inside the window. That yields 224 computable area-year changes (8 years × 28 areas).

Distribution of year-over-year median-price change, nominal (ledger
`planningAreaBaseline.changeByYear`):

| Year | Areas computed |    p10 |     p50 |     p90 |     Min |     Max |
| ---- | -------------: | -----: | ------: | ------: | ------: | ------: |
| 2018 |             28 | -3.89% |  -0.82% |  +5.70% |  -5.71% |  +7.58% |
| 2019 |             28 | -7.91% |  -2.06% |  +6.45% | -20.82% | +18.33% |
| 2020 |             28 | -5.59% |  +4.09% |  +9.92% | -11.37% | +21.10% |
| 2021 |             28 | +7.02% | +12.22% | +25.98% |  +2.86% | +51.86% |
| 2022 |             28 | -2.96% |  +7.31% | +13.62% |  -8.65% | +25.09% |
| 2023 |             28 | -4.91% |  +5.52% | +10.40% | -32.08% | +19.87% |
| 2024 |             28 | -0.93% |  +7.94% | +13.97% |  -4.99% | +25.13% |
| 2025 |             28 | +3.20% |  +5.70% | +14.29% |  -0.44% | +29.28% |

Overall (ledger `planningAreaBaseline.changeOverall`): median +5.17%, p10 -4.41%, p90 +14.52%,
min -32.08%, max +51.86%. **30.8% of the 224 computed area-year changes fall inside the 7–17%
band** the legacy text quotes ("Most areas cluster in the 7-17% YoY range during strong
years"). That share is measured on a _median-price change_, a different statistic from the
legacy model's appreciation figures — it does not reproduce, validate or refute the cluster
claim, and the pack does not offer it as such.

Absence is preserved, not zeroed, and exclusions are recorded as reason **sets**, never a
single cause:

- Changi, Downtown Core and Tanglin sit **below the n = 30 floor in every measured year**
  (2017–2026); their changes are excluded by the stated floor, not silently missing.
- **Sungei Kadut's changes are excluded for sets of reasons, not one**: every year in which it
  has sales is below the floor (its counts run n = 1–7), and two of its changes carry an
  absence as well. The 2024 change is excluded because 2024 has **no sales observed** (zero
  transactions in a covered month — `byYear["2024"]` records 31 areas observed, 3 below
  floor, 1 no-sales) **and** 2023 is below the floor (n = 6); the 2025 change is excluded
  because 2024 provides no baseline **and** 2025 itself is below the floor (n = 2). The
  ledger records every excluded change's full reason set (`planningAreaBaseline.excludedChanges`,
  e.g. `excludedBecause: ["no-sales-observed", "prior-year-below-floor"]` for 2024);
  no-sales-observed is never rendered as 0%.
- Area-year aggregates are bounded at the measured cutoff (`planningAreaBaseline.cutoffUpperBound`:
  2026-10), so the terminal partial month enters no count or median: 2026 covers 21,801
  transactions across the 32 areas (not the 22,591 an unbounded aggregate would show), and
  Outram's 2026 cell is n = 91, median 1,180,000 — three terminal-month rows lower than an
  unbounded count.
- Both extremes are the **same planning area, Outram**: the 2023 minimum of -32.08% is a median
  moving 876,044 (n = 130 in 2022) → 595,000 (n = 111 in 2023), and the 2021 maximum of +51.86%
  is 631,500 (n = 94 in 2020) → 959,000 (n = 172 in 2021). Neither cell is near the floor; the
  swing is a property of one small-base area's median across roughly 94–172 transactions a
  year, not a market fact.

Example areas named by the legacy text (ledger `planningAreaBaseline.exampleAreasPresent`):
Jurong East, Punggol, Bishan, Ang Mo Kio and Queenstown are present and measured per-area-year;
**Bidadari is not among the 32 planning areas with HDB transactions in the window**, so the
legacy example cannot even be population-checked here. No trajectory (accelerating / steady /
decelerating / volatile) is assigned to any area — that classification belonged to the retired
model and is withdrawn.

## 6. The feature-vintage audit: why the premium-evolution claims stop here

The legacy methodology regresses price on `dist_to_nearest_mrt` and school-quality features
year by year. A _change in premium across periods_ requires the feature **as of each period**.
Measured (ledger `featureVintages`):

| Source                                                                                   |                            Rows | Temporal dimension                                                            | Opening/historical dates                                     |
| ---------------------------------------------------------------------------------------- | ------------------------------: | ----------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `raw_mrt_stations.parquet`                                                               |                             188 | none — `name`, `lat`, `lon`, `line` only                                      | **none**                                                     |
| `MRTStations.geojson` (manual, legacy seed)                                              | 257 features (212 MRT / 45 LRT) | one update stamp on every feature: `FMEL_UPD_D` = 20191209180316 → 2019-12-09 | **no opening dates; one dated snapshot, nothing per window** |
| `mrt_lines_mapping.csv`                                                                  |                             217 | line/tier mapping                                                             | **none**                                                     |
| `raw_school_directory.parquet`                                                           |                             337 | none                                                                          | **none**                                                     |
| `school_tiers_primary.csv` / `school_tiers_secondary.csv` / `school_quality_weights.csv` |                    29 / 25 / 13 | none — current scoring vintage                                                | **none**                                                     |

One dated MRT snapshot does exist, and the pack states it precisely: `MRTStations.geojson`
carries the update stamp `FMEL_UPD_D` = 20191209180316 — 2019-12-09 — on **all 257 features**
(`featureVintages.mrtStationsGeojson.updateStampValues`), and the ingestion code itself
describes these files as the legacy seed to fall back to when a live fetch fails, in its own
words "the legacy static MRT seeds (MRTStations.geojson / mrt_stations.json, 2019 vintage)"
(`src/egg_n_bacon_housing/components/ingestion/geojson.py:517`, quoted verbatim in the ledger
at `featureVintages.mrtStationsGeojson.ingestionFallback`). What does not exist is a vintage
**per window**: nothing dates the network for 2017–2018 or any year from 2020 onward, and no
dated school series exists at all.

Which station input the shipped feature column consumed is itself measured
(`featureVintages.shippedFeatureLineage`), not inferred from an acquisition record: the
consumer site is `src/egg_n_bacon_housing/components/features.py:210` (`mrt_stations=raw_mrt_stations`
passed into `compute_proximity_features`), and the nearest-station distance recomputed over a
seeded sample of n = 20,000 shipped transactions reproduces the shipped `dist_to_nearest_mrt`
column from the 188-row bronze station frame — sha256-pinned in the ledger — with **zero
deviation (20,000 of 20,000 within 1e-6 m)**, while the 2019 seed produces **no match (0 of
20,000; deviations up to 1,702.6 m)**. The 188-vs-257 discrepancy is therefore meaningful and
resolves in favour of the bronze frame: the seed holds 257 features (249 kept by its own
loader, 219 distinct names) while the bronze frame holds 188 rows (185 distinct names, 30
carrying an LRT line). The shipped features are therefore a single current-vintage join
applied to every period alike: `dist_to_nearest_mrt` and `school_accessibility_score` are
**100% populated for all three windows**, including 2017-2019
(`featurePopulationByWindowHdb`), and a 2017 transaction carries its distance to that one
fixed network. How many of those distances are anachronistic is **not measurable** here,
because no source records when stations or schools entered the network — opening dates are
absent from every source measured in §6.

Consequence, stated as the gate requires: the MRT-premium-evolution claim and the
school-premium-resilience claim are **withdrawn as not measurable**, not restated with
hedging. The withdrawal rests on the narrower, measured ground: a single 2019-12-09 station
seed is not a vintage for any of the three windows, no station vintage exists for 2017–2018
or 2020 onward, and no dated school-quality series exists. What would be needed: station
lists (or opening dates) per window and a dated school-quality series; acquiring them is a
source acquisition, not a wording change.

## 7. What this pack does NOT establish

- **No premium, and no premium change.** No regression is fitted; the legacy "MRT premium by
  period" and "school premium resilience" claims are withdrawn, not re-estimated (§6).
- **No causal claim of any kind.** Window-to-window and year-over-year differences are
  descriptive of transaction populations whose composition measurably differs (§3). Nothing
  here supports "market structure shifted", "recovery", or any policy attribution.
- **No condo change statement.** The condo pre-COVID window is source-missing in this checkout;
  the condo COVID window is 24 of 36 months. No like-for-like condo baseline exists (§2, §4).
- **No trajectory classification and no clustering.** The 5-cluster result and the per-area
  trajectory labels are retired-model outputs; the descriptive baseline is measured instead
  (§5) and does not reproduce them.
- **No nominal-vs-real reading of history.** Real medians use the dataset's CPI column to
  2026-09; the CPI column itself is one vintage, ends before the transaction cutoff, and its
  coverage limits (2.16% of Post-COVID HDB rows excluded) are stated, not hidden.
- **No completeness claim about sources.** Inputs are hashed and counted; as in RS01, presence
  in the checkout is not evidence that nothing is missing elsewhere.

## 8. Sign-off record

| Role            | Signatory                                                | Attests                                                                                                                                  | Recorded                                    |
| --------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| Source / cutoff | repo owner                                               | the measured windows, the 2026-10 cutoff, the source-missing vs no-sales distinction, and the feature-vintage withdrawal that §6 implies | **pending**                                 |
| Scientific      | independent reviewer (different model; not the preparer) | the refreshed edition text matches this ledger and quotes the legacy text's actual phrases                                               | **pending** (required before any signature) |
| Publication     | repo owner (≠ scientific reviewer)                       | the exact edition text to publish                                                                                                        | **pending**                                 |

- **Ledger:** `docs/implementation/artifacts/rs03-temporal-evolution-evidence.json`
- **Ledger sha256:** `1f0aef749b9f26b6f2f4a5f09cd472956080a413a11397c2160fd45759f71012`
- **Reproduce:** `uv run python scripts/tools/temporal_evolution_evidence.py --check`

Until all three attestations exist (D12), the refreshed edition stays `historical`/`draft` in
the edition registry and the series keeps saying no approved current edition exists. The
ledger is referenced from this pack — never the other way round — and is never hand-edited;
regenerating it changes the hash and invalidates any signature that pinned the old one.
