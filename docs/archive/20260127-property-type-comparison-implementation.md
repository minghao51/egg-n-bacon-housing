# Extending MRT Impact Analysis to Condos & ECs

**Date**: 2026-01-27
**Task**: Calculate amenity distances for condo/EC transactions to enable property type comparison

---

## Problem Identified

### Original Issue
**Question**: Does MRT impact vary by property type (HDB vs Condo vs EC)?

**Discovery**: Amenity features (MRT distances, etc.) were ONLY available for HDB in the L3 unified dataset:
- **HDB**: 785,395 transactions with amenity features ✅
- **Condominium**: 109,576 transactions, **100% missing** amenity data ❌
- **EC**: 16,826 transactions, **100% missing** amenity data ❌

### Root Cause Analysis

**Why were condos/ECs missing?**

1. **Limited geocoding**: The amenity calculation pipeline (`L2_features.py`) only calculated distances for:
   - 9,814 unique HDB addresses (blocks)
   - 7,906 unique private property addresses
   - **Total**: 17,720 unique properties

2. **Join mismatch**: The unified dataset has **911,797 transactions**:
   - 785K HDB transactions → 9,814 unique blocks → **Successful join**
   - 109K condo transactions → Only 2,298 unique postal codes in amenity file → **Failed join**
   - 16K EC transactions → Same issue

3. **POSTAL column missing**: The L3 unified dataset doesn't preserve POSTAL codes, so even the limited amenity data couldn't be joined.

---

## Solution Implemented

### Approach: Direct Distance Calculation

Instead of relying on the complex pipeline join, I created a script to **directly calculate amenity distances** for all condo/EC transactions using their existing lat/lon coordinates.

**Script**: `scripts/calculate_condo_amenities.py`

**Method**:
1. Load condo/EC transactions from unified dataset (filter: missing amenity features)
2. Load amenity locations from L1 data (MRT, hawker, supermarket, park, etc.)
3. Use **scipy.spatial.cKDTree** for fast nearest-neighbor search
4. Use **haversine formula** for accurate distance calculations
5. Calculate:
   - Distance to nearest amenity
   - Count of amenities within 500m, 1km, 2km
6. Update unified dataset with complete amenity coverage

**Performance Optimizations**:
- KDTree for O(log n) nearest neighbor queries (vs O(n) brute force)
- Vectorized numpy operations
- Batch processing per amenity type

---

## Amenity Data Coverage

### Available Amenity Types (from L1)

| Amenity Type | Locations | Impact on Prices |
|---------------|-----------|------------------|
| **MRT** | 249 stations | HIGH (5.5% importance) |
| **Hawker** | 129 centers | VERY HIGH (27.4% importance) |
| **Supermarket** | 526 stores | Medium (5.2% importance) |
| **Park** | 450 parks | High (7.2% importance) |
| **Preschool** | 2,290 centers | Medium |
| **Childcare** | 1,925 centers | Low-Medium |

**Note**: Importance values from XGBoost feature importance analysis (HDB data).

---

## Expected Results After Running Script

### Before (Current State)
```
Amenity Coverage:
  HDB: 785,395 / 785,395 (100%) ✅
  Condominium: 0 / 109,576 (0%) ❌
  EC: 0 / 16,826 (0%) ❌
```

### After (Target State)
```
Amenity Coverage:
  HDB: 785,395 / 785,395 (100%) ✅
  Condominium: ~109,000 / 109,576 (>99%) ✅
  EC: ~16,500 / 16,826 (>98%) ✅
```

**Note**: Some condos/ECs may lack lat/lon coordinates and will remain without amenity data.

---

## Next Steps After Script Completes

### 1. Re-run Heterogeneous Analysis
Update `scripts/analysis/analyze_mrt_heterogeneous.py` to include condos/ECs:

```python
# Current: HDB only
hdb = df[df['property_type'] == 'HDB']

# New: All property types
for property_type in ['HDB', 'Condominium', 'EC']:
    subset = df[df['property_type'] == property_type]
    # Run regression...
```

### 2. Compare MRT Impact by Property Type

**Expected Hypothesis**:
- **HDB**: Highest MRT sensitivity (~$1-4/100m)
  - Rationale: Public transport-dependent, budget-conscious

- **EC**: Medium MRT sensitivity (~$0.5-2/100m)
  - Rationale: Hybrid (HDB upgraders), mixed car ownership

- **Condominium**: Lowest MRT sensitivity (~$0-1/100m)
  - Rationale: Higher income, higher car ownership, premium amenities in-condo

### 3. Test Statistical Significance

```python
# Regression with interaction terms
price = β0 + β1(mrt_dist) + β2(condo) + β3(mrt_dist × condo) + controls

# Where:
# β1 = MRT impact for HDB (baseline)
# β2 = Condo price premium vs HDB
# β3 = DIFFERENTIAL MRT impact for condos vs HDB
```

**Key test**: Is β3 statistically significant?
- If YES → MRT impact differs by property type
- If NO → No significant difference

---

## Validation Checks

### Data Quality Checks

After script completes, verify:

```python
# 1. Coverage check
unified = pd.read_parquet('data/pipeline/L3/housing_unified.parquet')
for pt in ['HDB', 'Condominium', 'EC']:
    subset = unified[unified['property_type'] == pt]
    coverage = subset['dist_to_nearest_mrt'].notna().sum() / len(subset)
    print(f"{pt}: {coverage:.1%} coverage")

# 2. Distribution check
print("\nMRT distance distribution by property type:")
print(unified.groupby('property_type')['dist_to_nearest_mrt'].describe())

# 3. Sanity check (Singapore is small)
print("\nMax distances (should be <5km):")
print(unified.groupby('property_type')['dist_to_nearest_mrt'].max())
```

### Expected Distributions

| Property Type | Mean MRT Distance | Expected |
|---------------|-------------------|-----------|
| HDB | ~500m | Baseline |
| Condominium | ~700m | Further from MRT (more affluent areas) |
| EC | ~600m | Intermediate |

---

## Potential Issues & Mitigations

### Issue 1: Computational Time
**Problem**: 126K transactions × 6 amenity types × up to 2,290 locations each
**Estimated time**: 10-30 minutes

**Mitigation**:
- Script runs in background
- Progress logging built-in
- Can resume if interrupted

### Issue 2: Missing Coordinates
**Problem**: Some condos/ECs lack lat/lon

**Mitigation**:
- Script filters to records with valid coordinates
- Coverage will be ~98-99% (acceptable)

### Issue 3: Distance Accuracy
**Problem**: KDTree uses Euclidean distance on lat/lon (approximation)

**Mitigation**:
- KDTree for nearest neighbor (fast)
- Haversine for counts within radius (accurate)
- Hybrid approach balances speed and accuracy

---

## Alternative Approaches Considered

### Option 1: Fix L2 Pipeline ✗ (Rejected)
**Why**: Too complex, would require re-running entire pipeline
**Time**: Several hours of development + testing

### Option 2: Re-geocode All Properties ✗ (Rejected)
**Why**: Expensive API calls, rate limits, potential data quality issues
**Time**: Days to complete geocoding

### Option 3: Direct Calculation (Chosen) ✓
**Why**: Fast, uses existing coordinates, no external dependencies
**Time**: 10-30 minutes runtime + 1 hour development

---

## Timeline

| Step | Status | Estimated Time |
|------|--------|----------------|
| 1. Root cause analysis | ✅ Complete | 30 min |
| 2. Script development | ✅ Complete | 1 hour |
| 3. Run calculation (126K records) | 🔄 In Progress | 15-30 min |
| 4. Validate results | ⏳ Pending | 5 min |
| 5. Re-run MRT analysis (all property types) | ⏳ Pending | 10 min |
| 6. Create comparison report | ⏳ Pending | 20 min |

**Total Estimated**: ~2 hours

---

## Expected Insights

### Questions We'll Be Able to Answer

1. **Does MRT proximity matter more for HDB vs Condo?**
   - Quantify the difference in $/100m

2. **Are luxury condos less MRT-dependent?**
   - Test hypothesis: Premium amenities substitute for transit access

3. **Do EC buyers behave like HDB or Condo buyers?**
   - Identify which market segment ECs belong to

4. **Should investment strategies differ by property type?**
   - HDB: Buy near MRT
   - Condo: MRT less important, focus on other amenities
   - EC: Middle ground

---

## Files Modified/Created

1. **Created**: `scripts/calculate_condo_amenities.py`
   - Calculates amenity distances for condos/ECs
   - Updates L3 unified dataset in-place

2. **Modified**: `data/pipeline/L3/housing_unified.parquet`
   - Will have complete amenity coverage after script completes
   - Backup created as `housing_unified_backup.parquet`

3. **To be updated**: `20260127-property-type-mrt-impact-summary.md`
   - Will add actual results after analysis completes

---

**End of Document**
