# Directory Structure

## Repository Layout

```
egg-n-bacon-housing/
├── app/                          # Astro/React frontend
│   ├── src/
│   │   ├── components/           # React components
│   │   ├── hooks/               # Custom React hooks
│   │   ├── layouts/             # Astro layouts
│   │   ├── pages/               # File-based routing
│   │   ├── styles/              # CSS/styling
│   │   ├── types/               # TypeScript definitions
│   │   └── utils/               # Utility functions
│   ├── public/                  # Static assets
│   │   └── data/                # JSON data for webapp
│   ├── astro.config.mjs         # Astro configuration
│   ├── package.json             # Frontend dependencies
│   └── tsconfig.json            # TypeScript configuration
│
├── scripts/                     # Python data pipeline
│   ├── core/                    # Core utilities and config
│   │   ├── stages/              # Pipeline stages (L0-L5)
│   │   ├── config.py            # Central configuration
│   │   ├── data_helpers.py      # Data I/O utilities
│   │   ├── geocoding.py         # Geocoding utilities
│   │   └── metrics.py           # Metrics calculation
│   ├── analytics/              # Analysis scripts
│   │   ├── analysis/            # Analysis modules
│   │   ├── models/              # ML models
│   │   └── pipelines/           # Analysis pipelines
│   ├── data/                   # Data processing scripts
│   ├── utils/                  # Utility scripts
│   └── run_pipeline.py         # Main pipeline entry point
│
├── data/                       # Data storage
│   ├── pipeline/               # Pipeline outputs (L0-L5)
│   │   ├── L0/                 # Raw data
│   │   ├── L1/                 # Processed data
│   │   ├── L2/                 # Feature-enriched data
│   │   └── L3/                 # Unified dataset
│   ├── manual/                 # Manually uploaded data
│   ├── analytics/              # Analysis outputs
│   ├── logs/                   # Pipeline logs
│   └── metadata.json          # Dataset metadata
│
├── notebooks/                  # Jupyter notebooks
│   ├── L0_datagovsg.ipynb      # Data collection (paired .py)
│   └── ...
│
├── tests/                      # Test suite
│   ├── core/                   # Core functionality tests
│   ├── analytics/              # Analytics tests
│   ├── data/                   # Data processing tests
│   └── conftest.py             # Shared fixtures
│
├── .planning/                  # Planning documentation
│   └── codebase/               # Codebase documentation
│       ├── ARCHITECTURE.md
│       ├── CONCERNS.md
│       ├── CONVENTIONS.md
│       ├── INTEGRATIONS.md
│       ├── STACK.md
│       ├── STRUCTURE.md
│       └── TESTING.md
│
├── .env                        # Environment variables (not in git)
├── .env.example                # Environment template
├── pyproject.toml              # Python project configuration
├── jupytext.toml               # Notebook pairing configuration
├── CLAUDE.md                   # Project instructions
└── README.md                   # Project documentation
```

---

## Frontend Structure (app/)

### src/components/
**React components organized by domain**

```
components/
├── analytics/                  # Analytics-specific components
│   ├── TableOfContents.astro   # MDX table of contents
│   └── ...
├── charts/                     # Recharts visualization components
│   ├── TrendChart.tsx
│   ├── ComparisonChart.tsx
│   └── ...
├── dashboard/                  # Dashboard-specific components
│   ├── MetricCard.tsx
│   ├── Filters.tsx
│   └── ...
├── layout/                     # Layout components
│   ├── Header.astro
│   ├── Footer.astro
│   └── Sidebar.astro
└── shared/                     # Shared components
    ├── Button.tsx
    ├── Card.tsx
    └── ...
```

### src/hooks/
**Custom React hooks for data fetching and state**

```
hooks/
├── useAnalyticsData.ts        # Analytics data fetching
├── useLeaderboardData.ts      # Leaderboard data fetching
├── useSegmentsData.ts         # Market segments data
├── useGzipJson.ts             # Generic cached JSON fetching
└── ...
```

### src/layouts/
**Astro layout components**

```
layouts/
├── BaseLayout.astro           # Main layout wrapper
├── DashboardLayout.astro      # Dashboard-specific layout
└── AnalyticsLayout.astro      # Analytics page layout
```

### src/pages/
**File-based routing (Astro)**

```
pages/
├── index.astro                 # Landing page
├── dashboard/
│   ├── index.astro            # Main dashboard
│   ├── trends.astro           # Trends view
│   └── leaderboard.astro      # Leaderboard view
├── analytics/
│   └── [slug].astro           # Dynamic analytics (MDX)
└── ...
```

### src/types/
**TypeScript type definitions**

```
types/
├── analytics.ts               # Analytics data types
├── leaderboard.ts             # Leaderboard types
├── segments.ts                # Market segment types
└── ...
```

### src/utils/
**Utility functions**

```
utils/
├── gzip.ts                    # Gzip compression utilities
├── formatters.ts              # Data formatting helpers
└── ...
```

### public/data/
**Static JSON files (generated by Python)**

```
data/
├── overview.json.gz           # Dashboard overview data
├── trends.json.gz             # Trends time series
├── leaderboard.json.gz        # Leaderboard rankings
├── segments.json.gz           # Market segments
└── analytics/
    ├── spatial-analytics.json.gz
    ├── feature-analytics.json.gz
    └── predictive-analytics.json.gz
```

---

## Python Pipeline Structure (scripts/)

### core/
**Core utilities and configuration**

```
core/
├── config.py                  # Centralized configuration
├── data_helpers.py            # Parquet I/O with metadata
├── geocoding.py               # Geocoding (OneMap + Google)
├── metrics.py                 # Dashboard metrics
├── cache.py                   # Caching utilities
└── stages/                    # Pipeline stages
    ├── L0_collect.py          # Data collection
    ├── L1_process.py          # Processing & geocoding
    ├── L2_features.py         # Feature engineering
    ├── L3_export.py           # Unified dataset export
    ├── webapp_data_preparation.py  # JSON export
    └── regional_mapping.py    # Geographic regions
```

### analytics/
**Analysis and ML models**

```
analytics/
├── analysis/                  # Analysis modules
│   ├── mrt/                   # MRT impact analysis
│   ├── school/                # School tier analysis
│   ├── market/                # Market analysis
│   ├── amenity/               # Amenity impact
│   └── spatial/               # Spatial analysis
├── models/                    # ML models
│   ├── area_arimax.py        # ARIMAX models
│   ├── regional_var.py       # Regional variance models
│   └── ...
└── pipelines/                 # Analysis pipelines
    ├── cross_validate.py
    ├── forecast_appreciation.py
    └── calculate_l3_metrics_pipeline.py
```

### data/
**Data processing scripts**

```
data/
├── fetch_macro_data.py        # SingStat macro data
├── mrt_line_mapping.py        # MRT line definitions
└── ...
```

### utils/
**Utility scripts**

```
utils/
├── verify_imports.py          # Import verification
└── ...
```

---

## Data Storage Structure (data/)

### pipeline/
**Stage-based data storage**

```
pipeline/
├── L0/                        # Raw collected data
│   ├── hdb_resale.parquet
│   ├── ura_transactions.parquet
│   └── macro_data.parquet
├── L1/                        # Processed & geocoded
│   ├── hdb_transactions.parquet
│   ├── ura_transactions.parquet
│   └── ...
├── L2/                        # Feature-enriched
│   ├── hdb_with_features.parquet
│   ├── ura_with_features.parquet
│   └── ...
└── L3/                        # Unified dataset
    └── unified_dataset.parquet
```

### manual/
**Manually uploaded data**

```
manual/
├── mrt_stations.csv
├── school_locations.csv
└── ...
```

### analytics/
**Analysis outputs**

```
analytics/
├── mrt_impact.parquet
├── school_analysis.parquet
└── ...
```

### metadata.json
**Dataset metadata and tracking**

```json
{
  "datasets": {
    "L0_hdb_resale": {
      "path": "data/pipeline/L0/hdb_resale.parquet",
      "source": "data.gov.sg",
      "rows": 1000000,
      "columns": 12,
      "created_at": "2024-01-01T00:00:00",
      "checksum": "abc123"
    }
  }
}
```

---

## Test Structure (tests/)

**Mirrors production code structure**

```
tests/
├── conftest.py                 # Shared fixtures
├── core/                       # Core tests
│   ├── test_config.py
│   ├── test_data_helpers.py
│   ├── test_cache.py
│   └── test_regional_mapping.py
├── analytics/                  # Analytics tests
│   ├── models/
│   │   ├── test_area_arimax.py
│   │   └── test_regional_var.py
│   ├── pipelines/
│   │   ├── test_cross_validate.py
│   │   └── test_forecast_appreciation.py
│   └── test_prepare_timeseries_data.py
├── data/                       # Data processing tests
│   └── test_fetch_macro_data.py
└── integration/                # Integration tests
    ├── test_pipeline.py
    ├── test_geocoding.py
    ├── test_mrt_integration.py
    └── test_analytics_export.py
```

---

## Naming Conventions

### Python Files

**Pipeline Scripts:**
- Pattern: `L{stage}_{description}.py`
- Examples: `L0_collect.py`, `L1_process.py`, `L2_features.py`

**Dataset Files:**
- Pattern: `L{stage}_{entity}_{type}.parquet`
- Examples: `L1_hdb_transactions.parquet`, `L2_hdb_with_features.parquet`

**Analysis Scripts:**
- Pattern: `analyze_{topic}.py`
- Examples: `analyze_mrt_impact.py`, `analyze_school_tiers.py`

**Test Files:**
- Pattern: `test_{module}.py`
- Examples: `test_config.py`, `test_data_helpers.py`

### Frontend Files

**Components:**
- Pattern: PascalCase.astro or PascalCase.tsx
- Examples: `Sidebar.astro`, `TrendChart.tsx`

**Pages:**
- Pattern: kebab-case.astro
- Examples: `index.astro`, `leaderboard.astro`

**Hooks:**
- Pattern: camelCase with `use` prefix
- Examples: `useAnalyticsData.ts`, `useGzipJson.ts`

**Types:**
- Pattern: PascalCase.ts
- Examples: `analytics.ts`, `leaderboard.ts`

**JSON Data:**
- Pattern: `{entity}-{type}.json.gz`
- Examples: `spatial-analytics.json.gz`, `leaderboard.json.gz`

---

## Key File Locations

### Configuration
- **Python:** `scripts/core/config.py`
- **Frontend:** `app/astro.config.mjs`, `app/package.json`
- **TypeScript:** `app/tsconfig.json`
- **Tests:** `pyproject.toml`

### Entry Points
- **Pipeline:** `scripts/run_pipeline.py`
- **Frontend:** `app/src/pages/index.astro`
- **Dashboard:** `app/src/pages/dashboard/index.astro`
- **Analytics:** `app/src/pages/analytics/[slug].astro`

### Data Flow
- **Raw Data:** `data/pipeline/L0/`
- **Processed:** `data/pipeline/L1/`, `L2/`, `L3/`
- **Webapp Data:** `app/public/data/`
- **Generated By:** `scripts/prepare_webapp_data.py`

### Component Libraries
- **Shared:** `app/src/components/shared/`
- **Dashboard:** `app/src/components/dashboard/`
- **Analytics:** `app/src/components/analytics/`
- **Charts:** `app/src/components/charts/`

---

## Import Path Conventions

### Python
**ALWAYS use absolute imports from project root:**

```python
# ✓ Correct
from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet
from scripts.core.stages.L1_process import process_transactions

# ✗ Wrong
from ..core.config import Config
from .stages.L1_process import process_transactions
```

**Reason:** Relative imports break when scripts run from different directories.

### Frontend (TypeScript)
**Path aliases configured in tsconfig.json:**

```typescript
// Path aliases
import { MyComponent } from '@components/shared/MyComponent';
import { useAnalyticsData } from '@hooks/useAnalyticsData';
import { AnalyticsData } from '@types/analytics';
import { formatDate } from '@utils/formatters';
```

**Available Aliases:**
- `@/*` → `./src/*`
- `@components/*` → `./src/components/*`
- `@layouts/*` → `./src/layouts/*`
- `@hooks/*` → `./src/hooks/*`
- `@types/*` → `./src/types/*`
- `@utils/*` → `./src/utils/*`
- `@data/*` → `./src/data/*`

---

## Hidden/System Files

```
.venv/                        # Python virtual environment (not in git)
.node_modules/                # Node dependencies (not in git)
.astro/                       # Astro build cache (not in git)
.env                          # Environment variables (not in git)
.claude/                      # Claude Code handoffs (not in git)
.context7/                    # Context data (not in git)
gitignore                     # Git ignore rules
.env.example                  # Environment template
```

---

## File Organization Principles

1. **Separation of Concerns:** Clear boundary between data processing and presentation
2. **Domain-Driven Structure:** Files grouped by feature/domain
3. **Mirrored Test Structure:** Tests mirror production code
4. **Centralized Configuration:** Config files in dedicated locations
5. **Absolute Imports:** Prevents path issues
6. **Consistent Naming:** Clear patterns for easy navigation
7. **Metadata-Driven Data:** All data tracked in metadata.json
