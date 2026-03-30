---
title: Lease Decay Impact
category: "market-analysis"
description: Clear view of how remaining lease affects HDB resale value, where the sharpest discounts appear, and what that means for buyers
status: published
date: 2026-02-04
personas:
  - investor
  - first-time-buyer
  - upgrader
readingTime: "7 min read"
technicalLevel: intermediate
---

# Lease Decay Impact

**Analysis Date**: 2026-02-04  
**Data Period**: 2017-2026  
**Property Type**: HDB resale

## Key Takeaways

### The clearest finding

Lease decay is **non-linear**. The steepest market discount does not appear only in the oldest flats; it concentrates around the **70-80 year** lease band, where prices are about **21.9%** below the 90+ year baseline.

### Why this matters

- **Buyers** can find meaningful value in the **60-70 year** band, which combines deep discounts with the highest transaction volume.
- **Sellers** of 90+ year flats benefit from the market’s strongest pricing preference.
- **Investors** should not rely on straight-line depreciation assumptions for hold-period planning.

## Core Findings

### 1. The market discounts lease bands unevenly

<div data-chart-metadata="true" data-chart="comparison" data-chart-title="HDB price profile by lease band" data-chart-columns="Median Price,Median PSF,Transactions"></div>

| Lease Band | Avg Remaining Years | Median Price | Median PSF | Discount vs 90+ yrs | Transactions |
|------------|--------------------|--------------|------------|---------------------|--------------|
| 90+ years | 93.5 years | $558,000 | $6,205 | baseline | 50,912 |
| 80-90 years | 84.6 years | $520,000 | $5,389 | -13.2% | 29,562 |
| 70-80 years | 75.4 years | $548,000 | $4,845 | -21.9% | 47,044 |
| 60-70 years | 64.6 years | $446,000 | $4,730 | -23.8% | 54,521 |
| <60 years | 54.5 years | $390,000 | $5,274 | -15.0% | 41,595 |

**What stands out**

- The **70-80 year** band has the sharpest market penalty.
- The **60-70 year** band is the market’s main value bucket: heavily discounted, but still liquid.
- The **<60 year** group is not the cheapest on a PSF basis, which suggests location mix still matters a lot.

### 2. The 60-70 year band is the main trade-off zone

This is the band where price relief and market liquidity overlap most clearly.

| Metric | Value | Why it matters |
|--------|-------|----------------|
| Discount vs 90+ years | -23.8% | Large entry-price reduction |
| Share of transactions | 24.4% | Resale market remains active |
| Pure lease effect | +$54.75 PSF per extra year | Lease still has measurable pricing power |

**Impact**

- For owner-occupiers with a long but finite holding period, this band can offer better value than near-new stock.
- For investors, liquidity is better than many buyers expect, but financing rules still matter.

### 3. Lease decay interacts with location

The same lease gap can price very differently across towns.

<div data-chart-metadata="true" data-chart="comparison" data-chart-title="Within-town short-lease discount" data-chart-columns="Short Lease (PSM),Fresh Lease (PSM),Discount %"></div>

| Town | Short Lease (PSM) | Fresh Lease (PSM) | Discount % |
|------|-------------------|-------------------|-----------|
| CLEMENTI | $5,224 | $8,796 | 40.6% |
| TOA PAYOH | $4,939 | $8,182 | 39.6% |
| QUEENSTOWN | $5,526 | $9,048 | 38.9% |
| WOODLANDS | $4,262 | $4,544 | 6.2% |
| JURONG WEST | $4,496 | $4,516 | 0.4% |
| PASIR RIS | $5,621 | $4,676 | -20.2% |

**Impact**

- In mature central towns, shorter leases are usually penalized heavily.
- In some suburban towns, location and town-level desirability can offset or even outweigh lease penalties.
- Buyers should compare lease discounts **within the same town**, not only across Singapore-wide averages.

## Decision Guide

### For first-time buyers

- Do not rule out **60-70 year** flats automatically.
- Check CPF and financing constraints early.
- Compare the discount you are getting against the actual years of lease you are giving up.

### For investors

- Prioritize discounted lease bands only where liquidity is proven and town-level demand is stable.
- Avoid assuming older lease automatically means underpriced.

### For upgraders

- Selling a 90+ year flat can crystallize the market’s strongest lease premium.
- Buying into a shorter lease can be rational if it unlocks a better location without a full central premium.

## Technical Appendix

### Data Used

- **Primary input**: `data/parquets/L1/housing_hdb_transaction.parquet`
- **Sample**: 223,634 HDB transactions, 2017-2026, lease range 30-99 years
- **Advanced input**: `data/parquets/L3/housing_unified.parquet` for multivariate hedonic regression

### Methodology

- **Lease bands**: bins [0, 60, 70, 80, 90, 100], labels [<60, 60-70, 70-80, 80-90, 90+]
- **Remaining lease years**: `remaining_lease_months / 12`
- **Price statistics**: median `resale_price` and `price_per_sqm` by band
- **Discount to 90+ baseline**: `(baseline_psm - band_psm) / baseline_psm × 100`
- **Annual decay rate**: linear approximation from discount vs years elapsed
- **Town-level comparison**: short lease (<70 yr) vs fresh lease (90+ yr) median PSM within same town
- **Hedonic regression** (advanced): `Price = β₀ + β₁(Lease) + β₂(FloorLevel) + β₃(DistToMRT) + β₄(Town) + ε`
- **Policy threshold analysis**: Mann-Whitney U tests at 60-yr and 30-yr marks
- **Bala's curve validation**: empirical vs theoretical depreciation, ≥5% deviation flagged

### Technical Findings

- **90+ year band**: 50,912 transactions, median $558,000, median PSM $6,205
- **70-80 yr band**: 47,044 transactions, -21.9% discount (steepest penalty)
- **60-70 yr band**: 54,521 transactions, -23.8% discount (deepest, highest volume)
- **Pure lease effect**: +$54.75 PSF per extra year (after controlling for town, floor level, MRT distance)
- **Town variation**: Clementi -40.6%, Toa Payoh -39.6%, Woodlands -6.2%, Pasir Ris +20.2% (inverted)
- **60-yr policy threshold**: measurable “liquidity tax” between 61-yr and 59-yr leases (CPF restriction)
- **Spline-based arbitrage**: identifies BUY/SELL/HOLD signals at lease years where market deviates ≥5% from theoretical Bala curve

### Conclusion

The data confirms non-linear lease decay. The 70-80 yr band shows the steepest penalty (not the oldest flats), while the 60-70 yr band offers the deepest absolute discount with strong liquidity. The pure lease effect of +$54.75 PSF/year is robust after multivariate controls. Town-level heterogeneity is extreme: central mature towns penalize short leases heavily (Clementi -40.6%), while some suburban towns show minimal or even inverted discounts, likely due to location desirability offsetting lease age. Key limitations: renovation condition, HIP timing, and block-level maintenance are not fully captured; financing rules shrink the buyer pool for shorter leases.

### Scripts

- `scripts/analytics/analysis/market/analyze_lease_decay.py` — Lease banding, price statistics, decay rates
- `scripts/analytics/analysis/market/analyze_lease_decay_advanced.py` — Hedonic regression, Bala curve validation, spline arbitrage, policy thresholds
