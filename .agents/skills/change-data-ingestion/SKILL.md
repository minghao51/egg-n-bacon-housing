---
name: change-data-ingestion
description: Safely change external API or manual-file ingestion, adapters, caching, geocoding, bronze nodes, and source-level tests in egg-n-bacon-housing.
---

# Change data ingestion

Use this skill for new or changed data.gov.sg, URA, GeoJSON, macro, manual CSV,
geocoding, adapter, cache, or bronze-layer behavior.

## Boundary rules

- Put transport, authentication, pagination, retries, response parsing, and
  source-specific error translation in `src/egg_n_bacon_housing/adapters/`.
- Put Hamilton node assembly, bronze normalization, source-to-node wiring, and
  bronze persistence in `components/ingestion/`.
- Keep credentials in settings/environment configuration; never hard-code them.
- Use the existing cache utilities and bronze paths. A valid existing cache must
  not be replaced by an empty or partial source response.
- Distinguish expected source failures (availability, authentication, malformed
  payloads, rate limits) from programming defects. Handle only the former at the
  source boundary and preserve actionable context in logs and exceptions.
- Keep bronze data raw/immutable apart from documented normalization needed to
  establish a stable source contract. Cleaning and quarantine belong downstream
  in the silver stage.

## Required source-onboarding record

For every new or materially changed source, document:

- source identity, owner, URL/resource ID, and acquisition method;
- cadence and expected freshness;
- authentication/environment variables;
- row grain, primary/business keys, and join keys;
- schema and normalization assumptions;
- cache location and freshness policy;
- failure policy, fallback behavior, and whether the source is required;
- bronze output name, layer path, and downstream consumers.

Update `docs/guides/data-ingestion-development.md` or the relevant source
documentation with this record.

## Required tests

Add focused tests for the adapter and node as applicable:

- successful response parsing and schema normalization;
- cache hit behavior and cache preservation on empty/error responses;
- authentication, rate-limit, timeout, and malformed-response handling;
- manual-file discovery and missing-file behavior;
- Hamilton node output name, bronze path, and dependency wiring.

Prefer mocked transport in unit tests. Do not make the default test suite depend
on a live external service.

## Verification

```bash
uv run pytest tests/test_ingestion.py tests/test_datagovsg.py tests/test_onemap.py --no-cov -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/tools/validate_docs_layout.py
uv run python scripts/tools/validate_agent_skills.py
git diff --check
```
