"""L5: Metrics calculation pipeline.

This module provides functions for:
- Calculating price metrics at planning area level
- Computing rental yield summaries by area
- Analyzing appreciation patterns (MoM, YoY)
- Generating market momentum indicators
- Creating affordability metrics
- Identifying investment hotspots
- Running complete L5 metrics pipeline
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet, save_parquet
from scripts.core import metrics as metrics_module

logger = logging.getLogger(__name__)


def load_unified_data() -> pd.DataFrame:
    """Load L3 unified dataset.

    Returns:
        Unified transaction DataFrame
    """
    logger.info("Loading L3 unified dataset...")

    df = load_parquet("L3_unified")

    logger.info(f"  Loaded {len(df):,} transactions")

    # Ensure datetime columns
    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")

    # Add temporal columns
    if "transaction_date" in df.columns:
        df["year"] = df["transaction_date"].dt.year
        df["month"] = df["transaction_date"].dt.to_period("M").astype(str)

    return df


def calculate_price_metrics_by_area(
    df: pd.DataFrame,
    group_by: list = ["planning_area", "month", "property_type"]
) -> pd.DataFrame:
    """Calculate price metrics at planning area level.

    Args:
        df: Transaction DataFrame
        group_by: Columns to group by

    Returns:
        DataFrame with price metrics
    """
    logger.info("Calculating price metrics by planning area...")

    # Map column names (handle different schemas)
    price_col = "resale_price" if "resale_price" in df.columns else "price"
    psf_col = "unitprice_psf" if "unitprice_psf" in df.columns else "price_psf"
    area_col = "area_sqft" if "area_sqft" in df.columns else "floor_area_sqft"

    # Ensure required columns exist
    if price_col not in df.columns:
        logger.warning(f"Price column not found (looking for '{price_col}')")
        return pd.DataFrame()

    if "planning_area" not in df.columns:
        logger.warning("planning_area column not found")
        return pd.DataFrame()

    # Add price_psf if not exists
    df = df.copy()
    if psf_col not in df.columns and area_col in df.columns:
        df[psf_col] = df[price_col] / df[area_col]

    # Adjust group_by based on available columns
    available_group_cols = [c for c in group_by if c in df.columns]
    if not available_group_cols:
        available_group_cols = ["planning_area"]

    # Build aggregation dictionary
    agg_dict = {price_col: ["median", "mean", "count"]}
    if psf_col in df.columns:
        agg_dict[psf_col] = ["median", "mean"]

    # Group by available columns
    price_metrics = df.groupby(available_group_cols).agg(agg_dict).reset_index()

    # Flatten column names
    price_metrics.columns = [
        "_".join(col).strip("_") if col[1] else col[0]
        for col in price_metrics.columns.values
    ]

    logger.info(f"  Created price metrics with {len(price_metrics):,} records")

    return price_metrics


def calculate_volume_metrics_by_area(
    df: pd.DataFrame,
    group_by: list = ["planning_area", "month"]
) -> pd.DataFrame:
    """Calculate transaction volume metrics by planning area.

    Args:
        df: Transaction DataFrame
        group_by: Columns to group by

    Returns:
        DataFrame with volume metrics
    """
    logger.info("Calculating volume metrics by planning area...")

    if "planning_area" not in df.columns or "transaction_date" not in df.columns:
        logger.warning("Missing required columns for volume metrics")
        return pd.DataFrame()

    # Adjust group_by based on available columns
    available_group_cols = [c for c in group_by if c in df.columns]
    if "month" not in available_group_cols and "transaction_date" in df.columns:
        df = df.copy()
        df["month"] = df["transaction_date"].dt.to_period("M").astype(str)
        available_group_cols = ["planning_area", "month"]

    # Count transactions
    volume = df.groupby(available_group_cols).size().reset_index(name="transaction_count")

    # Sort for rolling calculations
    if len(available_group_cols) >= 2:
        volume = volume.sort_values(available_group_cols)

        # Calculate rolling averages (3-month, 12-month)
        if "planning_area" in available_group_cols:
            volume["volume_3m_avg"] = volume.groupby("planning_area")["transaction_count"].transform(
                lambda x: x.rolling(3, min_periods=1).mean()
            )
            volume["volume_12m_avg"] = volume.groupby("planning_area")["transaction_count"].transform(
                lambda x: x.rolling(12, min_periods=1).mean()
            )

    logger.info(f"  Created volume metrics with {len(volume):,} records")

    return volume


def calculate_growth_metrics_by_area(
    df: pd.DataFrame,
    price_col: str = None,
    group_col: str = "planning_area",
    date_col: str = "month"
) -> pd.DataFrame:
    """Calculate month-over-month and year-over-year growth metrics.

    Args:
        df: Transaction DataFrame with monthly data
        price_col: Price column name (auto-detected if None)
        group_col: Grouping column (planning_area)
        date_col: Date column (month)

    Returns:
        DataFrame with growth metrics
    """
    logger.info("Calculating growth metrics by planning area...")

    # Auto-detect price column
    if price_col is None:
        price_col = "resale_price" if "resale_price" in df.columns else "price"

    # First, aggregate to monthly level if needed
    if date_col not in df.columns:
        if "transaction_date" in df.columns:
            df = df.copy()
            df[date_col] = df["transaction_date"].dt.to_period("M").astype(str)
        else:
            logger.warning("Cannot calculate growth: no date column available")
            return pd.DataFrame()

    # Group by area and month, calculate median price
    if group_col not in df.columns:
        logger.warning(f"Group column '{group_col}' not found")
        return pd.DataFrame()

    if price_col not in df.columns:
        logger.warning(f"Price column '{price_col}' not found")
        return pd.DataFrame()

    monthly_prices = df.groupby([group_col, date_col])[price_col].median().reset_index()
    monthly_prices = monthly_prices.sort_values([group_col, date_col])

    # Calculate growth rates
    monthly_prices["mom_change_pct"] = monthly_prices.groupby(group_col)[price_col].transform(
        lambda x: x.pct_change() * 100
    )

    monthly_prices["yoy_change_pct"] = monthly_prices.groupby(group_col)[price_col].transform(
        lambda x: x.pct_change(12) * 100
    )

    # Calculate momentum
    monthly_prices["growth_3m"] = monthly_prices.groupby(group_col)[price_col].transform(
        lambda x: x.pct_change(3) * 100
    )
    monthly_prices["growth_12m"] = monthly_prices.groupby(group_col)[price_col].transform(
        lambda x: x.pct_change(12) * 100
    )
    monthly_prices["momentum"] = monthly_prices["growth_3m"] - monthly_prices["growth_12m"]

    # Add momentum signal
    monthly_prices["momentum_signal"] = pd.cut(
        monthly_prices["momentum"],
        bins=[-float("inf"), -5, -2, 2, 5, float("inf")],
        labels=[
            "Strong Deceleration",
            "Moderate Deceleration",
            "Stable",
            "Moderate Acceleration",
            "Strong Acceleration"
        ]
    )

    logger.info(f"  Created growth metrics with {len(monthly_prices):,} records")

    return monthly_prices


def calculate_rental_yield_by_area(
    df: pd.DataFrame,
    group_by: list = ["planning_area"]
) -> pd.DataFrame:
    """Calculate rental yield statistics by planning area.

    Args:
        df: Transaction DataFrame with rental_yield_pct column
        group_by: Columns to group by

    Returns:
        DataFrame with rental yield metrics
    """
    logger.info("Calculating rental yield metrics by planning area...")

    if "rental_yield_pct" not in df.columns:
        logger.warning("rental_yield_pct column not found, skipping rental yield calculations")
        return pd.DataFrame()

    # Filter to records with rental yield data
    yield_df = df[df["rental_yield_pct"].notna()].copy()

    if yield_df.empty:
        logger.warning("No rental yield data available")
        return pd.DataFrame()

    # Adjust group_by based on available columns
    available_group_cols = [c for c in group_by if c in yield_df.columns]

    # Calculate yield statistics
    yield_stats = yield_df.groupby(available_group_cols)["rental_yield_pct"].agg([
        ("count", "count"),
        ("mean", "mean"),
        ("median", "median"),
        ("std", "std"),
        ("min", "min"),
        ("max", "max")
    ]).reset_index()

    # Filter to areas with sufficient data (>= 10 records)
    yield_stats = yield_stats[yield_stats["count"] >= 10]

    logger.info(f"  Created rental yield metrics for {len(yield_stats)} areas")

    return yield_stats


def calculate_affordability_by_area(
    df: pd.DataFrame,
    income_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """Calculate affordability metrics by planning area.

    Args:
        df: Transaction DataFrame with prices
        income_df: Optional DataFrame with estimated income by planning area

    Returns:
        DataFrame with affordability metrics
    """
    logger.info("Calculating affordability metrics by planning area...")

    # Auto-detect price column
    price_col = "resale_price" if "resale_price" in df.columns else "price"

    if "planning_area" not in df.columns or price_col not in df.columns:
        logger.warning("Missing required columns for affordability calculation")
        return pd.DataFrame()

    # Calculate median price by planning area
    area_prices = df.groupby("planning_area")[price_col].median().reset_index()
    area_prices.columns = ["planning_area", "median_price"]

    # If no income data provided, try to load it
    if income_df is None:
        try:
            income_df = load_parquet("L3_income_estimates")
        except Exception:
            logger.warning("Income estimates not available, using national median")
            # Use national median household income (approx SGD 90,000)
            area_prices["estimated_annual_income"] = 90000
            income_df = None

    if income_df is not None and "estimated_median_annual_income" in income_df.columns:
        # Merge with income data
        area_prices = area_prices.merge(
            income_df[["planning_area", "estimated_median_annual_income"]],
            on="planning_area",
            how="left"
        )
        # Fill missing with national median
        area_prices["estimated_annual_income"] = area_prices["estimated_annual_income"].fillna(90000)

    # Calculate affordability metrics
    area_prices["affordability_ratio"] = area_prices["median_price"] / area_prices["estimated_annual_income"]

    # Classify affordability
    def classify_affordability(ratio):
        if ratio < 3.0:
            return "Affordable"
        elif ratio < 5.0:
            return "Moderate"
        elif ratio < 7.0:
            return "Expensive"
        else:
            return "Severely Unaffordable"

    area_prices["affordability_class"] = area_prices["affordability_ratio"].apply(classify_affordability)

    # Calculate mortgage payment
    area_prices["monthly_mortgage"] = area_prices["median_price"].apply(
        lambda price: metrics_module.calculate_mortgage_payment(price)
    )

    area_prices["mortgage_to_income_pct"] = (
        area_prices["monthly_mortgage"] * 12 / area_prices["estimated_annual_income"] * 100
    )

    logger.info(f"  Created affordability metrics for {len(area_prices)} planning areas")

    return area_prices


def identify_appreciation_hotspots(
    growth_df: pd.DataFrame,
    consistency_threshold: float = 0.7,
    min_years: int = 3
) -> pd.DataFrame:
    """Identify planning areas with consistently high appreciation.

    Args:
        growth_df: DataFrame with yoy_change_pct column
        consistency_threshold: Minimum proportion of years with positive growth
        min_years: Minimum number of years of data required

    Returns:
        DataFrame with hotspot classifications
    """
    logger.info("Identifying appreciation hotspots...")

    if "planning_area" not in growth_df.columns or "yoy_change_pct" not in growth_df.columns:
        logger.warning("Missing required columns for hotspot identification")
        return pd.DataFrame()

    # Filter to recent data (last 3 years)
    if "year" in growth_df.columns:
        recent_years = growth_df["year"].max() - min_years + 1
        recent_data = growth_df[growth_df["year"] >= recent_years].copy()
    else:
        recent_data = growth_df.copy()

    # Calculate statistics by planning area
    hotspots = recent_data.groupby("planning_area").agg({
        "yoy_change_pct": ["mean", "median", "std", "count"]
    }).reset_index()

    hotspots.columns = ["planning_area", "mean_yoy", "median_yoy", "std_yoy", "years"]

    # Filter to areas with sufficient data
    hotspots = hotspots[hotspots["years"] >= min_years]

    if hotspots.empty:
        logger.warning("No areas meet minimum data requirements")
        return pd.DataFrame()

    # Calculate consistency (% of years with positive growth)
    positive_growth = recent_data[recent_data["yoy_change_pct"] > 0].groupby("planning_area").size()
    total_years = recent_data.groupby("planning_area").size()

    consistency = (positive_growth / total_years).fillna(0).reset_index()
    consistency.columns = ["planning_area", "consistency"]

    hotspots = hotspots.merge(consistency, on="planning_area")

    # Categorize hotspots
    def categorize_hotspot(row):
        if row["consistency"] >= consistency_threshold and row["mean_yoy"] > 10:
            return "Elite Hotspot"
        elif row["consistency"] >= 0.5 and row["mean_yoy"] > 5:
            return "High Growth"
        elif row["mean_yoy"] > 0:
            return "Moderate Growth"
        else:
            return "Low Growth"

    hotspots["category"] = hotspots.apply(categorize_hotspot, axis=1)

    logger.info(f"  Identified {len(hotspots)} appreciation hotspots")

    return hotspots


def run_metrics_pipeline(
    calculate_affordability: bool = True,
    min_records_threshold: int = 10
) -> Dict:
    """Run complete L5 metrics pipeline.

    Args:
        calculate_affordability: Whether to calculate affordability metrics
        min_records_threshold: Minimum records required for area-level stats

    Returns:
        Dictionary with pipeline results and output DataFrames
    """
    logger.info("=" * 60)
    logger.info("L5 Metrics Pipeline")
    logger.info("=" * 60)

    results = {}

    # Load data
    df = load_unified_data()

    if df.empty:
        logger.error("No data available for metrics calculation")
        return results

    results["total_records"] = len(df)

    # 1. Calculate price metrics
    price_metrics = calculate_price_metrics_by_area(df)
    if not price_metrics.empty:
        save_parquet(price_metrics, "L5_price_metrics_by_area", source="L5 metrics pipeline")
        results["price_metrics"] = len(price_metrics)

    # 2. Calculate volume metrics
    volume_metrics = calculate_volume_metrics_by_area(df)
    if not volume_metrics.empty:
        save_parquet(volume_metrics, "L5_volume_metrics_by_area", source="L5 metrics pipeline")
        results["volume_metrics"] = len(volume_metrics)

    # 3. Calculate growth metrics
    growth_metrics = calculate_growth_metrics_by_area(df)
    if not growth_metrics.empty:
        save_parquet(growth_metrics, "L5_growth_metrics_by_area", source="L5 metrics pipeline")
        results["growth_metrics"] = len(growth_metrics)

    # 4. Calculate rental yield
    rental_yield = calculate_rental_yield_by_area(df)
    if not rental_yield.empty:
        save_parquet(rental_yield, "L5_rental_yield_by_area", source="L5 metrics pipeline")
        results["rental_yield"] = len(rental_yield)

    # 5. Calculate affordability
    if calculate_affordability:
        affordability = calculate_affordability_by_area(df)
        if not affordability.empty:
            save_parquet(affordability, "L5_affordability_by_area", source="L5 metrics pipeline")
            results["affordability"] = len(affordability)

    # 6. Identify hotspots
    if not growth_metrics.empty:
        hotspots = identify_appreciation_hotspots(growth_metrics)
        if not hotspots.empty:
            save_parquet(hotspots, "L5_appreciation_hotspots", source="L5 metrics pipeline")
            results["hotspots"] = len(hotspots)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("✅ L5 Metrics Pipeline Complete!")
    logger.info(f"  Total records processed: {results.get('total_records', 0):,}")
    logger.info(f"  Price metrics: {results.get('price_metrics', 0):,} records")
    logger.info(f"  Volume metrics: {results.get('volume_metrics', 0):,} records")
    logger.info(f"  Growth metrics: {results.get('growth_metrics', 0):,} records")
    logger.info(f"  Rental yield: {results.get('rental_yield', 0)} areas")
    logger.info(f"  Affordability: {results.get('affordability', 0)} areas")
    logger.info(f"  Hotspots: {results.get('hotspots', 0)} areas")
    logger.info("=" * 60)

    return results


def main():
    """Main entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Run L5 metrics pipeline")
    parser.add_argument(
        "--skip-affordability",
        action="store_true",
        help="Skip affordability calculations (requires income data)"
    )

    args = parser.parse_args()

    run_metrics_pipeline(calculate_affordability=not args.skip_affordability)


if __name__ == "__main__":
    main()
