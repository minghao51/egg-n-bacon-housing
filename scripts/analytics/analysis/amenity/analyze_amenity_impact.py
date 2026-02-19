#!/usr/bin/env python3
"""
Amenity Impact Analysis for Singapore Housing Market

Analyzes the impact of amenities and MRT proximity on property prices,
with focus on:
1. Temporal comparison (pre-COVID vs COVID vs post-COVID)
2. Within-town analysis (controlling for town-level effects)
3. Grid-based analysis (500m x 500m, controlling for exact location)
4. MRT distance stratification

Usage:
    uv run python scripts/analyze_amenity_impact.py
"""

import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Add project root to Python path
from scripts.core.config import Config
from scripts.core.utils import add_project_to_path
from scripts.core.stages.helpers.analysis_helpers import save_analysis_result

warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Setup project path
add_project_to_path(Path(__file__))

OUTPUT_DIR = Config.DATA_DIR / "analysis" / "amenity_impact"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_data():
    """Load L3 unified dataset."""
    logger.info("Loading L3 unified dataset...")
    path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
    df = pd.read_parquet(path)
    logger.info(f"Loaded {len(df):,} records")
    return df


def create_grid_id(df, grid_size_meters=500):
    """Create grid IDs from lat/lon coordinates."""
    logger.info(f"Creating {grid_size_meters}m x {grid_size_meters}m grid IDs...")

    meters_per_degree_lat = 111320
    meters_per_degree_lon = 111320 * np.cos(np.radians(1))

    df = df.copy()
    df["grid_lat"] = (df["lat"] * meters_per_degree_lat / grid_size_meters).astype(int)
    df["grid_lon"] = (df["lon"] * meters_per_degree_lon / grid_size_meters).astype(int)
    df["grid_id"] = df["grid_lat"].astype(str) + "_" + df["grid_lon"].astype(str)

    grid_counts = df["grid_id"].value_counts()
    valid_grids = grid_counts[grid_counts >= 10].index
    df = df[df["grid_id"].isin(valid_grids)]

    logger.info(f"Created {df['grid_id'].nunique():,} grids with 10+ transactions")
    return df


def get_amenity_features():
    """Return list of amenity features to analyze."""
    return {
        "mrt_distance": [
            "dist_to_nearest_mrt",
            "mrt_within_500m",
            "mrt_within_1km",
            "mrt_within_2km",
        ],
        "amenities": [
            "dist_to_nearest_hawker",
            "dist_to_nearest_supermarket",
            "dist_to_nearest_park",
            "dist_to_nearest_preschool",
            "dist_to_nearest_childcare",
            "hawker_within_500m",
            "hawker_within_1km",
            "hawker_within_2km",
            "supermarket_within_500m",
            "supermarket_within_1km",
            "supermarket_within_2km",
            "park_within_500m",
            "park_within_1km",
            "park_within_2km",
            "preschool_within_500m",
            "preschool_within_1km",
            "preschool_within_2km",
            "childcare_within_500m",
            "childcare_within_1km",
            "childcare_within_2km",
        ],
    }


def run_temporal_analysis(df):
    """Run feature importance analysis for each time period."""
    logger.info("\n" + "=" * 60)
    logger.info("TEMPORAL ANALYSIS (Pre-COVID vs COVID vs Post-COVID)")
    logger.info("=" * 60)

    periods = {"pre_covid": (2015, 2019), "covid": (2020, 2022), "post_covid": (2023, 2025)}

    amenity_features = get_amenity_features()["mrt_distance"] + get_amenity_features()["amenities"]

    property_features = ["floor_area_sqm", "remaining_lease_months"]
    all_features = amenity_features + property_features

    all_results = []

    for period_name, (start_year, end_year) in periods.items():
        period_df = df[(df["year"] >= start_year) & (df["year"] <= end_year)].copy()
        period_df = period_df.dropna(subset=["price_psm"] + all_features)
        logger.info(
            f"\n{period_name.upper()} ({start_year}-{end_year}): {len(period_df):,} records"
        )

        if len(period_df) < 1000:
            logger.warning(f"Insufficient data for {period_name}")
            continue

        X = period_df[all_features]
        y = period_df["price_psm"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        rf = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42, n_jobs=-1)
        rf.fit(X_train, y_train)

        importance_df = pd.DataFrame(
            {"feature": all_features, "importance": rf.feature_importances_}
        ).sort_values("importance", ascending=False)

        importance_df["period"] = period_name
        importance_df["test_r2"] = rf.score(X_test, y_test)

        logger.info(f"  Test R2: {rf.score(X_test, y_test):.4f}")
        logger.info("  Top 5 features:")
        for _, row in importance_df.head(5).iterrows():
            logger.info(f"    {row['feature']}: {row['importance']:.4f}")

        all_results.append(importance_df)

    results_df = pd.concat(all_results, ignore_index=True)
    save_analysis_result(
        df=results_df,
        category="amenity",
        name="temporal_comparison",
        description="Feature importance by time period (pre-COVID, COVID, post-COVID)",
    )

    return results_df


def run_within_town_analysis(df):
    """Run within-town regression analysis for each town."""
    logger.info("\n" + "=" * 60)
    logger.info("WITHIN-TOWN ANALYSIS (Controlling for town-level effects)")
    logger.info("=" * 60)

    amenity_features = get_amenity_features()["mrt_distance"]
    property_features = ["floor_area_sqm", "remaining_lease_months"]
    all_features = amenity_features + property_features

    town_results = []

    towns = df["town"].dropna().unique()
    logger.info(f"Analyzing {len(towns)} towns...")

    for town in sorted(towns):
        town_df = df[df["town"] == town].copy()
        town_df = town_df.dropna(subset=["price_psm"] + all_features)

        if len(town_df) < 100:
            continue

        X = town_df[all_features]
        y = town_df["price_psm"]

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )

        rf = RandomForestRegressor(n_estimators=50, max_depth=8, random_state=42, n_jobs=-1)
        rf.fit(X_train, y_train)

        importance_df = pd.DataFrame(
            {"feature": all_features, "importance": rf.feature_importances_}
        )

        mrt_importance = importance_df[importance_df["feature"] == "dist_to_nearest_mrt"][
            "importance"
        ].values[0]

        town_results.append(
            {
                "town": town,
                "n_transactions": len(town_df),
                "mrt_distance_importance": mrt_importance,
                "test_r2": rf.score(X_test, y_test),
            }
        )

    results_df = pd.DataFrame(town_results)
    results_df = results_df.sort_values("mrt_distance_importance", ascending=False)

    save_analysis_result(
        df=results_df,
        category="amenity",
        name="within_town_effects",
        description="MRT distance importance by town (controlling for town-level effects)",
    )

    return results_df


def run_grid_analysis(df):
    """Run grid-based analysis (500m x 500m)."""
    logger.info("\n" + "=" * 60)
    logger.info("GRID ANALYSIS (500m x 500m)")
    logger.info("=" * 60)

    df = create_grid_id(df, grid_size_meters=500)
    logger.info(f"Working with {df['grid_id'].nunique():,} grids")

    amenity_features = get_amenity_features()["mrt_distance"]
    property_features = ["floor_area_sqm", "remaining_lease_months"]
    all_features = amenity_features + property_features

    grid_results = []

    grids = df["grid_id"].unique()
    logger.info(f"Processing {len(grids)} grids...")

    for i, grid_id in enumerate(grids):
        if i % 500 == 0:
            logger.info(f"  Processed {i}/{len(grids)} grids...")

        grid_df = df[df["grid_id"] == grid_id].copy()
        grid_df = grid_df.dropna(subset=["price_psm"] + all_features)

        if len(grid_df) < 5:
            continue

        X = grid_df[all_features]
        y = grid_df["price_psm"]

        if len(grid_df) < 20:
            continue

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.3, random_state=42
        )

        rf = RandomForestRegressor(n_estimators=30, max_depth=5, random_state=42, n_jobs=-1)
        try:
            rf.fit(X_train, y_train)

            importance_df = pd.DataFrame(
                {"feature": all_features, "importance": rf.feature_importances_}
            )

            mrt_within_500m_importance = importance_df[
                importance_df["feature"] == "mrt_within_500m"
            ]["importance"].values[0]

            mrt_dist_importance = importance_df[importance_df["feature"] == "dist_to_nearest_mrt"][
                "importance"
            ].values[0]

            grid_results.append(
                {
                    "grid_id": grid_id,
                    "n_transactions": len(grid_df),
                    "mrt_within_500m_importance": mrt_within_500m_importance,
                    "mrt_distance_importance": mrt_dist_importance,
                    "median_price_psm": grid_df["price_psm"].median(),
                    "lat": grid_df["lat"].mean(),
                    "lon": grid_df["lon"].mean(),
                }
            )
        except Exception:
            continue

    results_df = pd.DataFrame(grid_results)
    logger.info(f"\nCompleted analysis for {len(results_df):,} grids")

    logger.info("\nGrid-level MRT impact statistics:")
    logger.info(
        f"  Mean mrt_within_500m importance: {results_df['mrt_within_500m_importance'].mean():.4f}"
    )
    logger.info(
        f"  Median mrt_within_500m importance: {results_df['mrt_within_500m_importance'].median():.4f}"
    )

    save_analysis_result(
        df=results_df,
        category="amenity",
        name="grid_analysis",
        description="Grid-level (500m x 500m) MRT impact analysis",
    )

    return results_df


def run_mrt_distance_stratification(df):
    """Analyze price by MRT distance bands."""
    logger.info("\n" + "=" * 60)
    logger.info("MRT DISTANCE STRATIFICATION")
    logger.info("=" * 60)

    df = df.dropna(subset=["price_psm", "dist_to_nearest_mrt"])

    dist_bands = [0, 200, 400, 600, 800, 1000, 1500, 2000, 3000]
    labels = [
        "0-200m",
        "200-400m",
        "400-600m",
        "600-800m",
        "800-1000m",
        "1000-1500m",
        "1500-2000m",
        "2000m+",
    ]

    df = df.copy()
    df["dist_band"] = pd.cut(
        df["dist_to_nearest_mrt"], bins=dist_bands, labels=labels, include_lowest=True
    )

    band_stats = (
        df.groupby("dist_band")
        .agg(
            {
                "price_psm": ["count", "median", "mean", "std"],
                "dist_to_nearest_mrt": ["min", "max", "mean"],
            }
        )
        .round(2)
    )

    band_stats.columns = ["_".join(col).strip() for col in band_stats.columns.values]
    band_stats = band_stats.reset_index()

    logger.info("\nPrice PSM by MRT distance band:")
    for _, row in band_stats.iterrows():
        if row["price_psm_count"] > 0:
            logger.info(
                f"  {row['dist_band']}: n={row['price_psm_count']:,}, "
                f"median=${row['price_psm_median']:,.0f}/psm"
            )

    save_analysis_result(
        df=band_stats,
        category="amenity",
        name="mrt_distance_stratification",
        description="Price PSM statistics by MRT distance bands",
    )

    return band_stats


def generate_summary_stats(temporal_df, within_town_df, grid_df, dist_strat_df):
    """Generate summary statistics for dashboard."""
    logger.info("\n" + "=" * 60)
    logger.info("GENERATING SUMMARY STATISTICS")
    logger.info("=" * 60)

    summary = {}

    if temporal_df is not None and len(temporal_df) > 0:
        mrt_pre = temporal_df[
            (temporal_df["period"] == "pre_covid")
            & (temporal_df["feature"] == "dist_to_nearest_mrt")
        ]["importance"].values
        mrt_covid = temporal_df[
            (temporal_df["period"] == "covid") & (temporal_df["feature"] == "dist_to_nearest_mrt")
        ]["importance"].values
        mrt_post = temporal_df[
            (temporal_df["period"] == "post_covid")
            & (temporal_df["feature"] == "dist_to_nearest_mrt")
        ]["importance"].values

        summary["mrt_importance_pre_covid"] = mrt_pre[0] if len(mrt_pre) > 0 else None
        summary["mrt_importance_covid"] = mrt_covid[0] if len(mrt_covid) > 0 else None
        summary["mrt_importance_post_covid"] = mrt_post[0] if len(mrt_post) > 0 else None

        if summary["mrt_importance_pre_covid"] and summary["mrt_importance_post_covid"]:
            change = (
                (summary["mrt_importance_post_covid"] - summary["mrt_importance_pre_covid"])
                / summary["mrt_importance_pre_covid"]
                * 100
            )
            summary["mrt_importance_change_pct"] = change

    if within_town_df is not None and len(within_town_df) > 0:
        summary["avg_mrt_within_town_importance"] = within_town_df["mrt_distance_importance"].mean()
        summary["top_mrt_sensitive_town"] = within_town_df.iloc[0]["town"]
        summary["top_mrt_sensitive_town_importance"] = within_town_df.iloc[0][
            "mrt_distance_importance"
        ]

    if grid_df is not None and len(grid_df) > 0:
        summary["avg_grid_mrt_importance"] = grid_df["mrt_within_500m_importance"].mean()
        summary["grids_with_high_mrt_impact"] = int(
            (grid_df["mrt_within_500m_importance"] > 0.1).sum()
        )

    if dist_strat_df is not None and len(dist_strat_df) > 0:
        closest_band = dist_strat_df.iloc[0]
        farthest_band = dist_strat_df.iloc[-1]
        if closest_band["price_psm_median"] and farthest_band["price_psm_median"]:
            premium = (
                (closest_band["price_psm_median"] - farthest_band["price_psm_median"])
                / farthest_band["price_psm_median"]
                * 100
            )
            summary["mrt_proximity_premium_pct"] = premium

    summary_df = pd.DataFrame([summary])
    save_analysis_result(
        df=summary_df,
        category="amenity",
        name="amenity_summary_stats",
        description="Summary statistics for amenity impact analysis",
    )

    logger.info("\n=== KEY FINDINGS ===")
    if "mrt_importance_change_pct" in summary:
        logger.info(
            f"MRT importance change (Pre-COVID to Post-COVID): {summary['mrt_importance_change_pct']:.1f}%"
        )
    if "mrt_proximity_premium_pct" in summary:
        logger.info(
            f"MRT proximity premium (closest vs farthest band): {summary['mrt_proximity_premium_pct']:.1f}%"
        )
    if "top_mrt_sensitive_town" in summary:
        logger.info(f"Town with highest MRT sensitivity: {summary['top_mrt_sensitive_town']}")

    return summary_df


def main():
    """Main analysis pipeline."""
    logger.info("=" * 60)
    logger.info("AMENITY IMPACT ANALYSIS")
    logger.info("=" * 60)

    df = load_data()

    temporal_df = run_temporal_analysis(df)
    within_town_df = run_within_town_analysis(df)
    grid_df = run_grid_analysis(df)
    dist_strat_df = run_mrt_distance_stratification(df)

    generate_summary_stats(temporal_df, within_town_df, grid_df, dist_strat_df)

    logger.info("\n" + "=" * 60)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 60)
    logger.info(f"\nOutput directory: {OUTPUT_DIR}")
    logger.info("\nGenerated files:")
    for f in OUTPUT_DIR.iterdir():
        if f.is_file():
            logger.info(f"  - {f.name}")


if __name__ == "__main__":
    main()
