# CI/CD Pipeline Guide

**Last Updated**: 2026-06-12

## Overview

The repository currently uses two active GitHub Actions workflows:

| Workflow   | File                           | Purpose                                                        |
| ---------- | ------------------------------ | -------------------------------------------------------------- |
| CI         | `.github/workflows/ci.yml`     | Python linting, type checking, tests, docs validation, app E2E |
| Deploy App | `.github/workflows/deploy.yml` | Build and deploy the Astro app to GitHub Pages                 |

## CI Workflow

File: `.github/workflows/ci.yml`

The CI workflow runs these jobs:

1. `lint`
   - installs Python deps with `uv sync --dev`
   - runs the configured pre-commit checks
2. `typecheck`
   - runs the supported mypy target set for the core Python surface
3. `security`
   - runs `uv run pip-audit --skip-editable`
4. `test`
   - creates a minimal `.env`
   - runs pytest with coverage
   - enforces the core coverage floor
   - validates active docs with `scripts/tools/validate_docs_layout.py`
5. `e2e`
   - installs app deps with Bun
   - builds the Astro app
   - runs Playwright against the preview server

## Deploy Workflow

File: `.github/workflows/deploy.yml`

The deploy workflow:

1. checks out the repo
2. installs Bun and Python
3. installs app dependencies with `bun install`
4. verifies the required dashboard data files under `app/public/data/`
5. builds the Astro app with `bun run build`
6. uploads `app/dist/`
7. deploys to GitHub Pages
8. runs a lightweight smoke check against the deployed pages

## Local Mirrors of CI

Python checks:

```bash
uv sync --dev
uv run ruff check .
uv run mypy src/egg_n_bacon_housing/components src/egg_n_bacon_housing/adapters src/egg_n_bacon_housing/utils/cache.py src/egg_n_bacon_housing/utils/contracts.py src/egg_n_bacon_housing/pipeline.py src/egg_n_bacon_housing/config.py tests
uv run pytest
uv run python scripts/tools/validate_docs_layout.py
```

App checks:

```bash
cd app
bun install
bun run build
bun run test:e2e
```

## Notes

- The app no longer relies on the older content-sync shell step.
- The app loads analytics markdown directly from `docs/analytics/` via Astro content collections.
- If deployment fails on missing app data files, regenerate or restore the expected contents of `app/public/data/` before re-running the workflow.
