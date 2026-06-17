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

from egg_n_bacon_housing.adapters import datagovsg
from egg_n_bacon_housing.config import settings
from egg_n_bacon_housing.utils.cache import cached_call
from egg_n_bacon_housing.utils.geocoding import build_default_geocoder

logger = logging.getLogger(__name__)

DATAGOVSG_API_BASE_URL = "https://data.gov.sg/api/action/datastore_search?resource_id="


def _manual_ura_dir(bronze_dir: Path) -> Path:
    return bronze_dir.parent.parent / "manual" / "csv" / "ura"


def _load_ura_csvs(ura_dir: Path, prefix: str) -> list[pd.DataFrame]:
    dataframes: list[pd.DataFrame] = []
    for csv_path in sorted(ura_dir.glob(f"{prefix}*.csv")):
        dataframes.append(pd.read_csv(csv_path, encoding="latin1"))
    return dataframes


HDB_RESALE_RESOURCE_ID = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"


@parameterize(
    raw_rental_index={
        "resource_id": value("d_8e4c50283fb7052a391dfb746a05c853"),
        "cache_id": value("bronze_rental_index"),
        "cache_filenames": value(("raw_rental_index.parquet", "raw_datagov_rental_index.parquet")),
        "display_name": value("rental index"),
        "error_name": value("rental_index"),
    },
    raw_hdb_rental={
        "resource_id": value("d_c9f57187485a850908655db0e8cfe651"),
        "cache_id": value("bronze_hdb_rental_raw"),
        "cache_filenames": value(("raw_hdb_rental.parquet", "raw_datagov_hdb_rental.parquet")),
        "display_name": value("HDB rental"),
        "error_name": value("hdb_rental"),
    },
    raw_school_directory={
        "resource_id": value("d_688b934f82c1059ed0a6993d2a829089"),
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


def _hdb_resale_csv_dir(bronze_dir: Path) -> Path:
    return bronze_dir.parent.parent / "manual" / "csv" / "ResaleFlatPrices"


def raw_hdb_resale_transactions(bronze_dir: Path) -> pd.DataFrame:
    """Fetch HDB resale transactions from data.gov.sg API (Jan 2017+) merged with
    historical CSVs (1990–2016) for full coverage.

    The original single-resource dataset was deprecated. The replacement resource
    only covers Jan 2017 onwards, so pre-2017 data is loaded from local CSVs.
    """
    cache_paths = [bronze_dir / "raw_hdb_resale.parquet"]

    for cache_path in cache_paths:
        if cache_path.exists():
            logger.info("Loading HDB resale from bronze: %s", cache_path)
            return pd.read_parquet(cache_path)

    api_df = datagovsg.fetch_datagovsg_dataset(
        DATAGOVSG_API_BASE_URL, HDB_RESALE_RESOURCE_ID, use_cache=False
    )
    if api_df is None or api_df.empty:
        raise RuntimeError("Core dataset fetch failed: hdb_resale")

    logger.info("Fetched %s HDB resale records from API (Jan 2017+)", len(api_df))

    csv_dir = _hdb_resale_csv_dir(bronze_dir)
    historical_dfs: list[pd.DataFrame] = []
    if csv_dir.exists():
        for csv_path in sorted(csv_dir.glob("*.csv")):
            df = pd.read_csv(csv_path)
            historical_dfs.append(df)
            logger.info("Loaded %s rows from %s", len(df), csv_path.name)

    if historical_dfs:
        hist_df = pd.concat(historical_dfs, ignore_index=True)
        hist_df = hist_df[hist_df["month"] < "2017-01"]
        logger.info("Loaded %s historical HDB resale records (pre-2017)", len(hist_df))
        combined = pd.concat([hist_df, api_df], ignore_index=True)
    else:
        logger.warning("No historical HDB resale CSVs found — API data only (2017+)")
        combined = api_df

    for col in ("floor_area_sqm", "lease_commence_date", "resale_price"):
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")

    if "remaining_lease" in combined.columns:
        combined["remaining_lease"] = combined["remaining_lease"].astype(str)

    if "_id" in combined.columns:
        combined = combined.drop(columns=["_id"])

    combined = combined.sort_values("month").reset_index(drop=True)

    bronze_dir.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(cache_paths[0], index=False)
    logger.info("Saved %s HDB resale records to bronze", len(combined))
    return combined


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


CPI_RESOURCE_ID = "d_bdaff844e3ef89d39fceb962ff8f0791"
GDP_RESOURCE_ID = "d_a5ff719648a0e6d4b4c623ee383ab686"
UNEMPLOYMENT_RESOURCE_ID = "d_b0da22a41f952764376a2b7b5b0f2533"
HDB_RPI_RESOURCE_ID = "d_14f63e595975691e7c24a27ae4c07c79"
URA_PPI_RESOURCE_ID = "d_97f8a2e995022d311c6c68cfda6d034c"
SUPPLY_PIPELINE_RESOURCE_ID = "d_baa848bbdbf4af7b4d709f147fcf3c9b"


def _melt_pivot_monthly(df: pd.DataFrame, value_filter: str, value_col: str) -> pd.DataFrame:
    """Melt a data.gov.sg pivot table with monthly columns (e.g. '2026Apr') into long format."""
    label_col = "DataSeries" if "DataSeries" in df.columns else df.columns[1]
    melted = df.melt(id_vars=[label_col], var_name="period", value_name=value_col)
    melted = melted[melted[label_col].astype(str).str.strip() == value_filter]
    melted["date"] = pd.to_datetime(melted["period"], format="%Y%b", errors="coerce")
    melted[value_col] = pd.to_numeric(melted[value_col], errors="coerce")
    return (
        melted[["date", value_col]]
        .dropna(subset=["date"])
        .sort_values("date")
        .reset_index(drop=True)
    )


def _melt_pivot_quarterly(df: pd.DataFrame, value_filter: str, value_col: str) -> pd.DataFrame:
    """Melt a data.gov.sg pivot table with quarterly columns (e.g. '20261Q') into long format."""
    label_col = "DataSeries" if "DataSeries" in df.columns else df.columns[1]
    melted = df.melt(id_vars=[label_col], var_name="period", value_name=value_col)
    melted = melted[melted[label_col].astype(str).str.strip() == value_filter]
    melted[value_col] = pd.to_numeric(melted[value_col], errors="coerce")

    def _parse_quarter(p: str) -> pd.Timestamp | None:
        p = str(p)
        if len(p) >= 5 and p[-1] == "Q":
            try:
                year = int(p[:-2])
                qtr = int(p[-2])
                return pd.Timestamp(year=year, month=qtr * 3, day=1) + pd.offsets.QuarterEnd(0)
            except (ValueError, IndexError):
                return None
        if len(p) >= 6 and p[4] == "Q":
            try:
                year = int(p[:4])
                qtr = int(p[5])
                return pd.Timestamp(year=year, month=qtr * 3, day=1) + pd.offsets.QuarterEnd(0)
            except (ValueError, IndexError):
                return None
        return None

    melted["quarter"] = melted["period"].apply(_parse_quarter)
    return (
        melted[["quarter", value_col]]
        .dropna(subset=["quarter"])
        .sort_values("quarter")
        .reset_index(drop=True)
    )


def _parse_datagov_quarter(series: pd.Series) -> pd.Series:
    """Parse data.gov.sg quarter strings into quarter-end timestamps."""
    series_str = series.astype(str).str.strip()
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")

    def _quarter_end(year: int, quarter: int) -> pd.Timestamp:
        return pd.Timestamp(year=year, month=quarter * 3, day=1) + pd.offsets.QuarterEnd(0)

    for idx, quarter_text in series_str.items():
        try:
            if len(quarter_text) == 6 and quarter_text.endswith("Q"):
                parsed.at[idx] = _quarter_end(int(quarter_text[:4]), int(quarter_text[4]))
            elif len(quarter_text) == 6 and quarter_text[4] == "Q":
                parsed.at[idx] = _quarter_end(int(quarter_text[:4]), int(quarter_text[5]))
        except (ValueError, IndexError):
            continue

    return parsed


def raw_macro_data(bronze_dir: Path) -> dict[str, pd.DataFrame]:
    """Fetch and load macro economic indicators from data.gov.sg API + local SORA.

    CPI and unemployment are fetched as pivot tables and melted to long format.
    SORA is loaded from the pre-built parquet in bronze/external.

    Returns:
        Dictionary with keys: 'sora', 'cpi', 'gdp', 'unemployment'.
    """
    external_dir = bronze_dir / "external"
    external_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, pd.DataFrame] = {}

    sora_path = external_dir / "sora_rates.parquet"
    if sora_path.exists():
        result["sora"] = pd.read_parquet(sora_path)
        logger.info("Loaded SORA: %s records", len(result["sora"]))
    else:
        logger.warning("SORA data not found in bronze/external")
        result["sora"] = pd.DataFrame()

    cpi_path = external_dir / "cpi.parquet"
    if cpi_path.exists():
        result["cpi"] = pd.read_parquet(cpi_path)
    else:
        try:
            logger.info("Fetching CPI from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, CPI_RESOURCE_ID, use_cache=False
            )
            result["cpi"] = _melt_pivot_monthly(raw, "All Items", "cpi")
            result["cpi"].to_parquet(cpi_path, index=False)
            logger.info("Fetched CPI: %s records -> %s", len(result["cpi"]), cpi_path)
        except Exception as exc:
            logger.warning("Failed to fetch CPI: %s", exc)
            result["cpi"] = pd.DataFrame()

    unemployment_path = external_dir / "unemployment.parquet"
    if unemployment_path.exists():
        result["unemployment"] = pd.read_parquet(unemployment_path)
    else:
        try:
            logger.info("Fetching unemployment from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, UNEMPLOYMENT_RESOURCE_ID, use_cache=False
            )
            result["unemployment"] = _melt_pivot_quarterly(
                raw, "Total Unemployment Rate", "unemployment_rate"
            )
            result["unemployment"].to_parquet(unemployment_path, index=False)
            logger.info(
                "Fetched unemployment: %s records -> %s",
                len(result["unemployment"]),
                unemployment_path,
            )
        except Exception as exc:
            logger.warning("Failed to fetch unemployment: %s", exc)
            result["unemployment"] = pd.DataFrame()

    gdp_path = external_dir / "gdp.parquet"
    if gdp_path.exists():
        result["gdp"] = pd.read_parquet(gdp_path)
    else:
        try:
            logger.info("Fetching GDP from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, GDP_RESOURCE_ID, use_cache=False
            )
            result["gdp"] = _melt_pivot_quarterly(raw, "GDP In Chained (2015) Dollars", "gdp")
            if result["gdp"].empty:
                label_col = "DataSeries" if "DataSeries" in raw.columns else raw.columns[1]
                first_series = str(raw.iloc[0][label_col]).strip()
                result["gdp"] = _melt_pivot_quarterly(raw, first_series, "gdp")
            result["gdp"].to_parquet(gdp_path, index=False)
            logger.info("Fetched GDP: %s records -> %s", len(result["gdp"]), gdp_path)
        except Exception as exc:
            logger.warning("Failed to fetch GDP: %s", exc)
            result["gdp"] = pd.DataFrame()

    bank_rates_path = external_dir / "bank_rates.parquet"
    if bank_rates_path.exists():
        result["bank_rates"] = pd.read_parquet(bank_rates_path)
    else:
        try:
            logger.info("Fetching bank interest rates from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, BANK_RATES_RESOURCE_ID, use_cache=False
            )
            result["bank_rates"] = _melt_pivot_monthly(
                raw, "Compounded Singapore Overnight Rate Average (SORA) - 3 Month", "sora_3m"
            )
            result["bank_rates"].to_parquet(bank_rates_path, index=False)
            logger.info(
                "Fetched bank rates (SORA 3M): %s records -> %s",
                len(result["bank_rates"]),
                bank_rates_path,
            )
        except Exception as exc:
            logger.warning("Failed to fetch bank rates: %s", exc)
            result["bank_rates"] = pd.DataFrame()

    hdb_rpi_path = external_dir / "hdb_rpi.parquet"
    if hdb_rpi_path.exists():
        result["hdb_rpi"] = pd.read_parquet(hdb_rpi_path)
    else:
        try:
            logger.info("Fetching HDB Resale Price Index from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, HDB_RPI_RESOURCE_ID, use_cache=False
            )
            rpi = raw[["quarter", "index"]].copy()
            rpi["index"] = pd.to_numeric(rpi["index"], errors="coerce")
            rpi = rpi.dropna(subset=["index"])
            rpi["quarter"] = _parse_datagov_quarter(rpi["quarter"])
            rpi = rpi.dropna(subset=["quarter"]).sort_values("quarter").reset_index(drop=True)
            result["hdb_rpi"] = rpi.rename(columns={"index": "hdb_rpi"})
            result["hdb_rpi"].to_parquet(hdb_rpi_path, index=False)
            logger.info("Fetched HDB RPI: %s records -> %s", len(result["hdb_rpi"]), hdb_rpi_path)
        except Exception as exc:
            logger.warning("Failed to fetch HDB RPI: %s", exc)
            result["hdb_rpi"] = pd.DataFrame()

    ura_ppi_path = external_dir / "ura_ppi.parquet"
    if ura_ppi_path.exists():
        result["ura_ppi"] = pd.read_parquet(ura_ppi_path)
    else:
        try:
            logger.info("Fetching URA Property Price Index from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, URA_PPI_RESOURCE_ID, use_cache=False
            )
            ppi = raw[raw["property_type"].astype(str).str.strip() == "All Residential"].copy()
            ppi["index"] = pd.to_numeric(ppi["index"], errors="coerce")
            ppi = ppi.dropna(subset=["index"])
            ppi["quarter"] = _parse_datagov_quarter(ppi["quarter"])
            ppi = ppi.dropna(subset=["quarter"]).sort_values("quarter").reset_index(drop=True)
            result["ura_ppi"] = ppi[["quarter", "index"]].rename(columns={"index": "ura_ppi"})
            result["ura_ppi"].to_parquet(ura_ppi_path, index=False)
            logger.info("Fetched URA PPI: %s records -> %s", len(result["ura_ppi"]), ura_ppi_path)
        except Exception as exc:
            logger.warning("Failed to fetch URA PPI: %s", exc)
            result["ura_ppi"] = pd.DataFrame()

    supply_path = external_dir / "supply_pipeline.parquet"
    if supply_path.exists():
        result["supply_pipeline"] = pd.read_parquet(supply_path)
    else:
        try:
            logger.info("Fetching private housing supply pipeline from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, SUPPLY_PIPELINE_RESOURCE_ID, use_cache=False
            )
            supply = raw.copy()
            supply["no_of_units"] = pd.to_numeric(supply["no_of_units"], errors="coerce")
            supply["quarter"] = _parse_datagov_quarter(supply["quarter"])
            supply = supply.dropna(subset=["quarter", "no_of_units"])
            supply = supply.dropna(subset=["quarter"]).sort_values("quarter").reset_index(drop=True)
            result["supply_pipeline"] = supply
            result["supply_pipeline"].to_parquet(supply_path, index=False)
            logger.info(
                "Fetched supply pipeline: %s records -> %s",
                len(result["supply_pipeline"]),
                supply_path,
            )
        except Exception as exc:
            logger.warning("Failed to fetch supply pipeline: %s", exc)
            result["supply_pipeline"] = pd.DataFrame()

    wage_path = external_dir / "wage_growth.parquet"
    if wage_path.exists():
        result["wage_growth"] = pd.read_parquet(wage_path)
        if result["wage_growth"].empty:
            wage_path.unlink()
    if "wage_growth" not in result or result["wage_growth"].empty:
        try:
            logger.info("Fetching wage growth from data.gov.sg...")
            raw = datagovsg.fetch_datagovsg_dataset(
                DATAGOVSG_API_BASE_URL, WAGE_GROWTH_RESOURCE_ID, use_cache=False
            )
            label_col = "DataSeries" if "DataSeries" in raw.columns else raw.columns[-1]
            melted = raw.melt(id_vars=[label_col], var_name="year", value_name="wage_growth")
            melted = melted[melted[label_col].astype(str).str.strip() == "Overall Economy"]
            melted["wage_growth"] = pd.to_numeric(melted["wage_growth"], errors="coerce")
            melted["year"] = pd.to_numeric(melted["year"], errors="coerce")
            melted = melted.dropna(subset=["year", "wage_growth"])

            quarterly_rows = []
            for _, row in melted.iterrows():
                year = int(row["year"])
                for q in range(1, 5):
                    quarter_date = pd.Timestamp(
                        year=year, month=q * 3, day=1
                    ) + pd.offsets.QuarterEnd(0)
                    quarterly_rows.append(
                        {"quarter": quarter_date, "wage_growth": row["wage_growth"]}
                    )
            result["wage_growth"] = (
                pd.DataFrame(quarterly_rows).sort_values("quarter").reset_index(drop=True)
            )

            result["wage_growth"].to_parquet(wage_path, index=False)
            logger.info(
                "Fetched wage growth: %s annual records -> %s quarterly -> %s",
                len(melted),
                len(result["wage_growth"]),
                wage_path,
            )
        except Exception as exc:
            logger.warning("Failed to fetch wage growth: %s", exc)
            result["wage_growth"] = pd.DataFrame()

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
            geocoder = build_default_geocoder(settings)
            geocoded_df = _standardize_geocoded_mall_columns(
                geocoder.geocode_dataframe(malls_df, "shopping_mall")
            )
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


def _load_geojson_amenities(
    geojson_path: Path, name_props: list[str], amenity_type: str
) -> pd.DataFrame:
    """Load amenity locations from a GeoJSON file into a DataFrame.

    Handles both Point (direct coords) and Polygon (centroid) geometries.
    """
    if not geojson_path.exists():
        logger.warning("%s GeoJSON not found: %s", amenity_type, geojson_path)
        return pd.DataFrame()

    with open(geojson_path, encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    rows: list[dict] = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        geom_type = geom.get("type", "")
        coords = geom.get("coordinates", [])

        name = ""
        for prop_name in name_props:
            val = props.get(prop_name)
            if val and str(val).strip():
                name = str(val).strip()
                break

        lat, lon = None, None
        if geom_type == "Point":
            lon, lat = coords[0], coords[1]
        elif coords:
            flat = _flatten_coord(coords)
            if flat:
                lon = float(np.mean([c[0] for c in flat]))
                lat = float(np.mean([c[1] for c in flat]))

        if lat and lon:
            rows.append({"name": name, "lat": lat, "lon": lon, "amenity_type": amenity_type})

    logger.info("Loaded %s %s locations", len(rows), amenity_type)
    return pd.DataFrame(rows)


def raw_hawker_centres(bronze_dir: Path) -> pd.DataFrame:
    """Load hawker centre locations from bronze/external GeoJSON."""
    return _load_geojson_amenities(
        bronze_dir / "external" / "HawkerCentresGEOJSON.geojson", ["NAME"], "hawker"
    )


def raw_supermarkets(bronze_dir: Path) -> pd.DataFrame:
    """Load supermarket locations from bronze/external GeoJSON."""
    return _load_geojson_amenities(
        bronze_dir / "external" / "SupermarketsGEOJSON.geojson", ["Name", "LIC_NAME"], "supermarket"
    )


def raw_parks(bronze_dir: Path) -> pd.DataFrame:
    """Load park and nature reserve locations from bronze/external GeoJSON."""
    return _load_geojson_amenities(
        bronze_dir / "external" / "NParksParksandNatureReserves.geojson", ["NAME"], "park"
    )


def raw_childcare(bronze_dir: Path) -> pd.DataFrame:
    """Load childcare centre locations from bronze/external GeoJSON."""
    return _load_geojson_amenities(
        bronze_dir / "external" / "ChildCareServices.geojson", ["NAME"], "childcare"
    )


def raw_kindergartens(bronze_dir: Path) -> pd.DataFrame:
    """Load preschool/kindergarten locations from bronze/external GeoJSON.

    Uses PreSchoolsLocation.geojson (2,290 features with Point geometry)
    — Kindergartens.geojson only contains incidental charges, no coordinates.
    """
    return _load_geojson_amenities(
        bronze_dir / "external" / "PreSchoolsLocation.geojson",
        ["Name"],
        "kindergarten",
    )


# ---------------------------------------------------------------------------
# New data sources — June 2026 expansion
# ---------------------------------------------------------------------------

HDB_PROPERTY_INFO_RESOURCE_ID = "d_17f5382f26140b1fdae0ba2ef6239d2f"
BANK_RATES_RESOURCE_ID = "d_5fe5a4bb4a1ecc4d8a56a095832e2b24"
INCOME_BY_PLANNING_AREA_RESOURCE_ID = "d_bb771c5189ce18007621533dd36142bb"


def raw_hdb_property_info(bronze_dir: Path) -> pd.DataFrame:
    """Fetch HDB Property Information from data.gov.sg (13K+ blocks).

    Contains block-level metadata for every HDB block: max floor, year completed,
    total dwelling units, flat type breakdown, mixed-use flags.
    """
    cache_path = bronze_dir / "raw_hdb_property_info.parquet"
    if cache_path.exists():
        logger.info("Loading HDB property info from bronze: %s", cache_path)
        return pd.read_parquet(cache_path)

    df = datagovsg.fetch_datagovsg_dataset(
        DATAGOVSG_API_BASE_URL, HDB_PROPERTY_INFO_RESOURCE_ID, use_cache=False
    )
    if df is None or df.empty:
        logger.warning("HDB Property Information fetch failed — returning empty")
        return pd.DataFrame()

    bronze_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    logger.info("Saved %s HDB property info records to bronze", len(df))
    return df


def _income_bracket_midpoints() -> list[tuple[str, float]]:
    """Return (column_name, midpoint) for income brackets."""
    return [
        ("Below_1_000", 500),
        ("1_000_1_499", 1250),
        ("1_500_1_999", 1750),
        ("2_000_2_499", 2250),
        ("2_500_2_999", 2750),
        ("3_000_3_999", 3500),
        ("4_000_4_999", 4500),
        ("5_000_5_999", 5500),
        ("6_000_6_999", 6500),
        ("7_000_7_999", 7500),
        ("8_000_8_999", 8500),
        ("9_000_9_999", 9500),
        ("10_000_10_999", 10500),
        ("11_000_11_999", 11500),
        ("12_000andOver", 15000),
    ]


def raw_income_by_planning_area(bronze_dir: Path) -> pd.DataFrame:
    """Fetch resident working persons income distribution by planning area.

    Source: General Household Survey 2015 (SingStat).
    Returns one row per planning area with median_monthly_income computed
    from income bracket distributions.
    """
    cache_path = bronze_dir / "raw_income_by_planning_area.parquet"
    if cache_path.exists():
        logger.info("Loading income by planning area from bronze: %s", cache_path)
        return pd.read_parquet(cache_path)

    raw = datagovsg.fetch_datagovsg_dataset(
        DATAGOVSG_API_BASE_URL, INCOME_BY_PLANNING_AREA_RESOURCE_ID, use_cache=False
    )
    if raw is None or raw.empty:
        logger.warning("Income by planning area fetch failed — returning empty")
        return pd.DataFrame()

    df = raw[raw["Thousands"].astype(str).str.strip() != "Total"].copy()
    df = df.rename(columns={"Thousands": "planning_area"})

    brackets = _income_bracket_midpoints()
    for col, _ in brackets:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    def _weighted_median(row: pd.Series) -> float:
        total = 0.0
        cumulative = 0.0
        weights = []
        midpoints = []
        for col, mid in brackets:
            if col in row.index and pd.notna(row[col]):
                w = float(row[col])
                total += w
                weights.append(w)
                midpoints.append(mid)
        if total == 0 or not weights:
            return pd.NA
        half = total / 2
        for w, mid in zip(weights, midpoints, strict=True):
            cumulative += w
            if cumulative >= half:
                return mid
        return midpoints[-1]

    df["median_monthly_income"] = df.apply(_weighted_median, axis=1)
    df["planning_area"] = df["planning_area"].astype(str).str.strip()

    bronze_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    logger.info("Saved %s planning area income records to bronze", len(df))
    return df


def raw_bus_stops(bronze_dir: Path) -> pd.DataFrame:
    """Load bus stop locations from bronze/external GeoJSON.

    Requires manual download from data.gov.sg (LTA Bus Stop dataset).
    The GEOJSON format is not accessible via datastore_search API.
    """
    return _load_geojson_amenities(
        bronze_dir / "external" / "BusStops.geojson",
        ["BUS_STOP_NUM", "BUS_ROOF_NUM", "Name"],
        "bus_stop",
    )


GREEN_MARK_BUILDINGS_RESOURCE_ID = "d_c4bd082b48fa7611713f39e23d250c27"


def raw_green_mark_buildings(bronze_dir: Path) -> pd.DataFrame:
    """Fetch BCA Green Mark certified buildings from data.gov.sg (CSV).

    ~4,800 buildings with postal codes, ratings (Platinum/Gold/etc),
    and project types. Geocoding happens in the features layer.
    """
    cache_path = bronze_dir / "raw_green_mark_buildings.parquet"
    if cache_path.exists():
        logger.info("Loading green mark buildings from bronze: %s", cache_path)
        return pd.read_parquet(cache_path)

    df = datagovsg.fetch_datagovsg_dataset(
        DATAGOVSG_API_BASE_URL, GREEN_MARK_BUILDINGS_RESOURCE_ID, use_cache=False
    )
    if df is None or df.empty:
        logger.warning("Green Mark Buildings fetch failed — returning empty")
        return pd.DataFrame()

    df = df[df["Postal_Code"].notna() & df["Postal_Code"].astype(str).str.strip().ne("")].copy()
    df["postal_code"] = df["Postal_Code"].astype(str).str.strip()

    bronze_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    logger.info("Saved %s green mark buildings to bronze", len(df))
    return df


def geocoded_green_mark_buildings(
    bronze_dir: Path,
    raw_green_mark_buildings: pd.DataFrame,
) -> pd.DataFrame:
    """Geocode Green Mark buildings via OneMap, cache as bronze parquet.

    Extracts unique postal codes from the raw Green Mark dataset and geocodes
    each one through OneMap's search API. Results are cached as bronze parquet
    so this expensive (~11 min, ~4K calls) operation runs only once.
    """
    cache_path = bronze_dir / "raw_green_mark_buildings_geocoded.parquet"
    if cache_path.exists():
        logger.info("Loading geocoded green mark buildings from bronze: %s", cache_path)
        return pd.read_parquet(cache_path)

    df = raw_green_mark_buildings
    if df.empty or "postal_code" not in df.columns:
        logger.warning("Green Mark buildings empty or missing postal_code — returning as-is")
        return df

    logger.info("Geocoding %s unique Green Mark postal codes...", df["postal_code"].nunique())
    geocoder = build_default_geocoder(settings)
    geocoded = geocoder.geocode(df["postal_code"].drop_duplicates())
    coord_map = dict(zip(geocoded["input"], zip(geocoded["lat"], geocoded["lon"]), strict=False))

    df = df.copy()
    df["lat"] = df["postal_code"].map(lambda pc: coord_map.get(str(pc), (None, None))[0])
    df["lon"] = df["postal_code"].map(lambda pc: coord_map.get(str(pc), (None, None))[1])
    df["name"] = df.get("Project_Name", df["postal_code"])

    bronze_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    logger.info(
        "Geocoded Green Mark buildings: %s/%s saved to %s",
        df["lat"].notna().sum(),
        len(df),
        cache_path,
    )
    return df


def raw_chas_clinics(bronze_dir: Path) -> pd.DataFrame:
    """Load CHAS clinic locations from bronze/external GeoJSON.

    Community Health Assist Scheme clinics — subsidised primary care.
    Requires manual download from data.gov.sg.
    """
    return _load_geojson_amenities(
        bronze_dir / "external" / "CHASClinics.geojson",
        ["Name", "NAME", "HCI_NAME"],
        "chas_clinic",
    )


def raw_sports_facilities(bronze_dir: Path) -> pd.DataFrame:
    """Load SportSG facility locations from bronze/external GeoJSON.

    Includes stadiums, swimming pools, sports halls, gyms.
    Requires manual download from data.gov.sg.
    """
    return _load_geojson_amenities(
        bronze_dir / "external" / "SportSGFacilities.geojson",
        ["Name", "NAME"],
        "sports_facility",
    )


def raw_community_clubs(bronze_dir: Path) -> pd.DataFrame:
    """Load Community Club locations from bronze/external GeoJSON.

    PA Community Clubs / Centres across Singapore.
    Requires manual download from data.gov.sg.
    """
    return _load_geojson_amenities(
        bronze_dir / "external" / "CommunityClubs.geojson",
        ["Name", "NAME", "CC_NAME"],
        "community_club",
    )


# ---------------------------------------------------------------------------
# New data sources — Round 3 expansion
# ---------------------------------------------------------------------------

DWELLING_UNITS_RESOURCE_ID = "d_07b1eeeb22efdf7faf5bd6a13667359d"
MEDIAN_ANNUAL_VALUE_RESOURCE_ID = "d_48143be392f1ed22f0700835212e5a60"
HDB_RESIDENT_POPULATION_RESOURCE_ID = "d_0a6c6d71f6fa14e2d27e406f1d018439"
WAGE_GROWTH_RESOURCE_ID = "d_64f98475cef1e94300362cb400a50012"


def raw_dwelling_units_by_town(bronze_dir: Path) -> pd.DataFrame:
    """Fetch dwelling units under HDB management by town and flat type.

    Provides town-level housing supply composition — total dwelling units
    broken down by flat type (1-room through executive/multi-generation).
    """
    cache_path = bronze_dir / "raw_dwelling_units_by_town.parquet"
    if cache_path.exists():
        logger.info("Loading dwelling units by town from bronze: %s", cache_path)
        return pd.read_parquet(cache_path)

    df = datagovsg.fetch_datagovsg_dataset(
        DATAGOVSG_API_BASE_URL, DWELLING_UNITS_RESOURCE_ID, use_cache=False
    )
    if df is None or df.empty:
        logger.warning("Dwelling units by town fetch failed — returning empty")
        return pd.DataFrame()

    bronze_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    logger.info("Saved %s dwelling units by town records to bronze", len(df))
    return df


def raw_median_annual_value(bronze_dir: Path) -> pd.DataFrame:
    """Fetch median annual value and property tax by HDB flat type from IRAS.

    Provides official government tax assessment values per HDB room type,
    useful as a proxy for government-estimated property worth.
    """
    cache_path = bronze_dir / "raw_median_annual_value.parquet"
    if cache_path.exists():
        logger.info("Loading median annual value from bronze: %s", cache_path)
        return pd.read_parquet(cache_path)

    df = datagovsg.fetch_datagovsg_dataset(
        DATAGOVSG_API_BASE_URL, MEDIAN_ANNUAL_VALUE_RESOURCE_ID, use_cache=False
    )
    if df is None or df.empty:
        logger.warning("Median annual value fetch failed — returning empty")
        return pd.DataFrame()

    bronze_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    logger.info("Saved %s median annual value records to bronze", len(df))
    return df


def raw_hdb_resident_population(bronze_dir: Path) -> pd.DataFrame:
    """Fetch HDB resident population by geographical distribution (town/estate).

    Provides population counts per town — enables population density features
    when combined with dwelling unit counts.
    """
    cache_path = bronze_dir / "raw_hdb_resident_population.parquet"
    if cache_path.exists():
        logger.info("Loading HDB resident population from bronze: %s", cache_path)
        return pd.read_parquet(cache_path)

    df = datagovsg.fetch_datagovsg_dataset(
        DATAGOVSG_API_BASE_URL, HDB_RESIDENT_POPULATION_RESOURCE_ID, use_cache=False
    )
    if df is None or df.empty:
        logger.warning("HDB resident population fetch failed — returning empty")
        return pd.DataFrame()

    bronze_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache_path, index=False)
    logger.info("Saved %s HDB resident population records to bronze", len(df))
    return df
