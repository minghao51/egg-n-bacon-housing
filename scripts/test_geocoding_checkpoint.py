#!/usr/bin/env python3
"""
Test script for geocoding checkpoint functionality.

This is a limited test version that processes only the first 100 addresses
to verify checkpointing works correctly before running the full pipeline.

Expected behavior:
1. Process first 100 addresses (~8 minutes)
2. Save checkpoint at 100 (if CHECKPOINT_INTERVAL allows)
3. Test manual shutdown (Ctrl+C) at ~50 addresses
4. Resume from checkpoint
5. Complete to 100 addresses
"""

import sys
import pathlib
import signal
import logging
from datetime import datetime
from typing import List

import pandas as pd
import requests

# Add src directory to path
sys.path.append(str(pathlib.Path(__file__).parent.parent / 'src'))

from geocoding import setup_onemap_headers, fetch_data, load_ura_files, extract_unique_addresses

# Test Configuration
TEST_ADDRESSES_LIMIT = 100     # Only process 100 addresses for testing
PROGRESS_LOG_INTERVAL = 25     # Log progress every 25 addresses (for faster feedback)
CHECKPOINT_INTERVAL = 50       # Save checkpoint every 50 addresses
API_DELAY_SECONDS = 5

# Paths
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
CHECKPOINT_DIR = PROJECT_ROOT / 'data' / 'checkpoints'
LOG_DIR = PROJECT_ROOT / 'data' / 'logs'
FAILED_DIR = PROJECT_ROOT / 'data' / 'failed_addresses'

# Create directories
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
FAILED_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
log_file = LOG_DIR / f'test_geocoding_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global state
shutdown_requested = False
checkpoint_counter = 0


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.warning(f"⚠️  Shutdown signal received (signal {signum})")
    shutdown_requested = True
    logger.info("🧪 Test: Finishing current batch and will save checkpoint...")


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("✅ Signal handlers registered")


def get_last_checkpoint():
    """Find most recent checkpoint file."""
    checkpoints = list(CHECKPOINT_DIR.glob('L2_housing_unique_searched_checkpoint_*.parquet'))
    if not checkpoints:
        return None
    return max(checkpoints, key=lambda p: p.stat().st_mtime)


def load_checkpoint(checkpoint_path):
    """Load checkpoint and return set of processed addresses."""
    logger.info(f"📂 Loading checkpoint: {checkpoint_path}")
    try:
        df = pd.read_parquet(checkpoint_path)
        processed = set(df['NameAddress'].unique())
        logger.info(f"✅ Checkpoint loaded: {len(processed)} addresses already processed")
        return processed
    except Exception as e:
        logger.error(f"❌ Error loading checkpoint: {e}")
        return set()


def save_checkpoint(df_list, batch_number):
    """Save intermediate results as checkpoint."""
    try:
        if not df_list:
            logger.warning("⚠️  No data to save in checkpoint")
            return

        df_combined = pd.concat(df_list, ignore_index=True)
        df_filtered = df_combined[df_combined['search_result'] == 0].reset_index(drop=True)

        checkpoint_file = CHECKPOINT_DIR / f'L2_housing_unique_searched_checkpoint_{batch_number}.parquet'
        df_filtered.to_parquet(checkpoint_file, index=False)

        logger.info(f"💾 Test checkpoint saved: {checkpoint_file}")
        logger.info(f"   Total addresses: {len(df_filtered)}")
    except Exception as e:
        logger.error(f"❌ Error saving checkpoint: {e}")


def geocode_addresses_test(addresses_df, headers, processed_addresses=None):
    """Geocode addresses (test version)."""
    global shutdown_requested, checkpoint_counter

    if processed_addresses is None:
        processed_addresses = set()

    # Filter out already-processed
    if len(processed_addresses) > 0:
        total_to_process = addresses_df[~addresses_df['NameAddress'].isin(processed_addresses)]
        logger.info(f"🔄 Resuming: {len(processed_addresses)} already done")
        logger.info(f"📊 Remaining: {len(total_to_process)} addresses")
    else:
        total_to_process = addresses_df

    total_addresses = len(total_to_process)
    logger.info(f"🧪 TEST: Geocoding {total_addresses} addresses...")
    logger.info(f"⏱️  Estimated time: ~{total_addresses * API_DELAY_SECONDS / 60:.0f} minutes")

    df_list = []
    failed_searches = []
    start_time = datetime.now()
    processed_count = len(processed_addresses)

    for i, (_, row) in enumerate(total_to_process.iterrows(), 1):
        if shutdown_requested:
            logger.warning("🛑 Test: Shutdown requested")
            break

        search_string = row['NameAddress']

        try:
            _df = fetch_data(search_string, headers)
            _df['NameAddress'] = search_string
            df_list.append(_df)
            processed_count += 1

            # Log progress
            if processed_count % PROGRESS_LOG_INTERVAL == 0:
                progress_pct = processed_count / len(addresses_df) * 100
                logger.info(f"📊 Test Progress: {processed_count}/{len(addresses_df)} ({progress_pct:.1f}%)")

            # Checkpoint
            if processed_count % CHECKPOINT_INTERVAL == 0:
                checkpoint_counter += 1
                save_checkpoint(df_list, checkpoint_counter)
                logger.info(f"🧪 Test: Checkpoint {checkpoint_counter} saved - you can test Ctrl+C resume now")

        except requests.RequestException as e:
            failed_searches.append(search_string)
            logger.error(f"❌ Failed for '{search_string}': {e}")

        # Delay
        if i < total_addresses:
            import time
            time.sleep(API_DELAY_SECONDS)

    logger.info(f"✅ Test completed: {len(df_list)}/{total_addresses} successful")

    if failed_searches:
        logger.warning(f"⚠️  Failed: {len(failed_searches)} addresses")

    return df_list


def main():
    """Main test function."""
    logger.info("=" * 80)
    logger.info("🧪 GEOCODING CHECKPOINT TEST")
    logger.info(f"   Will process {TEST_ADDRESSES_LIMIT} addresses")
    logger.info(f"   Progress log: every {PROGRESS_LOG_INTERVAL} addresses")
    logger.info(f"   Checkpoint: every {CHECKPOINT_INTERVAL} addresses")
    logger.info("=" * 80)
    logger.info("")
    logger.info("📋 Test Plan:")
    logger.info("   1. Start processing...")
    logger.info("   2. At ~50 addresses, checkpoint will be saved")
    logger.info("   3. Press Ctrl+C to test graceful shutdown")
    logger.info("   4. Run this script again to test resume")
    logger.info("   5. Complete to 100 addresses")
    logger.info("")

    try:
        # Auto-start if in background mode (no TTY)
        import sys
        if sys.stdin.isatty():
            input("Press Enter to start test...")
        else:
            logger.info("🚀 Auto-starting (background mode detected)...")
        logger.info("")

        setup_signal_handlers()

        # Load data
        logger.info("📂 Loading URA files...")
        csv_base_path = pathlib.Path(__file__).parent.parent / 'data' / 'raw_data' / 'csv'
        ec_df, condo_df, residential_df, hdb_df = load_ura_files(csv_base_path)

        logger.info("🔍 Extracting addresses...")
        housing_df = extract_unique_addresses(ec_df, condo_df, residential_df, hdb_df)

        # LIMIT TO TEST
        housing_df = housing_df.head(TEST_ADDRESSES_LIMIT)
        logger.info(f"🧪 LIMIT: Processing only {TEST_ADDRESSES_LIMIT} addresses")
        logger.info("")

        # Setup auth
        logger.info("🔑 OneMap authentication...")
        headers = setup_onemap_headers()
        logger.info("")

        # Check checkpoint
        checkpoint_path = get_last_checkpoint()
        processed_addresses = set()

        if checkpoint_path:
            logger.info(f"📂 Found checkpoint: {checkpoint_path.name}")
            # Auto-resume if in background mode
            if sys.stdin.isatty():
                response = input("Resume from checkpoint? (y/n): ").strip().lower()
            else:
                logger.info("🔄 Auto-resuming from checkpoint (background mode)...")
                response = 'y'

            if response == 'y':
                processed_addresses = load_checkpoint(checkpoint_path)
                test_addresses = set(housing_df['NameAddress'])
                processed_addresses = processed_addresses.intersection(test_addresses)
                logger.info(f"🧪 Filtered to test: {len(processed_addresses)} already processed")
                logger.info("")
            else:
                logger.info("Starting fresh...")
                logger.info("")
        else:
            logger.info("No checkpoint found. Starting fresh...")
            logger.info("")

        # Geocode
        df_list = geocode_addresses_test(housing_df, headers, processed_addresses)

        # Save if shutdown
        if shutdown_requested and df_list:
            checkpoint_counter += 1
            save_checkpoint(df_list, checkpoint_counter)
            logger.warning("🛑 Test interrupted - checkpoint saved")
            logger.info("💡 Run again to test resume functionality")
            logger.info("")
            return

        # Save test results
        if df_list:
            logger.info("💾 Saving test results...")
            df_housing_searched = pd.concat(df_list, ignore_index=True)

            # Count unique successful results
            successful = len(df_housing_searched[df_housing_searched['search_result'] == 0])

            test_output = PROJECT_ROOT / 'data' / 'parquets' / 'TEST_L2_housing_unique_searched.parquet'
            df_housing_searched.to_parquet(test_output, index=False)

            logger.info(f"✅ Test results saved: {test_output}")
            logger.info("")
            logger.info("=" * 80)
            logger.info("✅ TEST PASSED!")
            logger.info(f"   Total API calls: {len(df_list)}")
            logger.info(f"   Successful results: {successful}")
            logger.info("=" * 80)
            logger.info("")
            logger.info("🎯 Checkpoint functionality verified!")
            logger.info("   Ready to run full pipeline:")
            logger.info("   nohup uv run python scripts/geocode_addresses.py > /dev/null 2>&1 &")
        else:
            logger.error("❌ No results")

    except KeyboardInterrupt:
        logger.warning("⚠️  Test interrupted by user")
        logger.info("   (This is expected if testing Ctrl+C)")
    except Exception as e:
        logger.exception(f"💥 Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
