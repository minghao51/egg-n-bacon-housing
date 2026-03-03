# CI/CD Pipeline Guide

**Last Updated:** 2026-02-28

---

## Overview

This repository uses GitHub Actions for continuous integration and deployment. The CI/CD pipeline ensures code quality, runs tests, and automatically deploys the web application to GitHub Pages.

---

## Workflows

The repository contains four GitHub Actions workflows:

| Workflow | File | Purpose | Triggers |
|----------|------|---------|----------|
| **Test Suite** | `.github/workflows/test.yml` | Run Python tests with coverage | Push to main/develop, PRs |
| **Code Quality** | `.github/workflows/lint.yml` | Check formatting and linting | Push to main/develop, PRs |
| **Deploy App** | `.github/workflows/deploy-app.yml` | Build and deploy to GitHub Pages | Push to main, manual |
| **Docs Layout Check** | `.github/workflows/docs-layout.yml` | Validate documentation structure | Push to main/develop, PRs |

---

## 1. Test Suite Workflow

**File:** `.github/workflows/test.yml`

### What It Does

1. **Sets up environment:**
   - Checks out code
   - Installs uv package manager
   - Sets up Python 3.11
   - Installs dependencies with `uv sync`

2. **Creates test environment:**
   - Generates `.env` file with test values
   - Creates required data directories

3. **Runs tests:**
   - Executes pytest with verbose output
   - Generates coverage report for `scripts/core`
   - Outputs coverage in XML and terminal formats

4. **Uploads results:**
   - Sends coverage to Codecov (optional)
   - Archives HTML coverage report as artifact

### Environment Variables

The workflow creates a test `.env` file with these values:

```bash
ONEMAP_EMAIL=test@example.com
GOOGLE_API_KEY=test-api-key
ONEMAP_EMAIL_PASSWORD=test-password
SUPABASE_URL=https://test.supabase.co
SUPABASE_KEY=test-key
JINA_AI=test-jina-key
LOG_LEVEL=DEBUG
```

### Coverage Reporting

- **Codecov Integration:** Coverage uploaded to [codecov.io](https://codecov.io)
- **Artifact:** HTML report stored as `coverage-report-python-3.11`
- **Threshold:** No hard failure threshold (fail_ci_if_error: false)

### View Coverage Reports

1. **In CI logs:** Check GitHub Actions run logs
2. **Download artifact:** Go to Actions → Select run → Scroll to "Artifacts" section
3. **Codecov dashboard:** Visit your repository's Codecov page

---

## 2. Code Quality Workflow

**File:** `.github/workflows/lint.yml`

### What It Does

1. **Checks code formatting:**
   - Runs `ruff format --check` on `scripts/core` and `tests`
   - Fails if code is not properly formatted

2. **Checks code quality:**
   - Runs `ruff check` with GitHub output format
   - Catches linting errors, unused imports, code smells

### Fixing Linting Errors Locally

Before pushing, run these commands:

```bash
# Format code
uv run ruff format scripts/core tests

# Check linting
uv run ruff check scripts/core tests

# Auto-fix issues
uv run ruff check scripts/core tests --fix
```

### Common Linting Issues

| Issue | Fix Command |
|-------|-------------|
| Import not used | `uv run ruff check --fix` |
| Line too long | Manual fix (target: 100 chars) |
| Missing type hints | Add type annotations |
| Incorrect formatting | `uv run ruff format` |

---

## 3. Deploy App Workflow

**File:** `.github/workflows/deploy-app.yml`

### What It Does

#### Build Job

1. **Sets up environment:**
   - Checks out code
   - Installs Bun (JavaScript runtime)
   - Installs Python 3.11
   - Installs uv package manager

2. **Installs dependencies:**
   - Runs `bun install` in `app/` directory

3. **Syncs content files:**
   - Executes `scripts/sync-content.sh` to prepare data

4. **Verifies dashboard data:**
   - Checks for required JSON files in `app/public/data/`
   - Fails build if any required files are missing

5. **Builds Astro app:**
   - Runs `bun run build` in `app/` directory
   - Verifies `dist/index.html` exists

6. **Uploads artifact:**
   - Uploads `app/dist/` directory for deployment

#### Deploy Job

1. **Deploys to GitHub Pages:**
   - Uses GitHub Pages deployment action
   - Deploys artifact from build job
   - Provides deployment URL

### Required Data Files

The workflow verifies these files exist before building:

```bash
# Dashboard overview and trends
public/data/dashboard_overview.json.gz
public/data/dashboard_trends.json.gz

# Market segments
public/data/dashboard_segments.json.gz

# Leaderboards
public/data/dashboard_leaderboard.json.gz

# Map data
public/data/map_metrics.json.gz
public/data/hotspots.json.gz

# Amenity summary
public/data/amenity_summary.json.gz

# Interactive tools
public/data/interactive_tools/mrt_cbd_impact.json.gz
public/data/interactive_tools/lease_decay_analysis.json.gz
public/data/interactive_tools/affordability_metrics.json.gz
public/data/interactive_tools/spatial_hotspots.json.gz
```

**Missing files cause build failure.**

### Trigger Conditions

- **Automatic:** Runs on push to `main` branch
- **Manual:** Can be triggered via GitHub Actions UI (workflow_dispatch)

### Deployment URL

After deployment:
- URL: `https://<username>.github.io/egg-n-bacon-housing/`
- Available in: Repository → Settings → Pages

### Sync Content Script

The `scripts/sync-content.sh` script prepares data for deployment:

```bash
#!/bin/bash
# Copies generated analytics data to app/public/data/
# Ensures dashboard has latest data
```

---

## 4. Docs Layout Check Workflow

**File:** `.github/workflows/docs-layout.yml`

### What It Does

1. **Validates documentation:**
   - Runs `scripts/tools/validate_docs_layout.py`
   - Checks for broken internal links
   - Verifies documentation structure

### Validation Rules

- All internal links must point to existing files
- Documentation must follow naming conventions
- Required sections must be present

### Fixing Documentation Errors

```bash
# Run validation locally
uv run python scripts/tools/validate_docs_layout.py
```

---

## Workflow Dependencies

```
Push to main/develop or Pull Request
         │
         ├─→ [test.yml] → Run tests → Upload coverage
         │
         ├─→ [lint.yml] → Check formatting → Check linting
         │
         └─→ [docs-layout.yml] → Validate docs

Push to main only
         │
         └─→ [deploy-app.yml] → Build → Deploy to GitHub Pages
```

---

## Environment Variables in CI

### Required Secrets

For local development, these are in `.env`. For CI, they're set in the workflow files:

| Variable | Purpose | Source |
|----------|---------|--------|
| `ONEMAP_EMAIL` | OneMap API authentication | `.env` or GitHub Secrets |
| `GOOGLE_API_KEY` | Google Maps fallback | `.env` or GitHub Secrets |
| `SUPABASE_URL` | Supabase connection | `.env` or GitHub Secrets |
| `SUPABASE_KEY` | Supabase authentication | `.env` or GitHub Secrets |

**Note:** Current workflows use test values that don't access real APIs.

---

## Troubleshooting

### Test Failures in CI

**Issue:** Tests pass locally but fail in CI

**Solutions:**

1. **Check Python version:**
   ```bash
   # CI uses Python 3.11
   python --version  # Should be 3.11.x
   ```

2. **Sync dependencies:**
   ```bash
   uv sync --upgrade
   ```

3. **Check test environment:**
   ```bash
   # CI creates these directories
   mkdir -p data/pipeline/{L0,L1,L2,L3} data/{cache,manual,analysis}
   ```

4. **Run tests with CI flags:**
   ```bash
   uv run pytest tests/ -v --tb=short --cov=scripts/core
   ```

---

### Linting Failures

**Issue:** Code fails `ruff format --check` in CI

**Solution:**
```bash
# Format code locally
uv run ruff format scripts/core tests

# Verify no changes needed
uv run ruff format --check scripts/core tests
```

---

### Deployment Failures

**Issue:** Deploy workflow fails on "Missing required data file"

**Solutions:**

1. **Generate missing data:**
   ```bash
   # Run webapp data preparation
   uv run python scripts/prepare_webapp_data.py
   ```

2. **Verify files exist:**
   ```bash
   ls -la app/public/data/
   ls -la app/public/data/interactive_tools/
   ```

3. **Check file permissions:**
   ```bash
   chmod 644 app/public/data/*.json.gz
   ```

---

### Docs Validation Failures

**Issue:** Docs layout check fails

**Solution:**
```bash
# Run validation locally to see errors
uv run python scripts/tools/validate_docs_layout.py

# Fix reported issues
# - Update broken links
# - Rename files to match conventions
# - Add missing sections
```

---

## Workflow Status Badges

Add these badges to your README:

```markdown
[![Tests](https://github.com/<username>/egg-n-bacon-housing/actions/workflows/test.yml/badge.svg)](https://github.com/<username>/egg-n-bacon-housing/actions/workflows/test.yml)
[![Lint](https://github.com/<username>/egg-n-bacon-housing/actions/workflows/lint.yml/badge.svg)](https://github.com/<username>/egg-n-bacon-housing/actions/workflows/lint.yml)
[![Deploy](https://github.com/<username>/egg-n-bacon-housing/actions/workflows/deploy-app.yml/badge.svg)](https://github.com/<username>/egg-n-bacon-housing/actions/workflows/deploy-app.yml)
```

---

## Manual Workflow Triggers

### Trigger Deploy Manually

1. Go to **Actions** tab in GitHub
2. Select **Deploy App to GitHub Pages** workflow
3. Click **Run workflow** dropdown
4. Select branch (usually `main`)
5. Click **Run workflow** button

### Trigger Test Manually

Not currently supported - tests only run on push/PR. To enable:

```yaml
on:
  workflow_dispatch:  # Add this to test.yml
  push:
    branches: [ main, develop ]
```

---

## CI Performance

| Workflow | Typical Duration |
|----------|-----------------|
| Test Suite | 2-3 minutes |
| Code Quality | 30-60 seconds |
| Deploy App | 3-5 minutes |
| Docs Layout | 10-20 seconds |

**Total CI time per push:** ~5-8 minutes (all workflows run in parallel)

---

## Best Practices

### 1. Run Checks Locally First

Before pushing:

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Run tests
uv run pytest

# Validate docs
uv run python scripts/tools/validate_docs_layout.py
```

### 2. Fix CI Failures Promptly

- CI failures block merges to main
- Fix issues before pushing new commits
- Use draft PRs to test CI without blocking

### 3. Keep Tests Fast

- Use `@pytest.mark.unit` for fast tests
- Use `@pytest.mark.slow` for integration tests
- Skip slow tests in CI: `pytest -m "not slow"`

### 4. Monitor Coverage

- Check coverage reports in PRs
- Aim to maintain or increase coverage
- Investigate coverage drops

---

## Related Documentation

- [Testing Guide](./testing-guide.md) - Writing and running tests
- [Architecture](../architecture.md) - Project structure overview
- [Configuration Guide](./configuration.md) - Environment setup
- [GitHub Docs](https://docs.github.com/en/actions) - GitHub Actions documentation

---

## Summary

| Workflow | Status Checks | Artifacts | Deployment |
|----------|---------------|-----------|------------|
| **Test** | ✅ Required | Coverage report | No |
| **Lint** | ✅ Required | None | No |
| **Deploy** | ❌ Optional | Build artifact | Yes (GitHub Pages) |
| **Docs** | ✅ Required | None | No |

**Key Points:**
- All workflows run automatically on push/PR
- Tests and linting must pass before merging
- Deployment happens automatically on push to main
- Docs validation prevents broken documentation

---

**Need Help?**
- Check [GitHub Actions runs](https://github.com/<username>/egg-n-bacon-housing/actions)
- Review workflow logs for detailed error messages
- Open an issue for persistent CI failures
