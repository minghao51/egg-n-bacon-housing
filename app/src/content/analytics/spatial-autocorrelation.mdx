---
title: Neighborhood Clusters
category: "market-analysis"
description: How strongly appreciation clusters by neighborhood, what cluster status means for buyers, and where spatial effects are most decision-relevant
status: published
date: 2026-02-06
personas:
  - investor
  - first-time-buyer
  - upgrader
readingTime: "7 min read"
technicalLevel: intermediate
---

# Spatial Autocorrelation

**Analysis Date**: 2026-02-06  
**Data Period**: 2021-2026  
**Coverage**: HDB, EC, and condominium appreciation patterns

## Key Takeaways

### The clearest finding

Appreciation is spatially clustered. Nearby neighborhoods tend to move together strongly enough that location context becomes a major part of short- to medium-term performance.

### What this means in practice

- **Investors** should treat neighborhood cluster status as a real risk and return factor.
- **Homebuyers** should not evaluate units in isolation from their surrounding submarket.
- **Upsiders and catch-up plays** exist, but not every lagging area converts into a hotspot.

## Core Findings

### 1. Neighborhood effects are statistically strong

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Moran's I | 0.766 | Strong positive spatial clustering |
| Z-score | 9.91 | Highly significant |

This means appreciation is not randomly distributed. Nearby areas tend to share price momentum.

### 2. Hotspot and lagging clusters differ in performance

<div data-chart-metadata="true" data-chart="comparison" data-chart-title="Appreciation by spatial cluster type" data-chart-columns="Count,YoY Appreciation"></div>

| Cluster Type | Count | YoY Appreciation | Description |
|-------------|-------|------------------|-------------|
| HH (hotspot) | 16 | 12.7% | High-growth areas near other high-growth areas |
| LH (lagging in strong neighborhoods) | 17 | 11.3% | Potential catch-up or persistent underperformers |
| LL (coldspot) | 1 | about 10% | Weak area in weak surroundings |
| Not significant | 8 | 12.0% | No strong local pattern |

**Impact**

- Hotspot neighborhoods have a measurable appreciation edge.
- LH areas deserve case-by-case analysis; some are opportunities, some are structural laggards.

### 3. Spatial dependence is stronger in some segments than others

| Property Type | Spatial lag correlation |
|---------------|-------------------------|
| Condo | 78% |
| HDB | 71% |
| EC | 65% |

**Impact**

- Condo buyers are especially exposed to neighborhood momentum and peer pricing effects.
- HDB still shows strong neighborhood dependence, though somewhat less than condo.

## Decision Guide

### For investors

- Start with neighborhood classification, then evaluate the unit.
- Use HH clusters for stability and LH clusters only where there is a clear catalyst or discount.

### For first-time buyers

- A good unit in a weak micro-market can still underperform a slightly less attractive unit in a stronger surrounding cluster.

### For upgraders

- Cluster effects matter most when your hold period depends on future resale strength.

## Technical Appendix

### Data Used

- **Primary input**: `data/parquets/L1/housing_hdb_rental.parquet`
- **Spatial aggregation**: H3 hexagonal grid at resolution 8 (~0.5 km² cells)
- **Aggregation method**: median `monthly_rent` per H3 cell
- **Minimum threshold**: ≥10 records per cell for analysis

### Methodology

- **Global Moran's I**: KNN weights (k=8), row-standardized, 99 permutations
- **Local LISA** (Local Indicators of Spatial Association): `Moran_Local` with 99 permutations
- **Cluster classification**: HH (high-high), LL (low-low), HL (high-low), LH (low-high), NS (not significant)
- **Significance threshold**: p ≤ 0.05
- **Spatial lag correlation**: computed per property type (Condo, HDB, EC) to measure neighborhood dependence

### Technical Findings

- **Global Moran's I**: 0.766 (strong positive spatial clustering)
- **Z-score**: 9.91, p-value < 0.001 — highly significant
- **Cluster distribution**:
  - HH (hotspot): 16 cells, 12.7% YoY appreciation
  - LH (lagging in strong neighborhood): 17 cells, 11.3% YoY
  - LL (coldspot): 1 cell, ~10% YoY
  - Not significant: 8 cells, 12.0% YoY
- **Spatial lag correlation by segment**: Condo 78%, HDB 71%, EC 65%
- **Transition analysis**: moderate persistence — hotspot and coldspot status are sticky but not permanent

### Conclusion

The Moran's I of 0.766 with z=9.91 confirms that appreciation is far from randomly distributed; nearby areas share price momentum strongly. The HH cluster premium (12.7% YoY vs ~10-12% elsewhere) is modest but statistically robust. LH clusters (17 cells) represent the most analytically interesting group — potential catch-up opportunities, but also potential structural laggards requiring case-by-case assessment. The stronger spatial dependence in condos (78%) vs HDB (71%) vs EC (65%) suggests that condo pricing is more influenced by peer neighborhood performance. Key limitations: cluster labels summarize local context and do not override unit-specific factors; spatial patterns can shift with supply, policy, or infrastructure changes.

### Scripts

- `scripts/analytics/analysis/spatial/analyze_spatial_autocorrelation.py` — Moran's I + LISA
- `scripts/analytics/analysis/spatial/analyze_h3_clusters.py` — H3 cluster classification
