# WS-A4 — Pacing reservation and refresh retry (CORE-6, CORE-5)

**Severity:** MEDIUM 8 + MEDIUM 9. **Effort:** S. **Wave:** 0.

Two small, independent fixes. Do both in one order; they touch different files.

## 1. Geocoder pacing releases a burst (CORE-6)

`src/egg_n_bacon_housing/utils/geocoding.py:190-197`:

```python
delay = max(0.0, self._next_slot - now)
self._next_slot = now + self._interval
```

Every waiter overwrites `_next_slot` from *its own* arrival time, discarding earlier reservations, so concurrent waiters release together after the first slot.

Probe: `../evidence/core-poc-results.json` → `rate_limiter` (80 ms interval; releases at 0.00000, 0.08011, 0.08019, 0.08021, 0.08029 → 20–80 µs gaps).

**Required change:** reserve the slot, advance from the reservation, then sleep until it.

```python
slot = max(now, self._next_slot)
self._next_slot = slot + self._interval
delay = slot - now
```

Keep the lock scope, keep the `_interval <= 0` fast path, keep "cache hits are never paced".

**Test:** deterministic spacing test — N concurrent waiters with a small interval must have consecutive release gaps ≥ interval (allow a small epsilon for scheduler jitter); assert reservation monotonicity rather than sleeping for real time where possible (inject a clock or patch `time.monotonic`/`time.sleep`). The existing parallel test that replaces `wait()` with a counter does not prove spacing — keep it, add the real one.

**Note:** WS-A1 also edits this file. If WS-A1 has landed, re-read `geocoding.py` before editing and keep both changes; if it has not landed, make this fix now and tell the integrator so A1 rebases on it.

## 2. Failed scheduled refresh becomes a no-op (CORE-5)

`scripts/40_refresh_rolling.py:240-242`:

```python
if args.stale_only and not removed:
    logger.info("Nothing was stale — skipping pipeline rerun (idempotent no-op).")
    return 0
```

`removed` counts deleted parquets. If invalidation deleted the file but the fetch then failed before bronze was rewritten, the next identical run finds nothing to delete and exits 0 without running the pipeline. The dataset stays missing and still selected by `stale_names`.

Probe: `../evidence/core-poc-results.json` → `refresh_retry` (first exit 1, second exit 0, `pipeline_calls=1`, bronze still missing, still stale-selected).

**Required change:** decide the rerun from *selected work*, not *deletions*. Under `--stale-only`, run the pipeline when any selected dataset is stale **or** its parquet is missing. Keep `--dry-run`, `--all`, `--pattern` behaviour and the exit codes unchanged (0 success/no-op, 1 failure, 2 usage).

**Test** (`tests/test_refresh_rolling.py`): two invocations — first with a mocked fetch failure, second with success — assert two pipeline invocations, `stale_names` no longer selects the dataset, and the parquet exists. Add a genuine no-op case (nothing stale, nothing missing) that still exits 0 without running the pipeline.

## Verification

```bash
uv run pytest tests/test_refresh_rolling.py tests/test_onemap.py --no-cov -q
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

## Owns

`scripts/40_refresh_rolling.py`, `tests/test_refresh_rolling.py`; `src/egg_n_bacon_housing/utils/geocoding.py` only for §1 (coordinate with WS-A1).

## Do not touch

`utils/bronze.py` refresh helpers' semantics beyond what §2 requires, sync script, frontend.

## Done when

Spacing is provably spaced under concurrency, a failed refresh retries on the next identical invocation, and the gate passes.
