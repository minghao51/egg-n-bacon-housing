"""GeoJSON amenity loader nodes for bronze layer."""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

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


def raw_mrt_stations(bronze_dir: Path) -> pd.DataFrame:
    """Load MRT station data from bronze/external.

    Merges station-line mapping (mrt_stations.json) with GeoJSON coordinates.
    """
    lines_path = bronze_dir / "external" / "mrt_stations.json"
    geojson_path = bronze_dir / "external" / "MRTStations.geojson"

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
    merged = merged.drop(columns=["_key"])

    merged = merged.drop_duplicates(subset=["name"], keep="first")
    logger.info("Loaded %s MRT stations with coordinates", len(merged))
    return merged


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
    """Load preschool/kindergarten locations from bronze/external GeoJSON."""
    return _load_geojson_amenities(
        bronze_dir / "external" / "PreSchoolsLocation.geojson",
        ["Name"],
        "kindergarten",
    )


def raw_bus_stops(bronze_dir: Path) -> pd.DataFrame:
    """Load bus stop locations from bronze/external GeoJSON."""
    return _load_geojson_amenities(
        bronze_dir / "external" / "BusStops.geojson",
        ["BUS_STOP_NUM", "BUS_ROOF_NUM", "Name"],
        "bus_stop",
    )


def raw_chas_clinics(bronze_dir: Path) -> pd.DataFrame:
    """Load CHAS clinic locations from bronze/external GeoJSON."""
    return _load_geojson_amenities(
        bronze_dir / "external" / "CHASClinics.geojson",
        ["Name", "NAME", "HCI_NAME"],
        "chas_clinic",
    )


def raw_sports_facilities(bronze_dir: Path) -> pd.DataFrame:
    """Load SportSG facility locations from bronze/external GeoJSON."""
    return _load_geojson_amenities(
        bronze_dir / "external" / "SportSGFacilities.geojson",
        ["Name", "NAME"],
        "sports_facility",
    )


def raw_community_clubs(bronze_dir: Path) -> pd.DataFrame:
    """Load Community Club locations from bronze/external GeoJSON."""
    return _load_geojson_amenities(
        bronze_dir / "external" / "CommunityClubs.geojson",
        ["Name", "NAME", "CC_NAME"],
        "community_club",
    )
