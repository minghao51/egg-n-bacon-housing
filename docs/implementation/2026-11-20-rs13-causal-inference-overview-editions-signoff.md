# RS13 — `causal-inference-overview` editions sign-off

- **Date:** 2026-11-20
- **Study:** RS13, series `causal-inference-overview`, edition `causal-inference-overview-2026-11-20`
- **Result:** approved and published, under the owner's **blanket delegation** recorded in D12 on 2026-11-20.
- **Gate:** register row RS13, quoted clause by clause in the edition text.

## The two pins

| Object                                                                                                            | sha256                                                             |  Bytes |
| ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | -----: |
| Evidence ledger — `docs/implementation/artifacts/rs13-causal-inference-overview-evidence.json`                    | `d65c014401b58b5eb4bfd92360bfd63c3ac159eac05bd5b3d85bdf9fad3a4bf3` | 97,812 |
| Frozen edition text — `docs/analytics/editions/causal-inference-overview/2026-11-20/causal-inference-overview.md` | `73b02d4843ee5ecd1873c73054b3889380ef286ec5f4274a0662a6b8de2290cd` | 50,822 |

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

Estimand, treatment and control construction, pretrends, concurrent policies, anticipation, placebos and multiplicity are each recorded as absent-unmeasurable with the boundary of the scan that searched for them, and what would be required to make the design reconstructable (a dated policy artefact with a bandwidth rule) is stated as a requirement rather than a plan.

## What this edition withdraws

The CCR-versus-OCR DiD estimate of -$137,743 and the HDB RDiT jump of +$13,118, both withdrawn as unreconstructable identification under the D12 disposition of 2026-11-18, because no dated policy artefact exists in this checkout.

## Verification at sign-off

ledger `--check` byte-identical twice and after a full pytest run; lexicon 0 forbidden; hooks green; registry entry approved with three attestations on the ledger hash and `editionSha256` on the text; the archive route re-verifies the text hash at build time.
