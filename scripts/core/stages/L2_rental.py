"""L2: Rental yield pipeline.

This module provides functions for:
- Downloading HDB rental data
- Downloading URA rental index
- Calculating rental yields for HDB, Condo, and EC
- Running complete L2 rental pipeline
"""  # noqa: N999

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from scripts.core.config import Config

logger = logging.getLogger(__name__)

DISTRICT_TO_REGION = {
    **{str(i): "Core Central Region" for i in range(1, 12)},
    **{str(i): "Rest of Central Region" for i in [12, 13, 14, 15, 19, 20]},
    **{str(i): "Outside Central Region" for i in [16, 17, 18, 21, 22, 23, 24, 25, 26, 27, 28]},
}

PRIVATE_LOCALITIES = [
    "Core Central Region",
    "Rest of Central Region",
    "Outside Central Region",
]

HDB_MEDIAN_RENT_DATASET_ID = "d_23000a00c52996c55106084ed0339566"
HDB_MEDIAN_RENT_OUTPUT = "housing_hdb_median_rent_by_town_flat_type.parquet"

MIN_HDB_RENTAL_ROWS = 50_000
MIN_HDB_RENTAL_MONTHS = 12


def _normalize_hdb_rental_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize HDB rental schema from L0/raw or downloader outputs."""
    result = df.copy()
    result.columns = result.columns.str.lower().str.replace(" ", "_")
    if "_id" in result.columns:
        result = result.drop(columns=["_id"])
    if "monthly_rent" in result.columns:
        result["monthly_rent"] = pd.to_numeric(result["monthly_rent"], errors="coerce")
    if "rent_approval_date" in result.columns:
        result["rent_approval_date"] = pd.to_datetime(result["rent_approval_date"], errors="coerce")
    return result


def _hdb_rental_coverage_signature(df: pd.DataFrame) -> tuple[int, pd.Period | None, pd.Period | None]:
    """Return (month_count, min_month, max_month) for HDB rental records."""
    if "rent_approval_date" not in df.columns:
        return 0, None, None
    months = pd.to_datetime(df["rent_approval_date"], errors="coerce").dt.to_period("M").dropna()
    if months.empty:
        return 0, None, None
    return int(months.nunique()), months.min(), months.max()


def _write_hdb_rental_output(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, compression="snappy", index=False)


def _assert_hdb_rental_completeness(df: pd.DataFrame, source_name: str) -> None:
    """Fail loudly if HDB rental source looks truncated."""
    month_count, min_month, max_month = _hdb_rental_coverage_signature(df)
    row_count = len(df)
    if row_count < MIN_HDB_RENTAL_ROWS or month_count < MIN_HDB_RENTAL_MONTHS:
        raise ValueError(
            "HDB rental source appears truncated "
            f"({source_name}: {row_count:,} rows, {month_count} month(s), "
            f"range={min_month} to {max_month}; expected at least "
            f"{MIN_HDB_RENTAL_ROWS:,} rows and {MIN_HDB_RENTAL_MONTHS} months). "
            "Run L0 collection to refresh raw_datagov_hdb_rental or verify data.gov fetch."
        )


def _canonical_hdb_flat_type(series: pd.Series) -> pd.Series:
    """Normalize HDB flat types to a common join key used by the median-rent dataset."""
    return (
        series.astype(str)
        .str.upper()
        .str.strip()
        .replace(
            {
                "1 ROOM": "1-RM",
                "2 ROOM": "2-RM",
                "3 ROOM": "3-RM",
                "4 ROOM": "4-RM",
                "5 ROOM": "5-RM",
                "EXECUTIVE": "EXEC",
                "MULTI GENERATION": None,
                "MULTI-GENERATION": None,
                "NAN": None,
            }
        )
    )


def _load_hdb_median_rent_by_town_flat_type(force: bool = False) -> pd.DataFrame:
    """Load/download quarterly HDB median rent by town and flat type (aggregate fallback)."""
    output_path = Config.PIPELINE_DIR / "L1" / HDB_MEDIAN_RENT_OUTPUT
    if not force and check_file_freshness(output_path, max_age_days=90):
        df = pd.read_parquet(output_path)
        logger.info("✓ HDB median rent aggregate data is fresh")
        return df

    from scripts.data.download.download_hdb_rental_data import (
        download_hdb_rental_data as fetch_dataset_download_api,
    )

    logger.info("Downloading HDB median rent aggregate dataset for fallback...")
    df = fetch_dataset_download_api(dataset_id=HDB_MEDIAN_RENT_DATASET_ID)
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, compression="snappy", index=False)
    logger.info("✅ Saved %s (%s rows)", output_path.name, len(df))
    return df


def calculate_hdb_rental_yield_from_median_rent_fallback(force_download: bool = False) -> pd.DataFrame:
    """Estimate HDB rental yields using quarterly median rent by town+flat_type as fallback."""
    logger.warning(
        "Using aggregate HDB fallback: quarterly median rent by town/flat_type (data.gov.sg) "
        "because transaction-level HDB rental source is truncated"
    )
    rental_df = _load_hdb_median_rent_by_town_flat_type(force=force_download).copy()
    trans_path = Config.PIPELINE_DIR / "L1" / "housing_hdb_transaction.parquet"
    trans_df = pd.read_parquet(trans_path).copy()

    rental_df.columns = rental_df.columns.str.lower().str.replace(" ", "_")
    required_cols = {"quarter", "town", "flat_type", "median_rent"}
    missing = required_cols - set(rental_df.columns)
    if missing:
        raise ValueError(f"HDB median rent fallback dataset missing columns: {sorted(missing)}")

    rental_df["town"] = rental_df["town"].astype(str).str.upper().str.strip()
    rental_df["flat_type_key"] = _canonical_hdb_flat_type(rental_df["flat_type"])
    rental_df["quarter"] = rental_df["quarter"].astype(str).str.replace("-", "", regex=False)
    rental_df["quarter"] = pd.PeriodIndex(rental_df["quarter"], freq="Q")
    rental_df["median_rent"] = pd.to_numeric(rental_df["median_rent"], errors="coerce")
    rental_df = rental_df.dropna(subset=["quarter", "town", "flat_type_key", "median_rent"])

    trans_df["town"] = trans_df["town"].astype(str).str.upper().str.strip()
    trans_df["flat_type_key"] = _canonical_hdb_flat_type(trans_df["flat_type"])
    trans_df["month"] = pd.to_datetime(trans_df["month"], format="%Y-%m", errors="coerce").dt.to_period("M")
    trans_df["quarter"] = trans_df["month"].dt.asfreq("Q")
    trans_df["resale_price"] = pd.to_numeric(trans_df["resale_price"], errors="coerce")
    trans_df = trans_df.dropna(subset=["quarter", "town", "flat_type_key", "resale_price"])

    rental_q = (
        rental_df.groupby(["town", "quarter", "flat_type_key"], as_index=False)["median_rent"]
        .median()
    )
    trans_q = (
        trans_df.groupby(["town", "quarter", "flat_type_key"], as_index=False)
        .agg(resale_price=("resale_price", "median"), txn_count=("resale_price", "size"))
    )

    merged_q = rental_q.merge(trans_q, on=["town", "quarter", "flat_type_key"], how="inner")
    if merged_q.empty:
        raise ValueError("HDB median-rent fallback produced no town+quarter+flat_type matches")

    merged_q["rental_yield_pct_combo"] = (merged_q["median_rent"] * 12 / merged_q["resale_price"]) * 100
    merged_q["_weighted_yield"] = merged_q["rental_yield_pct_combo"] * merged_q["txn_count"]
    town_q = (
        merged_q.groupby(["town", "quarter"], as_index=False)
        .agg(
            weighted_yield_sum=("_weighted_yield", "sum"),
            txn_count=("txn_count", "sum"),
        )
    )
    town_q["rental_yield_pct"] = town_q["weighted_yield_sum"] / town_q["txn_count"]
    town_q = town_q[["town", "quarter", "rental_yield_pct"]]

    # Expand quarterly estimates to each month in the quarter so L3's HDB month join can match.
    expanded_rows: list[dict] = []
    for row in town_q.itertuples(index=False):
        start_month = row.quarter.asfreq("M", how="start")
        for m in pd.period_range(start=start_month, periods=3, freq="M"):
            expanded_rows.append(
                {"town": row.town, "month": m, "rental_yield_pct": float(row.rental_yield_pct)}
            )
    result = pd.DataFrame(expanded_rows)
    result = result.groupby(["town", "month"], as_index=False)["rental_yield_pct"].median()

    logger.info(
        "HDB fallback rental yield coverage: %s town-month records from %s quarters (%s to %s)",
        len(result),
        int(town_q["quarter"].nunique()),
        town_q["quarter"].min() if not town_q.empty else None,
        town_q["quarter"].max() if not town_q.empty else None,
    )
    return result


def check_file_freshness(file_path: Path, max_age_days: int = 30) -> bool:
    """Check if a file exists and is fresh enough."""
    if not file_path.exists():
        return False
    file_age_days = (datetime.now().timestamp() - file_path.stat().st_mtime) / 86400
    return file_age_days <= max_age_days


def download_hdb_rental_data(force: bool = False) -> bool:
    """Download HDB rental data from data.gov.sg."""
    logger.info("Step 1: HDB Rental Data")
    output_path = Config.PIPELINE_DIR / "L1" / "housing_hdb_rental.parquet"
    raw_l0_path = Config.PIPELINE_DIR / "raw_datagov_hdb_rental.parquet"

    # Prefer L0 raw HDB rental dataset when available, especially if it has broader history.
    if raw_l0_path.exists():
        try:
            raw_df = _normalize_hdb_rental_df(pd.read_parquet(raw_l0_path))
            raw_months, raw_min, raw_max = _hdb_rental_coverage_signature(raw_df)
            logger.info(
                "Found L0 HDB rental raw data: %s rows, %s month(s) (%s to %s)",
                len(raw_df),
                raw_months,
                raw_min,
                raw_max,
            )

            should_write_from_l0 = force or not output_path.exists()
            if output_path.exists() and not should_write_from_l0:
                existing_df = _normalize_hdb_rental_df(pd.read_parquet(output_path))
                existing_months, existing_min, existing_max = _hdb_rental_coverage_signature(existing_df)
                logger.info(
                    "Existing L1 HDB rental data: %s rows, %s month(s) (%s to %s)",
                    len(existing_df),
                    existing_months,
                    existing_min,
                    existing_max,
                )
                should_write_from_l0 = (
                    raw_months > existing_months
                    or (raw_months == existing_months and len(raw_df) > len(existing_df))
                )

            if should_write_from_l0:
                _assert_hdb_rental_completeness(raw_df, "L0 raw HDB rental")
                _write_hdb_rental_output(raw_df, output_path)
                logger.info("✅ Seeded L1 HDB rental data from L0 raw dataset")
                return True
        except Exception as e:
            logger.warning(f"Failed to use L0 raw HDB rental dataset: {e}")

    if not force and check_file_freshness(output_path, max_age_days=30):
        logger.info("✓ HDB rental data is fresh")
        return True

    try:
        from scripts.data.download.download_hdb_rental_data import (
            download_hdb_rental_data as fetch_hdb_rental_data,
        )
        df = fetch_hdb_rental_data()
        df = _normalize_hdb_rental_df(df)
        _assert_hdb_rental_completeness(df, "direct HDB rental download")
        _write_hdb_rental_output(df, output_path)
        logger.info(f"✅ Saved {len(df):,} records")
        return True
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        return False


def download_ura_rental_index(force: bool = False) -> bool:
    """Download URA rental index from data.gov.sg."""
    logger.info("Step 2: URA Rental Index")
    output_path = Config.PIPELINE_DIR / "L1" / "housing_ura_rental_index.parquet"

    if not force and check_file_freshness(output_path, max_age_days=90):
        logger.info("✓ URA rental index is fresh")
        return True

    try:
        from scripts.data.download.download_ura_rental_index import (
            download_ura_rental_index as fetch_ura_rental_index,
        )
        df = fetch_ura_rental_index()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, compression="snappy", index=False)
        logger.info(f"✅ Saved {len(df):,} records")
        return True
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        return False


def calculate_hdb_rental_yield() -> pd.DataFrame:
    """Calculate rental yield for HDB flats."""
    rental_path = Config.PIPELINE_DIR / "L1" / "housing_hdb_rental.parquet"
    trans_path = Config.PIPELINE_DIR / "L1" / "housing_hdb_transaction.parquet"

    if not rental_path.exists():
        logger.warning("HDB rental transaction dataset missing at %s", rental_path)
        return calculate_hdb_rental_yield_from_median_rent_fallback()

    rental_df = pd.read_parquet(rental_path)
    trans_df = pd.read_parquet(trans_path)
    try:
        _assert_hdb_rental_completeness(rental_df, str(rental_path))
    except ValueError as e:
        logger.warning("%s", e)
        return calculate_hdb_rental_yield_from_median_rent_fallback()

    rental_df["month"] = pd.to_datetime(rental_df["rent_approval_date"]).dt.to_period("M")
    rental_months = rental_df["month"].dropna()
    if not rental_months.empty:
        month_count = rental_months.nunique()
        logger.info(
            "HDB rental source covers %s month(s): %s to %s",
            month_count,
            rental_months.min(),
            rental_months.max(),
        )
        if month_count < 6:
            logger.warning(
                "HDB rental source has a narrow time window (%s month(s)); HDB rental yield coverage in L3 will be limited",
                month_count,
            )
    rental_agg = rental_df.groupby(["town", "month"]).agg({"monthly_rent": "median"}).reset_index()

    trans_df["month"] = pd.to_datetime(trans_df["month"], format="%Y-%m").dt.to_period("M")
    trans_agg = trans_df.groupby(["town", "month"]).agg({"resale_price": "median"}).reset_index()

    merged = rental_agg.merge(trans_agg, on=["town", "month"], how="inner")
    merged["rental_yield_pct"] = (merged["monthly_rent"] * 12 / merged["resale_price"]) * 100

    return merged


def calculate_condo_ec_yield(property_type: str, is_ec: bool = False) -> pd.DataFrame:
    """Calculate rental yield for condo or EC using estimation.

    Args:
        property_type: "Condo" or "EC"
        is_ec: True if calculating EC yields
    """
    logger.info(f"Calculating {property_type} rental yields...")

    rental_path = Config.PIPELINE_DIR / "L1" / "housing_ura_rental_index.parquet"
    trans_path = (
        Config.PIPELINE_DIR / "L1" / "housing_ec_transaction.parquet"
        if is_ec
        else Config.PIPELINE_DIR / "L1" / "housing_condo_transaction.parquet"
    )

    rental_df = pd.read_parquet(rental_path)
    trans_df = pd.read_parquet(trans_path)

    rental_df = rental_df[rental_df["property_type"] == "Non-Landed"].copy()
    rental_df["index"] = pd.to_numeric(rental_df["index"], errors="coerce")

    trans_df["quarter"] = pd.to_datetime(
        trans_df["Sale Date"], format="%b-%y", errors="coerce"
    ).dt.to_period("Q")
    trans_df["region"] = trans_df["Postal District"].astype(str).map(DISTRICT_TO_REGION)
    trans_agg = (
        trans_df[["region", "quarter"]]
        .dropna()
        .drop_duplicates()
    )

    rental_filtered = rental_df[
        rental_df["locality"].isin(PRIVATE_LOCALITIES)
    ]
    merged = rental_filtered.merge(
        trans_agg, left_on=["locality", "quarter"], right_on=["region", "quarter"], how="inner"
    )

    adjustment = 0.85 if is_ec else 1.0
    merged["rent_index"] = merged["index"] / 100
    merged["rental_yield_pct"] = merged["rent_index"] * 0.03 * 100 * adjustment
    merged = merged.rename(columns={"locality": "town"})

    logger.info(f"  Calculated {len(merged):,} {property_type} records")

    return merged[["town", "quarter", "rental_yield_pct"]]


def calculate_rental_yields() -> bool:
    """Calculate all rental yields from downloaded data."""
    logger.info("Step 3: Calculate Rental Yields")

    hdb_path = Config.PIPELINE_DIR / "L1" / "housing_hdb_rental.parquet"
    ura_path = Config.PIPELINE_DIR / "L1" / "housing_ura_rental_index.parquet"

    if not hdb_path.exists():
        logger.warning("⚠️ HDB rental transaction dataset not found; HDB aggregate fallback may be used")

    hdb_yields = pd.DataFrame(columns=["town", "month", "property_type", "rental_yield_pct"])
    condo_yields = pd.DataFrame(columns=["town", "quarter", "rental_yield_pct"])
    ec_yields = pd.DataFrame(columns=["town", "quarter", "rental_yield_pct"])
    output_frames: list[pd.DataFrame] = []

    # HDB yield path is independent from private (Condo/EC) yield path.
    try:
        hdb_yields = calculate_hdb_rental_yield()
        hdb_yields["property_type"] = "HDB"
        output_frames.append(hdb_yields[["town", "month", "property_type", "rental_yield_pct"]])
    except Exception as e:
        logger.error("❌ HDB rental yield calculation failed: %s", e)
        import traceback
        traceback.print_exc()

    # Private yield path depends on URA rental index but should not block HDB.
    try:
        if ura_path.exists():
            condo_yields = calculate_condo_ec_yield("Condo", is_ec=False)
            condo_yields["property_type"] = "Condo"

            ec_yields = calculate_condo_ec_yield("EC", is_ec=True)
            ec_yields["property_type"] = "EC"

            for df in [condo_yields, ec_yields]:
                private_df = df.rename(columns={"quarter": "month"}).copy()
                private_df["month"] = private_df["month"].dt.to_timestamp(how="start").dt.to_period("M")
                output_frames.append(
                    private_df[["town", "month", "property_type", "rental_yield_pct"]]
                )
        else:
            logger.warning("⚠️ URA rental index not found; skipping Condo/EC rental yields")
    except Exception as e:
        logger.error("❌ Condo/EC rental yield calculation failed: %s", e)
        import traceback
        traceback.print_exc()

    if not output_frames:
        logger.error("❌ Failed: no rental yield outputs were produced")
        return False

    all_yields = pd.concat(output_frames, ignore_index=True)
    all_yields["month"] = all_yields["month"].astype(str)
    all_yields = all_yields.drop_duplicates(["property_type", "town", "month"])

    output_path = Config.PIPELINE_DIR / "L2" / "rental_yield.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    all_yields.to_parquet(output_path, compression="snappy", index=False)

    logger.info(f"✅ Saved {len(all_yields):,} total records")
    if not hdb_yields.empty:
        logger.info(f"  HDB: {hdb_yields['rental_yield_pct'].mean():.2f}% avg")
    if not condo_yields.empty:
        logger.info(f"  Condo: {condo_yields['rental_yield_pct'].mean():.2f}% avg")
    if not ec_yields.empty:
        logger.info(f"  EC: {ec_yields['rental_yield_pct'].mean():.2f}% avg")

    return True


def run_rental_pipeline(force: bool = False) -> dict:
    """Run complete L2 rental pipeline."""
    logger.info("=" * 60)
    logger.info("L2 Rental Pipeline")
    logger.info("=" * 60)

    results = {}
    results["hdb_rental"] = download_hdb_rental_data(force=force)
    results["ura_rental"] = download_ura_rental_index(force=force)

    if results["hdb_rental"] or results["ura_rental"]:
        results["rental_yields"] = calculate_rental_yields()
    else:
        logger.warning("⚠️ Skipping rental yield calculation (no HDB or URA rental inputs available)")
        results["rental_yields"] = False

    # If transactional HDB rental failed but rental yields were produced via aggregate fallback,
    # treat the HDB input step as satisfied for pipeline success accounting.
    fallback_hdb_path = Config.PIPELINE_DIR / "L1" / HDB_MEDIAN_RENT_OUTPUT
    if not results["hdb_rental"] and results["rental_yields"] and fallback_hdb_path.exists():
        logger.warning(
            "Using aggregate HDB median-rent fallback as HDB rental input for this run (%s)",
            fallback_hdb_path.name,
        )
        results["hdb_rental"] = True

    logger.info("=" * 60)
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run L2 rental pipeline")
    parser.add_argument("--force", action="store_true", help="Force re-download")
    args = parser.parse_args()
    run_rental_pipeline(force=args.force)


if __name__ == "__main__":
    main()
