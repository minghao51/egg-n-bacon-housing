"""URA private property bronze nodes for the condo transaction source.

Primary path is the live URA Data Service API (rolling 5-year window,
batches 1-4) merged with the manual CSV history (pre-window years). The
CSV-only path remains as fallback when no ``URA_API_ACCESS_KEY`` is
configured or the API is unavailable.
"""

import logging
from pathlib import Path

import pandas as pd
import requests

from egg_n_bacon_housing.adapters import ura
from egg_n_bacon_housing.adapters.exceptions import AdapterError
from egg_n_bacon_housing.utils.bronze import (
    STALE_WARN_DAYS,
    read_bronze_cache,
    warn_if_stale,
    write_bronze_cache,
)
from egg_n_bacon_housing.utils.cache import CacheManager
from egg_n_bacon_housing.utils.hdb_lookups import SQFT_PER_SQM

logger = logging.getLogger(__name__)

__all__ = ["raw_condo_transactions", "_normalize_ura_api_rows"]


# --- API -> bronze contract mapping (matches the manual-CSV rename map) -----

_TYPE_OF_SALE = {"1": "New Sale", "2": "Sub Sale", "3": "Resale"}
_MARKET_SEGMENT = {
    "CCR": "Core Central Region",
    "RCR": "Rest of Central Region",
    "OCR": "Outside Central Region",
}


def _normalize_ura_api_rows(rows: list[dict]) -> pd.DataFrame:
    """Flatten raw URA API property rows to the condo bronze contract.

    Produces the same normalized columns as the manual-CSV path:
    project_name, street_name, price, area_sqft/area_sqm,
    transaction_date, type_of_sale, property_type (asset class: "condo"),
    property_subtype (URA's source property type),
    number_of_units, tenure, postal_district, market_segment, floor_level,
    type_of_area, nett_price.
    """
    records: list[dict] = []
    for entry in rows:
        base = {
            "project_name": str(entry.get("project") or "").strip(),
            "street_name": str(entry.get("street") or "").strip(),
            "market_segment": _MARKET_SEGMENT.get(
                str(entry.get("marketSegment") or "").strip().upper(),
                str(entry.get("marketSegment") or "").strip(),
            ),
        }
        for tx in entry.get("transaction") or []:
            type_of_area = str(tx.get("typeOfArea") or "").strip()
            try:
                area = float(tx.get("area")) if tx.get("area") not in (None, "") else None
            except (TypeError, ValueError):
                area = None
            try:
                price = float(tx.get("price")) if tx.get("price") not in (None, "") else None
            except (TypeError, ValueError):
                price = None

            area_sqft = area_sqm = None
            # URA API 'area' unit follows typeOfArea: Strata=sqft, Land=sqm.
            if area is not None and area > 0:
                if type_of_area.lower() == "land":
                    area_sqm, area_sqft = area, area * SQFT_PER_SQM
                else:
                    area_sqft, area_sqm = area, area / SQFT_PER_SQM

            floor_range = str(tx.get("floorRange") or "").strip()
            if "-" in floor_range and floor_range != "-":
                floor_range = floor_range.replace("-", " to ", 1)

            records.append(
                {
                    **base,
                    "price": price,
                    "area_sqft": area_sqft,
                    "area_sqm": area_sqm,
                    "transaction_date": pd.to_datetime(
                        str(tx.get("contractDate") or ""), format="%m%y", errors="coerce"
                    ),
                    "type_of_sale": _TYPE_OF_SALE.get(
                        str(tx.get("typeOfSale") or "").strip(),
                        str(tx.get("typeOfSale") or "").strip(),
                    ),
                    "property_type": "condo",
                    "property_subtype": str(tx.get("propertyType") or "").strip() or pd.NA,
                    "number_of_units": pd.to_numeric(tx.get("noOfUnits"), errors="coerce"),
                    "tenure": str(tx.get("tenure") or "").strip(),
                    "postal_district": pd.to_numeric(tx.get("district"), errors="coerce"),
                    "floor_level": floor_range,
                    "type_of_area": type_of_area,
                    "nett_price": pd.NA,
                }
            )

    df = pd.DataFrame(records)
    if not df.empty:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        pre_date_filter = len(df)
        df = df.dropna(subset=["transaction_date"])
        dropped_bad_dates = pre_date_filter - len(df)
        if dropped_bad_dates:
            logger.warning(
                "URA API normalization: dropped %s/%s row(s) with unparseable "
                "contractDate; kept %s",
                dropped_bad_dates,
                pre_date_filter,
                len(df),
            )
    return df


def _load_ura_csvs(ura_dir: Path, prefix: str) -> list[pd.DataFrame]:
    dataframes: list[pd.DataFrame] = []
    for csv_path in sorted(ura_dir.glob(f"{prefix}*.csv")):
        dataframes.append(pd.read_csv(csv_path, encoding="latin1"))
    return dataframes


_CSV_RENAME_MAP = {
    "Transacted Price ($)": "price",
    "Area (SQFT)": "area_sqft",
    "Area (SQM)": "area_sqm",
    "Sale Date": "sale_date",
    "Project Name": "project_name",
    "Street Name": "street_name",
    "Type of Sale": "type_of_sale",
    "Property Type": "property_subtype",
    "Number of Units": "number_of_units",
    "Tenure": "tenure",
    "Postal District": "postal_district",
    "Market Segment": "market_segment",
    "Floor Level": "floor_level",
    "Type of Area": "type_of_area",
    "Nett Price($)": "nett_price",
}


def _normalize_ura_csvs(
    dfs: list[pd.DataFrame], default_property_subtype: str | None = None
) -> pd.DataFrame:
    """Concatenate raw URA CSV frames and normalize to the bronze contract."""
    df = pd.concat(dfs, ignore_index=True)
    df = df.rename(columns={k: v for k, v in _CSV_RENAME_MAP.items() if k in df.columns})

    if "price" in df.columns:
        df["price"] = df["price"].astype(str).str.replace(",", "", regex=False)
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

    for col in ["area_sqft", "area_sqm"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False), errors="coerce"
            )

    if "transaction_date" not in df.columns and "sale_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["sale_date"], format="%b-%y", errors="coerce")

    if "property_subtype" not in df.columns:
        df["property_subtype"] = default_property_subtype or pd.NA
    elif default_property_subtype:
        missing_subtype = df["property_subtype"].isna() | (
            df["property_subtype"].astype(str).str.strip() == ""
        )
        df.loc[missing_subtype, "property_subtype"] = default_property_subtype

    df["property_type"] = "condo"

    return df


_DEDUPE_KEYS = [
    "project_name",
    "street_name",
    "transaction_date",
    "price",
    "area_sqft",
    "type_of_sale",
    "floor_level",
    "number_of_units",
]


def raw_condo_transactions(
    bronze_dir: Path,
    manual_dir: Path,
    cache_manager: CacheManager | None = None,
    ura_api_access_key: str = "",
) -> pd.DataFrame:
    """Load condo transactions: live URA API (5y window) merged with CSV history.

    Manual CSV history is looked up under ``manual_dir`` (injected by the
    pipeline from ``RuntimePaths.manual_dir``; no filesystem traversal).

    Order of preference:
    1. Bronze cache (``raw_condo_transactions.parquet``).
    2. Live URA API merged with manual CSV history, deduped on the natural
       key (CSV rows win, keeping one canonical copy of overlap years).
    3. Manual CSVs only (when no access key is configured or the API fails).
    """
    cached = read_bronze_cache(bronze_dir, "raw_condo_transactions")
    if cached is not None:
        logger.info("Loading condo from bronze: %s", bronze_dir / "raw_condo_transactions.parquet")
        warn_if_stale(
            bronze_dir, "raw_condo_transactions", STALE_WARN_DAYS["raw_condo_transactions"]
        )
        if "property_subtype" not in cached.columns:
            cached["property_subtype"] = pd.NA
            logger.warning(
                "Legacy condo bronze cache has no property_subtype; refresh it to recover URA subtypes"
            )
        return cached

    ura_dir = manual_dir / "csv" / "ura"
    residential_dfs = _load_ura_csvs(ura_dir, "ResidentialTransaction")
    ec_dfs = _load_ura_csvs(ura_dir, "ECResidentialTransaction")
    csv_parts: list[pd.DataFrame] = []
    if residential_dfs:
        csv_parts.append(_normalize_ura_csvs(residential_dfs))
    if ec_dfs:
        csv_parts.append(
            _normalize_ura_csvs(ec_dfs, default_property_subtype="Executive Condominium")
        )
    csv_df = pd.concat(csv_parts, ignore_index=True) if csv_parts else None

    api_df: pd.DataFrame | None = None
    if ura_api_access_key:
        try:
            rows = ura.fetch_all_resi_transactions(ura_api_access_key, cache_manager=cache_manager)
            if rows:
                api_df = _normalize_ura_api_rows(rows)
                logger.info("URA API: %d transaction rows after normalization", len(api_df))
            else:
                logger.warning("URA API returned no transaction rows")
        except (AdapterError, requests.RequestException, OSError, ValueError) as exc:
            logger.warning(
                "URA API fetch failed (%s: %s) — falling back to manual CSVs",
                exc.__class__.__name__,
                exc,
            )

    if api_df is not None and not api_df.empty:
        if csv_df is not None and not csv_df.empty:
            combined = pd.concat([csv_df, api_df], ignore_index=True)
            before = len(combined)
            combined = combined.drop_duplicates(subset=_DEDUPE_KEYS, keep="first")
            logger.info(
                "Merged condo history: %d CSV + %d API rows -> %d after dedupe",
                len(csv_df),
                len(api_df),
                len(combined),
            )
            if before != len(combined):
                logger.info("Removed %d overlapping rows", before - len(combined))
        else:
            logger.warning("No URA CSVs found — API window only (~5 years)")
            combined = api_df
    elif csv_df is not None and not csv_df.empty:
        combined = csv_df
    else:
        raise RuntimeError("Core dataset fetch failed: condo_resale (no URA CSVs found)")

    # Stable downstream asset class; URA's actual type remains available in
    # property_subtype (including Executive Condominium rows).
    combined["property_type"] = "condo"

    api_used = api_df is not None and not api_df.empty
    csvs_used = csv_df is not None and not csv_df.empty
    condo_source = (
        "+".join(part for part, used in (("ura_api", api_used), ("manual_csv", csvs_used)) if used)
        or "manual_csv"
    )

    write_bronze_cache(bronze_dir, combined, "raw_condo_transactions", condo_source)
    logger.info("Saved %s condo records to bronze", len(combined))
    return combined
