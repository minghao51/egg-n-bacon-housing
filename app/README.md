# Egg n Bacon Housing Analytics

A modern, static documentation site for Singapore housing market analytics, built with Bun, Astro, and React.

## 🚀 Features

- **Fast & Modern**: Built with Bun runtime and Astro static site generator
- **Interactive Charts**: Time series, comparison, and statistical visualizations
- **Beautiful UI**: Tailwind CSS with shadcn/ui components
- **Dark Mode**: Toggle between light and dark themes
- **Responsive**: Works perfectly on mobile, tablet, and desktop
- **Searchable Tables**: Sortable, filterable data tables with search
- **Syntax Highlighting**: Code snippets with 100+ language support
- **Math Formulas**: LaTeX-style math rendering with KaTeX
- **Table of Contents**: Auto-generated navigation for long documents
- **Image Support**: Display PNG/JPG charts from Python
- **Plotly Support**: Embed interactive Plotly charts
- **Static HTML**: No server required, deploy anywhere

## 📊 Analytics Documentation

Displays 11 comprehensive analytics documents covering Singapore housing market analysis, including metrics design, causal inference, rental yields, spatial analytics, MRT impact, and policy analysis.

## 🛠️ Tech Stack

- **Runtime**: Bun (ultra-fast JavaScript runtime)
- **Framework**: Astro (static site generator)
- **UI**: React 19 + shadcn/ui components
- **Charts**: Recharts (time series, comparison, scatter plots)
- **Tables**: TanStack Table v8 (sortable, filterable)
- **Styling**: Tailwind CSS v3
- **Language**: TypeScript

## 📦 Installation

```bash
# Install dependencies
bun install
```

## 🚀 Development

```bash
# Start development server
bun run dev

# Site will be available at http://localhost:4321
```

## 🏗️ Build

```bash
# Build for production
bun run build

# Output will be in /dist directory
```

## 📁 Preview Production Build

```bash
bun run preview
```

## 📂 Project Structure

```
app/
├── src/
│   ├── components/
│   │   ├── charts/              # Chart components
│   │   ├── Sidebar.astro        # Navigation sidebar
│   │   └── DarkModeToggle.tsx   # Theme toggle
│   ├── layouts/
│   │   └── Layout.astro         # Base layout
│   ├── pages/
│   │   └── analytics/           # Analytics pages
│   ├── styles/
│   │   └── globals.css          # Global styles + Tailwind
│   └── utils/                   # Utility functions
├── public/                      # Static assets
├── astro.config.mjs            # Astro configuration
└── tailwind.config.mjs         # Tailwind configuration
```

## 🎨 Features Breakdown

### Chart Types

1. **Time Series Charts** - Line charts for trends
2. **Comparison Charts** - Bar charts for comparisons
3. **Statistical Plots** - Scatter plots for distributions
4. **Interactive Tables** - Sortable, filterable tables

### Auto-Detection

The `ChartRenderer` component automatically:
- Detects time-series and comparison data
- Extracts numeric values from formatted text
- Renders appropriate chart types

## 🌙 Dark Mode

Toggle button in sidebar with localStorage persistence.

## 📱 Responsive Design

Mobile-first approach with sidebar hidden on smaller screens.

## 🚢 Deployment

Deploy `/dist` folder to any static host (Netlify, Vercel, GitHub Pages, etc.)

## ⚡ Performance

- **Build Time**: ~1.3 seconds for 13 pages
- **Bundle Size**: ~440KB (gzipped: ~128KB) for all charts
- **Static HTML**: No client-side JavaScript required for core content

## 🤝 Integration with Python Pipeline

This site is **read-only** and automatically reads markdown files from `docs/analytics/`. No changes needed to Python scripts.

---

*Generated with Bun + Astro + React*
