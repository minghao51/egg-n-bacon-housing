"""Tests for utils/school_features.py and utils/geo.py (haversine)."""

import pandas as pd
import pytest

from egg_n_bacon_housing.utils import school_features
from egg_n_bacon_housing.utils.geo import haversine_distance

pytestmark = pytest.mark.unit


class TestHaversineDistance:
    def test_same_point_returns_zero(self):
        assert haversine_distance(1.3521, 103.8198, 1.3521, 103.8198) == pytest.approx(0.0, abs=1.0)

    def test_known_distance_marina_bay_to_sentosa(self):
        dist = haversine_distance(1.2816, 103.8636, 1.2494, 103.8303)
        assert dist == pytest.approx(5150.0, rel=0.05)

    def test_lat_first_signature(self):
        zero_dist = haversine_distance(1.0, 103.0, 1.0, 103.0)
        assert zero_dist == pytest.approx(0.0, abs=1.0)

    def test_antipodal_distance(self):
        dist = haversine_distance(0, 0, 0, 180)
        assert dist == pytest.approx(20015115.0, rel=0.01)

    def test_singapore_north_to_south(self):
        dist = haversine_distance(1.4708, 103.8198, 1.2025, 103.8198)
        assert dist == pytest.approx(29900.0, rel=0.05)


class TestCalculateAccessibilityScore:
    def test_zero_distance_returns_quality_normalized(self):
        score = school_features.calculate_accessibility_score(0, 8.0)
        assert score == pytest.approx(0.8)

    def test_large_distance_decays_to_zero(self):
        score = school_features.calculate_accessibility_score(3000, 10.0)
        assert score < 0.01

    def test_higher_quality_higher_score(self):
        close = school_features.calculate_accessibility_score(500, 5.0)
        high = school_features.calculate_accessibility_score(500, 10.0)
        assert high > close

    def test_closer_distance_higher_score(self):
        near = school_features.calculate_accessibility_score(100, 8.0)
        far = school_features.calculate_accessibility_score(1500, 8.0)
        assert near > far


class TestCalculatePrimaryQualityScore:
    def test_all_flags_max_score(self):
        row = pd.Series({"gep": "Yes", "sap": "Yes", "tier": 1, "popularity_p2b": "High"})
        score = school_features.calculate_primary_quality_score(row)
        assert score == pytest.approx(8.0)

    def test_no_flags_min_score(self):
        row = pd.Series({"gep": "No", "sap": "No", "tier": 3, "popularity_p2b": None})
        score = school_features.calculate_primary_quality_score(row)
        assert score == pytest.approx(1.0)

    def test_tier2_intermediate(self):
        row = pd.Series({"gep": "No", "sap": "No", "tier": 2, "popularity_p2b": None})
        score = school_features.calculate_primary_quality_score(row)
        assert score == pytest.approx(2.0)

    def test_score_capped_at_10(self):
        row = pd.Series({"gep": "Yes", "sap": "Yes", "tier": 1, "popularity_p2b": "High"})
        score = school_features.calculate_primary_quality_score(row)
        assert score == pytest.approx(8.0)
        assert score <= 10.0


class TestCalculateSecondaryQualityScore:
    def test_ip_sap_autonomous_tier1(self):
        row = pd.Series(
            {
                "ip": "Yes",
                "sap": "Yes",
                "autonomous": "Yes",
                "tier": 1,
                "ip_cutoff_2026": "4-6",
            }
        )
        score = school_features.calculate_secondary_quality_score(row)
        assert score >= 9.0
        assert score <= 10.0

    def test_no_flags(self):
        row = pd.Series(
            {
                "ip": "No",
                "sap": "No",
                "autonomous": "No",
                "tier": 3,
                "ip_cutoff_2026": None,
            }
        )
        score = school_features.calculate_secondary_quality_score(row)
        assert score == pytest.approx(1.0)


class TestInitializeSchoolColumns:
    def test_creates_expected_column_count(self):
        df = pd.DataFrame({"lat": [1.35], "lon": [103.82]})
        levels = ["PRIMARY", "SECONDARY (S1-S5)"]
        result = school_features._initialize_school_columns(df, levels)
        assert "nearest_schoolPRIMARY_dist" in result.columns
        assert "nearest_schoolSECONDARY_dist" in result.columns
        assert "schoolPRIMARY_count500m" in result.columns
        assert "school_within_1km" in result.columns
        assert "school_accessibility_score" in result.columns

    def test_count_columns_initialized_to_zero(self):
        df = pd.DataFrame({"lat": [1.35], "lon": [103.82]})
        result = school_features._initialize_school_columns(df, ["PRIMARY"])
        assert result["schoolPRIMARY_count500m"].iloc[0] == 0
        assert result["school_within_2km"].iloc[0] == 0

    def test_quality_columns_initialized_to_zero(self):
        df = pd.DataFrame({"lat": [1.35], "lon": [103.82]})
        result = school_features._initialize_school_columns(df, ["PRIMARY"])
        assert result["school_accessibility_score"].iloc[0] == 0.0
        assert result["school_primary_quality_score"].iloc[0] == 0.0


class TestGetSchoolAttributes:
    def test_extracts_basic_attributes(self):
        school = pd.Series(
            {
                "school_name": "Test School",
                "type_code": "GOV",
                "dgp_code": "NORTH",
                "zone_code": "Z1",
                "nature_code": "COED",
                "mrt_desc": "MRT",
                "sap_ind": "Yes",
                "autonomous_ind": "No",
                "gifted_ind": "Yes",
                "ip_ind": "No",
            }
        )
        attrs = school_features._get_school_attributes(school)
        assert attrs["name"] == "Test School"
        assert attrs["type"] == "GOV"
        assert attrs["sap"] is True
        assert attrs["autonomous"] is False
        assert attrs["gifted"] is True
        assert attrs["ip"] is False

    def test_missing_indicators_return_none(self):
        school = pd.Series({"school_name": "X"})
        attrs = school_features._get_school_attributes(school)
        assert attrs["sap"] is None
        assert attrs["autonomous"] is None


class TestCreateUniqueLocationIndex:
    def test_deduplicates_identical_coords(self):
        df = pd.DataFrame({"lat": [1.35, 1.35, 1.36], "lon": [103.82, 103.82, 103.83]})
        unique, mapping = school_features._create_unique_location_index(df)
        assert len(unique) == 2
        assert len(mapping[0]) == 2
        assert len(mapping[1]) == 1

    def test_single_row(self):
        df = pd.DataFrame({"lat": [1.35], "lon": [103.82]})
        unique, mapping = school_features._create_unique_location_index(df)
        assert len(unique) == 1
        assert len(mapping[0]) == 1


class TestCalculateSchoolFeatures:
    @pytest.fixture
    def school_data(self):
        return pd.DataFrame(
            [
                {
                    "school_name": "Test Primary",
                    "latitude": 1.355,
                    "longitude": 103.825,
                    "mainlevel_code": "PRIMARY",
                    "type_code": "GOV",
                    "dgp_code": "CENTRAL",
                    "zone_code": "Z1",
                    "nature_code": "COED",
                    "mrt_desc": "MRT",
                    "sap_ind": "No",
                    "autonomous_ind": "No",
                    "gifted_ind": "No",
                    "ip_ind": "No",
                },
            ]
        )

    @pytest.fixture
    def property_data(self):
        return pd.DataFrame(
            [
                {"lat": 1.350, "lon": 103.820, "id": 1},
                {"lat": 1.360, "lon": 103.830, "id": 2},
            ]
        )

    def test_returns_dataframe_with_features(self, school_data, property_data, monkeypatch):
        monkeypatch.setattr(
            school_features, "load_school_tiers", lambda: (pd.DataFrame(), pd.DataFrame())
        )
        result = school_features.calculate_school_features(property_data, school_data)
        assert len(result) == 2
        assert "nearest_schoolPRIMARY_dist" in result.columns
        assert "school_accessibility_score" in result.columns

    def test_nearest_school_distance_positive(self, school_data, property_data, monkeypatch):
        monkeypatch.setattr(
            school_features, "load_school_tiers", lambda: (pd.DataFrame(), pd.DataFrame())
        )
        result = school_features.calculate_school_features(property_data, school_data)
        assert (result["nearest_schoolPRIMARY_dist"] > 0).all()

    def test_empty_schools_returns_input(self, monkeypatch):
        monkeypatch.setattr(
            school_features, "load_school_tiers", lambda: (pd.DataFrame(), pd.DataFrame())
        )
        props = pd.DataFrame([{"lat": 1.35, "lon": 103.82}])
        empty_schools = pd.DataFrame(columns=["latitude", "longitude", "mainlevel_code"])
        result = school_features.calculate_school_features(props, empty_schools)
        assert len(result) == 1

    def test_single_school_single_property(self, monkeypatch):
        monkeypatch.setattr(
            school_features, "load_school_tiers", lambda: (pd.DataFrame(), pd.DataFrame())
        )
        schools = pd.DataFrame(
            [
                {
                    "school_name": "S1",
                    "latitude": 1.35,
                    "longitude": 103.82,
                    "mainlevel_code": "PRIMARY",
                    "type_code": "GOV",
                    "dgp_code": "N",
                    "zone_code": "Z1",
                    "nature_code": "COED",
                    "mrt_desc": "",
                    "sap_ind": "No",
                    "autonomous_ind": "No",
                    "gifted_ind": "No",
                    "ip_ind": "No",
                }
            ]
        )
        props = pd.DataFrame([{"lat": 1.3501, "lon": 103.8201}])
        result = school_features.calculate_school_features(props, schools)
        assert result["nearest_schoolPRIMARY_dist"].iloc[0] < 100
