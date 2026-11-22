# RF08 — handoffs for the remaining nine studies

- **Written:** 2026-11-18, immediately after RS09 was signed.
- **For:** fresh agents taking RS06, RS07, RS08, RS10 (text only), RS11, RS12, RS13, RS14, RS15.
- **State:** **all 15 series approved and published.** The nine studies this document was written for all closed: RS06, RS07, RS08, RS11, RS12, RS13, RS14 on 2026-11-20-21 and RS15 last. The instruments in §2 are what every signature rests on, and each of the eight hard rules in §3 was earned again at least once in the closing run — including a fabricated absence claim, a broken determinism gate, a cross-object citation, a stale pin on an already-signed edition, and restated scan counts.
- **Read in this order:** [remaining-studies runbook](rf08-remaining-studies-runbook.md) (process) · [the account](../docs/implementation/2026-11-18-rf08-remaining-studies-account.md) (per-study inputs, measured) · **this document** (what changed after RS09, and the per-study briefs).

> This document exists because RS09 cost **fourteen ledger rounds and seven text rounds** against a previous worst of five, and almost none of that was arithmetic. Everything below is either an instrument that ended a recurring defect class, or a per-study trap that has already been measured. Use them. Do not rediscover them.

---

## 1. The shared contract, compressed

Five gates, in order, per study. The full text is in the [runbook §2](rf08-remaining-studies-runbook.md); this is the skeleton:

1. **Evidence pack** — a `scripts/tools/<series>_evidence.py` producer, a canonical JSON ledger under `docs/implementation/artifacts/`, and a prose pack under `docs/implementation/`. The producer must have a `--check` mode that re-measures the checkout and fail on drift.
2. **Owner source/cutoff signature** on the **ledger** hash. Only the owner signs. The preparer is `repo-agent/session-<date>`; the registry rejects any sign-off whose `name` equals `preparedBy`.
3. **Edition text** as a **new** frozen source at `docs/analytics/editions/<series>/<date>/<series>.md`. Never edit the RF00 original under `editions/legacy/2026-11-12/`.
4. **Independent scientific review** of the text against the ledger, by `codex-luna-reviewer` on `openai-codex/gpt-6-luna`, thinking `xhigh`. The producer never reviews its own text.
5. **Owner publication signature** on the **text** hash, then one atomic registry edit carrying three attestations (all on the ledger hash) plus `editionSha256` (the text hash).

**Three actors, not four.** The orchestrator produces code, numbers and text. `doc-writer` (`opencode-go/mimo-v2.6-pro`) is available for long-form records but is **no longer a required hop** — the D12 pass-through row of 2026-11-18 lets the orchestrator author draft records directly. The reviewer reviews and writes nothing. The owner signs.

**Two pins, two objects.** Sign-offs pin the ledger; `editionSha256` pins the text. A re-run that changes one byte voids only its own pin.

---

## 2. The instruments — use these, don't rebuild them

All four exist in the repo and each one closed a defect class that recurred for multiple rounds.

### 2.1 Producer template

Copy the structure of `scripts/tools/market_segments_evidence.py` or `macro_sensitivity_evidence.py`:

- `canonical_bytes()` — `json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False)` + trailing newline; no timestamps, no absolute paths.
- `--check` — re-measure, compare bytes, print which **top-level key** drifted.
- `inputs` — every file read, sha256 + row/byte counts.
- `cutoff` — the measured last-complete-month rule (terminal month's count ÷ trailing-12 median), recorded as a field, not prose.
- `legacyClaims` + `legacyQuoteCheck` — every claim of the legacy text with a status, a ledger key, and a verbatim quote check.

Determinism is a **hard requirement**: two runs must be byte-identical (`cp` → re-run → `cmp`). A ledger that does not re-measure is not a ledger; RS09's passed review and then failed `--check` when a sibling tool was added to its scan.

### 2.2 `claimKeyCheck` — every claim key must resolve

Both signed ledgers call a resolver at build time: each `legacyClaims[].ledgerKey` is walked against the ledger (dicts by key, lists by item `id`), and an **unresolved key fails the build**. Three dangling keys shipped in RS09 and two in RS10 before this existed; every review round after that spent its effort on content instead of references.

Copy it verbatim. It is ~30 lines. Document in the ledger that resolution is **syntactic** — it does not judge whether the resolved field supports the disposition. That judgement stays with the reviewer.

### 2.3 `methodArtefacts` — measure absences, never assert them

The single most productive instrument of the whole programme. `notMeasurable` entries are **absence claims**, and an absence claim must cite a scan that lists its matches:

```json
"lagTesting": {
  "status": "notMeasurable",
  "reason": "the methodArtefacts scan of the shipping Python surface found no
             cross-correlation, lead-lag or lag-order implementation
             (methodArtefacts.results.lagOrCrossCorrelation records zero matches
             beside the scanned file count ...), and this study ran no such test ..."
}
```

Rules learned the hard way:

- Record **every matched file and its count**, not just a number.
- **Exclude the instruments.** `scripts/tools/` must be out of any scan whose result is hash-pinned, or the ledger drifts the moment a sibling study adds a tool. Disclose the exclusion in an `excludedFromScan` field. **A scan with prose roots needs a wider exclusion than a Python-only scan:** RS10's scan covered `docs`, `scripts`, `src`, `assets`, `prompts`, `app/src` and `.claude/handoffs`, so the `check_edition_lexicon.py` instrument alone moved its pinned `filesScanned` 348 → 349 and `--check` failed on a ledger that had already passed review. Excluding only `scripts/tools/` would have fixed that one file and left the same failure waiting for the next edition text or handoff; the shipped fix excludes `scripts/tools/`, `prompts/`, `docs/implementation/` and published edition texts (`editions/legacy/` stays in, because the article's own method claims are what the tokens match). Prove the exclusion cost nothing by diffing the two ledgers field by field — RS10's diff was three fields, all in the scan declaration, with every token match block byte-identical.
- Never write a count into prose. RS09 hard-coded "across 66 files", the exclusion changed the scan to 54, and the ledger failed its own check. Prose says "records zero matches beside the scanned file count"; the number lives in the field.
- A zero match is counter-evidence for _"none was found"_, never for _"none exists"_. Say which.

### 2.4 `check_edition_lexicon.py` — advisory only

```bash
uv run python scripts/tools/check_edition_lexicon.py \
  --ledger docs/implementation/artifacts/<series>-evidence.json \
  docs/analytics/editions/<series>/<date>/<series>.md
```

Forbidden: "is/was generated", "the generated … series", "identifies the generated", "proven to be", "proves", "confirms that", "shows how", "demonstrates", chronology claims, and the registry tokens `approved`/`signoffs`/`editionSha256`. Review-required: `generat*`, `fallback`, `identif*`, causal vocabulary.

**It is not proof.** A reviewer demonstrated a sentence that commits the defect and passes it. It is a smoke alarm. The text passes on a reader's judgement, and the gate's `--ledger` exemption only works when a match sits inside a quoted span whose content matches a `legacyClaims` phrase.

### 2.5 Retain superseded artifacts

RS09's reviewer could not diff its final ledger against its round-12 bytes because earlier artifacts were not kept, so its verdict covered current fields but could not prove equivalence. **Copy each attested ledger to `docs/implementation/artifacts/superseded/` before regenerating it.** A re-attestation should be a diff, not a fresh audit.

---

## 3. The eight hard rules

Each one cost at least one review round. They are ordered by how often they recurred.

1. **A screen is not a finding about origin.** A structural pattern ("annual-ramp signature", "annual-resolution tiling") says what a series _looks like_, never how it was produced. Seven instances across RS09's ledger and text; it is the most frequent defect in the programme. Write "screened as `<pattern>`", "flagged", "origin unverified" — never "generated", "is a fallback", "identified as".
2. **An unlinked artefact cannot adjudicate a linked claim.** Six instances in RS10. If a plot or panel is not linked to the run being described, it is evidence _neither for nor against_; say so in both directions. The limitation is symmetric — do not use it to support a conclusion and then deny the linkage one paragraph later.
3. **An absence needs a boundary and a scan.** State which roots were searched, list the matches, and do not let the sentence claim more than the scan does. Two RS10 absences were simply wrong because the producer chose the wrong directory.
4. **Do not prescribe what the source does not state.** RS10's producer asserted an observational unit for the legacy article's `r ~ -0.3` that the article never specifies. Record such statistics as _underspecified and not reproducible_.
5. **Do not invent or infer a number you cannot re-derive.** Plots were recorded as a **human visual read** with hashes, explicitly not machine-measured and not re-derived from pixels. That is the honest form.
6. **Scope claims match the code.** Read the parquet **schema** (metadata only) before claiming a column set; read the producer before claiming what it scanned.
7. **`no-sales` ≠ `0` ≠ `missing-source` ≠ absent.** RS09's `bank_rates` is 465 **file rows**, 213 missing-source, 252 values from 2005-10. A file-row count describes the file, not the series.
8. **Cutoff discipline.** Every aggregation — not just the headline — bounded at `lastCompleteMonth` (**2026-10**), with the bound recorded as a field.

---

## 4. Verification matrix (baselines after RS09)

| Check         | Command                                                                                                                                                                        | Expected                                                                          |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| Unit          | `cd app && PATH="$HOME/.bun/bin:$PATH" bun run test:unit`                                                                                                                      | **534 pass / 0 fail / 34 files** — grows by one entry per signed series           |
| Types         | `bun run astro check`                                                                                                                                                          | **0 errors / 0 warnings / 22 hints**                                              |
| Build         | `bun run build`                                                                                                                                                                | **225 pages**, +1 per new archive route; fails if the text hash ≠ `editionSha256` |
| E2E analytics | `PLAYWRIGHT_SERVER_COMMAND='bun run preview -- --host 127.0.0.1 --port 4399' PLAYWRIGHT_BASE_URL='http://127.0.0.1:4399' bunx playwright test tests/e2e/analytics --workers=4` | **57 passed**                                                                     |
| E2E full      | same, `tests/e2e`                                                                                                                                                              | **237 passed / 9 skipped**                                                        |
| Python        | `uv run pytest tests/ -q --no-cov`                                                                                                                                             | **1136 passed**                                                                   |
| Baseline      | `uv run python scripts/tools/verify_reporting_baseline.py --assets`                                                                                                            | 15 sources / 72 assets, bytes match                                               |
| Docs layout   | `uv run python scripts/tools/validate_docs_layout.py`                                                                                                                          | no findings                                                                       |
| Evidence      | `uv run python scripts/tools/<series>_evidence.py --check`                                                                                                                     | byte-identical                                                                    |
| Hooks         | `uvx --from pre-commit pre-commit run --all-files` **(twice)**                                                                                                                 | all 13 pass on the second run                                                     |

Two operational notes: `bun run build` does **not** currently rewrite `catalog.jsonl.gz`, but check `git status` after any build. A new edition's 64-hex hashes need **two `.secrets.baseline` entries** (`is_secret: false`) or `detect-secrets` fails — compute `sha1(secret).hexdigest()` and insert them sorted by line number, then `git add .secrets.baseline` (staging, not committing).

---

## 5. Per-study briefs

Each brief names the gate verbatim, what the checkout actually holds (measured 2026-11-18, see the [account](../docs/implementation/2026-11-18-rf08-remaining-studies-account.md) for detail), the trap specific to that study, and the outcome shape the gate most plausibly permits. **The order is the recommended order**, and it front-loads cheap source audits before expensive identification work.

### RS06 `lease-decay` — model/unit approval

> "Resolve PSF/PSM and total-price versus per-area response before fitting. Validate lease age as of transaction date. Reconcile article versus interactive-band lineage. Keep chart/model gates until repaired coefficients and wording are reviewed. Never convert a coefficient without confirming its original response/unit."

**Present:** `lease_commence_date`, `remaining_lease`, `price`, `area_sqm`, `psf`, `Unit Price ($ PSF)`, `Unit Price ($ PSM)`, `town`, `floor_level`, `dist_to_nearest_mrt`; `app/public/data/interactive_tools/lease_decay_analysis.json.gz` (13 bands + 3 insights + 30 `town_decay_rates`).
**Absent:** the legacy band definition as executed (the L1 frame is retired); the fitted model.
**Traps:** `+$54.75 PSF per extra year` — the appendix calls the response `price_per_sqm` while the sentence says PSF, which is precisely what the gate forbids converting without confirming; the `Discount vs 90+ yrs` column mixes median **price** with PSF discounts; `PASIR RIS −20.2%` is the inverse of its own row.
**Outcome shape:** unit reconciliation plus one stated response (or explicit unit-withdrawal), and the article-vs-interactive band reconciliation.

### RS07 `mrt-impact` — model approval

> "Confirm metres/km and total-price/log/PSF response. Compare standardized effects or state non-comparability; no raw coefficient '15×' or '4×' marketing. Separate predictive association from causation. Do not automatically unlock the MRT calculator."

**Present:** `dist_to_nearest_mrt`, `nearest_mrt_tier`, `nearest_mrt_is_interchange`, `nearest_mrt_score`; `interactive_tools/mrt_cbd_impact.json.gz` (`property_type_multipliers`, `town_multipliers`, `cbd_coefficients`, `town_premiums`, `town_impacts`).
**Absent:** **`raw_mrt_stations.parquet` is 188 rows of `name/lat/lon/line` — no opening date, no status.** No XGBoost/SHAP artefact, no OLS output, no CBD definition asset.
**Traps:** the `15×` condo-vs-HDB multiple is explicitly banned; the SHAP importance table (hawker 27.4% …) has no artefact, the same withdrawal shape as RS04; the town table's sign spread (+$59.19 → −$38.54) is unlabelled heterogeneity.
**Outcome shape:** a stated response and standardized-effect comparison the checkout can re-measure; withdraw the multiple and the ranking.

### RS08 `school-quality` — causal/RDD review

> "Recheck tier provenance, bandwidth, treatment assignment, covariate balance and multiple-testing policy. School-quality model fit does not establish a causal admissions premium. Keep policy eligibility outside model outputs."

**Present:** `nearest_schoolPRIMARY_dist`, `nearest_schoolSECONDARY_dist`, `dist_to_nearest_school`, `nearest_top_primary_school_dist`, `nearest_top_secondary_school_dist`, `school_accessibility_score`; `raw_school_directory.parquet` 337 rows with `sap_ind`, `autonomous_ind`, `gifted_ind`, `ip_ind`, `zone_code`, `mainlevel_code`, `nature_code`.
**Absent:** **none of the three feature names the coefficients use exists in any layer** (`school_primary_quality_score`, `school_primary_dist_score`, `school_secondary_dist_score`); no school coordinates; no tier artefact; no dated 1 km admission boundary; no RDD.
**Traps:** the three coefficients (+$9.66/+$6.27/+$3.52 PSF) cannot be re-derived; the RDD's `−$79.47 PSF` rests on a **failed covariate balance** — a failed-design estimate, not a premium; the regional split flips sign in RCR.
**Outcome shape:** an identification audit, a distance-based association with the proxy tier named, and withdrawal of causal/RDD language.

### RS10 `market-segments` — **text only; the ledger has PASSED**

**Ledger (signed-ready, do not regenerate without cause):** `docs/implementation/artifacts/rs10-market-segments-evidence.json`, `96054968644b2251eee27b9975af468b6223987e9750e74d60db7e8879c7e55e`, 102,541 bytes, passed at round 14 with one non-blocking warning about `definition` wording.
**What it establishes:** the six segments' names and shares come from a PSF-based KMeans (`data/analysis/market_segmentation_2.0/`, **6/6 names, 6/6 shares at three decimals**); the counts are **not** those cluster counts nor a constant multiple (ratios 9.502–9.5831); **0 id matches** for per-transaction membership; a many-to-many area block; an adjacent 911,797-row three-tier panel at **+343**; documented version `Cluster Version: 2.0 (PSF-based)`; plot annotations as a human visual read; HDB-only CAGR (5 of 6 areas outside the legacy bands, Bukit Timah refused at n=39); **36 claims** disposed.
**The one job:** write the edition text, then gate 4 then gate 5. The text must never say "no per-transaction segmentation exists in the checkout" — the six _stored segments_ have no membership.

### RS11 `spatial-autocorrelation` — spatial method review

> "Record weights/neighbour definition, disconnected areas, permutation settings, sample adequacy and multiplicity correction. High-high labels are not future return or demand predictions. Produce reproducible memberships and uncertainty/significance metadata."

**Present:** `lat`/`lon` on every transaction; `esda>=2.8.1`, `libpysal>=4.14.1`, `h3==4.1.0b2` in the `research` dependency group, so the method **is** runnable here; `app/public/data/analytics/spatial_analysis.json.gz` with a `methodology` string and 41 planning areas.
**Absent / broken:** the served payload is a **placeholder** — the first area returns `z_score 0.0`, `p_value 1.0`, `moran_i_local 0.0`, `spatial_lag 295000.0` (a constant), `neighborhood_multiplier 1.0`. **Moran's I 0.766 / z 9.91 are not recoverable from it.** The legacy appendix also names a _rental_ input for an _appreciation_ finding.
**Traps:** the cluster table (16 HH / 17 LH / 1 LL / 8 NS cells) is unreproducible as stated; "transition analysis: moderate persistence" is a time-series claim with no time dimension in the asset.
**Outcome shape:** re-measured Moran's I and LISA memberships with recorded seed, weights and multiplicity; withdraw the transition/persistence claims.
**Ownership note:** RA04 (`analytics/spatial_analysis.json.gz`) is **RS11's alone** — RS12 must write a new rental-only asset.

### RS12 `spatial-hotspots` — spatial method review

> "Retain January 2024–January 2025 as its own historical window. Rerun the stated hotspot method, disclose persistence/instability and sample changes. Keep rental hotspot results separate from the transaction-activity product."

**Present:** `raw_hdb_rental.parquet` 215,469 rows (2021-01 → 2026-10, **no coordinates**); sale-side block geocodes give 11,637 distinct `(block, street_name)` keys. **Measured today: 39,385 of 39,478 rental rows in the gate's own window (2024-01 → 2025-01) join to a sale-side block geocode = 99.76%.** The retired `search_result == 0` flag is replaceable with that join, and the 0.24% unmatched rows are a disclosable population.
**Absent:** the Gi\* implementation, the H3 cell tables (legacy claims 847 cells / 623 sufficient), transition probabilities.
**Traps:** `Orchard $3,200 median` — check `monthly_rent`'s observed range before quoting any level; "12 H3 cells at 99%" and the −3.21/−2.98/−2.67 coldspots have no artefact.
**Outcome shape:** a rerun of the stated method on the measured population, window pinned, written to a **new** rental-only asset (never overwrite RA04).

### RS13 `causal-inference-overview` — causal identification review

> "Recover estimand, treatment/control construction and assumptions. Check pretrends, confounding concurrent policies, anticipation and robustness/placebos. A new observation year does not by itself validate an old causal estimate."

**Present:** 1,236,310 transactions 1990-01 → 2026-11; `property_type`, `planning_area`, `region`; `market_segment` **private rows only** (990,655 nulls = the HDB rows).
**Absent:** `housing_policy_dates.parquet`, the DiD/RDiT code, the estimand, the bandwidth grid, pretrends, the Bala depreciation schedule.
**Recorded disposition (D12, 2026-11-18):** with no dated policy artefact, the two headline numbers — the CCR-vs-OCR DiD `−$137,743` and the HDB RDiT `+$13,118` jump — are **withdrawn as unreconstructable identification**, and the edition publishes that absence with the reason. This is already decided; do not re-litigate it.
**Outcome shape:** an identification audit; withdrawals, not reconstructions.

### RS14 `price-forecasts` — forecast/model approval

> "Reconcile article and predictive asset lineage first. Use rolling-origin validation, leakage checks, naïve trend/seasonal baselines, error metrics and empirical prediction-interval coverage. Name R² correctly. Score expired 2025 forecasts where comparable outcomes exist. Never advance a stored forecast date or reuse BUY/SELL prompts as current advice."

**Present:** `app/public/data/analytics/predictive_analytics.json.gz` — `forecast_horizon "6_months"`, `model_r2 0.89`, `last_training_date "2025-01-01"`; 41 areas each with `price_forecast{projected_change_pct, CI bounds, model_r2, forecast_date "2025-07-01", signal "BUY"}`.
**Absent:** the train/test splits, the feature list, per-segment model outputs, any provenance for the article's per-segment R² table (79.8/98.5/85.6/72.6/30.1 with ±18.58% to ±1877.88%).
**The opportunity this gate gives you:** realised outcomes now run to **2026-10**, so the expired `2025-07-01` projections **can be scored** — rolling-origin, naïve baseline, empirical PI coverage. That turns an audit into a measurement.
**Traps:** `model_r2 0.89` is an in-sample fit statistic, not forecast accuracy — "name R² correctly" is the gate's own wording; `signal: "BUY"` on an expired forecast is exactly the "never reuse BUY/SELL prompts as current advice" clause.
**Outcome shape:** lineage reconciliation plus an accuracy table scoring the expired projections.

### RS15 `findings` — **last, always**

> "Refresh last. Every quantitative sentence links to a reviewed edition and exact population/window/unit. Omit or explicitly flag blocked dependencies; never summarize unresolved models as settled conclusions."

**Present:** the legacy text; **six** approved editions; RA01 `app/src/data/persona-content.json` still carrying unsupported promises.
**Constraint:** blocked by design until every cited claim has a signed edition. The register permits a **narrower** summary ("The whole register need not be completed to publish an honest, narrower summary"), so a six-edition findings page is publishable before the rest — as an explicit narrower scope, never as "programme complete".

---

## 6. Parallelism, and the file-ownership map

Measurement and drafting parallelise cleanly; **signature materialisation does not**. Do not start a study's prose until its ledger has passed, and do not update an edition text's digest citations until the ledger is final — RS09's text was re-reviewed three times for that single mistake.

**Owned per study, safe to write concurrently:** `scripts/tools/<series>_evidence.py` · `docs/implementation/artifacts/<series>-evidence.json` · `docs/implementation/<date>-rs<NN>-<series>-evidence.md` · `docs/analytics/editions/<series>/<date>/<series>.md` · the sign-off record.

**Shared, serialised, signature-time only:** `app/src/components/studies/lib/edition-registry.ts` (one entry per edition; a file under `editions/*/*/*.md` with no registry entry makes `getStaticPaths` throw) · `app/tests/unit/edition-registry.test.ts` (the approved-list guard, which **will** fail until extended — that is the guard working) · `docs/plans/2026-11-12-reporting-refresh-decisions.md` (three D12 rows) · `docs/implementation/README.md`, `prompts/handoffs.md`, the continuation brief · `.secrets.baseline` (two entries per new edition) · `app/public/data/catalog.jsonl.gz` (build output; check `git status`).

**Policy:** RA06→RS06, RA07→RS07, RA05→RS10, RA02→RS14, **RA04→RS11 only**. RS12 writes a new rental-only asset. Producers never write `data/pipeline/**`; if a refit must persist, use a study-scoped path outside the medallion.

**Suggested waves:** (A) RS06 + RS07 units · (B) RS11 + RS12 spatial · (C) RS14 forecast · (D) RS08 + RS13 identification · (E) RS10 text · (F) RS15 last. Waves are not barriers — a finished study can sign while the next measures.

---

## 7. Reporting back, and escalation

Report per study using the runbook's §8 form: `STUDY / ROUNDS / LEDGER sha256 / TEXT sha256 / WHAT IT ESTABLISHES / WHAT IT WITHDRAWS / STATUS / VERIFICATION`.

**Escalate to the owner** when a gate input is missing (that is a finding, not a failure — withdraw and say why), when a refit needs a unit or response decision, when a withdrawal would remove the study's entire subject, when a verification step fails for reasons outside the study, or when anything requires a commit, push, deploy, credential or signature.

**Never:** commit, push, deploy, read `.env`, run an R2 sync, or write `approved`/`signoffs`/`editionSha256` for a study the owner has not signed. The orchestrator authors the text that will be signed, so it never reviews that text and never approves it.

**Definition of done for one study:** ledger re-measures byte-identically · frozen text at a new path with the legacy original untouched · registry `approved`/`published` with three distinct attestations on one ledger hash plus a matching `editionSha256` · unit, astro-check, build (with the new archive route rendering `data-edition-status="approved"` and three sign-off records), e2e, pytest, baseline, layout and hooks green · README, handoffs and the sign-off record updated.
