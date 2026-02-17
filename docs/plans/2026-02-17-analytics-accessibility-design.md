# Analytics Documentation Accessibility Improvements - Design Document

**Date:** 2026-02-17
**Status:** Approved
**Author:** Claude (with stakeholder approval)

---

## Overview

Transform the analytics documentation from technical reports into accessible, actionable guides for non-technical users. This design addresses four critical barriers:

1. **Technical terminology** - Jargon without plain English explanations
2. **Lack of actionable guidance** - Stats without clear "what to do" implications
3. **Information overload** - Dense tables without visual hierarchy
4. **Unclear relevance** - Users can't find content matching their situation

**Pilot Document:** MRT Impact Analysis (`docs/analytics/analyze_mrt-impact-analysis.md`)

---

## Core Features

### 1. Persona-Based Navigation

Three core personas to help users find relevant content:

**First-Time Home Buyer** (🏠)
- Buying first HDB/condo for owner-occupation
- Cares about: Affordability, lease decay, location value
- Curated docs: Lease decay, price predictions, affordability analysis

**Property Investor** (💼)
- Building investment portfolio (rental or capital appreciation)
- Cares about: Price appreciation, MRT/CBD premiums, market timing
- Curated docs: Price predictions, MRT impact, clustering analysis, policy effects

**Upsizer / Upgrader** (⬆️)
- Moving from smaller to larger property (HDB → condo, or larger HDB)
- Cares about: Maximizing sale price, finding best value upgrade location
- Curated docs: Price appreciation, MRT impact, market forecasts

**Implementation:** Create `app/src/pages/analytics/personas/{first-time-buyer,investor,upgrader}.astro`

---

### 2. Enhanced Document Structure

**New Top Section for Each Analytics Document:**

```markdown
## Key Takeaways (📋)

**💡 The One Big Insight**
One-sentence revolutionary finding

**🎯 What This Means For You**
3 bullet points translating technical findings into plain English implications

**✅ Action Steps**
3-5 concrete actions users can take

**📊 By The Numbers**
3-5 key statistics in visual callout boxes
```

**Enhanced Executive Summary:**
- Keep existing 3 critical insights format
- Add "Who should read this" badge (First-time buyer, Investor, Upgrader, or All)
- Add "Reading time" and "Technical level" indicators

---

### 3. Visual & Accessibility Enhancements

**A. Inline Tooltips for Technical Terms**

Astro component: `<Tooltip term="H3 hexagons">`

- Renders as underlined/dotted text showing tooltip on hover/tap
- Tooltip content: Plain English explanation + "Why it matters"
- Glossary data source: `app/src/data/analytics-glossary.json`

**Sample glossary entries:**
```json
{
  "H3 hexagons": {
    "explanation": "A grid system that divides Singapore into hexagonal areas, like a honeycomb pattern",
    "whyItMatters": "Lets us compare property values across neighborhoods consistently"
  },
  "VAR model": {
    "explanation": "Vector Autoregression - a statistical method that predicts how multiple factors influence each other over time",
    "whyItMatters": "We can forecast how MRT development, CBD changes, and prices affect each other"
  }
}
```

**B. Visual Callout Boxes**

Astro component: `<StatCallout>`

```astro
<StatCallout
  value="22.6%"
  label="of price variation explained by CBD distance alone"
  trend="high"
  context="That's more than floor area, lease remaining, or unit type"
/>
```

**C. Enhanced Tables**

- Keep existing chart rendering (InlineChartRenderer) - already great
- Add highlight rows for most important findings
- Plain English column headers
- Summary rows at top

---

### 4. Actionability Components

**A. "What This Means For You" Callout Boxes**

Astro component: `<ImplicationBox persona="investor">`

```markdown
<ImplicationBox persona="investor">
**For Investors:** MRT proximity drives condo prices much more strongly.
- ✅ **Opportunity**: Condos near future MRT lines may see larger price jumps
- ⚠️ **Risk**: Condos far from MRT stations may lag in appreciation
- **Action**: When evaluating condos, prioritize MRT access more than for HDBs
</ImplicationBox>
```

**B. Scenario Examples**

Astro component: `<Scenario>`

```markdown
<Scenario title="Condo near Future MRT Line">
**Situation:** You're considering a $1.2M condo 500m from a future MRT station opening in 2028

**Our Analysis Says:**
- Condos see 2.3% price increase per 100m closer to MRT
- Future MRT lines typically boost nearby prices by 5-10% once operational

**Your Decision Framework:**
1. Check if the 5-10% premium is already priced in
2. If not fully priced in and you can hold until 2028+, this may be a good investment
3. Verify the station isn't already factored into current valuation
</Scenario>
```

**C. Decision Checklist Component**

Astro component: `<DecisionChecklist>`

```markdown
<DecisionChecklist title="Evaluating MRT Proximity Premium">
- [ ] What type of property? (Condo = MRT matters more; HDB = less important)
- [ ] How far to nearest MRT? (Under 500m = premium; 500m-1km = moderate; >1km = minimal)
- [ ] Is CBD distance the REAL driver?
- [ ] Is MRT premium already priced in?
- [ ] Future MRT lines planned?
</DecisionChecklist>
```

---

## Technical Implementation

### Astro Components to Create

1. **`src/components/analytics/Tooltip.astro`**
   - Props: `term`, `definition`, `whyItMatters`
   - Fetches from `analytics-glossary.json` if only `term` provided
   - CSS: Hover/tap to show tooltip bubble

2. **`src/components/analytics/StatCallout.astro`**
   - Props: `value`, `label`, `trend`, `context`
   - Renders: Card with large number, colored trend indicator

3. **`src/components/analytics/ImplicationBox.astro`**
   - Props: `persona`, `html` (or `children`)
   - Color-coded card by persona (investor=blue, first-time=green, upgrader=orange)

4. **`src/components/analytics/Scenario.astro`**
   - Props: `title`, `html` (or `children`)
   - Box with scenario header, bulleted analysis, decision framework

5. **`src/components/analytics/DecisionChecklist.astro`**
   - Props: `title`, `items`
   - Interactive checklist with checkboxes (local storage to save state)

6. **`src/pages/analytics/personas/[persona].astro`**
   - Dynamic route for each persona
   - Curates relevant docs and insights

### Data Files

1. **`src/data/analytics-glossary.json`** - All technical term definitions
2. **`src/data/persona-content.json`** - Persona-specific content and doc curation

### CSS Updates

- Tooltip styles (positioning, z-index, mobile-friendly tap behavior)
- Stat callout card styles (consistent with existing design system)
- Implication box persona color themes
- Scenario and checklist component styles
- Responsive design (tooltips on mobile = tap-to-show)

### Markdown Content Updates

- Update frontmatter to include new badges
- Add Key Takeaways section at top
- Insert component syntax throughout document
- Keep original content intact - enhancing, not replacing

---

## Content Strategy for MRT Impact Analysis Pilot

**Specific additions to `analyze_mrt-impact-analysis.md`:**

1. Add "Key Takeaways" section at top with the CBD premium insight
2. Identify 15-20 technical terms for tooltips (VAR, DiD, RDiT, H3, coefficient, p-value, etc.)
3. Add 5-7 StatCallout boxes for key numbers (15x difference, 22.6% CBD explanation, $1.28-$59 per 100m)
4. Add 3 ImplicationBoxes after major findings (investor, first-time buyer, upgrader perspectives)
5. Add 2 Scenario examples (condo buyer, HDB buyer evaluating MRT proximity)
6. Add 1 DecisionChecklist for evaluating MRT premium
7. Create "By The Numbers" summary box with 5 key statistics
8. Add "Who should read this" badge: All personas

**Estimated content additions:** ~2,150 words (mostly components, not narrative)

---

## Success Criteria

### Accessibility Improvements

- ✅ Technical terms explained via tooltips (20+ terms in pilot doc)
- ✅ Actionable guidance provided (3+ implication boxes, 2+ scenarios, 1+ checklist)
- ✅ Visual hierarchy established (key takeaways, stat callouts, highlighted sections)
- ✅ User can find relevant content via persona pages (3 personas launched)

### Quality Metrics

- Reading level reduced from post-graduate to college-educated (Flesch-Kincaid)
- Time to key insight reduced (scannable top section)
- Zero statistics without plain English translation
- Each major finding has "what to do about it" guidance

### User Experience

- Mobile-friendly tooltips (tap-to-show)
- Persona pages load fast (<1s)
- All components responsive on mobile/tablet/desktop
- Accessibility: WCAG AA compliant (keyboard navigation, screen reader support)

### Template Completeness

- MRT Impact Analysis fully enhanced with all features
- Component library documented for reuse in other docs
- Glossary seeded with 20+ common terms from analytics docs
- Process documented for enhancing remaining 14 docs

---

## Future Considerations

### Phase 2 (After Pilot)

- Apply template to remaining 14 analytics documents
- Expand glossary to cover all jargon across all docs
- A/B test different presentations (measure engagement)
- Add "Not sure? Take our 2-minute quiz" for persona detection
- Create PDF export of enhanced docs

### Phase 3 (Advanced)

- Interactive calculators ("MRT Premium Calculator", "Price Prediction Tool")
- Dynamic content personalization based on user profile
- Community features (user comments, questions, success stories)
- Video explanations of complex concepts
- Integration with property listings

### Avoid in Phase 1

- Don't build interactive calculators yet (enhance content first)
- Don't add user accounts/personalization (keep it static)
- Don't create duplicate content (enhance existing, don't rewrite)
- Don't add premium/paywalled content (keep all insights free)
- Don't over-engineer the tooltip system (keep it simple)

---

## Implementation Order

1. Create Astro components (Tooltip, StatCallout, ImplicationBox, Scenario, DecisionChecklist)
2. Create data files (analytics-glossary.json with 20+ terms, persona-content.json)
3. Add CSS styles for all new components
4. Create persona landing pages
5. Enhance MRT Impact Analysis document with all components
6. Test on mobile/tablet/desktop
7. Validate accessibility (WCAG AA)
8. Document process for remaining docs
9. Commit and deploy pilot

---

## Stakeholder Approval

**Approved by:** Project stakeholder
**Date:** 2026-02-17
**Changes requested:** None - approved as presented
