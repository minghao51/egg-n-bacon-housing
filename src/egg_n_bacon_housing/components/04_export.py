"""04_export: Platinum layer export and webapp data (Hamilton DAG node).

This module provides Hamilton-compatible functions for exporting unified
data to the platinum layer and generating webapp-ready JSON.
"""

import logging
from pathlib import Path

import orjson
import pandas as pd

from egg_n_bacon_housing.utils.contracts import require_columns
from egg_n_bacon_housing.utils.io_helpers import save_parquet

logger = logging.getLogger(__name__)


def _safe_json_serialize(data: dict) -> bytes:
    return orjson.dumps(data, option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_INDENT_2)


def unified_dataset(unified_features: pd.DataFrame, platinum_dir: Path) -> pd.DataFrame:
    """Create the unified dataset for platinum layer.

    Args:
        unified_features: Output from 03_features unified_features.

    Returns:
        DataFrame ready for analysis and dashboards.
    """
    if unified_features.empty:
        return pd.DataFrame()

    df = unified_features.copy()
    require_columns(df, {"price", "property_type", "transaction_date"}, "unified_features")

    save_parquet(df, platinum_dir / "unified_dataset.parquet", "unified dataset")

    return df


def dashboard_json(unified_dataset: pd.DataFrame, webapp_data_dir: Path) -> dict:
    """Generate webapp-ready JSON summary.

    Args:
        unified_dataset: Full unified dataset.

    Returns:
        Dictionary with dashboard summary data.
    """
    if unified_dataset.empty:
        return {}

    summary = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "total_transactions": len(unified_dataset),
        "property_types": unified_dataset["property_type"].value_counts().to_dict(),
        "price_range": {
            "min": float(unified_dataset["price"].min()),
            "max": float(unified_dataset["price"].max()),
            "median": float(unified_dataset["price"].median()),
        },
    }

    if "planning_area" in unified_dataset.columns:
        summary["by_planning_area"] = unified_dataset.groupby("planning_area").size().to_dict()

    webapp_data_dir.mkdir(parents=True, exist_ok=True)
    out_path = webapp_data_dir / "dashboard_summary.json"
    out_path.write_bytes(_safe_json_serialize(summary))
    logger.info(f"Saved dashboard JSON to {out_path}")

    return summary


def segments_data(unified_dataset: pd.DataFrame, webapp_data_dir: Path) -> dict:
    """Generate market segments data for webapp.

    Args:
        unified_dataset: Full unified dataset.

    Returns:
        Dictionary with segment data.
    """
    if unified_dataset.empty:
        return {}

    segments = []

    if "price" in unified_dataset.columns and "property_type" in unified_dataset.columns:
        for ptype in unified_dataset["property_type"].unique():
            subset = unified_dataset[unified_dataset["property_type"] == ptype]
            if len(subset) > 0:
                segments.append(
                    {
                        "property_type": ptype,
                        "count": len(subset),
                        "median_price": float(subset["price"].median()),
                        "median_psf": float(subset["psf"].median())
                        if "psf" in subset.columns
                        else None,
                    }
                )

    result = {"segments": segments, "generated_at": pd.Timestamp.now().isoformat()}

    webapp_data_dir.mkdir(parents=True, exist_ok=True)
    out_path = webapp_data_dir / "segments_data.json"
    out_path.write_bytes(_safe_json_serialize(result))
    logger.info(f"Saved segments data to {out_path}")

    return result


def interactive_tools_data(unified_dataset: pd.DataFrame, webapp_data_dir: Path) -> dict:
    """Generate interactive tools data (hotspots, trends).

    Args:
        unified_dataset: Full unified dataset.

    Returns:
        Dictionary with interactive tool data.
    """
    if unified_dataset.empty:
        return {}

    result = {}

    if "planning_area" in unified_dataset.columns and "price" in unified_dataset.columns:
        pa_stats = (
            unified_dataset.groupby("planning_area")["price"]
            .agg(["median", "count", "std"])
            .reset_index()
        )
        pa_stats.columns = ["planning_area", "median_price", "transaction_count", "price_std"]
        result["planning_area_stats"] = pa_stats.to_dict(orient="records")

    webapp_data_dir.mkdir(parents=True, exist_ok=True)
    out_path = webapp_data_dir / "interactive_tools_data.json"
    out_path.write_bytes(_safe_json_serialize(result))
    logger.info(f"Saved interactive tools data to {out_path}")

    return result
