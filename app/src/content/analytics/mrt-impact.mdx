---
title: MRT Impact
category: "market-analysis"
description: What MRT access really contributes to housing prices, where the effect is meaningful, and where it is mostly overstated
status: published
date: 2026-02-04
personas:
  - first-time-buyer
  - investor
  - upgrader
readingTime: "8 min read"
technicalLevel: intermediate
---

# MRT Impact Analysis

**Analysis Date**: 2026-02-04  
**Data Period**: 2021-2026  
**Primary Focus**: HDB, with cross-segment comparison

## Key Takeaways

### The clearest finding

For HDB, the “MRT premium” is much smaller than popular market language suggests. Much of the apparent accessibility premium is better explained by **CBD proximity and broader neighborhood context**.

### What this means in practice

- **HDB buyers** should not pay large premiums purely for shorter MRT distance.
- **Condo buyers and investors** should still take MRT seriously; condo pricing is far more transit-sensitive.
- **Town context matters**. MRT access does not price the same way across central and suburban locations.

## Core Findings

### 1. MRT has a modest average effect on HDB prices

| Metric | Value | Interpretation |
|--------|-------|----------------|
| HDB MRT premium | $1.28 per 100m closer | Small average pricing effect |
| Mean HDB price PSF | $552 | Context for the premium |
| OLS R² | 0.52 | Moderate explanatory power |

On its own, that average is too small to justify many listing premiums seen in practice.

### 2. The average hides large town-level differences

<div data-chart-metadata="true" data-chart="comparison" data-chart-title="Town-level MRT premium variation" data-chart-columns="MRT Premium,Mean Price PSF,Transactions"></div>

| Town | MRT Premium per 100m | Mean Price PSF | Transactions |
|------|----------------------|----------------|--------------|
| Central Area | +$59.19 | $903 | 599 |
| Serangoon | +$12.91 | $566 | 1,853 |
| Bishan | +$5.88 | $644 | 1,951 |
| Marine Parade | -$38.54 | $629 | 515 |
| Geylang | -$20.54 | $584 | 2,054 |
| Sengkang | -$16.88 | $558 | 7,585 |

**Impact**

- In central areas, MRT access can still command a meaningful premium.
- In some suburban and already well-served areas, shorter station distance may coincide with crowding, noise, or other offsetting trade-offs.

### 3. MRT matters far more for condos than HDB

| Property Type | MRT sensitivity |
|--------------|-----------------|
| HDB | low |
| Condo | roughly 15x higher than HDB |

**Impact**

- Investors should keep separate heuristics for HDB and condo.
- A transport argument that makes sense for condo often does not translate well to HDB.

### 4. Other amenities can outrank MRT in HDB pricing

| Feature | Importance |
|---------|------------|
| Hawker within 1km | 27.4% |
| Remaining lease months | 14.1% |
| Park within 1km | 7.2% |
| MRT within 1km | 5.5% |

**Impact**

- For HDB, daily convenience and lease still matter more than station access in the pricing model.
- Buyers who stretch only for MRT may be paying for the wrong attribute mix.

## Decision Guide

### For HDB buyers

- Compare MRT distance against lease, town, and amenity trade-offs.
- Use town-specific evidence rather than a generic “near MRT is always better” rule.

### For investors

- Prioritize MRT proximity for condos and future tenant demand.
- Be skeptical of HDB listings that justify large premiums mainly on MRT access.

### For upgraders

- When moving from HDB to condo, recalibrate your accessibility assumptions. The same 300-500m difference carries different market value across segments.

## Technical Appendix

### Data Used

- **Primary input**: `data/parquets/L3/housing_unified.parquet`
- **Sample**: 97,133 HDB transactions, filtered to 2021 onward, with valid coordinates
- **Spatial grid**: H3 hexagonal grid at resolution 8 (~0.5 km² cells), minimum 10 records per cell
- **CBD reference point**: (1.2839, 103.8513), haversine distance calculation

### Methodology

- **OLS LinearRegression** controlling for `dist_to_nearest_mrt`, `floor_area_sqm`, `remaining_lease_months`
- **XGBoost** (100 trees, max_depth=6, learning_rate=0.1) for non-linear patterns, with SHAP for explainability
- **Hierarchical regression** via `scripts/analytics/analysis/spatial/analyze_cbd_mrt_decomposition.py`: CBD-only → CBD+MRT → Full model, to isolate incremental MRT contribution
- **VIF analysis** to check multicollinearity between MRT and CBD distance
- **Town-level OLS** in `scripts/analytics/analysis/mrt/analyze_mrt_heterogeneous.py`, minimum 500 transactions per town
- **Cross-property comparison** in `scripts/analytics/analysis/mrt/analyze_mrt_by_property_type.py`, interaction terms for property type × MRT distance

### Technical Findings

- **CBD-only model R² = 0.2263**, CBD+MRT R² = 0.2341, ΔR² = +0.0078 (MRT adds less than 1 percentage point beyond CBD)
- **Full model R² = 0.4977** (broader housing features dominate)
- **HDB MRT coefficient**: $1.28/100m (mean PSF $552); **Condo MRT sensitivity ~15× HDB**
- **Feature importance (XGBoost)**: hawker_within_1km = 27.4%, remaining_lease_months = 14.1%, park_within_1km = 7.2%, mrt_within_1km = 5.5%
- **Town-level variation**: Central Area +$59.19/100m, Marine Parade -$38.54/100m
- **VIF**: MRT and CBD distance show moderate collinearity (~0.5-0.7 correlation), confirming they capture overlapping but distinct location effects

### Conclusion

The technical evidence supports the headline finding: CBD proximity is the dominant location factor for HDB, and MRT adds only a marginal incremental contribution. The ~15× condo-vs-HDB sensitivity gap is robust across OLS and XGBoost specifications. Town-level heterogeneity is large enough that a single national MRT premium is misleading. Key limitations: distances are straight-line to nearest station (not walking path quality), and some town coefficients likely absorb omitted neighborhood factors.

### Scripts

- `scripts/analytics/analysis/mrt/analyze_mrt_impact.py` — OLS + XGBoost + SHAP on H3 H8 grid
- `scripts/analytics/analysis/mrt/analyze_mrt_heterogeneous.py` — Town-level, flat-type, price-tier stratification
- `scripts/analytics/analysis/mrt/analyze_mrt_by_property_type.py` — HDB vs Condo comparison
- `scripts/analytics/analysis/spatial/analyze_cbd_mrt_decomposition.py` — Hierarchical regression, VIF, PCA
