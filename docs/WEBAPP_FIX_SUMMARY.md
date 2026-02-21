# Webapp Data Loading Fix - Implementation Summary

**Date**: 2026-02-21
**Issue**: Dashboard pages showing "Data not available" on deployed GitHub Pages site

## Root Cause

The deployed webapp showed "Data not available" errors because:

1. **GitHub workflow didn't generate data files**: The CI/CD workflow built the Astro app without first running the data generation script
2. **Build-time data loading**: Astro components use `fs.readFileSync()` at build time to load data, so files must exist before building
3. **Incorrect decompression**: The `gunzip()` function in Astro pages used `zlib.inflateSync()` with base64 encoding, but the data files were raw gzip compressed

## Changes Made

### 1. GitHub Actions Workflow (`.github/workflows/deploy-app.yml`)

**Added**:
- Python 3.11 setup step
- uv package manager installation
- Dashboard data generation step with environment variables
- Data file verification step

**Key change**:
```yaml
- name: Generate dashboard data
  run: PYTHONPATH=. uv run python scripts/prepare_webapp_data.py
  env:
    ONEMAP_EMAIL: ${{ secrets.ONEMAP_EMAIL }}
    GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
```

### 2. Fixed Gunzip Functions (Astro Pages)

**Files modified**:
- `app/src/pages/dashboard/index.astro`
- `app/src/pages/dashboard/trends.astro`
- `app/src/pages/dashboard/segments.astro`
- `app/src/pages/dashboard/leaderboard.astro`

**Change**:
```javascript
// Before (incorrect):
function gunzip(data) {
  return zlib.inflateSync(Buffer.from(data, 'base64')).toString('utf-8');
}

// After (correct):
function gunzip(data) {
  return zlib.gunzipSync(data).toString('utf-8');
}
```

**Why**: The data files are gzipped (not deflated) and stored as raw bytes (not base64).

### 3. Documentation

**Created**: `docs/GITHUB_SETSUP.md`
- Instructions for adding required GitHub secrets
- Troubleshooting guide
- Security best practices

## Verification

### Local Testing
✅ Data generation: `PYTHONPATH=. uv run python scripts/prepare_webapp_data.py`
✅ Build succeeds: `cd app && bun run build`
✅ Built HTML contains data (no "Data not available" messages)
✅ All dashboard pages verified: index, trends, segments, leaderboard

### Expected CI/CD Behavior
1. On push to `main`, workflow triggers
2. Python + uv are installed
3. Dashboard data is generated (requires API keys from secrets)
4. Data files are verified to exist
5. Astro builds with embedded data
6. Site deploys to GitHub Pages
7. Dashboard pages show actual data

## Required GitHub Secrets

Before this will work in CI/CD, add these repository secrets:

1. **ONEMAP_EMAIL**: Your email address for Singapore OneMap API
2. **GOOGLE_API_KEY**: Google Maps Geocoding API key

See `docs/GITHUB_SETSUP.md` for detailed instructions.

## Files Changed

| File | Change |
|------|--------|
| `.github/workflows/deploy-app.yml` | Added Python setup, data generation, verification |
| `app/src/pages/dashboard/index.astro` | Fixed gunzip function |
| `app/src/pages/dashboard/trends.astro` | Fixed gunzip function |
| `app/src/pages/dashboard/segments.astro` | Fixed gunzip function |
| `app/src/pages/dashboard/leaderboard.astro` | Fixed gunzip function |
| `docs/GITHUB_SETSUP.md` | New documentation file |

## Testing Checklist

After deployment to GitHub Pages:
- [ ] https://minghao51.github.io/egg-n-bacon-housing/dashboard/ shows market overview
- [ ] https://minghao51.github.io/egg-n-bacon-housing/dashboard/segments/ shows scatter plot
- [ ] https://minghao51.github.io/egg-n-bacon-housing/dashboard/trends/ shows trends charts
- [ ] https://minghao51.github.io/egg-n-bacon-housing/dashboard/leaderboard/ shows rankings
- [ ] No "Data not available" messages
- [ ] GitHub Actions workflow passes all steps

## Impact

- **Dashboard pages will display correctly** after next deployment
- **Build time increases** by ~30-60 seconds for data generation
- **Requires GitHub secrets** to be configured (one-time setup)
- **Data is always fresh** on each deployment (no stale data issues)
