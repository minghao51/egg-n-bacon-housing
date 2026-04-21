"""01_ingestion: Bronze layer data collection (Hamilton DAG node).

This module provides Hamilton-compatible functions for fetching raw data
from data.gov.sg and other external sources into the bronze layer.

Functions here are "pure" in the Hamilton sense: output depends only on
inputs + config, no global state.
"""

import logging
from pathlib import Path

import pandas as pd

from egg_n_bacon_housing.adapters import datagovsg, onemap
from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.cache import cached_call

logger = logging.getLogger(__name__)

DATASET_IDS = {
    "hdb_resale": "d_5785799d63a9da091f4e0b456291eeb8",
    "condo_resale": "d_2fd959a62c2d04c67a5a7c7538c53ddd",
    "private_transactions": "d_77b2707fa5e1d23fb40ca42f5f8a9d6d",
    "hdb_rental": "d_8b84f0dfe7acb6d6585a7d7e6e406b31",
    "rental_index": "d_e03d53203e43c32df38b5123c9e1d2a4",
    "price_index": "d_9e06eb3f7b3b1e19aa2e0d868b0f1c8",
    "school_directory": "d_69d6a3ed8b3b1e19aa2e0d868b0f2c7",
}


def bronze_dir() -> Path:
    """Bronze layer directory path."""
    return settings.bronze_dir


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
    cache_candidates = [
        bronze_dir() / "raw_rental_index.parquet",
        bronze_dir() / "raw_datagov_rental_index.parquet",
    ]

    for cache_path in cache_candidates:
        if cache_path.exists():
            logger.info(f"Loading rental index from bronze: {cache_path}")
            return pd.read_parquet(cache_path)

    def _fetch():
        url = "https://data.gov.sg/api/action/datastore_search?resource_id="
        return datagovsg.fetch_datagovsg_dataset(url, DATASET_IDS["rental_index"], use_cache=False)

    df = cached_call(cache_id, _fetch)
    if df is not None and not df.empty:
        bronze_dir().mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_candidates[0], index=False)
        logger.info(f"Saved {len(df)} rental index records to bronze")
    return df if df is not None else pd.DataFrame()


def raw_hdb_rental() -> pd.DataFrame:
    """Fetch or load raw HDB rental transactions from bronze."""
    cache_id = "bronze_hdb_rental_raw"
    cache_candidates = [
        bronze_dir() / "raw_hdb_rental.parquet",
        bronze_dir() / "raw_datagov_hdb_rental.parquet",
    ]

    for cache_path in cache_candidates:
        if cache_path.exists():
            logger.info(f"Loading HDB rental data from bronze: {cache_path}")
            return pd.read_parquet(cache_path)

    def _fetch():
        url = "https://data.gov.sg/api/action/datastore_search?resource_id="
        return datagovsg.fetch_datagovsg_dataset(url, DATASET_IDS["hdb_rental"], use_cache=False)

    df = cached_call(cache_id, _fetch)
    if df is not None and not df.empty:
        bronze_dir().mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_candidates[0], index=False)
        logger.info(f"Saved {len(df)} HDB rental records to bronze")
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
        return datagovsg.fetch_datagovsg_dataset(
            url, DATASET_IDS["school_directory"], use_cache=False
        )

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
    external_dir = bronze_dir() / "external"
    result = {}

    sora_path = external_dir / "sora_rates.parquet"
    if sora_path.exists():
        result["sora"] = pd.read_parquet(sora_path)
    else:
        logger.warning("SORA data not found in bronze/external")
        result["sora"] = pd.DataFrame()

    for indicator in ["cpi", "gdp", "unemployment", "ppi"]:
        path = external_dir / f"{indicator}.parquet"
        if path.exists():
            result[indicator] = pd.read_parquet(path)
        else:
            logger.warning(f"Macro data not found: {indicator}")
            result[indicator] = pd.DataFrame()

    return result


def _mall_cache_paths() -> tuple[Path, Path]:
    """Return raw and geocoded mall bronze paths."""
    return (
        bronze_dir() / "raw_wiki_shopping_mall.parquet",
        bronze_dir() / "raw_wiki_shopping_mall_geocoded.parquet",
    )


def _standardize_geocoded_mall_columns(malls_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize geocoded mall columns to the feature-stage schema."""
    df = malls_df.copy()

    rename_map = {
        "LATITUDE": "lat",
        "LONGITUDE": "lon",
        "POSTAL": "postal_code",
        "ADDRESS": "address",
        "SEARCHVAL": "matched_name",
        "BUILDING": "building",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    for column in ["lat", "lon"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "shopping_mall" in df.columns:
        df["shopping_mall"] = df["shopping_mall"].astype(str).str.strip()
    return df


def _geocode_shopping_malls(malls_df: pd.DataFrame) -> pd.DataFrame:
    """Geocode shopping mall names using OneMap search and cache the result."""
    if malls_df.empty or "shopping_mall" not in malls_df.columns:
        return malls_df

    headers = onemap.setup_onemap_headers()
    geocoded_rows: list[dict] = []

    for mall_name in malls_df["shopping_mall"].dropna().astype(str).str.strip():
        if not mall_name:
            continue

        query_candidates = [mall_name]
        if "singapore" not in mall_name.lower():
            query_candidates.append(f"{mall_name} Singapore")

        best_match: dict | None = None
        for query in query_candidates:
            results = onemap.fetch_data_cached(query, headers=headers, timeout=30)
            if results is None or results.empty:
                continue

            first = results.iloc[0].to_dict()
            first["shopping_mall"] = mall_name
            first["search_term"] = query
            first["found"] = True
            best_match = first

            building = str(first.get("BUILDING", "")).strip().lower()
            searchval = str(first.get("SEARCHVAL", "")).strip().lower()
            if mall_name.lower() in {building, searchval}:
                break

        if best_match is None:
            geocoded_rows.append(
                {
                    "shopping_mall": mall_name,
                    "search_term": query_candidates[-1],
                    "found": False,
                    "lat": pd.NA,
                    "lon": pd.NA,
                    "matched_name": pd.NA,
                    "postal_code": pd.NA,
                    "address": pd.NA,
                    "search_result": pd.NA,
                }
            )
            logger.warning(f"Could not geocode shopping mall: {mall_name}")
        else:
            geocoded_rows.append(best_match)

    return _standardize_geocoded_mall_columns(pd.DataFrame(geocoded_rows))


def raw_shopping_malls() -> pd.DataFrame:
    """Load shopping mall data from bronze layer.

    Returns:
        DataFrame with mall locations.
    """
    raw_path, geocoded_path = _mall_cache_paths()

    if geocoded_path.exists():
        logger.info(f"Loading geocoded shopping malls from bronze: {geocoded_path}")
        return _standardize_geocoded_mall_columns(pd.read_parquet(geocoded_path))

    if raw_path.exists():
        logger.info(f"Loading shopping malls from bronze: {raw_path}")
        malls_df = pd.read_parquet(raw_path)

        has_coordinates = {"lat", "lon"}.issubset(malls_df.columns) or {
            "latitude",
            "longitude",
        }.issubset(malls_df.columns)
        if has_coordinates:
            return _standardize_geocoded_mall_columns(malls_df)

        try:
            geocoded_df = _geocode_shopping_malls(malls_df)
            if not geocoded_df.empty:
                geocoded_path.parent.mkdir(parents=True, exist_ok=True)
                geocoded_df.to_parquet(geocoded_path, index=False)
                logger.info(f"Saved {len(geocoded_df)} geocoded shopping malls to bronze")
                return geocoded_df
        except Exception as exc:
            logger.warning(f"Could not geocode shopping malls via OneMap: {exc}")

        return malls_df

    logger.warning("Shopping mall data not found in bronze layer")
    return pd.DataFrame()


def raw_mrt_stations() -> pd.DataFrame:
    """Load MRT station data from bronze/external.

    Returns:
        DataFrame with MRT station locations.
    """
    config_path = bronze_dir() / "external" / "mrt_stations.json"

    if not config_path.exists():
        logger.warning("MRT stations config not found")
        return pd.DataFrame()

    import json

    with open(config_path) as f:
        data = json.load(f)

    return pd.DataFrame(data) if data else pd.DataFrame()
