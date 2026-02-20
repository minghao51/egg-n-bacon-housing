# tests/core/test_regional_mapping.py
from scripts.core.regional_mapping import get_region_for_planning_area


def test_ccr_planning_areas():
    """Test CCR planning areas mapped correctly."""
    ccr_areas = ["Downtown", "Newton", "Orchard", "Marina Bay", "Tanglin", "Bukit Merah"]
    for area in ccr_areas:
        assert get_region_for_planning_area(area) == "CCR"


def test_ocr_east_planning_areas():
    """Test OCR East planning areas mapped correctly."""
    east_areas = ["Bedok", "Pasir Ris", "Tampines", "Changi"]
    for area in east_areas:
        assert get_region_for_planning_area(area) == "OCR East"


def test_unknown_area_returns_none():
    """Test unknown planning area returns None."""
    assert get_region_for_planning_area("UnknownArea") is None


def test_all_planning_areas_have_regions():
    """Test all common planning areas are mapped."""
    from scripts.core.regional_mapping import get_all_regional_mappings

    mappings = get_all_regional_mappings()
    assert len(mappings) > 50  # Should cover most planning areas
    assert "Downtown" in mappings
    assert "Bedok" in mappings
