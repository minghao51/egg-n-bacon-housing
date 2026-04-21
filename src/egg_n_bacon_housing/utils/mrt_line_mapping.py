"""MRT line mapping for Singapore MRT stations.

This module provides functions to determine which MRT line(s) a station belongs to
and assign importance scores based on line tier and interchange status.
"""

import json
import logging

import pandas as pd

from egg_n_bacon_housing.config import settings

logger = logging.getLogger(__name__)


def _load_json_config(filename: str) -> dict:
    """Load JSON reference file with fallback to empty dict.

    Args:
        filename: Name of JSON file in data/pipeline/01_bronze/external/

    Returns:
        Parsed JSON data or empty dict if not found
    """
    config_path = settings.bronze_dir / "external" / filename
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    logger.warning(f"Config file not found: {config_path}")
    return {}


def _get_mrt_lines() -> dict:
    """Get MRT line metadata, loading from JSON if available.

    Returns:
        Dict mapping line code to line metadata
    """
    data = _load_json_config("mrt_lines.json")
    if data:
        return data

    return {
        "NSL": {
            "name": "North-South Line",
            "color": "#DC241F",
            "tier": 1,
            "description": "Main North-South artery",
        },
        "EWL": {
            "name": "East-West Line",
            "color": "#009640",
            "tier": 1,
            "description": "Main East-West artery",
        },
        "NEL": {
            "name": "North-East Line",
            "color": "#7D2884",
            "tier": 1,
            "description": "North-East to Harbourfront",
        },
        "CCL": {
            "name": "Circle Line",
            "color": "#C46500",
            "tier": 1,
            "description": "Orbital line connecting major lines",
        },
        "DTL": {
            "name": "Downtown Line",
            "color": "#005EC4",
            "tier": 2,
            "description": "Downtown and Bukit Timah corridor",
        },
        "TEL": {
            "name": "Thomson-East Coast Line",
            "color": "#6C2B95",
            "tier": 2,
            "description": "Thomson corridor to East Coast",
        },
        "BPLR": {
            "name": "Bukit Panjang LRT",
            "color": "#9A2F36",
            "tier": 3,
            "description": "Bukit Panjang feeder",
        },
        "SKRLRT": {
            "name": "Sengkang LRT",
            "color": "#9A2F36",
            "tier": 3,
            "description": "Sengkang feeder",
        },
        "PKLRT": {
            "name": "Punggol LRT",
            "color": "#9A2F36",
            "tier": 3,
            "description": "Punggol feeder",
        },
    }


def _get_station_lines() -> dict:
    """Get station to line mapping, loading from JSON if available.

    Returns:
        Dict mapping station name to list of line codes
    """
    data = _load_json_config("mrt_stations.json")
    if data:
        return data

    return {}


def _build_fallback_station_lines() -> dict:
    """Build station lines mapping from hardcoded station lists.

    Returns:
        Dict mapping station name to list of line codes
    """
    station_lines: dict = {}

    nsl = [
        "JURONG EAST",
        "BUKIT BATOK",
        "BUKIT GOMBAK",
        "CHOA CHU KANG",
        "YEW TEE",
        "KRANJI",
        "MARSILING",
        "WOODLANDS",
        "ADMIRALTY",
        "SEMBAWANG",
        "CANBERRA",
        "YISHUN",
        "KHATIB",
        "YIO CHU KANG",
        "ANG MO KIO",
        "BISHAN",
        "BRADDELL",
        "TOA PAYOH",
        "NOVENA",
        "NEWTON",
        "ORCHARD",
        "SOMERSET",
        "DHOBY GHAUT",
        "CITY HALL",
        "RAFFLES PLACE",
        "MARINA BAY",
        "MARINA SOUTH",
    ]
    for s in nsl:
        station_lines[
            f"{s} INTERCHANGE"
            if s in ["JURONG EAST", "ANG MO KIO", "BISHAN", "NEWTON", "DHOBY GHAUT"]
            else s
        ] = ["NSL"]

    ewl = [
        "PASIR RIS",
        "TAMPINES",
        "SAFRA",
        "TANAH MERAH",
        "BEDOK",
        "KEMBANGAN",
        "EUNOS",
        "PAYA LEBAR",
        "ALJUNIED",
        "KALLANG",
        "LAVENDER",
        "BUGIS",
        "CITY HALL",
        "RAFFLES PLACE",
        "MARINA BAY",
        "GARDENS BY THE BAY",
        "JURONG EAST",
        "CLEMENTI",
        "BOON LAY",
        "PIONEER",
        "JOO KOON",
        "GUL CIRCLE",
        "TUAS CRESCENT",
        "TUAS WEST ROAD",
        "TUAS LINK",
    ]
    for s in ewl:
        key = f"{s} INTERCHANGE" if s in ["JURONG EAST", "BOON LAY", "PAYA LEBAR"] else s
        if key in station_lines:
            station_lines[key].append("EWL")
        else:
            station_lines[key] = ["EWL"]

    return station_lines


_MRT_LINES: dict | None = None
_STATION_LINES: dict | None = None


def get_mrt_lines() -> dict:
    """Get MRT line metadata (cached)."""
    global _MRT_LINES
    if _MRT_LINES is None:
        _MRT_LINES = _get_mrt_lines()
    return _MRT_LINES


def get_station_lines_mapping() -> dict:
    """Get station to line mapping (cached)."""
    global _STATION_LINES
    if _STATION_LINES is None:
        _STATION_LINES = _get_station_lines()
        if not _STATION_LINES:
            _STATION_LINES = _build_fallback_station_lines()
    return _STATION_LINES


_MRT_LINES: dict | None = None
_STATION_LINES: dict | None = None


def get_station_lines(station_name: str) -> list[str]:
    """Get MRT line codes for a station.

    Args:
        station_name: Name of MRT station

    Returns:
        List of line codes (e.g., ['NSL', 'EWL'] for interchanges)
    """
    station_mapping = get_station_lines_mapping()

    if station_name is None or pd.isna(station_name):
        return []

    station_upper = str(station_name).upper().strip()

    if not station_upper or station_upper == "<NULL>":
        return []

    if station_upper in station_mapping:
        return station_mapping[station_upper]

    variants = [
        station_upper,
        station_upper.replace(" INTERCHANGE", ""),
        station_upper.replace(" MRT", ""),
        station_upper + " INTERCHANGE",
        station_upper + " MRT",
    ]

    for variant in variants:
        if variant in station_mapping:
            return station_mapping[variant]

    logger.debug(f"No line info found for station: {station_name}")
    return []


def get_station_tier(station_name: str) -> int:
    """Get station importance tier (1=highest, 3=lowest).

    Tier 1: Major interchange stations, lines passing through CBD
    Tier 2: Secondary MRT lines
    Tier 3: LRT feeder lines

    Args:
        station_name: Name of MRT station

    Returns:
        Tier level (1, 2, or 3)
    """
    lines = get_station_lines(station_name)

    if not lines:
        return 3

    mrt_lines = get_mrt_lines()
    min_tier = min(mrt_lines.get(line, {}).get("tier", 3) for line in lines)

    if len(lines) >= 3:
        return 1

    return min_tier


def is_interchange(station_name: str) -> bool:
    """Check if station is an interchange (serves 2+ lines).

    Args:
        station_name: Name of MRT station

    Returns:
        True if interchange, False otherwise
    """
    lines = get_station_lines(station_name)
    return len(lines) >= 2


def get_station_score(station_name: str, distance_m: float) -> float:
    """Calculate overall station score considering line tier and distance.

    Higher score = better/more important station

    Score = (4 - tier) * 1000 / distance
    - Tier 1 stations get 3x weight
    - Tier 2 stations get 2x weight
    - Tier 3 stations get 1x weight
    - Normalized by distance (closer = better)

    Args:
        station_name: Name of MRT station
        distance_m: Distance in meters

    Returns:
        Station score (higher is better)
    """
    tier = get_station_tier(station_name)
    lines = get_station_lines(station_name)

    tier_score = 4 - tier

    if len(lines) >= 2:
        tier_score += 1
    if len(lines) >= 3:
        tier_score += 1

    if distance_m <= 0:
        distance_m = 1

    score = (tier_score * 1000) / distance_m

    return score


def get_line_color(line_code: str) -> str:
    """Get color hex code for MRT line.

    Args:
        line_code: MRT line code (e.g., 'NSL', 'EWL')

    Returns:
        Hex color string
    """
    return get_mrt_lines().get(line_code, {}).get("color", "#CCCCCC")


def get_line_name(line_code: str) -> str:
    """Get full name for MRT line.

    Args:
        line_code: MRT line code (e.g., 'NSL', 'EWL')

    Returns:
        Full line name
    """
    return get_mrt_lines().get(line_code, {}).get("name", "Unknown Line")


if __name__ == "__main__":
    test_stations = [
        "DHOBY GHAUT INTERCHANGE",
        "ANG MO KIO INTERCHANGE",
        "CLEMENTI",
        "PUNGGOL",
        "BUKIT PANJANG",
    ]

    print("MRT Line Mapping Test")
    print("=" * 60)

    for station in test_stations:
        lines = get_station_lines(station)
        tier = get_station_tier(station)
        is_interch = is_interchange(station)

        line_names = [get_line_name(line) for line in lines]
        colors = [get_line_color(line) for line in lines]

        print(f"\nStation: {station}")
        print(f"  Lines: {', '.join(line_names)}")
        print(f"  Tier: {tier}")
        print(f"  Interchange: {is_interch}")
        print(f"  Score (500m): {get_station_score(station, 500):.2f}")
