"""datagov.sg API fetch nodes for bronze layer.

Hamilton DAG nodes that fetch datasets from data.gov.sg into bronze parquet,
plus geocoding post-processing nodes for malls and green mark buildings.
"""

import logging
from pathlib import Path

import pandas as pd
import requests
from hamilton.function_modifiers import parameterize, value

from egg_n_bacon_housing.adapters import datagovsg
from egg_n_bacon_housing.utils.cache import cached_call
from egg_n_bacon_housing.utils.geocoding import Geocoder

logger = logging.getLogger(__name__)

DATAGOVSG_API_BASE_URL = "https://data.gov.sg/api/action/datastore_search?resource_id="

__all__ = [
    "raw_dataset",
    "raw_hdb_resale_transactions",
    "raw_hdb_property_info",
    "raw_income_by_planning_area",
    "raw_green_mark_buildings",
    "geocoded_green_mark_buildings",
    "raw_dwelling_units_by_town",
    "raw_median_annual_value",
    "raw_hdb_resident_population",
    "raw_shopping_malls",
]

HDB_RESALE_RESOURCE_ID = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"

HDB_PROPERTY_INFO_RESOURCE_ID = "d_17f5382f26140b1fdae0ba2ef6239d2f"
INCOME_BY_PLANNING_AREA_RESOURCE_ID = "d_bb771c5189ce18007621533dd36142bb"
GREEN_MARK_BUILDINGS_RESOURCE_ID = "d_c4bd082b48fa7611713f39e23d250c27"
DWELLING_UNITS_RESOURCE_ID = "d_07b1eeeb22efdf7faf5bd6a13667359d"
MEDIAN_ANNUAL_VALUE_RESOURCE_ID = "d_48143be392f1ed22f0700835212e5a60"
HDB_RESIDENT_POPULATION_RESOURCE_ID = "d_0a6c6d71f6fa14e2d27e406f1d018439"


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


def raw_hdb_property_info(bronze_dir: Path) -> pd.DataFrame:
    """Fetch HDB Property Information from data.gov.sg (13K+ blocks)."""
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
    """Fetch resident working persons income distribution by planning area."""
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


def raw_green_mark_buildings(bronze_dir: Path) -> pd.DataFrame:
    """Fetch BCA Green Mark certified buildings from data.gov.sg (CSV)."""
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
    geocoder: Geocoder,
) -> pd.DataFrame:
    """Geocode Green Mark buildings via OneMap, cache as bronze parquet."""
    cache_path = bronze_dir / "raw_green_mark_buildings_geocoded.parquet"
    if cache_path.exists():
        logger.info("Loading geocoded green mark buildings from bronze: %s", cache_path)
        return pd.read_parquet(cache_path)

    df = raw_green_mark_buildings
    if df.empty or "postal_code" not in df.columns:
        logger.warning("Green Mark buildings empty or missing postal_code — returning as-is")
        return df

    logger.info("Geocoding %s unique Green Mark postal codes...", df["postal_code"].nunique())
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


def raw_dwelling_units_by_town(bronze_dir: Path) -> pd.DataFrame:
    """Fetch dwelling units under HDB management by town and flat type."""
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
    """Fetch median annual value and property tax by HDB flat type from IRAS."""
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
    """Fetch HDB resident population by geographical distribution (town/estate)."""
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


def raw_shopping_malls(bronze_dir: Path, geocoder: Geocoder) -> pd.DataFrame:
    """Load shopping mall data from bronze layer."""
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
