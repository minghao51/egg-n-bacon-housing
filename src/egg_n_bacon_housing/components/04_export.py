"""04_export: Platinum layer export and lightweight summaries.

This module keeps the Hamilton export stage focused on the platinum dataset
and in-memory summaries. The published app assets are maintained separately
from this stage.
"""

from pathlib import Path

import pandas as pd

from egg_n_bacon_housing.utils.contracts import require_columns
from egg_n_bacon_housing.utils.io_helpers import save_parquet
from egg_n_bacon_housing.utils.layer_writer import LayerWriter


def unified_dataset(
    town_supply_enriched: pd.DataFrame,
    platinum_dir: Path,
    writer: LayerWriter | None = None,
) -> pd.DataFrame:
    """Create the unified dataset for platinum layer.

    Args:
        town_supply_enriched: Output from 03_features town_supply_enriched.

    Returns:
        DataFrame ready for analysis and dashboards.
    """
    if town_supply_enriched.empty:
        return pd.DataFrame()

    df = town_supply_enriched.copy()
    require_columns(df, {"price", "property_type", "transaction_date"}, "town_supply_enriched")

    if writer is not None:
        writer.write(df, "unified_dataset", "platinum")
    else:
        save_parquet(df, platinum_dir / "unified_dataset.parquet", "unified dataset")

    return df


def dashboard_json(unified_dataset: pd.DataFrame, webapp_data_dir: Path) -> dict:
    """Generate a lightweight dataset summary.

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

    return summary


def segments_data(unified_dataset: pd.DataFrame, webapp_data_dir: Path) -> dict:
    """Generate lightweight segment summaries.

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

    return {"segments": segments, "generated_at": pd.Timestamp.now().isoformat()}


def interactive_tools_data(unified_dataset: pd.DataFrame, webapp_data_dir: Path) -> dict:
    """Generate lightweight planning-area aggregates.

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

    return result
