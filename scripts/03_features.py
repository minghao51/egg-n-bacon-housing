"""Feature engineering script: compute features into gold layer."""
from egg_n_bacon_housing.pipeline import build_pipeline
from egg_n_bacon_housing.utils.logging_config import setup_logging_from_env, get_logger

def main():
    setup_logging_from_env()
    logger = get_logger(__name__)
    logger.info("Starting gold feature engineering...")
    dr = build_pipeline()
    results = dr.execute(final_vars=[
        "rental_yield",
        "features_with_amenities",
        "unified_features",
    ])
    logger.info(f"Feature engineering complete. Results: {list(results.keys())}")

if __name__ == "__main__":
    main()