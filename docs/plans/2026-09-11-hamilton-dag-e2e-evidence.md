# Hamilton DAG — Credentialed E2E Evidence (2026-09-11)

**Host:** local dev host, serial Hamilton execution, `PYTHONPATH=src uv run python main.py --stage all`
(the documented entrypoint; `uv sync` does not install this checkout as importable).
Credentials loaded from the local ignored `.env` (OneMap token obtained fresh; never printed).

> Note: the host clock jumped forward roughly nine hours between RUN1b (log
> timestamps ~00:23) and RUN1c (~09:25). File mtimes and `/usr/bin/time`
> elapsed values are authoritative below; log-line wall times are not
> comparable across that boundary.

## Run inventory

| Run | Label | Exit | Wall clock | Notes |
| --- | --- | --- | --- | --- |
| RUN1 (23:18–00:15) | resumed-cold attempt | 1 | 27:48.01 | crashed in `CacheManager.get()` TOCTOU; cache retained |
| RUN1b | resumed-cold | 0 | 4:14.70 | geocoding cache mostly warm; **pre-fix CLI**: only 7/12 outputs |
| RUN1c | first-warm (post-fix) | 0 | 3:09.96 | **all 12 outputs**; first fully correct E2E |
| WARM2 | second-warm | 0 | 1:13.90 | all 12 outputs |
| WARM3 | third-warm | 0 | 1:12.18 | all 12 outputs |
| RECREATE | deletion-recovery | 0 | 1:12.47 | town_360.parquet deleted pre-run; recreated |

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
