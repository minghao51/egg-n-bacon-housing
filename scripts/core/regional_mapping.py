# scripts/core/config/regional_mapping.py
"""
Regional mapping configuration for Singapore planning areas.

Groups 50+ planning areas into 7 regions for VAR modeling:
- CCR (Core Central Region)
- RCR (Rest of Central Region)
- OCR East, North-East, North, West, Central
"""


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
    'Changi Bay': 'OCR East',
    'Expo': 'OCR East',
    'Pasir Ris': 'OCR East',

    # Additional areas from L3 dataset (uppercase versions)
    'DOWNTOWN CORE': 'CCR',
    'NEWTON': 'CCR',
    'ORCHARD': 'CCR',
    'MARINA BAY': 'CCR',
    'TANGLIN': 'CCR',
    'RIVER VALLEY': 'CCR',
    'BUKIT MERAH': 'CCR',
    'QUEENSTOWN': 'RCR',
    'GEYLANG': 'RCR',
    'KALLANG': 'RCR',
    'BISHAN': 'RCR',
    'TOA PAYOH': 'RCR',
    'BEDOK': 'OCR East',
    'PASIR RIS': 'OCR East',
    'TAMPINES': 'OCR East',
    'CHANGI': 'OCR East',
    'ANG MO KIO': 'OCR North-East',
    'SERANGOON': 'OCR North-East',
    'HOUGANG': 'OCR North-East',
    'SENGKANG': 'OCR North-East',
    'PUNGGOL': 'OCR North-East',
    'WOODLANDS': 'OCR North',
    'YISHUN': 'OCR North',
    'SEMBAWANG': 'OCR North',
    'JURONG EAST': 'OCR West',
    'JURONG WEST': 'OCR West',
    'BUKIT BATOK': 'OCR West',
    'BUKIT PANJANG': 'OCR West',
    'CHOA CHU KANG': 'OCR West',
    'CLEMENTI': 'OCR West',
    'MANDAI': 'OCR North',
    'SEMBAWANG': 'OCR North',
    'TAMPINES': 'OCR East',
    'MARINA SOUTH': 'RCR',
    'MARINE PARADE': 'RCR',
    'ROCHOR': 'RCR',
    'OUTRAM': 'RCR',
    'ALEXANDRA': 'RCR',
    'BUKIT TIMAH': 'RCR',
    'MUSEUM': 'CCR',
    'SINGAPORE RIVER': 'RCR',
    'STRAITS VIEW': 'RCR',
    'Changi Bay': 'OCR East',
    'Expo': 'OCR East',

    # More planning areas
    'Lavender': 'RCR',
    'Farrer Park': 'RCR',
    'Little India': 'RCR',
    'Jalan Besar': 'RCR',
    'Bugis': 'RCR',
}


def get_region_for_planning_area(planning_area: str) -> str | None:
    """
    Get region for a given planning area.

    Args:
        planning_area: Planning area name (e.g., 'Downtown', 'ANG MO KIO')

    Returns:
        Region name ('CCR', 'RCR', 'OCR East', etc.) or None if not found

    Example:
        >>> get_region_for_planning_area('Downtown')
        'CCR'
        >>> get_region_for_planning_area('ANG MO KIO')
        'OCR North-East'
        >>> get_region_for_planning_area('Unknown')
        None
    """
    # Try exact match first
    region = PLANNING_AREA_TO_REGION.get(planning_area)
    if region is not None:
        return region

    # Try uppercase version
    region = PLANNING_AREA_TO_REGION.get(planning_area.upper())
    if region is not None:
        return region

    # Try title case version
    region = PLANNING_AREA_TO_REGION.get(planning_area.title())
    if region is not None:
        return region

    return None


def get_all_regional_mappings() -> dict[str, str]:
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
