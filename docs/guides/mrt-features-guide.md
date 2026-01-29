# Enhanced MRT Features - Quick Reference Guide

## Overview

The enhanced MRT distance feature provides **8 columns** of information for each property, enabling sophisticated analysis of transport accessibility.

---

## Column Reference

### 1. `nearest_mrt_name`
**Type**: `string`
**Description**: Name of closest MRT station
**Example**: `"ANG MO KIO INTERCHANGE"`
**Use Case**: Location reference, matching with external data

### 2. `nearest_mrt_distance`
**Type**: `float`
**Description**: Distance in meters to closest MRT station
**Example**: `386.5`
**Use Case**: Proximity filtering, accessibility scoring

### 3. `nearest_mrt_lines`
**Type**: `list[string]`
**Description**: MRT line codes (e.g., ['NSL', 'EWL'])
**Example**: `['NSL']` or `['NSL', 'EWL', 'CCL']`
**Use Case**: Line-specific analysis, filtering by line

### 4. `nearest_mrt_line_names`
**Type**: `list[string]`
**Description**: Full line names
**Example**: `['North-South Line']` or `['North-South Line', 'East-West Line']`
**Use Case**: Display, reporting, user-facing text

### 5. `nearest_mrt_tier`
**Type**: `int`
**Description**: Importance tier (1=highest, 3=lowest)
**Example**: `1`, `2`, or `3`
**Use Case**: Categorical feature, quick importance filter

### 6. `nearest_mrt_is_interchange`
**Type**: `boolean`
**Description**: Whether station connects 2+ lines
**Example**: `True` or `False`
**Use Case**: Interchange premium, transfer convenience

### 7. `nearest_mrt_colors`
**Type**: `list[string]`
**Description**: Hex color codes for visualization
**Example**: `['#DC241F']` or `['#DC241F', '#009640']`
**Use Case**: Map visualization, UI elements

### 8. `nearest_mrt_score`
**Type**: `float`
**Description**: Overall accessibility score (higher = better)
**Example**: `7.77` or `13.20`
**Use Case**: Property ranking, sorting, comparison

---

## Quick Examples

### Filter by Tier
```python
# Only properties near major MRT lines
tier1 = df[df['nearest_mrt_tier'] == 1]

# Exclude LRT (tier 3)
major_lines_only = df[df['nearest_mrt_tier'] <= 2]
```

### Filter by Distance
```python
# Within walking distance (500m)
walking_distance = df[df['nearest_mrt_distance'] <= 500]

# Within 10-minute walk (800m)
close_mrt = df[df['nearest_mrt_distance'] <= 800]
```

### Filter by Interchange
```python
# Properties near interchanges (best connectivity)
interchange = df[df['nearest_mrt_is_interchange'] == True]
```

### Filter by Score
```python
# Excellent accessibility (score > 10)
excellent = df[df['nearest_mrt_score'] > 10]

# Good accessibility (score > 5)
good = df[df['nearest_mrt_score'] > 5]
```

### Combined Filters
```python
# Prime properties: Tier 1, within 500m, interchange
prime = df[
    (df['nearest_mrt_tier'] == 1) &
    (df['nearest_mrt_distance'] <= 500) &
    (df['nearest_mrt_is_interchange'] == True)
]

# Budget-friendly: Within 1km, any tier
affordable = df[df['nearest_mrt_distance'] <= 1000]
```

---

## Common Queries

### "Which properties have the best MRT access?"
```python
top_10 = df.nlargest(10, 'nearest_mrt_score')
```

### "How many properties are within walking distance of Tier 1 stations?"
```python
count = len(df[
    (df['nearest_mrt_tier'] == 1) &
    (df['nearest_mrt_distance'] <= 500)
])
```

### "What are the most common MRT stations?"
```python
top_stations = df['nearest_mrt_name'].value_counts().head(10)
```

### "Which stations are interchanges?"
```python
interchange_stations = df[
    df['nearest_mrt_is_interchange'] == True
]['nearest_mrt_name'].unique()
```

---

## Analysis Examples

### Price vs Distance Analysis
```python
# Group by distance ranges
df['distance_bin'] = pd.cut(
    df['nearest_mrt_distance'],
    bins=[0, 500, 1000, 1500, float('inf')],
    labels=['<500m', '500-1km', '1-1.5km', '>1.5km']
)

# Compare prices
price_by_distance = df.groupby('distance_bin')['price'].mean()
```

### Tier Premium Analysis
```python
# Calculate premium for each tier
tier_premium = df.groupby('nearest_mrt_tier')['price_psf'].agg([
    ('mean_psf', 'mean'),
    ('median_psf', 'median'),
    ('count', 'count')
])
```

### Interchange Premium
```python
# Compare interchange vs non-interchange
interchange_premium = df.groupby('nearest_mrt_is_interchange')['price_psf'].mean()
premium_pct = (interchange_premium[True] / interchange_premium[False] - 1) * 100
```

### Score Correlation
```python
# Correlation between score and price
correlation = df[['nearest_mrt_score', 'price_psf']].corr().iloc[0, 1]
```

---

## Visualization Examples

### Map Colored by Tier
```python
import plotly.express as px

fig = px.scatter_mapbox(
    df,
    lat='lat',
    lon='lon',
    color='nearest_mrt_tier',
    color_continuous_scale=['red', 'yellow', 'green'],
    mapbox_style='open-street-map',
    title='Properties by MRT Tier'
)
fig.show()
```

### Map Colored by Score
```python
fig = px.scatter_mapbox(
    df,
    lat='lat',
    lon='lon',
    color='nearest_mrt_score',
    color_continuous_scale='RdYlGn',
    mapbox_style='open-street-map',
    title='Properties by MRT Accessibility Score'
)
fig.show()
```

### Distance Distribution
```python
import matplotlib.pyplot as plt

plt.hist(df['nearest_mrt_distance'], bins=50)
plt.xlabel('Distance to MRT (m)')
plt.ylabel('Number of Properties')
plt.title('MRT Distance Distribution')
plt.show()
```

### Tier Distribution
```python
tier_counts = df['nearest_mrt_tier'].value_counts().sort_index()
tier_counts.plot(kind='bar')
plt.xlabel('MRT Tier')
plt.ylabel('Number of Properties')
plt.title('Properties by MRT Tier')
plt.show()
```

---

## Machine Learning Features

### Feature Engineering
```python
# Create binary features
df['within_500m'] = (df['nearest_mrt_distance'] <= 500).astype(int)
df['within_1km'] = (df['nearest_mrt_distance'] <= 1000).astype(int)
df['is_tier1'] = (df['nearest_mrt_tier'] == 1).astype(int)
df['is_interchange'] = df['nearest_mrt_is_interchange'].astype(int)

# Create categorical features
df['tier_category'] = df['nearest_mrt_tier'].astype('category')

# Log transform score
df['log_score'] = np.log1p(df['nearest_mrt_score'])
```

### Feature Selection for Price Prediction
```python
features = [
    'nearest_mrt_distance',
    'nearest_mrt_tier',
    'nearest_mrt_is_interchange',
    'nearest_mrt_score',
    'within_500m',
    'within_1km'
]

X = df[features]
y = df['price_psf']
```

---

## Performance Tips

### Indexing
```python
# Create index for faster filtering
df.set_index('nearest_mrt_tier', inplace=True)

# Filter faster
tier1 = df.loc[1]
```

### Categorical Types
```python
# Convert to categorical for memory efficiency
df['nearest_mrt_tier'] = df['nearest_mrt_tier'].astype('category')
df['nearest_mrt_name'] = df['nearest_mrt_name'].astype('category')
```

### Sparse Representation
```python
# For very large datasets, use sparse matrices for lines
from sklearn.feature_extraction import FeatureHasher

hasher = FeatureHasher(n_features=10, input_type='string')
line_features = hasher.transform(df['nearest_mrt_lines'])
```

---

## Troubleshooting

### Issue: Missing MRT Data
```python
# Check for missing values
missing = df['nearest_mrt_name'].isna().sum()
print(f"Properties without MRT data: {missing}")
```

### Issue: Invalid Coordinates
```python
# Check coordinate ranges
valid_lat = df['lat'].between(1.2, 1.5)
valid_lon = df['lon'].between(103.6, 104.0)
df = df[valid_lat & valid_lon]
```

### Issue: Outlier Distances
```python
# Check for impossible distances (>5km)
df = df[df['nearest_mrt_distance'] <= 5000]
```

---

## Best Practices

1. **Always validate** MRT distance data before analysis
2. **Use tier** as categorical feature, not continuous
3. **Prefer score** over single distance for ranking
4. **Combine MRT features** with other amenities (bus, shops, etc.)
5. **Update station mapping** when new MRT lines open
6. **Document** any custom thresholds used in analysis

---

## Reference

- **Full Documentation**: `20260126-mrt-enhanced-complete.md`
- **Test Script**: `test_mrt_enhanced.py`
- **Module**: `core/mrt_distance.py`
- **Mapping**: `core/mrt_line_mapping.py`

---

**Last Updated**: 2026-01-26
**Version**: 2.0 (Enhanced)
