"""Tests for utils/school_features.py and utils/geo.py (haversine)."""

import pandas as pd
import pytest

from egg_n_bacon_housing.utils import school_features
from egg_n_bacon_housing.utils.geo import haversine_distance

pytestmark = pytest.mark.unit

# The only school columns any consumer reads (components/features.py derives
# dist_to_nearest_school as their min). Everything else was pruned.
EXPECTED_DIST_COLUMNS = [
    "nearest_schoolPRIMARY_dist",
    "nearest_schoolSECONDARY_dist",
    "nearest_schoolJUNIOR_dist",
]


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


class TestCalculateSchoolFeatures:
    @pytest.fixture
    def school_data(self):
        # One school per level at distinct known coordinates.
        return pd.DataFrame(
            [
                {
                    "school_name": "Test Primary",
                    "latitude": 1.355,
                    "longitude": 103.825,
                    "mainlevel_code": "PRIMARY",
                },
                {
                    "school_name": "Test Secondary",
                    "latitude": 1.340,
                    "longitude": 103.835,
                    "mainlevel_code": "SECONDARY (S1-S5)",
                },
                {
                    "school_name": "Test Junior College",
                    "latitude": 1.370,
                    "longitude": 103.800,
                    "mainlevel_code": "JUNIOR COLLEGE",
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

    def test_output_has_exactly_the_consumed_columns(self, school_data, property_data):
        """Only the three consumed distance columns may be added — attribute,
        count, and score columns were pruned."""
        result = school_features.calculate_school_features(property_data, school_data)

        added = [c for c in result.columns if c not in property_data.columns]
        assert sorted(added) == sorted(EXPECTED_DIST_COLUMNS)
        for pruned in (
            "nearest_schoolPRIMARY_name",
            "schoolPRIMARY_count500m",
            "school_within_1km",
            "school_accessibility_score",
            "school_primary_quality_score",
            "school_density_score",
        ):
            assert pruned not in result.columns

    def test_distances_match_brute_force_haversine(self, school_data, property_data):
        """Vectorized KD-tree results equal a brute-force nearest scan."""
        result = school_features.calculate_school_features(property_data, school_data)

        for _, prop in property_data.iterrows():
            for level, col in zip(
                school_features.SCHOOL_LEVELS, EXPECTED_DIST_COLUMNS, strict=True
            ):
                level_schools = school_data[school_data["mainlevel_code"] == level]
                expected = min(
                    haversine_distance(prop["lat"], prop["lon"], row["latitude"], row["longitude"])
                    for _, row in level_schools.iterrows()
                )
                assert result.iloc[int(prop["id"]) - 1][col] == pytest.approx(expected, rel=1e-6)

    def test_nearest_school_distance_positive(self, school_data, property_data):
        result = school_features.calculate_school_features(property_data, school_data)
        for col in EXPECTED_DIST_COLUMNS:
            assert (result[col] > 0).all()

    def test_duplicated_coordinates_get_identical_distances(self, school_data):
        """The unique-location mapping must fan results out to duplicate rows."""
        props = pd.DataFrame(
            [
                {"lat": 1.350, "lon": 103.820, "id": 1},
                {"lat": 1.350, "lon": 103.820, "id": 2},
                {"lat": 1.350, "lon": 103.820, "id": 3},
                {"lat": 1.360, "lon": 103.830, "id": 4},
            ]
        )
        result = school_features.calculate_school_features(props, school_data)

        for col in EXPECTED_DIST_COLUMNS:
            dup = result.loc[[0, 1, 2], col]
            assert dup.nunique() == 1
            assert result.loc[0, col] != result.loc[3, col]

    def test_row_order_and_count_preserved(self, school_data):
        props = pd.DataFrame(
            [
                {"lat": 1.36, "lon": 103.83, "id": "a"},
                {"lat": 1.35, "lon": 103.82, "id": "b"},
                {"lat": 1.34, "lon": 103.81, "id": "c"},
            ]
        )
        result = school_features.calculate_school_features(props, school_data)
        assert list(result["id"]) == ["a", "b", "c"]
        assert len(result) == 3

    def test_missing_level_leaves_column_na(self, school_data, property_data):
        schools = school_data[school_data["mainlevel_code"] != "JUNIOR COLLEGE"]
        result = school_features.calculate_school_features(property_data, schools)

        assert "nearest_schoolJUNIOR_dist" in result.columns
        assert result["nearest_schoolJUNIOR_dist"].isna().all()
        assert result["nearest_schoolPRIMARY_dist"].notna().all()

    def test_custom_levels_subset(self, school_data, property_data):
        result = school_features.calculate_school_features(property_data, school_data, ["PRIMARY"])
        assert "nearest_schoolPRIMARY_dist" in result.columns
        assert "nearest_schoolSECONDARY_dist" not in result.columns

    def test_rows_without_coordinates_get_na(self, school_data):
        props = pd.DataFrame(
            [
                {"lat": 1.350, "lon": 103.820, "id": 1},
                {"lat": pd.NA, "lon": 103.830, "id": 2},
                {"lat": 1.370, "lon": pd.NA, "id": 3},
            ]
        )
        result = school_features.calculate_school_features(props, school_data)

        for col in EXPECTED_DIST_COLUMNS:
            assert not pd.isna(result.loc[0, col])
            assert pd.isna(result.loc[1, col])
            assert pd.isna(result.loc[2, col])

    def test_empty_schools_returns_input_unchanged(self):
        props = pd.DataFrame([{"lat": 1.35, "lon": 103.82}])
        empty_schools = pd.DataFrame(columns=["latitude", "longitude", "mainlevel_code"])
        result = school_features.calculate_school_features(props, empty_schools)

        assert len(result) == 1
        assert list(result.columns) == ["lat", "lon"]

    def test_single_school_single_property(self):
        schools = pd.DataFrame(
            [
                {
                    "school_name": "S1",
                    "latitude": 1.35,
                    "longitude": 103.82,
                    "mainlevel_code": "PRIMARY",
                }
            ]
        )
        props = pd.DataFrame([{"lat": 1.3501, "lon": 103.8201}])
        result = school_features.calculate_school_features(props, schools)
        assert result["nearest_schoolPRIMARY_dist"].iloc[0] < 100

    def test_repository_param_removed(self):
        """WS17: the reserved repository param (unused since the scoring prune)
        is gone from the signature — no caller can pass it anymore."""
        import inspect

        params = inspect.signature(school_features.calculate_school_features).parameters
        assert "repository" not in params
        assert list(params) == ["properties_df", "schools_df", "levels"]


class TestSchoolQualityScores:
    """WO-11: 0-10 quality scores per data/manual/csv/school_scoring_methodology.md."""

    def _primary_tiers(self):
        return pd.DataFrame(
            [
                {
                    "school_name": "NANYANG PRIMARY SCHOOL",
                    "gep": "Yes",
                    "sap": "Yes",
                    "tier": 1,
                    "popularity_p2b": 1.5,
                },
                {
                    "school_name": "PLAIN PRIMARY SCHOOL",
                    "gep": "No",
                    "sap": "No",
                    "tier": 3,
                    "popularity_p2b": "n/a",
                },
            ]
        )

    def _secondary_tiers(self):
        return pd.DataFrame(
            [
                {
                    "school_name": "RAFFLES INSTITUTION",
                    "track": "IP",
                    "tier": 1,
                    "ip_cutoff_2026": "4-6",
                    "sap": "Yes",
                    "autonomous": "Yes",
                    "ip": "Yes",
                    "awards": "Premier boys school",
                },
            ]
        )

    def test_primary_score_math(self):
        primary, _ = school_features.calculate_school_quality_scores(
            self._primary_tiers(), pd.DataFrame()
        )
        # NANYANG: gep 2.5 + sap 2.0 + tier1 3.0 + popularity (1.5/3 capped)*0.5
        # = 0.25 → terms 7.75; + MIN(1, 7.75) = 1 → 8.75.
        assert primary.loc[0, "quality_score"] == pytest.approx(8.75)
        # PLAIN: tier3 1.0 only → terms 1.0; + MIN(1, 1.0) = 1.0 → 2.0.
        assert primary.loc[1, "quality_score"] == pytest.approx(2.0)

    def test_secondary_score_math_clips_at_ten(self):
        _, secondary = school_features.calculate_school_quality_scores(
            pd.DataFrame(), self._secondary_tiers()
        )
        # RAFFLES: ip 3 + sap 2 + autonomous 1.5 + tier1 3 + cutoff "4-6"
        # midpoint 5 → (10-5)/6*1.5 = 1.25 → terms 10.75; +1 → clipped to 10.
        assert secondary.loc[0, "quality_score"] == pytest.approx(10.0)

    def test_popularity_high_marker_maps_to_cap(self):
        tiers = pd.DataFrame(
            [
                {
                    "school_name": "HOT SCHOOL",
                    "gep": "No",
                    "sap": "No",
                    "tier": 2,
                    "popularity_p2b": "High",
                }
            ]
        )
        primary, _ = school_features.calculate_school_quality_scores(tiers, pd.DataFrame())
        # tier2 2.0 + popularity cap 1.0*0.5 = 0.5 → terms 2.5; +1 → 3.5.
        assert primary.loc[0, "quality_score"] == pytest.approx(3.5)

    def test_empty_frames_round_trip(self):
        primary, secondary = school_features.calculate_school_quality_scores(
            pd.DataFrame(), pd.DataFrame()
        )
        assert primary.empty and secondary.empty
        assert list(primary.columns) == ["school_name", "quality_score"]


class TestSchoolQualityFeatures:
    """WO-11: tier-weighted location features (top-tier distances + blend)."""

    LAT, LON = 1.300, 103.850

    def _schools(self):
        # A: tier-1 primary ~111m north of the property.
        # B: tier-1 secondary ~222m north.
        # C: unlisted secondary ~55m north (nearest secondary, quality 0).
        return pd.DataFrame(
            [
                {
                    "school_name": "TOP PRIMARY",
                    "latitude": 1.3010,
                    "longitude": 103.850,
                    "mainlevel_code": "PRIMARY",
                },
                {
                    "school_name": "TOP SECONDARY",
                    "latitude": 1.3020,
                    "longitude": 103.850,
                    "mainlevel_code": "SECONDARY (S1-S5)",
                },
                {
                    "school_name": "NOBODY SECONDARY",
                    "latitude": 1.3005,
                    "longitude": 103.850,
                    "mainlevel_code": "SECONDARY (S1-S5)",
                },
            ]
        )

    def _primary_tiers(self):
        return pd.DataFrame(
            [
                {
                    "school_name": "TOP PRIMARY",
                    "gep": "Yes",
                    "sap": "No",
                    "tier": 1,
                    "popularity_p2b": 1.2,
                },
                {
                    "school_name": "DISTANT PRIMARY",
                    "gep": "No",
                    "sap": "No",
                    "tier": 3,
                    "popularity_p2b": 1.0,
                },
            ]
        )

    def _secondary_tiers(self):
        return pd.DataFrame(
            [
                {
                    "school_name": "TOP SECONDARY",
                    "track": "IP",
                    "tier": 1,
                    "ip_cutoff_2026": "7-8",
                    "sap": "No",
                    "autonomous": "No",
                    "ip": "Yes",
                    "awards": "",
                }
            ]
        )

    def _props(self):
        return pd.DataFrame([{"lat": self.LAT, "lon": self.LON}])

    def test_quality_feature_columns_and_values(self):
        result = school_features.calculate_school_quality_features(
            self._props(), self._schools(), self._primary_tiers(), self._secondary_tiers()
        )

        for col in school_features.QUALITY_FEATURE_COLUMNS:
            assert col in result.columns, col

        dist_top_primary = haversine_distance(self.LAT, self.LON, 1.3010, 103.850)
        dist_top_secondary = haversine_distance(self.LAT, self.LON, 1.3020, 103.850)
        assert result.loc[0, "nearest_top_primary_school_dist"] == pytest.approx(
            dist_top_primary, rel=1e-3
        )
        # The unlisted nearer secondary must NOT win the tier-1 distance.
        assert result.loc[0, "nearest_top_secondary_school_dist"] == pytest.approx(
            dist_top_secondary, rel=1e-3
        )

        # Accessibility: primary nearest is TOP PRIMARY (only primary with
        # coords); q = 2.5 + 3.0 + (1.2/3)*0.5 = 5.7 → +1 → 6.7. Secondary
        # nearest is the unlisted school → q=0 → secondary contributes 0.
        q = 6.7
        d_pri = haversine_distance(self.LAT, self.LON, 1.3010, 103.850)
        expected = 0.4 * max(0.0, 1 - d_pri / 2000) * (1 + q / 10) * q / 10
        assert result.loc[0, "school_accessibility_score"] == pytest.approx(expected, rel=1e-3)

    def test_missing_tier1_level_keeps_column_na(self):
        secondary_only_tiers = pd.DataFrame()  # no primary tiers at all
        result = school_features.calculate_school_quality_features(
            self._props(), self._schools(), secondary_only_tiers, self._secondary_tiers()
        )
        assert result["nearest_top_primary_school_dist"].isna().all()

    def test_no_geocoded_schools_degrades_to_na(self):
        schools = self._schools().drop(columns=["latitude", "longitude"])
        result = school_features.calculate_school_quality_features(
            self._props(), schools, self._primary_tiers(), self._secondary_tiers()
        )
        for col in school_features.QUALITY_FEATURE_COLUMNS:
            assert result[col].isna().all(), col


class TestSecondaryPoolMoeLevelCodes:
    """Regression (live-run finding): MOE's directory codes IP and S1-S4
    schools differently from the tier tables — the secondary pool must span
    SECONDARY (S1-S5), SECONDARY (S1-S4), and MIXED LEVEL (S1-JC2), and
    tier names may be prefixes of directory names."""

    def test_mixed_level_ip_school_counts_as_secondary_tier1(self):
        # RAFFLES INSTITUTION: tier-1, MOE code MIXED LEVEL (S1-JC2).
        schools = pd.DataFrame(
            [
                {
                    "school_name": "RAFFLES INSTITUTION",
                    "latitude": 1.3010,
                    "longitude": 103.850,
                    "mainlevel_code": "MIXED LEVEL (S1-JC2)",
                },
                {
                    "school_name": "NOBODY SECONDARY SCHOOL",
                    "latitude": 1.3020,
                    "longitude": 103.850,
                    "mainlevel_code": "SECONDARY (S1-S5)",
                },
            ]
        )
        tiers = pd.DataFrame(
            [
                {
                    "school_name": "RAFFLES INSTITUTION",
                    "track": "IP",
                    "tier": 1,
                    "ip_cutoff_2026": "4-6",
                    "sap": "Yes",
                    "autonomous": "Yes",
                    "ip": "Yes",
                    "awards": "",
                }
            ]
        )
        props = pd.DataFrame([{"lat": 1.300, "lon": 103.850}])

        result = school_features.calculate_school_quality_features(
            props, schools, pd.DataFrame(), tiers
        )

        # Tier-1 distance must anchor on the IP school, not the nearer
        # unlisted SECONDARY (S1-S5) school.
        assert result.loc[0, "nearest_top_secondary_school_dist"] == pytest.approx(
            haversine_distance(1.300, 103.850, 1.3010, 103.850), rel=1e-3
        )
        # Its quality must flow into the blend (non-zero secondary score).
        assert result.loc[0, "school_accessibility_score"] > 0

    def test_s1_s4_school_counts_as_secondary(self):
        schools = pd.DataFrame(
            [
                {
                    "school_name": "RAFFLES GIRLS' SCHOOL (SECONDARY)",
                    "latitude": 1.3010,
                    "longitude": 103.850,
                    "mainlevel_code": "SECONDARY (S1-S4)",
                }
            ]
        )
        tiers = pd.DataFrame(
            [
                {
                    "school_name": "RAFFLES GIRLS' SCHOOL",  # prefix of directory name
                    "track": "IP",
                    "tier": 1,
                    "ip_cutoff_2026": "5-7",
                    "sap": "Yes",
                    "autonomous": "No",
                    "ip": "Yes",
                    "awards": "",
                }
            ]
        )
        props = pd.DataFrame([{"lat": 1.300, "lon": 103.850}])

        result = school_features.calculate_school_quality_features(
            props, schools, pd.DataFrame(), tiers
        )

        assert result.loc[0, "nearest_top_secondary_school_dist"] == pytest.approx(
            haversine_distance(1.300, 103.850, 1.3010, 103.850), rel=1e-3
        )
        # Prefix-matched tier-1 school contributes a non-zero blend score.
        assert result.loc[0, "school_accessibility_score"] > 0

    def test_prefix_fallback_quality_resolution(self):
        schools = pd.DataFrame(
            [
                {
                    "school_name": "NANYANG GIRLS' HIGH SCHOOL",  # tier says HIGH
                    "latitude": 1.3002,
                    "longitude": 103.850,
                    "mainlevel_code": "SECONDARY (S1-S4)",
                }
            ]
        )
        tiers = pd.DataFrame(
            [
                {
                    "school_name": "NANYANG GIRLS' HIGH",
                    "track": "IP",
                    "tier": 2,
                    "ip_cutoff_2026": "6-8",
                    "sap": "Yes",
                    "autonomous": "No",
                    "ip": "Yes",
                    "awards": "",
                }
            ]
        )
        props = pd.DataFrame([{"lat": 1.300, "lon": 103.850}])

        result = school_features.calculate_school_quality_features(
            props, schools, pd.DataFrame(), tiers
        )

        # Tier-2 school: no top-tier distance, but quality > 0 flows in.
        assert result["nearest_top_secondary_school_dist"].isna().all()
        assert result.loc[0, "school_accessibility_score"] > 0
