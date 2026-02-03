# Singapore School Quality Scoring Methodology

## Overview

This document describes the methodology for calculating school quality scores to enable detection of school proximity premiums in Singapore housing prices.

## Data Sources

- **School Tiers (Secondary):** `school_tiers_secondary.csv`
  - IP schools with 2026 cut-off points
  - SAP and Autonomous status
  - School tier classification (1-3)

- **School Tiers (Primary):** `school_tiers_primary.csv`
  - GEP and SAP status
  - Popularity ratios (Phase 2B)
  - Tier classification (1-3)

- **Quality Weights:** `school_quality_weights.csv`
  - Feature importance weights
  - Calculation methods

## Quality Score Calculation

### Primary School Quality Score

```
quality_score = (
    (gep_program * 2.5) +
    (sap_status * 2.0) +
    (tier_1 * 3.0) +
    (tier_2 * 2.0) +
    (tier_3 * 1.0) +
    (popularity_score * 0.5) +
    MIN(1.0, sum_all_weights)
)
```

**Range:** 0-10 scale

### Secondary School Quality Score

```
quality_score = (
    (ip_track * 3.0) +
    (sap_status * 2.0) +
    (autonomous_status * 1.5) +
    (tier_1 * 3.0) +
    (tier_2 * 2.0) +
    (tier_3 * 1.0) +
    (ip_cutoff_quality * 1.5) +
    (academic_awards * 0.5) +
    MIN(1.0, sum_all_weights)
)
```

**Range:** 0-10 scale

## Distance Decay Function

School proximity premium should use exponential decay:

```python
def school_accessibility_score(distance_m, quality_score):
    """
    Calculate school accessibility score with distance decay.

    Args:
        distance_m: Distance to school in meters
        quality_score: School quality score (0-10)

    Returns:
        Accessibility score (0-1)
    """
    # Distance decay: half-value at 500m, negligible at 2km
    distance_factor = max(0, 1 - (distance_m / 2000))

    # Quality amplification: better schools have wider catchment
    quality_amplification = 1 + (quality_score / 10)

    return distance_factor * quality_amplification * quality_score / 10
```

## Aggregate School Features

For each property, calculate:

1. **Primary School Accessibility:**
   - Distance-weighted score of nearest primary school
   - Count of GEP/SAP schools within 1km

2. **Secondary School Accessibility:**
   - Distance-weighted score of nearest secondary school
   - Count of IP/SAP schools within 1km

3. **Overall School Accessibility:**
   - Weighted combination: 0.4 * primary + 0.6 * secondary
   - Reflects secondary school priority in housing decisions

## Implementation Steps

1. **Load School Quality Data:**
   ```python
   primary_tiers = pd.read_csv('school_tiers_primary.csv')
   secondary_tiers = pd.read_csv('school_tiers_secondary.csv')
   ```

2. **Calculate Quality Scores:**
   ```python
   primary_tiers['quality_score'] = calculate_primary_quality(primary_tiers)
   secondary_tiers['quality_score'] = calculate_secondary_quality(secondary_tiers)
   ```

3. **Merge with School Coordinates:**
   ```python
   schools_df = schools_df.merge(tiers_df, on='school_name', how='left')
   schools_df['quality_score'] = schools_df['quality_score'].fillna(0)
   ```

4. **Calculate Distance-Weighted Scores:**
   ```python
   for property in properties:
       nearest_school = find_nearest_school(property, schools_df)
       distance = calculate_distance(property, nearest_school)

       property['school_accessibility'] = school_accessibility_score(
           distance,
           nearest_school['quality_score']
       )
   ```

## Expected Impact

With quality-weighted features, the analysis should detect:

1. **IP School Premium:** 5-15% price premium within 1km of RI/HCI/NYGH
2. **SAP School Premium:** 3-8% price premium near top SAP schools
3. **GEP Primary Premium:** 5-10% price premium near GEP primary schools
4. **Distance Decay:** Exponential decrease in premium with distance

## Validation

Validate quality scores by:
1. Checking correlation with PSLE cut-off points
2. Comparing with Phase 2B popularity ratios
3. Testing price prediction model performance improvement
4. Verifying school premium detection in known hotspots (Bukit Timah, Marine Parade)

## References

- MOE School Directory: https://www.moe.gov.sg/schoolfinder
- PSLE Cut-off Points 2026: https://www.fa.edu.sg/psle-cut-off-points/
- School Rankings: https://sgschooling.com/secondary/cop/all
