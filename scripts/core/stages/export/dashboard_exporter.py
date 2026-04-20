"""Summary table creation and export functions for the L3 export pipeline."""

import logging
from pathlib import Path

import pandas as pd

from scripts.core.config import Config
from scripts.core.data_quality import record_dataframe_quality

logger = logging.getLogger(__name__)


def create_market_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Create market summary table with aggregated statistics.

    Args:
        df: Full transaction DataFrame

    Returns:
        Summary table by property_type, period_5yr, market_tier_period
    """
    logger.info("Creating market summary table...")

    if df.empty:
        return pd.DataFrame()

    group_cols = ["property_type", "period_5yr", "market_tier_period"]

    # Filter to columns that exist
    available_group_cols = [col for col in group_cols if col in df.columns]

    if len(available_group_cols) < 2:
        logger.warning("Cannot create market summary - missing required columns")
        return pd.DataFrame()

    summary = (
        df.groupby(available_group_cols)
        .agg(
            {
                "price": ["count", "median", "mean", "min", "max", "std"],
                "price_psm": ["median", "mean"] if "price_psm" in df.columns else "count",
                "price_psf": ["median", "mean"] if "price_psf" in df.columns else "count",
                "floor_area_sqft": ["median", "mean"]
                if "floor_area_sqft" in df.columns
                else "count",
            }
        )
        .reset_index()
    )

    # Flatten column names
    summary.columns = [
        "_".join(col).strip("_") if isinstance(col, tuple) else col for col in summary.columns
    ]

    # Calculate tier distribution percentages
    if "market_tier_period" in available_group_cols:
        total_by_group = (
            summary.groupby(available_group_cols[:2])["price_count"].sum().reset_index()
        )
        total_by_group.columns = available_group_cols[:2] + ["total_count"]
        summary = summary.merge(total_by_group, on=available_group_cols[:2], how="left")
        summary["tier_pct"] = (summary["price_count"] / summary["total_count"] * 100).round(1)
        summary = summary.drop(columns=["total_count"])

    logger.info(f"Created market summary with {len(summary):,} rows")
    return summary


def create_tier_thresholds_evolution(df: pd.DataFrame) -> pd.DataFrame:
    """Create tier threshold evolution table.

    Args:
        df: Full transaction DataFrame

    Returns:
        Table with max/median price thresholds by period and property_type
    """
    logger.info("Creating tier thresholds evolution table...")

    if df.empty or "market_tier_period" not in df.columns:
        return pd.DataFrame()

    # Calculate thresholds for each tier
    thresholds = []

    for ptype in df["property_type"].unique():
        ptype_df = df[df["property_type"] == ptype]

        for period in ptype_df["period_5yr"].unique():
            period_df = ptype_df[ptype_df["period_5yr"] == period]

            for tier in ["Mass Market", "Mid-Tier", "Luxury"]:
                tier_data = period_df[period_df["market_tier_period"] == tier]

                if not tier_data.empty:
                    thresholds.append(
                        {
                            "property_type": ptype,
                            "period": period,
                            "tier": tier,
                            "count": len(tier_data),
                            "min_price": tier_data["price"].min(),
                            "max_price": tier_data["price"].max(),
                            "median_price": tier_data["price"].median(),
                            "mean_price": tier_data["price"].mean(),
                        }
                    )

    result = pd.DataFrame(thresholds)

    # Pivot to get tier columns for easier comparison
    if not result.empty:
        pivot = result.pivot_table(
            index=["property_type", "period"], columns="tier", values="median_price"
        ).reset_index()
        pivot.columns.name = None
        pivot = pivot.rename(
            columns={
                "Mass Market": "mass_market_median",
                "Mid-Tier": "mid_tier_median",
                "Luxury": "luxury_median",
            }
        )
        result = result.merge(pivot, on=["property_type", "period"], how="left")

    logger.info(f"Created tier thresholds with {len(result):,} rows")
    return result


def create_planning_area_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Create planning area metrics table.

    Args:
        df: Full transaction DataFrame

    Returns:
        Aggregated metrics by planning_area
    """
    logger.info("Creating planning area metrics table...")

    if df.empty or "planning_area" not in df.columns:
        return pd.DataFrame()

    metrics = (
        df.groupby("planning_area")
        .agg(
            {
                "price": ["count", "median", "mean"],
                "price_psf": ["median", "mean"] if "price_psf" in df.columns else "count",
                "rental_yield_pct": ["median", "mean"]
                if "rental_yield_pct" in df.columns
                else "count",
            }
        )
        .reset_index()
    )

    # Flatten column names
    metrics.columns = [
        "_".join(col).strip("_") if isinstance(col, tuple) else col for col in metrics.columns
    ]

    # Add amenity accessibility scores if available
    amenity_distance_cols = [col for col in df.columns if col.startswith("dist_to_nearest_")]
    if amenity_distance_cols:
        amenity_means = df.groupby("planning_area")[amenity_distance_cols].mean().reset_index()
        # Rename amenity columns to include _avg suffix
        rename_cols = {col: f"{col}_avg" for col in amenity_means.columns if col != "planning_area"}
        amenity_means = amenity_means.rename(columns=rename_cols)
        metrics = metrics.merge(amenity_means, on="planning_area", how="left")

    # Add period breakdown
    if "period_5yr" in df.columns:
        pa_period_counts = df.groupby(["planning_area", "period_5yr"]).size().unstack(fill_value=0)
        pa_period_counts.columns = [f"transactions_{col}" for col in pa_period_counts.columns]
        pa_period_counts = pa_period_counts.reset_index()
        metrics = metrics.merge(pa_period_counts, on="planning_area", how="left")

    metrics = metrics.rename(columns={"price_count": "transaction_count"})
    metrics = metrics.sort_values("transaction_count", ascending=False)

    logger.info(f"Created planning area metrics with {len(metrics):,} rows")
    return metrics


def create_lease_decay_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Create lease decay statistics table for HDB properties.

    Args:
        df: Full transaction DataFrame

    Returns:
        Price statistics by lease band
    """
    logger.info("Creating lease decay statistics...")

    if df.empty:
        return pd.DataFrame()

    # Filter to HDB with remaining lease
    hdb_df = df[df["property_type"] == "HDB"].copy()

    if (
        "remaining_lease_months" not in hdb_df.columns
        and "remaining_lease_years" not in hdb_df.columns
    ):
        logger.warning("No remaining lease data found, skipping lease decay stats")
        return pd.DataFrame()

    # Convert to years if needed
    if "remaining_lease_months" in hdb_df.columns and "remaining_lease_years" not in hdb_df.columns:
        hdb_df["remaining_lease_years"] = hdb_df["remaining_lease_months"] / 12

    if "remaining_lease_years" not in hdb_df.columns:
        return pd.DataFrame()

    # Create lease bands
    hdb_df["lease_band"] = pd.cut(
        hdb_df["remaining_lease_years"],
        bins=[0, 60, 70, 80, 90, 100],
        labels=["<60 years", "60-70 years", "70-80 years", "80-90 years", "90+ years"],
    )

    # Calculate statistics
    stats = (
        hdb_df.groupby("lease_band", observed=True)
        .agg(
            {
                "price": ["count", "median", "mean", "min", "max"],
                "price_psf": ["median", "mean"] if "price_psf" in hdb_df.columns else "count",
            }
        )
        .reset_index()
    )

    stats.columns = [
        "lease_band",
        "transaction_count",
        "median_price",
        "mean_price",
        "min_price",
        "max_price",
        "median_psf",
        "mean_psf",
    ]

    # Calculate discount to baseline (90+ years)
    baseline_median = stats[stats["lease_band"] == "90+ years"]["median_price"].values
    if len(baseline_median) > 0:
        baseline = baseline_median[0]
        stats["discount_to_baseline_pct"] = (
            (baseline - stats["median_price"]) / baseline * 100
        ).round(1)
        stats["annual_decay_pct"] = (
            stats["discount_to_baseline_pct"]
            / (99 - stats["lease_band"].astype(str).str.extract(r"(\d+)")[0].astype(float))
        ).round(2)

    logger.info(f"Created lease decay stats with {len(stats):,} rows")
    return stats


def create_rental_yield_top_combos(df: pd.DataFrame) -> pd.DataFrame:
    """Create top rental yield combinations table.

    Args:
        df: Full transaction DataFrame

    Returns:
        Top rental yield combos by town and flat_type
    """
    logger.info("Creating rental yield top combinations...")

    if df.empty or "rental_yield_pct" not in df.columns:
        return pd.DataFrame()

    rental_df = df[df["rental_yield_pct"].notna()].copy()

    if rental_df.empty:
        return pd.DataFrame()

    # Town + flat type combinations
    if "flat_type" in rental_df.columns and "town" in rental_df.columns:
        combos = (
            rental_df.groupby(["town", "flat_type"])
            .agg(
                {
                    "rental_yield_pct": ["median", "mean", "count"],
                    "price": ["median", "mean"],
                }
            )
            .reset_index()
        )

        combos.columns = [
            "town",
            "flat_type",
            "yield_median",
            "yield_mean",
            "yield_count",
            "price_median",
            "price_mean",
        ]

        # Calculate estimated monthly rent
        combos["monthly_rent_est"] = (
            combos["price_median"] * combos["yield_median"] / 100 / 12
        ).round(0)

        combos = combos.sort_values("yield_median", ascending=False)
        combos["rank"] = range(1, len(combos) + 1)

        logger.info(f"Created {len(combos)} rental yield combinations")
        return combos

    # Town only
    if "town" in rental_df.columns:
        town_yields = (
            rental_df.groupby("town")
            .agg(
                {
                    "rental_yield_pct": ["median", "mean", "count"],
                    "price": ["median", "mean"],
                }
            )
            .reset_index()
        )

        town_yields.columns = [
            "town",
            "yield_median",
            "yield_mean",
            "yield_count",
            "price_median",
            "price_mean",
        ]
        town_yields = town_yields.sort_values("yield_median", ascending=False)
        town_yields["rank"] = range(1, len(town_yields) + 1)

        logger.info(f"Created {len(town_yields)} town rental yields")
        return town_yields

    return pd.DataFrame()


def save_precomputed_tables(
    market_summary: pd.DataFrame,
    tier_thresholds: pd.DataFrame,
    pa_metrics: pd.DataFrame,
    lease_decay: pd.DataFrame,
    rental_combos: pd.DataFrame,
    l3_dir: Path,
) -> None:
    """Save all precomputed tables to parquet.

    Args:
        market_summary: Market summary table
        tier_thresholds: Tier thresholds evolution
        pa_metrics: Planning area metrics
        lease_decay: Lease decay statistics
        rental_combos: Rental yield combinations
        l3_dir: Output directory
    """
    logger.info("Saving precomputed tables...")

    tables = {
        "market_summary": ("L3_market_summary", market_summary),
        "tier_thresholds_evolution": ("L3_tier_thresholds_evolution", tier_thresholds),
        "planning_area_metrics": ("L3_planning_area_metrics", pa_metrics),
        "lease_decay_stats": ("L3_lease_decay_stats", lease_decay),
        "rental_yield_top_combos": ("L3_rental_yield_top_combos", rental_combos),
    }

    for name, (dataset_name, table) in tables.items():
        if not table.empty:
            output_path = l3_dir / f"{name}.parquet"
            table.to_parquet(output_path, compression="snappy", index=False)
            record_dataframe_quality(
                table,
                dataset_name,
                source="L3 precomputed tables",
            )
            logger.info(f"  Saved {name}: {len(table):,} rows -> {output_path}")
        else:
            logger.warning(f"  Skipping {name}: empty DataFrame")


def upload_to_s3(df: pd.DataFrame, key: str, bucket: str | None = None) -> bool:
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
        from io import BytesIO

        import boto3

        s3_client = boto3.client("s3")

        buffer = BytesIO()
        df.to_parquet(buffer, compression="snappy", index=False)
        buffer.seek(0)

        s3_client.put_object(
            Bucket=bucket, Key=key, Body=buffer.getvalue(), ContentType="application/parquet"
        )

        logger.info(f"Uploaded to s3://{bucket}/{key}")
        return True

    except Exception as e:
        logger.error(f"Failed to upload to S3: {e}")
        return False


def export_to_csv(df: pd.DataFrame, filename: str, output_dir: Path | None = None) -> Path:
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
    logger.info(f"Exported to {output_path}")

    return output_path
