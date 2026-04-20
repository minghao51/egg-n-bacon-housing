"""01_ingestion: Bronze layer data collection (Hamilton DAG node).

This module provides Hamilton-compatible functions for fetching raw data
from data.gov.sg and other external sources into the bronze layer.

Functions here are "pure" in the Hamilton sense: output depends only on
inputs + config, no global state.
"""

import logging
from pathlib import Path

import pandas as pd

from egg_n_bacon_housing.adapters import datagovsg
from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.cache import cached_call

logger = logging.getLogger(__name__)

DATASET_IDS = {
    "hdb_resale": "d_5785799d63a9da091f4e0b456291eeb8",
    "condo_resale": "d_2fd959a62c2d04c67a5a7c7538c53ddd",
    "private_transactions": "d_77b2707fa5e1d23fb40ca42f5f8a9d6d",
    "rental_index": "d_e03d53203e43c32df38b5123c9e1d2a4",
    "price_index": "d_9e06eb3f7b3b1e19aa2e0d868b0f1c8",
    "median_price": "d_1d6d7c0c40c0e0c6b9f4d9e6c1e9e5b",
}


def bronze_dir() -> Path:
    """Bronze layer directory path."""
    return settings.data_dir / "01_bronze"


def raw_hdb_resale_transactions() -> pd.DataFrame:
    """Fetch raw HDB resale transactions from data.gov.sg.

    Returns:
        DataFrame with raw HDB resale transactions.

    Loads from bronze if cached, otherwise fetches from API.
    """
    cache_id = "bronze_hdb_resale_raw"
    cache_path = bronze_dir() / "raw_hdb_resale.parquet"

    if cache_path.exists():
        logger.info(f"Loading HDB resale from bronze: {cache_path}")
        return pd.read_parquet(cache_path)

    def _fetch():
        url = "https://data.gov.sg/api/action/datastore_search?resource_id="
        return datagovsg.fetch_datagovsg_dataset(url, DATASET_IDS["hdb_resale"], use_cache=False)

    df = cached_call(cache_id, _fetch)
    if df is not None and not df.empty:
        bronze_dir().mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path, index=False)
        logger.info(f"Saved {len(df)} HDB resale records to bronze")
    return df if df is not None else pd.DataFrame()


def raw_condo_transactions() -> pd.DataFrame:
    """Fetch raw condo transactions from data.gov.sg.

    Returns:
        DataFrame with raw condo transactions.
    """
    cache_id = "bronze_condo_raw"
    cache_path = bronze_dir() / "raw_condo_transactions.parquet"

    if cache_path.exists():
        logger.info(f"Loading condo transactions from bronze: {cache_path}")
        return pd.read_parquet(cache_path)

    def _fetch():
        url = "https://data.gov.sg/api/action/datastore_search?resource_id="
        return datagovsg.fetch_datagovsg_dataset(url, DATASET_IDS["condo_resale"], use_cache=False)

    df = cached_call(cache_id, _fetch)
    if df is not None and not df.empty:
        bronze_dir().mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path, index=False)
        logger.info(f"Saved {len(df)} condo records to bronze")
    return df if df is not None else pd.DataFrame()


def raw_rental_index() -> pd.DataFrame:
    """Fetch URA rental index from data.gov.sg.

    Returns:
        DataFrame with rental index time series.
    """
    cache_id = "bronze_rental_index"
    cache_path = bronze_dir() / "raw_rental_index.parquet"

    if cache_path.exists():
        logger.info(f"Loading rental index from bronze: {cache_path}")
        return pd.read_parquet(cache_path)

    def _fetch():
        url = "https://data.gov.sg/api/action/datastore_search?resource_id="
        return datagovsg.fetch_datagovsg_dataset(url, DATASET_IDS["rental_index"], use_cache=False)

    df = cached_call(cache_id, _fetch)
    if df is not None and not df.empty:
        bronze_dir().mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path, index=False)
        logger.info(f"Saved {len(df)} rental index records to bronze")
    return df if df is not None else pd.DataFrame()


def raw_school_directory() -> pd.DataFrame:
    """Fetch school directory data.

    Returns:
        DataFrame with school locations and attributes.
    """
    cache_id = "bronze_school_directory"
    cache_path = bronze_dir() / "raw_school_directory.parquet"

    if cache_path.exists():
        logger.info(f"Loading school directory from bronze: {cache_path}")
        return pd.read_parquet(cache_path)

    def _fetch():
        url = "https://data.gov.sg/api/action/datastore_search?resource_id="
        return datagovsg.fetch_datagovsg_dataset(url, DATASET_IDS["median_price"], use_cache=False)

    df = cached_call(cache_id, _fetch)
    if df is not None and not df.empty:
        bronze_dir().mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_path, index=False)
        logger.info(f"Saved {len(df)} school records to bronze")
    return df if df is not None else pd.DataFrame()


def raw_macro_data() -> dict[str, pd.DataFrame]:
    """Load macro economic data from bronze layer.

    Returns:
        Dictionary with keys: 'sora', 'cpi', 'gdp', 'unemployment', 'ppi'.
    """
    macro_dir = settings.data_dir / "raw_data" / "macro"
    result = {}

    for indicator in ["sora", "cpi", "gdp", "unemployment", "ppi"]:
        path = macro_dir / f"{indicator}.parquet"
        if path.exists():
            result[indicator] = pd.read_parquet(path)
        else:
            logger.warning(f"Macro data not found: {indicator}")
            result[indicator] = pd.DataFrame()

    return result


def raw_shopping_malls() -> pd.DataFrame:
    """Load shopping mall data from bronze layer.

    Returns:
        DataFrame with mall locations.
    """
    cache_path = bronze_dir() / "raw_wiki_shopping_mall.parquet"

    if cache_path.exists():
        logger.info(f"Loading shopping malls from bronze: {cache_path}")
        return pd.read_parquet(cache_path)

    logger.warning("Shopping mall data not found in bronze layer")
    return pd.DataFrame()


def raw_mrt_stations() -> pd.DataFrame:
    """Load MRT station data from manual config.

    Returns:
        DataFrame with MRT station locations.
    """
    config_path = settings.data_dir / "config" / "mrt_stations.json"

    if not config_path.exists():
        logger.warning("MRT stations config not found")
        return pd.DataFrame()

    import json

    with open(config_path) as f:
        data = json.load(f)

    return pd.DataFrame(data) if data else pd.DataFrame()
