"""
Web Export Pipeline (L3)

Exports processed analytics data to lightweight JSON files for the
static web dashboard (Astro/React).
"""

import json
import logging
from pathlib import Path
import shutil
import sys
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root to path for direct script execution
if __name__ == "__main__" and __file__:
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from scripts.core.config import Config
from scripts.core.data_loader import load_unified_data
from scripts.core.stages.L5_metrics import (
    calculate_growth_metrics_by_area,
    calculate_rental_yield_by_area,
    calculate_affordability_by_area,
    identify_appreciation_hotspots
)

logger = logging.getLogger(__name__)


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
    
    # Ensure backend data directory exists
    output_dir = Path("backend/public/data")
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
    
    # 1. Export Overview Data
    logger.info("Exporting overview data...")
    overview_data = generate_overview_data(df)
    with open(output_dir / "dashboard_overview.json", "w") as f:
        json.dump(sanitize_for_json(overview_data), f, indent=2)
        
    # 2. Export Trends Data
    logger.info("Exporting trends data...")
    trends_data = generate_trends_data(df)
    with open(output_dir / "dashboard_trends.json", "w") as f:
        json.dump(sanitize_for_json(trends_data), f, indent=2)

    # 3. Export Map Data
    logger.info("Exporting map data...")
    map_data = generate_map_data(df)
    with open(output_dir / "map_metrics.json", "w") as f:
        json.dump(sanitize_for_json(map_data), f, indent=2)
        
    # Copy GeoJSON
    geojson_src = Path("data/manual/geojsons/onemap_planning_area_polygon.geojson")
    if geojson_src.exists():
        shutil.copy(geojson_src, output_dir / "planning_areas.geojson")
        logger.info("Copied planning_areas.geojson")
    else:
        logger.warning("GeoJSON source not found!")

    # 4. Export Segments Data
    logger.info("Exporting segments data...")
    segments_data = generate_segments_data(df)
    with open(output_dir / "dashboard_segments.json", "w") as f:
        json.dump(sanitize_for_json(segments_data), f, indent=2)

    # 5. Export Town Leaderboard
    logger.info("Exporting leaderboard data...")
    leaderboard_data = generate_leaderboard_data(df)
    with open(output_dir / "dashboard_leaderboard.json", "w") as f:
        json.dump(sanitize_for_json(leaderboard_data), f, indent=2)

    # 6. Export Appreciation Hotspots (NEW)
    logger.info("Exporting hotspots data...")
    hotspots_data = generate_hotspots_data(df)
    with open(output_dir / "hotspots.json", "w") as f:
        json.dump(sanitize_for_json(hotspots_data), f, indent=2)

    logger.info(f"Export complete! Files saved to {output_dir}")

def get_stats(sub_df):
    if sub_df.empty:
        return {
            "count": 0,
            "median_price": 0,
            "median_psf": 0,
            "volume": 0
        }
    return {
        "count": int(len(sub_df)),
        "median_price": int(sub_df["price"].median()),
        "median_psf": int(sub_df["price_psf"].median()) if "price_psf" in sub_df.columns else 0,
        "volume": int(len(sub_df)) # Same as count
    }

def generate_overview_data(df):
    pre_covid = df[df["transaction_date"].dt.year <= 2021]
    pre_covid = df[df["transaction_date"].dt.year <= 2021]
    recent = df[df["transaction_date"].dt.year >= 2022]
    year_2025 = df[df["transaction_date"].dt.year == 2025]
    
    stats_whole = get_stats(df)
    stats_pre = get_stats(pre_covid)
    stats_recent = get_stats(recent)
    stats_2025 = get_stats(year_2025)
    
    type_counts = df["property_type"].value_counts().to_dict()
    top_areas = df["planning_area"].value_counts().head(10).to_dict()
    
    return {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_records": len(df),
            "date_range": {
                "start": df["transaction_date"].min().strftime("%Y-%m-%d"),
                "end": df["transaction_date"].max().strftime("%Y-%m-%d")
            }
        },
        "stats": {
            "whole": stats_whole,
            "pre_covid": stats_pre,
            "whole": stats_whole,
            "pre_covid": stats_pre,
            "recent": stats_recent,
            "year_2025": stats_2025
        },
        "distributions": {
            "property_type": type_counts,
            "planning_area": top_areas
        }
    }

def generate_trends_data(df):
    price_pivot = df.pivot_table(
        index="month",
        columns="property_type",
        values="price",
        aggfunc="median"
    ).reset_index()
    
    vol_pivot = df.pivot_table(
        index="month",
        columns="property_type",
        values="price",
        aggfunc="count"
    ).reset_index()
    
    overall = df.groupby("month").agg({
        "price": "median",
        "price_psf": "median"
    }).reset_index()
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
        
    agg = sub_df.groupby("planning_area").agg({
        "price": "median",
        "price_psf": "median",
        "transaction_date": "count"
    }).reset_index()
    
    agg.columns = ["planning_area", "median_price", "median_psf", "volume"]
    
    map_metrics = {}
    for _, row in agg.iterrows():
        name = row["planning_area"].upper()
        map_metrics[name] = {
            "median_price": int(row["median_price"]),
            "median_psf": int(row["median_psf"]),
            "volume": int(row["volume"])
        }
    return map_metrics

def generate_map_data(df):
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
        "condo": generate_map_metrics_for_subset(condo)
    }

    # Calculate L5 growth metrics
    try:
        growth_df = calculate_growth_metrics_by_area(df)
        if not growth_df.empty:
            # Get latest growth metrics per planning area
            latest_growth = growth_df.sort_values("month").groupby("planning_area").last()
            # Convert index to lowercase for consistent lookup
            latest_growth.index = latest_growth.index.str.lower()

            # Merge into metrics
            for era in ["whole", "pre_covid", "recent"]:
                for area_name, metrics in base_metrics[era].items():
                    area_lower = area_name.lower()
                    if area_lower in latest_growth.index:
                        row = latest_growth.loc[area_lower]
                        metrics["mom_change_pct"] = safe_float(row.get("mom_change_pct"), 0)
                        metrics["yoy_change_pct"] = safe_float(row.get("yoy_change_pct"), 0)
                        metrics["momentum"] = safe_float(row.get("momentum"), 0)
                        metrics["momentum_signal"] = str(row.get("momentum_signal", "Unknown"))
    except Exception as e:
        logger.warning(f"Could not add growth metrics: {e}")

    # Calculate rental yield metrics
    try:
        yield_df = calculate_rental_yield_by_area(df)
        if not yield_df.empty:
            # Convert to dict for easy lookup with lowercase keys
            yield_df_indexed = yield_df.set_index("planning_area")[
                ["mean", "median", "std"]
            ]
            # Convert index to lowercase
            yield_df_indexed.index = yield_df_indexed.index.str.lower()
            yield_dict = yield_df_indexed.to_dict("index")

            # Merge into metrics
            for era in ["whole", "pre_covid", "recent", "year_2025", "hdb", "ec", "condo"]:
                for area_name, metrics in base_metrics[era].items():
                    area_lower = area_name.lower()
                    if area_lower in yield_dict:
                        y_data = yield_dict[area_lower]
                        metrics["rental_yield_mean"] = safe_float(y_data.get("mean"))
                        metrics["rental_yield_median"] = safe_float(y_data.get("median"))
                        metrics["rental_yield_std"] = safe_float(y_data.get("std"))
    except Exception as e:
        logger.warning(f"Could not add rental yield metrics: {e}")

    # Calculate affordability metrics
    try:
        aff_df = calculate_affordability_by_area(df)
        if not aff_df.empty:
            # Convert to dict for easy lookup with lowercase keys
            aff_df_indexed = aff_df.set_index("planning_area")[
                ["affordability_ratio", "affordability_class", "mortgage_to_income_pct"]
            ]
            # Convert index to lowercase
            aff_df_indexed.index = aff_df_indexed.index.str.lower()
            aff_dict = aff_df_indexed.to_dict("index")

            # Merge into metrics
            for era in ["whole", "pre_covid", "recent", "year_2025", "hdb", "ec", "condo"]:
                for area_name, metrics in base_metrics[era].items():
                    area_lower = area_name.lower()
                    if area_lower in aff_dict:
                        a_data = aff_dict[area_lower]
                        metrics["affordability_ratio"] = safe_float(a_data.get("affordability_ratio"))
                        metrics["affordability_class"] = str(a_data.get("affordability_class", "Unknown"))
                        metrics["mortgage_to_income_pct"] = safe_float(a_data.get("mortgage_to_income_pct"))
    except Exception as e:
        logger.warning(f"Could not add affordability metrics: {e}")

    logger.info("Enhanced map data generation complete")
    return base_metrics

def generate_hotspots_data(df):
    """Generate appreciation hotspots classification by planning area."""
    logger.info("Generating hotspots data...")

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
            "years": int(row.get("years", 0))
        }

    logger.info(f"Generated hotspots data for {len(hotspots)} areas")
    return hotspots

def generate_segments_data(df):
    """Generate scatter plot data for Market Segments (Price PSF vs Yield)."""
    # Group by Planning Area and Flat Type/Property Type
    if "flat_type" in df.columns:
        group_cols = ["planning_area", "property_type", "flat_type"]
    else:
        group_cols = ["planning_area", "property_type"]
        
    # Recent data only
    df_recent = df[df["year"] >= 2022].copy()
    
    agg = df_recent.groupby(group_cols).agg({
        "price_psf": "median",
        "rental_yield_pct": "mean",
        "price": "count"
    }).reset_index()
    
    agg.columns = [*group_cols, "price_psf", "rental_yield", "volume"]
    
    # Filter outliers
    agg = agg[agg["volume"] > 10] # Minimum volume
    agg = agg.dropna()
    
    segments = []
    for _, row in agg.iterrows():
        label = f"{row['planning_area']} - {row['property_type']}"
        if "flat_type" in row and pd.notna(row["flat_type"]):
            label += f" ({row['flat_type']})"
            
        segments.append({
            "name": label,
            "x": float(row["price_psf"]),
            "y": float(row["rental_yield"]),
            "z": int(row["volume"]), # Bubble size
            "category": row["property_type"]
        })
        
    return segments

def generate_leaderboard_data(df):
    """Generate simple town leaderboard rankings."""
    df_recent = df[df["year"] >= 2023].copy()
    
    # Calculate metrics by Town
    town_metrics = df_recent.groupby("town").agg({
        "price": "median",
        "price_psf": "median",
        "rental_yield_pct": "mean",
        "transaction_date": "count"
    }).reset_index()
    
    town_metrics.columns = ["town", "median_price", "median_psf", "yield", "volume"]
    
    # Calculate Growth (Year over Year for last year)
    current_year = df["year"].max()
    prev_year = current_year - 1
    
    price_curr = df[df["year"] == current_year].groupby("town")["price"].median()
    price_prev = df[df["year"] == prev_year].groupby("town")["price"].median()
    
    growth = ((price_curr - price_prev) / price_prev * 100).reset_index()
    growth.columns = ["town", "growth"]
    
    # Merge
    leaderboard = pd.merge(town_metrics, growth, on="town", how="left").fillna(0)
    
    # Simple Ranking Score (just an example: Growth + Yield)
    leaderboard["score"] = leaderboard["growth"] + leaderboard["yield"]
    leaderboard = leaderboard.sort_values("score", ascending=False)
    
    # Convert to list of dicts
    result = []
    for rank, (_, row) in enumerate(leaderboard.iterrows(), 1):
        result.append({
            "rank": rank,
            "town": row["town"],
            "median_price": int(row["median_price"]),
            "median_psf": int(row["median_psf"]),
            "yield": round(float(row["yield"]), 2) if row["yield"] else 0,
            "growth": round(float(row["growth"]), 2),
            "volume": int(row["volume"])
        })
        
    return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    export_dashboard_data()
