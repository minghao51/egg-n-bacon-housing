# External Integrations

**Generated**: 2026-02-28

## Data Sources

### data.gov.sg
**Purpose**: Primary source for Singapore property transaction data

**Endpoints Used**:
- HDB resale price indices
- URA private property transactions
- Private residential property price indices

**Authentication**: None required (public API)

**Rate Limits**:
- No strict rate limit
- Polite: 1 request per second

**Usage Locations**:
- `scripts/core/stages/L0_collect.py`
- `scripts/data/download/refresh_external_data.py`

**Data Retrieved**:
- Monthly HDB resale transactions
- Quarterly URA rental contracts
- Price indices by property type

---

## Geocoding Services

### OneMap API (Primary)
**Purpose**: Singapore address geocoding (official government service)

**Base URL**: `https://www.onemap.gov.sg/apis`

**Authentication**:
- Email-based token generation
- Auto-refresh on 401/403 responses
- Token expiry: ~3 days

**Endpoints**:
- `/api/auth/POST/GETTOKEN` - Generate JWT token
- `/api/common/elastic/search` - Address search and geocoding

**Rate Limiting**:
- **Delay**: 1.2 seconds between requests
- **Retry**: Exponential backoff on failures
- **Circuit Breaking**: Skip address after 3 failed attempts

**Implementation**:
- `scripts/core/geocoding.py` - `geocode_address_onemap()`
- `scripts/utils/refresh_onemap_token.py` - Token management

**Error Handling**:
- Fallback to Google Maps if OneMap fails
- Automatic token refresh on authentication errors
- Logged failures for debugging

### Google Maps API (Fallback)
**Purpose**: Geocoding when OneMap fails

**Base URL**: `https://maps.googleapis.com/maps/api/geocode/json`

**Authentication**: API key from environment variable `GOOGLE_API_KEY`

**Rate Limits**:
- Standard Google API quotas
- Used sparingly (only as fallback)

**Usage Locations**:
- `scripts/core/geocoding.py` - `geocode_address_google()`

**Cost Considerations**:
- Pay-per-use pricing
- Minimize usage by preferring OneMap first

---

## Singapore Government APIs

### SingStat API
**Purpose**: Macroeconomic indicators for housing market analysis

**Data Retrieved**:
- **CPI** (Consumer Price Index) - Inflation adjustment
- **GDP** - Economic growth indicators
- **Unemployment Rate** - Labor market health
- **SORA/SIBOR** - Interest rate trends
- **Producer Price Index** - Construction cost trends

**Authentication**: None required (public API)

**Usage Locations**:
- `scripts/data/fetch_macro_data.py`
- `scripts/core/stages/L0_macro.py`

**Integration Points**:
- Feature engineering for price prediction models
- Economic indicators in causal analysis
- Time series forecasting

---

## Web Scraping

### Jina AI Reader
**Purpose**: AI-powered web content extraction

**Base URL**: `https://r.jina.ai/`

**Usage**: Extract clean text from web pages

**Authentication**: None (free tier)

**Usage Locations**:
- `notebooks/L0_webscrap_jina.py`
- `scripts/data/download/scrape_ura_rental_stats.py`

**Benefits**:
- Removes ads, navigation, clutter
- Extracts main content
- Handles dynamic pages

---

## Cloud Services

### AWS S3 (Optional)
**Purpose**: Cloud storage for data backup/archiving

**SDK**: `boto3`

**Environment Variables**:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_S3_BUCKET`

**Usage Locations**:
- Data upload/download utilities
- Backup/restore scripts

**Status**: Optional - not required for core functionality

### Supabase (Optional)
**Purpose**: Database and authentication (future features)

**SDK**: `supabase` Python client

**Environment Variables**:
- `SUPABASE_URL`
- `SUPABASE_KEY`

**Status**: Optional - experimental integration

---

## Internal Data Pipelines

### Parquet Data Store
**Purpose**: Primary storage for processed datasets

**Location**: `data/parquets/`

**Format**: Apache Parquet with metadata tracking

**Management**:
- `scripts/core/data_helpers.py` - `load_parquet()`, `save_parquet()`
- `data/metadata.json` - Dataset registry

**Data Flow**:
```
L0 (raw) → L1 (cleaned) → L2 (features) → L3 (unified) → L4 (analytics) → L5 (metrics)
```

### Metadata Tracking
**File**: `data/metadata.json`

**Structure**:
```json
{
  "datasets": {
    "dataset_name": {
      "path": "data/parquets/file.parquet",
      "rows": 1000000,
      "source": "data.gov.sg",
      "last_updated": "2026-02-28T00:00:00",
      "description": "Human-readable description"
    }
  }
}
```

**Usage**:
- Automatic updates via `save_parquet()`
- Query via `load_parquet()`
- Validation and error checking

---

## API Rate Limiting Strategy

### OneMap
- **Delay**: 1.2 seconds between requests
- **Implementation**: `time.sleep(1.2)` in geocoding loop
- **Reason**: Respectful usage, avoid blocking

### Google Maps
- **Usage**: Fallback only
- **Delay**: 2 seconds between requests (conservative)
- **Reason**: Minimize API costs

### data.gov.sg
- **Delay**: 1 second between requests
- **Reason**: Polite usage

### Retry Logic
```python
# Exponential backoff pattern
for attempt in range(max_retries):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response
    except Exception as e:
        wait_time = 2 ** attempt
        time.sleep(wait_time)
```

---

## Authentication Management

### Environment Variables
**File**: `.env` (not in git)

**Required Variables**:
```bash
ONEMAP_EMAIL=your@email.com
GOOGLE_API_KEY=your_api_key_here
```

**Optional Variables**:
```bash
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_REGION=us-east-1
SUPABASE_URL=xxx
SUPABASE_KEY=xxx
```

### Configuration Loading
**File**: `scripts/core/config.py`

**Pattern**:
```python
import os
from dotenv import load_dotenv

load_dotenv()

ONEMAP_EMAIL = os.getenv("ONEMAP_EMAIL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def validate():
    """Check required environment variables."""
    if not ONEMAP_EMAIL:
        raise ValueError("ONEMAP_EMAIL not set")
```

---

## Error Handling & Fallbacks

### Geocoding Fallback Chain
1. **OneMap** (primary) - Fast, free, Singapore-specific
2. **Google Maps** (fallback) - More comprehensive, costs money
3. **Skip** - After 3 failed attempts, log and continue

### API Failure Handling
```python
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
except requests.Timeout:
    logger.warning(f"Timeout: {url}")
    return None
except requests.HTTPError as e:
    logger.error(f"HTTP {e.response.status_code}: {url}")
    return None
```

### Circuit Breaking
- **Skip after N failures**: Avoid infinite retries
- **Log failures**: Track problematic addresses
- **Continue processing**: Don't let one failure stop entire pipeline

---

## Caching Strategy

### API Response Caching
**TTL**: 24 hours (default)

**Implementation**: File-based caching in `data/cache/`

**Benefits**:
- Reduce API calls
- Faster development iteration
- Cost savings (Google Maps)

**Cache Key**: Hash of request parameters

---

## Security Considerations

### Secrets Management
- **Never commit** `.env` file
- **Use** `.env.example` as template
- **Rotate** API keys regularly
- **Monitor** usage for suspicious activity

### API Key Protection
- **Loaded** from environment variables
- **Never** hardcoded in source
- **Validation** on startup via `Config.validate()`

---

## Monitoring & Logging

### API Call Logging
```python
logger.info(f"Geocoding address: {address}")
logger.warning(f"OneMap failed, trying Google")
logger.error(f"Failed to geocode after 3 attempts: {address}")
```

### Success Metrics
- Geocoding success rate
- API response times
- Cache hit rate
- Fallback usage frequency

---

## Integration Risks

### OneMap API
- **Risk**: Token expiry, service downtime
- **Mitigation**: Auto-refresh, Google fallback

### Google Maps API
- **Risk**: Cost overruns, quota exceeded
- **Mitigation**: Use as fallback only, monitor usage

### data.gov.sg
- **Risk**: API changes, data format changes
- **Mitigation**: Validation, error handling, manual checks

---

## Future Integrations (Planned)

- **PropertyGuru** - Private property listings
- **EdgeProp** - Market news and insights
- **SRX Property** - Real-time transaction data
- **URA Master Plan** - Future land use data
- **LTA DataMall** - Transport data enhancements

---

## Summary

| Service | Purpose | Auth | Rate Limit | Fallback |
|---------|---------|------|------------|----------|
| data.gov.sg | Property transactions | None | 1 req/sec | - |
| OneMap | Geocoding | Email token | 1.2s delay | Google Maps |
| Google Maps | Geocoding fallback | API key | 2 sec delay | Skip |
| SingStat | Macro data | None | 1 req/sec | - |
| Jina AI | Web scraping | None | Free tier | - |
| AWS S3 | Cloud storage | API keys | Boto3 | Local storage |
| Supabase | Database | API keys | TBD | - |
