"""GeoJSON amenity loader nodes for bronze layer."""

import html
import json
import logging
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from shapely.geometry import shape

from egg_n_bacon_housing.adapters import datagovsg
from egg_n_bacon_housing.adapters.exceptions import DatasetFetchError
from egg_n_bacon_housing.utils.bronze import (
    read_bronze_cache,
    record_bronze_fetch,
    write_bronze_cache,
)
from egg_n_bacon_housing.utils.mrt_line_mapping import MrtReferenceRepository
from egg_n_bacon_housing.utils.runtime import MrtReference

logger = logging.getLogger(__name__)

__all__ = [
    "raw_mrt_stations",
    "raw_hawker_centres",
    "raw_supermarkets",
    "raw_parks",
    "raw_childcare",
    "raw_kindergartens",
    "raw_bus_stops",
    "raw_chas_clinics",
    "raw_sports_facilities",
    "raw_community_clubs",
]


_KML_PLACEHOLDER_RE = re.compile(r"^kml[_ -]?\d+$", re.IGNORECASE)


def _valid_coord(value: Any) -> bool:
    """True for a usable numeric coordinate; 0.0 is valid, None/NaN/inf are not.

    Equator/prime-meridian coordinates are meaningless in Singapore but
    0.0 must never be treated as *missing* — the previous truthiness check
    (``if lat and lon``) silently dropped legitimate zeros and coerced the
    validity test to Python truthiness.
    """
    if value is None:
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def _name_from_description(props: dict, name_props: list[str]) -> str:
    """Extract a name from a datagovsg KML-style HTML Description table.

    Some datagovsg GeoJSON exports (e.g. CHAS Clinics) carry their attributes
    only inside an HTML ``<table>`` in the feature's ``Description`` property:
    ``<th>HCI_NAME</th> <td>Acumed Medical Group</td>``.
    """
    description = str(props.get("Description") or "")
    if not description:
        return ""
    for prop_name in name_props:
        match = re.search(
            rf"<th[^>]*>\s*{re.escape(prop_name)}\s*</th>\s*<td[^>]*>([^<]+)</td>",
            description,
            flags=re.IGNORECASE,
        )
        if match:
            return html.unescape(match.group(1)).strip()
    return ""


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
    dropped_bad_coords = 0
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        geom_type = geom.get("type", "")
        coords = geom.get("coordinates", [])

        name = ""
        for prop_name in name_props:
            val = props.get(prop_name)
            if val and str(val).strip() and not _KML_PLACEHOLDER_RE.match(str(val).strip()):
                name = str(val).strip()
                break

        if not name:
            name = _name_from_description(props, name_props)

        lat, lon = None, None
        if geom_type == "Point" and len(coords) >= 2:
            lon, lat = coords[0], coords[1]
        elif geom:
            try:
                geom_shape = shape(geom)
                if not geom_shape.is_empty:
                    centroid = geom_shape.centroid
                    lon, lat = float(centroid.x), float(centroid.y)
            except Exception as e:
                logger.warning("Failed to parse geometry for centroid calculation: %s", e)

        if _valid_coord(lat) and _valid_coord(lon):
            rows.append({"name": name, "lat": lat, "lon": lon, "amenity_type": amenity_type})
        else:
            dropped_bad_coords += 1

    if dropped_bad_coords:
        logger.warning(
            "Dropped %d %s feature(s) with invalid/unparseable coordinates from %s",
            dropped_bad_coords,
            amenity_type,
            geojson_path.name,
        )
    logger.info("Loaded %s %s locations", len(rows), amenity_type)
    return pd.DataFrame(rows)


def _load_mrt_geojson(geojson_path: Path) -> pd.DataFrame:
    """Load MRT station centroids from GeoJSON."""
    # Station names are non-ASCII-capable (e.g. Chinese-name exports); the
    # default locale encoding would crash or mojibake them on some platforms.
    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    dropped_no_name = 0
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        name = props.get("NAME", "")
        geom_type = geom.get("type", "")
        coords = geom.get("coordinates", [])

        lat, lon = None, None
        if geom_type == "Point" and len(coords) >= 2:
            lon, lat = coords[0], coords[1]
        elif geom:
            try:
                geom_shape = shape(geom)
                if not geom_shape.is_empty:
                    centroid = geom_shape.centroid
                    lon, lat = float(centroid.x), float(centroid.y)
            except Exception as e:
                logger.warning("Failed to parse geometry for centroid calculation: %s", e)

        if name and _valid_coord(lat) and _valid_coord(lon):
            rows.append({"name": name, "lat": lat, "lon": lon})
        elif not name and _valid_coord(lat) and _valid_coord(lon):
            dropped_no_name += 1

    if dropped_no_name:
        logger.warning(
            "Dropped %d name-less MRT station feature(s) from %s (no NAME property)",
            dropped_no_name,
            geojson_path.name,
        )

    return pd.DataFrame(rows)


# LTA live sources (data.gov.sg). The station-exit GeoJSON carries fresh
# coordinates (updated by LTA); the station-codes datastore dataset maps every
# MRT/LRT station to its line(s). Together they supersede the legacy 2019
# MRTStations.geojson + static mrt_stations.json seeds.
MRT_STATION_EXITS_DATASET_ID = "d_b39d3a0871985372d7e1637193335da5"
TRAIN_STATION_CODES_DATASET_ID = "d_d312a5b127e1ae74299b8ae664cedd4e"

_STATION_SUFFIX_RE = re.compile(r" (MRT|LRT) STATION$")

# Stations from lines missing from LTA's "Train Station Chinese Names"
# dataset (as of 2026-08 it has no Thomson-East Coast Line rows at all).
# Line-major: every open TEL station + CCL's Punggol Coast extension.
# Merge-safe with dataset-derived lines; trim once the LTA dataset catches up.
_STATION_LINE_SUPPLEMENT: dict[str, list[str]] = {
    "TEL": [
        "WOODLANDS NORTH",
        "WOODLANDS",
        "WOODLANDS SOUTH",
        "SPRINGLEAF",
        "LENTOR",
        "MAYFLOWER",
        "BRIGHT HILL",
        "UPPER THOMSON",
        "CALDECOTT",
        "NAPIER",
        "ORCHARD BOULEVARD",
        "ORCHARD",
        "GREAT WORLD",
        "HAVELOCK",
        "OUTRAM PARK",
        "MAXWELL",
        "SHENTON WAY",
        "MARINA BAY",
        "FOUNDERS MEMORIAL",
        "GARDENS BY THE BAY",
        "TANJONG RHU",
        "KATONG PARK",
        "TANJONG KATONG",
        "MARINE PARADE",
        "MARINE TERRACE",
        "SIGLAP",
        "BAYSHORE",
        "BEDOK SOUTH",
    ],
    "CCL": ["PUNGGOL COAST"],
}


def _normalize_station_name(name: str) -> str:
    """Normalize station names for joins and mrt_line_mapping lookups.

    'BAYSHORE MRT STATION' -> 'BAYSHORE'; matches the keys used by the
    legacy fallback lists in utils/mrt_line_mapping.py.
    """
    normalized = re.sub(r"\s+", " ", str(name)).strip().upper()
    return _STATION_SUFFIX_RE.sub("", normalized)


def _stations_from_exits(exits_geojson: dict) -> pd.DataFrame:
    """Collapse per-exit points into one row per station (centroid of exits)."""
    by_station: dict[str, list[tuple[float, float]]] = {}
    for feature in exits_geojson.get("features", []):
        props = feature.get("properties", {})
        station = str(props.get("STATION_NA") or "").strip()
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        if not station or len(coords) < 2:
            continue
        try:
            by_station.setdefault(station, []).append((float(coords[0]), float(coords[1])))
        except (TypeError, ValueError):
            continue

    rows = []
    for station, points in by_station.items():
        lons = [p[0] for p in points]
        lats = [p[1] for p in points]
        rows.append(
            {
                "name": _normalize_station_name(station),
                "lat": sum(lats) / len(lats),
                "lon": sum(lons) / len(lons),
            }
        )
    return pd.DataFrame(rows)


def _normalized_key(value: str) -> str:
    """Uppercase alphanumerics only, so 'North-South Line' == 'North South Line'."""
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def _station_lines_mapping(
    codes: pd.DataFrame, mrt_reference: MrtReference | None = None
) -> dict[str, list[str]]:
    """Build station -> [line codes] from the LTA codes table + static supplement."""
    required = {"stn_code", "mrt_station_english", "mrt_line_english"}
    station_lines: dict[str, list[str]] = {}
    unknown_lines: set[str] = set()
    if codes.empty or not required.issubset(codes.columns):
        logger.warning("Station-codes table unusable — relying on the static line supplement")
        codes = pd.DataFrame(columns=list(required))

    reference = mrt_reference or MrtReferenceRepository(None)
    code_by_line_name = {
        _normalized_key(meta.get("name", "")): code for code, meta in reference.mrt_lines().items()
    }

    for _, rec in codes.iterrows():
        station = _normalize_station_name(rec["mrt_station_english"])
        line_code = code_by_line_name.get(_normalized_key(rec["mrt_line_english"]))
        if not station or not line_code:
            if station:
                unknown_lines.add(str(rec["mrt_line_english"]))
            continue
        lines = station_lines.setdefault(station, [])
        if line_code not in lines:
            lines.append(line_code)

    for line_code, stations_in_line in _STATION_LINE_SUPPLEMENT.items():
        for station in stations_in_line:
            lines = station_lines.setdefault(_normalize_station_name(station), [])
            if line_code not in lines:
                lines.append(line_code)

    if unknown_lines:
        logger.info("Station-codes table references lines without codes: %s", sorted(unknown_lines))
    return station_lines


def _attach_station_lines(
    stations: pd.DataFrame, codes: pd.DataFrame, mrt_reference: MrtReference | None = None
) -> pd.DataFrame:
    """Attach a 'line' column ("NSL;EWL") to stations from the codes table."""
    station_lines = _station_lines_mapping(codes, mrt_reference)
    stations = stations.copy()
    stations["line"] = stations["name"].map(lambda n: ";".join(station_lines.get(n, [])))
    return stations


def _warn_stations_without_lines(stations: pd.DataFrame) -> None:
    """Tripwire: flag live-fetched stations that got no line assignment.

    A station present in the exit dataset but absent from the station-codes
    table AND ``_STATION_LINE_SUPPLEMENT`` ends up with an empty/missing
    ``line`` — this warning is the signal that the supplement needs updating.
    """
    if stations.empty:
        return
    if "line" in stations.columns:
        line_values = stations["line"]
        missing = stations[line_values.isna() | (line_values.astype(str).str.strip() == "")]
    else:
        missing = stations
    if missing.empty:
        return
    examples = ", ".join(missing["name"].astype(str).head(5).tolist())
    logger.warning(
        "%d MRT station(s) have no line assignment (e.g. %s) — present in "
        "the station-exit dataset but missing from the station-codes table "
        "and _STATION_LINE_SUPPLEMENT; update the supplement or tier/interchange "
        "features will be degraded for those stations",
        len(missing),
        examples,
    )


def _write_station_lines_json(
    bronze_dir: Path, codes: pd.DataFrame, mrt_reference: MrtReference | None = None
) -> None:
    """Refresh bronze/external/mrt_stations.json from the live codes table.

    utils/mrt_line_mapping.py reads this file first (its hardcoded fallback
    only covers 48 stations), so writing it here upgrades tier/interchange
    features for every station. The seeder never overwrites existing files,
    and raw_mrt_stations regenerates it on each live fetch.
    """
    station_lines = _station_lines_mapping(codes, mrt_reference)
    if not station_lines:
        return
    path = bronze_dir / "external" / "mrt_stations.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(station_lines.items())), f, indent=1)
    logger.info("Refreshed station->line mapping: %s (%d stations)", path, len(station_lines))


def _fetch_live_mrt_stations(
    bronze_dir: Path, mrt_reference: MrtReference | None = None
) -> tuple[pd.DataFrame, str | None]:
    """Fetch stations from the two live LTA datasets.

    Returns the stations (empty on any failure) and, when the live path
    yielded nothing, a short reason suitable for a fallback warning.
    """
    try:
        exits_geojson = datagovsg.fetch_datagovsg_geojson(
            MRT_STATION_EXITS_DATASET_ID, use_cache=False
        )
    except (DatasetFetchError, requests.RequestException) as exc:
        logger.warning("Station-exit fetch failed: %s — will try legacy bronze files", exc)
        return pd.DataFrame(), f"station-exit fetch failed: {exc}"

    stations = _stations_from_exits(exits_geojson)
    if stations.empty:
        logger.warning("Station-exit dataset yielded no stations — will try legacy bronze files")
        return pd.DataFrame(), "station-exit dataset yielded no stations"

    try:
        codes = datagovsg.fetch_datagovsg_dataset(
            f"{datagovsg.DATAGOVSG_BASE_URL}?resource_id=",
            TRAIN_STATION_CODES_DATASET_ID,
            use_cache=False,
        )
    except (DatasetFetchError, requests.RequestException) as exc:
        logger.warning("Station-codes fetch failed (%s); stations will lack line info", exc)
        return stations, None

    stations = _attach_station_lines(stations, codes, mrt_reference)
    _write_station_lines_json(bronze_dir, codes, mrt_reference)
    return stations, None


def _mrt_stations_from_legacy_files(bronze_dir: Path) -> pd.DataFrame:
    """Legacy static path: seeded MRTStations.geojson + mrt_stations.json (2019)."""
    lines_path = bronze_dir / "external" / "mrt_stations.json"
    geojson_path = bronze_dir / "external" / "MRTStations.geojson"

    lines_df = pd.DataFrame()
    if lines_path.exists():
        with open(lines_path, encoding="utf-8") as f:
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

    geo_df["_key"] = geo_df["name"].str.upper().str.strip()
    lines_df["_key"] = lines_df["name"].str.upper().str.strip()

    merged = geo_df.merge(lines_df[["_key", "line"]], on="_key", how="left")

    # The merge yields one row per (station x line). Collapse interchanges
    # into ONE row per station with ";".join(sorted(lines)), matching the
    # live path's _attach_station_lines format — a plain drop_duplicates
    # here used to silently drop all but one line per station.
    lines_by_key: dict[str, list[str]] = {}
    for key, line in zip(merged["_key"], merged["line"], strict=True):
        if pd.isna(line):
            continue
        line_code = str(line).strip()
        if not line_code:
            continue
        station_lines = lines_by_key.setdefault(str(key), [])
        if line_code not in station_lines:
            station_lines.append(line_code)

    merged = merged.drop(columns="line").drop_duplicates(subset=["_key"], keep="first")
    merged["line"] = merged["_key"].map(lambda key: ";".join(sorted(lines_by_key.get(key, []))))
    merged = merged.drop(columns="_key").reset_index(drop=True)
    logger.info("Loaded %s MRT stations with coordinates", len(merged))
    return merged


def raw_mrt_stations(bronze_dir: Path, mrt_reference: MrtReference | None = None) -> pd.DataFrame:
    """Load MRT/LRT station data, preferring live LTA sources over legacy seeds.

    Primary: LTA MRT Station Exit GeoJSON (fresh coordinates, per-exit,
    collapsed to one centroid row per station) + LTA Train Station Codes
    (station -> line mapping, written to bronze/external/mrt_stations.json
    for utils/mrt_line_mapping.py). Result is bronze-cached at
    ``raw_mrt_stations.parquet`` (empty results are never cached; use
    ``main.py --refresh raw_mrt_stations`` to re-fetch).

    Fallback: the legacy static seeds (MRTStations.geojson from 2019 +
    optional mrt_stations.json), used when live fetching fails.
    """
    cache_path = bronze_dir / "raw_mrt_stations.parquet"
    cached = read_bronze_cache(bronze_dir, "raw_mrt_stations")
    if cached is not None:
        if not cached.empty:
            logger.info("Loading %s MRT stations from bronze: %s", len(cached), cache_path)
            return cached
        logger.warning("Ignoring empty MRT bronze cache: %s", cache_path)

    stations, live_failure = _fetch_live_mrt_stations(bronze_dir, mrt_reference)
    if not stations.empty:
        _warn_stations_without_lines(stations)
        write_bronze_cache(bronze_dir, stations, "raw_mrt_stations", "lta_api")
        logger.info("Cached %s MRT stations -> %s", len(stations), cache_path)
        return stations

    legacy = _mrt_stations_from_legacy_files(bronze_dir)
    if not legacy.empty:
        logger.warning(
            "Live MRT fetch failed (%s) — using the legacy static MRT seeds "
            "(MRTStations.geojson / mrt_stations.json, 2019 vintage) with %d "
            "station(s); station/line data is years stale and may be missing "
            "newer lines",
            live_failure,
            len(legacy),
        )
    return legacy


def _load_external_amenity(
    bronze_dir: Path, filename: str, name_props: list[str], amenity_type: str
) -> pd.DataFrame:
    """Load one seeded amenity GeoJSON from bronze/external, recording the read.

    These files have no fetch-and-write path of their own (they are seeded by
    seed_bronze_external from R2-synced data/manual/), so the load IS the
    acquisition point: each successful read is recorded in the bronze manifest
    with source "r2_external" for freshness observability.
    """
    path = bronze_dir / "external" / filename
    df = _load_geojson_amenities(path, name_props, amenity_type)
    if path.exists():
        record_bronze_fetch(bronze_dir, filename, "r2_external", len(df))
    return df


def raw_hawker_centres(bronze_dir: Path) -> pd.DataFrame:
    """Load hawker centre locations from bronze/external GeoJSON."""
    return _load_external_amenity(bronze_dir, "HawkerCentresGEOJSON.geojson", ["NAME"], "hawker")


def raw_supermarkets(bronze_dir: Path) -> pd.DataFrame:
    """Load supermarket locations from bronze/external GeoJSON."""
    return _load_external_amenity(
        bronze_dir, "SupermarketsGEOJSON.geojson", ["Name", "LIC_NAME"], "supermarket"
    )


def raw_parks(bronze_dir: Path) -> pd.DataFrame:
    """Load park and nature reserve locations from bronze/external GeoJSON."""
    return _load_external_amenity(
        bronze_dir, "NParksParksandNatureReserves.geojson", ["NAME"], "park"
    )


def raw_childcare(bronze_dir: Path) -> pd.DataFrame:
    """Load childcare centre locations from bronze/external GeoJSON."""
    return _load_external_amenity(bronze_dir, "ChildCareServices.geojson", ["NAME"], "childcare")


def raw_kindergartens(bronze_dir: Path) -> pd.DataFrame:
    """Load preschool/kindergarten locations from bronze/external GeoJSON."""
    return _load_external_amenity(
        bronze_dir,
        "PreSchoolsLocation.geojson",
        ["Name"],
        "kindergarten",
    )


def raw_bus_stops(bronze_dir: Path) -> pd.DataFrame:
    """Load bus stop locations from bronze/external GeoJSON."""
    return _load_external_amenity(
        bronze_dir,
        "BusStops.geojson",
        ["BUS_STOP_NUM", "BUS_ROOF_NUM", "Name"],
        "bus_stop",
    )


def raw_chas_clinics(bronze_dir: Path) -> pd.DataFrame:
    """Load CHAS clinic locations from bronze/external GeoJSON."""
    return _load_external_amenity(
        bronze_dir,
        "CHASClinics.geojson",
        ["Name", "NAME", "HCI_NAME"],
        "chas_clinic",
    )


def raw_sports_facilities(bronze_dir: Path) -> pd.DataFrame:
    """Load SportSG facility locations from bronze/external GeoJSON."""
    return _load_external_amenity(
        bronze_dir,
        "SportSGFacilities.geojson",
        ["Name", "NAME", "VENUE"],
        "sports_facility",
    )


def raw_community_clubs(bronze_dir: Path) -> pd.DataFrame:
    """Load Community Club locations from bronze/external GeoJSON."""
    return _load_external_amenity(
        bronze_dir,
        "CommunityClubs.geojson",
        ["Name", "NAME", "CC_NAME"],
        "community_club",
    )
