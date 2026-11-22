"""Rental-domain Hamilton nodes and normalization helpers."""

import logging
from typing import Any, cast

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


# The index is context, not a denominator, and it is the URA *private
# residential* property rental index -- not an HDB index. It is carried beside
# the HDB yield as a market marker only. Preference order, measured against
# `raw_rental_index.parquet` at the 2026-10 cutoff:
#   Non-Landed      91 quarters, 2004Q1-2026Q3  <- continuous to the cutoff
#   All Residential 70 quarters, 2004Q1-2021Q2  <- stops five years early
#   Landed          91 quarters, 2004Q1-2026Q3  <- different segment
# Choosing "All Residential" would leave 91.4% of published rows (1,599 of
# 1,749) with a null index, so the continuous non-landed series is used,
# falling back to "All Residential" only when a source carries nothing else.
RENTAL_INDEX_SERIES_PREFERENCE: tuple[str, ...] = ("NON-LANDED", "ALL RESIDENTIAL")


def _whole_island_rental_index(raw_rental_index: pd.DataFrame) -> pd.DataFrame:
    """Expand one whole-island index series to `month -> rental_index`.

    The source carries **three property-type series per quarter** (Landed,
    Non-Landed, All Residential) under the same `locality`. Selecting only the
    locality and merging on `month` therefore multiplied every town-month row
    2–3× — identical yields, different `rental_index` — which RS02 caught in
    `rental_yield.parquet` (3,623 rows for 1,749 town-months).

    One series is chosen by `RENTAL_INDEX_SERIES_PREFERENCE`; a source without a
    `property_type` column is treated as a single series. Months the chosen
    series does not cover stay null rather than borrowing another segment.
    """
    rental_index = raw_rental_index.copy()
    rental_index = cast(
        pd.DataFrame,
        rental_index[
            rental_index["locality"].astype(str).str.upper().str.strip() == "WHOLE ISLAND"
        ],
    )
    if "property_type" in rental_index.columns:
        property_type = rental_index["property_type"].astype(str).str.upper().str.strip()
        for series in RENTAL_INDEX_SERIES_PREFERENCE:
            selected = cast(pd.DataFrame, rental_index[property_type == series])
            if not selected.empty:
                rental_index = selected
                break
        else:
            return pd.DataFrame(columns=cast(Any, ["month", "rental_index"]))
    rental_index["quarter"] = pd.PeriodIndex(rental_index["quarter"], freq="Q")
    rental_index["rental_index"] = pd.to_numeric(rental_index["index"], errors="coerce")
    rental_index = rental_index.dropna(subset=["rental_index"])
    if rental_index.empty:
        return pd.DataFrame(columns=cast(Any, ["month", "rental_index"]))

    expanded_index: list[dict[str, object]] = []
    latest = rental_index.sort_values("quarter").drop_duplicates(subset=["quarter"], keep="last")
    for row in cast(Any, latest[["quarter", "rental_index"]].itertuples(index=False)):
        start_month = row.quarter.asfreq("M", how="start")
        for month in pd.period_range(start=start_month, periods=3, freq="M"):
            expanded_index.append({"month": str(month), "rental_index": row.rental_index})

    return (
        pd.DataFrame(expanded_index)
        .drop_duplicates(subset=["month"], keep="last")
        .reset_index(drop=True)
    )


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
    sales["flat_type"] = normalize_hdb_flat_type(cast(pd.Series, sales["flat_type"]))
    sales = sales.dropna(subset=["price", "transaction_date", "town", "flat_type"])
    sales = sales[sales["price"] > 0]

    rents["monthly_rent"] = pd.to_numeric(rents["monthly_rent"], errors="coerce")
    rents["rent_approval_date"] = pd.to_datetime(
        rents["rent_approval_date"], format="%Y-%m", errors="coerce"
    )
    rents = ensure_month_column(rents, date_column="rent_approval_date")
    rents["town"] = rents["town"].astype(str).str.upper().str.strip()
    rents["flat_type"] = normalize_hdb_flat_type(cast(pd.Series, rents["flat_type"]))
    rents = rents.dropna(subset=["monthly_rent", "rent_approval_date", "town", "flat_type"])
    rents = rents[rents["monthly_rent"] > 0]

    monthly_sales = cast(
        pd.DataFrame,
        sales.groupby(["town", "flat_type", "month"], as_index=False).agg(
            median_price=("price", "median"), sale_sample_size=("price", "size")
        ),
    )
    monthly_rents = cast(
        pd.DataFrame,
        rents.groupby(["town", "flat_type", "month"], as_index=False).agg(
            median_rent=("monthly_rent", "median"), rent_sample_size=("monthly_rent", "size")
        ),
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

    df = cast(
        pd.DataFrame,
        combo_yields.groupby(["town", "month"], as_index=False).agg(
            median_price=("median_price", "median"),
            median_rent=("median_rent", "median"),
            rental_yield_pct=("weighted_yield", lambda x: x.sum()),
            sample_size=("sale_sample_size", "sum"),
        ),
    )
    df["rental_yield_pct"] = df["rental_yield_pct"] / df["sample_size"]
    df["property_type"] = "HDB"
    # The output is intentionally aggregated across flat types; make that
    # grain explicit rather than returning a misleading null field.
    df["flat_type"] = "ALL"

    if not raw_rental_index.empty and {"quarter", "locality", "index"}.issubset(
        raw_rental_index.columns
    ):
        rental_index = _whole_island_rental_index(raw_rental_index)
        if not rental_index.empty:
            # `validate="m:1"` makes a fan-out a loud failure instead of
            # silently duplicating every town-month row (the defect RS02 found:
            # three property-type series per quarter merged on month alone).
            df = df.merge(rental_index, on="month", how="left", validate="m:1")

    return extracted_validation(
        validate_and_quarantine(df, HRentalYieldRecord, "rental_yield"),
        "rental_yield",
        "rental_yield_quarantine",
    )
