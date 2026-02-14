# Analytics Content Organization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reorganize the analytics section into 4 categories with collapsible sections and category-based navigation.

**Architecture:** Update sync script to validate categories, add category frontmatter to 11 markdown files, and modify the analytics index page to group and display documents by category using native HTML details/summary elements.

**Tech Stack:** Shell scripting (sync-content.sh), Astro/TSX (analytics index page), Markdown frontmatter

---

## Task 1: Update Sync Script with Category Validation

**Files:**
- Modify: `scripts/sync-content.sh:20-33`

**Step 1: Add validation function to sync script**

```bash
#!/bin/bash
# Sync markdown files from docs/ to app/src/content/analytics/
# Also creates symlinks for data/analysis so relative image paths work

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="$PROJECT_ROOT/docs/analytics"
APP_CONTENT_DIR="$PROJECT_ROOT/app/src/content/analytics"
DATA_ANALYSIS_DIR="$PROJECT_ROOT/data/analysis"
APP_SRC_DIR="$PROJECT_ROOT/app/src"

# Valid categories
declare -A VALID_CATEGORIES=(
  ["investment-guides"]="Investment Guides"
  ["market-analysis"]="Market Analysis"
  ["technical-reports"]="Technical Reports"
  ["quick-reference"]="Quick Reference"
)

# Function to extract category from frontmatter
extract_category() {
  local file="$1"
  grep -m1 '^category:' "$file" | sed 's/^category: *//' | tr -d '"'"'"
}

# Function to validate category
validate_category() {
  local file="$1"
  local category=$(extract_category "$file")

  if [[ -z "$category" ]]; then
    echo "⚠️  Missing category in: $(basename "$file")"
    echo "   Valid categories: ${!VALID_CATEGORIES[@]}"
    return 1
  fi

  if [[ ! -v VALID_CATEGORIES["$category"] ]]; then
    echo "⚠️  Invalid category '$category' in: $(basename "$file")"
    echo "   Valid categories: ${!VALID_CATEGORIES[@]}"
    return 1
  fi

  return 0
}
```

**Step 2: Add validation after copy operation**

```bash
echo "Syncing analytics markdown files..."

# Create app content directory if it doesn't exist
mkdir -p "$APP_CONTENT_DIR"

# Clean up old .md files first (ensures deleted files are removed)
rm -f "$APP_CONTENT_DIR"/*.md 2>/dev/null || true
echo "🧹 Cleaned up old markdown files from $APP_CONTENT_DIR/"

# Copy all .md files from docs/analytics to app content
cp -r "$DOCS_DIR"/*.md "$APP_CONTENT_DIR/" 2>/dev/null || true

# Validate categories in copied files
echo "🔍 Validating categories..."
invalid_count=0
for file in "$APP_CONTENT_DIR"/*.md; do
  if ! validate_category "$file"; then
    ((invalid_count++))
  fi
done

if [[ $invalid_count -gt 0 ]]; then
  echo "⚠️  Found $invalid_count file(s) with invalid/missing categories"
  echo "   Please fix category frontmatter in source files"
  exit 1
fi

echo "✅ All categories validated successfully"
```

**Step 3: Test validation with existing files**

Run: `bash scripts/sync-content.sh`
Expected: ⚠️  Missing category warnings (current files don't have categories yet)

**Step 4: Commit**

```bash
git add scripts/sync-content.sh
git commit -m "feat(sync): add category validation to sync script

Add validation for category frontmatter field in analytics markdown files.
Ensures all documents have one of 4 valid categories before syncing to app.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Update Frontmatter for Investment Guides Category

**Files:**
- Modify: `docs/analytics/findings.md:2-7`

**Step 1: Add category frontmatter to findings.md**

```markdown
---
title: "Singapore Housing Market - Key Investment Findings"
category: "investment-guides"
description: "Actionable insights for property buyers and investors from comprehensive market analysis (2021-2026)"
status: "published"
date: "2026-02-06"
---
```

**Step 2: Test sync script validates correctly**

Run: `bash scripts/sync-content.sh`
Expected: ✅ No validation errors for findings.md

**Step 3: Commit**

```bash
git add docs/analytics/findings.md
git commit -m "docs(analytics): add category to findings.md

Mark findings.md as 'investment-guides' category for proper grouping
in analytics index page.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Update Frontmatter for Market Analysis Files

**Files:**
- Modify: `docs/analytics/analyze_lease_decay.md:2-7`
- Modify: `docs/analytics/analyze_mrt-impact-analysis.md:2-7`
- Modify: `docs/analytics/analyze_school-quality-features.md:2-7`
- Modify: `docs/analytics/analyze_spatial_autocorrelation.md:2-7`

**Step 1: Add category to analyze_lease_decay.md**

```markdown
---
title: Lease Decay Analysis - Singapore Housing Market
category: "market-analysis"
description: Analysis of how remaining lease affects HDB prices and appreciation (2021+)
status: "published"
---
```

**Step 2: Add category to analyze_mrt-impact-analysis.md**

```markdown
---
title: MRT Impact Analysis - Singapore Housing Market
category: "market-analysis"
description: Comprehensive analysis of MRT proximity impact on HDB prices and appreciation (2021+)
status: "published"
---
```

**Step 3: Add category to analyze_school-quality-features.md**

```markdown
---
title: School Quality Features Analysis
category: "market-analysis"
description: Analysis of how school proximity and quality affect housing prices
status: "published"
---
```

**Step 4: Add category to analyze_spatial_autocorrelation.md**

```markdown
---
title: Spatial Autocorrelation Analysis
category: "market-analysis"
description: Analysis of neighborhood clustering and spatial patterns in housing appreciation
status: "published"
---
```

**Step 5: Test validation**

Run: `bash scripts/sync-content.sh`
Expected: ✅ All 4 market-analysis files validate

**Step 6: Commit**

```bash
git add docs/analytics/analyze_*.md
git commit -m "docs(analytics): add market-analysis category to analyze_ files

Update 4 analysis documents with 'market-analysis' category:
- analyze_lease_decay.md
- analyze_mrt-impact-analysis.md
- analyze_school-quality-features.md
- analyze_spatial_autocorrelation.md

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Update Frontmatter for Technical Reports Files

**Files:**
- Modify: `docs/analytics/causal-inference-overview.md:2-7`
- Modify: `docs/analytics/plan_analyze_h3_clusters.md:2-7`
- Modify: `docs/analytics/plan_analyze_policy_impact.md:2-7`
- Modify: `docs/analytics/plan_school-impact-analysis.md:2-7`
- Modify: `docs/analytics/plan_spatial-analytics-overview.md:2-7`
- Modify: `docs/analytics/zzz_analyze_spatial_hotspots.md:2-7`

**Step 1: Add category to causal-inference-overview.md**

```markdown
---
title: Causal Inference Overview
category: "technical-reports"
description: Statistical methodology for causal analysis in housing market
status: "published"
---
```

**Step 2: Add category to plan_analyze_h3_clusters.md**

```markdown
---
title: H3 Cluster Analysis Plan
category: "technical-reports"
description: Implementation plan for H3 hexagonal grid spatial analysis
status: "published"
---
```

**Step 3: Add category to plan_analyze_policy_impact.md**

```markdown
---
title: Policy Impact Analysis Plan
category: "technical-reports"
description: Plan for analyzing government policy effects on housing market
status: "published"
---
```

**Step 4: Add category to plan_school-impact-analysis.md**

```markdown
---
title: School Impact Analysis Plan
category: "technical-reports"
description: Implementation plan for school quality analysis
status: "published"
---
```

**Step 5: Add category to plan_spatial-analytics-overview.md**

```markdown
---
title: Spatial Analytics Overview
category: "technical-reports"
description: Technical overview of spatial analysis methods
status: "published"
---
```

**Step 6: Add category to zzz_analyze_spatial_hotspots.md**

```markdown
---
title: Spatial Hotspots Analysis
category: "technical-reports"
description: Detailed analysis of spatial hotspots
status: "published"
---
```

**Step 7: Test validation**

Run: `bash scripts/sync-content.sh`
Expected: ✅ All 6 technical-reports files validate

**Step 8: Commit**

```bash
git add docs/analytics/*.md
git commit -m "docs(analytics): add technical-reports category to plan/overview files

Update 6 technical documents with 'technical-reports' category:
- causal-inference-overview.md
- plan_analyze_h3_clusters.md
- plan_analyze_policy_impact.md
- plan_school-impact-analysis.md
- plan_spatial-analytics-overview.md
- zzz_analyze_spatial_hotspots.md

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Update Analytics Index Page with Category Grouping

**Files:**
- Modify: `app/src/pages/analytics/index.astro:5-93`

**Step 1: Add category configuration and grouping logic**

```astro
---
import Layout from '@/layouts/Layout.astro';
import Sidebar from '@/components/Sidebar.astro';
import { getCollection } from 'astro:content';

const allDocs = await getCollection('analytics');

// Category configuration
const categoryConfig = {
  'investment-guides': {
    label: 'Investment Guides',
    icon: '💼',
    description: 'Actionable insights for investors and buyers',
  },
  'market-analysis': {
    label: 'Market Analysis',
    icon: '📊',
    description: 'Trends and patterns in housing market',
  },
  'technical-reports': {
    label: 'Technical Reports',
    icon: '🔬',
    description: 'Methodology and statistical models',
  },
  'quick-reference': {
    label: 'Quick Reference',
    icon: '📋',
    description: 'Tables and condensed summaries',
  },
};

// Group documents by category
const docsByCategory = allDocs.reduce((acc, doc) => {
  const category = doc.data.category || 'technical-reports'; // Default fallback
  if (!acc[category]) {
    acc[category] = [];
  }
  acc[category].push({
    slug: doc.slug,
    title: doc.data.title || doc.slug,
    description: doc.data.description || '',
    category: doc.data.category,
  });
  return acc;
}, {} as Record<string, Array<{
  slug: string;
  title: string;
  description: string;
  category: string;
}>>);

// Sort categories by display order
const sortedCategories = Object.keys(categoryConfig).filter(
  cat => docsByCategory[cat]?.length > 0
);
---

<Layout title="Analytics - Singapore Housing Market">
  <Sidebar />

  <main class="flex-1 ml-64">
    <div class="max-w-4xl mx-auto px-8 py-12">
      <!-- Header -->
      <header class="mb-8">
        <h1 class="text-4xl font-bold text-foreground mb-2">
          Singapore Housing Market Analytics
        </h1>
        <p class="text-lg text-muted-foreground">
          Comprehensive analysis of HDB and Condo market trends, rental yields,
          spatial patterns, and policy impacts.
        </p>
      </header>

      <!-- Quick Stats -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
        <div class="bg-card border border-border rounded-lg p-6">
          <div class="text-sm font-medium text-muted-foreground mb-1">
            Total Reports
          </div>
          <div class="text-3xl font-bold text-foreground">{allDocs.length}</div>
        </div>
        <div class="bg-card border border-border rounded-lg p-6">
          <div class="text-sm font-medium text-muted-foreground mb-1">
            Data Coverage
          </div>
          <div class="text-3xl font-bold text-foreground">11 Years</div>
        </div>
        <div class="bg-card border border-border rounded-lg p-6">
          <div class="text-sm font-medium text-muted-foreground mb-1">
            Categories
          </div>
          <div class="text-3xl font-bold text-foreground">{sortedCategories.length}</div>
        </div>
      </div>

      <!-- Category Sections -->
      <div class="space-y-8">
        {sortedCategories.map((category) => (
          <section class="border border-border rounded-lg overflow-hidden">
            <details class="group" open>
              <summary class="flex items-center justify-between p-6 cursor-pointer hover:bg-accent transition-colors">
                <div class="flex items-center gap-3">
                  <span class="text-2xl">{categoryConfig[category].icon}</span>
                  <div>
                    <h2 class="text-xl font-semibold text-foreground">
                      {categoryConfig[category].label}
                    </h2>
                    <p class="text-sm text-muted-foreground">
                      {categoryConfig[category].description}
                    </p>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-sm font-medium text-muted-foreground">
                    {docsByCategory[category].length} {docsByCategory[category].length === 1 ? 'report' : 'reports'}
                  </span>
                  <svg
                    class="w-5 h-5 text-muted-foreground transition-transform group-open:rotate-90"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </div>
              </summary>

              <div class="p-6 pt-0 border-t border-border">
                <div class="grid grid-cols-1 gap-3 mt-6">
                  {docsByCategory[category].sort((a, b) => a.slug.localeCompare(b.slug)).map((doc) => (
                    <a
                      href={`${import.meta.env.BASE_URL}analytics/${doc.slug}`}
                      class="block p-4 bg-card border border-border rounded-lg hover:bg-accent transition-colors"
                    >
                      <div class="flex items-center justify-between">
                        <div class="flex-1">
                          <h3 class="font-semibold text-foreground">
                            {doc.title}
                          </h3>
                          <p class="text-sm text-muted-foreground mt-1">
                            {doc.description}
                          </p>
                        </div>
                        <svg
                          class="w-5 h-5 text-muted-foreground ml-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width={2}
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            </details>
          </section>
        ))}
      </div>
    </div>
  </main>
</Layout>
```

**Step 2: Test locally**

Run: `cd app && bun run dev`
Visit: `http://localhost:4321/analytics`
Expected: See 4 collapsible category sections with documents grouped

**Step 3: Verify responsive design**

Check: Mobile view (viewport < 768px)
Expected: Sections stack vertically, collapse/expand works with touch

**Step 4: Commit**

```bash
git add app/src/pages/analytics/index.astro
git commit -m "feat(analytics): add category-based grouping with collapsible sections

Replace flat document list with 4 category sections:
- Investment Guides (1 doc)
- Market Analysis (4 docs)
- Technical Reports (6 docs)
- Quick Reference (0 docs)

Each section uses native <details> element for collapse/expand,
with category icons and document counts. Mobile responsive.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Verify Full Integration

**Files:**
- Test: `scripts/sync-content.sh`
- Test: `app/src/pages/analytics/index.astro`

**Step 1: Run sync script**

Run: `bash scripts/sync-content.sh`
Expected: ✅ All 11 files synced with valid categories

**Step 2: Check app content directory**

Run: `ls -la app/src/content/analytics/`
Expected: 11 .md files with proper frontmatter

**Step 3: Build app locally**

Run: `cd app && bun run build`
Expected: Build succeeds without errors

**Step 4: Verify analytics page**

Run: `cd app && bun run preview`
Visit: `http://localhost:4321/analytics`
Verify:
- ✅ 4 category sections visible
- ✅ Documents grouped correctly
- ✅ Collapse/expand works
- ✅ Icons display correctly
- ✅ Document counts accurate

**Step 5: Test mobile responsive**

Resize browser to 375px width (iPhone)
Verify:
- ✅ Sections stack vertically
- ✅ Touch-friendly expand/collapse
- ✅ No horizontal scroll

**Step 6: Create summary commit**

```bash
git add .
git commit -m "feat(analytics): complete category-based organization implementation

Implement full category organization for analytics section:
- Sync script validates categories
- All 11 documents have category frontmatter
- Analytics page displays grouped sections
- Mobile responsive collapsible design

Categories: investment-guides, market-analysis, technical-reports, quick-reference

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Update Content Config Schema (Optional Enhancement)

**Files:**
- Modify: `app/src/content/config.ts:1-17`

**Step 1: Add category enum validation**

```typescript
import { defineCollection, z } from 'astro:content';

const analyticsCollection = defineCollection({
    type: 'content',
    schema: z.object({
        title: z.string().optional(),
        date: z.coerce.date().optional(),
        status: z.string().optional(),
        category: z.enum([
            'investment-guides',
            'market-analysis',
            'technical-reports',
            'quick-reference'
        ]).optional(),
        description: z.string().optional(),
    }),
});

export const collections = {
    'analytics': analyticsCollection,
};
```

**Step 2: Test schema validation**

Run: `cd app && bun run build`
Expected: Build validates categories successfully

**Step 3: Commit**

```bash
git add app/src/content/config.ts
git commit -m "feat(content): add category enum validation to schema

Enforce valid category values in analytics content frontmatter.
Provides type safety and build-time validation.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Testing Checklist

### Sync Script Validation
- [ ] Missing category prints warning
- [ ] Invalid category prints warning with valid values
- [ ] Valid categories pass silently
- [ ] Exit code 1 on validation errors

### Frontmatter Updates
- [ ] All 11 files have category field
- [ ] Category values match specification
- [ ] No typos in category names

### Analytics Page Display
- [ ] 4 category sections render
- [ ] Documents grouped correctly
- [ ] Collapse/expand works
- [ ] Icons display correctly
- [ ] Document counts accurate

### Responsive Design
- [ ] Desktop: sections display side-by-side stats
- [ ] Mobile: sections stack vertically
- [ ] Touch-friendly expand/collapse
- [ ] No horizontal scroll

### Build Verification
- [ ] Local build succeeds: `cd app && bun run build`
- [ ] No console errors
- [ ] All assets load correctly

---

## Rollback Plan

If deployment fails:

1. Revert commits:
```bash
git revert HEAD~6..HEAD
```

2. Restore previous sync script:
```bash
git checkout HEAD~6 scripts/sync-content.sh
```

3. Remove category frontmatter:
```bash
git checkout HEAD~6 docs/analytics/*.md
```

4. Restore analytics page:
```bash
git checkout HEAD~6 app/src/pages/analytics/index.astro
```

---

**Estimated completion time**: 30-45 minutes
**Total tasks**: 7
**Files modified**: 16 files (1 script, 11 markdown, 3 Astro/TS files)
**Commits**: 6-7 commits for incremental progress
