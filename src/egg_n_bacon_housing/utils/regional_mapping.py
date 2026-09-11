# egg_n_bacon_housing/utils/regional_mapping.py
"""
Regional mapping configuration for Singapore planning areas.

Maps all 55 official OneMap planning areas (the ``pln_area_n`` values in
``data/manual/geojsons/onemap_planning_area_polygon.geojson``) to the three
coarse URA market segments used by ``location_dim.region`` and the app's
region filter:

- CCR (Core Central Region)
- RCR (Rest of Central Region)
- OCR (Outside Central Region)

Every mapping value is exactly one of ``"CCR"``, ``"RCR"``, or ``"OCR"``,
keeping ``location_dim.region`` in parity with the app's ``Region`` type
(``app/src/types/segments.ts``), which exact-match filters on those three
strings. A legacy fine-grained convention (``"OCR East"`` / ``"OCR North-
East"`` / ``"OCR North"`` / ``"OCR West"`` / ``"OCR Central"``) was retired:
those values never matched the app's coarse filter. The former sub-region
groupings survive only as comments below for geographic context.
"""

# Keys are the exact uppercase `pln_area_n` values published by OneMap, so the
# table can be validated 1:1 against the official planning-area GeoJSON.
PLANNING_AREA_TO_REGION = {
    # --- CCR (Core Central Region) ---
    "DOWNTOWN CORE": "CCR",
    "NEWTON": "CCR",
    "ORCHARD": "CCR",
    "TANGLIN": "CCR",
    "RIVER VALLEY": "CCR",
    "BUKIT MERAH": "CCR",
    "MUSEUM": "CCR",
    "MARINA EAST": "CCR",
    "SOUTHERN ISLANDS": "CCR",  # Sentosa
    # --- RCR (Rest of Central Region) ---
    "QUEENSTOWN": "RCR",
    "GEYLANG": "RCR",
    "KALLANG": "RCR",
    "BISHAN": "RCR",
    "TOA PAYOH": "RCR",
    "MARINE PARADE": "RCR",
    "ROCHOR": "RCR",
    "OUTRAM": "RCR",
    "BUKIT TIMAH": "RCR",
    "MARINA SOUTH": "RCR",
    "SINGAPORE RIVER": "RCR",
    "STRAITS VIEW": "RCR",
    "PAYA LEBAR": "RCR",
    # --- OCR (former sub-region: East) ---
    "BEDOK": "OCR",
    "PASIR RIS": "OCR",
    "TAMPINES": "OCR",
    "CHANGI": "OCR",
    "CHANGI BAY": "OCR",
    # --- OCR (former sub-region: North-East) ---
    "ANG MO KIO": "OCR",
    "SERANGOON": "OCR",
    "HOUGANG": "OCR",
    "SENGKANG": "OCR",
    "PUNGGOL": "OCR",
    # --- OCR (former sub-region: North) ---
    "WOODLANDS": "OCR",
    "YISHUN": "OCR",
    "SEMBAWANG": "OCR",
    "MANDAI": "OCR",
    # --- OCR (former sub-region: West) ---
    "JURONG EAST": "OCR",
    "JURONG WEST": "OCR",
    "BUKIT BATOK": "OCR",
    "BUKIT PANJANG": "OCR",
    "CHOA CHU KANG": "OCR",
    "CLEMENTI": "OCR",
    "TENGAH": "OCR",
    "BOON LAY": "OCR",
    # --- OCR (former sub-region: Central) ---
    "NOVENA": "OCR",
    # --- OCR (never had a sub-region) ---
    "CENTRAL WATER CATCHMENT": "OCR",
    "LIM CHU KANG": "OCR",
    "NORTH-EASTERN ISLANDS": "OCR",
    "PIONEER": "OCR",
    "SELETAR": "OCR",
    "SIMPANG": "OCR",
    "SUNGEI KADUT": "OCR",
    "TUAS": "OCR",
    "WESTERN ISLANDS": "OCR",
    "WESTERN WATER CATCHMENT": "OCR",
}


def get_region_for_planning_area(planning_area: str) -> str | None:
    return PLANNING_AREA_TO_REGION.get(planning_area.strip().upper())
