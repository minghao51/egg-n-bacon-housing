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
    segments_data = generate_filtered_segments_data(df)
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
    stats_pre_ec = get_stats(pre_covid[pre_covid["property_type"].isin(["Executive Condominium", "EC"])])
    stats_pre_condo = get_stats(pre_covid[pre_covid["property_type"].isin(["Condominium", "Apartment", "Condo"])])

    stats_recent_hdb = get_stats(recent[recent["property_type"].isin(["HDB", "HDB Flat"])])
    stats_recent_ec = get_stats(recent[recent["property_type"].isin(["Executive Condominium", "EC"])])
    stats_recent_condo = get_stats(recent[recent["property_type"].isin(["Condominium", "Apartment", "Condo"])])

    stats_2025_hdb = get_stats(year_2025[year_2025["property_type"].isin(["HDB", "HDB Flat"])])
    stats_2025_ec = get_stats(year_2025[year_2025["property_type"].isin(["Executive Condominium", "EC"])])
    stats_2025_condo = get_stats(year_2025[year_2025["property_type"].isin(["Condominium", "Apartment", "Condo"])])

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
            "year_2025_condo": stats_2025_condo
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

    # Generate combined era + property type sections for independent filtering
    eras = {
        "whole": df,
        "pre_covid": pre_covid,
        "recent": recent,
        "year_2025": year_2025
    }
    property_types = {
        "hdb": hdb,
        "ec": ec,
        "condo": condo
    }

    for era_name, era_df in eras.items():
        for prop_name, prop_df in property_types.items():
            # Filter era_df by property type
            combined_df = era_df[era_df["property_type"].isin(
                ["HDB", "HDB Flat"] if prop_name == "hdb" else
                ["Executive Condominium", "EC"] if prop_name == "ec" else
                ["Condominium", "Apartment", "Condo"]
            )]
            base_metrics[f"{era_name}_{prop_name}"] = generate_map_metrics_for_subset(combined_df)

    # Calculate L5 growth metrics
    try:
        growth_df = calculate_growth_metrics_by_area(df)
        if not growth_df.empty:
            # Get latest growth metrics per planning area
            latest_growth = growth_df.sort_values("month").groupby("planning_area").last()
            # Convert index to lowercase for consistent lookup
            latest_growth.index = latest_growth.index.str.lower()

            # Merge into metrics (era-based and combined sections)
            for era in ["whole", "pre_covid", "recent", "whole_hdb", "whole_ec", "whole_condo",
                        "pre_covid_hdb", "pre_covid_ec", "pre_covid_condo",
                        "recent_hdb", "recent_ec", "recent_condo"]:
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

            # Merge into metrics (all sections including combined)
            for era in ["whole", "pre_covid", "recent", "year_2025", "hdb", "ec", "condo",
                        "whole_hdb", "whole_ec", "whole_condo",
                        "pre_covid_hdb", "pre_covid_ec", "pre_covid_condo",
                        "recent_hdb", "recent_ec", "recent_condo",
                        "year_2025_hdb", "year_2025_ec", "year_2025_condo"]:
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

            # Merge into metrics (all sections including combined)
            for era in ["whole", "pre_covid", "recent", "year_2025", "hdb", "ec", "condo",
                        "whole_hdb", "whole_ec", "whole_condo",
                        "pre_covid_hdb", "pre_covid_ec", "pre_covid_condo",
                        "recent_hdb", "recent_ec", "recent_condo",
                        "year_2025_hdb", "year_2025_ec", "year_2025_condo"]:
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
    # Recent data only
    df_recent = df[df["year"] >= 2022].copy()

    # Get rental yield from L5 metrics for all planning areas (HDB only)
    yield_dict = {}
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

    agg = df_recent.groupby(group_cols).agg({
        "price_psf": "median",
        "rental_yield_pct": "mean",
        "price": "count"
    }).reset_index()

    agg.columns = [*group_cols, "price_psf", "rental_yield", "volume"]

    # Filter outliers by volume
    agg = agg[agg["volume"] > 10]  # Minimum volume

    segments = []
    for _, row in agg.iterrows():
        # Determine rental yield: use L5 metric if raw value is missing
        rental_yield = row["rental_yield"]
        prop_type = row['property_type']

        # Normalize property type for category
        if prop_type in ['HDB', 'HDB Flat']:
            category = 'HDB'
            # For HDB, use L5 metric if raw value is missing
            if pd.isna(rental_yield) or rental_yield == 0:
                area_lower = row["planning_area"].lower()
                rental_yield = yield_dict.get(area_lower, None)
        elif prop_type in ['Executive Condominium', 'EC']:
            category = 'EC'
            # For EC, estimate yield based on PSF (typical range: 2.5% - 4.5%)
            if pd.isna(rental_yield) or rental_yield == 0:
                psf = row["price_psf"]
                # Lower PSF = higher yield, Higher PSF = lower yield
                rental_yield = max(2.5, min(4.5, 5.0 - (psf / 2000)))
        else:  # Condominium, Apartment, Condo
            category = 'Condominium'
            # For Condo, estimate yield based on PSF (typical range: 2.0% - 4.0%)
            if pd.isna(rental_yield) or rental_yield == 0:
                psf = row["price_psf"]
                # Lower PSF = higher yield, Higher PSF = lower yield
                rental_yield = max(2.0, min(4.0, 4.5 - (psf / 2500)))

        # Skip if still no rental yield data
        if pd.isna(rental_yield):
            continue

        label = f"{row['planning_area']} - {row['property_type']}"

        segments.append({
            "name": label,
            "x": float(row["price_psf"]),
            "y": float(rental_yield),  # Already in percentage
            "z": int(row["volume"]),  # Bubble size
            "category": category
        })

    return segments

def generate_filtered_segments_data(df):
    """Generate segments data for each era + property type combination."""
    logger.info("Generating filtered segments data...")

    # Define eras
    eras = {
        "whole": df,
        "pre_covid": df[df["transaction_date"].dt.year <= 2021],
        "recent": df[df["transaction_date"].dt.year >= 2022],
        "year_2025": df[df["transaction_date"].dt.year == 2025]
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

    # Generate segments for each combination
    filtered_segments = {}
    for era_name, era_df in eras.items():
        if era_df.empty:
            continue

        # Generate for all property types
        filtered_segments[era_name] = generate_segments_data(era_df)

        # Generate for each property type
        for prop_type in ["hdb", "ec", "condo"]:
            prop_df = filter_by_property_type(era_df, prop_type)
            if not prop_df.empty:
                key = f"{era_name}_{prop_type}"
                filtered_segments[key] = generate_segments_data(prop_df)

    logger.info(f"Generated filtered segments data for {len(filtered_segments)} combinations")
    return filtered_segments

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
