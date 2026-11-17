---
title: Amenity Impact
category: "market-analysis"
description: What the current dataset can and cannot say about amenities and HDB resale prices — measured amenity vintages, a snapshot-join audit, and descriptive conditional associations with stated units and controls
status: draft
date: 2026-11-16
personas:
  - first-time-buyer
  - investor
  - upgrader
readingTime: "7 min read"
technicalLevel: intermediate
---

# Amenity Impact

**Edition:** `amenity-impact-2026-11-16` · **Measured:** 2026-11-16 · **Observation cutoff:** 2026-10 (last complete month)

This edition replaces the amenity-impact text published 2026-03-31 (frozen in the archive as `legacy-2026-11-12`). The old text ranked amenities by feature importance, described premiums shifting across COVID periods and called parks an underpriced driver. Every one of those is a claim about price *effects*, and a claim about effects needs three things — amenities with units and controls, a statement of what is and is not historical about the amenity data, and an identification strategy the dataset can actually support. This edition reports what the pack measured against each of the three, and says where the answer is nothing. The measurement lives in [`scripts/tools/amenity_impact_evidence.py`](../../../../implementation/2026-11-16-rs04-amenity-impact-evidence.md), whose canonical ledger is [`artifacts/rs04-amenity-impact-evidence.json`](../../../../implementation/artifacts/rs04-amenity-impact-evidence.json) — sha256 `6232702eb8ab01e6508dee7a91418a7f272a41ae76681f35e3881a61de12e6ed`. Running `uv run python scripts/tools/amenity_impact_evidence.py --check` re-measures this checkout and fails if it no longer matches that ledger. The terminal month, 2026-11, holds 790 HDB transactions — 0.3718 of the trailing-12-month median of 2,125 (`cutoff`) — and is excluded as partial; every number below ends at 2026-10.

## What the numbers in this edition are — and are not

One specification is **recorded** in the evidence ledger, only that one is fitted in this pack, and all its results are reported (`associations.estimator`): an OLS of **log resale price (nominal Singapore dollars)** on five jointly-fitted amenity indicators, with HC1 robust standard errors. Each indicator is `1` when the shipped distance column is **≤ 1,000 metres** and `0` otherwise. Controls: **floor area (sqm)**, **lease commencement year**, **storey midpoint (storey number)**, flat-type fixed effects (7 levels), town fixed effects and transaction-year fixed effects. What is **not** controlled is stated in the ledger: flat model, unit condition and view, block attributes, grants and quota constraints, walking-path distance, amenity quality or operating status, town×year shocks, and the amenity snapshot's own vintage. The specification is recorded, not pre-registered: no dated prior protocol exists in this checkout, so the possibility of specification search cannot be ruled out — the single-specification discipline is a disclosed limitation, not a credential.

Sample: **n = 281,020 HDB resale transactions, 2015-01 → 2026-10 (142 months)**, R² = 0.9157, k = 51 (`associations.sample`, `associations.fit`). Exclusions are recorded as reason sets, never one bucket: **697,246 rows fail only before-study-window**, 790 only the terminal partial month, and **11,599 rows carry a six-reason set** — before-window plus all five amenity distances null (`missing-source`), because their locations have no coordinates; the total before-window count is 708,845 because the six-reason rows are also pre-window (`associations.sample.excludedReasonCounts`, `excludedRowsByReasonCount`). That is a missing source, not a zero distance and not "no amenity nearby"; it is not rendered as either (`associations.sample.excludedReasonCounts`). **No row inside the window is excluded** (`excludedInWindowRows` is empty).

None of the coefficients in this edition is a premium. They are conditional associations in one cross-section, and the amenity features come from **one snapshot per layer, of mixed datedness** (update stamps from 2021-12 to 2026-01 where they exist; supermarkets, preschools, malls and MRT carry no dates at all) **joined to transactions reaching back to 2015** — so a 2015 transaction is scored against the same snapshot values as a 2026 one, and no coefficient compares amenity states at two dates.

## The amenity snapshot: what is dated and what is not

Contemporary presence must not be read as historical presence. Measured, layer by layer (`amenityVintages`):

| Layer | Features/rows | Dated presence | What it carries |
| --- | ---: | --- | --- |
| Hawker centres (raw GeoJSON) | 129 | **Yes — the only dated amenity** | `EST_ORIGINAL_COMPLETION_DATE` populated on 128 of 129 features: 100 exact dates (`exactDateRange` min 1967-07-19 → max 2024-10-08), 21 year-only, 6 future years (2027, 2029, 2030), 1 `Pre-War`; the 129th (Tiong Bahru Market) has no value; `STATUS` marks **6 `Under Construction`**; three update stamps (2024-12-11, 2025-04-05, 2025-08-07 — dataset refresh stamps, not presence dates) |
| Hawker centres (bronze ingest) | 129 | No | the ingest keeps `name/lat/lon` and **drops the dates** the raw file carries; names join exactly (129/129) |
| Parks | 450 | No | dataset update stamps only (450 features across two `FMEL_UPD_D` values, both normalising to 2026-01-15); no gazetting or opening date |
| Supermarkets | 526 | No | no date field of any kind |
| Malls (URA MP25 layer) | 294 | No | bronze has no dates and **no names** (`nearest_mall` is empty for 100% of transactions); the raw layer is fetched live at ingestion and is not in this checkout; the ingestion code describes it as polygons that "approximate existing and designated mall sites" (`amenityVintages.mall.layerCompositionCitation`) |
| MRT | 188 | No | no opening dates; the only dated MRT snapshot is a single 2019-12-09 legacy seed (measured fully in RS03) |
| Childcare / preschools | 1,925 / 2,290 | No | one 2021-12-01 stamp / no dates |

So: hawker **completion dates** exist but are never used by the shipped features; for parks, supermarkets, preschools, childcare, malls and MRT there is **no dated vintage anywhere in this checkout** — and absence of dates is not evidence that nothing changed. An amenity that is missing from the snapshot layer is not an amenity that "did not exist" in the transaction's year.

## The snapshot join is not history — measured

The shipped distance columns reproduce exactly from the snapshot frames in this checkout: recomputing nearest distances over **every unique location in the study window (9,789)** with the pipeline's own estimator matches the shipped `dist_to_nearest_hawker`, `dist_to_nearest_mrt` and `dist_to_nearest_mall` for **9,789/9,789 locations, max deviation 0.0 m** (`shippedFeatureLineage`) — that exact full-frame match is the lineage evidence. A targeted **ablation** then locates the six `Under Construction` centres inside the shipped hawker feature: excluding them from the frame changes the shipped value for **738/738** of the locations whose shipped nearest centre is one of those six, while the other **9,051** keep matching. What this ablation shows is that those six centres' coordinates feed the single distance value the location join applies to transactions of every study month; it does not establish when construction at each site began, and it is not by itself evidence about historical operating status.

For hawkers — the one amenity with completion dates — the mismatch is quantified (`snapshotJoinMismatch`). Classifying each transaction's nearest centre by name against its completion date:

| Nearest hawker centre | Transactions (n = 281,020) | Share |
| --- | ---: | ---: |
| Completed before the transaction | 203,172 | 72.29% |
| **Not established as completed at the transaction date** | **77,173** | **27.46%** |
| Completion unknown (Tiong Bahru Market carries no date) | 675 | 0.24% |

By period, the not-established share is **40.4%** of 2015-2019 transactions (n = 101,409), **32.36%** of 2020-2022 (n = 79,140) and **10.55%** of 2023-2026 (n = 100,471). **17,179 transactions (6.11%)** have a nearest centre that is `Under Construction` — Bukit Timah Market, Chong Pang, Tampines North, Tanglin Halt, Telok Blangah and Yew Tee (all six named in the ledger; completion years 2027, 2029 and 2030 in `futureYearCompletionYears`). For these transactions the shipped distance is measured to a centre that is not operating in the snapshot, and that same value is joined to transactions of every study month; when construction at each site began is not in this checkout, so the distance's meaning at earlier dates is not established. For every other amenity the mismatch is present by construction — one snapshot's values joined to transactions of every month — but its **magnitude is not measurable here**, because no presence dates exist (`snapshotJoinMismatch.notMeasurableForOtherAmenities`). This measure classifies only the nearest centre, and completion dates describe building completion, not operating continuity.

## Measured conditional associations

| Indicator | n with indicator = 1 (share of 281,020) | Log point | Robust SE | exp(β)−1 |
| --- | ---: | ---: | ---: | ---: |
| Hawker within 1 km | 215,641 (76.74%) | +0.027498 | 0.000470 | **+2.79%** |
| Mall within 1 km | 25,851 (9.20%) | +0.054422 | 0.001062 | **+5.59%** |
| Park within 1 km | 220,273 (78.38%) | +0.007215 | 0.000506 | **+0.72%** |
| Supermarket within 1 km | 279,843 (99.58%) | −0.155732 | 0.003000 | **−14.42%** |
| MRT within 1 km | 241,370 (85.89%) | +0.099587 | 0.000667 | **+10.47%** |
| Amenity count (0–5 types within 1 km, separate model) | distribution in ledger | +0.040195 | 0.000302 | **+4.10% per additional type** |

(ledger `associations.indicatorCoefficients`, `associations.amenityCountModel`; all five indicators fitted jointly in one specification, so each row is conditional on the other four and on the controls.)

The controls, in natural units (coefficients, not effects): the floor-area coefficient is **+0.008273 log points per sqm**, the lease-commencement coefficient **+0.010563 per year**, and the storey-midpoint coefficient **+0.007554 per floor** (all with HC1 standard errors in `associations.controlCoefficients`; the full 51-column coefficient vector is in the ledger).

Read these rows as conditional differences between transactions, not effects of amenities on prices:

- **The supermarket row is a thin, geographically concentrated contrast with no effect interpretation** (`associations.supermarketContrast`): the indicator is 0 for **1,177 transactions (0.42%)**, whose nearest supermarket is at best 1,006.7 m away (median 1,176.9 m), overwhelmingly in WOODLANDS (1,077), PASIR RIS (59) and TAMPINES (41). The ledger records this group's composition and distances and runs no sensitivity or sign-flip analysis; at this contrast size the coefficient is reported for completeness, not interpreted.
- **These numbers are cross-sectional.** Town and transaction-year fixed effects enter **separately**: the amenity coefficients are identified from within-town differences in indicator status after removing year-to-year price movements common to all towns, and they do **not** condition on joint town-year cells. Town-specific time shocks, unit quality and the snapshot's own vintage remain uncontrolled (`associations.estimator.notControlled`). Nothing here identifies why two otherwise-similar flats differ, so nothing here is a "premium of X%".
- **These numbers do not rank amenities.** The old text's importance ranking came from a retired XGBoost/SHAP model; a conditional association is a different quantity and cannot be turned into an importance share without that model.

## Presence varies within areas

The old text's 500 m-grid model is not reproduced and no grid is constructed. What is measured is whether the within-1 km indicator varies inside an area at all, on the same bounded window (`withinAreaVariation`; the shipped dataset carries both `town` and `planning_area` and they disagree, so both are measured):

- **Hawker**: the within-1 km share varies inside **22 of 26 towns** (23 of 32 planning areas) — from CHOA CHU KANG at 0.386 (n = 12,695) to ANG MO KIO at 1.000 (n = 11,673).
- **Park**: varies inside **19 of 26 towns** — WOODLANDS 0.406 (n = 19,945) to ANG MO KIO 1.000 (n = 11,673).
- **MRT**: varies inside **18 of 26 towns** — PASIR RIS 0.451 (n = 8,238) to BUKIT PANJANG 1.000 (n = 10,042).
- **Mall**: varies inside only **7 of 26 towns** — ANG MO KIO 0.000 (n = 11,673) to CENTRAL AREA 1.000 (n = 2,305); mall access in this snapshot is mostly a town-level attribute.
- **Supermarket**: varies inside only **3 of 26 towns** — the indicator is nearly universal (99.58% of the sample).

That is the descriptive fragment of the old grid claim: presence profiles do differ inside towns. No premium is computed per area, and variation in an indicator is not variation in a premium.

## Superseded figures

Every quantitative claim in the old text, and what happened to it. Quoted phrases are verbatim from `docs/analytics/editions/legacy/2026-11-12/amenity-impact.md` (bold markers stripped); all 19 quotes are machine-checked against that file by the producer (`legacyQuoteCheck`).

| Legacy figure (as the old text states it) | New measured value | Why it changed |
| --- | --- | --- |
| "Hawker centre proximity is the single most important amenity feature for HDB pricing, outranking even MRT access." | not measured — withdrawn | The ranking is an output of the retired XGBoost/SHAP model; importance shares are not associations with units, and a conditional association cannot rank importance. Measured analogue, not a replacement: hawker within 1 km is associated with **+2.79%** (log point +0.027498, SE 0.000470), conditional on controls, on a current snapshot |
| "Hawker within 1km is the dominant non-structural feature at 27.4% XGBoost importance, followed by remaining lease (14.1%), park within 1km (7.2%), and MRT within 1km (5.5%)" | not measured — withdrawn | The importance model is not reproduced; no importance table is re-estimated |
| "Parks and green space are the most underappreciated premium driver." | not measured — withdrawn | "premium driver" phrasing is causal; nothing here identifies an effect. Measured analogue: park within 1 km **+0.72%** (+0.007215, SE 0.000506), conditional on controls — descriptive, snapshot-joined |
| "Park proximity adds a measurable premium that is frequently underweighted in buyer decisions." | withdrawn | "adds" is causal and "underweighted" needs a model of buyer beliefs; neither exists in this checkout |
| "Properties near large parks (East Coast, Bishan-Ang Mo Kio, Bukit Timah) may offer better value per dollar than equivalent properties near MRT stations, because the market has not fully priced the green-space premium." | not measured — withdrawn | "not fully priced" is a market-efficiency finding no model here can produce; park and MRT associations exist in the ledger but do not compare "value per dollar" |
| "Hawker proximity" row: "High", "High", "High" (Pre-COVID / COVID / Post-COVID) | not measured — withdrawn | A period comparison needs amenity features as they stood in each period; the shipped features are one snapshot applied to every period alike, no amenity vintage per period exists (hawker completion dates are a mismatch audit, not per-period features), and the retired RandomForest temporal comparison is not reproduced |
| Period table "Park proximity" row: "Moderate", "Elevated", "Elevated" | not measured — withdrawn | Same reason as the row above |
| Period table "MRT proximity" row: "Moderate", "Reduced", "Partially recovered" | not measured — withdrawn | Same reason as the row above |
| Period table "Mall proximity" row: "Moderate", "Reduced", "Recovered" | not measured — withdrawn | Same reason as the row above |
| "COVID elevated the importance of nearby green space and reduced the MRT premium as remote work reduced commute frequency." | not measured — withdrawn | Same missing per-period vintages; the remote-work attribution is causal and unmeasured |
| "Park importance increased post-COVID and has remained elevated, suggesting a structural shift in buyer preferences" | not measured — withdrawn | Same missing per-period vintages; preference shifts are not measurable from a cross-sectional snapshot join |
| "MRT importance dipped during COVID and has only partially recovered, likely reflecting sustained hybrid work patterns" | not measured — withdrawn | Same missing per-period vintages; measured MRT association (+10.47%, conditional, snapshot-joined) is a different quantity from an importance trajectory |
| "The combined effect of having multiple amenities nearby exceeds the sum of individual effects." | not measured — withdrawn | A SHAP-interaction output of the retired model. The measured amenity-count association (**+4.10% per additional type within 1 km**, SE 0.000302) is a different quantity — a conditional association of a count, not an interaction that exceeds the sum of its parts |
| "MRT + Mall + Hawker" — "Synergistic premium" | not measured — withdrawn | No interaction model is reproduced; no combination is ranked |
| "At the 500m x 500m grid level, amenity premiums are highly localized within the same town." | not measured — withdrawn; the presence-dispersion fragment is measured instead | The grid premium model is not reproduced and no 500 m grid is constructed; presence varies inside 22 of 26 towns (hawker) — variation in an indicator is not variation in a premium |
| "Two flats in the same planning area but different grids can have materially different amenity profiles." | Re-measured descriptively (without grids): within-1 km shares vary inside 22/26 towns for hawker, 19/26 for park, 18/26 for MRT, 7/26 for mall, 3/26 for supermarket (`withinAreaVariation`) | Presence dispersion is measured; no grid, no premium, and the legacy model's within-town regressions are not reproduced |
| "Condo buyers get more pricing benefit from MRT and mall proximity than from most in-facility amenities." | not measured — withdrawn | No condo model is fitted: the private-residential source in this checkout starts 2021-01 (0 condo rows before it; 245,234 in-window; 421 in the excluded terminal month — `condoScope`), while this claim spans 2015-2026 |
| "HDB buyers should prioritize hawker proximity over MRT proximity when evaluating daily convenience." | withdrawn | A decision rule built on the retired importance ranking; the measured conditional associations (hawker +2.79%, MRT +10.47%) are descriptive and do not rank amenities for choice |
| "Target multi-amenity hubs for stronger rental demand and capital appreciation." | not measured — withdrawn | Rental demand and capital appreciation are not measured in this pack; the sentence is also prescriptive |
| "Data Period: 2015-2026" | Re-cut: **HDB 2015-01 → 2026-10 (142 months, n = 281,020)**; condo coverage starts 2021-01 | The private-residential source starts 2021-01 in this checkout; "2015-2026" holds only for HDB, and the terminal month 2026-11 is excluded as partial |
| Methodology: "XGBoost (100 trees, max_depth=6, learning_rate=0.1) with SHAP values for feature importance and interaction detection" (and the RandomForest, within-town and grid models) | Superseded for this edition: the ledger's single recorded OLS with stated controls (R² = 0.9157, n = 281,020) | The retired analysis scripts are not in the supported repo surface (the old text says so itself); none of the four model families is reproduced |
| "data/04_platinum/housing_unified.parquet" | Superseded: the shipped path is `data/pipeline/04_platinum/unified_dataset.parquet` (1,236,310 × 97, sha-pinned in the ledger `inputs`) | Path and provenance moved; the pinned hash matches the published pack's input |
| "Distance and threshold indicators for hawker, mall, park, supermarket, preschool, childcare at 500m, 1km, and 2km radii" | Superseded: the shipped dataset carries **distances in metres**, not threshold indicators at three radii; this pack constructs exactly one threshold (1,000 m) per measured amenity and states it (`associations.estimator.indicators`) | The legacy features belonged to the retired scripts and cannot be verified against the shipped dataset |

## What this edition does not establish

- **No causal premium.** No coefficient measures what an amenity does to a price; no identification strategy exists here, so none is implied.
- **No temporal statement.** One snapshot is joined to every period alike; 27.46% of transactions' nearest hawker centre is not established as completed at their transaction date, and for every other amenity the mismatch is unmeasured, not absent.
- **No importance ranking and no interaction estimate.** Both belonged to the retired model.
- **No condo statement.** The condo source starts 2021-01; no condo model is fitted.
- **No completeness claim.** The raw MP25 mall layer is not in this checkout; hawker completion dates describe completion, not operating continuity; sources outside this checkout are not assessed.

## Reading this edition

- **First-time buyers:** the association table says transactions whose location is nearer a snapshot amenity tended to have differed in price *conditional on flat type, town, year, size, lease and storey* — not that proximity adds anything. The vintage audit finds a mixed, partly undated snapshot — hawker update stamps end 2025-08-07, parks carry 2026-01-15, childcare 2021-12-01, and supermarkets, preschools, malls and MRT carry no dates — so a flat's historical amenity access could differ from what the distances record.
- **Investors:** every value above carries its n and its ledger key. The supermarket contrast (0.42% of the sample, concentrated in three towns) is thin and geographically concentrated; the ledger records its composition and distances and runs no sensitivity analysis on it. The count association (+4.10% per additional amenity type) is descriptive and is not a synergy estimate.
- **Upgraders:** the condo amenity claims this page used to carry are withdrawn — the condo source in this checkout starts 2021-01, and no condo model was fitted. If condo amenity questions matter, the private-residential vintages needed are a source-acquisition decision, not a wording change.

## Provenance

Prepared by `repo-agent/session-2026-11-16` and registered as `evidenceStatus: "historical"`, `editorialStatus: "draft"` with no sign-offs and no `editionSha256`: under the refresh rules (D12), those are recorded only by the owner and an independent reviewer, never by the preparer. Evidence pack: [RS04 amenity-impact evidence](../../../../implementation/2026-11-16-rs04-amenity-impact-evidence.md); ledger: [`artifacts/rs04-amenity-impact-evidence.json`](../../../../implementation/artifacts/rs04-amenity-impact-evidence.json) (sha256 `6232702eb8ab01e6508dee7a91418a7f272a41ae76681f35e3881a61de12e6ed`), reproducible with `uv run python scripts/tools/amenity_impact_evidence.py --check`.
