# RF08 — RS03 `temporal-evolution` edition sign-off record

- **Date:** 2026-11-15
- **Slice:** RF08 (refreshed studies), series `temporal-evolution` (register row RS03)
- **Evidence pack:** [RS03](2026-11-15-rs03-temporal-evolution-evidence.md) · ledger [`artifacts/rs03-temporal-evolution-evidence.json`](artifacts/rs03-temporal-evolution-evidence.json)
- **Producer:** `scripts/tools/temporal_evolution_evidence.py` (`--check` re-measures the checkout)
- **Frozen edition:** [`docs/analytics/editions/temporal-evolution/2026-11-15/temporal-evolution.md`](../analytics/editions/temporal-evolution/2026-11-15/temporal-evolution.md)
- **Contract:** [D12](../plans/2026-11-12-reporting-refresh-decisions.md) (three distinct attestations, no self-approval), [D07](../plans/2026-11-12-reporting-refresh-decisions.md) (edition ≠ observation window)
- **Registry:** `app/src/components/studies/lib/edition-registry.ts` — `temporal-evolution-2026-11-15`

This is the durable record of the RS03 gate sequence. The registry entry is the
machine-readable approval; this file keeps the reviewer's verbatim attestation and the
review history, so the wording survives outside a one-line `statement` field.

> **Status: complete.** Both owner signatures were given on 2026-11-15 and the registry
> entry is `approved`/`published` with three attestations on the ledger hash and
> `editionSha256` pinning the text. Gate 4 below records what was given and when.

## Gate 1 — evidence ledger

| Thing               | Value                                                                         |
| ------------------- | ----------------------------------------------------------------------------- |
| Ledger              | `docs/implementation/artifacts/rs03-temporal-evolution-evidence.json`         |
| sha256              | `1f0aef749b9f26b6f2f4a5f09cd472956080a413a11397c2160fd45759f71012`            |
| Reproducibility     | producer run twice → byte-identical; `--check` re-measures the tree           |
| Frozen edition text | `docs/analytics/editions/temporal-evolution/2026-11-15/temporal-evolution.md` |
| Text sha256         | `d95beefc8386291ffa60c94db6c0d9a5b9f9b289e52cf9c6a74c5517d4b02b8d`            |

Sign-offs attach to the **ledger** hash; the text is pinned separately by
`editionSha256`. A later edit to either invalidates its signature (trap #4).

## Gate 2 — the study's extra gate

The register requires comparable periods and period-correct feature vintages. Measured
outcome:

- **HDB re-cuts cleanly**: 118 study-window months observed across the three legacy
  windows, no source-missing and no zero-transaction months; the terminal month (2026-11,
  790 transactions = 0.3718 of the trailing-12-month median) is excluded as partial, and
  `planningAreaBaseline` is bounded at the same `lastCompleteMonth` (2026-10).
- **Condo cannot reproduce the comparison**: the private-residential source starts
  2021-01, so the pre-COVID window is 36/36 months **source-missing**; every condo change
  statement is withdrawn.
- **No vintage per window**: the only dated station snapshot is a single 2019-12-09
  legacy seed, school scoring carries no dates, and the shipped `dist_to_nearest_mrt` is
  measured to derive from the sha-pinned bronze station frame (`48a47362…`, 188 rows) and
  **not** from the 2019 seed — 1,224,710/1,224,710 rows reproduce exactly from bronze,
  0/1,224,710 from the seed. Premium-evolution claims are therefore **withdrawn as not
  measurable**, not restated softly.

## Gate 3 — scientific re-review of the article text (three rounds)

Reviewed by `openai-codex/gpt-6-luna (xhigh)` as `codex-luna-reviewer`. The pack review
does not cover article sentences, so this is a separate review of the frozen text.

**Round 1 — FAIL.** (i) the table extremes were attributed to "cells near the floor
(n = 30–60)" when both are Outram (2021: 631,500 n=94 → 959,000 n=172; 2023: 876,044
n=130 → 595,000 n=111); (ii) Sungei Kadut was counted as below-floor in 2024 when it has
no 2024 sales at all; (iii) "no source records MRT stations as of any past date"
overstated absence, since `MRTStations.geojson` is a 2019-12-09 vintage. Judgement calls
ruled in the author's favour: bold-stripped quotes are acceptable, and one
ellipsis-stitched quote is acceptable with the qualification that the fragments come from
different sections.

**Round 2 — FAIL.** (iv) the aggregation declared a 2026-10 cutoff but had no upper bound,
so the 2026 area-year figures included 790 November transactions (22,591 instead of
21,801); (v) exclusions were bucketed into a single reason although the endpoints overlap
(Sungei Kadut 2023 n=6 and 2024 absent); (vi) the "built from the current LTA snapshot …
per RS01" attribution was unsupported lineage, ruled **must re-measure or remove**.

**Round 3 — PASS.** All six prior defects closed; no new defects. The reviewer did not
accept the producer's 20,000-row sample as sufficient and recomputed the **full
population**: bronze 1,224,710/1,224,710 exact (0.0 m max deviation), legacy fallback
0/1,224,710 (2,010.3 m max deviation), using transaction coordinates and independently
recomputed distances rather than the shipped distance column as an input. It also noted
`sourceCoverage` extending to 2026-11 is legitimate coverage evidence while every study
window and the area-year baseline end at 2026-10.

### Verbatim attestation (round 3)

> “openai-codex/gpt-6-luna (xhigh; codex-luna-reviewer) reviewed
> `docs/analytics/editions/temporal-evolution/2026-11-15/temporal-evolution.md` (sha256
> `d95beefc8386291ffa60c94db6c0d9a5b9f9b289e52cf9c6a74c5517d4b02b8d`) against ledger
> sha256 `1f0aef749b9f26b6f2f4a5f09cd472956080a413a11397c2160fd45759f71012` and pack
> sha256 `586e133216d372d7784b2048e60cdcb08bdcf704dee66f9af72ad16ae6fbaeb1`;
> quantitative claims, lineage, cutoffs, absences and quotations verified; source
> completeness beyond this checkout and future revisions are out of scope.”

## Gate 4 — owner's signatures (**not yet given**)

Recorded 2026-11-15 by `howt` (repo owner, release authority), in the form D12 prescribes:

1. **Source/cutoff** on ledger `1f0aef749b9f26b6f2f4a5f09cd472956080a413a11397c2160fd45759f71012`
   — accepting 2026-10 as the last complete month, the measured HDB window coverage and
   composition, the condo pre-COVID window as source-missing, the single 2019-12-09 station
   vintage with no vintage per window, and the withdrawals that follow.
2. **Publication** on text `d95beefc8386291ffa60c94db6c0d9a5b9f9b289e52cf9c6a74c5517d4b02b8d`
   — authorising this exact text as the current approved edition.

Both are materialised in `signoffs[]` (roles `source` and `publication`, both pinning the
**ledger** hash) in the same edit that set `editionSha256` and flipped the entry to
`approved`/`published`. The scientific seat is the recorded review above
(`automated: true`). Decision rows: [D12](../plans/2026-11-12-reporting-refresh-decisions.md).

Verified after the flip: `bun run test:unit` 534 pass (the approved-series guard now
expects three signed series), `bun run build` 222 pages with
`dist/analytics/archive/2026/temporal-evolution-2026-11-15/temporal-evolution/` rendering
`data-edition-status="approved"` and three sign-off records, and the series page rendering
"Read the approved edition".

## What this edition does not establish

Restated so the signature is bounded: no premium and no premium change; no causal
attribution; no condo change statement; no trajectory or cluster classification; no
source-completeness claim. The withdrawals and their reasons are measured in the ledger,
not asserted in prose.
