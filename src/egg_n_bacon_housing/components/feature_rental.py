"""Rental-domain Hamilton nodes and normalization helpers."""

import logging

import numpy as np
import pandas as pd
from hamilton.function_modifiers import extract_fields, hamilton_exclude

from egg_n_bacon_housing.schemas.feature_models import HRentalYieldRecord
from egg_n_bacon_housing.utils.hdb_lookups import normalize_hdb_flat_type
from egg_n_bacon_housing.utils.time_index import ensure_month_column
from egg_n_bacon_housing.utils.validation_gateway import (
    empty_extracted,
    extracted_validation,
    validate_and_quarantine,
)

logger = logging.getLogger(__name__)


@hamilton_exclude
def rental_yield(*args, **kwargs) -> pd.DataFrame:
    result = validate_rental_yield(*args, **kwargs)
    if not result["rental_yield_quarantine"].empty:
        logger.warning(
            "rental_yield: %s row(s) quarantined at the gold boundary",
            len(result["rental_yield_quarantine"]),
        )
    return result["rental_yield"]


@extract_fields({"rental_yield": pd.DataFrame, "rental_yield_quarantine": pd.DataFrame})
def validate_rental_yield(
    hdb_validated: pd.DataFrame,
    raw_hdb_rental: pd.DataFrame,
    raw_rental_index: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
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
        return empty_extracted(hdb_validated, "rental_yield", "rental_yield_quarantine")

    sales = hdb_validated.copy()
    rents = raw_hdb_rental.copy()

    sales["price"] = pd.to_numeric(sales["price"], errors="coerce")
    sales["transaction_date"] = pd.to_datetime(sales["transaction_date"], errors="coerce")
    sales = ensure_month_column(sales)
    sales["town"] = sales["town"].astype(str).str.upper().str.strip()
    sales["flat_type"] = normalize_hdb_flat_type(sales["flat_type"])
    sales = sales.dropna(subset=["price", "transaction_date", "town", "flat_type"])
    sales = sales[sales["price"] > 0]

    rents["monthly_rent"] = pd.to_numeric(rents["monthly_rent"], errors="coerce")
    rents["rent_approval_date"] = pd.to_datetime(
        rents["rent_approval_date"], format="%Y-%m", errors="coerce"
    )
    rents = ensure_month_column(rents, date_column="rent_approval_date")
    rents["town"] = rents["town"].astype(str).str.upper().str.strip()
    rents["flat_type"] = normalize_hdb_flat_type(rents["flat_type"])
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
    matched_keys = sales_keys & rent_keys
    sales_only_count = len(sales_keys - rent_keys)
    rent_only_count = len(rent_keys - sales_keys)
    if sales_only_count > 0 or rent_only_count > 0:
        # The inner merge below drops every sales group without a matching
        # rent group — a population-defining cut, so it warns with coverage.
        matched_coverage = (len(matched_keys) / len(sales_keys) * 100) if sales_keys else 100.0
        logger.warning(
            "Rental yield join: %s of %s sales (town/flat_type/month) groups have no "
            "matching rent group — inner merge drops them (matched-group coverage "
            "%.1f%%); %s rent group(s) have no matching sales group",
            sales_only_count,
            len(sales_keys),
            matched_coverage,
            rent_only_count,
        )

    combo_yields = monthly_sales.merge(
        monthly_rents,
        on=["town", "flat_type", "month"],
        how="inner",
    )

    if combo_yields.empty:
        return empty_extracted(combo_yields, "rental_yield", "rental_yield_quarantine")

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
    )
    df["rental_yield_pct"] = df["rental_yield_pct"] / df["sample_size"]
    df["property_type"] = "HDB"
    # The output is intentionally aggregated across flat types; make that
    # grain explicit rather than returning a misleading null field.
    df["flat_type"] = "ALL"

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
        if expanded_index:
            rental_index = pd.DataFrame(expanded_index)
            df = df.merge(
                rental_index.drop_duplicates(),
                on="month",
                how="left",
            )

    return extracted_validation(
        validate_and_quarantine(df, HRentalYieldRecord, "rental_yield"),
        "rental_yield",
        "rental_yield_quarantine",
    )
