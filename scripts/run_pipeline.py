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
from src.pipeline.L1_process import run_full_l1_pipeline, save_failed_addresses
from src.data_helpers import list_datasets

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

    # Run full L1 pipeline using extracted module
    results = run_full_l1_pipeline(
        csv_base_path=Config.DATA_DIR / 'raw_data' / 'csv',
        use_parallel_geocoding=use_parallel
    )

    # Save failed addresses for later retry
    if results.get('failed_addresses'):
        # Note: We only save first 10 in results dict
        # For full list, you'd need to modify the pipeline to return all
        pass

    logger.info("✅ L1 Complete")
    return results


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
