# RS15 — `findings` editions sign-off

- **Date:** 2026-11-20
- **Study:** RS15, series `findings`, edition `findings-2026-11-20`
- **Result:** approved and published, under the owner's **blanket delegation** recorded in D12 on 2026-11-20.
- **Gate:** register row RS15, quoted clause by clause in the edition text.

## The two pins

| Object                                                                          | sha256                                                             |   Bytes |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------ | ------: |
| Evidence ledger — `docs/implementation/artifacts/rs15-findings-evidence.json`   | `f20b2a6221f8c563b661725726931f299fc7d4f53831bbf03063f04e9c143086` | 138,705 |
| Frozen edition text — `docs/analytics/editions/findings/2026-11-20/findings.md` | `a2c20043c55e9497082be96c534d9fc46b614f028dd5b5830362c7fc16897073` |  21,804 |

All three attestations pin the ledger hash; `editionSha256` pins the text hash. A later edit to either object voids only its own pin.

## What the delegation changes, and what it does not

The owner instructed on 2026-11-20 that the per-study approval hops be dropped and the waves completed directly (D12, "blanket delegation"). Under that directive the **source/cutoff** and **publication** attestations were materialised by this session once the study reached its reviewed state; the owner accepted the hashes without reading the ledger first. That is what the statements say, and it is the honest limit of them.

What was **not** delegated: the scientific seat. `openai-codex/gpt-6-luna (xhigh)` reviewed the text against the ledger as an independent run and its verdict is recorded below with model identity. That is the hop that found every real defect in RS09 and RS10, and it is the one check this programme cannot afford to lose.

## Review

Independent review at `codex-luna/gpt-6-luna` on the final bytes. Round 1 FAILed on one overclaim — the page said all 85 placeholder strings were one ledger's acquisition status when 26 sit in other studies' substantive fields, and the cited match list was truncated so the qualifier could not be checked. Fixed at the measurement (complete `byLedger`/`split` fields) and in the sentence; round 2 PASSed after the reviewer recounted all 85 itself.

## Verbatim attestations

All three statements are recorded in `app/src/components/studies/lib/edition-registry.ts`; they are reproduced here for the record.

> **source/cutoff (owner, delegated):** Recorded under the owner's blanket delegation of 2026-11-20 (D12), which dropped the per-study approval hop and expressly kept the scientific review: I attest that the measured ledger pins this checkout and accept the cutoff and the dispositions it implies, including that this page records its own series as not yet signed. The session materialised this attestation; the owner accepted the hash without reading the ledger first, and the statement says so.

> **scientific (recorded run):** I reviewed the edition text against this ledger hash by running the producer and re-deriving the register myself: the fourteen edition hashes against their files, the fourteen ledger pins, the 85-row placeholder split recounted from the sibling ledgers, and the page's own claims. The register presents no unresolved model as settled, every quantitative sentence names its edition with population, window and unit, and the series is recorded as not signed on the page that lists it. I do not attest to sibling studies' reasoning, source completeness beyond this checkout, or later edits.

> **publication (owner, delegated):** I approve publication of this edition at the frozen text sha256 recorded here as its current edition; recorded under the same delegation.

## What this edition establishes

A measured register of the fifteen series: for each one, its registered edition, its three attestations, and two hash comparisons made at build time (the edition file against its registered editionSha256, and the ledger file against the attestation pin). Fourteen series carry a signed edition; this page records its own series as not signed and states what that means. Every quantitative sentence on the page names its edition together with the population, window and unit, and the placeholder-vocabulary finding is measured rather than assumed: 85 placeholder strings across the fourteen sibling ledgers, 59 of them in one ledger's per-source acquisition status and 26 in four other studies' substantive fields, so a placeholder means 'not recorded for that study' and never 'absent everywhere'.

## What this edition withdraws

The frozen findings summary's own quantitative claims, disposed against this ledger (15 claims: 0 re-measured, 0 withdrawn, 0 not-reproducible), and any reading of the register as a claim that the fifteen studies agree with one another.

## Verification at sign-off

ledger `--check` byte-identical twice and `cmp`-deterministic; lexicon 0 forbidden; hooks green; registry entry with three attestations on the ledger hash and `editionSha256` on the text; archive route re-verifies the text hash at build time.
