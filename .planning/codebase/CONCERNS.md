# Codebase Concerns

**Analysis Date:** 2026-05-12

## Tech Debt

**Macro Data Integration:**

- File: `src/egg_n_bacon_housing/components/01_ingestion.py`
- Issue: MAS API call may be incomplete
- Impact: External economic indicators not available

**Disabled Data Collection:**

- File: `src/egg_n_bacon_housing/components/01_ingestion.py`
- Issue: Some rental data sources return None without failing
- Trigger: Pipeline steps expecting rental data
- Workaround: Manual data procurement

**Segment Data Generation:**

- File: `src/egg_n_bacon_housing/components/04_export.py`
- Issue: `forecast6m` and `avgYield` may use placeholder values
- Impact: Dashboard displays incomplete metrics

## Known Bugs

**Config Path Discrepancy:**

- `config.yaml` and `config.py` had differing `layer_dirs` paths (`data/pipeline/` vs `data/`). Now aligned to `data/`.

**Stale **pycache** for deleted tests:**

- Files in `tests/__pycache__/` for removed test files
- Fix: `uv run pytest --cache-clear`

## Security Considerations

**API Credential Management:**

- `.env` with live credentials must remain gitignored
- `.env.example` shows expected structure without values

**Hardcoded API Endpoints:**

- Files: `src/egg_n_bacon_housing/adapters/onemap.py`, `datagovsg.py`
- Mitigation: Uses government official APIs (data.gov.sg, onemap.gov.sg)

## Performance Bottlenecks

**Large JSON Payload Processing:**

- Dashboard loads gzip-compressed JSON files
- Files: `app/src/hooks/useGzipJson.ts`, `app/src/utils/gzip.ts`
- Improvement: Pagination, streaming, Web Workers

**Map Rendering with Multiple Overlays:**

- `app/src/components/dashboard/PriceMap.tsx` renders multiple analytical layers
- Improvement: Virtualize off-screen layers, memoize calculations

## Fragile Areas

**Spatial Analysis Components:**

- Complex spatial econometrics, depends on external MRT data freshness
- Files: `src/egg_n_bacon_housing/analytics/analysis/spatial/`

**Price Appreciation Modeling:**

- Statistical models can degrade with data drift
- Files: `src/egg_n_bacon_housing/analytics/price_appreciation_modeling/`

## Missing Critical Features

- Forecast integration (placeholder values in segment data)
- Rental yield calculation from actual rental data
- MAS/SingStat economic data integration

## Test Coverage Gaps

- Frontend dashboard components: map interactions, filter state
- Analytics pipelines: output format validation, statistical edge cases
- Adapter error handling: malformed API responses
