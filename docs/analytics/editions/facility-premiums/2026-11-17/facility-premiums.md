---
title: Facility Premiums
category: "market-analysis"
description: What the current dataset can and cannot say about condo facility premiums — a measured source audit, the recovered project join key, project-structure evidence, and descriptive access associations with stated units
status: draft
date: 2026-11-17
personas:
  - investor
  - upgrader
readingTime: "7 min read"
technicalLevel: intermediate
---

# Facility Premiums

**Edition:** `facility-premiums-2026-11-17` · **Measured:** 2026-11-17 · **Observation cutoff:** 2026-10 (last complete month)

This edition replaces the facility-premiums text published 2026-03-31 (frozen in the archive as `legacy-2026-11-12`). The old text sorted condo facilities into "table stakes" and "differentiators", attached premium percentages to facility combinations, and advised buyers on which facilities to pay for. Every one of those sentences needs data this checkout does not have: a layer saying which development has which facility. That layer is **absent — measured, not assumed** (`legacySourceAudit`), so no facility prevalence, no facility premium and no facility comparison is measurable here, and each legacy facility claim is withdrawn below with that measured reason. What this edition does instead: it recovers the join key a facility layer would have had to use and measures its coverage; records per-facility `no-record` status; measures how much of condo price variation lies between projects — the quantified reason an unadjusted facility comparison is a comparison of projects; and publishes one descriptive, recorded access-association model with stated units, sample sizes, and both HC1 and project-clustered standard errors (cluster = `project_name`; the clustered battery is the published uncertainty). The measurement lives in [`scripts/tools/facility_premiums_evidence.py`](../../../../implementation/2026-11-17-rs05-facility-premiums-evidence.md), whose canonical ledger is [`artifacts/rs05-facility-premiums-evidence.json`](../../../../implementation/artifacts/rs05-facility-premiums-evidence.json) — sha256 `8bdc5b8465907bbbe98851841b4080caa4fb246b8ed8e61503d59bcedf348970`. Running `uv run python scripts/tools/facility_premiums_evidence.py --check` re-measures this checkout and fails if it no longer matches that ledger. The terminal month, 2026-11, holds 421 condo transactions — 0.1974 of the trailing-12-month median of 2,133 (`cutoff`) — and is excluded as partial; every number below ends at 2026-10.

## What the numbers in this edition are — and are not

One specification is **recorded** in the evidence ledger, only that one is fitted in this pack, and all its results are reported (`associations.estimator`): an OLS of **log price per square foot** (price in nominal Singapore dollars per square foot of strata area; the shipped `psf` column's identity with `price/area_sqft` is measured exact on 245,655/245,655 condo rows, max deviation 0.0 — `responseLineage`) on five jointly-fitted **external-access** indicators, each `1` when the shipped distance column is **≤ 1,000 metres**, with two standard-error batteries reported for every coefficient — HC1 (unclustered) and project-clustered (see the associations section). Controls: **floor area (sqft)**, a **freehold** indicator, a **long-lease** indicator (parsed lease duration ≥ 100 years), **lease commencement year**, floor-band fixed effects (17 levels; baseline `01 to 05`), property-subtype fixed effects (Condominium / Apartment / Executive Condominium), transaction-type fixed effects, transaction-year fixed effects, and planning-area fixed effects (41 levels). The specification is recorded, not pre-registered: no dated prior protocol exists in this checkout, so the possibility of specification search cannot be ruled out — the single-specification discipline is a disclosed limitation, not a credential.

This model does **not condition on project identity**: it carries no project fixed effects, so every coefficient below is a **between-project** association — it compares transactions of projects that differ in the indicator with transactions of projects that do not (`associations.estimator.projectEffects`). That label is the design, and the sentences below are written to match it. Sample: **n = 234,479 condo transactions, 2021-01 → 2026-10 (70 months)**, k = 75, R² = 0.7872 (`associations.sample`, `associations.fit`). Exclusions are recorded as reason sets over all 245,655 condo rows: **9,995 rows fail `landed-or-strata-landed-subtype`** (strata landed units are a different market from the condominium focus here), **421** fail only the terminal partial month, **934** fail `unparseable-tenure` (the source's `99 years leasehold`-style strings carry no commencement year to control for), and **1 row carries a seven-reason set** — landed subtype, missing planning area, and all five `missing-source:<amenity>-distance` reasons, because its location has no coordinates; the remaining overlaps are 174 two-reason rows and 11,001 single-reason rows (`associations.sample.excludedReasonCounts`, `excludedRowsByReasonCount`; the 10,755 in-window excluded rows are recorded as reason-set signatures plus a sha256 digest over the canonical per-row payload — `excludedInWindowRowsSha256`, recomputed by `--check`, with the first five rows sampled in the ledger). A null distance is a **missing source** — it is not a zero distance and not "no amenity nearby", and it is not rendered as either.

Nothing in this edition measures a facility. The indicators describe **external public amenities**; the in-house facility layer the legacy study ranked is absent, as the next section measures.

## The facility layer is absent — measured

The four facility sources the old text cited are not in this checkout (`legacySourceAudit.legacyNamedSources`, each measured on disk):

| Legacy-named source (as the old text cites it) | In this checkout |
| --- | --- |
| `data/04_platinum/private_property_facilities.parquet` (172,504 records) | **absent** |
| `data/04_platinum/property_nearby_facilities.parquet` (3,638,104 records) | **absent** |
| `data/04_platinum/property.parquet` (41,340 records) | **absent** |
| `data/04_platinum/housing_unified.parquet` | **absent** |

They belonged to the retired v1 pipeline: the archive document `docs/archive/20250120-data-pipeline.md` defines L3 stages named `L3_private_property_facilities` and `L3_property_nearby_facilities` (cited verbatim in the ledger from lines 268/269, 3 occurrences each — `archivedPipeline.doc`). The Hamilton pipeline under `data/pipeline/` defines no facility stage.

The absence claim is checked against what DOES ship, so "no in-house facility layer" is not an argument from silence (`legacySourceAudit`):

- The shipped dataset's only facility-like columns are `dist_to_nearest_sports_facility` and `nearest_sports_facility` (`unifiedDataset.facilityLikeColumns`, measured by scanning the full physical schema — all 97 columns, read from the parquet metadata). No column describes a development's private facility list.
- The layer behind those columns is **SportSG**: 45 public venues (`sportsgLayer.parquet.rows = 45`, 45 distinct names; the raw GeoJSON holds 45 features with names in a `VENUE` property and only dataset-update stamps — `FMEL_UPD_D` on 44 features at 2024-10-24 and 1 at 2025-07-11, refresh stamps rather than presence dates). These are public sport centres, swimming complexes, ActiveSG gyms and stadiums — shared infrastructure, not a development's facility list. This edition does not treat them as one.
- One row carries the literal string `None` as its `nearest_sports_facility` value (`unresolvedNameMarker`) — a missing-name marker, not a facility named "None"; it is the same un-geocoded row that carries the missing-source reasons above.

So facility **ownership and dates cannot be recovered**: the absent layers are the only place a facility attribute (which project has which facility, since when) has ever lived in this repo's data. No dated facility vintage exists to measure presence at any past date.

## The recovered join key — and its missing counterparty

The only candidate key a facility layer could have joined on is **`project_name`** (`joinKey.key`), present and fully populated on both sides of where the join would have been:

| Measure (`joinKey`) | Bronze (245,655 rows) | Window (245,234 rows, 2021-01 → 2026-10) |
| --- | ---: | ---: |
| Empty key values | 0 (share 0.0) | 0 (share 0.0) |
| Distinct projects | 3,005 | 3,005 |
| Transactions per project: min / p10 / median / p90 / max | 1 / 2 / 18 / 228.6 / 2,800 | 1 / 2 / 18 / 226.6 / 2,788 |
| Largest value of the key | "LANDED HOUSING DEVELOPMENT", 2,800 | "LANDED HOUSING DEVELOPMENT", 2,788 |
| Single-transaction projects | 138 | 140 |
| Projects with ≥ 30 transactions | 1,155 | 1,154 |

Two measured caveats bind what this key could ever support (`joinKey.normalisation`, `joinKey.counterparty`):

1. The key joins as **exact shipped strings**, and no project master layer or crosswalk exists here to validate spelling — the risk of two developments sharing one name string is **not measurable**. The most frequent value of the key is itself a category label, "LANDED HOUSING DEVELOPMENT" (2,788 window transactions), which the source attaches to bulk records rather than a named development (`joinKey.window.largestValueNote`).
2. **The counterparty layer is absent**: `facilityLayerPresent: false`, and records joined to a facility layer are **none — the key has no counterparty layer in this checkout**. "None joined" is a missing counterparty. It is not a count of zero facilities, and nothing in this edition reads it as one.

## Missing facilities are not absent facilities

Every facility the old text named is recorded as **`no-record`** (`facilityMissingness`): the source layer that carried the attribute is absent. That is a different statement from "**absent**" (a record exists and shows the facility missing) and from "**zero**" (a count was taken and returned 0) — and this checkout supports only the first:

| Legacy facility (old prevalence table) | Status here | Properties counted | Share |
| --- | --- | ---: | ---: |
| Swimming pool | `no-record` | none | none |
| Security (24hr) | `no-record` | none | none |
| Gym / Fitness corner | `no-record` | none | none |
| BBQ pits | `no-record` | none | none |
| Function room | `no-record` | none | none |
| Tennis court | `no-record` | none | none |
| Sky garden / Roof terrace | `no-record` | none | none |
| Concierge / Clubhouse | `no-record` | none | none |
| Jacuzzi / Hydrospa | `no-record` | none | none |
| Facility combinations (old synergy table, 5 rows) | `no-record` | none | none |

"No facility record" does not mean "the development has no pool", and it is not 0. The old prevalence shares, the old classifications (table stake / differentiator) and the old combination premiums are withdrawn below — not restated at zero.

## Projects differ — measured, and what that means for every number here

Facilities cluster inside developments, and projects differ from each other in ways that also correlate with price. On the exact model sample (`projectStructure`, n = 234,479, 2,413 projects):

- **91.0638% of log price-psf variance lies BETWEEN projects**; 8.9362% lies within them (`logPsfVariance` — a one-way decomposition, descriptive variance accounting, not an effect estimate).
- The five access indicators are nearly **project-level constants**: the between-project share of each indicator's variation is MRT 0.998792, hawker 0.997726, SportSG facility 0.997387, mall 0.996830, childcare 0.989010 (`indicatorBetweenProjectShare`). A transaction's access profile is essentially its project's access profile.
- Projects differ enormously in price: across the **1,102 projects with ≥ 30 transactions** (`perProjectMedianPsf`), median psf runs from **824.16 SGD/sqft (WOODSVALE, n = 214)** to **4,707.67 SGD/sqft (PARK NOVA, n = 78)** — p10 1,132.57, median 1,692.19, p90 2,509.00. Next-lowest: NORTHOAKS 842.32 (n = 273), KEW GREEN 859.60 (n = 59). Next-highest: ARDMORE PARK 4,107.83 (n = 66), BOULEVARD 88 3,959.28 (n = 94).

This is the quantified reason the old methodology's comparison could not do what it claimed: with-vs-without-facility price comparisons conditioned only on planning area and age leave this between-project structure intact, so they compare **projects**, not facilities. This edition therefore states it plainly: its model compares across projects, and the decomposition above is the measured account of what that comparison does and does not hold fixed. No direction or size of project-level confounding is claimed — the decomposition is not an estimate of anything.

## Measured conditional associations (between projects)

| Indicator | n with indicator = 1 (share of 234,479) | Log point | HC1 SE | Clustered SE | clustered/HC1 | exp(β)−1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| MRT within 1 km | 200,169 (85.37%) | +0.068648 | 0.001083 | 0.017982 | 16.5991 | +7.1059% |
| Mall within 1 km | 57,049 (24.33%) | −0.017691 | 0.001227 | 0.014870 | 12.1179 | −1.7536% |
| Hawker within 1 km | 165,838 (70.73%) | −0.001337 | 0.000871 | 0.012159 | 13.9573 | −0.1336% |
| SportSG facility within 1 km | 75,939 (32.39%) | −0.023912 | 0.000846 | 0.011079 | 13.0999 | −2.3628% |
| Childcare within 1 km | 233,231 (99.47%) | −0.142079 | 0.018301 | 0.050451 | 2.7567 | −13.2448% |

(ledger `associations.indicatorCoefficients`; all five indicators fitted jointly in one specification, so each row is conditional on the other four and on the controls. Coefficients are identical under both covariance estimates; only the standard errors differ.)

**Two standard-error batteries, one published inference.** HC1 treats transactions as independent. Transactions inside one project share a location and project-level unobservables, so the project-clustered battery — cluster = `project_name`, 2,413 clusters, cluster-robust CRVE with statsmodels' default finite-cluster corrections (`associations.estimator.clusteredStandardErrors`) — is the published uncertainty. The ratio column is the measured scale of the HC1 understatement: 2.76× for childcare and roughly 12× to 16.6× for the other four indicators.

**Which inferences change:** on the clustered battery, **mall (|t| = 1.19) and hawker (|t| = 0.11) are not distinguishable from zero on this design** — their clustered standard errors are 12.1× and 14.0× the HC1 ones. MRT (|t| = 3.82), SportSG facility (|t| = 2.16) and childcare (|t| = 2.82) remain larger than twice their clustered standard errors; the childcare row keeps its thin-contrast caveat below and still carries no effect interpretation. No significance statement in this edition rests on the HC1 column.

The controls, in natural units (coefficients, not effects; clustered SEs in the ledger): floor area **−0.00000178 log points per sqft** (HC1 SE 0.00000088, clustered SE 0.00000115), lease commencement year **+0.00377342 per year** (HC1 SE 0.00007974, clustered SE 0.00103723); the freehold flag is **+0.49407081** (HC1 SE 0.00896221, clustered SE 0.11545212) and the long-lease flag **+0.42689178** (HC1 SE 0.01149295, clustered SE 0.15095446) (`controlCoefficients`, `flagControls`; the full 75-column coefficient vector with both SE batteries is in the ledger). The tenure flags are close to project-level attributes, which is why their clustered SEs grow the most — one more measurement of the same clustering structure.

Read these rows as conditional differences **between projects**, not effects of amenities on prices:

- Each row compares transactions of projects that differ in the indicator with transactions of projects that do not, holding planning area, year, floor band, subtype, sale type, area and the tenure controls fixed. Project identity is **not** conditioned on, project completion year is null for **245,649** of 245,655 condo rows (`associations.sample.yearCompletedNullRows`), and unit quality, condition and the access snapshot's own vintage are uncontrolled (`associations.estimator.notControlled`). None of these numbers is a premium, and none measures a facility.
- **The childcare row is a thin, geographically concentrated contrast with no effect interpretation** (`associations.childcareContrast`): the indicator is 0 for **1,248 transactions (0.53%)** — MARINA SOUTH (1,108), SOUTHERN ISLANDS (89), CHANGI (51) — whose nearest childcare is 1,026.0 m away at best (median 1,372.9 m). The ledger records the group's composition and distances and runs no sensitivity or sign-flip analysis; at this contrast size the coefficient is reported for completeness, not interpreted — its clustered |t| of 2.82 does not change that.
- **These numbers do not rank amenities.** The old text's differentiator ranking came from a facility dataset that is not in this checkout; a conditional association is a different quantity and cannot be turned into a ranking or into buyer guidance.

## Superseded figures

Every quantitative claim in the old text, and what happened to it. Quoted phrases are verbatim from `docs/analytics/editions/legacy/2026-11-12/facility-premiums.md` (bold markers stripped; table-cell quotes show the escaped table pipes; no ellipses). The producer extracts the quoted spans of this table from this edition and machine-checks each against the legacy file (`legacyQuoteCheck.editionSpans`): `--check` fails if an edition quotation drifts from the legacy file, or if a registered claim loses its quotation here.

| Legacy figure (as the old text states it) | New measured value | Why it changed |
| --- | --- | --- |
| "The facilities that actually move prices are the ones that are not universally available. A condo with a tennis court or sky garden commands a measurable premium over an equivalent property with only standard facilities." | not measured — withdrawn | The in-house facility layer is absent from this checkout (`legacySourceAudit`), so no with-vs-without tennis-court or sky-garden population exists; the claim is causal in form, and no identification strategy exists here |
| "\| Swimming pool \| ~85-90% \| Minimal (expected) \| Table stake \|" | not measured — withdrawn | `facilityMissingness` records the facility as `no-record`: the layer that carried per-project facility lists is absent, so no prevalence share or premium classification is measurable; `no-record` is not zero and not absence |
| "\| Security (24hr) \| ~80-85% \| Minimal (expected) \| Table stake \|" | not measured — withdrawn | Same absent layer |
| "\| Gym / Fitness corner \| ~75-80% \| Minimal (expected) \| Table stake \|" | not measured — withdrawn | Same absent layer |
| "\| BBQ pits \| ~70-75% \| Minimal \| Table stake \|" | not measured — withdrawn | Same absent layer |
| "\| Function room \| ~60-65% \| Modest \| Nice-to-have \|" | not measured — withdrawn | Same absent layer |
| "\| Tennis court \| ~25-30% \| Moderate \| Differentiator \|" | not measured — withdrawn | Same absent layer |
| "\| Sky garden / Roof terrace \| ~15-20% \| Moderate-High \| Differentiator \|" | not measured — withdrawn | Same absent layer |
| "\| Concierge / Clubhouse \| ~10-15% \| Moderate \| Differentiator \|" | not measured — withdrawn | Same absent layer |
| "\| Jacuzzi / Hydrospa \| ~20-25% \| Low-Moderate \| Minor differentiator \|" | not measured — withdrawn | Same absent layer |
| "\| Pool + Gym + Security \| Baseline \| 0% (expected) \|" | not measured — withdrawn | No interaction model is reproduced and no facility combination is observable (the layer is absent) |
| "\| + Tennis Court \| Moderate \| +2-4% \|" | not measured — withdrawn | Same absent layer |
| "\| + Sky Garden \| Moderate-High \| +3-5% \|" | not measured — withdrawn | Same absent layer |
| "\| Tennis + Sky Garden + Concierge \| Strong \| +5-8% \|" | not measured — withdrawn | Same absent layer |
| "\| Full premium suite \| Diminishing returns \| +6-10% \|" | not measured — withdrawn | Same absent layer |
| "The first differentiating facility adds the most value. Adding more facilities beyond the first premium one shows diminishing returns." | not measured — withdrawn | The verb is causal and the facility-count regressor it needs does not exist here |
| "Condos near MRT stations with good in-house facilities command the strongest pricing." | not measured — withdrawn | Needs both an MRT measure (exists, snapshot) and an in-house facility measure (absent); the verb is causal |
| "\| MRT within 500m \| High \| Strong synergy with condo facilities \|" | not measured — withdrawn | The 3.6M-record nearby-facilities layer is absent; the label came from the retired v1 pipeline. Measured analogue, not a replacement: MRT within 1 km is associated with **+7.1059%** (log point +0.068648, HC1 SE 0.001083, project-clustered SE 0.017982, n = 200,169 of 234,479), conditional on controls, between projects, on an undated snapshot (`associations.indicatorCoefficients`) |
| "\| Mall within 500m \| Moderate \| Complements retail-deprived condos \|" | not measured — withdrawn | Same absent layer; the interaction reading is a claim nothing here measures. Measured analogue: mall within 1 km **−1.7536%** (−0.017691, clustered SE 0.014870, n = 57,049), between projects — **not distinguishable from zero under clustering** (clustered t = −1.19) — a different threshold and design, not a replacement |
| "\| Childcare within 500m \| Low-Moderate \| Relevant for family-oriented buyers \|" | not measured — withdrawn | Same absent layer; buyer-preference relevance is not a measured quantity here. The recorded childcare coefficient (**−13.2448%**, clustered SE 0.050451) rests on a 0.53% thin contrast and has no effect interpretation |
| "\| Hawker within 1km \| Low \| Less relevant for condo segment \|" | not measured — withdrawn | Same absent layer; segment relevance is not measured here. Measured analogue: hawker within 1 km **−0.1336%** (−0.001337, clustered SE 0.012159, n = 165,838), between projects — **not distinguishable from zero under clustering** (clustered t = −0.11) |
| "The interaction effect suggests that internal and external amenities are complementary, not substitutes." | not measured — withdrawn | An interaction claim needs both measures; the in-house half is absent, and no interaction model is fitted |
| "Properties with aging or poorly maintained facilities show weaker value retention compared to well-maintained equivalents." | not measured — withdrawn | Facility condition is not recorded anywhere in this checkout (the old text itself flags this), and no longitudinal property-level trajectory is reproducible without a unit-level key (RS01: no source carries one) |
| "Properties with differentiated facilities attract stronger tenant demand and command higher rents." | not measured — withdrawn | Rental demand is not measured in this pack (no rental join for condos), facility presence is unmeasurable, and the verb is causal |
| "Do not pay extra for table-stakes facilities (pool, gym, security). Every comparable condo has them." | withdrawn | A decision rule built on the unmeasurable prevalence and premium claims; the measured associations are between-project and support no guidance of this form |
| "Look for one or two genuine differentiators (tennis court, sky garden, concierge). These support future resale value." | not measured — withdrawn | Built on the unmeasurable differentiator claims; no future-resale measurement exists in this pack |
| "Inspect facility condition during viewings. A poorly maintained pool is a liability, not a selling point." | not measured — withdrawn | Facility condition is not recorded anywhere in this checkout; the sentence is prescriptive |
| "Facility quality matters more for tenant retention than facility quantity." | not measured — withdrawn | Neither facility quality nor tenant retention is measured in this checkout; the sentence is prescriptive |
| "Check the MCST (management corporation) financials. Well-funded reserve funds indicate sustainable facility maintenance." | not measured — withdrawn | No MCST financial data exists in this checkout |
| "When the EC privatizes after MOP, facility quality becomes a direct pricing factor." | not measured — withdrawn | No EC privatisation event, facility quality or pricing factor is measured here; EC rows enter the model sample only as a subtype fixed-effect level |
| "ECs typically have more extensive facilities than equivalent-price condos. Compare the facility quality, not just the list." | not measured — withdrawn | No EC facility comparison is measurable (the layer is absent); the sentence is prescriptive |
| "Prioritize developments with at least one differentiating facility that will appeal to future private-market buyers." | not measured — withdrawn | Built on the unmeasurable differentiator claims and a future-buyer-preference assertion nothing here measures |
| "Swimming pools, security, and gyms are present in 75-90% of properties, making them baseline expectations rather than pricing differentiators" | not measured — withdrawn | Same absent layer; no prevalence share is measurable (`facilityMissingness`) |
| "Tennis courts and sky gardens are the strongest individual facility differentiators, present in only 15-30% of properties" | not measured — withdrawn | Same absent layer; no prevalence share and no differentiator ranking is measurable |
| "Combination effects show diminishing returns: the first premium facility adds 2-5%, subsequent ones add 1-3% each" | not measured — withdrawn | The verb is causal and the combination model is not reproduced; no facility count exists |
| "3.6M nearby facility records provide granular proximity data for childcare, hawker, mall, and other external amenities" | not measured — withdrawn | `property_nearby_facilities.parquet` is absent from this checkout (`legacyNamedSources`); the shipped dataset carries nearest-distance columns per amenity layer instead, whose lineage RS04 audited |
| "Private property facility analysis reveals that most facilities are table stakes with minimal individual pricing impact." | not measured — withdrawn | The analysis is not reproducible in this checkout; this edition makes no table-stakes claim because no facility-level pricing measurement exists here |
| "Data Period: Cross-sectional (facility data) with transaction data 2017-2026" | Re-cut: **condo 2021-01 → 2026-10 (70 months, n = 234,479 in the model sample)**; the facility cross-section has no source at all here | The private-residential source starts 2021-01 with 0 earlier rows (`condoSourceCoverage`), so 2017-2020 is source-missing; the terminal month 2026-11 (421 rows) is excluded as partial |
| "Premium estimation: Comparison of price PSF for properties with vs without each facility type, controlling for location (planning area) and property age" | not measured — withdrawn; the comparison's structure is measured instead | The comparison population is unavailable (no facility layer); and `projectStructure` measures why that control set is insufficient on this data: 91.0638% of log-psf variance lies between projects, so a with-vs-without comparison conditioned only on planning area and age compares projects |
| "Property facilities: data/04_platinum/private_property_facilities.parquet (172,504 records)" | Superseded: the path does not exist in this checkout (`legacyNamedSources` measures each) | The v1 pipeline's L3 facility stages were never carried into the Hamilton pipeline under `data/pipeline/` |
| "Nearby facilities: data/04_platinum/property_nearby_facilities.parquet (3,638,104 records)" | Superseded: the path does not exist in this checkout | The shipped dataset carries nearest-distance columns per amenity layer instead |
| "Property master data: data/04_platinum/property.parquet (41,340 records, 30 columns including amenity distance features)" | Superseded: the path does not exist in this checkout | Condo-side location and amenity features live in the gold location dimension and the platinum unified dataset under `data/pipeline/` |
| "Transaction data: data/04_platinum/housing_unified.parquet (price data for premium estimation)" | Superseded: the shipped path is `data/pipeline/04_platinum/unified_dataset.parquet` (sha-pinned in the ledger `inputs`) | Path and provenance moved; the pin matches the published pack's input |
| "Analysis Date: 2026-03-31" | Superseded: this edition is dated 2026-11-17, measured from the current checkout at the 2026-10 cutoff | Edition date and observation window are recorded in the ledger, not carried forward |
| "Primary Focus: Condominium and EC facilities" | Superseded as a measurement claim; kept as a scope statement | The model sample is non-landed strata including Executive Condominium rows, but no facility measurement is possible under this focus in this checkout |
| "Key limitation: facility data is cross-sectional and does not capture facility quality or condition directly." | Superseded — still true, and now stronger | The facility data is not merely cross-sectional; it is absent from this checkout, and this edition also states the between-project limitation the old methodology carried without stating |

## What this edition does not establish

- **No facility premium, prevalence, combination, quality or retention estimate of any kind.** The in-house facility layer is absent; every legacy facility claim is withdrawn with that measured reason, not restated.
- **No causal claim.** Nothing here identifies why two transactions differ in price, and no sentence above attributes a price difference to a facility or an amenity.
- **No inference from the unclustered battery.** Every significance statement in this edition rests on the project-clustered standard errors; the HC1 column exists only to show how much the clustering correction matters.
- **No within-project estimate.** The project-fixed-effects variant of the model is recorded as not fitted (`notFitted.projectFixedEffectsSpecification`); the between-project labelling plus the variance decomposition is the disclosure, not a substitute estimate.
- **No temporal statement.** One undated snapshot per access layer is joined to 2021-2026 transactions alike; no per-period model is fitted, and no facility vintage exists to correct anything with.
- **No 2017-2020 statement.** The private source starts 2021-01; the old "2017-2026" period is re-cut, not confirmed.
- **No ranking of facilities or amenities.** Conditional associations are not importance shares and support no buyer guidance.
- **No completeness claim about sources outside this checkout.** The legacy layers are measured absent here; whether they survive elsewhere is not assessed.
- **No pre-registration credential.** One specification is recorded and only that one is fitted, with all coefficients reported; specification search cannot be ruled out.

## Reading this edition

- **Investors:** every value above carries its n and its ledger key. The one model here compares across projects and describes external public amenities — it does not price a tennis court or a sky garden, because the data that would answer that question is not in this checkout. The childcare row is a 0.53% thin contrast with no effect interpretation.
- **Upgraders:** the facility advice this page used to carry is withdrawn, not updated. If facility-level questions matter to a decision, the missing ingredient is a source-acquisition decision (a per-development facility layer with coverage and dates), not a wording change.
- **First-time buyers:** the only facility statement this edition can support is the measured one — the data needed to price facilities does not exist here, and "no record" is not "no pool".

## Provenance

Prepared by `repo-agent/session-2026-11-17` and registered as `evidenceStatus: "historical"`, `editorialStatus: "draft"` with no sign-offs and no `editionSha256`: under the refresh rules (D12), those are recorded only by the owner and an independent reviewer, never by the preparer. Evidence pack: [RS05 facility-premiums evidence](../../../../implementation/2026-11-17-rs05-facility-premiums-evidence.md); ledger: [`artifacts/rs05-facility-premiums-evidence.json`](../../../../implementation/artifacts/rs05-facility-premiums-evidence.json) (sha256 `8bdc5b8465907bbbe98851841b4080caa4fb246b8ed8e61503d59bcedf348970`), reproducible with `uv run python scripts/tools/facility_premiums_evidence.py --check`.
