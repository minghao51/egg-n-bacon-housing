#!/usr/bin/env python3
"""
Geocoding runner for property addresses.

This script geocodes property addresses using the OneMap API with support for:
- Sequential processing (slower but simpler)
- Parallel processing (3-5x faster with multiple workers)
- Checkpointing and progress logging
- Graceful shutdown and resume

Usage:
    # Sequential processing (default, safer)
    uv run python scripts/data/process/geocode/geocode_addresses.py

    # Parallel processing (faster)
    uv run python scripts/data/process/geocode/geocode_addresses.py --parallel

    # Specify number of workers (default: 5)
    uv run python scripts/data/process/geocode/geocode_addresses.py --parallel --workers 10

    # Run in background
    nohup uv run python scripts/data/process/geocode/geocode_addresses.py --parallel > /dev/null 2>&1 &

Monitor progress:
    tail -f data/logs/geocoding_*.log
"""

import argparse
import logging
import pathlib
import signal
import sys
from datetime import datetime
from typing import List, Tuple

import pandas as pd

# Add src directory to path
sys.path.append(str(pathlib.Path(__file__).parent.parent.parent / 'src'))

# Import from src
import geocoding
import data_helpers
from config import Config

# Configuration
BATCH_SIZE = 1000              # Process addresses in batches of this size
CHECKPOINT_INTERVAL = 500      # Save checkpoint every N addresses
HEARTBEAT_INTERVAL = 60        # Log heartbeat every N seconds

# Paths
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
CHECKPOINT_DIR = PROJECT_ROOT / 'data' / 'checkpoints'
LOG_DIR = PROJECT_ROOT / 'data' / 'logs'
FAILED_DIR = PROJECT_ROOT / 'data' / 'failed_addresses'

# Create directories
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
FAILED_DIR.mkdir(parents=True, exist_ok=True)

# Global state for graceful shutdown
shutdown_requested = False


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


def geocode_addresses_sequential(addresses_df: pd.DataFrame,
                                 headers: dict,
                                 processed_addresses: set = None) -> Tuple[List[pd.DataFrame], List[str]]:
    """
    Geocode addresses sequentially using OneMap API.

    Args:
        addresses_df: DataFrame with NameAddress column
        headers: OneMap API authentication headers
        processed_addresses: Set of addresses already processed (for resume)

    Returns:
        Tuple of (results, failed_addresses)
    """
    global shutdown_requested

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
    logger.info(f"🚀 Starting sequential geocoding for {total_addresses} unique addresses...")
    logger.info(f"⏱️  Estimated time: {total_addresses * Config.GEOCODING_API_DELAY / 60:.0f}-{total_addresses * Config.GEOCODING_API_DELAY * 2 / 60:.0f} minutes")

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
            _df = geocoding.fetch_data(search_string, headers)
            _df['NameAddress'] = search_string
            df_list.append(_df)
            processed_count += 1

            # Log progress every N addresses
            if processed_count % 200 == 0:
                progress_pct = processed_count / len(addresses_df) * 100
                eta = calculate_eta(start_time, processed_count, len(addresses_df))
                logger.info(f"📊 Progress: {processed_count}/{len(addresses_df)} addresses ({progress_pct:.1f}%) | ETA: {eta}")
                last_heartbeat = datetime.now()

            # Save checkpoint every N addresses
            if processed_count % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(df_list, processed_count // CHECKPOINT_INTERVAL)

        except Exception as e:
            failed_searches.append(search_string)
            logger.error(f"❌ Error for '{search_string}': {type(e).__name__}: {e}")

        # Log heartbeat periodically
        if (datetime.now() - last_heartbeat).total_seconds() > HEARTBEAT_INTERVAL:
            elapsed = datetime.now() - start_time
            logger.info(f"💓 Heartbeat: {processed_count}/{len(addresses_df)} addresses | Elapsed: {elapsed}")
            last_heartbeat = datetime.now()

        # Respect API rate limits
        if i < total_addresses:
            import time
            time.sleep(Config.GEOCODING_API_DELAY)

    logger.info(f"✅ Completed: {len(df_list)}/{total_addresses} successful")

    if failed_searches:
        logger.warning(f"⚠️  Failed to retrieve data for {len(failed_searches)} addresses")

    return df_list, failed_searches


def geocode_addresses_parallel(addresses_df: pd.DataFrame,
                               headers: dict,
                               processed_addresses: set = None,
                               max_workers: int = None) -> Tuple[List[pd.DataFrame], List[str]]:
    """
    Geocode addresses using parallel processing with ThreadPoolExecutor.

    Args:
        addresses_df: DataFrame with NameAddress column
        headers: OneMap API authentication headers
        processed_addresses: Set of addresses already processed (for resume)
        max_workers: Number of parallel workers (default: from Config)

    Returns:
        Tuple of (results, failed_addresses)
    """
    global shutdown_requested

    if max_workers is None:
        max_workers = Config.GEOCODING_MAX_WORKERS

    if processed_addresses is None:
        processed_addresses = set()

    # Filter out already-processed addresses
    if len(processed_addresses) > 0:
        addresses_to_process = addresses_df[~addresses_df['NameAddress'].isin(processed_addresses)]['NameAddress'].tolist()
        total_addresses = len(addresses_df)
        logger.info(f"🔄 Resuming from checkpoint: {len(processed_addresses)} addresses already done")
        logger.info(f"📊 Remaining to process: {len(addresses_to_process)} addresses")
    else:
        addresses_to_process = addresses_df['NameAddress'].tolist()
        total_addresses = len(addresses_df)

    logger.info(f"🚀 Starting parallel geocoding for {len(addresses_to_process)} addresses...")
    logger.info(f"⚙️  Batch size: {BATCH_SIZE}")
    logger.info(f"⚙️  Parallel workers: {max_workers}")
    logger.info(f"⏱️  Estimated time: {len(addresses_to_process) / max_workers * Config.GEOCODING_API_DELAY / 60:.1f} minutes")

    all_results = []
    all_failed = []
    start_time = datetime.now()
    processed_count = len(processed_addresses)
    last_heartbeat = start_time
    batch_number = 0

    # Process in batches
    for i in range(0, len(addresses_to_process), BATCH_SIZE):
        if shutdown_requested:
            logger.warning("🛑 Shutdown requested, stopping geocoding...")
            break

        batch_end = min(i + BATCH_SIZE, len(addresses_to_process))
        batch_addresses = addresses_to_process[i:batch_end]
        batch_number += 1

        logger.info(f"📦 Processing batch {batch_number} ({i+1}-{batch_end} of {len(addresses_to_process)})")

        # Process batch in parallel
        batch_results, batch_failed = geocoding.fetch_data_parallel(
            batch_addresses,
            headers,
            max_workers=max_workers,
            show_progress=True
        )

        all_results.extend(batch_results)
        all_failed.extend(batch_failed)
        processed_count += len(batch_results)

        # Calculate progress
        progress_pct = processed_count / total_addresses * 100
        eta = calculate_eta(start_time, processed_count, total_addresses)

        logger.info(f"✅ Batch {batch_number} complete: {len(batch_results)} successful, {len(batch_failed)} failed")
        logger.info(f"📊 Overall progress: {processed_count}/{total_addresses} ({progress_pct:.1f}%) | ETA: {eta}")

        # Save checkpoint periodically
        if processed_count % CHECKPOINT_INTERVAL == 0:
            save_checkpoint(all_results, batch_number)

        # Log heartbeat periodically
        if (datetime.now() - last_heartbeat).total_seconds() > HEARTBEAT_INTERVAL:
            elapsed = datetime.now() - start_time
            logger.info(f"💓 Heartbeat: {processed_count}/{total_addresses} addresses | Elapsed: {elapsed}")
            last_heartbeat = datetime.now()

    # Final summary
    elapsed_total = datetime.now() - start_time
    logger.info(f"✅ Parallel geocoding complete in {elapsed_total}")
    logger.info(f"   Total: {len(all_results)}/{total_addresses} successful")
    logger.info(f"   Failed: {len(all_failed)}")

    if all_failed:
        logger.warning(f"⚠️  Failed to retrieve data for {len(all_failed)} addresses")

    return all_results, all_failed


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
    data_helpers.save_parquet(df_housing_searched, "L2_housing_unique_full_searched", source="L1 transaction data")
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
    data_helpers.save_parquet(df_housing_searched_selected, "L2_housing_unique_searched", source="L2 housing data")
    logger.info(f"✅ Saved L2_housing_unique_searched.parquet ({len(df_housing_searched_selected)} rows)")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Geocode property addresses using OneMap API",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Use parallel processing (faster, ~3-5x speed improvement)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=Config.GEOCODING_MAX_WORKERS,
        help=f'Number of parallel workers (default: {Config.GEOCODING_MAX_WORKERS})'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=BATCH_SIZE,
        help=f'Batch size for processing (default: {BATCH_SIZE})'
    )

    args = parser.parse_args()

    # Setup logging
    log_mode = "parallel" if args.parallel else "sequential"
    log_file = LOG_DIR / f'geocoding_{log_mode}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    global logger
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info(f"🚀 Starting Address Geocoding Pipeline ({log_mode} mode)")
    logger.info("=" * 80)

    if args.parallel:
        logger.info(f"⚙️  Parallel mode: {args.workers} workers")
    else:
        logger.info("⚙️  Sequential mode")

    try:
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers()

        # Load URA files
        logger.info("📂 Loading URA transaction files...")
        csv_base_path = PROJECT_ROOT / 'data' / 'raw_data' / 'csv'
        ec_df, condo_df, residential_df, hdb_df = geocoding.load_ura_files(csv_base_path)

        # Save individual transaction datasets
        logger.info("💾 Saving transaction datasets...")
        data_helpers.save_parquet(ec_df, "L1_housing_ec_transaction", source="URA CSV data")
        data_helpers.save_parquet(condo_df, "L1_housing_condo_transaction", source="URA CSV data")
        data_helpers.save_parquet(residential_df, "L1_housing_residential_transaction", source="URA CSV data")
        data_helpers.save_parquet(hdb_df, "L1_housing_hdb_transaction", source="data.gov.sg CSV data")

        # Extract unique addresses
        logger.info("🔍 Extracting unique addresses...")
        housing_df = geocoding.extract_unique_addresses(ec_df, condo_df, residential_df, hdb_df)

        # Setup OneMap authentication
        logger.info("🔑 Setting up OneMap authentication...")
        headers = geocoding.setup_onemap_headers()

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
        if args.parallel:
            df_list, failed = geocode_addresses_parallel(
                housing_df, headers, processed_addresses, max_workers=args.workers
            )
        else:
            df_list, failed = geocode_addresses_sequential(
                housing_df, headers, processed_addresses
            )

        # Save checkpoint if shutdown was requested
        if shutdown_requested and df_list:
            save_checkpoint(df_list, 999)  # Use 999 for emergency checkpoint
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
