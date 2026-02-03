# School Features Calculation Optimization

**Date**: 2026-02-03
**Status**: ✅ Implemented
**File**: `scripts/core/school_features.py`

## Problem

The `calculate_school_features()` function was processing all ~1.1M property records individually, even though many properties share the same lat/lon coordinates (multiple transactions per property address). This resulted in redundant KDTree queries and distance calculations.

## Solution

**Aggregate to unique lat/lon combinations, calculate once, then map back to all records.**

### Key Changes

1. **New Helper Function**: `_create_unique_location_index()`
   - Identifies unique lat/lon pairs from the property dataset
   - Creates a bidirectional mapping between unique locations and original indices
   - Returns both the unique coordinates DataFrame and the index mapping

2. **Modified Core Loop** (lines 485-580):
   - **Before**: Iterated through all 1.1M records
   - **After**: Iterates through only unique locations (~50K-100K expected)
   - Stores calculated features in a `unique_features` DataFrame instead of `properties_df`

3. **Feature Mapping** (new section after loop):
   - Maps calculated features from unique locations back to all original records
   - Uses the `index_mapping` dictionary to efficiently propagate values

4. **Updated Logging**:
   - Changed progress interval from 10,000 to 1,000 (fewer records to process)
   - Added logging for unique location reduction
   - Added logging for feature mapping step

## Expected Performance Improvement

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Records processed | ~1.1M | ~50K-100K | **10-20x reduction** |
| KDTree queries | 1.1M × N | 50K × N | **10-20x fewer** |
| Processing time | ~30-60 min | ~2-5 min | **10-20x faster** |

## Implementation Details

### `_create_unique_location_index()` Function

```python
def _create_unique_location_index(properties_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Create unique location index and mapping back to original indices."""
    # Get unique lat/lon combinations
    unique_coords = properties_df[['lat', 'lon']].drop_duplicates()

    # Create mapping from unique coordinates back to original indices
    coord_to_idx = {}
    for orig_idx, row in properties_df[['lat', 'lon']].iterrows():
        coord_key = (row['lat'], row['lon'])
        if coord_key not in coord_to_idx:
            coord_to_idx[coord_key] = []
        coord_to_idx[coord_key].append(orig_idx)

    # Convert to index mapping
    index_mapping = {i: coord_to_idx[(row['lat'], row['lon'])]
                     for i, row in unique_coords.reset_index(drop=True).iterrows()}

    return unique_coords, index_mapping
```

### Modified Processing Flow

1. Create unique location index from properties with coordinates
2. Initialize `unique_features` DataFrame with all required columns
3. Process only unique locations in the main loop
4. Map calculated features back to all original records using `index_mapping`

## Verification

To verify correctness after running:

```python
import pandas as pd

# Load data
df = pd.read_parquet('data/pipeline/L3/housing_unified.parquet')

# 1. Check that all records with coordinates have school features
assert df['school_accessibility_score'].notna().sum() == df['lat'].notna().sum()

# 2. Verify same lat/lon has same school features
dupes = df[df.duplicated(['lat', 'lon'], keep=False)]
grouped = dupes.groupby(['lat', 'lon'])
for (lat, lon), group in grouped:
    assert group['school_accessibility_score'].nunique() == 1
```

## Risk Assessment

**Low Risk**: Pure performance optimization with no logic changes.

**Potential Mitigations**:
- Memory usage for `index_mapping` dict is acceptable (~50K-100K entries)
- Coordinate precision handled naturally by pandas `drop_duplicates()`
- Change is isolated to `school_features.py` and can be easily reverted

## Rollback Plan

If issues arise:
1. Revert `scripts/core/school_features.py` to git HEAD
2. No data pipeline changes required
3. No downstream impact on other scripts
