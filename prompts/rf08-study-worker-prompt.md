# RF08 study worker — dispatch prompt (glm-5.3-flash)

- **Written:** 2026-11-14
- **Purpose:** the exact prompt to hand one `glm-flash-worker` subagent so it can take **one** of the 13
  remaining `historical` studies from "no evidence" to "ready for the owner's signature".
- **Companion:** [RF08 continuation brief](../docs/implementation/2026-11-14-rf08-continuation-brief.md)
  (gate sequence, mechanics, traps). This file is the paste-ready form of it.
- **Not in this prompt:** the owner's signatures. A worker cannot give one, and a worker that writes
  `evidenceStatus: "approved"` has produced a forged approval.

## 0. How to dispatch

One study per worker. Sequential in the shared checkout, because every study edits the same four
files (`app/src/components/studies/lib/edition-registry.ts`, `docs/implementation/README.md`,
`prompts/handoffs.md`, `docs/plans/2026-11-12-reporting-refresh-decisions.md`). Only use
`isolation: "worktree"` if you intend to run several **in parallel** and merge each study's branch
yourself.

```
Agent
  subagent_type: "glm-flash-worker"        # implementation worker on zai/glm-5.3-flash
  model:         "zai/glm-5.3-flash"
  description:   "RF08 <series> evidence + edition"
  prompt:        <the filled template from §2>
```

Then, before the owner signs, dispatch the **independent reviewer** (§3) on a _different_ model.
A worker must never review its own text: the D12 scientific signatory has to be a separate record.

## 1. Dispatch order

| Wave | Studies                                                                                                                                                         | Why now                                                              |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 1    | `temporal-evolution` (RS03), `amenity-impact` (RS04)                                                                                                            | inputs already measured, smallest extra gate, proves the loop        |
| 2    | `facility-premiums` (RS05), `macro-sensitivity` (RS09)                                                                                                          | matched facilities / real vintages, no model approval needed         |
| —    | `lease-decay`, `mrt-impact`, `market-segments`, `price-forecasts`, `school-quality`, `spatial-autocorrelation`, `spatial-hotspots`, `causal-inference-overview` | **hold** until a named model/causal/spatial/forecast reviewer exists |
| last | `findings` (RS15)                                                                                                                                               | every quantitative sentence must link to a reviewed edition          |

Do not dispatch a held study "to make progress": an edition refreshed without its model approval is
exactly the artefact D12 exists to prevent.

## 2. Worker prompt template

Fill `{{SERIES}}`, `{{REGISTER_ROW}}`, `{{EDITION_DATE}}` (today's ISO date) and `{{EXTRA_GATE}}`
(see the table in the continuation brief §1), then send it verbatim. Everything else is fixed.

---

You are taking **one** study of the egg-n-bacon-housing reporting refresh from `historical` to
"ready for signature". Repository: `/home/howt/work/egg-n-bacon-housing`. Study: **`{{SERIES}}`**
(register row `{{REGISTER_ROW}}`), new edition date `{{EDITION_DATE}}`.

### Why this task exists

Fifteen analytics series were published years ago and were re-frozen as immutable sources under
`docs/analytics/editions/legacy/2026-11-12/`. They are marked `historical` because the paper's
numbers were never re-measured. Two series have since been re-measured, re-reviewed and signed
(`data-sources`, `rental-yields`). You are doing that job for `{{SERIES}}`, **except the
signatures**: you produce the evidence pack and the refreshed text, and you stop.

### Read these first (do not skip)

1. `docs/implementation/2026-11-14-rf08-continuation-brief.md` — the gate sequence, mechanics, traps.
2. The reference pair, which is the shape to copy:
   - `docs/implementation/2026-11-14-rs01-source-inventory.md` + `scripts/tools/source_inventory.py`
     - `docs/implementation/artifacts/rs01-source-inventory.json`
   - `docs/implementation/2026-11-14-rs02-rental-yield-evidence.md` + `scripts/tools/rental_yield_evidence.py`
     - `docs/implementation/artifacts/rs02-rental-yield-evidence.json`
   - `docs/analytics/editions/data-sources/2026-11-14/data-sources.md`
     (sha256 `bde11c61b720c2504cdf78bde9238c5e57925e319457d52356cde0bcdeeafb81`)
3. `docs/analytics/editions/legacy/2026-11-12/{{SERIES}}.md` — the old text you are superseding.
   **Never edit it.**
4. `docs/analytics/{{SERIES}}.md` — the live series text the app renders today.
5. `app/src/components/studies/lib/edition-registry.ts` — `REFRESHED_EDITIONS`, `AnalyticsEdition`,
   `validateEditionRegistry`, `verifyEditionArtifacts`.
6. `app/src/pages/analytics/archive/[year]/[edition]/[slug].astro` — the build-time gate.
7. `docs/plans/2026-11-12-reporting-refresh-research-register.md` (row `{{REGISTER_ROW}}`) and
   `docs/plans/2026-11-12-reporting-refresh-decisions.md` (D12).

### Extra gate for this study

{{EXTRA_GATE}}

If that gate requires an approval you do not have, **stop before writing the edition** and report
which approval is missing. Do not paper over it with hedging language.

### What to produce

**Gate 1 — evidence pack (measured, reproducible).**

- A tool at `scripts/tools/{{SERIES_SNAKE}}_evidence.py` with `--output` (default
  `docs/implementation/artifacts/rs{{RS_NN}}-{{SERIES}}-evidence.json`) and `--check`, following
  `rental_yield_evidence.py`: it measures from the checkout, writes canonical JSON (sorted keys, no
  timestamps, no absolute paths), and `--check` re-measures and fails on drift.
- A prose pack `docs/implementation/{{EDITION_DATE}}-rs{{RS_NN}}-{{SERIES}}-evidence.md` with: what was
  measured and how; the measured tables; what the pack does **not** establish; and a sign-off section
  with `sha256sum` of the ledger.
- Reproducibility is a requirement, not a nicety: run the tool twice and confirm the bytes and hash
  are identical. Re-running must not change a hash that was already quoted.

**Gate 2 — stop.** Report the ledger path and its sha256. The owner gives the source/cutoff
signature; you do not.

**Gate 3 — refreshed text as a new frozen source.**

- Author `docs/analytics/editions/{{SERIES}}/{{EDITION_DATE}}/{{SERIES}}.md`, frontmatter copied in
  shape from the `data-sources` edition (`title`, `category`, `description`, `status: draft`,
  `date`, `personas`, `readingTime`, `technicalLevel`), body rewritten so that:

  - every quantitative sentence is either re-measured from your ledger or removed;
  - withdrawn claims go in a **"Superseded figures"** table naming the old figure, the new measured
    value (or `not measured`), and why — never quietly deleted;
  - `no-sales` is not written as `0`, and `missing-source` is not written as `no-sales`;
  - no directional market vocabulary (hot, cold, booming, demand surge) and no claim your ledger
    does not support;
  - uncertainty is stated where the measurement is thin (`n = …`, thin-sample floor).

- Register the new file **in the same change** or the build fails with "no identity in the edition
  registry": add one `REFRESHED_EDITIONS` entry with
  `evidenceStatus: "historical"`, `editorialStatus: "draft"`, `preparedBy:
"repo-agent/session-{{EDITION_DATE}}"`, `assetsPinned: 0`, and **no `signoffs`, no
  `editionSha256`** (both are forbidden on a non-approved edition, and a sign-off on a non-approved
  edition is rejected by design).

**Gate 4 — hand it to an independent reviewer.** Report the text sha256
(`sha256sum docs/analytics/editions/{{SERIES}}/{{EDITION_DATE}}/{{SERIES}}.md`) and stop. Do not
ask another instance of yourself to bless it.

### Hard rules

- **Do not** commit, push, deploy, or run `gh`. Nothing in this task is published.
- **Do not** open, print or create `.env`; never read credentials.
- **Do not** set `evidenceStatus: "approved"`, fill `signoffs`, or set `editionSha256`. Those three
  are the owner's signature and the reviewer's attestation — a worker writing them is forging an
  approval.
- **Do not** edit `docs/analytics/editions/legacy/**` or `docs/analytics/editions/*/2026-11-14/**`
  belonging to other series.
- **Do not** loosen a validator, a hash check or a test to make something pass. If a check
  disagrees with you, the check is the specification.
- **Never report a command you did not run**, and never quote a number you did not measure. Write
  `not measured` instead.
- Prefer "I measured X, which does not establish Y" over an unsupported sentence.

### Environment

- `uv run <cmd>` for Python (never bare `python`); `~/.bun/bin` on `PATH` for the frontend.
- Non-interactive shells do not read rc files: prefix `PATH="$HOME/.bun/bin:$PATH"`.

### Verification to run before you report

```
uv run python scripts/tools/{{SERIES_SNAKE}}_evidence.py --check
uv run python scripts/tools/verify_reporting_baseline.py --assets     # must still be 15 sources / 72 assets
uv run python scripts/tools/validate_docs_layout.py
uv run ruff check && uv run ruff format --check
uv run pytest tests/ -q --no-cov
cd app && PATH="$HOME/.bun/bin:$PATH" bun run test:unit
cd app && PATH="$HOME/.bun/bin:$PATH" bun run astro check              # 0 errors / 0 warnings / 22 hints
cd app && PATH="$HOME/.bun/bin:$PATH" bun run build                    # new archive route must appear
cd app && PATH="$HOME/.bun/bin:$PATH" bunx playwright test tests/e2e/analytics --workers=2
```

`bun run build` rewrites `app/public/data/catalog.jsonl.gz`: keep the change and note its new size
and hash. If `cd app && bun run build` fails with the registry error, you forgot the registry entry.

### Return exactly this

```
STUDY: {{SERIES}} ({{REGISTER_ROW}})
REACHED GATE: 1 | 3 | 4   (and why you stopped)
LEDGER: <path> sha256=<64 hex>
TEXT:   <path> sha256=<64 hex>
REGISTRY: <evidenceStatus>/<editorialStatus> entry added (no signoffs, no editionSha256)
MEASURED: <3-6bullet summary of what the ledger establishes, with n=>
NOT ESTABLISHED: <what the pack explicitly refuses to claim>
WITHDRAWN: <old figure -> new value or "not measured">
EXTRA GATE: <satisfied | missing: what approval is needed>
VERIFICATION: <each command above with pass/fail>
PROBLEMS: <anything a reviewer must know, or "none">
```

Do not summarise this as success if any verification step failed: say which one and leave the study
in progress.

---

## 3. Independent reviewer prompt (gate 4, different model)

Dispatch after the worker returns, on `codex-luna-reviewer` (`openai-codex/gpt-6-luna`, `xhigh`).
Short form:

> Review only the edition text at `docs/analytics/editions/{{SERIES}}/{{EDITION_DATE}}/{{SERIES}}.md`
> against the evidence ledger `docs/implementation/artifacts/rs{{RS_NN}}-{{SERIES}}-evidence.json`
> (sha256 `<ledger hash>`) and the pack `docs/implementation/{{EDITION_DATE}}-rs{{RS_NN}}-{{SERIES}}-evidence.md`.
> Check: every quantitative sentence is either backed by that ledger or marked withdrawn; the
> "Superseded figures" table matches the legacy text's **actual phrases**; `no-sales`/`missing-source`
> are not conflated with `0`; nothing directional or causal is asserted beyond the measurement;
> thin samples are labelled. Attempt to **refute** each numeric claim. Report defects as a list with
> the sentence quoted; end with `PASS` or `FAIL` and a one-line attestation that names the ledger
> hash and the text hash. Do not edit any file.

Store the verdict verbatim in the sign-off record; a first-pass `FAIL` is normal (RS02's first pass
had three hard defects).

## 4. Owner's gate (do this yourself, never delegate)

1. Read the pack and the reviewer verdict; approve the **source/cutoff** on the ledger hash.
2. Approve the **publication** on the text hash.
3. Only then edit the registry: `evidenceStatus: "approved"`, `editorialStatus: "published"`, the
   three `signoffs[]` (all pinning the **ledger** hash, none named
   `repo-agent/session-…`), plus `editionSha256` = the text hash. Record both decisions under D12 in
   `docs/plans/2026-11-12-reporting-refresh-decisions.md` in the same working session.

`validateEditionRegistry()` refuses anything less; `getStaticPaths` re-hashes the text at build time,
so a later edit to a signed edition fails the build rather than shipping silently.
