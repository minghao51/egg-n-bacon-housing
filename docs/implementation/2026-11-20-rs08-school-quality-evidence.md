# RS08 evidence pack — school-quality: the tier lists exist and drive the shipped score, the legacy's three features exist in no shipped schema, its RDD stands on a failed balance, and one descriptive distance association replaces the premium

- **Date:** 2026-11-20
- **Status:** **Prepared for review, not signed off.** The ledger is measured and `--check`-able; nothing here re-fits the legacy's models, and every quantitative claim of the frozen legacy text is disposed with a stated reason. No signature in this pack is an approval. Register row: RS08. Gate (research register, quoted verbatim): _"Recheck tier provenance, bandwidth, treatment assignment, covariate balance and multiple-testing policy. School-quality model fit does not establish a causal admissions premium. Keep policy eligibility outside model outputs."_
- **Prepared by:** `repo-agent/session-2026-11-20`. The producer and the ledger were already on disk when this stage began and `--check` passed at stage start; this pack was written from the ledger **without re-measuring and without touching any measured value**.
- **Machine-readable ledger:** [`artifacts/rs08-school-quality-evidence.json`](artifacts/rs08-school-quality-evidence.json) — sha256 `c25c4b64b942e9b920eaa7a075be5abfbbabd8dc28b28650f410695d44bee4ad`, 252,385 bytes (canonical JSON, sorted keys, no timestamps, no absolute paths; schemaVersion 1.1.0). **Round 2 (2026-11-20 review):** the first-stage ledger (`71f78ece…`, 94,668 bytes) is retained at [`artifacts/superseded/rs08-school-quality-evidence.stage1-71f78ece.json`](artifacts/superseded/rs08-school-quality-evidence.stage1-71f78ece.json); the review-driven producer change and its field-by-field diff are recorded at the end of this pack (§13). Three intermediate round-2 ledger states (…`bc5afb50`, `dcbdfd69`, `16c3ae9c`…) were generated and superseded within the session while the scan-stability exclusions of §13b were being hardened against concurrent sibling activity; none was ever signed, and the final state re-measures green (§13c).
- **Producer:** `scripts/tools/school_quality_evidence.py`. Run twice → byte-identical; `uv run python scripts/tools/school_quality_evidence.py --check` re-measures the checkout and passes (output recorded twice at the end of this pack). It never runs the pipeline, never geocodes, never re-fits the legacy's models, and never writes outside `--output`.
- **Frozen legacy text:** `docs/analytics/editions/legacy/2026-11-12/school-quality.md` — sha256 `ec5fc939efa4a0b6604d57eff630f99d8d65f578a00899a0e856c2bce9dffcf9`, 7,200 bytes. All **36** quoted phrases verified to appear verbatim (46 recorded occurrences across the 36 quotes; sum of `legacyQuoteCheck.quotes[].occurrences`).
- **Upstream:** the cutoff rule and the "measured, never cited" lineage discipline from RS03/RS04/RS05/RS09/RS10; the claim-inventory and quote-check pattern from RS05/RS09/RS10. `unified_dataset.parquet` sha256 `39d234f703c9d6e098acc885eaadfdc965a6ac217189277c066676b3b117cefe` (1,236,310 × 97, `inputs`) is the same platinum dataset the sibling studies pinned.

## The gate, clause by clause

| Gate clause (verbatim)                                                     | Disposition in this pack                                                                                                                                                                                                                                                                                   | Ledger key                                    |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| "Recheck tier provenance"                                                  | **rechecked, measured end to end** — the tier artefacts exist (four hand-authored files), the producer's preferred bronze JSON is absent so the CSV fallback is the active tier source, and the tier-list→directory join is counted; the 2026-11-18 lead "no tier artefact" is corrected by this scan (§2) | `tierProvenance`                              |
| "bandwidth"                                                                | **notRecorded** — no bandwidth object, sensitivity table or placebo output exists; the legacy's 200 m / 100–300 m / 800–1200 m figures are recorded as its own prose, with the scan that bounds the absence (§7a)                                                                                          | `rddRecovery.bandwidth`                       |
| "treatment assignment"                                                     | **unmeasurable** — assignment needs school coordinates linked to shipped rows and a dated 1 km boundary artefact; neither exists in a linked form, so no shipped row can be assigned treatment (§7b)                                                                                                       | `rddRecovery.treatmentAssignment`             |
| "covariate balance"                                                        | **unmeasurable** — with no treatment assignment there are no boundary groups; the legacy's own verdict is recorded verbatim: FAILED (§7c)                                                                                                                                                                  | `rddRecovery.covariateBalance`                |
| "multiple-testing policy"                                                  | the legacy names at least six test families and records no correction anywhere in the scanned roots (no recorded occurrence of six correction tokens); this pack runs one pre-stated specification, reports all three coefficients, applies no correction and selects on nothing (§6b)                     | `multiplicityPolicy`                          |
| "School-quality model fit does not establish a causal admissions premium." | **enforced as the pack's conclusion** — the three legacy coefficients cannot be re-derived (0 of 57 parquet schemas carry any of the three feature names), and this pack's single model is a descriptive conditional association reported as an association (§4, §6)                                       | `notMeasurable.legacyModelFit`, `association` |
| "Keep policy eligibility outside model outputs."                           | **enforced by construction** — the association's regressors are three policy-free distance columns; the one shipped column that is screened as embedding policy-status flags is excluded from it; the bronze flags have zero call sites under `src/` (§3)                                                  | `policyEligibility`                           |

## 1. Cutoff

The same measured rule RS03/RS04/RS05/RS09/RS10 shipped — the terminal month's transaction count as a measured fraction of the trailing-12-month median — with the all-types headline and private/HDB cross-checks (`cutoff`):

| Field                             |   All types | Private rows | HDB rows |
| --------------------------------- | ----------: | -----------: | -------: |
| Terminal month                    |     2026-11 |      2026-11 |  2026-11 |
| Terminal transactions             |       1,211 |          421 |      790 |
| Trailing-12 median                |     4,587.5 |      2,133.0 |  2,125.0 |
| Terminal share of trailing median |       0.264 |       0.1974 |   0.3718 |
| Last complete month               | **2026-10** |      2026-10 |  2026-10 |
| Last complete month transactions  |       4,719 |        2,546 |    2,173 |

Trailing-12 window: 2025-11 → 2026-10 (`cutoff.trailing12Months`). The frame itself runs 1990-01 → 2026-11 (`cutoff.frameFirstMonth`, `cutoff.frameLastMonth`). Every window, count and share in this ledger that touches the frame stops at `lastCompleteMonth` — `cutoff.meaning` states this and `cutoff.basis` records the rule.

## 2. Tier provenance, rechecked end to end (`tierProvenance`)

The 2026-11-18 checkout lead said no tier artefact exists. **This scan corrects it**: the tier artefacts DO exist — four hand-authored files under `data/manual/csv/` — and they drive the shipped `school_accessibility_score` through the producer's documented formula.

| Artefact (`tierProvenance.manualArtefacts.*`) | sha256      | Bytes | Rows | Tier composition                                         |
| --------------------------------------------- | ----------- | ----: | ---: | -------------------------------------------------------- |
| `school_tiers_primary.csv`                    | `2d985e4d…` | 1,858 |   29 | tier 1: 10, tier 2: 16, tier 3: 3 (`tierCounts`)         |
| `school_tiers_secondary.csv`                  | `3109779a…` | 1,700 |   25 | tier 1: 5, tier 2: 10, tier 3: 10 (`tierCounts`)         |
| `school_quality_weights.csv`                  | `aef604d2…` |   969 |   13 | 13 feature weights (`features`)                          |
| `school_scoring_methodology.md`               | `f711e614…` | 4,298 |    — | the formula in prose (`qualityScoreFormula.methodology`) |

- **The active tier source is the CSV fallback, and that is measured.** The producer prefers `data/pipeline/01_bronze/external/school_tiers.json`, which is absent (`tierProvenance.bronzeJsonPreferredAndAbsent.exists = false`); `school_features.py:73` (`load_json("school_tiers.json")`) and `:83` (`csv_dir = self.data_dir / "manual" / "csv"`) are cited (`producerPreference`, `csvFallback`). The four CSV/MD files are therefore the active tier source of the shipped score.
- **The join to the bronze directory is counted** (`tierProvenance.directoryJoin`), under the producer's own exact-then-longest-prefix rule, with unresolved schools scoring quality 0 and never tier 1: primary 26 exact + 2 prefix = 28 of 29 rows joined, 1 unresolved (`FAIRFIELD METHODIST PRIMARY SCHOOL`, `unresolved`); secondary 21 exact + 4 prefix = 25 of 25 rows joined, 0 unresolved. Counts are against the 337-row bronze directory (`directoryRows`).
- **Origin: screened as hand-authored reference data, origin unverified — and the screen is now a measured scan.** The call-site scan enumerates the code files — all of `src/` plus `scripts/` outside the disclosed `scripts/tools/` instrument surface (`tierProvenance.origin.callSiteScan.filesScanned`; per-file pins at `scanManifests.codeRoots`, whose `excludedPrefixes` and `excludedPrefixReason` record why the programme's own actively-edited evidence producers are excluded from a hash-pinned scan) — and finds occurrences of the four artefact names, each classified in `classOf` (occurrence, file and path counts at `callSiteScan.occurrences`, `.matchedFiles`, `.matchedFilePaths`): the pipeline's own CSV-fallback reads (`src/egg_n_bacon_housing/utils/school_features.py`, `utils/bronze.py`, `components/features.py`). No extraction, download or other pipeline call site appears in the scanned code, and the files record no dated source snapshot (`datedSnapshotRecorded: false`). A call-site screen bounds what the checked-out code references; it is not a finding about how the files came to exist.
- **What the served/stored scan does bound** (`tierProvenance.servedTierArtefactScan`, now measured): the filename scan enumerates the files under `data/` (excluding the disclosed `data/cache/` and `app/public/data/analytics/` surfaces) plus the rest of `app/public/data/`, the enumerated-file count being `filesEnumerated` (per-file pins at `scanManifests.dataArtefactRoots`), and matches the tier-named files listed at `matchedFiles` (count at `matchedCount`) — the two school tier lists under `data/manual/csv/` and four market-segmentation tier files under `data/analysis/` (a different series, recorded so the vocabulary near-match cannot be mistaken for RS08 lineage). No tier-named file is served under `app/public/data`; the only school-named served paths are the two PNG plots recorded at `rddRecovery.servedPlots` (`schoolFileNameScan` lists every matched path with its class).
- **The formula the tiers feed** (`tierProvenance.qualityScoreFormula`): `calculate_school_quality_scores` (`school_features.py:155`), a 0.4·primary + 0.6·secondary accessibility blend (`:307`) over a 2,000 m decay range (`:32`), with the producer documenting one deviation — `academic_awards` is 0 for every school (`:164`). The inputs to this formula are the hand-authored tier lists, so the shipped score is screened as a tier-list-derived feature, not a measured school-quality measure independent of those lists.

## 3. Policy eligibility stays outside model outputs (`policyEligibility`)

- **The bronze flags are counted, never used** (`policyEligibility.bronzeFlags`, against the 337-row directory): `sap_ind` 23 yes / 314 no, `gifted_ind` 16 / 321, `ip_ind` 19 / 318, `autonomous_ind` 28 / 309. They are admission-policy eligibility flags; `schoolDirectory.policyFlagMeaning` states they are counted only.
- **Zero consumption under `src/`** (`policyEligibility.srcConsumptionScan`): the four flag names scanned over the code files under `src/` (`filesScanned`, per-file pins at the `src/` entries of `scanManifests.codeRoots`) return no occurrence, the total being `totalOccurrences`.
- **The tier lists themselves carry policy columns, and the quality formula consumes them** (`policyEligibility.tierListPolicyColumns`): primary gep Yes 8 / sap Yes 18; secondary sap Yes 12 / autonomous Yes 16 / ip Yes 20. The producer's quality formula consumes these columns (`qualityScoreFormula.producerImplementation`), so the shipped `school_accessibility_score` is **screened as embedding policy-status flags** — which is why it is excluded from this pack's one association model (`association.accessibilityExcluded`).
- **Compliance** (`policyEligibility.compliance`): no model output in this pack uses a policy-eligibility flag. The association regressors are three shipped distance columns; the controls are floor area, lease commencement, storey band, flat type, town and year.

## 4. What the shipped school columns actually contain (`columnHealth`)

Four missingness states, kept apart (`columnHealth.states` + `columnHealth.stateCounts`): a **null value**, a **recorded zero**, an **absent row**, and an **absent column** — each with its own measured count. **Round 2:** every frame-level aggregation in this block is measured through the cutoff bound — `frameStatsBound` = 2026-10 = `cutoff.lastCompleteMonth` — covering `frameRowsThroughBound` = 1,235,099 rows; the file's 1,236,310 rows (`frameRowCount`, a file property) include `frameRowsBeyondBound` = 1,211 terminal-month rows (equal to `cutoff.terminalMonthTransactions`) that sit outside every frame-level aggregation (`boundNote`).

**Absent columns — the legacy's three feature names** (`stateCounts.absentColumn.count` = 3). A metadata-only pyarrow schema read of every parquet file under `data/pipeline/` and `data/analysis/` — `filesScanned` is its file count (per-file pins at `scanManifests.schemaRoots`), `data/cache/` excluded because it is a content-addressed API-response cache with no analysis parquet (`legacyFeatureNames.schemaScan.roots`, `.filesScanned`, `.excludedRoots`) — finds `school_primary_quality_score`, `school_primary_dist_score` and `school_secondary_dist_score` in no file — each name's `files` count is a field (`schemaScan.columnPresence`). The text side of the same scan (file count at `scanManifests.textRoots.fileCount`, roots in §4a) finds them only in the frozen legacy article, its live twin and the retired programme's two plan documents — prose, not shipped columns.

**Present columns — seven school columns in the platinum frame** (`columnHealth.columns`; frame rows through the bound 1,235,099, association sample 156,231 rows):

| Column                              | Frame median (through bound) | Null values | Recorded zeros | Sample nulls | Sample recorded zeros |
| ----------------------------------- | ---------------------------: | ----------: | -------------: | -----------: | --------------------: |
| `dist_to_nearest_school`            |                     327.2635 |      11,600 |            146 |            0 |                     0 |
| `nearest_schoolPRIMARY_dist`        |                     409.0648 |      11,600 |            142 |            0 |                     0 |
| `nearest_schoolSECONDARY_dist`      |                     518.2853 |      11,600 |              4 |            0 |                     0 |
| `nearest_schoolJUNIOR_dist`         |                   2,601.8867 |      11,600 |              0 |            0 |                     0 |
| `nearest_top_primary_school_dist`   |                   3,945.8761 |      11,600 |              0 |            0 |                     0 |
| `nearest_top_secondary_school_dist` |                   7,231.4076 |      11,600 |              0 |            0 |                     0 |
| `school_accessibility_score`        |                          0.0 |      11,600 |        969,151 |            0 |               129,735 |

(`columnHealth.columns.<col>.frame.nullCount/.recordedZeroCount`, `.associationSample.nullCount/.recordedZeroCount`.)

- **The four states are counted separately** (`stateCounts`): 3 absent column names; 81,200 null cells (11,600 per column × 7, through the bound); 969,443 recorded-zero cells (through the bound); and **1,078,868 rows outside the measured screen** for the absent-row state (`stateCounts.absentRow.rowsOutsideMeasuredScreen`), with its operands recorded (`frameRowsThroughBound` 1,235,099 − `measuredScreenRows` 156,231) and the stated limit that the frame cannot be audited for rows outside itself — no count is invented for that sense.
- **The zeros are recorded values, not missing ones.** `school_accessibility_score` is 0 on 969,151 of the bound rows with a further 11,600 nulls (`columnHealth.accessibilityZeroMass.frameRecordedZeros`, `.frameNulls`, bound = 2026-10): the producer's formula contributes 0 when the nearest school is not in the manual tier lists — screened as, from the formula — so the column cannot be read as a coverage measure.
- **A file-row count describes the file, not the series.** The 11,600 nulls are shared across all seven columns' bound reads; the association sample's complete-case screen leaves 0 nulls and 0 recorded zeros on every distance regressor it uses.

### 4a. The text scan (`legacyFeatureNames.textScan`)

Roots: `docs`, `scripts`, `src`, `assets`, `prompts`, `app/src`, `.claude/handoffs` — file count at `textScan.filesScanned`, with the programme's own surfaces excluded (`docs/implementation/`, `scripts/tools/`, `prompts/`; `docs/plans/2026-11-12-reporting-refresh-decisions.md` as a path; published edition texts excluded except the frozen `editions/legacy/` originals — disclosed at `textScan.excludedPrefixes`, `.excludedPaths`, `.excludedEditionTexts`). Occurrences: one token record per name, each with its own `occurrences` and `fileCount` (`textScan.tokens`) — all inside the legacy article, its live twin (`docs/analytics/school-quality.md`, sha-pinned at `methodRecordSurfaces.liveTwin`) and the two retired plan documents (`methodRecordSurfaces.plan2025`, `.plan2026`).

### 4b. School coordinates: corrected and narrowed (`schoolCoordinates`)

- **No shipped layer carries school coordinates.** The bronze directory's schema (metadata read) has 0 coordinate columns (`schoolCoordinates.bronzeDirectoryCoordinates.coordinateColumnCount`); the shipped layers carry the resulting per-property distance columns instead.
- **But a coordinate-bearing school artefact does exist**: `data/manual/csv/datagov/SchoolsMOE.geojson` — 197 Point features, all 197 with lat/lng, all 197 names also in the bronze directory, 0 names only in the geojson (`schoolCoordinates.schoolsMoeGeojson`), sha256 `6ed84238…`.
- **It is unlinked in BOTH directions** (`schoolsMoeGeojson.consumerScan`): the token `SchoolsMOE` records no occurrence under `src/` (`schoolsMoeGeojson.consumerScan.occurrencesUnderSrc`), so the geojson is neither evidence that the shipped distances were produced from it, nor evidence that they were not. An unlinked artefact adjudicates nothing, symmetrically.
- **What the code records** (`schoolCoordinates.runtimeGeocoding`): `features.py:165` calls `geocode_schools(...)`; `school_features.py:409` defines it; `datagov.py:143` names the bronze source. The producer is screened as geocoding school postal codes at runtime and not persisting school coordinates as a school-keyed artefact.
- `schoolCoordinates.schoolFileNameScan` lists every school-named path with its class, so the preschool amenity sources (`PreSchoolsLocation.*`) cannot be mistaken for primary/secondary school artefacts.

## 5. The legacy sample: constructible screen, unreproducible counts (`legacySampleReconciliation`)

The legacy's stated screen — "2021 onward, within 2 km of primary schools" — is adopted **verbatim** as this pack's association screen and measured (`legacySampleReconciliation.screen`): HDB rows, 2021-01 → 2026-10, `nearest_schoolPRIMARY_dist` ≤ 2,000 m. Measured sample: **156,231 rows**, 26 distinct towns, median PSF 542.43, median primary distance 374.7 m (`measuredSample`).

**No measured candidate reproduces the legacy's 194,165** (`legacyClaim.sampleSize`; `anyCandidateReproducesLegacySample = false`):

| Candidate reading (`candidatePopulations[].label`)       |    Rows |                                     Difference from 194,165 |
| -------------------------------------------------------- | ------: | ----------------------------------------------------------: |
| HDB, windowed, within 2 km of primary                    | 156,231 |                       −37,934 (recorded field `difference`) |
| HDB, windowed, within 2 km of nearest school (any level) | 156,231 | −37,934 (arithmetic on `rows` and `legacyClaim.sampleSize`) |
| HDB, window start → legacy publication month (2026-01)   | 136,774 |                 −57,391 (arithmetic on the same two fields) |
| All property types, windowed, within 2 km of primary     | 394,678 |                +200,513 (arithmetic on the same two fields) |

**No regional count reproduces the legacy's split** (`anyRegionalCountReproduced = false`):

| Region | Legacy count (`legacyRegionalCounts`) | Measured (`regionalComparison[].measuredCount`) | Difference (recorded `difference`) |
| ------ | ------------------------------------: | ----------------------------------------------: | ---------------------------------: |
| CCR    |                                 1,314 |                                           5,961 |                             +4,647 |
| OCR    |                               146,553 |                                         128,159 |                            −18,394 |
| RCR    |                                46,298 |                                          22,111 |                            −24,187 |

The legacy's RCR sign flip is recorded as a property of the legacy's own **unrecorded** fit — nothing measured here can confirm or refute it (`notMeasurable.regionalFits`), and no neighbourhood explanation is drawn from it.

**The RDD band does not reproduce either** (`rddBand`; `anyCandidateReproducesLegacyRddSample = false`), on three candidate readings of "in [800, 1200] m" against the legacy's 52,881:

| Candidate reading (`rddBand.candidatePopulations[].label`)         |   Rows |                                                                  Difference from 52,881 |
| ------------------------------------------------------------------ | -----: | --------------------------------------------------------------------------------------: |
| HDB, windowed, `nearest_schoolPRIMARY_dist` in band                | 10,088 |                                                   −42,793 (recorded field `difference`) |
| HDB, windowed, `dist_to_nearest_school` in band                    |  5,314 | −47,567 (arithmetic on `rows` and `rddBand.candidatePopulations[].legacyClaimCompared`) |
| All property types, windowed, `nearest_schoolPRIMARY_dist` in band | 60,586 |                                              +7,705 (arithmetic on the same two fields) |

The legacy does not state **which** distance column its near-boundary band runs on (`rddBand.runningVariableNote`). That is recorded as **underspecified** and no choice is made for it — three candidate readings are measured instead. The same discipline covers the 100–300 m sensitivity claim: the number of bandwidths inside that range is unstated and is not chosen for it.

## 6. The one association: descriptive, on the columns that exist (`association`)

One pre-stated specification (`multipleTesting.preStatedSpecifications = 1`), on the legacy's own screen, complete cases, psf > 0 (`association.screen`).

- **Estimator** (`association.estimator`): OLS of ln(psf), HC1 robust covariance, statsmodels `sm.OLS`; fixed effects for town (26 levels in sample, baseline `ANG MO KIO`), flat type (baseline `4-ROOM`) and year (baseline `2021`); continuous controls `floor_area_sqm/10`, `(lease_commence_date − 2000)/10`, `(storey_min + storey_max)/2/10`. Design: 43 columns (`sample.designColumnCount`), n = 156,231 (`sample.n`), 2021-01 → 2026-10.
- **Exclusions** (`association.exclusionReasonCounts`): every per-row exclusion reason is 0 except `outside-study-window-or-hdb-or-radius` = 1,080,079 — which is exact arithmetic on two ledger fields: `columnHealth.frameRowCount` 1,236,310 − `association.sample.n` 156,231 = 1,080,079.

### 6a. The three distance coefficients, with the proxy tier named (`association.distanceCoefficients`)

| Regressor                     | Shipped column, proxy named                                                                                                                                    | log-point /100 m | robust SE /100 m |      t | % effect /100 m |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------: | ---------------: | -----: | --------------: |
| `dist_primary_per_100m`       | `nearest_schoolPRIMARY_dist` — nearest primary-level school, no tier or policy content                                                                         |        −0.002455 |         0.000113 | −21.69 |         −0.2452 |
| `dist_top_primary_per_100m`   | `nearest_top_primary_school_dist` — nearest **tier-1 primary of the manual tier list** (29 listed, 10 tier 1); hand-authored reference data, origin unverified |        −0.000704 |         0.000054 | −12.98 |         −0.0704 |
| `dist_top_secondary_per_100m` | `nearest_top_secondary_school_dist` — nearest **tier-1 secondary of the manual tier list** (25 listed, 5 tier 1); same named proxy                             |        +0.000065 |         0.000049 |  +1.34 |         +0.0065 |

(The proxy tier named explicitly above is the manual CSV tier list of §2 — "tier 1" means "listed tier 1 in `school_tiers_primary.csv` / `school_tiers_secondary.csv`", not any verified admissions tier.)

Regressor correlations (`association.regressorCorrelations`): the two top-school distances correlate at 0.7936; the plain primary distance correlates −0.1154 / −0.1828 with them — recorded so the three coefficients are read as a block, not three independent effects.

**Interpretation, binding on any downstream text** (`association.interpretation`): a descriptive conditional association measured on the columns that exist, on the legacy's own stated screen. It does **not** establish a causal admissions premium, and the pack draws no eligibility or valuation rule from it. Every coefficient's own `interpretation` field repeats: descriptive only, NOT a causal admissions premium.

### 6b. The multiple-testing policy (gate clause) (`multiplicityPolicy`)

- **The legacy's side** (`legacyRecordedCorrection`): it names at least six test families — one headline OLS (+ one XGBoost), three regional fits, one RDD at 1 km, bandwidth sensitivity 100–300 m (count unstated), two placebo cutoffs, covariate balance t-tests (`legacyNamedTestFamilies`) — and records **no** multiple-testing correction anywhere in the scanned roots: six correction tokens (`bonferroni`, `holm`, `fdr`, `false discovery`, `multiple comparison`, `multiple testing`), no occurrence over the same text boundary as §4a (`tokens`, `totalOccurrences`, `filesScanned`). The boundary is disclosed rather than widened: a correction recorded only inside the excluded programme surfaces would not be found (`scanBoundary`).
- **This pack's side** (`thisPack`): one pre-stated specification; all three distance coefficients reported regardless of significance (`allCoefficientsReported = true`); correction applied: none; selection on significance: false. A single pre-stated descriptive specification with all coefficients reported needs no correction, and the pack's conclusion — association, not premium — is not a conclusion any coefficient significance could upgrade (`thisPack.reason`).

## 7. The RDD clauses, each absent or unmeasurable with its scan (`rddRecovery`)

### 7a. Bandwidth — `notRecorded` (`rddRecovery.bandwidth`)

**Round 2: the absence is now bounded by a measured three-pass artefact scan** (`artefactScan`), not a prose assertion. One enumeration under `data/` (excluding the disclosed `data/cache/` and `app/public/data/analytics/` surfaces) plus the rest of `app/public/data/`, its file count being `artefactScan.filenameScan.filesEnumerated`, feeds three passes: (a) the **filename pass** matches files whose name carries a bandwidth/sensitivity/placebo/discontinuity/rdd token — exactly one match, the served RDD PNG itself (`filenameScan.matchedFiles`: `app/public/data/analysis/school_rdd/rdd_visualization.png`); (b) the **content pass** scans every `.csv`/`.json`/`.md` under the same roots line by line for bandwidth/sensitivity/placebo, its file and occurrence counts being `contentScan.filesScanned` and `.occurrences`; (c) the **parquet-column pass** checks the schemas under `data/pipeline/` and `data/analysis/` (metadata-only, count at `scanManifests.schemaRoots.fileCount`) for column names carrying the same tokens, recording no match (`parquetColumnScan`). The scan bounds what is _named_ in the checkout; a bandwidth value could in principle hide inside a binary or a generically named file, and that boundary is stated rather than widened (`artefactScan.meaning`). The legacy's figures are recorded as its own prose (`legacyStatements`): bandwidth 200 m on each side of boundary; sensitivity tested at 100–300 m; placebos at 800 m and 1200 m fake cutoffs. Re-deriving a bandwidth would mean re-running the RDD, which this pack does not do (`meaning`).

### 7b. Treatment assignment — `unmeasurable` (`rddRecovery.treatmentAssignment`)

The definition requires treating "within 1 km of the nearest primary school **at the admissions boundary**", which needs (a) school coordinates linked to shipped rows and (b) a dated boundary artefact (`definitionRequired`). Measured: no shipped layer carries school coordinates (§4b); **round 2** — the boundary-artefact scan is now measured over the same enumeration (count at `boundaryArtefact.filenameScan.filesEnumerated`): the **filename pass** matches exactly one boundary-named file, `data/manual/geojsons/ura_planning_area_boundary.geojson` (`boundaryArtefact.filenameScan.matchedFiles`), classified in `classificationOfMatches` as URA planning-area geometry (screened as, from its name) — not school-keyed and not dated to admissions — and the **content pass** records no admissions-boundary-token occurrence across the text-format files, its file and occurrence counts being `boundaryArtefact.contentScan.filesScanned` and `.occurrences`; the filename/content boundary is stated rather than widened (`boundaryArtefact.meaning`). The one coordinate-bearing school artefact (`SchoolsMOE.geojson`) is unlinked to the shipped distances in both directions and consumed by nothing. So no shipped row can be assigned treatment and the assignment rule cannot be rechecked — only recorded as unmeasurable with its scan (`meaning`).

### 7c. Covariate balance — `unmeasurable` (`rddRecovery.covariateBalance`)

The legacy itself records the verdict: "FAILED — boundary groups differ systematically on age, size, MRT distance, and neighborhood profile" (`legacyStatement`, verbatim). With no treatment assignment there are no boundary groups to balance, so the failure is neither re-measurable nor refutable here (`meaning`). **A failed-design estimate is not a premium**: the legacy's −$79.47 PSF figure is recorded as a failed-design estimate and its causal reading is withdrawn at `legacyClaims` (C18/C19/C24/C25 below).

### 7d. The served plots: sha-pinned, visually read, unlinked in both directions (`rddRecovery.servedPlots`)

Two PNGs are sha-pinned in `inputs` and given a HUMAN VISUAL READ (`method` — the pixels are not machine-read; a hash change invalidates the read):

- `rdd_visualization.png` (96,540 bytes, sha `e69200fd…`): visibly prints a red dashed rule at 1000 m and a fitted line stepping DOWN across the cutoff, on sparse binned means over about 800–1200 m — **not** the 52,881-row sub-sample (`visiblePrint`). A plot with no numbers attached: it neither reproduces nor refutes −$79.47 (`rddVisualization.meaning`).
- `exploratory_analysis.png` (168,559 bytes, sha `25c35923…`): visibly prints a quality-bands panel reading "No data for quality bands" and a histogram annotated "Median: 0.00" (`visiblePrint.panels`) — consistent with the measured zero mass in `columnHealth.accessibilityZeroMass`, and a visual record that the quality-score axis of the legacy study was data-starved at plot time.

**Unlinkage cuts both ways** (`unlinkedNote`): the legacy's provenance section names the served analysis tree generically as the canonical asset location; neither PNG carries a run identifier, so each is recorded as what it visibly prints and as evidence in **neither** direction about the legacy's stored fits. The same discipline governs every unlinked artefact in this pack (the geojson at §4b, the importance tables at §8).

## 8. The nearest stored model outputs are unlinked, and the $29,000 arithmetic closes on an unreproducible coefficient

- **`data/analysis/feature_importance/`** (`adjacentModelArtefacts`): seven files, sha-pinned. Zero rows for any of the three legacy feature names (`legacyFeatureNameRowsTotal = 0`); the 24 school-token rows are preschool amenity features (`schoolTokenRowsTotal = 24`). The trees are unlinked to the legacy article's fits — symmetrically, evidence neither for nor against its coefficients — and their `price_psf` linear test R² 0.912287 is a different model on a different population, recorded only so the near-match in vocabulary cannot be mistaken for lineage (`meaning`, `pricePsfLinearTestR2`).
- **The legacy's own arithmetic** (`legacyArithmetic`): its $29,000 figure is its own `+$9.66 PSF` (`coefficientPsf`) × 3 points (`points`) × 1,000 sqft (`floorAreaSqft`) = **28,980** (`product`), rounded up to the stated 29,000 (`legacyStated`); `difference` records −20.0. The arithmetic is internally consistent — and it inherits the non-reproducibility of the coefficient it scales (`meaning`), which fails at `legacyFeatureNames.schemaScan` (§4).

## 9. Every legacy claim, disposed (`legacyClaims`, 36 entries)

**36 claims, 36/36 phrases verified verbatim in the frozen file** (`legacyQuoteCheck.claimsChecked = 36`, `allQuotesFound = true`, 46 recorded occurrences). Status split (`legacyClaims[].status`): **3 re-measured, 4 withdrawn, 29 not-reproducible**.

- **Re-measured (3)**: C3 — the screen definition itself, adopted verbatim as this pack's association screen; C21 — the 800–1200 m band definition, adopted verbatim and measured under three candidate readings; C34 — "Post-2021 housing market", with the measured window boundaries recorded.
- **Withdrawn (4)** — the causal/RDD language: C18 (−$79.47 PSF: a failed-design estimate, not re-derivable, causal reading withdrawn and no "within-1km discount" stated), C19 ("Units within 1km were cheaper after controls": treatment cannot even be assigned), C24 (the RDD sentence withdrawn **in both directions** — no premium is supported, and the implied negative treatment reading is equally not re-established), C25 (the conclusion's causal/RDD language retired; what remains is the descriptive association and the recorded unmeasurability).
- **Not-reproducible (29)**: the three coefficients C4/C5/C6 (features exist in no shipped schema; no coefficient table is stored), the $29,000 sentence C7 (internally consistent arithmetic inheriting that non-reproducibility), the regional table C8–C17 (fits not stored; measured row analogues recorded beside each count; the sign flip recorded, not re-measured, and no neighbourhood explanation drawn), the RDD sub-sample C20 (running variable underspecified; three candidate readings, none reproduces), the balance verdicts C22/C23, the method statements C26–C30 and C33 (parameters, HC3, CV split, RDD model formula — prose only, no fitted counterpart), the boundary assertion C32 (no dated boundary artefact; recorded without endorsing a date or geometry), the feature-set sentence C35, the XGBoost/OLS agreement claim C36, and the two sample-size figures C1/C2.

Every `ledgerKey` is resolved **at build time** (`claimKeyCheck`: 36 checked, `unresolved` empty) and an unresolved key **fails the build**. The ledger states that resolution is syntactic (`resolutionIsSyntactic = true`): it verifies the key names a recorded node, not whether that node supports the disposition.

## 10. What this checkout cannot supply (`notMeasurable`, 8 entries)

| Gate clause                               | Id                                | Status                                                                                       |
| ----------------------------------------- | --------------------------------- | -------------------------------------------------------------------------------------------- |
| School-quality model fit ≠ causal premium | `legacyModelFit`                  | `notReproducible` — coefficients cannot be re-derived; this pack fits no premium model       |
| (regional fits)                           | `regionalFits`                    | `notReproducible` — fits not stored; row counts reproduce none of the legacy's segment sizes |
| (RDD estimate)                            | `rddEstimate`                     | `withdrawn` — failed-design estimate, not a premium                                          |
| treatment assignment                      | `treatmentAssignment`             | `unmeasurable` — needs coordinates + a dated boundary; neither exists linked                 |
| covariate balance                         | `covariateBalance`                | `unmeasurable` — no treatment ⇒ no boundary groups                                           |
| bandwidth                                 | `bandwidthArtefact`               | `notRecorded` — no bandwidth/sensitivity/placebo artefact                                    |
| (spatial CV)                              | `spatialCv`                       | `notReproducible` — "large generalization gap" with no magnitude recorded; underspecified    |
| policy eligibility outside outputs        | `policyEligibilityOutsideOutputs` | `enforcedByConstruction` — see §3                                                            |

## 11. What this pack does not establish

- **No premium and no causal estimate of any kind.** One descriptive conditional association is measured; the gate's sentence is enforced as the conclusion, not merely recorded.
- **No re-derived legacy coefficient.** +$9.66 / +$6.27 / +$3.52 PSF and the regional/RDD figures stand as the legacy's own, unreproducible from this checkout.
- **No re-estimated RDD, balance test or bandwidth.** Each is recorded as absent or unmeasurable with its scan; the −$79.47 figure is a failed-design estimate and is withdrawn in both directions.
- **No verified tier origin.** The four artefacts are screened as hand-authored reference data, origin unverified; "tier 1" means listed tier 1 in those files.
- **No lineage for the unlinked artefacts.** The geojson, the two PNGs and the feature-importance tables adjudicate nothing about the legacy's fits in either direction.
- **No policy-eligibility flag in any output**, and no eligibility or valuation rule drawn from the association.

## 12. Scan-exclusion disclosure (the programme's own surfaces)

Every hash-pinned scan excludes the programme's own output surfaces, and the exclusions are declared in the ledger (`legacyFeatureNames.schemaScan.excludedRoots`, `legacyFeatureNames.textScan` / `rddRecovery.tokenScan` / `multiplicityPolicy.legacyRecordedCorrection` sharing `excludedPrefixes` `docs/implementation/`, `scripts/tools/`, `prompts/`; `excludedPaths` `docs/plans/2026-11-12-reporting-refresh-decisions.md`; `excludedEditionTexts` = published edition texts under `docs/analytics/editions/` except the frozen `editions/legacy/` originals, which stay **in** the scan because the legacy's own claims are what the tokens are matched against; `data/cache/` excluded from the schema scan as a content-addressed API cache). **Round 2:** every enumerated scan surface also carries a per-file manifest in the ledger — `scanManifests.textRoots` (`fileCount`), `scanManifests.schemaRoots` (`fileCount`), `scanManifests.dataArtefactRoots` (254, with `data/cache/` and the actively rewritten `app/public/data/analytics/` surface excluded and disclosed), `scanManifests.codeRoots` (54, with the programme's own `scripts/tools/` instrument surface excluded and disclosed) — each a sorted path/sha256/bytes list, so an aggregate `filesScanned` count is never a substitute for per-file records. The two exclusions beyond the stage-1 disclosures exist because sibling programme surfaces moved while this stage ran: the RS10 §6a/§6b lesson, applied until `--check` stayed green across concurrent sibling activity. Absence claims are bounded by these scans and claim no more than they cover — each absence in this pack names its scan.

## 13. Check record and the round-2 producer change

### 13a. Why the producer changed, and what did not

The 2026-11-20 independent review returned FAIL with eight findings against the edition text. Two of them showed that **statements in the ledger were broader than the scans behind them** (the bandwidth and boundary absence claims cited hand-authored prose rather than measured scans), two showed **aggregation-bound and manifest gaps** (frame-level column statistics measured through the terminal month rather than the cutoff, violating the programme's cutoff discipline; inputs lacking per-file pins), and the rest were edition-text defects (an unledgered number, an asymmetric plot sentence, an uncounted missingness state).

**The stage-1 measurements were not wrong — one bound was.** The stage-1 `columnHealth` frame statistics correctly measured the full file (median `nearest_schoolPRIMARY_dist` 409.0697, accessibility zeros 969,982 over all 1,236,310 rows, including the terminal month's 1,211 rows); what violated the programme's cutoff discipline was the _bound_, not the arithmetic. The producer now measures every frame-level aggregation through `lastCompleteMonth` and records the bound as a field; the stage-1 values are superseded, not corrected. Determinism was re-proven after the change (two runs, `cmp` byte-identical).

### 13b. The field-by-field diff (superseded → current)

The full diff (superseded `71f78ece…` → prior round-2 state `36740efe…`) touches only the fields the findings name plus the new scan bookkeeping. The current checkout ledger is `74ab4e0c…` (252,385 bytes); the prior round-2 hash is historical, not current.

- **Measured-value changes (cutoff bound, 17 leaf fields):** `columnHealth.columns.*.frame.rowCount` 1,236,310 → 1,235,099 (×7); `nearest_schoolPRIMARY_dist.frame.median` 409.0697 → 409.0648; `nearest_schoolSECONDARY_dist.frame.median` 518.4282 → 518.2853 and `.p95` 1,588.5227 → 1,586.7301; `nearest_top_secondary_school_dist.frame.p95` 12,375.7876 → 12,375.9521; `school_accessibility_score.frame.recordedZeroCount` 969,982 → 969,151 (= `accessibilityZeroMass.frameRecordedZeros`). Nothing outside `columnHealth` moved.
- **New bound fields:** `columnHealth.frameStatsBound`, `frameRowsThroughBound`, `frameRowsBeyondBound`, `boundNote`, `accessibilityZeroMass.frameStatsBound`.
- **New state counts (F5):** `columnHealth.stateCounts` (absentColumn 3; null cells 81,200; recorded-zero cells 969,443; absentRow 1,078,868 with operands), `states.absentRow` definition reworded.
- **Measured absence scans replacing prose (F2, F3, F4):** `rddRecovery.bandwidth.artefactScan` string → object (filename/content/parquet-column passes with counts and matched-file lists); `rddRecovery.treatmentAssignment.boundaryArtefact.scan` removed → `filenameScan` + `contentScan` + `classificationOfMatches` + `meaning`; `tierProvenance.origin` string → object with `callSiteScan` (`filesScanned` outside the disclosed instrument surface, with `occurrences`, `matchedFiles`, `matchedFilePaths` and `classOf`); `tierProvenance.servedTierArtefactScan` gains measured counts and a corrected finding (6 tier-named matches listed).
- **Manifests and pins (F7, F8):** new top-level `scanManifests` — `textRoots`, `schemaRoots`, `dataArtefactRoots` (with `data/cache/` **and** the actively rewritten `app/public/data/analytics/` surface excluded and disclosed) and `codeRoots` (with the programme's own `scripts/tools/` instrument surface excluded and disclosed) — each a sorted path/sha256/bytes list whose length is its `fileCount`; `manifestKey` added to `legacyFeatureNames.schemaScan/.textScan`, `rddRecovery.tokenScan`, `multiplicityPolicy.legacyRecordedCorrection`, `policyEligibility.srcConsumptionScan` (+ `filesScanned` 48), `schoolCoordinates.schoolsMoeGeojson.consumerScan` (+ `filesScanned`); `inputs` gains the three cited source files (sha256/bytes/lines) and `lines` for the legacy edition (136) and methodology; `methodRecordSurfaces` gains `lines`.
- **Disclosure:** `association.exclusionBasis` added (the exclusion partition's basis and the terminal-month rows inside it); `schemaVersion` 1.0.0 → 1.1.0.
- **Untouched:** `cutoff`, `association` estimates/sample/screen, `legacySampleReconciliation`, `legacyClaims` (36) and their notes, `legacyQuoteCheck` (36/36), `claimKeyCheck` (36/0 unresolved), `notMeasurable`, `schoolDirectory`, `adjacentModelArtefacts`, `rddRecovery.servedPlots`, `policyEligibility` counts, `tierProvenance` join/quality-formula fields.

**Four code-manifest pins moved without a producing-code change:** `cleaning.py`, `feature_rental.py`, `feature_transactions.py`, and `hdb_lookups.py` were re-pinned in `scanManifests.codeRoots.files` / `scanManifests.textRoots.files` because the checkout contains added `cast(...)` wrappers for typing. I verified each file against `HEAD` by stripping those `cast(...)` calls (and their typing-only imports) from both ASTs: all four ASTs are identical. `cast` is a typing-only no-op, and the identical ASTs establish that no executable expression or control flow changed; none of the measured values can move from these edits. The pin movement is scan bookkeeping, not a changed producer measurement.

### 13c. Check runs at the current ledger

`uv run python scripts/tools/school_quality_evidence.py --check` is run twice against the current checkout ledger — both green, ledger sha256 `c25c4b64b942e9b920eaa7a075be5abfbbabd8dc28b28650f410695d44bee4ad` (252,385 bytes):

```text
Pass: RS08 ledger re-measures byte-identically from this checkout.
Ledger sha256: c25c4b64b942e9b920eaa7a075be5abfbbabd8dc28b28650f410695d44bee4ad

Pass: RS08 ledger re-measures byte-identically from this checkout.
Ledger sha256: c25c4b64b942e9b920eaa7a075be5abfbbabd8dc28b28650f410695d44bee4ad
```

Determinism: producer runs are byte-identical (`cmp` clean) and byte-identical to the pinned ledger. Getting there took two stability hardenings beyond the review findings themselves, both instances of the RS10 §6a/§6b lesson: (1) an early round-2 ledger pinned `scripts/tools/` code files — including this producer's own bytes — so the act of formatting the producer moved the ledger (a self-reference fixed point, proven converged, then removed by excluding the instrument surface); (2) a sibling stage rewrote `app/public/data/analytics/rental_hotspots_2024-01_2025-01.json.gz` between two runs, moving the data-artefact manifest, so that actively rewritten surface was excluded and disclosed. Both intermediate ledger states were superseded before any signature. The stage-1 pack text (superseded values 409.0697 / 969,982 / full-frame language) was updated to the round-2 ledger in the same pass; the edition text was corrected against the same fields.

### 13d. Scan-stabilisation citation round (2026-11-22)

The scan-stabilisation round regenerated every ledger in this programme and was never logged in this pack; it is recorded here with the prose round that followed. The text-roots scan is now recorded as `scanManifests.textRoots.fileCount`, and this pack and the edition text no longer restate it or any other scan-scope count: each block cites the field that carries it (`rddRecovery.tokenScan.filesScanned`, `multiplicityPolicy.legacyRecordedCorrection.filesScanned`, `legacyFeatureNames.textScan.filesScanned`, `legacyFeatureNames.schemaScan.filesScanned`, `policyEligibility.srcConsumptionScan.filesScanned`, `tierProvenance.origin.callSiteScan.filesScanned`, `rddRecovery.bandwidth.artefactScan.filenameScan.filesEnumerated`, `.contentScan.filesScanned`/`.occurrences`, `rddRecovery.treatmentAssignment.boundaryArtefact.filenameScan.filesEnumerated`, `.contentScan.filesScanned`/`.occurrences`, `scanManifests.{textRoots,schemaRoots,dataArtefactRoots,codeRoots}.fileCount`). **No producer change and no ledger regeneration:** the RS08 producer re-measures byte-identically at these bytes (`--check` green, §13c), so the fields were already correct and the prose was what had drifted.

**One identity defect was also repaired.** The edition text had recorded the same SHA-256 and byte count for two different artefacts — this pack and the ledger — which is the ledger's identity applied to a prose document that is not the ledger. Each artefact now carries its own: the pack's bytes are pinned in the edition's provenance paragraph. Because editing this pack moves its bytes, that pin is written after the last edit to this file.

### 13e. Citation-path round (2026-11-22)

One defect was in the ledger rather than in the sentence, so it was fixed at the producer. `policyEligibility.srcConsumptionScan.manifestKey` read `scanManifests.srcRoots`, a key this ledger has never carried; the pins for that scan are the `src/` entries of `scanManifests.codeRoots`, which the edition sentence already named. `scripts/tools/school_quality_evidence.py` now emits `scanManifests.codeRoots` there, and the edition sentence no longer discloses a dangling pointer: it states that this scan's own `manifestKey`, its `roots`, and its `filesScanned` agree, with the pins at the `src/` entries of `scanManifests.codeRoots`.

Field diff (one leaf, no measured value touched):

```text
policyEligibility.srcConsumptionScan.manifestKey
   - 'scanManifests.srcRoots'
   + 'scanManifests.codeRoots'
```

Superseded bytes: `artifacts/superseded/rs08-school-quality-evidence.pre-manifest-key-fix.json` (sha256 `c25c4b64b942e9b920eaa7a075be5abfbbabd8dc28b28650f410695d44bee4ad`, 252,385 bytes). The producer's `--check` is green twice at the new bytes (§13c), and two non-check runs are `cmp`-identical and byte-identical to the pinned ledger.
