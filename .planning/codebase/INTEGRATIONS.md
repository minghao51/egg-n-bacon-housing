# External Integrations

**Analysis Date:** 2026-02-02

## APIs & External Services

**Mapping & Geocoding:**
- OneMap Singapore - Address geocoding and location data
- SDK/Client: requests + custom implementation
- Auth: ONEMAP_EMAIL, ONEMAP_PASSWORD, ONEMAP_TOKEN

**AI/ML Services:**
- Google Gemini AI - LLM integration for data analysis
- SDK/Client: langchain-google-genai 2.0.0
- Auth: GOOGLE_API_KEY

- Jina AI - Neural search and web scraping
- SDK/Client: requests + custom implementation  
- Auth: JINA_AI

**Government Data:**
- Data.gov.sg - Singapore government open data
- SDK/Client: requests + custom implementation
- Auth: API keys from government portal

**Real Estate Data:**
- URA (Urban Redevelopment Authority) - Property transaction data
- SDK/Client: requests + CSV parsing
- Auth: Public datasets with rate limiting

## Data Storage

**Databases:**
- Supabase - Primary database for application data
- Connection: SUPABASE_URL, SUPABASE_KEY
- Client: supabase Python library

**File Storage:**
- AWS S3 - Data lake for parquet files and exports
- Connection: boto3 with AWS credentials
- Client: boto3 library

- Local filesystem - Development and temporary storage

**Caching:**
- Local filesystem caching with cachetools
- API response caching with configurable TTL

## Authentication & Identity

**Auth Provider:**
- Custom implementation using environment variables
- Implementation: API key-based authentication for external services

## Monitoring & Observability

**Error Tracking:**
- Custom error handling in scripts/core/error_handling.py
- No external error tracking service

**Logs:**
- Python logging module with configurable levels
- File-based logging with timestamps

## CI/CD & Deployment

**Hosting:**
- Streamlit Community Cloud (deployment target)
- Local development for pipeline execution

**CI Pipeline:**
- GitHub Actions (implied from git status)
- Manual testing and deployment

## Environment Configuration

**Required env vars:**
- ONEMAP_EMAIL, ONEMAP_PASSWORD, ONEMAP_TOKEN
- GOOGLE_API_KEY
- SUPABASE_URL, SUPABASE_KEY
- JINA_AI

**Secrets location:**
- .env file for development
- Environment variables in production

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

---

*Integration audit: 2026-02-02*
