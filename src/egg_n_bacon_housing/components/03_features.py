"""03_features: Gold layer feature engineering (Hamilton DAG node).

This module provides Hamilton-compatible functions for computing features
from silver data into the gold layer.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from egg_n_bacon_housing.schemas.feature_models import HFeatureTransaction, HRentalYieldRecord
from egg_n_bacon_housing.utils.contracts import require_columns
from egg_n_bacon_housing.utils.proximity import compute_proximity_features
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


def features_with_amenities(
    geocoded_validated: pd.DataFrame,
    raw_school_directory: pd.DataFrame,
    raw_shopping_malls: pd.DataFrame,
    raw_mrt_stations: pd.DataFrame,
    raw_hawker_centres: pd.DataFrame,
    raw_supermarkets: pd.DataFrame,
    raw_parks: pd.DataFrame,
    raw_childcare: pd.DataFrame,
    raw_kindergartens: pd.DataFrame,
    raw_bus_stops: pd.DataFrame,
    raw_chas_clinics: pd.DataFrame,
    raw_sports_facilities: pd.DataFrame,
    raw_community_clubs: pd.DataFrame,
    raw_green_mark_buildings: pd.DataFrame,
    gold_dir: Path,
) -> pd.DataFrame:
    """Compute amenity distance features.

    Args:
        geocoded_validated: Geocoded transaction data.
        raw_school_directory: School locations.
        raw_mrt_stations: MRT station data (from 01_ingestion).
        raw_hawker_centres: Hawker centre locations.
        raw_supermarkets: Supermarket locations.
        raw_parks: Park and nature reserve locations.
        raw_childcare: Childcare centre locations.
        raw_kindergartens: Kindergarten locations.
        raw_bus_stops: Bus stop locations.
        raw_chas_clinics: CHAS subsidised clinic locations.
        raw_sports_facilities: SportSG facility locations.
        raw_community_clubs: Community club locations.
        raw_green_mark_buildings: BCA Green Mark certified buildings.

    Returns:
        DataFrame with computed features.
    """
    if geocoded_validated.empty:
        return pd.DataFrame()

    df = geocoded_validated.copy()
    require_columns(df, {"lat", "lon", "price"}, "geocoded_validated")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])

    if df.empty:
        return pd.DataFrame()

    if "price" in df.columns and "floor_area_sqft" in df.columns:
        price = pd.to_numeric(df["price"], errors="coerce")
        floor_area_sqft = pd.to_numeric(df["floor_area_sqft"], errors="coerce")
        df["psf"] = np.where(floor_area_sqft > 0, price / floor_area_sqft, np.nan)
    else:
        df["psf"] = np.nan

    if "remaining_lease_months" in df.columns:
        df["remaining_lease_years"] = df["remaining_lease_months"] / 12

    if not raw_school_directory.empty:
        if (
            "latitude" not in raw_school_directory.columns
            or raw_school_directory["latitude"].isna().all()
        ):
            logger.info("School directory lacks lat/lon — geocoding via OneMap...")
            raw_school_directory = _geocode_schools(raw_school_directory)
        df = calculate_school_features(df, raw_school_directory)
        school_distance_cols = [
            col
            for col in [
                "nearest_schoolPRIMARY_dist",
                "nearest_schoolSECONDARY_dist",
                "nearest_schoolJUNIOR_dist",
            ]
            if col in df.columns
        ]
        if school_distance_cols:
            df["dist_to_nearest_school"] = df[school_distance_cols].min(axis=1, skipna=True)

    green_mark_poi = raw_green_mark_buildings
    if not green_mark_poi.empty and "postal_code" in green_mark_poi.columns:
        unique_postals = green_mark_poi["postal_code"].drop_duplicates()
        geocoded_map: dict[str, tuple[float | None, float | None]] = {}
        if "lat" not in green_mark_poi.columns or green_mark_poi["lat"].isna().all():
            logger.info("Geocoding %s unique Green Mark postal codes...", len(unique_postals))
            import time

            from egg_n_bacon_housing.adapters import onemap

            headers = onemap.setup_onemap_headers()
            for pc in unique_postals:
                try:
                    results = onemap.fetch_data(f"Singapore {pc}", headers, timeout=15)
                    if results is not None and not results.empty:
                        row = results.iloc[0]
                        lat = pd.to_numeric(row.get("LATITUDE") or row.get("Y"), errors="coerce")
                        lon = pd.to_numeric(row.get("LONGITUDE") or row.get("X"), errors="coerce")
                        geocoded_map[str(pc)] = (lat, lon)
                    else:
                        geocoded_map[str(pc)] = (None, None)
                except Exception:
                    geocoded_map[str(pc)] = (None, None)
                time.sleep(0.3)
            green_mark_poi = green_mark_poi.copy()
            green_mark_poi["lat"] = green_mark_poi["postal_code"].map(
                lambda pc: geocoded_map.get(str(pc), (None, None))[0]
            )
            green_mark_poi["lon"] = green_mark_poi["postal_code"].map(
                lambda pc: geocoded_map.get(str(pc), (None, None))[1]
            )
            green_mark_poi["name"] = green_mark_poi.get(
                "Project_Name", green_mark_poi["postal_code"]
            )
            logger.info(
                "Green Mark geocoded: %s/%s",
                green_mark_poi["lat"].notna().sum(),
                len(green_mark_poi),
            )

    try:
        df = compute_proximity_features(
            df,
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
            green_mark_buildings=green_mark_poi if not green_mark_poi.empty else None,
        )
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        logger.warning("Skipping proximity features: %s", exc)
        df["dist_to_nearest_mrt"] = pd.NA
        df["nearest_mrt_station"] = pd.NA
        df["dist_to_nearest_mall"] = pd.NA
        df["nearest_mall"] = pd.NA
        for label in (
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
            df[f"dist_to_nearest_{label}"] = pd.NA
            df[f"nearest_{label}"] = pd.NA

    df = _add_planning_area(df)

    df = validate_and_quarantine(
        df,
        HFeatureTransaction,
        "feature_transaction",
        layer_dir=gold_dir,
        filename="features_with_amenities.parquet",
    )

    return df


def unified_features(
    features_with_amenities: pd.DataFrame, rental_yield: pd.DataFrame, gold_dir: Path
) -> pd.DataFrame:
    """Merge rental yield onto feature data.

    Args:
        features_with_amenities: Feature-enriched transactions.
        rental_yield: Precomputed rental yields.

    Returns:
        Unified feature DataFrame.
    """
    if features_with_amenities.empty:
        return pd.DataFrame()

    df = features_with_amenities.copy()

    if not rental_yield.empty:
        rental_df = rental_yield.copy()

        if "transaction_date" in df.columns and "month" not in df.columns:
            df = ensure_month_column(df)

        if "flat_type" in df.columns:
            df["flat_type"] = _normalize_hdb_flat_type(df["flat_type"])
        if "flat_type" in rental_df.columns:
            rental_df["flat_type"] = _normalize_hdb_flat_type(rental_df["flat_type"])

        merge_priority = [
            ["town", "month", "flat_type"],
            ["town", "month"],
        ]
        merge_keys: list[str] = []
        for keys in merge_priority:
            if all(k in df.columns for k in keys) and all(k in rental_df.columns for k in keys):
                merge_keys = keys
                break

        if merge_keys and "rental_yield_pct" in rental_df.columns:
            rental_cols = [*merge_keys, "rental_yield_pct"]
            rental_lookup = rental_df[rental_cols].dropna(subset=["rental_yield_pct"])
            sort_col = next((c for c in merge_keys if "month" in c or "date" in c), merge_keys[0])
            rental_lookup = rental_lookup.sort_values(sort_col).drop_duplicates(
                subset=merge_keys,
                keep="last",
            )
            df = df.merge(rental_lookup, on=merge_keys, how="left")
        else:
            logger.warning(
                "Skipping rental yield join: missing required join keys between feature and yield datasets"
            )

    df = validate_and_quarantine(
        df,
        HFeatureTransaction,
        "unified_feature",
        layer_dir=gold_dir,
        filename="unified_features.parquet",
    )

    return df


def macro_enriched_features(
    unified_features: pd.DataFrame,
    raw_macro_data: dict[str, pd.DataFrame],
    gold_dir: Path,
) -> pd.DataFrame:
    """Enrich unified features with macro economic indicators.

    Merges CPI, SORA, bank rates (SORA 3M), unemployment, and GDP onto
    transactions by matching date periods (monthly indicators by month,
    quarterly by quarter).

    Args:
        unified_features: Output from unified_features().
        raw_macro_data: Dict from raw_macro_data() with keys 'sora', 'cpi',
            'gdp', 'unemployment', 'bank_rates'.

    Returns:
        DataFrame with macro indicator columns added.
    """
    if unified_features.empty:
        return pd.DataFrame()

    df = unified_features.copy()
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

    logger.info(
        "Macro enrichment: cpi=%s, sora_rate=%s, sora_3m=%s, "
        "unemployment_rate=%s, gdp=%s, hdb_rpi=%s, ura_ppi=%s, wage_growth=%s",
        df["cpi"].notna().sum() if "cpi" in df.columns else 0,
        df["sora_rate"].notna().sum() if "sora_rate" in df.columns else 0,
        df["sora_3m"].notna().sum() if "sora_3m" in df.columns else 0,
        df["unemployment_rate"].notna().sum() if "unemployment_rate" in df.columns else 0,
        df["gdp"].notna().sum() if "gdp" in df.columns else 0,
        df["hdb_rpi"].notna().sum() if "hdb_rpi" in df.columns else 0,
        df["ura_ppi"].notna().sum() if "ura_ppi" in df.columns else 0,
        df["wage_growth"].notna().sum() if "wage_growth" in df.columns else 0,
    )

    df = validate_and_quarantine(
        df,
        HFeatureTransaction,
        "macro_enriched_feature",
        layer_dir=gold_dir,
        filename="macro_enriched_features.parquet",
    )

    return df


def block_metadata_enriched(
    macro_enriched_features: pd.DataFrame,
    raw_hdb_property_info: pd.DataFrame,
    gold_dir: Path,
) -> pd.DataFrame:
    """Enrich transactions with HDB block-level metadata.

    Merges max_floor_lvl, year_completed, total_dwelling_units, and flat type
    supply from HDB Property Information onto each transaction by matching
    block number + street name.

    Args:
        macro_enriched_features: Output from macro_enriched_features().
        raw_hdb_property_info: HDB Property Information from data.gov.sg.

    Returns:
        DataFrame with block metadata columns added.
    """
    if macro_enriched_features.empty or raw_hdb_property_info.empty:
        return macro_enriched_features

    df = macro_enriched_features.copy()

    if "block" not in df.columns or "street_name" not in df.columns:
        if "blk_no" not in df.columns:
            logger.warning("block_metadata_enriched: missing block/street columns")
            return df

    prop = raw_hdb_property_info.copy()
    prop["blk_no"] = prop["blk_no"].astype(str).str.strip().str.upper()
    prop["street"] = prop["street"].astype(str).str.strip().str.upper()

    block_col = "block" if "block" in df.columns else "blk_no"
    street_col = "street_name" if "street_name" in df.columns else "street"

    df["_join_block"] = df[block_col].astype(str).str.strip().str.upper()
    df["_join_street"] = df[street_col].astype(str).str.strip().str.upper()

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
        columns={
            "blk_no": "_join_block",
            "street": "_join_street",
        }
    )
    for col in ("max_floor_lvl", "year_completed", "total_dwelling_units"):
        if col in prop_lookup.columns:
            prop_lookup[col] = pd.to_numeric(prop_lookup[col], errors="coerce")

    prop_lookup = prop_lookup.drop_duplicates(subset=["_join_block", "_join_street"], keep="first")

    df = df.merge(prop_lookup, on=["_join_block", "_join_street"], how="left")
    df = df.drop(columns=["_join_block", "_join_street"], errors="ignore")

    matched = df["year_completed"].notna().sum() if "year_completed" in df.columns else 0
    logger.info(
        "Block metadata enrichment: %s/%s (%.1f%%) matched",
        matched,
        len(df),
        matched / len(df) * 100 if len(df) else 0,
    )

    df = validate_and_quarantine(
        df,
        HFeatureTransaction,
        "block_metadata_feature",
        layer_dir=gold_dir,
        filename="block_metadata_enriched.parquet",
    )

    return df


def income_enriched_features(
    block_metadata_enriched: pd.DataFrame,
    raw_income_by_planning_area: pd.DataFrame,
    gold_dir: Path,
) -> pd.DataFrame:
    """Enrich transactions with median household income by planning area.

    Args:
        block_metadata_enriched: Output from block_metadata_enriched().
        raw_income_by_planning_area: Income distribution by planning area.

    Returns:
        DataFrame with median_monthly_income column added.
    """
    if block_metadata_enriched.empty:
        return pd.DataFrame()
    df = block_metadata_enriched.copy()

    if raw_income_by_planning_area.empty or "planning_area" not in df.columns:
        df["median_monthly_income"] = pd.NA
        return df

    income_lookup = raw_income_by_planning_area[["planning_area", "median_monthly_income"]].copy()
    income_lookup["planning_area"] = income_lookup["planning_area"].astype(str).str.strip()
    income_lookup = income_lookup.dropna(subset=["median_monthly_income"])
    income_lookup = income_lookup.drop_duplicates(subset="planning_area", keep="first")

    df["planning_area"] = df["planning_area"].astype(str).str.strip()
    df = df.merge(income_lookup, on="planning_area", how="left")

    matched = df["median_monthly_income"].notna().sum()
    logger.info(
        "Income enrichment: %s/%s (%.1f%%) matched",
        matched,
        len(df),
        matched / len(df) * 100 if len(df) else 0,
    )

    df = validate_and_quarantine(
        df,
        HFeatureTransaction,
        "income_enriched_feature",
        layer_dir=gold_dir,
        filename="income_enriched_features.parquet",
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


def town_supply_enriched(
    income_enriched_features: pd.DataFrame,
    raw_dwelling_units_by_town: pd.DataFrame,
    raw_hdb_resident_population: pd.DataFrame,
    raw_median_annual_value: pd.DataFrame,
    gold_dir: Path,
) -> pd.DataFrame:
    """Enrich transactions with town-level supply, population density, and tax values.

    Merges total dwelling units (sold), resident population, and IRAS annual
    value onto each transaction by matching town name and flat type.

    Args:
        income_enriched_features: Output from income_enriched_features().
        raw_dwelling_units_by_town: Dwelling units under HDB management by town.
        raw_hdb_resident_population: HDB resident population by town.
        raw_median_annual_value: IRAS median annual value + property tax.

    Returns:
        DataFrame with town-level supply, demographic, and tax columns added.
    """
    if income_enriched_features.empty:
        return pd.DataFrame()

    df = income_enriched_features.copy()

    town_col = "town" if "town" in df.columns else None
    if town_col is None:
        logger.warning("town_supply_enriched: no 'town' column — skipping enrichment")
        for col in (
            "dwelling_units_in_town",
            "population_in_town",
            "population_per_dwelling",
            "annual_value",
            "property_tax",
        ):
            df[col] = pd.NA
        return df

    df["_town_upper"] = df[town_col].astype(str).str.strip().str.upper()

    # --- Dwelling units: filter to latest year + Sold Units, sum by town ---
    if not raw_dwelling_units_by_town.empty:
        dwell = raw_dwelling_units_by_town.copy()
        if {"town_or_estate", "no_of_dwelling_units", "financial_year", "sold_or_rental"}.issubset(
            dwell.columns
        ):
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
            matched = df["dwelling_units_in_town"].notna().sum()
            logger.info(
                "Town dwelling units (%s, Sold): %s/%s (%.1f%%) matched",
                int(latest_year),
                matched,
                len(df),
                matched / len(df) * 100 if len(df) else 0,
            )
        else:
            logger.warning("Dwelling units schema mismatch — skipping")
    if "dwelling_units_in_town" not in df.columns:
        df["dwelling_units_in_town"] = pd.NA

    # --- Population: filter to latest year, use number column ---
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
            matched_pop = df["population_in_town"].notna().sum()
            logger.info(
                "Town population (%s): %s/%s (%.1f%%) matched",
                int(latest_pop_year),
                matched_pop,
                len(df),
                matched_pop / len(df) * 100 if len(df) else 0,
            )
        else:
            logger.warning("Population schema mismatch — skipping")
    if "population_in_town" not in df.columns:
        df["population_in_town"] = pd.NA

    # --- Derived: population per dwelling ---
    units = pd.to_numeric(df["dwelling_units_in_town"], errors="coerce")
    pop_vals = pd.to_numeric(df["population_in_town"], errors="coerce")
    df["population_per_dwelling"] = np.where(units > 0, pop_vals / units, pd.NA)

    # --- Annual value: filter to latest year, match by flat type ---
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
            mav["median_annual_value"] = pd.to_numeric(mav["median_annual_value"], errors="coerce")
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

            matched_av = df["annual_value"].notna().sum() if "annual_value" in df.columns else 0
            logger.info(
                "Annual value (%s): %s/%s (%.1f%%) matched",
                int(latest_mav_year),
                matched_av,
                len(df),
                matched_av / len(df) * 100 if len(df) else 0,
            )
        else:
            logger.warning("Annual value schema mismatch — skipping")

    for col in (
        "dwelling_units_in_town",
        "population_in_town",
        "population_per_dwelling",
        "annual_value",
        "property_tax",
    ):
        if col not in df.columns:
            df[col] = pd.NA

    df = df.drop(columns=["_town_upper", "_av_type"], errors="ignore")

    df = validate_and_quarantine(
        df,
        HFeatureTransaction,
        "town_supply_feature",
        layer_dir=gold_dir,
        filename="town_supply_enriched.parquet",
    )

    return df
