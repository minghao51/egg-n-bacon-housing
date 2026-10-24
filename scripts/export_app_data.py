#!/usr/bin/env python3
"""Export Hamilton pipeline outputs to the Astro app's dashboard JSON assets.

Regenerates exactly the seven dashboard data files consumed by the app under
``app/public/data/`` (all gzipped JSON, atomically written):

    dashboard_overview.json.gz      market stats by era x property type
    dashboard_trends.json.gz        monthly median price / volume series
    dashboard_segments.json.gz      PSF-vs-yield scatter per era x type
    dashboard_leaderboard.json.gz   planning-area leaderboard with breakdowns
    map_metrics.json.gz             per-area metrics per era x type (19 views)
    hotspots.json.gz                appreciation classification per area
    amenity_summary.json.gz         mean amenity distances per area

Everything else in ``app/public/data/`` (segments_enhanced, interactive_tools/,
analytics/, planning_areas*, catalog.jsonl.gz) is owned by separate workflows
and is deliberately not touched.

Writes are staged: every payload is serialized+gzipped to a ``.tmp`` sibling
first, and only once all seven exist and are non-empty are they swapped in via
``os.replace``. Atomicity is therefore per file — the window in which a reader
could see a mixed generation is narrowed to the seven replaces, not eliminated.

Inputs (Hamilton platinum outputs, read-only):

    data/pipeline/04_platinum/unified_dataset.parquet
    data/pipeline/04_platinum/metrics/pa_monthly_metrics.parquet
    data/manual/geojsons/ura_planning_area_boundary.geojson   (leaderboard
        region + centroid metadata; onemap polygon fallback)

Growth (MoM/YoY/momentum), hotspot classification, rental-yield stats, and the
mortgage-based ``mortgage_to_income_pct`` are derived here with the same
formulas the retired web exporter used, so the frontend semantics are
unchanged. The monthly growth series is built from ``pa_monthly_metrics``
(the pipeline's own planning-area x month median-price table) instead of
re-aggregating raw transactions. The current calendar month is treated as
partial and dropped before any growth/trends math, so published growth and
the trends series end at the last completed month; year-bucketed leaderboard
growth pairs completed years only. Affordability ratio/class use the
pipeline-configured income and thresholds instead of the retired exporter's
hardcoded values — see "Affordability semantics" in app/public/data/README.md.

Refresh flow: run after ``main.py --stage all``, then validate:

    uv run python scripts/export_app_data.py
    cd app && bun scripts/validate-data.mjs

Exit codes: 0 success, 1 export/validation failure, 2 CLI usage error.
"""

import argparse
import gzip
import json
import math
import os
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from egg_n_bacon_housing.config import settings  # noqa: E402
from egg_n_bacon_housing.utils.logging_config import get_logger, setup_logging  # noqa: E402

logger = get_logger(__name__)

DEFAULT_OUTPUT_DIR = ROOT / "app" / "public" / "data"

# ---------------------------------------------------------------------------
# Contract constants (frozen by app/src types + app/public/data/manifest.json)
# ---------------------------------------------------------------------------

ERA_FILTERS: dict[str, str] = {
    "whole": "all",
    "pre_covid": "year <= 2021",
    "recent": "year >= 2022",
    "year_2025": "year == 2025",
}
PROPERTY_TYPE_FILTERS: dict[str, str] = {
    "hdb": "HDB",
    "ec": "EC",
    "condo": "Condominium",
}

# Old momentum_signal banding (L5 metrics): 3m growth minus 12m growth.
MOMENTUM_BINS = [-np.inf, -5, -2, 2, 5, np.inf]
MOMENTUM_LABELS = [
    "Strong Deceleration",
    "Moderate Deceleration",
    "Stable",
    "Moderate Acceleration",
    "Strong Acceleration",
]

# Planning areas with no residential zoning in URA's master plan: nature
# reserves and industrial land. A few transactions still geocode into these
# polygons (road-point and boundary effects), but publishing them as housing
# areas is misleading — with such tiny samples they also top the ranking.
# Area-level surfaces exclude them; global aggregates (dashboard_overview)
# intentionally keep every row.
NON_RESIDENTIAL_AREAS = frozenset(
    {
        "CENTRAL WATER CATCHMENT",
        "MANDAI",
        "SUNGEI KADUT",
    }
)

# Minimum trailing-12-month (completed months) transactions for an area to be
# RANKED on the comparison board. Below it, YoY growth and rental yield are
# noise — a 3-transaction area would outrank a 20,000-transaction town. Such
# areas stay in the payload but sort after every qualified area.
MIN_RANKING_VOLUME = 150

# Old mortgage assumptions (scripts/core/metrics.py): 20% down, 3.5% interest,
# 25-year loan — used for mortgage_to_income_pct only.
MORTGAGE_DOWN_PAYMENT_PCT = 0.20
MORTGAGE_INTEREST_RATE = 0.035
MORTGAGE_LOAN_TERM_YEARS = 25.0

# Map sections that receive growth enrichment (the old exporter skipped the
# year_2025 views here because YoY at a single-year boundary is meaningless).
GROWTH_SECTIONS = [
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
]
# Every map view receives yield/affordability enrichment: standalone eras,
# standalone property types, and era x type combinations (19 views).
YIELD_SECTIONS = (
    list(ERA_FILTERS)
    + list(PROPERTY_TYPE_FILTERS)
    + [f"{era}_{prop}" for era in ERA_FILTERS for prop in PROPERTY_TYPE_FILTERS]
)

# Unified-dataset distance columns -> amenity_summary.json.gz keys. The old
# exporter also emitted mrt_exit distances and 500m radius counts; the current
# unified dataset no longer carries those columns, so they are omitted.
AMENITY_DISTANCE_COLUMNS = {
    "dist_to_nearest_hawker": "avg_dist_to_hawker",
    "dist_to_nearest_supermarket": "avg_dist_to_supermarket",
    "dist_to_nearest_mrt": "avg_dist_to_mrt_station",
    "dist_to_nearest_childcare": "avg_dist_to_childcare",
    "dist_to_nearest_park": "avg_dist_to_park",
    "dist_to_nearest_mall": "avg_dist_to_mall",
}

REQUIRED_UNIFIED_COLUMNS = [
    "transaction_date",
    "price",
    "psf",
    "property_type",
    "is_ec",
    "planning_area",
    "town",
    "rental_yield_pct",
]

# GeoJSON sources for leaderboard region + centroid metadata (URA first: it
# carries REGION_N; onemap polygon is the fallback without region info).
GEOJSON_CANDIDATES = [
    "manual/geojsons/ura_planning_area_boundary.geojson",
    "manual/geojsons/onemap_planning_area_polygon.geojson",
]

# ---------------------------------------------------------------------------
# JSON helpers (ported from the retired exporter)
# ---------------------------------------------------------------------------


def safe_float(val, default=None):
    """Safely convert value to float, returning default if NaN/Inf."""
    try:
        f = float(val)
        if pd.isna(f) or np.isinf(f):
            return default
        return round(f, 2)
    except (ValueError, TypeError):
        return default


def sanitize_for_json(obj):
    """Recursively replace NaN/Inf (and numpy scalars) with JSON-safe values."""
    if isinstance(obj, (float, np.floating)):
        if pd.isna(obj) or np.isinf(obj):
            return None
        return float(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(v) for v in obj]
    return obj


def stage_json_gzip(payload, filepath: Path) -> Path:
    """Serialize gzipped JSON to a ``.tmp`` sibling; target is untouched."""
    tmp_path = filepath.with_name(filepath.name + ".tmp")
    with gzip.open(tmp_path, "wt", encoding="utf-8") as f:
        json.dump(sanitize_for_json(payload), f, indent=2)
    return tmp_path


# ---------------------------------------------------------------------------
# Data loading and derived columns
# ---------------------------------------------------------------------------


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the platinum parquets the export depends on; exit 1 if unusable."""
    unified_path = settings.platinum_dir / "unified_dataset.parquet"
    pa_metrics_path = settings.layer_dir("platinum_metrics") / "pa_monthly_metrics.parquet"

    missing = [str(p) for p in (unified_path, pa_metrics_path) if not p.exists()]
    if missing:
        logger.error("Missing required pipeline parquet(s): %s", ", ".join(missing))
        raise SystemExit(1)

    unified = pd.read_parquet(unified_path)
    pa_metrics = pd.read_parquet(pa_metrics_path)

    if unified.empty:
        logger.error("Unified dataset is empty: %s", unified_path)
        raise SystemExit(1)
    if pa_metrics.empty:
        logger.error("PA monthly metrics table is empty: %s", pa_metrics_path)
        raise SystemExit(1)

    missing_cols = [c for c in REQUIRED_UNIFIED_COLUMNS if c not in unified.columns]
    if missing_cols:
        logger.error("Unified dataset missing required column(s): %s", ", ".join(missing_cols))
        raise SystemExit(1)

    logger.info("Loaded unified dataset: %d rows", len(unified))
    logger.info("Loaded PA monthly metrics: %d rows", len(pa_metrics))
    return unified, pa_metrics


def prepare_unified(df: pd.DataFrame) -> pd.DataFrame:
    """Add the derived time + normalized-label columns every exporter uses."""
    df = df.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df["month"] = df["transaction_date"].dt.to_period("M").astype(str)
    df["year"] = df["transaction_date"].dt.year

    # The current pipeline stores lowercase segments ('hdb'/'condo') with an
    # is_ec flag; the dashboard contract speaks in HDB / Condominium / EC.
    prop_lower = df["property_type"].astype(str).str.lower()
    is_ec = df["is_ec"].astype("boolean").fillna(False).astype(bool)
    df["property_label"] = np.select(
        condlist=[
            is_ec,
            prop_lower.isin({"hdb", "hdb flat"}),
            prop_lower.isin({"executive condominium", "ec"}),
        ],
        choicelist=["EC", "HDB", "EC"],
        default="Condominium",
    )
    return df


def era_subset(df: pd.DataFrame, era: str) -> pd.DataFrame:
    """Filter a frame by dashboard era key."""
    rule = ERA_FILTERS[era]
    if rule == "all":
        return df
    return df.query(rule)


def type_subset(df: pd.DataFrame, prop: str | None) -> pd.DataFrame:
    """Filter a frame by dashboard property-type key (None = all types)."""
    if prop is None:
        return df
    return df[df["property_label"] == PROPERTY_TYPE_FILTERS[prop]]


# ---------------------------------------------------------------------------
# Derived metric tables (old L5 formulas, pipeline inputs)
# ---------------------------------------------------------------------------


def drop_incomplete_trailing_month(
    df: pd.DataFrame, month_col: str, today: date | None = None
) -> pd.DataFrame:
    """Drop monthly buckets in the current calendar month (UTC) or later.

    The latest source month is typically partial (publishers release it
    progressively), so a trailing partial bucket would pollute every trailing
    snapshot: MoM/YoY/momentum math, hotspot YoY means, and the trends series
    all key off the last bucket. A bucket is kept only when its month is
    strictly before ``today``'s calendar month; ``today`` is injectable for
    tests.
    """
    if today is None:
        today = datetime.now(UTC).date()
    current_month = pd.Period(today, freq="M")
    months = pd.PeriodIndex(pd.to_datetime(df[month_col]), freq="M")
    return df.loc[months < current_month]


def last_completed_year(today: date | None = None) -> int:
    """Latest calendar year whose buckets are complete (UTC clock).

    Year-bucketed growth must not pair the current (still partial) year
    against a completed one; mirrors ``drop_incomplete_trailing_month`` for
    year buckets.
    """
    if today is None:
        today = datetime.now(UTC).date()
    return today.year - 1


def drop_non_residential(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows in planning areas with no residential zoning.

    Applied to the area-level surfaces (leaderboard, map, segments, hotspots,
    amenity summary) only: a nature reserve or industrial estate is not a
    housing area, and the handful of rows that geocode into those polygons
    would otherwise be published as one. Global aggregates keep every row.
    """
    if "planning_area" not in df.columns:
        return df
    return df[~df["planning_area"].astype(str).str.upper().isin(NON_RESIDENTIAL_AREAS)]


def recent_volume_by_area(
    df: pd.DataFrame, month_col: str = "month", today: date | None = None
) -> pd.Series:
    """Transactions per planning area over the last 12 completed months.

    This is the sample size behind the trailing YoY/yield figures, so it is
    what ``MIN_RANKING_VOLUME`` gates — the published ``volume`` field spans
    the multi-year recent window and is not comparable.
    """
    if df.empty or "planning_area" not in df.columns:
        return pd.Series(dtype="int64")
    if today is None:
        today = datetime.now(UTC).date()
    months = pd.PeriodIndex(pd.to_datetime(df[month_col]), freq="M")
    window_start = pd.Period(today, freq="M") - 12
    window = df.loc[(months >= window_start) & (months < pd.Period(today, freq="M"))]
    return window.groupby("planning_area").size()


def build_growth_table(pa_metrics: pd.DataFrame, today: date | None = None) -> pd.DataFrame:
    """MoM/YoY/momentum per planning area x month from monthly median prices.

    Same math as the retired L5 ``calculate_growth_metrics_by_area``, fed from
    the pipeline's own ``pa_monthly_metrics`` median-price series. Buckets in
    the current (partial) calendar month are dropped first so every trailing
    growth snapshot and the hotspot classification key off completed months.
    ``today`` (UTC date) is injectable for tests.
    """
    complete = drop_incomplete_trailing_month(pa_metrics, "month", today)
    growth = complete.sort_values(["planning_area", "month"]).copy()
    grouped = growth.groupby("planning_area")["median_price"]
    growth["mom_change_pct"] = grouped.transform(lambda x: x.pct_change() * 100)
    growth["yoy_change_pct"] = grouped.transform(lambda x: x.pct_change(12) * 100)
    growth["growth_3m"] = grouped.transform(lambda x: x.pct_change(3) * 100)
    growth["growth_12m"] = grouped.transform(lambda x: x.pct_change(12) * 100)
    growth["momentum"] = growth["growth_3m"] - growth["growth_12m"]
    growth["momentum_signal"] = pd.cut(
        growth["momentum"], bins=MOMENTUM_BINS, labels=MOMENTUM_LABELS
    )
    return growth


def latest_growth_by_area(growth: pd.DataFrame) -> dict[str, dict]:
    """Latest-month growth snapshot per planning area (lowercased keys)."""
    latest = growth.sort_values("month").groupby("planning_area").last()
    latest.index = latest.index.astype(str).str.lower()
    return latest[["mom_change_pct", "yoy_change_pct", "momentum", "momentum_signal"]].to_dict(
        "index"
    )


def rental_yield_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Per-area rental yield mean/median/std over rows with yield data.

    Mirrors the retired L5 ``calculate_rental_yield_by_area`` including the
    minimum-sample filter (>= 10 transactions with yield data).
    """
    yield_df = df[df["rental_yield_pct"].notna()]
    stats = (
        yield_df.groupby("planning_area")["rental_yield_pct"]
        .agg([("count", "count"), ("mean", "mean"), ("median", "median"), ("std", "std")])
        .reset_index()
    )
    return stats[stats["count"] >= 10]


def yield_lookup(df: pd.DataFrame, value_cols: list[str]) -> dict[str, dict]:
    """Lowercased-area lookup into rental-yield stats for the given columns."""
    stats = rental_yield_stats(df)
    if stats.empty:
        return {}
    indexed = stats.set_index("planning_area")[value_cols].copy()
    indexed.index = indexed.index.astype(str).str.lower()
    return indexed.to_dict("index")


def monthly_mortgage_payment(price: float) -> float:
    """Monthly mortgage payment (20% down, 3.5% interest, 25-year term)."""
    loan_amount = price * (1 - MORTGAGE_DOWN_PAYMENT_PCT)
    monthly_rate = MORTGAGE_INTEREST_RATE / 12
    num_payments = MORTGAGE_LOAN_TERM_YEARS * 12
    return loan_amount * (
        (monthly_rate * (1 + monthly_rate) ** num_payments)
        / ((1 + monthly_rate) ** num_payments - 1)
    )


def affordability_lookup(df: pd.DataFrame) -> dict[str, dict]:
    """Per-area affordability from all-time median prices.

    Port of the retired L5 ``calculate_affordability_by_area``: median price
    divided by a flat national median annual household income (the old
    hardcoded 90k replaced by the pipeline-configured
    ``metrics.median_household_income``), banded with the pipeline's
    affordability thresholds. The unified table's ``median_monthly_income``
    is a flat placeholder for HDB rows and null for condos, so it cannot be
    used per area. ``mortgage_to_income_pct`` keeps the old fixed-mortgage
    formula (20% down, 3.5% interest, 25-year term).
    """
    annual_income = float(settings.metrics.median_household_income)
    thresholds = settings.metrics.affordability_thresholds

    area_prices = df.groupby("planning_area")["price"].median()
    lookup = {}
    for area, median_price in area_prices.items():
        ratio = float(median_price) / annual_income
        if ratio < thresholds["affordable"]:
            aff_class = "Affordable"
        elif ratio < thresholds["moderate"]:
            aff_class = "Moderate"
        elif ratio < thresholds["expensive"]:
            aff_class = "Expensive"
        else:
            aff_class = "Severely Unaffordable"
        lookup[str(area).lower()] = {
            "affordability_ratio": safe_float(ratio),
            "affordability_class": aff_class,
            "mortgage_to_income_pct": safe_float(
                monthly_mortgage_payment(float(median_price)) * 12 / annual_income * 100
            ),
        }
    return lookup


def build_hotspots(growth: pd.DataFrame) -> dict[str, dict]:
    """Appreciation classification per planning area.

    Port of the retired L5 ``identify_appreciation_hotspots``: aggregate each
    area's monthly YoY changes, keep areas with >= 3 months of YoY history,
    score consistency (share of months with positive YoY), and band into the
    Elite/High/Moderate/Low Growth categories the frontend expects.
    """
    if growth.empty or "yoy_change_pct" not in growth.columns:
        return {}

    yoy = growth[growth["yoy_change_pct"].notna()]
    stats = (
        yoy.groupby("planning_area")["yoy_change_pct"]
        .agg(
            [("mean_yoy", "mean"), ("median_yoy", "median"), ("std_yoy", "std"), ("years", "count")]
        )
        .reset_index()
    )
    stats = stats[stats["years"] >= 3]
    if stats.empty:
        return {}

    total_months = growth.groupby("planning_area").size()
    positive_months = growth[growth["yoy_change_pct"] > 0].groupby("planning_area").size()
    consistency = (positive_months / total_months).fillna(0).reset_index()
    consistency.columns = ["planning_area", "consistency"]
    stats = stats.merge(consistency, on="planning_area")

    def categorize(row) -> str:
        if row["consistency"] >= 0.7 and row["mean_yoy"] > 10:
            return "Elite Hotspot"
        if row["consistency"] >= 0.5 and row["mean_yoy"] > 5:
            return "High Growth"
        if row["mean_yoy"] > 0:
            return "Moderate Growth"
        return "Low Growth"

    hotspots = {}
    for _, row in stats.iterrows():
        area_key = str(row["planning_area"]).upper()
        if area_key in NON_RESIDENTIAL_AREAS:
            continue
        hotspots[area_key] = {
            "category": categorize(row),
            "mean_yoy_growth": safe_float(row["mean_yoy"], 0),
            "median_yoy_growth": safe_float(row["median_yoy"], 0),
            "std_yoy_growth": safe_float(row["std_yoy"], 0),
            "consistency": safe_float(row["consistency"], 0),
            "years": int(row["years"]),
        }
    return hotspots


# ---------------------------------------------------------------------------
# Exporters (one per dashboard file; old formulas, normalized labels)
# ---------------------------------------------------------------------------


def get_stats(sub_df: pd.DataFrame) -> dict:
    """Count/median block used by the overview stats cards."""
    if sub_df.empty:
        return {"count": 0, "median_price": 0, "median_psf": 0, "volume": 0}
    return {
        "count": int(len(sub_df)),
        "median_price": int(sub_df["price"].median()),
        "median_psf": int(sub_df["psf"].median()),
        "volume": int(len(sub_df)),
    }


def generate_overview_data(df: pd.DataFrame) -> dict:
    """Overview stats for whole/pre_covid/recent/year_2025 x all/HDB/EC/condo."""
    eras = {era: era_subset(df, era) for era in ERA_FILTERS}

    stats: dict[str, dict] = {}
    for era, era_df in eras.items():
        stats[era] = get_stats(era_df)
        for prop in PROPERTY_TYPE_FILTERS:
            stats[f"{era}_{prop}"] = get_stats(type_subset(era_df, prop))

    return {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_records": int(len(df)),
            "date_range": {
                "start": df["transaction_date"].min().strftime("%Y-%m-%d"),
                "end": df["transaction_date"].max().strftime("%Y-%m-%d"),
            },
        },
        "stats": stats,
        "distributions": {
            "property_type": df["property_label"].value_counts().to_dict(),
            "planning_area": df["planning_area"].value_counts().head(10).to_dict(),
        },
    }


def generate_trends_data(df: pd.DataFrame, today: date | None = None) -> list[dict]:
    """Monthly series: 'Overall Price' plus '<label> Price'/'<label> Volume'.

    Every row carries the full eight-key contract; months without a segment's
    sales emit ``null`` (the frontend treats null and absent keys alike, and
    the payload validator requires the complete key set on every row). The
    current (partial) calendar month is dropped, so the series ends at the
    last completed month. ``today`` (UTC date) is injectable for tests.
    """
    df = drop_incomplete_trailing_month(df, "month", today)
    price_pivot = df.pivot_table(
        index="month", columns="property_label", values="price", aggfunc="median"
    )
    vol_pivot = df.pivot_table(
        index="month", columns="property_label", values="price", aggfunc="count"
    )
    overall = df.groupby("month")["price"].median()

    def cell(pivot: pd.DataFrame, label: str, month: str):
        value = pivot[label].get(month, np.nan) if label in pivot.columns else np.nan
        return int(value) if pd.notna(value) else None

    trends = []
    for m in sorted(df["month"].unique()):
        overall_price = overall.get(m)
        record: dict = {
            "date": m,
            "Overall Price": int(overall_price) if pd.notna(overall_price) else None,
        }
        for label in PROPERTY_TYPE_FILTERS.values():
            record[f"{label} Price"] = cell(price_pivot, label, m)
            record[f"{label} Volume"] = cell(vol_pivot, label, m)
        trends.append(record)
    return trends


def generate_map_metrics_for_subset(sub_df: pd.DataFrame) -> dict[str, dict]:
    """Median price/PSF + volume per planning area for one dashboard view."""
    if sub_df.empty:
        return {}
    agg = (
        sub_df.groupby("planning_area")
        .agg(
            median_price=("price", "median"),
            median_psf=("psf", "median"),
            volume=("price", "count"),
        )
        .reset_index()
    )
    return {
        str(row["planning_area"]).upper(): {
            "median_price": int(row["median_price"]),
            "median_psf": int(row["median_psf"]),
            "volume": int(row["volume"]),
        }
        for _, row in agg.iterrows()
    }


def generate_map_data(
    df: pd.DataFrame,
    growth_lookup: dict[str, dict],
    whole_yield: dict[str, dict],
    affordability: dict[str, dict],
) -> dict:
    """19 era x property-type views of per-area metrics with enrichments."""
    base_metrics: dict[str, dict] = {}
    for era in ERA_FILTERS:
        era_df = era_subset(df, era)
        base_metrics[era] = generate_map_metrics_for_subset(era_df)
        for prop in PROPERTY_TYPE_FILTERS:
            base_metrics[f"{era}_{prop}"] = generate_map_metrics_for_subset(
                type_subset(era_df, prop)
            )
    for prop in PROPERTY_TYPE_FILTERS:
        base_metrics[prop] = generate_map_metrics_for_subset(type_subset(df, prop))

    # Growth enrichment: latest MoM/YoY/momentum snapshot per area.
    for section in GROWTH_SECTIONS:
        for area_name, metrics in base_metrics[section].items():
            row = growth_lookup.get(area_name.lower())
            if row:
                metrics["mom_change_pct"] = safe_float(row.get("mom_change_pct"), 0)
                metrics["yoy_change_pct"] = safe_float(row.get("yoy_change_pct"), 0)
                metrics["momentum"] = safe_float(row.get("momentum"), 0)
                signal = row.get("momentum_signal")
                metrics["momentum_signal"] = (
                    "Unknown"
                    if signal is None or (isinstance(signal, float) and pd.isna(signal))
                    else str(signal)
                )

    # Rental yield enrichment (whole-history stats) on every view.
    for section in YIELD_SECTIONS:
        for area_name, metrics in base_metrics[section].items():
            y_data = whole_yield.get(area_name.lower())
            if y_data:
                metrics["rental_yield_mean"] = safe_float(y_data.get("mean"))
                metrics["rental_yield_median"] = safe_float(y_data.get("median"))
                metrics["rental_yield_std"] = safe_float(y_data.get("std"))

    # Affordability enrichment on every view.
    for section in YIELD_SECTIONS:
        for area_name, metrics in base_metrics[section].items():
            a_data = affordability.get(area_name.lower())
            if a_data:
                metrics["affordability_ratio"] = safe_float(a_data.get("affordability_ratio"))
                metrics["affordability_class"] = str(a_data.get("affordability_class", "Unknown"))
                metrics["mortgage_to_income_pct"] = safe_float(a_data.get("mortgage_to_income_pct"))

    return base_metrics


def generate_segments_data(df: pd.DataFrame, yield_by_area: dict[str, float]) -> list[dict]:
    """PSF-vs-yield scatter points (recent years) for one dashboard view."""
    df_recent = df[df["year"] >= 2022]
    if df_recent.empty:
        return []

    agg = (
        df_recent.groupby(["planning_area", "property_label"])
        .agg(
            psf=("psf", "median"), raw_yield=("rental_yield_pct", "mean"), volume=("price", "count")
        )
        .reset_index()
    )
    agg = agg[agg["volume"] > 10]

    segments = []
    for _, row in agg.iterrows():
        rental_yield = row["raw_yield"]
        label = row["property_label"]
        if pd.isna(rental_yield) or rental_yield == 0:
            if label == "HDB":
                # HDB: fall back to the area's aggregate yield metric.
                rental_yield = yield_by_area.get(str(row["planning_area"]).lower())
            elif label == "EC":
                psf = row["psf"]
                rental_yield = max(2.5, min(4.5, 5.0 - (psf / 2000)))
            else:
                psf = row["psf"]
                rental_yield = max(2.0, min(4.0, 4.5 - (psf / 2500)))
        if rental_yield is None or pd.isna(rental_yield):
            continue
        segments.append(
            {
                "name": f"{row['planning_area']} - {label}",
                "x": float(row["psf"]),
                "y": float(rental_yield),
                "z": int(row["volume"]),
                "category": label,
            }
        )
    return segments


def _segment_yield_lookup(df_subset: pd.DataFrame) -> dict[str, float]:
    """Recent-window HDB yield fallback values for one dashboard view.

    Port of the old ``_build_segment_yield_lookup``: the >= 2022 subset of the
    given view, only when it contains HDB rows, aggregated with the same
    minimum-sample filter as the yield stats.
    """
    if df_subset.empty or not df_subset["property_label"].eq("HDB").any():
        return {}
    recent = df_subset[df_subset["year"] >= 2022]
    if recent.empty:
        return {}
    stats = rental_yield_stats(recent)
    if stats.empty:
        return {}
    series = stats.set_index("planning_area")["mean"]
    series.index = series.index.astype(str).str.lower()
    return series.to_dict()


def generate_filtered_segments_data(df: pd.DataFrame) -> dict:
    """Segments for every era x property-type combination."""
    filtered: dict[str, list[dict]] = {}
    for era in ERA_FILTERS:
        era_df = era_subset(df, era)
        if era_df.empty:
            continue
        filtered[era] = generate_segments_data(era_df, _segment_yield_lookup(era_df))
        for prop in PROPERTY_TYPE_FILTERS:
            prop_df = type_subset(era_df, prop)
            if not prop_df.empty:
                filtered[f"{era}_{prop}"] = generate_segments_data(
                    prop_df, _segment_yield_lookup(prop_df)
                )
    return filtered


def _ranking_score(entry: dict) -> float:
    """Default comparison score; missing components count as 0."""
    return (safe_float(entry.get("yoy_growth_pct")) or 0.0) + (
        safe_float(entry.get("rental_yield_mean")) or 0.0
    )


def generate_leaderboard_data(
    df: pd.DataFrame,
    growth_lookup: dict[str, dict],
    recent_yield: dict[str, dict],
    affordability: dict[str, dict],
    hotspots: dict[str, dict],
    area_metadata: dict[str, dict],
    today: date | None = None,
) -> list[dict]:
    """Planning-area leaderboard rows with era/type breakdowns and ranking.

    ``today`` (UTC date) is injectable for tests; it fixes the completed-year
    pair used for YoY growth.
    """
    df_recent = df[df["year"] >= 2022]

    area_metrics = (
        df_recent.groupby("planning_area")
        .agg(
            median_price=("price", "median"),
            median_psf=("psf", "median"),
            rental_yield_mean=("rental_yield_pct", "mean"),
            volume=("price", "count"),
        )
        .reset_index()
    )

    area_metrics["rental_yield_median"] = area_metrics["planning_area"].map(
        lambda area: safe_float((recent_yield.get(str(area).lower()) or {}).get("median"))
    )

    # YoY growth over the most recent full year pair inside the recent window;
    # the current calendar year is still partial and is excluded from the pair
    # (same completed-buckets rule as the monthly growth series).
    current_year = min(int(df_recent["year"].max()), last_completed_year(today))
    prev_year = current_year - 1
    price_curr = (
        df_recent[df_recent["year"] == current_year].groupby("planning_area")["price"].median()
    )
    price_prev = (
        df_recent[df_recent["year"] == prev_year].groupby("planning_area")["price"].median()
    )
    yoy = ((price_curr - price_prev) / price_prev * 100).rename("yoy_growth_pct")
    area_metrics = area_metrics.merge(yoy.reset_index(), on="planning_area", how="left")

    result = []
    for _, row in area_metrics.iterrows():
        area_name = str(row["planning_area"])
        area_lower = area_name.lower()
        meta = area_metadata.get(area_lower, {})

        growth = growth_lookup.get(area_lower, {})
        mom_change = safe_float(growth.get("mom_change_pct"))
        momentum = safe_float(growth.get("momentum"))
        aff_ratio = safe_float(affordability.get(area_lower, {}).get("affordability_ratio"))

        result.append(
            {
                "planning_area": area_name,
                "region": meta.get("region", "Unknown"),
                "coordinates": meta.get("coordinates"),
                "spatial_hotspot": hotspots.get(area_name.upper(), {}).get("category", "Unknown"),
                "rank_overall": 0,  # assigned after sorting below
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
                "affordability_ratio": aff_ratio if aff_ratio else 0,
                "by_property_type": _property_type_breakdown(df, area_name),
                "by_time_period": _time_period_breakdown(df, area_name, today),
            }
        )

    # Ranking gate: an area needs MIN_RANKING_VOLUME trailing-12-month
    # transactions to be ranked on merit. Thin areas keep their row but sort
    # after every qualified area, so noisy tiny-sample growth/yield can never
    # top the board. NaN scores (area missing one component) sort as 0 so the
    # order stays deterministic instead of inheriting NaN comparison quirks.
    recent_volume = recent_volume_by_area(df, today=today)
    result.sort(
        key=lambda entry: (
            int(recent_volume.get(entry["planning_area"], 0)) >= MIN_RANKING_VOLUME,
            _ranking_score(entry),
        ),
        reverse=True,
    )
    for rank, entry in enumerate(result, 1):
        entry["rank_overall"] = rank
    return result


def _property_type_breakdown(df: pd.DataFrame, area_name: str) -> dict[str, dict]:
    """Median price + volume per property label within one planning area."""
    breakdown = {}
    area_df = df[df["planning_area"] == area_name]
    for prop, label in PROPERTY_TYPE_FILTERS.items():
        prop_area = area_df[area_df["property_label"] == label]
        if prop_area.empty:
            breakdown[prop] = {"median_price": None, "volume": 0}
        else:
            breakdown[prop] = {
                "median_price": int(prop_area["price"].median()),
                "volume": int(len(prop_area)),
            }
    return breakdown


def _time_period_breakdown(
    df: pd.DataFrame, area_name: str, today: date | None = None
) -> dict[str, dict]:
    """Median price + YoY growth per era within one planning area."""
    breakdown = {}
    area_df = df[df["planning_area"] == area_name]
    for era in ERA_FILTERS:
        period_df = era_subset(area_df, era)
        if period_df.empty:
            breakdown[era] = {"median_price": None, "yoy_growth": None}
            continue
        median_price = int(period_df["price"].median())
        # Pair completed years only; a partial current year would skew the
        # published growth (same rule as the monthly growth table).
        period_year = min(int(period_df["year"].max()), last_completed_year(today))
        price_curr = period_df[period_df["year"] == period_year]["price"].median()
        price_prev = period_df[period_df["year"] == period_year - 1]["price"].median()
        if pd.notna(price_curr) and pd.notna(price_prev) and price_prev > 0:
            yoy = round(((price_curr - price_prev) / price_prev) * 100, 2)
        else:
            yoy = None
        breakdown[era] = {"median_price": median_price, "yoy_growth": yoy}
    return breakdown


def generate_amenity_summary_data(df: pd.DataFrame) -> list[dict]:
    """Mean amenity distance per planning area (meters)."""
    available = {col: key for col, key in AMENITY_DISTANCE_COLUMNS.items() if col in df.columns}
    if not available:
        logger.warning("No amenity distance columns found in unified dataset")
        return []

    amenity_stats = (
        df.groupby("planning_area").agg({col: "mean" for col in available}).reset_index()
    )
    return [
        {
            "planning_area": row["planning_area"],
            **{key: safe_float(row[col]) for col, key in available.items()},
        }
        for _, row in amenity_stats.iterrows()
    ]


# ---------------------------------------------------------------------------
# Leaderboard metadata (region + centroid from planning-area GeoJSON)
# ---------------------------------------------------------------------------


def load_area_metadata() -> dict[str, dict]:
    """Lowercased-area -> {region, coordinates} from the planning-area GeoJSON."""
    geojson_path = None
    for candidate in GEOJSON_CANDIDATES:
        path = settings.data_dir / candidate
        if path.exists():
            geojson_path = path
            break
    if geojson_path is None:
        logger.warning("Planning area GeoJSON not found; leaderboard metadata will be sparse")
        return {}

    with open(geojson_path) as f:
        geojson = json.load(f)

    metadata = {}
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        area_name = props.get("PLN_AREA_N") or props.get("planning_area_n", "")
        region_name = props.get("REGION_N") or props.get("region_n", "Unknown")
        metadata[str(area_name).lower()] = {
            "region": region_name,
            "coordinates": _centroid_from_geometry(feature.get("geometry", {})),
        }
    logger.info("Loaded metadata for %d planning areas from %s", len(metadata), geojson_path.name)
    return metadata


def _centroid_from_geometry(geometry: dict) -> list[float] | None:
    """Average of the first coordinate ring, as [lon, lat] rounded to 6dp."""
    coordinates = geometry.get("coordinates", [])
    if not coordinates:
        return None
    if geometry.get("type") == "Polygon":
        all_coords = coordinates[0]
    elif geometry.get("type") == "MultiPolygon":
        all_coords = coordinates[0][0]
    else:
        all_coords = coordinates[0] if isinstance(coordinates[0], list) else coordinates
    if not all_coords:
        return None
    lons = [c[0] for c in all_coords]
    lats = [c[1] for c in all_coords]
    return [round(sum(lons) / len(lons), 6), round(sum(lats) / len(lats), 6)]


# ---------------------------------------------------------------------------
# Payload validation (record-level: never overwrite with a malformed payload)
# ---------------------------------------------------------------------------

# Full eight-key row contract consumed by app/src dashboard charts.
TREND_KEYS = {
    "date",
    "Overall Price",
    "HDB Price",
    "HDB Volume",
    "Condominium Price",
    "Condominium Volume",
    "EC Price",
    "EC Volume",
}
TREND_PRICE_KEYS = ("Overall Price", "HDB Price", "Condominium Price", "EC Price")
STAT_BLOCK_KEYS = ("count", "median_price", "median_psf", "volume")
SEGMENT_POINT_KEYS = ("name", "x", "y", "z", "category")
AMENITY_KEYS = set(AMENITY_DISTANCE_COLUMNS.values())
MIN_TREND_SPAN_MONTHS = 24
MIN_SEGMENT_POINTS = 50
# Area-level payload floors. Since NON_RESIDENTIAL_AREAS is excluded from the
# area surfaces, these are set below the observed post-exclusion counts
# (2026-10 run: 40 leaderboard entries, 40 hotspot areas, 41 amenity rows) so
# the guards still catch a collapsed payload without breaking when the
# exclusion list or geocoding coverage shifts the area count.
MIN_LEADERBOARD_ENTRIES = 35
MIN_HOTSPOT_AREAS = 35
MIN_AMENITY_ROWS = 35


def _is_number(value) -> bool:
    """True for finite JSON numbers (bool excluded; NaN/Inf are null)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return not (isinstance(value, float) and (math.isnan(value) or math.isinf(value)))


def _month_index(month: str) -> int:
    """YYYY-MM (pre-validated) -> absolute month count."""
    year, mon = month.split("-")
    return int(year) * 12 + int(mon)


def _validate_trends(rows, errors: list[str]) -> None:
    if not isinstance(rows, list) or not rows:
        errors.append("trends: empty payload")
        return
    month_re = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
    first_month = last_month = None
    for i, row in enumerate(rows):
        label = f"trends row {i}"
        if not isinstance(row, dict):
            errors.append(f"{label}: not an object")
            continue
        missing = TREND_KEYS - row.keys()
        if missing:
            errors.append(f"{label}: missing key(s) {', '.join(sorted(missing))}")
        date = row.get("date")
        if not isinstance(date, str) or not month_re.fullmatch(date):
            errors.append(f"{label}: date {date!r} is not parseable YYYY-MM")
        elif first_month is None:
            first_month = date
        last_month = date
        if not any(_is_number(row.get(k)) for k in TREND_PRICE_KEYS):
            errors.append(f"{label}: no non-null price value")
    if (
        first_month
        and last_month
        and _month_index(last_month) - _month_index(first_month) < MIN_TREND_SPAN_MONTHS
    ):
        errors.append(
            f"trends: span {first_month}..{last_month} shorter than {MIN_TREND_SPAN_MONTHS} months"
        )


def _validate_overview(payload, errors: list[str]) -> None:
    if not isinstance(payload, dict):
        errors.append("overview: payload is not an object")
        return
    stats = payload.get("stats")
    if not isinstance(stats, dict):
        errors.append("overview: missing stats object")
        stats = {}
    for era in ERA_FILTERS:
        for block in [era] + [f"{era}_{prop}" for prop in PROPERTY_TYPE_FILTERS]:
            entry = stats.get(block)
            if not isinstance(entry, dict):
                errors.append(f"overview: stats block '{block}' missing")
                continue
            for key in STAT_BLOCK_KEYS:
                if key not in entry:
                    errors.append(f"overview: stats '{block}' missing '{key}'")
    total_records = (payload.get("metadata") or {}).get("total_records")
    if not _is_number(total_records) or total_records <= 0:
        errors.append("overview: metadata.total_records must be > 0")
    if not (payload.get("distributions") or {}).get("property_type"):
        errors.append("overview: empty distributions.property_type")


def _validate_segments(payload, errors: list[str]) -> None:
    whole = payload.get("whole") if isinstance(payload, dict) else None
    if not isinstance(whole, list) or len(whole) < MIN_SEGMENT_POINTS:
        found = len(whole) if isinstance(whole, list) else 0
        errors.append(f"segments: 'whole' must hold >= {MIN_SEGMENT_POINTS} points (found {found})")
        return
    for i, point in enumerate(whole):
        if not isinstance(point, dict):
            errors.append(f"segments point {i}: not an object")
            continue
        missing = [key for key in SEGMENT_POINT_KEYS if key not in point]
        if missing:
            errors.append(f"segments point {i}: missing key(s) {', '.join(missing)}")


def _validate_leaderboard(entries, errors: list[str]) -> None:
    if not isinstance(entries, list) or len(entries) < MIN_LEADERBOARD_ENTRIES:
        errors.append(f"leaderboard: must hold >= {MIN_LEADERBOARD_ENTRIES} entries")
        return
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"leaderboard entry {i}: not an object")
            continue
        if not entry.get("planning_area"):
            errors.append(f"leaderboard entry {i}: missing planning_area")
        if not entry.get("region"):
            errors.append(f"leaderboard entry {i}: missing region")
        coords = entry.get("coordinates")
        if not (isinstance(coords, list) and len(coords) == 2 and all(map(_is_number, coords))):
            errors.append(f"leaderboard entry {i}: coordinates must be a non-null [lon, lat] pair")
        median_price = entry.get("median_price")
        if not _is_number(median_price) or median_price <= 0:
            errors.append(f"leaderboard entry {i}: median_price must be > 0")


def _validate_map_metrics(payload, errors: list[str]) -> None:
    for view in YIELD_SECTIONS:
        areas = payload.get(view) if isinstance(payload, dict) else None
        if not isinstance(areas, dict) or not areas:
            errors.append(f"map_metrics: view '{view}' missing or empty")


def _validate_hotspots(payload, errors: list[str]) -> None:
    if not isinstance(payload, dict) or len(payload) < MIN_HOTSPOT_AREAS:
        found = len(payload) if isinstance(payload, dict) else 0
        errors.append(f"hotspots: must cover >= {MIN_HOTSPOT_AREAS} areas (found {found})")
        return
    for area, entry in payload.items():
        if not isinstance(entry, dict):
            errors.append(f"hotspots '{area}': not an object")
            continue
        if "category" not in entry:
            errors.append(f"hotspots '{area}': missing 'category'")
        if "mean_yoy_growth" not in entry:
            errors.append(f"hotspots '{area}': missing 'mean_yoy_growth'")


def _validate_amenity_summary(rows, errors: list[str]) -> None:
    if not isinstance(rows, list) or len(rows) < MIN_AMENITY_ROWS:
        errors.append(f"amenity_summary: must hold >= {MIN_AMENITY_ROWS} rows")
        return
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"amenity_summary row {i}: not an object")
            continue
        if not row.get("planning_area"):
            errors.append(f"amenity_summary row {i}: missing planning_area")
        missing = AMENITY_KEYS - row.keys()
        if missing:
            errors.append(f"amenity_summary row {i}: missing key(s) {', '.join(sorted(missing))}")


def validate_payloads(payloads: dict[str, object]) -> None:
    """Record-level validation of every payload; raises before anything is written."""
    errors: list[str] = []
    _validate_overview(payloads["dashboard_overview.json.gz"], errors)
    _validate_trends(payloads["dashboard_trends.json.gz"], errors)
    _validate_segments(payloads["dashboard_segments.json.gz"], errors)
    _validate_leaderboard(payloads["dashboard_leaderboard.json.gz"], errors)
    _validate_map_metrics(payloads["map_metrics.json.gz"], errors)
    _validate_hotspots(payloads["hotspots.json.gz"], errors)
    _validate_amenity_summary(payloads["amenity_summary.json.gz"], errors)
    if errors:
        raise ValueError("; ".join(errors))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def export_app_data(output_dir: Path) -> None:
    """Generate, validate, then atomically write all seven dashboard files."""
    unified, pa_metrics = load_inputs()
    df = prepare_unified(unified)

    # Area-level surfaces exclude non-residential planning areas (nature
    # reserves / industrial land); global aggregates keep the full frame.
    area_df = drop_non_residential(df)

    # Shared derived tables.
    growth = build_growth_table(pa_metrics)
    latest_growth = latest_growth_by_area(growth)
    whole_yield = yield_lookup(df, ["mean", "median", "std"])
    recent_yield = yield_lookup(df[df["year"] >= 2022], ["mean", "median", "std"])
    affordability = affordability_lookup(df)
    hotspots = build_hotspots(growth)
    area_metadata = load_area_metadata()

    payloads: dict[str, object] = {
        "dashboard_overview.json.gz": generate_overview_data(df),
        "dashboard_trends.json.gz": generate_trends_data(df),
        "dashboard_segments.json.gz": generate_filtered_segments_data(area_df),
        "dashboard_leaderboard.json.gz": generate_leaderboard_data(
            area_df, latest_growth, recent_yield, affordability, hotspots, area_metadata
        ),
        "map_metrics.json.gz": generate_map_data(
            area_df, latest_growth, whole_yield, affordability
        ),
        "hotspots.json.gz": hotspots,
        "amenity_summary.json.gz": generate_amenity_summary_data(area_df),
    }

    try:
        validate_payloads(payloads)
    except ValueError as exc:
        logger.error("Payload validation failed (%s); no files written", exc)
        raise SystemExit(1) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path]] = []
    try:
        # Stage all seven payloads first so a serialization failure cannot leave
        # a mixed generation; only then swap the files in (per-file atomic).
        for filename, payload in payloads.items():
            final_path = output_dir / filename
            staged.append((stage_json_gzip(payload, final_path), final_path))
        empty = [str(tmp_path) for tmp_path, _ in staged if tmp_path.stat().st_size == 0]
        if empty:
            raise ValueError(f"staged payload(s) empty: {', '.join(empty)}")
        for tmp_path, final_path in staged:
            os.replace(tmp_path, final_path)
            logger.info("Saved: %s", final_path)
    finally:
        for tmp_path, _ in staged:
            tmp_path.unlink(missing_ok=True)
    logger.info("Export complete: %d files written to %s", len(payloads), output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Hamilton pipeline outputs to app/public/data dashboard JSON assets."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Target directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    setup_logging()
    export_app_data(args.output_dir)


if __name__ == "__main__":
    main()
