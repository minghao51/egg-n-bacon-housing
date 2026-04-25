"""Ingestion script: fetch raw data into bronze layer."""

from egg_n_bacon_housing.pipeline import build_pipeline
from egg_n_bacon_housing.utils.logging_config import get_logger, setup_logging_from_env


def main():
    setup_logging_from_env()
    logger = get_logger(__name__)
    logger.info("Starting bronze ingestion...")
    dr = build_pipeline()
    results = dr.execute(
        final_vars=[
            "raw_hdb_resale_transactions",
            "raw_condo_transactions",
            "raw_hdb_rental",
            "raw_rental_index",
            "raw_school_directory",
            "raw_shopping_malls",
            "raw_macro_data",
        ]
    )
    logger.info(f"Ingestion complete. Results: {list(results.keys())}")


if __name__ == "__main__":
    main()
