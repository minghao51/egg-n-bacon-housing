"""WO-4 + FU-1: regional mapping covers all 55 official OneMap planning areas.

FU-1 normalized every mapping value to the coarse URA market segments
(``"CCR"`` / ``"RCR"`` / ``"OCR"``) for parity with the app's ``Region``
type, which exact-match filters on those three strings.
"""

import json
from pathlib import Path

import pytest

from egg_n_bacon_housing.utils.regional_mapping import (
    PLANNING_AREA_TO_REGION,
    get_region_for_planning_area,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[1]
_GEOMETRY_PATH = (
    _REPO_ROOT / "data" / "manual" / "geojsons" / "onemap_planning_area_polygon.geojson"
)

# Embedded fixture: the 55 official OneMap `pln_area_n` values (verified
# against data/manual/geojsons/onemap_planning_area_polygon.geojson). The
# GeoJSON is R2-synced manual content and may be absent in CI, so the literal
# list keeps the coverage test runnable everywhere; a separate test cross-checks
# the two when the file exists.
_OFFICIAL_PLANNING_AREAS = {
    "ANG MO KIO",
    "BEDOK",
    "BISHAN",
    "BOON LAY",
    "BUKIT BATOK",
    "BUKIT MERAH",
    "BUKIT PANJANG",
    "BUKIT TIMAH",
    "CENTRAL WATER CATCHMENT",
    "CHANGI",
    "CHANGI BAY",
    "CHOA CHU KANG",
    "CLEMENTI",
    "DOWNTOWN CORE",
    "GEYLANG",
    "HOUGANG",
    "JURONG EAST",
    "JURONG WEST",
    "KALLANG",
    "LIM CHU KANG",
    "MANDAI",
    "MARINA EAST",
    "MARINA SOUTH",
    "MARINE PARADE",
    "MUSEUM",
    "NEWTON",
    "NORTH-EASTERN ISLANDS",
    "NOVENA",
    "ORCHARD",
    "OUTRAM",
    "PASIR RIS",
    "PAYA LEBAR",
    "PIONEER",
    "PUNGGOL",
    "QUEENSTOWN",
    "RIVER VALLEY",
    "ROCHOR",
    "SELETAR",
    "SEMBAWANG",
    "SENGKANG",
    "SERANGOON",
    "SIMPANG",
    "SINGAPORE RIVER",
    "SOUTHERN ISLANDS",
    "STRAITS VIEW",
    "SUNGEI KADUT",
    "TAMPINES",
    "TANGLIN",
    "TENGAH",
    "TOA PAYOH",
    "TUAS",
    "WESTERN ISLANDS",
    "WESTERN WATER CATCHMENT",
    "WOODLANDS",
    "YISHUN",
}

# The 13 planning areas added by WO-4, with their URA market-segment regions.
_NEWLY_ADDED_EXPECTED_REGIONS = {
    "CENTRAL WATER CATCHMENT": "OCR",
    "LIM CHU KANG": "OCR",
    "MARINA EAST": "CCR",
    "NORTH-EASTERN ISLANDS": "OCR",
    "PAYA LEBAR": "RCR",
    "PIONEER": "OCR",
    "SELETAR": "OCR",
    "SIMPANG": "OCR",
    "SOUTHERN ISLANDS": "CCR",
    "SUNGEI KADUT": "OCR",
    "TUAS": "OCR",
    "WESTERN ISLANDS": "OCR",
    "WESTERN WATER CATCHMENT": "OCR",
}


def _official_names_from_geojson() -> set[str]:
    with _GEOMETRY_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    return {str(feature["properties"]["pln_area_n"]) for feature in payload["features"]}


class TestOfficialPlanningAreaCoverage:
    def test_mapping_covers_every_official_planning_area(self):
        unmapped = sorted(
            name for name in _OFFICIAL_PLANNING_AREAS if get_region_for_planning_area(name) is None
        )
        assert unmapped == []

    def test_mapping_keys_exactly_match_official_planning_areas(self):
        """No dead keys: every key must be an official pln_area_n value."""
        assert set(PLANNING_AREA_TO_REGION) == _OFFICIAL_PLANNING_AREAS

    @pytest.mark.skipif(not _GEOMETRY_PATH.exists(), reason="OneMap GeoJSON not synced from R2")
    def test_embedded_fixture_matches_geojson(self):
        assert _OFFICIAL_PLANNING_AREAS == _official_names_from_geojson()

    @pytest.mark.skipif(not _GEOMETRY_PATH.exists(), reason="OneMap GeoJSON not synced from R2")
    def test_every_geojson_planning_area_maps_to_a_region(self):
        for name in sorted(_official_names_from_geojson()):
            assert get_region_for_planning_area(name) is not None, name


class TestRegionAssignments:
    def test_ccr_spot_check(self):
        assert get_region_for_planning_area("ORCHARD") == "CCR"

    def test_rcr_spot_check(self):
        assert get_region_for_planning_area("QUEENSTOWN") == "RCR"

    def test_ocr_spot_check(self):
        assert get_region_for_planning_area("BEDOK") == "OCR"

    def test_all_values_are_coarse_market_segments(self):
        """FU-1: values are exactly the app Region type strings (app parity)."""
        assert set(PLANNING_AREA_TO_REGION.values()) == {"CCR", "RCR", "OCR"}

    def test_newly_added_planning_areas(self):
        for name, expected in _NEWLY_ADDED_EXPECTED_REGIONS.items():
            assert get_region_for_planning_area(name) == expected, name


class TestLookupNormalization:
    def test_lowercase_and_surrounding_whitespace_are_tolerated(self):
        assert get_region_for_planning_area("  orchard ") == "CCR"
        assert get_region_for_planning_area("queenstown") == "RCR"
        assert get_region_for_planning_area("Marina East") == "CCR"

    def test_unknown_planning_area_returns_none(self):
        assert get_region_for_planning_area("Unknown Area") is None
        assert get_region_for_planning_area("") is None
