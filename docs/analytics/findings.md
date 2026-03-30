---
title: Key Investment Findings
category: "market-analysis"
description: Concise summary of the strongest findings from the 2017-2026 housing analysis, with technical details moved to appendices
status: published
date: 2026-02-06
personas:
  - investor
  - first-time-buyer
  - upgrader
readingTime: "8 min read"
technicalLevel: intermediate
---

# Key Investment Findings

**Last Updated**: 2026-02-06  
**Data Coverage**: 911,797 transactions (2017-2026)  
**Primary Analysis Window**: 2021-2026

## Key Takeaways

### The clearest finding

The market premium often attributed to MRT access is mostly a **city-access premium**. CBD distance explains **22.6%** of price variation on its own, while adding MRT access increases explanatory power by only **0.78 percentage points**.

### What matters most in practice

- **HDB buyers** should not overpay for MRT proximity alone. Lease remaining, affordability, and neighborhood quality matter more.
- **Condo buyers and investors** should still care about MRT access. Condo prices are roughly **15x** more MRT-sensitive than HDB prices.
- **Timing and segment matter**. Policy effects, lease decay, and forecast reliability differ materially across HDB, condo, and EC markets.

### Recommended decision order

1. Start with **segment**: HDB, condo, and EC behave differently.
2. Check **city access** before station access.
3. For HDB, focus on **lease and affordability**.
4. For condos, treat **MRT proximity as a real pricing factor**.
5. Use forecasts selectively: HDB and mass-market condo models are more reliable than luxury condo models.

## The Findings That Matter Most

### 1. CBD access explains more than MRT access

The most decision-useful location result is simple: centrality matters more than station distance.

| Model | R² | Main interpretation |
|------|----|---------------------|
| CBD only | 0.2263 | City access explains a meaningful share of pricing |
| CBD + MRT | 0.2341 | MRT adds only a modest incremental lift |
| Full model | 0.4977 | Broader housing features still matter materially |

**Impact**

- For **HDB**, paying a large premium purely for being a few hundred meters closer to MRT is usually hard to justify.
- For **condos**, MRT still matters, but as part of a broader accessibility package rather than as a standalone rule.

### 2. MRT sensitivity is highly segment-specific

The headline average hides a sharp split by property type.

| Property Type | MRT premium per 100m | Takeaway |
|--------------|----------------------|----------|
| HDB | about negative 1 to 5 dollars | Small effect |
| Condominium | about negative 19 to 46 dollars | Large effect |
| EC | roughly plus 6 to negative 37 dollars | Unstable effect |

**Impact**

- **Investors** targeting rental demand should prioritize MRT proximity for condos, not HDB.
- **Owner-occupiers** in HDB should treat MRT access as a convenience factor, not the main valuation anchor.
- **EC buyers** should be cautious about using historical MRT premiums as a stable guide.

### 3. Lease decay is real, but not linear

Remaining lease affects HDB prices, but not in a smooth straight line. The sharpest pricing pressure appears in the **70-80 year** lease band.

<div data-chart-metadata="true" data-chart="comparison" data-chart-title="Lease band discounts versus 90+ year HDBs" data-chart-columns="Discount vs 90+ yrs,Transactions"></div>

| Lease Band | Discount vs 90+ yrs | Transactions |
|------------|---------------------|--------------|
| 80-90 years | -13.2% | 29,562 |
| 70-80 years | -21.9% | 47,044 |
| 60-70 years | -23.8% | 54,521 |
| <60 years | -15.0% | 41,595 |

**Impact**

- **Buyers** can often find value in the **60-70 year** range if financing and holding period fit.
- **Sellers** of 90+ year leases should recognize they are selling into the market’s most favored band.
- Straight-line depreciation assumptions are not reliable enough for pricing decisions.

### 4. Forecast quality varies more by segment than by model brand

The important question is not “is there a model?” but “which market is being modeled?”

| Segment | R² | Directional accuracy | Practical use |
|--------|----|----------------------|---------------|
| HDB | 79.8% | 99.4% | Useful for timing and trend direction |
| EC | 98.5% | 97.1% | Strong, but sample is smaller |
| Mass market condo | 85.6% | 96.4% | Useful with caution |
| Luxury condo | 30.1% | 92.3% | Trend only, magnitude unreliable |

**Impact**

- HDB and mass-market condo forecasts can inform planning.
- Luxury condo forecasts should not be used as precise valuation tools.

### 5. Policy shocks do not transmit evenly across the market

Cooling measures appear to have worked in prime condo markets, but not in HDB.

| Policy question | Observed effect |
|-----------------|-----------------|
| Sep 2022 CCR condo cooling | about **-$137,743** relative effect vs OCR |
| Dec 2023 HDB cooling | about **+$13,118** immediate jump |

**Impact**

- Policy headlines are not enough. Buyers need to ask **which segment** is exposed.
- HDB buyers should be careful about delaying purchases based on a generic “prices may cool” narrative.

## So What Should Different Buyers Do?

### Investors

- Use **segment-specific rules**, not market-wide rules.
- Prioritize **MRT access for condos**, **lease and affordability for HDB**.
- Treat forecast outputs as stronger in HDB and mass-market condos than in luxury condos.

### First-time buyers

- Avoid stretching budget mainly for an MRT label on HDB listings.
- Compare lease, affordability, and town-level context before accessibility premiums.
- Be careful with “school premium” or “future MRT premium” claims unless the unit trade-offs are also clear.

### Upgraders

- OCR and selected RCR locations often provide the best balance between access and price.
- When selling HDB and buying condo, remember that the two segments price accessibility differently.

## Technical Appendix

### Data Used

- **Full dataset**: 911,797 transactions (2017-2026) across HDB, condo, and EC segments
- **Primary analysis window**: 2021-2026
- **Key inputs**: `data/parquets/L3/housing_unified.parquet`, `data/parquets/L1/housing_hdb_transaction.parquet`, `data/parquets/L1/housing_hdb_rental.parquet`
- **Detailed data sources**: see individual analysis documents for per-topic data specifics

### Methodology

Each finding draws from a distinct analytical pipeline. The table below cross-references the detailed analysis document and the underlying scripts.

| Finding Area | Analysis Doc | Key Scripts |
|-------------|-------------|-------------|
| CBD vs MRT decomposition | `mrt-impact.md` | `analyze_mrt_impact.py`, `analyze_cbd_mrt_decomposition.py` |
| MRT segment heterogeneity | `mrt-impact.md` | `analyze_mrt_heterogeneous.py`, `analyze_mrt_by_property_type.py` |
| Lease decay and band pricing | `lease-decay.md` | `analyze_lease_decay.py`, `analyze_lease_decay_advanced.py` |
| Price forecast reliability | `price-forecasts.md` | `forecast_prices.py`, `train_by_property_type.py`, `create_smart_ensemble.py` |
| School quality premium | `school-quality.md` | `analyze_school_impact.py`, `analyze_school_rdd.py`, `analyze_school_spatial_cv.py` |
| Spatial autocorrelation | `spatial-autocorrelation.md` | `analyze_spatial_autocorrelation.py`, `analyze_h3_clusters.py` |
| Rental hotspots | `spatial-hotspots.md` | `analyze_spatial_hotspots.py` |
| Policy causal effects | `causal-inference-overview.md` | `analyze_causal_did_enhanced.py`, `analyze_rd_policy_timing.py` |

### Technical Findings (Consolidated)

| Topic | Key Metric | Value | Confidence |
|-------|-----------|-------|------------|
| CBD effect | R² from CBD-only model | 0.2263 | High — robust across specifications |
| MRT incremental lift | ΔR² after adding MRT to CBD model | +0.0078 | High — hierarchical regression |
| Condo vs HDB MRT sensitivity | Relative magnitude | ~15× | High — consistent across OLS and XGBoost |
| Lease steepest penalty | 70-80 yr band discount | -21.9% vs 90+ yr | High — 47,044 transactions |
| Lease deepest discount | 60-70 yr band discount | -23.8% vs 90+ yr | High — 54,521 transactions |
| Pure lease effect | Per extra year (after controls) | +$54.75 PSF | Moderate — hedonic regression |
| HDB forecast accuracy | R² / directional accuracy | 79.8% / 99.4% | High — segment-specific XGBoost |
| Luxury condo forecast | R² / directional accuracy | 30.1% / 92.3% | Low — magnitude unusable |
| Ensemble vs unified | Accuracy improvement | 74% vs 47% | High — out-of-sample |
| School quality OLS | Coefficient | +$9.66 PSF | High — predictive |
| School RDD | Treatment effect at 1 km | -$79.47 PSF | Low — covariate balance failed |
| Spatial clustering | Moran's I / z-score | 0.766 / 9.91 | High — p < 0.001 |
| Rental hotspot selectivity | 99% confidence cells | 12 of 847 | High — Gi* statistic |
| CCR condo policy effect | DiD estimate (Sep 2022) | ~-$137,743 | Moderate — regime-specific |
| HDB policy response | RDiT jump (Dec 2023) | ~+$13,118 | Moderate — bandwidth-sensitive |

### Conclusion

Across all seven analysis domains, the most decision-useful findings share a common pattern: segment-level specificity matters far more than model sophistication. HDB and condo markets respond differently to MRT access, lease decay, policy shocks, and forecasting signals. The strongest technical evidence supports the CBD-over-MRT finding (R² decomposition), the non-linear lease decay curve (223K transactions), and the forecast reliability gradient across segments (74% ensemble accuracy). The weakest causal claims are around school quality premiums (RDD covariate balance failed) and luxury condo forecasting (R²=30.1%). All findings are strongest for the 2021-2026 market regime. Forecasts are best used as decision support, not standalone valuation.

### Scripts

All scripts referenced above are located under `scripts/analytics/analysis/`. See individual analysis documents for full script paths and methodology details.
