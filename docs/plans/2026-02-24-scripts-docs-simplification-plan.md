# Scripts and Docs Simplification Plan

**Date**: 2026-02-24
**Status**: In Progress

## Objective

Reduce root-level clutter in `scripts/`, align script/docs indexes with the actual filesystem, and make `docs/` easier to navigate by lifecycle.

## Audit Summary

### Scripts

- `scripts/` root contained a mix of stable entrypoints, webapp data generators, transforms, and developer utilities.
- `scripts/README.md` described directories that no longer exist (`scripts/pipeline/`, `scripts/analytics/calculate/`, `scripts/analytics/forecast/`).
- Several root scripts were primarily webapp-export helpers and not core entrypoints.

### Docs

- `docs/` root mixed architecture docs, operational guides, and implementation summaries.
- Guide links in `README.md` and `docs/guides/README.md` referenced moved/nonexistent paths.
- `docs/plans/` uses mixed filename conventions (`plan_*`, `YYYYMMDD-*`, `YYYY-MM-DD-*`).

## Decisions

### 1. Scripts Root Policy

Keep only stable entrypoints and top-level script docs at `scripts/` root:

- `run_pipeline.py`
- `prepare_webapp_data.py`
- `sync-content.sh`
- `README.md`, `PIPELINE_GUIDE.md`, `CODING_STANDARDS.md`

Move implementation helpers into subdirectories:

- `scripts/webapp/` for dashboard JSON generators and transforms
- `scripts/tools/` for developer validation/tooling

### 2. Backward Compatibility

When moving Python scripts that are referenced by tests or historical docs:

- leave a thin compatibility wrapper at the old path
- wrapper should import and run the new implementation

### 3. Docs Root Policy

Keep only foundational docs at `docs/` root:

- `README.md` (new documentation map)
- `architecture.md`
- directory indexes (`guides/`, `plans/`, `archive/`, `analytics/`)

Move other operational/how-to docs into `docs/guides/`.
Move historical implementation summaries into `docs/archive/`.

### 4. Naming Conventions (New Files)

- Guides/analytics docs: `kebab-case.md`
- Dated plans/reports: `YYYY-MM-DD-short-title.md`
- Avoid new `plan_*` file names unless required by an external tool

## Implementation Checklist

- [x] Create `scripts/webapp/` and `scripts/tools/`
- [x] Move root helper scripts into those directories
- [x] Add compatibility wrappers at legacy paths
- [x] Rewrite `scripts/README.md` to match current layout
- [x] Add `docs/README.md`
- [x] Move root guides into `docs/guides/`
- [x] Move implementation summary into `docs/archive/`
- [x] Add `docs/plans/README.md`
- [ ] Normalize all legacy plan filenames (deferred; large historical set)
- [ ] Add CI job for docs layout validation (optional follow-up)

## Guardrail

Use `scripts/tools/validate_docs_layout.py` to validate active docs references and naming conventions after future moves.
