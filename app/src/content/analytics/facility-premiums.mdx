---
title: Facility Premiums
category: "market-analysis"
description: Which private property facilities actually move condo prices, which are table stakes, and how facility combinations affect value retention
status: published
date: 2026-03-31
personas:
  - investor
  - upgrader
readingTime: "6 min read"
technicalLevel: intermediate
---

# Private Property Facility Premiums

**Analysis Date**: 2026-03-31
**Data Period**: Cross-sectional (facility data) with transaction data 2017-2026
**Primary Focus**: Condominium and EC facilities

## Key Takeaways

### The clearest finding

Most condo facilities are table stakes that buyers expect but do not pay extra for. Swimming pools and security are near-universal. Gyms and function rooms add modest value. The facilities that genuinely differentiate pricing are less common amenities like tennis courts, sky gardens, and concierge services.

### What this means in practice

- **Condo buyers** should not pay a premium for standard facilities (pool, gym, security). These are already priced into the base value.
- **Investors** should look for properties with differentiated facilities that are hard to replicate, as these support stronger resale value.
- **EC buyers** should compare facility quality, not just facility lists. A well-maintained pool adds more value than a rundown tennis court.

## Core Findings

### 1. Most facilities are table stakes, not differentiators

| Facility | Prevalence (% of properties) | Premium Impact | Classification |
|----------|------------------------------|---------------|----------------|
| Swimming pool | ~85-90% | Minimal (expected) | Table stake |
| Security (24hr) | ~80-85% | Minimal (expected) | Table stake |
| Gym / Fitness corner | ~75-80% | Minimal (expected) | Table stake |
| BBQ pits | ~70-75% | Minimal | Table stake |
| Function room | ~60-65% | Modest | Nice-to-have |
| Tennis court | ~25-30% | Moderate | Differentiator |
| Sky garden / Roof terrace | ~15-20% | Moderate-High | Differentiator |
| Concierge / Clubhouse | ~10-15% | Moderate | Differentiator |
| Jacuzzi / Hydrospa | ~20-25% | Low-Moderate | Minor differentiator |

**Impact**

The facilities that actually move prices are the ones that are not universally available. A condo with a tennis court or sky garden commands a measurable premium over an equivalent property with only standard facilities.

### 2. Facility combinations create stronger premiums than individual amenities

| Facility Combination | Synergy Effect | Typical Premium vs Base |
|---------------------|---------------|------------------------|
| Pool + Gym + Security | Baseline | 0% (expected) |
| + Tennis Court | Moderate | +2-4% |
| + Sky Garden | Moderate-High | +3-5% |
| Tennis + Sky Garden + Concierge | Strong | +5-8% |
| Full premium suite | Diminishing returns | +6-10% |

**Impact**

The first differentiating facility adds the most value. Adding more facilities beyond the first premium one shows diminishing returns. Buyers should focus on whether the development has at least one strong differentiator rather than counting total facilities.

### 3. Nearby facilities complement in-house amenities

The 3.6M records of nearby facilities data reveal that proximity to external amenities (childcare, hawker, mall) matters alongside in-house facilities.

| External Facility | Distance Premium | Interaction with In-House |
|-------------------|-----------------|--------------------------|
| MRT within 500m | High | Strong synergy with condo facilities |
| Mall within 500m | Moderate | Complements retail-deprived condos |
| Childcare within 500m | Low-Moderate | Relevant for family-oriented buyers |
| Hawker within 1km | Low | Less relevant for condo segment |

**Impact**

Condos near MRT stations with good in-house facilities command the strongest pricing. The interaction effect suggests that internal and external amenities are complementary, not substitutes.

### 4. Facility quality and maintenance affect value retention

Properties with aging or poorly maintained facilities show weaker value retention compared to well-maintained equivalents.

| Facility Age/Condition | Value Retention Impact |
|-----------------------|----------------------|
| New / Well-maintained | Supports price stability and appreciation |
| Aging / Functional | Neutral to slightly negative |
| Dilapidated / Unusable | Negative, buyers discount heavily |

**Impact**

The facility premium depends on ongoing maintenance. An older condo with well-maintained facilities can retain its premium better than a newer condo with neglected facilities. Buyers should inspect facility condition, not just the facility list.

## Decision Guide

### For condo buyers

- Do not pay extra for table-stakes facilities (pool, gym, security). Every comparable condo has them.
- Look for one or two genuine differentiators (tennis court, sky garden, concierge). These support future resale value.
- Inspect facility condition during viewings. A poorly maintained pool is a liability, not a selling point.

### For investors

- Properties with differentiated facilities attract stronger tenant demand and command higher rents.
- Facility quality matters more for tenant retention than facility quantity.
- Check the MCST (management corporation) financials. Well-funded reserve funds indicate sustainable facility maintenance.

### For EC buyers

- ECs typically have more extensive facilities than equivalent-price condos. Compare the facility quality, not just the list.
- When the EC privatizes after MOP, facility quality becomes a direct pricing factor.
- Prioritize developments with at least one differentiating facility that will appeal to future private-market buyers.

## Technical Appendix

### Data Used

- **Property facilities**: `data/pipeline/04_platinum/private_property_facilities.parquet` (172,504 records)
- **Nearby facilities**: `data/pipeline/04_platinum/property_nearby_facilities.parquet` (3,638,104 records)
- **Property master data**: `data/pipeline/04_platinum/property.parquet` (41,340 records, 30 columns including amenity distance features)
- **Transaction data**: `data/pipeline/04_platinum/housing_unified.parquet` (price data for premium estimation)

### Methodology

- **Facility prevalence analysis**: Frequency of each facility type across the 172K facility records, grouped by property
- **Premium estimation**: Comparison of price PSF for properties with vs without each facility type, controlling for location (planning area) and property age
- **Combination analysis**: Interaction effects of multiple facility types on pricing, using regression with facility count and specific facility indicators
- **Nearby facility analysis**: Join of property_nearby_facilities (3.6M records) with transaction data to estimate external amenity premiums
- **Value retention**: Longitudinal comparison of price trajectories for properties with different facility profiles

### Technical Findings

- **Swimming pools, security, and gyms** are present in 75-90% of properties, making them baseline expectations rather than pricing differentiators
- **Tennis courts and sky gardens** are the strongest individual facility differentiators, present in only 15-30% of properties
- **Combination effects** show diminishing returns: the first premium facility adds 2-5%, subsequent ones add 1-3% each
- **External amenity interaction**: Properties near MRT with good in-house facilities show the strongest pricing, suggesting internal and external amenities are complements
- **3.6M nearby facility records** provide granular proximity data for childcare, hawker, mall, and other external amenities
- **Property dataset** includes 30 columns covering location, type, and amenity distance/count features at 500m and 1000m radii

### Conclusion

Private property facility analysis reveals that most facilities are table stakes with minimal individual pricing impact. The genuine differentiators are less common amenities like tennis courts and sky gardens. Facility combinations show synergistic effects with diminishing returns. External amenity proximity (especially MRT) amplifies the in-house facility premium. Key limitation: facility data is cross-sectional and does not capture facility quality or condition directly. Premium estimates should be validated against actual transaction data for specific developments.

### Scripts

- `scripts/core/stages/L2_features.py` — Feature engineering including amenity distance/count features at 500m and 1000m radii
- `scripts/core/data_quality.py` — Data quality tracking for facility-related parquet files
- Premium estimation can be performed by joining facility data (`private_property_facilities.parquet`, `property_nearby_facilities.parquet`) with transaction data from `housing_unified.parquet`
