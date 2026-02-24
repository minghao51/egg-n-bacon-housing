"""
Web Export Pipeline (L3)

Exports processed analytics data to lightweight JSON.gz files for the
static web dashboard (Astro/React).
"""

import gzip
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path for direct script execution
if __name__ == "__main__" and __file__:
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from scripts.core.data_loader import load_unified_data
from scripts.core.stages.L5_metrics import (
    calculate_affordability_by_area,
    calculate_growth_metrics_by_area,
    calculate_rental_yield_by_area,
    identify_appreciation_hotspots,
)

logger = logging.getLogger(__name__)


def _to_lower_indexed_records(
    df: pd.DataFrame, index_col: str, value_cols: list[str]
) -> dict[str, dict]:
    """Convert a DataFrame to a lowercased-index dict for fast lookups."""
    if df.empty or index_col not in df.columns:
        return {}
    indexed = df.set_index(index_col)[value_cols].copy()
    indexed.index = indexed.index.astype(str).str.lower()
    return indexed.to_dict("index")


def build_l5_metric_cache(df: pd.DataFrame) -> dict:
    """Compute reusable L5-derived metrics once per web export run."""
    cache: dict = {
        "latest_growth_by_area": {},
        "yield_by_area": {},
        "recent_yield_by_area": {},
        "affordability_by_area": {},
        "hotspots": {},
    }

    # Growth metrics + latest snapshot
    growth_df = pd.DataFrame()
    try:
        growth_df = calculate_growth_metrics_by_area(df)
        if not growth_df.empty:
            latest_growth = growth_df.sort_values("month").groupby("planning_area").last()
            latest_growth.index = latest_growth.index.astype(str).str.lower()
            cache["latest_growth_by_area"] = latest_growth[
                ["mom_change_pct", "yoy_change_pct", "momentum", "momentum_signal"]
            ].to_dict("index")
    except Exception as e:
        logger.warning(f"Could not precompute growth metrics cache: {e}")

    # Rental yield metrics (whole dataset)
    try:
        yield_df = calculate_rental_yield_by_area(df)
        cache["yield_by_area"] = _to_lower_indexed_records(
            yield_df, "planning_area", ["mean", "median", "std"]
        )
    except Exception as e:
        logger.warning(f"Could not precompute rental yield cache: {e}")

    # Rental yield metrics (recent subset used by leaderboard)
    try:
        recent_df = df[df["transaction_date"].dt.year >= 2022]
        recent_yield_df = calculate_rental_yield_by_area(recent_df)
        cache["recent_yield_by_area"] = _to_lower_indexed_records(
            recent_yield_df, "planning_area", ["mean", "median", "std"]
        )
    except Exception as e:
        logger.warning(f"Could not precompute recent rental yield cache: {e}")

    # Affordability metrics
    try:
        aff_df = calculate_affordability_by_area(df)
        cache["affordability_by_area"] = _to_lower_indexed_records(
            aff_df,
            "planning_area",
            ["affordability_ratio", "affordability_class", "mortgage_to_income_pct"],
        )
    except Exception as e:
        logger.warning(f"Could not precompute affordability cache: {e}")

    # Hotspots derived from growth metrics
    try:
        if not growth_df.empty:
            hotspots_df = identify_appreciation_hotspots(growth_df)
            hotspots = {}
            for _, row in hotspots_df.iterrows():
                area_name = str(row["planning_area"]).upper()
                hotspots[area_name] = {
                    "category": str(row["category"]),
                    "mean_yoy_growth": safe_float(row.get("mean_yoy"), 0),
                    "median_yoy_growth": safe_float(row.get("median_yoy"), 0),
                    "std_yoy_growth": safe_float(row.get("std_yoy"), 0),
                    "consistency": safe_float(row.get("consistency"), 0),
                    "years": int(row.get("years", 0)),
                }
            cache["hotspots"] = hotspots
    except Exception as e:
        logger.warning(f"Could not precompute hotspots cache: {e}")

    return cache


def write_json_gzip(data, filepath: Path):
    """Write data to a gzipped JSON file."""
    with gzip.open(filepath, "wt", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved: {filepath}")


def sanitize_for_json(obj):
    """
    Recursively replace NaN, Infinity, -Infinity with None (null in JSON).
    """
    if isinstance(obj, float):
        if pd.isna(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    return obj


def safe_float(val, default=None):
    """Safely convert value to float, returning default if NaN/Inf."""
    try:
        f = float(val)
        if pd.isna(f) or np.isinf(f):
            return default
        return round(f, 2)
    except (ValueError, TypeError):
        return default


def export_dashboard_data():
    """
    Main entry point to export all dashboard data.
    """
    logger.info("Starting web dashboard data export...")

    # Ensure app data directory exists
    output_dir = Path("app/public/data")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    logger.info("Loading unified dataset...")
    df = load_unified_data()

    if df.empty:
        logger.error("Unified dataset is empty!")
        return

    # Ensure dates
    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])
        df["month"] = df["transaction_date"].dt.to_period("M").astype(str)
        df["year"] = df["transaction_date"].dt.year

    # Precompute reusable L5-derived metrics once for all web exports
    l5_cache = build_l5_metric_cache(df)

    # 1. Export Overview Data
    logger.info("Exporting overview data...")
    overview_data = generate_overview_data(df)
    write_json_gzip(sanitize_for_json(overview_data), output_dir / "dashboard_overview.json.gz")

    # 2. Export Trends Data
    logger.info("Exporting trends data...")
    trends_data = generate_trends_data(df)
    write_json_gzip(sanitize_for_json(trends_data), output_dir / "dashboard_trends.json.gz")

    # 3. Export Map Data
    logger.info("Exporting map data...")
    map_data = generate_map_data(df, l5_cache=l5_cache)
    write_json_gzip(sanitize_for_json(map_data), output_dir / "map_metrics.json.gz")

    # Copy GeoJSON (prefer URA file with region data)
    geojson_src = Path("data/manual/geojsons/ura_planning_area_boundary.geojson")
    if not geojson_src.exists():
        geojson_src = Path("data/manual/geojsons/onemap_planning_area_polygon.geojson")
    if geojson_src.exists():
        shutil.copy(geojson_src, output_dir / "planning_areas.geojson")
        logger.info(f"Copied planning_areas.geojson from {geojson_src.name}")
    else:
        logger.warning("GeoJSON source not found!")

    # 4. Export Segments Data
    logger.info("Exporting segments data...")
    segments_data = generate_filtered_segments_data(df)
    write_json_gzip(sanitize_for_json(segments_data), output_dir / "dashboard_segments.json.gz")

    # 5. Export Town Leaderboard
    logger.info("Exporting leaderboard data...")
    leaderboard_data = generate_leaderboard_data(df, l5_cache=l5_cache)
    write_json_gzip(
        sanitize_for_json(leaderboard_data), output_dir / "dashboard_leaderboard.json.gz"
    )

    # 6. Export Appreciation Hotspots (NEW)
    logger.info("Exporting hotspots data...")
    hotspots_data = generate_hotspots_data(df, l5_cache=l5_cache)
    write_json_gzip(sanitize_for_json(hotspots_data), output_dir / "hotspots.json.gz")

    # 7. Export Amenity Summary (NEW - Phase 2)
    logger.info("Exporting amenity summary data...")
    amenity_summary_data = generate_amenity_summary_data(df)
    write_json_gzip(sanitize_for_json(amenity_summary_data), output_dir / "amenity_summary.json.gz")

    logger.info(f"Export complete! Files saved to {output_dir}")


def get_stats(sub_df):
    if sub_df.empty:
        return {"count": 0, "median_price": 0, "median_psf": 0, "volume": 0}
    return {
        "count": int(len(sub_df)),
        "median_price": int(sub_df["price"].median()),
        "median_psf": int(sub_df["price_psf"].median()) if "price_psf" in sub_df.columns else 0,
        "volume": int(len(sub_df)),  # Same as count
    }


def generate_overview_data(df):
    pre_covid = df[df["transaction_date"].dt.year <= 2021]
    recent = df[df["transaction_date"].dt.year >= 2022]
    year_2025 = df[df["transaction_date"].dt.year == 2025]

    # Property type filters
    hdb = df[df["property_type"].isin(["HDB", "HDB Flat"])]
    ec = df[df["property_type"].isin(["Executive Condominium", "EC"])]
    condo = df[df["property_type"].isin(["Condominium", "Apartment", "Condo"])]

    # Stats by era
    stats_whole = get_stats(df)
    stats_pre = get_stats(pre_covid)
    stats_recent = get_stats(recent)
    stats_2025 = get_stats(year_2025)

    # Stats by property type (all time)
    stats_hdb = get_stats(hdb)
    stats_ec = get_stats(ec)
    stats_condo = get_stats(condo)

    # Combined era + property type stats
    stats_pre_hdb = get_stats(pre_covid[pre_covid["property_type"].isin(["HDB", "HDB Flat"])])
    stats_pre_ec = get_stats(
        pre_covid[pre_covid["property_type"].isin(["Executive Condominium", "EC"])]
    )
    stats_pre_condo = get_stats(
        pre_covid[pre_covid["property_type"].isin(["Condominium", "Apartment", "Condo"])]
    )

    stats_recent_hdb = get_stats(recent[recent["property_type"].isin(["HDB", "HDB Flat"])])
    stats_recent_ec = get_stats(
        recent[recent["property_type"].isin(["Executive Condominium", "EC"])]
    )
    stats_recent_condo = get_stats(
        recent[recent["property_type"].isin(["Condominium", "Apartment", "Condo"])]
    )

    stats_2025_hdb = get_stats(year_2025[year_2025["property_type"].isin(["HDB", "HDB Flat"])])
    stats_2025_ec = get_stats(
        year_2025[year_2025["property_type"].isin(["Executive Condominium", "EC"])]
    )
    stats_2025_condo = get_stats(
        year_2025[year_2025["property_type"].isin(["Condominium", "Apartment", "Condo"])]
    )

    type_counts = df["property_type"].value_counts().to_dict()
    top_areas = df["planning_area"].value_counts().head(10).to_dict()

    return {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_records": len(df),
            "date_range": {
                "start": df["transaction_date"].min().strftime("%Y-%m-%d"),
                "end": df["transaction_date"].max().strftime("%Y-%m-%d"),
            },
        },
        "stats": {
            "whole": stats_whole,
            "pre_covid": stats_pre,
            "recent": stats_recent,
            "year_2025": stats_2025,
            # Combined era + property type
            "whole_hdb": stats_hdb,
            "whole_ec": stats_ec,
            "whole_condo": stats_condo,
            "pre_covid_hdb": stats_pre_hdb,
            "pre_covid_ec": stats_pre_ec,
            "pre_covid_condo": stats_pre_condo,
            "recent_hdb": stats_recent_hdb,
            "recent_ec": stats_recent_ec,
            "recent_condo": stats_recent_condo,
            "year_2025_hdb": stats_2025_hdb,
            "year_2025_ec": stats_2025_ec,
            "year_2025_condo": stats_2025_condo,
        },
        "distributions": {"property_type": type_counts, "planning_area": top_areas},
    }


def generate_trends_data(df):
    price_pivot = df.pivot_table(
        index="month", columns="property_type", values="price", aggfunc="median"
    ).reset_index()

    vol_pivot = df.pivot_table(
        index="month", columns="property_type", values="price", aggfunc="count"
    ).reset_index()

    overall = df.groupby("month").agg({"price": "median", "price_psf": "median"}).reset_index()
    overall.columns = ["month", "overall_price", "overall_psf"]

    trends = []
    all_months = sorted(df["month"].unique())

    for m in all_months:
        record = {"date": m}
        ov = overall[overall["month"] == m]
        if not ov.empty:
            record["Overall Price"] = int(ov.iloc[0]["overall_price"])

        p_row = price_pivot[price_pivot["month"] == m]
        if not p_row.empty:
            for col in p_row.columns:
                if col != "month" and not pd.isna(p_row.iloc[0][col]):
                    record[f"{col} Price"] = int(p_row.iloc[0][col])

        v_row = vol_pivot[vol_pivot["month"] == m]
        if not v_row.empty:
            for col in v_row.columns:
                if col != "month" and not pd.isna(v_row.iloc[0][col]):
                    record[f"{col} Volume"] = int(v_row.iloc[0][col])

        trends.append(record)

    return trends


def generate_map_metrics_for_subset(sub_df):
    if sub_df.empty:
        return {}

    agg = (
        sub_df.groupby("planning_area")
        .agg({"price": "median", "price_psf": "median", "transaction_date": "count"})
        .reset_index()
    )

    agg.columns = ["planning_area", "median_price", "median_psf", "volume"]

    map_metrics = {}
    for _, row in agg.iterrows():
        name = row["planning_area"].upper()
        map_metrics[name] = {
            "median_price": int(row["median_price"]),
            "median_psf": int(row["median_psf"]),
            "volume": int(row["volume"]),
        }
    return map_metrics


def generate_map_data(df, l5_cache: dict | None = None):
    """Aggregates metrics by Planning Area for different eras, including L5 metrics."""
    logger.info("Generating enhanced map data with L5 metrics...")

    # Eras
    pre_covid = df[df["transaction_date"].dt.year <= 2021]
    pre_covid = df[df["transaction_date"].dt.year <= 2021]
    recent = df[df["transaction_date"].dt.year >= 2022]
    year_2025 = df[df["transaction_date"].dt.year == 2025]

    # Property Types
    # Check for exact matches in your dataset or use str.contains if unsure
    hdb = df[df["property_type"].isin(["HDB", "HDB Flat"])]
    ec = df[df["property_type"].isin(["Executive Condominium", "EC"])]
    condo = df[df["property_type"].isin(["Condominium", "Apartment", "Condo"])]

    # Get base metrics
    base_metrics = {
        "whole": generate_map_metrics_for_subset(df),
        "pre_covid": generate_map_metrics_for_subset(pre_covid),
        "recent": generate_map_metrics_for_subset(recent),
        "year_2025": generate_map_metrics_for_subset(year_2025),
        "hdb": generate_map_metrics_for_subset(hdb),
        "ec": generate_map_metrics_for_subset(ec),
        "condo": generate_map_metrics_for_subset(condo),
    }

    # Generate combined era + property type sections for independent filtering
    eras = {"whole": df, "pre_covid": pre_covid, "recent": recent, "year_2025": year_2025}
    property_types = {"hdb": hdb, "ec": ec, "condo": condo}

    for era_name, era_df in eras.items():
        for prop_name, prop_df in property_types.items():
            # Filter era_df by property type
            combined_df = era_df[
                era_df["property_type"].isin(
                    ["HDB", "HDB Flat"]
                    if prop_name == "hdb"
                    else ["Executive Condominium", "EC"]
                    if prop_name == "ec"
                    else ["Condominium", "Apartment", "Condo"]
                )
            ]
            base_metrics[f"{era_name}_{prop_name}"] = generate_map_metrics_for_subset(combined_df)

    # Calculate L5 growth metrics
    try:
        growth_lookup = (l5_cache or {}).get("latest_growth_by_area", {})
        if growth_lookup:
            for era in [
                "whole",
                "pre_covid",
                "recent",
                "whole_hdb",
                "whole_ec",
                "whole_condo",
                "pre_covid_hdb",
                "pre_covid_ec",
                "pre_covid_condo",
                "recent_hdb",
                "recent_ec",
                "recent_condo",
            ]:
                for area_name, metrics in base_metrics[era].items():
                    row = growth_lookup.get(area_name.lower())
                    if row:
                        metrics["mom_change_pct"] = safe_float(row.get("mom_change_pct"), 0)
                        metrics["yoy_change_pct"] = safe_float(row.get("yoy_change_pct"), 0)
                        metrics["momentum"] = safe_float(row.get("momentum"), 0)
                        metrics["momentum_signal"] = str(row.get("momentum_signal", "Unknown"))
    except Exception as e:
        logger.warning(f"Could not add growth metrics: {e}")

    # Calculate rental yield metrics
    try:
        yield_dict = (l5_cache or {}).get("yield_by_area", {})
        if yield_dict:
            for era in [
                "whole",
                "pre_covid",
                "recent",
                "year_2025",
                "hdb",
                "ec",
                "condo",
                "whole_hdb",
                "whole_ec",
                "whole_condo",
                "pre_covid_hdb",
                "pre_covid_ec",
                "pre_covid_condo",
                "recent_hdb",
                "recent_ec",
                "recent_condo",
                "year_2025_hdb",
                "year_2025_ec",
                "year_2025_condo",
            ]:
                for area_name, metrics in base_metrics[era].items():
                    y_data = yield_dict.get(area_name.lower())
                    if y_data:
                        metrics["rental_yield_mean"] = safe_float(y_data.get("mean"))
                        metrics["rental_yield_median"] = safe_float(y_data.get("median"))
                        metrics["rental_yield_std"] = safe_float(y_data.get("std"))
    except Exception as e:
        logger.warning(f"Could not add rental yield metrics: {e}")

    # Calculate affordability metrics
    try:
        aff_dict = (l5_cache or {}).get("affordability_by_area", {})
        if aff_dict:
            for era in [
                "whole",
                "pre_covid",
                "recent",
                "year_2025",
                "hdb",
                "ec",
                "condo",
                "whole_hdb",
                "whole_ec",
                "whole_condo",
                "pre_covid_hdb",
                "pre_covid_ec",
                "pre_covid_condo",
                "recent_hdb",
                "recent_ec",
                "recent_condo",
                "year_2025_hdb",
                "year_2025_ec",
                "year_2025_condo",
            ]:
                for area_name, metrics in base_metrics[era].items():
                    a_data = aff_dict.get(area_name.lower())
                    if a_data:
                        metrics["affordability_ratio"] = safe_float(
                            a_data.get("affordability_ratio")
                        )
                        metrics["affordability_class"] = str(
                            a_data.get("affordability_class", "Unknown")
                        )
                        metrics["mortgage_to_income_pct"] = safe_float(
                            a_data.get("mortgage_to_income_pct")
                        )
    except Exception as e:
        logger.warning(f"Could not add affordability metrics: {e}")

    logger.info("Enhanced map data generation complete")
    return base_metrics


def generate_hotspots_data(df, l5_cache: dict | None = None):
    """Generate appreciation hotspots classification by planning area."""
    logger.info("Generating hotspots data...")

    cache_hotspots = (l5_cache or {}).get("hotspots")
    if cache_hotspots:
        return cache_hotspots

    # Calculate growth metrics first (needed for hotspot identification)
    try:
        growth_df = calculate_growth_metrics_by_area(df)
        if growth_df.empty:
            logger.warning("No growth data available for hotspots")
            return {}
    except Exception as e:
        logger.warning(f"Could not calculate growth metrics: {e}")
        return {}

    # Identify hotspots
    try:
        hotspots_df = identify_appreciation_hotspots(growth_df)
        if hotspots_df.empty:
            logger.warning("No hotspots identified")
            return {}
    except Exception as e:
        logger.warning(f"Could not identify hotspots: {e}")
        return {}

    # Convert to dictionary format
    hotspots = {}
    for _, row in hotspots_df.iterrows():
        area_name = row["planning_area"].upper()
        hotspots[area_name] = {
            "category": str(row["category"]),
            "mean_yoy_growth": safe_float(row.get("mean_yoy"), 0),
            "median_yoy_growth": safe_float(row.get("median_yoy"), 0),
            "std_yoy_growth": safe_float(row.get("std_yoy"), 0),
            "consistency": safe_float(row.get("consistency"), 0),
            "years": int(row.get("years", 0)),
        }

    logger.info(f"Generated hotspots data for {len(hotspots)} areas")
    return hotspots


def generate_segments_data(df, yield_lookup: dict[str, float] | None = None):
    """Generate scatter plot data for Market Segments (Price PSF vs Yield)."""
    # Recent data only
    df_recent = df[df["year"] >= 2022].copy()

    # Get rental yield from L5 metrics for all planning areas (HDB only)
    yield_dict = yield_lookup or {}
    if not yield_dict and not df_recent.empty:
        has_hdb = df_recent["property_type"].isin(["HDB", "HDB Flat"]).any()
        if has_hdb:
            try:
                yield_df = calculate_rental_yield_by_area(df_recent)
                if not yield_df.empty:
                    yield_df_indexed = yield_df.set_index("planning_area")["mean"]
                    yield_df_indexed.index = yield_df_indexed.index.str.lower()
                    yield_dict = yield_df_indexed.to_dict()
            except Exception as e:
                logger.warning(f"Could not calculate rental yield for segments: {e}")

    # Group by Planning Area and Property Type (NOT flat_type for non-HDB)
    # For HDB, we want flat_type breakdown; for condo/EC, we don't
    group_cols = ["planning_area", "property_type"]

    agg = (
        df_recent.groupby(group_cols)
        .agg({"price_psf": "median", "rental_yield_pct": "mean", "price": "count"})
        .reset_index()
    )

    agg.columns = [*group_cols, "price_psf", "rental_yield", "volume"]

    # Filter outliers by volume
    agg = agg[agg["volume"] > 10]  # Minimum volume

    segments = []
    for _, row in agg.iterrows():
        # Determine rental yield: use L5 metric if raw value is missing
        rental_yield = row["rental_yield"]
        prop_type = row["property_type"]

        # Normalize property type for category
        if prop_type in ["HDB", "HDB Flat"]:
            category = "HDB"
            # For HDB, use L5 metric if raw value is missing
            if pd.isna(rental_yield) or rental_yield == 0:
                area_lower = row["planning_area"].lower()
                rental_yield = yield_dict.get(area_lower, None)
        elif prop_type in ["Executive Condominium", "EC"]:
            category = "EC"
            # For EC, estimate yield based on PSF (typical range: 2.5% - 4.5%)
            if pd.isna(rental_yield) or rental_yield == 0:
                psf = row["price_psf"]
                # Lower PSF = higher yield, Higher PSF = lower yield
                rental_yield = max(2.5, min(4.5, 5.0 - (psf / 2000)))
        else:  # Condominium, Apartment, Condo
            category = "Condominium"
            # For Condo, estimate yield based on PSF (typical range: 2.0% - 4.0%)
            if pd.isna(rental_yield) or rental_yield == 0:
                psf = row["price_psf"]
                # Lower PSF = higher yield, Higher PSF = lower yield
                rental_yield = max(2.0, min(4.0, 4.5 - (psf / 2500)))

        # Skip if still no rental yield data
        if pd.isna(rental_yield):
            continue

        label = f"{row['planning_area']} - {row['property_type']}"

        segments.append(
            {
                "name": label,
                "x": float(row["price_psf"]),
                "y": float(rental_yield),  # Already in percentage
                "z": int(row["volume"]),  # Bubble size
                "category": category,
            }
        )

    return segments


def _build_segment_yield_lookup(df_subset: pd.DataFrame) -> dict[str, float]:
    """Build cached rental yield lookup for segment generation when HDB fallback is needed."""
    if df_subset.empty:
        return {}

    if not df_subset["property_type"].isin(["HDB", "HDB Flat"]).any():
        return {}

    recent_subset = df_subset[df_subset["year"] >= 2022]
    if recent_subset.empty:
        return {}

    try:
        yield_df = calculate_rental_yield_by_area(recent_subset)
        if yield_df.empty:
            return {}
        yield_series = yield_df.set_index("planning_area")["mean"]
        yield_series.index = yield_series.index.astype(str).str.lower()
        return yield_series.to_dict()
    except Exception as e:
        logger.warning(f"Could not calculate rental yield for segments subset: {e}")
        return {}


def generate_filtered_segments_data(df):
    """Generate segments data for each era + property type combination."""
    logger.info("Generating filtered segments data...")

    # Define eras
    eras = {
        "whole": df,
        "pre_covid": df[df["transaction_date"].dt.year <= 2021],
        "recent": df[df["transaction_date"].dt.year >= 2022],
        "year_2025": df[df["transaction_date"].dt.year == 2025],
    }

    # Define property type filters
    def filter_by_property_type(df_subset, prop_type):
        if prop_type == "hdb":
            return df_subset[df_subset["property_type"].isin(["HDB", "HDB Flat"])]
        elif prop_type == "ec":
            return df_subset[df_subset["property_type"].isin(["Executive Condominium", "EC"])]
        elif prop_type == "condo":
            return df_subset[df_subset["property_type"].isin(["Condominium", "Apartment", "Condo"])]
        return df_subset

    # Build cached yield lookups only for combinations that may need HDB fallback values
    segment_yield_lookups: dict[str, dict[str, float]] = {}

    def cache_lookup(key: str, df_subset: pd.DataFrame):
        segment_yield_lookups[key] = _build_segment_yield_lookup(df_subset)

    for era_name, era_df in eras.items():
        cache_lookup(era_name, era_df)
        hdb_df = filter_by_property_type(era_df, "hdb")
        cache_lookup(f"{era_name}_hdb", hdb_df)

    # Generate segments for each combination
    filtered_segments = {}
    for era_name, era_df in eras.items():
        if era_df.empty:
            continue

        # Generate for all property types
        filtered_segments[era_name] = generate_segments_data(
            era_df, yield_lookup=segment_yield_lookups.get(era_name)
        )

        # Generate for each property type
        for prop_type in ["hdb", "ec", "condo"]:
            prop_df = filter_by_property_type(era_df, prop_type)
            if not prop_df.empty:
                key = f"{era_name}_{prop_type}"
                filtered_segments[key] = generate_segments_data(
                    prop_df, yield_lookup=segment_yield_lookups.get(key)
                )

    logger.info(f"Generated filtered segments data for {len(filtered_segments)} combinations")
    return filtered_segments


def get_planning_area_metadata():
    """
    Load planning area metadata from GeoJSON (region, coordinates).

    Returns:
        dict: Mapping of lowercase area name to metadata dict with 'region' and 'coordinates'
    """
    geojson_path = Path("data/manual/geojsons/ura_planning_area_boundary.geojson")
    if not geojson_path.exists():
        geojson_path = Path("data/manual/geojsons/onemap_planning_area_polygon.geojson")

    metadata = {}
    if geojson_path.exists():
        with open(geojson_path) as f:
            geojson = json.load(f)

        for feature in geojson.get("features", []):
            props = feature.get("properties", {})
            area_name = props.get("PLN_AREA_N") or props.get("planning_area_n", "")
            region_name = props.get("REGION_N") or props.get("region_n", "Unknown")

            # Calculate centroid from coordinates
            centroid = _calculate_centroid_from_geometry(feature.get("geometry", {}))

            metadata[area_name.lower()] = {
                "region": region_name,
                "coordinates": centroid,
            }

    return metadata


def _calculate_centroid_from_geometry(geometry: dict) -> list[float] | None:
    """
    Calculate centroid from GeoJSON geometry.

    Args:
        geometry: GeoJSON geometry dict with 'type' and 'coordinates'

    Returns:
        [longitude, latitude] or None if no coordinates
    """
    coordinates = geometry.get("coordinates", [])

    if not coordinates or len(coordinates) == 0:
        return None

    # Extract coordinate array based on geometry type
    if geometry.get("type") == "Polygon":
        all_coords = coordinates[0]  # First ring of polygon
    elif geometry.get("type") == "MultiPolygon":
        all_coords = coordinates[0][0]  # First ring of first polygon
    else:
        # Fallback for other types
        all_coords = coordinates[0] if isinstance(coordinates[0], list) else coordinates

    # Calculate centroid as average of all coordinates
    lons = [c[0] for c in all_coords]
    lats = [c[1] for c in all_coords]
    return [round(sum(lons) / len(lons), 6), round(sum(lats) / len(lats), 6)]


def _calculate_property_type_breakdown(
    df_full: pd.DataFrame, area_col: str, area_name: str
) -> dict[str, dict[str, int | None]]:
    """
    Calculate property type breakdown for a specific planning area.

    Args:
        df_full: Full transaction dataframe
        area_col: Column name for planning area
        area_name: Planning area name to filter by

    Returns:
        Dict with keys 'hdb', 'ec', 'condo' containing median_price and volume
    """
    property_filters = {
        "hdb": df_full["property_type"].isin(["HDB", "HDB Flat"]),
        "ec": df_full["property_type"].isin(["Executive Condominium", "EC"]),
        "condo": df_full["property_type"].isin(["Condominium", "Apartment", "Condo"]),
    }

    breakdown = {}
    for prop_name, mask in property_filters.items():
        prop_area_data = df_full[mask & (df_full[area_col] == area_name)]

        if prop_area_data.empty:
            breakdown[prop_name] = {"median_price": None, "volume": 0}
        else:
            breakdown[prop_name] = {
                "median_price": int(prop_area_data["price"].median()),
                "volume": int(len(prop_area_data)),
            }

    return breakdown


def _calculate_time_period_breakdown(
    time_periods: dict[str, pd.DataFrame], area_col: str, area_name: str
) -> dict[str, dict[str, int | float | None]]:
    """
    Calculate time period breakdown for a specific planning area.

    Args:
        time_periods: Dict of period name to filtered dataframe
        area_col: Column name for planning area
        area_name: Planning area name to filter by

    Returns:
        Dict with period names containing median_price and yoy_growth
    """
    breakdown = {}

    for period_name, period_df in time_periods.items():
        period_area_data = period_df[period_df[area_col] == area_name]

        if period_area_data.empty:
            breakdown[period_name] = {"median_price": None, "yoy_growth": None}
            continue

        median_price = int(period_area_data["price"].median())

        # Calculate YoY growth for this period
        period_year = period_area_data["year"].max()
        period_prev_year = period_year - 1

        price_curr = period_area_data[period_area_data["year"] == period_year]["price"].median()
        price_prev = period_area_data[period_area_data["year"] == period_prev_year][
            "price"
        ].median()

        if pd.notna(price_curr) and pd.notna(price_prev) and price_prev > 0:
            yoy = round(((price_curr - price_prev) / price_prev) * 100, 2)
        else:
            yoy = None

        breakdown[period_name] = {"median_price": median_price, "yoy_growth": yoy}

    return breakdown


def generate_leaderboard_data(df, l5_cache: dict | None = None):
    """
    Generate enhanced town leaderboard with filterable breakdowns.

    Args:
        df: Unified transaction dataframe with planning_area column

    Returns:
        List of leaderboard entry dicts with planning area metrics
    """
    logger.info("Generating enhanced leaderboard data...")

    # Load planning area metadata (region, coordinates)
    area_metadata = get_planning_area_metadata()
    logger.info(f"Loaded metadata for {len(area_metadata)} planning areas")

    # Get hotspot data
    hotspots = generate_hotspots_data(df, l5_cache=l5_cache)

    # Get affordability metrics
    aff_lookup = (l5_cache or {}).get("affordability_by_area")
    if aff_lookup:
        aff_dict = {area: values.get("affordability_ratio") for area, values in aff_lookup.items()}
    else:
        try:
            aff_df = calculate_affordability_by_area(df)
            aff_series = aff_df.set_index("planning_area")["affordability_ratio"]
            aff_series.index = aff_series.index.astype(str).str.lower()
            aff_dict = aff_series.to_dict()
        except Exception as e:
            logger.warning(f"Could not load affordability metrics: {e}")
            aff_dict = {}

    # Get growth metrics (for mom_change and momentum)
    growth_lookup = (l5_cache or {}).get("latest_growth_by_area")
    if growth_lookup:
        growth_dict = growth_lookup
    else:
        try:
            growth_df = calculate_growth_metrics_by_area(df)
            latest_growth = growth_df.sort_values("month").groupby("planning_area").last()
            latest_growth.index = latest_growth.index.astype(str).str.lower()
            growth_dict = latest_growth[["mom_change_pct", "yoy_change_pct", "momentum"]].to_dict(
                "index"
            )
        except Exception as e:
            logger.warning(f"Could not load growth metrics: {e}")
            growth_dict = {}

    # Use planning_area for consistent aggregation
    area_col = "planning_area" if "planning_area" in df.columns else "town"

    # Define time periods
    time_periods = {
        "whole": df,
        "pre_covid": df[df["transaction_date"].dt.year <= 2021],
        "recent": df[df["transaction_date"].dt.year >= 2022],
        "year_2025": df[df["transaction_date"].dt.year == 2025],
    }

    # Calculate overall metrics (recent data for default display)
    df_recent = time_periods["recent"].copy()

    area_metrics = (
        df_recent.groupby(area_col)
        .agg(
            {
                "price": "median",
                "price_psf": "median",
                "rental_yield_pct": "mean",
                "transaction_date": "count",
            }
        )
        .reset_index()
    )

    area_metrics.columns = ["area", "median_price", "median_psf", "rental_yield_mean", "volume"]

    # Get rental yield median from L5 metrics
    recent_yield_lookup = (l5_cache or {}).get("recent_yield_by_area")
    if recent_yield_lookup:
        area_metrics["rental_yield_median"] = area_metrics["area"].map(
            lambda x: safe_float((recent_yield_lookup.get(x.lower()) or {}).get("median"))
        )
    else:
        try:
            yield_df = calculate_rental_yield_by_area(df_recent)
            yield_median = yield_df.set_index("planning_area")["median"]
            yield_median.index = yield_median.index.astype(str).str.lower()
            area_metrics["rental_yield_median"] = area_metrics["area"].map(
                lambda x: safe_float(yield_median.get(x.lower()))
            )
        except Exception as e:
            logger.warning(f"Could not add rental yield median: {e}")
            area_metrics["rental_yield_median"] = None

    # Calculate YoY growth
    current_year = df_recent["year"].max()
    prev_year = current_year - 1

    price_curr = df_recent[df_recent["year"] == current_year].groupby(area_col)["price"].median()
    price_prev = df_recent[df_recent["year"] == prev_year].groupby(area_col)["price"].median()

    yoy_growth = ((price_curr - price_prev) / price_prev * 100).reset_index()
    yoy_growth.columns = ["area", "yoy_growth_pct"]

    # Merge growth metrics
    area_metrics = pd.merge(area_metrics, yoy_growth, on="area", how="left")

    # Build enhanced leaderboard entries
    result = []
    for _, row in area_metrics.iterrows():
        area_name = row["area"]
        area_lower = area_name.lower()

        # Get metadata
        meta = area_metadata.get(area_lower, {})
        region = meta.get("region", "Unknown")
        coordinates = meta.get("coordinates")

        # Get hotspot category
        hotspot = hotspots.get(area_name.upper(), {}).get("category", "Unknown")

        # Get additional metrics
        mom_change = safe_float(growth_dict.get(area_lower, {}).get("mom_change_pct"))
        momentum = safe_float(growth_dict.get(area_lower, {}).get("momentum"))
        affordability = safe_float(aff_dict.get(area_lower))

        # Calculate breakdowns using helper functions
        by_property_type = _calculate_property_type_breakdown(df, area_col, area_name)
        by_time_period = _calculate_time_period_breakdown(time_periods, area_col, area_name)

        # Build entry
        entry = {
            "planning_area": area_name,
            "region": region,
            "coordinates": coordinates,
            "spatial_hotspot": hotspot,
            "rank_overall": 0,  # Will be assigned after sorting
            "median_price": int(row["median_price"]),
            "median_psf": int(row["median_psf"]),
            "rental_yield_mean": round(float(row["rental_yield_mean"]), 2)
            if row["rental_yield_mean"]
            else 0,
            "rental_yield_median": row["rental_yield_median"],
            "yoy_growth_pct": round(float(row["yoy_growth_pct"]), 2)
            if pd.notna(row["yoy_growth_pct"])
            else 0,
            "mom_change_pct": mom_change if mom_change else 0,
            "momentum": momentum if momentum else 0,
            "volume": int(row["volume"]),
            "affordability_ratio": affordability if affordability else 0,
            "by_property_type": by_property_type,
            "by_time_period": by_time_period,
        }

        result.append(entry)

    # Rank by growth + yield (default)
    result.sort(key=lambda x: x["yoy_growth_pct"] + x["rental_yield_mean"], reverse=True)
    for rank, entry in enumerate(result, 1):
        entry["rank_overall"] = rank

    logger.info(f"Generated enhanced leaderboard for {len(result)} planning areas")
    return result


def generate_amenity_summary_data(df):
    """Generate amenity coverage statistics by planning area.

    Calculates mean distances and counts for each amenity type
    (hawker, supermarket, mrt_station, mrt_exit, childcare, park, mall).

    Args:
        df: Unified dataset with amenity columns

    Returns:
        List of dicts with amenity stats by planning area
    """
    logger.info("Generating amenity summary data...")

    # Amenity columns to aggregate
    distance_cols = [
        "dist_nearest_hawker",
        "dist_nearest_supermarket",
        "dist_nearest_mrt_station",
        "dist_nearest_mrt_exit",
        "dist_nearest_childcare",
        "dist_nearest_park",
        "dist_nearest_mall",
    ]

    count_cols_500m = [
        "count_hawker_500m",
        "count_supermarket_500m",
        "count_mrt_station_500m",
        "count_mrt_exit_500m",
        "count_childcare_500m",
        "count_park_500m",
        "count_mall_500m",
    ]

    # Check if amenity columns exist
    available_distance_cols = [col for col in distance_cols if col in df.columns]
    available_count_cols = [col for col in count_cols_500m if col in df.columns]

    if not available_distance_cols and not available_count_cols:
        logger.warning("No amenity columns found in dataset")
        return []

    # Aggregate by planning area
    agg_dict = {}
    for col in available_distance_cols:
        agg_dict[col] = "mean"
    for col in available_count_cols:
        agg_dict[col] = "mean"

    amenity_stats = df.groupby("planning_area").agg(agg_dict).reset_index()

    # Convert to list of dicts for JSON export
    result = []
    for _, row in amenity_stats.iterrows():
        area_data = {"planning_area": row["planning_area"]}

        # Add distance stats (in meters, rounded)
        for col in available_distance_cols:
            amenity_type = col.replace("dist_nearest_", "")
            area_data[f"avg_dist_to_{amenity_type}"] = safe_float(row[col])

        # Add count stats (average within 500m)
        for col in available_count_cols:
            amenity_type = col.replace("count_", "").replace("_500m", "")
            area_data[f"avg_count_{amenity_type}_500m"] = safe_float(row[col])

        result.append(area_data)

    logger.info(f"Generated amenity summary for {len(result)} planning areas")
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    export_dashboard_data()
