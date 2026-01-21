#!/usr/bin/env python3
"""
Background geocoding runner for URA transactions.

This script geocodes property addresses using the OneMap API in the background
with checkpointing and progress logging. It can be stopped and resumed safely.

Usage:
    python scripts/geocode_addresses.py
    # Or run in background:
    nohup python scripts/geocode_addresses.py > /dev/null 2>&1 &

Monitor progress:
    tail -f data/logs/geocoding_*.log
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
from data_helpers import save_parquet

# Configuration
PROGRESS_LOG_INTERVAL = 200  # Log progress every N addresses
CHECKPOINT_INTERVAL = 500    # Save checkpoint every N addresses
API_DELAY_SECONDS = 1.0      # Delay between API calls (1.0s = 1 request/second, safer)
HEARTBEAT_INTERVAL = 60      # Log heartbeat every N seconds (for monitoring)

# Paths
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
CHECKPOINT_DIR = PROJECT_ROOT / 'data' / 'checkpoints'
LOG_DIR = PROJECT_ROOT / 'data' / 'logs'
FAILED_DIR = PROJECT_ROOT / 'data' / 'failed_addresses'
CSV_BASE_PATH = PROJECT_ROOT / 'data' / 'raw_data' / 'csv'

# Create directories
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
FAILED_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
log_file = LOG_DIR / f'geocoding_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global state for graceful shutdown
shutdown_requested = False
checkpoint_counter = 0


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.warning(f"⚠️  Shutdown signal received (signal {signum})")
    shutdown_requested = True
    logger.info("Finishing current batch and will save checkpoint...")


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill command
    logger.info("✅ Signal handlers registered (SIGINT, SIGTERM)")


def get_last_checkpoint() -> pathlib.Path | None:
    """
    Find the most recent checkpoint file.

    Returns:
        Path to checkpoint file, or None if no checkpoint exists
    """
    checkpoints = list(CHECKPOINT_DIR.glob('L2_housing_unique_searched_checkpoint_*.parquet'))
    if not checkpoints:
        return None
    return max(checkpoints, key=lambda p: p.stat().st_mtime)


def load_checkpoint(checkpoint_path: pathlib.Path) -> set:
    """
    Load checkpoint and return set of already-processed addresses.

    Args:
        checkpoint_path: Path to checkpoint file

    Returns:
        Set of addresses that have already been processed
    """
    logger.info(f"📂 Loading checkpoint: {checkpoint_path}")
    try:
        df = pd.read_parquet(checkpoint_path)
        processed_addresses = set(df['NameAddress'].unique())
        logger.info(f"✅ Checkpoint loaded: {len(processed_addresses)} addresses already processed")
        return processed_addresses
    except Exception as e:
        logger.error(f"❌ Error loading checkpoint: {e}")
        return set()


def save_checkpoint(df_list: List[pd.DataFrame], batch_number: int):
    """
    Save intermediate results as checkpoint.

    Args:
        df_list: List of DataFrames with geocoding results
        batch_number: Current batch number for filename
    """
    try:
        if not df_list:
            logger.warning("⚠️  No data to save in checkpoint")
            return

        # Concatenate all results
        df_combined = pd.concat(df_list, ignore_index=True)

        # Filter for best result (search_result == 0)
        df_filtered = df_combined[df_combined['search_result'] == 0].reset_index(drop=True)

        # Save checkpoint
        checkpoint_file = CHECKPOINT_DIR / f'L2_housing_unique_searched_checkpoint_{batch_number}.parquet'
        df_filtered.to_parquet(checkpoint_file, index=False)

        logger.info(f"💾 Checkpoint saved: {checkpoint_file}")
        logger.info(f"   Total addresses in checkpoint: {len(df_filtered)}")

    except Exception as e:
        logger.error(f"❌ Error saving checkpoint: {e}")


def calculate_eta(start_time, current_count, total_count):
    """Calculate estimated time remaining."""
    if current_count == 0:
        return "Unknown"

    elapsed = datetime.now() - start_time
    rate = current_count / elapsed.total_seconds()  # addresses per second

    if rate == 0:
        return "Unknown"

    remaining = total_count - current_count
    eta_seconds = remaining / rate

    hours = int(eta_seconds // 3600)
    minutes = int((eta_seconds % 3600) // 60)

    if hours > 0:
        return f"~{hours}h {minutes}m"
    else:
        return f"~{minutes}m"


def geocode_addresses(addresses_df: pd.DataFrame,
                     headers: dict,
                     processed_addresses: set = None) -> List[pd.DataFrame]:
    """
    Geocode all addresses using OneMap API.

    Args:
        addresses_df: DataFrame with NameAddress column
        headers: OneMap API authentication headers
        processed_addresses: Set of addresses already processed (for resume)

    Returns:
        List of DataFrames with geocoding results
    """
    global shutdown_requested, checkpoint_counter

    if processed_addresses is None:
        processed_addresses = set()

    # Filter out already-processed addresses
    if len(processed_addresses) > 0:
        total_to_process = addresses_df[~addresses_df['NameAddress'].isin(processed_addresses)]
        logger.info(f"🔄 Resuming from checkpoint: {len(processed_addresses)} addresses already done")
        logger.info(f"📊 Remaining to process: {len(total_to_process)} addresses")
    else:
        total_to_process = addresses_df

    total_addresses = len(total_to_process)
    logger.info(f"🚀 Starting geocoding for {total_addresses} unique addresses...")
    logger.info(f"⏱️  Estimated time: {total_addresses * API_DELAY_SECONDS / 60:.0f}-{total_addresses * API_DELAY_SECONDS * 2 / 60:.0f} minutes")
    logger.info(f"📝 Progress log interval: every {PROGRESS_LOG_INTERVAL} addresses")
    logger.info(f"💾 Checkpoint interval: every {CHECKPOINT_INTERVAL} addresses")

    df_list = []
    failed_searches = []
    start_time = datetime.now()
    processed_count = len(processed_addresses)
    last_heartbeat = start_time

    for i, (_, row) in enumerate(total_to_process.iterrows(), 1):
        if shutdown_requested:
            logger.warning("🛑 Shutdown requested, stopping geocoding...")
            break

        search_string = row['NameAddress']

        try:
            _df = fetch_data(search_string, headers)
            _df['NameAddress'] = search_string
            df_list.append(_df)
            processed_count += 1

            # Log progress every N addresses
            if processed_count % PROGRESS_LOG_INTERVAL == 0:
                progress_pct = processed_count / len(addresses_df) * 100
                eta = calculate_eta(start_time, processed_count, len(addresses_df))
                logger.info(f"📊 Progress: {processed_count}/{len(addresses_df)} addresses ({progress_pct:.1f}%) | ETA: {eta}")
                last_heartbeat = datetime.now()  # Reset heartbeat on progress log

            # Save checkpoint every N addresses
            if processed_count % CHECKPOINT_INTERVAL == 0:
                checkpoint_counter += 1
                save_checkpoint(df_list, checkpoint_counter)

        except requests.exceptions.Timeout:
            failed_searches.append(search_string)
            logger.error(f"❌ Request timeout for '{search_string}' (address {processed_count + 1})")
        except requests.RequestException as e:
            failed_searches.append(search_string)
            logger.error(f"❌ Request failed for '{search_string}': {e}")
        except Exception as e:
            failed_searches.append(search_string)
            logger.error(f"❌ Unexpected error for '{search_string}': {type(e).__name__}: {e}")

        # Log heartbeat periodically (to detect hung processes)
        if (datetime.now() - last_heartbeat).total_seconds() > HEARTBEAT_INTERVAL:
            elapsed = datetime.now() - start_time
            logger.info(f"💓 Heartbeat: Process {processed_count}/{len(addresses_df)} addresses | Elapsed: {elapsed}")
            last_heartbeat = datetime.now()

        # Respect API rate limits
        if i < total_addresses:  # Don't sleep after last address
            import time
            time.sleep(API_DELAY_SECONDS)

    # Final log
    logger.info(f"✅ Completed geocoding: {len(df_list)}/{total_addresses} successful")

    if failed_searches:
        logger.warning(f"⚠️  Failed to retrieve data for {len(failed_searches)} addresses")
        # Save failed addresses
        failed_file = FAILED_DIR / f'failed_addresses_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        pd.DataFrame({'address': failed_searches}).to_csv(failed_file, index=False)
        logger.info(f"📝 Failed addresses saved to: {failed_file}")

    return df_list


def save_final_results(df_list: List[pd.DataFrame], housing_df: pd.DataFrame):
    """
    Save final geocoding results to parquet files.

    Args:
        df_list: List of DataFrames with geocoding results
        housing_df: Original housing DataFrame with property types
    """
    logger.info("💾 Saving final results...")

    # Concatenate all results
    df_housing_searched = pd.concat(df_list, ignore_index=True)

    # Save full dataset
    save_parquet(df_housing_searched, "L2_housing_unique_full_searched", source="L1 transaction data")
    logger.info(f"✅ Saved L2_housing_unique_full_searched.parquet ({len(df_housing_searched)} rows)")

    # Filter for best result and add property type
    df_housing_searched_selected = df_housing_searched[df_housing_searched['search_result'] == 0].reset_index(drop=True)

    # Merge property type from original housing_df
    df_housing_searched_selected = df_housing_searched_selected.merge(
        housing_df[['NameAddress', 'property_type']],
        on='NameAddress',
        how='left'
    )

    # Save filtered dataset
    save_parquet(df_housing_searched_selected, "L2_housing_unique_searched", source="L2 housing data")
    logger.info(f"✅ Saved L2_housing_unique_searched.parquet ({len(df_housing_searched_selected)} rows)")


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("🚀 Starting URA Address Geocoding Pipeline")
    logger.info("=" * 80)

    try:
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers()

        # Load URA files
        logger.info("📂 Loading URA transaction files...")
        csv_base_path = pathlib.Path(__file__).parent.parent / 'data' / 'raw_data' / 'csv'
        ec_df, condo_df, residential_df, hdb_df = load_ura_files(csv_base_path)

        # Save individual transaction datasets
        logger.info("💾 Saving transaction datasets...")
        from data_helpers import save_parquet
        save_parquet(ec_df, "L1_housing_ec_transaction", source="URA CSV data")
        save_parquet(condo_df, "L1_housing_condo_transaction", source="URA CSV data")
        save_parquet(residential_df, "L1_housing_residential_transaction", source="URA CSV data")
        save_parquet(hdb_df, "L1_housing_hdb_transaction", source="data.gov.sg CSV data")

        # Extract unique addresses
        logger.info("🔍 Extracting unique addresses...")
        housing_df = extract_unique_addresses(ec_df, condo_df, residential_df, hdb_df)

        # Setup OneMap authentication
        logger.info("🔑 Setting up OneMap authentication...")
        headers = setup_onemap_headers()

        # Check for existing checkpoint
        checkpoint_path = get_last_checkpoint()
        processed_addresses = set()

        if checkpoint_path:
            logger.info(f"📂 Found checkpoint: {checkpoint_path}")
            # Auto-resume if in background mode (no TTY)
            if sys.stdin.isatty():
                response = input("Do you want to resume from checkpoint? (y/n): ").strip().lower()
            else:
                logger.info("🔄 Auto-resuming from checkpoint (background mode)...")
                response = 'y'

            if response == 'y':
                processed_addresses = load_checkpoint(checkpoint_path)
            else:
                logger.info("Starting from beginning...")
        else:
            logger.info("No existing checkpoint found. Starting fresh...")

        # Geocode addresses
        df_list = geocode_addresses(housing_df, headers, processed_addresses)

        # Save checkpoint if shutdown was requested
        if shutdown_requested and df_list:
            checkpoint_counter += 1
            save_checkpoint(df_list, checkpoint_counter)
            logger.warning("🛑 Shutdown complete. Progress saved in checkpoint.")
            logger.info("Run script again to resume from checkpoint.")
            return

        # Save final results
        if df_list:
            save_final_results(df_list, housing_df)
            logger.info("=" * 80)
            logger.info("✅ Geocoding pipeline completed successfully!")
            logger.info("=" * 80)
        else:
            logger.error("❌ No geocoding results to save")

    except Exception as e:
        logger.exception(f"💥 Fatal error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
