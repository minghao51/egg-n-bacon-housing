# System Architecture

## Overview

This project uses a **dual-track architecture** with clear separation between:

1. **Python ETL Pipeline** - Data processing, analytics, and ML models
2. **Astro/React Webapp** - Frontend dashboard and visualization

**Key Principle:** Frontend consumes pre-generated static JSON files; no runtime API calls or backend database.

---

## Data Pipeline Architecture

### Stage-Based ETL Pattern

The pipeline follows a **stage-based architecture** (L0-L5) where each stage has a single responsibility:

```
L0 (Collection) → L1 (Processing) → L2 (Features) → L3 (Export) → L4 (Analysis) → L5 (Metrics)
```

#### Stage Descriptions

**L0 - Data Collection**
- **Purpose:** Fetch raw data from external APIs
- **Sources:** data.gov.sg (HDB/URA transactions), SingStat (macro data)
- **Output:** Raw Parquet files
- **Location:** `scripts/core/stages/L0_collect.py`

**L1 - Data Processing**
- **Purpose:** Clean data, standardize formats, geocode addresses
- **Process:** OneMap geocoding → Google Maps fallback
- **Output:** Geocoded transaction data
- **Location:** `scripts/core/stages/L1_process.py`

**L2 - Feature Engineering**
- **Purpose:** Add features (MRT distances, CBD distance, school tiers, amenities)
- **Features:** Spatial distances, rental yields, property features
- **Output:** Feature-enriched datasets
- **Location:** `scripts/core/stages/L2_features.py`

**L3 - Export & Unification**
- **Purpose:** Create unified dataset combining all property types
- **Output:** Single Parquet with HDB + Condo + Landed
- **Location:** `scripts/core/stages/L3_export.py`

**L4 - Analysis**
- **Purpose:** ML models, spatial analysis, forecasting
- **Models:** XGBoost, ARIMA, spatial regression
- **Output:** Analysis results (Parquet)
- **Location:** `scripts/analytics/`

**L5 - Metrics**
- **Purpose:** Calculate dashboard metrics at planning area level
- **Output:** Aggregated metrics for frontend
- **Location:** `scripts/core/metrics.py`

---

### Pipeline Orchestration

**Entry Point:** `scripts/run_pipeline.py`

**Features:**
- Sequential stage execution with dependencies
- Checkpoint-based recovery (skip completed stages)
- Progress logging and error reporting
- Configurable stage execution (run specific stages)

**Usage:**
```bash
uv run python scripts/run_pipeline.py --stages L0 L1 L2
```

---

## Frontend Architecture

### Framework Choice: Astro

**Why Astro?**
- Static site generation (optimal performance)
- Islands architecture for interactive components
- Zero JS by default (minimal bundle size)
- Built-in MDX support for analytics reports

### Component Architecture

**Pattern:** Component-based with React islands

**Entry Points:**
- `app/src/pages/index.astro` - Landing page
- `app/src/pages/dashboard/index.astro` - Dashboard
- `app/src/pages/analytics/[slug].astro` - Dynamic analytics (MDX)

**Component Hierarchy:**
```
Layouts (BaseLayout.astro)
  ↓
Pages (index.astro, dashboard/*)
  ↓
Components (charts/, dashboard/, analytics/)
  ↓
Utilities (hooks/, utils/)
```

---

### Data Loading Strategy

**Pattern:** Custom hook-based data fetching

**Primary Hook:** `useGzipJson<T>(url, key, enabled)`

**Features:**
- Cached data fetching (localStorage)
- Gzip decompression
- Type-safe with TypeScript generics
- Error handling with retry

**Usage:**
```typescript
const { data, isLoading, error } = useGzipJson<AnalyticsData>(
  '/data/spatial-analytics.json.gz',
  'spatial-analytics',
  true
);
```

**Specialized Hooks:**
- `useAnalyticsData<T>()` - Analytics data
- `useLeaderboardData()` - Leaderboard rankings
- `useSegmentsData()` - Market segments

---

### State Management

**Approach:** Hook-based state (no Redux/Zustand)

**Patterns:**
- Custom hooks for domain-specific state
- React useState for local component state
- URL params for shared state (filters, selections)

**Example:**
```typescript
const [filteredData, setFilteredData] = useState<Data>([]);
const [filters, setFilters] = useState<Filters>({});
```

---

## Data Flow Architecture

### Processing Pipeline Flow

```
External APIs (data.gov.sg, SingStat)
    ↓
L0: Fetch + Cache
    ↓
L1: Clean + Geocode (OneMap → Google)
    ↓
L2: Add Features (MRT, CBD, Schools)
    ↓
L3: Merge + Export Unified Dataset
    ↓
L4: Run Analysis (ML, Spatial)
    ↓
L5: Calculate Metrics
    ↓
JSON Export (prepare_webapp_data.py)
    ↓
Static Files (app/public/data/*.json.gz)
```

### Frontend Data Flow

```
User Request
    ↓
useGzipJson Hook
    ↓
Fetch JSON.gz
    ↓
Decompress + Parse
    ↓
Type-Safe Data
    ↓
React Components
    ↓
Visualizations (Recharts, Leaflet)
```

**Key Benefits:**
- No backend API latency
- Perfect caching (static files)
- CDN-friendly
- Simplified deployment

---

## Abstractions & Patterns

### Python Side

#### Configuration Abstraction
**File:** `scripts/core/config.py`

**Pattern:** Centralized Config class with class-level properties

**Benefits:**
- Single source of truth
- Type-safe access
- Validation on initialization
- Environment variable management

**Usage:**
```python
from scripts.core.config import Config

data_dir = Config.DATA_DIR
api_key = Config.ONEMAP_EMAIL
```

#### Data Abstraction
**File:** `scripts/core/data_helpers.py`

**Pattern:** Metadata-driven Parquet I/O

**Features:**
- Load/save by dataset name (not path)
- Automatic metadata tracking
- Version control support
- Checksum verification

**Usage:**
```python
from scripts.core.data_helpers import load_parquet, save_parquet

df = load_parquet("L1_hdb_transactions")
save_parquet(df, "L2_hdb_with_features")
```

#### API Abstraction
**Pattern:** Decorator-based caching

**Features:**
- TTL-based caching (24h default)
- Retry logic with tenacity
- Rate limiting (delays)
- Error handling

**Usage:**
```python
@cached_call(ttl=86400)
def fetch_api_data(url):
    # API call
    pass
```

---

### Frontend Side

#### Data Loading Abstraction
**Pattern:** Generic useGzipJson hook

**Features:**
- Type-safe with generics
- Automatic decompression
- Local storage caching
- Error handling

**Usage:**
```typescript
const { data } = useGzipJson<MyDataType>('/data/file.json.gz', 'cache-key');
```

#### Component Abstraction
**Pattern:** Composable components with TypeScript interfaces

**Example:**
```typescript
interface ChartProps {
  data: TrendRecord[];
  title: string;
  metric: string;
}

export function TrendChart({ data, title, metric }: ChartProps) {
  // Component logic
}
```

---

## Design Decisions & Rationale

### 1. Why Stage-Based Pipeline?
**Benefit:** Clear separation of concerns, easy debugging, checkpoint recovery

### 2. Why Parquet Files?
**Benefit:** Columnar storage, efficient compression, fast queries, schema preservation

### 3. Why Static JSON for Frontend?
**Benefit:** No backend latency, perfect caching, CDN-friendly, simplified deployment

### 4. Why Astro Over Next.js?
**Benefit:** Better performance for content-focused sites, zero JS by default

### 5. Why Absolute Imports?
**Benefit:** Prevents import issues when running from different directories

### 6. Why Custom Hooks Over Redux?
**Benefit:** Simpler for this use case, no boilerplate, better TypeScript support

### 7. Why Metadata-Driven Data?
**Benefit:** Reproducibility, versioning, automatic tracking, easier debugging

---

## Error Handling Architecture

### Python Side

**Hierarchy:**
- `ValueError` - Invalid input, configuration issues
- `FileNotFoundError` - Missing files
- `RuntimeError` - API failures, general errors

**Pattern:** Try-Except-Log-Raise
```python
try:
    df = pd.read_parquet(path)
except Exception as e:
    logger.error(f"Failed to load {path}: {e}")
    raise RuntimeError(f"Load failed: {e}") from e
```

### Frontend Side

**Pattern:** Error boundaries + hook-based error handling

**Example:**
```typescript
const { data, error, isLoading } = useGzipJson(url);

if (error) return <ErrorDisplay error={error} />;
if (isLoading) return <LoadingSpinner />;
```

---

## Performance Optimizations

### Python Side
- **Vectorized Operations:** Pandas/Numpy (avoid loops)
- **Parallel Processing:** Thread pools for geocoding
- **Caching:** API response caching (24h TTL)
- **Incremental Processing:** Checkpoint-based recovery

### Frontend Side
- **Code Splitting:** Astro islands architecture
- **Lazy Loading:** Components loaded on demand
- **Gzip Compression:** JSON files compressed
- **Client-Side Caching:** localStorage for data
- **CDN Delivery:** Static assets via CDN

---

## Scalability Considerations

### Current Limitations
- Full datasets loaded into memory
- Sequential geocoding (with parallel workers)
- Single-machine processing

### Future Scalability Options
- **Chunked Processing:** Process large files in batches
- **Distributed Computing:** Dask or Ray for parallel processing
- **Database Migration:** PostGIS for spatial queries
- **API Backend:** FastAPI for dynamic data loading

---

## Security Architecture

### API Key Management
- Environment variables via `.env`
- No hardcoded secrets
- `.env.example` template
- Pre-commit secret scanning (recommended)

### Data Validation
- Input validation at API boundaries
- Parquet schema validation
- Type hints for all public functions

### Error Messages
- No sensitive data in logs
- Sanitized error messages
- Structured logging

---

## Monitoring & Observability

### Logging
- **Location:** `data/logs/`
- **Format:** Timestamped, structured
- **Levels:** DEBUG, INFO, WARNING, ERROR
- **Visual Cues:** Emojis for quick scanning

### Pipeline Tracking
- **Metadata:** `data/metadata.json`
- **Checksums:** Data integrity verification
- **Versions:** Dataset versioning
- **Timestamps:** Processing time tracking

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                            │
│  data.gov.sg API    SingStat API    OneMap API              │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  PYTHON ETL PIPELINE                         │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐    │
│  │ L0  │→│ L1  │→│ L2  │→│ L3  │→│ L4  │→│ L5  │    │
│  │Collect│Process│Features│Export│Analysis│Metrics│    │
│  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘    │
│                                                           │
│  Core Utilities: Config, DataHelpers, Geocoding          │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              JSON EXPORT (prepare_webapp_data.py)           │
│         app/public/data/*.json.gz                           │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                   ASTRO/REACT WEBAPP                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   PAGES                              │   │
│  │  Landing  Dashboard  Analytics (MDX)                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                        ↓                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 COMPONENTS                           │   │
│  │  Charts  Tables  Maps  Filters                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                        ↓                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  HOOKS                               │   │
│  │  useGzipJson  useAnalyticsData  useLeaderboardData   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Architectural Principles

1. **Separation of Concerns:** Clear boundary between data processing and presentation
2. **Single Responsibility:** Each stage/module has one purpose
3. **Metadata-Driven:** All datasets tracked and versioned
4. **Type Safety:** TypeScript (frontend), Python type hints (backend)
5. **Error Resilience:** Comprehensive error handling and retry logic
6. **Performance-First:** Caching, compression, vectorized operations
7. **Developer Experience:** Absolute imports, centralized config, clear patterns
