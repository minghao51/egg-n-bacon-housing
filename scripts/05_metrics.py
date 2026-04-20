"""Metrics script: compute planning area metrics."""
from egg_n_bacon_housing.pipeline import build_pipeline
from egg_n_bacon_housing.utils.logging_config import setup_logging_from_env, get_logger

def main():
    setup_logging_from_env()
    logger = get_logger(__name__)
    logger.info("Starting metrics computation...")
    dr = build_pipeline()
    results = dr.execute(final_vars=[
        "price_metrics_by_area",
        "rental_yield_by_area",
        "affordability_metrics",
        "appreciation_hotspots",
    ])
    logger.info(f"Metrics complete. Results: {list(results.keys())}")

if __name__ == "__main__":
    main()