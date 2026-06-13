"""01_ingestion: Bronze layer data collection (Hamilton DAG node).

This module provides Hamilton-compatible functions for fetching raw data
from data.gov.sg and other external sources into the bronze layer.

Functions here are "pure" in the Hamilton sense: output depends only on
inputs + config, no global state.
"""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from hamilton.function_modifiers import parameterize, value

from egg_n_bacon_housing.adapters import datagovsg, onemap
from egg_n_bacon_housing.utils.cache import cached_call

logger = logging.getLogger(__name__)

DATAGOVSG_API_BASE_URL = "https://data.gov.sg/api/action/datastore_search?resource_id="


def _manual_ura_dir(bronze_dir: Path) -> Path:
    return bronze_dir.parent.parent / "manual" / "csv" / "ura"


def _load_ura_csvs(ura_dir: Path, prefix: str) -> list[pd.DataFrame]:
    dataframes: list[pd.DataFrame] = []
    for csv_path in sorted(ura_dir.glob(f"{prefix}*.csv")):
        dataframes.append(pd.read_csv(csv_path, encoding="latin1"))
    return dataframes


@parameterize(
    raw_hdb_resale_transactions={
        "resource_id": value("d_5785799d63a9da091f4e0b456291eeb8"),
        "cache_id": value("bronze_hdb_resale_raw"),
        "cache_filenames": value(("raw_hdb_resale.parquet",)),
        "display_name": value("HDB resale"),
        "error_name": value("hdb_resale"),
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
        "cache_filenames": value(
            ("raw_school_directory.parquet", "raw_datagov_school_directory.parquet")
        ),
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
            df[column] = df[column].apply(
                lambda x: float(x) if pd.notna(x) and not isinstance(x, type(pd.NA)) else pd.NA
            )
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
            if results is None:
                continue
            if isinstance(results, pd.DataFrame):
                if results.empty:
                    continue
            else:
                continue

            first = results.iloc[0].to_dict()
            building = str(first.get("BUILDING", "")).strip().lower()
            searchval = str(first.get("SEARCHVAL", "")).strip().lower()
            best_match = {
                "shopping_mall": mall_name,
                "search_term": query,
                "found": True,
                "lat": first.get("LATITUDE") or first.get("Y"),
                "lon": first.get("LONGITUDE") or first.get("X"),
                "matched_name": first.get("SEARCHVAL") or first.get("BUILDING"),
                "postal_code": first.get("POSTAL"),
                "address": first.get("ADDRESS"),
                "search_result": first.get("search_result"),
            }
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


def _load_mrt_geojson(geojson_path: Path) -> pd.DataFrame:
    """Load MRT station centroids from GeoJSON."""
    with open(geojson_path) as f:
        data = json.load(f)

    rows = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        name = props.get("NAME", "")
        geom_type = geom.get("type", "")
        coords = geom.get("coordinates", [])

        lat, lon = None, None
        if geom_type == "Point":
            lon, lat = coords[0], coords[1]
        elif coords:
            flat = _flatten_coord(coords)
            if flat:
                lons = [c[0] for c in flat]
                lats = [c[1] for c in flat]
                lon = float(np.mean(lons))
                lat = float(np.mean(lats))

        if name and lat and lon:
            rows.append({"name": name, "lat": lat, "lon": lon})

    return pd.DataFrame(rows)


def _flatten_coord(coords: list) -> list[list[float]]:
    """Recursively flatten nested coordinate lists into [lon, lat] pairs."""
    if not coords:
        return []
    if isinstance(coords[0], int | float):
        return [coords[:2]]
    result = []
    for item in coords:
        result.extend(_flatten_coord(item))
    return result


def raw_mrt_stations(bronze_dir: Path) -> pd.DataFrame:
    """Load MRT station data from bronze/external.

    Merges station-line mapping (mrt_stations.json) with GeoJSON coordinates.

    Returns:
        DataFrame with MRT station locations (name, lat, lon, line).
    """
    lines_path = bronze_dir / "external" / "mrt_stations.json"
    geojson_path = bronze_dir / "external" / "MRTStations.geojson"

    # Load line mapping
    lines_df = pd.DataFrame()
    if lines_path.exists():
        with open(lines_path) as f:
            data = json.load(f)
        if isinstance(data, dict):
            rows = []
            for station_name, lines in data.items():
                if isinstance(lines, list):
                    for line in lines:
                        rows.append({"name": station_name, "line": line})
                else:
                    rows.append({"name": station_name, "line": lines})
            lines_df = pd.DataFrame(rows)
        elif isinstance(data, list):
            lines_df = pd.DataFrame(data)

    # Load GeoJSON coordinates
    geo_df = pd.DataFrame()
    if geojson_path.exists():
        geo_df = _load_mrt_geojson(geojson_path)

    if geo_df.empty and lines_df.empty:
        logger.warning("No MRT station data found")
        return pd.DataFrame()

    if geo_df.empty:
        logger.warning("MRT GeoJSON not found — proximity features will be missing lat/lon")
        return lines_df

    if lines_df.empty:
        logger.info("Loaded %s MRT stations from GeoJSON (no line data)", len(geo_df))
        return geo_df

    # Normalize station names for matching
    geo_df["_key"] = geo_df["name"].str.upper().str.strip()
    lines_df["_key"] = lines_df["name"].str.upper().str.strip()

    merged = geo_df.merge(lines_df[["_key", "line"]], on="_key", how="left")
    merged = merged.drop(columns=["_key"])

    # Deduplicate — one row per station (keep first line if multiple)
    merged = merged.drop_duplicates(subset=["name"], keep="first")
    logger.info("Loaded %s MRT stations with coordinates", len(merged))
    return merged
