"""01_ingestion: Bronze layer data collection (Hamilton DAG node).

This module provides Hamilton-compatible functions for fetching raw data
from data.gov.sg and other external sources into the bronze layer.

Functions here are "pure" in the Hamilton sense: output depends only on
inputs + config, no global state.
"""

import json
import logging
from pathlib import Path

import pandas as pd
import requests
from hamilton.function_modifiers import parameterize, value

from egg_n_bacon_housing.adapters import datagovsg, onemap
from egg_n_bacon_housing.utils.cache import cached_call

logger = logging.getLogger(__name__)

DATAGOVSG_API_BASE_URL = "https://data.gov.sg/api/action/datastore_search?resource_id="


@parameterize(
    raw_hdb_resale_transactions={
        "resource_id": value("d_5785799d63a9da091f4e0b456291eeb8"),
        "cache_id": value("bronze_hdb_resale_raw"),
        "cache_filenames": value(("raw_hdb_resale.parquet",)),
        "display_name": value("HDB resale"),
        "error_name": value("hdb_resale"),
    },
    raw_condo_transactions={
        "resource_id": value("d_2fd959a62c2d04c67a5a7c7538c53ddd"),
        "cache_id": value("bronze_condo_raw"),
        "cache_filenames": value(("raw_condo_transactions.parquet",)),
        "display_name": value("condo"),
        "error_name": value("condo_resale"),
    },
    raw_rental_index={
        "resource_id": value("d_e03d53203e43c32df38b5123c9e1d2a4"),
        "cache_id": value("bronze_rental_index"),
        "cache_filenames": value(("raw_rental_index.parquet", "raw_datagov_rental_index.parquet")),
        "display_name": value("rental index"),
        "error_name": value("rental_index"),
    },
    raw_hdb_rental={
        "resource_id": value("d_8b84f0dfe7acb6d6585a7d7e6e406b31"),
        "cache_id": value("bronze_hdb_rental_raw"),
        "cache_filenames": value(("raw_hdb_rental.parquet", "raw_datagov_hdb_rental.parquet")),
        "display_name": value("HDB rental"),
        "error_name": value("hdb_rental"),
    },
    raw_school_directory={
        "resource_id": value("d_69d6a3ed8b3b1e19aa2e0d868b0f2c7"),
        "cache_id": value("bronze_school_directory"),
        "cache_filenames": value(("raw_school_directory.parquet",)),
        "display_name": value("school"),
        "error_name": value("school_directory"),
    },
)
def raw_dataset(
    bronze_dir: Path,
    resource_id: str,
    cache_id: str,
    cache_filenames: tuple[str, ...],
    display_name: str,
    error_name: str,
) -> pd.DataFrame:
    cache_paths = [bronze_dir / f for f in cache_filenames]

    for cache_path in cache_paths:
        if cache_path.exists():
            logger.info("Loading %s from bronze: %s", display_name, cache_path)
            return pd.read_parquet(cache_path)

    def _fetch():
        return datagovsg.fetch_datagovsg_dataset(
            DATAGOVSG_API_BASE_URL, resource_id, use_cache=False
        )

    df = cached_call(cache_id, _fetch)
    if df is not None and not df.empty:
        bronze_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_paths[0], index=False)
        logger.info("Saved %s %s records to bronze", len(df), display_name)
    if df is None or df.empty:
        raise RuntimeError(f"Core dataset fetch failed: {error_name}")
    return df


def raw_macro_data(bronze_dir: Path) -> dict[str, pd.DataFrame]:
    """Load macro economic data from bronze layer.

    Returns:
        Dictionary with keys: 'sora', 'cpi', 'gdp', 'unemployment', 'ppi'.
    """
    external_dir = bronze_dir / "external"
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
            logger.warning("Macro data not found: %s", indicator)
            result[indicator] = pd.DataFrame()

    return result


def _mall_cache_paths(bronze_dir: Path) -> tuple[Path, Path]:
    """Return raw and geocoded mall bronze paths."""
    return (
        bronze_dir / "raw_wiki_shopping_mall.parquet",
        bronze_dir / "raw_wiki_shopping_mall_geocoded.parquet",
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
            logger.warning("Could not geocode shopping mall: %s", mall_name)
        else:
            geocoded_rows.append(best_match)

    return _standardize_geocoded_mall_columns(pd.DataFrame(geocoded_rows))


def raw_shopping_malls(bronze_dir: Path) -> pd.DataFrame:
    """Load shopping mall data from bronze layer.

    Returns:
        DataFrame with mall locations.
    """
    raw_path, geocoded_path = _mall_cache_paths(bronze_dir)

    if geocoded_path.exists():
        logger.info("Loading geocoded shopping malls from bronze: %s", geocoded_path)
        return _standardize_geocoded_mall_columns(pd.read_parquet(geocoded_path))

    if raw_path.exists():
        logger.info("Loading shopping malls from bronze: %s", raw_path)
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
                logger.info("Saved %s geocoded shopping malls to bronze", len(geocoded_df))
                return geocoded_df
        except (requests.RequestException, OSError, ValueError, KeyError) as exc:
            logger.warning("Could not geocode shopping malls via OneMap: %s", exc)

        return malls_df

    logger.warning(
        "Shopping mall data not found in bronze layer — "
        "downstream mall proximity features (dist_to_nearest_mall, nearest_mall) "
        "will be empty for all records"
    )
    return pd.DataFrame()


def raw_mrt_stations(bronze_dir: Path) -> pd.DataFrame:
    """Load MRT station data from bronze/external.

    Returns:
        DataFrame with MRT station locations.
    """
    config_path = bronze_dir / "external" / "mrt_stations.json"

    if not config_path.exists():
        logger.warning("MRT stations config not found")
        return pd.DataFrame()

    with open(config_path) as f:
        data = json.load(f)

    return pd.DataFrame(data) if data else pd.DataFrame()
