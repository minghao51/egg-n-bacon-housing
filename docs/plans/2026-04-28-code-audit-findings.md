# Code Audit Findings — 2026-04-28

Scope: commits `4dde6da`..`3241b8a` (last 5 commits), covering the Hamilton DAG refactor, HDB rental ingestion, mall geocoding, rental yield rewrite, schema relaxation, and data loader migration.

## Summary

| Severity | Count |
|----------|-------|
| Critical | 3 |
| High | 6 |
| Medium | 7 |
| Low | 5 |

All 42 existing tests pass. Ruff and mypy (components) are clean. The issues below are all in untested paths or logic gaps that the current test suite does not cover.

---

## Critical

### C1 — Broken `mock_config` fixture references stale Settings API

**File:** `tests/conftest.py:86-105`

The `mock_config` fixture sets `settings.DATA_DIR`, `settings.PIPELINE_DIR`, `settings.PARQUETS_DIR`, `settings.CACHE_DIR`, `settings.MANUAL_DIR`. None of these attributes exist on the current `Settings` class (it uses computed `@property` methods: `data_dir`, `bronze_dir`, `silver_dir`, `gold_dir`, `platinum_dir`).

Any test that uses this fixture will crash with `AttributeError`. It is currently dead code (no test imports it) but is a landmine for future development.

**Fix:** Rewrite the fixture to monkeypatch the `Settings` properties or delete it if unused.

---

### C2 — `pct_change(3)` and `pct_change(12)` assume contiguous monthly rows

**File:** `src/egg_n_bacon_housing/components/05_metrics.py:183`

The appreciation hotspot computation uses positional `pct_change(3)` and `pct_change(12)` without verifying the `month` column is actually contiguous. If a planning area has gaps (missing months), lag-3 computes 3 rows back rather than 3 months back, producing incorrect appreciation percentages.

**Fix:** Resample to monthly frequency before computing positional lags (e.g., `.asfreq("M")` on a DateTimeIndex), or use date-aware differencing.

---

### C3 — Wrong config field used for geocoding cache duration

**File:** `src/egg_n_bacon_housing/adapters/onemap.py:149`

```python
cached_call(cache_id, _fetch_from_api, duration_hours=settings.geocoding.timeout_seconds)
```

`timeout_seconds` is `30` and the parameter name is `duration_hours`. The cache expires in 30 hours by coincidence. This is a semantic bug — the wrong config field is used.

**Fix:** Replace with `settings.pipeline.cache_duration_hours` or add a dedicated `geocoding.cache_duration_hours` config field.

---

## High

### H1 — Hardcoded median household income

**File:** `src/egg_n_bacon_housing/components/05_metrics.py:145`

```python
estimated_income = 85000
```

The sole affordability metric uses a hardcoded income figure. Should be configurable and ideally vary by year.

**Fix:** Move to `config.yaml` or a reference data file.

---

### H2 — Silent fallback to hardcoded `"2025-01"` month

**File:** `src/egg_n_bacon_housing/components/05_metrics.py:44, 93, 134`

When neither `month` nor `transaction_date` columns exist, every row gets `"2025-01"`. This silently corrupts all downstream monthly aggregations.

**Fix:** Raise `ValueError` or log an error and return an empty DataFrame.

---

### H3 — `print()` instead of `logging` in OneMap adapter

**File:** `src/egg_n_bacon_housing/adapters/onemap.py:50-86`

Six `print()` calls in `setup_onemap_headers()` bypass the logging subsystem. These cannot be silenced or redirected in production.

**Fix:** Replace all `print()` with `logger.info()` / `logger.warning()`.

---

### H4 — No retry on OneMap authentication token request

**File:** `src/egg_n_bacon_housing/adapters/onemap.py:67-87`

The token-fetch POST has no retry logic. A transient network error during auth kills the entire pipeline, even though the downstream `fetch_data` function uses tenacity retries.

**Fix:** Wrap the auth POST in a `@retry` decorator or tenacity retry block.

---

### H5 — Misleading PSF fallback in export

**File:** `src/egg_n_bacon_housing/components/04_export.py:108`

```python
"avg_psf": float(subset.get("psf", subset["price"] / 1000).median()),
```

`DataFrame.get()` returns a Series. The fallback `price / 1000` is an arbitrary number that silently masks missing PSF data — it is not a meaningful PSF value.

**Fix:** Use `np.nan` as the fallback instead of `price / 1000`.

---

### H6 — Cache never stores falsy results

**File:** `src/egg_n_bacon_housing/utils/cache.py:195`

```python
if cached_value is not None:
    return cached_value
```

If the cached function returns an empty DataFrame, `None`, `{}`, or `0`, the cache never hits — the function re-executes every call.

**Fix:** Use a sentinel object (`_MISSING = object()`) instead of `is not None` for cache-hit detection.

---

## Medium

### M1 — Rows with NaN coordinates silently dropped in MRT distance

**File:** `src/egg_n_bacon_housing/utils/mrt_distance.py:153-161`

Properties with NaN lat/lon are dropped from the output DataFrame. Downstream consumers have no way to know rows were removed.

**Fix:** Return all original rows, setting `dist_to_nearest_mrt` to `NaN` for un-geocoded properties instead of dropping them.

---

### M2 — `logging.basicConfig` at module level overrides root logger

**File:** `src/egg_n_bacon_housing/utils/school_features.py:23`

`logging.basicConfig(level=logging.INFO)` runs on import, overriding any logging configuration set by the importing module or tests.

**Fix:** Remove the `basicConfig` call. The application entry point should configure logging.

---

### M3 — `run_appreciation_analysis` references non-existent column

**File:** `src/egg_n_bacon_housing/components/06_analytics.py:107-113`

The function references `appreciation_3m_pct` which only exists in the `appreciation_hotspots()` output. It returns an empty dict when called with the standard metrics input.

**Fix:** Either wire the function to the correct upstream DAG node or fix the column reference.

---

### M4 — `save_analytics_report` is dead code in the DAG

**File:** `src/egg_n_bacon_housing/components/06_analytics.py:118-136`

The function expects a dict called `analytics_results` but no DAG node produces this variable. It can never execute through the Hamilton pipeline.

**Fix:** Either wire it properly or remove it.

---

### M5 — `duration_hours=0` treated as cache miss

**File:** `src/egg_n_bacon_housing/utils/cache.py:192`

```python
duration = duration_hours or settings.pipeline.cache_duration_hours
```

Passing `duration_hours=0` (intending no cache) is falsy and falls back to the 24-hour default.

**Fix:** Use `duration_hours if duration_hours is not None else settings.pipeline.cache_duration_hours`.

---

### M6 — Dead `fetch_fn` parameter in datagovsg adapter

**File:** `src/egg_n_bacon_housing/adapters/datagovsg.py:169`

`save_datagovsg_dataset` accepts a `fetch_fn` parameter but never calls it — it uses `fetch_datagovsg_dataset` directly.

**Fix:** Remove the unused parameter.

---

### M7 — Unmatched schools get `quality_score=0.0`

**File:** `src/egg_n_bacon_housing/utils/school_features.py:510-520`

All unmatched schools receive `quality_score=0.0`. Properties near only unmatched schools get an artificially low accessibility score.

**Fix:** Use `np.nan` or a separate `quality_score_available` flag.

---

## Low

| # | File | Issue |
|---|------|-------|
| L1 | `04_export.py:112` | Local variable `segments_data` shadows the function name. Harmless but confusing. |
| L2 | `05_metrics.py:148-155` | Affordability thresholds (`<5`, `<7`, `<9`) hardcoded. Should be configurable. |
| L3 | `school_features.py:680` | Accessibility weights `0.4/0.6` for primary/secondary hardcoded. |
| L4 | `mrt_distance.py`, `school_features.py` | `__main__` blocks in library code. Should be scripts. |
| L5 | `04_export.py:63` | `pd.Timestamp.now().isoformat()` is timezone-naive. |

---

## Test Coverage Gaps

The following modules have **zero test coverage**:

| Module | Risk |
|--------|------|
| `components/05_metrics.py` | High — affordability income, appreciation hotspots, rental yield metrics |
| `components/06_analytics.py` | Medium — analytics wiring, dead code |
| `adapters/onemap.py` | High — auth flow, retry, caching |
| `adapters/datagovsg.py` | Medium — pagination, rate limiting |
| `utils/cache.py` | High — falsy-value cache bug |
| `utils/mrt_distance.py` | Medium — row dropping |
| `utils/school_features.py` | Medium — quality scores, KDTree |
| `pipeline.py` | Low — DAG build, import failure |

**Recommended test priority:** `05_metrics.py` → `cache.py` → `onemap.py` → `mrt_distance.py`

---

## Proposed Remediation Order

1. Fix `mock_config` fixture (C1) — prevents future test breakage
2. Fix `pct_change` time-gap issue (C2) — data integrity
3. Fix cache duration config field (C3) — data freshness
4. Fix falsy-value cache bug (H6) — performance and correctness
5. Replace `print()` with `logger` (H3) — observability
6. Fix PSF fallback (H5) — metric accuracy
7. Add tests for `05_metrics.py` — covers H1, H2, and C2
8. Make hardcoded values configurable (H1, L2, L3)
9. Add auth retry (H4) — resilience
10. Clean up dead code (M4, M6) — maintainability
