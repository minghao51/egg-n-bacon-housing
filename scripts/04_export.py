"""Export script: create platinum layer outputs and webapp data."""

from egg_n_bacon_housing.pipeline import build_pipeline
from egg_n_bacon_housing.utils.logging_config import get_logger, setup_logging_from_env


def main():
    setup_logging_from_env()
    logger = get_logger(__name__)
    logger.info("Starting platinum export...")
    dr = build_pipeline()
    results = dr.execute(
        final_vars=[
            "unified_dataset",
            "dashboard_json",
            "segments_data",
            "interactive_tools_data",
        ]
    )
    logger.info(f"Export complete. Results: {list(results.keys())}")


if __name__ == "__main__":
    main()
