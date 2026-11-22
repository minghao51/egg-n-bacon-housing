# RS12 — `spatial-hotspots` editions sign-off

- **Date:** 2026-11-20
- **Study:** RS12, series `spatial-hotspots`, edition `spatial-hotspots-2026-11-20`
- **Result:** approved and published, under the owner's **blanket delegation** recorded in D12 on 2026-11-20.
- **Gate:** register row RS12, quoted clause by clause in the edition text.

## The two pins

| Object                                                                                          | sha256                                                             |   Bytes |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | ------: |
| Evidence ledger — `docs/implementation/artifacts/rs12-spatial-hotspots-evidence.json`           | `6c4027340264cdc079dd19a2a5040b4c34e4f4059d53236f313c1ac56b86beab` | 202,191 |
| Frozen edition text — `docs/analytics/editions/spatial-hotspots/2026-11-20/spatial-hotspots.md` | `81236f9abc1214424e6ef7a0ad1c0bed98300c0b6291ab167958a38f6cdea072` |  38,401 |

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

The rental hotspot method is rerun with the gate's window pinned to 2024-01 to 2025-01 as its own historical window, on a population built from a measured 99.76% block-geocode join (39,385 of 39,478 rental rows), with the unmatched 0.24% reported as a population rather than dropped, and the result written to a new rental-only asset kept separate from the transaction-activity product.

## What this edition withdraws

The `847 H3 cells / 623 sufficient` counts, the `12 cells at 99%` claim and the -3.21 / -2.98 / -2.67 coldspots, none of which has an artefact in this checkout, and every rental claim that had been carried on the retired `search_result == 0` flag.

## Verification at sign-off

ledger `--check` byte-identical twice and after a full pytest run; lexicon 0 forbidden; hooks green; registry entry approved with three attestations on the ledger hash and `editionSha256` on the text; the archive route re-verifies the text hash at build time.
