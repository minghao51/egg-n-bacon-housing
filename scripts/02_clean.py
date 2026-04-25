"""Cleaning script: validate and clean bronze data into silver layer."""

from egg_n_bacon_housing.pipeline import build_pipeline
from egg_n_bacon_housing.utils.logging_config import get_logger, setup_logging_from_env


def main():
    setup_logging_from_env()
    logger = get_logger(__name__)
    logger.info("Starting silver cleaning...")
    dr = build_pipeline()
    results = dr.execute(
        final_vars=[
            "cleaned_hdb_transactions",
            "hdb_validated",
            "cleaned_condo_transactions",
            "condo_validated",
            "cleaned_ec_transactions",
            "ec_validated",
            "geocoded_properties",
            "geocoded_validated",
        ]
    )
    logger.info(f"Cleaning complete. Results: {list(results.keys())}")


if __name__ == "__main__":
    main()
