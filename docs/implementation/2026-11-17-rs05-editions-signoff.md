# RF08 — RS05 `facility-premiums` edition sign-off record

- **Date:** 2026-11-17
- **Slice:** RF08 (refreshed studies), series `facility-premiums` (register row RS05)
- **Evidence pack:** [RS05](2026-11-17-rs05-facility-premiums-evidence.md) · ledger [`artifacts/rs05-facility-premiums-evidence.json`](artifacts/rs05-facility-premiums-evidence.json)
- **Producer:** `scripts/tools/facility_premiums_evidence.py` (`--check` re-measures the checkout)
- **Frozen edition:** [`docs/analytics/editions/facility-premiums/2026-11-17/facility-premiums.md`](../analytics/editions/facility-premiums/2026-11-17/facility-premiums.md)
- **Contract:** [D12](../plans/2026-11-12-reporting-refresh-decisions.md) (three distinct attestations, no self-approval), [D07](../plans/2026-11-12-reporting-refresh-decisions.md) (edition ≠ observation window)
- **Registry:** `app/src/components/studies/lib/edition-registry.ts` — `facility-premiums-2026-11-17`

> **Status: complete.** Both owner signatures were given on 2026-11-18 and the registry
> entry is `approved`/`published`, with three attestations on the ledger hash and
> `editionSha256` pinning the text.

## Gate 1 — evidence ledger

| Thing                             | Value                                                                       |
| --------------------------------- | --------------------------------------------------------------------------- |
| Ledger                            | `docs/implementation/artifacts/rs05-facility-premiums-evidence.json`        |
| sha256                            | `8bdc5b8465907bbbe98851841b4080caa4fb246b8ed8e61503d59bcedf348970`          |
| Reproducibility                   | producer run twice → byte-identical; `--check` re-measures the tree         |
| Frozen edition text               | `docs/analytics/editions/facility-premiums/2026-11-17/facility-premiums.md` |
| Text sha256                       | `8027e19e6d4cc8fd2402b7dd1691d1e5ab7eaf4baae547605914380fbe38f6ea`          |
| Evidence pack                     | `docs/implementation/2026-11-17-rs05-facility-premiums-evidence.md`         |
| Pack sha256                       | `b40282cd734230dfb79764731f5f71f10c6b7b3706648b2539a53c93a53f8f76`          |
| Legacy text (immutable, unedited) | `d44ad9c54586b2b658ecd5589d0a9698b049f1b244e4e055216f8aad7a96efa0`          |

## Gate 2 — the study's extra gate (register RS05)

> "Recover facility ownership/date and join keys; assess missing facilities, correlated
> amenities and project effects. Publish uncertainty and sample sizes; no isolated
> causal-premium claim from unadjusted comparisons."

**The study's central measured finding is an absence**, and the edition is built around
disclosing it rather than working around it:

- **The in-house facility layer is absent from this checkout.** No source records which
  development has which private facility. Confirmed twice by the reviewer, independently:
  searches of `data/manual`, `data/pipeline/01_bronze` and the ingestion code, plus a
  full-schema scan of all 97 `unified_dataset` columns, find only the **public SportSG**
  layer (`dist_to_nearest_sports_facility`, `nearest_sports_facility`) — a different
  subject, not in-house facilities.
- **So the legacy study's core claims are withdrawn, not re-estimated:** the nine
  prevalence rows, the five "synergy" rows (+2–4% … +6–10%), "the first differentiating
  facility adds the most value", the external-proximity table, the buyer/investor/EC
  guidance, the "Data Period 2017-2026" window, and the four legacy data paths.
- **Missingness is `no-record`, never absence.** All nine legacy facilities and all five
  synergy combinations are recorded as `no-record` with reason
  `facility-source-absent` — explicitly not "0 facilities", not "the development has no
  pool".
- **Join key recovered and bounded:** `project_name`, 0 empty over 245,234 window rows,
  3,005 distinct strings, with the honest caveat that the most frequent value is the bulk
  label `LANDED HOUSING DEVELOPMENT` (2,788 rows, its own cluster; all landed subtypes, so
  none enters the non-landed model sample).
- **Project effects measured, not asserted:** 91.06% of log-psf variance is between
  projects and the five access indicators are 98.9–99.9% between-project, so the fitted
  access model is labelled a **between-project** comparison throughout, and a
  project-fixed-effects variant is recorded as `notFitted`, never run.
- **Uncertainty published two ways** (see Gate 3 — this was the study's hardest defect).
- **No facility premium, ranking, combination, quality or retention estimate is made.**

## Gate 3 — scientific re-review (three rounds)

Reviewed by `openai-codex/gpt-6-luna (xhigh)` as `codex-luna-reviewer`.

| Round | Verdict           | Findings                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ----- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | FAIL              | **HC1 SEs ignored project clustering**: with 91% of log-psf variance between projects, HC1 understated uncertainty 12–17× (MRT `0.001083`→`0.017982`, mall `0.001227`→`0.014870`, hawker `0.000871`→`0.012159`, SportSG `0.000846`→`0.011079`, childcare `0.018301`→`0.050451`), making mall and hawker indistinguishable from zero; own-voice use of banned vocabulary ("this edition **adds**…", reciting the banned verbs in a denial, "is **worth**"); the quotation check did not cover the edition, despite a sentence claiming it did |
| 2     | FAIL              | clustering fixed and verified independently (the reviewer recomputed the sandwich covariance and matched every value; correction factor `1.00073042`); vocabulary and quote-check coverage closed; **but three "measured analogue" cells still quoted HC1 SEs unlabelled** (mall `0.001227` vs clustered `0.014870`), and the edition claimed a **97-column** facility-like audit while the producer scanned an 18-column projection                                                                                                         |
| 3     | **PASS**          | all cells labelled clustered or explicitly HC1-for-comparison (16 `SE` occurrences, none bare); `legacy_source_audit()` reads the full parquet **schema** (`pq.read_schema`, no data read) and records 97 names, so the "all 97 columns" claim is exactly true and `--check` guards it; no new defects                                                                                                                                                                                                                                       |
| 4     | **PASS** (narrow) | serialisation-only change verified: every measurement present and unchanged (`includedN` 234,479; R² 0.7872/0.7871; 0.910638; 45 facility rows `no-record`; 46/46 quotes; 97/97 columns), the exclusion digest is recomputed by `--check` over a stated canonical basis (`500b8b2b…`, 10,755 rows), the edition wording stays accurate, and the large-file guard passes at 72,411 bytes. Re-attested the current pins because the round-3 attestation covers bytes that no longer exist (D12 trap #4)                                        |

### Verbatim attestation (round 3)

> "I reviewed the edition text at
> `docs/analytics/editions/facility-premiums/2026-11-17/facility-premiums.md` (sha256
> `381c3893fae8ccf8e948a80f4a2cda99fec44e922b83c96355cf7e0c3ab3a3a1`) against evidence
> ledger sha256 `056bdc239b236d1b56ea8dd9d3502eda89ad95b996ab757a9e31b1d2f837cd69`:
> I verified the listed corrections, schema audit, numerical consistency, withdrawals,
> quotation checks, and reproducibility. I do not attest to the evidence pack's method
> beyond these checks, to source availability outside this checkout, other studies, or
> later edits."

**Superseded pins (recorded 2026-11-18).** The round-3 review above ran against ledger
`056bdc23…` and text `381c3893…`. After it, the repo owner requested a size-only
serialisation change — the 10,755-row exclusion dump replaced by a count, reason-set
signatures, a sha256 digest and a 5-row sample; no measurement changed, re-verified by
`--check` — which moved the pins. The attestable bytes are now the ones in the Gate 1
table (ledger `8bdc5b8465907bbbe98851841b4080caa4fb246b8ed8e61503d59bcedf348970`, text
`8027e19e6d4cc8fd2402b7dd1691d1e5ab7eaf4baae547605914380fbe38f6ea`, pack
`b40282cd734230dfb79764731f5f71f10c6b7b3706648b2539a53c93a53f8f76`); the verbatim
attestation above is preserved as the record of what was reviewed and must not be
edited. Before signing, the owner should have the serialisation diff (measurements
unchanged) confirmed against the new ledger hash.

**The lesson this study adds to the programme:** after correcting a statistic, sweep for
its other copies. The clustered-SE correction was right in round two and still failed,
because three cells in a different table kept the old numbers — a page can contradict
itself without either sentence being wrong in isolation.

### Verbatim attestation (round 4 — the operative one)

> "I reviewed the edition text at
> `docs/analytics/editions/facility-premiums/2026-11-17/facility-premiums.md` (sha256
> `8027e19e6d4cc8fd2402b7dd1691d1e5ab7eaf4baae547605914380fbe38f6ea`) against evidence
> ledger sha256 `8bdc5b8465907bbbe98851841b4080caa4fb246b8ed8e61503d59bcedf348970`:
> I verified the listed measurements remain present and unchanged, the exclusion digest is
> reproducibly enforced, and this attestation supersedes the round-three one because the
> ledger changed only in serialisation. I do not attest to the evidence pack's method
> beyond these checks, to source availability outside this checkout, other studies, or
> later edits."

The reviewer could not byte-compare against the pre-slim ledger (it is not in git), so it
reasoned from the producer code plus the round-3 measurements recorded above — and
independently confirmed 1,102 projects in the median summary, all 45 facility rows
`no-record`, 46/46 quotes, 46/46 edition spans, 97/97 column names, and a byte-identical
rebuild at 72,411 bytes.

Recorded 2026-11-18 by `howt` (repo owner, release authority):

1. **Source/cutoff** on ledger `8bdc5b8465907bbbe98851841b4080caa4fb246b8ed8e61503d59bcedf348970`.
2. **Publication** on text `8027e19e6d4cc8fd2402b7dd1691d1e5ab7eaf4baae547605914380fbe38f6ea`.

Materialised in `signoffs[]` (source and publication both pinning the ledger hash) in the
same edit that set `editionSha256` and flipped the entry to `approved`/`published`. The
scientific seat is the round-four attestation above. Decision rows:
[D12](../plans/2026-11-12-reporting-refresh-decisions.md).

Verified after the flip by re-hashing both files against the
registry (`artifactSha256` × 3 = ledger on disk, `editionSha256` = text on disk, roles exactly
source/scientific/publication), `bun run test:unit` 534 pass with the approved-series guard
now expecting five signed series, and `bun run build` 224 pages with the archive route
rendering `data-edition-status="approved"` and three sign-off records.

## What this edition does not establish

No facility premium, prevalence, combination, quality or retention estimate; no causal
claim of any kind; no within-project estimate; no temporal or per-period statement (one
undated snapshot per access layer); no 2017–2020 statement (the condo source starts
2021-01); no ranking of facilities or amenities; no completeness claim about sources
outside this checkout. The accessible coefficients describe **external access between
projects**, with project-clustered uncertainty, and mall/hawker are not distinguishable
from zero on this design.
