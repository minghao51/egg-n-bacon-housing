"""URA private property CSV loading nodes for bronze layer."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

__all__ = ["raw_condo_transactions"]


def _manual_ura_dir(bronze_dir: Path) -> Path:
    return bronze_dir.parent.parent / "manual" / "csv" / "ura"


def _load_ura_csvs(ura_dir: Path, prefix: str) -> list[pd.DataFrame]:
    dataframes: list[pd.DataFrame] = []
    for csv_path in sorted(ura_dir.glob(f"{prefix}*.csv")):
        dataframes.append(pd.read_csv(csv_path, encoding="latin1"))
    return dataframes


def raw_condo_transactions(bronze_dir: Path) -> pd.DataFrame:
    cache_path = bronze_dir / "raw_condo_transactions.parquet"
    if cache_path.exists():
        logger.info("Loading condo from bronze: %s", cache_path)
        return pd.read_parquet(cache_path)

    ura_dir = _manual_ura_dir(bronze_dir)
    dfs = _load_ura_csvs(ura_dir, "ResidentialTransaction")

    if not dfs:
        raise RuntimeError("Core dataset fetch failed: condo_resale (no URA CSVs found)")

    df = pd.concat(dfs, ignore_index=True)

    rename_map = {
        "Transacted Price ($)": "price",
        "Area (SQFT)": "area_sqft",
        "Area (SQM)": "area_sqm",
        "Unit Price ($ PSF)": "unit_price_psf",
        "Unit Price ($ PSM)": "unit_price_psm",
        "Sale Date": "sale_date",
        "Project Name": "project_name",
        "Street Name": "street_name",
        "Type of Sale": "type_of_sale",
        "Property Type": "property_type",
        "Number of Units": "number_of_units",
        "Tenure": "tenure",
        "Postal District": "postal_district",
        "Market Segment": "market_segment",
        "Floor Level": "floor_level",
        "Type of Area": "type_of_area",
        "Nett Price($)": "nett_price",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    if "price" in df.columns:
        df["price"] = df["price"].astype(str).str.replace(",", "").astype(float)

    for col in ["area_sqft", "area_sqm", "unit_price_psf", "unit_price_psm"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

    if "sale_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["sale_date"], format="%b-%y", errors="coerce")

    df["property_type"] = "condo"

    bronze_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    logger.info("Saved %s condo records to bronze from URA CSVs", len(df))
    return df
