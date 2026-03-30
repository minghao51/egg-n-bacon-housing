---
title: Rental Yields
category: "market-analysis"
description: Rental yield by property type and area, the yield vs appreciation trade-off, and what affordability trends mean for buyers and investors
status: published
date: 2026-03-31
personas:
  - investor
  - first-time-buyer
  - upgrader
readingTime: "7 min read"
technicalLevel: intermediate
---

# Rental Market Deep Dive

**Analysis Date**: 2026-03-31
**Data Period**: 2017-2026
**Primary Focus**: HDB rental yields, yield vs appreciation trade-offs, affordability

## Key Takeaways

### The clearest finding

Rental yield and price appreciation are largely separate strategies. High-yield areas tend to have lower capital appreciation, and vice versa. Investors need to pick their strategy deliberately rather than expecting both.

### What this means in practice

- **Income-focused investors** should target 1-2 room flats in non-central areas for yields above 5%.
- **Growth-focused investors** should accept lower yields (3-4%) in high-appreciation areas.
- **First-time buyers** should use rental yields as a "floor value" check. If an area has strong rental demand, the downside risk is lower even if prices correct.

## Core Findings

### 1. Rental yields vary significantly by flat type and location

<div data-chart-metadata="true" data-chart="comparison" data-chart-title="Median rental yield by flat type" data-chart-columns="Median Yield,Typical Monthly Rent"></div>

| Flat Type | Median Yield | Typical Monthly Rent | Best-Yield Towns |
|-----------|-------------|---------------------|-----------------|
| 1-Room | 5-7% | $1,200-1,600 | Central, Queenstown |
| 2-Room | 4-6% | $1,500-2,200 | Ang Mo Kio, Bedok, Jurong |
| 3-Room | 3.5-5% | $2,000-2,800 | Most mature towns |
| 4-Room | 3-4.5% | $2,500-3,500 | Town-dependent |
| 5-Room | 2.5-4% | $3,000-3,800 | Lower yields, larger units |
| Multi-generation | 2-3.5% | $3,200-4,000 | Lowest yield, niche demand |

**Impact**

Smaller flats offer higher yields but lower absolute rental income. Investors should calculate total return (yield + appreciation) rather than optimizing yield alone.

### 2. Yield and appreciation are weakly negatively correlated

| Strategy | Yield Focus | Appreciation Focus | Combined Score |
|----------|------------|-------------------|---------------|
| Income investing | >5% yield | 1-3% CAGR | Moderate |
| Growth investing | 2-3% yield | 5-7% CAGR | Moderate |
| Balanced approach | 3.5-4.5% yield | 3-5% CAGR | Often highest |

**Impact**

The highest total returns often come from a balanced approach rather than optimizing either dimension in isolation. Areas with moderate yields and moderate appreciation frequently outperform extreme yield or growth plays on a risk-adjusted basis.

### 3. Top rental yield combinations reveal niche opportunities

| Rank | Flat Type + Area | Estimated Yield | Why It Works |
|------|-----------------|----------------|-------------|
| 1 | 2-Room Queenstown | ~6% | Central location, strong rental demand |
| 2 | 1-Room Central Area | ~6% | Expat and single professional demand |
| 3 | 3-Room Ang Mo Kio | ~5% | Mature amenities, MRT connectivity |
| 4 | 2-Room Jurong East | ~5% | Business hub proximity, new supply |
| 5 | 4-Room Bedok | ~4.5% | Town revitalization, transport links |

**Impact**

The top yield combinations are not random. They cluster around areas with strong employment centers, good transport, and established amenities. Investors should verify that current yield levels are sustainable (not driven by temporary demand spikes).

### 4. Affordability ratios show sustainable HDB rental market

| Metric | Value | Interpretation |
|--------|-------|---------------|
| Median HDB rent / median household income | 15-25% | Within the 30% affordability threshold |
| Income growth vs rental growth | Income slightly ahead | Rental affordability stable or improving |
| Rental burden by quintile | Higher for lower quintiles | Affordability stress concentrated at lower incomes |

**Impact**

Overall HDB rental affordability is sustainable, but lower-income households face higher rental burdens. This supports stable rental demand for mass-market HDB flats and suggests low risk of a rental market correction driven by affordability limits.

### 5. HDB rental market dynamics favor steady income

| Pattern | Observation |
|---------|------------|
| Annual rental growth | 3-5% median rent increase |
| Seasonal variation | Slightly higher demand year-end |
| Volume trends | Steady with COVID bump (2021-2022) |
| Dominant segments | 3-room and 4-room flats dominate rental volume |

**Impact**

The HDB rental market is less volatile than the sales market, making it a relatively stable income source. The year-end seasonal pattern is mild enough that investors should not over-index on timing.

## Decision Guide

### For investors

- Decide your strategy first: yield, growth, or balanced. Then pick the flat type and area that matches.
- Use the yield-appreciation trade-off framework. Do not expect a single property to deliver top-quartile results on both dimensions.
- Check the sustainability of high yields. Yields above 6% may indicate risk factors (older flats, less desirable locations) that affect long-term value.

### For first-time buyers

- Rental yields provide a downside floor. If an area has strong rental demand, you can rent out the unit if your circumstances change.
- Do not buy purely for rental yield. Owner-occupiers should prioritize livability. The best yield properties are not always the best homes.
- Use affordability ratios to check whether your target area's rental market supports your purchase price as a long-term investment.

### For upgraders

- Before upgrading, calculate the rental yield on your current HDB. It may be more attractive than you think, especially for smaller flats in mature towns.
- Consider keeping your current HDB as a rental property if the yield exceeds your mortgage rate.
- Compare the forgone rental income against the capital gain from selling, factoring in transaction costs.

## Technical Appendix

### Data Used

- **HDB rental transactions**: `data/pipeline/L1/housing_hdb_rental.parquet`
- **HDB resale prices**: `data/pipeline/L1/housing_hdb_transaction.parquet`
- **Rental yields**: `data/pipeline/L2/rental_yield.parquet`
- **Top yield combinations**: `data/pipeline/L3/rental_yield_top_combos.parquet`
- **Household income**: `data/pipeline/L1/household_income_estimates.parquet`
- **HDB median rent by town/flat type**: `data/pipeline/L1/housing_hdb_median_rent_by_town_flat_type.parquet`

### Methodology

- **Rental yield calculation**: Annual median rent / median resale price per flat type per town, with minimum 50 transactions for statistical reliability
- **Yield-appreciation correlation**: Pearson correlation between yield and CAGR at the planning area level
- **Affordability ratio**: Median monthly rent / estimated median monthly household income, with quintile breakdown
- **Investment scoring**: Composite of appreciation z-score (50%) + yield z-score (50%), normalized to 0-100
- **Seasonal analysis**: Monthly rental volume and median rent decomposition
- **Top combinations**: Ranked by yield within flat type x planning area, filtered for minimum transaction count

### Technical Findings

- **Median HDB rental yield** is approximately 4.2%, with 1-2 room flats offering 5-7% and 5-room/MG flats at 2-3.5%
- **Yield and appreciation are weakly negatively correlated** (r ~ -0.3), confirming that these are fundamentally different strategies
- **Affordability ratios** show HDB rental costs at 15-25% of median household income, well within the 30% threshold
- **Rental growth** averages 3-5% annually, broadly tracking income growth
- **Seasonal patterns** are mild, with slightly higher year-end demand unlikely to materially affect investment returns
- **COVID rental bump** (2021-2022) has largely normalized, with rents returning to trend growth

### Conclusion

The HDB rental market offers stable, moderate yields that are broadly sustainable. The yield vs appreciation trade-off means investors must choose their strategy deliberately. Smaller flats in well-connected non-central areas offer the best yields, while larger flats in appreciating areas offer better total returns. Affordability metrics suggest the rental market is not overheated. Key limitation: rental yield calculations use median resale price as the denominator, which may differ from actual purchase price for individual units. Household income estimates are modeled rather than directly observed.

### Scripts

- `scripts/analytics/analysis/market/analyze_hdb_rental_market.py` — HDB rental yield by town and flat type, affordability analysis, market dynamics
- `scripts/analytics/price_appreciation_modeling/residual_analysis.py` — Yield vs appreciation correlation, investment scoring
- `scripts/analytics/price_appreciation_modeling/residual_analysis_by_property_type.py` — Property type-specific residual analysis
- `scripts/analytics/price_appreciation_modeling/residual_analysis_simple.py` — Simplified residual analysis
