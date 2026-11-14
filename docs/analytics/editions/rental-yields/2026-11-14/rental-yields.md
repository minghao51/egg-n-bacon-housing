---
title: Rental Yields
category: "market-analysis"
description: What the published rental yield is — a gross town-level proxy over two independent transaction populations — what its denominators are, and which yield claims this data cannot support
status: published
date: 2026-11-14
personas:
  - investor
  - first-time-buyer
  - upgrader
readingTime: "9 min read"
technicalLevel: intermediate
---

# Rental Yields

**Edition:** `rental-yields-2026-11-14` · **Measured:** 2026-11-14 · **Observation window:** 2021-01 → 2026-10

This edition replaces the analysis published 2026-03-31. That text presented per-flat-type yield bands, a yield-versus-appreciation trade-off, a top-yield league table and an affordability conclusion. **None of those have an artifact behind them in this tree.** Two of them are also methodologically unavailable: the published asset aggregates flat types, and no source carries a **unit** identifier, so a matched-unit yield cannot be estimated at all (a block-level proxy is feasible — §1). What follows is the definition the pipeline actually implements, the denominators it runs on, and the limits that follow.

Evidence: [RS02 pack](../../../../implementation/2026-11-14-rs02-rental-yield-evidence.md), ledger [`artifacts/rs02-rental-yield-evidence.json`](../../../../implementation/artifacts/rs02-rental-yield-evidence.json) — sha256 `db1345253c4c9e4d80b7e3067962199a12f120ccfdfe1b6f599a7d95459f0313`, reproducible with `uv run python scripts/tools/rental_yield_evidence.py`.

## 1. What the number is: a gross proxy, not a matched-unit yield

The shipped method (`src/egg_n_bacon_housing/components/feature_rental.py`) is:

1. For each `(town, flat_type, month)`: `median_rent × 12 / median_sale_price × 100`, computed over **two independent transaction populations** — approved rental applications and registered resale applications.
2. For each `(town, month)`: a **sale-count-weighted mean of those flat-type ratios**, published with `flat_type: "ALL"` and `property_type: "HDB"`.

Two properties of that definition rule out a common misreading:

- It is a **mean of ratios, not a ratio of sums**, so it inherits the mix of both populations. A town whose matched flat types skew small in one month and large in the next will move for composition reasons as well as for price reasons.
- The numerator and denominator come from **different dwellings**. A rental median for a 4-room flat in a town is not the rent of the flat whose sale price supplies the denominator. The figure is a town-level rent-to-price proxy.

**Matched-unit yield is not computable from any source here.** No file in this tree carries a unit identifier; `(town, block, street, flat_type, month)` is the finest joint grain. A **block-level** matched proxy is feasible — over the last 12 months 7,397 blocks appear in both the sale and rental populations, 90.4% of sale blocks — but it is a method change requiring its own definition and review, not a refresh of this edition. It is not implemented.

**Gross means gross.** Vacancy, property tax, income tax, agency fees, maintenance, repairs and financing costs are **outside** this number. It is not a net return, not a cash-flow figure, and not an investment recommendation. In particular, a yield exceeding a mortgage rate does **not** make a purchase viable: that comparison needs financing terms, vacancy expectations, tax treatment and maintenance, none of which are in this data.

## 2. Coverage: the join is the population-defining cut

| Measure | Value |
| --- | --- |
| Months where either side exists | 443 (1990-01 → 2026-11) |
| Months with rentals | 2021-01 → 2026-10 — rentals are the short side |
| Sale months with no rental group | 2020-12 and 2026-11 (the unpaired terminal month) |
| Matched share of `(town, flat_type)` sale groups, full period (70 months) | **median 92.5%** (min 86.6%, max 95.6%) |
| Same measure, last 24 months | median 93.1% (min 89.3%, max 95.5%) |
| Same measure **without** the flat-type normaliser, last 24 months | median 16.0% (min 13.5%, max 18.3%) |

The last two rows are the point. The join keeps ~92% of sale groups **only because** `normalize_hdb_flat_type` reconciles `"3 ROOM"` / `"3-ROOM"` / `"3 ROOM FLAT"` spellings — measured on the same 24-month window, without it the join would keep 16%. That normaliser is load-bearing, not cosmetic, and any change to it must re-run this measurement.

A yield point is therefore a **town-month aggregate over 86.6–95.6% of that month's sale groups**, from 2021-01 onward. The previously published "Data Period: 2017-2026" cannot be supported: rentals begin in 2021, so no yield observation exists before 2021-01.

## 3. Denominators and distribution

Measured from `data/pipeline/03_gold/rental_yield.parquet`:

| Measure | Value |
| --- | --- |
| Rows / unique `(town, month)` | 1,749 / 1,749 — one row per town-month |
| Towns | 25 |
| Window | 2021-01 → 2026-10 |
| `rental_yield_pct` | min 3.41 · p10 5.16 · **p50 6.24** · p90 7.29 · max 8.57 |
| `sample_size` (sales behind a point) | min 1 · p10 30 · p50 78 · p90 162.2 · max 279 |
| Town-months with fewer than 20 sales | **136 (7.8%)** — thin, must not be ranked |
| Non-positive or non-finite yields | 0 |
| Yields above 20% | 0 |
| Contextual `rental_index` present | 1,724 of 1,749 rows (2021-01 → 2026-09) |

Because there is one row per town-month, this distribution is already unweighted — there is no row-weighting question to settle. `sample_size` is the summed sale sample of the flat-type groups that matched, so it is the honest denominator for "how many sales stand behind this point". 136 town-months sit below 20 sales and carry a median built on very little.

**Missing is not zero.** The inner join and the finite-value filter remove empty rows, so a town-month with no yield is **missing source data**, never a zero yield. Reading a gap as 0% would invent a catastrophic return that does not exist.

The `rental_index` column is **context only**: it is the URA *private residential* rental index, not an HDB index, and it is never a denominator here. Its last observed quarter is 2026-Q3, which is why 25 rows (2026-10) carry a null rather than a borrowed value.

## 4. A defect found, fixed at source, and regenerated

The published asset previously held **3,623 rows for 1,749 distinct `(town, month)` pairs** — 1,574 pairs twice, 150 three times. The yield columns agreed within a pair; `rental_index` did not.

Cause was code, not a stale file: `raw_rental_index.parquet` carries **three property-type series per quarter** under the same `locality` (Landed 91 quarters, Non-Landed 91, All Residential 70). The feature joined on locality only and merged on `month` alone, so every town-month matched 2–3 index rows and fanned out. Regenerating without a code change would have reproduced it.

The fix selects **one** series — `Non-Landed`, falling back to `All Residential` — de-duplicates the source quarters, and merges with `validate="m:1"` so a future fan-out fails loudly instead of multiplying rows. Measured coverage picked the order: `All Residential` stops at 2021-Q2, which would have left 91.4% of rows (1,599 of 1,749) with a null index. `Landed` is never borrowed. Months the chosen series does not cover stay null.

After regeneration: **1,749 rows for 1,749 town-months, zero duplicates**, one index per pair. The blast radius is stated only as far as it was verified — `unified_dataset` came out at the same sha256 the published v2 pack records as its input, so **no published observation changed**; the catalog moved because the `rental_yield` row count did.

## 5. What this edition does not claim

These sentences from the 2026-03-31 edition are withdrawn, not softened:

| Withdrawn claim | Why |
| --- | --- |
| Per-flat-type yield bands (1-room 5–7%, 2-room 4–6%, 3-room 3.5–5%, 4-room 3–4.5%, 5-room 2.5–4%, multi-gen 2–3.5%) with typical monthly rents | The published asset aggregates flat types; no artifact in this tree produces per-flat-type yield bands |
| "Yield and appreciation are weakly negatively correlated (r ≈ −0.3)" and the strategy table built on it | Needs joint yield and appreciation series with a stated method; neither exists as an artifact here |
| "Top rental yield combinations" league table by flat type and area | Same missing per-flat-type yield; the table is unsupported at any granularity finer than town |
| "Median HDB rent / median household income 15–25%" and the affordability conclusion | Household income and rent are from different populations and periods; the ratio was never computed here |
| "Rental growth averages 3–5% annually", "year-end seasonal demand" | Not measured in this tree; annual growth is derivable from these files but is not part of this evidence |
| "Rental yields provide a downside floor … yields above 6% may indicate risk" | A gross proxy cannot establish a downside floor, and a high proxy can equally reflect a thin sale sample or a flat-type mix effect |

A yield above the median is a composition-and-price observation about one town-month, on a gross proxy, over 86.6–95.6% of that month's sale groups. That is all it is.

## 6. Evidence and sign-off

Whether this edition is current is decided by its entry in the edition registry (`app/src/components/studies/lib/edition-registry.ts`), which is the only place an edition sign-off may be recorded. `approvedEditionFor()` offers this edition as its series' current edition **only** when that entry is `approved` and carries three distinct attestations — source/cutoff, scientific and publication — that exclude the preparer, cover one evidence hash, and pin this file's own sha256 (`editionSha256`), which the archive route re-verifies against the frozen bytes at build time. Until that holds, the series page and every archive route render this edition as not approved. The D12 policy and the source/cutoff record for the evidence behind this edition are in the [decision ledger](../../../../plans/2026-11-12-reporting-refresh-decisions.md); the scientific and publication attestations belong to the registry entry, not to that ledger. The evidence they would cover is the [RS02 pack](../../../../implementation/2026-11-14-rs02-rental-yield-evidence.md).
