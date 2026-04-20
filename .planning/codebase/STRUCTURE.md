# Structure

## Top-Level Directory

```
egg-n-bacon-housing/
├── app/                  # Astro webapp
├── scripts/              # Python pipeline & analytics
├── notebooks/            # Jupyter notebooks (exploration, analysis)
├── tests/                # Pytest test suite
├── data/                 # Pipeline outputs, cache, logs
├── docs/                 # Documentation
├── CLAUDE.md             # Development guidelines
├── README.md             # Project overview
├── QUICKSTART.md         # Quick start guide
├── pyproject.toml        # Python dependencies (uv)
├── jupytext.toml         # Jupyter notebook config
└── .env.example          # Environment template
```

## Python (`scripts/`)

```
scripts/
├── run_pipeline.py           # Pipeline orchestrator (main entry)
├── core/                     # Core pipeline modules
│   ├── config.py             # Configuration (paths, API keys)
│   ├── cache.py               # Caching utilities
│   ├── geocoding.py           # OneMap geocoding
│   ├── data_helpers.py       # Data loading helpers
│   ├── data_loader.py        # Data loading utilities
│   ├── data_quality.py       # Quality checks
│   ├── logging_config.py     # Logging setup
│   ├── metrics.py            # Metric calculations
│   ├── mrt_distance.py       # MRT distance calculations
│   ├── mrt_line_mapping.py   # MRT line mappings
│   ├── network_check.py      # Network utilities
│   ├── regional_mapping.py   # Regional mappings
│   ├── script_base.py        # Base script class
│   ├── school_features.py    # School feature engineering
│   ├── utils.py              # General utilities
│   ├── stages/               # Pipeline stages
│   │   ├── L0_collect.py     # Data collection
│   │   ├── L1_process.py     # Processing + geocoding
│   │   ├── L2_features.py   # Feature engineering
│   │   ├── L2_rental.py      # Rental yield calculations
│   │   ├── L3_export.py      # Export
│   │   ├── L4_analysis.py    # Analysis
│   │   ├── L5_metrics.py     # Metrics
│   │   ├── spatial_h3.py     # H3 spatial indexing
│   │   └── webapp_data_preparation.py  # Dashboard data
│   └── helpers/              # Stage helpers
│       ├── collect_helpers.py
│       ├── export_helpers.py
│       ├── geocoding_helpers.py
│       ├── spatial_helpers.py
│       └── analysis_helpers.py
├── analytics/                # ML & statistical analysis
│   ├── analysis/             # Analysis scripts
│   │   ├── school/           # School impact analysis
│   │   └── policy/           # Policy findings
│   ├── models/               # ML models
│   ├── pipelines/            # Analysis pipelines
│   ├── price_appreciation_modeling/  # Price modeling
│   ├── segmentation/         # Market segmentation
│   └── viz/                  # Visualizations
├── webapp/                   # Webapp data preparation
├── utils/                    # Standalone utilities
└── tools/                    # Development tools
```

## Astro Webapp (`app/`)

```
app/
├── astro.config.mjs          # Astro configuration
├── package.json              # Node dependencies
├── tsconfig.json             # TypeScript config
├── tailwind.config.mjs       # Tailwind CSS config
├── playwright.config.ts      # E2E test config
├── public/                   # Static assets
└── src/
    ├── index.astro            # Homepage
    ├── content.config.ts      # Content collections
    ├── layouts/
    │   └── Layout.astro      # Base layout
    ├── pages/
    │   ├── index.astro       # Landing page
    │   ├── dashboard/
    │   │   ├── index.astro   # Market overview
    │   │   ├── map.astro     # Price map
    │   │   ├── trends.astro  # Trends analysis
    │   │   ├── segments.astro # Market segments
    │   │   └── leaderboard.astro # Town rankings
    │   └── analytics/
    │       ├── index.astro   # Analytics overview
    │       ├── [slug].astro  # Dynamic analytics pages
    │       └── personas/
    │           └── [persona].astro # Persona-specific views
    ├── components/
    │   ├── charts/           # Reusable chart components
    │   │   ├── ChartRenderer.tsx
    │   │   ├── ClientChart.tsx
    │   │   ├── ComparisonChart.tsx
    │   │   ├── InlineChartRenderer.tsx
    │   │   ├── InteractiveTable.tsx
    │   │   ├── StatisticalPlot.tsx
    │   │   └── TimeSeriesChart.tsx
    │   ├── dashboard/        # Dashboard-specific components
    │   │   ├── segments/     # Segment analysis
    │   │   │   ├── compare/  # Comparison tab
    │   │   │   ├── details/  # Details tab
    │   │   │   ├── discover/ # Discovery tab
    │   │   │   ├── investigate/ # Investigation tab
    │   │   │   ├── FilterPanel.tsx
    │   │   │   ├── SegmentCard.tsx
    │   │   │   ├── SegmentsAnalysis.tsx
    │   │   │   ├── TabNavigation.tsx
    │   │   │   └── SegmentsDashboard.tsx
    │   │   ├── leaderboard/  # Leaderboard components
    │   │   ├── map/          # Map components
    │   │   │   └── overlays/ # Map overlays
    │   │   ├── tools/        # Interactive tools
    │   │   ├── PriceMap.tsx
    │   │   ├── TrendsMap.tsx
    │   │   └── ...
    │   ├── Sidebar.astro
    │   ├── TableOfContents.astro
    │   ├── DarkModeToggle.tsx
    │   └── MarkdownContent.tsx
    ├── hooks/                # React hooks
    │   ├── useAnalyticsData.ts
    │   ├── useFilterState.ts
    │   ├── useGzipJson.ts
    │   ├── useLeaderboardData.ts
    │   ├── useSegmentMatching.ts
    │   └── useSegmentsData.ts
    ├── types/                # TypeScript types
    │   ├── analytics.ts
    │   ├── leaderboard.ts
    │   └── segments.ts
    ├── utils/                # Utilities
    │   ├── cn.ts             # Class name utility
    │   ├── colorScales.ts
    │   ├── data-parser.ts
    │   └── gzip.ts
    ├── constants/            # App constants
    │   ├── data-urls.ts
    │   └── dashboard-nav.ts
    ├── data/                 # Static data (JSON)
    │   ├── analytics-glossary.json
    │   └── persona-content.json
    ├── content/              # Content collections
    │   └── analytics/        # MDX analytics articles
    │       ├── causal-inference-overview.mdx
    │       ├── findings.mdx
    │       ├── lease-decay.mdx
    │       ├── mrt-impact.mdx
    │       ├── price-forecasts.mdx
    │       ├── school-quality.mdx
    │       ├── spatial-autocorrelation.mdx
    │       └── spatial-hotspots.mdx
    └── styles/
        └── globals.css
```

## Key Locations

| Purpose | Location |
|---------|----------|
| Pipeline runner | `scripts/run_pipeline.py` |
| Config | `scripts/core/config.py` |
| Tests | `tests/` |
| App entry | `app/src/pages/index.astro` |
| Dashboard routes | `app/src/pages/dashboard/` |
| Analytics routes | `app/src/pages/analytics/` |
| Dashboard components | `app/src/components/dashboard/` |
| Chart components | `app/src/components/charts/` |
| Static data | `app/src/data/` |
| Content collection | `app/src/content/analytics/` |
| Data outputs | `data/analytics/` |

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Python modules | snake_case | `data_helpers.py` |
| Python classes | PascalCase | `class Config:` |
| Python functions | snake_case | `run_processing_pipeline()` |
| Astro pages | kebab-case | `price-trends.astro` |
| React components | PascalCase | `SegmentsDashboard.tsx` |
| TypeScript types | PascalCase | `interface AnalyticsData` |
| Hooks | camelCase | `useSegmentsData.ts` |
| Constants | SCREAMING_SNAKE | `MAX_BUFFER_SIZE` |
| CSS classes | kebab-case | `bg-background` |
