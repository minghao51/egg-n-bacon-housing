# egg_n_bacon_housing/utils/regional_mapping.py
"""
Regional mapping configuration for Singapore planning areas.

Groups 50+ planning areas into 7 regions for VAR modeling:
- CCR (Core Central Region)
- RCR (Rest of Central Region)
- OCR East, North-East, North, West, Central
"""

# Regional mapping dictionary
_PLANNING_AREA_TO_REGION_BASE = {
    "Downtown": "CCR",
    "Newton": "CCR",
    "Orchard": "CCR",
    "Marina Bay": "CCR",
    "Tanglin": "CCR",
    "River Valley": "CCR",
    "Bukit Merah": "CCR",
    "Downtown Core": "CCR",
    "Museum": "CCR",
    "Queenstown": "RCR",
    "Geylang": "RCR",
    "Kallang": "RCR",
    "Bishan": "RCR",
    "Toa Payoh": "RCR",
    "Marine Parade": "RCR",
    "Rochor": "RCR",
    "Outram": "RCR",
    "Alexandra": "RCR",
    "Bukit Timah": "RCR",
    "Marina South": "RCR",
    "Singapore River": "RCR",
    "Straits View": "RCR",
    "Lavender": "RCR",
    "Farrer Park": "RCR",
    "Little India": "RCR",
    "Jalan Besar": "RCR",
    "Bugis": "RCR",
    "Bedok": "OCR East",
    "Pasir Ris": "OCR East",
    "Tampines": "OCR East",
    "Changi": "OCR East",
    "Simei": "OCR East",
    "Loyang": "OCR East",
    "Changi Bay": "OCR East",
    "Expo": "OCR East",
    "Ang Mo Kio": "OCR North-East",
    "Serangoon": "OCR North-East",
    "Hougang": "OCR North-East",
    "Sengkang": "OCR North-East",
    "Punggol": "OCR North-East",
    "Woodlands": "OCR North",
    "Yishun": "OCR North",
    "Sembawang": "OCR North",
    "Khatib": "OCR North",
    "Yio Chu Kang": "OCR North",
    "Mandai": "OCR North",
    "Jurong": "OCR West",
    "Jurong East": "OCR West",
    "Jurong West": "OCR West",
    "Bukit Batok": "OCR West",
    "Bukit Panjang": "OCR West",
    "Choa Chu Kang": "OCR West",
    "Clementi": "OCR West",
    "Tengah": "OCR West",
    "Boon Lay": "OCR West",
    "Central": "OCR Central",
    "Novena": "OCR Central",
    "Thomson": "OCR Central",
    "Balestier": "OCR Central",
    "Whampoa": "OCR Central",
    "MacPherson": "OCR Central",
    "Potong Pasir": "OCR Central",
}

PLANNING_AREA_TO_REGION = {k.upper(): v for k, v in _PLANNING_AREA_TO_REGION_BASE.items()}


def get_region_for_planning_area(planning_area: str) -> str | None:
    return PLANNING_AREA_TO_REGION.get(planning_area.strip().upper())
