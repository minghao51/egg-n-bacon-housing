# WS-D2 — Dependency hygiene and advisory gates (DEP-1, REL-4)

**Severity:** LOW 3 + MEDIUM 9. **Effort:** M. **Wave:** 3 (sole owner of dependency manifests in this wave).

## Problem

1. **No advisory gate outside the CI-parity environment.** `.github/workflows/ci.yml:34-42` runs `pip-audit --skip-editable` in a `--dev`-only environment; the `research` group is never audited. There is no `bun audit` step at all.
   Fresh evidence (`../evidence/dependency-pip-audit.txt`, `../evidence/dependency-bun-audit.txt`): core+dev 165 deps / 0 advisories; all groups 303 deps / 238 raw advisory records across 23 packages; `bun audit` 110 raw records across 24 names (Astro 14, DOMPurify 21, KaTeX 1, Sharp 3). Raw records include duplicate/alias representations — not unique CVEs, and no reachability was established. No `astro:assets`/`<Image>`/AVIF usage exists in `app/src`, so the Astro AVIF RCE advisory (`GHSA-26w7-cxv4-gfx2`) is **not** claimed reachable here.
2. **Declared dependencies with no reference.** `pyproject.toml:18` `rapidfuzz`, `:35` `pytest-mock`, `:36` `pytest-asyncio`, `:50` `cachetools` — zero matches across `src/`, `scripts/`, `tests/`, `app/src/`. The scan cannot prove unusedness (dynamic use, CLI-only use, future intent).

## Required change

### A — Advisory gates (REL-4)

1. Add an all-groups Python audit job (frozen export → `pip-audit -r`, no install) and a `bun audit` job for `app/`.
2. Because both are currently non-empty, introduce a **reviewed exception file** (e.g. `.github/security-audit-exceptions.yml`) listing each accepted advisory id with: scope, package, rationale, owner role, expiry/review date. The job fails on any finding not listed, and fails when a listed entry has expired.
3. Record in `docs/guides/ci-cd-pipeline.md` how to triage a new advisory and how to raise a fix (lockfile upgrade path, compatibility validation).
4. Do **not** attempt the Astro major upgrade in this order. Instead: document the upgrade path (5.16.16 → 7.x) and the required validation (build, `astro check`, unit, E2E, Pages-prefixed E2E) as a follow-up decision. If a lower-risk in-range upgrade fixes any listed advisory, apply only that, with the full gate.
5. Keep the existing CI-parity `pip-audit` job as-is.

### B — Dependency hygiene (DEP-1)

6. Confirm with the owner (or by checking notebooks/plans) that `rapidfuzz`, `pytest-mock`, `pytest-asyncio` and `cachetools` are genuinely unused. If confirmed, remove them from `pyproject.toml` and refresh `uv.lock` with `uv lock`.
7. Run the full suite and both frontend commands after removal. If anything fails, restore the package rather than changing tests.
8. Do not remove anything from the `research` group in this order — those are notebook/analysis surfaces with documented caveats, and removal needs its own decision.

## Verification

```bash
uv lock && uv sync --dev --locked
uv run pytest tests/ -q --no-cov
uv run ruff check . && uv run mypy
uv run pip-audit --skip-editable
cd app && PATH="$HOME/.bun/bin:$PATH" bun install --frozen-lockfile && bun run test:unit && bun run astro check
git diff --stat   # expect pyproject.toml + uv.lock (+ workflow/docs/exception file)
```

## Owns

`pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml`, `.github/security-audit-exceptions.yml` (new), `docs/guides/ci-cd-pipeline.md`.

## Do not touch

`app/bun.lock` or `app/package.json` unless an in-range patch upgrade is chosen (then follow the pinned-bun rule and restore on accidental rewrite). No application source.

## Done when

Both audit scopes run in CI with a reviewed, expiring exception list; no unreviewed advisory can pass silently; unreferenced packages are removed (or a written reason keeps them); and the full gate plus `pip-audit` is green.
