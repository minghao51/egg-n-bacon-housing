# Codebase Concerns

**Analysis Date:** 2026-04-19

## Tech Debt

**Segment Data Generation:**
- Issue: Hardcoded mock values for `forecast6m` (0.0) and `avgYield` (5.0) in segment data
- Files: `scripts/webapp/generate_segments_data.py:612,614`
- Impact: Dashboard displays placeholder metrics instead of real forecast data
- Fix approach: Integrate actual forecast pipeline output and calculate yield from rental data

**Macro Data Integration:**
- Issue: MAS API call is stubbed with TODO comment
- Files: `scripts/data/fetch_macro_data.py:154`
- Impact: External economic indicators not available for analysis
- Fix approach: Implement actual MAS API integration

**L3 Metrics Pipeline:**
- Issue: Affordability index and ROI potential score lack required data inputs
- Files: `scripts/analytics/pipelines/calculate_l3_metrics_pipeline.py:12,13`
- Impact: Key investment metrics cannot be computed
- Fix approach: Source income data and rental data, then implement calculations

**URA Rental Scraper:**
- Issue: Both rental statistics and rental contracts scrapers are disabled
- Files: `scripts/core/stages/L0_collect.py:385,404`
- Impact: Rental market data unavailable for analysis
- Fix approach: Fix scraper and re-enable

## Known Bugs

**Disabled Data Collection:**
- Symptoms: Rental data collection silently returns None without failing
- Files: `scripts/core/stages/L0_collect.py:385,404`
- Trigger: Any pipeline step expecting rental data
- Workaround: Manual data procurement or scraper fix

## Security Considerations

**API Credential Management:**
- Risk: `.env` file with live credentials present in repository structure
- Files: `.env` (not tracked if gitignored, but exists)
- Current mitigation: `.env.example` shows expected structure without values
- Recommendations: Ensure `.env` is in `.gitignore`; rotate any committed credentials; use secrets manager in production

**Hardcoded API Endpoints:**
- Risk: Third-party service URLs embedded in scripts could become outdated
- Files: `scripts/core/geocoding.py:76,128`, `scripts/core/stages/L0_collect.py:426`
- Current mitigation: Uses government official APIs (data.gov.sg, onemap.gov.sg)
- Recommendations: Externalize to config; add health checks for external services

## Performance Bottlenecks

**Large JSON Payload Processing:**
- Problem: Dashboard loads and decompresses large gzip-compressed JSON files
- Files: `app/src/hooks/useGzipJson.ts`, `app/src/utils/gzip.ts`
- Cause: Property transaction datasets can be very large
- Improvement path: Implement pagination or streaming; consider Web Workers for decompression

**Map Rendering with Multiple Overlays:**
- Problem: PriceMap.tsx (716 lines) renders multiple analytical layers simultaneously
- Files: `app/src/components/dashboard/PriceMap.tsx`
- Cause: LayerControl allows up to 5 active overlays; each renders GeoJSON with tooltips
- Improvement path: Virtualize off-screen layers; memoize layer calculations; reduce re-renders

**Complex Data Parsing:**
- Problem: data-parser.ts and colorScales.ts contain complex transformations
- Files: `app/src/utils/data-parser.ts:325`, `app/src/utils/colorScales.ts:227`
- Cause: Heavy computation during chart rendering
- Improvement path: Pre-compute in pipelines; cache parsed results; web worker offloading

## Fragile Areas

**Spatial Hotspot Explorer:**
- Files: `app/src/components/dashboard/tools/SpatialHotspotExplorer.tsx:483`
- Why fragile: Large component with complex spatial calculations; heavy coupling to geo data structures
- Safe modification: Add feature flags; maintain regression test suite for spatial calculations
- Test coverage: Likely minimal - spatial analysis is visual/heuristic

**MRT Impact Analysis Pipeline:**
- Files: `scripts/analytics/analysis/mrt/analyze_mrt_impact.py:837`
- Why fragile: Complex spatial econometrics; depends on external MRT data freshness
- Safe modification: Mock external data in tests; verify statistical outputs before production

**Price Appreciation Modeling:**
- Files: `scripts/analytics/price_appreciation_modeling/train_models.py:618`, `scripts/analytics/price_appreciation_modeling/residual_analysis.py:674`
- Why fragile: Statistical models can degrade with data drift; multiple similar scripts suggest parallel experimentation
- Safe modification: Version models; track prediction accuracy over time
- Test coverage: Backtesting exists but may not cover edge cases

## Scaling Limits

**In-Memory Data Processing:**
- Current capacity: Designed for Singapore property market (~1M transactions)
- Limit: Full dataset loading may strain browsers on low-end devices
- Scaling path: Server-side aggregation; incremental loading; client-side sampling

**Static JSON Data Files:**
- Current capacity: Pre-computed analytics stored as gzip JSON
- Limit: Growth bounded by pipeline execution time and storage
- Scaling path: Migrate to API endpoints with database backend; implement caching

## Dependencies at Risk

**OneMap API:**
- Risk: External dependency on Singapore government mapping service
- Impact: Geocoding and spatial features fail if service is down or rate-limited
- Migration plan: Fallback to alternative geocoding (Google, HERE); cache aggressively

**URA Data Portal:**
- Risk: Scraping targets may change HTML structure or block requests
- Impact: All rental and transaction data collection breaks
- Migration plan: Official bulk download API when available; monitor for changes

**Supabase:**
- Risk: Database URL and key exposed in client code pattern
- Impact: If keys are compromised, database can be accessed
- Migration plan: Use server-side API routes instead of direct client access; rotate keys

## Missing Critical Features

**Forecast Integration:**
- Problem: `forecast6m` field is hardcoded to 0.0 in segment data
- Blocks: Forward-looking investment analysis; trend prediction dashboards

**Rental Yield Calculation:**
- Problem: `avgYield` is hardcoded to 5.0 across all segments
- Blocks: Accurate buy-to-let investment analysis

**MAS/SingStat Economic Data:**
- Problem: Macro indicators not integrated
- Blocks: Affordability analysis; market cycle analysis

## Test Coverage Gaps

**Frontend Dashboard Components:**
- What's not tested: Interactive chart rendering; map interactions; filter state management
- Files: `app/src/components/dashboard/**/*.tsx`
- Risk: UI regression undetected; edge cases in user interactions fail silently
- Priority: Medium

**Analytics Pipelines:**
- What's not tested: Output format validation; edge cases in statistical calculations
- Files: `scripts/analytics/pipelines/*.py`
- Risk: Invalid data propagates to dashboard; incorrect metrics displayed
- Priority: High

**Scraper/Stages:**
- What's not tested: HTML parsing resilience; error handling for malformed responses
- Files: `scripts/core/stages/*.py`, `scripts/data/download/*.py`
- Risk: Silent failures; partial data collection
- Priority: Medium

---

*Concerns audit: 2026-04-19*
