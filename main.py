"""CLI entry point for egg-n-bacon-housing pipeline."""

import argparse

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.pipeline import build_pipeline, run_full_pipeline
from egg_n_bacon_housing.utils.logging_config import get_logger, setup_logging_from_env


def main():
    parser = argparse.ArgumentParser(
        description="egg-n-bacon-housing: Singapore housing data pipeline"
    )

    parser.add_argument(
        "--stage",
        choices=["ingest", "clean", "features", "export", "metrics", "all"],
        default="all",
        help="Pipeline stage to run",
    )
    parser.add_argument(
        "--final-var",
        action="append",
        dest="final_vars",
        help="Specific output variable(s) to compute",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate DAG visualization PNG",
    )

    args = parser.parse_args()

    setup_logging_from_env()
    logger = get_logger(__name__)

    stage_vars = {
        "ingest": [
            "raw_hdb_resale_transactions",
            "raw_condo_transactions",
            "raw_hdb_rental",
            "raw_rental_index",
            "raw_school_directory",
            "raw_shopping_malls",
            "raw_macro_data",
        ],
        "clean": [
            "cleaned_hdb_transactions",
            "hdb_validated",
            "cleaned_condo_transactions",
            "condo_validated",
            "geocoded_properties",
            "geocoded_validated",
        ],
        "features": [
            "rental_yield",
            "features_with_amenities",
            "unified_features",
        ],
        "export": [
            "unified_dataset",
            "dashboard_json",
            "segments_data",
            "interactive_tools_data",
        ],
        "metrics": [
            "price_metrics_by_area",
            "rental_yield_by_area",
            "affordability_metrics",
            "appreciation_hotspots",
        ],
        "all": None,
    }

    final_vars = args.final_vars or stage_vars.get(args.stage)

    logger.info(f"Starting pipeline stage: {args.stage}")
    logger.info(f"Data path: {settings.data_dir}")

    if args.visualize:
        dr = build_pipeline()
        logger.info(f"Available nodes: {len(dr.list_available_variables())}")
        try:
            dr.visualize_execution(
                final_vars=final_vars or ["unified_dataset"],
                output_file_path="dag.png",
            )
            logger.info("DAG visualization saved to dag.png")
        except Exception as e:
            logger.warning(f"Could not generate DAG visualization: {e}")

    results = run_full_pipeline(final_vars=final_vars)

    logger.info(f"Pipeline complete. Results: {list(results.keys())}")

    for name, value in results.items():
        if hasattr(value, "shape"):
            logger.info(f"  {name}: {value.shape}")
        elif isinstance(value, (int, float)):
            logger.info(f"  {name}: {value}")
        elif isinstance(value, dict):
            logger.info(f"  {name}: {len(value)} keys")


if __name__ == "__main__":
    main()
