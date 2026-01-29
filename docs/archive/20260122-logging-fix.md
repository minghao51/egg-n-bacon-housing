# Logging Fix Documentation

**Date:** 2026-01-22
**Issue:** Log files appearing empty despite process running successfully
**Status:** ✅ Fixed

## Problem

Log files in `data/logs/` were created but remained empty (0 bytes) even though:
- The geocoding process was running successfully
- Log messages were visible in stderr/stdout
- No errors were reported

## Root Cause

**`logging.basicConfig()` call in `core/data_helpers.py:17` was blocking file logging.**

### Technical Details

1. **`core/data_helpers.py`** imported `logging` and called:
   ```python
   logging.basicConfig(level=logging.INFO)
   ```

2. When **`scripts/geocode_addresses.py`** imported data_helpers:
   ```python
   from data_helpers import save_parquet
   ```

3. The data_helpers module's `basicConfig()` ran **first**, configuring the root logger with only a StreamHandler (console output).

4. When geocode_addresses.py then tried to configure logging:
   ```python
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(levelname)s - %(message)s',
       handlers=[
           logging.FileHandler(log_file),
           logging.StreamHandler(sys.stdout)
       ]
   )
   ```

5. **This call was IGNORED** because `logging.basicConfig()` does nothing if the root logger is already configured.

6. Result: Logs went to console (stderr) but NOT to the file.

## Solution

**Removed `logging.basicConfig()` from `core/data_helpers.py:17`**

### Before
```python
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### After
```python
# Get logger (don't call basicConfig - let the main script configure logging)
logger = logging.getLogger(__name__)
```

## Logging Best Practices

### ✅ DO: In Library/Utility Modules

```python
# In core/my_module.py
import logging

# Just get a logger - don't configure logging
logger = logging.getLogger(__name__)

def my_function():
    logger.info("Message from module")
```

### ✅ DO: In Main Scripts

```python
# In scripts/my_script.py
import logging
import sys

# Configure logging FIRST (before importing other modules)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('my_script.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# NOW import other modules
from core.my_module import my_function
```

### ❌ DON'T: In Library/Utility Modules

```python
# In core/my_module.py
import logging

# NEVER call basicConfig in library modules!
logging.basicConfig(level=logging.INFO)  # ❌ WRONG
```

## Testing

Run the test script to verify the fix:
```bash
uv run python scripts/test_logging_fix.py
```

Expected output:
- Log messages to console (stdout)
- Log messages written to file
- "✅ LOGGING FIX SUCCESSFUL!" message

## Impact on Running Processes

The current geocoding process (PID 54241) will NOT be affected by this fix because:
- It was started with the old code
- Its logging configuration is already set

**To apply the fix:**
1. Let current process complete (~4 hours)
2. Future runs will automatically use the fixed logging
3. No manual intervention needed

## Verification

After the fix, new geocoding runs will have:
- ✅ Console output (stderr/stdout)
- ✅ File logging to `data/logs/geocoding_YYYYMMDD_HHMMSS.log`
- ✅ Progress logs every 200 addresses
- ✅ Heartbeat logs every 60 seconds
- ✅ Checkpoint saves every 500 addresses

## Related Files

- `core/data_helpers.py` - Fixed (removed basicConfig)
- `scripts/geocode_addresses.py` - Main script with proper logging setup
- `scripts/test_logging_fix.py` - Test script to verify fix

## References

- [Python logging.basicConfig() documentation](https://docs.python.org/3/library/logging.html#logging.basicConfig)
- "basicConfig() does nothing if the root logger already has handlers configured"
