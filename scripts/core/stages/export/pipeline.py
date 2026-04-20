"""L3 pipeline orchestration: run_l3_pipeline and main entry point."""

import logging

import pandas as pd

from scripts.core.config import Config
from scripts.core.data_helpers import save_parquet
from scripts.core.school_features import calculate_school_features, load_schools
from scripts.core.stages.export.base_exporter import (
    load_amenity_features,
    load_condo_transactions,
    load_ec_transactions,
    load_geocoded_properties,
    load_hdb_transactions,
    load_planning_areas,
    load_precomputed_metrics,
    load_rental_yield,
    standardize_condo_data,
    standardize_ec_data,
    standardize_hdb_data,
)
from scripts.core.stages.export.dashboard_exporter import (
    create_lease_decay_stats,
    create_market_summary,
    create_planning_area_metrics,
    create_rental_yield_top_combos,
    create_tier_thresholds_evolution,
    export_to_csv,
    save_precomputed_tables,
    upload_to_s3,
)
from scripts.core.stages.export.metrics_exporter import (
    add_amenity_features,
    add_period_segmentation,
    add_planning_area,
    filter_final_columns,
    merge_precomputed_metrics,
    merge_rental_yield,
    merge_with_geocoding,
)

logger = logging.getLogger(__name__)


def run_l3_pipeline(
    upload_s3: bool = False, export_csv: bool = False, s3_bucket: str | None = None
) -> dict:
    """Run complete L3 unified dataset creation and export pipeline.

    Args:
        upload_s3: Whether to upload unified dataset to S3
        export_csv: Whether to export unified dataset to CSV
        s3_bucket: S3 bucket name (defaults to Config.S3_BUCKET)

    Returns:
        Dictionary with pipeline results
    """
    logger.info("=" * 60)
    logger.info("L3 Unified Dataset Creation Pipeline")
    logger.info("=" * 60)

    results = {}

    # Load data
    hdb_df = load_hdb_transactions()
    condo_df = load_condo_transactions()
    ec_df = load_ec_transactions()
    geo_df = load_geocoded_properties()
    amenity_df = load_amenity_features()
    rental_yield_df = load_rental_yield()
    metrics_df = load_precomputed_metrics()
    planning_areas_gdf = load_planning_areas()

    # Check if we have any data
    if hdb_df.empty and condo_df.empty and ec_df.empty:
        logger.error("No transaction data available. Exiting.")
        return results

    # Standardize data
    standardized_dfs = []

    if not hdb_df.empty:
        hdb_standardized = standardize_hdb_data(hdb_df)
        standardized_dfs.append(hdb_standardized)

    if not condo_df.empty:
        condo_standardized = standardize_condo_data(condo_df)
        standardized_dfs.append(condo_standardized)

    if not ec_df.empty:
        ec_standardized = standardize_ec_data(ec_df)
        standardized_dfs.append(ec_standardized)

    # Combine HDB, Condo, and EC
    combined = pd.concat(standardized_dfs, ignore_index=True)
    logger.info(f"Combined {len(combined):,} total transactions")

    # Merge with geocoding
    combined = merge_with_geocoding(combined, geo_df)

    # Add planning areas
    combined = add_planning_area(combined, planning_areas_gdf)

    # Add amenity features
    combined = add_amenity_features(combined, amenity_df)

    # Merge rental yield
    combined = merge_rental_yield(combined, rental_yield_df)

    # Merge precomputed metrics
    combined = merge_precomputed_metrics(combined, metrics_df)

    # Add period-dependent market segmentation
    combined = add_period_segmentation(combined)

    # Add school distance features
    logger.info("=" * 60)
    logger.info("Adding School Distance Features")
    logger.info("=" * 60)
    try:
        schools_df = load_schools()
        logger.info(f"Loaded {len(schools_df)} schools")

        # Only process properties that have coordinates
        combined_with_coords = combined.dropna(subset=["lat", "lon"])
        if not combined_with_coords.empty:
            combined = calculate_school_features(combined, schools_df)
            logger.info("School features added successfully")
        else:
            logger.warning("No properties with coordinates found, skipping school features")
    except Exception as e:
        logger.warning(f"Failed to add school features: {e}")
        logger.info("Continuing without school features...")

    # Filter to successfully geocoded properties
    if "lat" in combined.columns and "lon" in combined.columns:
        before_count = len(combined)
        combined = combined.dropna(subset=["lat", "lon"])
        after_count = len(combined)
        logger.info(
            f"Filtered to {after_count:,} geocoded properties (removed {before_count - after_count:,} without coordinates)"
        )

    # Select final columns
    final_df = filter_final_columns(combined)

    # Save main unified dataset
    output_path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
    save_parquet(final_df, "L3_housing_unified", source="L3 export pipeline")
    logger.info(f"Saved unified dataset to {output_path}")
    results["unified"] = len(final_df)

    # Create L3 directory for precomputed outputs
    l3_dir = Config.PARQUETS_DIR / "L3"
    l3_dir.mkdir(exist_ok=True)

    # Optional: Upload to S3
    if upload_s3:
        upload_to_s3(final_df, "unified/l3_housing_unified.parquet", bucket=s3_bucket)

    # Optional: Export to CSV
    if export_csv:
        export_to_csv(final_df, "l3_housing_unified.csv")

    # ============================================================================
    # PRECOMPUTE SUMMARY TABLES
    # ============================================================================
    logger.info("=" * 60)
    logger.info("Creating Precomputed Summary Tables")
    logger.info("=" * 60)

    market_summary = create_market_summary(final_df)
    tier_thresholds = create_tier_thresholds_evolution(final_df)
    pa_metrics = create_planning_area_metrics(final_df)
    lease_decay = create_lease_decay_stats(final_df)
    rental_combos = create_rental_yield_top_combos(final_df)

    save_precomputed_tables(
        market_summary, tier_thresholds, pa_metrics, lease_decay, rental_combos, l3_dir
    )

    results["market_summary"] = len(market_summary)
    results["tier_thresholds"] = len(tier_thresholds)
    results["planning_area_metrics"] = len(pa_metrics)
    results["lease_decay_stats"] = len(lease_decay)
    results["rental_yield_combos"] = len(rental_combos)

    logger.info("=" * 60)
    logger.info("Precomputed tables created successfully!")
    logger.info("=" * 60)

    # Print summary
    logger.info("=" * 60)
    logger.info("Dataset Summary")
    logger.info("=" * 60)
    logger.info(f"Total records: {len(final_df):,}")
    logger.info(f"Total columns: {len(final_df.columns)}")
    logger.info(
        f"Date range: {final_df['transaction_date'].min()} to {final_df['transaction_date'].max()}"
    )

    if "property_type" in final_df.columns:
        for ptype, count in final_df["property_type"].value_counts().items():
            logger.info(f"  {ptype}: {count:,} records")

    if "planning_area" in final_df.columns:
        pa_coverage = final_df["planning_area"].notna().sum()
        logger.info(
            f"Planning area coverage: {pa_coverage:,} of {len(final_df):,} ({pa_coverage / len(final_df) * 100:.1f}%)"
        )

    if "price" in final_df.columns:
        logger.info(
            f"Price range: ${final_df['price'].min():,.0f} to ${final_df['price'].max():,.0f}"
        )
        logger.info(f"Median price: ${final_df['price'].median():,.0f}")

    # New feature coverage
    if "rental_yield_pct" in final_df.columns:
        ry_coverage = final_df["rental_yield_pct"].notna().sum()
        logger.info(
            f"Rental yield coverage: {ry_coverage:,} of {len(final_df):,} ({ry_coverage / len(final_df) * 100:.1f}%)"
        )

    amenity_distance_cols = [col for col in final_df.columns if col.startswith("dist_to_nearest_")]
    if amenity_distance_cols:
        logger.info(f"Amenity distance features: {len(amenity_distance_cols)} columns")

    amenity_count_cols = [
        col
        for col in final_df.columns
        if col.endswith("_within_500m")
        or col.endswith("_within_1km")
        or col.endswith("_within_2km")
    ]
    if amenity_count_cols:
        logger.info(f"Amenity count features: {len(amenity_count_cols)} columns")

    metric_cols = [
        col
        for col in final_df.columns
        if col in ["stratified_median_price", "mom_change_pct", "momentum_signal"]
    ]
    if metric_cols:
        logger.info(f"Precomputed metrics: {len(metric_cols)} columns")

    # Precomputed summary tables summary
    logger.info("-" * 60)
    logger.info("Precomputed Summary Tables:")
    if not market_summary.empty:
        logger.info(
            f"  - market_summary: {len(market_summary):,} rows (by property_type/period/tier)"
        )
    if not tier_thresholds.empty:
        logger.info(f"  - tier_thresholds_evolution: {len(tier_thresholds):,} rows")
    if not pa_metrics.empty:
        logger.info(f"  - planning_area_metrics: {len(pa_metrics):,} rows")
    if not lease_decay.empty:
        logger.info(f"  - lease_decay_stats: {len(lease_decay):,} rows")
    if not rental_combos.empty:
        logger.info(f"  - rental_yield_top_combos: {len(rental_combos):,} rows")

    logger.info("=" * 60)
    logger.info("Pipeline completed successfully!")
    logger.info("=" * 60)

    return results


def main():
    """Main entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Run L3 unified dataset creation pipeline")
    parser.add_argument("--upload-s3", action="store_true", help="Upload unified dataset to S3")
    parser.add_argument("--export-csv", action="store_true", help="Export unified dataset to CSV")
    parser.add_argument("--s3-bucket", type=str, help="S3 bucket name")

    args = parser.parse_args()
    run_l3_pipeline(upload_s3=args.upload_s3, export_csv=args.export_csv, s3_bucket=args.s3_bucket)


if __name__ == "__main__":
    main()
