# Egg-n-Bacon-Housing: Technical Concerns & Areas for Improvement

## Overview

This document catalogs technical debt, known issues, security concerns, performance bottlenecks, and areas for improvement in the egg-n-bacon-housing project.

**Last Updated**: 2026-02-19
**Status**: Active tracking

---

## Technical Debt

### 1. Large File Complexity

**Files Over 1000 Lines**:

| File | Lines | Concern |
|------|-------|---------|
| `scripts/core/stages/L3_export.py` | 1639 | Should be split into smaller functions |
| `scripts/dashboard/create_l3_unified_dataset.py` | 1443 | Duplicate logic with L3_export.py |
| `scripts/core/metrics.py` | 914 | Complex statistical calculations |
| `scripts/analytics/analysis/mrt/analyze_mrt_impact.py` | 797 | Large analysis file |
| `scripts/analytics/analysis/market/analyze_lease_decay_advanced.py` | 768 | Complex lease decay modeling |
| `scripts/analytics/enhanced_mrt_analysis.py` | 756 | Duplicate MRT analysis |
| `scripts/core/school_features.py` | 726 | Complex feature engineering |
| `scripts/core/mrt_line_mapping.py` | 534 | Hardcoded station data |

**Impact**: Difficult to test, maintain, and understand

**Recommendation**:
- Break L3_export.py into modules by function (export, validation, JSON generation)
- Consolidate duplicate logic between L3_export.py and create_l3_unified_dataset.py
- Extract hardcoded data to CSV/JSON files (MRT stations, schools)

### 2. Hardcoded Data

**MRT Station Mapping** (`scripts/core/mrt_line_mapping.py`):
- 534 lines of hardcoded station-to-line mappings
- Should be in a CSV/JSON file for easy updates

**School Tiers** (`scripts/core/school_features.py`):
- Hardcoded school tier assignments
- Should be data-driven from a configuration file

**Planning Area Crosswalk**:
- Manual crosswalk file exists but needs validation

**Impact**: Maintenance burden, error-prone updates

### 3. Duplicate Code

**L3 Export Logic**:
- `L3_export.py` (1632 lines)
- `create_l3_unified_dataset.py` (1443 lines)
- Significant overlap in data processing and export logic

**Recommendation**: Consolidate into shared module

**Data Loading**:
- Multiple patterns for loading transaction data
- Partially addressed with `TransactionLoader` but not fully migrated

### 4. Import Path Fragility

**Status**: Partially resolved (2026-02-03)

**Remaining Issues**:
- Some scripts still use relative imports
- Notebook imports may fail if run from different directory

**Example**:
```python
# Fragile
from ..core.config import Config

# Better
from scripts.core.config import Config
```

---

## Known Issues

### 0. TODO/FIXME Comments

**Active TODOs Found**:

| File | Line | Description | Status |
|------|------|-------------|--------|
| `scripts/data/fetch_macro_data.py` | 50 | Replace with actual MAS API call | TODO |
| `scripts/analytics/pipelines/calculate_l3_metrics_pipeline.py` | 12 | Affordability index needs income data | TODO |
| `scripts/analytics/pipelines/calculate_l3_metrics_pipeline.py` | 13 | ROI potential score needs rental data | TODO |

**Resolved**:
- `scripts/data/fetch_macro_data.py` - SingStat API integration implemented (CPI falls back to mock, GDP works)

**Impact**: Incomplete functionality, missing data integrations

**Recommendation**: Implement API integrations or mark as known limitations

### 1. Test Coverage Gaps

**Current Coverage**: Limited to `scripts/core`

**Missing Coverage**:
- `scripts/analytics/` - No tests
- `scripts/data/` - No tests
- `scripts/utils/` - No tests
- Frontend (app/, backend/) - No tests

**Impact**: Risk of regressions in untested code

**Recommendation**: Add tests for critical analytics paths

### 2. Geocoding Fallback Handling

**Issue**: When both OneMap and Google Maps fail, address is skipped

**Current Behavior**:
- Logs error
- Continues without geocoding
- Manual intervention required to retry

**Better Approach**:
- Queue failed addresses for retry
- Save checkpoint for recovery
- Alert when failure rate exceeds threshold

### 3. Token Expiry Management

**Issue**: OneMap token expires after ~3 days

**Current Handling**:
- Auto-refresh on 401/403
- But may lose in-flight requests

**Better Approach**:
- Proactive refresh before expiry
- Background refresh thread
- Token pre-validation before batch jobs

### 4. Memory Usage for Large Datasets

**Issue**: Full datasets loaded into memory

**Files Affected**:
- L3_export.py (1632 lines) - Processes all data at once
- Large parquet files (>500MB)

**Impact**: High memory usage, potential OOM on smaller machines

**Recommendation**: Implement chunked processing for large datasets

---

## Security Concerns

### 1. API Key Exposure Risk

**Environment Variables**:
- `.env` file (not in git) - Good
- All API keys loaded from environment (ONEMAP_TOKEN, GOOGLE_API_KEY)
- No hardcoded secrets found in scripts (only test fixtures)

**Current Pattern** (Good):
```python
# scripts/core/config.py
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ONEMAP_TOKEN = os.getenv("ONEMAP_TOKEN")
```

**Recommendation**:
- Add `.env` to `.gitignore` (already done)
- Add pre-commit hook to check for API keys in commits
- Use secret scanning in CI/CD

### 2. Dependency Vulnerabilities

**Outdated Dependencies**:
- Langchain packages pinned to specific versions
- Some packages in beta (e.g., `h3==4.1.0b2`)

**Impact**: Potential security vulnerabilities

**Recommendation**: Regular dependency updates via `uv sync --upgrade`

### 3. Data Validation

**Issue**: Limited input validation on user-provided data

**Areas**:
- Manual CSV uploads not validated
- API responses assumed correct

**Recommendation**: Add schema validation (pydantic/marshmallow)

---

## Performance Bottlenecks

### 1. Geocoding Throughput

**Current**: Sequential API calls with 1 second delay

**Impact**:
- 10,000 addresses = ~2.8 hours
- Not practical for large datasets

**Better Approach**:
- Parallel workers (already implemented but with low concurrency)
- Dynamic rate limiting based on API response time
- Batch geocoding API (if available)

### 2. MRT Distance Calculation

**Issue**: Computed on-the-fly for each analysis

**Files**: `scripts/core/mrt_distance.py`

**Recommendation**:
- Pre-compute and cache MRT distances
- Use spatial indexing (H3) for faster queries

### 3. Feature Engineering

**Issue**: Re-computed for each analysis run

**Example**: School features, CBD distances

**Recommendation**:
- Store computed features in parquet files
- Check for existing features before re-computing

### 4. Dashboard JSON Generation

**Issue**: `prepare_webapp_data.py` can be slow

**Impact**: Delayed dashboard updates

**Recommendation**:
- Incremental updates (only changed data)
- Cache previous results
- Parallel generation for independent files

---

## Fragile Areas

### 1. Pipeline State Management

**Issue**: No explicit state management

**Current Behavior**:
- Stages run based on file existence
- No validation of intermediate results

**Impact**: Hard to recover from failures

**Recommendation**:
- Add checkpoint file tracking stage completion
- Validate stage outputs before proceeding
- Add `--resume` flag to skip completed stages

### 2. Error Recovery

**Issue**: Limited retry logic for external APIs

**Current**: Only geocoding has retry (via tenacity)

**Impact**: Single API failure can break pipeline

**Recommendation**: Add retry logic to all external API calls

### 3. Data Lineage Tracking

**Issue**: Limited metadata tracking

**Current**: Only tracks file creation, not transformations

**Recommendation**:
- Track all transformations applied to data
- Store transformation history in metadata.json
- Enable data reproducibility

---

## Code Quality Issues

### 1. Inconsistent Docstring Coverage

**Status**: Good for core modules, spotty for analytics

**Files Missing Docstrings**:
- Some utility scripts
- Legacy notebook code
- Some analysis scripts

**Recommendation**: Enforce docstring coverage in CI

### 2. Type Hint Coverage

**Status**: Partial

**Coverage**:
- Core services: Good
- Analytics scripts: Spotty
- Tests: Minimal

**Recommendation**: Add type hints to all public functions

### 3. Logging Inconsistency

**Issue**: Mix of print() and logger

**Files Using print()**:
- Some scripts still use `print()` instead of `logger`

**Recommendation**: Replace all `print()` with `logger`

---

## Configuration Issues

### 1. Environment Variable Validation

**Issue**: Some optional vars not validated when used

**Example**:
```python
# AWS credentials validated only when S3 is used
# But no clear error if AWS vars are missing
```

**Recommendation**: Lazy validation with clear error messages

### 2. Hardcoded Constants

**Examples**:
- Cache duration (24 hours)
- API delays (1 second)
- Retry attempts (3)

**Recommendation**: Move to Config class

---

## Deployment Concerns

### 1. GitHub Pages Deployment

**Issue**: No automated testing of deployed site

**Current**: Deploy on push to main

**Risk**: Broken site deployed if tests fail

**Recommendation**: Add deployment gate (tests must pass)

### 2. Data File Size

**Issue**: Large JSON files in `app/public/data/`

**Impact**:
- Slow page loads
- High bandwidth usage

**Recommendation**:
- Implement data pagination
- Compress JSON files (gzip)
- Use incremental loading

### 3. No Rollback Strategy

**Issue**: No easy way to rollback bad deployments

**Recommendation**: Tag releases, use GitHub Pages branches

---

## Documentation Gaps

### 1. Architecture Documentation

**Status**: This document (CONCERNS.md) exists but...

**Missing**:
- Sequence diagrams for complex flows
- Data flow diagrams
- Deployment guide

### 2. Onboarding Documentation

**Issue**: steep learning curve for new developers

**Missing**:
- Setup troubleshooting guide
- Common workflows
- Debugging guide

### 3. API Documentation

**Issue**: No docstrings for internal APIs

**Impact**: Hard to reuse code

**Recommendation**: Add docstrings to all public functions

---

## Prioritized Action Items

### High Priority

1. **Consolidate L3 Export Logic** - Eliminate duplicate code
2. **Add Analytics Tests** - Cover critical paths
3. **Extract Hardcoded Data** - MRT stations, schools to CSV/JSON
4. **Improve Geocoding Performance** - Parallel workers, batch API

### Medium Priority

5. **Add Pipeline Checkpoints** - Enable resume from failures
6. **Implement Data Pagination** - Reduce dashboard load time
7. **Add Deployment Gates** - Tests must pass before deploy
8. **Consolidate Data Loading** - Migrate all to DataLoader pattern

### Low Priority

9. **Add Type Hints** - Complete coverage
10. **Replace print() with logger** - Consistent logging
11. **Add Onboarding Guide** - Developer documentation
12. **Implement Chunked Processing** - Reduce memory usage

---

## Related Documents

- `20260203-tech-debt-mitigation.md` - Previous tech debt work
- `20260203-school-features-optimization.md` - School features optimization
- `docs/analytics/findings.md` - Analysis findings (uses this data)

---

## Summary

**Critical Areas**:
- Large file complexity (L3_export.py: 1639 lines)
- Duplicate export logic (L3_export.py vs create_l3_unified_dataset.py)
- Test coverage gaps (analytics, data processing)
- Geocoding performance bottleneck
- 3 active TODO comments requiring attention (MAS SORA API, affordability index, ROI score)

**Quick Wins**:
- Extract hardcoded data to CSV/JSON
- Add deployment gates (tests before deploy)
- Replace remaining print() with logger
- Add type hints to analytics scripts

**Long-term Improvements**:
- Pipeline checkpoint system
- Chunked processing for large datasets
- Comprehensive test suite
- Performance optimization (MRT distances, feature caching)

Overall, the codebase is well-structured with good separation of concerns. The main areas for improvement are reducing file complexity, consolidating duplicate code, and improving test coverage.
