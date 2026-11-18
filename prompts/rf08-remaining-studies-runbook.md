# RF08 remaining-studies runbook — taking the last 10 from `historical` to signed

- **Written:** 2026-11-18
- **For:** a fresh agent (and the repo owner) finishing RF08 after RS01–RS05
- **State at handoff:** **5 of 15 series signed and published** (`data-sources`, `rental-yields`, `temporal-evolution`, `amenity-impact`, `facility-premiums`). **10 remain.**
- **Read first:** [continuation brief](../docs/implementation/2026-11-14-rf08-continuation-brief.md) (gate sequence, mechanics, traps) · [worker prompt](rf08-study-worker-prompt.md) (the per-study dispatch template) · [handoff §4a–§4d](../prompts/handoffs.md) (what each completed study cost and taught) · [decision ledger D12](../docs/plans/2026-11-12-reporting-refresh-decisions.md)

This runbook is the operating manual. It assumes you will run the same loop the first five studies proved: **worker produces → you verify → independent reviewer re-derives → fix pass → narrow re-review → owner signs → verify and ship.**

---

## 0. The one decision the owner must make before anything starts

Every remaining study's register row names a specialist gate: **model approval** (`lease-decay`, `mrt-impact`, `macro-sensitivity`, `price-forecasts`), **causal/RDD review** (`school-quality`, `causal-inference-overview`), **spatial method review** (`spatial-autocorrelation`, `spatial-hotspots`), **segment/scoring owner approval** (`market-segments`), and RS15 gates on the rest.

Earlier in the programme those seats were left unnamed on purpose: a refreshed edition without its model approval is exactly what D12 exists to prevent. So the first act is a recorded owner decision, in this shape (add a row to the decision ledger's "Recorded decisions" table):

> **D12 / RF08 — named scientific reviewer for the remaining studies** — 2026-11-XX — `howt` — approves `openai-codex/gpt-6-luna` (xhigh, `codex-luna-reviewer`) as the independent scientific reviewer for RS06–RS15, including the model, causal/RDD, spatial-method and forecast seats, on the same terms as RS01–RS05: every verdict is recorded with model identity, `automated: true`, and the owner retains both signatures.

Until that row exists, a worker may produce evidence and text but **you must not** present a signature packet for a model-gated study. Do not invent a reviewer, and do not treat "the agent ran it" as approval.

Also agree the operating envelope with the owner before the first dispatch:

- **Signatures are per study and never delegated.** Two acts, both the owner's: source/cutoff on the ledger hash, publication on the text hash. You materialise them only after they are given.
- **Commit/push/deploy is per-turn permission**, not standing. The live site is `https://minghao51.github.io/egg-n-bacon-housing/`; each push redeploys.
- **No `.env`, no R2 sync, no `gh` mutations** unless the owner asks in that turn.

---

## 1. The queue

| #   | Series                                | Register gate                                               | Suggested order                           | What "done" may look like                                                            |
| --- | ------------------------------------- | ----------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------ |
| 1   | `macro-sensitivity`                   | real release vintages; fallback series excluded from claims | **first** — mostly a source-vintage audit | measured vintages + withdrawal of any claim resting on a generated/fallback series   |
| 2   | `segment/scoring` → `market-segments` | recover scaling, model version, cohort counts               | second — data archaeology                 | recovered or withdrawn segments; never reuse an old segment ID for a new population  |
| 3   | `lease-decay`                         | resolve PSF/PSM and total vs per-area **before fitting**    | third                                     | unit reconciliation + a refit or an explicit unit-withdrawal                         |
| 4   | `mrt-impact`                          | confirm metres/km and response variable; no "15×"           | fourth                                    | a stated response/log/PSF design, or withdrawal                                      |
| 5   | `price-forecasts`                     | rolling-origin validation, leakage, score expired 2025      | fifth                                     | validation harness + accuracy table, or withdrawal of dated forecasts                |
| 6   | `school-quality`                      | tiers, bandwidth, assignment, multiple testing              | sixth                                     | identification audit; almost certainly a withdrawal of causal language               |
| 7   | `spatial-autocorrelation`             | weights, disconnected areas, permutations                   | seventh                                   | reproducible weights + significance metadata                                         |
| 8   | `spatial-hotspots`                    | keep Jan 2024–Jan 2025 as its own window                    | eighth                                    | rerun of the stated method + instability disclosure                                  |
| 9   | `causal-inference-overview`           | estimand, pretrends, placebos                               | ninth                                     | identification audit; withdrawals likely                                             |
| 10  | `findings`                            | every sentence links to a reviewed edition                  | **last, always**                          | a summary whose every claim cites an approved edition and its population/window/unit |

Order rationale: front-load studies whose gate is a **source/vintage audit** (cheap, mechanical, high certainty), and push the ones whose gate is **identification** (expensive, likely withdrawal) later. `findings` must not start until every claim it cites is signed — if a dependency is unresolved, omit it or flag it, never summarize an unresolved model as settled.

---

## 2. The loop, per study

### 2.1 Dispatch the worker

Use `Agent` with `subagent_type: "glm-flash-worker"`, `model: "zai/glm-5.3-flash"`, `run_in_background: true`, a short `name` (`rf08-rs06`, …), and the prompt from [`rf08-study-worker-prompt.md`](rf08-study-worker-prompt.md) §2 with these substitutions:

`{{SERIES}}`, `{{SERIES_SNAKE}}`, `{{REGISTER_ROW}}`, `{{RS_NN}}`, `{{EDITION_DATE}}` (today, ISO), `{{EXTRA_GATE}}` (quote the register row verbatim).

Add to the prompt, every time:

- the two or three completed studies most similar to it, as worked examples of failure;
- the specific edge: e.g. for `lease-decay`, "resolve PSF/PSM and total-price vs per-area response **before** fitting; never convert a coefficient without confirming its original response/unit";
- the **ledger size ceiling**: no row-level dumps; counts + reason-set signatures + a `sha256` digest recomputed by `--check` (RS05 shrank 1,740 KB → 70.7 KB this way and the repo's large-file guard rejects >500 KB);
- "print full digests; never assemble a hash from a truncated prefix" (this cost a review round).

### 2.2 Verify the worker before any review

Never forward a worker's summary as fact. Minimum:

```bash
sha256sum docs/implementation/artifacts/rs<NN>-<series>-evidence.json \
          docs/analytics/editions/<series>/<date>/<series>.md      # must equal the reported digests
cp <ledger> /tmp/a.json && uv run python scripts/tools/<series>_evidence.py >/dev/null && cmp -s /tmp/a.json <ledger> && echo BYTE-IDENTICAL
uv run python scripts/tools/<series>_evidence.py --check
uv run python scripts/tools/verify_reporting_baseline.py --assets   # 15 sources / 72 assets
git status --porcelain                       # only this study's files + the registry entry
grep -c 'evidenceStatus: "approved"' ...     # the new entry must still be historical/draft
```

Then read the **edition text** yourself and grep for the defect classes in §4. Spot-check three numbers against the ledger keys the text cites. Only then dispatch the reviewer.

### 2.3 Dispatch the reviewer

`Agent` with `subagent_type: "codex-luna-reviewer"`, model `openai-codex/gpt-6-luna`, `thinking: "xhigh"`. Prompt template:

> You are performing the independent scientific review (D12 gate 4) of `<series>` in `/home/howt/work/egg-n-bacon-housing`. Review exactly: edition `<path>` sha256 `<full text hash>`; ledger `<path>` sha256 `<full ledger hash>`; pack `<path>` sha256 `<full pack hash>`; producer `<path>`; legacy text `<path>` (immutable — confirm unedited). Registry entry must be `historical`/`draft`, `editionSha256: null`, `signoffs: []`.
>
> This study's gate (register row `<RS_NN>`, verbatim): "<quote>". Judge the text against it.
>
> **Re-derive; do not proofread.** Extract every quantitative sentence and recompute it from the ledger or from the data. Re-run the producer and confirm byte-identical output. Check standard errors against the dependence structure the study itself measures (RS05's defect: HC1 SEs understated uncertainty 12–17× because 91% of variance was between projects — if a study publishes a between-group share, it must cluster on that group). Check quotations verbatim against the legacy file, absence semantics (`no-sales` ≠ `0` ≠ `missing-source` ≠ "facility absent"), cutoffs respected in every aggregation, exclusions as reason **sets**, and whether any inference rests on a battery the text elsewhere disclaims. Sweep for: own-voice causal vocabulary, chronology claims ("declared before", "pre-registered", "within-project … planned" — anything implying the design preceded the analysis without a dated protocol), proof language ("proves", "shows how") for descriptive or ablation results, and scope claims that exceed the code ("all 97 columns" when the producer scanned 18).
>
> Edit nothing. Do not read `.env`. Return `VERDICT: PASS|FAIL`, numbered defects each quoting the exact sentence and naming the ledger key or command, re-derived numbers, checks run, notes, and a one-line attestation naming the text and ledger hashes and stating what is out of scope.

Expect a first-pass FAIL. RS03 needed 3 rounds, RS04 needed 5, RS05 needed 4. A PASS on round one is possible but has not happened yet.

### 2.4 Fix passes

Resume **the same worker** (`resume: "<agent id>"`), not a fresh one — it retains the tool, ledger and text in context. The prompt must contain, for each defect: the exact sentence, the ledger key that contradicts it, and what the corrected sentence must say. Always add:

- "fix the **class**, then sweep the whole document for it; list every extra fix";
- "no measured number may change unless the defect is a measurement" (for wording-only passes, require a **structural ledger diff** proving strings-only — RS04's final pass changed exactly two keys);
- for a statistics or scope defect: change the **producer**, regenerate, and expect the ledger hash to move.

After any ledger change, the previous attestation is void (D12 trap #4 — a signature pins bytes, not a document). Re-review the **new** bytes; if the change was serialisation-only, say so and ask for a **narrow** PASS that re-attests.

### 2.5 The signature packet

Give the owner, in one message: the two **full** digests (ledger and text), what each signature covers, what it explicitly excludes, and the reviewer's verdict history. Then stop. Do not pre-fill `signoffs`.

### 2.6 Materialising a signature (only after it is given)

1. Registry entry: `evidenceStatus: "approved"`, `editorialStatus: "published"`, three `signoffs[]` (**all** pinning the ledger hash; none named `repo-agent/session-…`; scientific is the recorded run with `automated: true` and its `evidencePath`), and `editionSha256` = the text hash.
2. Unit test guard: extend the approved-series list in `app/tests/unit/edition-registry.test.ts` (it will fail until you do — that is the guard working).
3. Decision ledger: three rows (source/cutoff, scientific re-review, publication) with the full hashes and the round history.
4. Sign-off record: `docs/implementation/<date>-rs<NN>-<series>-editions-signoff.md` with the gate sequence, the review table (verdict per round and what each found), the **verbatim** attestation, and what the edition does not establish.
5. Docs: implementation README entry, `prompts/handoffs.md` (state row, §4x lesson block, next-actions), continuation-brief status row.
6. Verify: re-hash both files against the registry (`artifactSha256` ×3 = ledger, `editionSha256` = text, roles exactly source/scientific/publication); `bun run test:unit`; `bun run astro check`; `bun run build` and confirm the archive route renders `data-edition-status="approved"` with 3 sign-off records; `bunx playwright test tests/e2e/analytics`; `uv run pytest tests/ -q --no-cov`; baseline; layout; ruff; `uvx pre-commit run --all-files` (run twice — the fixers settle on the second).

---

## 3. Verification matrix (baselines at handoff)

| Check         | Command                                                                                                                                                            | Expected                                                                                  |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| Unit          | `cd app && PATH="$HOME/.bun/bin:$PATH" bun run test:unit`                                                                                                          | **534 pass / 0 fail / 34 files** (grows with each signed series: the approved-list guard) |
| Types/lint    | `bun run astro check`                                                                                                                                              | **0 errors / 0 warnings / 22 hints**                                                      |
| Build         | `bun run build`                                                                                                                                                    | **224 pages**, +1 per new archive route                                                   |
| E2E           | `PLAYWRIGHT_SERVER_COMMAND='bun run preview -- --host 127.0.0.1 --port <p>' PLAYWRIGHT_BASE_URL='http://127.0.0.1:<p>' bunx playwright test tests/e2e --workers=4` | **237 passed / 9 skipped**                                                                |
| Pages-prefix  | `bun run build:pages` then `node scripts/serve-pages-base.mjs` + `pages-base.spec.ts`                                                                              | **9 passed**                                                                              |
| Python        | `uv run pytest tests/ -q --no-cov`                                                                                                                                 | **1136 passed**                                                                           |
| Baseline      | `uv run python scripts/tools/verify_reporting_baseline.py --assets`                                                                                                | **15 sources / 72 assets**, bytes match                                                   |
| Docs layout   | `uv run python scripts/tools/validate_docs_layout.py`                                                                                                              | no findings                                                                               |
| Evidence      | `uv run python scripts/tools/<series>_evidence.py --check`                                                                                                         | re-measures byte-identically                                                              |
| Data boundary | `bun run validate-data`                                                                                                                                            | v1 `0e1013ee485f`, v2 `2c30e2aa836c`, 47,104 month cells                                  |
| Hooks         | `uvx pre-commit run --all-files` (twice)                                                                                                                           | all 13 pass                                                                               |

`bun run build` rewrites `app/public/data/catalog.jsonl.gz`; it is authorised output — keep it and pin the post-build bytes (30,414 B, `a67f2f68…` at handoff).

---

## 4. The defect canon — check every study against this

Every defect found in RS03–RS05 was **prose outrunning the ledger** except one statistics error. Use this as the authoring checklist _and_ the review checklist.

1. **Cell attribution.** A quoted extreme/percentile/count must name the group and its n (`RS03`: "cells near the floor (n=30–60)" when the cells were Outram at n=94–172).
2. **Reason sets, not buckets.** An exclusion with two causes records both (`RS03`/`RS04`: Sungei Kadut 2024 = no-sales _and_ prior-year below floor).
3. **Absence claims need counter-evidence.** Before writing "no source records X", grep the checkout — and read the _values_ of stamp columns you list (`RS03`: `FMEL_UPD_D = 2019-12-09` existed while the ledger only listed the column name).
4. **Cutoff discipline.** Every aggregation, not just the headline, ends at `lastCompleteMonth`; record the bound in the ledger (`RS03`: 790 November rows leaked into a 2026 table).
5. **Lineage must be measured, never cited.** RS03 re-measured with a negative control (1,224,710/1,224,710 from bronze, 0/1,224,710 from the seed); RS04 repeated it at location grain.
6. **An ablation is not a control.** Removing the nearest point is expected to change a distance; say what it demonstrates (the coordinates are in the feature) and what it does not (historical status).
7. **Standard errors must match the dependence structure you measured.** If you publish a between-project variance share, cluster on project (`RS05`: HC1 → clustered 12–17×; mall and hawker become indistinguishable from zero).
8. **Sweep for the statistic's other copies.** RS05 passed the main table and failed on three cells in a different table that kept the HC1 numbers.
9. **Scope claims must match the code.** "all 97 columns" when the producer scanned an 18-column projection; read the parquet **schema** (metadata only) if you claim the schema.
10. **No chronology claims.** "declared before it was run", "measures before any sentence below was written", "pre-registered" — without a dated prior protocol, disclose instead: _recorded, not pre-registered; specification search cannot be ruled out_.
11. **No proof language** for descriptive results: not "proves", "confirms that", "shows how".
12. **No own-voice causal vocabulary** — and do not recite the banned verbs inside a denial; a denial that repeats the claim keeps it on the page.
13. **Quote the legacy text's actual phrases**, not a paraphrase in quotation marks; strip bold markers is fine; ellipsis only for a genuine omission. Machine-check **both directions** (edition spans ↔ legacy, claims still quoted).
14. **Thin contrasts are labelled** and never interpreted (`RS04` supermarket −14.42% on 0.42% of rows; `RS05` childcare −13.24% on 1,248 rows in three planning areas).
15. **`no-sales` ≠ `0` ≠ `missing-source` ≠ "absent"**. Three distinct states; a grid gap is not a zero.
16. **Never fabricate a figure or a hash.** Measure it, print it, copy it. A sequencer once padded a truncated digest and the reviewer caught it — that cost a round and it was the right outcome.

---

## 5. Ledger hygiene

- Canonical JSON: `sort_keys=True`, `indent=2`, trailing newline, no timestamps, no absolute paths; two runs must be byte-identical.
- **Under 500 KB.** The pre-commit large-file guard rejects more. No row-level dumps: counts + per-reason counts + reason-set signatures + a `sha256` over the canonical payload, recomputed by `--check` (RS05's pattern, 1,740 KB → 70.7 KB with every measurement intact).
- Record `cutoffUpperBound`, `reasonSetSemantics`, `missingSourceSemantics`, `notFitted` (with reasons), `estimator` (units, controls, FE, SE type, what is **not** controlled), and `legacyQuoteCheck`.
- Ledgers, packs and editions are **hash-pinned**. `docs/analytics/editions/` and `docs/implementation/artifacts/` are excluded from prettier **and** `detect-secrets`; do not run formatters over them, and never re-pin a hash to match a formatter — regenerate with the producer.
- `--check` must fail on drift: quotes, digests, schema scope, exclusions, measurements.

---

## 6. Per-study gates, quoted from the register

Use these verbatim in the worker prompt's `{{EXTRA_GATE}}`; they are the acceptance bar, not decoration.

| Row                              | Gate                                                                                                                                                                                                                                                                                                                                                                |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RS06 `lease-decay`               | "Resolve PSF/PSM and total-price versus per-area response before fitting. Validate lease age as of transaction date. Reconcile article versus interactive-band lineage. Keep chart/model gates until repaired coefficients and wording are reviewed. Never convert a coefficient without confirming its original response/unit."                                    |
| RS07 `mrt-impact`                | "Confirm metres/km and total-price/log/PSF response. Compare standardized effects or state non-comparability; no raw coefficient '15×' or '4×' marketing. Separate predictive association from causation. Do not automatically unlock the MRT calculator."                                                                                                          |
| RS08 `school-quality`            | "Recheck tier provenance, bandwidth, treatment assignment, covariate balance and multiple-testing policy. School-quality model fit does not establish a causal admissions premium. Keep policy eligibility outside model outputs."                                                                                                                                  |
| RS09 `macro-sensitivity`         | "Explicitly identify generated/fallback series and exclude them from empirical claims unless the entire result is a labelled simulation. Document release lag, revisions, missing periods, stationarity and uncertainty. No present-day timing regime claims from unknown source vintages."                                                                         |
| RS10 `market-segments`           | "Recover feature scaling, clustering/model version and cohort counts; assess stability and map old/new segment identities. Do not reuse a segment ID for a different population."                                                                                                                                                                                   |
| RS11 `spatial-autocorrelation`   | "Record weights/neighbour definition, disconnected areas, permutation settings, sample adequacy and multiplicity correction. High-high labels are not future return or demand predictions. Produce reproducible memberships and uncertainty/significance metadata."                                                                                                 |
| RS12 `spatial-hotspots`          | "Retain January 2024–January 2025 as its own historical window. Rerun the stated hotspot method, disclose persistence/instability and sample changes. Keep rental hotspot results separate from the transaction-activity product."                                                                                                                                  |
| RS13 `causal-inference-overview` | "Recover estimand, treatment/control construction and assumptions. Check pretrends, confounding concurrent policies, anticipation and robustness/placebos. A new observation year does not by itself validate an old causal estimate."                                                                                                                              |
| RS14 `price-forecasts`           | "Reconcile article and predictive asset lineage first. Use rolling-origin validation, leakage checks, naïve trend/seasonal baselines, error metrics and empirical prediction-interval coverage. Name R² correctly. Score expired 2025 forecasts where comparable outcomes exist. Never advance a stored forecast date or reuse BUY/SELL prompts as current advice." |
| RS15 `findings`                  | "Refresh last. Every quantitative sentence links to a reviewed edition and exact population/window/unit. Omit or explicitly flag blocked dependencies; never summarize unresolved models as settled conclusions."                                                                                                                                                   |

---

## 7. Escalate to the owner when

- a study's gate cannot be satisfied from the checkout (a source or vintage is missing) — that is a **finding**, not a failure; withdraw the claim and say why;
- a refit would need a unit or response decision the register defers to the owner (`RS06`, `RS07`);
- a legacy claim's withdrawal would remove the study's entire subject (as RS05 effectively did) — confirm the owner still wants an edition that publishes an absence;
- a verification step fails for reasons outside the study (a baseline drift, a hook change, a CI red unrelated to the work);
- anything requires a commit, push, deploy, credential, or a signature.

## 8. Reporting back each study

```
STUDY: <series> (<row>)
ROUNDS: <n> — <verdict per round with the defect that caused it>
LEDGER: <path> sha256=<full>
TEXT:   <path> sha256=<full>
WHAT IT ESTABLISHES: <3-6 bullets with units and n>
WHAT IT WITHDRAWS: <legacy phrase -> not measured | re-measured, with the reason>
STATUS: ready-for-signature | signed | blocked (why)
VERIFICATION: <commands with counts>
```

**Definition of done for the programme:** all 15 series `approved`/`published`, each with a ledger that re-measures byte-identically, a frozen text no one has retro-edited, three distinct attestations, a sign-off record with the review history, and a live archive route that re-verifies its own pin on every build.
