---
title: Policy Impact
category: "market-analysis"
description: What the causal analysis suggests about cooling measures, timing effects, and lease-related mispricing across major housing segments
status: published
date: 2026-02-06
personas:
  - investor
  - first-time-buyer
  - upgrader
readingTime: "8 min read"
technicalLevel: intermediate
---

# Policy Impact & Market Dynamics

**Analysis Date**: 2026-02-06  
**Data Period**: 2017-2026  
**Coverage**: HDB, condominium, and EC market dynamics

## Key Takeaways

### The clearest finding

Cooling measures do **not** transmit evenly across Singapore housing segments. The condo market showed measurable suppression in prime districts, while HDB prices remained resilient and in this sample even moved higher after a major policy event.

### What this means in practice

- **Investors** should avoid treating policy news as a market-wide signal.
- **First-time HDB buyers** should be cautious about delaying purchases purely on expectations of policy-driven price declines.
- **Cash buyers** may find selective lease-related mispricing where financing constraints distort demand.

## Core Findings

### 1. Prime condos reacted differently from HDB

| Policy event | Segment | Observed effect | Interpretation |
|-------------|---------|-----------------|----------------|
| Sep 2022 ABSD changes | CCR condos vs OCR | about -$137,743 relative effect | Prime condos were meaningfully suppressed |
| Dec 2023 cooling measures | HDB | about +$13,118 immediate jump | HDB did not show the intended cooling response |

**Impact**

- Private and public housing should not be modeled as one policy-response market.
- Buyers need segment-specific expectations when interpreting regulation.

### 2. Timing matters, not just the existence of a policy

The causal work suggests that immediate level changes and post-announcement slope changes can tell different stories from simple before-and-after comparisons.

| Timing lens | What it adds |
|------------|--------------|
| Difference-in-differences | Relative segment effect |
| Regression discontinuity in time | Immediate jump and slope-change behavior |

**Impact**

- Policy effects can look muted in a broad average while still creating short-lived buying or selling windows.
- Analysts should avoid relying only on simple period splits.

### 3. Lease mispricing is concentrated, not universal

| Lease range | Signal |
|------------|--------|
| 30-50 years | Market appears richly priced relative to theory |
| 80-84 years | Mild undervaluation in some cases |
| 97-98 years | Large discount relative to theoretical schedule |

**Impact**

- Not all short leases are bargains.
- Near-fresh leases may offer value mainly to buyers not constrained by typical financing behavior.

## Decision Guide

### For investors

- Separate **policy-sensitive condo exposure** from **resilient HDB exposure**.
- Use policy events to improve entry discipline, not to justify broad market calls.

### For first-time buyers

- In HDB, affordability and unit fit still matter more than trying to “game” policy announcements.

### For upgraders

- If selling HDB and buying condo, remember you are moving between segments with different policy sensitivity.

## Technical Appendix

### Data Used

- **Primary input**: `data/parquets/L3/housing_unified.parquet`
- **Coverage**: 2017-2026, split by property type (Condominium, HDB)
- **Condo DiD sample**: Condominium transactions post-2021, CCR vs OCR
- **HDB RDiT sample**: HDB transactions, Jun 2022 - Jun 2025 (18 months before/after policy)

### Methodology

- **Regional classification**: CCR (10 planning areas — Bukit Timah, Downtown Core, Orchard, River Valley, etc.), RCR (12 planning areas — Bishan, Queenstown, Toa Payoh, Novena, etc.), OCR (remainder)
- **Difference-in-differences (DiD)** via `scripts/analytics/analysis/causal/analyze_causal_did_enhanced.py`:
  - Treatment: CCR condos; Control: OCR condos
  - Policy event: Sep 2022 ABSD changes for foreigners
  - Regression: `price ~ treatment + post + treatment × post`
  - Minimum 100 transactions per group
- **Regression discontinuity in time (RDiT)** via `scripts/analytics/analysis/causal/analyze_rd_policy_timing.py`:
  - Running variable: months since policy (negative = before, positive = after)
  - Policy event: Dec 2023 cooling measures
  - Bandwidth: ±6 months (default), robustness tested at 3, 6, 9, 12 months
  - Jump test: `price ~ post`; Kink test: `price ~ months_since + post + post × time`
  - Minimum 100 transactions for analysis
- **Lease mispricing**: empirical market pricing vs theoretical Bala depreciation schedule, ≥5% deviation flagged

### Technical Findings

- **Condo DiD**: ~-$137,743 relative effect (CCR vs OCR, Sep 2022 ABSD) — prime condos meaningfully suppressed
- **HDB RDiT**: ~+$13,118 immediate jump after Dec 2023 measures — HDB did not show intended cooling
- **Lease mispricing patterns**:
  - 30-50 yr range: market appears richly priced relative to Bala theory
  - 80-84 yr range: mild undervaluation in some cases
  - 97-98 yr range: large discount relative to theoretical schedule
- **Robustness**: RDiT bandwidth sensitivity (3-12 months) confirms direction is stable, magnitude varies

### Conclusion

The causal evidence supports segment-specific policy transmission: prime condos absorbed a measurable price suppression (~$138K) from ABSD changes, while HDB showed resilience or even upward movement (+$13K) after cooling measures. This asymmetry is robust across multiple bandwidths and timing windows. The lease mispricing analysis suggests that the market does not price strictly to theoretical Bala depreciation — shorter leases (30-50 yr) may be richly valued while near-fresh leases (97-98 yr) trade at unexpected discounts, possibly due to financing constraints distorting the buyer pool. Key limitations: DiD relies on comparability of CCR and OCR condo segments; RDiT assumes no confounding events at the cutoff; causal estimates are regime-specific and should not be treated as timeless constants.

### Scripts

- `scripts/analytics/analysis/causal/analyze_causal_did_enhanced.py` — DiD with CCR/OCR regions
- `scripts/analytics/analysis/causal/analyze_rd_policy_timing.py` — RDiT around policy events
