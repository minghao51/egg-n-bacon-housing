# Price Appreciation Forecasting Report - Design Document

**Date:** 2026-02-19
**Status:** Design Approved - Pending Implementation
**Author:** Claude (brainstorming session with user)
**Type:** Analytics Report Design

---

## Overview

Design a comprehensive analytics report translating the VAR (Vector Autoregression) forecasting system into actionable insights for property buyers and investors in Singapore.

**Target Document:** `app/src/content/analytics/analyze_price_appreciation_predictions.md`

**Reference Documents:**
- `docs/analytics/20250217-var-implementation-report.md` (VAR system technical documentation)
- `docs/analytics/analyze_mrt-impact-analysis.md` (Style reference for buyer-friendly analytics)

---

## Purpose & Audience

**Primary Purpose:** Translate technical VAR forecasts into buyer-friendly insights that help readers make data-driven property decisions.

**Target Audiences:**
1. **First-time HDB buyers** - Focus on affordability, entry-level decisions, timing
2. **Property investors/flippers** - Focus on appreciation potential, regional comparisons, timing strategies
3. **HDB upgraders** - Focus on maximizing resale value, optimal selling timing

**Key Insight (Hook):**
> "Scenario planning beats market timing" + "24-month visibility into appreciation"

Don't guess the market - plan for multiple scenarios with data-driven 24-month forecasts that reduce guesswork.

---

## Report Specifications

| Attribute | Value |
|-----------|-------|
| **Length** | ~800-1000 lines (similar to MRT analysis) |
| **Reading Time** | 15 minutes |
| **Technical Level** | Intermediate (accessible to non-technical readers) |
| **Update Frequency** | One-time static report (update only for major methodology changes) |
| **Visualization Suite** | Full (10 charts/figures) |
| **Component Library** | Same as MRT analysis (Astro components) |

---

## Content Structure

### 1. Front Matter & Key Takeaways (~200 lines)

**Front Matter:**
```yaml
---
title: Price Appreciation Forecasts - Singapore Housing Market
category: "market-analysis"
description: 24-month VAR-based price appreciation forecasts with scenario planning
status: published
date: 2026-02-XX
personas:
  - first-time-buyer
  - investor
  - upgrader
readingTime: "15 min read"
technicalLevel: intermediate
---
```

**Component Imports:**
```markdown
import Tooltip from '@/components/analytics/Tooltip.astro';
import StatCallout from '@/components/analytics/StatCallout.astro';
import ImplicationBox from '@/components/analytics/ImplicationBox.astro';
import Scenario from '@/components/analytics/Scenario.astro';
import DecisionChecklist from '@/components/analytics/DecisionChecklist.astro';
```

**Key Takeaways Section:**
- **The One Big Insight:** "Scenario planning beats market timing"
- **What This Means For You:** Bullet points for each persona (first-time buyer, investor, upgrader)
- **✅ Action Steps:** 5 concrete steps for using forecasts
- **📊 By The Numbers:** 4-5 `<StatCallout>` components showing:
  - Forecast horizon (24 months)
  - Regional appreciation spread (e.g., "OCR: 8-12%, CCR: 3-7%")
  - Confidence interval ranges
  - Scenario variance (bullish vs bearish)

---

### 2. Executive Summary (~150 lines)

**Purpose:** Give readers the complete picture in 2-3 minutes

**Content:**
- Brief overview of VAR forecasting system (non-technical)
- What regions/planning areas are covered
- Forecast horizon and confidence levels
- Top 3 findings from the forecasts
- Link to forecasting dashboard

**Tone:** High-level, skip methodology details, focus on actionable insights

---

### 3. Methodology - "How We Forecast" (~200 lines)

**Purpose:** Build credibility, explain without overwhelming

**Subsections:**

**3.1 Two-Stage Hierarchical VAR System**
- Stage 1: Regional models (7 regions)
- Stage 2: Planning area models (~20 high-volume areas)
- Why hierarchical: Regional macro → local performance

**3.2 What Goes Into Forecasts**
- Historical appreciation rates
- Transaction volumes
- Macroeconomic factors (SORA, CPI, GDP)
- Housing policy changes

**3.3 Scenario Modeling**
- Baseline, bullish, bearish, policy_shock
- How scenarios differ (interest rates, policy changes)
- Confidence intervals explained simply

**3.4 Performance & Validation**
- Backtesting results (RMSE, directional accuracy)
- Model limitations

**Visualizations:**
- Flowchart showing two-stage hierarchy
- Example forecast curve with confidence bands

---

### 4. Regional Outlook - "Where Will Prices Grow?" (~250 lines)

**Purpose:** Answer the #1 question: "Which regions will appreciate most?"

**Structure:**

**4.1 Regional Comparison Table**
- All 7 regions with 24-month forecasts
- Baseline, bullish, bearish scenarios
- Confidence intervals

**4.2 Deep Dive: Top 3 Regions**
- Each with 3-4 paragraphs explaining:
  - Why it's forecasted to appreciate
  - Key drivers (e.g., new MRT lines, development plans)
  - Planning area highlights within region

**4.3 Deep Dive: Bottom 2 Regions**
- Why lower appreciation
- Risks to consider

**Visualizations:**
- Regional forecast comparison chart (line chart, 24 months, 3 scenarios each)
- Regional heatmap (choropleth map with forecast bands)

**StatCallouts:**
- Highest appreciation region
- Most stable region (narrowest confidence band)
- Best risk/reward region

---

### 5. Planning Area Forecasts - "Pinpoint Your Search" (~200 lines)

**Purpose:** Help buyers narrow down to specific neighborhoods

**Coverage:** Top 15-20 planning areas by transaction volume

**Structure:**

**5.1 Planning Area Ranking Table**
- Sorted by baseline forecast appreciation
- Show region, forecast, confidence, scenario spread

**5.2 Area Spotlight Sections** (3-4 high-interest areas)
- Each with:
  - Forecast overview
  - Why it's appreciating
  - Local developments
  - Comparison to region average

**5.3 Regional Grouping**
- "If you're eyeing CCR, consider: Downtown, Newton, Orchard..."
- "If you're eyeing OCR East, consider: Pasir Ris, Tampines..."

**Visualizations:**
- Planning area forecast chart (top 15 areas, side-by-side bars)
- Scatter plot: current price vs forecast appreciation (identify undervalued areas)

---

### 6. Scenario Analysis - "Plan for Uncertainty" (~150 lines)

**Purpose:** Teach readers how to use scenario planning

**Content:**

**6.1 Scenario Explainer**
- What each scenario means (baseline, bullish, bearish, policy_shock)
- How to interpret confidence intervals

**6.2 Scenario Comparison Table**
- Side-by-side scenario forecasts for all regions
- Show spread: "OCR: 8% baseline, 5% bearish, 12% bullish"

**6.3 Strategy Framework**
- "Buy if: All scenarios > 5% appreciation"
- "Buy if: Baseline > X AND bearish > Y%"
- "Avoid if: Bearish scenario shows negative appreciation"

**Visualizations:**
- Scenario fan chart (baseline with confidence bands)
- Tornado chart: which factors most impact forecasts

---

### 7. Persona-Specific Guidance (~200 lines)

**Purpose:** Translate forecasts into action for each user type

**7.1 First-Time Buyers Section**
```markdown
<ImplicationBox persona="first-time-buyer">
**For First-Time Buyers:** Don't chase hot areas, find stable appreciation.

- Focus on affordability + steady growth (OCR regions)
- Best regions for first-time buyers: OCR North, OCR East
- How to use forecasts: Look for narrow confidence bands (low risk)
- Avoid: Regions with bearish scenarios < 3%
</ImplicationBox>
```

**7.2 Investors Section**
```markdown
<ImplicationBox persona="investor">
**For Investors:** Maximize appreciation with scenario-based risk management.

- Top picks for investors: CCR areas with bullish upside
- How to use forecasts: Portfolio diversification across regions
- Strategy: Buy if bearish scenario still > 5%
- Consider: Scenario spread as risk indicator
</ImplicationBox>
```

**7.3 Upgraders Section**
```markdown
<ImplicationBox persona="upgrader">
**For Upsizers:** Time your sale and purchase using regional forecasts.

- When to sell: Check your region's forecast peak
- Where to upgrade: Balance appreciation vs affordability
- Strategy: Sell in flat/growth regions, buy in high-appreciation areas
- Timeline: Align 24-month forecast with your upgrade plans
</ImplicationBox>
```

**Visualizations:**
- Decision tree: "What type of buyer are you?" → forecast recommendations

---

### 8. Scenario-Based Decision Frameworks (~150 lines)

**Purpose:** Put forecasts into practice with concrete examples

**Content:** 2-3 `<Scenario>` components

**Example Scenario 1:**
```markdown
<Scenario title="First-Time Buyer with $600K Budget - OCR or RCR?">
**Situation:** You're choosing between:
- Option A: 4-room HDB in Pasir Ris (OCR East) - $600K
- Option B: 4-room HDB in Bishan (RCR) - $600K

**Our Forecasts Say:**
- OCR East 24-month forecast: 10.5% ± 2% (Baseline: 10.5%, Bearish: 8%, Bullish: 13%)
- RCR 24-month forecast: 6.2% ± 3% (Baseline: 6.2%, Bearish: 3%, Bullish: 10%)

**Your Decision Framework:**
1. Check risk tolerance: OCR has narrower band (±2% vs ±3%)
2. Consider total appreciation: OCR = $63K, RCR = $37K (baseline)
3. Evaluate downside: OCR bearish = 8% ($48K), RCR bearish = 3% ($18K)
4. Assess trade-offs: RCR has location premium, OCR has growth potential

**Bottom Line:** If you can hold 24+ months, OCR East offers better appreciation. If you might sell earlier, RCR's stable location premium may be safer. Consider lifestyle factors too (commute, amenities).
</Scenario>
```

**Example Scenario 2:**
```markdown
<Scenario title="Investor - Condo in CCR Now or Wait for Price Correction?">
**Situation:** [Investment scenario with forecasts]

**Our Forecasts Say:**

**Your Decision Framework:**

**Bottom Line:**
</Scenario>
```

---

### 9. Forecasting Dashboard Integration (~50 lines)

**Purpose:** Connect report to interactive dashboard

**Content:**
- Link to live forecasting dashboard
- How to use dashboard: "Filter by region, scenario, property type"
- What's in dashboard: Interactive charts, custom forecasts
- "This report shows the Feb 2026 forecast; dashboard always has latest"

**Visualization:** Screenshot of dashboard with annotations

---

### 10. Technical Appendix (~100 lines)

**Purpose:** Detailed technical info for interested readers

**Content:**

**10.1 Data Sources**
- What data feeds the forecasts
- Update schedule

**10.2 Model Performance**
- RMSE, MAE, MAPE by region
- Backtesting results

**10.3 Forecast Horizon**
- Why 24 months for areas, 36 months for regions
- Forecast accuracy over time

**10.4 Known Limitations**
- What forecasts can't predict (black swan events)
- Confidence interval interpretation

**Tone:** More technical, but still accessible

---

### 11. Decision Checklist (~50 lines)

**Purpose:** Actionable checklist for using forecasts

**Component:**
```markdown
<DecisionChecklist
  title="Use this checklist when evaluating any property purchase"
  storageKey="forecast-decision-checklist"
>
- [ ] **What's the 24-month forecast for this region?** (Check regional outlook)
- [ ] **How do scenarios compare?** (If bearish < 3%, reconsider)
- [ ] **What's driving the forecast?** (New MRT? Policy changes? Supply constraints?)
- [ ] **How wide is the confidence band?** (Wide bands = higher uncertainty)
- [ ] **Does this match my time horizon?** (24-month forecast vs 5-year holding plan)
- [ ] **What do all 3 scenarios say?** (Buy if all scenarios show appreciation)
- [ ] **How does this area compare to its region?** (Above or below regional average?)
- [ ] **Am I paying for forecasted appreciation?** (Check if premium already priced in)
</DecisionChecklist>
```

---

### 12. Related Analytics & Document History (~30 lines)

**Related Analytics:**
- Price Appreciation Predictions (this report)
- MRT Impact Analysis
- Lease Decay Analysis
- Master Findings Summary

**Document History:**
- **2026-02-19 (v1.0)**: Initial design and structure
- Version history with dates and changes to be added as report evolves

---

## Visualizations Summary

**Required Charts** (10 total):

| # | Chart Type | Description | Generated From |
|---|------------|-------------|----------------|
| 1 | Flowchart | Two-stage VAR hierarchy | Custom visualization script |
| 2 | Line Chart | Example forecast curve with confidence bands | `forecast_appreciation.py` output |
| 3 | Line Chart | Regional forecast comparison (7 regions × 3 scenarios) | `forecast_appreciation.py` |
| 4 | Choropleth Map | Regional heatmap with forecast bands | `forecast_appreciation.py` |
| 5 | Bar Chart | Planning area forecast comparison (top 15) | `forecast_appreciation.py` |
| 6 | Scatter Plot | Current price vs forecast appreciation | `forecast_appreciation.py` |
| 7 | Fan Chart | Scenario fan chart with confidence bands | `forecast_appreciation.py` |
| 8 | Tornado Chart | Factor sensitivity analysis | `forecast_appreciation.py` |
| 9 | Decision Tree | Buyer type → forecast recommendations | Custom visualization |
| 10 | Screenshot | Dashboard with annotations | Existing dashboard |

**Output Location:** All charts exported to `app/public/data/analysis/price_forecasts/`

---

## Data Requirements

### From VAR Pipeline

**Regional Forecasts:**
- 7 regions × 4 scenarios (baseline, bullish, bearish, policy_shock)
- 36-month horizon
- 95% confidence intervals
- Backtesting performance metrics

**Planning Area Forecasts:**
- ~20 high-volume areas
- 4 scenarios each
- 24-month horizon
- 95% confidence intervals

### From Existing Data

- Regional mapping: `scripts/core/regional_mapping.py`
- Planning area transaction volumes: L2 parquets
- Current median prices by area: L2 parquets

### Placeholders to Fill In

All forecast numbers will be placeholders until VAR pipeline runs with real data:

**Example Placeholders:**
```markdown
- "OCR 24-month forecast: [X]% ± [Y]%"
- "Top region by appreciation: [Region Name] at [X]%"
- "Planning area #1: [Area Name] - [X]% forecast"
```

---

## Content Generation Guidelines

### Tone & Voice

**Overall Tone:** Professional but accessible, similar to MRT analysis

**Key Principles:**
- Lead with actionable insights, bury methodology
- Use scenarios to teach decision-making, not just present numbers
- Persona-specific sections make it relevant
- Decision checklist converts insights to action

### Writing Style

**Headings:** Action-oriented and question-based
- ✓ "Where Will Prices Grow?"
- ✓ "How to Use Forecasts for Your Situation"
- ✗ "Regional Analysis Results"

**Explanations:** Always answer "So What?"
- ✓ "OCR will appreciate 10%. This means a $500K HDB could gain $50K in 2 years."
- ✗ "OCR forecasted appreciation is 10%."

**Uncertainty:** Embrace it, don't hide it
- ✓ "Our model forecasts 8-12% with 95% confidence"
- ✗ "Our model predicts 10%"

### Consistency with MRT Analysis

**Similarities:**
- Same front matter structure
- Same component library (Tooltip, StatCallout, ImplicationBox, Scenario, DecisionChecklist)
- Similar section flow: Key Takeaways → Executive Summary → Methodology → Findings → Implications
- Same visual polish

**Differences:**
- **Focus:** Future (forecasts) vs past (historical analysis)
- **Uncertainty:** Confidence intervals, scenarios everywhere (MRT has less uncertainty)
- **Action:** "Plan for multiple outcomes" vs "understand historical patterns"

---

## Implementation Workflow

### Phase 1: Data Preparation (Prerequisite)

**Tasks:**
1. Generate L3 unified dataset from existing transaction data
2. Run full VAR forecasting pipeline with real data
3. Generate all 10 visualizations
4. Export forecast data to JSON for webapp

**Deliverables:**
- Regional forecast CSVs
- Planning area forecast CSVs
- All visualization PNGs
- Forecast JSON for dashboard

### Phase 2: Report Writing

**Tasks:**
1. Create report structure following this design document
2. Fill in methodology section (can be written now, based on VAR implementation report)
3. Fill in placeholder content for all forecast-dependent sections
4. Add all StatCallouts, ImplicationBoxes, Scenarios with placeholders

**Deliverables:**
- Complete report markdown with placeholders
- Ready for data insertion

### Phase 3: Data Insertion & Finalization

**Tasks:**
1. Replace all placeholders with actual forecast numbers
2. Generate all visualizations
3. Insert visualization links
4. Write scenario examples using real data
5. Create decision checklist with specific thresholds
6. Front matter: Set publication date

**Deliverables:**
- Final report ready for publication
- All visualizations in place
- Review copy for accuracy

### Phase 4: Review & Publish

**Tasks:**
1. Technical review: Verify forecast accuracy
2. Editorial review: Check clarity and tone
3. Link validation: Ensure all dashboard links work
4. Commit to git with proper message
5. Deploy to analytics site

**Deliverables:**
- Published report
- Git commit with changelog

---

## Success Criteria

**Content Requirements:**
- ✅ All 12 sections complete
- ✅ All 10 visualizations generated and embedded
- ✅ All 3 personas addressed with specific guidance
- ✅ At least 2 scenario examples with real data
- ✅ Decision checklist with 8+ actionable items
- ✅ Zero placeholders in final version

**Quality Requirements:**
- ✅ All forecast numbers sourced from VAR pipeline output
- ✅ All claims backed by data (no speculation)
- ✅ Confidence intervals clearly communicated
- ✅ Scenario logic explained simply
- ✅ Action steps specific and measurable

**Technical Requirements:**
- ✅ Markdown file valid for Astro processing
- ✅ All image paths correct and relative
- ✅ All component imports valid
- ✅ Front matter complete and accurate
- ✅ Links to dashboard functional

---

## Open Questions

1. **Forecast Refresh Schedule:** When will VAR pipeline be re-run? (Quarterly? Monthly?)
   - **Decision:** Report is one-time, but should note when forecasts will be refreshed

2. **Dashboard Integration:** Does interactive dashboard exist yet?
   - **Action Needed:** Confirm dashboard URL and screenshot

3. **Planning Area Coverage:** Exactly which 15-20 areas will be included?
   - **Decision Needed:** Top areas by transaction volume

4. **Scenario Definitions:** Are bullish/bearish/policy_shock clearly defined?
   - **Action Needed:** Document scenario assumptions in appendix

---

## References

**Source Documents:**
- `docs/analytics/20250217-var-implementation-report.md` - VAR system technical details
- `docs/analytics/analyze_mrt-impact-analysis.md` - Style and structure reference

**Implementation Plan:** To be created by `writing-plans` skill (next step)

**Output Files:**
- Report: `app/src/content/analytics/analyze_price_appreciation_predictions.md`
- Visualizations: `app/public/data/analysis/price_forecasts/*.png`
- Forecast Data: `app/public/data/analysis/price_forecasts/*.csv`

---

## Next Steps

1. ✅ Design document approved
2. ⏭️ Invoke `writing-plans` skill to create detailed implementation plan
3. ⏭️ Complete Phase 1: Data preparation (run VAR pipeline)
4. ⏭️ Complete Phase 2: Write report structure with placeholders
5. ⏭️ Complete Phase 3: Insert real data and generate visualizations
6. ⏭️ Complete Phase 4: Review, publish, and deploy

---

**End of Design Document**
