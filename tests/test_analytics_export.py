"""
Tests for analytics data export functionality.

Tests the Python scripts that generate analytics JSON files
for the web dashboard.
"""

import json

import pytest

from scripts.core.data_helpers import load_parquet
from scripts.prepare_analytics_json import (
    export_all_analytics,
    generate_feature_impact_json,
    generate_predictive_analytics_json,
    generate_spatial_analysis_json,
    sanitize_for_json,
)


class TestAnalyticsDataExport:
    """Test suite for analytics JSON export functionality."""

    def test_sanitize_for_json_handles_nan(self):
        """Test that NaN and Inf values are converted to None."""
        import numpy as np

        # Test NaN
        assert sanitize_for_json(float('nan')) is None
        assert sanitize_for_json(np.nan) is None

        # Test Inf
        assert sanitize_for_json(float('inf')) is None
        assert sanitize_for_json(np.inf) is None

        # Test -Inf
        assert sanitize_for_json(float('-inf')) is None
        assert sanitize_for_json(-np.inf) is None

        # Test normal values
        assert sanitize_for_json(1.5) == 1.5
        assert sanitize_for_json(0) == 0

    def test_sanitize_for_json_handles_nested_structures(self):
        """Test that nested structures are sanitized recursively."""
        import numpy as np

        data = {
            "normal": 1.5,
            "nan_value": np.nan,
            "nested": {
                "deep_nan": np.nan,
                "normal": 2.0,
            },
            "list": [1.0, np.nan, 2.0],
        }

        result = sanitize_for_json(data)

        assert result["normal"] == 1.5
        assert result["nan_value"] is None
        assert result["nested"]["deep_nan"] is None
        assert result["nested"]["normal"] == 2.0
        assert result["list"][0] == 1.0
        assert result["list"][1] is None
        assert result["list"][2] == 2.0

    def test_generate_spatial_analysis_json_structure(self):
        """Test that spatial analysis JSON has correct structure."""
        result = generate_spatial_analysis_json()

        # Check metadata
        assert "metadata" in result
        assert "generated_at" in result["metadata"]
        assert "data_version" in result["metadata"]
        assert "methodology" in result["metadata"]

        # Check planning areas
        assert "planning_areas" in result
        assert isinstance(result["planning_areas"], dict)

    def test_generate_spatial_analysis_json_with_data(self):
        """Test spatial analysis JSON with actual data structure."""
        result = generate_spatial_analysis_json()

        # If there's data, check the structure
        if result["planning_areas"]:
            # Check a sample area
            area_name = list(result["planning_areas"].keys())[0]
            area_data = result["planning_areas"][area_name]

            # Verify all required keys exist
            assert "hotspot" in area_data
            assert "lisa_cluster" in area_data
            assert "neighborhood_effect" in area_data

            # Verify hotspot structure
            hotspot = area_data["hotspot"]
            assert "z_score" in hotspot
            assert "p_value" in hotspot
            assert "confidence" in hotspot
            assert "classification" in hotspot

            # Verify LISA cluster structure
            lisa = area_data["lisa_cluster"]
            assert "type" in lisa
            assert "yoy_appreciation" in lisa
            assert "persistence_rate" in lisa
            assert "transition_probabilities" in lisa

    def test_generate_feature_impact_json_structure(self):
        """Test that feature impact JSON has correct structure."""
        result = generate_feature_impact_json()

        # Check metadata
        assert "metadata" in result
        assert "generated_at" in result["metadata"]
        assert "data_version" in result["metadata"]

        # Check planning areas
        assert "planning_areas" in result
        assert isinstance(result["planning_areas"], dict)

    def test_generate_feature_impact_json_with_data(self):
        """Test feature impact JSON with actual data structure."""
        result = generate_feature_impact_json()

        if result["planning_areas"]:
            area_name = list(result["planning_areas"].keys())[0]
            area_data = result["planning_areas"][area_name]

            # Verify all required keys exist
            assert "mrt_impact" in area_data
            assert "school_quality" in area_data
            assert "amenity_score" in area_data

            # Verify MRT impact structure
            mrt = area_data["mrt_impact"]
            assert "hdb_sensitivity_psf_per_100m" in mrt
            assert "condo_sensitivity_psf_per_100m" in mrt
            assert "cbd_distance_km" in mrt

            # Verify school quality structure
            school = area_data["school_quality"]
            assert "primary_school_score" in school
            assert "secondary_school_score" in school
            assert "weighted_score" in school

    def test_generate_predictive_analytics_json_structure(self):
        """Test that predictive analytics JSON has correct structure."""
        result = generate_predictive_analytics_json()

        # Check metadata
        assert "metadata" in result
        assert "generated_at" in result["metadata"]
        assert "forecast_horizon" in result["metadata"]

        # Check planning areas
        assert "planning_areas" in result
        assert isinstance(result["planning_areas"], dict)

    def test_generate_predictive_analytics_json_with_data(self):
        """Test predictive analytics JSON with actual data structure."""
        result = generate_predictive_analytics_json()

        if result["planning_areas"]:
            area_name = list(result["planning_areas"].keys())[0]
            area_data = result["planning_areas"][area_name]

            # Verify all required keys exist
            assert "price_forecast" in area_data
            assert "policy_risk" in area_data
            assert "lease_arbitrage" in area_data

            # Verify price forecast structure
            forecast = area_data["price_forecast"]
            assert "projected_change_pct" in forecast
            assert "confidence_interval_lower" in forecast
            assert "confidence_interval_upper" in forecast
            assert "signal" in forecast
            assert forecast["signal"] in ["BUY", "HOLD", "SELL"]

    @pytest.mark.integration
    def test_export_all_analytics_creates_files(self, tmp_path):
        """Test that export_all_analytics creates JSON files."""

        # Create output directory in temp path
        output_dir = tmp_path / "data" / "analytics"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Run export with custom output directory
        export_all_analytics(output_dir=output_dir)

        # Verify files were created
        assert (output_dir / "spatial_analysis.json").exists()
        assert (output_dir / "feature_impact.json").exists()
        assert (output_dir / "predictive_analytics.json").exists()

    def test_json_files_are_valid_json(self, tmp_path):
        """Test that exported JSON files are valid JSON."""
        from scripts.prepare_analytics_json import (
            generate_feature_impact_json,
            generate_predictive_analytics_json,
            generate_spatial_analysis_json,
        )

        # Generate data
        spatial = generate_spatial_analysis_json()
        feature = generate_feature_impact_json()
        predictive = generate_predictive_analytics_json()

        # Verify they can be serialized to JSON

        # Should not raise exceptions
        json.dumps(spatial)
        json.dumps(feature)
        json.dumps(predictive)

    @pytest.mark.slow
    def test_json_files_load_from_parquets_if_available(self):
        """Test that JSON files load actual data when parquets exist."""
        # This test is slow and only runs if parquet files exist
        try:
            df = load_parquet("L3_unified_dataset")
            has_data = not df.empty
        except (FileNotFoundError, ValueError):
            has_data = False
            pytest.skip("No L3_unified_dataset available")

        if has_data:
            result = generate_spatial_analysis_json()
            # Should have some planning areas if data exists
            assert len(result["planning_areas"]) > 0


class TestAnalyticsJSONValidation:
    """Test suite for validating analytics JSON schemas."""

    def test_spatial_analysis_required_fields(self):
        """Test that spatial analysis has all required fields."""
        from scripts.prepare_analytics_json import generate_spatial_analysis_json

        result = generate_spatial_analysis_json()

        required_metadata_fields = [
            "generated_at",
            "data_version",
            "methodology",
        ]

        for field in required_metadata_fields:
            assert field in result["metadata"]

    def test_feature_impact_required_fields(self):
        """Test that feature impact has all required fields."""
        from scripts.prepare_analytics_json import generate_feature_impact_json

        result = generate_feature_impact_json()

        required_metadata_fields = [
            "generated_at",
            "data_version",
        ]

        for field in required_metadata_fields:
            assert field in result["metadata"]

    def test_predictive_analytics_required_fields(self):
        """Test that predictive analytics has all required fields."""
        from scripts.prepare_analytics_json import generate_predictive_analytics_json

        result = generate_predictive_analytics_json()

        required_metadata_fields = [
            "generated_at",
            "forecast_horizon",
            "model_r2",
        ]

        for field in required_metadata_fields:
            assert field in result["metadata"]


class TestCompressionScript:
    """Test suite for JSON compression functionality."""

    @pytest.mark.integration
    def test_compress_json_files_creates_gz_files(self, tmp_path):
        """Test that compression script creates .gz files."""
        from scripts.compress_json_files import compress_file

        # Create a larger test JSON file (small files may not compress well due to gzip overhead)
        test_file = tmp_path / "test.json"
        test_data = '{"test": "' + 'data' * 100 + '"}'  # Larger file that will compress
        test_file.write_text(test_data)

        # Compress it
        original_size, compressed_size = compress_file(test_file)

        # Verify .gz file was created
        gz_file = tmp_path / "test.json.gz"
        assert gz_file.exists()
        assert compressed_size < original_size  # Should be smaller (for files large enough)

    def test_compress_file_returns_size_reduction(self, tmp_path):
        """Test that compress_file returns correct size information."""
        from scripts.compress_json_files import compress_file

        # Create a test JSON file (large enough to compress well)
        test_file = tmp_path / "test.json"
        test_data = '{"test": "' + 'data' * 200 + '"}'  # Larger file for better compression
        test_file.write_text(test_data)

        # Compress it
        original_size, compressed_size = compress_file(test_file)

        # Verify sizes
        assert original_size > 0
        assert compressed_size > 0
        assert compressed_size < original_size

        # Check compression ratio (should have significant reduction for this size)
        reduction = (1 - compressed_size / original_size) * 100
        assert reduction > 10  # Should have at least 10% compression
