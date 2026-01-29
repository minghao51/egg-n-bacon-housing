"""MRT line mapping for Singapore MRT stations.

This module provides functions to determine which MRT line(s) a station belongs to
and assign importance scores based on line tier and interchange status.
"""

import logging
from typing import Dict, List, Optional, Set

import pandas as pd

logger = logging.getLogger(__name__)

# MRT Lines with their metadata
MRT_LINES = {
    # Major Interchange Lines (Tier 1)
    'NSL': {
        'name': 'North-South Line',
        'color': '#DC241F',
        'tier': 1,
        'description': 'Main North-South artery through city center'
    },
    'EWL': {
        'name': 'East-West Line',
        'color': '#009640',
        'tier': 1,
        'description': 'Main East-West artery through city center'
    },
    'NEL': {
        'name': 'North-East Line',
        'color': '#7D2884',
        'tier': 1,
        'description': 'North-East to Harbourfront'
    },
    'CCL': {
        'name': 'Circle Line',
        'color': '#C46500',
        'tier': 1,
        'description': 'Orbital line connecting major lines'
    },

    # Secondary Lines (Tier 2)
    'DTL': {
        'name': 'Downtown Line',
        'color': '#005EC4',
        'tier': 2,
        'description': 'Downtown and Bukit Timah corridor'
    },
    'TEL': {
        'name': 'Thomson-East Coast Line',
        'color': '#6C2B95',
        'tier': 2,
        'description': 'Thomson corridor to East Coast'
    },

    # LRT Lines (Tier 3 - Feeder services)
    'BPLR': {
        'name': 'Bukit Panjang LRT',
        'color': '#9A2F36',
        'tier': 3,
        'description': 'Bukit Panjang feeder'
    },
    'SKRLRT': {
        'name': 'Sengkang LRT',
        'color': '#9A2F36',
        'tier': 3,
        'description': 'Sengkang feeder'
    },
    'PKLRT': {
        'name': 'Punggol LRT',
        'color': '#9A2F36',
        'tier': 3,
        'description': 'Punggol feeder'
    },
}

# Station to Line(s) mapping
# Key: Station name (uppercase, as in geojson)
# Value: List of line codes
STATION_LINES: Dict[str, List[str]] = {}

# North-South Line (NSL)
NSL_STATIONS = [
    'JURONG EAST INTERCHANGE', 'BUKIT BATOK', 'BUKIT GOMBAK', 'CHOA CHU KANG',
    'YEW TEE', 'KRANJI', 'MARSILING', 'WOODLANDS', 'ADMIRALTY',
    'SEMBAWANG', 'CANBERRA', 'YISHUN', 'KHATIB', 'YIO CHU KANG',
    'ANG MO KIO INTERCHANGE', 'BISHAN INTERCHANGE', 'BRADDELL', 'TOA PAYOH',
    'NOVENA', 'NEWTON INTERCHANGE', 'ORCHARD', 'SOMERSET', 'DHOBY GHAUT INTERCHANGE',
    'CITY HALL', 'RAFFLES PLACE', 'MARINA BAY', 'MARINA SOUTH'
]
for station in NSL_STATIONS:
    STATION_LINES[station] = ['NSL']

# East-West Line (EWL)
EWL_STATIONS = [
    'PASIR RIS', 'TAMPINES', 'SAFRA', 'TANAH MERAH', 'BEDOK', 'KEMBANGAN',
    'EUNOS', 'PAYA LEBAR INTERCHANGE', 'ALJUNIED', 'KALLANG', 'LAVENDER',
    'BUGIS', 'CITY HALL', 'RAFFLES PLACE', 'MARINA BAY', 'GARDENS BY THE BAY',
    'JURONG EAST INTERCHANGE', 'CLEMENTI', 'BOON LAY INTERCHANGE',
    'PIONEER', 'JOO KOON', 'GUL CIRCLE', 'TUAS CRESCENT', 'TUAS WEST ROAD', 'TUAS LINK'
]
for station in EWL_STATIONS:
    if station in STATION_LINES:
        STATION_LINES[station].append('EWL')
    else:
        STATION_LINES[station] = ['EWL']

# North-East Line (NEL)
NEL_STATIONS = [
    'HARBOURFRONT INTERCHANGE', 'OUTRAM PARK INTERCHANGE', 'CHINATOWN',
    'CLARKE QUAY', 'DHOBY GHAUT INTERCHANGE', 'LITTLE INDIA', 'FARRER PARK',
    'BOON KENG', 'SERANGOON INTERCHANGE', 'KOVAN', 'HOUGANG INTERCHANGE',
    'BUANGKOK', 'SENGKANG', 'PUNGGOL', 'PUNGGOL CENTRAL'
]
for station in NEL_STATIONS:
    if station in STATION_LINES:
        STATION_LINES[station].append('NEL')
    else:
        STATION_LINES[station] = ['NEL']

# Circle Line (CCL)
CCL_STATIONS = [
    'DHOBY GHAUT INTERCHANGE', 'BRAS BASAH', 'ESPLANADE', 'PROMENADE',
    'NICOLL HIGHWAY', 'STADIUM', 'MOUNTBATTEN', 'DAKOTA', 'PAYA LEBAR INTERCHANGE',
    'MACPHERSON', 'TAI SENG', 'BARTLEY', 'SERANGOON INTERCHANGE', 'LORONG CHUAN',
    'BISHAN INTERCHANGE', 'MARYMOUNT', 'CALDECOTT INTERCHANGE', 'BOTANIC GARDENS INTERCHANGE',
    'FARRER ROAD', 'HOLLAND VILLAGE', 'BUONA VISTA INTERCHANGE', 'ONE NORTH',
    'LABRADOR PARK', 'TELOK BLANGAH', 'HARBOURFRONT INTERCHANGE',
    'KEPPEL', 'BUKIT MERAH', 'HARRIER PARK', 'CANTONMENT', 'PRINCE EDWARD ROAD'
]
for station in CCL_STATIONS:
    if station in STATION_LINES:
        STATION_LINES[station].append('CCL')
    else:
        STATION_LINES[station] = ['CCL']

# Downtown Line (DTL)
DTL_STATIONS = [
    'BUKIT PANJANG', 'CHEW SUNG', 'CASH EW', 'HILLVIEW', 'BEAUTY WORLD',
    'KING ALBERT PARK', 'STEVENS', 'BOTANIC GARDENS INTERCHANGE',
    'TAN KAH KEE', 'SIXTH AVENUE', 'NEWTON INTERCHANGE', 'LITTLE INDIA',
    'ROCHOR', 'BUGIS', 'PROMENADE', 'BAYFRONT', 'DOWNTOWN', 'TELOK BLANGAH',
    'LABRADOR PARK', 'ONE NORTH', 'BUONA VISTA INTERCHANGE', 'HAWKER VILLAGE',
    'CLEMENTI', 'CLEMENTI ROAD', 'DOVER', 'EXPO INTERCHANGE', 'UPPER CHANGI'
]
for station in DTL_STATIONS:
    if station in STATION_LINES:
        STATION_LINES[station].append('DTL')
    else:
        STATION_LINES[station] = ['DTL']

# Thomson-East Coast Line (TEL)
TEL_STATIONS = [
    'WOODLANDS SOUTH', 'WOODLANDS NORTH', 'WOODLANDS', 'SEMBAWANG',
    'CANBERRA', 'YISHUN', 'SPRINGLEAF', 'TAGORE', 'BRIGHT HILL INTERCHANGE',
    'UPPER THOMSON', 'CALDECOTT INTERCHANGE', 'MT PLEASANT', 'STEvens',
    'ORCHARD BOULEVARD', 'ORCHARD', 'NEWTON INTERCHANGE',
    'LITTLE INDIA', 'SPOT', 'PENDING', 'GATEWAY', 'MANDAI',
    'AVIATION PARK', 'CHANGI AIRPORT'
]
for station in TEL_STATIONS:
    if station in STATION_LINES:
        STATION_LINES[station].append('TEL')
    else:
        STATION_LINES[station] = ['TEL']

# Bukit Panjang LRT (BPLR)
BPLR_STATIONS = [
    'CHOA CHU KANG', 'SOUTH VIEW', 'KEAT HONG', 'TECK WHYE', 'PHOENIX',
    'BUKIT PANJANG', 'FAJAR', 'SEGAR', 'JELAPANG', 'SENJA'
]
for station in BPLR_STATIONS:
    if station in STATION_LINES:
        STATION_LINES[station].append('BPLR')
    else:
        STATION_LINES[station] = ['BPLR']

# Sengkang LRT (SKRLRT)
SKRLRT_STATIONS = [
    'SENGKANG', 'CHENG LIM', 'FARMWAY', 'KANGKAR', 'RANGGUNG',
    'THANGGAM', 'RENJONG', 'COMPASSVALE', 'LAYAR', 'TONGKANG'
]
for station in SKRLRT_STATIONS:
    if station in STATION_LINES:
        STATION_LINES[station].append('SKRLRT')
    else:
        STATION_LINES[station] = ['SKRLRT']

# Punggol LRT (PKLRT)
PKLRT_STATIONS = [
    'PUNGGOL', 'SOO TECK', 'MERIDIAN', 'CORAL EDGE', 'RIVIERA',
    'KADALOOR', 'COVE', 'SAMUDERA', 'NIBONG', 'SUMANG', 'OM', 'DAMAI',
    'PUNGGOL POINT', 'SAMKEE', 'TECK LEE', 'OASIS'
]
for station in PKLRT_STATIONS:
    if station in STATION_LINES:
        STATION_LINES[station].append('PKLRT')
    else:
        STATION_LINES[station] = ['PKLRT']

# Major Interchanges (stations with 3+ lines)
MAJOR_INTERCHANGES = {
    'DHOBY GHAUT INTERCHANGE': ['NSL', 'NEL', 'CCL'],
    'CITY HALL': ['NSL', 'EWL'],
    'RAFFLES PLACE': ['NSL', 'EWL'],
    'JURONG EAST INTERCHANGE': ['NSL', 'EWL'],
    'BISHAN INTERCHANGE': ['NSL', 'CCL'],
    'BUONA VISTA INTERCHANGE': ['EWL', 'CCL'],
    'PAYA LEBAR INTERCHANGE': ['EWL', 'CCL'],
    'SERANGOON INTERCHANGE': ['NEL', 'CCL'],
    'BOTANIC GARDENS INTERCHANGE': ['CCL', 'DTL'],
    'NEWTON INTERCHANGE': ['NSL', 'DTL', 'TEL'],
    'MARINA BAY': ['NSL', 'EWL'],
    'HARBOURFRONT INTERCHANGE': ['NEL', 'CCL'],
    'OUTRAM PARK INTERCHANGE': ['NEL', 'EWL'],
    'CHANGI AIRPORT': ['EWL', 'TEL'],
}

# Update major interchanges
for station, lines in MAJOR_INTERCHANGES.items():
    STATION_LINES[station] = lines


def get_station_lines(station_name: str) -> List[str]:
    """Get MRT line codes for a station.

    Args:
        station_name: Name of MRT station

    Returns:
        List of line codes (e.g., ['NSL', 'EWL'] for interchanges)
    """
    # Handle null/None station names
    if station_name is None or pd.isna(station_name):
        return []

    # Normalize station name
    station_upper = str(station_name).upper().strip()

    # Skip empty names
    if not station_upper or station_upper == '<NULL>':
        return []

    # Direct lookup
    if station_upper in STATION_LINES:
        return STATION_LINES[station_upper]

    # Fuzzy match - try removing/adding common suffixes
    variants = [
        station_upper,
        station_upper.replace(' INTERCHANGE', ''),
        station_upper.replace(' MRT', ''),
        station_upper + ' INTERCHANGE',
        station_upper + ' MRT',
    ]

    for variant in variants:
        if variant in STATION_LINES:
            return STATION_LINES[variant]

    # Default: no line info
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
        return 3  # Default to lowest tier

    # Get minimum tier among all lines (highest importance)
    min_tier = min(MRT_LINES.get(line, {}).get('tier', 3) for line in lines)

    # Boost major interchanges (3+ lines)
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

    # Base score from tier (tier 1 = 3, tier 2 = 2, tier 3 = 1)
    tier_score = 4 - tier

    # Interchange bonus
    if len(lines) >= 2:
        tier_score += 1  # +1 for interchanges
    if len(lines) >= 3:
        tier_score += 1  # Additional +1 for major interchanges

    # Calculate final score (inverse of distance)
    if distance_m <= 0:
        distance_m = 1  # Avoid division by zero

    score = (tier_score * 1000) / distance_m

    return score


def get_line_color(line_code: str) -> str:
    """Get color hex code for MRT line.

    Args:
        line_code: MRT line code (e.g., 'NSL', 'EWL')

    Returns:
        Hex color string
    """
    return MRT_LINES.get(line_code, {}).get('color', '#CCCCCC')


def get_line_name(line_code: str) -> str:
    """Get full name for MRT line.

    Args:
        line_code: MRT line code (e.g., 'NSL', 'EWL')

    Returns:
        Full line name
    """
    return MRT_LINES.get(line_code, {}).get('name', 'Unknown Line')


if __name__ == "__main__":
    # Test the mapping
    test_stations = [
        'DHOBY GHAUT INTERCHANGE',
        'ANG MO KIO INTERCHANGE',
        'CLEMENTI',
        'PUNGGOL',
        'BUKIT PANJANG'
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
