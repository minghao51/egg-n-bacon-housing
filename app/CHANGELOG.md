# Backend Changelog

Astro/Bun static documentation site for Singapore housing market analytics.

## Version 1.0.0 (2026-01-30)

### Initial Release Features

#### Core Features
- **Fast & Modern**: Built with Bun runtime and Astro static site generator
- **Interactive Charts**: Time series, comparison, and statistical visualizations
- **Beautiful UI**: Tailwind CSS with shadcn/ui components
- **Dark Mode**: Toggle between light and dark themes
- **Responsive**: Mobile, tablet, and desktop support
- **Searchable Tables**: Sortable, filterable data tables
- **Syntax Highlighting**: 100+ language support via Shiki
- **Math Formulas**: LaTeX-style rendering with KaTeX
- **Table of Contents**: Auto-generated navigation for long documents
- **Image Support**: PNG/JPG charts from Python scripts
- **Plotly Support**: Embed interactive Plotly charts
- **Static HTML**: No server required, deploy anywhere

### Major Improvements Implemented

#### 1. Syntax Highlighting (Shiki)
- **Engine**: Shiki v3.21.0
- **Languages**: 100+ (Python, JavaScript, SQL, etc.)
- **Themes**: GitHub Light/Dark with auto-switching
- **Impact**: Professional code display with colored syntax

#### 2. Formula LaTeX Rendering (KaTeX)
- **Auto-conversion**: Plain text to LaTeX (e.g., `P_t` → \(P_t\))
- **Features**:
  - Subscripts: `P_{t-1}` → \(P_{t-1}\)
  - Fractions: `a / b` → \(\frac{a}{b}\)
  - Multiplication: `×` → \(\times\)
  - Percentages: `%` → `\%\)
- **Result**: Beautiful mathematical notation

#### 3. Inline Chart Rendering
- **Architecture**: React portals for inline placement
- **Component**: `InlineChartRenderer.tsx`
- **Bundle Improvement**: 55KB smaller (440KB → 385KB)
- **UX**: Charts appear inline with content, not at bottom

#### 4. Table of Contents
- **Auto-generated**: From H2/H3 headings
- **Position**: Sticky right sidebar (xl screens only)
- **Features**:
  - Smooth scroll navigation
  - Active section highlighting
  - Intersection Observer for scroll tracking
  - Hidden on smaller screens

#### 5. Enhanced Markdown Rendering
- **Tables**: Proper HTML with borders, styling, hover effects
- **Typography**: Proper H2/H3 spacing with scroll offset
- **Code blocks**: Background, padding, monospace font
- **Inline code**: Muted background with rounded corners
- **Blockquotes**: Left border accent
- **Links**: Hover states

### Layout Changes

**Before**: Single column (sidebar + content)
**After**: Three column on xl screens (sidebar + content + TOC)

```
┌─────────────┬──────────────────┬─────────────┐
│  Sidebar    │   Main Content   │   TOC       │
│  (256px)    │   (max-w-4xl)    │   (256px)   │
└─────────────┴──────────────────┴─────────────┘
```

### Performance Metrics

| Metric | Value |
|--------|-------|
| Build Time | 1.48s for 13 pages |
| Chart Bundle | 385KB (gzipped: ~110KB) |
| Total Bundle | 415KB (gzipped: ~120KB) |
| Page Generation | 1-67ms per page |

### Dependencies

**Production**:
- `astro@^4.18.0`
- `react@^19.2.4`
- `shiki@^3.21.0` (syntax highlighting)
- `@tailwindcss/vite@^4.0.0`

**Dev Dependencies**:
- `@astrojs/react@^4.0.1`
- `@astrojs/tailwind@^6.0.0`
- `bun-types@latest`

### Files Created

#### Components
- `src/components/charts/InlineChartRenderer.tsx` - Inline chart rendering
- `src/components/PlotlyEmbed.astro` - Plotly iframe embed
- `src/components/TableOfContents.astro` - Auto-generated TOC
- `src/components/DarkModeToggle.tsx` - Theme switcher

#### Utilities
- `src/utils/markdown-renderer.ts` - Markdown to HTML with async highlighting
- `src/utils/syntax-highlight.ts` - Shiki integration
- `src/utils/formula-converter.ts` - Plain text to LaTeX converter

#### Directories
- `public/images/analytics/` - Static chart images
- `public/plots/` - Plotly HTML exports

### Files Modified

- `src/pages/analytics/[slug].astro` - Main analytics page template
- `src/utils/markdown.ts` - Added `stripTitle()` function
- `package.json` - Added dependencies
- `astro.config.mjs` - Astro configuration
- `tailwind.config.mjs` - Tailwind CSS configuration

### Known Limitations

1. **Formula Conversion**: Simple pattern matching (not full LaTeX parser)
2. **TOC**: Only H2/H3 headings (not H4+)
3. **Plotly**: iframe-based (can't style internals)
4. **Images**: Must be in `public/` directory (no external paths)
5. **Build Time**: +0.17s vs. baseline (acceptable for features)

### Testing Checklist

- [x] Tables render with borders and hover effects
- [x] Code blocks have syntax highlighting
- [x] Formulas render with LaTeX
- [x] Charts appear inline (not at bottom)
- [x] TOC appears on right (xl screens)
- [x] Dark mode toggle works
- [x] Images display correctly
- [x] Plotly charts are interactive
- [x] Responsive design works

### Usage Examples

#### Adding Images
```python
# Python: Save chart
plt.savefig('app/public/images/analytics/chart.png', dpi=150)
```

```markdown
<!-- Markdown: Reference image -->
![Analysis Results](images/analytics/chart.png)
```

#### Adding Plotly Charts
```python
# Python: Export Plotly
fig.write_html('app/public/plots/price-trend.html')
```

Auto-detected - just place HTML file in `public/plots/`

#### Writing Formulas
```markdown
**Formula:**
```
Growth (%) = (P_t - P_{t-1}) / P_{t-1} × 100
```
```

Auto-converts to: \(Growth (\%) = \frac{P_t - P_{t-1}}{P_{t-1}} \times 100\)

### Development

```bash
# Install dependencies
bun install

# Start dev server
bun run dev
# Site: http://localhost:4321/

# Build for production
bun run build
# Output: dist/ directory

# Preview production build
bun run preview
```

### Deployment

1. **Build**: `bun run build`
2. **Output**: `dist/` folder
3. **Deploy**: Upload to any static host (Netlify, Vercel, GitHub Pages)

### Migration Notes

**For Content Authors**:
- No markdown changes needed
- Code blocks auto-highlight (specify language for best results)
- Tables auto-convert to inline charts
- Formulas auto-convert to LaTeX
- TOC auto-generates from H2/H3 headings

**No Breaking Changes**: All changes are backward compatible.

---

## Future Enhancements (Optional)

- [ ] Line numbers in code blocks
- [ ] Copy button on code blocks
- [ ] Search functionality
- [ ] Print-friendly styles
- [ ] PDF export
- [ ] Reading progress indicator
- [ ] Image lightbox/gallery
- [ ] Mermaid diagram support
- [ ] More syntax highlighting themes
- [ ] Collapsible TOC sections

---

**Last Updated**: 2026-01-30
**Tech Stack**: Bun + Astro + React + Shiki + KaTeX
**Status**: Production Ready ✅
