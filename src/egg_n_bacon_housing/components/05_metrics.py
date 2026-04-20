"""05_metrics: Planning area metrics computation (Hamilton DAG node).

This module provides Hamilton-compatible functions for computing
planning-area-level metrics from the platinum layer.
"""

import logging
from pathlib import Path

import pandas as pd

from egg_n_bacon_housing.config import settings

logger = logging.getLogger(__name__)


def platinum_metrics_dir() -> Path:
    """Platinum layer metrics subdirectory."""
    return settings.data_dir / "04_platinum" / "metrics"


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

    df = unified_dataset.copy()

    if "month" not in df.columns and "transaction_date" in df.columns:
        df["month"] = pd.to_datetime(df["transaction_date"]).dt.to_period("M").astype(str)

    if "month" not in df.columns:
        df["month"] = "2025-01"

    metrics = (
        df.groupby(["planning_area", "month"])
        .agg(
            median_price=("price", "median"),
            mean_price=("price", "mean"),
            transaction_count=("price", "count"),
            avg_psf=("psf", "mean")
            if "psf" in df.columns
            else ("price", lambda x: x.median() / 1000),
        )
        .reset_index()
    )

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

    df = unified_dataset.copy()

    if "planning_area" not in df.columns:
        return pd.DataFrame()

    if "month" not in df.columns and "transaction_date" in df.columns:
        df["month"] = pd.to_datetime(df["transaction_date"]).dt.to_period("M").astype(str)

    if "month" not in df.columns:
        df["month"] = "2025-01"

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

    df = unified_dataset.copy()

    if "month" not in df.columns and "transaction_date" in df.columns:
        df["month"] = pd.to_datetime(df["transaction_date"]).dt.to_period("M").astype(str)

    if "month" not in df.columns:
        df["month"] = "2025-01"

    metrics = (
        df.groupby(["planning_area", "month"])
        .agg(
            median_price=("price", "median"),
            transaction_count=("price", "count"),
        )
        .reset_index()
    )

    estimated_income = 85000
    metrics["affordability_ratio"] = metrics["median_price"] / estimated_income

    def classify_affordability(ratio):
        if ratio < 5:
            return "Affordable"
        elif ratio < 7:
            return "Moderate"
        elif ratio < 9:
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

    if "median_price" in df.columns:
        df = df.sort_values(["planning_area", "month"])
        df["appreciation_3m_pct"] = df.groupby("planning_area")["median_price"].pct_change(3) * 100
        df["appreciation_12m_pct"] = (
            df.groupby("planning_area")["median_price"].pct_change(12) * 100
        )

        hotspots = df.dropna(subset=["appreciation_3m_pct"]).copy()
        hotspots = hotspots[hotspots["appreciation_3m_pct"] > 0]

        if len(hotspots) > 0:
            hotspots = hotspots.sort_values("appreciation_3m_pct", ascending=False).head(20)

        platinum_metrics_dir().mkdir(parents=True, exist_ok=True)
        out_path = platinum_metrics_dir() / "L5_appreciation_hotspots.parquet"
        hotspots.to_parquet(out_path, index=False)
        logger.info(f"Saved {len(hotspots)} appreciation hotspot records")

        return hotspots

    return pd.DataFrame()
