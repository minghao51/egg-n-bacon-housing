# Geocoding Implementation Summary
**Date:** 2026-01-21
**Last Updated:** 2026-01-22
**Status:** ✅ Batched Implementation Complete

---

## ⚡ IMPORTANT UPDATE: Batched Implementation (2026-01-22)

**A new parallel batched geocoding implementation is now available and RECOMMENDED:**

- **Script:** `scripts/geocode_addresses_batched.py`
- **Speed:** ~5x faster (48 min vs 4-7 hours)
- **Workers:** 5 parallel threads using ThreadPoolExecutor
- **Benefits:**
  - Dramatically faster completion time
  - Same checkpointing and resume capability
  - Better error handling
  - Real-time progress monitoring

**See:** [20260122-geocoding-batched-restart.md](20260122-geocoding-batched-restart.md) for complete details.

**This document** describes the original sequential implementation. Use `geocode_addresses_batched.py` for new runs.

---

## Overview

Implemented a robust background geocoding system for the Singapore Housing Data Pipeline, enabling the processing of 14,369 unique property addresses using the OneMap API with checkpointing, progress monitoring, and graceful shutdown capabilities.

---

## Problem Statement

The L1 URA Transactions processing stage required geocoding 14,369 unique property addresses via the OneMap API. Initial estimates showed this would take **10-33 hours** at conservative API rate limits (5-10 seconds per request).

**Key Challenges:**
1. Long-running process (10-33 hours) prone to interruption
2. No checkpoint/resume capability
3. No progress monitoring during execution
4. Risk of API rate limiting/blocking
5. Manual notebook execution not suitable for production

---

## Solution Implemented

### 1. Shared Geocoding Module (`core/geocoding.py`)

**Purpose:** Extract reusable geocoding functions for use by both notebooks and scripts.

**Key Functions:**
- `setup_onemap_headers()` - JWT token authentication with expiration checking
- `fetch_data(search_string, headers)` - OneMap API call with retry logic (tenacity)
- `load_ura_files(base_path)` - Load all URA/HDB CSV files (1.1M rows total)
- `extract_unique_addresses(...)` - Extract 14,369 unique addresses from transactions

**Benefits:**
- DRY principle - single source of truth
- Testable functions
- Can be imported by notebooks or standalone scripts

### 2. Background Runner Script (`scripts/geocode_addresses.py`)

**Purpose:** Production-ready background geocoding with checkpointing.

**Features:**
- **Checkpointing:** Saves progress every 500 addresses
- **Progress Logging:** Logs every 200 addresses
- **Graceful Shutdown:** Handles SIGINT/SIGTERM, saves checkpoint on exit
- **Auto-Resume:** Detects checkpoints on restart, resumes automatically in background
- **Error Handling:** Logs failed addresses, continues processing
- **Rate Limiting:** Configurable `API_DELAY_SECONDS` (currently 1.0s)

**Configuration:**
```python
PROGRESS_LOG_INTERVAL = 200  # Log every 200 addresses
CHECKPOINT_INTERVAL = 500    # Save checkpoint every 500 addresses
API_DELAY_SECONDS = 1.0      # 1 request/second (safe rate)
```

### 3. Progress Monitor (`scripts/check_geocoding_progress.py`)

**Purpose:** Quick status check without reading full logs.

**Output:**
- Current progress (addresses processed / total)
- Percentage complete
- Estimated time remaining
- Recent errors
- Checkpoint information

**Usage:**
```bash
uv run python scripts/check_geocoding_progress.py
```

### 4. Test Suite (`scripts/test_geocoding_checkpoint.py`)

**Purpose:** Validate checkpoint/resume functionality before full run.

**Test Results (100 addresses):**
- ✅ Checkpoint saving every 50 addresses
- ✅ Progress logging every 25 addresses
- ✅ 98% success rate (98/100 addresses)
- ✅ Checkpoint resume functionality verified
- ✅ Test duration: 8 minutes 43 seconds

---

## Performance Optimizations

### Attempted Speeds

| Delay | Requests/Second | Duration | Result |
|-------|----------------|----------|--------|
| 5.0s (original) | 0.2 req/s | 20 hours | Too slow |
| 0.3s | 3.3 req/s | ~48 min | ❌ Crashed (API blocking) |
| **1.0s (final)** | **1.0 req/s** | **~4-5 hours** | ✅ **Optimal** |

### Key Learnings

**0.3s Delay (Too Fast):**
- Processed 600 addresses in 2 minutes
- Then hung/crashed silently
- Likely triggered OneMap API rate limiting
- Checkpoint bug: saved 0 addresses

**1.0s Delay (Optimal):**
- 5x faster than original (20h → 4-5h)
- No API blocking
- Stable processing
- ~40 addresses/minute throughput

---

## File Structure

```
egg-n-bacon-housing/
├── core/
│   ├── geocoding.py              # NEW: Shared geocoding functions
│   ├── config.py
│   └── data_helpers.py
│
├── scripts/
│   ├── geocode_addresses.py      # NEW: Main background runner
│   ├── check_geocoding_progress.py  # NEW: Progress monitor
│   └── test_geocoding_checkpoint.py  # NEW: Test suite
│
├── data/
│   ├── parquets/
│   │   ├── L1/housing_*.parquet  # L1 transaction datasets (4 files)
│   │   └── L2_housing_unique_searched.parquet  # OUTPUT (geocoded)
│   │
│   ├── checkpoints/
│   │   └── L2_housing_unique_searched_checkpoint_*.parquet
│   │
│   ├── logs/
│   │   └── geocoding_YYYYMMDD_HHMMSS.log
│   │
│   └── failed_addresses/
│       └── failed_addresses_*.csv
│
└── docs/
    └── 20260121-geocoding-implementation.md  # This file
```

---

## Usage Guide

### Starting Geocoding

```bash
# Run in background with output captured
nohup uv run python scripts/geocode_addresses.py > /tmp/geocode_output.log 2>&1 &

# Or run directly and monitor
uv run python scripts/geocode_addresses.py > /tmp/geocode_output.log 2>&1 &
```

### Monitoring Progress

```bash
# Quick status check
uv run python scripts/check_geocoding_progress.py

# View real-time logs
tail -f /tmp/geocode_output.log

# Check if process is running
ps aux | grep geocode_addresses | grep -v grep

# Check checkpoints
ls -lh data/checkpoints/
```

### Stopping Gracefully

```bash
# Find process
ps aux | grep geocode_addresses | grep -v grep

# Send SIGTERM (graceful shutdown, saves checkpoint)
kill <PID>

# Or force kill if needed
kill -9 <PID>
```

### Resuming After Interruption

```bash
# Just restart - it auto-detects checkpoint
uv run python scripts/geocode_addresses.py > /tmp/geocode_output.log 2>&1 &

# In background mode, it auto-resumes without prompting
```

---

## Current Status

### Active Geocoding Job

**Started:** 2026-01-21 20:50
**Process ID:** 31922
**Configuration:** 1.0s delay (1 request/second)
**Progress:** 200/14,369 addresses (1.4%)
**ETA:** ~5 hours
**Status:** ✅ Running smoothly

### Datasets Created

**L1 Transaction Files (Completed):**
- `L1_housing_ec_transaction.parquet` - 17,051 EC transactions
- `L1_housing_condo_transaction.parquet` - 49,052 condo transactions
- `L1_housing_residential_transaction.parquet` - 61,037 residential transactions
- `L1_housing_hdb_transaction.parquet` - 969,748 HDB transactions

**L2 Geocoded Output (In Progress):**
- `L2_housing_unique_searched.parquet` - Expected completion: ~5 hours

---

## Technical Details

### API Rate Limiting Strategy

**OneMap API Constraints:**
- Unknown official rate limit
- Testing showed 0.3s delay (3.3 req/s) triggers blocking
- 1.0s delay (1 req/s) appears safe

**Implemented Protections:**
- Configurable delay between requests
- Exponential backoff retry logic (tenacity library)
- Failed address logging
- Graceful degradation

### Checkpoint System

**Save Format:** Parquet files with geocoded addresses
**Filter:** Only `search_result == 0` (best match)
**Frequency:** Every 500 successful geocodes
**Resume:** Detects checkpoint, filters processed addresses, continues

**Benefits:**
- Survives process crashes
- Survives system shutdowns
- Can be manually stopped and resumed
- No duplicate processing

### Signal Handling

**SIGINT (Ctrl+C):**
- Sets `shutdown_requested = True`
- Finishes current API call
- Saves checkpoint
- Logs "Shutdown complete"
- Exits cleanly

**SIGTERM (kill command):**
- Same graceful shutdown as SIGINT
- Saves progress before exit

---

## Troubleshooting

### Process Stuck/Hung

**Symptoms:**
- No progress updates for >10 minutes
- CPU usage 0%
- Log file not growing

**Diagnosis:**
```bash
# Check process age and CPU
ps -p <PID> -o etime,%cpu,command

# Check latest logs
tail -n 50 /tmp/geocode_output.log

# Check for API errors
grep -i "error\|exception\|failed" /tmp/geocode_output.log
```

**Resolution:**
- Kill process: `kill -9 <PID>`
- Check checkpoints: `ls data/checkpoints/`
- Restart: `uv run python scripts/geocode_addresses.py > /tmp/geocode_output.log 2>&1 &`

### Checkpoint Resume Not Working

**Symptoms:**
- Re-processes already geocoded addresses
- Starts from beginning despite checkpoint existing

**Diagnosis:**
```bash
# Check checkpoint file
uv run python -c "
import pandas as pd
df = pd.read_parquet('data/checkpoints/L2_housing_unique_searched_checkpoint_1.parquet')
print(f'Rows: {len(df)}')
print(df.head())
"
```

**Resolution:**
- If checkpoint is empty (0 rows), delete and restart
- This can happen if process crashes during checkpoint save

### API Rate Limiting

**Symptoms:**
- Many "Request failed" errors
- HTTP 429 status codes
- Progress slows dramatically

**Resolution:**
- Increase `API_DELAY_SECONDS` in `scripts/geocode_addresses.py`
- Current: 1.0s (recommended)
- Conservative: 2.0s or 5.0s
- Restart process

---

## Next Steps

### Immediate (Current Geocoding)

1. Monitor current job for ~5 hours
2. Verify final output created: `L2_housing_unique_searched.parquet`
3. Check failed addresses: `data/failed_addresses/failed_addresses_*.csv`
4. Validate output quality (coordinates present, reasonable success rate)

### Future Enhancements

1. **Batch Geocoding Services**
   - Consider Google Maps API ($5/1000 calls)
   - Cost: ~$70 for all 14K addresses
   - Benefits: Faster, more reliable, higher accuracy
   - Completion time: ~1-2 hours

2. **Parallel Processing**
   - Use `concurrent.futures` or `asyncio`
   - Multiple API keys (if available)
   - Could reduce time by 50-70%
   - Must respect rate limits

3. **Smart Caching**
   - Cache geocoded addresses in `{address: {lat, lon}}` format
   - Reuse across different datasets
   - Avoid redundant API calls

4. **Address Preprocessing**
   - Standardize address formats before geocoding
   - Remove duplicates more aggressively
   - Could reduce total API calls needed

---

## Lessons Learned

### What Worked Well

1. **Modular Design**
   - Extracting shared functions to `core/geocoding.py`
   - Easy to test and reuse
   - Clean separation of concerns

2. **Checkpoint System**
   - Saved us from the 0.3s delay crash
   - Enables safe long-running processes
   - Simple and reliable

3. **Progress Monitoring**
   - Clear visibility into long-running job
   - Easy to estimate completion time
   - Quick debugging when stuck

4. **Testing First**
   - 100-address test caught issues early
   - Validated checkpoint/resume functionality
   - Gave confidence for full run

### What Could Be Improved

1. **Checkpoint Bug**
   - Initial checkpoint saved with 0 addresses when resuming
   - Fixed by deleting bad checkpoints
   - Root cause: Filtering logic when resuming

2. **API Rate Limits Unknown**
   - No official documentation on OneMap limits
   - Had to learn by trial and error
   - 0.3s delay too fast, 1.0s appears safe

3. **Silent Failures**
   - Process can hang without clear error messages
   - Better to have explicit error handling
   - Need more visibility into API responses

---

## References

**Related Documentation:**
- `20260121-pipeline-progress-report.md` - Overall pipeline status
- `20260121-background-geocoding-guide.md` - User guide for geocoding scripts
- `20250120-data-pipeline.md` - Original pipeline architecture

**Code Files:**
- `core/geocoding.py` - Core geocoding functions
- `scripts/geocode_addresses.py` - Main background runner
- `scripts/check_geocoding_progress.py` - Progress monitor
- `scripts/test_geocoding_checkpoint.py` - Test suite

---

**Last Updated:** 2026-01-21 20:55
**Status:** Geocoding in progress (ETA: ~5 hours)
