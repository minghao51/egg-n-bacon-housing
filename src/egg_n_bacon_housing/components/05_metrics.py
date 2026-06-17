"""05_metrics: Planning area metrics computation (Hamilton DAG node).

This module provides Hamilton-compatible functions for computing
planning-area-level metrics from the enriched transaction layer.
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


def pa_monthly_metrics(
    transactions_enriched: pd.DataFrame,
    platinum_dir: Path,
    writer: LayerWriter | None = None,
    median_household_income: int = 85000,
) -> pd.DataFrame:
    """Compute a single PA x month time series with all metrics.

    Replaces price_metrics_by_area, rental_yield_by_area, and
    affordability_metrics with one unified aggregation.

    Args:
        transactions_enriched: Full enriched transactions from 03_features.
        median_household_income: Fallback annual income for affordability.

    Returns:
        DataFrame with PA x month metrics (~5K rows).
    """
    if transactions_enriched.empty:
        return pd.DataFrame()

    if (
        "planning_area" not in transactions_enriched.columns
        or "price" not in transactions_enriched.columns
    ):
        logger.warning("pa_monthly_metrics: missing planning_area or price")
        return pd.DataFrame()

    df = ensure_month_column(transactions_enriched.copy())
    if df.empty:
        return pd.DataFrame()

    df = df[df["planning_area"].notna()]

    agg_spec: dict[str, tuple] = {
        "median_price": ("price", "median"),
        "mean_price": ("price", "mean"),
        "transaction_count": ("price", "count"),
    }
    if "psf" in df.columns:
        agg_spec["avg_psf"] = ("psf", "mean")
    if "rental_yield_pct" in df.columns:
        agg_spec["median_rental_yield"] = ("rental_yield_pct", "median")
        agg_spec["avg_rental_yield"] = ("rental_yield_pct", "mean")
    if "median_monthly_income" in df.columns:
        agg_spec["median_monthly_income"] = ("median_monthly_income", "mean")

    metrics = df.groupby(["planning_area", "month"]).agg(**agg_spec).reset_index()

    if "median_monthly_income" in metrics.columns:
        annual_income = metrics["median_monthly_income"] * 12
        annual_income = annual_income.where(annual_income > 0, median_household_income)
    else:
        annual_income = float(median_household_income)
    metrics["affordability_ratio"] = metrics["median_price"] / annual_income
    metrics["affordability_class"] = metrics["affordability_ratio"].apply(classify_affordability)

    if writer is not None:
        writer.write(metrics, "pa_monthly_metrics", "platinum_metrics")
    else:
        save_parquet(
            metrics,
            platinum_dir / "metrics" / "pa_monthly_metrics.parquet",
            "PA monthly metrics",
        )

    logger.info("pa_monthly_metrics: %s PA-month rows", len(metrics))
    return metrics


def appreciation_hotspots(
    pa_monthly_metrics: pd.DataFrame,
    platinum_dir: Path,
    writer: LayerWriter | None = None,
) -> pd.DataFrame:
    """Identify price appreciation hotspots from PA monthly metrics.

    Args:
        pa_monthly_metrics: Output from pa_monthly_metrics.

    Returns:
        DataFrame with appreciation hotspot rankings (top 20).
    """
    if pa_monthly_metrics.empty:
        return pd.DataFrame()

    df = pa_monthly_metrics.copy()

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
