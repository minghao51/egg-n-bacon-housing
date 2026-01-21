#!/usr/bin/env python3
"""
Test script to verify logging fix works correctly.

This script tests that logging is now properly configured
when data_helpers module is imported.
"""

import sys
import pathlib
import logging
from datetime import datetime

# Add src directory to path
sys.path.append(str(pathlib.Path(__file__).parent.parent / 'src'))

# Setup logging FIRST (before importing data_helpers)
LOG_DIR = pathlib.Path(__file__).parent.parent / 'data' / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / f'test_logging_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

# Configure logging with both file and console handlers
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# NOW import data_helpers (this used to break logging)
from data_helpers import save_parquet
from geocoding import setup_onemap_headers

# Test logging
print("=" * 80)
print("Testing Logging Fix")
print("=" * 80)
print()

logger.info("Test 1: This message should go to BOTH console and file")
print()

# Test that data_helpers logger also works
data_logger = logging.getLogger('data_helpers')
data_logger.info("Test 2: Message from data_helpers logger")

print()
print(f"Checking log file: {log_file.name}")
print("-" * 80)

# Check if file has content
if log_file.exists():
    size = log_file.stat().st_size
    print(f"✅ Log file exists: {size} bytes")

    with open(log_file, 'r') as f:
        content = f.read()

    if content:
        print(f"✅ Log file has content: {len(content)} characters")
        print()
        print("Log file contents:")
        print("-" * 80)
        print(content)
        print("-" * 80)
        print()
        print("✅ LOGGING FIX SUCCESSFUL!")
        print("   Both console and file logging work correctly")
    else:
        print("❌ Log file is empty - fix didn't work")
else:
    print("❌ Log file doesn't exist")

# Cleanup
if log_file.exists():
    log_file.unlink()
    print(f"Cleaned up test file: {log_file.name}")
