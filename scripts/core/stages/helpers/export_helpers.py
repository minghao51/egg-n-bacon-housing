"""Helper functions for L3 data export and column cleaning."""

import logging
from typing import List

import pandas as pd

logger = logging.getLogger(__name__)


def clean_numeric_column(
    df: pd.DataFrame, col_name: str, remove_dollar: bool = False
) -> pd.DataFrame:
    """
    Clean a numeric column by removing commas and optional dollar signs.

    Args:
        df: DataFrame to clean
        col_name: Column name to clean
        remove_dollar: Whether to remove $ signs

    Returns:
        DataFrame with cleaned column (modified in place)
    """
    if col_name not in df.columns:
        return df

    df[col_name] = df[col_name].astype(str).str.replace(",", "")

    if remove_dollar:
        df[col_name] = df[col_name].str.replace("$", "").str.strip()

    df[col_name] = pd.to_numeric(df[col_name], errors="coerce")

    return df


def clean_price_columns(
    df: pd.DataFrame,
    price_cols: List[str],
    area_cols: List[str],
    psf_cols: List[str],
) -> pd.DataFrame:
    """
    Clean multiple price, area, and PSF columns in a DataFrame.

    Args:
        df: DataFrame to clean
        price_cols: List of price column names
        area_cols: List of area column names
        psf_cols: List of PSF column names

    Returns:
        Cleaned DataFrame
    """
    df = df.copy()

    # Clean price columns (may have $ signs)
    for col in price_cols:
        if col in df.columns:
            df = clean_numeric_column(df, col, remove_dollar=True)

    # Clean area columns (no $ signs)
    for col in area_cols:
        if col in df.columns:
            df = clean_numeric_column(df, col, remove_dollar=False)

    # Clean PSF columns
    for col in psf_cols:
        if col in df.columns:
            df = clean_numeric_column(df, col, remove_dollar=False)

    return df


def add_psf_psm_columns(df: pd.DataFrame, price_col: str = "price") -> pd.DataFrame:
    """
    Add PSF and PSM columns if floor area data exists.

    Args:
        df: DataFrame with price and area data
        price_col: Name of price column

    Returns:
        DataFrame with price_psf and price_psm columns added
    """
    df = df.copy()

    # Check if we have both sqft and sqm data
    has_sqft = "floor_area_sqft" in df.columns
    has_sqm = "floor_area_sqm" in df.columns

    if has_sqft:
        df["price_psf"] = df[price_col] / df["floor_area_sqft"]

        # Derive PSM from PSF if no SQM data
        if not has_sqm:
            df["price_psm"] = df["price_psf"] * 10.764

    if has_sqm and not has_sqft:
        # Derive PSF from PSM if no SQFT data
        df["price_psm"] = df[price_col] / df["floor_area_sqm"]
        df["price_psf"] = df["price_psm"] / 10.764

    return df
