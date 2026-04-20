# Architecture

## Overview

Dual-stack project: **Python data pipeline** + **Astro webapp**.

## Patterns

### Python Pipeline: Stage-Based Processing
Sequential data pipeline with clear separation:
- **L0**: Data collection (data.gov.sg APIs)
- **L0_macro**: Macro economic data (CPI, GDP, SORA, unemployment, PPI)
- **L1**: Processing + geocoding
- **L2**: Feature engineering (rental yields, property features)
- **L3**: Export to unified dataset
- **L4**: Analysis (spatial, school, price modeling)
- **L5**: Metrics calculation
- **Webapp**: JSON export for dashboard

### Astro Webapp: Page-Based + Content Collections
- File-based routing in `app/src/pages/`
- Content collections for analytics (`app/src/content/analytics/`)
- React components for interactive dashboard elements
- Astro layouts for consistent page structure

## Layers

### Python (`scripts/`)
```
core/           # Config, geocoding, cache, pipeline orchestration
├── config.py   # Centralized configuration (entry point dependency)
├── cache.py    # Caching utilities
├── geocoding.py # OneMap API integration
└── stages/     # Pipeline stage implementations
analytics/      # ML models, statistical analysis
webapp/         # Dashboard data preparation scripts
```

### Astro (`app/src/`)
```
pages/          # File-based routes (Astro + dynamic routes)
layouts/       # Page layouts (Layout.astro)
components/     # UI components (Astro + React)
  ├── charts/   # Reusable chart components (tsx)
  ├── dashboard/ # Dashboard-specific components (tsx)
  └── ...
hooks/          # React hooks (useSegmentsData, useGzipJson, etc.)
types/          # TypeScript type definitions
utils/          # Utility functions (data-parser, colorScales, gzip)
constants/      # App constants (data-urls, dashboard-nav)
content/        # Content collection (MDX analytics)
data/           # Static JSON data (personas, glossary)
styles/         # Global CSS
```

## Data Flow

```
data.gov.sg APIs
      ↓
L0_collect → L1_process → L2_features → L3_export → L4/L5 → webapp_data_preparation
      ↓           ↓            ↓            ↓            ↓              ↓
   Raw JSON   Geocoded    Rental yields  Unified    Analytics    Dashboard JSON
   datasets   parquet     + features     dataset    results      (app/data/)
```

Dashboard reads JSON from `app/src/data/` or generated analytics.

## Entry Points

| Component | Entry Point |
|-----------|-------------|
| Pipeline | `scripts/run_pipeline.py` |
| Webapp | `app/src/pages/index.astro` |
| Dashboard Routes | `app/src/pages/dashboard/*.astro` |
| Analytics Routes | `app/src/pages/analytics/*.astro` |
| Content | `app/src/content.config.ts` |

## Routing

### Astro Pages
- `/` → `index.astro`
- `/dashboard` → `dashboard/index.astro`
- `/dashboard/map` → `dashboard/map.astro`
- `/dashboard/trends` → `dashboard/trends.astro`
- `/dashboard/segments` → `dashboard/segments.astro`
- `/dashboard/leaderboard` → `dashboard/leaderboard.astro`
- `/analytics` → `analytics/index.astro`
- `/analytics/[slug]` → `analytics/[slug].astro`
- `/analytics/personas/[persona]` → `analytics/personas/[persona].astro`

### Dynamic Routing
- `[slug].astro` uses `getStaticPaths()` for analytics content
- `[persona].astro` uses persona routing for personalized views
