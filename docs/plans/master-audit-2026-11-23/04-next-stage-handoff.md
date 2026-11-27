# Next stage — handoff after the 2026-11-23 audit remediation

- **Written:** 2026-11-27
- **Landed as:** PR [#4](https://github.com/minghao51/egg-n-bacon-housing/pull/4), merge commit `830c418`, 12 commits, 10/10 CI checks green, 131 files (+45.8k/−3.4k)
- **Audit of record:** [the pack](./README.md) — [discovery](01-discovery.md), [findings](02-findings.md), [remediation spec](03-remediation-spec.md) (§7.1 records the owner decisions taken)
- **Ledger review record:** [2026-11-24 ledger re-pin review](../../implementation/2026-11-24-ledger-repin-review.md)
- **Programme ledger:** [implementation README](../../implementation/README.md) — status-claim rule applies: every status statement cites a file or a test

## 0. Resume here

All 18 audit findings are closed and verified. Nothing in this document is a
half-finished change: the tree on `main` is green and deployable.

**In priority order:**

1. **Evidence gate CI provisioning** (§2.1) — the one piece deliberately left
   undone because it is a provisioning change, not a flag. Blocks nothing else.
2. **First authorised data refresh** (§2.2) — the three HIGH defects existed to
   gate this. It is now safe, and it is the only way to prove the fixes on real
   ingestion end to end.
3. **Post-merge deploy verification** (§2.3) — merge is not deploy; confirm the
   Pages site.
4. The rest (§2.4–§2.8) is hygiene and two decisions.

## 1. What is done, and what "done" was measured by

| Finding                                  | Severity  | Where it lives now                                                                                           |
| ---------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------ |
| CORE-1 warm-cache geocode contract       | HIGH 16   | `utils/geocoding.py` — one `_row_from_result` conversion for cold and warm; `_empty_row` fabricates nothing  |
| CORE-2 pagination completeness           | HIGH 12   | `adapters/datagovsg.py` — envelope validation at any offset, terminal reconciliation vs advertised `total`   |
| CORE-3/4 R2 sync integrity + containment | HIGH 16+8 | `scripts/00_sync_data.py` — one containment resolver, exact-size filter, `--verify-content`, recorded sha256 |
| CORE-5 failed refresh became no-op       | MED 9     | `scripts/40_refresh_rolling.py` — rerun decided from selected work, not deletions                            |
| CORE-6 pacing burst                      | MED 8     | `utils/geocoding.py::_RateLimiter.wait` — slot reservation                                                   |
| UI-1 verified bytes                      | MED 9     | `utils/release-manifest.ts` + `hooks/useGzipJson.ts` — rendered payloads are the hashed buffers              |
| UI-2 map accessibility                   | MED 9     | `dashboard/PriceMap.tsx` — labelled area select, `aria-pressed`, `dt`/`dd` inspector, escaped tooltips       |
| UI-3 handoff dropped scope               | MED 9     | `dashboard/map/lib/handoff.ts` — one serializer over the explorer's own vocabulary                           |
| UI-4 financing boundaries                | MED 6     | `tools/lib/tool-amortization.ts` — cash purchase, `expm1`/`log1p`, fail-closed                               |
| REL-1 Pages gate                         | MED 6     | `.github/workflows/ci.yml` `pages-e2e`; `deploy.yml` runs the same suite                                     |
| REL-2 evidence artifact integrity        | MED 6     | `studies/lib/edition-registry.ts` + archive route — build-time verification of the cited ledger              |
| REL-3 producer checks in CI              | MED 9     | `.github/workflows/evidence.yml`                                                                             |
| REL-4 advisory gates                     | MED 9     | `audit-python` / `audit-frontend` jobs + `.github/security-audit-exceptions.yml`                             |
| ARCH-1 type scope                        | MED 6     | `pyproject.toml` 11→25 entries (46 files); `tests/test_type_scope.py` guard                                  |
| ARCH-2 duplicate layer resolver          | MED 6     | `config.resolve_layer_paths` authoritative; `layer_writer` re-exports                                        |
| DOC-1 ledger drift                       | LOW 4     | `docs/implementation/README.md` reconciled                                                                   |
| DEP-1 unreferenced deps                  | LOW 3     | `rapidfuzz`, `pytest-mock`, `pytest-asyncio` removed                                                         |
| B3 dependencies                          | —         | DOMPurify 3.5.0, Astro 7.4.13                                                                                |

**Verified at merge:**

| Gate               | Result                                                              |
| ------------------ | ------------------------------------------------------------------- |
| Python             | 1,204 passed, 54 skipped (baseline 1,136)                           |
| Frontend unit      | 575 passed (baseline 534)                                           |
| Root E2E           | 241 passed / 9 skipped (baseline 237/9)                             |
| Pages-prefixed E2E | 9 passed / 0 skipped — now runs in CI and before deploy             |
| `astro check`      | 0 errors / 0 warnings / 21 hints (baseline 22)                      |
| `mypy`             | clean on 46 files (was 29)                                          |
| Evidence producers | 13/13 `--check` pass, twice consecutively, **no allowlist**         |
| Audit scopes       | python-all-groups 238 findings / 23 entries; app-bun 28 / 8 entries |
| Live suites        | 36 passed, 18 skipped against real providers (opt-in, `EGG_LIVE=1`) |

**The single most important live result**, because it de-risks the HIGH fix
everyone would otherwise discover in production: **all 18 ingested resources
advertise exactly the rows their `next` chain yields** — `hdb_rental`
215,469/215,469 across 22 pages, `hdb_resale` 245,441/245,441 across 25. CORE-2's
hard fail is therefore safe on today's data. Re-run it before relying on that
claim for a new source:
`EGG_LIVE=1 EGG_LIVE_DEEP=1 uv run pytest tests/test_live_datagovsg.py -m live -s -k deep`
(~6 min; it paces and honours `Retry-After`).

## 2. Open work

### 2.1 Evidence gate in CI — the one scoped piece left

The gate works, is wired, and runs weekly + on demand. **It does not run on pull
requests**, and that was a reversal after trying it.

**Why the trigger was reverted.** With `pull_request` enabled, the job failed
from a clean checkout asking for six inputs the seven-artifact scope does not
carry:

```
data/pipeline/01_bronze/external/HawkerCentresGEOJSON.parquet
data/pipeline/01_bronze/bronze_manifest.json
data/analysis/lease_decay/lease_decay_analysis.csv
data/analysis/feature_importance/model_comparison.csv
data/forecasts/hdb_price_forecasts.csv
app/dist/data/analysis/causal_did_analysis.png   <- a BUILD OUTPUT
```

The last line is decisive: a producer reads a _shipped asset_ out of `app/dist`,
so a faithful CI run needs the app **built** as well as data provisioned.

**To close it:**

1. Enumerate, per producer, every path it opens (grep the producer for
   `read_parquet|read_csv|open(|Path(`), and derive the minimal provable set.
2. Extend `EVIDENCE_FILES` in `scripts/00_sync_data.py` — or add a second scope —
   to cover `01_bronze/external/**`, `bronze_manifest.json`, `data/analysis/**`
   and `data/forecasts/**`. Reuse `_resolve_local_target` and the sha256
   machinery; do **not** add a parallel code path.
3. Add a build step to `.github/workflows/evidence.yml`, or change the producer
   that reads `app/dist` to read the committed source instead — prefer the
   latter, since a build output is a poor evidence input.
4. Re-enable `pull_request:` and delete the "NOT on pull requests" rationale
   block. The fork guard is already in place and commented for that moment.
5. **Acceptance:** the job passes from a clean checkout on a PR, and the first
   deliberate drift still fails it.

**Watch the cost model:** every producer is a census over files. Anything
untracked — generated output, prose, formatter output — cannot be in a hash CI
must reproduce. That single rule caused four separate re-pins in one branch;
see §4.

### 2.2 First authorised data refresh

The audit's gate was "do not refresh until CORE-1/2/3 are fixed". They are.

```bash
uv run python scripts/40_refresh_rolling.py --stale-only --run   # retries a failed fetch by design
uv run python main.py --stage all                                 # supported entrypoint
uv run python scripts/tools/validate_docs_layout.py
uv run python scripts/99_cleanup.py                               # cache stats + clear
```

Then, in order: regenerate the catalog (`scripts/generate_catalog.py`), check
plausibility and coverage warnings, re-run the 13 evidence producers (expect
drift — a refresh moves data-derived numbers), and **review each ledger diff
before re-pinning**. A refresh is exactly where CORE-5's retry and CORE-2's
reconciliation earn their keep: watch for `IncompleteDatasetFetchError` and treat
it as a real finding, not an obstacle.

**Acceptance:** pipeline completes, catalog regenerates cleanly,
`check_catalog.py` passes, every producer drift is explained by the new data, and
the site builds with all editions still verifying.

### 2.3 Post-merge deploy verification

CI re-runs on `main` and `deploy.yml` fires on merge — but nothing has been
probed on the live host for this change set. Confirm:

1. `deploy.yml` run for `830c418` succeeded.
2. The Pages site serves `/egg-n-bacon-housing/` with no same-origin 404s.
3. `/explore` still verifies its pack (the UI-1 change is the largest frontend
   change here — a failure would show as an empty table with an unverified
   notice rather than wrong numbers).
4. `/research/map`: keyboard-only area selection works, and "Open observed
   comparison" carries property + period.
5. The archive route still renders approved editions — REL-2 now verifies the
   cited ledger at build time, so a failure would have blocked the build, but
   confirm the pages render.
6. **Rollback is still unrehearsed.** This has now been an open item across two
   audits. It is a release-process gap, not a code gap.

### 2.4 Remaining dependency advisories

28 raw records across 8 package names, all build-time transitives:
`fast-uri` 12, `picomatch` 4, `postcss` 4, `nanoid` 3,
`postcss-selector-parser` 2, `katex` 1, `source-map-js` 1, `yaml` 1.

Each has a reviewed, expiring entry (`2027-02-28`) in
`.github/security-audit-exceptions.yml`. Triage by trying the cheapest fix first:

```bash
cd app && bun update                     # in-range; closes what it can
cd app && bun audit --json | python3 -c "import json,sys; d=json.load(sys.stdin); print({k: len(v) for k,v in d.items()})"
```

Then delete the entries whose advisories closed — the register's rule 3 requires
it, and an unmatched entry is only a notice, so leftovers hide. If a fix needs a
new major, document it and leave the entry dated.

### 2.5 Canonical-JSON parity test

`edition-registry.ts` re-implements Python's
`json.dumps(sort_keys=True, indent=2, ensure_ascii=False) + "\n"` as
`canonicalJsonText`. It verifies all 15 artifacts today, but two implementations
of one hash is a drift hazard: a change to either side silently breaks the pin.

**Do:** one test that runs the Python canonicaliser over every artifact and
compares to the TS output. Cheap, and it retires a class of future confusion.

### 2.6 Pyright — decide whether it gates

`pyrightconfig.json` now exists (the audit's GAP-1). It declares that `mypy` is
the gate, downgrades `reportMissingImports` to warning (for the optional
`hamilton_sdk` import), and suppresses four pandas-heavy modules **by path** with
the reason recorded.

Pyright is **not** in CI. Two honest options, pick one and record it:

- **Gate it.** Add a job, verify the four suppressions are still the only ones,
  and treat a new suppression as a reviewed change.
- **Declare it out.** Delete the file and state that `mypy` is the only checker;
  then the standalone Pyright noise stops being a recurring false alarm.

What must not persist is the current ambiguity, where a tool that is not a gate
produces findings that look like defects (it cost time in this branch).

### 2.7 Small doc corrections

- `app/CHANGELOG.md` still references `@astrojs/tailwind` as a dependency; it is
  gone (Tailwind now runs through `app/postcss.config.mjs`).
- `docs/guides/ci-cd-pipeline.md` is accurate about the audit jobs; re-read the
  evidence section after §2.1 lands.

### 2.8 Basemap key hygiene

`PUBLIC_CARTO_API_KEY` is set locally and as a repo **variable** (not a secret —
it is inlined into the client bundle and public by construction). Confirm it is
domain-restricted at CARTO, and note the endpoint returns 200 with _or_ without
the key, so a blank map is a network/rate-limit problem, not a missing key.

## 3. Owner decisions outstanding

| #   | Decision                                                                                         | Default if silent             |
| --- | ------------------------------------------------------------------------------------------------ | ----------------------------- |
| 1   | Evidence gate: provision for PRs (§2.1) or leave weekly/on-demand                                | weekly/on-demand              |
| 2   | Audit exceptions: keep renewing per-advisory entries, or take the majors that close them in bulk | renew yearly                  |
| 3   | Pyright: gate or declare out (§2.6)                                                              | ambiguity persists — pick one |
| 4   | Rollback rehearsal (§2.3)                                                                        | remains unrehearsed           |
| 5   | R2 secrets now exist on the repo for the evidence job; keep or remove                            | keep                          |

## 4. Traps that cost real time — read before repeating the work

These are all reproducible, and each one produced a wrong conclusion at least
once in this branch.

1. **`envDir` is a Vite option, not an Astro one.** A top-level `envDir` in
   `astro.config.mjs` is silently ignored, so a key in the root `.env` never
   reaches the bundle. It must be `vite: { envDir: ".." }`. Verify by writing a
   marker **into `.env`** and building — testing with a process env var proves
   nothing, because that path bypasses `.env` loading entirely.
2. **`build:base` is not `build`.** `bun run build:base` omits
   `PUBLIC_OBSERVED_RELEASE=v2`, which makes 9 `/explore` E2E tests fail. Use
   `bun run build` for E2E.
3. **Builds rewrite `app/public/data/catalog.jsonl.gz`.** Restore it
   (`git checkout -- app/public/data/catalog.jsonl.gz`) after every build, or it
   becomes an accidental commit.
4. **`@types/node` must be declared.** It arrived transitively and the Astro/Vite
   major pruned the provider; a stale local `node_modules` hid it while CI
   reported 118 errors. When a type error exists in CI but not locally, suspect
   an undeclared transitive and check the lockfile.
5. **`detect-secrets` rewrites `.secrets.baseline`** to refresh line numbers, and
   then refuses to run because the baseline is "unstaged". The only stable state
   is the file the hook itself emits — run it, stage the result, run it again
   (expect exit 0), then commit.
6. **Format before you pin.** A `pre-commit run --all-files` pass reformatted
   five source files after a ledger re-pin, re-drifting four ledgers on their
   pre-format hashes. Whitespace counts.
7. **Ledger pins are censuses.** Adding any file (`filesScanned` +1) re-pins
   several ledgers. `findings` (rs15) pins its siblings' hashes, so it must be
   regenerated _last_; it is self-excluded, so one extra cycle settles it.
8. **Anything untracked cannot be pinned.** `data/analysis` was a scan root; it
   exists on a worktree (38 files) and not in CI, so the ledger was
   unreproducible by construction.
9. **A producer may read `app/dist`.** That is why the evidence gate needs a
   build. Prefer pointing such a producer at committed source.
10. **Bumping Playwright moves the browser build.** `@playwright/test` 1.65
    needs `chromium_headless_shell-1255`; without `bunx playwright install
chromium` every E2E fails in ~1 ms with a launch error, which looks like a
    site outage.
11. **`git checkout -- <path>` restores from the index, not HEAD.** After
    staging, that is not the reset you want; use `git checkout HEAD -- <path>`.
12. **A new advisory can redden CI with no code change.** `virtualenv`
    PYSEC-2026-4402 appeared mid-branch. Fix in range; never blanket-renew.

## 5. Commands

Full gate (what CI enforces, plus what it does not):

```bash
uv run pytest tests/ -q --no-cov
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run python scripts/tools/validate_docs_layout.py
uv run python scripts/tools/validate_agent_skills.py
uv run python scripts/tools/check_catalog.py
uv lock --check || uv lock            # the pre-commit `uv-lock` hook gates this
git diff --check

cd app && PATH="$HOME/.bun/bin:$PATH" bun install --frozen-lockfile
cd app && PATH="$HOME/.bun/bin:$PATH" bun run test:unit
cd app && PATH="$HOME/.bun/bin:$PATH" bun run astro check     # 0/0/21
cd app && PATH="$HOME/.bun/bin:$PATH" bun run validate-data
cd app && PATH="$HOME/.bun/bin:$PATH" bun run build            # NOT build:base
cd app && PLAYWRIGHT_HTML_OPEN=never \
  PLAYWRIGHT_SERVER_COMMAND='bun run preview -- --host 127.0.0.1' \
  PLAYWRIGHT_BASE_URL='http://127.0.0.1:4321' \
  PATH="$HOME/.bun/bin:$PATH" bunx playwright test --workers=2   # 241/9
cd app && PATH="$HOME/.bun/bin:$PATH" bun run build:pages
cd app && PLAYWRIGHT_HTML_OPEN=never PLAYWRIGHT_SERVER_COMMAND='bun run serve:pages' \
  PLAYWRIGHT_BASE_URL='http://127.0.0.1:4402/egg-n-bacon-housing/' \
  PAGES_ORIGIN='http://127.0.0.1:4402' PAGES_BASE_PATH='/egg-n-bacon-housing' \
  PATH="$HOME/.bun/bin:$PATH" bunx playwright test tests/e2e/pages-base.spec.ts --workers=2  # 9/0
git checkout -- app/public/data/catalog.jsonl.gz
```

Evidence + audits:

```bash
for p in amenity_impact causal_inference facility_premiums findings lease_decay \
         macro_sensitivity market_segments mrt_impact price_forecasts school_quality \
         spatial_autocorrelation spatial_hotspots temporal_evolution; do
  uv run python scripts/tools/${p}_evidence.py --check || echo "DRIFT: $p"
done
uv run pip-audit --skip-editable                                  # CI-parity scope
actionlint .github/workflows/*.yml
```

Live (opt-in, real network):

```bash
EGG_LIVE=1 uv run pytest tests/ -m live -q --no-cov
EGG_LIVE=1 uv run python scripts/00_sync_data.py --verify --only evidence --verify-content
```

Toolchain rules: Python only through `uv run`; Bun pinned at **1.2.23**
(`~/.bun/bin`, `/.bun-version`); never `npm i -g bun`; a bun upgrade that rewrites
`app/bun.lock` is a revert.

## 6. Where the evidence lives

| Question                                       | File                                                                                        |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------- |
| What was measured, and with what limits        | [01-discovery.md](01-discovery.md)                                                          |
| Every finding with `path:line` and a probe     | [02-findings.md](02-findings.md)                                                            |
| Phases, gates, gap register, owner decisions   | [03-remediation-spec.md](03-remediation-spec.md)                                            |
| Machine-readable delta baseline                | [baseline.yaml](baseline.yaml)                                                              |
| Runtime logs and reproduced probes             | [evidence/](evidence/)                                                                      |
| Why nine ledgers moved and how it was reviewed | [2026-11-24-ledger-repin-review.md](../../implementation/2026-11-24-ledger-repin-review.md) |
| CI/CD contract                                 | [docs/guides/ci-cd-pipeline.md](../../guides/ci-cd-pipeline.md)                             |
| R2 sync + live validation                      | [docs/guides/r2-sync-guide.md](../../guides/r2-sync-guide.md)                               |
| Programme status ledger                        | [docs/implementation/README.md](../../implementation/README.md)                             |
