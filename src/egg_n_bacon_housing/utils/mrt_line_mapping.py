"""MRT line mapping for Singapore MRT stations.

This module provides functions to determine which MRT line(s) a station belongs to
and assign importance scores based on line tier and interchange status.
"""

import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# Guard so the NSL/EWL-only fallback warning fires once per process, not
# once per MrtReferenceRepository instance.
_fallback_station_lines_warned = False


def _load_json_config(config_dir: Path | None, filename: str) -> dict:
    """Load JSON reference file with fallback to empty dict.

    Args:
        filename: Name of JSON file in config dir

    Returns:
        Parsed JSON data or empty dict if not found
    """
    if config_dir is None:
        logger.debug("MRT config dir not configured — using hardcoded defaults")
        return {}
    config_path = config_dir / filename
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError, TypeError):
            logger.warning("Invalid MRT config file: %s", config_path)
            return {}
    logger.warning("Config file not found: %s", config_path)
    return {}


def _get_mrt_lines(config_dir: Path | None = None) -> dict:
    """Get MRT line metadata, loading from JSON if available.

    Returns:
        Dict mapping line code to line metadata
    """
    data = _load_json_config(config_dir, "mrt_lines.json")
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


def _get_station_lines(config_dir: Path | None = None) -> dict:
    """Get station to line mapping, loading from JSON if available.

    Returns:
        Dict mapping station name to list of line codes
    """
    data = _load_json_config(config_dir, "mrt_stations.json")
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


@dataclass(frozen=True)
class MrtReferenceRepository:
    """MRT reference data rooted at one immutable config directory."""

    config_dir: Path | None
    _lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, repr=False, compare=False
    )
    _lines_cache: dict[str, dict] | None = field(default=None, init=False, repr=False)
    _stations_cache: dict[str, list[str]] | None = field(default=None, init=False, repr=False)

    def mrt_lines(self) -> dict[str, dict]:
        with self._lock:
            if self._lines_cache is None:
                object.__setattr__(self, "_lines_cache", _get_mrt_lines(self.config_dir))
            assert self._lines_cache is not None
            return {code: dict(metadata) for code, metadata in self._lines_cache.items()}

    def station_lines_mapping(self) -> dict[str, list[str]]:
        global _fallback_station_lines_warned
        with self._lock:
            if self._stations_cache is None:
                mapping = _get_station_lines(self.config_dir)
                if not mapping:
                    mapping = _build_fallback_station_lines()
                    if not _fallback_station_lines_warned:
                        _fallback_station_lines_warned = True
                        logger.warning(
                            "mrt_stations.json not found — using the hardcoded "
                            "station->line fallback, which covers only %d "
                            "NSL/EWL stations while the line reference knows "
                            "%d lines; tier and interchange flags will be "
                            "degraded for CCL/DTL/TEL/LRT stations. Fix: run "
                            "the pipeline so raw_mrt_stations refreshes "
                            "bronze/external/mrt_stations.json from the live "
                            "LTA station-codes dataset.",
                            len(mapping),
                            len(self.mrt_lines()),
                        )
                object.__setattr__(self, "_stations_cache", mapping)
            assert self._stations_cache is not None
            return {station: list(lines) for station, lines in self._stations_cache.items()}

    def station_lines(self, station_name: str) -> list[str]:
        station_mapping = self.station_lines_mapping()
        if station_name is None or pd.isna(station_name):
            return []
        station_upper = str(station_name).upper().strip()
        if not station_upper or station_upper == "<NULL>":
            return []
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
        logger.debug("No line info found for station: %s", station_name)
        return []

    def station_tier(self, station_name: str) -> int:
        lines = self.station_lines(station_name)
        if not lines:
            return 3
        min_tier = min(self.mrt_lines().get(line, {}).get("tier", 3) for line in lines)
        return 1 if len(lines) >= 3 else min_tier

    def station_score(self, station_name: str, distance_m: float) -> float:
        basis = station_score_basis(
            self.station_lines(station_name), self.station_tier(station_name)
        )
        return (basis * 1000) / max(distance_m, 1)


def station_score_basis(lines: list[str], tier: int) -> float:
    """Score numerator = 4 - tier + interchange bonuses.

    Single source of truth for the station-score arithmetic, shared by
    ``MrtReferenceRepository.station_score`` and the vectorized proximity
    path in ``utils.proximity`` (which multiplies by ``1000 / max(dist, 1)``
    per property row).
    """
    basis = 4 - tier
    if len(lines) >= 2:
        basis += 1
    if len(lines) >= 3:
        basis += 1
    return basis
