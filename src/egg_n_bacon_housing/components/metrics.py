"""Metrics: Planning area metrics computation (Hamilton DAG node).

This module provides Hamilton-compatible functions for computing
planning-area-level metrics from the enriched transaction layer.
"""

import logging

import numpy as np
import pandas as pd
from hamilton.function_modifiers import extract_fields, hamilton_exclude

from egg_n_bacon_housing.config import AFFORDABILITY_THRESHOLD_DEFAULTS
from egg_n_bacon_housing.schemas.platinum_models import AppreciationHotspot, PaMonthlyMetric
from egg_n_bacon_housing.utils.time_index import ensure_month_column
from egg_n_bacon_housing.utils.validation_gateway import (
    empty_extracted,
    extracted_validation,
    validate_and_quarantine,
)

logger = logging.getLogger(__name__)


@hamilton_exclude
def pa_monthly_metrics(*args, **kwargs) -> pd.DataFrame:
    result = validate_pa_monthly_metrics(*args, **kwargs)
    if isinstance(result, pd.DataFrame):
        return result
    if not result["pa_monthly_metrics_quarantine"].empty:
        logger.warning(
            "pa_monthly_metrics: %s PA-month row(s) quarantined",
            len(result["pa_monthly_metrics_quarantine"]),
        )
    return result["pa_monthly_metrics"]


@hamilton_exclude
def appreciation_hotspots(*args, **kwargs) -> pd.DataFrame:
    return validate_appreciation_hotspots(*args, **kwargs)["appreciation_hotspots"]


@extract_fields({"pa_monthly_metrics": pd.DataFrame, "pa_monthly_metrics_quarantine": pd.DataFrame})
def validate_pa_monthly_metrics(
    transactions_enriched: pd.DataFrame,
    median_household_income: int = 85000,
    affordability_thresholds: dict[str, float] | None = None,
) -> dict[str, pd.DataFrame]:
    """Compute a single PA x month time series with all metrics.

    Replaces price_metrics_by_area, rental_yield_by_area, and
    affordability_metrics with one unified aggregation.

    Args:
        transactions_enriched: Full enriched transactions from features.
        median_household_income: Fallback annual income for affordability.
        affordability_thresholds: Optional thresholds dict for classification.

    Returns:
        DataFrame with PA x month metrics (~5K rows).
    """
    if transactions_enriched.empty:
        return empty_extracted(
            transactions_enriched, "pa_monthly_metrics", "pa_monthly_metrics_quarantine"
        )

    if (
        "planning_area" not in transactions_enriched.columns
        or "price" not in transactions_enriched.columns
    ):
        logger.warning("pa_monthly_metrics: missing planning_area or price")
        return empty_extracted(
            transactions_enriched, "pa_monthly_metrics", "pa_monthly_metrics_quarantine"
        )

    df = ensure_month_column(transactions_enriched.copy())
    if df.empty:
        return empty_extracted(df, "pa_monthly_metrics", "pa_monthly_metrics_quarantine")

    pre_pa_filter = len(df)
    df = df[df["planning_area"].notna()]
    dropped_null_pa = pre_pa_filter - len(df)
    if dropped_null_pa:
        logger.warning(
            "pa_monthly_metrics: dropped %s row(s) with null planning_area; kept %s",
            dropped_null_pa,
            len(df),
        )

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
    # Vectorized classification (np.select) — same semantics as the per-row
    # apply it replaced: strict less-than banding against the thresholds, so
    # a ratio exactly on a threshold lands in the next band up, and a NaN
    # ratio fails every comparison and falls through to the default band.
    thresholds = (
        affordability_thresholds
        if affordability_thresholds is not None
        else AFFORDABILITY_THRESHOLD_DEFAULTS
    )
    ratio = metrics["affordability_ratio"]
    metrics["affordability_class"] = np.select(
        condlist=[
            ratio < thresholds["affordable"],
            ratio < thresholds["moderate"],
            ratio < thresholds["expensive"],
        ],
        choicelist=["Affordable", "Moderate", "Expensive"],
        default="Severely Unaffordable",
    )

    # Small table (~5K rows) — always full validation; persistence is owned by
    # materialize_pa_monthly_metrics.
    validated = validate_and_quarantine(metrics, PaMonthlyMetric, "pa_monthly_metrics")
    # Keep the computation easy to isolate in unit tests that deliberately
    # bypass schema validation; production always receives ValidationResult.
    if isinstance(validated, pd.DataFrame):
        return validated
    logger.info("pa_monthly_metrics: %s PA-month rows", len(validated["valid"]))
    return extracted_validation(validated, "pa_monthly_metrics", "pa_monthly_metrics_quarantine")


@extract_fields(
    {"appreciation_hotspots": pd.DataFrame, "appreciation_hotspots_quarantine": pd.DataFrame}
)
def validate_appreciation_hotspots(
    pa_monthly_metrics: pd.DataFrame,
    min_transactions_for_hotspot: int = 5,
) -> dict[str, pd.DataFrame]:
    """Identify price appreciation hotspots from PA monthly metrics.

    Months with fewer than ``min_transactions_for_hotspot`` transactions are
    dropped BEFORE ffill/pct_change so a low-volume spike can neither rank as
    a hotspot nor distort the comparison base of later months (the floor
    applies to both the ranked month and the pct_change base month). Defaults
    to 5; override via ``Settings.MetricsConfig.min_transactions_for_hotspot``
    (env: ``METRICS__MIN_TRANSACTIONS_FOR_HOTSPOT``), which the pipeline
    injects into this node.

    Args:
        pa_monthly_metrics: Output from pa_monthly_metrics.
        min_transactions_for_hotspot: Minimum transaction_count per PA-month.

    Returns:
        DataFrame with appreciation hotspot rankings (top 20).
    """
    if pa_monthly_metrics.empty:
        return empty_extracted(
            pa_monthly_metrics, "appreciation_hotspots", "appreciation_hotspots_quarantine"
        )

    df = pa_monthly_metrics.copy()

    if "median_price" not in df.columns:
        return empty_extracted(df, "appreciation_hotspots", "appreciation_hotspots_quarantine")

    # Volume floor before ffill/pct_change: floored months are excluded from
    # the ranking AND from the ffilled comparison base. Frames without a
    # transaction_count column (e.g. synthetic standalone inputs) skip the
    # floor; production input from pa_monthly_metrics always carries it.
    if "transaction_count" in df.columns:
        eligible = df["transaction_count"] >= min_transactions_for_hotspot
        floored = int((~eligible).sum())
        if floored:
            logger.info(
                "appreciation_hotspots: floored %s (planning_area, month) row(s) "
                "below transaction_count >= %s",
                floored,
                min_transactions_for_hotspot,
            )
        df = df[eligible]
        if df.empty:
            return empty_extracted(df, "appreciation_hotspots", "appreciation_hotspots_quarantine")

    df["month_period"] = pd.PeriodIndex(df["month"], freq="M")
    df = df.sort_values(["planning_area", "month_period"])

    all_months = pd.period_range(df["month_period"].min(), df["month_period"].max(), freq="M")
    # Per planning area, construct the output frame straight from the reindexed
    # / pct-change Series with a boolean mask, instead of appending one dict per
    # period with Series.get() lookups (~5k PA-month rows). The per-PA groupby
    # stays because each area is reindexed+ffilled against the full month range.
    parts: list[pd.DataFrame] = []
    for pa, group in df.groupby("planning_area"):
        reindexed = group.set_index("month_period")["median_price"].reindex(all_months).ffill()
        if len(reindexed.dropna()) < 2:
            continue
        pct_3m = reindexed.pct_change(3) * 100
        pct_12m = reindexed.pct_change(12) * 100
        keep = pct_3m.notna()
        if not keep.any():
            continue
        parts.append(
            pd.DataFrame(
                {
                    "planning_area": pa,
                    "month": [str(p) for p in reindexed.index[keep]],
                    "median_price": reindexed[keep].to_numpy(),
                    "appreciation_3m_pct": pct_3m[keep].to_numpy(),
                    "appreciation_12m_pct": pct_12m[keep].to_numpy(),
                }
            )
        )

    if not parts:
        return empty_extracted(
            pa_monthly_metrics, "appreciation_hotspots", "appreciation_hotspots_quarantine"
        )

    hotspots = pd.concat(parts, ignore_index=True)
    hotspots = hotspots.dropna(subset=["appreciation_3m_pct"])
    hotspots["is_declining"] = hotspots["appreciation_3m_pct"] < 0

    hotspots = hotspots.sort_values("appreciation_3m_pct", ascending=False).head(20)

    # Small table (top 20) — always full validation; persistence is owned by
    # materialize_appreciation_hotspots.
    return extracted_validation(
        validate_and_quarantine(hotspots, AppreciationHotspot, "appreciation_hotspots"),
        "appreciation_hotspots",
        "appreciation_hotspots_quarantine",
    )
