#!/usr/bin/env python3
"""
Example pipeline runner script.

This script demonstrates how to use the extracted pipeline modules
to run data collection and processing tasks programmatically.

Usage:
    uv run python scripts/run_pipeline.py --stage L0
    uv run python scripts/run_pipeline.py --stage L1
    uv run python scripts/run_pipeline.py --stage all

Examples:
    # Run L0 data collection
    python scripts/run_pipeline.py --stage L0

    # Run L1 processing with parallel geocoding
    python scripts/run_pipeline.py --stage L1 --parallel

    # Run all stages
    python scripts/run_pipeline.py --stage all --parallel
"""

import logging
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from src.config import Config
from src.pipeline.L0_collect import run_all_datagovsg_collection
from src.geocoding import (
    setup_onemap_headers,
    load_ura_files,
    extract_unique_addresses,
    fetch_data_parallel,
    batch_geocode_addresses
)
from src.data_helpers import save_parquet, list_datasets

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_L0_collection():
    """Run L0: Data collection from external APIs."""
    logger.info("🚀 Starting L0: Data Collection")

    # Run data.gov.sg collection
    results = run_all_datagovsg_collection()

    logger.info(f"✅ L0 Complete: Collected {len(results)} datasets")
    return results


def run_L1_processing(use_parallel: bool = True):
    """Run L1: Data processing including geocoding."""
    logger.info("🚀 Starting L1: Data Processing")

    # Load URA transaction files
    csv_base_path = Config.DATA_DIR / 'raw_data' / 'csv'
    ec_df, condo_df, residential_df, hdb_df = load_ura_files(csv_base_path)

    # Save individual transaction datasets
    save_parquet(ec_df, "L1_housing_ec_transaction", source="URA CSV data")
    save_parquet(condo_df, "L1_housing_condo_transaction", source="URA CSV data")
    save_parquet(residential_df, "L1_housing_residential_transaction", source="URA CSV data")
    save_parquet(hdb_df, "L1_housing_hdb_transaction", source="data.gov.sg CSV data")

    # Extract unique addresses
    housing_df = extract_unique_addresses(ec_df, condo_df, residential_df, hdb_df)

    logger.info(f"Found {len(housing_df)} unique addresses to geocode")

    # Setup OneMap authentication
    headers = setup_onemap_headers()

    # Geocode addresses
    if use_parallel:
        logger.info("Using parallel geocoding for faster processing")
        addresses = housing_df['NameAddress'].tolist()

        # Use batch geocoding for better performance
        geocoded_df = batch_geocode_addresses(
            addresses,
            headers,
            batch_size=1000,
            checkpoint_interval=500
        )
    else:
        logger.info("Using sequential geocoding")
        # Sequential geocoding (slower)
        import requests
        df_list = []
        failed_searches = []

        for i, search_string in enumerate(housing_df['NameAddress'], 1):
            try:
                from src.geocoding import fetch_data_cached
                _df = fetch_data_cached(search_string, headers)
                _df['NameAddress'] = search_string
                df_list.append(_df)

                if i % 50 == 0:
                    logger.info(f"Progress: {i}/{len(housing_df)} addresses")

            except requests.RequestException:
                failed_searches.append(search_string)
                logger.warning(f"❌ Request failed for {search_string}")

        if df_list:
            geocoded_df = pd.concat(df_list, ignore_index=True)
        else:
            geocoded_df = pd.DataFrame()

    # Save geocoded data
    if not geocoded_df.empty:
        save_parquet(geocoded_df, "L1_geocoded_addresses", source="OneMap API")
        logger.info(f"✅ Saved {len(geocoded_df)} geocoded addresses")
    else:
        logger.error("❌ No geocoded results to save")

    logger.info("✅ L1 Complete")
    return geocoded_df


def run_pipeline(stages: str, use_parallel: bool = True):
    """
    Run the data pipeline.

    Args:
        stages: Which stages to run (L0, L1, or 'all')
        use_parallel: Whether to use parallel processing for geocoding
    """
    logger.info("🥓🥚 Egg-n-Bacon Housing Pipeline Starting")
    logger.info(f"Configuration: stages={stages}, parallel={use_parallel}")

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)

    # Print configuration
    Config.print_config()

    # Run requested stages
    if stages in ['L0', 'all']:
        logger.info("=" * 80)
        run_L0_collection()

    if stages in ['L1', 'all']:
        logger.info("=" * 80)
        run_L1_processing(use_parallel=use_parallel)

    # Summary
    logger.info("=" * 80)
    logger.info("🎉 Pipeline complete!")

    # List all datasets
    datasets = list_datasets()
    logger.info(f"📊 Total datasets: {len(datasets)}")
    for name, info in datasets.items():
        logger.info(f"  - {name}: {info['rows']} rows")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the Egg-n-Bacon Housing data pipeline"
    )
    parser.add_argument(
        '--stage',
        choices=['L0', 'L1', 'all'],
        default='all',
        help='Which pipeline stage to run (default: all)'
    )
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Use parallel processing for geocoding (faster)'
    )
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel processing for geocoding (slower but safer)'
    )

    args = parser.parse_args()

    # Determine whether to use parallel processing
    use_parallel = args.parallel and not args.no_parallel

    # Run pipeline
    try:
        run_pipeline(stages=args.stage, use_parallel=use_parallel)
    except Exception as e:
        logger.exception(f"❌ Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
