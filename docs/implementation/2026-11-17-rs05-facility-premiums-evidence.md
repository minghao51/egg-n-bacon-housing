# RS05 evidence pack — facility-premiums: the facility layer is absent, the join is recovered, and project structure is measured

- **Date:** 2026-11-17
- **Status:** **Prepared for review, not signed off.** The ledger is measured, reproducible and `--check`-able; no facility premium is fitted and every facility-level claim of the legacy text is withdrawn with a measured reason. No signature in this pack is an approval. Register row: RS05 — `docs/analytics/facility-premiums.md`. Gate (research register, quoted): _"Recover facility ownership/date and join keys; assess missing facilities, correlated amenities and project effects. Publish uncertainty and sample sizes; no isolated causal-premium claim from unadjusted comparisons."_
- **Prepared by:** `repo-agent/session-2026-11-17`.
- **Machine-readable ledger:** [`artifacts/rs05-facility-premiums-evidence.json`](artifacts/rs05-facility-premiums-evidence.json) — sha256 `8bdc5b8465907bbbe98851841b4080caa4fb246b8ed8e61503d59bcedf348970` (canonical JSON, sorted keys, no timestamps, no absolute paths).
- **Producer:** `scripts/tools/facility_premiums_evidence.py`. Run twice → byte-identical (`cmp` clean); `uv run python scripts/tools/facility_premiums_evidence.py --check` re-measures the checkout and passes.
- **Frozen legacy text this pack checks against:** `docs/analytics/editions/legacy/2026-11-12/facility-premiums.md` — sha256 `d44ad9c54586b2b658ecd5589d0a9698b049f1b244e4e055216f8aad7a96efa0` (recorded in the ledger at `legacyQuoteCheck.legacyFileSha256`; all 46 legacy quotes verified verbatim, bold/backtick-stripped and whitespace-normalised — including every prevalence, synergy and external-proximity table row quoted in the edition's superseded-figures table. From this revision the producer also extracts those 46 quoted spans from the edition itself and verifies each against the legacy file — `--check` fails if an edition quotation drifts or a registered claim loses its quotation (`legacyQuoteCheck.editionSpans`).
- **Upstream:** [RS03 temporal-evolution](2026-11-15-rs03-temporal-evolution-evidence.md) (cutoff rule; the private-residential source's 2021-01 start) and [RS04 amenity-impact](2026-11-16-rs04-amenity-impact-evidence.md) (snapshot-join vintage semantics, which this pack inherits by reference and does not re-audit). This pack re-measures everything it cites from the checkout; the shared inputs agree (`unified_dataset.parquet` sha `39d234f703c9…` is the same platinum dataset RS04 pinned).

## 1. What was measured, and the cutoff

The observation cutoff is the same measured rule RS03/RS04 shipped (`cutoff` in the ledger): the last complete month is **2026-10**, because the terminal month 2026-11 holds **421 condo transactions** — **0.1974** of the trailing-12-month median of **2,133** (`cutoff.terminalMonthTransactions`, `terminalMonthShareOfTrailingMedian`, `trailing12MedianTransactions`) — and is partial. **`cutoffUpperBound` is a ledger field** on the source coverage (`condoSourceCoverage.cutoffUpperBound`) and on the model sample (`associations.sample.cutoffUpperBound`), and every aggregation in this pack — coverage counts, join-key distributions, the variance decomposition, the model — is bounded at BOTH ends (2021-01 and 2026-10). No 2026-11 row enters any count below.

The study population is the **private-residential (condo) source**, because the legacy study is about condo facilities. Its measured coverage (`condoSourceCoverage`): **245,655 rows**, 2021-01 → 2026-11 as observed on disk; **0 rows before 2021-01** (`rowsBeforeSourceStart` — the legacy text's "transaction data 2017-2026" has no 2017-2020 analogue here); **245,234 rows in the window**; **70 window months, none source-missing** (`windowMonths`, `sourceMissingWindowMonths` is empty); the thinnest window month is **2026-02 with 1,547 transactions** (`minWindowMonthTransactions`).

Inputs are sha-pinned in the ledger (`inputs`): the platinum dataset, the bronze condo transactions, both SportSG layers, and the archived v1 pipeline document.

## 2. The source audit: the facility layer the legacy study used is not in this checkout

This is the gate's "recover facility ownership/date and join keys" and "assess missing facilities" audit, measured (`legacySourceAudit`):

| Legacy-named source (as the old text cites it)                            | In this checkout                                                    |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `data/04_platinum/private_property_facilities.parquet` (172,504 records)  | **absent** (`legacyNamedSources`, `exists: false` measured on disk) |
| `data/04_platinum/property_nearby_facilities.parquet` (3,638,104 records) | **absent**                                                          |
| `data/04_platinum/property.parquet` (41,340 records)                      | **absent**                                                          |
| `data/04_platinum/housing_unified.parquet`                                | **absent**                                                          |

Where the layers went: the archived v1 pipeline document defines L3 stages named `L3_private_property_facilities` and `L3_property_nearby_facilities` — quoted verbatim in the ledger from `docs/archive/20250120-data-pipeline.md` line 268/269 (3 occurrences each; the doc's own sha256 is pinned at `archivedPipeline.doc.sha256`). The Hamilton pipeline under `data/pipeline/` defines no facility stage.

The absence claim is checked against counter-evidence, not made against silence:

- The shipped dataset's **only facility-like columns** are `dist_to_nearest_sports_facility` and `nearest_sports_facility` (`legacySourceAudit.unifiedDataset.facilityLikeColumns`, measured by scanning the full physical schema — all 97 columns, read from the parquet metadata rather than this tool's own 18-column projection, with every column name recorded at `columnNames`; the producer fails loudly if this list ever changes). No column describes a development's in-house facility list.
- The layer behind those columns is **SportSG**: 45 public venues in the bronze parquet (`sportsgLayer.parquet.rows = 45`, 45 distinct names), 45 features in the raw GeoJSON with names in a `VENUE` property and only dataset-update stamps (`FMEL_UPD_D`: 44 × 20241024152749, 1 × 20250711141125 — refresh stamps, not presence dates). The loader is cited verbatim from `src/egg_n_bacon_housing/components/ingestion/geojson.py` (`sportsgLayer.loaderCitations`). These are **public** sport centres, swimming complexes, ActiveSG gyms and stadiums — shared infrastructure, not a development's private facility list. This pack does not treat them as one, and the refreshed edition may not either.
- One shipped row carries the literal string `None` as its `nearest_sports_facility` value alongside null distances (`unresolvedNameMarker`) — a missing-name marker, not a facility named "None". It is the same row that carries the missing-source reasons in §6.

Consequences, all measured: the legacy facility prevalence table, the facility-combination synergy table and every with-vs-without facility comparison have **no population** in this checkout. Facility **ownership/date cannot be recovered** — the absent layers are the only place a facility attribute (which project has which facility, since when) has ever lived in this repo's data.

## 3. The recovered join key, and what it cannot do

The only candidate key a facility layer could have joined on is **`project_name`** (`joinKey.key`), present and fully populated in both the bronze condo source and the unified dataset:

| Measure (`joinKey`)                                      |           Bronze (all 245,655 rows) | Window (245,234 rows, 2021-01 → 2026-10) |
| -------------------------------------------------------- | ----------------------------------: | ---------------------------------------: |
| Empty key values                                         |                       0 (share 0.0) |                            0 (share 0.0) |
| Distinct projects                                        |                               3,005 |                                    3,005 |
| Transactions per project: min / p10 / median / p90 / max |          1 / 2 / 18 / 228.6 / 2,800 |               1 / 2 / 18 / 226.6 / 2,788 |
| Largest value of the key                                 | "LANDED HOUSING DEVELOPMENT", 2,800 |      "LANDED HOUSING DEVELOPMENT", 2,788 |
| Single-transaction projects                              |                                 138 |                                      140 |
| Projects with ≥ 30 transactions                          |                               1,155 |                                    1,154 |

Two measured caveats bind what the key could ever support (`joinKey.normalisation`, `counterparty`):

- The key joins as exact shipped strings; **no project master layer or crosswalk exists** in this checkout to validate spelling, and the risk of two developments sharing one name string is **not measurable** here. The most frequent value of the key is the literal string "LANDED HOUSING DEVELOPMENT" — a category label the source attaches to bulk records, not a named development (`largestValueNote`).
- **The counterparty layer is absent**: `facilityLayerPresent: false`, and `recordsJoinedToAFacilityLayer` is **"none — the key has no counterparty layer in this checkout"**. That is a missing counterparty, not zero facilities: nothing here may be read as a count of zero facilities per project.

## 4. Facility missingness: every legacy facility is `no-record`

Per-facility status for everything the legacy prevalence and synergy tables name (`facilityMissingness`):

| Legacy facility / combination       | Status                                        | Properties counted | Share of properties |
| ----------------------------------- | --------------------------------------------- | -----------------: | ------------------: |
| Swimming pool                       | `no-record` (reason `facility-source-absent`) |               none |                none |
| Security (24hr)                     | `no-record`                                   |               none |                none |
| Gym / Fitness corner                | `no-record`                                   |               none |                none |
| BBQ pits                            | `no-record`                                   |               none |                none |
| Function room                       | `no-record`                                   |               none |                none |
| Tennis court                        | `no-record`                                   |               none |                none |
| Sky garden / Roof terrace           | `no-record`                                   |               none |                none |
| Concierge / Clubhouse               | `no-record`                                   |               none |                none |
| Jacuzzi / Hydrospa                  | `no-record`                                   |               none |                none |
| All five synergy-table combinations | `no-record`                                   |               none |                none |

Semantics, stated in the ledger and binding on the refreshed edition (`facilityMissingness.semantics`): **`no-record`** (the source layer that carried the attribute is absent) is distinguished from **`absent`** (a record exists and shows the facility missing) and from **`zero`** (a count was taken and returned 0). This checkout supports only `no-record`. "No facility record" is not "the development has no pool", and it is not 0.

## 5. Project structure: what an unadjusted facility comparison would actually compare

The gate's "correlated amenities and project effects" assessment, measured on the exact model sample (n = 234,479, 2,413 projects; `projectStructure`):

- **91.0638% of log price-psf variance lies BETWEEN projects** (between-project share 0.910638, within-project share 0.089362; one-way decomposition, method recorded at `logPsfVariance.method`). Within a project, transactions differ mostly by floor band, size and timing — 8.94% of the variance.
- The five external-access indicators are nearly **project-level constants**: the between-project share of each indicator's variation is **mrt 0.998792, hawker 0.997726, sports_facility 0.997387, mall 0.996830, childcare 0.989010** (`indicatorBetweenProjectShare`). A transaction's access profile is essentially its project's access profile.
- Projects differ enormously in price: across the **1,102 projects with ≥ 30 transactions** (`perProjectMedianPsf`), the median psf ranges from **824.16 (WOODSVALE, n = 214)** to **4,707.67 SGD/sqft (PARK NOVA, n = 78)** — p10 1,132.57, median 1,692.19, p90 2,509.00. The next-lowest are NORTHOAKS 842.32 (n = 273) and KEW GREEN 859.60 (n = 59); the next-highest ARDMORE PARK 4,107.83 (n = 66) and BOULEVARD 88 3,959.28 (n = 94).

What this means for the gate: facilities cluster inside developments, and projects differ from each other in ways that also correlate with price. An unadjusted comparison between "has facility X" and "does not" on this population **is a comparison of projects** — the legacy method's controls (planning area, property age) leave that between-project structure intact. This pack therefore (a) labels its fitted model a **between-project comparison** with no project fixed effects, and (b) records the decomposition above as the quantification of what that label means. No direction or magnitude of project-level confounding is claimed — the decomposition is descriptive variance accounting, not an effect estimate.

## 6. The recorded specification: one descriptive model, uncertainty and n published

**This pack fits no facility model** (`notFitted.facilityPremiumModel`) — the facility regressor the legacy study used does not exist here. What is fitted is **one recorded specification** of the access-question fragment the checkout CAN support, with the explicit purpose of publishing units, uncertainty and sample sizes; no dated prior protocol exists, so specification search cannot be ruled out — the single-specification discipline is a disclosed limitation, not a credential. A project-fixed-effects variant is **recorded as not fitted** (`notFitted.projectFixedEffectsSpecification`), not run; the legacy methodology itself is not reproduced (`notFitted.legacyMethodReproduction`).

**Estimator** (`associations.estimator`): OLS (statsmodels, `use_t=False`) with **two covariance batteries reported for every coefficient**: HC1 heteroskedasticity-robust (unclustered — treats transactions as independent) and **project-clustered CRVE** (cluster = `project_name`, 2,413 clusters, statsmodels `cov_type='cluster'` with its default finite-cluster corrections; coefficients identical to the HC1 fit, only the covariance differs). The **clustered battery is the published uncertainty**; the HC1 battery is retained only to show the scale of the clustering understatement (`clusteredStandardErrors.why`). Response: **log(price per square foot)**, price in nominal SGD per square foot of strata area. The shipped `psf` column's identity with `price/area_sqft` is measured exact on **245,655/245,655** condo rows, max deviation 0.0 (`responseLineage.check`). Coefficients are log points; `pctEffectExpMinus1 = 100·(exp(β)−1)` is the approximate percentage difference implied.

**Regressors:** five binary access indicators, each `1` when the shipped distance column is ≤ 1,000 m — **all five fitted jointly in the one specification** (no selection, no stepwise search): mrt, mall, hawker, sports_facility, childcare.

**Controls** (`associations.estimator.controls`): area in **square feet** (continuous, /100 internally, back-transformed), a **freehold** indicator (1 when the tenure string is exactly `Freehold`), a **long-lease** indicator (parsed lease duration ≥ 100 years), **lease commencement year** ((year−1900)/100; 0 for freehold rows, identified from leasehold variation), floor-band fixed effects (**17 levels** observed; baseline `01 to 05`; `-` is the unreported band, kept as its own level and never read as a storey number), property-subtype fixed effects (Condominium / Apartment / Executive Condominium; baseline Condominium), transaction-type fixed effects (Resale / New Sale / Sub Sale; baseline Resale), transaction-year fixed effects (baseline 2021), planning-area fixed effects (**41 levels**; baseline BUKIT TIMAH). The tenure parse is documented in the producer (`TENURE_PATTERN`). **Not controlled** is listed in the ledger: project identity, project completion year (null for **245,649** of 245,655 condo rows — `sample.yearCompletedNullRows`), in-house facility presence, unit condition, floor level within a band, tenure gradations beyond the two flags, new-sale incentives, walking-path distance, planning-area×year shocks, and the snapshot's own vintage.

**Sample** (`associations.sample`): condo rows 2021-01 → 2026-10, non-landed strata subtypes, **n = 234,479**, k = 75, R² = 0.7872 (adjusted 0.7871), df_resid = 234,404 (`associations.fit`). Exclusions are **reason sets over every condo row** (245,655): **9,995 rows fail `landed-or-strata-landed-subtype`**, **421** the terminal partial month, **934** `unparseable-tenure` (the source's `99 years leasehold` / `999 years leasehold` strings carry no commencement year), and **1 row carries a seven-reason set** — landed subtype + missing planning area + all five `missing-source:<amenity>-distance` (the un-geocoded row of §2); the other overlaps are **174 two-reason rows** and **11,001 single-reason rows** (`excludedRowsByReasonCount`: 1 → 11,001, 2 → 174, 7 → 1). `before-study-window` is 0 (the source starts 2021-01), and price/area/project-name failure counts are 0. The **10,755 in-window excluded rows** are not carried as a row dump: the ledger records their count, the reason-set signatures (`excludedInWindowReasonSignatures`), and a sha256 digest over the canonical per-row payload (`excludedInWindowRowsSha256` — recomputed by `--check`, so a single drifting row fails it), with the first five rows sampled to show the shape (`excludedInWindowRowsSample`). A null distance is a **missing source**, not a zero distance and not "no amenity nearby" (`missingSourceSemantics`).

### 6a. Measured conditional associations (`associations.indicatorCoefficients`)

| Indicator                    | n with indicator = 1 (share of 234,479) | Log point β |   HC1 SE | Clustered SE | clustered/HC1 | clustered t |      exp(β)−1 |
| ---------------------------- | --------------------------------------: | ----------: | -------: | -----------: | ------------: | ----------: | ------------: |
| MRT within 1 km              |                        200,169 (85.37%) |   +0.068648 | 0.001083 |     0.017982 |       16.5991 |        3.82 |  **+7.1059%** |
| Mall within 1 km             |                         57,049 (24.33%) |   −0.017691 | 0.001227 |     0.014870 |       12.1179 |       −1.19 |  **−1.7536%** |
| Hawker within 1 km           |                        165,838 (70.73%) |   −0.001337 | 0.000871 |     0.012159 |       13.9573 |       −0.11 |  **−0.1336%** |
| SportSG facility within 1 km |                         75,939 (32.39%) |   −0.023912 | 0.000846 |     0.011079 |       13.0999 |       −2.16 |  **−2.3628%** |
| Childcare within 1 km        |                        233,231 (99.47%) |   −0.142079 | 0.018301 |     0.050451 |        2.7567 |       −2.82 | **−13.2448%** |

Coefficients are identical under both covariance estimates; only the standard errors differ. The ratio column is the measured scale of the HC1 understatement: **2.76× for childcare and roughly 12× to 16.6× for the other four indicators** — the direct consequence of the access indicators being 98.9–99.9% between-project (§5).

**Which inferences change:** on the clustered battery, **mall (|t| = 1.19) and hawker (|t| = 0.11) are not distinguishable from zero on this design**. MRT (|t| = 3.82), SportSG facility (|t| = 2.16) and childcare (|t| = 2.82) remain larger than twice their clustered standard errors; the childcare caveat below is unchanged and no row gains an effect interpretation. No significance statement in this pack or the refreshed edition rests on the HC1 column.

Controls (natural units, log points per unit, same specification; HC1 SE, clustered SE): area −0.00000178 per sqft (0.00000088, 0.00000115), lease commencement year +0.00377342 per year (0.00007974, 0.00103723); freehold flag +0.49407081 (0.00896221, 0.11545212), long-lease flag +0.42689178 (0.01149295, 0.15095446) (`controlCoefficients`, `flagControls`). The tenure flags are close to project-level attributes, which is why their clustered SEs grow the most. The full 75-column coefficient vector with both SE batteries is in the ledger (`fullCoefficientVector`).

**Read these rows as conditional differences BETWEEN projects, not effects of anything on prices:**

- Every coefficient compares transactions of projects that differ in the indicator with transactions of projects that do not, holding planning area, year, floor band, subtype, sale type, area and the tenure controls fixed. **Project identity is not conditioned on** (`estimator.projectEffects`), and §5 quantifies why that label matters. No sentence in the refreshed edition may turn these into premiums, rankings or guidance.
- **The childcare row is a thin, geographically concentrated contrast with no effect interpretation** (`associations.childcareContrast`): the indicator is 0 for **1,248 transactions (0.53%)** — MARINA SOUTH (1,108), SOUTHERN ISLANDS (89), CHANGI (51) — whose nearest childcare is 1,026.0 m away at best (median 1,372.9 m). The ledger records the group's composition and distances and runs no sensitivity or sign-flip analysis; at this contrast size the coefficient is reported for completeness, not interpreted — its clustered |t| of 2.82 does not change that.
- **These numbers do not rank amenities and do not touch facilities.** The indicators describe external access; the in-house facility layer the legacy study ranked is absent (§2).

## 7. What this pack does not establish

- **No facility premium, prevalence, combination or quality estimate of any kind.** The in-house facility layer is absent; every legacy facility claim is withdrawn with that measured reason, not restated.
- **No causal claim.** Nothing here identifies why two transactions differ in price; "commands", "adds", "worth", "drives" appear nowhere in this pack's findings, and the refreshed edition inherits that rule.
- **No within-project (project-fixed-effects) estimate.** The variant is recorded as not fitted; the between-project labelling and the variance decomposition are the disclosure, not a substitute estimate.
- **No temporal statement.** One undated snapshot per access layer is joined to 2021-2026 transactions alike (RS04's vintage audit); no per-period model is fitted.
- **No 2017-2020 coverage.** The private source starts 2021-01 with 0 earlier rows; the legacy "2017-2026" data period is re-cut, not confirmed.
- **No ranking.** Conditional associations are not importance shares; no model here produces a ranking of facilities or amenities.
- **No completeness claim about sources outside this checkout.** The absent legacy layers are measured absent _here_; whether they survive elsewhere is not assessed.
- **No pre-registration credential.** One specification is recorded and only that one is fitted, with all coefficients reported; specification search cannot be ruled out.
- **No significance claim from the unclustered battery.** Every inference statement in this pack rests on the project-clustered standard errors; the HC1 column exists only to show how much the clustering correction matters (§6a).

## 8. Sign-off record

| Role          | Signatory         | Attests | Recorded |
| ------------- | ----------------- | ------- | -------- |
| source/cutoff | — not yet given — |         |          |
| scientific    | — not yet given — |         |          |
| publication   | — not yet given — |         |          |

Sign-offs belong to the owner and an independent reviewer, never to the preparer (`repo-agent/session-2026-11-17`), and they attach to the **ledger** sha256 `8bdc5b8465907bbbe98851841b4080caa4fb246b8ed8e61503d59bcedf348970`. A later re-run of the producer that changes a byte changes that hash and invalidates any signature recorded against it — re-run, diff, and re-sign only if the owner re-attests. The registry entry stays `evidenceStatus: "historical"`, `editorialStatus: "draft"`, `editionSha256: null`, `signoffs: []` until those signatures exist.
