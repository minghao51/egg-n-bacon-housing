# Codebase Concerns

**Analysis Date:** 2026-02-02

## Tech Debt

**Hardcoded Configuration and Data Paths:**
- Issue: Extensive hardcoded paths and file names throughout the codebase
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/config.py`, `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/stages/L0_collect.py`, `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/geocoding.py`
- Impact: Difficult to maintain, deploy, and test; requires manual updates for different environments
- Fix approach: Centralize all configuration in Config class, use environment variables for paths, implement configuration validation

**Duplicate Code in Data Loading:**
- Issue: Similar data loading logic repeated across multiple files with slight variations
- Files: Multiple L-stage pipeline files and processing scripts
- Impact: Code duplication increases maintenance burden and risk of inconsistencies
- Fix approach: Create a unified data loader factory pattern with common interfaces and shared utilities

**Import Path Fragility:**
- Issue: Complex import patterns with multiple fallbacks (e.g., scripts/core/config.py lines 18-38)
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/cache.py`, `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/geocoding.py`
- Impact: Breaks easily with directory structure changes, makes refactoring difficult
- Fix approach: Implement proper package structure with consistent imports, use relative imports where appropriate

## Known Bugs

**Date Format Inconsistency:**
- Issue: Different date formats causing parsing errors (e.g., 'Dec-22' vs '2022-12')
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/stages/L3_export.py` lines 342-346, 645-653
- Symptoms: Date parsing failures, incorrect period calculations
- Trigger: When processing Condo vs HDB data with different date formats
- Workaround: Multiple format handling with error coercion, but not robust

**MRT Line Mapping Inconsistency:**
- Issue: Station names with 'BUGIS' appear in hardcoded lists but may not match actual API responses
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/mrt_line_mapping.py` lines 98, 142
- Symptoms: Incomplete station matches, missing line assignments
- Trigger: When OneMap API returns slightly different station naming
- Workaround: Fuzzy matching helps but isn't foolproof

**Memory Management in Large Data Processing:**
- Issue: Multiple large DataFrames loaded simultaneously without proper cleanup
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/stages/L3_export.py` lines 435-443
- Symptoms: High memory usage, potential crashes with large datasets
- Trigger: Processing full transaction datasets with multiple merges
- Workaround: Batch processing implemented but not consistently applied

## Security Considerations

**API Key Exposure in Code:**
- Risk: API keys stored in environment variables but with fallback authentication methods that could expose credentials
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/geocoding.py` lines 55-106
- Current mitigation: Basic JWT token expiration checking
- Recommendations: Implement proper secret management, use credential rotation, add audit logging

**File Path Tr Vulnerabilities:**
- Risk: Direct file path construction without validation could allow directory traversal
- Files: Multiple data loading scripts
- Current mitigation: Limited validation in some modules
- Recommendations: Implement path validation, sanitize all file inputs, use pathlib.Path safely

**Data Privacy Concerns:**
- Risk: Property transaction data contains sensitive pricing and location information
- Files: All transaction processing modules
- Current mitigation: Basic data masking in some exports
- Recommendations: Implement data anonymization, access controls, audit trails for sensitive data

## Performance Bottlenecks

**Sequential API Calls:**
- Problem: Slow geocoding due to sequential API calls despite parallel implementation
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/geocoding.py` lines 311-363
- Cause: OneMap API rate limiting and artificial delays
- Improvement path: Implement exponential backoff, better error handling, alternative geocoding services

**Large Memory Footprint:**
- Problem: Multiple large DataFrames loaded simultaneously in memory
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/stages/L3_export.py`
- Cause: Loading all transaction types, geocoding, and features before processing
- Improvement path: Implement streaming processing, chunked operations, and memory-efficient data types

**Inefficient String Operations:**
- Problem: Multiple string manipulations in data processing loops
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/stages/L1_process.py`
- Cause: Repeated string operations on large datasets without vectorization
- Improvement path: Use pandas string methods, vectorized operations, minimize intermediate columns

## Fragile Areas

**Pipeline Dependencies:**
- Component: Multi-stage data pipeline (L0-L5)
- Files: All `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/stages/` modules
- Why fragile: Each stage depends on specific outputs from previous stages, no error recovery
- Safe modification: Add input validation, implement checkpoint/recovery, add dependency graphs
- Test coverage: Limited integration testing between stages

**Configuration System:**
- Component: Centralized Config class
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/config.py`
- Why fragile: Global validation on import, complex path resolution, many dependencies
- Safe modification: Add configuration schema validation, implement gradual migration
- Test coverage: Configuration testing needs improvement

**External API Integration:**
- Component: OneMap API integration
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/scripts/core/geocoding.py`
- Why fragile: API rate limits, authentication changes, service availability
- Safe modification: Add circuit breakers, implement fallback services, better error handling
- Test coverage: Limited API failure scenario testing

## Scaling Limits

**Dataset Size Limits:**
- Current capacity: ~100K transaction records processing
- Limit: Memory constraints during DataFrame operations, slow processing times
- Scaling path: Implement distributed processing, use database backend, optimize memory usage

**API Rate Limiting:**
- Current capacity: ~5 parallel workers with 1.2s delays
- Limit: OneMap API constraints (unknown but likely ~60-100 requests/minute)
- Scaling path: Implement request queuing, use multiple API keys, implement caching

**Concurrent Processing:**
- Current capacity: Single-threaded pandas operations
- Limit: CPU-bound operations not parallelized
- Scaling path: Implement Dask or PySpark for distributed processing, optimize pandas operations

## Dependencies at Risk

**Python Package Ecosystem:**
- Package: pandas
- Risk: Core dependency, frequent breaking changes between versions
- Impact: Data processing functionality
- Migration plan: Pin specific version, implement compatibility layer, monitor deprecation warnings

**External APIs:**
- Package: OneMap API service
- Risk: Service availability, rate limiting changes, API breaking changes
- Impact: Geocoding functionality
- Migration plan: Implement alternative geocoding services (Google Maps, OpenStreetMap), add service abstraction layer

**File Format Dependencies:**
- Package: parquet file format
- Risk: Library updates, format compatibility issues
- Impact: Data storage and retrieval
- Migration plan: Maintain backward compatibility, implement format versioning, add validation

## Missing Critical Features

**Data Quality Monitoring:**
- Problem: No comprehensive data quality checks or alerts
- Blocks: Early detection of data corruption, missing values, anomalies
- Priority: High

**Automated Testing:**
- Problem: Limited test coverage, especially for integration scenarios
- Blocks: Refactoring confidence, CI/CD pipeline reliability
- Priority: High

**Error Recovery Mechanisms:**
- Problem: Pipeline failures require manual intervention
- Blocks: Automated workflows, production reliability
- Priority: Medium

**Documentation and Knowledge Base:**
- Problem: Limited technical documentation, code comments outdated
- Blocks: Onboarding, maintenance, knowledge transfer
- Priority: Medium

## Test Coverage Gaps

**Geocoding Integration Testing:**
- What's not tested: API failure scenarios, rate limiting, edge cases
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/tests/test_geocoding.py`
- Risk: Real-world API failures not handled gracefully
- Priority: High

**Pipeline Integration Testing:**
- What's not tested: End-to-end pipeline execution, stage interactions
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/tests/test_pipeline.py`
- Risk: Integration issues between pipeline stages
- Priority: High

**Configuration Validation Testing:**
- What's not tested: Configuration scenarios, error conditions
- Files: `/Users/minghao/Desktop/personal/egg-n-bacon-housing/tests/test_config.py`
- Risk: Configuration errors not caught early
- Priority: Medium

**Performance Testing:**
- What's not tested: Large dataset handling, memory usage, execution time
- Files: Limited performance tests exist
- Risk: Performance degradation not detected
- Priority: Medium

---

*Concerns audit: 2026-02-02*
