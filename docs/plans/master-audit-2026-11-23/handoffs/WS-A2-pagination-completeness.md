# WS-A2 — Pagination completeness (CORE-2)

**Severity:** HIGH (4×3 = 12). **Effort:** M. **Wave:** 1. **Skill:** `change-data-ingestion`.

## Problem

A later page that returns HTTP 200 without `result.records` exits pagination normally and returns the accumulated rows. Completeness reconciliation exists only inside `except` branches, so a "successful" malformed page publishes a partial dataset and writes a fresh manifest, making it a permanent bronze hit.

- `src/egg_n_bacon_housing/adapters/datagovsg.py:222-226` — missing envelope → `logger.warning` → `break`.
- `:229`, `:332-336` — concat and return without a final reconciliation.
- `:294-298`, `:313-317`, `:323-327` — the only `IncompleteDatasetFetchError` raises (exception paths).
- Probe: `../evidence/core-poc-results.json` → `partial_fetch` (advertised 4, returned 2, cached 2, manifest 2).

## Required change

1. Treat a malformed page envelope as a fetch failure at **any** offset, not just before the first successful page. Preserve the current first-page behaviour if it is deliberate (empty dataset vs malformed response) — distinguish them explicitly rather than by accident: a first page with `success: false` or a missing `result` is an error, not an empty dataset.
2. Add a terminal reconciliation before returning: fetched row count vs advertised `total` (when the source provides one). Raise `IncompleteDatasetFetchError` naming dataset id, advertised total, fetched total and the offending URL.
3. Reject non-progressing pagination (repeated `next` link, offset that does not advance, `offset > total` handled today at `:246-248`).
4. Ensure nothing is persisted on failure: the bronze writer must not run when the adapter raises (`components/ingestion/datagov.py:109-125` already raises for required sources; confirm the optional-source path does not cache a partial result).
5. Keep retry semantics unchanged for transient HTTP statuses (429/5xx/network) — this is about envelopes, not status codes.

## Tests (`tests/test_datagovsg.py`)

- Valid page → HTTP-200 error envelope: raises, and no parquet/manifest is written.
- Valid page → page without `result.records`: raises with advertised/fetched counts in the message.
- Repeated `next` link: raises rather than looping or truncating.
- First-page `success: false`: raises (required) / documented empty behaviour (optional) — assert whichever you implement.
- Existing tests for HTTP failure after pagination and missing records on the first page must still pass.

## Verification

```bash
uv run pytest tests/test_datagovsg.py tests/test_datagov.py tests/test_ingestion.py --no-cov -q
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

## Owns

`src/egg_n_bacon_housing/adapters/datagovsg.py`, `src/egg_n_bacon_housing/components/ingestion/datagov.py` (only if the optional-source path needs a guard), `tests/test_datagovsg.py`.

## Do not touch

`utils/bronze.py` paths, geocoding, sync script, frontend.

## Done when

No code path can return fewer rows than the source advertised without raising, no failure persists bronze, and the focused + full gate passes.
