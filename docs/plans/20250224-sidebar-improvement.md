# Sidebar Improvement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve the dashboard sidebar with better visual separation, active page highlighting, and clearer section hierarchy.

**Architecture:** Refactor Sidebar.astro component to accept currentPath prop, implement active state detection logic, add visual dividers between sections with accent bars, and update all page components to pass current path.

**Tech Stack:** Astro (React-like components), TypeScript, Tailwind CSS

---

## Task 1: Update Sidebar Component with New Structure

**Files:**
- Modify: `app/src/components/Sidebar.astro`

**Step 1: Add currentPath prop to Sidebar component**

Add to frontmatter:
```typescript
interface Props {
  currentPath?: string;
}

const { currentPath = '' } = Astro.props;
```

**Step 2: Create isActive helper function**

Add after imports:
```typescript
function isActive(path: string, href: string): boolean {
  if (!path) return false;
  // Exact match for dashboard pages
  if (href.includes('/dashboard/')) {
    const normalizedPath = path.replace(/\/$/, '') || '/dashboard';
    const normalizedHref = href.replace(/\/$/, '') || '/dashboard';
    return normalizedPath === normalizedHref;
  }
  // Prefix match for analytics
  return path.startsWith(href);
}
```

**Step 3: Update Dashboard section with new styling**

Replace Dashboard section with:
```astro
<!-- Dashboard Section -->
<div>
  <div class="px-3 mb-3 mt-6 flex items-center gap-2">
    <div class="h-4 w-0.5 bg-primary rounded-full"></div>
    <span class="text-xs font-bold text-foreground uppercase tracking-wider">
      Dashboard
    </span>
  </div>
  <div class="border-t border-border my-3"></div>

  <ul class="space-y-1">
    <li>
      <a
        href={`${import.meta.env.BASE_URL}dashboard`}
        class:list={[
          "block px-3 py-2 rounded-md text-sm font-medium transition-colors",
          isActive(currentPath, `${import.meta.env.BASE_URL}dashboard`)
            ? "text-foreground bg-accent/50 border-l-2 border-primary"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        ]}
      >
        Market Overview
      </a>
    </li>
    <li>
      <a
        href={`${import.meta.env.BASE_URL}dashboard/map`}
        class:list={[
          "block px-3 py-2 rounded-md text-sm font-medium transition-colors",
          isActive(currentPath, `${import.meta.env.BASE_URL}dashboard/map`)
            ? "text-foreground bg-accent/50 border-l-2 border-primary"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        ]}
      >
        Interactive Map
      </a>
    </li>
    <li>
      <a
        href={`${import.meta.env.BASE_URL}dashboard/trends`}
        class:list={[
          "block px-3 py-2 rounded-md text-sm font-medium transition-colors",
          isActive(currentPath, `${import.meta.env.BASE_URL}dashboard/trends`)
            ? "text-foreground bg-accent/50 border-l-2 border-primary"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        ]}
      >
        Analysis Tools
      </a>
    </li>
    <li>
      <a
        href={`${import.meta.env.BASE_URL}dashboard/segments`}
        class:list={[
          "block px-3 py-2 rounded-md text-sm font-medium transition-colors",
          isActive(currentPath, `${import.meta.env.BASE_URL}dashboard/segments`)
            ? "text-foreground bg-accent/50 border-l-2 border-primary"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        ]}
      >
        Market Segments
      </a>
    </li>
    <li>
      <a
        href={`${import.meta.env.BASE_URL}dashboard/leaderboard`}
        class:list={[
          "block px-3 py-2 rounded-md text-sm font-medium transition-colors",
          isActive(currentPath, `${import.meta.env.BASE_URL}dashboard/leaderboard`)
            ? "text-foreground bg-accent/50 border-l-2 border-primary"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        ]}
      >
        Area Rankings
      </a>
    </li>
  </ul>
</div>
```

**Step 4: Update Personas section as standalone**

Replace Personas subsection with:
```astro
<!-- Personas Section -->
<div class="mt-6">
  <div class="px-3 mb-3 flex items-center gap-2">
    <div class="h-4 w-0.5 bg-primary rounded-full"></div>
    <span class="text-xs font-bold text-foreground uppercase tracking-wider">
      Personas
    </span>
  </div>
  <div class="border-t border-border my-3"></div>

  <ul class="space-y-1">
    <li>
      <a
        href={`${import.meta.env.BASE_URL}analytics/personas/first-time-buyer`}
        class:list={[
          "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors",
          isActive(currentPath, `${import.meta.env.BASE_URL}analytics/personas/first-time-buyer`)
            ? "text-foreground bg-accent/50 border-l-2 border-primary"
            : "text-muted-foreground hover:text-foreground hover:bg-accent"
        ]}
      >
        <span>🏠</span>
        <span>First-Time Buyer</span>
      </a>
    </li>
    <li>
      <a
        href={`${import.meta.env.BASE_URL}analytics/personas/investor`}
        class:list={[
          "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors",
          isActive(currentPath, `${import.meta.env.BASE_URL}analytics/personas/investor`)
            ? "text-foreground bg-accent/50 border-l-2 border-primary"
            : "text-muted-foreground hover:text-foreground hover:bg-accent"
        ]}
      >
        <span>💼</span>
        <span>Investor</span>
      </a>
    </li>
    <li>
      <a
        href={`${import.meta.env.BASE_URL}analytics/personas/upgrader`}
        class:list={[
          "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors",
          isActive(currentPath, `${import.meta.env.BASE_URL}analytics/personas/upgrader`)
            ? "text-foreground bg-accent/50 border-l-2 border-primary"
            : "text-muted-foreground hover:text-foreground hover:bg-accent"
        ]}
      >
        <span>⬆️</span>
        <span>Upgrader</span>
      </a>
    </li>
  </ul>
</div>
```

**Step 5: Update Analytics section with new styling**

Replace Analytics section with:
```astro
<!-- Analytics Section -->
<div class="mt-6">
  <div class="px-3 mb-3 flex items-center gap-2">
    <div class="h-4 w-0.5 bg-primary rounded-full"></div>
    <span class="text-xs font-bold text-foreground uppercase tracking-wider">
      Analytics
    </span>
  </div>
  <div class="border-t border-border my-3"></div>

  <ul class="space-y-1">
    <!-- Analytics Index -->
    <li>
      <a
        href={`${import.meta.env.BASE_URL}analytics/`}
        class:list={[
          "block px-3 py-2 rounded-md text-sm font-medium transition-colors",
          currentPath === `${import.meta.env.BASE_URL}analytics/` || currentPath === `${import.meta.env.BASE_URL}analytics`
            ? "text-foreground bg-accent/50 border-l-2 border-primary"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        ]}
      >
        Analytics Index
      </a>
    </li>

    <!-- Dynamic Analytics Docs -->
    {analyticsDocs.map((doc) => (
      <li>
        <a
          href={`${import.meta.env.BASE_URL}analytics/${doc.slug}`}
          class:list={[
            "block px-3 py-2 rounded-md text-sm font-medium transition-colors",
            isActive(currentPath, `${import.meta.env.BASE_URL}analytics/${doc.slug}`)
              ? "text-foreground bg-accent/50 border-l-2 border-primary"
              : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          ]}
        >
          {doc.title}
        </a>
      </li>
    ))}
  </ul>
</div>
```

**Step 6: Commit changes**

```bash
git add app/src/components/Sidebar.astro
git commit -m "feat(sidebar): add active state highlighting and visual separation

- Add currentPath prop for active state detection
- Implement isActive helper function for path matching
- Add accent bars and dividers between sections
- Promote Personas to standalone section
- Apply active styling with left border accent
- Improve section headers with bold weight"
```

---

## Task 2: Update Dashboard Pages

**Files:**
- Modify: `app/src/pages/dashboard/index.astro`
- Modify: `app/src/pages/dashboard/map.astro`
- Modify: `app/src/pages/dashboard/trends.astro`
- Modify: `app/src/pages/dashboard/segments.astro`
- Modify: `app/src/pages/dashboard/leaderboard.astro`

**Step 1: Update index.astro**

Find line with `<Sidebar />` and replace with:
```astro
<Sidebar currentPath={Astro.url.pathname} />
```

**Step 2: Update map.astro**

Find line with `<Sidebar />` and replace with:
```astro
<Sidebar currentPath={Astro.url.pathname} />
```

**Step 3: Update trends.astro**

Find line with `<Sidebar />` and replace with:
```astro
<Sidebar currentPath={Astro.url.pathname} />
```

**Step 4: Update segments.astro**

Find line with `<Sidebar />` and replace with:
```astro
<Sidebar currentPath={Astro.url.pathname} />
```

**Step 5: Update leaderboard.astro**

Find line with `<Sidebar />` and replace with:
```astro
<Sidebar currentPath={Astro.url.pathname} />
```

**Step 6: Commit changes**

```bash
git add app/src/pages/dashboard/
git commit -m "feat(sidebar): pass currentPath to Sidebar in dashboard pages

Update all dashboard pages to pass current pathname to Sidebar component for active state highlighting"
```

---

## Task 3: Update Analytics Pages

**Files:**
- Modify: `app/src/pages/analytics/index.astro`
- Modify: `app/src/pages/analytics/[slug].astro`
- Modify: `app/src/pages/analytics/personas/[persona].astro`

**Step 1: Update analytics index.astro**

Read file first to locate Sidebar usage, then update:
```astro
<Sidebar currentPath={Astro.url.pathname} />
```

**Step 2: Update analytics [slug].astro**

Read file first to locate Sidebar usage, then update:
```astro
<Sidebar currentPath={Astro.url.pathname} />
```

**Step 3: Update analytics personas [persona].astro**

Read file first to locate Sidebar usage (around line 32), then update:
```astro
<Sidebar currentPath={Astro.url.pathname} />
```

**Step 4: Commit changes**

```bash
git add app/src/pages/analytics/
git commit -m "feat(sidebar): pass currentPath to Sidebar in analytics pages

Update all analytics pages including persona pages to pass current pathname to Sidebar component"
```

---

## Task 4: Build and Test

**Files:**
- No file modifications

**Step 1: Build the application**

Run from app directory:
```bash
cd app
npm run build
```
Expected: Build completes successfully

**Step 2: Start dev server**

Run:
```bash
npm run dev
```
Expected: Dev server starts on default port

**Step 3: Manual testing checklist**

Navigate to each page and verify:

Dashboard pages:
- [ ] `/dashboard` - "Market Overview" link is active (left border, darker bg)
- [ ] `/dashboard/map` - "Interactive Map" link is active
- [ ] `/dashboard/trends` - "Analysis Tools" link is active
- [ ] `/dashboard/segments` - "Market Segments" link is active
- [ ] `/dashboard/leaderboard` - "Area Rankings" link is active

Analytics pages:
- [ ] `/analytics/` - "Analytics Index" link is active
- [ ] `/analytics/lease-decay` - "Lease Decay" doc link is active
- [ ] `/analytics/mrt-impact` - "MRT Impact" doc link is active

Persona pages:
- [ ] `/analytics/personas/first-time-buyer` - "First-Time Buyer" link is active
- [ ] `/analytics/personas/investor` - "Investor" link is active
- [ ] `/analytics/personas/upgrader` - "Upgrader" link is active

Visual checks:
- [ ] Section headers have colored accent bar on left
- [ ] Horizontal dividers separate sections
- [ ] Sections have proper vertical spacing (mt-6)
- [ ] Active links have 2px left border in primary color
- [ ] Active links have darker background (bg-accent/50)
- [ ] Active links have brighter text (text-foreground)
- [ ] Non-active links are muted (text-muted-foreground)
- [ ] Hover states work correctly

**Step 4: Test responsive behavior**

Check mobile view:
- [ ] Sidebar hidden on mobile
- [ ] Layout works without sidebar on small screens

Check desktop view:
- [ ] Sidebar visible on lg breakpoint
- [ ] Main content has proper left margin (ml-64)

**Step 5: Final commit if adjustments needed**

If any styling adjustments were made during testing:
```bash
git add app/src/components/Sidebar.astro
git commit -m "style(sidebar): fine-tune active state styling based on testing"
```

---

## Task 5: Update Documentation

**Files:**
- Modify: `docs/plans/20250224-sidebar-improvement-design.md`

**Step 1: Mark design as implemented**

Add to top of design document:
```markdown
**Status:** ✅ Implemented
```

**Step 2: Add implementation notes**

Add section at end:
```markdown
## Implementation Notes

- Implemented 2025-02-24
- Active state uses Astro's class:list directive for conditional styling
- Path matching handles both exact matches (dashboard) and prefix matches (analytics)
- All pages updated to pass Astro.url.pathname to Sidebar
```

**Step 3: Commit documentation update**

```bash
git add docs/plans/20250224-sidebar-improvement-design.md
git commit -m "docs: mark sidebar improvement as implemented"
```

---

## Verification Checklist

After implementation, verify:

- [ ] All dashboard pages show correct active state
- [ ] All analytics doc pages show correct active state
- [ ] All persona pages show correct active state
- [ ] Section headers have accent bars
- [ ] Horizontal dividers separate sections cleanly
- [ ] Personas section is standalone (not nested under Analytics)
- [ ] Visual hierarchy is clear (Dashboard → Personas → Analytics)
- [ ] Build completes without errors
- [ ] No console errors in browser
- [ ] Responsive behavior maintained

---

## Related Files

Reference these files during implementation:
- Design doc: `docs/plans/20250224-sidebar-improvement-design.md`
- Component: `app/src/components/Sidebar.astro`
- Layout: `app/src/layouts/Layout.astro`
- Example page: `app/src/pages/dashboard/map.astro`

## Rollback Plan

If issues arise, revert commits:
```bash
git revert HEAD~3..HEAD
```

This will remove:
1. Documentation update
2. Analytics page updates
3. Dashboard page updates
4. Sidebar component changes
