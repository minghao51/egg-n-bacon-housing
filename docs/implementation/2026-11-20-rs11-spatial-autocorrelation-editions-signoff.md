# RS11 — `spatial-autocorrelation` editions sign-off

- **Date:** 2026-11-20
- **Study:** RS11, series `spatial-autocorrelation`, edition `spatial-autocorrelation-2026-11-20`
- **Result:** approved and published, under the owner's **blanket delegation** recorded in D12 on 2026-11-20.
- **Gate:** register row RS11, quoted clause by clause in the edition text.

## The two pins

| Object                                                                                                        | sha256                                                             |  Bytes |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | -----: |
| Evidence ledger — `docs/implementation/artifacts/rs11-spatial-autocorrelation-evidence.json`                  | `3af671b1dc437121d3c2d98d45cc3ec1fecf93fda99ff4fb4a69a50e1796e36a` | 93,324 |
| Frozen edition text — `docs/analytics/editions/spatial-autocorrelation/2026-11-20/spatial-autocorrelation.md` | `d1363aafce5489f6a4e5bdb663f0f93fa29746ef972177ad8ae91483550d84ee` | 54,274 |

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

Moran's I and the local indicators are re-measured from the transaction frame with the weights definition, neighbourhood structure, disconnected areas, permutation count and seed recorded as fields, so the memberships are reproducible; the served asset's placeholder values (`z_score 0.0`, `p_value 1.0`, a constant `spatial_lag`) are recorded as a limitation of that asset rather than as results.

## What this edition withdraws

The `Moran's I 0.766 / z 9.91` figures as unrecoverable from the served payload, the 16 HH / 17 LH / 1 LL / 8 NS cluster table as stated, and the `transition analysis: moderate persistence` claim, which has no time dimension in the asset it was drawn from.

## Verification at sign-off

ledger `--check` byte-identical twice and after a full pytest run; lexicon 0 forbidden; hooks green; registry entry approved with three attestations on the ledger hash and `editionSha256` on the text; the archive route re-verifies the text hash at build time.
