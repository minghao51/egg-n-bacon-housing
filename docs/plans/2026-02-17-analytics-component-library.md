# Analytics Accessibility Component Library

**Date:** 2026-02-18
**Status:** Complete
**Components:** 5 Astro components + 2 data files

---

## Overview

This component library transforms technical analytics documentation into accessible, actionable guides for non-technical users. All components use Tailwind CSS with existing design system variables.

---

## Components

### 1. Tooltip Component

**Purpose:** Explain technical jargon without interrupting reading flow

**File:** `app/src/components/analytics/Tooltip.astro`

**Usage:**
```md
<Tooltip term="H3 hexagons">H3 hexagons</Tooltip>
```

**Features:**
- Looks up terms in `analytics-glossary.json`
- Hover on desktop, tap on mobile
- Shows explanation + "why it matters"
- Accessible with ARIA tooltip role

**Glossary format:**
```json
{
  "TERM": {
    "explanation": "Plain English definition",
    "whyItMatters": "Why user should care"
  }
}
```

---

### 2. StatCallout Component

**Purpose:** Highlight key statistics with visual prominence

**File:** `app/src/components/analytics/StatCallout.astro`

**Usage:**
```md
<StatCallout
  value="22.6%"
  label="of price variation explained by CBD distance"
  trend="high"
  context="More than floor area, lease, or unit type"
/>
```

**Props:**
- `value` (required): The statistic to display
- `label` (required): Description of what it means
- `trend` (optional): "high" | "medium" | "low" | "neutral"
- `context` (optional): Additional interpretation

**Features:**
- Large prominent value (4xl font)
- Color-coded by trend (green/yellow/red)
- Hover animation
- Contextual information

---

### 3. ImplicationBox Component

**Purpose:** Show what findings mean for different user personas

**File:** `app/src/components/analytics/ImplicationBox.astro`

**Usage:**
```md
<ImplicationBox persona="investor">
**For Investors:** MRT proximity drives condo prices 15x more than HDBs.
- ✅ **Opportunity**: Condos near future MRT lines may see larger price jumps
- ⚠️ **Risk**: Don't overpay for already-priced premiums
- **Action**: Prioritize MRT access for condos, not HDBs
</ImplicationBox>
```

**Props:**
- `persona` (required): "first-time-buyer" | "investor" | "upgrader"
- `title` (optional): Custom header (defaults to "For {Persona}")

**Features:**
- Color-coded by persona (green/blue/orange)
- Renders markdown content
- Pulls colors from `persona-content.json`

---

### 4. Scenario Component

**Purpose:** Real-world examples showing how to apply insights

**File:** `app/src/components/analytics/Scenario.astro`

**Usage:**
```md
<Scenario title="Evaluating a Condo Near Future MRT Line">
**Situation:** You're considering a $1.2M condo 500m from a future MRT station.

**Our Analysis Says:**
- Condos show 15x higher MRT sensitivity than HDBs
- Future MRT lines typically boost prices by 5-10%

**Your Decision Framework:**
1. Check if premium is already priced in
2. Verify holding timeline
3. Assess CBD distance

**Bottom Line:** If premium isn't priced in AND you can hold until 2028+, good investment.
</Scenario>
```

**Features:**
- Prominent border and styling
- Markdown content support
- Visual hierarchy (Situation → Analysis → Framework → Bottom Line)

---

### 5. DecisionChecklist Component

**Purpose:** Interactive evaluation framework for property decisions

**File:** `app/src/components/analytics/DecisionChecklist.astro`

**Usage:**
```md
<DecisionChecklist
  title="Evaluating MRT Proximity Premium"
  storageKey="mrt-premium-checklist"
>

- [ ] Property type? (Condo = MRT matters 15x more)
- [ ] Distance to nearest MRT?
- [ ] Is CBD distance the real driver?
- [ ] Is premium already priced in?

</DecisionChecklist>
```

**Props:**
- `title` (required): Checklist name
- `storageKey` (optional): Unique localStorage key (auto-generated if omitted)

**Features:**
- Interactive checkboxes
- Persisted to localStorage
- Reset button
- Accessible form controls

---

## Data Files

### analytics-glossary.json

**Location:** `app/src/data/analytics-glossary.json`

**Contains:** 22 technical terms with explanations

**Current terms:** H3 hexagons, VAR model, OLS Regression, XGBoost, R², coefficient, p-value, DiD, RDiT, standard error, 95% confidence interval, spatial autocorrelation, cross-validation, feature importance, YoY, PSF, amenity agglomeration, lease decay, appreciation rate, heterogeneous effects, CBD

**Adding new terms:**
```json
{
  "NEW TERM": {
    "explanation": "Plain English definition",
    "whyItMatters": "Why it matters context"
  }
}
```

---

### persona-content.json

**Location:** `app/src/data/persona-content.json`

**Contains:** 3 personas with metadata

**Current personas:**
- **first-time-buyer** (green): Affordability, lease decay, location
- **investor** (blue): Price appreciation, rental yields, market timing
- **upgrader** (orange): Maximizing sale price, finding upgrade value

**Persona structure:**
```json
{
  "persona-key": {
    "title": "Display Name",
    "icon": "emoji",
    "description": "Brief description",
    "keyConcerns": ["concern1", "concern2"],
    "recommendedDocs": [
      {
        "slug": "doc-slug",
        "reason": "Why this doc matters"
      }
    ],
    "color": {
      "bg": "bg-colorname-50 dark:bg-colorname-950",
      "border": "border-colorname-200 dark:border-colorname-800",
      "text": "text-colorname-700 dark:text-colorname-300",
      "accent": "text-colorname-600 dark:text-colorname-400"
    }
  }
}
```

---

## Content Enhancement Process

### Step 1: Update Frontmatter

```yaml
---
title: Document Title
# ... existing fields ...
personas:
  - first-time-buyer
  - investor
readingTime: "8 min read"
technicalLevel: intermediate
---
```

### Step 2: Add Imports

```markdown
---

import Tooltip from '@/components/analytics/Tooltip.astro';
import StatCallout from '@/components/analytics/StatCallout.astro';
import ImplicationBox from '@/components/analytics/ImplicationBox.astro';
import Scenario from '@/components/analytics/Scenario.astro';
import DecisionChecklist from '@/components/analytics/DecisionChecklist.astro';
```

### Step 3: Add Key Takeaways Section

```markdown
## 📋 Key Takeaways

### 💡 The One Big Insight
One-sentence revolutionary finding

### 🎯 What This Means For You
3 bullet points translating findings

### ✅ Action Steps
3-5 concrete actions

### 📊 By The Numbers
3-5 <StatCallout> components
```

### Step 4: Wrap Technical Terms

```markdown
Before: "Using H3 hexagons for spatial analysis..."
After: "Using <Tooltip term='H3 hexagons'>H3 hexagons</Tooltip> for spatial analysis..."
```

### Step 5: Add Implication Boxes

After major findings, add persona-specific implications.

### Step 6: Add Scenario Examples

Use for real-world application of insights.

### Step 7: Add Decision Checklist

At the end of the document for interactive evaluation.

### Step 8: Sync to Reference Directory

```bash
cp app/src/content/analytics/doc-name.md docs/analytics/doc-name.md
```

---

## Testing Checklist

- [ ] All tooltips render with hover/tap
- [ ] StatCallouts display with correct colors
- [ ] ImplicationBoxes show persona-specific colors
- [ ] Scenarios have proper formatting
- [ ] DecisionChecklist saves to localStorage
- [ ] Persona pages load and show curated docs
- [ ] Mobile responsive (test on viewport < 768px)
- [ ] Dark mode works (all colors have dark variants)
- [ ] Accessibility: keyboard navigation works
- [ ] Accessibility: screen reader announces tooltips

---

## Known Limitations

1. **Tooltip positioning** - Basic implementation may overflow viewport edges
2. **Mobile tap behavior** - Requires clicking outside to close tooltips
3. **Glossary sync** - Must manually add terms when using new jargon
4. **Persona curation** - Currently manual; could be automated via frontmatter

---

## Future Enhancements

**Phase 2:**
- Apply template to remaining 14 analytics docs
- Expand glossary to 50+ terms
- A/B test component effectiveness
- Add PDF export with styles

**Phase 3:**
- Interactive calculators (MRT Premium Calculator)
- Dynamic persona detection via quiz
- Video explainers for complex concepts
- Property listing integration

---

## Troubleshooting

**Tooltip not showing:**
- Check term exists in `analytics-glossary.json`
- Verify component import at top of document
- Check browser console for JavaScript errors

**StatCallout not rendering:**
- Verify all required props (value, label) are provided
- Check trend value is valid: "high" | "medium" | "low" | "neutral"

**DecisionChecklist not persisting:**
- Check localStorage is enabled in browser
- Verify storageKey is unique per checklist
- Check browser console for quota exceeded errors

**Persona page showing no docs:**
- Verify docs have `personas` field in frontmatter
- Check slug matches in `persona-content.json`
- Ensure doc status is "published"

---

## Component Development Guidelines

**When adding new components:**

1. Follow Tailwind patterns from existing components
2. Use CSS custom properties (--foreground, --muted, etc.)
3. Support dark mode (all colors need dark: variants)
4. Make responsive (mobile-first approach)
5. Ensure accessibility (ARIA roles, keyboard nav)
6. Document in this file

**Component checklist:**
- [ ] Astro component in `app/src/components/analytics/`
- [ ] TypeScript props interface
- [ ] Tailwind styling with CSS variables
- [ ] Dark mode support
- [ ] Mobile responsive
- [ ] Accessible (ARIA, keyboard)
- [ ] Documented in this library file
- [ ] Tested on desktop and mobile
- [ ] Committed to git

---

## Maintenance

**Regular tasks:**
- Add new technical terms to glossary as they appear
- Update persona recommendations as new docs are added
- Test all components after Astro version upgrades
- Check localStorage quota limits for checklists
- Verify mobile responsiveness quarterly

**When new analytics docs are added:**
1. Add to appropriate persona's `recommendedDocs` in `persona-content.json`
2. Set `personas` frontmatter field
3. Apply enhancement template (this document)
4. Sync to reference directory
5. Test on all device types
