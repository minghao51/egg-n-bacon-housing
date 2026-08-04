# Data Ingestion Development Guide

**Status**: Active

Data ingestion acquires external and manual sources into the bronze layer. The
supported path is a source adapter plus a Hamilton node under
`src/egg_n_bacon_housing/components/ingestion/`.

## Source-onboarding record

Before adding a source, record the following in this guide or the source's
documentation:

| Field      | Required detail                                                     |
| ---------- | ------------------------------------------------------------------- |
| Identity   | Owner, URL/resource ID, dataset name, and acquisition method        |
| Operations | Cadence, freshness expectation, and source grain                    |
| Access     | Authentication variables, rate limits, and request constraints      |
| Contract   | Schema, primary/business keys, join keys, and normalization         |
| Storage    | Bronze node/output name, cache path, and retention/freshness policy |
| Failure    | Required/optional status, retries, fallback, and error behavior     |
| Lineage    | Downstream silver/gold/platinum consumers                           |

Manual source bundles are synced from Cloudflare R2 with
`dotenvx run -- uv run python scripts/00_sync_data.py`; they are not committed
to the repository.

## Code placement

- `adapters/` owns HTTP/CSV transport, authentication, pagination, retries,
  response parsing, and source-specific exceptions.
- `components/ingestion/` owns Hamilton node signatures, source selection,
  bronze normalization, and output persistence.
- `utils/cache.py` owns reusable cache behavior. Existing valid caches take
  precedence when a source is unavailable; empty responses must not destroy a
  valid cache.
- Cleaning, schema validation, and quarantine belong to the silver stage.

Keep source credentials in `Settings` and environment variables. The default
test suite must use mocked transport and deterministic fixtures rather than live
APIs.

## Minimum tests

Every new or changed source should cover, as applicable:

- successful fetch and response normalization;
- cache hit and cache preservation on empty/error responses;
- timeout, authentication, rate-limit, and malformed-response behavior;
- manual-file discovery and missing-file behavior;
- Hamilton node name, dependencies, bronze output, and empty-source policy.

Run the focused suite with:

```bash
uv run pytest tests/test_ingestion.py tests/test_datagovsg.py tests/test_onemap.py --no-cov -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/tools/validate_docs_layout.py
uv run python scripts/tools/validate_agent_skills.py
git diff --check
```
