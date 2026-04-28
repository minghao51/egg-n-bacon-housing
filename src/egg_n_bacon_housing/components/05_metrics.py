"""05_metrics: Planning area metrics computation (Hamilton DAG node).

This module provides Hamilton-compatible functions for computing
planning-area-level metrics from the platinum layer.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from egg_n_bacon_housing.config import settings

logger = logging.getLogger(__name__)


def platinum_metrics_dir() -> Path:
    """Platinum layer metrics subdirectory."""
    return settings.platinum_dir / "metrics"


def _ensure_month_column(df: pd.DataFrame) -> pd.DataFrame:
    """Derive a month column from transaction_date, or return empty if impossible."""
    if "month" not in df.columns and "transaction_date" in df.columns:
        df["month"] = pd.to_datetime(df["transaction_date"]).dt.to_period("M").astype(str)

    if "month" not in df.columns:
        logger.error("No month or transaction_date column -- cannot compute metrics")
        return pd.DataFrame()

    return df


def price_metrics_by_area(unified_dataset: pd.DataFrame) -> pd.DataFrame:
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

    df = _ensure_month_column(unified_dataset.copy())
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

    platinum_metrics_dir().mkdir(parents=True, exist_ok=True)
    out_path = platinum_metrics_dir() / "L5_price_metrics_by_area.parquet"
    metrics.to_parquet(out_path, index=False)
    logger.info(f"Saved {len(metrics)} price metrics records")

    return metrics


def rental_yield_by_area(unified_dataset: pd.DataFrame) -> pd.DataFrame:
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

    df = _ensure_month_column(unified_dataset.copy())
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

    platinum_metrics_dir().mkdir(parents=True, exist_ok=True)
    out_path = platinum_metrics_dir() / "L5_rental_yield_by_area.parquet"
    metrics.to_parquet(out_path, index=False)
    logger.info(f"Saved {len(metrics)} rental yield metrics records")

    return metrics


def affordability_metrics(unified_dataset: pd.DataFrame) -> pd.DataFrame:
    """Compute affordability metrics by planning area.

    Args:
        unified_dataset: Full unified dataset.

    Returns:
        DataFrame with affordability metrics.
    """
    if unified_dataset.empty:
        return pd.DataFrame()

    if "planning_area" not in unified_dataset.columns:
        return pd.DataFrame()

    df = _ensure_month_column(unified_dataset.copy())
    if df.empty:
        return pd.DataFrame()

    metrics = (
        df.groupby(["planning_area", "month"])
        .agg(
            median_price=("price", "median"),
            transaction_count=("price", "count"),
        )
        .reset_index()
    )

    estimated_income = settings.metrics.median_household_income
    metrics["affordability_ratio"] = metrics["median_price"] / estimated_income

    thresholds = settings.metrics.affordability_thresholds

    def classify_affordability(ratio):
        if ratio < thresholds["affordable"]:
            return "Affordable"
        elif ratio < thresholds["moderate"]:
            return "Moderate"
        elif ratio < thresholds["expensive"]:
            return "Expensive"
        return "Severely Unaffordable"

    metrics["affordability_class"] = metrics["affordability_ratio"].apply(classify_affordability)

    platinum_metrics_dir().mkdir(parents=True, exist_ok=True)
    out_path = platinum_metrics_dir() / "L5_affordability_by_area.parquet"
    metrics.to_parquet(out_path, index=False)
    logger.info(f"Saved {len(metrics)} affordability metrics records")

    return metrics


def appreciation_hotspots(price_metrics_by_area: pd.DataFrame) -> pd.DataFrame:
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
    hotspots = hotspots[hotspots["appreciation_3m_pct"] > 0]

    if len(hotspots) > 0:
        hotspots = hotspots.sort_values("appreciation_3m_pct", ascending=False).head(20)

    platinum_metrics_dir().mkdir(parents=True, exist_ok=True)
    out_path = platinum_metrics_dir() / "L5_appreciation_hotspots.parquet"
    hotspots.to_parquet(out_path, index=False)
    logger.info(f"Saved {len(hotspots)} appreciation hotspot records")

    return hotspots
