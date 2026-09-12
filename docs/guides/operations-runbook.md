# Operations Runbook

Verified operating procedure for full pipeline runs, from the credentialed E2E
evidence in `docs/plans/2026-09-11-hamilton-dag-e2e-evidence.md` (context and
history: `docs/plans/2026-09-10-hamilton-dag-next-thread-handoff.md`).

## Entrypoint

```bash
uv sync                          # one-off: installs the project editable
uv run python main.py --stage all   # supported production entrypoint
```

`main.py --stage all` works without `PYTHONPATH=src`: the project now has a
hatchling `[build-system]`, so `uv sync` installs `egg_n_bacon_housing`
(editable). Do not add a parallel runner or ad-hoc persistence path.

## Credentials

Load from the local, git-ignored `.env` (template: `.env.example`). Never print
or commit `.env` or any secret.

| Purpose                         | Variables                                                                               |
| ------------------------------- | --------------------------------------------------------------------------------------- |
| OneMap geocoding                | `ONEMAP_EMAIL`, `ONEMAP_EMAIL_PASSWORD`, `ONEMAP_TOKEN`                                 |
| URA live condo fetch (optional) | `URA_API_ACCESS_KEY`                                                                    |
| Cloudflare R2 manual data       | `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_ENDPOINT` |

## Large-table validation policy

`PIPELINE__LARGE_TABLE_VALIDATION_POLICY` selects how the ~1M-row gold
(`transactions_enriched`) and platinum (`unified_dataset`) boundaries validate
rows against their pydantic contracts:

| Policy   | Behavior                                                                                                                                                                                                                                                                                                                    |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sample` | **Default.** A 100%-coverage vectorized pre-check (required-field nulls, numeric/datetime bounds, string min-length — all read from the pydantic models) plus a deterministic 10k-row pydantic spot-check. Sampled rejects are quarantined and dropped from the published frame; the exact unvalidated row count is logged. |
| `full`   | Every row validated in deterministic chunks; rejects quarantined with per-row reasons. Proves the whole table against the contract.                                                                                                                                                                                         |
| `fail`   | Like `full`, but the run raises on any invalid row instead of persisting. Strictest option.                                                                                                                                                                                                                                 |

Quarantine writes are run-scoped
(`<layer>/_quarantine/<dataset>/<run_id>.parquet`) and excluded from quality
baselines under every policy, so switching policies never silences rejects —
it only changes whether unsampled rows go through pydantic.

Cold runs and CI should prove the full contract: set `full` (or `fail` for a
hard gate) before running, e.g.
`PIPELINE__LARGE_TABLE_VALIDATION_POLICY=fail uv run python main.py --stage all`.
The warm default `sample` trades unsampled-row pydantic validation for the
vectorized pre-check; its quarantine volumes can legitimately differ from a
`full` run, so do not compare quarantine counts across policies.

## Execution contract: serial by default

Serial Hamilton execution is deliberate, not incidental. Warm-cache in-process
benchmark (`run_pipeline()`, builder mirroring `build_pipeline()`):

| Variant                        | Wall clock (repeated trials) |
| ------------------------------ | ---------------------------- |
| v1 production (serial)         | 87.95s / 23.82s / 34.86s     |
| v2 driver, serial              | 55.33s / 29.44s / 25.56s     |
| v2 + MultiThreadingExecutor(4) | 40.95s                       |
| v2 + MultiThreadingExecutor(8) | 34.62s / 39.19s              |

Run-to-run variance within a variant exceeds any between-variant delta:
materialization rewrites ~12 parquet outputs (incl. the 1.2M-row
`unified_dataset`) every run, so the workload is I/O-bound and page-cache state
dominates. Parallel also requires
`enable_dynamic_execution(allow_experimental_mode=True)` (experimental in
Hamilton 1.89). An initial 2.4× "parallel speedup" was a run-order warm-up
artifact.

**Decision: the ≥20% stable end-to-end improvement gate is NOT met — do not
enable parallel execution without re-benchmarking** (and only after Hamilton
promotes the V2 driver out of experimental and materialization I/O is separated
from compute).

## Cache rules

- `data/cache/` holds the OneMap search cache (thousands of hashed parquet
  entries) and `data/cache/hamilton/` holds the Hamilton result store.
- **Never clear caches unless intentionally measuring a cold run.**
  `scripts/99_cleanup.py` clears everything — dangerous before a credentialed
  run: cold geocoding of ~11.6k unique addresses is rate-limited and can take
  tens of minutes. Interrupted runs resume from cache with the same command.
- Bronze caches only expire via `--refresh` (below).

## Expected timings

| Scenario                                   | Wall clock                     |
| ------------------------------------------ | ------------------------------ |
| Resumed-cold (geocoding cache mostly warm) | ~4m15s                         |
| Warm, via CLI (`--stage all`)              | ~1m12s–1m14s                   |
| In-process (`run_pipeline()`), warm        | ~24–88s (page-cache dependent) |

## Verification after each full run

A successful `--stage all` run (exit 0) must produce:

1. **Exactly 12 published outputs** (fresh mtimes, LayerWriter "Saved" lines):

   | Layer    | Outputs (rows in evidence run)                                                                                                                           |
   | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | Silver   | `hdb_validated` (985,670), `condo_validated` (231,639), `geocoded_validated` (1,217,309)                                                                 |
   | Gold     | `rental_yield` (3,473), `location_dim` (11,454), `transactions_enriched` (1,205,504), `planning_area_360` (44), `town_360` (28), `block_profile` (9,866) |
   | Platinum | `unified_dataset` (1,205,504), `pa_monthly_metrics` (13,244), `appreciation_hotspots` (20)                                                               |

2. **Exactly six terminal frames returned:**
   `unified_dataset` (1,205,504 × 97), `planning_area_360` (44 × 27),
   `town_360` (28 × 13), `block_profile` (9,866 × 6),
   `pa_monthly_metrics` (13,244 × 11), `appreciation_hotspots` (20 × 6).

3. **Run-scoped quarantine** under
   `data/pipeline/03_gold/_quarantine/<boundary>/<run-id>_<uuid>.parquet`
   (observed: `transactions_enriched`). Inspect the source identity / rejection
   reason columns; rejected rows are recorded, never silently dropped.

## Published-output recovery

Deleting a published parquet and rerunning the same request recreates it
deterministically from cached computation — verified byte-identical sha256 —
without clearing unrelated caches (hamilton store 59 → 59, source cache
14,001 → 14,001 in the evidence run). Do not clear the full cache to "fix" a
missing output.

## Post-run sequence

```bash
uv run python scripts/generate_catalog.py
uv run python scripts/tools/check_catalog.py
cd app && bun install --frozen-lockfile && bun run build
```

Bun is pinned via `app/.bun-version` (currently 1.2.23).

## Cache refresh

`--refresh` invalidates caches before running so sources are re-fetched:

| Invocation          | Effect                                                                                         |
| ------------------- | ---------------------------------------------------------------------------------------------- |
| `--refresh`         | Everything: bronze parquets + DAG + API caches                                                 |
| `--refresh PATTERN` | Glob matched against bronze paths, e.g. `--refresh raw_hdb_resale` or `--refresh 'external/*'` |

## Known issues / benign artifacts

- **Interrupted (Ctrl-C) runs** may emit a cache-hook assertion during Hamilton
  shutdown — benign; cache entries are written per key and the run resumes from
  cache.
- **76 Hamilton-internal DeprecationWarnings (`ast.Str`)** — library-side;
  track sf-hamilton upgrades rather than patching locally.
- **Host clock should run NTP.** A ~9h clock jump during verification corrupted
  log timestamps (file mtimes and measured elapsed times remained trustworthy).
