# RS06 — `lease-decay` editions sign-off

- **Date:** 2026-11-20
- **Study:** RS06, series `lease-decay`, edition `lease-decay-2026-11-20`
- **Result:** approved and published, under the owner's **blanket delegation** recorded in D12 on 2026-11-20.
- **Gate:** register row RS06, quoted clause by clause in the edition text.

## The two pins

| Object | sha256 | Bytes |
| --- | --- | ---: |
| Evidence ledger — `docs/implementation/artifacts/rs06-lease-decay-evidence.json` | `f022f8c3babc8f603f91ae04b5b6e9791780900c3b9e157e7a07cae6cf555d27` | 197,825 |
| Frozen edition text — `docs/analytics/editions/lease-decay/2026-11-20/lease-decay.md` | `ab591689af641175ac8f0298d10ddda068911c490d1fcab35018daf93d44543b` | 48,884 |

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

The response is stated and its identity measured: on all 990,655 HDB rows `psf` equals `price / (floor_area_sqm x 10.7639104167)` with a maximum absolute deviation of 0.001503, so PSF and the derived per-square-metre measure are exact arithmetic on two measured columns rather than competing responses. Lease age is validated as of the transaction date on 281,810 parsed values (281,674 within one year of `99 - (transaction_year - lease_commence_date)`, maximum deviation 14.9167), with the stored `remaining_lease` column parsed across its four real formats and its 708,845 `nan` sentinel strings recorded as a missingness state of their own. The stored `Unit Price ($ PSM)` column is measured as a string column holding 122,017 values, not an empty one.

## What this edition withdraws

The legacy `+$54.75 PSF per extra year` coefficient, withdrawn rather than converted: the sentence names PSF while the appendix names `price_per_sqm`, and no conversion is performed because the original response is not established. The per-area band-discount readings are reconciled against the interactive asset and reported as a measured correspondence, not as coefficients.

## Verification at sign-off

ledger `--check` byte-identical twice and after a full pytest run; lexicon 0 forbidden; hooks green; registry entry approved with three attestations on the ledger hash and `editionSha256` on the text; the archive route re-verifies the text hash at build time.
