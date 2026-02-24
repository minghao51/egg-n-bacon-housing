# External Integrations

## Data Sources

### data.gov.sg API
**Purpose:** Primary source for Singapore property transaction data

**Endpoints Used:**
- HDB resale price transactions
- URA private property transactions

**Authentication:** None required (public API)

**Rate Limiting:** No explicit limit, implements pagination

**Usage Location:** `scripts/core/stages/L0_collect.py`

**Response Format:** JSON with pagination support

---

### SingStat API
**Purpose:** Singapore macroeconomic data

**Data Retrieved:**
- Consumer Price Index (CPI)
- GDP
- SORA (Singapore Overnight Rate Average)
- Unemployment rate
- Producer Price Index (PPI)

**Usage Location:** `scripts/data/fetch_macro_data.py`

**Note:** One TODO comment mentions replacing with actual MAS API call

---

## Geocoding Services

### OneMap Singapore API (Primary)
**Purpose:** Singapore-specific address geocoding

**Authentication:**
- Email: `ONEMAP_EMAIL` (required)
- Token: `ONEMAP_TOKEN` (auto-generated from email)
- Password: `ONEMAP_PASSWORD` (optional, for token refresh)

**Rate Limiting:**
- 1.2 second delay between calls (configurable)
- Token expiry: ~3 days (auto-refresh on 401/403)

**Fallback:** Google Maps API

**Usage Location:** `scripts/core/geocoding.py`

**Features:**
- Address to coordinates conversion
- Singapore-specific address formats
- Batch geocoding support

**Error Handling:**
- Automatic token refresh on expiry
- Retry logic with tenacity
- Fallback to Google Maps on failure

---

### Google Maps Geocoding API (Fallback)
**Purpose:** Fallback geocoding when OneMap fails

**Authentication:**
- API Key: `GOOGLE_API_KEY` (required)

**Usage Location:** `scripts/core/geocoding.py`

**Rate Limiting:**
- Implements delay between calls
- Used only when OneMap fails

**Cost:** Free tier limited, paid tier beyond quotas

---

## Cloud Services

### AWS S3 (Optional)
**Purpose:** Cloud storage for data exports

**Library:** boto3==1.0.0

**Configuration:**
- Environment: AWS credentials
- Feature flag: `upload_s3=False` (default disabled)

**Usage Location:** Not actively used in current codebase

**Note:** Configured but no active implementation found

---

## AI/LLM Services

### Google Generative AI (Gemini)
**Purpose:** LLM integration via Langchain

**Library:** langchain-google-genai==2.0.0

**Authentication:**
- API Key: Configured in environment

**Status:** Configured but no active usage found in codebase

**Note:** Available for future features

---

### Jina AI
**Purpose:** Semantic search/encoding (unclear)

**Authentication:**
- API Token: `JINA_AI` in .env.example

**Status:** Available but no active usage found

**Note:** Purpose unclear, may be experimental

---

## Database

### Supabase
**Purpose:** Backend-as-a-Service (database, auth, storage)

**Authentication:**
- URL: `SUPABASE_URL`
- Key: `SUPABASE_KEY`

**Status:** Client configured but no active database operations found

**Usage Location:** Referenced in test fixtures only

**Note:** Available for future user management or data storage

---

## Data Processing Pipeline

### Stage-Based ETL Architecture
**Pattern:** L0 → L1 → L2 → L3 → L4 → L5

**Stages:**
- **L0 (Collection):** Fetch from external APIs
- **L1 (Processing):** Clean and geocode
- **L2 (Features):** Add features (distances, amenities)
- **L3 (Export):** Create unified dataset
- **L4 (Analysis):** ML models, spatial analysis
- **L5 (Metrics):** Dashboard metrics

**Integration Points:**
- Each stage reads from previous stage's Parquet files
- Metadata tracking in `data/metadata.json`
- Checkpoint-based recovery (partial)

---

## Frontend Data Strategy

### Static JSON Files
**Pattern:** Python scripts export JSON, frontend consumes

**Data Location:** `app/public/data/`

**Generation:** `scripts/prepare_webapp_data.py`

**Features:**
- Gzip compression for transfer size
- No runtime API calls
- Pre-computed aggregations

**Caching:**
- Browser cache headers
- Service worker support (potential)
- Versioned filenames (cache busting)

---

## Development & Testing

### pytest Markers
**Test Categories:**
- `@pytest.mark.unit` - Fast, isolated tests
- `@pytest.mark.integration` - Component interaction tests
- `@pytest.mark.slow` - Full pipeline tests
- `@pytest.mark.api` - Tests making API calls

**Mock Strategy:**
- Extensive use of `@patch` for external dependencies
- Mock API responses in unit tests
- Fixture-based test data

---

## Authentication & Security

### API Key Management
**Storage:** Environment variables via `.env` file

**Required Keys:**
- `ONEMAP_EMAIL` - OneMap geocoding
- `ONEMAP_PASSWORD` - Token refresh (optional)
- `GOOGLE_API_KEY` - Geocoding fallback
- `SUPABASE_URL` - Database (optional)
- `SUPABASE_KEY` - Database (optional)
- `JINA_AI` - AI features (optional)
- `GOOGLE_API_KEY` - Gemini (optional)

**Security Practices:**
- `.env` not in git
- `.env.example` provides template
- No hardcoded secrets
- Pre-commit hooks for secret scanning (recommended)

---

## Monitoring & Logging

### Structured Logging
**Format:** Python logging with timestamps

**Output:** `data/logs/` directory

**Log Levels:**
- `logger.debug()` - Detailed debug information
- `logger.info()` - General information (most common)
- `logger.warning()` - Warnings (non-critical)
- `logger.error()` - Errors (exceptions)

**Visual Indicators:**
- ✅ Success/completion
- ⚠️ Warnings
- ❌ Errors
- 🔄 Progress/processing
- 📦 Batch processing

---

## Caching Strategy

### API Response Caching
**TTL:** 24 hours (default, configurable)

**Implementation:** Python decorators

**Cache Location:** File-based or in-memory (based on configuration)

**Cache Invalidation:**
- Time-based (TTL)
- Manual flush available

---

## Error Handling

### Exception Hierarchy
- `ValueError` - Invalid input, configuration issues
- `FileNotFoundError` - Missing files
- `RuntimeError` - API failures, general errors

**Pattern:** Try-Except-Log-Raise
```python
try:
    # Operation
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise RuntimeError(f"Operation failed: {e}") from e
```

**Retry Logic:**
- Tenacity for geocoding (automatic retries)
- No retry for other API calls (TODO)

---

## Known Integrations (Not Currently Used)

### Available but Inactive
- **Langchain components** - Installed but no active implementation
- **Supabase client** - Configured but no database operations
- **Google AI (Gemini)** - SDK available but no direct API calls
- **Jina AI** - Token available but purpose unclear
- **AWS S3** - boto3 installed but upload disabled

### Potential Future Use
- User authentication (Supabase Auth)
- Real-time data updates (Supabase Realtime)
- AI-powered features (Gemini, Langchain)
- Cloud data export (S3)
- Semantic search (Jina AI)

---

## Integration Risks & Mitigations

### Rate Limiting
**Risk:** API rate limits exceeded

**Mitigation:**
- Delays between calls (1.2s for OneMap)
- Token refresh on expiry
- Fallback services (Google Maps)

### API Key Exposure
**Risk:** Keys committed to git

**Mitigation:**
- `.env` in `.gitignore`
- No hardcoded keys
- Pre-commit secret scanning (recommended)

### Token Expiry
**Risk:** OneMap token expires (~3 days)

**Mitigation:**
- Auto-refresh on 401/403
- Email-based re-authentication
- Graceful degradation to Google Maps

### Service Downtime
**Risk:** External APIs unavailable

**Mitigation:**
- Caching reduces dependency
- Fallback services available
- Pipeline can run with cached data

---

## Data Flow Summary

```
External APIs (data.gov.sg, SingStat)
    ↓
L0 Collection (cached)
    ↓
L1 Processing + Geocoding (OneMap → Google fallback)
    ↓
L2 Feature Engineering
    ↓
L3 Unified Dataset → Export to Parquet
    ↓
L4 Analysis (ML, spatial)
    ↓
L5 Metrics
    ↓
JSON Export (prepare_webapp_data.py)
    ↓
Static JSON Files (app/public/data/)
    ↓
Frontend (Astro/React)
```

**Key Principle:** Python scripts process data and export JSON; frontend only reads JSON files (no backend API).
