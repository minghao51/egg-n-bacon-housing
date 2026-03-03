# Technical Debt & Concerns

**Generated**: 2026-02-28

## Overview

This document tracks known issues, technical debt, security concerns, and areas for improvement in the codebase.

**Priority Levels**:
- 🔴 **Critical** - Must fix soon (security, data loss risk)
- 🟡 **High** - Should fix soon (performance, maintainability)
- 🟢 **Medium** - Nice to have (code quality, cleanup)
- ⚪ **Low** - Minor issues (typos, inconsistencies)

---

## Large Files Requiring Refactoring

### 🔴 Critical

#### `scripts/core/stages/L3_export.py` - 1,879 lines

**Issues**:
- Too many responsibilities in one file
- Difficult to navigate and maintain
- High risk of introducing bugs

**Recommendation**:
- Split into module-level functions
- Create separate files for different export types
- Use a factory pattern for export generators

**Refactoring Plan**:
```
L3_export.py (1,879 lines)
    ↓
scripts/core/stages/export/
    ├── __init__.py
    ├── base_exporter.py
    ├── metrics_exporter.py
    ├── planning_area_exporter.py
    └── trends_exporter.py
```

### 🟡 High

#### `scripts/analytics/analysis/market/analyze_lease_decay_advanced.py` - 838 lines

**Issues**:
- Complex analysis logic mixed with visualization
- Hard to test individual components

**Recommendation**:
- Extract analysis logic to separate module
- Create dedicated visualization module
- Add unit tests for core analysis functions

#### `scripts/analytics/analysis/mrt/analyze_mrt_impact.py` - 837 lines

**Issues**:
- Multiple analysis approaches in one file
- Difficult to understand which method is used

**Recommendation**:
- Split into separate analysis methods
- Create base class for impact analysis
- Document each approach clearly

#### `scripts/analytics/analysis/mrt/analyze_mrt_spatial_econometrics.py` - 817 lines

**Issues**:
- Spatial econometrics models mixed with data processing
- Hard to reuse model components

**Recommendation**:
- Extract model definitions to `scripts/analytics/models/`
- Create reusable spatial regression classes
- Separate data preprocessing

#### `scripts/analytics/analysis/appreciation/analyze_appreciation_patterns.py` - 747 lines

**Issues**:
- Multiple appreciation analysis methods
- Complex parameter configurations

**Recommendation**:
- Create strategy pattern for different methods
- Extract configuration to YAML/JSON
- Add comprehensive documentation

---

## Hardcoded Data

### 🟡 High

#### `scripts/core/mrt_line_mapping.py` - 407 lines

**Issues**:
- Hardcoded MRT stations and lines
- Manual updates required when new stations open
- Risk of outdated data

**Current Content**:
```python
MRT_LINES = {
    "EW": {"name": "East West Line", "stations": [...]},
    "NS": {"name": "North South Line", "stations": [...]},
    # ... 400+ lines
}
```

**Recommendation**:
- Externalize to `data/reference/mrt_stations.json`
- Create script to fetch from LTA DataMall
- Add validation to detect missing stations
- Version control the JSON file

**Refactoring Plan**:
```python
# Before
from scripts.core.mrt_line_mapping import MRT_LINES

# After
from scripts.core.data_helpers import load_reference_data

MRT_LINES = load_reference_data("mrt_stations")
```

#### `scripts/core/school_features.py` - 726 lines

**Issues**:
- Hardcoded school tiers and ratings
- Manual updates required annually
- Subjective tier assignments

**Current Content**:
```python
SCHOOL_TIERS = {
    "school_name": 1,  # Tier 1
    "another_school": 2,  # Tier 2
    # ... 700+ lines
}
```

**Recommendation**:
- Externalize to `data/reference/school_tiers.json`
- Create data update script with validation
- Document tier assignment methodology
- Consider data-driven tier assignment (PSLE scores, awards)

**Data Source**:
- Ministry of Education school directory
- PSLE performance data
- Awards and achievements

---

## Performance Concerns

### 🟡 High

#### Sequential Geocoding

**Location**: `scripts/core/geocoding.py`

**Issue**:
- Sequential API calls with 1.2 second delay
- Bottleneck for large datasets
- Estimated time: 10,000 addresses × 1.2s = 3.3 hours

**Current Implementation**:
```python
for address in addresses:
    result = geocode_address(address)
    time.sleep(1.2)  # Rate limit delay
```

**Recommendation**:
- Implement parallel processing with ThreadPoolExecutor
- Use async/await with aiohttp
- Batch geocoding requests where possible
- Optimize delay timing (1.0s might be sufficient)

**Refactoring Plan**:
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(geocode_address, addresses))
```

**Expected Improvement**:
- 5 workers = 5x faster
- 10,000 addresses in ~40 minutes (vs 3.3 hours)

#### Full Dataset Loading

**Location**: Throughout codebase

**Issue**:
- Complete datasets loaded into memory
- Large datasets (1M+ rows) cause memory issues
- No chunked processing

**Current Implementation**:
```python
df = load_parquet("L3_unified_dataset")  # All rows in memory
```

**Recommendation**:
- Implement chunked processing for large files
- Use PyArrow for memory-efficient loading
- Consider streaming data for some operations

**Refactoring Plan**:
```python
# Process in chunks
for chunk in pd.read_parquet(path, chunksize=10000):
    process_chunk(chunk)
```

#### API Rate Limiting

**Location**: `scripts/core/geocoding.py`, `scripts/data/download/`

**Issue**:
- Conservative delays may be unnecessary
- No adaptive rate limiting based on API response
- Wastes time during processing

**Current Implementation**:
```python
time.sleep(1.2)  # Fixed delay
```

**Recommendation**:
- Implement adaptive rate limiting
- Monitor API response headers for rate limit info
- Use exponential backoff on 429 responses
- Cache responses aggressively

---

## Missing Test Coverage

### 🔴 Critical

#### Analytics Module

**Stats**:
- 49 analysis scripts
- 1 test file
- ~48 missing test files

**Gap**: 98% of analytics code is untested

**High Priority for Testing**:
- `scripts/analytics/models/` - ML models
- `scripts/analytics/analysis/market/` - Market analysis
- `scripts/analytics/pipelines/` - Metric calculation

**Recommendation**:
1. Add tests for core models first
2. Test data processing pipelines
3. Add integration tests for analysis scripts
4. Use fixtures for sample data

**Minimum Target**:
- 60% coverage for analytics module
- Critical paths: price prediction, segmentation

#### Data Module

**Stats**:
- 44 scripts
- 3 test files
- ~41 missing test files

**Gap**: 93% of data code is untested

**High Priority for Testing**:
- `scripts/data/download/` - Data fetching
- `scripts/data/process/` - Data processing
- `scripts/core/geocoding.py` - Geocoding logic

**Recommendation**:
1. Mock API calls in tests
2. Test error handling
3. Validate data transformations
4. Test edge cases (empty data, missing fields)

---

## Security Concerns

### 🟢 Medium (Well Managed)

#### Environment Variables

**Status**: ✅ **Properly Managed**

**Findings**:
- No hardcoded secrets found in codebase
- All secrets in `.env` file (not in git)
- `.env.example` provided as template
- `Config.validate()` checks required vars

**Best Practices Followed**:
- ✅ Secrets loaded from environment
- ✅ `.env` in `.gitignore`
- ✅ Template provided (`.env.example`)
- ✅ Validation on startup

**No Action Required**

#### API Key Exposure Risk

**Potential Issue**: Logging might expose sensitive data

**Current Implementation**:
```python
logger.info(f"API response: {response}")  # Might include API key?
```

**Recommendation**:
- Audit logging statements for sensitive data
- Scrub API keys from logs
- Use environment variable names in logs, not values

**Fix**:
```python
# Before
logger.info(f"Using API key: {api_key}")

# After
logger.info("Using API key from environment")
```

---

## Code Quality Issues

### 🟡 High

#### Duplicate Logic

**Location**: L3 dataset creation

**Files**:
- `scripts/create_l3_unified_dataset.py` - 1,443 lines
- `scripts/core/stages/L3_export.py` - 1,879 lines

**Issue**:
- Duplicate dataset merging logic in both files
- Inconsistent behavior
- Maintenance burden (fix in both places)

**Recommendation**:
- Extract common logic to shared module
- Create single source of truth
- Add tests to verify consistency

**Refactoring Plan**:
```python
# scripts/core/stages/L3_merge.py
def create_unified_dataset(hdb_df, ura_df, condo_df):
    """Single implementation of dataset merging."""
    # Merge logic here
    return merged_df

# Used by both
from scripts.core.stages.L3_merge import create_unified_dataset
```

#### Missing Type Hints

**Location**: Various files, especially older scripts

**Issue**:
- Some functions lack type hints
- Difficult to understand expected inputs/outputs
- IDE autocomplete less effective

**Example**:
```python
# Before
def process_data(df, config):
    # What types are df and config?
    pass

# After
def process_data(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Clear parameter and return types."""
    pass
```

**Recommendation**:
- Add type hints to all public functions
- Use `mypy` for static type checking
- Make it part of code review process

#### Inconsistent Error Messages

**Location**: Throughout codebase

**Issue**:
- Some error messages are vague
- Inconsistent formatting
- No suggested fixes

**Examples**:
```python
# Bad
raise ValueError("Invalid data")

# Good
raise ValueError(
    f"Invalid data: expected 'price' column, "
    f"got columns: {list(df.columns)}"
)
```

**Recommendation**:
- Standardize error message format
- Include context and suggestions
- Document common errors

---

## Documentation Gaps

### 🟢 Medium

#### Missing Docstrings

**Location**: Various modules

**Issue**:
- Some functions lack docstrings
- Inconsistent docstring style
- Missing parameter descriptions

**Recommendation**:
- Add docstrings to all public functions
- Use Google style consistently
- Include examples for complex functions

#### Outdated Documentation

**Location**: Some README files

**Issue**:
- Setup instructions may be outdated
- Examples don't match current API
- Missing new features

**Recommendation**:
- Audit all documentation quarterly
- Update examples with code review
- Add changelog for major changes

---

## Technical Debt Summary

### Immediate Actions (This Sprint)

1. 🔴 **Split L3_export.py** - Break into smaller modules
2. 🔴 **Add tests for core utilities** - `data_helpers.py`, `geocoding.py`
3. 🟡 **Externalize MRT data** - Move to JSON file
4. 🟡 **Implement parallel geocoding** - 5x performance improvement

### Short-term (Next Month)

1. 🟡 **Split large analysis files** - Reduce complexity
2. 🟡 **Add analytics tests** - Target 60% coverage
3. 🟡 **Implement chunked processing** - Reduce memory usage
4. 🟢 **Externalize school data** - Move to JSON file

### Long-term (Next Quarter)

1. 🟢 **Complete test coverage** - 80%+ coverage target
2. 🟢 **Refactor duplicate logic** - Single source of truth
3. 🟢 **Update documentation** - Audit and refresh
4. 🟢 **Add type hints everywhere** - Enable mypy checking

---

## Known Bugs

### 🟡 High

#### Geocoding Token Expiry

**Location**: `scripts/core/geocoding.py`

**Issue**:
- OneMap tokens expire unpredictably
- Auto-refresh doesn't always work
- Manual token refresh sometimes needed

**Symptoms**:
```
HTTPError: 401 Unauthorized
Failed to geocode after 3 attempts
```

**Workaround**:
```bash
uv run python scripts/utils/refresh_onemap_token.py
```

**Permanent Fix Needed**:
- Implement proper token expiry detection
- Add pre-emptive token refresh
- Better error handling and recovery

#### Missing Address Fields

**Location**: `scripts/core/stages/L1_process.py`

**Issue**:
- Some transactions missing address fields
- Causes geocoding to fail silently
- Results in incomplete data

**Symptoms**:
- Missing coordinates for some properties
- Inconsistent geocoding success rate

**Fix Needed**:
- Validate address fields before geocoding
- Log properties with missing addresses
- Add fallback strategies (e.g., use postal code only)

---

## Performance Metrics

### Current State

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Test Coverage | ~40% | 80% | 🟡 Below target |
| Avg File Size | 350 lines | <300 lines | 🟡 Slightly high |
| Max File Size | 1,879 lines | <500 lines | 🔴 Way over |
| Geocoding Speed | 1 addr/1.2s | 1 addr/0.5s | 🟡 Slow |
| Memory Usage | High (full load) | Medium | 🟡 Needs optimization |

### Improvement Targets

**Q1 2026**:
- Reduce max file size to <800 lines
- Add 50 test files
- Implement parallel geocoding
- Externalize MRT/school data

**Q2 2026**:
- Reach 70% test coverage
- Reduce max file size to <500 lines
- Implement chunked processing
- Complete documentation audit

---

## Debt Tracking Template

Use this template to track new debt:

```markdown
### [Priority] [File/Module]

**Description**: Brief description of the issue

**Impact**: Why this matters (performance, security, maintainability)

**Recommendation**: What should be done

**Effort**: Estimate (Low/Medium/High)

**Owner**: Who is responsible (leave blank if unassigned)

**Status**: Todo / In Progress / Done
```

---

## Summary

**🔴 Critical Issues**: 3
- L3_export.py too large
- Missing test coverage (analytics, data)
- Geocoding token expiry

**🟡 High Priority**: 8
- Large files (4 files >700 lines)
- Hardcoded data (MRT, schools)
- Sequential geocoding
- Duplicate L3 logic

**🟢 Medium Priority**: 6
- Missing type hints
- Documentation gaps
- Code quality issues

**✅ Well Managed**: 1
- Environment variable security

**Total Debt Items**: 18

**Recommended Focus**:
1. Split large files first (reduces complexity)
2. Add tests for core utilities (builds confidence)
3. Implement parallel geocoding (performance win)
4. Externalize hardcoded data (maintainability)

**Next Review**: 2026-03-31
