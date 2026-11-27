# WS-C1 — Pages-base release gate (REL-1)

**Severity:** MEDIUM (3×2 = 6). **Effort:** M. **Wave:** 1.

## Problem

The only suite that exercises the real GitHub Pages prefix is skipped in CI and is not run before deployment.

- `.github/workflows/ci.yml:142-151` — E2E builds the default site and runs `astro preview` at `/`.
- `app/tests/e2e/pages-base.spec.ts:21-24` — `test.skip(!ORIGIN, …)` when `PAGES_ORIGIN` is unset.
- `.github/workflows/deploy.yml:52-67` — route smoke is `grep` on headings; `:85-121` checks one base-prefixed CSS asset only.
- Deploy has no dependency on CI.

Audit evidence: at baseline the root E2E run skipped exactly those 9 tests, and the prefixed run passed 9/9 (`evidence/e2e.log`, `evidence/pages-e2e.log`).

## Required change

1. Add a CI job (e.g. `pages-e2e`) that:
   - installs with `bun install --frozen-lockfile` (Bun 1.2.23),
   - runs `bun run build:pages`,
   - serves `node scripts/serve-pages-base.mjs` on 4402,
   - runs `bunx playwright test tests/e2e/pages-base.spec.ts` with `PAGES_ORIGIN`, `PAGES_BASE_PATH`, `PLAYWRIGHT_BASE_URL`, `PLAYWRIGHT_SERVER_COMMAND='bun run serve:pages'`.
2. Make the deploy job depend on that coverage — either add the same steps to `deploy.yml`'s build job or introduce a required workflow that deploy `needs:`. Do not weaken the existing deploy smoke checks.
3. Make the build-time catalog rewrite harmless in CI: `bun run build:pages` rewrites `app/public/data/catalog.jsonl.gz`. Add a post-build `git diff --exit-code -- app/public/data/catalog.jsonl.gz` assertion (restore first if the rewrite is expected) so a drifting generated asset fails loudly instead of silently.
4. Keep the whole-root E2E job unchanged (it covers `/` behaviour).

## Tests / proof

- The new job must fail when a base-prefixed asset is broken: verify locally by temporarily deleting `dist/_astro/*.css` or rewriting a prefixed link in `dist`, run the job's commands, confirm failure, then restore. Record the result in the handoff completion note.
- Confirm the 9 tests run (not skip) in CI output.

## Verification

```bash
cd app && PATH="$HOME/.bun/bin:$PATH" bun run build:pages
cd app && PLAYWRIGHT_HTML_OPEN=never PLAYWRIGHT_SERVER_COMMAND='bun run serve:pages' \
  PLAYWRIGHT_BASE_URL='http://127.0.0.1:4402/egg-n-bacon-housing/' \
  PAGES_ORIGIN='http://127.0.0.1:4402' PAGES_BASE_PATH='/egg-n-bacon-housing' \
  bunx playwright test tests/e2e/pages-base.spec.ts --workers=2
git checkout -- app/public/data/catalog.jsonl.gz
```

## Owns

`.github/workflows/ci.yml`, `.github/workflows/deploy.yml`, `app/package.json` (only if a script alias is needed), `docs/guides/ci-cd-pipeline.md`.

## Do not touch

Application source, test bodies, Python packaging.

## Done when

The Pages-prefixed suite is a required, non-skipping part of the pipeline, a deliberately broken prefix fails it, generated-asset drift is detected, and `docs/guides/ci-cd-pipeline.md` describes the gate.
