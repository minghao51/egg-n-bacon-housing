# Plans Index

Planning and design documents for repository changes.

## Naming Convention

- Preferred: `YYYY-MM-DD-short-title.md`
- Legacy files may use older date formats; avoid creating new files in those formats.

## Status Convention (recommended)

Include a header block near the top with:

- `Date`
- `Status` (`Draft`, `Approved`, `In Progress`, `Completed`, `Superseded`)
- `Superseded By` (optional)

## Working Rules

- Active design and implementation plans stay in `docs/plans/`.
- Once a plan becomes purely historical and no longer drives work, move the outcome summary to `docs/archive/`.
- If a plan is replaced, keep the file but mark it `Superseded` and point to the replacement.

## Recent Meta Plans

- `docs/plans/2026-02-24-scripts-docs-simplification-plan.md` - scripts/docs organization conventions and migration steps

## Audit Reports

- `docs/plans/2026-04-28-code-audit-findings.md` - code audit of DAG refactor, rental ingestion, and schema relaxation (3 critical, 6 high, 7 medium, 5 low)
