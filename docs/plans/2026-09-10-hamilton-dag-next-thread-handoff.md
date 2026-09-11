# Hamilton DAG Improvement — Next-Thread Handoff

**Date:** 2026-09-10
**Status:** Ready for continuation — implementation is uncommitted
**Baseline:** Current working tree; preserve unrelated user changes and do not reset or commit.

## Current state

The four-work-order Hamilton/DAG improvement sequence is implemented in the
working tree. The main behavior now includes:

- one `PublishedOutputSpec` registry for the 12 silver/gold/platinum outputs;
- `stage="all"` materializing all 12 outputs while returning the six terminal
  frames, with narrow `final_vars` behavior preserved;
- typed validation results and run-scoped quarantine artifacts with source
  identity/rejection reason;
- atomic `LayerWriter` writes and anomaly checks before the current snapshot;
- explicit cache/runtime dependency injection, deterministic cache fingerprints,
  lazy external clients, and cache-disabled published/materializer nodes;
- removal of the `L5` alias, global runtime configuration surfaces, deprecated
  loader helpers, and confirmed orphan artifacts;
- committed app-data manifest/validator, pinned Bun metadata, managed Ruff
  setup, research dependency naming, and optional tracking extra.

## Verification already completed

The latest hermetic verification completed successfully:

- `uv run pytest -q --no-cov`: **747 passed** (76 Hamilton deprecation warnings);
- coverage run: **95%**;
- Ruff check and format check: passed;
- mypy: passed;
- catalog, docs-layout, agent-skill, app-data, lockfile, and `git diff --check`:
  passed.

The production app build has not been run because Bun is not available on the
current host. No commit was created.

## Continuation attempt (2026-09-10)

- Pinned Bun metadata was confirmed (`app/.bun-version` = `1.2.23`), but the
  Bun executable is not installed on this host, so the production build remains
  blocked.
- Focused pipeline verification passed: 51 tests in
  `tests/test_pipeline.py`, `tests/test_pipeline_integration.py`, and
  `tests/test_materialization.py`.
- Ruff, format, mypy, catalog, docs-layout, agent-skill, and diff checks passed.
- The catalog was regenerated from the current pipeline outputs. It still
  contains `flat_type_count` because the existing
  `data/pipeline/03_gold/rental_yield.parquet` contains that physical column;
  a credentialed/full pipeline run is required before deciding whether to retire
  that artifact.
- Historical plan references to `L5` and compatibility APIs were left intact as
  archival history.

## Continuation attempt 2 (2026-09-10)

- `dotenvx` removal is functional: the direct supported command loads the local
  ignored `.env`, and network-enabled execution successfully obtained a fresh
  OneMap token.
- `uv sync` does not install this checkout as an importable package; the run
  therefore used `PYTHONPATH=src` with the unchanged `main.py --stage all`
  entrypoint. This packaging gap should be resolved or documented before the
  final production run.
- The full run reached `geocoded_properties` and began populating the OneMap
  search cache for 11,605 unique addresses. It was stopped after approximately
  ten minutes because this was a cold, rate-limited geocoding pass; it did not
  reach materialization or terminal result reporting. The interrupted Hamilton
  run emitted a cache-hook assertion during shutdown, so it is not a passing
  E2E result.
- The partial OneMap cache is retained in ignored runtime data. Resume with the
  same serial command on a host intended for the cold geocoding workload; do not
  clear the cache unless intentionally measuring a cold run.
- Bun remains unavailable; the pinned app build is still pending.

## Continuation attempt 3 (2026-09-11) — checklist complete

All seven checklist items are done; evidence in
`docs/plans/2026-09-11-hamilton-dag-e2e-evidence.md`.

- **Bun build:** pinned 1.2.23 installed; `bun install --frozen-lockfile` +
  `bun run build` succeeded (148 pages).
- **Credentialed E2E:** two real bugs surfaced and were fixed: (1) `main.py`
  pre-collapsed `--stage` into `final_vars`, so the CLI never hit the
  materialize-all-12 branch (only 6 terminal materializers ran) — fixed by
  passing `stage` through to `run_pipeline`, with CLI regression tests; (2)
  `CacheManager` TOCTOU races (vanished-file `stat()` crash + fixed-`.tmp`
  write collisions) — fixed with miss-on-vanish and unique tmp names, with
  focused tests. After the fixes, `--stage all` materialized all 12 outputs,
  returned exactly the six terminal frames, and wrote run-scoped quarantine
  artifacts. Exit 0.
- **Timings:** resumed-cold 4:14.70 → warm 3:09.96 / 1:13.90 / 1:12.18;
  ingestion + materializers execute while heavy transforms hit the Hamilton
  result store. Serial remains the default (parallel gate not met/benched).
- **Deletion recovery:** `town_360.parquet` recreated byte-identical in
  1:12.47 with zero cache churn (59→59 hamilton, 14,001→14,001 source).
- **Catalog:** fresh `rental_yield` no longer has `flat_type_count`;
  regenerated catalog has zero such rows and `check_catalog.py` passes.
  Orphaned old-named silver artifacts removed.
- **L5/compat history:** kept as archival history (active docs clean; no
  edits needed).
- **writer= shim:** removed from all six compute-node facades + tests
  (748 passed, lint/type/docs clean).

## Next thread checklist

Complete these in order:

1. Install/use the pinned Bun version (`app/.bun-version`, currently 1.2.23),
   then run `cd app && bun install --frozen-lockfile && bun run build`.
2. Run a credentialed end-to-end `main.py --stage all` using the supported
   entrypoint and verify all 12 published files plus the six returned terminal
   frames. Keep execution serial.
3. Capture cold, first-warm, and third-warm timings. Confirm ingestion and
   materializers execute while expensive transformations/reference branches are
   reused; do not enable parallel Hamilton execution unless an isolated
   benchmark shows at least 20% end-to-end improvement without rate-limit or
   determinism regressions.
4. Validate the deleted-file recreation path: remove one published parquet,
   rerun the same request, and confirm unrelated cached nodes are not cleared.
5. Resolve the catalog follow-up: the regenerated
   `data/catalog/catalog.jsonl` still contains `flat_type_count` because the
   current checked-out `rental_yield.parquet` contains that physical column.
   After a fresh pipeline output, either regenerate the catalog again or record
   the artifact as intentionally historical; do not edit the generated row
   manually.
6. Decide whether historical `docs/plans/`/archive references to removed `L5`
   and compatibility APIs should remain as history or be marked explicitly as
   superseded. Active source/docs references are already clean.
7. If strict API removal is desired, remove the remaining test-facing wrapper
   handling of legacy `writer=` kwargs after confirming downstream callers; the
   pure compute nodes are writer-free.

## Acceptance criteria for handoff completion

- pinned Bun production build succeeds;
- credentialed full run materializes all registered outputs and returns exactly
  the terminal result set;
- quarantine, retention cleanup, atomic-write recovery, anomaly ordering, and
  `pipeline_as_of_date` cache invalidation are demonstrated;
- cold/warm timing evidence is recorded and serial execution remains the
  default unless the benchmark gate is met;
- catalog and active documentation agree with the output registry, quarantine
  paths, tracking extra, and removal of `L5`.

## Files to read first

- `docs/plans/2026-09-10-code-audit-remediation-roadmap.md` — broader audit
  backlog and deferred follow-ups;
- `docs/plans/2026-09-01-pipeline-refresh-handoff.md` — refresh/data-source
  history;
- `docs/plans/2026-09-03-runtime-dependency-injection-handoff.md` — runtime DI
  migration history;
- `.agents/handoffs/EXECUTION-PLAN.md` — archived work-order history.
