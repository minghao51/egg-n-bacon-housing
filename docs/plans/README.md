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
- Once a plan becomes purely historical and no longer drives work, move the outcome summary to `docs/archive/` and keep only the active or superseding plan here.
- If a plan is replaced, keep the file but mark it `Superseded` and point to the replacement.
- Many older plans document now-removed analytics scripts and historical output paths; use them as design history only unless a newer active doc explicitly revives that surface.

## Current Reporting Refresh Proposal

**Resume point:** [`prompts/handoffs.md`](../../prompts/handoffs.md) — where the refresh stands and what to do next.

**Status:** RF00–RF07, RF09 and RF11 are implemented locally and uncommitted (see the [implementation ledger](../implementation/README.md)); the v2 observed pack is published in the working tree, nothing is deployed, RF08 stays blocked on its sign-offs, and RF10/RF12 have not started.

- [Full implementation map](2026-11-12-reporting-refresh-implementation-map.md) — RF00–RF12 dependencies, contracts, ownership and milestone release gates.
- [Implementation handoffs](2026-11-12-reporting-refresh-handoffs.md) — bounded assignments, entry files, tests, approvals and stop conditions.
- [Research and asset register](2026-11-12-reporting-refresh-research-register.md) — all 15 studies, persona pages and separate asset vintages.
- [Decision ledger](2026-11-12-reporting-refresh-decisions.md) — the 12 open decisions, what each blocks, and the format for recording them.
- [Audit evidence](../implementation/2026-reporting-refresh-audit.md) — observed freshness and correctness findings behind the proposal.

## Recent Meta Plans

- `docs/plans/2026-02-24-scripts-docs-simplification-plan.md` - scripts/docs organization conventions and migration steps
- `docs/plans/2026-09-10-hamilton-dag-next-thread-handoff.md` - current resume point for the completed Hamilton/DAG improvement sequence
- `docs/plans/2026-09-10-code-audit-remediation-roadmap.md` - **Completed 2026-09-12** — all audit follow-ups landed and verified; closeout evidence in `2026-09-11-hamilton-dag-e2e-evidence.md`
- `docs/plans/2026-09-12-remediation-followups-handoff.md` - **Closed 2026-09-12** — amenity catalog descriptions added, pip-audit verified clean; remaining items are standing decisions/notes (incl. 2026-09-12 published-output baseline + pip-audit recipe)

## Audit Reports

- `docs/plans/2026-04-28-code-audit-findings.md` - code audit of DAG refactor, rental ingestion, and schema relaxation (3 critical, 6 high, 7 medium, 5 low)
