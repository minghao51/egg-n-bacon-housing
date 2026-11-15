# RF08 continuation brief — the 13 studies that are still `historical`

- **Written:** 2026-11-14
- **For:** the next agent (or the next session) picking up RF08 where RS01/RS02 left off
- **Status of the programme:** 2 of 15 studies have a signed, approved edition (`data-sources`, `rental-yields`). **13 do not.** Nothing is deployed.
- **Read first:** [`prompts/handoffs.md`](../../prompts/handoffs.md) §0 and §4a · [RF08 sign-off record](2026-11-14-rf08-editions-signoff.md) · [RF08 readiness](2026-11-13-rf08-readiness.md) · [research register](../plans/2026-11-12-reporting-refresh-research-register.md) · [decision ledger](../plans/2026-11-12-reporting-refresh-decisions.md) (D12)
- **Paste-ready dispatch prompt:** [`prompts/rf08-study-worker-prompt.md`](../../prompts/rf08-study-worker-prompt.md) — one study per worker, waves, the reviewer prompt and the owner's gate
- **Reference pair to copy:** [RS01](2026-11-14-rs01-source-inventory.md) + [`data-sources` edition](../../docs/analytics/editions/data-sources/2026-11-14/data-sources.md) and [RS02](2026-11-14-rs02-rental-yield-evidence.md) + [`rental-yields` edition](../../docs/analytics/editions/rental-yields/2026-11-14/rental-yields.md)

## 1. The studies that remain

| Series                      | Register row | Extra gate beyond D12                                                                                      |
| --------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------- |
| `temporal-evolution`        | RS03         | Comparable periods and period-correct feature vintages                                                     |
| `amenity-impact`            | RS04         | Refit with units and controls; no causal premium                                                           |
| `facility-premiums`         | RS05         | Matched facilities; publish uncertainty                                                                    |
| `lease-decay`               | RS06         | **Model/unit approval** — per-square-metre vs per-square-foot must be resolved first; charts stay withheld |
| `mrt-impact`                | RS07         | **Model approval** — confirm metres/km and the response variable; no "15×" marketing                       |
| `school-quality`            | RS08         | **Causal/RDD review** — tiers, bandwidth, assignment, multiple testing                                     |
| `macro-sensitivity`         | RS09         | Real release vintages; fallback series excluded from claims                                                |
| `market-segments`           | RS10         | **Segment/scoring owner approval** — recover scaling and cohort counts                                     |
| `spatial-autocorrelation`   | RS11         | **Spatial method review** — weights, disconnected areas, permutations                                      |
| `spatial-hotspots`          | RS12         | **Spatial method review** — keep Jan 2024–Jan 2025 as its own historical window                            |
| `causal-inference-overview` | RS13         | **Causal identification approval** — estimand, pretrends, placebos                                         |
| `price-forecasts`           | RS14         | **Forecast/model approval** — rolling-origin validation, leakage checks, score expired 2025 forecasts      |
| `findings`                  | RS15         | **Last** — every quantitative sentence must link to a reviewed edition                                     |

`amenity-impact`…`findings` are the 13. RS15 must not start until its dependencies exist.

## 2. The gate sequence that is now proven (do not improvise a different one)

For each study, in this order, stopping at each gate:

1. **Evidence pack** — a measured, reproducible ledger plus a prose pack, written under
   `docs/implementation/`, produced by a `scripts/tools/*.py` measurement tool with a
   `--check` mode that re-hashes the checkout. Copy the RS01/RS02 shape: what was measured
   and how, the measured tables, what the pack does **not** establish, and a sign-off
   section. The ledger is canonical JSON (sorted keys, no timestamps) so re-running it
   reproduces a byte-identical file.
2. **Owner source/cutoff signature** on the ledger sha256 — ask for it, record it in the
   decision ledger under D12, and never record a signature the owner did not give. The
   preparer label is `repo-agent/session-<date>`; the registry rejects any sign-off that
   equals it.
3. **Author the refreshed text** as a **new** frozen source at
   `docs/analytics/editions/<series>/<edition-date>/<series>.md`. Never edit the RF00
   originals under `editions/legacy/2026-11-12/` — `verify_reporting_baseline.py --assets`
   is what proves you did not. Withdraw unsupported claims explicitly in a
   "Superseded figures" table instead of quietly deleting them.
4. **Scientific re-review of the text** (the pack review does not cover article sentences).
   Use an independent reviewer (`codex-luna-reviewer` on `openai-codex/gpt-6-luna`,
   `xhigh` worked); expect a first pass with real defects and fix them; store the verbatim
   attestation in the sign-off record.
5. **Owner publication signature** on the frozen text hashes, then one atomic registry edit
   per edition: `evidenceStatus: "approved"`, `editorialStatus: "published"`, the three
   `signoffs[]` (all pinning the **evidence ledger** hash) and `editionSha256` (the text
   hash). `validateEditionRegistry()` refuses anything less.

## 3. Mechanics you will need

| Thing                                    | Where                                                                                                                                                   |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Edition registry + validation + text pin | `app/src/components/studies/lib/edition-registry.ts` (`REFRESHED_EDITIONS`, `editionSha256`, `verifyEditionArtifacts`)                                  |
| Build-time enforcement                   | `app/src/pages/analytics/archive/[year]/[edition]/[slug].astro` — `getStaticPaths` throws on an invalid registry **or** a drifted frozen text           |
| Series page                              | `app/src/pages/analytics/[slug].astro` — the approved branch names and links the approved edition and says the narrative below may predate it           |
| Everything is unregistered ⇒ build fails | A new file under `editions/*/*/*.md` **must** get a registry entry in the same change, or `getStaticPaths` throws "no identity in the edition registry" |
| Signed hashes currently pinned           | `data-sources` text `bde11c61…`, RS01 ledger `65ce7a10…`; `rental-yields` text `f6b0bd9d…`, RS02 ledger `db134525…`                                     |

## 4. Traps that cost time the first two times

1. **Astro extracts `getStaticPaths`** into its own module: frontmatter helpers are out of scope (`X is not defined` at build).
2. **One artifact hash per edition.** All three sign-offs must pin the same `artifactSha256`; the text is pinned separately by `editionSha256`. Do not "fix" a mismatch by loosening the validator.
3. **No sign-off on a non-approved edition** — a partial approval record is rejected by design. If the owner signs early, record it in the decision ledger and materialise it in the same edit that flips the status.
4. **Regenerating a ledger invalidates a signature.** Re-run the producer and diff before citing numbers; a signature pins a hash, not a document.
5. **Missing ≠ zero, and absence ≠ missing asset.** State which one you measured. Both RS01 and RS02 lost a review pass to that distinction.
6. **Do not quote an old article's summary figures loosely** — quote its actual phrases or paraphrase without quotation marks.
7. **`bun run build` rewrites `app/public/data/catalog.jsonl.gz`**; keep the change (RF11 authorised output) and pin the **post-build** bytes.
8. **Never report a command you did not run**, and do not let a PASS verdict on the pack stand in for a review of the article.

## 5. Definition of done for one study

- The ledger re-measures byte-identically (`--check`-style tool) and its sha256 is in the pack.
- A frozen edition exists at a new path; the legacy original is byte-identical.
- The registry entry is `approved`/`published` with three distinct attestations, none of them the preparer, all on one evidence hash, plus a matching `editionSha256`.
- `cd app && bun run test:unit` and `bun run astro check` are green (0 errors / 0 warnings / 22 hints), `bun run build` emits the new archive route, and the archive E2E suite passes.
- `docs/implementation/README.md`, `prompts/handoffs.md` and the study's own record say what shipped and what was withdrawn.
- Nothing committed, nothing deployed, `.env` never opened.

## 6. Suggested order

`findings` is last and gates on everything. Among the rest, start with the ones whose inputs
are already measured and whose extra gate is smallest — `temporal-evolution` (RS03) and
`amenity-impact` (RS04) — and leave the ones that need a **model or causal approval**
(`lease-decay`, `mrt-impact`, `school-quality`, `causal-inference-overview`,
`price-forecasts`, `market-segments`, `spatial-*`) until that reviewer is named, because a
refreshed edition without its model approval is exactly what D12 exists to prevent.
