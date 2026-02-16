# scripts/core/config/regional_mapping.py
"""
Regional mapping configuration for Singapore planning areas.

Groups 50+ planning areas into 7 regions for VAR modeling:
- CCR (Core Central Region)
- RCR (Rest of Central Region)
- OCR East, North-East, North, West, Central
"""

from typing import Dict, Optional

# Regional mapping dictionary
PLANNING_AREA_TO_REGION = {
    # CCR (Core Central Region)
    'Downtown': 'CCR',
    'Newton': 'CCR',
    'Orchard': 'CCR',
    'Marina Bay': 'CCR',
    'Tanglin': 'CCR',
    'River Valley': 'CCR',
    'Bukit Merah': 'CCR',  # Includes part of CCR

    # RCR (Rest of Central Region)
    'Queenstown': 'RCR',
    'Geylang': 'RCR',
    'Kallang': 'RCR',
    'Bishan': 'RCR',  # Sometimes classified as RCR
    'Toa Payoh': 'RCR',

    # OCR East
    'Bedok': 'OCR East',
    'Pasir Ris': 'OCR East',
    'Tampines': 'OCR East',
    'Changi': 'OCR East',
    'Simei': 'OCR East',

    # OCR North-East
    'Ang Mo Kio': 'OCR North-East',
    'Serangoon': 'OCR North-East',
    'Hougang': 'OCR North-East',
    'Sengkang': 'OCR North-East',
    'Punggol': 'OCR North-East',

    # OCR North
    'Woodlands': 'OCR North',
    'Yishun': 'OCR North',
    'Sembawang': 'OCR North',

    # OCR West
    'Jurong': 'OCR West',
    'Bukit Batok': 'OCR West',
    'Bukit Panjang': 'OCR West',
    'Choa Chu Kang': 'OCR West',
    'Clementi': 'OCR West',
    'Jurong West': 'OCR West',
    'Tengah': 'OCR West',
    'Boon Lay': 'OCR West',

    # OCR Central
    'Central': 'OCR Central',
    'Novena': 'OCR Central',
    'Thomson': 'OCR Central',
    'Balestier': 'OCR Central',
    'Whampoa': 'OCR Central',
    'MacPherson': 'OCR Central',
    'Potong Pasir': 'OCR Central',

    # Additional RCR areas
    'Marine Parade': 'RCR',
    'Rochor': 'RCR',
    'Outram': 'RCR',
    'Alexandra': 'RCR',
    'Bukit Timah': 'RCR',

    # Additional OCR areas
    'Khatib': 'OCR North',
    'Yio Chu Kang': 'OCR North',
    'Loyang': 'OCR East',
    'Pasir Ris': 'OCR East',
    'Changi Bay': 'OCR East',
    'Expo': 'OCR East',

    # More planning areas
    'Lavender': 'RCR',
    'Farrer Park': 'RCR',
    'Little India': 'RCR',
    'Jalan Besar': 'RCR',
    'Bugis': 'RCR',
}


def get_region_for_planning_area(planning_area: str) -> Optional[str]:
    """
    Get region for a given planning area.

    Args:
        planning_area: Planning area name (e.g., 'Downtown')

    Returns:
        Region name ('CCR', 'RCR', 'OCR East', etc.) or None if not found

    Example:
        >>> get_region_for_planning_area('Downtown')
        'CCR'
        >>> get_region_for_planning_area('Unknown')
        None
    """
    return PLANNING_AREA_TO_REGION.get(planning_area)


def get_all_regional_mappings() -> Dict[str, str]:
    """
    Get all planning area to region mappings.

    Returns:
        Dictionary mapping planning_area -> region
    """
    return PLANNING_AREA_TO_REGION.copy()


def get_regions() -> list:
    """
    Get list of all regions.

    Returns:
        List of region names
    """
    return sorted(set(PLANNING_AREA_TO_REGION.values()))


def get_planning_areas_in_region(region: str) -> list:
    """
    Get all planning areas belonging to a region.

    Args:
        region: Region name (e.g., 'CCR')

    Returns:
        List of planning area names in that region

    Raises:
        ValueError: If region is not found
    """
    areas = [area for area, reg in PLANNING_AREA_TO_REGION.items() if reg == region]

    if not areas and region not in get_regions():
        raise ValueError(f"Unknown region: {region}")

    return sorted(areas)
