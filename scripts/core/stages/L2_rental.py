"""L2: Rental yield pipeline.

This module provides functions for:
- Downloading HDB rental data
- Downloading URA rental index
- Calculating rental yields for HDB and Condo
- Running complete L2 rental pipeline
"""  # noqa: N999

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from scripts.core.config import Config

logger = logging.getLogger(__name__)


def check_file_freshness(file_path: Path, max_age_days: int = 30) -> bool:
    """Check if a file exists and is fresh enough.

    Args:
        file_path: Path to check
        max_age_days: Maximum age in days (default: 30)

    Returns:
        True if file is fresh enough, False otherwise
    """
    if not file_path.exists():
        return False

    file_age_days = (datetime.now().timestamp() - file_path.stat().st_mtime) / 86400
    return file_age_days <= max_age_days


def download_hdb_rental_data(force: bool = False) -> bool:
    """Download HDB rental data from data.gov.sg.

    Args:
        force: Force re-download even if data is fresh

    Returns:
        True if download successful or data is fresh
    """
    logger.info("=" * 60)
    logger.info("Step 1: HDB Rental Data")
    logger.info("=" * 60)

    output_path = Config.PIPELINE_DIR / "L1" / "housing_hdb_rental.parquet"

    if not force and check_file_freshness(output_path, max_age_days=30):
        logger.info("✓ HDB rental data is fresh (< 30 days old)")
        logger.info("  Skipping download. Use --force to re-download.")
        return True

    try:
        from scripts.download_hdb_rental_data import download_hdb_rental_data

        df = download_hdb_rental_data()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, compression="snappy", index=False)

        logger.info(f"✅ Saved {len(df):,} records to {output_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to download HDB rental data: {e}")
        return False


def download_ura_rental_index(force: bool = False) -> bool:
    """Download URA rental index from data.gov.sg.

    Args:
        force: Force re-download even if data is fresh

    Returns:
        True if download successful or data is fresh
    """
    logger.info("=" * 60)
    logger.info("Step 2: URA Rental Index")
    logger.info("=" * 60)

    output_path = Config.PIPELINE_DIR / "L1" / "housing_ura_rental_index.parquet"

    if not force and check_file_freshness(output_path, max_age_days=90):
        logger.info("✓ URA rental index is fresh (< 90 days old)")
        logger.info("  Skipping download. Use --force to re-download.")
        return True

    try:
        from scripts.download_ura_rental_index import download_ura_rental_index

        df = download_ura_rental_index()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, compression="snappy", index=False)

        logger.info(f"✅ Saved {len(df):,} records to {output_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to download URA rental index: {e}")
        return False


def calculate_hdb_rental_yield() -> pd.DataFrame:
    """Calculate rental yield for HDB flats by town and month.

    Returns:
        DataFrame with rental yield metrics
    """
    logger.info("Calculating HDB rental yields...")

    rental_path = Config.PIPELINE_DIR / "L1" / "housing_hdb_rental.parquet"
    trans_path = Config.PIPELINE_DIR / "L1" / "housing_hdb_transaction.parquet"

    rental_df = pd.read_parquet(rental_path)
    trans_df = pd.read_parquet(trans_path)

    logger.info(f"  Rental records: {len(rental_df):,}")
    logger.info(f"  Transaction records: {len(trans_df):,}")

    rental_df["month"] = pd.to_datetime(rental_df["rent_approval_date"]).dt.to_period("M")
    rental_agg = rental_df.groupby(["town", "month"]).agg({"monthly_rent": "median"}).reset_index()

    trans_df["month"] = pd.to_datetime(trans_df["month"], format="%Y-%m").dt.to_period("M")
    trans_agg = trans_df.groupby(["town", "month"]).agg({"resale_price": "median"}).reset_index()

    merged = rental_agg.merge(trans_agg, on=["town", "month"], how="inner")
    merged["rental_yield_pct"] = (merged["monthly_rent"] * 12 / merged["resale_price"]) * 100

    logger.info(f"  Calculated {len(merged):,} HDB rental yield records")

    return merged


def calculate_condo_rental_yield() -> pd.DataFrame:
    """Calculate rental yield for condos using URA rental index.

    Returns:
        DataFrame with rental yield metrics
    """
    logger.info("Calculating Condo rental yields...")

    district_to_region = {
        "1": "Core Central Region",
        "2": "Core Central Region",
        "3": "Core Central Region",
        "4": "Core Central Region",
        "5": "Core Central Region",
        "6": "Core Central Region",
        "7": "Core Central Region",
        "8": "Core Central Region",
        "9": "Core Central Region",
        "10": "Core Central Region",
        "11": "Core Central Region",
        "12": "Rest of Central Region",
        "13": "Rest of Central Region",
        "14": "Rest of Central Region",
        "15": "Rest of Central Region",
        "19": "Rest of Central Region",
        "20": "Rest of Central Region",
        "16": "Outside Central Region",
        "17": "Outside Central Region",
        "18": "Outside Central Region",
        "21": "Outside Central Region",
        "22": "Outside Central Region",
        "23": "Outside Central Region",
        "24": "Outside Central Region",
        "25": "Outside Central Region",
        "26": "Outside Central Region",
        "27": "Outside Central Region",
        "28": "Outside Central Region",
    }

    rental_path = Config.PIPELINE_DIR / "L1" / "housing_ura_rental_index.parquet"
    trans_path = Config.PIPELINE_DIR / "L1" / "housing_condo_transaction.parquet"

    rental_df = pd.read_parquet(rental_path)
    trans_df = pd.read_parquet(trans_path)

    rental_df = rental_df[rental_df["property_type"] == "Non-Landed"].copy()
    rental_df["index"] = pd.to_numeric(rental_df["index"], errors="coerce")

    logger.info(f"  Rental index records: {len(rental_df):,}")
    logger.info(f"  Transaction records: {len(trans_df):,}")

    trans_df["quarter"] = pd.to_datetime(
        trans_df["Sale Date"], format="%b-%y", errors="coerce"
    ).dt.to_period("Q")
    trans_df["Transacted Price ($)"] = (
        trans_df["Transacted Price ($)"].astype(str).str.replace(",", "").astype(float)
    )
    trans_df["region"] = trans_df["Postal District"].astype(str).map(district_to_region)

    trans_agg = (
        trans_df.groupby(["region", "quarter"])
        .agg({"Transacted Price ($)": "median"})
        .reset_index()
    )

    rental_filtered = rental_df[
        rental_df["locality"].isin(
            ["Core Central Region", "Rest of Central Region", "Outside Central Region"]
        )
    ]
    merged = rental_filtered.merge(
        trans_agg, left_on=["locality", "quarter"], right_on=["region", "quarter"], how="inner"
    )

    merged["rent_index"] = merged["index"] / 100
    merged["rental_yield_pct"] = merged["rent_index"] * 0.03 * 100
    merged = merged.rename(columns={"locality": "town"})

    logger.info(f"  Calculated {len(merged):,} Condo rental yield records")

    return merged[["town", "quarter", "rental_yield_pct"]]


def calculate_rental_yields() -> bool:
    """Calculate rental yields from downloaded data.

    Returns:
        True if calculation successful
    """
    logger.info("=" * 60)
    logger.info("Step 3: Calculate Rental Yields")
    logger.info("=" * 60)

    hdb_path = Config.PIPELINE_DIR / "L1" / "housing_hdb_rental.parquet"
    ura_path = Config.PIPELINE_DIR / "L1" / "housing_ura_rental_index.parquet"

    if not hdb_path.exists():
        logger.error(f"❌ HDB rental data not found: {hdb_path}")
        return False

    if not ura_path.exists():
        logger.error(f"❌ URA rental index not found: {ura_path}")
        return False

    try:
        hdb_yields = calculate_hdb_rental_yield()
        logger.info(f"✅ Calculated {len(hdb_yields):,} HDB rental yields")

        condo_yields = calculate_condo_rental_yield()
        logger.info(f"✅ Calculated {len(condo_yields):,} Condo rental yields")

        hdb_yields["property_type"] = "HDB"
        condo_yields["property_type"] = "Condo"

        condo_yields = condo_yields.rename(columns={"quarter": "month"})

        all_yields = pd.concat(
            [
                hdb_yields[["town", "month", "property_type", "rental_yield_pct"]],
                condo_yields[["town", "month", "property_type", "rental_yield_pct"]],
            ],
            ignore_index=True,
        )

        all_yields["month"] = all_yields["month"].astype(str)

        output_path = Config.PIPELINE_DIR / "L2" / "rental_yield.parquet"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        all_yields.to_parquet(output_path, compression="snappy", index=False)
        logger.info(f"✅ Saved {len(all_yields):,} total records to {output_path}")

        logger.info("\nSummary:")
        logger.info(
            f"  HDB: {len(hdb_yields):,} records, {hdb_yields['rental_yield_pct'].mean():.2f}% avg yield"
        )
        logger.info(
            f"  Condo: {len(condo_yields):,} records, {condo_yields['rental_yield_pct'].mean():.2f}% avg yield"
        )

        return True

    except Exception as e:
        logger.error(f"❌ Failed to calculate rental yields: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_rental_pipeline(force: bool = False) -> dict:
    """Run complete L2 rental pipeline.

    Args:
        force: Force re-download even if data is fresh

    Returns:
        Dictionary with pipeline results
    """
    logger.info("=" * 60)
    logger.info("L2 Rental Pipeline")
    logger.info("=" * 60)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")

    results = {}

    results["hdb_rental"] = download_hdb_rental_data(force=force)
    results["ura_rental"] = download_ura_rental_index(force=force)

    if results["hdb_rental"] and results["ura_rental"]:
        results["rental_yields"] = calculate_rental_yields()
    else:
        logger.warning("⚠️ Skipping rental yield calculation due to download failures")
        results["rental_yields"] = False

    logger.info("")
    logger.info("=" * 60)
    logger.info("Pipeline Summary")
    logger.info("=" * 60)

    for step, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"  {step}: {status}")

    all_success = all(results.values())
    if all_success:
        logger.info("\n✅ All pipeline steps completed successfully!")
    else:
        failed_steps = [step for step, success in results.items() if not success]
        logger.warning(f"\n⚠️ Some steps failed: {', '.join(failed_steps)}")

    logger.info(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    return results


def main():
    """Main entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Run L2 rental pipeline")
    parser.add_argument(
        "--force", action="store_true", help="Force re-download even if data is fresh"
    )

    args = parser.parse_args()
    run_rental_pipeline(force=args.force)


if __name__ == "__main__":
    main()
