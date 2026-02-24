# Sidebar Improvement Design

**Date:** 2025-02-24
**Status:** ✅ Implemented
**Author:** Claude

## Overview

Improve the dashboard sidebar with better visual hierarchy, section separation, and active page highlighting to enhance navigation clarity and user experience.

## Current Issues

1. **No active page highlighting** - Users can't tell which page they're currently viewing
2. **Poor section separation** - Dashboard, Personas, and Analytics blend together
3. **Personas lack purpose** - Mixed into Analytics section without clear differentiation
4. **Flat hierarchy** - All links have same styling regardless of importance

## Design Decisions

### 1. Keep Personas as Standalone Section

**Decision:** Keep personas but elevate them to a top-level section with clearer purpose.

**Rationale:**
- Personas provide valuable context for different user types (first-time buyers, investors, upgraders)
- They serve as onboarding/educational content, not analytics
- Deserves own section to highlight their unique role

### 2. Visual Separation with Dividers

**Decision:** Use horizontal divider lines between major sections with prominent section headers.

**Rationale:**
- Clean, professional look matching dashboard aesthetic
- Clear visual boundaries without overwhelming card-style containers
- Scales well if more sections are added later

### 3. Active State: Bold Left Border

**Decision:** Active links have a 2px colored left border with darker background and brighter text.

**Rationale:**
- Modern, recognizable pattern for navigation
- Subtle but clear indication
- Works well with existing hover states (`hover:bg-accent`)
- Avoids heavy backgrounds that can feel overwhelming

## Implementation Specification

### Section Structure

```
Sidebar
├── Brand Header
├── Dark Mode Toggle
├── Dashboard Section
│   ├── Section Header (with accent bar)
│   ├── Divider
│   ├── Market Overview
│   ├── Interactive Map
│   ├── Analysis Tools
│   ├── Market Segments
│   └── Area Rankings
├── Personas Section
│   ├── Section Header (with accent bar)
│   ├── Divider
│   ├── First-Time Buyer (🏠)
│   ├── Investor (💼)
│   └── Upgrader (⬆️)
└── Analytics Section
    ├── Section Header (with accent bar)
    ├── Divider
    ├── Analytics Index
    └── [Dynamic .mdx docs]
        ├── Causal Inference Overview
        ├── Findings
        ├── Lease Decay
        ├── MRT Impact
        ├── Price Forecasts
        ├── School Quality
        ├── Spatial Autocorrelation
        └── Spatial Hotspots
```

### Component Props

```typescript
interface SidebarProps {
  currentPath: string;  // e.g., "/dashboard/map"
}
```

### Section Header Template

```html
<div class="px-3 mb-3 mt-6 flex items-center gap-2">
  <div class="h-4 w-0.5 bg-primary rounded-full"></div>
  <span class="text-xs font-bold text-foreground uppercase tracking-wider">
    Section Name
  </span>
</div>
<div class="border-t border-border my-3"></div>
```

### Link States

**Default:**
```html
<a class="block px-3 py-2 rounded-md text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors">
```

**Active:**
```html
<a class="block px-3 py-2 rounded-md text-sm font-medium text-foreground bg-accent/50 border-l-2 border-primary transition-colors">
```

### Active State Logic

```typescript
function isActive(currentPath: string, href: string): boolean {
  // Exact match for dashboard pages
  if (href.includes('/dashboard/')) {
    return currentPath === href;
  }
  // Prefix match for analytics (e.g., /analytics/lease-decay)
  return currentPath.startsWith(href);
}
```

### Styling Changes

**Section Headers:**
- Add vertical accent bar (`.h-4.w-0.5.bg-primary.rounded-full`)
- Increase font weight to `font-bold`
- Add margin top (`mt-6`)
- Add divider after header (`border-t.border-border.my-3`)

**Links:**
- Active: `bg-accent/50.border-l-2.border-primary.text-foreground`
- Remove `text-muted-foreground` from active state
- Keep hover states consistent

**Spacing:**
- `mt-6` before each major section
- `mb-3` after section header
- `my-3` for dividers

## Technical Implementation

### Files to Modify

1. **`app/src/components/Sidebar.astro`**
   - Add `currentPath` prop
   - Implement active state detection
   - Add section header styling with accent bars
   - Add dividers between sections
   - Reorganize into three clear sections

2. **All page components** (to pass `currentPath`):
   - `app/src/pages/dashboard/*.astro`
   - `app/src/pages/analytics/*.astro`
   - `app/src/pages/analytics/personas/[persona].astro`

### Migration Steps

1. Update Sidebar.astro with new structure and styling
2. Update all page files to pass `currentPath={Astro.url.pathname}` to Sidebar
3. Test active states on all page types (dashboard, analytics, personas)
4. Verify visual hierarchy and spacing

## Design Considerations

### Accessibility

- Active state uses both color and visual indicator (left border)
- Sufficient color contrast maintained
- Clear focus states for keyboard navigation

### Responsiveness

- Changes only affect sidebar (hidden on mobile, shown on `lg:` breakpoint)
- No mobile layout changes needed

### Extensibility

- Easy to add new sections following established pattern
- Section header component can be extracted if reused
- Active state logic handles both exact and prefix matching

## Success Criteria

- ✅ Active page clearly visible with left border accent
- ✅ Three sections visually separated with dividers
- ✅ Section headers prominent with accent bars
- ✅ Personas elevated to standalone section
- ✅ Consistent spacing throughout
- ✅ Works across all page types (dashboard, analytics, personas)

## Implementation Notes

- **Implemented:** 2025-02-24
- **Active state mechanism:** Uses Astro's `class:list` directive for conditional styling
- **Path matching logic:**
  - Exact match for dashboard pages (with trailing slash normalization)
  - Prefix match for analytics pages
  - BASE_URL-aware to work in production environments
- **Integration:** All pages updated to pass `Astro.url.pathname` to Sidebar component
- **Commits:**
  - d321447 + 1d0efdd + 085a279: Sidebar component implementation
  - f8f4e5d + de51015: Dashboard pages update
  - 4a4f211: Analytics pages update
  - dad1970: BASE_URL bug fix
- **Build:** Successful, no errors
