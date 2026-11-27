# Ledger re-pin review — 2026-11-24

**Scope:** the nine evidence ledgers re-pinned during the `master-audit-2026-11-23`
remediation, and the `artifactSha256` pins in
`app/src/components/studies/lib/edition-registry.ts` that hold them.

**Outcome:** approved. Every changed value is attributable to one of four
permitted causes; no coefficient, statistic, p-value, sample size, row count,
cutoff, disposition or data-derived number changed.

This record is the evidence path for the `scientific` attestation on the nine
affected editions. It replaces the free-text caveat that previously described
those pins as "re-derived, not re-attested".

## Why the ledgers moved

Two causes, kept separate because they need different treatment:

1. **Scan-surface defect.** The absence/method/token scans hashed _human prose_.
   A document that merely named a method — including the control table that
   documented the drift — moved a measurement, and the ledgers recorded line
   numbers and file hashes of that prose. `docs/plans/` and `docs/guides/` are
   now excluded from those scans and the exclusion is disclosed inside each
   ledger's own scan metadata. `docs/analytics/**` study prose and the frozen
   legacy corpus `docs/analytics/editions/legacy/**` remain **inside** every
   scan, because those are the article's own method words.
2. **Genuine code-hash drift.** The remediation edited source and test files the
   ledgers pin. A pin is supposed to follow its code; those re-hashes are
   legitimate and were spot-checked against `sha256sum` of files that
   `git status`/`git diff` show as genuinely changed.

## Review history

Three passes were run. All three are recorded because a rejected pass that was
later refuted is part of the evidence, not noise to be tidied away.

| Pass | Verdict     | What it established                                                                                                                                                                                                                                                                                                             | What went wrong                                                                                                                                                                                                                                                                                |
| ---- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | reject      | Verified all nine canonical hashes match the registry pins 3× each, and `rs15`'s `jointModel` drop. Judged `rs06/07/08/10/13/14` clean.                                                                                                                                                                                         | Flagged `rs11`/`rs12` as unverified within its turn budget, without enumerating them.                                                                                                                                                                                                          |
| 2    | reject      | Confirmed `rs15`; judged `rs11`'s disclosure **adequate** (`exclusions.prefixes` + `selfExclusion` name the narrowed surface, so the `meaning` sentence need not change).                                                                                                                                                       | Two methodological errors: (a) it expected the dropped-document `matchCount` sum to equal the _net_ delta, forgetting that an added file contributes; (b) it looked for dropped paths in the _current_ artifact, where by definition they cannot be. It also declined to recompute the hashes. |
| 3    | **approve** | Re-ran with corrected method (diff against `HEAD`; net-change identity). Verified per-leaf that every change is a disclosed exclusion, a re-hashed or newly-matching file that this working tree genuinely changed, a shifted line number inside identical quoted text, or a sibling-ledger re-pin. Recomputed all nine hashes. | Nothing.                                                                                                                                                                                                                                                                                       |

## The two contested reconciliations

**`rs11` `absenceScans.methodImplementationScan`** — `matchedFileCount` 31 → 22,
`totalMatches` 188 → 86. Ten files dropped, **all** under `docs/plans/`; one
file added, `app/src/components/dashboard/PriceMap.tsx`, because the scan token
`lisa` substring-matches the word "norm**alisa**tion" in a comment the
remediation reworded (`HEAD` said "normalized"). `rootsSearched`, `suffixes`
and `tokenPattern` are byte-identical to `HEAD`; only `exclusions.prefixes`
gained the two prose surfaces. The arithmetic is a net change:

```
188  old total
-103 dropped docs' matchCounts
  +1 added PriceMap match
= 86  new total   ✓ exact
```

**`rs12` `methodRecovery.tokens`** — 59 file-token pairs across 27 distinct
paths dropped: 24 under `docs/plans/`, 3 under `docs/guides/`
(`datagovsg-resource-migration.md`, `operations-runbook.md`,
`pipeline-development.md`), **0 unexplained**. Two pairs added, both
`tests/test_live_datagovsg.py`, a file this tree created.

**`rs15` `absenceScans.jointModel`** — `matchCount` 2 → 0; both dropped matches
were `docs/plans/*`.

## Canonical hashes (each appears exactly 3× — one per sign-off)

| Ledger                           | Canonical sha256                                                   |
| -------------------------------- | ------------------------------------------------------------------ |
| `rs06` lease-decay               | `496b63b5e1a4d7fc8d2399e70d81f063203fd6777ed73f7801ac1839db78560e` |
| `rs07` mrt-impact                | `bfb2c51800a65c622a402c130728efc0cebe1e84d0e36e6713223a96b9099e40` |
| `rs08` school-quality            | `1a02b6fa089d7d0f0f4767c173d4f476c38639d2123537fa231e71aa2b387e1d` |
| `rs10` market-segments           | `163273c4524bea3b45b2f53a0219ee459a7ce69812f49524218c2eda76bc9167` |
| `rs11` spatial-autocorrelation   | `0f2442ce74c2c6255b70ffd4b7ff94dc59b59c663af9e5de11519363e10fa4f7` |
| `rs12` spatial-hotspots          | `8103ac7579050a1f70aea713a4d23b673738684f550d5ef6769436baebc18567` |
| `rs13` causal-inference-overview | `d01d9d5f440a07a82f575fe3bc19c3e693ac315600097b304c39aba24130d059` |
| `rs14` price-forecasts           | `8d309700ff15a10501e758e27adb3d80409b745ce6d004803904f3828ff3a386` |
| `rs15` findings                  | `d0cabbf233efcc38e5ae989911a83c35ee99b0577cf14f93dae5dc42ee23e667` |

Hashing rule: `json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False)` +
a trailing newline, then sha256.

### Re-pins in this branch: four causes, all permitted

The ledgers were re-pinned four times. Each is the same permitted class — the
pinned surface genuinely changed — and none moved a coefficient, statistic,
sample size, cutoff or disposition. Recorded because the sequence is a real
property of this design, not tidying:

1. **Scan-surface narrowing + remediation code changes.** The original drift:
   `docs/plans/` and `docs/guides/` prose left the scans; six source files were
   re-hashed by the remediation itself.
2. **A new file.** `app/src/config/map-tiles.ts` raised `filesScanned` by one in
   seven ledgers — a census counts files, so adding one moves it.
3. **Formatting.** A `pre-commit run --all-files` pass reformatted five app
   source files _after_ re-pin 2, so four ledgers drifted onto their pre-format
   hashes. **Ordering matters:** format first, re-pin last. A whitespace-only
   source change still moves a pinned hash.
4. **A gitignored directory in a scan root.** `spatial_hotspots` scanned
   `data/analysis`, which is pipeline-generated and gitignored — present on a
   working checkout, absent on a clean one. Its census could never agree between
   a developer machine and CI. `data/analysis` is no longer a scan root; the
   census establishes absence from _tracked_ surfaces, and the legacy claims that
   cite `data/analysis/...` paths are recorded as text with their own
   "does not exist" notes.

Two consequences worth carrying into the next audit:

- **A pin on a file census is a maintenance cost, not a bug.** Every added file,
  every formatting pass and every generated directory is a re-pin event. That is
  the strongest argument for the evidence gate running weekly and on demand
  rather than in the path of every pull request.
- **The gate must be reproducible in the environment it runs in.** Anything
  untracked — generated output, prose, local caches — cannot be part of a hash
  that CI is expected to match.

## What this approval does and does not cover

- **Covers:** that the nine re-pinned ledgers differ from their previous
  committed bytes only for the four disclosed reasons, and that their new
  canonical hashes match the registry pins.
- **Does not cover:** the edition prose (`editionSha256`), other studies, or any
  claim about the underlying data. The `source` and `publication` attestations
  remain the recorded human signatures at their original dates; they are not
  restated here.

## Residual risk

The narrowing removes operational/planning prose from _code-absence_ scans. A
token that appears only in a guide is now invisible to those scans — which is
the intent (a runbook naming a method is not evidence the method is
implemented), but it does mean the ledgers no longer notice documentation that
describes an unimplemented method. That trade was made deliberately and is
disclosed in every ledger's own scan metadata.
