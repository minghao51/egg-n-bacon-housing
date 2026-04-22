"""02_cleaning: Silver layer cleaning and validation (Hamilton DAG node).

This module provides Hamilton-compatible functions for cleaning and
validating bronze data into the silver layer.
"""

import logging
from pathlib import Path

import pandas as pd

from egg_n_bacon_housing.config import settings

logger = logging.getLogger(__name__)


def silver_dir() -> Path:
    """Silver layer directory path."""
    return settings.silver_dir


def cleaned_hdb_transactions(raw_hdb_resale_transactions: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate HDB resale transactions.

    Args:
        raw_hdb_resale_transactions: Raw bronze data.

    Returns:
        Cleaned DataFrame with validated fields.
    """
    if raw_hdb_resale_transactions.empty:
        return pd.DataFrame()

    df = raw_hdb_resale_transactions.copy()

    if "resale_price" in df.columns:
        df = df.rename(columns={"resale_price": "price"})

    if "floor_area_sqm" in df.columns and "floor_area_sqft" not in df.columns:
        df["floor_area_sqft"] = df["floor_area_sqm"] * 10.764

    if "month" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["month"], format="%Y-%m", errors="coerce")

    if "property_type" not in df.columns:
        df["property_type"] = "hdb"

    if "remaining_lease_months" in df.columns:
        mask = df["remaining_lease_months"].isna()
        if mask.any():
            lcd = df.loc[mask, "lease_commence_date"].astype(int)
            tx_year = df.loc[mask, "transaction_date"].dt.year
            df.loc[mask, "remaining_lease_months"] = 99 - (tx_year - lcd)

    if "storey_range" in df.columns and "storey_min" not in df.columns:
        storey_parts = df["storey_range"].str.split(" TO ", n=1, expand=True)
        df["storey_min"] = pd.to_numeric(storey_parts[0], errors="coerce").astype("Int64")
        df["storey_max"] = pd.to_numeric(storey_parts[1], errors="coerce").astype("Int64")

    if "address" not in df.columns and "block" in df.columns and "street_name" in df.columns:
        df["address"] = df["block"] + " " + df["street_name"]

    df = df.dropna(subset=["price", "transaction_date"])
    df = df[df["price"] > 0]

    silver_dir().mkdir(parents=True, exist_ok=True)
    out_path = silver_dir() / "cleaned_hdb_transactions.parquet"
    df.to_parquet(out_path, index=False)
    logger.info(f"Saved {len(df)} cleaned HDB transactions to silver")

    return df


def hdb_validated(cleaned_hdb_transactions: pd.DataFrame) -> pd.DataFrame:
    """Validate HDB transactions against schema.

    Args:
        cleaned_hdb_transactions: Output from cleaned_hdb_transactions.

    Returns:
        Validated DataFrame.

    Raises:
        ValueError: If validation fails.
    """
    if cleaned_hdb_transactions.empty:
        return pd.DataFrame()

    from egg_n_bacon_housing.schemas.clean_models import HCleanHDBTransaction

    validation_errors = []
    validated_records = []

    for idx, row in cleaned_hdb_transactions.iterrows():
        try:
            record = HCleanHDBTransaction(**row.to_dict())
            validated_records.append(record.model_dump())
        except Exception as e:
            validation_errors.append({"index": idx, "error": str(e)})

    if validation_errors:
        error_count = len(validation_errors)
        logger.warning(f"Validation failed for {error_count} HDB records")
        if error_count <= 5:
            for err in validation_errors[:5]:
                logger.debug(f"  Row {err['index']}: {err['error']}")
        else:
            for err in validation_errors[:3]:
                logger.debug(f"  Row {err['index']}: {err['error']}")
            logger.debug(f"  ... and {error_count - 3} more")

    if validated_records:
        validated_df = pd.DataFrame(validated_records)
        logger.info(f"Validated {len(validated_df)} HDB transactions successfully")
        return validated_df
    else:
        logger.warning("No HDB transactions passed validation")
        return pd.DataFrame()


def cleaned_condo_transactions(raw_condo_transactions: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate condo transactions.

    Args:
        raw_condo_transactions: Raw bronze data.

    Returns:
        Cleaned DataFrame.
    """
    if raw_condo_transactions.empty:
        return pd.DataFrame()

    df = raw_condo_transactions.copy()

    if "transaction_date" not in df.columns and "date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["date"], errors="coerce")

    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

    df = df.dropna(subset=["price", "transaction_date"])
    df = df[df["price"] > 0]

    silver_dir().mkdir(parents=True, exist_ok=True)
    out_path = silver_dir() / "cleaned_condo_transactions.parquet"
    df.to_parquet(out_path, index=False)
    logger.info(f"Saved {len(df)} cleaned condo transactions to silver")

    return df


def condo_validated(cleaned_condo_transactions: pd.DataFrame) -> pd.DataFrame:
    """Validate condo transactions against schema."""
    if cleaned_condo_transactions.empty:
        return pd.DataFrame()

    from egg_n_bacon_housing.schemas.clean_models import HCleanCondoTransaction

    validation_errors = []
    validated_records = []

    for idx, row in cleaned_condo_transactions.iterrows():
        try:
            record = HCleanCondoTransaction(**row.to_dict())
            validated_records.append(record.model_dump())
        except Exception as e:
            validation_errors.append({"index": idx, "error": str(e)})

    if validation_errors:
        error_count = len(validation_errors)
        logger.warning(f"Validation failed for {error_count} condo records")
        if error_count <= 5:
            for err in validation_errors[:5]:
                logger.debug(f"  Row {err['index']}: {err['error']}")
        else:
            for err in validation_errors[:3]:
                logger.debug(f"  Row {err['index']}: {err['error']}")
            logger.debug(f"  ... and {error_count - 3} more")

    if validated_records:
        validated_df = pd.DataFrame(validated_records)
        logger.info(f"Validated {len(validated_df)} condo transactions successfully")
        return validated_df
    else:
        logger.warning("No condo transactions passed validation")
        return pd.DataFrame()


def cleaned_ec_transactions(raw_condo_transactions: pd.DataFrame) -> pd.DataFrame:
    """Clean EC transactions (subset of condo data with EC filter).

    Args:
        raw_condo_transactions: Raw condo data.

    Returns:
        Cleaned EC DataFrame.
    """
    if raw_condo_transactions.empty:
        return pd.DataFrame()

    df = raw_condo_transactions.copy()

    if "property_type" in df.columns:
        df = df[df["property_type"].str.lower().str.contains("ec", na=False)]

    if "transaction_date" not in df.columns and "date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["date"], errors="coerce")

    df["price"] = pd.to_numeric(df.get("price", df.get("transaction_price", 0)), errors="coerce")
    df = df.dropna(subset=["price", "transaction_date"])
    df = df[df["price"] > 0]

    silver_dir().mkdir(parents=True, exist_ok=True)
    out_path = silver_dir() / "cleaned_ec_transactions.parquet"
    df.to_parquet(out_path, index=False)
    logger.info(f"Saved {len(df)} cleaned EC transactions to silver")

    return df


def ec_validated(cleaned_ec_transactions: pd.DataFrame) -> pd.DataFrame:
    """Validate EC transactions against schema."""
    if cleaned_ec_transactions.empty:
        return pd.DataFrame()

    from egg_n_bacon_housing.schemas.clean_models import HCleanECTransaction

    validation_errors = []
    validated_records = []

    for idx, row in cleaned_ec_transactions.iterrows():
        try:
            record = HCleanECTransaction(**row.to_dict())
            validated_records.append(record.model_dump())
        except Exception as e:
            validation_errors.append({"index": idx, "error": str(e)})

    if validation_errors:
        error_count = len(validation_errors)
        logger.warning(f"Validation failed for {error_count} EC records")
        if error_count <= 5:
            for err in validation_errors[:5]:
                logger.debug(f"  Row {err['index']}: {err['error']}")
        else:
            for err in validation_errors[:3]:
                logger.debug(f"  Row {err['index']}: {err['error']}")
            logger.debug(f"  ... and {error_count - 3} more")

    if validated_records:
        validated_df = pd.DataFrame(validated_records)
        logger.info(f"Validated {len(validated_df)} EC transactions successfully")
        return validated_df
    else:
        logger.warning("No EC transactions passed validation")
        return pd.DataFrame()


def geocoded_properties(hdb_validated: pd.DataFrame, condo_validated: pd.DataFrame) -> pd.DataFrame:
    """Merge geocoding data onto validated transactions.

    Args:
        hdb_validated: Validated HDB transactions.
        condo_validated: Validated condo transactions.

    Returns:
        DataFrame with lat/lon coordinates.
    """

    dfs = []
    for df, ptype in [(hdb_validated, "hdb"), (condo_validated, "condo")]:
        if df.empty:
            continue
        df = df.copy()
        df["property_type"] = ptype
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)

    if "lat" not in combined.columns or "lon" not in combined.columns:
        logger.warning("Geocoding not available - returning coordinates as-is")
        return combined

    silver_dir().mkdir(parents=True, exist_ok=True)
    out_path = silver_dir() / "geocoded_properties.parquet"
    combined.to_parquet(out_path, index=False)
    logger.info(f"Saved {len(combined)} geocoded properties to silver")

    return combined


def geocoded_validated(geocoded_properties: pd.DataFrame) -> pd.DataFrame:
    """Validate geocoded properties against schema."""
    if geocoded_properties.empty:
        return pd.DataFrame()

    from egg_n_bacon_housing.schemas.clean_models import GeocodedProperty

    validation_errors = []
    validated_records = []

    for idx, row in geocoded_properties.iterrows():
        try:
            record = GeocodedProperty(**row.to_dict())
            validated_records.append(record.model_dump())
        except Exception as e:
            validation_errors.append({"index": idx, "error": str(e)})

    if validation_errors:
        error_count = len(validation_errors)
        logger.warning(f"Validation failed for {error_count} geocoded records")
        if error_count <= 5:
            for err in validation_errors[:5]:
                logger.debug(f"  Row {err['index']}: {err['error']}")
        else:
            for err in validation_errors[:3]:
                logger.debug(f"  Row {err['index']}: {err['error']}")
            logger.debug(f"  ... and {error_count - 3} more")

    if validated_records:
        validated_df = pd.DataFrame(validated_records)
        logger.info(f"Validated {len(validated_df)} geocoded properties successfully")
        return validated_df
    else:
        logger.warning("No geocoded properties passed validation")
        return pd.DataFrame()
