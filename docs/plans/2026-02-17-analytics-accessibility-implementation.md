# Analytics Documentation Accessibility Improvements - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform technical analytics documentation into accessible, actionable guides for non-technical users through persona-based navigation, inline tooltips, visual callouts, and actionable guidance components.

**Architecture:** Astro 5 static site with MDX content collections, React components for interactivity, Tailwind CSS with shadcn/ui design system. Components will be pure Astro/React with local state (no backend). Data stored in JSON files alongside components.

**Tech Stack:** Astro 5, React 19, MDX, Tailwind CSS, TypeScript, existing shadcn/ui design tokens

---

## Task 1: Create Analytics Components Directory Structure

**Files:**
- Create: `app/src/components/analytics/` directory

**Step 1: Create the analytics components directory**

```bash
mkdir -p app/src/components/analytics
```

**Step 2: Verify directory creation**

Run: `ls -la app/src/components/analytics/`
Expected: Directory exists, empty

**Step 3: Commit**

```bash
git add app/src/components/analytics
git commit -m "feat(analytics): create analytics components directory"
```

---

## Task 2: Create Tooltip Component

**Files:**
- Create: `app/src/components/analytics/Tooltip.astro`
- Create: `app/src/data/analytics-glossary.json`

**Step 1: Write the Tooltip component**

Create `app/src/components/analytics/Tooltip.astro`:

```astro
---
/**
 * Tooltip component for explaining technical terms in analytics docs
 *
 * Usage:
 *   <Tooltip term="H3 hexagons">H3 hexagons</Tooltip>
 *   <Tooltip term="VAR model" definition="Custom definition" whyItMatters="Custom note">VAR model</Tooltip>
 */

interface Props {
  term: string;
  definition?: string;
  whyItMatters?: string;
}

const { term, definition, whyItMatters } = Astro.props;

// Load glossary
let glossaryEntry: Record<string, { explanation: string; whyItMatters: string }> = {};
try {
  const glossaryModule = await import('@/data/analytics-glossary.json');
  glossaryEntry = glossaryModule.default;
} catch (e) {
  console.warn('Could not load analytics-glossary.json:', e);
}

const termDefinition = definition || glossaryEntry[term]?.explanation || `Definition for ${term}`;
const termWhyItMatters = whyItMatters || glossaryEntry[term]?.whyItMatters || '';
---

<span
  class="tooltip-trigger"
  data-term={term}
  aria-label={`Show definition for ${term}`}
  role="button"
  tabindex="0"
>
  <slot />
  <span class="tooltip-content">
    <strong>{term}</strong>
    <p class="tooltip-explanation">{termDefinition}</p>
    {termWhyItMatters && (
      <p class="tooltip-why-it-matters">
        <em>Why it matters:</em> {termWhyItMatters}
      </p>
    )}
  </span>
</span>

<style>
  .tooltip-trigger {
    position: relative;
    display: inline-block;
    border-bottom: 1px dotted hsl(var(--primary));
    cursor: help;
  }

  .tooltip-content {
    visibility: hidden;
    opacity: 0;
    position: absolute;
    bottom: 125%;
    left: 50%;
    transform: translateX(-50%);
    width: 300px;
    max-width: 90vw;
    background-color: hsl(var(--popover));
    color: hsl(var(--popover-foreground));
    border: 1px solid hsl(var(--border));
    border-radius: var(--radius);
    padding: 0.75rem;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    z-index: 50;
    transition: visibility 0.2s, opacity 0.2s;
    pointer-events: none;
  }

  .tooltip-trigger:hover .tooltip-content,
  .tooltip-trigger:focus .tooltip-content {
    visibility: visible;
    opacity: 1;
  }

  .tooltip-content strong {
    display: block;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    color: hsl(var(--foreground));
  }

  .tooltip-explanation {
    margin: 0.5rem 0;
    font-size: 0.875rem;
    line-height: 1.5;
    color: hsl(var(--muted-foreground));
  }

  .tooltip-why-it-matters {
    margin: 0.5rem 0 0 0;
    padding: 0.5rem;
    background-color: hsl(var(--accent));
    border-radius: calc(var(--radius) - 2px);
    font-size: 0.8125rem;
    line-height: 1.4;
  }

  /* Mobile: tap to show */
  @media (max-width: 768px) {
    .tooltip-trigger:focus .tooltip-content {
      visibility: visible;
      opacity: 1;
      pointer-events: auto;
    }
  }
</style>
```

**Step 2: Create initial glossary data**

Create `app/src/data/analytics-glossary.json` (with 20+ terms - see full content in next step)

**Step 3: Commit**

```bash
git add app/src/components/analytics/Tooltip.astro app/src/data/analytics-glossary.json
git commit -m "feat(analytics): add Tooltip component with glossary

- Hover/click tooltips for technical jargon
- 20+ terms in initial glossary
- Mobile-friendly tap-to-show behavior
- Accessible with ARIA labels and keyboard navigation
"
```

---

## Task 3-16: (Continued in next part due to length)

[Note: Due to length limits, the full implementation plan continues with:]
- Task 3: StatCallout component
- Task 4: ImplicationBox component
- Task 5: Scenario component
- Task 6: DecisionChecklist component
- Task 7: Persona data file
- Task 8: Persona landing pages
- Task 9: Content collection schema update
- Task 10: KeyTakeaways component
- Task 11: Enhance MRT Impact Analysis document
- Task 12: Update analytics slug page
- Task 13: Test enhanced document
- Task 14: Create component documentation
- Task 15: Update CLAUDE.md
- Task 16: Final testing and validation
- Task 17: Create summary document

**Total estimated implementation time:** 4-6 hours for all 17 tasks

**For full implementation plan details, see the design document at:**
`docs/plans/2026-02-17-analytics-accessibility-design.md`
