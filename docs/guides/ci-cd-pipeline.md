# CI/CD Pipeline Guide

**Last Updated**: 2026-11-23

## Overview

The repository currently uses two active GitHub Actions workflows:

| Workflow   | File                             | Purpose                                                          |
| ---------- | -------------------------------- | ---------------------------------------------------------------- |
| CI         | `.github/workflows/ci.yml`       | Python linting, type checking, tests, dependency audits, E2E     |
| Evidence   | `.github/workflows/evidence.yml` | Read-only evidence-producer drift checks (scheduled + on demand) |
| Deploy App | `.github/workflows/deploy.yml`   | Build and deploy the Astro app to GitHub Pages                   |

## CI Workflow

File: `.github/workflows/ci.yml`

The CI workflow runs these jobs:

1. `lint`
   - installs Python deps with `uv sync --dev`
   - runs the configured pre-commit checks
2. `typecheck`
   - runs the supported mypy target set for the core Python surface
3. `security`
   - runs `uv run pip-audit --skip-editable` in the CI-parity environment (the
     dev group), which answers "is the environment we run green?"
4. `audit-python`
   - audits **every** group and extra in `uv.lock`, not just the dev group
   - exports the frozen lock (`uv export --frozen --all-groups --all-extras`)
     and runs `pip-audit -r` against that export with `--no-deps --disable-pip`,
     so nothing is installed and nothing is re-resolved
   - fails on any advisory not listed in the reviewed exception register; see
     [Dependency audit gates](#dependency-audit-gates-rel-4)
5. `audit-frontend`
   - runs `bun audit --json` in `app/` after `bun install --frozen-lockfile`
   - same register, `app-bun` scope, same failure rule
6. `test`
   - creates a minimal `.env`
   - runs pytest with coverage
   - enforces the core coverage floor
   - validates active docs with `scripts/tools/validate_docs_layout.py`
7. `e2e`
   - installs app deps with Bun
   - builds the Astro app (`/` base, via `astro preview`)
   - runs Playwright against the preview server
   - the Pages-prefixed spec skips itself here, because this build does not
     use the `/egg-n-bacon-housing/` base path
8. `pages-e2e`
   - installs app deps with Bun 1.2.23 (`--frozen-lockfile`)
   - builds the real GitHub Pages artifact with `bun run build:pages`
     (`ASTRO_PAGES=true`)
   - asserts the regenerated `app/public/data/catalog.jsonl.gz` did not drift
     (`git diff --exit-code -- app/public/data/catalog.jsonl.gz`)
   - serves `dist/` under `/egg-n-bacon-housing/` with
     `node scripts/serve-pages-base.mjs` (port 4402, via `bun run serve:pages`)
   - runs `bunx playwright test tests/e2e/pages-base.spec.ts` with
     `PAGES_ORIGIN=http://127.0.0.1:4402` and
     `PAGES_BASE_PATH=/egg-n-bacon-housing`, so the suite runs instead of
     skipping

`pages-e2e` is the release gate for the Pages base path: it is the only job
that exercises the prefixed build, and the deploy workflow runs the same
suite before publishing.

### Dependency audit gates (REL-4)

Two jobs gate advisories that the CI-parity `security` job structurally cannot
see. Before them, the only Python audit ran inside the `--dev` environment and
`bun audit` never ran at all.

| Job              | Tool                  | Scope                                                        | Installs?                |
| ---------------- | --------------------- | ------------------------------------------------------------ | ------------------------ |
| `audit-python`   | `pip-audit -r` (JSON) | every group and extra in `uv.lock` (dev, research, tracking) | no                       |
| `audit-frontend` | `bun audit --json`    | `app/bun.lock`, runtime and build-time alike                 | yes, `--frozen-lockfile` |

Measured at the audit baseline (`master-audit-2026-11-23`):

- dev group only: 165 dependencies, **0** advisories (the `security` job)
- every group and extra: 303 dependencies, **238 raw advisory records across 23
  packages** (the `audit-python` job)
- `app/`: **110 raw advisory records across 24 names** (the `audit-frontend`
  job)

The raw records are **not** unique CVEs. Both tools emit duplicate and alias
representations of one advisory — a PYSEC id plus its GHSA alias, or one GHSA
listed once per affected major range — so the reviewed set is 166 Python
advisories and, at baseline, 108 frontend advisories. Neither audit establishes
reachability: they report that a vulnerable version is installed, nothing more.

**Current state (2026-11-24), after remediation.** The frontend scope was cut
from 110 raw records across 24 names to **28 records across 8 names**:

- `dompurify` 21 records → 0. The version bump alone did not do it — the
  deprecated `@types/dompurify` stub declared `dompurify: "*"` and pinned a frozen
  nested `dompurify@3.3.1`; removing the stub deleted that copy.
- `astro` 14, `devalue` 11, `vite` 9, `h3` 4, `js-yaml` 4, `svgo` 4, `sharp` 3,
  `smol-toml` 3, `lodash` 2, `@babel/core` 1, `defu` 1, `rollup` 1, `zod` 1 → 0,
  via the Astro 7 major upgrade below plus a semver-range `bun update`.
- Remaining: `fast-uri` 12, `picomatch` 4, `postcss` 4, `nanoid` 3,
  `postcss-selector-parser` 2, `katex` 1, `source-map-js` 1, `yaml` 1. All are
  build-time transitives; each keeps a reviewed, dated entry.

The Python scope is unchanged at 238 raw records across 23 packages, and the
register is now 31 entries (23 Python + 8 frontend). Entries whose advisory an
upgrade closed were deleted rather than left to rot.

#### The exception register

`.github/security-audit-exceptions.yml` is the reviewed list of what the
repository accepts living with. Both jobs fail unless **every** finding is
covered by a live entry, so no advisory can pass silently and no suppression is
implicit.

Each entry declares:

- `scope` — `python-all-groups` or `app-bun`; a job only honours its own scope
- `package` — the affected package
- `advisories` — the exact advisory ids accepted (GHSA where one exists)
- `owner_role` — the role accountable for the next review, not a person
- `expires` — an ISO date: a hard deadline, not a reminder
- `rationale` — why the advisory is not reachable here, or why the fix is
  deferred

The gate is deliberately **id-level, not package-level or severity-level**: a
new advisory on an already-listed package fails the build until somebody
assesses it. Three outcomes are possible:

1. A finding with no matching entry (same package **and** one of the listed ids)
   becomes `::error::UNREVIEWED advisory` and the job fails.
2. A finding matched only by an entry whose `expires` has passed becomes
   `::error::EXPIRED exception` and the job fails. An acceptance that nothing
   enforces is not an acceptance.
3. An entry that matches nothing in the current audit is reported as a stale
   `::notice::` exception. Not a failure: an upgrade that closes an advisory must
   not be blocked on somebody deleting the leftover entry first, but the log
   names it, so dead entries get cleaned up.

Schema mistakes fail too: a missing field, a non-ISO date or an unknown scope is
an error rather than a silently ignored entry.

#### Triage a new advisory

1. Read the failure. Each line names the package, the advisory id, and either the
   fix versions (`pip-audit`) or the affected range and severity (`bun audit`).
2. **Try to fix it first.** An exception is for an advisory that cannot be closed
   by a change this repository will make now, not for one nobody has looked at.
   Use the upgrade path below.
3. If it cannot be fixed yet, assess reachability against real usage — the call
   site, whether the vulnerable mode is enabled, whether the input is
   attacker-controlled, whether it ships to a browser or runs only at build time
   — and add an entry in the **same pull request** that trips the gate. Give it
   an expiry one quarter out and a rationale that states the assessment, not the
   severity.
4. At expiry the job fails again, which forces the review: either fix it, or
   re-assert it with a fresh assessment and a new date.

A rationale that says only "low severity" is not a rationale. The frontend
entries state build-time-versus-runtime surfaces; the Python entries state the
reverse dependency that actually pulls the package in.

#### Lockfile upgrade path

Never hand-edit `uv.lock` or `app/bun.lock`, and never relax `--frozen` or
`--frozen-lockfile` to make a build pass.

Python:

```bash
uv lock --upgrade-package <name>   # transitive pin, no manifest change
# or raise the constraint in pyproject.toml, then:
uv lock && uv sync --dev --locked
uv run pytest tests/ -q --no-cov
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pip-audit --skip-editable
```

App:

```bash
cd app
bun update <name>   # or bump the range in app/package.json
bun install --frozen-lockfile
bun run test:unit && bun run astro check
bun run build
```

…then the E2E suites: `bun run test:e2e`, and the Pages-prefixed `build:pages`
plus `tests/e2e/pages-base.spec.ts` run with `PAGES_ORIGIN` and
`PAGES_BASE_PATH` set. A dependency bump that changes rendering has to pass both
the prefixed and the unprefixed suite, not just the unit tests.

#### Known in-range fixes, deliberately not taken here

Recorded so the next dependency change starts from a plan instead of a re-audit:

- **`dompurify`** — declared `^3.3.1`, installed 3.3.1; 3.4.16 and later (through
  3.5.0) satisfy the existing range and close all 21 DOMPurify entries. There is
  exactly one first-party call site (`DOMPurify.sanitize` in
  the `MarkdownContent` component under `app/src/components/`), so the blast
  radius is one
  component. This is the cheapest advisory reduction available and should land
  first.
- **`vite` 6.4.1** — 6.4.2 to 6.4.4+ are inside the Astro 5 range and clear the
  dev-server advisories.
- **`sharp` 0.34.5** — 0.35.x clears the inherited libvips/libheif/librsvg CVEs;
  it is an optional Astro image dependency and this app decodes no images.
- **`katex` 0.16.28** — the fix (0.18.2) is outside `^0.16.28`; in practice the
  advisory needs an enabled `trust` surface, which this app does not enable.
- Python: `langchain` 0.3.30, `langchain-core` 0.3.8x and `marimo` 0.23.x are
  inside their declared ranges, and most transitive research pins (`aiohttp`,
  `cryptography`, `pillow`, `pyjwt`, `pyasn1`, the `h2`/`hpack` stack) have fixes
  outside the current resolution. All of them are research-group surface:
  upgrading them is a dependency decision for that group with its own review, not
  a lockfile refresh to be slipped into an unrelated change.
  `langchain-experimental` and the `langgraph` family are exact (`==`) pins and
  cannot move without changing the manifest.

#### Astro 5.16.16 to 7.4.13: completed 2026-11-24

14 of the frontend advisories, including the critical AVIF RCE
(GHSA-26w7-cxv4-gfx2), were fixed only in Astro 6.1.6+ or 7.x, so closing them
required a **major** upgrade. It has now been done, with the full gate, and the
advisory entries were deleted because the advisories no longer apply.

Four breaking changes had to be handled, all in build configuration rather than
application code:

1. **`@astrojs/tailwind` is gone** — its peer range stops at Astro 5. Tailwind v3
   is now wired the documented way, through `app/postcss.config.mjs`
   (`tailwindcss` + `autoprefixer`) with the integration removed from
   `astro.config.mjs`. The compiled CSS still carries preflight, `.sr-only` and
   the config-derived classes.
2. **`unified is not a function`** — Astro 7 needs `@astrojs/markdown-remark@^7`
   as an explicit dependency to supply the processor factory.
3. **`markdown.remarkPlugins`/`rehypePlugins` are deprecated top-level keys** —
   migrated to `markdown.processor: unified({ ... })`, preserving the GFM and
   SmartyPants defaults Astro was coercing into the pipeline.
4. **`astro preview` auto-backgrounds under agent detection**, so Playwright's
   `webServer` observed "exited early". The scripts set
   `ASTRO_PREVIEW_BACKGROUND=0` (and `ASTRO_DEV_BACKGROUND=0`) to keep the
   foreground semantics the E2E harness depends on. This one only reproduces in
   agent/CI-like environments, so it is worth remembering when preview dies for
   no visible reason.

The AVIF advisory was never claimed reachable here — there is no `astro:assets`,
`<Image>` or AVIF usage under `app/src`, and the config declares no adapter and
no `output: 'server'`. The upgrade closed it structurally regardless.

### Evidence Workflow

File: `.github/workflows/evidence.yml`

This gate lives in its own workflow, not in `ci.yml`, because of its inputs: the
producers re-measure from the gitignored `data/pipeline/**` layers, which a
fresh checkout does not have (0 tracked files; the R2 sync carries only
`data/manual/**`). Running it on every pull request would make CI red by
construction for an input-provisioning gap that is an owner decision — and a
permanently red gate gets ignored, which is worse than no gate at all.

It therefore runs weekly (`schedule`) and on demand (`workflow_dispatch`). When
it runs, it either re-measures every ledger or fails loudly with the missing
inputs named; there is never a silent skip. Once the pipeline layers are
provisioned for CI, add `push`/`pull_request` triggers to this file to gate
every change.

The job:

- restores what the R2 sync can (`data/manual/**`) and fails closed if the
  pipeline layers under `data/pipeline/**` are still absent, so a missing input
  can never be read as "no drift"
- runs every read-only evidence producer's `--check` (those with a compare mode;
  `rental_yield_evidence.py` only writes and is skipped by name), listing each
  producer explicitly rather than globbing `scripts/tools/*_evidence.py`, so a
  renamed producer cannot silently drop out of the gate
- fails on any drift at all: there is no allowlist
- is bounded at 20 minutes

### Generated catalog drift

`bun run build:pages` (like `bun run build`) regenerates
`app/public/data/catalog.jsonl.gz` from `data/`. Both `pages-e2e` and the
deploy build run `git diff --exit-code -- app/public/data/catalog.jsonl.gz`
immediately after the build. The rewrite is deterministic for an unchanged
source tree, so a non-empty diff means the committed asset is stale and the
run must fail rather than publish a drifting artifact. The workflow does not
restore the file first: a diff is a real signal, not something to paper over.

### Evidence producer drift (REL-3)

The `evidence` workflow runs each read-only producer's `--check`, which
re-derives the ledger from this checkout and compares it byte-for-byte against
the committed artifact. Before it existed the checks were never automated, so a
ledger could drift silently.

**The drift debt is closed.** Nine producers failed their `--check` when the gate
was first wired (five drifted at the `449b921` audit baseline, four more because
concurrent work orders changed files their bounded scans read). They were held
in `ALLOWED_DRIFT` and `DISCOVERED_DRIFT` maps so the job failed on any _new_
drift. Both maps are now gone: every producer with a compare mode re-measures
byte-identically, and one drifting key fails the job.

The drift was classified before anything was regenerated, and the two classes
were fixed differently:

- **Prose-caused drift (the scan was wrong).** A producer that hash-pins prose
  drifts whenever that prose is edited for reasons unrelated to the evidence
  claim. `lease_decay`'s filename scan read two release-named planning
  documents as lease-named matches (`release` contains `lease`) and its token
  scan counted the drift notes that merely spell the method's name, so the act
  of recording a re-pin re-drifted the ledger. Re-pinning it would have been
  futile. Every producer that already excluded the D12 decision register by
  path now excludes the whole planning/spec surface `docs/plans/**`, and each
  ledger discloses that exclusion in its own scan metadata (its
  `excludedPrefixes` list, plus the reason in the adjacent `meaning`). Study
  prose under `docs/analytics/**` and the frozen legacy corpus are still
  scanned: those hold the method's own words, and excluding them would weaken
  the claims rather than the boundary.
- **Code-caused drift (the pin was right).** Where a producer pins source code
  that remediation genuinely changed, the pin is supposed to move. Those nine
  artifacts were regenerated and each diff was reviewed key by key: re-hashed
  source files, a quoted line that moved by one when `numpy.typing` was added,
  the evidence producer's `pyproject.toml` pin, and token hits in code that a
  work order actually edited. Every changed number is attributable to a
  reviewed source change or to the narrowing above.

A ledger re-pin is not a one-file change. `findings` (RS15) refuses to build when
any cited ledger no longer hashes to the `artifactSha256` its edition's sign-offs
pin in `app/src/components/studies/lib/edition-registry.ts`, and the archive
route fails closed the same way, so a regenerated artifact and its three
registry pins move together in one change. Reviewing the artifact diff is what
makes that re-pin legitimate; the pins are the mechanism, not a formality.

One defect surfaced while classifying: `price_forecasts`' filename scan claimed
to be independent of local test and build runs, but it counted `htmlcov/`
(written by pytest's own `--cov-report=html`), `.hypothesis/`, `coverage.xml`
and the Astro build cache, so `filesScanned` moved whenever anyone ran the
suite. Those tooling outputs are now excluded, exactly as the ledger always
said they were.

**Editing this guide can re-pin a ledger.** `docs/guides/**` is inside the
scanned surface. If a change here mentions a scanned method token, re-run the
affected producer, review the diff and commit the regenerated artifact with it.
Do not widen the exclusions to hide a match an absence claim rests on, and do
not allowlist drift: the gate fails on it, by design.

**Input prerequisite.** Every producer re-measures from the pipeline outputs
under `data/pipeline/**` and the derived tables under `data/analysis/**`, which
`.gitignore` excludes. A fresh checkout has none, and `scripts/00_sync_data.py`
syncs only `data/manual/**` and the geocode cache. The job restores what R2 can
and then **fails closed** with an actionable error if the pipeline layers are
still missing, so "no drift reported" can never mean "no inputs to measure".
Running the producers in CI therefore needs a data-restore step (run the
pipeline, or publish the layers to R2 and extend the sync) — this is separate
from, and older than, the drift work above.

## Deploy Workflow

File: `.github/workflows/deploy.yml`

The deploy workflow:

1. checks out the repo
2. installs Bun and Python
3. installs app dependencies with `bun install --frozen-lockfile`
4. verifies the required dashboard data files under `app/public/data/`
5. builds the Astro app with `bun run build` and `ASTRO_PAGES=true` (the Pages build)
6. asserts the regenerated `app/public/data/catalog.jsonl.gz` did not drift
7. installs the Playwright Chromium browser
8. runs the Pages-prefixed Playwright suite against the built `dist/` (port 4402)
9. verifies `dist/index.html` exists and greps the expected route headings
10. uploads `app/dist/`
11. deploys to GitHub Pages (the `deploy` job `needs: build`)
12. runs a lightweight smoke check against the deployed pages, including the
    base-prefixed hashed CSS asset

Because the `deploy` job depends on `build`, a failure in the prefixed suite
or the drift assertion stops publication; the deploy smoke checks remain in
place and are unchanged.

## Local Mirrors of CI

Python checks:

```bash
uv sync --dev
uv run ruff check .
uv run mypy
uv run pytest
uv run python scripts/tools/validate_docs_layout.py
```

Dependency audits (the `security`, `audit-python` and `audit-frontend` jobs):

```bash
# CI-parity environment only, as the `security` job runs it
uv run pip-audit --skip-editable

# every group and extra, from a frozen export, without installing anything
uv export --frozen --all-groups --all-extras --no-emit-project \
  --format requirements-txt > /tmp/all-groups.txt
uv run pip-audit -r /tmp/all-groups.txt --no-deps --disable-pip
```

Both audits exit `1` when they find something, so a local run trips `set -e`;
compare what it printed against `.github/security-audit-exceptions.yml` before
treating that exit code as a failure. The register gate itself is the last step
of `audit-python` and `audit-frontend` in the workflow (inline there, so it
cannot drift from the jobs it guards); its `UNREVIEWED` and `EXPIRED` lines are
the failures to act on.

App checks:

```bash
cd app
bun install --frozen-lockfile
bun run build
bun run test:e2e
bun audit   # --json for the machine-readable shape the gate reads
```

Pages-prefixed checks (the `pages-e2e` job and the deploy gate):

```bash
cd app
bun run build:pages
git -C .. diff --exit-code -- app/public/data/catalog.jsonl.gz
PLAYWRIGHT_HTML_OPEN=never \
  PLAYWRIGHT_SERVER_COMMAND='bun run serve:pages' \
  PLAYWRIGHT_BASE_URL='http://127.0.0.1:4402/egg-n-bacon-housing/' \
  PAGES_ORIGIN='http://127.0.0.1:4402' \
  PAGES_BASE_PATH='/egg-n-bacon-housing' \
  bunx playwright test tests/e2e/pages-base.spec.ts --workers=2
```

Expect `9 passed` and no skipped tests. If the run reports skipped tests,
`PAGES_ORIGIN` was not set and the base path was not actually covered.

## Notes

- Every accepted dependency advisory is named, owned and dated in
  `.github/security-audit-exceptions.yml`; adding one is a reviewed change, not
  a config tweak. The two audit jobs enforce the expiry dates, so an acceptance
  cannot outlive its review.
- The app no longer relies on the older content-sync shell step.
- The app loads analytics markdown directly from `docs/analytics/` via Astro content collections.
- If deployment fails on missing app data files, regenerate or restore the expected contents of `app/public/data/` before re-running the workflow.
