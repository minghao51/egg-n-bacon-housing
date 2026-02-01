"""L3: Export pipeline.

This module provides functions for:
- Uploading datasets to S3
- Creating final unified datasets
- Exporting data for downstream use
- Running complete L3 export pipeline
"""

import logging
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet, save_parquet, list_datasets

logger = logging.getLogger(__name__)


def load_l3_datasets() -> Dict[str, pd.DataFrame]:
    """Load all L3 datasets for export.

    Returns:
        Dictionary of dataset name to DataFrame
    """
    logger.info("Loading L3 datasets...")

    datasets = {}

    dataset_names = [
        "L3_property",
        "L3_private_property_facilities",
        "L3_property_nearby_facilities",
        "L3_property_transactions_sales",
        "L3_property_listing_sales",
    ]

    for name in dataset_names:
        try:
            df = load_parquet(name)
            datasets[name] = df
            logger.info(f"  Loaded {name}: {len(df):,} records")
        except Exception as e:
            logger.warning(f"  Could not load {name}: {e}")

    return datasets


def create_unified_dataset(
    property_df: pd.DataFrame, transaction_sales: pd.DataFrame, listing_sales: pd.DataFrame
) -> pd.DataFrame:
    """Create unified dataset by joining property with transactions and listings.

    Args:
        property_df: Property table
        transaction_sales: Transaction sales table
        listing_sales: Listing sales table

    Returns:
        Unified DataFrame
    """
    logger.info("Creating unified dataset...")

    property_with_transactions = property_df.merge(
        transaction_sales,
        left_on="property_id",
        right_on="property_index",
        how="left",
        suffixes=("_prop", "_trans"),
    )

    property_with_transactions = property_with_transactions.merge(
        listing_sales,
        left_on="property_id",
        right_on="property_index",
        how="left",
        suffixes=("", "_list"),
    )

    duplicate_cols = [
        c for c in property_with_transactions.columns if c.endswith("_trans") or c.endswith("_list")
    ]
    property_with_transactions = property_with_transactions.drop(
        columns=duplicate_cols, errors="ignore"
    )

    # Add nearest MRT information for properties with lat/lon
    if 'lat' in property_with_transactions.columns and 'lon' in property_with_transactions.columns:
        logger.info("Adding nearest MRT station information...")
        # Import here to avoid circular dependencies
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from mrt_distance import calculate_nearest_mrt

        # Filter to properties with valid coordinates
        has_coords = property_with_transactions['lat'].notna() & property_with_transactions['lon'].notna()

        if has_coords.sum() > 0:
            property_with_coords = property_with_transactions[has_coords].copy()

            # Calculate nearest MRT
            property_with_coords = calculate_nearest_mrt(
                property_with_coords,
                show_progress=True
            )

            # Merge back
            property_with_transactions = pd.concat([
                property_with_coords,
                property_with_transactions[~has_coords]
            ], ignore_index=True)

            logger.info(f"  Added MRT info for {has_coords.sum():,} properties with coordinates")

    logger.info(f"  Created unified dataset with {len(property_with_transactions):,} records")
    return property_with_transactions


def upload_to_s3(df: pd.DataFrame, key: str, bucket: Optional[str] = None) -> bool:
    """Upload DataFrame to S3.

    Args:
        df: DataFrame to upload
        key: S3 key (path)
        bucket: S3 bucket name (defaults to Config.S3_BUCKET)

    Returns:
        True if upload successful
    """
    if bucket is None:
        bucket = Config.S3_BUCKET

    if not bucket:
        logger.warning("S3_BUCKET not configured, skipping upload")
        return False

    try:
        import boto3
        from io import BytesIO

        s3_client = boto3.client("s3")

        buffer = BytesIO()
        df.to_parquet(buffer, compression="snappy", index=False)
        buffer.seek(0)

        s3_client.put_object(
            Bucket=bucket, Key=key, Body=buffer.getvalue(), ContentType="application/parquet"
        )

        logger.info(f"✅ Uploaded to s3://{bucket}/{key}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to upload to S3: {e}")
        return False


def export_to_csv(df: pd.DataFrame, filename: str, output_dir: Optional[Path] = None) -> Path:
    """Export DataFrame to CSV.

    Args:
        df: DataFrame to export
        filename: Output filename
        output_dir: Output directory (defaults to Config.DATA_DIR / 'exports')

    Returns:
        Path to exported file
    """
    if output_dir is None:
        output_dir = Config.DATA_DIR / "exports"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    df.to_csv(output_path, index=False)
    logger.info(f"✅ Exported to {output_path}")

    return output_path


def run_export_pipeline(upload_s3: bool = False, export_csv: bool = False) -> Dict:
    """Run complete L3 export pipeline.

    Args:
        upload_s3: Whether to upload to S3
        export_csv: Whether to export to CSV

    Returns:
        Dictionary with export results
    """
    logger.info("=" * 60)
    logger.info("L3 Export Pipeline")
    logger.info("=" * 60)

    results = {}

    datasets = load_l3_datasets()

    if (
        "L3_property" in datasets
        and "L3_property_transactions_sales" in datasets
        and "L3_property_listing_sales" in datasets
    ):
        unified = create_unified_dataset(
            datasets["L3_property"],
            datasets["L3_property_transactions_sales"],
            datasets["L3_property_listing_sales"],
        )

        save_parquet(unified, "L3_unified", source="L3 export pipeline")
        results["unified"] = len(unified)

        if upload_s3:
            upload_to_s3(unified, "unified/l3_unified.parquet")

        if export_csv:
            export_to_csv(unified, "l3_unified.csv")

    if upload_s3:
        for name, df in datasets.items():
            key = f"{name.lower()}.parquet"
            upload_to_s3(df, key)

    if export_csv:
        for name, df in datasets.items():
            export_to_csv(df, f"{name.lower()}.csv")

    all_datasets = list_datasets()
    logger.info("\n📊 All available datasets:")
    for name, info in all_datasets.items():
        logger.info(f"  - {name}: {info['rows']} rows")

    logger.info("\n" + "=" * 60)
    logger.info("✅ L3 Export Pipeline Complete!")
    logger.info("=" * 60)

    return results


def main():
    """Main entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Run L3 export pipeline")
    parser.add_argument("--upload-s3", action="store_true", help="Upload datasets to S3")
    parser.add_argument("--export-csv", action="store_true", help="Export datasets to CSV")

    args = parser.parse_args()
    run_l3_export_pipeline(upload_s3=args.upload_s3, export_csv=args.export_csv)


if __name__ == "__main__":
    main()
