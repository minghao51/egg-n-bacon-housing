# RS09 — `macro-sensitivity` editions sign-off

- **Date:** 2026-11-18
- **Study:** RS09, series `macro-sensitivity`, edition `macro-sensitivity-2026-11-18`
- **Result:** **approved and published** — the sixth of the fifteen RF08 series to carry three attestations and a frozen text pin.
- **Gate:** register row RS09, quoted verbatim in the [runbook §0](../../prompts/rf08-remaining-studies-runbook.md) and in the ledger's `scope`.

## The two pins

Two different objects, signed by three different attestations. Neither hash may be inferred from the other.

| Object                                                                                            | sha256                                                             | Bytes  |
| ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | ------ |
| Evidence ledger — `docs/implementation/artifacts/rs09-macro-sensitivity-evidence.json`            | `ae403f11db8786e4258418d8791c6e0255fe2f4800d32e624f4014b6af629d7b` | 96,351 |
| Frozen edition text — `docs/analytics/editions/macro-sensitivity/2026-11-18/macro-sensitivity.md` | `0741e45bde949357c9bd39fdbd59e40a341c7b86597223ad9ff0484b157f002c` | 39,982 |

- **All three sign-offs pin the ledger hash.** The source/cutoff and publication signatures are the owner's (`howt`, `automated: false`); the scientific signature is the recorded reviewer run (`openai-codex/gpt-6-luna (xhigh)`, `automated: true`).
- **`editionSha256` pins the text hash.** A later edit to either object voids only its own pin.
- The preparer is `repo-agent/session-2026-11-18`; the registry rejects any sign-off whose `name` equals `preparedBy`, and none of the three does.

## Gate sequence

1. **Evidence pack** — measured ledger plus the prose pack, produced by `scripts/tools/macro_sensitivity_evidence.py`, whose `--check` re-measures the checkout and passes byte-identically.
2. **Owner source/cutoff signature** on the ledger hash, recorded in the decision ledger under D12 before the status changed.
3. **Edition text** authored as a _new_ frozen source at the path above; the RF00 original under `editions/legacy/2026-11-12/` is unedited, which `verify_reporting_baseline.py --assets` proves (15 frozen sources, 72 assets).
4. **Independent scientific review** of the text against the ledger — seven text rounds, fourteen ledger rounds, all defects closed.
5. **Owner publication signature** on the text hash, then one atomic registry edit carrying the three attestations and `editionSha256`.

## Review history

Fourteen ledger rounds and seven text rounds produced roughly **30 defects**. Their distribution is the finding worth recording:

| Kind                                      | Count | Outcome                                                 |
| ----------------------------------------- | ----- | ------------------------------------------------------- |
| Wrong measurement                         | 4     | fixed at the computation and re-derived by the reviewer |
| Prose claiming more than the ledger held  | ~12   | rewritten to cite the field that establishes the claim  |
| Absence claimed against a chosen boundary | ~5    | scoped, and in two cases replaced by a measured scan    |
| A screen stated as a finding about origin | 7     | mechanised — see `check_edition_lexicon.py`             |
| A field that stopped re-measuring         | 1     | the scan no longer reads its own instruments            |

The four measurement defects are worth naming because they were not wording:

1. **Real CAGR** reused the nominal window's 36.75 years after deflating to a 36.667-year span (0.0432 → 0.0433).
2. **Missing-source rows were invisible** — `bank_rates`' 213 null rows were dropped before the inventory counted periods, so a 465-row file read as a 252-row series with no gap.
3. **A rate band was measured over the wrong window** — the article's 2024-2025 claim was answered with a 32-month mean instead of its own 24 months (2.3303 vs **2.7390**).
4. **The effective-n formula used one side of the pair** rather than the product of both series' lag-1 autocorrelations, which mis-scaled every serial-adjusted interval in both directions (`bank_rates` differences: effective n 34.7 → **248.3**).

One further defect was found by the producer's own final verification rather than by a reviewer: the ledger **stopped re-measuring** once sibling evidence tools were added to the directory its artefact scan covered. A hash-pinned artifact whose `--check` fails is not an artifact, so the scan now excludes `scripts/tools/` and the exclusion is disclosed in `excludedFromScan`.

## The scientific attestation, verbatim

> I attest to review of `docs/analytics/editions/macro-sensitivity/2026-11-18/macro-sensitivity.md`, sha256 `0741e45bde949357c9bd39fdbd59e40a341c7b86597223ad9ff0484b157f002c`, tracing to ledger sha256 `ae403f11db8786e4258418d8791c6e0255fe2f4800d32e624f4014b6af629d7b`. The text establishes checkout-specific fill-pattern screens, SORA comparison and lineage, stationarity and descriptive associations, and the stated legacy-claim dispositions. It does not establish series provenance, release lag or revisions, causal effects, timing or regime claims, affordability stress sensitivity, or segment CAGRs. The publication signature pins the **text** hash as `editionSha256`; the three sign-offs pin the **ledger** hash. These are distinct pins on distinct objects, with separate scopes.

Two limits on that attestation, stated rather than glossed:

- The reviewer could **not** diff the final ledger against its round-12 bytes, because superseded artifacts were not retained. Its verdict covers the current fields, not a proven equivalence to earlier rounds.
- `scripts/tools/check_edition_lexicon.py` is **advisory**. It reports 0 forbidden / 18 review-required on this text, but the reviewer demonstrated a construction that evades its quotation exemption. The text passed on reading, not on the gate.

## What this edition establishes

- The generated/fallback **screen**: `sora_rates` carries an annual-ramp signature (between-year variance share 0.9939, year-boundary step share 0.3444, monotone year-mean path, ADF **+5.16**), and `wage_growth` carries annual-resolution tiling (25 of 25 years hold one distinct value across four quarters). Both are excluded from every edition-facing figure, and **neither series' origin is certified** — a structural screen is not provenance.
- The **cost of that exclusion**, quantified on the 60 shared months: levels r **0.9422** for the ramp against **0.5870** for the source, same target, same months.
- The **source series**: `bank_rates.sora_3m`, 465 file rows of which 213 are missing-source and 252 carry values from 2005-10 to 2026-09.
- The **gold-column trap**: both SORAs ship as separate columns, each reproducing its source exactly (`sora_rate` from `sora_rates` 60/60; `sora_3m` from `bank_rates` 252/252), so `sora_rate` is the screened-out ramp.
- **Two of four rate bands reproduce** on the source series (2021 H1 mean 0.1796; 2023 mean 3.5915) and **two do not** (2022 H2 2.2247 against a quoted 2.5–3.5%; 2024-2025 2.7390 against 3.0–3.5%).
- **Stationarity and association**: six of eight series fail to reject a unit root in levels; associations are reported in levels _and_ first differences with serial-adjusted intervals, and level coefficients are explicitly not sensitivity readings.
- **35 legacy claims disposed**: 7 re-measured, 28 withdrawn, all quotations verbatim, every claim key resolving at build time.

## What this edition does not establish

- No series **provenance**; no release lag or revision history, because no vintages exist in the checkout.
- No **causal** effect and no **timing, lag-order or regime** claim — the regime boundaries and policy dates are recorded as unmeasurable.
- No **rate-shock or borrower-specific affordability** claim. A static export-time affordability lookup does exist (`scripts/export_app_data.py`), which is why the withdrawal is narrower than "no affordability code".
- No **segment-level CAGR**; annual tier medians exist but are not a constant-quality index.
- Nothing about the truth of the withdrawn legacy claims, and nothing outside the checkout at the pinned cutoff.

## Verification run for this sign-off

Run against the pinned bytes, in this order, all passing:

| Check                                | Result                                                                                                       |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| Producer `--check`, both studies     | byte-identical re-measure (RS09 `ae403f11…`, RS10 `96054968…`)                                               |
| Reporting baseline (`--assets`)      | 15 frozen sources, 0 live, 72 pinned assets; bytes match                                                     |
| Unit (`bun run test:unit`)           | **534 pass / 0 fail / 34 files** — the approved-list guard extended to six series                            |
| Types (`bun run astro check`)        | **0 errors / 0 warnings / 22 hints**                                                                         |
| Build (`bun run build`)              | **225 pages** (224 + the new archive route); the build fails if the text hash does not match `editionSha256` |
| Archive route render                 | `data-edition-status="approved"`, three `data-signoff-role` records (source, scientific, publication)        |
| Series page render                   | links the approved edition — "Read the approved edition"                                                     |
| E2E (`tests/e2e/analytics`)          | **57 passed**                                                                                                |
| Python (`pytest tests/ -q --no-cov`) | **1136 passed**                                                                                              |
| Docs layout                          | no findings                                                                                                  |
| Ruff                                 | clean                                                                                                        |
| Pre-commit (`--all-files`, twice)    | all 13 hooks pass on the second run                                                                          |

`app/public/data/catalog.jsonl.gz` was not rewritten by the build. `.secrets.baseline` gained two entries for the new edition's hashes — `detect-secrets` reads 64-hex sha256 values as high-entropy strings; the baseline records them as, correctly, `is_secret: false`.
