---
title: Market Segments
category: "market-analysis"
description: What this checkout can and cannot say about behavioural market segmentation — six stored segments, cohort counts that reproduce no measured population, zero per-transaction membership, a measured correspondence to PSF-based cluster profiles, an unlinked K-selection sweep, and thirty-six legacy claims disposed with measured reasons
status: draft
date: 2026-11-20
personas:
  - investor
  - first-time-buyer
  - upgrader
readingTime: "11 min read"
technicalLevel: intermediate
---

# Market Segments

**Edition:** `market-segments-2026-11-20` · **Measured:** 2026-11-20 · **Observation cutoff:** 2026-10 (last complete month)

This edition replaces the market-segments text dated 2026-03-31, frozen in the archive as [`legacy/2026-11-12/market-segments.md`](../../legacy/2026-11-12/market-segments.md) (157 lines, sha256 `6813e4e121d8e1784f8a4605e8911ea26b634910cac02ce3702c1093d498e958` — `inputs`, `legacyQuoteCheck.legacyFileSha256`). It is a **re-measurement, not a re-publication**. The legacy article's five behavioural segments (`High-Growth HDB`, `Stable Mid-Tier`, `Premium Condo (Low Yield)`, `High-Yield Apartments`, `Luxury Segment`) have no membership anywhere in this checkout: no column carries them and no stored mapping assigns a transaction to one. The served asset holds **six different segments**, and its six counts reproduce no measured population here — not the frame, not any window of it, not even the rows inside each segment's own declared planning areas. So this edition does not restate a taxonomy with new numbers; it measures the stored asset, states what the cohort counts are and are not, and disposes every quantitative claim of the old text — **36 claims, 1 re-measured, 4 withdrawn, 31 not reproducible** (`legacyClaims`).

Every figure below comes from the canonical ledger [`artifacts/rs10-market-segments-evidence.json`](../../../../implementation/artifacts/rs10-market-segments-evidence.json) — sha256 `d8f0658807b4864c049481d289f7dd1312be8fb052eeddcbdcdb5c6e0b0f8c56`, 102,883 bytes — re-measured byte-identically from this checkout by `uv run python scripts/tools/market_segments_evidence.py --check`. The terminal month, 2026-11, holds 421 private-row transactions — 0.1974 of the trailing-12-month median of 2,133.0 (`cutoff`) — and is excluded as partial; every window and share below stops at **2026-10**.

## The register gate, clause by clause

RS10 is judged against its research-register row (`docs/plans/2026-11-12-reporting-refresh-research-register.md`, RS10). The row's first two sentences are quoted verbatim: *"Recover feature scaling, clustering/model version and cohort counts; assess stability and map old/new segment identities. Do not reuse a segment ID for a different population."* Its third sentence requires the app's matching weights to stay unchanged unless a change is separately authorised by the owner; that sentence is paraphrased here rather than quoted, so that a draft carries no assertion about an authorisation that has not been given — the requirement itself is unchanged and is answered in the table's last row.

| Gate clause | Where it is answered | Outcome |
| --- | --- | --- |
| Recover feature scaling | `methodRecovery.items.featureScaling`; the scan at `methodRecovery.tokenScan` | `notRecorded` — no scaler, offset or transformed-column list is stored for the article's six-segment method; preprocessing artefacts exist elsewhere as **data**, which is why the absence is stated narrowly (§7) |
| Recover clustering/model version | `methodRecovery.items.modelVersion`, `clusteringArtefacts` | `notRecorded` as a model version — the asset's `version` is its own payload label (`1.0.0`), and the documented `Cluster Version: 2.0 (PSF-based)` label is not a library version. A clustering **artefact** does exist and corresponds to the asset's names and shares (§6) |
| Recover cohort counts | `cohortReconciliation` | counts are recorded as the asset's own figures, `notReproducible` against any measured population; internally consistent arithmetic (§4) |
| Assess stability | `notMeasurable.stabilityEvidence` | `notRecorded` — the asset's only stability-shaped field is a per-label constant, not a measured transition rate (§11) |
| Map old/new segment identities | `methodRecovery.legacyIdentityRecovery`, `membershipRecovery`, `dashboardAssetContrast` | `notReproducible` — the legacy names carry no id, so there is no old id set to map; the six asset ids match zero stored values and zero dashboard identifiers (§5, §8) |
| Do not reuse a segment ID for a different population | `notMeasurable.oldToNewIdentityMapping` | satisfied by absence of a source: reusing an old id is not merely prohibited here, there is no old id set in existence to reuse |
| app matching weights unchanged unless separately authorised | `appMatchingWeights` | recorded and sha256-pinned; this study changes no app code and no authorisation for a change is recorded (§10) |

## What the numbers in this edition are — and are not

Three reading rules bind every figure here.

**The asset's counts are the asset's own numbers.** The six `transactionCount` values are consistent with their own `marketShare` values and with nothing else (§4). Where this edition reports a count, it reports a stored field; where it reports row counts from the transaction frame, it says so and names the window.

**The token scan is a search, not a proof of absence.** It reports where a method token appears in the scanned roots and lists the matches (`methodRecovery.tokenScan.tokens.<token>`). A zero match is counter-evidence for *"no implementation was found on this surface"* and never for *"no such analysis was ever run"*; the scan's breadth is a recorded field (`tokenScan.filesScanned`, `roots`, `suffixes`, `excludedPrefixes`), not a claim of this page.

**A correspondence is not a lineage.** Where the stored profile output matches the asset's names and shares, this edition says *corresponds* and states exactly what is linked and what is not (§6). Nothing in the checkout ties those profiles to the code that wrote the asset, and no sentence here converts a correspondence into a parentage.

**Four kinds of nothingness, kept apart.** A **null value** (the row exists, the field does not), a **recorded zero**, an **absent row**, and an **absent column** are counted and reported separately and are not interchangeable. This matters at three places: `market_segment`'s 990,655 nulls are the HDB rows of a private-only label, not missing data (§5); the 50,913 frame rows outside the asset's areas are two distinct populations — 39,313 rows in 13 planning areas the asset does not name, and 11,600 rows with no planning area at all (§5); and the absence of per-transaction membership for the six stored segments is an **absent column**, not a null in a present one (§5).

## The stored asset: six segments and their own numbers

`app/public/data/segments_enhanced.json.gz` — 3,432 bytes, sha256 `76979cc5fdc4e7fff27847147b70520f896c3f344d701f4ef702c252dd571d56`, `version "1.0.0"`, `lastUpdated 2026-04-19T23:23:07.521202`, top-level keys `insights, lastUpdated, planningAreas, segments, version` (`segmentAsset`). Six segments, ids unique, metrics present on every one, four insight cards, 31 planning areas:

| id | name | stored count | share | avg psf | avg yield | `yoyGrowth` | `persistenceProbability` | classification | declared areas |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `large_size_stable` | Large Size Stable | 114,700 | 0.126 | 570.0 | 5.54 | 12.0 | 0.6 | HH | 10 |
| `high_growth_recent` | High Growth Recent | 300,872 | 0.330 | 509.0 | 5.20 | 24.4 | 0.6 | HH | 10 |
| `speculator_hotspots` | Speculator Hotspots | 51,957 | 0.057 | 550.0 | 4.80 | 83.9 | 0.6 | HH | 10 |
| `declining_areas` | Declining Areas | 112,943 | 0.124 | 564.0 | 5.00 | −3.6 | 0.33 | LH | 10 |
| `mid_tier_value` | Mid-Tier Value | 230,685 | 0.253 | 463.0 | 6.36 | 8.5 | 0.5 | LL | 1 |
| `premium_new_units` | Premium New Units | 100,297 | 0.110 | 826.0 | 3.80 | 12.3 | 0.6 | HH | 10 |

(`segmentAsset.segments`; the six counts sum to 911,454, the asset's own cohort total.) The article's heading claims five segments; the asset holds six, and **none of the article's five names appears in it** (`segmentAsset.segmentIds`, `methodRecovery.legacyIdentityRecovery.legacyNamesInAsset: []`).

Three of the stored fields invite a reading this edition does not support:

- **`persistenceProbability` is a per-label lookup, not a transition rate.** It takes exactly three values, constant within each `clusterClassification` — 0.6 for the four HH segments, 0.33 for `declining_areas` (LH), 0.5 for `mid_tier_value` (LL) (`segmentAsset.persistenceByClassification`) — and the generator body cited in `methodRecovery.generatorProvenance` assigns it from the label. No transition matrix, no period-to-period comparison and no measured persistence exists here.
- **`yoyGrowth` is the asset's own field.** `speculator_hotspots` at 83.9 and `declining_areas` at −3.6 are stored values; no window, base period or population is recorded with them, and the frame carries no segment membership to recompute either from.
- **The asset's internal correlations describe the asset, not the market** (`segmentAsset.internalCorrelations`): across the six segment rows, `avgYield` against `yoyGrowth` gives Pearson r = −0.1869 (n = 6); across the 31 area rows, `avgYield` against `avgPricePsf` gives −0.1158, `avgYield` against `forecast6m` gives 0.7726, and `avgPricePsf` against `forecast6m` gives 0.2443 (n = 31 each). These are measurements of the stored fields' mutual consistency, not re-measurements of any market relationship.

## Cohort arithmetic: consistent with itself, reproducible against nothing

The six counts close on their own shares and on nothing else (`cohortReconciliation`):

| Segment | stored count | share | count ÷ own total | residual | implied denominator | rows in its declared areas | difference |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `large_size_stable` | 114,700 | 0.126 | 0.125843 | +0.000157 | 910,317.5 | 176,470 | +61,770 |
| `high_growth_recent` | 300,872 | 0.330 | 0.330101 | −0.000101 | 911,733.3 | 319,455 | +18,583 |
| `speculator_hotspots` | 51,957 | 0.057 | 0.057005 | −0.000005 | 911,526.3 | 176,470 | +124,513 |
| `declining_areas` | 112,943 | 0.124 | 0.123915 | +0.000085 | 910,830.6 | 577,562 | +464,619 |
| `mid_tier_value` | 230,685 | 0.253 | 0.253096 | −0.000096 | 911,798.4 | **33** | **−230,652** |
| `premium_new_units` | 100,297 | 0.110 | 0.110041 | −0.000041 | 911,790.9 | 176,470 | +76,173 |

The shares sum to 1.0 with a residual of 0.0, and every segment's share equals its count over the asset's own total within the three-decimal rounding tolerance of 0.0005 (`marketShareSum`, `shareRoundingTolerance`). That is the whole of what the arithmetic establishes. Each segment's stored count is **not** the number of rows inside the planning areas it declares, and for `mid_tier_value` the two differ by a factor of nearly seven thousand — its single declared area, Lim Chu Kang, holds 33 transactions against a stored count of 230,685.

No measured population equals the cohort total either:

| Candidate population | rows | difference from 911,454 |
| --- | ---: | ---: |
| Full frame (1990-01 → 2026-11) | 1,236,310 | +324,856 |
| Article's stated period (2017-01 → 2026-10) | 489,101 | −422,353 |
| Article's emphasis window (2021-01 → 2026-10) | 401,512 | −509,942 |
| Asset's `lastUpdated` month cap (2021-01 → 2026-04) | 376,256 | −535,198 |
| Private rows only | 245,655 | −665,799 |
| The adjacent segmented panel (§5a) | 911,797 | **+343** |

(`cohortReconciliation.candidatePopulations`; the adjacent panel is listed here on purpose, so the near-match is visible beside the other candidates rather than only in its own block.) The nearest candidate overall is 343 rows away and is a different taxonomy; of the same-taxonomy candidates the closest is the full frame at 1,236,310 rows, 324,856 away, and among the article- and asset-dated windows the closest is the article's stated 2017-01 → 2026-10 period at 489,101, 422,353 away. The only recorded denominator for these counts is a comment hard-coded beside a literal in the plan document that holds them — `"transactionCount": 114700,  # 12.6% of ~910K` (`cohortReconciliation.recordedDenominator`) — and the ledger's verdict is that the counts are the asset's own unverified figures, recorded as inspection-only (`definition`).

## Membership: zero id matches, and a many-to-many area block

**The six ids occur zero times as stored values.** The 97-column frame was read for exact string equality between each of the six ids and every distinct non-null value of the three segment-shaped columns (`membershipRecovery.segmentIdMatchesInColumns`): `market_segment` 0, `property_segment` 0, `price_stratum` 0, total **0**. This is a count of matches, not a claim that data is missing.

What those three columns actually hold:

| Column | distinct values | nulls | what it is |
| --- | ---: | ---: | --- |
| `market_segment` | 3 | 990,655 | the three national region labels expanded — `Core Central Region` 38,699, `Rest of Central Region` 74,161, `Outside Central Region` 132,795; populated on the 245,655 private rows only, so the nulls equal the HDB rows exactly (`marketSegmentIsARegionLabel`) |
| `property_segment` | 5 | 0 | `hdb` 990,655, `condominium` 103,395, `apartment` 101,856, `ec` 30,409, `other_private_residential` 9,995 — a property-type label, not a behavioural cluster |
| `price_stratum` | 5 | 0 | `Q1` 248,224, `Q2` 246,566, `Q3` 247,866, `Q4` 246,398, `Q5` 247,256 — a price quintile, not a behavioural cluster |

`market_segment` is the trap: its name is the article's subject, and its values are regions. A query that reads it as segment membership reads a CCR/RCR/OCR split, and joining it to the article's five names is a name collision, not a join.

**The asset's own membership is many-to-many at planning-area granularity.** Its `planningAreas` block pairs 31 area names with segment name lists, 51 pairs in all, and the two directions (area→segments and segment→areas) agree exactly — symmetric difference empty (`segmentAsset.planningAreaMembership`). The shape is the finding:

- areas by segment count: 6 areas map to **no** segment, 15 map to 1, 4 map to 3, 6 map to 4 — so a planning area can be described by up to four segments at once;
- pairs per segment: ten each for `large_size_stable`, `high_growth_recent`, `speculator_hotspots`, `declining_areas` and `premium_new_units`, and **one** for `mid_tier_value`;
- six areas — Bedok, Bukit Batok, Bukit Panjang, Geylang, Jurong East, Marine Parade — carry no segment at all.

Joined to the frame on `planning_area` (`membershipRecovery.areaLevelJoin`), all 31 asset areas are present among the frame's 44 values, covering **1,185,397** rows; 50,913 rows sit outside, of which **39,313** are in 13 planning areas the asset never names (Central Water Catchment, Changi, Downtown Core, Mandai, Museum, Novena, Outram, Rochor, Seletar, Singapore River, Southern Islands, Sungei Kadut, Tengah) and **11,600** carry no planning area. A many-to-many area block assigns no transaction to a single segment: it cannot serve as per-transaction membership, and it is why the article's per-segment bands have nothing to be computed over.

### 5a. A per-transaction segmented panel *does* exist — and it is not this taxonomy

An earlier draft of this evidence nearly stated that no per-transaction segmentation exists in the checkout. That would have been false, and the record now says so explicitly (`adjacentSegmentedPanel`, `notMeasurable.perTransactionMembership.reason`).

`data/analysis/market_segmentation/housing_unified_segmented.parquet` holds **911,797 rows across 61 columns**, 1990-01 → 2026-01, with three price tiers assigned per row plus a `market_tier_period` / `psf_tier_period` variant, defined by a cut-point file (`tier_thresholds.csv`, sha256-pinned; HDB cuts at 208,000 and 390,000, condominium at 1,306,400 and 2,091,000, EC at 1,229,000 and 1,520,000). Its tier distributions are exhaustive — `market_tier` Mass Market 273,615, Mid-Tier 368,370, Luxury 269,812; `psf_tier` Low 273,565, Medium 364,770, High 273,462.

It carries **none of the six asset ids** — 0 matches across all 61 columns — and its labels are price tiers, not behavioural clusters. So the two statements that hold are precise: *the six stored segments have no per-transaction membership*, and *a per-transaction segmentation of a different kind does exist in this checkout*. Its row count is the 911,454 + **343** candidate above. A second directory, `data/analysis/market_segmentation_period/`, holds another period-labelled panel of the same size with two tier-threshold files; it also carries none of the six ids, and its threshold files are why no sentence in this edition may call the first cut-point file the only preprocessing artefact in the checkout.

## Provenance: literals in a plan document, and a measured correspondence to cluster profiles

Two separate things are true, and neither substitutes for the other.

**The asset's segment objects are hand-written literals.** They appear as literal dicts in the generator body of `docs/plans/2026-02-22-interactive-market-segments-dashboard-implementation.md` (sha256 `961f173e…`), beside the `~910K` denominator comment above; the handoff that records running that generator (`.claude/handoffs/2026-02-23-interactive-segments-dashboard-implementation.md`, sha256 `c0487e94…`) describes hand-written loaders and reports producing "6 segments, 31 planning areas, 4 insight cards" (`methodRecovery.generatorProvenance`). The generator script the plan describes is **not** in the checkout (`generatorScriptExists: false`).

**A PSF-based clustering artefact corresponds to those names and shares.** `data/analysis/market_segmentation_2.0/cluster_profiles.csv` (3,541 bytes, sha256 `46109df8…`) holds six KMeans cluster profiles whose names map 1:1 onto the six asset ids and whose `cluster_percentage` values reproduce the asset's `marketShare` values at three decimals — **6 of 6 names, 6 of 6 shares** (`clusteringArtefacts.nameSlugMatches`, `shareMatches`):

| profile `segment_name` | derived id | cluster count | cluster % | asset share | avg psf | avg `yoyChangePct` |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Large Size Stable | `large_size_stable` | 12,038 | 12.601145 | 0.126 | 570.39 | 8.271 |
| High Growth Recent | `high_growth_recent` | 31,504 | 32.977777 | 0.330 | 509.081 | 24.418 |
| Speculator Hotspots | `speculator_hotspots` | 5,468 | 5.723796 | 0.057 | 550.45 | 83.935 |
| Declining Areas | `declining_areas` | 11,866 | 12.421099 | 0.124 | 564.013 | −3.634 |
| Mid-Tier Value | `mid_tier_value` | 24,189 | 25.320577 | 0.253 | 462.757 | 27.75 |
| Premium New Units | `premium_new_units` | 10,466 | 10.955606 | 0.110 | 826.462 | 12.289 |

That is a **correspondence**, and its limits are exact. The profiles are aggregate cluster summaries: their cluster counts total 95,531 against the asset's own total of 911,454 (`clusteringArtefacts.clusterCountTotal`, `.assetCohortTotal`) — the asset's counts are larger by a factor of 9.54. They are also neither the profile counts nor a constant multiple of them — the per-segment ratio runs **9.502 to 9.5831** (`clusteringArtefacts.countRatios`), so no single scale factor relates the two, and each figure was approximated separately. Nothing in the directory links these profiles to the code that wrote the asset.

### 6a. The selection sweep is stored, unlinked, and cuts both ways

`optimal_clusters.png` (281,872 bytes, sha256 `113e4cf1…`) prints an elbow marker at **K=7** and a silhouette maximum at **K=2** across a sweep of K = 2 to 10; `clusters_pca.png` (4,960,984 bytes, sha256 `08bf618b…`) is titled "Market Segments - PCA Visualization (K=2)". Both are recorded as a **human visual read** of the sha-pinned images, not a machine measurement and not a re-derivation from pixels (`clusteringArtefacts.visibleAnnotations`).

Nothing links either plot to the six-row profile run, and the limitation is symmetric: the sweep does **not** establish what the stored six-cluster solution scored, and it equally does **not** establish that six was a poor choice. What it records is narrower — a K-selection sweep exists whose annotations are K=2 (silhouette maximum) and K=7 (elbow); it annotates neither as K=6, and whether it is the same run as the stored profiles is unestablished (`runLinkage`). For the same reason the article's `5-cluster solution` claim is neither supported nor refuted by it: the sweep plots a K=5 point, and that point's relationship to the article's method is unknown.

### 6b. The one documented version label

An archive document records `_Cluster Version: 2.0 (PSF-based)_` (`docs/archive/20260124-market-insights-fixes-complete.md` line 156, sha256 `06b01a6a…`) and names `scripts/quick_cluster_profiles.py` as the script that updated the log transformation to a square-foot basis. That is a **documented label and a documented intent**: it is not a model-library version, not the identity of the fitted run behind the profile CSV, and the script it names is not in the checkout, so its parameters are not recoverable (`clusteringArtefacts.documentedVersion`; `methodRecovery.items.logTransform`).

## What of the legacy method is recorded

| Gate input | Status | What exists |
| --- | --- | --- |
| Feature set (six derived features) | `recorded` | the article's names, matched against the shipped schema (§11) |
| `k` | `recorded` as a count | six segment objects and six list literals — a stored count, not evidence that a K was selected (`methodRecovery.items.k`) |
| Persistence | `recorded` | a per-label constant lookup (§3) |
| Feature scaling | `notRecorded` | no scaler object, mean/scale vector or fitted transformer for this method |
| Log transform | `notRecorded` | no log/offset parameter or transformed-column list; documented intent only (§6b) |
| Clustering model version | `notRecorded` | no model-library version, no fitted parameters (§6) |
| Clustering implementation | `notRecorded` | no call site for MiniBatchKMeans, AgglomerativeClustering or PCA under `scripts/` or `src/`; the products exist as stored files (§6) |
| Silhouette outputs | `notRecorded` | an unlinked sweep only (§6a) |
| Elbow outputs | `notRecorded` | the same unlinked sweep |
| Composite investment score | `notRecorded` | prose weights only; no implementation, score vector or normalisation parameters for this population (§11) |
| Risk-adjusted momentum | `notRecorded` | prose ratio only; no rolling window, no numerator or denominator series |

The token scan behind the four implementation absences searches the shipping surface for seven tokens and lists every matched file with its line and quote (`methodRecovery.tokenScan`). It excludes the programme's own instruments — its own file, `scripts/tools/`, `prompts/`, `docs/implementation/` and published edition texts — and those exclusions are recorded in the ledger rather than implied (`excludedPrefixes`, `excludedPaths`, `excludedEditionTexts`). It reports zero matches for `log1p` and small, enumerated hit counts for the others; `MiniBatchKMeans`, `AgglomerativeClustering` and `elbow` occur only in the legacy article and in plan documents. The most important disclosure is inside the ledger's own `meaning`: the hits are **not** claimed to be uniformly prose or false positives — `docs/plans/2026-02-19-pipeline-improvements-plan.md` contains a KMeans/StandardScaler code **example**, counted among the hits, and it is an illustration in a plan rather than evidence that this study used that model. Nothing connects it to the shipped values.

## The served dashboard asset: no shared identity

The gate's mapping clause has a second surface to check, and it fails the same way (`dashboardAssetContrast`). `app/public/data/dashboard_segments.json.gz` — 6,080 bytes, sha256 `69d7a3d2…`, 16 top-level keys — is a bubble chart: rows carry `category`, `name`, `x`, `y`, `z`, with no id field at all (`hasSegmentIdField: false`, `segmentIds: []`). Its identifiers are planning-area × property-type composite names (84 distinct), its categories are the three property types, and the intersection with the asset's six ids is **zero** (`sharedIds: 0`) — empty by construction as well as by measurement.

Three readings of that asset are traps:

- **Four of its 16 keys are empty** — `pre_covid`, `pre_covid_condo`, `pre_covid_ec`, `pre_covid_hdb` carry 0 rows, and an empty key is not a zero count.
- **Four key pairs carry identical payloads** — `recent` ≡ `whole`, `recent_condo` ≡ `whole_condo`, `recent_ec` ≡ `whole_ec`, `recent_hdb` ≡ `whole_hdb` — so "recent" and "whole" are the same stored data under two labels in this file (`identicalPayloads`).
- **Its `z` total is 333,555**, matching neither the frame's 1,236,310 rows nor the asset's 911,454 (`countPopulation`), so it cannot reconcile either.

## The CAGR table: the window is a property-type question

The legacy table is headed `CAGR by planning area (2015-2025)` and mixes property types. The window does not exist across them (`cagrWindow.perPropertyType`, `window2015to2025`):

| Property type | rows | distinct months | first month | 2015-2025 window | months observed / expected | rows in window |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| HDB | 990,655 | 443 | 1990-01 | **available** | **132 / 132** | 259,219 |
| Condominium | 245,655 | 71 | **2021-01** | **not available** | 60 / 132 | 224,404 |

The private rows begin in 2021-01, so an all-property-type 2015-2025 area CAGR cannot be measured from this frame at all; the HDB rows span the window completely. Applying the legacy's **own stated definition** — 10-year compound annual growth rate by planning area, minimum 50 transactions per area — to the HDB rows, on median psf per area-year, with the floor required at **both** endpoint years (`cagrWindow.areaCagr.definition`), gives five measurable areas out of the six the article names:

| Area | start year median psf (rows) | end year median psf (rows) | HDB CAGR | legacy band | within band? |
| --- | ---: | ---: | ---: | --- | --- |
| Queenstown | 571.71 (485) | 920.18 (599) | **4.87%** | `~4-6%` | **yes** |
| Jurong East | 406.77 (399) | 545.25 (482) | 2.97% | `~4-6%` | no |
| Punggol | 396.95 (628) | 686.68 (1,538) | 5.63% | `~3-5%` | no |
| Sengkang | 396.54 (1,176) | 641.33 (1,905) | 4.93% | `~2-4%` | no |
| Woodlands | 344.29 (1,228) | 531.81 (1,748) | 4.44% | `~1-3%` | no |
| Bukit Timah | 610.87 (**39**) | 821.35 (60) | — | `~5-7%` | `notMeasurableUnderLegacyFloor` |

Of the five areas the article's own floor permits, **four fall outside** the band it published (Jurong East, Punggol, Sengkang, Woodlands) and **one falls inside** (Queenstown); the sixth, Bukit Timah, is not measurable at all. Refusing Bukit Timah is a measurement, not a gap: its 2015 endpoint holds 39 transactions, below the floor the article itself declares, and the ledger records the refusal rather than a number derived under a weakened floor (`cagrWindow.areaCagr.rowsSatisfyingFloor: 5`; `areas[].withinLegacyBand` is `null` for that area).

This is a re-measurement of the **HDB subset**, not of the article's mixed-property-type table (`areaCagr.meaning`). Each row's quoted psf band and its segment label are disposed separately below: they rest on a membership that does not exist, which is a different defect from a window that does not exist.

## Absences, each with its boundary and its scan

Every absence below names the surface searched, so a reader can re-run the search rather than trust the sentence (`methodRecovery.tokenScan`; each entry's `reason` in `notMeasurable`).

| Absent thing | Boundary of the search | Recorded as |
| --- | --- | --- |
| Feature scaling for this method | the shipping Python surface, seven tokens, matches listed | `methodRecovery.items.featureScaling` `notRecorded` |
| A clustering model version and its fitted K | the same surface, plus every stored file under `data/analysis/market_segmentation_2.0/` | `modelVersion` `notRecorded` |
| Stability or cross-validation evidence for the six-cluster run | the same surface, plus the two sha-pinned plots read by eye | `stabilityEvidence` `notRecorded` |
| Cohort counts as verified populations | five frame windows plus the adjacent panel, each with its row count | `cohortCountsAsVerifiedPopulations` `notReproducible` |
| Per-transaction membership **for the six stored segments** | the frame's 97 columns, three segment-shaped columns, exact string equality | `perTransactionMembership` `notRecorded` |
| An old→new identity mapping | every line in the scanned roots pairing a legacy name with an id field: **0** | `oldToNewIdentityMapping` `notReproducible` |
| A composite investment score for this population | the same surface, plus the archive precedents' parameters | `compositeScore` `notRecorded` |
| A risk-adjusted momentum series | the same surface, plus the archive's published scores and their missing window | `riskAdjustedMomentum` `notRecorded` |

Two of these absences are deliberately narrow, because the checkout does hold precedents and a bare "nothing exists" would have been false (`methodRecovery.items.compositeScore.relatedPrecedent`, `methodRecovery.items.riskAdjustedMomentum.detail`):

- **The composite score.** `docs/archive/20260123-hdb-comprehensive-investment-analysis.md` records a 50/50 appreciation/yield composite with per-town score vectors (`ANG MO KIO 100.0`, `PUNGGOL 94.3`) over **785,395 HDB transactions, 1990-2026, 2015-2025 focus**, and it states the **same procedure** the article states (z-scores, 50/50 weights, scaled 0-100). It records too few parameters to decide whether its normalisation is equivalent, so no difference in normalisation is claimed. What differs, measurably, is population and period: HDB resale only and 1990-2026 there, against the article's all-property-type framing and 2017-2026 window.
- **Risk-adjusted momentum.** The same archive publishes a per-area Risk-Adjusted Score table — `TANGLIN 0.822` on a sample of **10**, `SEMBAWANG 0.526` on **1,457** — on HDB resale over 1990-2026, without recording its volatility window. Those values cannot stand in for the article's measure on its own population and with no rolling window defined.

## The legacy feature list, matched against the shipped schema

The article's six derived features are recorded, which makes them checkable rather than merely quotable (`methodRecovery.items.featureSet.featureMap`; the schema is the 97-column platinum frame):

| Article's feature | Status in the frame |
| --- | --- |
| `floor_area_sqm` | present verbatim |
| `rental_yield_pct` | present verbatim |
| `price_psm` | present under a different name — `Unit Price ($ PSM)` |
| `mom_change_pct` | **absent** |
| `remaining_lease_months` | **absent** |
| `yoy_change_pct` | **absent** |

Three of the six named features have no counterpart column. That is a scope fact about the frame, and it is one of the reasons the article's clustering cannot be re-run here even before asking what K was chosen.

## Superseded figures

Every quantitative claim in the old text, its status, and the measured reason. Quoted phrases are verbatim from [`legacy/2026-11-12/market-segments.md`](../../legacy/2026-11-12/market-segments.md) and each is machine-checked against the frozen file (`legacyQuoteCheck`: **36 of 36 found**, `allQuotesFound: true`). Every claim's ledger key resolves against the ledger at build time (`claimKeyCheck`: 36 checked, 0 unresolved — resolution is syntactic and does not judge whether the resolved field supports the disposition). Statuses are the ledger's own (`legacyClaims.<id>.status`): **re-measured** means the claim was answered with a measurement of this checkout, **withdrawn** means the claim is not made by this edition, **`not-reproducible`** means the artefact the claim would need is not in this checkout, or does not exist in the form the claim assumes — a measured absence with the search recorded, not a silent omission.

| Legacy claim (as the old text states it) | Status | Measured reason |
| --- | --- | --- |
| "Five behavioral segments emerge from clustering" | withdrawn | the shipped asset holds six segments, not five, and the five names appear in none of its ids (`segmentAsset.segmentCount`) |
| "High-Growth HDB" profile row — `$450-550` psf, `4-5%` yield, `8-15%` appreciation | `not-reproducible` | no membership exists to compute a psf, yield or appreciation band for any named segment, and the name has no counterpart id in the asset (`membershipRecovery.perTransactionMembership`) |
| "Stable Mid-Tier" profile row — `$500-700`, `3-4.5%`, `3-7%` | `not-reproducible` | a stored band with no segment population behind it and no matching id |
| "Premium Condo (Low Yield)" profile row — `$1,200-2,000`, `2-3%`, `4-8%` | `not-reproducible` | same; "Premium Condo" resembles no asset name and no asset id |
| "High-Yield Apartments" profile row — `$800-1,200`, `4-6%`, `5-10%` | `not-reproducible` | no membership, no id, no population |
| "Luxury Segment" profile row — `$2,000+`, `1-2.5%`, "Variable" | `not-reproducible` | same, and "Variable" is an open-ended band that no measurement can confirm or refute |
| "CAGR by planning area (2015-2025)" | `not-reproducible` | the HDB rows span the window and the private rows begin in 2021-01, so an all-property-type 2015-2025 area CAGR is not measurable from this frame (`cagrWindow.window2015to2025`) |
| "10-year compound annual growth rate by planning area, minimum 50 transactions per area" | **re-measured** | adopted verbatim as the ledger's own area-CAGR definition and applied to the HDB rows, with the floor required at both endpoint years (`cagrWindow.areaCagr`) |
| "Bukit Timah" CAGR row | `not-reproducible` | refused under the article's own floor — the 2015 endpoint holds 39 transactions — and the row's psf level and "Luxury" label rest on a membership that does not exist |
| "Queenstown" CAGR row | `not-reproducible` | the HDB subset measures 4.87%; the row mixes property types and labels a segment with no membership |
| "Jurong East" CAGR row | `not-reproducible` | same, measuring 2.97% on the HDB subset |
| "Punggol" CAGR row | `not-reproducible` | same, measuring 5.63% |
| "Sengkang" CAGR row | `not-reproducible` | same, measuring 4.93% |
| "Woodlands" CAGR row | `not-reproducible` | same, measuring 4.44% |
| "50% appreciation z-score + 50% yield z-score, normalized to 0-100" | `not-reproducible` | no composite-score artefact or implementation exists for this article's score; the weights are stated only in prose (`methodRecovery.items.compositeScore`) |
| "0-19" score band — "Weak", "Depreciating or oversupplied areas" | `not-reproducible` | the score bands have no definition, no artefact and no area list behind them |
| "with >85% agreement on cluster assignments" | `not-reproducible` | no hierarchical validation run, agreement table or assignment artefact is stored; `AgglomerativeClustering` occurs only in the legacy article and in plan documents (`tokenScan.tokens.AgglomerativeClustering`) |
| "(r ~ -0.3)" | `not-reproducible` | the cited sentence does not specify its observational unit — within clusters, across transaction records, or across segment summaries — so the statistic is **underspecified and not reproducible**, and this edition does not prescribe what its unit was. Separately: the six segment rows give r = −0.1869 for `avgYield` against `yoyGrowth` (`segmentAsset.internalCorrelations`), which is a different quantity on a different unit |
| "~288K records (2021-2026 emphasis)" | `not-reproducible` | the measured row counts for the article's own windows are recorded; none equals the stated volume and none equals the asset's cohort total (`cohortReconciliation.candidatePopulations`) |
| "provides the best balance of interpretability and granularity based on silhouette analysis" | `not-reproducible` | no silhouette result is linked or attributable to the claim. A silhouette curve **is** stored (maximum marked at K=2 on an unlinked sweep), and that artefact is neither evidence for nor against the statement (§6a) |
| "Log-transform for skewed variables, StandardScaler normalization" | `not-reproducible` | no scaler parameters, offset or transformed-column list is stored for this method; the PSF-based profile run is unlinked to it and its own scaling is unknown, so it bears neither for nor against the claim. Preprocessing artefacts exist as data elsewhere, which is why the absence is stated narrowly |
| "Cluster assignments per transaction with segment labels" | withdrawn | no assignment **of the six stored segments** exists in any column of the frame; a different, three-tier per-row segmentation does exist under `data/analysis/` (§5a) |
| "**Data Period**: 2017-2026, with emphasis on 2021-2026" | withdrawn | the private rows begin in 2021-01, so 2017-onwards coverage exists only for the HDB rows, and the period cannot describe the asset's mixed population (`cagrWindow.perPropertyType`) |
| "clusters are defined on 2021-2026 data and may shift as market conditions change" | `not-reproducible` | the stated window is measurable for the private rows, but the asset's cohort total reproduces no measured window, so the definition window cannot be confirmed for the stored clusters |
| "80-100" score band — "Exceptional", "Emerging towns with new MRT lines" | `not-reproducible` | the score is described only in prose, so the band cannot be recomputed for this population; the archived HDB analysis carries score vectors for a different population and period |
| "60-79" score band — "Strong", "Mature estates with good yield" | `not-reproducible` | the score definition has no implementation to re-run |
| "40-59" score band — "Average", "Most established areas" | `not-reproducible` | same |
| "20-39" score band — "Below average", "Luxury areas (low yield offsets appreciation)" | `not-reproducible` | same, and the interpretation itself is an unsupported explanation: no yield/appreciation decomposition for this band and population is available |
| "Hold & Grow" strategy row — `>6%` yield, `>10%` growth | `not-reproducible` | a screen defined against thresholds whose population is not recoverable; six aggregate yield/growth pairs exist, one of which meets both thresholds, but they are unlinked to the article's strategy populations |
| "Yield Play" strategy row — `>6%` yield | `not-reproducible` | the threshold is defined; the population it screens is not recoverable |
| "Growth Play" strategy row — `>15%` YoY | `not-reproducible` | no membership means no YoY series can be attributed to a segment |
| "Value Investing" strategy row — `<5,000 PSF` | `not-reproducible` | the only strategy whose screen could be evaluated against transactions, but it is attributed to segments with no membership, so the claim is about a population this checkout cannot build |
| "most areas cluster around 2-5%" | `not-reproducible` | a distributional claim over planning areas; CAGR is measured only for the six named areas under the article's own floor, which cannot characterise a distribution |
| "A town with 4-5% CAGR and affordable entry is often a better long-term bet" | withdrawn | advice, not a measurement; the ledger reports the measured CAGR per named area with no return, risk or affordability comparison behind the recommendation |
| "Risk-adjusted momentum (YoY change divided by price volatility)" | `not-reproducible` | the ratio is defined in prose only — no rolling window, no numerator or denominator series, no per-area value for this population; the archive's per-area Risk-Adjusted Scores are a different population and omit their window |
| "YoY change divided by rolling price volatility" | `not-reproducible` | the methodology restates the ratio; the rolling window it names is never specified and no momentum series is stored |

## What this edition does not establish

- **No behavioural segmentation of this market.** The six stored segments have no membership; the frame's segment-shaped columns are a region label, a property-type label and a price quintile (§5).
- **No verified cohort.** The six counts close against their own shares and against nothing else; they are the asset's own figures, not measured populations (§4).
- **No old→new identity mapping.** The legacy names carry no id, so there is no id set to map, and the asset's six ids share nothing with the served dashboard asset (§5, §8).
- **No lineage for the segment values.** That the stored profiles correspond to the asset's names and shares is measured; that they are the asset's parent is not, and this edition asserts only the first (§6).
- **No reading of the selection sweep in either direction.** The stored plots mark K=2 and K=7 on an unlinked sweep; they do not score the stored six-cluster run and do not show that six was a poor choice (§6a).
- **No stability, transition or persistence measurement.** The only stability-shaped field is a per-label constant (§3, §11).
- **No composite investment score and no momentum series** for this population, and no claim that the archive precedents are or are not the same computation — only that they cover a different population and period and record too few parameters to decide (§11).
- **No 2015-2025 CAGR for any property type except HDB**, and none at all for Bukit Timah under the article's own floor (§9).
- **No re-measurement of the article's strategy or score tables.** Their thresholds are quoted and their populations are not recoverable; nothing here fills them in.
- **No change to the app's matching weights**, and no authorisation for one (§10).
- **No statistical fit of any kind.** No model is refitted, no cluster is re-identified, and no segment taxonomy is proposed to replace the withdrawn one (`definition`).
- **No completeness claim beyond scope.** What was measured is the stored segment asset and its arithmetic, what membership can and cannot be joined to the frame, the dashboard asset's identity intersection, the provenance of the asset's literals and its correspondence to the profile output, the CAGR window per property type, and the app's matching weights (`scope`) — nothing outside that surface is asserted.

## Reading this edition

- **Investors:** the article's five behavioural segments cannot be located in any data here, and the six served segments cannot be priced — no transaction carries one of their ids, and each segment's stored count is not the number of rows in the areas it declares (one segment's declared area holds 33 rows against a stored count of 230,685). What survives measurement is narrower: an HDB area-level CAGR for five of the article's six named areas under the article's own 50-transaction floor — Queenstown 4.87%, Jurong East 2.97%, Punggol 5.63%, Sengkang 4.93%, Woodlands 4.44% — and the withdrawal of the strategy and score tables those areas were used to sell.
- **First-time buyers:** the "Value Investing" and "Balanced Approach" rows are withdrawn, not softened — they are attributed to segments with no membership and rest on a composite score that has no implementation for this population. The measured HDB area CAGRs above are descriptive price paths of a median, not entry-cost or affordability measures, and nothing here recommends a town.
- **Upgraders:** there is no segment to map your current property to and no target segment to compare against. The article's upgrade guidance was built on the five-name taxonomy; the asset that replaced it carries six different names with no per-transaction membership, and the legacy names occur only as prose — no line anywhere pairs one with an id (§11).

## Data and inputs (`inputs`, sha256-pinned)

| Path | Rows / bytes | sha256 |
| --- | ---: | --- |
| `app/public/data/segments_enhanced.json.gz` | 3,432 | `76979cc5fdc4e7fff27847147b70520f896c3f344d701f4ef702c252dd571d56` |
| `app/public/data/dashboard_segments.json.gz` | 6,080 | `69d7a3d266452811d8153f009c1df0baa4e6b91bc48ec3bc78d7ffe745373a24` |
| `data/analysis/market_segmentation/housing_unified_segmented.parquet` | 911,797 × 61 cols | `d49c4cb3ab144ed24193076f1892b03a2b764600a26f8754e0981f759a0e4e60` |
| `data/analysis/market_segmentation/tier_performance.parquet` | 139 × 6 cols | `1777b2aa4a698ed1ecc179d2197f68693651c2e6fb64b9010d6c42cb47e53921` |
| `data/analysis/market_segmentation/tier_thresholds.csv` | 160 | `8414fdb044c66f89147ffa37b0ff7f864ca9c3c5f4737b0915cad7b69d3ba7f4` |
| `data/analysis/market_segmentation_2.0/cluster_profiles.csv` | 3,541 | `46109df842155720959b1f3a9b44152fd739afb91faa19ecbcad527602689a0e` |
| `data/analysis/market_segmentation_2.0/investment_strategies.csv` | 760 | `24224211f68bd6af68080ca6b12be728b6522a983d1135bece541dbfdaf36450` |
| `data/analysis/market_segmentation_2.0/optimal_clusters.png` | 281,872 | `113e4cf1bcb6dd631c74339f33ef48d0543566c02a60d173eedd63f82bbf7273` |
| `data/analysis/market_segmentation_2.0/clusters_pca.png` | 4,960,984 | `08bf618b6cfdd713a42146d64ce36b9437beefc5585914b6fe1143a70ac005c7` |
| `data/pipeline/04_platinum/unified_dataset.parquet` | 1,236,310 × 97 cols | `39d234f703c9d6e098acc885eaadfdc965a6ac217189277c066676b3b117cefe` |
| `app/src/hooks/useSegmentMatching.ts` | — | `4682a8033aceb900eb17287b216127d50242b37ad2a56df63590c7392dc354d7` |
| `docs/plans/2026-02-22-interactive-market-segments-dashboard-implementation.md` | — | `961f173ebe10a35525b3b4f2b5a78c847089ddb2b19bc6e4157e84399d6142a6` |
| `.claude/handoffs/2026-02-23-interactive-segments-dashboard-implementation.md` | — | `c0487e94a6fbb4c246b487356517fa1c5f8f1a07e1f23db8bf177dd8f7ba375a` |
| `docs/analytics/editions/legacy/2026-11-12/market-segments.md` | 157 lines | `6813e4e121d8e1784f8a4605e8911ea26b634910cac02ce3702c1093d498e958` |

## Provenance

Prepared by `repo-agent/session-2026-11-20` as a **draft awaiting review**; its evidence status is `historical` and its editorial status is `draft`. Under the refresh rules (D12), the owner's and an independent reviewer's records are entered by them, never by the preparer — this document asserts no such record. Evidence pack: [RS10 market-segments evidence](../../../../implementation/2026-11-18-rs10-market-segments-evidence.md); ledger: [`artifacts/rs10-market-segments-evidence.json`](../../../../implementation/artifacts/rs10-market-segments-evidence.json) (sha256 `d8f0658807b4864c049481d289f7dd1312be8fb052eeddcbdcdb5c6e0b0f8c56`, 102,883 bytes), reproducible with `uv run python scripts/tools/market_segments_evidence.py --check`. The producer measures this checkout only — it never runs the pipeline, never re-fits a clustering, and never re-derives a housing aggregate past the 2026-10 cutoff.
