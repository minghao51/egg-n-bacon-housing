---
title: Amenity Impact
category: "market-analysis"
description: Which daily-convenience amenities actually move property prices, and which are mostly marketing noise
status: published
date: 2026-03-31
personas:
  - first-time-buyer
  - investor
  - upgrader
readingTime: "7 min read"
technicalLevel: intermediate
---

# Amenity Impact Analysis

**Analysis Date**: 2026-03-31
**Data Period**: 2015-2026
**Primary Focus**: HDB and condo, with amenity interaction effects

## Key Takeaways

### The clearest finding

Hawker centre proximity is the single most important amenity feature for HDB pricing, outranking even MRT access. Parks and green space are the most underappreciated premium driver. Many amenities that developers market heavily have surprisingly modest pricing effects.

### What this means in practice

- **HDB buyers** should prioritize hawker proximity over MRT proximity when evaluating daily convenience.
- **Condo buyers** get more pricing benefit from MRT and mall proximity than from most in-facility amenities.
- **Investors** should check the amenity mix holistically. MRT + mall + hawker proximity together create more pricing power than any single amenity.

## Core Findings

### 1. Hawker centres dominate HDB feature importance

| Feature | XGBoost Importance | Interpretation |
|---------|-------------------|----------------|
| Hawker within 1km | 27.4% | Strongest single feature after structural attributes |
| Remaining lease months | 14.1% | Core structural factor |
| Park within 1km | 7.2% | Meaningful and often underpriced |
| MRT within 1km | 5.5% | Modest relative to daily convenience |
| Supermarket within 1km | 3.8% | Present but secondary |

**Impact**

For HDB, daily food access is priced more strongly than transit access. This likely reflects the eating-out culture in Singapore and the walkability premium around established hawker centres.

### 2. Parks are the hidden premium driver

Park proximity adds a measurable premium that is frequently underweighted in buyer decisions.

| Amenity | HDB Premium Signal | Condo Premium Signal | Market Awareness |
|---------|--------------------|---------------------|-----------------|
| Park within 1km | 7.2% importance | Moderate | Low |
| MRT within 1km | 5.5% importance | High | High |
| Mall within 1km | 4.1% importance | Moderate | High |

**Impact**

Properties near large parks (East Coast, Bishan-Ang Mo Kio, Bukit Timah) may offer better value per dollar than equivalent properties near MRT stations, because the market has not fully priced the green-space premium.

### 3. Amenity premiums shifted during and after COVID

<div data-chart-metadata="true" data-chart="comparison" data-chart-title="Amenity feature importance across periods" data-chart-columns="Pre-COVID (2015-2019),COVID (2020-2022),Post-COVID (2023-2026)"></div>

| Amenity | Pre-COVID (2015-2019) | COVID (2020-2022) | Post-COVID (2023-2026) |
|---------|----------------------|-------------------|------------------------|
| Hawker proximity | High | High | High |
| Park proximity | Moderate | Elevated | Elevated |
| MRT proximity | Moderate | Reduced | Partially recovered |
| Mall proximity | Moderate | Reduced | Recovered |

**Impact**

COVID elevated the importance of nearby green space and reduced the MRT premium as remote work reduced commute frequency. Post-COVID, park premiums have remained elevated while MRT importance has only partially recovered. Buyers should not assume pre-COVID amenity weightings still apply.

### 4. Amenity interaction effects are real

The combined effect of having multiple amenities nearby exceeds the sum of individual effects.

| Amenity Combination | Observed Effect | Interpretation |
|---------------------|----------------|----------------|
| MRT + Mall + Hawker | Synergistic premium | Convenience hub effect |
| MRT + Park | Moderate synergy | Transit + lifestyle appeal |
| Park + Hawker | Mild synergy | Neighborhood livability |
| Mall + Supermarket | Minimal synergy | Largely substitutable |

**Impact**

The strongest pricing signal comes from being in a multi-amenity hub, not from proximity to any single facility. Buyers should evaluate the local amenity ecosystem rather than checking individual items off a list.

### 5. Grid-based micro-neighborhood analysis confirms town-level patterns

At the 500m x 500m grid level, amenity premiums are highly localized within the same town. Two flats in the same planning area but different grids can have materially different amenity profiles.

**Impact**

Town-level averages mask significant within-town variation. Buyers should check the specific 500m radius around their target unit rather than relying on town-wide amenity labels.

## Decision Guide

### For HDB buyers

- Check hawker, park, and supermarket proximity before MRT proximity. The data says daily convenience matters more than transit access for HDB pricing.
- Look for undervalued park-adjacent units. The market has not fully priced green-space benefits.
- Evaluate the full amenity ecosystem within 500m. A unit near a single amenity is less valuable than one near a convenience cluster.

### For investors

- Target multi-amenity hubs for stronger rental demand and capital appreciation.
- Do not overpay for MRT proximity alone in HDB. Hawker and park proximity drive more pricing power.
- Monitor post-COVID amenity shifts. Park premiums may continue to strengthen.

### For upgraders

- When upgrading from HDB to condo, recalibrate amenity expectations. Condos price MRT and mall proximity more strongly than HDB.
- If selling an HDB near a hawker centre, make sure to highlight this in marketing. Buyers may undervalue it relative to MRT labels.

## Technical Appendix

### Data Used

- **Primary input**: `data/pipeline/04_platinum/housing_unified.parquet`
- **Sample**: HDB and condo transactions, 2015-2026, with valid coordinates and amenity features
- **Amenity features**: Distance and threshold indicators for hawker, mall, park, supermarket, preschool, childcare at 500m, 1km, and 2km radii
- **Spatial grid**: 500m x 500m cells for micro-neighborhood analysis, minimum 10 transactions per cell

### Methodology

- **XGBoost** (100 trees, max_depth=6, learning_rate=0.1) with SHAP values for feature importance and interaction detection
- **RandomForestRegressor** (50 estimators, max_depth=10) for temporal period comparison (pre-COVID, COVID, post-COVID)
- **Within-town analysis**: Separate models per town (minimum 100 transactions) controlling for town-level effects with StandardScaler preprocessing
- **Grid-based analysis**: 500m x 500m spatial grid, minimum 5 records per grid cell, RandomForestRegressor (30 estimators, max_depth=5)
- **Temporal split**: Pre-COVID (2015-2019), COVID (2020-2022), Post-COVID (2023-2026) with minimum 1,000 records per period

### Technical Findings

- **Hawker within 1km** is the dominant non-structural feature at 27.4% XGBoost importance, followed by remaining lease (14.1%), park within 1km (7.2%), and MRT within 1km (5.5%)
- **Park importance increased post-COVID** and has remained elevated, suggesting a structural shift in buyer preferences
- **MRT importance dipped during COVID** and has only partially recovered, likely reflecting sustained hybrid work patterns
- **Grid-level analysis** shows high within-town variation in amenity premiums, confirming that town averages are insufficient for pricing decisions
- **Amenity interaction effects** are strongest for the MRT + Mall + Hawker combination, suggesting convenience hubs command pricing power beyond individual amenity effects

### Conclusion

Amenity analysis reveals that Singapore HDB buyers price daily food access (hawker) far more strongly than transit access. Parks represent an underpriced premium driver that has strengthened since COVID. The data supports a shift in buyer heuristics from "near MRT" to "near a multi-amenity hub." Key limitation: amenity distances are straight-line (not walking path quality), and some amenities may serve as proxies for broader neighborhood quality rather than standalone value drivers.

### Scripts

- `scripts/analytics/analysis/amenity/analyze_amenity_impact.py` — Temporal, within-town, and grid-based amenity analysis
- `scripts/analytics/analysis/amenity/analyze_feature_importance.py` — XGBoost feature importance with SHAP for price, rental yield, and appreciation targets
