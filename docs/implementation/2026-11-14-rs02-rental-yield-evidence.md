# RS02 evidence pack — rental-yield definition, coverage and denominators

- **Date:** 2026-11-14
- **Status:** **Prepared for review, not signed off.** The definition is pinned and the join/denominator evidence is measured. The **duplicated-row defect found in the first review has been fixed at its source and the gold asset regenerated** (§5). No published _observation_ changed — `unified_dataset` came out byte-identical to the hash the v2 pack pins as its input — but the **catalog** did change (`rental_yield` 3,623 → 1,749 rows) and was regenerated. Register row: RS02 — `docs/analytics/rental-yields.md`. Gate: "gross proxy vs matched-unit yield defined; denominators and zero/missing handling validated."
- **Prepared by:** `repo-agent/session-2026-11-14`.
- **Machine-readable ledger:** [`artifacts/rs02-rental-yield-evidence.json`](artifacts/rs02-rental-yield-evidence.json) — sha256 `db1345253c4c9e4d80b7e3067962199a12f120ccfdfe1b6f599a7d95459f0313`.
- **Producer:** `scripts/tools/rental_yield_evidence.py`.
- **Upstream:** [RS01 source inventory](2026-11-14-rs01-source-inventory.md) (rental coverage starts 2021-01).

## 1. The definition, stated exactly

The shipped method is a **gross proxy**, not a matched-unit yield:

1. Per `(town, flat_type, month)`: `median_rent × 12 / median_sale_price × 100`, computed over **two independent transaction populations** (rentals and resales).
2. Per `(town, month)`: a **sale-count-weighted mean of those flat-type ratios**, published with `flat_type: "ALL"` and `property_type: "HDB"` (`src/egg_n_bacon_housing/components/feature_rental.py:120-137`).

That is a _mean of ratios_, not a ratio of sums, and it inherits both populations' mix. **Matched-unit yield is not computable from any source in this repo**: no file carries a unit identifier (§3). The gross proxy is therefore **the only definition the shipped method implements** — a block-matched proxy is feasible (§3) but is a method change, not a refresh, and the edition must label the gross proxy as such.

## 2. Join coverage (the population-defining cut)

| Measure                                                                                          | Value                                                      |
| ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------- |
| Months where either side exists                                                                  | 443 (1990-01 → 2026-11)                                    |
| Months with rentals                                                                              | 2021-01 → 2026-10 (rentals are the short side of the join) |
| Sales months with no rental group                                                                | `2020-12` and `2026-11` (the terminal partial month)       |
| Matched share of `(town, flat_type)` sale groups, **full period** (70 months, 2021-01 → 2026-10) | **median 92.5%** (min 86.6%, max 95.6%)                    |
| Same measure, **last 24 months only**                                                            | median 93.1% (min 89.3%, max 95.5%)                        |
| Same measure **without** the flat-type normaliser, last 24 months                                | median 16.0% (min 13.5%, max 18.3%)                        |

The first row is the finding that matters: across the whole published period the inner join keeps **92.5% of sale groups (86.6–95.6%), and only because** `normalize_hdb_flat_type` reconciles `"3 ROOM"`/`"3-ROOM"`/`"3 ROOM FLAT"` variants — the 16.0% figure is measured on the same 24-month window the ~93% figure comes from, and is a like-for-like comparison. Without it the join would keep 16% of groups. The drop is not unrecorded — `feature_rental.py:96-108` logs a warning with the matched-group coverage — but **the published asset carries no coverage field**, so a reader of `rental_yield.parquet` alone cannot see it. The normaliser is load-bearing, not cosmetic; a future change to it must re-run this measurement.

Consequence for the article: a yield point is a **town-month aggregate over 86.6–95.6% of that month's sale groups** (full-period median 92.5%), covering 2021-01 onward. The article's "Data Period: 2017-2026" cannot be supported for yields — rentals start in 2021.

## 3. Matched-unit vs matched-block

| Option                    | Feasible?                | Evidence                                                                                                                       |
| ------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| Unit-level matched yield  | **No**                   | No source carries a unit identifier; `(town, block, street, flat_type, month)` is the finest joint grain.                      |
| Block-level matched proxy | **Yes, not implemented** | Over the last 12 months, 8,185 sale blocks and 8,770 rental blocks exist, and **7,397 appear in both (90.4% of sale blocks)**. |
| Gross proxy (shipped)     | Yes                      | See §1.                                                                                                                        |

A block-matched yield is a **method change**, not a refresh: it would need its own definition, review and a new method version. It is recorded here as an available option, not adopted.

## 4. Denominators, zeros and missingness

Measured from the published `data/pipeline/03_gold/rental_yield.parquet`:

| Measure                           | Value                                                                                         |
| --------------------------------- | --------------------------------------------------------------------------------------------- |
| Rows / unique `(town, month)`     | 1,749 / 1,749 (no duplicates — see §5)                                                        |
| Towns                             | 25                                                                                            |
| Coverage                          | 2021-01 → 2026-10                                                                             |
| `rental_yield_pct`                | min 3.41 · p10 5.16 · p50 **6.24** · p90 7.29 · max 8.57                                      |
| `sample_size`                     | min 1 · p10 30 · p50 78 · p90 162.2 · max 279                                                 |
| Rows with `< 20` sales            | **136** town-months (7.8%) — thin, must not be ranked                                         |
| Non-positive or non-finite yields | 0                                                                                             |
| Yields above 20%                  | 0                                                                                             |
| Contextual `rental_index`         | present for **1,724 of 1,749** rows, 2021-01 → 2026-09 (the source has not published 2026-Q4) |

There is no row-weighting question any more: one row per town-month means the distribution above is already unweighted.

There is no zero/missing yield row: the inner join and the finite-value filter remove them, so **absence is missing-source, never zero yield**. The `sample_size` is the summed sale sample of the flat-type groups that matched, so it is the correct denominator for "how many sales stand behind this yield point" — provided the duplication in §5 is not summed naively.

## 5. Defect found, fixed at source, and regenerated

**What was wrong.** `rental_yield.parquet` held **3,623 rows for 1,749 distinct `(town, month)` pairs** (1,574 pairs twice, 150 three times). The yield columns agreed within each pair; `rental_index` did not.

**Root cause (code, not a stale file).** `raw_rental_index.parquet` carries **three property-type series per quarter** under the same `locality` (Landed 91 quarters, Non-Landed 91, All Residential 70). `feature_rental.py` filtered on locality only, expanded every row to its three months, and merged on `month` alone — so every town-month row matched 2–3 index rows and fanned out. Regenerating without a code change would have reproduced it.

**Fix (`src/egg_n_bacon_housing/components/feature_rental.py`).**

| Change                                                                                                                        | Reason                                                                                                                                                                                                                                                                                                                                                                                                           |
| ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_whole_island_rental_index()` selects **one** series by `RENTAL_INDEX_SERIES_PREFERENCE = ("NON-LANDED", "ALL RESIDENTIAL")` | The index is **context only** — it is the URA _private residential_ property rental index (`docs/research/singapore-open-datasets.md`), not an HDB index, and it is never a denominator here. Measured coverage decides the order: `All Residential` **stops at 2021-Q2**, which would have left **91.4% of rows (1,599 of 1,749)** with a null index; `Non-Landed` runs to 2026-Q3. `Landed` is never borrowed. |
| Quarter de-duplication before expansion, and `df.merge(..., validate="m:1")`                                                  | A duplicated source quarter or a future re-introduction of the fan-out now fails loudly instead of silently multiplying rows.                                                                                                                                                                                                                                                                                    |
| Months the chosen series does not cover stay **null**                                                                         | 25 rows (2026-10) have no index; nothing is borrowed from another segment.                                                                                                                                                                                                                                                                                                                                       |

**After regeneration** (warm `--stage features`, no source refresh): **1,749 rows for 1,749 town-months, zero duplicates**, one index per pair, `rental_yield_pct` p50 6.24, 136 thin town-months, index populated 1,724/1,749 (2021-01 → 2026-09).

**Blast radius, measured — stated only as far as it was verified.** `unified_dataset` came out at `sha256 39d234f7…`, **the same hash the published v2 pack records as its input**, so the pack's observations are unchanged. `transactions_enriched` and the three profile outputs were regenerated with unchanged row counts (1,236,411; 44; 28; 10,031), but **no pre-rerun hash was pinned for `transactions_enriched` itself**, so byte-identity there is not claimed — only the `unified_dataset` hash is a checkable before/after. The catalog was regenerated because its `rental_yield` row count moved 3,623 → 1,749.

**Tests pinning it** (`tests/test_rental_yield_metrics.py`): three property-type series yield exactly one row per town-month with the non-landed index; `All Residential` is used only as a fallback; a duplicated quarter does not fan out; a source with only `Landed` leaves the context column out rather than borrowing it.

## 6. What this pack does not establish

- It does not validate the article's flat-type yield table (`docs/analytics/rental-yields.md:40-50`) — the published asset aggregates flat types, so those per-flat-type bands have no artifact behind them in this tree.
- It does not establish yield-versus-appreciation correlation (§2 of the article): that needs joint appreciation series and a stated method, neither of which is part of RS02's gate.
- It does not authorize a rerun or a method change; both are separate grants (D10) and, for the block-matched option, a separate review.

## 7. Sign-off record

| Role            | Signatory                                              | Attests                                                                                                                       | Recorded                |
| --------------- | ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| Source / cutoff | repo owner                                             | the measured coverage (2021-01 → 2026-10) and the §5 remediation (regenerate)                                                 | **pending**             |
| Scientific      | recorded review run (`openai-codex/gpt-6-luna`, xhigh) | §1–§4 and §6 are accurate; §5's defect, fix and blast radius are described correctly and not overclaimed — **recorded** below | **recorded 2026-11-14** |
| Publication     | repo owner (≠ scientific reviewer)                     | the exact artifacts to be published                                                                                           | **pending**             |

Until §5 has a disposition and all three attestations are in the registry, `rental-yields` stays historical and the series keeps saying "No approved current edition".

### Recorded scientific review (2026-11-14)

Run: `openai-codex/gpt-6-luna`, reasoning `xhigh`, four passes (the first three refused attestation; each refusal — the duplicate-identity overclaim, the stale statistics, the private-index misidentification, the wrong null share — became a fixed defect). Verdict on the final artifact: **PASS WITH NOTES**.

> I reviewed RS02 at ledger hash `db1345253c4c9e4d80b7e3067962199a12f120ccfdfe1b6f599a7d95459f0313` and verified the shipped gross-proxy method, join and yield measurements, and the regenerated one-row-per-town-month fix. The current `unified_dataset` hash matches the v2 pack's recorded input hash. I do not attest to the separate `transactions_enriched` before/after byte-identity claim or to article claims the pack explicitly excludes.

The note was resolved after the review: §5 now states the blast radius only as far as it was verified (the `unified_dataset` hash is checkable against the published pack; `transactions_enriched` byte-identity is not claimed). The ledger it pins did not change. This attestation covers the **evidence pack**, not the article's sentences, and it is not a publication approval.
