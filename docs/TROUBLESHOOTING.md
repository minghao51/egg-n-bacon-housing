# Troubleshooting Guide

Solutions to common issues when working with the Egg-n-Bacon-Housing project.

---

## Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| Can't import scripts | Run from project root with `uv run` |
| Tests fail locally | Run `uv sync` to update dependencies |
| Geocoding returns `None` | Check OneMap credentials in `.env` |
| Pipeline stage fails | Run prerequisite stages first |
| API rate limit error | Wait or check API quota |

---

## Common Errors

### ModuleNotFoundError: No module named 'scripts'

**Symptom:**
```
ModuleNotFoundError: No module named 'scripts'
```

**Cause:** Running Python from wrong directory or without `uv run`

**Solution:**
```bash
# Always run from project root
cd /path/to/egg-n-bacon-housing

# Always use uv run
uv run python scripts/run_pipeline.py --stage all
```

**Prevention:** Never use `python` or `python3` directly - always use `uv run python`

---

### Dataset 'X' not found

**Symptom:**
```
ValueError: Dataset 'L2_hdb_with_features' not found. Available: ['L0_hdb_resale']
```

**Cause:** Trying to load a dataset that hasn't been created yet

**Solution:**
```bash
# Run preceding pipeline stages first
uv run python scripts/run_pipeline.py --stage L0    # Raw data
uv run python scripts/run_pipeline.py --stage L1    # Processing
uv run python scripts/run_pipeline.py --stage L2    # Features
```

**Check available datasets:**
```python
from scripts.core.data_helpers import list_datasets
print(list_datasets())
```

---

### 429 Too Many Requests

**Symptom:**
```
HTTPError: 429 Client Error: Too Many Requests
```

**Cause:** Hitting API rate limits (OneMap or data.gov.sg)

**Solution:**
- Wait 15-30 minutes before retrying
- Check if you're running multiple pipeline instances
- Built-in delays should prevent this under normal use

**Prevention:**
- Use cached data when possible
- Don't run parallel geocoding with too many workers (>10)

---

### Geocoding Fails (All Addresses Return None)

**Symptom:**
```
All geocoded addresses are None or empty
```

**Cause:** Invalid OneMap credentials or expired token

**Solution:**
```bash
# Check .env file has correct credentials
cat .env | grep ONEMAP

# Should see:
# ONEMAP_EMAIL=your_email@example.com
# ONEMAP_EMAIL_PASSWORD=your_password
```

**Refresh token manually:**
```bash
uv run python scripts/utils/refresh_onemap_token.py
```

**Verify OneMap account:**
1. Log in to https://www.onemap.gov.sg/apidocs
2. Check account is active
3. Regenerate password if needed

---

### Tests Pass in CI but Fail Locally

**Symptom:** Tests pass on GitHub Actions but fail on your machine

**Cause:** Outdated dependencies or different environment

**Solution:**
```bash
# Update all dependencies
uv sync --upgrade

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +

# Run tests again
uv run pytest
```

**Check Python version:**
```bash
# Must be Python 3.11+
uv run python --version
```

---

### MemoryError When Loading Large Datasets

**Symptom:**
```
MemoryError: Unable to allocate array
```

**Cause:** Loading large parquet files exceeds available RAM

**Solution:**
```python
# Load in chunks
import pandas as pd

# Read only needed columns
df = pd.read_parquet('data/parquets/L2/L2_hdb_with_features.parquet',
                     columns=['town', 'resale_price', 'floor_area_sqm'])

# Or filter rows
df = pd.read_parquet('data/parquets/L2/L2_hdb_with_features.parquet',
                     filters=[('town', 'in', ['BISHAN', 'TOA PAYOH'])])
```

**Prevention:** Close Jupyter notebooks when not in use, restart kernel periodically

---

### OneMap Token Expiry During Pipeline

**Symptom:**
```
HTTPError: 401 Unauthorized - Token expired
```

**Cause:** OneMap token expires after ~3 days

**Solution:** The pipeline should auto-refresh, but if it fails:

```bash
# Manual token refresh
uv run python scripts/utils/refresh_onemap_token.py

# Resume pipeline
uv run python scripts/run_pipeline.py --stage L1
```

---

### Jupyter Notebook Can't Find Modules

**Symptom:**
```
ModuleNotFoundError: No module named 'scripts.core'
```

**Cause:** Jupyter kernel using wrong Python environment

**Solution:**
```bash
# Restart Jupyter with correct environment
uv run jupyter notebook

# Or register kernel manually
uv run python -m ipykernel install --user --name=egg-n-bacon
```

Then select the `egg-n-bacon` kernel in Jupyter.

---

## Data Issues

### Empty Dataset After Pipeline Run

**Symptom:** Pipeline completes but dataset is empty

**Cause:** API returned no data or filters too restrictive

**Solution:**
```python
# Check dataset size
from scripts.core.data_helpers import load_parquet
df = load_parquet("L2_hdb_with_features")
print(f"Rows: {len(df)}")

# Check logs for errors
tail -f data/logs/pipeline.log
```

**Check API status:**
- https://data.gov.sg - Should be accessible
- https://www.onemap.gov.sg - Should be accessible

---

### Duplicate Records in Dataset

**Symptom:** Same transaction appears multiple times

**Cause:** Running pipeline multiple times without clearing old data

**Solution:**
```bash
# Remove old parquet files
rm -rf data/parquets/L1/*.parquet

# Re-run pipeline
uv run python scripts/run_pipeline.py --stage L1
```

**Prevention:** Pipeline should handle duplicates automatically - check if deduplication logic is working

---

### Inconsistent Coordinates After Geocoding

**Symptom:** Same address has different coordinates across runs

**Cause:** OneMap API returning different results, cached data mixed with fresh results

**Solution:**
```bash
# Clear geocoding cache
rm -rf data/cache/geocoding_cache.*

# Re-geocode
uv run python scripts/data/process/geocode/geocode_addresses.py --parallel
```

---

## Performance Issues

### Pipeline Runs Slowly

**Symptom:** L1 stage takes hours

**Cause:** Sequential geocoding or not using parallel processing

**Solution:**
```bash
# Use parallel geocoding (10-20 workers recommended)
uv run python scripts/run_pipeline.py --stage L1 --parallel --workers 10
```

**Check if parallel is working:**
```bash
# Should see multiple CPU cores utilized
top -pid $(pgrep -f "geocode_addresses.py")
```

---

### High Memory Usage During Parallel Processing

**Symptom:** System swap increases, performance degrades

**Cause:** Too many workers for available RAM

**Solution:**
```bash
# Reduce worker count
uv run python scripts/run_pipeline.py --stage L1 --parallel --workers 5

# Or disable parallel for low-memory systems
uv run python scripts/run_pipeline.py --stage L1
```

**Rule of thumb:** Use `max(1, RAM_GB / 2)` workers

---

## Getting More Help

### Debug Mode

Enable verbose logging:

```bash
# Set environment variable
export VERBOSE_LOGGING=true

# Run pipeline
uv run python scripts/run_pipeline.py --stage L1
```

### Check Logs

```bash
# Pipeline logs
tail -f data/logs/pipeline.log

# Error logs
grep ERROR data/logs/pipeline.log | tail -50

# Geocoding logs
tail -f data/logs/geocoding.log
```

### Data Quality Report

```bash
# Check data quality metrics
uv run python scripts/utils/data_quality_report.py --summary
```

### Still Stuck?

1. **Search existing issues:** Check [GitHub Issues](https://github.com/your-org/egg-n-bacon-housing/issues)
2. **Read docs:** Start at [Documentation Hub](README.md)
3. **Ask for help:** Open a GitHub issue with:
   - Error message (full traceback)
   - Steps to reproduce
   - Your environment (OS, Python version, uv version)
   - What you've tried already

---

## Prevention Tips

1. **Always run from project root** - Avoids import errors
2. **Always use `uv run`** - Ensures correct environment
3. **Keep dependencies updated** - Run `uv sync --upgrade` monthly
4. **Check `.env` file** - Verify API keys before long runs
5. **Monitor logs during pipeline runs** - Catch issues early
6. **Run tests before committing** - Catch regressions quickly

---

**Last Updated:** 2025-03-10
