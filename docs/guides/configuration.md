# Configuration Guide

**Last Updated:** 2026-02-28

---

## Overview

This guide covers all aspects of configuring the egg-n-bacon-housing project, including environment variables, feature flags, path configuration, and validation.

---

## Quick Setup

### 1. Create Environment File

```bash
# Copy template
cp .env.example .env

# Edit with your values
nano .env  # or use your preferred editor
```

### 2. Add Required API Keys

```bash
# .env file
ONEMAP_EMAIL=your-email@example.com
GOOGLE_API_KEY=your-google-api-key
```

### 3. Verify Configuration

```bash
uv run python -c "from scripts.core.config import Config; Config.validate(); print('✅ Configuration valid')"
```

---

## Environment Variables

### Required Variables

These variables **must be set** for the project to function:

| Variable | Description | How to Get |
|----------|-------------|------------|
| `ONEMAP_EMAIL` | OneMap API email for Singapore geocoding | Register at [onemap.gov.sg](https://www.onemap.gov.sg/) |
| `GOOGLE_API_KEY` | Google Maps API key (geocoding fallback) | Create at [Google Cloud Console](https://console.cloud.google.com/) |

**Validation:** Both keys are checked by `Config.validate()`

---

### Optional Variables

These variables are optional but enable additional features:

| Variable | Description | Default |
|----------|-------------|---------|
| `ONEMAP_EMAIL_PASSWORD` | OneMap password for auto-token refresh | None (manual token refresh) |
| `ONEMAP_TOKEN` | Pre-generated OneMap JWT token | None (auto-generated if email/password provided) |
| `SUPABASE_URL` | Supabase project URL | None |
| `SUPABASE_KEY` | Supabase API key | None |
| `JINA_AI` | Jina AI API key for embeddings | None |

**Validation:** Not checked by `Config.validate()` - only used if provided

---

### Test-Only Variables

These variables are **only used in CI/CD** and don't need to be set locally:

```bash
# From .github/workflows/test.yml
LOG_LEVEL=DEBUG
```

---

## Feature Flags

Control project behavior using feature flags in `scripts/core/config.py`:

### `USE_CACHING`

**Type:** `bool`
**Default:** `True`
**Purpose:** Enable/disable caching for API calls and expensive operations

**Usage:**
```python
from scripts.core.config import Config

if Config.USE_CACHING:
    # Use cached results
    data = load_from_cache()
else:
    # Always fetch fresh data
    data = fetch_from_api()
```

**When to Disable:**
- Debugging API issues
- Testing with fresh data
- When cache is corrupted

---

### `VERBOSE_LOGGING`

**Type:** `bool`
**Default:** `True`
**Purpose:** Control logging verbosity

**Usage:**
```python
from scripts.core.config import Config
import logging

if Config.VERBOSE_LOGGING:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)
```

**When to Disable:**
- Production deployments
- Reducing log file size
- Performance optimization

---

### `AUTO_ADD_SRC_PATH` (Notebooks)

**Type:** `bool`
**Default:** `True`
**Purpose:** Automatically add scripts directory to Python path in Jupyter notebooks

**Usage:**
```python
# In notebooks
if Config.AUTO_ADD_SRC_PATH:
    import sys
    sys.path.insert(0, str(Config.SCRIPTS_DIR))
```

**When to Disable:**
- Custom path management
- Namespace conflicts

---

## Path Configuration

### Directory Structure

All paths are configured relative to `BASE_DIR` (project root):

```python
from scripts.core.config import Config

# Core directories
Config.BASE_DIR              # /path/to/project
Config.DATA_DIR              # /path/to/project/data
Config.PIPELINE_DIR          # /path/to/project/data/pipeline
Config.PARQUETS_DIR          # /path/to/project/data/pipeline (alias)
Config.MANUAL_DIR            # /path/to/project/data/manual
Config.ANALYTICS_DIR         # /path/to/project/data/analytics
```

### Pipeline Stage Directories

```python
# Data pipeline stages
Config.L0_DIR                # data/pipeline/L0/ (raw data)
Config.L1_DIR                # data/pipeline/L1/ (cleaned)
Config.L2_DIR                # data/pipeline/L2/ (features)
Config.L3_DIR                # data/pipeline/L3/ (metrics)
```

### Manual Data Directories

```python
# Manual data downloads
Config.CSV_DIR               # data/manual/csv/
Config.GEOJSON_DIR           # data/manual/geojsons/
Config.CROSSWALK_DIR         # data/manual/crosswalks/
Config.URA_DIR               # data/manual/csv/ura/
Config.HDB_RESALE_DIR        # data/manual/csv/ResaleFlatPrices/
```

### Cache Directory

```python
Config.CACHE_DIR             # data/cache/
Config.CACHE_DURATION_HOURS  # 24 (TTL for cache)
```

---

## Parquet Settings

### Compression

```python
Config.PARQUET_COMPRESSION    # "snappy"
```

**Options:**
- `"snappy"`: Fast compression (default)
- `"gzip"`: Better compression, slower
- `"brotli"`: Best compression, slowest
- `"zstd"`: Balanced (if available)

**Recommendation:** Use `snappy` for development, `gzip` for production

---

### Index

```python
Config.PARQUET_INDEX         # False
```

**Purpose:** Include DataFrame index in parquet files

**When to Enable:**
- Index has meaningful values
- Need to preserve index on load

**When to Disable (default):**
- Index is just row numbers
- Save disk space

---

### Engine

```python
Config.PARQUET_ENGINE        # "pyarrow"
```

**Options:**
- `"pyarrow"`: Faster, more features (default)
- `"fastparquet"`: Pure Python, slower

**Recommendation:** Always use `pyarrow`

---

## Geocoding Settings

### API Rate Limiting

```python
Config.GEOCODING_API_DELAY   # 1.2 seconds
```

**Purpose:** Delay between API calls to respect rate limits

**Increasing Delay:**
```python
# More conservative rate limiting
Config.GEOCODING_API_DELAY = 2.0
```

**Decreasing Delay:**
```python
# More aggressive (may hit rate limits)
Config.GEOCODING_API_DELAY = 1.0
```

---

### Timeout

```python
Config.GEOCODING_TIMEOUT     # 30 seconds
```

**Purpose:** Request timeout in seconds

**Increase For:**
- Slow networks
- Large batch requests

**Decrease For:**
- Fast failover
- Quick error detection

---

### Parallel Workers

```python
Config.GEOCODING_MAX_WORKERS # 5
```

**Purpose:** Number of parallel geocoding workers

**Increasing:**
- Faster processing (more API calls per second)
- Higher risk of rate limiting

**Decreasing:**
- Slower processing
- More conservative rate limiting

**Recommendation:** Keep at 5 or below to respect API limits

---

## Configuration Validation

### Running Validation

```python
from scripts.core.config import Config

try:
    Config.validate()
    print("✅ Configuration valid")
except ValueError as e:
    print(f"❌ Configuration error: {e}")
```

### What Validation Checks

1. **Required API Keys:**
   ```python
   - ONEMAP_EMAIL is set
   - GOOGLE_API_KEY is set
   ```

2. **Directory Existence:**
   ```python
   - DATA_DIR exists
   ```

3. **Directory Creation:**
   ```python
   - Creates all pipeline stage directories (L0-L3)
   - Creates manual data subdirectories
   - Creates analytics directory
   - Creates cache directory
   ```

### Common Validation Errors

#### Error: Missing required configuration

```
ValueError: Missing required configuration: ['ONEMAP_EMAIL']
```

**Solution:** Set the missing variable in `.env`

---

#### Error: DATA_DIR does not exist

```
ValueError: DATA_DIR does not exist: /path/to/project/data
```

**Solution:**
```bash
mkdir -p data
```

---

## Development vs Production Configuration

### Development Configuration

```bash
# .env (development)
ONEMAP_EMAIL=dev@example.com
GOOGLE_API_KEY=test-key
LOG_LEVEL=DEBUG
USE_CACHING=true
VERBOSE_LOGGING=true
```

**Characteristics:**
- Verbose logging
- Caching enabled
- Test API keys OK

---

### Production Configuration

```bash
# .env (production)
ONEMAP_EMAIL=prod@example.com
GOOGLE_API_KEY=prod-key
LOG_LEVEL=INFO
USE_CACHING=true
VERBOSE_LOGGING=false
```

**Characteristics:**
- Minimal logging
- Caching enabled
- Production API keys required

---

## Configuration Best Practices

### 1. Never Commit `.env`

**Problem:** API keys in version control are security risks

**Solution:**
```bash
# .gitignore
.env
.env.local
.env.*.local
```

---

### 2. Use Environment-Specific Files

```bash
# .env.development
ONEMAP_EMAIL=dev@example.com

# .env.production
ONEMAP_EMAIL=prod@example.com

# Load appropriate file
cp .env.development .env  # or .env.production
```

---

### 3. Document Required Variables

Keep `.env.example` updated with all required variables:

```bash
# .env.example
# Required
ONEMAP_EMAIL=your-email@example.com
GOOGLE_API_KEY=your-google-api-key

# Optional
ONEMAP_EMAIL_PASSWORD=your-password
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
```

---

### 4. Validate Early

```python
# At the start of your script
from scripts.core.config import Config

Config.validate()  # Fail fast if misconfigured
```

---

### 5. Use Type Hints for Config

```python
from scripts.core.config import Config

# Type hints make it clear what type is expected
email: str | None = Config.ONEMAP_EMAIL
delay: float = Config.GEOCODING_API_DELAY
workers: int = Config.GEOCODING_MAX_WORKERS
```

---

## Troubleshooting

### Issue: API Keys Not Loading

**Symptom:** `ONEMAP_EMAIL` is `None` despite being in `.env`

**Solutions:**

1. **Check file location:**
   ```bash
   # .env must be in project root
   ls -la .env
   ```

2. **Verify format:**
   ```bash
   # No spaces around =
   ONEMAP_EMAIL=correct@example.com  # ✅
   ONEMAP_EMAIL = wrong@example.com  # ❌
   ```

3. **Check python-dotenv is installed:**
   ```bash
   uv sync
   ```

---

### Issue: Directories Not Created

**Symptom:** `FileNotFoundError: data/pipeline/L0/`

**Solution:**
```python
from scripts.core.config import Config

Config.validate()  # Creates all directories
```

---

### Issue: Wrong Configuration Loaded

**Symptom:** Changes to `.env` not reflected

**Solutions:**

1. **Restart Python process:**
   ```bash
   # Environment variables loaded at import time
   uv run python script.py
   ```

2. **Check for multiple .env files:**
   ```bash
   # Only one .env should exist
   ls -la .env*
   ```

3. **Clear Python cache:**
   ```bash
   find . -type d -name __pycache__ -exec rm -rf {} +
   ```

---

## Related Documentation

- [External Data Setup](./external-data-setup.md) - API key setup instructions
- [GitHub Secrets Setup](./github-secrets-setup.md) - CI/CD configuration
- [API Reference](../reference/api-reference.md) - Config class API
- [Architecture](../architecture.md) - System design

---

## Summary

| Configuration | Type | Required | Default | Validation |
|---------------|------|----------|---------|------------|
| `ONEMAP_EMAIL` | str | ✅ Yes | None | Checked |
| `GOOGLE_API_KEY` | str | ✅ Yes | None | Checked |
| `ONEMAP_EMAIL_PASSWORD` | str | No | None | Not checked |
| `ONEMAP_TOKEN` | str | No | None | Not checked |
| `SUPABASE_URL` | str | No | None | Not checked |
| `SUPABASE_KEY` | str | No | None | Not checked |
| `JINA_AI` | str | No | None | Not checked |
| `USE_CACHING` | bool | No | True | Not checked |
| `VERBOSE_LOGGING` | bool | No | True | Not checked |
| `GEOCODING_API_DELAY` | float | No | 1.2 | Not checked |
| `GEOCODING_TIMEOUT` | int | No | 30 | Not checked |
| `GEOCODING_MAX_WORKERS` | int | No | 5 | Not checked |

---

**Need Help?**
- Check `.env.example` for required variables
- Run `Config.validate()` to check setup
- Review error messages carefully
- Open an issue for persistent issues
