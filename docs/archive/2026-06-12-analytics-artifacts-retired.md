# Analytics Artifact Retirement

**Date:** 2026-06-12

## Summary

The tracked historical artifact trees `data/analytics/` and `data/analysis/` were removed from the supported repo surface.

## Why

- the app reads analytics content from `docs/analytics/`
- the app reads runtime datasets from `app/public/data/`
- article images are served from `app/public/data/analysis/`
- no supported runtime path reads from `data/analytics/` or `data/analysis/`

## Resulting Boundary

- supported analytics publishing surface:
  - `docs/analytics/`
  - `app/public/data/`
  - `app/public/data/analysis/`
- historical analytics outputs:
  - no longer tracked as live repo inputs
  - should be regenerated intentionally if needed for research or archival review
