"""datagov.sg API fetch nodes for bronze layer.

Hamilton DAG nodes that fetch datasets from data.gov.sg into bronze parquet,
plus geocoding post-processing nodes for malls and green mark buildings.

The income-by-planning-area transform computes grouped-data medians with
linear interpolation inside the median bracket (not bracket midpoints).
The open top bracket ("12_000andOver") has no upper bound; its width is
assumed to equal the previous bracket's width (i.e. treated as
[12_000, 13_000) SGD), and the transform logs how many planning areas
relied on that assumption.
"""

import logging
from collections.abc import Callable
from pathlib import Path

import pandas as pd
import requests
from hamilton.function_modifiers import parameterize, value
from shapely.geometry import shape

from egg_n_bacon_housing.adapters import datagovsg
from egg_n_bacon_housing.adapters.exceptions import DatasetFetchError
from egg_n_bacon_housing.utils.bronze import (
    STALE_WARN_DAYS,
    read_bronze_cache,
    warn_if_stale,
    write_bronze_cache,
)
from egg_n_bacon_housing.utils.geocoding import Geocoder

logger = logging.getLogger(__name__)

# Request prefix built from the adapter's canonical base URL so the endpoint
# is single-sourced (components/ingestion/geojson.py builds the same prefix
# for the station-codes dataset).
DATAGOVSG_API_BASE_URL = f"{datagovsg.DATAGOVSG_BASE_URL}?resource_id="

# NOTE: raw_rental_index, raw_hdb_rental, and raw_school_directory are produced
# by @parameterize on raw_dataset below. They are Hamilton DAG node *names*
# (graph metadata), not module attributes -- the decorated object keeps the
# name raw_dataset. Hamilton discovers them by introspecting this module, so
# they are intentionally omitted from __all__ (adding them would break
# `from ...datagov import *` with AttributeError and aid nothing).
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


def _load_or_fetch_dataset(
    bronze_dir: Path,
    *,
    key: str,
    resource_id: str,
    display_name: str,
    cache_filenames: tuple[str, ...] | None = None,
    transform: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
    required: bool = False,
) -> pd.DataFrame:
    """Bronze-cache-first load of one data.gov.sg dataset.

    Bronze is the only cache layer: the adapter is called with
    ``use_cache=False`` so ``--refresh`` (which clears bronze but not the
    API-response cache) genuinely re-fetches instead of re-serving a
    24h-stale API payload under a fresh manifest timestamp. Empty (0-row)
    bronze caches are treated as misses (warn + refetch), mirroring the
    macro empty-guard contract.

    Args:
        bronze_dir: Bronze layer directory for parquet caches.
        key: Node/error key (also default cache filename stem).
        resource_id: data.gov.sg dataset ID.
        display_name: Human-readable name for logs.
        cache_filenames: Candidate bronze filenames, legacy names first.
            Defaults to ``(f"raw_{key}.parquet",)``; the first entry is
            where fresh fetches are written.
        transform: Optional pure post-fetch reshape.
        required: If True, an empty fetch raises RuntimeError (core
            datasets) instead of degrading to an empty frame.
    """
    filenames = cache_filenames if cache_filenames is not None else (f"raw_{key}.parquet",)

    for name in filenames:
        cached = read_bronze_cache(bronze_dir, name)
        if cached is None:
            continue
        if cached.empty:
            # An empty cache file must never be treated as valid data -- it
            # would silently poison the node with 0 rows on every subsequent
            # run (same contract as the macro loaders).
            logger.warning("Ignoring empty bronze cache: %s", bronze_dir / name)
            continue
        logger.info("Loading %s from bronze: %s", display_name, bronze_dir / name)
        return cached

    df = datagovsg.fetch_datagovsg_dataset(DATAGOVSG_API_BASE_URL, resource_id, use_cache=False)
    if df is None or df.empty:
        if required:
            raise RuntimeError(f"Core dataset fetch failed: {key}")
        logger.warning("%s fetch failed — returning empty", display_name)
        return pd.DataFrame()

    if transform is not None:
        df = transform(df)

    write_bronze_cache(bronze_dir, df, filenames[0].removesuffix(".parquet"), "datagov_api")
    logger.info("Saved %s %s records to bronze", len(df), display_name)
    return df


@parameterize(
    raw_rental_index={
        "resource_id": value("d_8e4c50283fb7052a391dfb746a05c853"),
        "cache_filenames": value(("raw_rental_index.parquet", "raw_datagov_rental_index.parquet")),
        "display_name": value("rental index"),
        "error_name": value("rental_index"),
    },
    raw_hdb_rental={
        "resource_id": value("d_c9f57187485a850908655db0e8cfe651"),
        "cache_filenames": value(("raw_hdb_rental.parquet", "raw_datagov_hdb_rental.parquet")),
        "display_name": value("HDB rental"),
        "error_name": value("hdb_rental"),
    },
    raw_school_directory={
        "resource_id": value("d_688b934f82c1059ed0a6993d2a829089"),
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
    cache_filenames: tuple[str, ...],
    display_name: str,
    error_name: str,
) -> pd.DataFrame:
    """Fetch a core dataset (rental index, HDB rental, schools); hard-fails if empty."""
    return _load_or_fetch_dataset(
        bronze_dir,
        key=error_name,
        resource_id=resource_id,
        display_name=display_name,
        cache_filenames=cache_filenames,
        required=True,
    )


def raw_hdb_resale_transactions(bronze_dir: Path, manual_dir: Path) -> pd.DataFrame:
    """Fetch HDB resale transactions from data.gov.sg API (Jan 2017+) merged with
    historical CSVs (1990–2016, looked up under ``manual_dir``) for full coverage.
    """
    cached = read_bronze_cache(bronze_dir, "raw_hdb_resale")
    if cached is not None:
        if cached.empty:
            # Empty bronze cache is a miss, not data (macro empty-guard contract).
            logger.warning("Ignoring empty bronze cache: %s", bronze_dir / "raw_hdb_resale.parquet")
        else:
            logger.info("Loading HDB resale from bronze: %s", bronze_dir / "raw_hdb_resale.parquet")
            warn_if_stale(bronze_dir, "raw_hdb_resale", STALE_WARN_DAYS["raw_hdb_resale"])
            return cached

    api_df = datagovsg.fetch_datagovsg_dataset(
        DATAGOVSG_API_BASE_URL, HDB_RESALE_RESOURCE_ID, use_cache=False
    )
    if api_df is None or api_df.empty:
        raise RuntimeError("Core dataset fetch failed: hdb_resale")

    logger.info("Fetched %s HDB resale records from API (Jan 2017+)", len(api_df))

    csv_dir = manual_dir / "csv" / "ResaleFlatPrices"
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

    resale_source = "datagov_api+manual_csv" if historical_dfs else "datagov_api"
    write_bronze_cache(bronze_dir, combined, "raw_hdb_resale", resale_source)
    logger.info("Saved %s HDB resale records to bronze", len(combined))
    return combined


def raw_hdb_property_info(bronze_dir: Path) -> pd.DataFrame:
    """Fetch HDB Property Information from data.gov.sg (13K+ blocks)."""
    return _load_or_fetch_dataset(
        bronze_dir,
        key="hdb_property_info",
        resource_id=HDB_PROPERTY_INFO_RESOURCE_ID,
        display_name="HDB property info",
    )


# Income bracket bounds (SGD/month) for data.gov.sg resource
# d_bb771c5189ce18007621533dd36142bb (resident working persons by planning
# area and monthly household income; Census 2020 vintage). Column names
# verified against the live dataset 2026-09-04. Bounds are derived from the
# bracket column names themselves (e.g. "1_000_1_499" -> [1000, 1500)); the
# list MUST stay sorted by lower bound. The final bracket has no upper bound
# ("12_000andOver"); see _transform_income_by_planning_area for the width
# convention applied to it.
_INCOME_BRACKETS: tuple[tuple[str, float, float | None], ...] = (
    ("Below_1_000", 0.0, 1000.0),
    ("1_000_1_499", 1000.0, 1500.0),
    ("1_500_1_999", 1500.0, 2000.0),
    ("2_000_2_499", 2000.0, 2500.0),
    ("2_500_2_999", 2500.0, 3000.0),
    ("3_000_3_999", 3000.0, 4000.0),
    ("4_000_4_999", 4000.0, 5000.0),
    ("5_000_5_999", 5000.0, 6000.0),
    ("6_000_6_999", 6000.0, 7000.0),
    ("7_000_7_999", 7000.0, 8000.0),
    ("8_000_8_999", 8000.0, 9000.0),
    ("9_000_9_999", 9000.0, 10000.0),
    ("10_000_10_999", 10000.0, 11000.0),
    ("11_000_11_999", 11000.0, 12000.0),
    ("12_000andOver", 12000.0, None),
)

# Documented convention for the open top bracket: since "12_000andOver" has
# no upper bound, it is assigned the PREVIOUS bracket's width (half that
# width above its lower bound, i.e. 12_500, plays the role the old 15_000
# midpoint did). Any within-bracket position is an assumption; this one is
# anchored to the neighbouring bracket, and the logger.info count in the
# transform is the bias tripwire quantifying how many planning areas rest
# on it.
_OPEN_BRACKET_ASSUMED_WIDTH: float = 1000.0


def _transform_income_by_planning_area(raw: pd.DataFrame) -> pd.DataFrame:
    """Compute grouped-median income per planning area from bracket counts.

    Standard grouped-data median: brackets are ordered by lower bound, the
    50%-of-total weight position is located, and the value is linearly
    interpolated WITHIN the median bracket as
    ``lower + (total/2 - cum_before) / bracket_count * bracket_width`` —
    not the bracket midpoint, which biased every PA toward its bracket
    centre. The open top bracket uses the assumed width
    ``_OPEN_BRACKET_ASSUMED_WIDTH`` (see the constant's comment).
    """
    df = raw[raw["Thousands"].astype(str).str.strip() != "Total"].copy()
    df = df.rename(columns={"Thousands": "planning_area"})

    missing_brackets = [col for col, _, _ in _INCOME_BRACKETS if col not in df.columns]
    if missing_brackets:
        logger.warning(
            "Income-by-planning-area: %d bracket column(s) missing/unknown and "
            "skipped: %s — medians for affluent areas may be biased low",
            len(missing_brackets),
            ", ".join(missing_brackets),
        )

    for col, _, _ in _INCOME_BRACKETS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    open_bracket_pas = 0

    def _grouped_median(row: pd.Series) -> float:
        nonlocal open_bracket_pas
        weights = [
            float(row[col]) if col in row.index and pd.notna(row[col]) else 0.0
            for col, _, _ in _INCOME_BRACKETS
        ]
        total = sum(weights)
        if total == 0:
            return pd.NA
        target = total / 2
        cumulative = 0.0
        for (_col, lower, upper), weight in zip(_INCOME_BRACKETS, weights, strict=True):
            if cumulative + weight < target:
                cumulative += weight
                continue
            if upper is None:
                open_bracket_pas += 1
                width = _OPEN_BRACKET_ASSUMED_WIDTH
            else:
                width = upper - lower
            return lower + (target - cumulative) / weight * width
        return pd.NA  # pragma: no cover -- total > 0 guarantees a crossing

    df["median_monthly_income"] = df.apply(_grouped_median, axis=1)

    # Bias tripwire: how many PAs needed the open-bracket assumption.
    logger.info(
        "Income grouped medians: %d planning area(s) fell inside the open top "
        "bracket '12_000andOver' (assumed width %s SGD, the previous bracket's "
        "width) — their medians rest on that convention",
        open_bracket_pas,
        _OPEN_BRACKET_ASSUMED_WIDTH,
    )

    df["planning_area"] = df["planning_area"].astype(str).str.strip()
    return df


def raw_income_by_planning_area(bronze_dir: Path) -> pd.DataFrame:
    """Fetch resident working persons income distribution by planning area."""
    return _load_or_fetch_dataset(
        bronze_dir,
        key="income_by_planning_area",
        resource_id=INCOME_BY_PLANNING_AREA_RESOURCE_ID,
        display_name="income by planning area",
        transform=_transform_income_by_planning_area,
    )


def _transform_green_mark_buildings(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows without a usable postal code and normalize it."""
    raw_count = len(df)
    df = df[df["Postal_Code"].notna() & df["Postal_Code"].astype(str).str.strip().ne("")].copy()
    dropped_blank_postal = raw_count - len(df)
    if dropped_blank_postal:
        logger.warning(
            "Green Mark buildings: dropped %s/%s row(s) with blank Postal_Code "
            "(unusable for geocoding); kept %s",
            dropped_blank_postal,
            raw_count,
            len(df),
        )
    df["postal_code"] = df["Postal_Code"].astype(str).str.strip()
    return df


def raw_green_mark_buildings(bronze_dir: Path) -> pd.DataFrame:
    """Fetch BCA Green Mark certified buildings from data.gov.sg (CSV)."""
    return _load_or_fetch_dataset(
        bronze_dir,
        key="green_mark_buildings",
        resource_id=GREEN_MARK_BUILDINGS_RESOURCE_ID,
        display_name="green mark buildings",
        transform=_transform_green_mark_buildings,
    )


def geocoded_green_mark_buildings(
    bronze_dir: Path,
    raw_green_mark_buildings: pd.DataFrame,
    geocoder: Geocoder,
) -> pd.DataFrame:
    """Geocode Green Mark buildings via OneMap, cache as bronze parquet."""
    cached = read_bronze_cache(bronze_dir, "raw_green_mark_buildings_geocoded")
    if cached is not None:
        logger.info(
            "Loading geocoded green mark buildings from bronze: %s",
            bronze_dir / "raw_green_mark_buildings_geocoded.parquet",
        )
        return cached

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

    geocoded_rows = int(df["lat"].notna().sum())
    if geocoded_rows == 0:
        # Same empty-guard semantics as the macro caches: an all-NA-coordinate
        # frame is degenerate and must never replace (or seed) a valid cache.
        logger.warning(
            "Green Mark geocoding matched no coordinates — not caching an "
            "all-NA-coordinate frame (%s rows returned uncached)",
            len(df),
        )
        return df

    write_bronze_cache(
        bronze_dir,
        df,
        "raw_green_mark_buildings_geocoded",
        "onemap_geocode",
        rows=geocoded_rows,
    )
    logger.info(
        "Geocoded Green Mark buildings: %s/%s saved to %s",
        geocoded_rows,
        len(df),
        bronze_dir / "raw_green_mark_buildings_geocoded.parquet",
    )
    return df


def raw_dwelling_units_by_town(bronze_dir: Path) -> pd.DataFrame:
    """Fetch dwelling units under HDB management by town and flat type."""
    return _load_or_fetch_dataset(
        bronze_dir,
        key="dwelling_units_by_town",
        resource_id=DWELLING_UNITS_RESOURCE_ID,
        display_name="dwelling units by town",
    )


def raw_median_annual_value(bronze_dir: Path) -> pd.DataFrame:
    """Fetch median annual value and property tax by HDB flat type from IRAS."""
    return _load_or_fetch_dataset(
        bronze_dir,
        key="median_annual_value",
        resource_id=MEDIAN_ANNUAL_VALUE_RESOURCE_ID,
        display_name="median annual value",
    )


def raw_hdb_resident_population(bronze_dir: Path) -> pd.DataFrame:
    """Fetch HDB resident population by geographical distribution (town/estate)."""
    return _load_or_fetch_dataset(
        bronze_dir,
        key="hdb_resident_population",
        resource_id=HDB_RESIDENT_POPULATION_RESOURCE_ID,
        display_name="HDB resident population",
    )


# URA Master Plan 2025 SDCP "Mall, Promenade and Thru-Block Link" layer,
# published by URA on data.gov.sg. MALL-classified polygons approximate
# existing and designated mall sites.
MP25_MALLS_DATASET_ID = "d_65a0bf22c15ef49e9a21b8bcf8c04c87"
_MP25_MALLS_BRONZE_NAME = "raw_mp25_malls"


def _malls_from_mp25_geojson(geojson: dict) -> pd.DataFrame:
    """Extract mall-site centroids from the URA MP25 mall layer GeoJSON.

    Keeps only MALL-classified polygons (promenades, thru-block links, and
    other classifications are excluded). Names are not present in this layer;
    ``nearest_mall`` stays empty while distances remain meaningful.
    """
    rows: list[dict] = []
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        if str(props.get("CLASSIFCTN", "")).strip().upper() != "MALL":
            continue
        geom = feature.get("geometry") or {}
        if not geom:
            continue
        try:
            centroid = shape(geom).centroid
        except Exception as exc:  # malformed geometry degrades one row, not the run
            logger.warning("Skipping malformed MP25 mall geometry: %s", exc)
            continue
        if centroid.is_empty:
            continue
        rows.append({"name": "", "lat": float(centroid.y), "lon": float(centroid.x)})
    return pd.DataFrame(rows)


def _load_mp25_malls(bronze_dir: Path) -> pd.DataFrame:
    """Load or fetch the MP25 mall layer into bronze (empty never cached)."""
    mp25_path = bronze_dir / f"{_MP25_MALLS_BRONZE_NAME}.parquet"
    cached = read_bronze_cache(bronze_dir, _MP25_MALLS_BRONZE_NAME)
    if cached is not None:
        if not cached.empty:
            logger.info("Loading MP25 shopping malls from bronze: %s", mp25_path)
            return cached
        logger.warning("Ignoring empty MP25 mall bronze cache: %s", mp25_path)

    try:
        geojson = datagovsg.fetch_datagovsg_geojson(MP25_MALLS_DATASET_ID, use_cache=False)
    except (DatasetFetchError, requests.RequestException) as exc:
        logger.warning(
            "Could not fetch URA MP25 mall layer: %s — mall proximity features "
            "(dist_to_nearest_mall, nearest_mall) will be empty",
            exc,
        )
        return pd.DataFrame()

    malls = _malls_from_mp25_geojson(geojson)
    if malls.empty:
        logger.warning(
            "MP25 mall layer contained no MALL polygons — mall proximity features will be empty"
        )
        return pd.DataFrame()

    write_bronze_cache(bronze_dir, malls, _MP25_MALLS_BRONZE_NAME, "datagov_api")
    logger.info("Fetched %s MP25 mall sites -> %s", len(malls), mp25_path)
    return malls


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
    """Load shopping mall data from bronze layer.

    Primary source is the URA MP25 mall layer (data.gov.sg, fetched via
    ``fetch_datagovsg_geojson`` and bronze-cached). Legacy wiki-sourced
    parquets produced by ``notebooks/L0_wiki.ipynb`` still take precedence
    when present; they have real names but no refresh path and are
    deprecated.
    """
    malls_df = read_bronze_cache(bronze_dir, "raw_wiki_shopping_mall")
    geocoded_df = read_bronze_cache(bronze_dir, "raw_wiki_shopping_mall_geocoded")
    # Empty wiki caches are misses, not data (macro empty-guard contract): a
    # 0-row parquet must fall through to the MP25 primary source.
    if malls_df is not None and malls_df.empty:
        logger.warning(
            "Ignoring empty bronze cache: %s", bronze_dir / "raw_wiki_shopping_mall.parquet"
        )
        malls_df = None
    if geocoded_df is not None and geocoded_df.empty:
        logger.warning(
            "Ignoring empty bronze cache: %s",
            bronze_dir / "raw_wiki_shopping_mall_geocoded.parquet",
        )
        geocoded_df = None

    if malls_df is None and geocoded_df is None:
        return _load_mp25_malls(bronze_dir)

    logger.warning(
        "Using deprecated wiki-sourced shopping mall bronze cache; the "
        "primary source is now the URA MP25 mall layer. Remove the wiki "
        "parquets (or run `main.py --refresh 'raw_wiki_shopping_mall*'`, "
        "quoted so the shell does not expand the glob) to switch."
    )

    if geocoded_df is not None:
        logger.info(
            "Loading geocoded shopping malls from bronze: %s",
            bronze_dir / "raw_wiki_shopping_mall_geocoded.parquet",
        )
        return _standardize_geocoded_mall_columns(geocoded_df)

    assert malls_df is not None  # both-None returned above; geocoded-None here

    has_coordinates = {"lat", "lon"}.issubset(malls_df.columns) or {
        "latitude",
        "longitude",
    }.issubset(malls_df.columns)
    if has_coordinates:
        return _standardize_geocoded_mall_columns(malls_df)

    try:
        geocoded = _standardize_geocoded_mall_columns(
            geocoder.geocode_dataframe(malls_df, "shopping_mall")
        )
        if not geocoded.empty:
            write_bronze_cache(
                bronze_dir, geocoded, "raw_wiki_shopping_mall_geocoded", "onemap_geocode"
            )
            logger.info("Saved %s geocoded shopping malls to bronze", len(geocoded))
            return geocoded
    except (requests.RequestException, OSError, ValueError, KeyError) as exc:
        logger.warning("Could not geocode shopping malls via OneMap: %s", exc)

    return malls_df
