"""03_features: Gold layer feature engineering (Hamilton DAG node).

This module provides Hamilton-compatible functions for computing features
from silver data into the gold layer.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from egg_n_bacon_housing.schemas.feature_models import (
    BlockProfile,
    HFeatureTransaction,
    HRentalYieldRecord,
    LocationDimRecord,
    PlanningArea360,
    Town360,
)
from egg_n_bacon_housing.utils.contracts import require_columns
from egg_n_bacon_housing.utils.proximity import compute_proximity_features
from egg_n_bacon_housing.utils.regional_mapping import get_region_for_planning_area
from egg_n_bacon_housing.utils.school_features import _geocode_schools, calculate_school_features
from egg_n_bacon_housing.utils.time_index import ensure_month_column
from egg_n_bacon_housing.utils.validation_gateway import validate_and_quarantine

logger = logging.getLogger(__name__)


_FLAT_TYPE_NORMALIZE_MAP: dict[str, str] = {}


def _build_flat_type_map() -> dict[str, str]:
    canonical = [
        ("1-ROOM", "1-ROOM"),
        ("2-ROOM", "2-ROOM"),
        ("3-ROOM", "3-ROOM"),
        ("4-ROOM", "4-ROOM"),
        ("5-ROOM", "5-ROOM"),
        ("EXECUTIVE", "EXECUTIVE"),
        ("MULTI-GENERATION", "MULTI-GENERATION"),
    ]
    variants: dict[str, str] = {}
    for std, val in canonical:
        for form in [std, std.replace("-", " "), std.replace("-", "")]:
            variants[form] = val
    variants["EXEC"] = "EXECUTIVE"
    variants["EXEC."] = "EXECUTIVE"
    variants["MULTI-GEN"] = "MULTI-GENERATION"
    variants["MULTI GEN"] = "MULTI-GENERATION"
    variants["MG"] = "MULTI-GENERATION"
    variants["STUDIO"] = "2-ROOM"
    variants["STUDIO APARTMENT"] = "2-ROOM"
    m: dict[str, str] = {}
    for k, v in {**variants}.items():
        m[k] = v
        m[k.upper()] = v
        m[k.lower()] = v
    return m


_FLAT_TYPE_NORMALIZE_MAP = _build_flat_type_map()


def _normalize_hdb_flat_type(series: pd.Series) -> pd.Series:
    upper = series.astype(str).str.strip().str.upper()
    return upper.map(_FLAT_TYPE_NORMALIZE_MAP).fillna(upper)


def rental_yield(
    hdb_validated: pd.DataFrame,
    raw_hdb_rental: pd.DataFrame,
    raw_rental_index: pd.DataFrame,
    gold_dir: Path,
) -> pd.DataFrame:
    """Compute rental yield metrics.

    Args:
        hdb_validated: Validated HDB transactions.
        raw_hdb_rental: Raw HDB rental transactions.
        raw_rental_index: Raw rental index time series.

    Returns:
        DataFrame with rental yield by town/month.
    """
    required_sale_cols = {"town", "price", "flat_type", "transaction_date"}
    required_rent_cols = {"town", "flat_type", "monthly_rent", "rent_approval_date"}

    if (
        hdb_validated.empty
        or raw_hdb_rental.empty
        or not required_sale_cols.issubset(hdb_validated.columns)
        or not required_rent_cols.issubset(raw_hdb_rental.columns)
    ):
        return pd.DataFrame()

    sales = hdb_validated.copy()
    rents = raw_hdb_rental.copy()

    sales["price"] = pd.to_numeric(sales["price"], errors="coerce")
    sales["transaction_date"] = pd.to_datetime(sales["transaction_date"], errors="coerce")
    sales = ensure_month_column(sales)
    sales["town"] = sales["town"].astype(str).str.upper().str.strip()
    sales["flat_type"] = _normalize_hdb_flat_type(sales["flat_type"])
    sales = sales.dropna(subset=["price", "transaction_date", "town", "flat_type"])
    sales = sales[sales["price"] > 0]

    rents["monthly_rent"] = pd.to_numeric(rents["monthly_rent"], errors="coerce")
    rents["rent_approval_date"] = pd.to_datetime(
        rents["rent_approval_date"], format="%Y-%m", errors="coerce"
    )
    rents = ensure_month_column(rents, date_column="rent_approval_date")
    rents["town"] = rents["town"].astype(str).str.upper().str.strip()
    rents["flat_type"] = _normalize_hdb_flat_type(rents["flat_type"])
    rents = rents.dropna(subset=["monthly_rent", "rent_approval_date", "town", "flat_type"])
    rents = rents[rents["monthly_rent"] > 0]

    monthly_sales = sales.groupby(["town", "flat_type", "month"], as_index=False).agg(
        median_price=("price", "median"), sale_sample_size=("price", "size")
    )
    monthly_rents = rents.groupby(["town", "flat_type", "month"], as_index=False).agg(
        median_rent=("monthly_rent", "median"), rent_sample_size=("monthly_rent", "size")
    )

    sales_keys = set(
        zip(monthly_sales["town"], monthly_sales["flat_type"], monthly_sales["month"], strict=True)
    )
    rent_keys = set(
        zip(monthly_rents["town"], monthly_rents["flat_type"], monthly_rents["month"], strict=True)
    )
    sales_only_count = len(sales_keys - rent_keys)
    rent_only_count = len(rent_keys - sales_keys)
    if sales_only_count > 0 or rent_only_count > 0:
        logger.info(
            "Rental yield join: %s unmatched sales groups, "
            "%s unmatched rent groups (no match on town/flat_type/month)",
            sales_only_count,
            rent_only_count,
        )

    combo_yields = monthly_sales.merge(
        monthly_rents,
        on=["town", "flat_type", "month"],
        how="inner",
    )

    if combo_yields.empty:
        return pd.DataFrame()

    combo_yields["rental_yield_pct"] = (
        combo_yields["median_rent"] * 12 / combo_yields["median_price"] * 100
    )
    combo_yields = combo_yields[np.isfinite(combo_yields["rental_yield_pct"])]
    combo_yields["weighted_yield"] = (
        combo_yields["rental_yield_pct"] * combo_yields["sale_sample_size"]
    )

    df = combo_yields.groupby(["town", "month"], as_index=False).agg(
        median_price=("median_price", "median"),
        median_rent=("median_rent", "median"),
        rental_yield_pct=("weighted_yield", lambda x: x.sum()),
        sample_size=("sale_sample_size", "sum"),
        flat_type_count=("flat_type", "nunique"),
    )
    df["rental_yield_pct"] = df["rental_yield_pct"] / df["sample_size"]
    df["property_type"] = "HDB"

    if not raw_rental_index.empty and {"quarter", "locality", "index"}.issubset(
        raw_rental_index.columns
    ):
        rental_index = raw_rental_index.copy()
        rental_index = rental_index[
            rental_index["locality"].astype(str).str.upper() == "WHOLE ISLAND"
        ]
        rental_index["quarter"] = pd.PeriodIndex(rental_index["quarter"], freq="Q")
        rental_index["rental_index"] = pd.to_numeric(rental_index["index"], errors="coerce")
        rental_index = rental_index.dropna(subset=["rental_index"])
        expanded_index = []
        for row in (
            rental_index[["quarter", "rental_index"]].drop_duplicates().itertuples(index=False)
        ):
            start_month = row.quarter.asfreq("M", how="start")
            for month in pd.period_range(start=start_month, periods=3, freq="M"):
                expanded_index.append({"month": str(month), "rental_index": row.rental_index})
        rental_index = pd.DataFrame(expanded_index)
        df = df.merge(
            rental_index.drop_duplicates(),
            on="month",
            how="left",
        )

    df = validate_and_quarantine(
        df,
        HRentalYieldRecord,
        "rental_yield",
        layer_dir=gold_dir,
        filename="rental_yield.parquet",
    )

    return df


def _add_planning_area(df: pd.DataFrame) -> pd.DataFrame:
    """Derive planning_area from lat/lon via point-in-polygon on unique coords."""
    if "lat" not in df.columns or "lon" not in df.columns:
        return df
    if "planning_area" in df.columns and df["planning_area"].notna().any():
        return df

    try:
        from egg_n_bacon_housing.utils.data_loader import get_planning_area_for_point
    except ImportError:
        logger.warning("data_loader not available — skipping planning_area derivation")
        return df

    unique_coords = df.drop_duplicates(subset=["lat", "lon"])[["lat", "lon"]]
    if unique_coords.empty:
        return df

    logger.info("Deriving planning_area for %s unique coordinates", len(unique_coords))
    pa_map: dict[tuple[float, float], str | None] = {}
    for _, row in unique_coords.iterrows():
        pa = get_planning_area_for_point(row["lat"], row["lon"])
        pa_map[(row["lat"], row["lon"])] = pa

    df["planning_area"] = df.apply(lambda r: pa_map.get((r["lat"], r["lon"])), axis=1)
    matched = df["planning_area"].notna().sum()
    logger.info(
        "planning_area derived: %s/%s (%.1f%%)",
        matched,
        len(df),
        matched / len(df) * 100 if len(df) else 0,
    )
    return df


def location_dim(
    geocoded_validated: pd.DataFrame,
    raw_mrt_stations: pd.DataFrame,
    raw_school_directory: pd.DataFrame,
    raw_shopping_malls: pd.DataFrame,
    raw_hawker_centres: pd.DataFrame,
    raw_supermarkets: pd.DataFrame,
    raw_parks: pd.DataFrame,
    raw_childcare: pd.DataFrame,
    raw_kindergartens: pd.DataFrame,
    raw_bus_stops: pd.DataFrame,
    raw_chas_clinics: pd.DataFrame,
    raw_sports_facilities: pd.DataFrame,
    raw_community_clubs: pd.DataFrame,
    geocoded_green_mark_buildings: pd.DataFrame,
    raw_hdb_property_info: pd.DataFrame,
    gold_dir: Path,
) -> pd.DataFrame:
    """Build the location dimension table — one row per unique (lat, lon).

    Computes ALL proximity features, school scores, block metadata, and
    planning_area on ~10K unique locations instead of 1M transactions.
    """
    if geocoded_validated.empty:
        return pd.DataFrame()

    df = geocoded_validated.copy()
    require_columns(df, {"lat", "lon"}, "geocoded_validated")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])

    if df.empty:
        return pd.DataFrame()

    carry_cols = [c for c in ("block", "street_name", "town") if c in df.columns]
    loc = (
        df.drop_duplicates(subset=["lat", "lon"], keep="first")[["lat", "lon", *carry_cols]]
        .reset_index(drop=True)
        .copy()
    )
    logger.info("location_dim: %s unique (lat, lon) pairs", len(loc))

    # --- School features ---
    if not raw_school_directory.empty:
        schools = raw_school_directory
        if "latitude" not in schools.columns or schools["latitude"].isna().all():
            logger.info("School directory lacks lat/lon — geocoding via OneMap...")
            schools = _geocode_schools(schools)
        loc = calculate_school_features(loc, schools)
        school_distance_cols = [
            col
            for col in [
                "nearest_schoolPRIMARY_dist",
                "nearest_schoolSECONDARY_dist",
                "nearest_schoolJUNIOR_dist",
            ]
            if col in loc.columns
        ]
        if school_distance_cols:
            loc["dist_to_nearest_school"] = loc[school_distance_cols].min(axis=1, skipna=True)

    # --- Proximity features (all 14 POI types) ---
    try:
        loc = compute_proximity_features(
            loc,
            mrt_stations=raw_mrt_stations if not raw_mrt_stations.empty else None,
            malls=raw_shopping_malls if not raw_shopping_malls.empty else None,
            hawkers=raw_hawker_centres if not raw_hawker_centres.empty else None,
            supermarkets=raw_supermarkets if not raw_supermarkets.empty else None,
            parks=raw_parks if not raw_parks.empty else None,
            childcare=raw_childcare if not raw_childcare.empty else None,
            kindergartens=raw_kindergartens if not raw_kindergartens.empty else None,
            bus_stops=raw_bus_stops if not raw_bus_stops.empty else None,
            chas_clinics=raw_chas_clinics if not raw_chas_clinics.empty else None,
            sports_facilities=raw_sports_facilities if not raw_sports_facilities.empty else None,
            community_clubs=raw_community_clubs if not raw_community_clubs.empty else None,
            green_mark_buildings=(
                geocoded_green_mark_buildings if not geocoded_green_mark_buildings.empty else None
            ),
        )
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        logger.warning("Skipping proximity features: %s", exc)
        loc["dist_to_nearest_mrt"] = pd.NA
        loc["nearest_mrt_station"] = pd.NA
        for label in (
            "mall",
            "hawker",
            "supermarket",
            "park",
            "childcare",
            "kindergarten",
            "bus_stop",
            "chas_clinic",
            "sports_facility",
            "community_club",
            "green_mark_building",
        ):
            loc[f"dist_to_nearest_{label}"] = pd.NA
            loc[f"nearest_{label}"] = pd.NA

    # --- Block metadata from HDB Property Info ---
    if not raw_hdb_property_info.empty and "block" in loc.columns and "street_name" in loc.columns:
        prop = raw_hdb_property_info.copy()
        prop["blk_no"] = prop["blk_no"].astype(str).str.strip().str.upper()
        prop["street"] = prop["street"].astype(str).str.strip().str.upper()

        loc["_join_block"] = loc["block"].astype(str).str.strip().str.upper()
        loc["_join_street"] = loc["street_name"].astype(str).str.strip().str.upper()

        prop_lookup = prop[
            [
                "blk_no",
                "street",
                "max_floor_lvl",
                "year_completed",
                "total_dwelling_units",
                "residential",
                "commercial",
                "market_hawker",
                "multistorey_carpark",
            ]
        ].copy()
        prop_lookup = prop_lookup.rename(
            columns={"blk_no": "_join_block", "street": "_join_street"}
        )
        for col in ("max_floor_lvl", "year_completed", "total_dwelling_units"):
            if col in prop_lookup.columns:
                prop_lookup[col] = pd.to_numeric(prop_lookup[col], errors="coerce")
        prop_lookup = prop_lookup.drop_duplicates(
            subset=["_join_block", "_join_street"], keep="first"
        )

        loc = loc.merge(prop_lookup, on=["_join_block", "_join_street"], how="left")
        loc = loc.drop(columns=["_join_block", "_join_street"], errors="ignore")

        matched = loc["year_completed"].notna().sum() if "year_completed" in loc.columns else 0
        logger.info(
            "location_dim block metadata: %s/%s (%.1f%%) matched",
            matched,
            len(loc),
            matched / len(loc) * 100 if len(loc) else 0,
        )

    for col in (
        "max_floor_lvl",
        "year_completed",
        "total_dwelling_units",
        "residential",
        "commercial",
        "market_hawker",
        "multistorey_carpark",
    ):
        if col not in loc.columns:
            loc[col] = pd.NA

    # --- Planning area + region ---
    loc = _add_planning_area(loc)
    if "planning_area" in loc.columns:
        loc["region"] = loc["planning_area"].apply(
            lambda pa: get_region_for_planning_area(str(pa)) if pd.notna(pa) else None
        )

    loc = validate_and_quarantine(
        loc,
        LocationDimRecord,
        "location_dim",
        layer_dir=gold_dir,
        filename="location_dim.parquet",
    )

    return loc


def transactions_enriched(
    geocoded_validated: pd.DataFrame,
    location_dim: pd.DataFrame,
    rental_yield: pd.DataFrame,
    raw_macro_data: dict[str, pd.DataFrame],
    raw_dwelling_units_by_town: pd.DataFrame,
    raw_hdb_resident_population: pd.DataFrame,
    raw_median_annual_value: pd.DataFrame,
    raw_income_by_planning_area: pd.DataFrame,
    gold_dir: Path,
) -> pd.DataFrame:
    """Join location_dim onto transactions + merge macro + yield + supply.

    Fast merge: location_dim (10K) → transactions (1M) by (lat, lon),
    then macro indicators, rental yield, town supply, income, and annual value.
    """
    if geocoded_validated.empty:
        return pd.DataFrame()

    df = geocoded_validated.copy()
    require_columns(df, {"lat", "lon", "price"}, "geocoded_validated")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    # --- Derived columns ---
    if "price" in df.columns and "floor_area_sqft" in df.columns:
        price = pd.to_numeric(df["price"], errors="coerce")
        floor_area_sqft = pd.to_numeric(df["floor_area_sqft"], errors="coerce")
        df["psf"] = np.where(floor_area_sqft > 0, price / floor_area_sqft, np.nan)
    else:
        df["psf"] = np.nan

    if "remaining_lease_months" in df.columns:
        df["remaining_lease_years"] = df["remaining_lease_months"] / 12

    # --- LEFT JOIN location_dim by (lat, lon) ---
    if not location_dim.empty:
        loc_join = location_dim.copy()
        overlap = set(df.columns) & set(loc_join.columns) - {"lat", "lon"}
        loc_join = loc_join.drop(columns=list(overlap))
        df = df.merge(loc_join, on=["lat", "lon"], how="left")
        logger.info("transactions_enriched: joined location_dim (%s cols)", len(loc_join.columns))

    # --- Rental yield ---
    if not rental_yield.empty and "rental_yield_pct" in rental_yield.columns:
        df = ensure_month_column(df)
        if "flat_type" in df.columns:
            df["flat_type"] = _normalize_hdb_flat_type(df["flat_type"])

        rental_df = rental_yield.copy()
        if "flat_type" in rental_df.columns:
            rental_df["flat_type"] = _normalize_hdb_flat_type(rental_df["flat_type"])

        merge_priority = [["town", "month", "flat_type"], ["town", "month"]]
        merge_keys: list[str] = []
        for keys in merge_priority:
            if all(k in df.columns for k in keys) and all(k in rental_df.columns for k in keys):
                merge_keys = keys
                break

        if merge_keys:
            rental_cols = [*merge_keys, "rental_yield_pct"]
            rental_lookup = rental_df[rental_cols].dropna(subset=["rental_yield_pct"])
            sort_col = next((c for c in merge_keys if "month" in c or "date" in c), merge_keys[0])
            rental_lookup = rental_lookup.sort_values(sort_col).drop_duplicates(
                subset=merge_keys, keep="last"
            )
            df = df.merge(rental_lookup, on=merge_keys, how="left")

    # --- Macro indicators ---
    df = ensure_month_column(df)
    df["_month_ts"] = pd.to_datetime(df["month"], errors="coerce")
    df["_month"] = df["_month_ts"].dt.to_period("M").astype(str)

    monthly_indicators = {
        "cpi": ("date", "cpi"),
        "sora": ("date", "sora_rate"),
        "bank_rates": ("date", "sora_3m"),
    }
    for key, (date_col, value_col) in monthly_indicators.items():
        macro_df = raw_macro_data.get(key, pd.DataFrame())
        if macro_df.empty or date_col not in macro_df.columns:
            df[value_col] = pd.NA
            continue
        lookup = macro_df[[date_col, value_col]].copy()
        lookup[date_col] = pd.to_datetime(lookup[date_col], errors="coerce")
        lookup["_month"] = lookup[date_col].dt.to_period("M").astype(str)
        lookup = lookup.dropna(subset=["_month", value_col])
        lookup = lookup.sort_values("_month").drop_duplicates(subset="_month", keep="last")
        df = df.merge(
            lookup[["_month", value_col]], on="_month", how="left", suffixes=("", f"_{key}")
        )
        if f"{value_col}_{key}" in df.columns:
            df[value_col] = df[value_col].fillna(df.pop(f"{value_col}_{key}"))

    quarterly_indicators = {
        "unemployment": ("quarter", "unemployment_rate"),
        "gdp": ("quarter", "gdp"),
        "hdb_rpi": ("quarter", "hdb_rpi"),
        "ura_ppi": ("quarter", "ura_ppi"),
        "wage_growth": ("quarter", "wage_growth"),
    }
    for key, (qtr_col, value_col) in quarterly_indicators.items():
        macro_df = raw_macro_data.get(key, pd.DataFrame())
        if macro_df.empty or qtr_col not in macro_df.columns:
            df[value_col] = pd.NA
            continue
        lookup = macro_df[[qtr_col, value_col]].copy()
        lookup[qtr_col] = pd.to_datetime(lookup[qtr_col], errors="coerce")
        lookup["_quarter"] = lookup[qtr_col].dt.to_period("Q")
        lookup = lookup.dropna(subset=["_quarter", value_col])
        lookup = lookup.sort_values("_quarter").drop_duplicates(subset="_quarter", keep="last")
        df["_quarter"] = df["_month_ts"].dt.to_period("Q")
        df = df.merge(
            lookup[["_quarter", value_col]], on="_quarter", how="left", suffixes=("", f"_{key}")
        )
        if f"{value_col}_{key}" in df.columns:
            df[value_col] = df[value_col].fillna(df.pop(f"{value_col}_{key}"))
        df = df.drop(columns=["_quarter"])

    df = df.drop(columns=["_month", "_month_ts"], errors="ignore")

    # --- Town supply, population, annual value ---
    town_col = "town" if "town" in df.columns else None
    if town_col:
        df["_town_upper"] = df[town_col].astype(str).str.strip().str.upper()

        if not raw_dwelling_units_by_town.empty:
            dwell = raw_dwelling_units_by_town.copy()
            if {
                "town_or_estate",
                "no_of_dwelling_units",
                "financial_year",
                "sold_or_rental",
            }.issubset(dwell.columns):
                dwell["financial_year"] = pd.to_numeric(dwell["financial_year"], errors="coerce")
                latest_year = dwell["financial_year"].max()
                dwell = dwell[dwell["financial_year"] == latest_year]
                dwell = dwell[dwell["sold_or_rental"].astype(str).str.strip() == "Sold Units"]
                dwell["no_of_dwelling_units"] = pd.to_numeric(
                    dwell["no_of_dwelling_units"], errors="coerce"
                )
                dwell["_town_upper"] = dwell["town_or_estate"].astype(str).str.strip().str.upper()
                dwell_lookup = (
                    dwell.groupby("_town_upper")["no_of_dwelling_units"]
                    .sum()
                    .reset_index()
                    .rename(columns={"no_of_dwelling_units": "dwelling_units_in_town"})
                )
                df = df.merge(dwell_lookup, on="_town_upper", how="left")

        if "dwelling_units_in_town" not in df.columns:
            df["dwelling_units_in_town"] = pd.NA

        if not raw_hdb_resident_population.empty:
            pop = raw_hdb_resident_population.copy()
            if {"town_estate", "number", "shs_year"}.issubset(pop.columns):
                pop["shs_year"] = pd.to_numeric(pop["shs_year"], errors="coerce")
                latest_pop_year = pop["shs_year"].max()
                pop = pop[pop["shs_year"] == latest_pop_year]
                pop["number"] = pd.to_numeric(pop["number"], errors="coerce")
                pop["_town_upper"] = pop["town_estate"].astype(str).str.strip().str.upper()
                pop_lookup = pop[["_town_upper", "number"]].rename(
                    columns={"number": "population_in_town"}
                )
                pop_lookup = pop_lookup.drop_duplicates(subset="_town_upper", keep="first")
                df = df.merge(pop_lookup, on="_town_upper", how="left")

        if "population_in_town" not in df.columns:
            df["population_in_town"] = pd.NA

        units = pd.to_numeric(df["dwelling_units_in_town"], errors="coerce")
        pop_vals = pd.to_numeric(df["population_in_town"], errors="coerce")
        df["population_per_dwelling"] = np.where(units > 0, pop_vals / units, pd.NA)

        if not raw_median_annual_value.empty and "flat_type" in df.columns:
            mav = raw_median_annual_value.copy()
            if {
                "type_of_hdb",
                "median_annual_value",
                "property_tax_collection",
                "financial_year",
            }.issubset(mav.columns):
                mav["financial_year"] = pd.to_numeric(mav["financial_year"], errors="coerce")
                latest_mav_year = mav["financial_year"].max()
                mav = mav[mav["financial_year"] == latest_mav_year]
                mav["median_annual_value"] = pd.to_numeric(
                    mav["median_annual_value"], errors="coerce"
                )
                mav["property_tax_collection"] = pd.to_numeric(
                    mav["property_tax_collection"], errors="coerce"
                )
                mav_lookup = mav[
                    ["type_of_hdb", "median_annual_value", "property_tax_collection"]
                ].rename(
                    columns={
                        "median_annual_value": "annual_value",
                        "property_tax_collection": "property_tax",
                    }
                )
                mav_lookup = mav_lookup.drop_duplicates(subset="type_of_hdb", keep="first")

                df["_av_type"] = df["flat_type"].apply(_map_flat_type_for_annual_value)
                df = df.merge(mav_lookup, left_on="_av_type", right_on="type_of_hdb", how="left")
                df = df.drop(columns=["_av_type", "type_of_hdb"], errors="ignore")

        df = df.drop(columns=["_town_upper"], errors="ignore")

    # --- Income by planning area ---
    if not raw_income_by_planning_area.empty and "planning_area" in df.columns:
        income_lookup = raw_income_by_planning_area[
            ["planning_area", "median_monthly_income"]
        ].copy()
        income_lookup["planning_area"] = income_lookup["planning_area"].astype(str).str.strip()
        income_lookup = income_lookup.dropna(subset=["median_monthly_income"])
        income_lookup = income_lookup.drop_duplicates(subset="planning_area", keep="first")

        df["planning_area"] = df["planning_area"].astype(str).str.strip()
        df = df.merge(income_lookup, on="planning_area", how="left")

    for col in (
        "dwelling_units_in_town",
        "population_in_town",
        "population_per_dwelling",
        "annual_value",
        "property_tax",
        "wage_growth",
        "median_monthly_income",
    ):
        if col not in df.columns:
            df[col] = pd.NA

    df = validate_and_quarantine(
        df,
        HFeatureTransaction,
        "transactions_enriched",
        layer_dir=gold_dir,
        filename="transactions_enriched.parquet",
        sample_validation_size=10_000,
    )

    return df


def _map_flat_type_for_annual_value(flat_type: str) -> str:
    """Map HDB flat_type to IRAS type_of_hdb category."""
    ft = str(flat_type).strip().upper()
    if ft in ("1-ROOM", "2-ROOM"):
        return "1 or 2 Room"
    if ft == "3-ROOM":
        return "3 Room"
    if ft == "4-ROOM":
        return "4 Room"
    if ft == "5-ROOM":
        return "5 Room"
    if ft in ("EXECUTIVE", "MULTI-GENERATION"):
        return "Executive & Others"
    return ft


def planning_area_360(
    location_dim: pd.DataFrame,
    transactions_enriched: pd.DataFrame,
    raw_income_by_planning_area: pd.DataFrame,
    raw_macro_data: dict[str, pd.DataFrame],
    gold_dir: Path,
) -> pd.DataFrame:
    """Build the planning-area 360-degree profile table (~43 rows).

    Aggregates spatial medians from location_dim, market stats from
    transactions_enriched, and merges income + latest macro indicators.
    """
    if location_dim.empty or "planning_area" not in location_dim.columns:
        return pd.DataFrame()

    loc = location_dim[location_dim["planning_area"].notna()].copy()

    dist_cols = [c for c in loc.columns if c.startswith("dist_to_nearest_")]
    loc_spatial = loc.groupby("planning_area")[dist_cols].median().reset_index()
    rename_map = {c: c.replace("dist_to_nearest_", "median_dist_to_") for c in dist_cols}
    loc_spatial = loc_spatial.rename(columns=rename_map)

    agg_map: dict[str, str] = {}
    if "year_completed" in loc.columns:
        agg_map["year_completed"] = "mean"
    if "max_floor_lvl" in loc.columns:
        agg_map["max_floor_lvl"] = "mean"
    if "total_dwelling_units" in loc.columns:
        agg_map["total_dwelling_units"] = "sum"
    if agg_map:
        block_profile = loc.groupby("planning_area").agg(agg_map).reset_index()
        block_profile = block_profile.rename(
            columns={
                "year_completed": "avg_year_completed",
                "max_floor_lvl": "avg_max_floor",
            }
        )
        loc_spatial = loc_spatial.merge(block_profile, on="planning_area", how="left")

    if "region" in loc.columns:
        pa_region = loc.groupby("planning_area")["region"].first().reset_index()
        loc_spatial = loc_spatial.merge(pa_region, on="planning_area", how="left")

    result = loc_spatial

    if not transactions_enriched.empty and "planning_area" in transactions_enriched.columns:
        tx = transactions_enriched[transactions_enriched["planning_area"].notna()].copy()
        agg_dict: dict[str, tuple] = {
            "median_price": ("price", "median"),
            "transaction_volume": ("price", "count"),
        }
        if "psf" in tx.columns:
            agg_dict["median_psf"] = ("psf", "median")
        if "rental_yield_pct" in tx.columns:
            agg_dict["median_rental_yield_pct"] = ("rental_yield_pct", "median")

        market = tx.groupby("planning_area").agg(**agg_dict).reset_index()
        result = result.merge(market, on="planning_area", how="left")

    if not raw_income_by_planning_area.empty:
        income = raw_income_by_planning_area[["planning_area", "median_monthly_income"]].copy()
        income["planning_area"] = income["planning_area"].astype(str).str.strip()
        income = income.dropna(subset=["median_monthly_income"])
        income = income.drop_duplicates(subset="planning_area", keep="first")
        result = result.merge(income, on="planning_area", how="left")

    for key in ("cpi", "bank_rates", "unemployment", "gdp"):
        macro_df = raw_macro_data.get(key, pd.DataFrame())
        if macro_df.empty:
            continue
        value_col = {
            "cpi": "cpi",
            "bank_rates": "sora_3m",
            "unemployment": "unemployment_rate",
            "gdp": "gdp",
        }.get(key)
        date_col = "date" if "date" in macro_df.columns else "quarter"
        if value_col not in macro_df.columns or date_col not in macro_df.columns:
            continue
        latest_value = macro_df.sort_values(date_col)[value_col].iloc[-1]
        result[value_col] = latest_value

    result = validate_and_quarantine(
        result,
        PlanningArea360,
        "planning_area_360",
        layer_dir=gold_dir,
        filename="planning_area_360.parquet",
    )

    logger.info("planning_area_360: %s planning areas", len(result))
    return result


def town_360(
    transactions_enriched: pd.DataFrame,
    raw_dwelling_units_by_town: pd.DataFrame,
    raw_hdb_resident_population: pd.DataFrame,
    raw_median_annual_value: pd.DataFrame,
    gold_dir: Path,
) -> pd.DataFrame:
    """Build the town 360-degree profile table (~27 rows).

    Aggregates market stats from transactions_enriched, merges supply,
    population, and tax from external sources.
    """
    if transactions_enriched.empty or "town" not in transactions_enriched.columns:
        return pd.DataFrame()

    tx = transactions_enriched.copy()
    tx["_town_upper"] = tx["town"].astype(str).str.strip().str.upper()

    agg_dict: dict[str, tuple] = {
        "median_price": ("price", "median"),
        "transaction_volume": ("price", "count"),
    }
    if "psf" in tx.columns:
        agg_dict["median_psf"] = ("psf", "median")

    result = (
        tx.groupby("_town_upper")
        .agg(**agg_dict)
        .reset_index()
        .rename(columns={"_town_upper": "town"})
    )

    if not raw_dwelling_units_by_town.empty:
        dwell = raw_dwelling_units_by_town.copy()
        if {
            "town_or_estate",
            "no_of_dwelling_units",
            "financial_year",
            "sold_or_rental",
        }.issubset(dwell.columns):
            dwell["financial_year"] = pd.to_numeric(dwell["financial_year"], errors="coerce")
            latest_year = dwell["financial_year"].max()
            dwell = dwell[dwell["financial_year"] == latest_year]
            dwell = dwell[dwell["sold_or_rental"].astype(str).str.strip() == "Sold Units"]
            dwell["no_of_dwelling_units"] = pd.to_numeric(
                dwell["no_of_dwelling_units"], errors="coerce"
            )
            dwell["_town_upper"] = dwell["town_or_estate"].astype(str).str.strip().str.upper()
            dwell_lookup = (
                dwell.groupby("_town_upper")["no_of_dwelling_units"]
                .sum()
                .reset_index()
                .rename(
                    columns={
                        "no_of_dwelling_units": "dwelling_units_in_town",
                        "_town_upper": "town",
                    }
                )
            )
            result = result.merge(dwell_lookup, on="town", how="left")

    if not raw_hdb_resident_population.empty:
        pop = raw_hdb_resident_population.copy()
        if {"town_estate", "number", "shs_year"}.issubset(pop.columns):
            pop["shs_year"] = pd.to_numeric(pop["shs_year"], errors="coerce")
            latest_pop_year = pop["shs_year"].max()
            pop = pop[pop["shs_year"] == latest_pop_year]
            pop["number"] = pd.to_numeric(pop["number"], errors="coerce")
            pop["_town_upper"] = pop["town_estate"].astype(str).str.strip().str.upper()
            pop_lookup = pop[["_town_upper", "number"]].rename(
                columns={"number": "population_in_town", "_town_upper": "town"}
            )
            pop_lookup = pop_lookup.drop_duplicates(subset="town", keep="first")
            result = result.merge(pop_lookup, on="town", how="left")

    if "dwelling_units_in_town" in result.columns and "population_in_town" in result.columns:
        units = pd.to_numeric(result["dwelling_units_in_town"], errors="coerce")
        pop_vals = pd.to_numeric(result["population_in_town"], errors="coerce")
        result["population_per_dwelling"] = np.where(units > 0, pop_vals / units, pd.NA)

    if not raw_median_annual_value.empty:
        mav = raw_median_annual_value.copy()
        if {
            "type_of_hdb",
            "median_annual_value",
            "property_tax_collection",
            "financial_year",
        }.issubset(mav.columns):
            mav["financial_year"] = pd.to_numeric(mav["financial_year"], errors="coerce")
            latest_mav_year = mav["financial_year"].max()
            mav = mav[mav["financial_year"] == latest_mav_year]
            mav["median_annual_value"] = pd.to_numeric(mav["median_annual_value"], errors="coerce")
            mav["property_tax_collection"] = pd.to_numeric(
                mav["property_tax_collection"], errors="coerce"
            )
            for ft in ("3 Room", "4 Room", "5 Room"):
                row = mav[mav["type_of_hdb"] == ft]
                if not row.empty:
                    suffix = ft.lower().replace(" ", "_")
                    result[f"annual_value_{suffix}"] = row.iloc[0]["median_annual_value"]
                    result[f"property_tax_{suffix}"] = row.iloc[0]["property_tax_collection"]

    for col in (
        "dwelling_units_in_town",
        "population_in_town",
        "population_per_dwelling",
        "annual_value_3_room",
        "annual_value_4_room",
        "annual_value_5_room",
        "property_tax_3_room",
        "property_tax_4_room",
        "property_tax_5_room",
    ):
        if col not in result.columns:
            result[col] = pd.NA

    result["town"] = result["town"].str.title()

    result = validate_and_quarantine(
        result,
        Town360,
        "town_360",
        layer_dir=gold_dir,
        filename="town_360.parquet",
    )

    logger.info("town_360: %s towns", len(result))
    return result


def block_profile(
    transactions_enriched: pd.DataFrame,
    gold_dir: Path,
) -> pd.DataFrame:
    """Build per-block transaction profile table (~10K rows).

    Aggregates median price/PSF, transaction count, and average remaining
    lease years by (block, street_name).
    """
    if transactions_enriched.empty:
        return pd.DataFrame()

    df = transactions_enriched.copy()

    if "block" not in df.columns or "street_name" not in df.columns:
        logger.warning("block_profile: missing block/street_name columns")
        return pd.DataFrame()

    agg_dict: dict[str, tuple] = {
        "median_price": ("price", "median"),
        "transaction_count": ("price", "count"),
    }
    if "psf" in df.columns:
        agg_dict["median_psf"] = ("psf", "median")
    if "remaining_lease_years" in df.columns:
        agg_dict["avg_remaining_lease_years"] = ("remaining_lease_years", "mean")
    if "town" in df.columns:
        agg_dict["town"] = ("town", "first")

    profile = df.groupby(["block", "street_name"]).agg(**agg_dict).reset_index()

    result = validate_and_quarantine(
        profile,
        BlockProfile,
        "block_profile",
        layer_dir=gold_dir,
        filename="block_profile.parquet",
    )

    logger.info("block_profile: %s blocks", len(result))
    return result
