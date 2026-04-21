---
title: Rental Hotspots
category: "market-analysis"
description: Where HDB rental premiums cluster geographically, how persistent those clusters are, and how to interpret hotspot status without overclaiming
status: published
date: 2026-02-20
personas:
  - investor
  - first-time-buyer
  - upgrader
readingTime: "6 min read"
technicalLevel: intermediate
---

# Singapore Rental Hotspots

**Analysis Date**: 2026-02-20  
**Data Period**: 2024-01 to 2025-01  
**Property Type**: HDB rentals

## Key Takeaways

### The clearest finding

Rental premiums cluster geographically rather than appearing randomly. A small number of areas consistently command above-market rents, while coldspots show structural discounts.

### What this means in practice

- **Investors** can use hotspot status as a rental-demand signal, not as a guarantee of capital appreciation.
- **Homebuyers** should avoid assuming that rental hotspots automatically justify an owner-occupier premium.
- **Value-seekers** may find better space-for-budget trade-offs in persistent coldspots.

## Core Findings

### 1. Hotspots are concentrated and statistically selective

<div data-chart-metadata="true" data-chart="comparison" data-chart-title="Top rental hotspots and coldspots" data-chart-columns="Gi* Statistic,Median Monthly Rent"></div>

| Area | Gi* Statistic | Median Monthly Rent | Interpretation |
|------|---------------|---------------------|----------------|
| Orchard | 4.21 | $3,200 | Strong hotspot |
| Marina South | 3.89 | $3,450 | Strong hotspot |
| Bukit Timah | 3.45 | $3,100 | Strong hotspot |
| Woodlands | -3.21 | $2,100 | Strong coldspot |
| Yishun | -2.98 | $2,050 | Strong coldspot |
| Sembawang | -2.67 | $2,000 | Strong coldspot |

Only **12 H3 cells** qualified as 99% confidence hotspots, which is a useful reminder that true hotspots are limited rather than widespread.

### 2. The rent gap is large

| Comparison | Value |
|-----------|-------|
| Hotspot median rent | $3,200 |
| Coldspot median rent | about 1,850 to 2,100 dollars |
| Typical gap | about $1,350 per month |

**Impact**

- For rental investors, location selection can dominate small property-level differences.
- For owner-occupiers, that same premium should be tested against lifestyle benefit, not rental logic alone.

### 3. Cluster status has moderate persistence

| Transition | Probability |
|-----------|-------------|
| Hotspot remains hotspot | 58-62% |
| Coldspot remains coldspot | 55-60% |
| Non-significant to hotspot | 8-10% |

**Impact**

- Hotspot status is sticky enough to matter.
- It is not so stable that it should be treated as permanent.

## Decision Guide

### For investors

- Use hotspot status to screen for stronger rental demand.
- Prefer established hotspots when stable income matters more than speculative upside.
- Do not overpay for “emerging hotspot” narratives without evidence of improving fundamentals.

### For buyers

- Treat hotspot premiums as a tenant-market signal, not a universal valuation rule.
- Coldspots can still be attractive when commute, amenities, and own-stay needs line up.

## Technical Appendix

### Data Used

- **Rental data**: `data/parquets/L1/housing_hdb_rental.parquet`
- **Geocoding data**: `data/parquets/L2/housing_unique_searched.parquet` (lat/lon)
- **Join key**: `block_street_name`, filtered to successfully geocoded records (`search_result == 0`)
- **Date range**: 2024-01 to 2025-01
- **Spatial aggregation**: H3 resolution 8, median `monthly_rent` per cell
- **Coverage**: 847 total cells, 623 with sufficient data for analysis

### Methodology

- **Data join**: L1 rental data joined to L2 geocoded properties via block+street_name key
- **Getis-Ord Gi\*** local statistic via `esda.getisord.G_Local`
- **Spatial weights**: KNN (k=8) and Queen contiguity
- **Classification thresholds**:
  - Hotspot: z > 2.58 (99% confidence)
  - Weak hotspot: z > 1.96 (95% confidence)
  - Coldspot: z < -2.58 (99% confidence)
  - Weak coldspot: z < -1.96 (95% confidence)
- **Permutations**: 99 for significance testing
- **Transition probability analysis**: persistence of hotspot/coldspot status across time periods

### Technical Findings

- **12 H3 cells** qualified as 99% confidence hotspots
- **Top hotspots**: Orchard Gi* = 4.21, Marina South Gi* = 3.89, Bukit Timah Gi* = 3.45
- **Top coldspots**: Woodlands Gi* = -3.21, Yishun Gi* = -2.98, Sembawang Gi* = -2.67
- **Rent gap**: hotspot median $3,200 vs coldspot median ~$1,850-$2,100 ≈ $1,350/month
- **Persistence rates**: hotspot remains hotspot 58-62%, coldspot remains coldspot 55-60%
- **Transition rate**: non-significant → hotspot only 8-10%, confirming true hotspots are limited

### Conclusion

The Getis-Ord Gi* analysis identifies a small, statistically selective set of rental hotspots concentrated around central and city-fringe locations, with coldspots in northern suburbs. The ~$1,350/month rent gap between hotspots and coldspots is economically significant. Persistence is moderate (58-62%), meaning hotspot status is sticky but not permanent — investors should not treat it as a guaranteed perpetual premium. The low non-significant→hotspot transition rate (8-10%) confirms that emerging hotspot narratives require strong fundamental evidence. Key limitations: hotspot analysis summarizes spatial pricing only, not full asset returns; acquisition price may already capitalize the rent premium; areas can shift with new transport links, supply additions, or policy changes.

### Scripts

- `scripts/analytics/analysis/spatial/analyze_spatial_hotspots.py` — Getis-Ord Gi* with KNN and Queen weights
