#!/usr/bin/env python3
"""
Pipeline runner script.

This script orchestrates all data pipeline stages:
- L0: Data collection from external APIs
- L1: Data processing and geocoding
- L2: Feature engineering (rental yields and property features)
- L3: Export and final output
- L5: Metrics calculation at planning area level
- Webapp: Export lightweight JSON for dashboard

Usage:
    uv run python scripts/run_pipeline.py --stage L0
    uv run python scripts/run_pipeline.py --stage L1
    uv run python scripts/run_pipeline.py --stage L2
    uv run python scripts/run_pipeline.py --stage L2_rental
    uv run python scripts/run_pipeline.py --stage L2_features
    uv run python scripts/run_pipeline.py --stage L3
    uv run python scripts/run_pipeline.py --stage L5
    uv run python scripts/run_pipeline.py --stage webapp
    uv run python scripts/run_pipeline.py --stage all

Examples:
    # Run L0 data collection
    python scripts/run_pipeline.py --stage L0

    # Run L1 processing with parallel geocoding
    python scripts/run_pipeline.py --stage L1 --parallel

    # Run L2 features only
    python scripts/run_pipeline.py --stage L2_features

    # Run all stages
    python scripts/run_pipeline.py --stage all --parallel
"""

import logging
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.core.config import Config
from scripts.core.stages.L0_collect import collect_all_datagovsg
from scripts.core.stages.L1_process import run_processing_pipeline, save_failed_addresses
from scripts.core.stages.L2_rental import run_rental_pipeline
from scripts.core.stages.L2_features import run_l2_features_pipeline
from scripts.core.stages.L3_export import run_l3_pipeline
from scripts.core.stages.L5_metrics import run_metrics_pipeline
from scripts.core.stages.webapp_data_preparation import export_dashboard_data
from scripts.core.data_helpers import list_datasets

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_L0_collection():
    """Run L0: Data collection from external APIs."""
    logger.info("🚀 Starting L0: Data Collection")

    # Run data.gov.sg collection
    results = collect_all_datagovsg()

    logger.info(f"✅ L0 Complete: Collected {len(results)} datasets")
    return results


def run_L1_processing(use_parallel: bool = True):
    """Run L1: Data processing including geocoding."""
    logger.info("🚀 Starting L1: Data Processing")

    # Run full L1 pipeline using extracted module
    results = run_processing_pipeline(
        csv_base_path=Config.MANUAL_DIR / "csv", use_parallel_geocoding=use_parallel
    )

    # Save failed addresses for later retry
    if results.get("failed_addresses"):
        # Note: We only save first 10 in results dict
        # For full list, you'd need to modify the pipeline to return all
        pass

    logger.info("✅ L1 Complete")
    return results


def run_L2_rental(force: bool = False):
    """Run L2: Rental yield calculations."""
    logger.info("🚀 Starting L2: Rental Yield Pipeline")

    results = run_rental_pipeline(force=force)

    logger.info("✅ L2 Rental Complete")
    return results


def run_L2_features():
    """Run L2: Property feature engineering."""
    logger.info("🚀 Starting L2: Feature Engineering Pipeline")

    results = run_l2_features_pipeline()

    logger.info("✅ L2 Features Complete")
    return results


def run_L2(force: bool = False):
    """Run L2: All L2 pipelines (rental + features)."""
    logger.info("🚀 Starting L2: Full L2 Pipeline")

    results = {}

    results["rental"] = run_rental_pipeline(force=force)
    results["features"] = run_l2_features_pipeline()

    logger.info("✅ L2 Complete")
    return results


def run_L3(upload_s3: bool = False, export_csv: bool = False):
    """Run L3: Export and final output."""
    logger.info("🚀 Starting L3: Unified Dataset Creation")

    results = run_l3_pipeline(upload_s3=upload_s3, export_csv=export_csv)

    logger.info("✅ L3 Complete")
    return results


def run_L5(skip_affordability: bool = False):
    """Run L5: Metrics calculation at planning area level."""
    logger.info("🚀 Starting L5: Metrics Pipeline")

    results = run_metrics_pipeline(calculate_affordability=not skip_affordability)

    logger.info("✅ L5 Complete")
    return results


def run_webapp():
    """Run Webapp: Export lightweight JSON files for dashboard."""
    logger.info("🚀 Starting Webapp: Data Export")

    export_dashboard_data()

    logger.info("✅ Webapp Export Complete")
    return {"status": "success"}


def run_pipeline(
    stages: str,
    use_parallel: bool = True,
    force: bool = False,
    upload_s3: bool = False,
    export_csv: bool = False,
    skip_affordability: bool = False,
):
    """
    Run the data pipeline.

    Args:
        stages: Which stages to run (L0, L1, L2, L2_rental, L2_features, L3, L5, webapp, or 'all')
        use_parallel: Whether to use parallel processing for geocoding
        force: Force re-download for rental data
        upload_s3: Upload outputs to S3 (L3 only)
        export_csv: Export outputs to CSV (L3 only)
        skip_affordability: Skip affordability calculations in L5 (requires income data)
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
    if stages in ["L0", "all"]:
        logger.info("=" * 80)
        run_L0_collection()

    if stages in ["L1", "all"]:
        logger.info("=" * 80)
        run_L1_processing(use_parallel=use_parallel)

    if stages in ["L2", "all"]:
        logger.info("=" * 80)
        run_L2(force=force)

    if stages == "L2_rental":
        logger.info("=" * 80)
        run_L2_rental(force=force)

    if stages == "L2_features":
        logger.info("=" * 80)
        run_L2_features()

    if stages in ["L3", "all"]:
        logger.info("=" * 80)
        run_L3(upload_s3=upload_s3, export_csv=export_csv)

    if stages in ["L5", "all"]:
        logger.info("=" * 80)
        run_L5(skip_affordability=skip_affordability)

    if stages in ["webapp", "all"]:
        logger.info("=" * 80)
        run_webapp()

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
    parser = argparse.ArgumentParser(description="Run the Egg-n-Bacon Housing data pipeline")
    parser.add_argument(
        "--stage",
        choices=["L0", "L1", "L2", "L2_rental", "L2_features", "L3", "L5", "webapp", "all"],
        default="all",
        help="Which pipeline stage to run (default: all)",
    )
    parser.add_argument(
        "--parallel", action="store_true", help="Use parallel processing for geocoding (faster)"
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel processing for geocoding (slower but safer)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-download of rental data even if fresh"
    )
    parser.add_argument("--upload-s3", action="store_true", help="Upload L3 outputs to S3")
    parser.add_argument("--export-csv", action="store_true", help="Export L3 outputs to CSV")
    parser.add_argument(
        "--skip-affordability",
        action="store_true",
        help="Skip affordability calculations in L5 (no income data required)"
    )

    args = parser.parse_args()

    # Determine whether to use parallel processing
    use_parallel = args.parallel and not args.no_parallel

    # Run pipeline
    try:
        run_pipeline(
            stages=args.stage,
            use_parallel=use_parallel,
            force=args.force,
            upload_s3=args.upload_s3,
            export_csv=args.export_csv,
            skip_affordability=args.skip_affordability,
        )
    except Exception as e:
        logger.exception(f"❌ Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
