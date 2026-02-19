#!/usr/bin/env python3
"""
Investment EDA Analysis for Singapore Housing Market

Provides quick EDA summaries for HDB investment analysis including:
1. Data quality overview
2. Planning area price trends and appreciation (CAGR)
3. Rental yield analysis by area
4. Investment scoring and recommendations
5. Market momentum analysis

Usage:
    uv run python scripts/analytics/analysis/market/analyze_investment_eda.py
"""

import logging
from pathlib import Path

import pandas as pd

from scripts.core.utils import add_project_to_path

add_project_to_path(Path(__file__))

from scripts.core.config import Config
from scripts.core.stages.helpers.analysis_helpers import save_analysis_result

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_data() -> pd.DataFrame:
    """Load L3 unified dataset."""
    logger.info("Loading L3 unified dataset...")
    path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"

    if not path.exists():
        logger.error(f"Unified dataset not found: {path}")
        return pd.DataFrame()

    df = pd.read_parquet(path)
    logger.info(f"Loaded {len(df):,} records")
    return df


def run_data_quality_overview(df: pd.DataFrame):
    """Display data quality overview."""
    logger.info("\n" + "=" * 80)
    logger.info("DATA QUALITY OVERVIEW")
    logger.info("=" * 80)

    hdb = df[df["property_type"] == "HDB"].copy()

    logger.info(f"Total HDB transactions: {len(hdb):,}")
    logger.info(
        f"Date range: {hdb['transaction_date'].min().strftime('%Y-%m')} to {hdb['transaction_date'].max().strftime('%Y-%m')}"
    )
    logger.info(f"Number of planning areas: {hdb['planning_area'].nunique()}")

    metrics_summary = {
        "price_psm": hdb["price_psm"].notna().sum(),
        "rental_yield_pct": hdb["rental_yield_pct"].notna().sum(),
        "yoy_change_pct": hdb["yoy_change_pct"].notna().sum(),
        "mom_change_pct": hdb["mom_change_pct"].notna().sum(),
        "dist_to_nearest_mrt": hdb["dist_to_nearest_mrt"].notna().sum(),
    }

    logger.info("\nKey Metrics Availability:")
    for metric, count in metrics_summary.items():
        pct = (count / len(hdb) * 100) if len(hdb) > 0 else 0
        logger.info(f"  {metric}: {count:,} ({pct:.1f}%)")


def run_planning_area_overview(df: pd.DataFrame):
    """Display planning area overview."""
    logger.info("\n" + "=" * 80)
    logger.info("PLANNING AREA OVERVIEW")
    logger.info("=" * 80)

    hdb = df[df["property_type"] == "HDB"].copy()

    area_stats = (
        hdb.groupby("planning_area")
        .agg(
            {
                "price": ["count", "mean", "median", "std"],
                "price_psm": ["mean", "median"],
                "floor_area_sqm": "mean",
            }
        )
        .round(2)
    )

    area_stats.columns = ["_".join(col).strip() for col in area_stats.columns.values]
    area_stats = area_stats.sort_values("price_count", ascending=False)

    logger.info("\nTop 15 Planning Areas by Transaction Volume:")
    logger.info(
        f"{'Planning Area':<20} {'Count':>8} {'Mean Price':>15} {'Median Price':>15} {'Mean PSM':>12}"
    )
    logger.info("-" * 75)
    for area, row in area_stats.head(15).iterrows():
        logger.info(
            f"{area:<20} {row['price_count']:>8,} ${row['price_mean']:>13,.0f} ${row['price_median']:>13,.0f} ${row['price_psm_mean']:>10,.0f}"
        )


def run_price_appreciation_analysis(df: pd.DataFrame):
    """Analyze price appreciation by planning area."""
    logger.info("\n" + "=" * 80)
    logger.info("PRICE APPRECIATION ANALYSIS (2015-2025)")
    logger.info("=" * 80)

    hdb = df[df["property_type"] == "HDB"].copy()
    recent_data = hdb[hdb["year"] >= 2015].copy()

    appreciation_by_area = (
        recent_data.groupby(["planning_area", "year"])["price_psm"].mean().unstack()
    )

    cagr_by_area = {}
    for area in appreciation_by_area.index:
        prices = appreciation_by_area.loc[area].dropna()
        if len(prices) >= 2:
            start_price = prices.iloc[0]
            end_price = prices.iloc[-1]
            years = len(prices) - 1
            if start_price > 0 and years > 0:
                cagr = ((end_price / start_price) ** (1 / years) - 1) * 100
                cagr_by_area[area] = {
                    "start_year": prices.index[0],
                    "end_year": prices.index[-1],
                    "start_psm": start_price,
                    "end_psm": end_price,
                    "cagr_pct": cagr,
                    "total_appreciation_pct": ((end_price / start_price) - 1) * 100,
                }

    appreciation_df = pd.DataFrame(cagr_by_area).T
    appreciation_df = appreciation_df.sort_values("cagr_pct", ascending=False)

    save_analysis_result(
        df=appreciation_df.reset_index(),
        category="eda",
        name="price_appreciation_by_area",
        description="Price appreciation (CAGR) by planning area (2015-2025)",
    )

    logger.info("\nTop 10 Planning Areas by Price Appreciation (CAGR):")
    logger.info(
        f"{'Planning Area':<20} {'CAGR %':>10} {'Total %':>12} {'Start PSM':>14} {'End PSM':>14}"
    )
    logger.info("-" * 75)
    for area, row in appreciation_df.head(10).iterrows():
        logger.info(
            f"{area:<20} {row['cagr_pct']:>9.2f}% {row['total_appreciation_pct']:>11.2f}% ${row['start_psm']:>12,.0f} ${row['end_psm']:>12,.0f}"
        )

    return appreciation_df


def run_rental_yield_analysis(df: pd.DataFrame):
    """Analyze rental yield by planning area."""
    logger.info("\n" + "=" * 80)
    logger.info("RENTAL YIELD ANALYSIS BY PLANNING AREA")
    logger.info("=" * 80)

    hdb = df[df["property_type"] == "HDB"].copy()
    rental_data = hdb[hdb["rental_yield_pct"].notna()].copy()

    logger.info(f"\nRecords with rental yield data: {len(rental_data):,}")

    rental_yield_by_area = (
        rental_data.groupby("planning_area")["rental_yield_pct"]
        .agg(
            [
                ("count", "count"),
                ("mean_yield", "mean"),
                ("median_yield", "median"),
                ("std_yield", "std"),
                ("min_yield", "min"),
                ("max_yield", "max"),
            ]
        )
        .round(2)
    )

    rental_yield_by_area = rental_yield_by_area[rental_yield_by_area["count"] >= 50]
    rental_yield_by_area = rental_yield_by_area.sort_values("mean_yield", ascending=False)

    save_analysis_result(
        df=rental_yield_by_area.reset_index(),
        category="eda",
        name="rental_yield_by_area",
        description="Rental yield statistics by planning area",
    )

    logger.info("\nTop 15 Planning Areas by Average Rental Yield:")
    logger.info(f"{'Planning Area':<20} {'Mean Yield':>12} {'Median Yield':>13} {'Count':>8}")
    logger.info("-" * 55)
    for area, row in rental_yield_by_area.head(15).iterrows():
        logger.info(
            f"{area:<20} {row['mean_yield']:>11.2f}% {row['median_yield']:>12.2f}% {row['count']:>8,}"
        )

    return rental_yield_by_area


def run_investment_scoring(
    df: pd.DataFrame, appreciation_df: pd.DataFrame, rental_yield_by_area: pd.DataFrame
):
    """Calculate and display investment attractiveness scores."""
    logger.info("\n" + "=" * 80)
    logger.info("INVESTMENT ATTRACTIVENESS SCORE")
    logger.info("=" * 80)

    combined_scores = pd.merge(
        appreciation_df[["cagr_pct", "total_appreciation_pct"]],
        rental_yield_by_area[["mean_yield", "median_yield"]],
        left_index=True,
        right_index=True,
        how="inner",
    )

    if len(combined_scores) == 0:
        logger.warning("No overlapping data between appreciation and rental yield analysis")
        return combined_scores

    combined_scores["appreciation_zscore"] = (
        combined_scores["cagr_pct"] - combined_scores["cagr_pct"].mean()
    ) / combined_scores["cagr_pct"].std()
    combined_scores["yield_zscore"] = (
        combined_scores["mean_yield"] - combined_scores["mean_yield"].mean()
    ) / combined_scores["mean_yield"].std()

    combined_scores["investment_score"] = (
        combined_scores["appreciation_zscore"] * 0.5 + combined_scores["yield_zscore"] * 0.5
    ) * 10 + 50

    combined_scores["investment_score"] = (
        (combined_scores["investment_score"] - combined_scores["investment_score"].min())
        / (combined_scores["investment_score"].max() - combined_scores["investment_score"].min())
        * 100
    )

    combined_scores = combined_scores.sort_values("investment_score", ascending=False)

    save_analysis_result(
        df=combined_scores.reset_index(),
        category="eda",
        name="investment_scores",
        description="Investment attractiveness scores by planning area",
    )

    logger.info("\nTop 15 Planning Areas by Investment Score:")
    logger.info(f"{'Planning Area':<20} {'Inv Score':>10} {'CAGR %':>10} {'Yield %':>10}")
    logger.info("-" * 52)
    for area, row in combined_scores.head(15).iterrows():
        logger.info(
            f"{area:<20} {row['investment_score']:>9.1f} {row['cagr_pct']:>9.2f}% {row['mean_yield']:>9.2f}%"
        )

    return combined_scores


def run_momentum_analysis(df: pd.DataFrame):
    """Analyze market momentum (YoY changes)."""
    logger.info("\n" + "=" * 80)
    logger.info("MARKET MOMENTUM ANALYSIS")
    logger.info("=" * 80)

    hdb = df[df["property_type"] == "HDB"].copy()
    momentum_data = hdb[hdb["yoy_change_pct"].notna()].copy()

    logger.info(f"\nRecords with YoY change data: {len(momentum_data):,}")

    recent_momentum = momentum_data[momentum_data["year"] >= 2023].copy()
    momentum_by_area = (
        recent_momentum.groupby("planning_area")["yoy_change_pct"]
        .agg(
            [
                ("count", "count"),
                ("mean_yoy_change", "mean"),
                ("median_yoy_change", "median"),
                ("volatility", "std"),
            ]
        )
        .round(2)
    )

    momentum_by_area = momentum_by_area[momentum_by_area["count"] >= 10]
    momentum_by_area["risk_adjusted_momentum"] = momentum_by_area["mean_yoy_change"] / (
        momentum_by_area["volatility"] + 1
    )
    momentum_by_area = momentum_by_area.sort_values("risk_adjusted_momentum", ascending=False)

    save_analysis_result(
        df=momentum_by_area.reset_index(),
        category="eda",
        name="market_momentum",
        description="Market momentum (YoY changes) by planning area",
    )

    logger.info("\nTop 10 Planning Areas by Risk-Adjusted Momentum:")
    logger.info(f"{'Planning Area':<20} {'YoY Change':>12} {'Volatility':>12} {'Risk-Adj':>12}")
    logger.info("-" * 58)
    for area, row in momentum_by_area.head(10).iterrows():
        logger.info(
            f"{area:<20} {row['mean_yoy_change']:>11.2f}% {row['volatility']:>11.2f}% {row['risk_adjusted_momentum']:>11.2f}"
        )

    return momentum_by_area


def run_amenity_impact_summary(df: pd.DataFrame):
    """Display amenity impact correlation summary."""
    logger.info("\n" + "=" * 80)
    logger.info("AMENITY IMPACT ON PRICES")
    logger.info("=" * 80)

    hdb = df[df["property_type"] == "HDB"].copy()

    amenity_cols = [
        "dist_to_nearest_mrt",
        "dist_to_nearest_supermarket",
        "dist_to_nearest_park",
        "dist_to_nearest_hawker",
        "dist_to_nearest_preschool",
        "dist_to_nearest_childcare",
    ]

    amenity_data = hdb[amenity_cols + ["price_psm", "planning_area"]].dropna()

    if len(amenity_data) > 0:
        amenity_corr = amenity_data[["price_psm"] + amenity_cols].corr()["price_psm"].sort_values()

        logger.info("\nCorrelation between Distance to Amenities and Price PSM:")
        logger.info("(Negative = closer amenities -> higher prices)")
        logger.info(f"{'Amenity':<30} {'Correlation':>12}")
        logger.info("-" * 45)
        for amenity, corr in amenity_corr[amenity_cols].items():
            logger.info(f"{amenity:<30} {corr:>12.3f}")
    else:
        logger.warning("No amenity data available for correlation analysis")


def run_eda():
    """Run full EDA pipeline."""
    logger.info("=" * 80)
    logger.info("INVESTMENT EDA ANALYSIS")
    logger.info("=" * 80)

    df = load_data()

    if df.empty:
        logger.error("No data available for EDA")
        return

    run_data_quality_overview(df)
    run_planning_area_overview(df)
    appreciation_df = run_price_appreciation_analysis(df)
    rental_yield_by_area = run_rental_yield_analysis(df)
    run_investment_scoring(df, appreciation_df, rental_yield_by_area)
    run_momentum_analysis(df)
    run_amenity_impact_summary(df)

    logger.info("\n" + "=" * 80)
    logger.info("EDA COMPLETE")
    logger.info("=" * 80)


def main():
    """Main entry point."""
    run_eda()


if __name__ == "__main__":
    main()
