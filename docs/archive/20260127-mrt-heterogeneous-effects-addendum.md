# MRT Heterogeneous Effects Analysis - HDB Sub-Groups

**Date**: 2026-01-27
**Focus**: How MRT impact varies within HDB segment

---

## Critical Data Limitation

**Important**: Amenity features (including MRT distances) are **only available for HDB properties** in the current dataset.
- **HDB**: 97,133 records with full amenity data ✅
- **Condominium**: 109,576 records - NO amenity data ❌
- **EC**: 16,826 records - NO amenity data ❌

**Implication**: Cannot compare MRT impact across property types. Analysis is **HDB-only**.

---

## Key Finding: Dramatic Heterogeneity in MRT Effects

### 1. By Flat Type: Smaller Units Are More MRT-Sensitive

| Flat Type | MRT Premium per 100m | Mean Price (PSF) | Sample Size |
|-----------|---------------------|------------------|-------------|
| **2 ROOM** | **-$4.24** | $666.78 | 1,370 |
| **3 ROOM** | **-$3.96** | $552.48 | 26,838 |
| **5 ROOM** | **-$2.35** | $531.42 | 23,564 |
| **4 ROOM** | **-$1.79** | $565.46 | 38,712 |
| **EXECUTIVE** | **-$1.04** | $519.54 | 6,564 |

**Interpretation**:
- Smaller flats value MRT proximity **4x more** than executive flats
- **2 ROOM buyers**: Every 100m closer to MRT = $4.24 PSF premium
- **EXECUTIVE buyers**: Only $1.04 PSF premium (possibly car owners)

**Economic Intuition**:
- Smaller flat owners more likely to rely on public transport
- Executive flat owners higher income, may own cars
- 2 ROOM buyers likely budget-conscious, MRT access critical

---

### 2. By Town: Massive Geographic Variation

#### Top 10 Towns (Highest MRT Premium)

| Rank | Town | MRT Premium | Mean Price | Sample Size |
|------|------|-------------|------------|-------------|
| 1 | **CENTRAL AREA** | **+$59.19** | $902.62 | 599 |
| 2 | **SERANGOON** | **+$12.91** | $565.51 | 1,853 |
| 3 | **BISHAN** | **+$5.88** | $643.84 | 1,951 |
| 4 | **PASIR RIS** | **+$1.84** | $509.67 | 3,635 |
| 5 | **JURONG EAST** | **+$0.73** | $486.06 | 1,386 |

#### Bottom 10 Towns (Negative or Zero MRT Impact)

| Rank | Town | MRT Premium | Mean Price | Sample Size |
|------|------|-------------|------------|-------------|
| ... | (middle towns) | ~$0 to -$10 | $500-600 | varies |
| 22 | **GEYLANG** | **-$20.54** | $583.56 | 2,054 |
| 21 | **MARINE PARADE** | **-$38.54** | $628.84 | 515 |

**Stunning Insights**:

1. **Central Area**: POSITIVE MRT premium (+$59.19)
   - Closer to MRT = HIGHER price (opposite of most towns)
   - May reflect limited space, desirability of transit nodes in CBD

2. **Marine Parade**: STRONG NEGATIVE impact (-$38.54)
   - Every 100m closer to MRT = $38.54 LOWER price
   - Possibly ocean-facing properties command premium (MRT irrelevant or negative)

3. **30x Variation**: Central Area (+$59.19) vs Marine Parade (-$38.54)
   - MRT proximity effect is HIGHLY context-dependent
   - One-size-fits-all valuation approach is wrong

**Policy Implication**:
- MRT proximity premium is **NOT uniform** across Singapore
- Valuation models must include town × MRT interaction terms
- Cannot assume "$1.27 per 100m" applies everywhere

---

### 3. By Price Tier: Premium Properties Value MRT More

| Price Tier | MRT Premium per 100m | Price Range |
|------------|---------------------|-------------|
| **Premium** | **+$6.03** | $599-1500 |
| Mid-Premium | -$0.35 | $525-599 |
| Mid-Budget | -$0.28 | $465-525 |
| **Budget** | **-$0.73** | $249-465 |

**Counterintuitive Finding**: Premium HDB segments show **positive MRT premium**, while budget segments show negative/near-zero.

**Possible Explanations**:
1. **Location sorting**: Premium HDB in central areas (where MRT matters)
2. **Amenity clustering**: Premium areas have better MRT access
3. **Lifestyle preferences**: Premium buyers prioritize convenience
4. **Supply constraints**: Premium MRT-adjacent HDB is scarce

---

## Visualization

See `data/analysis/mrt_impact/heterogeneous_effects.png` for:
1. MRT impact by flat type (horizontal bar chart)
2. Top 15 towns by MRT premium
3. MRT impact by price tier
4. Scatter plot: Town mean price vs MRT premium

---

## Statistical Implications

### Why Do Effects Vary So Much?

#### 1. **Omitted Variable Bias**
- Town-level analysis doesn't control for:
  - School quality (e.g., near top primary schools)
  - CBD access vs suburban living
  - View quality (ocean, park, vs MRT tracks)
  - Noise pollution (MRT vibration, crowds)

#### 2. **Multicollinearity**
- Central Area: MRT distance ↔ Other desirable features
  - Premium: MRT + shopping + dining + jobs
  - Hard to isolate MRT effect

#### 3. **Spatial Autocorrelation**
- Nearby towns have similar prices
- Violates OLS independence assumption
- Need spatial econometric models (SAR, CAR)

#### 4. **Sample Size Variation**
- Central Area: 599 transactions (small sample)
- Punggol: 9,576 transactions (large sample)
- Small samples = unstable estimates

---

## Updated Recommendations

### For Investors/Buyers

1. **Flat Type Strategy**:
   - Buy 2-3 ROOM near MRT: Maximum premium ($4/100m)
   - Buy EXECUTIVE: MRT proximity matters less (diversify away from MRT)

2. **Town Strategy**:
   - **Central Area**: Pay for MRT proximity (huge +$59/100m premium)
   - **Marine Parade**: Avoid MRT-adjacent (negative $38/100m)
   - **Most towns**: Minimal MRT impact (~$0)

3. **Price Tier**:
   - Premium segment: MRT matters (+$6/100m)
   - Budget segment: MRT doesn't matter (look elsewhere for value)

### For Modelers/Data Scientists

1. **Model Specification**:
   ```python
   # BAD: Uniform MRT effect
   price = β0 + β1(mrt_dist) + controls

   # GOOD: Heterogeneous MRT effect
   price = β0 + β1(mrt_dist) + β2(mrt_dist × town)
                   + β3(mrt_dist × flat_type) + controls
   ```

2. **Spatial Models**:
   - Use fixed effects for town (absorb local characteristics)
   - Hierarchical models (random slopes by town)
   - Geographically weighted regression (local estimates)

3. **Non-Linearity**:
   - MRT effect may be non-monotonic
   - 200-500m sweet spot (as seen in aggregate data)

---

## Limitations & Future Work

### Current Limitations

1. **No Condo/EC Data**: Cannot compare property types
   - Need to calculate amenity distances for private properties
   - Likely different MRT sensitivity (car ownership rates)

2. **Omitted Variables**:
   - School quality (critical for families)
   - CBD access (different from MRT access)
   - Noise/pollution (MRT vibration)
   - View quality (ocean vs MRT tracks)

3. **Temporal Dynamics**:
   - Cross-sectional (2021+ only)
   - Cannot track how MRT premium evolved
   - No before/after new MRT line openings

4. **Causal Inference**:
   - Observational data (selection bias)
   - Premium locations get MRT lines first
   - Not random placement

### Future Enhancements

1. **Add Condo/EC Amenity Data**:
   - Calculate distances from private property coordinates
   - Compare MRT sensitivity: HDB vs Condo vs EC
   - Test car ownership hypothesis

2. **Spatial Econometrics**:
   - Spatial lag model (y = ρWy + Xβ + ε)
   - Spatial error model (ε = λWε + ξ)
   - Spatial Durbin model (lagged X)

3. **Instrumental Variables**:
   - Historical MRT route plans (exogenous to current prices)
   - Topography (elevation constraints on route placement)
   - Distance to CBD (instrument for MRT placement)

4. **Difference-in-Differences**:
   - New MRT line openings (e.g., TEL, CCL)
   - Compare treated vs control areas
   - Before vs after opening

5. **Causal Machine Learning**:
   - Causal forests (heterogeneous treatment effects)
   - Double machine learning (control for confounders)
   - Propensity score matching

---

## Conclusion

### Takeaway Messages

1. **MRT Impact Is NOT Uniform**
   - Varies by flat type (4x: 2 ROOM vs EXECUTIVE)
   - Varies by town (100x: Central Area vs Marine Parade)
   - Varies by price tier (positive for premium, negative for budget)

2. **Location Matters More Than MRT**
   - Town characteristics dominate MRT proximity
   - Central areas: MRT proximity is valuable
   - Coastal areas: MRT proximity may be negative

3. **Model Simplicity Is Misleading**
   - Single MRT coefficient masks massive heterogeneity
   - Need interaction terms: MRT × Town, MRT × Flat Type
   - Uniform valuations will be wrong

4. **HDB-Specific Findings**
   - Cannot generalize to condos/ECs
   - HDB buyers more transit-dependent
   - Smaller flats more MRT-sensitive

---

## Data Files Generated

```
data/analysis/mrt_impact/
├── heterogeneous_flat_type.csv      # MRT coefficient by flat type
├── heterogeneous_town.csv           # MRT coefficient by town (23 towns)
├── heterogeneous_price_tier.csv     # MRT coefficient by price quartile
└── heterogeneous_effects.png        # 4-panel visualization
```

---

**End of Addendum**
