"""05_metrics: Planning area metrics computation (Hamilton DAG node).

This module provides Hamilton-compatible functions for computing
planning-area-level metrics from the platinum layer.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from egg_n_bacon_housing.utils.io_helpers import save_parquet
from egg_n_bacon_housing.utils.layer_writer import LayerWriter
from egg_n_bacon_housing.utils.metrics import classify_affordability
from egg_n_bacon_housing.utils.time_index import ensure_month_column

logger = logging.getLogger(__name__)


def price_metrics_by_area(
    unified_dataset: pd.DataFrame,
    platinum_dir: Path,
    writer: LayerWriter | None = None,
) -> pd.DataFrame:
    """Compute price metrics by planning area and month.

    Args:
        unified_dataset: Full unified dataset.

    Returns:
        DataFrame with price metrics.
    """
    if unified_dataset.empty:
        return pd.DataFrame()

    required_cols = ["price", "planning_area"]
    if not all(c in unified_dataset.columns for c in required_cols):
        logger.warning("Missing required columns for price metrics")
        return pd.DataFrame()

    df = ensure_month_column(unified_dataset.copy())
    if df.empty:
        return pd.DataFrame()

    agg_spec = {
        "median_price": ("price", "median"),
        "mean_price": ("price", "mean"),
        "transaction_count": ("price", "count"),
    }
    if "psf" in df.columns:
        agg_spec["avg_psf"] = ("psf", "mean")

    metrics = df.groupby(["planning_area", "month"]).agg(**agg_spec).reset_index()

    if writer is not None:
        writer.write(metrics, "L5_price_metrics_by_area", "platinum_metrics")
    else:
        save_parquet(
            metrics, platinum_dir / "metrics" / "L5_price_metrics_by_area.parquet", "price metrics"
        )

    return metrics


def rental_yield_by_area(
    unified_dataset: pd.DataFrame,
    platinum_dir: Path,
    writer: LayerWriter | None = None,
) -> pd.DataFrame:
    """Compute rental yield metrics by planning area.

    Args:
        unified_dataset: Full unified dataset.

    Returns:
        DataFrame with rental yield metrics.
    """
    if unified_dataset.empty:
        return pd.DataFrame()

    if "rental_yield_pct" not in unified_dataset.columns:
        logger.warning("No rental yield data available")
        return pd.DataFrame()

    df = ensure_month_column(unified_dataset.copy())
    if df.empty:
        return pd.DataFrame()

    if "planning_area" not in df.columns:
        return pd.DataFrame()

    metrics = (
        df.groupby(["planning_area", "month"])
        .agg(
            median_rental_yield=("rental_yield_pct", "median"),
            avg_rental_yield=("rental_yield_pct", "mean"),
            count=("rental_yield_pct", "count"),
        )
        .reset_index()
    )

    if writer is not None:
        writer.write(metrics, "L5_rental_yield_by_area", "platinum_metrics")
    else:
        save_parquet(
            metrics,
            platinum_dir / "metrics" / "L5_rental_yield_by_area.parquet",
            "rental yield metrics",
        )

    return metrics


def affordability_metrics(
    unified_dataset: pd.DataFrame,
    platinum_dir: Path,
    writer: LayerWriter | None = None,
    median_household_income: int = 85000,
) -> pd.DataFrame:
    """Compute affordability metrics by planning area.

    Uses per-planning-area median income from Census data if available,
    falling back to the global median_household_income parameter.

    Args:
        unified_dataset: Full unified dataset (includes median_monthly_income).
        median_household_income: Fallback annual income (default 85000).

    Returns:
        DataFrame with affordability metrics.
    """
    if unified_dataset.empty:
        return pd.DataFrame()

    if "planning_area" not in unified_dataset.columns:
        return pd.DataFrame()

    df = ensure_month_column(unified_dataset.copy())
    if df.empty:
        return pd.DataFrame()

    agg_spec = {
        "median_price": ("price", "median"),
        "transaction_count": ("price", "count"),
    }
    if "median_monthly_income" in df.columns:
        agg_spec["median_monthly_income"] = ("median_monthly_income", "mean")

    metrics = df.groupby(["planning_area", "month"]).agg(**agg_spec).reset_index()

    if "median_monthly_income" in metrics.columns:
        annual_income = metrics["median_monthly_income"] * 12
        annual_income = annual_income.where(annual_income > 0, median_household_income)
    else:
        annual_income = median_household_income
    metrics["affordability_ratio"] = metrics["median_price"] / annual_income

    metrics["affordability_class"] = metrics["affordability_ratio"].apply(classify_affordability)

    if writer is not None:
        writer.write(metrics, "L5_affordability_by_area", "platinum_metrics")
    else:
        save_parquet(
            metrics,
            platinum_dir / "metrics" / "L5_affordability_by_area.parquet",
            "affordability metrics",
        )

    return metrics


def appreciation_hotspots(
    price_metrics_by_area: pd.DataFrame,
    platinum_dir: Path,
    writer: LayerWriter | None = None,
) -> pd.DataFrame:
    """Identify price appreciation hotspots.

    Args:
        price_metrics_by_area: Output from price_metrics_by_area.

    Returns:
        DataFrame with appreciation hotspot rankings.
    """
    if price_metrics_by_area.empty:
        return pd.DataFrame()

    df = price_metrics_by_area.copy()

    if "median_price" not in df.columns:
        return pd.DataFrame()

    df["month_period"] = pd.PeriodIndex(df["month"], freq="M")
    df = df.sort_values(["planning_area", "month_period"])

    all_months = pd.period_range(df["month_period"].min(), df["month_period"].max(), freq="M")
    records = []
    for pa, group in df.groupby("planning_area"):
        reindexed = group.set_index("month_period")["median_price"].reindex(all_months).ffill()
        if len(reindexed.dropna()) < 2:
            continue
        pct_3m = reindexed.pct_change(3) * 100
        pct_12m = reindexed.pct_change(12) * 100
        for period in reindexed.index:
            if pd.isna(pct_3m.get(period, np.nan)):
                continue
            records.append(
                {
                    "planning_area": pa,
                    "month": str(period),
                    "median_price": reindexed.get(period),
                    "appreciation_3m_pct": pct_3m.get(period),
                    "appreciation_12m_pct": pct_12m.get(period),
                }
            )

    if not records:
        return pd.DataFrame()

    hotspots = pd.DataFrame(records)
    hotspots = hotspots.dropna(subset=["appreciation_3m_pct"])
    hotspots["is_declining"] = hotspots["appreciation_3m_pct"] < 0

    hotspots = hotspots.sort_values("appreciation_3m_pct", ascending=False).head(20)

    if writer is not None:
        writer.write(hotspots, "L5_appreciation_hotspots", "platinum_metrics")
    else:
        save_parquet(
            hotspots,
            platinum_dir / "metrics" / "L5_appreciation_hotspots.parquet",
            "appreciation hotspots",
        )

    return hotspots
