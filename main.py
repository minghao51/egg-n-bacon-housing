"""CLI entry point for egg-n-bacon-housing pipeline."""

import argparse

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.pipeline import STAGE_VARS, build_pipeline, run_pipeline
from egg_n_bacon_housing.utils.logging_config import LEVEL_MAP, get_logger, setup_logging


def _log_results(logger, results: dict):
    for name, value in results.items():
        if hasattr(value, "shape"):
            logger.info(f"  {name}: {value.shape}")
        elif isinstance(value, int | float):
            logger.info(f"  {name}: {value}")
        elif isinstance(value, dict):
            logger.info(f"  {name}: {len(value)} keys")


def main():
    parser = argparse.ArgumentParser(
        description="egg-n-bacon-housing: Singapore housing data pipeline"
    )
    parser.add_argument(
        "--stage",
        choices=list(STAGE_VARS),
        default="all",
        help="Pipeline stage to run",
    )
    parser.add_argument(
        "--final-var",
        action="append",
        dest="final_vars",
        help="Specific output variable(s) to compute (overrides --stage)",
    )
    parser.add_argument(
        "--log-level",
        choices=list(LEVEL_MAP),
        default="INFO",
        help="Logging level",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate DAG visualization PNG",
    )

    args = parser.parse_args()
    level = LEVEL_MAP[args.log_level]
    setup_logging(level=level)
    logger = get_logger(__name__)

    logger.info(f"Stage: {args.stage} | Data: {settings.data_dir}")

    dr = build_pipeline(settings)

    if args.visualize:
        logger.info(f"DAG nodes: {len(dr.list_available_variables())}")
        viz_vars = args.final_vars or STAGE_VARS.get(args.stage)
        try:
            dr.visualize_execution(
                final_vars=viz_vars or ["unified_dataset"],
                output_file_path="dag.png",
            )
            logger.info("DAG visualization saved to dag.png")
        except Exception as e:
            logger.warning(f"DAG visualization failed: {e}")

    results = run_pipeline(settings, final_vars=args.final_vars, stage=args.stage, dr=dr)

    logger.info(f"Pipeline complete. Results: {list(results.keys())}")
    _log_results(logger, results)


if __name__ == "__main__":
    main()
