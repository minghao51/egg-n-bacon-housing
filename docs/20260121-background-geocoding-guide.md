# Background Geocoding Guide
**Date:** 2026-01-21
**Last Updated:** 2026-01-22
**Purpose:** Run long-running OneMap geocoding in the background with monitoring

---

## ⚡ RECOMMENDED: Use Batched Geocoding (v0.3.0+)

**As of 2026-01-22, there is a faster batched geocoding script available:**

```bash
# Use this instead (5x faster, ~48 minutes vs 4-7 hours)
nohup uv run python scripts/geocode_addresses_batched.py > /dev/null 2>&1 &
```

**Benefits:**
- ✅ **5 parallel workers** instead of sequential processing
- ✅ **~48 minutes** vs 4-7 hours (old approach)
- ✅ Same checkpointing and resume capability
- ✅ Better error handling and monitoring

**See:** [20260122-geocoding-batched-restart.md](20260122-geocoding-batched-restart.md) for full details.

---

## Overview

The OneMap API has rate limits that make geocoding 14,369 addresses take considerable time. This guide shows how to run the geocoding process in the background with automatic checkpointing and progress monitoring.

**Note:** This guide describes the original sequential approach. For new installations, use the batched version above.

**Key Features:**
- ✅ Runs in background (doesn't block your terminal)
- ✅ Saves checkpoint every 500 addresses
- ✅ Logs progress every 200 addresses
- ✅ Resumes from checkpoint if interrupted
- ✅ Graceful shutdown on Ctrl+C
- ✅ Quick progress monitoring

---

## Quick Start

### 1. Start Geocoding in Background

```bash
# Option 1: Run with nohup (recommended)
nohup uv run python scripts/geocode_addresses.py > /dev/null 2>&1 &

# Option 2: Run in background
uv run python scripts/geocode_addresses.py > /dev/null 2>&1 &

# Option 3: Run in screen/tmux (interactive)
screen -S geocoding
uv run python scripts/geocode_addresses.py
# Press Ctrl+A, D to detach
```

### 2. Monitor Progress

```bash
# Quick status check
uv run python scripts/check_geocoding_progress.py

# Follow real-time logs
tail -f data/logs/geocoding_*.log

# Check recent progress
grep "Progress:" data/logs/geocoding_*.log | tail -n 5
```

### 3. Stop Gracefully (if needed)

```bash
# Find process ID
ps aux | grep geocode_addresses

# Send shutdown signal (will save checkpoint first)
kill <PID>

# Or if in screen session
screen -r geocoding
# Press Ctrl+C
```

---

## Files Created

### Source Code

**`src/geocoding.py`** - Shared geocoding functions
- `setup_onemap_headers()` - Authentication
- `fetch_data()` - API call with retry
- `load_ura_files()` - Load CSV files
- `extract_unique_addresses()` - Get unique addresses

**`scripts/geocode_addresses.py`** - Background runner
- Main geocoding script
- Checkpoint every 500 addresses
- Progress logging every 200 addresses
- Graceful shutdown handling

**`scripts/check_geocoding_progress.py`** - Progress monitor
- Quick status summary
- Shows: progress %, ETA, errors
- Parses latest log file

### Output Files

**Logs:** `data/logs/geocoding_YYYYMMDD_HHMMSS.log`
```
2026-01-21 14:30:22 - INFO - Starting geocoding for 12,166 unique addresses...
2026-01-21 14:52:45 - INFO - Progress: 200/12166 addresses (1.6%) | ETA: ~28 hours
2026-01-21 15:30:15 - INFO - Checkpoint saved: batch 1 (500 addresses)
```

**Checkpoints:** `data/checkpoints/L2_housing_unique_searched_checkpoint_*.parquet`
- Automatic save every 500 successful geocodes
- Used for resume after interruption

**Failed Addresses:** `data/failed_addresses/failed_addresses_*.csv`
- List of addresses that couldn't be geocoded
- Created when geocoding completes or stops

**Final Output:** `data/parquets/L2_housing_unique_searched.parquet`
- Created when all geocoding completes
- Contains all successfully geocoded addresses

---

## Expected Runtime

### Sequential Approach (Legacy `geocode_addresses.py`)

**Estimates based on configuration:**
- **Total addresses:** ~14,369
- **API delay:** 1 second per call (respects rate limits)
- **Estimated time:** 4-7 hours

**Time breakdown:**
- First checkpoint (500 addresses): ~8 minutes
- 1,000 addresses: ~17 minutes
- 5,000 addresses: ~1.4 hours
- All 14,369 addresses: ~4 hours (average)

### Batched Approach (Recommended `geocode_addresses_batched.py`)

**Performance improvements:**
- **Total addresses:** ~14,369
- **Parallel workers:** 5 concurrent threads
- **API delay:** 1 second per call (per worker)
- **Estimated time:** ~48 minutes (5x faster!)

**Time breakdown:**
- First checkpoint (500 addresses): ~2 minutes
- 1,000 addresses: ~3 minutes
- 5,000 addresses: ~17 minutes
- All 14,369 addresses: ~48 minutes

---

## Monitoring Examples

### Check Progress Quickly
```bash
$ uv run python scripts/check_geocoding_progress.py
======================================================================
📊 Geocoding Progress Check
======================================================================
📄 Log file: geocoding_20260121_143022.log
   Last modified: 2026-01-21 15:30:45

📍 Latest Progress:
   Processed: 500 / 12,166 addresses
   Complete: 4.1%

⏱️  Timing:
   Elapsed: 42m 15s
   Rate: 0.20 addresses/second
   ETA: ~15h 23m

💾 Latest Checkpoint:
   File: L2_housing_unique_searched_checkpoint_1.parquet
   Addresses: 500
   Modified: 2026-01-21 15:30:15

✅ No errors reported
```

### Follow Real-Time Logs
```bash
$ tail -f data/logs/geocoding_20260121_143022.log
2026-01-21 15:15:02 - INFO - Progress: 400/12166 addresses (3.3%) | ETA: ~26 hours
2026-01-21 15:30:15 - INFO - Checkpoint saved: batch 1 (500 addresses)
2026-01-21 15:45:30 - INFO - Progress: 600/12166 addresses (4.9%) | ETA: ~24 hours
```

---

## Resume After Interruption

If the script stops (crash, system shutdown, manual stop):

1. **Restart the script:**
   ```bash
   uv run python scripts/geocode_addresses.py
   ```

2. **Script will detect checkpoint:**
   ```
   📂 Found checkpoint: data/checkpoints/L2_housing_unique_searched_checkpoint_1.parquet
   Do you want to resume from checkpoint? (y/n):
   ```

3. **Type `y` to resume:**
   ```
   📂 Loading checkpoint...
   ✅ Checkpoint loaded: 500 addresses already processed
   📊 Remaining to process: 11,666 addresses
   🚀 Starting geocoding for 11,666 unique addresses...
   ```

The script will skip already-processed addresses and continue from where it left off.

---

## Troubleshooting

### Script won't start

**Check:** OneMap credentials in `.env`
```bash
cat .env | grep ONEMAP
```

Should see:
```
ONEMAP_TOKEN=eyJhbGci...
ONEMAP_EMAIL=your@email.com
ONEMAP_EMAIL_PASSWORD=yourpassword
```

### Script crashes immediately

**Check:** Python dependencies
```bash
uv sync
```

**Check:** Log file for error
```bash
tail -n 50 data/logs/geocoding_*.log
```

### Progress seems stuck

**Check:** Process still running
```bash
ps aux | grep geocode_addresses
```

**Check:** Latest log timestamp
```bash
tail -n 5 data/logs/geocoding_*.log
```

If log is >30 minutes old, process may have stopped. Check for errors in log.

### High failure rate

**Check:** Failed addresses file
```bash
cat data/failed_addresses/failed_addresses_*.csv
```

Some failures are normal (invalid addresses, API hiccups). If >20% failing, check:
- OneMap API status: https://www.onemap.gov.sg/
- Your token hasn't expired (valid for 24 hours)

---

## Configuration

**Edit settings in `scripts/geocode_addresses.py`:**

```python
PROGRESS_LOG_INTERVAL = 200  # Log progress every N addresses
CHECKPOINT_INTERVAL = 500    # Save checkpoint every N addresses
API_DELAY_SECONDS = 5        # Delay between API calls
```

**Trade-offs:**
- **Smaller intervals:** More frequent updates, but slower overall (more I/O)
- **Larger intervals:** Faster overall, but less granular progress tracking
- **Current settings (200/500):** Balanced for 10-33 hour runtime

---

## Advanced Usage

### Run in Screen Session

Screen allows you to reattach and see the script's output:

```bash
# Start screen session
screen -S geocoding

# Run script (you'll see all output)
uv run python scripts/geocode_addresses.py

# Detach (Ctrl+A, then D)
# [detached from 5329.geocoding]

# Do other work...

# Reattach later to see progress
screen -r geocoding

# Kill session when done
screen -X -S geocoding quit
```

### Limit to First N Addresses (Testing)

For testing before running full pipeline:

```bash
# Edit scripts/geocode_addresses.py
# In main() function, add limit:
# housing_df = housing_df.head(100)  # Test with 100 addresses

# Then run
uv run python scripts/geocode_addresses.py
```

---

## Next Steps After Geocoding

Once geocoding completes successfully:

1. **Verify output files:**
   ```bash
   ls -lh data/parquets/L2_housing_unique_searched.parquet
   ls -lh data/parquets/L2_housing_unique_full_searched.parquet
   ```

2. **Check for failed addresses:**
   ```bash
   cat data/failed_addresses/failed_addresses_*.csv
   ```

3. **Continue pipeline:**
   - L1 utilities processing (if source files available)
   - L2 sales and facilities feature engineering

4. **Clean up (optional):**
   ```bash
   # Remove checkpoint files (final output saved in parquets/)
   rm data/checkpoints/L2_housing_unique_searched_checkpoint_*.parquet
   ```

---

## Summary

### Batched Approach (Recommended)

**What happens:**
1. Script loads 14,369 unique addresses from URA/HDB CSV files
2. Processes in batches of 1,000 using 5 parallel workers
3. Each worker calls OneMap API with 1 second delay between calls
4. Saves checkpoint every 500 addresses (~2 minutes)
5. Logs progress every 200 addresses (~40 seconds)
6. If interrupted, saves current state as checkpoint
7. On restart, auto-resumes from checkpoint (background mode)
8. When complete, saves final parquet files

**What you do:**
1. Start script in background: `nohup uv run python scripts/geocode_addresses_batched.py > /dev/null 2>&1 &`
2. Monitor progress: `tail -f data/logs/geocoding_batched_*.log`
3. Wait ~48 minutes (or until completion)
4. Verify output files created

### Sequential Approach (Legacy)

**What happens:**
1. Script loads 14,369 unique addresses from URA/HDB CSV files
2. Calls OneMap API for each address (1 second delay between calls)
3. Saves checkpoint every 500 addresses (~8 minutes)
4. Logs progress every 200 addresses (~3 minutes)
5. If interrupted, saves current state as checkpoint
6. On restart, offers to resume from checkpoint
7. When complete, saves final parquet files

**What you do:**
1. Start script in background: `nohup uv run python scripts/geocode_addresses.py > /dev/null 2>&1 &`
2. Check progress periodically: `uv run python scripts/check_geocoding_progress.py`
3. Wait 4-7 hours (or until completion)
4. Verify output files created

**What could go wrong:**
- Token expires (valid for 24h) - Script will try to get new one
- API rate limit changes - Check OneMap status page
- System crash/shutdown - Resume from checkpoint (all progress saved)
- Script stops unexpectedly - Check log file for errors

---

**Questions?** Check the main pipeline progress report: `20260121-pipeline-progress-report.md`
