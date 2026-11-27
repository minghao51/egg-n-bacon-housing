# WS-A1 — Cached geocode metadata contract (CORE-1)

**Severity:** HIGH (4×4 = 16). **Effort:** M. **Wave:** 1. **Skill:** `change-data-ingestion`.

## Problem

The warm-cache branch of the OneMap geocoder returns coordinates only, stitched onto an "empty" metadata row whose `address` is the _query_, not OneMap's matched address. Condo project plausibility is then judged from `matched_name`/`address`, so the warm path compares the query with itself and accepts results the cold path rejects.

- `src/egg_n_bacon_housing/utils/geocoding.py:340-345` — cache hit returns `{**self._empty_row(addr), "lat": …, "lon": …}`.
- `src/egg_n_bacon_housing/utils/geocoding.py:299-317` — `_row_from_result` (full metadata) vs `:306-315` `_empty_row`.
- `src/egg_n_bacon_housing/components/cleaning.py:418-444` — `_accept_plausible_project_coords` consumes `matched_name`/`address` via `plausible_project_match`.
- Probe: `../evidence/core-poc-results.json` → `cache_plausibility` (cold rejects, warm accepts; warm `matched_name=null`).

## Required change

1. Make the cache carry the same row shape the API path produces. Preferred: cache the matched row set (or a compact record) and reconstruct through one shared conversion function so both paths call the same code.
2. `query_geocode_cache` must return more than a coordinate tuple, or the `lat`/`lon`-only cache must be upgraded with a versioned key so old coordinate-only entries are treated as misses rather than silently reused.
3. Keep backward compatibility for existing cache files where safe, but never fabricate `address` or `matched_name`. If metadata is genuinely unavailable, leave `matched_name`/`address` null so plausibility fails **closed** (reject → street fallback), not open.
4. Do not change the persisted `address` column semantics in silver (`cleaning.py:414-417`): the project-aware string is a query only.
5. Fix the pacing reservation while you are in this file — see WS-A4 §1 (CORE-6). It is the same module and must not be split across two owners.

## Tests (add to `tests/test_onemap.py` or a focused new module)

- Cold then warm run with a mocked implausible project result: identical coordinates, identical rejection, identical metadata.
- Cached entry produced by the old coordinate-only format: treated as a miss (no fabricated metadata).
- Cache hit still avoids an API call (assert call count).
- Rate limiter: deterministic assertion that N concurrent reservations release at `interval` spacing (WS-A4 §1).

## Verification

```bash
uv run pytest tests/test_onemap.py tests/test_ingestion.py tests/test_cleaning_validation.py --no-cov -q
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

## Owns

`src/egg_n_bacon_housing/utils/geocoding.py`, `tests/test_onemap.py` (or a new focused test file), `src/egg_n_bacon_housing/adapters/onemap.py` if the cache shape must change.

## Do not touch

`components/cleaning.py` semantics (only if a null-metadata contract needs a docstring), `scripts/`, `pyproject.toml`, other adapters.

## Done when

Cold and warm runs are provably equivalent (same coordinates, same accept/reject decisions, no fabricated metadata), the pacing test asserts real spacing, and the gate passes with no new `astro`/`mypy` findings.
