"""03_features: Gold layer feature engineering (Hamilton DAG node).

This module provides Hamilton-compatible functions for computing features
from silver data into the gold layer.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.mrt_distance import calculate_nearest_mrt, load_mrt_stations
from egg_n_bacon_housing.utils.school_features import calculate_school_features

logger = logging.getLogger(__name__)


def gold_dir() -> Path:
    """Gold layer directory path."""
    return settings.gold_dir


def _normalize_hdb_flat_type(series: pd.Series) -> pd.Series:
    """Normalize HDB flat types so rental and resale records can be joined."""
    return (
        series.astype(str)
        .str.upper()
        .str.strip()
        .replace(
            {
                "1 ROOM": "1-ROOM",
                "2 ROOM": "2-ROOM",
                "3 ROOM": "3-ROOM",
                "4 ROOM": "4-ROOM",
                "5 ROOM": "5-ROOM",
                "EXECUTIVE": "EXECUTIVE",
                "MULTI GENERATION": "MULTI-GENERATION",
            }
        )
    )


def _nearest_mall_features(
    properties_df: pd.DataFrame,
    malls_df: pd.DataFrame,
) -> pd.DataFrame:
    """Add nearest mall features when the source mall dataset has coordinates."""
    df = properties_df.copy()

    name_column = next(
        (col for col in ["shopping_mall", "name", "mall_name"] if col in malls_df.columns),
        None,
    )
    lat_column = next((col for col in ["lat", "latitude"] if col in malls_df.columns), None)
    lon_column = next((col for col in ["lon", "longitude"] if col in malls_df.columns), None)

    if not name_column or not lat_column or not lon_column:
        logger.warning("Skipping mall distance features: mall coordinates are unavailable")
        df["dist_to_nearest_mall"] = pd.NA
        df["nearest_mall"] = pd.NA
        return df

    valid_malls = malls_df[[name_column, lat_column, lon_column]].copy()
    valid_malls[lat_column] = pd.to_numeric(valid_malls[lat_column], errors="coerce")
    valid_malls[lon_column] = pd.to_numeric(valid_malls[lon_column], errors="coerce")
    valid_malls = valid_malls.dropna(subset=[lat_column, lon_column])

    if valid_malls.empty:
        logger.warning("Skipping mall distance features: no geocoded mall rows found")
        df["dist_to_nearest_mall"] = pd.NA
        df["nearest_mall"] = pd.NA
        return df

    property_coords = np.radians(df[["lat", "lon"]].astype(float).to_numpy())
    mall_coords = np.radians(valid_malls[[lat_column, lon_column]].to_numpy())

    tree = BallTree(mall_coords, metric="haversine")
    distances_rad, nearest_indices = tree.query(property_coords, k=1)
    distances_m = distances_rad[:, 0] * 6371000
    nearest_indices_flat = nearest_indices[:, 0]

    df["dist_to_nearest_mall"] = distances_m
    df["nearest_mall"] = valid_malls.iloc[nearest_indices_flat][name_column].to_numpy()
    return df


def rental_yield(
    hdb_validated: pd.DataFrame,
    raw_hdb_rental: pd.DataFrame,
    raw_rental_index: pd.DataFrame,
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
    sales["month"] = sales["transaction_date"].dt.to_period("M").astype(str)
    sales["town"] = sales["town"].astype(str).str.upper().str.strip()
    sales["flat_type"] = _normalize_hdb_flat_type(sales["flat_type"])
    sales = sales.dropna(subset=["price", "transaction_date", "town", "flat_type"])
    sales = sales[sales["price"] > 0]

    rents["monthly_rent"] = pd.to_numeric(rents["monthly_rent"], errors="coerce")
    rents["rent_approval_date"] = pd.to_datetime(
        rents["rent_approval_date"], format="%Y-%m", errors="coerce"
    )
    rents["month"] = rents["rent_approval_date"].dt.to_period("M").astype(str)
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

    gold_dir().mkdir(parents=True, exist_ok=True)
    out_path = gold_dir() / "rental_yield.parquet"
    df.to_parquet(out_path, index=False)
    logger.info(f"Saved {len(df)} rental yield records to gold")

    return df


def features_with_amenities(
    geocoded_validated: pd.DataFrame,
    raw_school_directory: pd.DataFrame,
    raw_shopping_malls: pd.DataFrame,
) -> pd.DataFrame:
    """Compute amenity distance features.

    Args:
        geocoded_validated: Geocoded transaction data.
        raw_school_directory: School locations.

    Returns:
        DataFrame with computed features.
    """
    if geocoded_validated.empty:
        return pd.DataFrame()

    df = geocoded_validated.copy()
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
        mrt_stations = load_mrt_stations()
        df = calculate_nearest_mrt(df, mrt_stations_df=mrt_stations, show_progress=False)
        if "nearest_mrt_distance" in df.columns:
            df["dist_to_nearest_mrt"] = df["nearest_mrt_distance"]
        if "nearest_mrt_name" in df.columns:
            df["nearest_mrt_station"] = df["nearest_mrt_name"]
    except Exception as exc:
        logger.warning(f"Skipping MRT feature enrichment: {exc}")
        df["dist_to_nearest_mrt"] = pd.NA
        df["nearest_mrt_station"] = pd.NA

    df = _nearest_mall_features(df, raw_shopping_malls)

    gold_dir().mkdir(parents=True, exist_ok=True)
    out_path = gold_dir() / "features_with_amenities.parquet"
    df.to_parquet(out_path, index=False)
    logger.info(f"Saved {len(df)} feature records to gold")

    return df


def unified_features(
    features_with_amenities: pd.DataFrame, rental_yield: pd.DataFrame
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
            df["month"] = (
                pd.to_datetime(df["transaction_date"], errors="coerce")
                .dt.to_period("M")
                .astype(str)
            )

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
            rental_cols = merge_keys + ["rental_yield_pct"]
            rental_lookup = (
                rental_df[rental_cols]
                .dropna(subset=["rental_yield_pct"])
                .drop_duplicates(
                    subset=merge_keys,
                    keep="last",
                )
            )
            df = df.merge(rental_lookup, on=merge_keys, how="left")
        else:
            logger.warning(
                "Skipping rental yield join: missing required join keys between feature and yield datasets"
            )

    gold_dir().mkdir(parents=True, exist_ok=True)
    out_path = gold_dir() / "unified_features.parquet"
    df.to_parquet(out_path, index=False)
    logger.info(f"Saved {len(df)} unified features to gold")

    return df
