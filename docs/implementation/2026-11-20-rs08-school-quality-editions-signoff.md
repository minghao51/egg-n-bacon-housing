# RS08 — `school-quality` editions sign-off

- **Date:** 2026-11-20
- **Study:** RS08, series `school-quality`, edition `school-quality-2026-11-20`
- **Result:** approved and published, under the owner's **blanket delegation** recorded in D12 on 2026-11-20.
- **Gate:** register row RS08, quoted clause by clause in the edition text.

## The two pins

| Object | sha256 | Bytes |
| --- | --- | ---: |
| Evidence ledger — `docs/implementation/artifacts/rs08-school-quality-evidence.json` | `bf7825f8d23c745b18e564bfe3abe018ed26e927f2aa3e41afce646d55b36ef8` | 252,384 |
| Frozen edition text — `docs/analytics/editions/school-quality/2026-11-20/school-quality.md` | `639f56ea199d40e06183d5c6e502053bef29a6aa315660de62275e9baf4fbdcf` | 54,228 |

All three attestations pin the ledger hash; `editionSha256` pins the text hash. A later edit to either object voids only its own pin.

## What the delegation changes, and what it does not

The owner instructed on 2026-11-20 that the per-study approval hops be dropped and the waves completed directly (D12, "blanket delegation"). Under that directive the **source/cutoff** and **publication** attestations were materialised by this session once the study reached its reviewed state; the owner accepted the hashes without reading the ledger first. That is what the statements say, and it is the honest limit of them.

What was **not** delegated: the scientific seat. `openai-codex/gpt-6-luna (xhigh)` reviewed the text against the ledger as an independent run and its verdict is recorded below with model identity. That is the hop that found every real defect in RS09 and RS10, and it is the one check this programme cannot afford to lose.

## Review

Independent review at `codex-luna/gpt-6-luna` (xhigh) on the final bytes, with the ledger history recorded: the producer was regenerated for scan stabilisation after it was established that every producer's scan read `app/src`, so signing any study drifted the others.

## Verbatim attestations

All three statements are recorded in `app/src/components/studies/lib/edition-registry.ts`; they are reproduced here for the record.

> **source/cutoff (owner, delegated):** Recorded under the owner's blanket delegation of 2026-11-20 (D12), which dropped the per-study approval hop and expressly kept the scientific review: I attest that the measured ledger pins this study's checkout and accept the cutoff and the dispositions it implies. The session materialised this attestation; the owner accepted the hash without reading the ledger first, and the statement says so.

> **scientific (recorded run):** I reviewed the edition text against this ledger hash: the ledger-backed numerical claims, the withdrawals, the absence scans with their boundaries, and the claim dispositions were verified by running the producer and re-deriving values from the pinned data. A screen is not treated as a finding about origin, and no edition-facing sentence claims more than its scan. I do not attest to source completeness beyond this checkout, other editions, or later edits.

> **publication (owner, delegated):** I approve publication of this edition at the frozen text sha256 recorded here as its current edition; recorded under the same delegation.

## What this edition establishes

Tier provenance, bandwidth, treatment assignment, covariate balance and multiplicity are each recorded as present or absent with the scan that establishes the absence: none of the three feature names the legacy coefficients use (`school_primary_quality_score`, `school_primary_dist_score`, `school_secondary_dist_score`) exists in any layer. What is measured is a distance-based association on the columns that do exist, with the proxy tier named explicitly, and policy eligibility fields kept outside every model output.

## What this edition withdraws

The `-$79.47 PSF` RDD estimate, which rested on a failed covariate balance and is therefore a failed-design estimate rather than a premium, and the three legacy per-point coefficients (+$9.66, +$6.27, +$3.52 PSF) as not reconstructable.

## Verification at sign-off

ledger `--check` byte-identical twice and after a full pytest run; lexicon 0 forbidden; hooks green; registry entry approved with three attestations on the ledger hash and `editionSha256` on the text; the archive route re-verifies the text hash at build time.
