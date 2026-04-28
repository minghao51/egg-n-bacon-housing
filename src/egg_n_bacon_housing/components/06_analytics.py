"""06_analytics: Analytics orchestration (Hamilton DAG node).

This module provides Hamilton-compatible functions for running analytics
on the platinum layer data. Analytics are organized by domain.

Note: Analytics scripts are primarily batch jobs that run after pipeline
completion. This component provides lightweight integration points.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from egg_n_bacon_housing.config import settings

logger = logging.getLogger(__name__)


def analytics_dir() -> Path:
    """Analytics output directory."""
    return settings.data_dir / "analytics"


def run_market_analysis(unified_dataset: pd.DataFrame) -> dict:
    """Run market analysis on unified dataset.

    Args:
        unified_dataset: Full unified dataset.

    Returns:
        Dictionary with analysis results.
    """
    results: dict[str, Any] = {}

    if unified_dataset.empty:
        return results

    required = ["price", "property_type"]
    if not all(c in unified_dataset.columns for c in required):
        return results

    for ptype in unified_dataset["property_type"].unique():
        subset = unified_dataset[unified_dataset["property_type"] == ptype]
        results[ptype] = {
            "count": len(subset),
            "median_price": float(subset["price"].median()),
            "mean_price": float(subset["price"].mean()),
            "std_price": float(subset["price"].std()),
        }

        if "psf" in subset.columns:
            results[ptype]["median_psf"] = float(subset["psf"].median())

    return results


def run_spatial_analysis(unified_dataset: pd.DataFrame) -> dict:
    """Run spatial autocorrelation analysis.

    Args:
        unified_dataset: Full unified dataset.

    Returns:
        Dictionary with spatial analysis results.
    """
    results: dict[str, Any] = {}

    if unified_dataset.empty:
        return results

    if not all(c in unified_dataset.columns for c in ["lat", "lon", "price"]):
        return results

    if len(unified_dataset) < 30:
        results["warning"] = "Insufficient data for spatial analysis"
        return results

    results["data_points"] = len(unified_dataset)
    results["lat_range"] = {
        "min": float(unified_dataset["lat"].min()),
        "max": float(unified_dataset["lat"].max()),
    }
    results["lon_range"] = {
        "min": float(unified_dataset["lon"].min()),
        "max": float(unified_dataset["lon"].max()),
    }

    return results


def run_appreciation_analysis(appreciation_hotspots: pd.DataFrame) -> dict:
    """Run price appreciation analysis.

    Args:
        appreciation_hotspots: Output from appreciation_hotspots in 05_metrics.

    Returns:
        Dictionary with appreciation analysis.
    """
    results: dict[str, Any] = {}

    if appreciation_hotspots.empty:
        return results

    if "appreciation_3m_pct" in appreciation_hotspots.columns:
        hotspots = appreciation_hotspots.dropna(subset=["appreciation_3m_pct"])
        hotspots = hotspots.sort_values("appreciation_3m_pct", ascending=False).head(10)

        results["top_hotspots"] = hotspots[["planning_area", "appreciation_3m_pct"]].to_dict(
            orient="records"
        )

    return results
