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
from egg_n_bacon_housing.utils.school_features import calculate_school_features
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
    gold_dir: Path,
) -> pd.DataFrame:
    """Compute amenity distance features.

    Args:
        geocoded_validated: Geocoded transaction data.
        raw_school_directory: School locations.
        raw_mrt_stations: MRT station data (from 01_ingestion).

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

    try:
        df = compute_proximity_features(
            df,
            mrt_stations=raw_mrt_stations if not raw_mrt_stations.empty else None,
            malls=raw_shopping_malls if not raw_shopping_malls.empty else None,
        )
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        logger.warning("Skipping proximity features: %s", exc)
        df["dist_to_nearest_mrt"] = pd.NA
        df["nearest_mrt_station"] = pd.NA
        df["dist_to_nearest_mall"] = pd.NA
        df["nearest_mall"] = pd.NA

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
