# Code Audit Remediation — Leftover-Work Handoff

**Date:** 2026-09-11
**Baseline:** `main` @ `4eeda3f` — CI + Deploy green, 753 tests passing, tree clean.
**Resume point:** this doc, then `docs/plans/2026-09-10-code-audit-remediation-roadmap.md`
for full per-item specs. This handoff lists only the VERIFIED-REMAINING items,
pre-grouped into subagent-dispatchable waves with file:line anchors.
**Mode:** dispatch `worker` subagents per wave (patterns that worked are in
"Subagent playbooks" below); the main thread should drive any long-running
pipeline execution itself.

## What already landed — do NOT redo

Four-work-order Hamilton migration + E2E hardening landed as commits
`f1bb052`, `959ad66`, `de90909`, `e352da8`, `334d519`, `4eeda3f`. Verified
against code on 2026-09-11, these roadmap items are DONE (or moot):

- **Item 8** (writer= facades) — removed from all six compute-node modules + tests.
- **Item 14** (`read_bronze_cache`) — exists at `utils/bronze.py:185`.
  Remainder (manifest_age_days extraction, skill-text sentence) still open.
- **Item 25** (cache `.tmp` uniqueness + concurrency test) — done as part of the
  E2E hardening (`utils/cache.py` pid+thread-unique tmp, miss-on-vanish, tests
  in `tests/test_cache.py`). The `clear()` sweep of legacy `*.json.tmp`
  orphans may still be worth a look.
- **Item 26** (.gitignore hygiene) — rules present; no committed artifacts.
  Deleting root `__pycache__/` (untracked) is trivial and still open.
- **Phase 6 renames** — docs-layout validator passes with zero findings.
- **Phase 7 validation** — warm full run, catalog regen + check, V-all,
  `pre-commit run --all-files`, pip-audit all done 2026-09-11; see
  `docs/plans/2026-09-11-hamilton-dag-e2e-evidence.md` for the published-output
  baseline (row counts × columns) and timing evidence. The final "flip doc to
  Completed" step is gated on the remaining phases.

## Session facts the next thread needs

- **Entrypoint:** `uv run python main.py --stage all` (no `PYTHONPATH` —
  `[build-system]` hatchling added; `uv sync` installs editable). Runbook:
  `docs/guides/operations-runbook.md`.
- **NEVER clear `data/cache`** (OneMap search cache + `hamilton/` result store).
  `scripts/99_cleanup.py` clears everything — only for intentional cold runs.
- **Serial execution is the deliberate default.** Parallel benchmark gate NOT
  met (I/O-bound variance dominates; V2 driver requires
  `allow_experimental_mode`) — evidence in the 2026-09-11 evidence doc.
- **pre-commit must pass `--all-files`** (CI runs it). ruff hooks are
  `types: [python]`-filtered; prettier formats markdown tables; `bun.lock` is
  excluded; detect-secrets uses `.secrets.baseline` + one inline pragma in
  ci.yml (fake test credential).
- **pip-audit is volatile** — advisories landed mid-session. If CI security
  fails: `uv lock --upgrade-package <pkg> && uv sync && uv run pip-audit
--skip-editable`, then commit the lock.
- **Host clock jumped ~9h once** — trust file mtimes + `/usr/bin/time` over
  log timestamps. NTP still not configured.
- **Warm full run:** ~1:12–1:14 wall via CLI. A worker subagent TIMED OUT
  during the 27-min cold run — the main thread should own long runs and
  nohup + log them (`/tmp/pipeline_<label>.log`).

## Wave 1 — parallel (small, high value)

### A. Phase 1 fix (items 5–6) — skill: `change-hamilton-pipeline`

Live crash, reproduced on main @ `4eeda3f`:
`uv run python main.py --final-var geocoded_properties` →
`ValueError: Required input writer not provided for nodes: [24 materializer nodes]`.

- Fix `src/egg_n_bacon_housing/pipeline.py:284-287`: gate the
  quarantine-companion loop (`execution_vars.append(_QUARANTINE_MAP[name])`)
  on `writer is not None`. Do NOT touch the `materialization_targets`
  extension (it already implies writer exists).
- Tests per roadmap item 6: give `DummyDriver` in `tests/test_pipeline.py`
  `list_available_variables()` + `what_is_upstream_of()` stubs; assert
  `run_pipeline(..., final_vars=["geocoded_properties"])` runs with no writer
  input and writes no parquet; one real-driver integration test.
- Verify: `uv run pytest tests/test_pipeline.py tests/test_pipeline_integration.py
tests/test_dag_smoke.py --no-cov -q` + the live repro command exits 0 +
  `ruff`/`mypy`/docs validators.

### B. Phase 0 bookkeeping (items 1–4) — no skill

- Mark `docs/plans/2026-04-28-code-audit-findings.md` `Status: Superseded`
  (→ src-audit program) and `docs/plans/2026-09-07-src-audit-improvement-
program.md` `Status: Completed` (note deferred item: quarantine-only persist
  mode). Add status note to `docs/plans/2026-09-03-runtime-dependency-
injection-handoff.md` (already has a Status line — extend it: compat-wrapper
  removal landed 2026-09-11, see evidence doc).
- Baseline capture (item 4) is satisfied by the evidence doc — link it.
- Annotate the roadmap's done items (list above) as verified-done 2026-09-11.

### C. Phase 2 dead code (items 7, 9, 10, 11) — skills: both

- Item 7: delete repo shims `utils/mrt_line_mapping.py:302-366` (6 `_repository`
  refs) and `utils/school_features.py:99-123` (2 refs; `_load_reference_data`,
  `load_school_tiers`); move `get_station_score`'s test to the repository;
  tests construct repositories directly.
- Item 9: remove `supply_pipeline` from `components/ingestion/macro.py`
  (5 refs: `_MACRO_SOURCES` entry + transform); retire bronze artifact +
  catalog row (`uv run python scripts/generate_catalog.py` then
  `scripts/tools/check_catalog.py`); check `docs/data-sources.md`.
- Item 10: dead symbols — `_is_null_scalar` (`utils/validation.py:17-29`,
  currently test-only usage), `_PUBLISHED_LAYERS` alias (`pipeline.py:97`;
  real consumers in `tests/test_pipeline.py`, `utils/layer_writer.py` —
  migrate them), `ura_csv.py` `unit_price_psf/psm` (verify catalog/docs silent).
- Item 11: purge orphaned `__pycache__` (root + `tests/` pyc for deleted sources).
- Wave-A/B agents touch pipeline.py/tests too — coordinate: this agent owns
  `utils/`, `components/ingestion/`, `docs/data-sources.md` only.

## Wave 2 — parallel (medium)

### D. Phase 3 item 12 — shared retry policy — skill: `change-data-ingestion`

`adapters/_http.py` already owns Retry-After parsing; the three adapters never
adopted it (`adapters/ura.py` has zero `_http` usage; retries permanent 4xx,
ignores Retry-After). Refactor `ura.py:71-79`, `datagovsg.py:47-61`,
`onemap.py:155` onto one transient-only policy (429/5xx/network, Retry-After
honored, single `MAX_RETRY_AFTER_WAIT`). Add `resource_url()` to datagovsg;
use at `datagov.py:36`, `macro.py:40`, `geojson.py:394`. Mocked-transport
tests incl. URA permanent-4xx fail-fast + Retry-After. Update failure-policy
records in `docs/guides/data-ingestion-development.md`.

### E. Phase 3 items 13, 15, 17 — helpers — skills: both

- 13: consolidate `_haversine_metres` (`utils/school_features.py:460-470` vs
  `utils/proximity.py:23-33`) into `utils/geo.py` (`haversine_metres` public);
  unify macro quarter parsing (`macro.py:295-311` lenient vs `:322-352` strict)
  onto strict + malformed-quarter fixture; extract geojson point/centroid
  helper (`geojson.py:112-125,156-168`).
- 15: add `merge_town_context()` to `utils/hdb_lookups.py`; refactor
  `feature_transactions.py:287-314` + `feature_profiles.py:171-201`; fixture
  equivalence test.
- 17: replace `features.py:21` private `_geocode_schools` import with a public
  API in its home module.

### F. Phase 4 items 18–20 — tests — skills: both

- 18: new `tests/test_cache_fingerprints.py` (key stability, input
  sensitivity, round-trip).
- 19: tests for `utils/contracts.py:4` `require_columns` and
  `utils/data_loader.py:110-127` polygon-overlap `keep="first"`.
- 20: bronze staleness gates for `raw_hdb_rental` + `raw_rental_index`
  (`utils/bronze.py:77-81`); fix overstated docstrings at `bronze.py:344-352`;
  per-dataset stale-gate tests.

## Wave 3 — parallel (the big ones)

### G. Phase 5 item 22 — sampled validation — skill: `change-hamilton-pipeline`

Decision already made (owner, 2026-09-10): default flips `"full"` → `"sample"`
(`config.py:23`, `feature_transactions.py:137`, `export.py:31`). Requirements
a–e per roadmap: extend `vectorized_precheck` (`validation_gateway.py:66-105`)
with datetime bounds (`transaction_date ge 1990`) + string `min_length` (it
currently has neither — verified); fix sample-mode double-count at
`validation_gateway.py:124` (sampled rejects land in both valid frame and
quarantine); keep `full`/`fail` env-selectable; resolve `export.py:29-64`
re-validation (drop or route through gate); update `.env.example` + docs.
Note: with this, quarantine volumes in a warm run will CHANGE — re-baseline
the evidence-doc row counts and re-run `check_catalog.py`.

### H. Phase 5 items 23–24 — skill: `change-hamilton-pipeline` / `change-data-ingestion`

- 23: `feature_transactions.py:108,188,224-226` — derive `month` once, kill 2
  full ~1M-row copies + the no-op round trip at 224-227; equivalence test
  (values + row order).
- 24: `geojson.py:509-528` — parse the 9 amenity GeoJSONs once into bronze
  parquet (raw JSON stays source of truth); document normalization in the
  source record.

### I. Phase 3 items 14/16 + Phase 4 item 21 — consolidation — skill: `change-hamilton-pipeline`

- 14-remainder: extract `manifest_age_days()` shared by `utils/bronze.py:148-170`
  and `scripts/40_refresh_rolling.py:73-99`; update the bronze-cache sentence
  in `.agents/skills/change-data-ingestion/SKILL.md`; re-run
  `validate_agent_skills.py`.
- 16: replace the 24 hand-written nodes in `components/materialization.py:11-196`
  with `@parameterize` families driven by `PUBLISHED_OUTPUTS`. Constraints:
  emitted variable names byte-identical to today's `materialize_*`; the three
  maps + `STAGE_VARS` unchanged; warm-run output equivalence check; update
  `docs/guides/pipeline-development.md`.
- 21 (last): raise CI floor `--min-coverage 60` → `70` (`.github/workflows/ci.yml:75`)
  once Waves 1–3 tests land.

## Final wave — Phase 7 closeout (items 28–29)

Owner or single agent: full warm run (`uv run python main.py --stage all`;
the roadmap's `dotenvx` wrapper is obsolete — removed); compare published
outputs against the evidence-doc baseline (tolerate expected changes from
Wave G quarantine/volume shifts — document deltas); regen catalog + check;
full V-all; `pre-commit run --all-files`; `uv run pip-audit --skip-editable`.
Flip the roadmap to `Status: Completed`; refresh `docs/plans/README.md` index;
append an evidence section to the 2026-09-11 evidence doc.

## Subagent playbooks (validated this session)

- Dispatch `worker` agents in parallel waves with DISJOINT file ownership;
  state the owned paths explicitly in each brief.
- Every code-touching brief MUST start with "Read `.agents/skills/<skill>/SKILL.md`
  FIRST and follow its checklist" + the skill's verification commands.
- Briefs need exact file:line anchors, the do-not-touch list, "no commits",
  and a report format (files changed, test/lint results).
- Long-running pipeline work: main thread, nohup + `/usr/bin/time -v`, poll
  the log; never let a subagent own a cold/geocoding run.
- After each wave: main thread runs the full gate
  (`pytest -q --no-cov`, `ruff`, `format --check`, `mypy`, both validators,
  `git diff --check`) before starting the next wave.

## Acceptance criteria for this handoff

- Phase 1 crash fixed with regression tests; live repro command exits 0.
- Roadmap items ticked verified-done or implemented; roadmap flipped to
  `Status: Completed` with Phase 7 evidence appended.
- CI + Deploy stay green on every pushed commit; suite ≥ 753 passing;
  coverage floor 70 green; catalog + docs-layout + agent-skills validators clean.
- Serial execution unchanged; caches never cleared except deliberate cold runs.
