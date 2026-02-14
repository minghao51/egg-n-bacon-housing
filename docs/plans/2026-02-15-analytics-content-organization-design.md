# Analytics Content Organization Design

**Date**: 2026-02-15
**Status**: Approved
**Author**: Claude Code (Sonnet 4.5)

---

## Problem Statement

The analytics section (`/app/src/content/analytics/`) displays 11 markdown documents in a flat, unorganized list. Users cannot quickly find relevant content based on their needs (investors vs. researchers vs. policymakers).

**Key pain points**:
1. Information overload - documents are 400+ lines with no quick navigation
2. Poor scannability - users can't identify relevant sections quickly
3. No clear hierarchy - all documents sit in one flat list

---

## Solution: Category-Based Grouping

Organize analytics documents into 4 distinct categories by content type:
- **Investment Guides** (1 file): Actionable insights, ROI calculations
- **Market Analysis** (4 files): Trends, patterns, market-wide analysis
- **Technical Reports** (6 files): Methodology, statistical models, implementation plans
- **Quick Reference** (0 files): Tables, metrics, summaries (empty for now)

---

## Architecture

### Data Flow

```
/docs/analytics/*.md (source)
    ↓
scripts/sync-content.sh (copy + validate)
    ↓
/app/src/content/analytics/*.md (destination)
    ↓
/app/src/pages/analytics/index.astro (display grouped by category)
```

### Category Mappings

| Category | Purpose | Files |
|----------|---------|--------|
| `investment-guides` | Actionable insights for investors | `findings.md` |
| `market-analysis` | Market trends and data patterns | `analyze_lease_decay.md`, `analyze_mrt-impact-analysis.md`, `analyze_school-quality-features.md`, `analyze_spatial_autocorrelation.md` |
| `technical-reports` | Methodology and statistical models | `causal-inference-overview.md`, `plan_analyze_h3_clusters.md`, `plan_analyze_policy_impact.md`, `plan_school-impact-analysis.md`, `plan_spatial-analytics-overview.md`, `zzz_analyze_spatial_hotspots.md` |
| `quick-reference` | Tables and condensed summaries | *(empty)* |

---

## Implementation Components

### 1. Sync Script Validation (`scripts/sync-content.sh`)

**Current behavior**: Copies all `.md` files from `/docs/analytics/` to `/app/src/content/analytics/`

**Enhancements**:
- Add validation for required frontmatter field: `category`
- Validate `category` is one of 4 allowed values
- Print warnings for missing/invalid categories

**Implementation**:
```bash
# Validate each copied file has category frontmatter
for file in "$APP_CONTENT_DIR"/*.md; do
  # Check category exists
  # Check category is valid (investment-guides, market-analysis, technical-reports, quick-reference)
done
```

### 2. Update Frontmatter (`/docs/analytics/*.md`)

Standardize category field for all 11 files:

**investment-guides**:
- `findings.md`: `category: investment-guides`

**market-analysis**:
- `analyze_lease_decay.md`: `category: market-analysis`
- `analyze_mrt-impact-analysis.md`: `category: market-analysis`
- `analyze_school-quality-features.md`: `category: market-analysis`
- `analyze_spatial_autocorrelation.md`: `category: market-analysis`

**technical-reports**:
- `causal-inference-overview.md`: `category: technical-reports`
- `plan_analyze_h3_clusters.md`: `category: technical-reports`
- `plan_analyze_policy_impact.md`: `category: technical-reports`
- `plan_school-impact-analysis.md`: `category: technical-reports`
- `plan_spatial-analytics-overview.md`: `category: technical-reports`
- `zzz_analyze_spatial_hotspots.md`: `category: technical-reports`

### 3. Update Analytics Index Page (`/app/src/pages/analytics/index.astro`)

**Current behavior**: Flat list of all documents

**New behavior**:
1. Fetch all analytics documents
2. Group by `category` field
3. Render 4 collapsible sections with category labels
4. Add category icons for visual distinction

**Component structure**:
```astro
{Object.entries(groupedDocs).map(([category, docs]) => (
  <details open>
    <summary>
      <Icon /> {categoryLabels[category]} ({docs.length})
    </summary>
    <div class="grid">
      {docs.map(doc => <DocumentCard />)}
    </div>
  </details>
))}
```

**Category icons**:
- 💼 Investment Guides
- 📊 Market Analysis
- 🔬 Technical Reports
- 📋 Quick Reference

**Collapsible behavior**:
- Use native `<details>` and `<summary>` elements
- Default `open` attribute for first section
- Smooth transitions for expand/collapse

### 4. Category Labels Configuration

**Location**: `/app/src/content/config.ts` or inline in index.astro

**Purpose**: Single source of truth for category display names and icons

```typescript
const categoryLabels = {
  'investment-guides': 'Investment Guides',
  'market-analysis': 'Market Analysis',
  'technical-reports': 'Technical Reports',
  'quick-reference': 'Quick Reference',
};

const categoryIcons = {
  'investment-guides': '💼',
  'market-analysis': '📊',
  'technical-reports': '🔬',
  'quick-reference': '📋',
};
```

---

## Technical Specifications

### Frontmatter Schema

**Required fields**:
```yaml
---
title: "Document Title"
category: "investment-guides"  # One of 4 allowed values
---
```

**Optional fields** (existing):
```yaml
---
description: "Brief description"
status: "published"
date: "2026-02-06"
---
```

### Allowed Category Values

- `investment-guides`
- `market-analysis`
- `technical-reports`
- `quick-reference`

### Sync Validation Rules

**Error handling**:
1. If `category` field missing: Print warning, skip file
2. If `category` value invalid: Print warning with valid values, skip file
3. If validation passes: Continue with copy
4. Always print total count of synced files

**Validation command** (pseudo-code):
```bash
validate_category() {
  local category=$(extract_frontmatter "$1" "category")
  local valid=("investment-guides" "market-analysis" "technical-reports" "quick-reference")

  if [[ ! " ${valid[@]} " =~ " ${category} " ]]; then
    echo "⚠️  Invalid category '$category' in $1"
    echo "   Valid values: ${valid[@]}"
    return 1
  fi
}
```

---

## UI/UX Design

### Document Cards (Enhanced)

**Current design**:
```astro
<a href="..." class="card">
  <h3>{doc.title}</h3>
  <p>{doc.description}</p>
</a>
```

**Enhanced design**:
```astro
<a href="..." class="card">
  <div class="header">
    <h3>{doc.title}</h3>
    <span class="category-badge">
      {categoryIcons[doc.category]}
      {categoryLabels[doc.category]}
    </span>
  </div>
  <p>{doc.description}</p>
</a>
```

**Visual hierarchy**:
1. Title (large, bold)
2. Description (medium, muted)
3. Category badge (small, colored, top-right)
4. Document count per section (in section header)

### Category Section Styling

**Collapsible sections**:
- Border-left: 4px solid with category color
- Padding: 1rem
- Border-radius: 0.5rem
- Hover: slight background change

**Section headers**:
- Icon + label + count (e.g., "💼 Investment Guides (1)")
- Font-size: 1.25rem
- Font-weight: 600
- Cursor: pointer (for expand/collapse)

**Category colors** (optional):
- Investment Guides: Blue/primary
- Market Analysis: Green/success
- Technical Reports: Orange/warning
- Quick Reference: Gray/muted

---

## Benefits

### For Users

1. **Faster discovery** - Navigate to relevant category instantly
2. **Reduced cognitive load** - See 11 documents organized into 4 groups
3. **Clear expectations** - Category labels indicate content type
4. **Mobile-friendly** - Collapsible sections save vertical space

### For Maintainers

1. **Scalable structure** - Easy to add new documents to categories
2. **Single source** - Frontmatter drives organization
3. **No breaking changes** - URLs remain unchanged
4. **Low maintenance** - Category validation catches errors early

---

## Future Enhancements (Out of Scope)

### Phase 2 Features
1. **Category filtering** - Checkbox filters to show/hide categories
2. **Search by category** - Add category to search index
3. **Sorting options** - Sort by date, title, or category
4. **Category-specific layouts** - Different card styles per category

### Advanced Features
1. **Role-based views** - "I'm an investor" button filters to investment-guides
2. **Progressive disclosure** - Show summaries first, full content on expand
3. **Related documents** - "Read more in Market Analysis" links
4. **Analytics tracking** - Track which categories users visit most

---

## Testing Checklist

### Sync Script
- [ ] Copied files have category frontmatter
- [ ] Invalid categories print warnings
- [ ] New files in `/docs/analytics/` sync automatically
- [ ] Total count displays correctly

### Frontmatter Updates
- [ ] All 11 files have category field
- [ ] Category values match specification
- [ ] Categories match proposed mappings

### Analytics Index Page
- [ ] Documents grouped by category
- [ ] Collapsible sections work
- [ ] Category icons display correctly
- [ ] Document counts accurate
- [ ] Mobile responsive (collapsible stacks vertically)

### Visual Verification
- [ ] Category badges visible on cards
- [ ] Icons render correctly
- [ ] Section headers are clear
- [ ] No layout breakage on large screens

---

## Migration Plan

### Step 1: Update Sync Script
1. Modify `scripts/sync-content.sh`
2. Add validation logic for categories
3. Test with current files
4. Commit changes

### Step 2: Update Frontmatter
1. Update all 11 files in `/docs/analytics/`
2. Add `category` field to each
3. Verify sync script validates correctly
4. Commit changes

### Step 3: Update Analytics Index
1. Modify `/app/src/pages/analytics/index.astro`
2. Add grouping logic
3. Add collapsible sections
4. Add category icons
5. Test locally
6. Commit changes

### Step 4: Deploy and Verify
1. Push to GitHub
2. Wait for build/deploy
3. Verify analytics page displays correctly
4. Test collapsible sections
5. Check mobile responsive

---

## Risks and Mitigations

### Risk 1: Breaking Changes
**Impact**: URLs could break if restructuring
**Mitigation**: No file moves, only frontmatter updates and UI changes

### Risk 2: Category Mismatch
**Impact**: Documents appear in wrong category
**Mitigation**: Sync script validation catches errors before deployment

### Risk 3: Mobile Layout Issues
**Impact**: Collapsible sections may break on small screens
**Mitigation**: Test on multiple viewport sizes, use responsive breakpoints

### Risk 4: Icon Rendering
**Impact**: Emoji icons may not render consistently
**Mitigation**: Test on multiple browsers, fallback to text if needed

---

## Success Criteria

### Primary Goals
1. ✅ Users can navigate to relevant content within 3 seconds
2. ✅ Analytics page displays 4 distinct category sections
3. ✅ All 11 documents have valid category frontmatter
4. ✅ Sync script validates categories automatically

### Secondary Goals
1. ✅ Mobile users can collapse sections easily
2. ✅ Visual hierarchy is clear (icons, labels, counts)
3. ✅ No breaking changes to existing URLs
4. ✅ Maintainable structure for future documents

---

**Next Steps**: Proceed to implementation plan writing via `writing-plans` skill.
