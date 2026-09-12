# Hamilton DAG — Credentialed E2E Evidence (2026-09-11)

**Host:** local dev host, serial Hamilton execution, `PYTHONPATH=src uv run python main.py --stage all`
(the documented entrypoint; `uv sync` does not install this checkout as importable).
Credentials loaded from the local ignored `.env` (OneMap token obtained fresh; never printed).

> Note: the host clock jumped forward roughly nine hours between RUN1b (log
> timestamps ~00:23) and RUN1c (~09:25). File mtimes and `/usr/bin/time`
> elapsed values are authoritative below; log-line wall times are not
> comparable across that boundary.

## Run inventory

| Run                | Label                 | Exit | Wall clock | Notes                                                           |
| ------------------ | --------------------- | ---- | ---------- | --------------------------------------------------------------- |
| RUN1 (23:18–00:15) | resumed-cold attempt  | 1    | 27:48.01   | crashed in `CacheManager.get()` TOCTOU; cache retained          |
| RUN1b              | resumed-cold          | 0    | 4:14.70    | geocoding cache mostly warm; **pre-fix CLI**: only 7/12 outputs |
| RUN1c              | first-warm (post-fix) | 0    | 3:09.96    | **all 12 outputs**; first fully correct E2E                     |
| WARM2              | second-warm           | 0    | 1:13.90    | all 12 outputs                                                  |
| WARM3              | third-warm            | 0    | 1:12.18    | all 12 outputs                                                  |
| RECREATE           | deletion-recovery     | 0    | 1:12.47    | town_360.parquet deleted pre-run; recreated                     |

## Fixes made during this thread

1. **`main.py` stage passthrough (checklist item 2 blocker).** `main.py`
   pre-resolved `final_vars` from `--stage` before calling `run_pipeline`, so
   `explicit_final_vars` was always true and the `stage="all"` branch that
   materializes all 12 registered outputs never fired from the CLI — only the
   6 terminal materializers ran. Fixed by passing
   `final_vars=args.final_vars, stage=args.stage`; explicit `--final-var`
   still overrides end-to-end. Regression tests:
   `tests/test_pipeline_integration.py::TestMainCLIStagePassthrough`.
2. **`CacheManager` concurrency races.** (a) `_is_expired` crashed with
   `FileNotFoundError` when a concurrent writer replaced an entry between the
   `exists()` probe and `stat()` — now treated as a miss. (b) `_atomic_write`
   used a fixed `.tmp` sibling name, so concurrent writers of one key consumed
   each other's temp file (ENOENT warnings) — tmp names are now
   pid+thread unique. Focused tests in `tests/test_cache.py`.

## Verification results (RUN1c–RECREATE)

- **12 published outputs materialized** (LayerWriter "Saved" lines, fresh
  mtimes): silver `hdb_validated` (985,670), `condo_validated` (231,639),
  `geocoded_validated` (1,217,309); gold `rental_yield` (3,473),
  `location_dim` (11,454), `transactions_enriched` (1,205,504),
  `planning_area_360` (44), `town_360` (28), `block_profile` (9,866);
  platinum `unified_dataset` (1,205,504), `pa_monthly_metrics` (13,244),
  `appreciation_hotspots` (20).
- **Exactly six terminal frames returned:**
  `unified_dataset (1,205,504 × 97)`, `planning_area_360 (44 × 27)`,
  `town_360 (28 × 13)`, `block_profile (9,866 × 6)`,
  `pa_monthly_metrics (13,244 × 11)`, `appreciation_hotspots (20 × 6)`.
- **Run-scoped quarantine:** each successful run wrote
  `03_gold/_quarantine/transactions_enriched/<run-id>_<uuid>.parquet`
  (rejected rows with source identity/reason, e.g. 11,805 rows in RUN1b).
- **Cache-reuse vs execution (WARM3):** 32 result-store hits vs 55 executed
  nodes. Ingestion re-executed (`raw_hdb_resale_transactions::adapter::execute_node`,
  `raw_condo_transactions::adapter::execute_node`); expensive transforms were
  reused (`geocoded_properties::result_store::get_result::hit`,
  `transactions_enriched::result_store::get_result::hit`); all materializers
  executed (`materialize_rental_yield::adapter::execute_node`, …), consistent
  with `build_pipeline`'s `disable=(materializers + quarantines + ingest)`.
- **Deleted-file recreation path:** `03_gold/town_360.parquet` (sha256 prefix
  `3acf640a7be105d4`) deleted, same request rerun → recreated in 1:12.47 with
  byte-identical sha256; `data/cache/hamilton` file count 59 → 59 (Δ0) and
  source-cache file count 14,001 → 14,001 (Δ0) — unrelated cached nodes were
  not cleared.
- **Catalog follow-up (item 5):** fresh `rental_yield.parquet` physical schema
  is `[town, month, median_price, median_rent, rental_yield_pct, sample_size,
property_type, flat_type, rental_index]` — no `flat_type_count`. Regenerated
  `data/catalog/catalog.jsonl` has zero `flat_type_count` rows;
  `scripts/tools/check_catalog.py` passes (4 layers, 2333 edges). Three
  orphaned old-named silver artifacts (`cleaned_hdb_transactions`,
  `cleaned_condo_transactions`, `validated_geocoded_properties`) were removed
  and the catalog regenerated (117 datasets).
- **Parallel-execution gate:** not benchmarked; serial execution remains the
  default per the handoff rule (no parallel run enabled anywhere).

## Parallel work completed in the same thread

- Pinned **Bun 1.2.23** installed; `cd app && bun install --frozen-lockfile`
  (559 packages) and `bun run build` succeeded (148 pages, `app/dist/` 20 MB,
  256 files).
- Legacy test-facing `writer=` kwargs shim removed from the six compute-node
  facades + tests; full suite 748 passed; ruff/format/mypy/docs/skills clean.
- Historical `L5` / compatibility-API references audited: decision is to keep
  them as archival history (active docs clean; archive READMEs already frame
  them as superseded). No edits needed.

## Parallel-execution gate (isolated benchmark, 2026-09-11)

Warm-cache, in-process benchmark via `run_pipeline()` on a builder mirroring
`build_pipeline()` (same modules/validator/cache+disable set):

| Variant                        | Wall clock (repeated trials) |
| ------------------------------ | ---------------------------- |
| v1 production (serial)         | 87.95s / 23.82s / 34.86s     |
| v2 driver, serial              | 55.33s / 29.44s / 25.56s     |
| v2 + MultiThreadingExecutor(4) | 40.95s                       |
| v2 + MultiThreadingExecutor(8) | 34.62s / 39.19s              |

Run-to-run variance within a single variant is larger than any
between-variant delta: materialization rewrites ~12 parquet outputs
(incl. 1.2M×97 unified_dataset) each run, so the warm workload is I/O-bound
and page-cache state dominates. An initial 2.4× "parallel speedup" was a
run-order warm-up artifact. Parallel also requires
`enable_dynamic_execution(allow_experimental_mode=True)` (Hamilton 1.89
flags this experimental). Determinism held: all runs returned identical
frame shapes and byte-identical published parquets (town_360 sha256
`3acf640a…` stable across every serial and parallel run).

**Decision: the ≥20% stable end-to-end improvement gate is NOT met — serial
execution remains the default.** Revisit only after (a) Hamilton promotes
the V2 driver out of experimental, and (b) materialization I/O is separated
from compute in any future benchmark.

## Remaining caveats

- ~~The `uv sync` packaging gap~~ — **resolved 2026-09-11:** the checkout lacked
  a `[build-system]` table, so uv treated it as a virtual (non-package)
  project and never installed `egg_n_bacon_housing` itself. Adding the
  hatchling build backend makes `uv sync` install the project (editable);
  `uv run python main.py --stage all` now works without `PYTHONPATH=src`
  (verified: exit 0 warm run, 98.65 s). Tests were unaffected all along via
  pytest's `pythonpath = ["src"]`.
- Quarantine/retention/atomic-write/anomaly-ordering/`pipeline_as_of_date`
  invalidation behaviors are demonstrated by the hermetic test suite
  (752 passing), not re-proven individually in the credentialed run.

---

## Closeout run — code-audit remediation final wave (2026-09-12)

All remediation-roadmap waves (1–3 + final) landed; this run re-baselined the
published outputs on the final tree (`994` tests passing, coverage floor 70).

**Run configuration:** `uv run python main.py --stage all` — a full DAG
recompute, not a warm cache-hit run: the targeted refresh smoke (item 28)
cleared the Hamilton result cache and all four rolling bronze sources
(pre-manifest bronze counts as stale), so the run re-fetched rolling data and
re-executed the geocoding loop against warm OneMap API caches.
`/usr/bin/time -v`: **wall 1:22:53, peak RSS ≈ 5.8 GiB, exit 0**, six terminal
frames (shapes logged by `main.py`).

**Fresh rolling fetches (vs. the 2026-09-11 baseline bronze):**
raw_hdb_resale 986,548 (+878) · raw_condo_transactions 247,050 (+15,411) ·
raw_hdb_rental 209,852 · raw_rental_index 520 · `external/BusStops` re-parsed
(5,205) via `--refresh external/BusStops`.

**Published outputs (rows × cols; cols unchanged everywhere):**

| Output                         | 2026-09-11 baseline | 2026-09-12 closeout | Delta                                       |
| ------------------------------ | ------------------- | ------------------- | ------------------------------------------- |
| silver/hdb_validated           | 985,670 × 17        | 986,548 × 17        | +878 (fresh resale)                         |
| silver/condo_validated         | 231,639 × 26        | 247,050 × 26        | +15,411 (fresh URA window)                  |
| silver/geocoded_validated      | 1,217,309 × 37      | 1,233,598 × 37      | +16,289 (= 986,548 + 247,050)               |
| gold/transactions_enriched     | 1,205,504 × 97      | 1,233,496 × 97      | +27,992 (fresh data − 102 precheck rejects) |
| gold/location_dim              | 11,454 × 48         | 11,457 × 48         | +3                                          |
| gold/rental_yield              | 3,473 × 9           | 3,498 × 9           | +25 (fresh rental data)                     |
| gold/block_profile             | 9,866 × 6           | 10,007 × 6          | +141                                        |
| gold/planning_area_360         | 44 × 27             | 44 × 27             | 0                                           |
| gold/town_360                  | 28 × 13             | 28 × 13             | 0                                           |
| platinum/unified_dataset       | 1,205,504 × 97      | 1,233,405 × 97      | +27,901 (= enriched − 91 rejects)           |
| platinum/pa_monthly_metrics    | 13,244 × 11         | 13,285 × 11         | +41                                         |
| platinum/appreciation_hotspots | 20 × 6              | 20 × 6              | 0                                           |

All deltas reconcile arithmetically: fresh upstream data plus the **sampled
validation flip** (roadmap item 22) — quarantine volumes are now the
vectorized-precheck rejects (gold 102 rows; platinum unified 91 rows) instead
of the full-pydantic rejects (~11.8k in the baseline era), and sampled rejects
are dropped from published frames. This row-count set is the new baseline.

**Closeout gates (all green):** `pytest -q --no-cov` 994 passed · coverage 95%
total, CI floor raised 60→70 · ruff/format/mypy clean · docs-layout +
agent-skills validators clean · catalog regenerated (4 layers, 125 datasets,
2,333 edges) + `check_catalog.py` · `pre-commit run --all-files` all hooks
passed · `pip-audit --skip-editable` no vulnerabilities.
