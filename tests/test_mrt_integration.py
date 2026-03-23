#!/usr/bin/env python3
"""Tests for MRT distance integration with unified dataset."""

import logging
import pytest
from pathlib import Path

import pandas as pd

from scripts.core.config import Config
from scripts.core.mrt_distance import calculate_nearest_mrt, load_mrt_stations

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.slow
class TestMRTIntegration:
    """Integration tests for MRT distance calculations on housing data."""

    @pytest.fixture(scope="class")
    def unified_dataset(self):
        """Load unified dataset for testing."""
        unified_path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
        if not unified_path.exists():
            pytest.skip(f"Unified dataset not found: {unified_path}")
        
        df = pd.read_parquet(unified_path)
        return df

    @pytest.fixture(scope="class")
    def mrt_stations(self):
        """Load MRT stations data."""
        return load_mrt_stations()

    def test_unified_dataset_structure(self, unified_dataset):
        """Test that unified dataset has required columns."""
        assert "lat" in unified_dataset.columns
        assert "lon" in unified_dataset.columns
        assert "address" in unified_dataset.columns
        assert len(unified_dataset) > 0

    def test_mrt_integration_on_sample(self, unified_dataset, mrt_stations):
        """Test MRT distance calculation on sample of housing data."""
        # Check if lat/lon exist
        if "lat" not in unified_dataset.columns or "lon" not in unified_dataset.columns:
            pytest.skip("Dataset missing lat/lon columns")

        # Filter to properties with coordinates
        has_coords = unified_dataset["lat"].notna() & unified_dataset["lon"].notna()
        
        if has_coords.sum() == 0:
            pytest.skip("No properties with coordinates found")

        # Test on a small sample first
        sample_size = min(100, has_coords.sum())
        sample_df = unified_dataset[has_coords].head(sample_size).copy()

        # Calculate nearest MRT
        sample_with_mrt = calculate_nearest_mrt(
            sample_df, mrt_stations_df=mrt_stations, show_progress=False
        )

        # Verify results
        assert len(sample_with_mrt) == len(sample_df)
        assert "nearest_mrt_name" in sample_with_mrt.columns
        assert "nearest_mrt_distance" in sample_with_mrt.columns

        # Verify data quality
        assert sample_with_mrt["nearest_mrt_distance"].min() >= 0
        assert sample_with_mrt["nearest_mrt_distance"].max() > 0

    def test_mrt_distance_statistics(self, unified_dataset, mrt_stations):
        """Test MRT distance statistics are reasonable."""
        has_coords = unified_dataset["lat"].notna() & unified_dataset["lon"].notna()
        
        if has_coords.sum() < 10:
            pytest.skip("Insufficient properties with coordinates")

        sample_df = unified_dataset[has_coords].head(100).copy()
        sample_with_mrt = calculate_nearest_mrt(
            sample_df, mrt_stations_df=mrt_stations, show_progress=False
        )

        # Check distance statistics
        mean_dist = sample_with_mrt["nearest_mrt_distance"].mean()
        median_dist = sample_with_mrt["nearest_mrt_distance"].median()
        
        assert mean_dist > 0
        assert median_dist > 0
        assert median_dist <= mean_dist * 2  # Sanity check

    def test_mrt_proximity_analysis(self, unified_dataset, mrt_stations):
        """Test proximity analysis (within 500m, 1km)."""
        has_coords = unified_dataset["lat"].notna() & unified_dataset["lon"].notna()
        
        if has_coords.sum() < 10:
            pytest.skip("Insufficient properties with coordinates")

        sample_df = unified_dataset[has_coords].head(100).copy()
        sample_with_mrt = calculate_nearest_mrt(
            sample_df, mrt_stations_df=mrt_stations, show_progress=False
        )

        within_500m = (sample_with_mrt["nearest_mrt_distance"] <= 500).sum()
        within_1km = (sample_with_mrt["nearest_mrt_distance"] <= 1000).sum()

        assert within_500m >= 0
        assert within_1km >= within_500m
        assert within_1km <= len(sample_with_mrt)

    def test_mrt_station_distribution(self, unified_dataset, mrt_stations):
        """Test that multiple MRT stations are represented."""
        has_coords = unified_dataset["lat"].notna() & unified_dataset["lon"].notna()
        
        if has_coords.sum() < 10:
            pytest.skip("Insufficient properties with coordinates")

        sample_df = unified_dataset[has_coords].head(100).copy()
        sample_with_mrt = calculate_nearest_mrt(
            sample_df, mrt_stations_df=mrt_stations, show_progress=False
        )

        # Check that we have multiple different nearest stations
        unique_stations = sample_with_mrt["nearest_mrt_name"].nunique()
        assert unique_stations > 1
