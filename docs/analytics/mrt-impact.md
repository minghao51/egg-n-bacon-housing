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

## Appendix A: Technical Summary

- Main HDB sample: **97,133 transactions** from 2021 onward.
- Additional decomposition work showed CBD distance explains more price variation than MRT distance alone.
- Non-linear models materially outperformed OLS, but the relative ranking of major drivers remained similar.

## Appendix B: Caveats

- Distances are based on nearest-station proximity, not true walking path quality.
- Some town-level coefficients may reflect omitted neighborhood factors.
- Future-line premiums require separate event-style analysis and should not be inferred directly from this summary.
