---
title: Macro Sensitivity
category: "market-analysis"
description: How Singapore housing prices respond to GDP growth, interest rates, inflation, and unemployment, and what current macro conditions signal for buyers
status: published
date: 2026-03-31
personas:
  - investor
  - first-time-buyer
  - upgrader
readingTime: "7 min read"
technicalLevel: intermediate
---

# Macro-Economic Sensitivity Analysis

**Analysis Date**: 2026-03-31
**Data Period**: 2021-2026 (macro data), 2017-2026 (housing data)
**Primary Focus**: Connecting housing market performance to broader economic conditions

## Key Takeaways

### The clearest finding

Housing prices and macro indicators are correlated, but the relationship is regime-dependent and segment-specific. Interest rates (SORA) have the most direct impact on affordability, while GDP growth is a leading indicator for transaction volume more than price level.

### What this means in practice

- **Buyers** should track interest rate trends more closely than GDP headlines when timing a purchase.
- **Investors** should adjust their yield expectations based on the macro regime. Rising rates compress yields; falling rates support price appreciation.
- **All personas** should compare inflation-adjusted real returns, not just nominal price changes, when evaluating performance.

## Core Findings

### 1. Interest rates have the most direct link to housing affordability

<div data-chart-metadata="true" data-chart="time-series" data-chart-title="SORA rate vs HDB median price trend" data-chart-columns="SORA Rate (%),HDB Median Price Index"></div>

| Period | SORA Rate | HDB Price Trend | Transaction Volume |
|--------|----------|----------------|-------------------|
| 2021 (H1) | 0.1-0.2% | Rising | High |
| 2022 (H2) | 2.5-3.5% | Decelerating | Declining |
| 2023 | 3.5-4.0% | Flat to modest growth | Low |
| 2024-2025 | 3.0-3.5% | Resumed growth | Recovering |

**Impact**

The rapid SORA increase from near-zero to 3.5-4% between 2022-2023 coincided with a clear deceleration in price growth and a decline in transaction volume. As rates stabilized in 2024-2025, price growth resumed. This confirms that interest rates are the most actionable macro indicator for housing decisions.

### 2. GDP growth leads transaction volume, not price level

| Indicator | Correlation with Price | Correlation with Volume | Lag |
|-----------|----------------------|----------------------|-----|
| GDP growth (quarterly) | Weak positive | Moderate positive | 1-2 quarters |
| SORA rate | Moderate negative | Strong negative | Immediate to 1 quarter |
| CPI inflation | Weak positive | Weak | Variable |
| Unemployment | Moderate negative | Moderate negative | 1-2 quarters |

**Impact**

GDP growth signals market activity (volume) more reliably than price direction. Interest rates are the better price-timing signal. Unemployment is a lagging indicator that confirms weakness rather than predicting it.

### 3. Inflation-adjusted returns vary significantly by segment

| Segment | Nominal CAGR | Real CAGR (CPI-adjusted) | Spread |
|---------|-------------|-------------------------|--------|
| HDB (overall) | ~4-5% | ~2-3% | ~2% |
| Mass-market condo | ~5-6% | ~3-4% | ~2% |
| Premium condo | ~3-5% | ~1-3% | ~2% |
| Luxury condo | ~2-4% | ~0-2% | ~2% |

**Impact**

All segments deliver positive real returns over the 2021-2026 period, but the spread over inflation is modest. Luxury condos barely clear inflation in some years, making them more of a wealth preservation play than a growth play.

### 4. Three macro regimes are identifiable (2021-2026)

| Regime | Period | Characteristics | Housing Market Behavior |
|--------|--------|----------------|------------------------|
| Expansion | 2021 - mid-2022 | Low rates, rising GDP, low unemployment | Strong price growth, high volume |
| Tightening | Mid-2022 - 2023 | Rapid rate hikes, GDP deceleration | Price growth stall, volume decline |
| Stabilization | 2024-2026 | Rates plateau, GDP recovery | Moderate price growth, volume recovery |

**Impact**

Each regime favors different strategies. Expansion favors buying early and levering up. Tightening favors patience and yield-focused investments. Stabilization favors balanced entry with moderate leverage.

### 5. Policy dates align with macro shifts

| Policy Date | Policy Change | Macro Context | Market Impact |
|------------|--------------|---------------|---------------|
| Dec 2021 | ABSD tightening | Low rates, exuberant market | Short-term price dip, quick recovery |
| Sep 2022 | Additional cooling | Rising rates, tightening regime | Amplified rate-driven slowdown |
| Apr 2023 | LTV tightening | Peak rates, low volume | Extended demand suppression |
| Dec 2023 | HDB-specific measures | Stabilizing rates | Counter-intuitive HDB price increase |

**Impact**

Policy changes are most effective when aligned with the macro regime. The Dec 2023 HDB measures, applied during rate stabilization, produced a counter-intuitive price jump rather than the intended cooling effect. Buyers should evaluate policy announcements in the context of the broader macro environment.

## Decision Guide

### For investors

- Track SORA trends as your primary macro timing signal. Rate stabilization or decline is a favorable entry signal.
- Adjust yield expectations by regime. In a tightening regime, rental yields need to be higher to compensate for higher financing costs.
- Compare real (inflation-adjusted) returns, not just nominal returns, when evaluating segment performance.

### For first-time buyers

- Do not time the market based on GDP headlines. Interest rates and affordability are more directly relevant.
- In a rising rate environment, prioritize lower loan-to-value to reduce refinancing risk.
- Check whether current SORA levels make your target purchase affordable under stress scenarios (rates +1%).

### For upgraders

- Evaluate your upgrade in the context of the macro regime. Selling in a tightening regime may yield a lower price but buying is also cheaper.
- Consider the interest rate differential between your current mortgage and the new one. A 1% rate difference on a large loan can offset any price advantage.

## Technical Appendix

### Data Used

- **Housing data**: `data/pipeline/L3/housing_unified.parquet` (2017-2026 transactions)
- **Macro data** (all from `data/raw_data/macro/`):
  - `singapore_cpi_monthly.parquet` — 60 monthly observations (2021-2025)
  - `sgdp_quarterly.parquet` — 21 quarterly observations (2021-2026)
  - `sora_rates_monthly.parquet` — 60 monthly observations (2021-2025)
  - `unemployment_rate_monthly.parquet` — 60 monthly observations (2021-2025)
  - `property_price_index_quarterly.parquet` — 21 quarterly observations (2021-2026)
  - `housing_policy_dates.parquet` — 5 major policy events (2021-2023)

### Methodology

- **Time series correlation**: Pearson and Spearman correlations between macro indicators and housing metrics (price, volume, yield) at monthly and quarterly frequencies
- **Lag analysis**: Cross-correlation functions to identify lead-lag relationships between macro variables and housing market responses
- **Regime identification**: Visual and statistical identification of distinct macro periods based on SORA, GDP, and policy event clustering
- **Real return calculation**: Nominal returns deflated by CPI index to compute inflation-adjusted CAGR by segment
- **Policy overlay**: Alignment analysis of policy dates with macro regime transitions

### Technical Findings

- **SORA is the most actionable indicator**: Immediate correlation with housing affordability and 1-quarter lag with price trends
- **GDP growth correlates more with volume than price**: 1-2 quarter lag, moderate positive correlation with transaction count
- **Real CAGR spread over inflation** is approximately 2% across all segments, suggesting housing reliably preserves purchasing power but is not a high-growth real asset class
- **Three distinct macro regimes** are identifiable in the 2021-2026 data: expansion, tightening, stabilization
- **Policy effectiveness is regime-dependent**: Cooling measures aligned with tightening are amplified; measures applied during stabilization may be counter-productive
- **Unemployment is a lagging indicator** for housing, confirming weakness rather than predicting it

### Conclusion

Macro-economic sensitivity analysis reveals that interest rates (SORA) are the most directly actionable macro signal for housing decisions, followed by unemployment (lagging) and GDP (volume-leading). The 2021-2026 period exhibits three distinct macro regimes, each with different implications for buying, selling, and investment strategy. Real returns are modestly positive across all segments, confirming housing as a wealth preservation asset. Key limitation: the 5-year macro data window covers only one full rate cycle, limiting generalizability. The macro data collection relies on SingStat API with fallback to generated data when API calls fail.

### Scripts

- `scripts/data/fetch_macro_data.py` — Centralized collection of CPI, GDP, SORA, unemployment, and PPI data from SingStat
- `scripts/analytics/pipelines/prepare_timeseries_data.py` — Combines L3 housing data with macro indicators for time series modeling
