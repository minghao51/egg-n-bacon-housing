# Execution Plan — src/ Improvement Program

> **Archived handoff history.** The work orders below describe the earlier
> multi-wave program and are retained for traceability. The current working
> tree has since completed the Hamilton/DAG improvement sequence. Start a new
> task from [`docs/plans/2026-09-10-hamilton-dag-next-thread-handoff.md`](../../docs/plans/2026-09-10-hamilton-dag-next-thread-handoff.md),
> then use `docs/plans/2026-09-10-code-audit-remediation-roadmap.md` for the
> remaining audit backlog.

**Archive status:** Completed and superseded; no pending dispatches from this file.

Status legend: ✅ done · 🔄 ready to dispatch · ⏳ ready after its wave gate

## Completed

- **Batch 1** (6 parallel): WS1 validation integrity, WS2 rental join, WS3 platinum contract, WS4 ingestion resilience, WS5 pipeline core, WS6 cache/adapters — integrated, 452→~500 tests green.
- **Batch 2a** (3 parallel): WS7 layer registry, WS8 dead surface + lookups, WS10 bronze freshness. **Batch 2b**: WS9' schema tightening + school prune + shim removal. Integrated: 525 tests green, all gates.
- **A3** closed by decision (coarse invalidation stays).

## Batch 3 — 🔄 READY

**Wave 1 (parallel — dispatch together):**

- WS11 materializer migration — `.agents/handoffs/WS11-materializer-migration.md`
- WS12 ingestion transforms — `.agents/handoffs/WS12-ingestion-transforms.md`
- WS14 time-index + sqft constant — `.agents/handoffs/WS14-time-index-constant.md`

**Gate:** full pytest + ruff check/format + mypy + catalog + doc/skill validators.

**Wave 2 (after gate):**

- WS13 hotspots floor (config) — `.agents/handoffs/WS13-hotspots-volume-floor.md`

**Gate:** same.

## Batch 4 — ⏳ after Batch 3 gate

**Wave 1 (parallel):**

- WS15 bronze centralization + manual_dir — `.agents/handoffs/WS15-bronze-centralization.md`
- WS16 cleaning validity (per-type coverage, contracts, quarantine tracking, sqft tail) — `.agents/handoffs/WS16-cleaning-validity.md`

**Gate.** **Wave 2:**

- WS17 contract/perf tail (vectorize MRT, index guard, duplicate/dead fields, DI unwiring, WS16 rider injection) — `.agents/handoffs/WS17-contract-tail.md`

**Gate.**

## Batch 5 — ⏳ after Batch 4 (all parallel, one wave)

- WS18 local refresh scheduling — `.agents/handoffs/WS18-local-refresh-scheduling.md`
- WS19 quality report tool — `.agents/handoffs/WS19-quality-report.md`
- WS20 DAG smoke test — `.agents/handoffs/WS20-dag-smoke-test.md`
- WS21 docs sync + D3 measurement — `.agents/handoffs/WS21-docs-sync-d3.md`

**Final gate.**

## Dispatch template (subagent "worker", one task per WS)

> Read .agents/handoffs/<WS-file>.md in the repo root and execute it fully: read-first, changes, tests, verification, constraints, definition-of-done. Stay strictly within the file ownership list.

Parallel dispatch = one subagent call with `tasks: [...]`; sequential wave = dispatch after the previous wave returns + gate passes.

## Integration gate (run between waves)

```
uv run pytest -q --no-cov
uv run ruff check . && uv run ruff format --check .
uv run mypy src/
uv run python scripts/tools/check_catalog.py
uv run python scripts/tools/validate_docs_layout.py
uv run python scripts/tools/validate_agent_skills.py
git diff --check
```

## Standing rules

- Single working tree, no worktrees, no commits (policy).
- Strict file ownership per WS; `tests/conftest.py` + `pyproject.toml` never owned.
- Workers: `uv run` directly (dotenvx not needed for hermetic tests).
- Decisions: see `DECISIONS.md`. Handoff archive: this directory (delete when program completes).
