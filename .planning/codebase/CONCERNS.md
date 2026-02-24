# Technical Debt & Concerns

## Active TODO Comments

**6 TODOs requiring attention:**

| File | Line | Description | Priority |
|------|------|-------------|----------|
| `scripts/generate_segments_data.py` | 247 | Implement in next task | Medium |
| `scripts/generate_segments_data.py` | 586 | Add from forecast data | Low |
| `scripts/generate_segments_data.py` | 588 | Calculate from data | Low |
| `scripts/generate_segments_data.py` | 611 | Will be used in future for hotspot integration | Low |
| `scripts/data/fetch_macro_data.py` | 154 | Replace with actual MAS API call | Medium |
| `scripts/analytics/pipelines/calculate_l3_metrics_pipeline.py` | 12-13 | Affordability index needs income data, ROI potential score needs rental data | Medium |

---

## Large Files Requiring Refactoring

**Critical (> 1000 lines):**

| File | Lines | Issues | Recommendation |
|------|-------|--------|----------------|
| `scripts/core/stages/L3_export.py` | 1,696 | Too large, hard to maintain | Split into smaller modules by function |
| `scripts/core/stages/webapp_data_preparation.py` | 998 | Complex dashboard data prep | Extract dashboard-specific functions |

**High Priority (> 700 lines):**

| File | Lines | Issues | Recommendation |
|------|-------|--------|----------------|
| `scripts/core/metrics.py` | 914 | Complex statistical calculations | Extract metric calculation functions |
| `scripts/core/stages/L2_features.py` | 808 | Complex feature engineering | Split by feature type |
| `scripts/analytics/analysis/mrt/analyze_mrt_impact.py` | 796 | Large analysis file | Extract helper functions |
| `scripts/analytics/analysis/market/analyze_lease_decay_advanced.py` | 766 | Complex lease decay modeling | Extract model functions |
| `scripts/core/school_features.py` | 726 | School feature engineering | Extract by school tier |
| `scripts/generate_segments_data.py` | 664 | Segment generation with TODOs | Complete TODOs, then refactor |

---

## Performance Issues

### Inefficient DataFrame Operations

**Anti-Pattern: Using `iterrows()`**

Found in multiple files (anti-pattern for performance):
- `scripts/core/mrt_distance.py:76`
- `scripts/core/school_features.py:262, 376, 385, 583`

**Issue:** `iterrows()` is extremely slow for large DataFrames

**Solution:** Use vectorized operations
```python
# ✗ Bad
for idx, row in df.iterrows():
    df.loc[idx, 'result'] = row['a'] + row['b']

# ✓ Good
df['result'] = df['a'] + df['b']
```

### Geocoding Performance

**Issue:** Sequential API calls with 1.2 second delays

**Location:** `scripts/core/geocoding.py`

**Impact:** Geocoding 10,000 addresses takes ~3.3 hours

**Solutions:**
1. Increase parallel workers (currently underutilized)
2. Implement batch geocoding API calls
3. Cache results more aggressively
4. Consider dedicated geocoding service

### Memory Usage

**Issue:** Large datasets loaded entirely into memory

**Impact:** High memory usage for large parquet files

**Solutions:**
1. Implement chunked processing for large files
2. Use PyArrow memory mapping for large datasets
3. Process data in batches
4. Add memory profiling to identify bottlenecks

### String Formatting in Loops

**Found in multiple files:**
```python
# ✗ Bad - Repeated string formatting in loop
df['column'] = df['column'].apply(lambda x: f"${x:,.0f}")

# ✓ Good - Vectorized formatting
df['column'] = df['column'].map("${:,.0f}".format)
```

**Impact:** Performance degradation on large datasets

---

## Security Concerns

### Status: Generally Good

**Strengths:**
- ✅ All API keys loaded from environment variables
- ✅ No hardcoded secrets found
- ✅ `.env` file not in git
- ✅ `.env.example` provides template

**Minor Concerns:**
- ⚠️ No pre-commit secret scanning (recommended)
- ⚠️ Some beta packages in dependencies could have vulnerabilities
- ⚠️ Password logged potentially in `geocoding.py:79`

**Recommendations:**
1. Add pre-commit secret scanning (e.g., truffleHog)
2. Audit dependencies for vulnerabilities
3. Review logging to ensure no sensitive data in logs

---

## Code Smells

### Excessive Lambda Functions

**Issue:** Overuse of `apply(lambda x: ...)` for simple operations

**Example:**
```python
# ✗ Bad - Lambda for simple operation
df['price_per_sqft'] = df.apply(lambda x: x['price'] / x['area'], axis=1)

# ✓ Good - Vectorized operation
df['price_per_sqft'] = df['price'] / df['area']
```

**Found in:** Multiple feature engineering files

### Nested Loops

**Issue:** Nested loops for data processing

**Found in:**
- School features calculation
- MRT distance calculation (with iterrows)

**Impact:** O(n²) or worse complexity

**Solution:** Use spatial indexes (e.g., H3, KD-tree) for distance calculations

### Magic Numbers

**Found in:** Various analysis scripts

**Example:**
```python
# ✗ Bad - Magic number
if distance < 1000:
    pass

# ✓ Good - Named constant
MRT_NEARBY_THRESHOLD_METERS = 1000
if distance < MRT_NEARBY_THRESHOLD_METERS:
    pass
```

---

## Missing Error Handling

### Limited Retry Logic

**Issue:** Only geocoding has retry logic (tenacity)

**Missing in:**
- API calls to data.gov.sg (no retry)
- SingStat API calls (no retry)
- File operations (no retry)

**Solution:** Add @retry decorator to all external API calls

### API Response Validation

**Issue:** Limited validation of API responses

**Risk:** Unexpected API responses could crash pipeline

**Solution:** Add schema validation for API responses

### Data Validation

**Issue:** Manual CSV uploads not validated

**Risk:** Invalid data could corrupt pipeline

**Solution:** Add schema validation for manual uploads

---

## Testing Gaps

### Missing Test Coverage

**No tests for:**
- `scripts/analytics/` - Large module with no test coverage
- `scripts/data/` - Data processing scripts
- `scripts/generate_segments_data.py` - Segment generation

**Coverage Goals:**
- Current: Core modules (~70%)
- Target: All modules ≥ 80%

**Recommendations:**
1. Prioritize test coverage for analytics modules
2. Add integration tests for data processing
3. Add property-based tests for feature engineering

### Test Data Management

**Issue:** Test data scattered across test files

**Solution:** Centralize test data in `tests/fixtures/`

---

## Documentation Issues

### Outdated Documentation

**Potential issues:**
- Architecture docs may not reflect recent changes
- Some README sections may be outdated
- API documentation may be incomplete

**Recommendations:**
1. Regularly review and update docs
2. Add docstrings to all public functions
3. Create API documentation with Sphinx/MkDocs

### Missing Documentation

**Not documented:**
- Recent changes to hooks (`useAnalyticsData`, `useLeaderboardData`, `useSegmentsData`)
- New constants directory (`app/src/constants/`)
- New gzip utility (`app/src/utils/gzip.ts`)
- New hook (`app/src/hooks/useGzipJson.ts`)

---

## Dependency Concerns

### Beta Packages

**Found in dependencies:**
- `h3==4.1.0b2` - Beta version

**Risk:** Potential bugs or API changes

**Recommendation:** Monitor for stable release, update when available

### Unused Dependencies

**Configured but not actively used:**
- Supabase client
- Langchain components
- Google AI SDK
- Jina AI

**Recommendation:** Remove if not needed, or document future use cases

---

## Scalability Concerns

### Current Limitations

1. **Single-Machine Processing:**
   - No distributed processing
   - Limited by single machine memory

2. **No Checkpoint System:**
   - Pipeline failures require full re-run
   - No incremental updates

3. **No Database:**
   - All data in Parquet files
   - No query optimization
   - No concurrent access

### Future Scalability Options

1. **Chunked Processing:**
   - Process large files in batches
   - Reduce memory usage

2. **Distributed Computing:**
   - Use Dask or Ray for parallel processing
   - Scale horizontally

3. **Database Migration:**
   - PostGIS for spatial queries
   - Enable concurrent access
   - Optimize queries

---

## Recent Changes (Unreviewed)

**Modified files not yet reviewed:**
- `app/src/hooks/useAnalyticsData.ts`
- `app/src/hooks/useLeaderboardData.ts`
- `app/src/hooks/useSegmentsData.ts`
- `app/src/utils/gzip.ts`

**New files not documented:**
- `app/src/constants/` (new directory)
- `app/src/hooks/useGzipJson.ts` (new hook)

**Recommendation:** Review and document these changes

---

## Priority Action Items

### Immediate (This Sprint)

1. ✅ **Address 6 active TODO comments**
   - Complete incomplete functionality
   - Remove or defer if not needed

2. ✅ **Replace `iterrows()` with vectorized operations**
   - `scripts/core/mrt_distance.py:76`
   - `scripts/core/school_features.py:262, 376, 385, 583`

3. ✅ **Add pre-commit secret scanning**
   - Install truffleHog or similar
   - Add to pre-commit hooks

### Short-Term (1-2 Months)

4. ✅ **Refactor `L3_export.py` (1,696 lines)**
   - Split into smaller modules
   - Extract common patterns

5. ✅ **Implement chunked processing**
   - Process large files in batches
   - Reduce memory usage

6. ✅ **Add retry logic to all API calls**
   - Use tenacity decorator
   - Handle rate limiting

7. ✅ **Create pipeline checkpoint system**
   - Save intermediate state
   - Enable incremental updates

8. ✅ **Add test coverage for analytics modules**
   - Prioritize high-impact modules
   - Target ≥ 80% coverage

### Long-Term (3-6 Months)

9. ✅ **Performance optimization**
   - Geocoding (parallel workers)
   - MRT/school distance calculations (spatial indexes)
   - Memory profiling and optimization

10. ✅ **Data validation schema**
    - API response validation
    - Manual upload validation
    - Parquet schema validation

11. ✅ **Documentation improvements**
    - Complete missing docs
    - Update outdated sections
    - Add API documentation

12. ✅ **Evaluate distributed processing**
    - Assess Dask/Ray for pipeline
    - Implement if needed

---

## Debt Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| **TODO Count** | 6 | 0 | ⚠️ Needs attention |
| **Large Files (>1000 lines)** | 1 | 0 | ⚠️ Refactor needed |
| **Large Files (>700 lines)** | 6 | 2 | ⚠️ Refactor needed |
| **Test Coverage (core)** | ~70% | ≥80% | ⚠️ Improve coverage |
| **Test Coverage (analytics)** | ~0% | ≥60% | ❌ Critical |
| **iterrows() usage** | 5 locations | 0 | ❌ Must fix |
| **API retry logic** | 1/5 services | 5/5 | ⚠️ Add retry |
| **Secret scanning** | No | Yes | ⚠️ Add to CI/CD |

---

## Summary

### Overall Health: ⚠️ Moderate Concern

**Strengths:**
- Good code organization and structure
- Comprehensive error handling in core modules
- Security best practices (environment variables)
- Clear separation of concerns

**Areas for Improvement:**
- Complete TODO comments (6 outstanding)
- Refactor large files (1 critical, 6 high priority)
- Replace `iterrows()` with vectorized operations (5 locations)
- Add test coverage for analytics modules (currently 0%)
- Implement retry logic for all API calls
- Add pre-commit secret scanning

**Risk Level:** Medium
- Performance issues will worsen with data growth
- Missing test coverage increases bug risk
- Large files are maintenance liabilities

**Recommended Approach:**
1. Address immediate concerns (TODOs, iterrows)
2. Refactor large files incrementally
3. Improve test coverage
4. Add performance optimizations
5. Implement scalability improvements

---

*Last Updated: 2025-02-24*
*Next Review: 2025-03-24*
