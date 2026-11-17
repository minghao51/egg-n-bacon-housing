# RF08 — RS04 `amenity-impact` edition sign-off record

- **Date:** 2026-11-16
- **Slice:** RF08 (refreshed studies), series `amenity-impact` (register row RS04)
- **Evidence pack:** [RS04](2026-11-16-rs04-amenity-impact-evidence.md) · ledger [`artifacts/rs04-amenity-impact-evidence.json`](artifacts/rs04-amenity-impact-evidence.json)
- **Producer:** `scripts/tools/amenity_impact_evidence.py` (`--check` re-measures the checkout)
- **Frozen edition:** [`docs/analytics/editions/amenity-impact/2026-11-16/amenity-impact.md`](../analytics/editions/amenity-impact/2026-11-16/amenity-impact.md)
- **Contract:** [D12](../plans/2026-11-12-reporting-refresh-decisions.md) (three distinct attestations, no self-approval), [D07](../plans/2026-11-12-reporting-refresh-decisions.md) (edition ≠ observation window)
- **Registry:** `app/src/components/studies/lib/edition-registry.ts` — `amenity-impact-2026-11-16`

> **Status: complete.** Both owner signatures were given on 2026-11-16 and the registry
> entry is `approved`/`published`, with three attestations on the ledger hash and
> `editionSha256` pinning the text. Gate 4 records what was given.

## Gate 1 — evidence ledger

| Thing                             | Value                                                                 |
| --------------------------------- | --------------------------------------------------------------------- |
| Ledger                            | `docs/implementation/artifacts/rs04-amenity-impact-evidence.json`     |
| sha256                            | `6232702eb8ab01e6508dee7a91418a7f272a41ae76681f35e3881a61de12e6ed`    |
| Reproducibility                   | producer run twice → byte-identical; `--check` re-measures the tree   |
| Frozen edition text               | `docs/analytics/editions/amenity-impact/2026-11-16/amenity-impact.md` |
| Text sha256                       | `3a5ef72d97af0c0004491567314e180bf3238bdaaff11457707a3138657b4507`    |
| Evidence pack                     | `docs/implementation/2026-11-16-rs04-amenity-impact-evidence.md`      |
| Pack sha256                       | `ede81c8a05240d798fbf3ee23e669f07362128e40119b82013183372fdccb209`    |
| Legacy text (immutable, unedited) | `5683269e4b3c04a61edcc45bd259fba6fa8b6c501946bbcc3740a312ab6ffb65`    |

Sign-offs attach to the **ledger** hash; the text is pinned separately by
`editionSha256`.

## Gate 2 — the study's extra gate (register RS04)

> "Refit documented associations with units and controls. Contemporary amenity
> presence must not imply historical presence; disclose snapshot join limitations.
> No causal premiums without identification."

Measured outcome:

- **One recorded specification, fully disclosed.** OLS of log HDB resale price (nominal
  SGD) on five jointly-fitted ≤1 km snapshot indicators, with floor area (sqm), lease
  commencement year and storey midpoint controls, flat-type / town / transaction-year
  fixed effects, HC1 standard errors, n = 281,020 (2015-01 → 2026-10), k = 51,
  df_resid = 280,969, R² `0.9156847988`, adjusted R² `0.9156697944`.
  Associations: hawker +2.79% (`0.027498`), mall +5.59% (`0.054422`), MRT +10.47%
  (`0.099587`), park +0.72% (`0.007215`), supermarket −14.42% (`−0.155732`), amenity
  count +4.10% (`0.040195`).
- **No causal premium.** The text reports conditional associations only; the word
  "premium" survives only inside quoted legacy claims marked withdrawn.
- **Snapshot ≠ history, measured.** 77,173/281,020 transactions (27.46%) have a nearest
  hawker centre not established as completed at the transaction date (40.4% in
  2015–2019, 32.36% in 2020–2022, 10.55% in 2023–2026); 17,179 (6.11%) are nearest an
  **Under Construction** centre. Hawker completion dates are the only amenity vintage in
  the checkout; parks/childcare carry update stamps only; supermarkets, preschools and
  MRT carry none.
- **Lineage measured, with an ablation honestly labelled.** The shipped distances
  reproduce exactly from the bronze snapshot frames for 9,789/9,789 unique locations
  (max deviation 0.0 m). Excluding the six Under-Construction centres changes the value
  for exactly the 738 locations whose nearest centre is one of them (9,051 unchanged) —
  a **targeted leave-out ablation** that locates those coordinates in the shipped
  feature; it does not establish historical operating status.
- **Withdrawn:** the legacy importance ranking (27.4/14.1/7.2/5.5/3.8%), the COVID
  period-shift rows, the interaction/synergy claim, the 500 m localisation, and every
  condo claim (the private source starts 2021-01).
- **Disclosed limitation:** the specification is **recorded, not pre-registered** — no
  dated prior protocol exists, so specification search cannot be ruled out.

## Gate 3 — scientific re-review (five rounds)

Reviewed by `openai-codex/gpt-6-luna (xhigh)` as `codex-luna-reviewer`. Each round
re-derived the model independently rather than proofreading.

| Round | Verdict  | Findings                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ----- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | FAIL     | completion-date range wrong at both ends (`1967-01-09→2024-08-21` vs ledger `1967-07-19→2024-10-08`); "construction site at every study date" overstated; "snapshot describes 2026 amenities" (mixed/undated layers); the identification sentence described town×year FE that the model does not have; "flips sign" claimed with no sensitivity analysis; the 738/738 ablation was called a negative control that "proves" bias |
| 2     | FAIL     | six round-one defects closed except the ablation label in the pack and producer; new: "declared before it was run" / "pre-registered" asserted a chronology no artefact supports                                                                                                                                                                                                                                                |
| 3     | FAIL     | the pre-registration wording was fixed but edition line 19 still asserted measurement "before any sentence below was written"                                                                                                                                                                                                                                                                                                   |
| 4     | FAIL     | pack line 32 said "Consequences, stated before any number is quoted" above a table that quotes numbers; **and the edition hash supplied in that round's brief was fabricated by the sequencer** (a truncated value padded out) — the reviewer caught the mismatch by recomputing                                                                                                                                                |
| 5     | **PASS** | no discrepancies; all hashes matched; chronology sweep clean apart from explicit negatives                                                                                                                                                                                                                                                                                                                                      |

**Process note for the next agent: never assemble a hash from a truncated prefix.**
The round-four brief printed `sha256sum … | cut -c1-20` and then invented the remaining
44 characters; the review correctly refused to sign on an identity mismatch. Measure the
full digest and copy it.

### Verbatim attestation (round 5)

> "I reviewed the edition text at
> `docs/analytics/editions/amenity-impact/2026-11-16/amenity-impact.md` (sha256
> `3a5ef72d97af0c0004491567314e180bf3238bdaaff11457707a3138657b4507`) against evidence
> ledger sha256 `6232702eb8ab01e6508dee7a91418a7f272a41ae76681f35e3881a61de12e6ed`:
> cutoff, sample arithmetic, model arithmetic, snapshot mismatch and lineage,
> quotations, and reproducibility were verified. I do not attest to the evidence pack's
> method beyond these checks, to other studies, or to later edits."

## Gate 4 — owner's signatures (recorded 2026-11-16)

Recorded 2026-11-16 by `howt` (repo owner, release authority):

1. **Source/cutoff** on ledger `6232702eb8ab01e6508dee7a91418a7f272a41ae76681f35e3881a61de12e6ed`
   — accepting 2026-10, the measured snapshot join and its 27.46% not-established share,
   hawker completion dates as the only amenity vintage, and the withdrawals that follow.
2. **Publication** on text `3a5ef72d97af0c0004491567314e180bf3238bdaaff11457707a3138657b4507`.

Both are materialised in `signoffs[]` (roles `source` and `publication`, pinning the
**ledger** hash) in the same edit that set `editionSha256` and flipped the entry to
`approved`/`published`. The scientific seat is the recorded round-five review
(`automated: true`). Decision rows: [D12](../plans/2026-11-12-reporting-refresh-decisions.md).

Verified after the flip: pins re-hashed against the registry (`artifactSha256` × 3 = the
ledger on disk, `editionSha256` = the text on disk, roles exactly source/scientific/
publication); `bun run test:unit` 534 pass with the approved-series guard now expecting
four signed series; `bun run build` 223 pages with the archive route rendering
`data-edition-status="approved"` and three sign-off records.

## What this edition does not establish

No causal premium or amenity effect; no importance ranking; no temporal or period-shift
claim (one snapshot is joined to every period); no interaction or synergy estimate; no
condo statement; no mismatch magnitude for parks, supermarkets, malls, childcare,
preschools or MRT (no dated vintage — absence of dates is not evidence nothing changed);
no source-completeness claim. The supermarket coefficient is a thin contrast (1,177
transactions, 0.42%) with no effect interpretation.
