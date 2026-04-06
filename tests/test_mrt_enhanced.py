#!/usr/bin/env python3
"""Tests for enhanced MRT distance features with line information."""

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
class TestMRTEnhancedFeatures:
    """Integration tests for enhanced MRT distance calculations."""

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

    def test_mrt_stations_loaded(self, mrt_stations):
        """Test that MRT stations are loaded with line information."""
        assert len(mrt_stations) > 0
        assert "name" in mrt_stations.columns
        assert "line_names" in mrt_stations.columns
        assert "tier" in mrt_stations.columns
        assert "is_interchange" in mrt_stations.columns

    def test_enhanced_mrt_calculation(self, unified_dataset, mrt_stations):
        """Test enhanced MRT distance calculation on sample data."""
        # Filter to properties with coordinates
        has_coords = unified_dataset["lat"].notna() & unified_dataset["lon"].notna()
        
        if has_coords.sum() == 0:
            pytest.skip("No properties with coordinates found")

        # Test on a small sample
        sample_size = min(100, has_coords.sum())
        sample_df = unified_dataset[has_coords].head(sample_size).copy()

        # Calculate nearest MRT with enhanced features
        sample_with_mrt = calculate_nearest_mrt(
            sample_df, mrt_stations_df=mrt_stations, show_progress=False
        )

        # Verify enhanced columns exist
        assert "nearest_mrt_name" in sample_with_mrt.columns
        assert "nearest_mrt_distance" in sample_with_mrt.columns
        assert "nearest_mrt_line_names" in sample_with_mrt.columns
        assert "nearest_mrt_tier" in sample_with_mrt.columns
        assert "nearest_mrt_is_interchange" in sample_with_mrt.columns
        assert "nearest_mrt_score" in sample_with_mrt.columns

        # Verify data quality
        assert len(sample_with_mrt) == len(sample_df)
        assert sample_with_mrt["nearest_mrt_distance"].min() >= 0
        assert sample_with_mrt["nearest_mrt_tier"].isin([1, 2, 3]).all()

    def test_mrt_tier_distribution(self, unified_dataset, mrt_stations):
        """Test MRT tier distribution in sample data."""
        has_coords = unified_dataset["lat"].notna() & unified_dataset["lon"].notna()
        
        if has_coords.sum() < 10:
            pytest.skip("Insufficient properties with coordinates")

        sample_df = unified_dataset[has_coords].head(50).copy()
        sample_with_mrt = calculate_nearest_mrt(
            sample_df, mrt_stations_df=mrt_stations, show_progress=False
        )

        # Check tier distribution
        tier_counts = sample_with_mrt["nearest_mrt_tier"].value_counts()
        assert len(tier_counts) > 0
        assert all(tier in [1, 2, 3] for tier in tier_counts.index)

    def test_interchange_detection(self, unified_dataset, mrt_stations):
        """Test interchange station detection."""
        has_coords = unified_dataset["lat"].notna() & unified_dataset["lon"].notna()
        
        if has_coords.sum() < 10:
            pytest.skip("Insufficient properties with coordinates")

        sample_df = unified_dataset[has_coords].head(50).copy()
        sample_with_mrt = calculate_nearest_mrt(
            sample_df, mrt_stations_df=mrt_stations, show_progress=False
        )

        # Verify interchange flag exists and is boolean
        assert "nearest_mrt_is_interchange" in sample_with_mrt.columns
        assert sample_with_mrt["nearest_mrt_is_interchange"].dtype == bool

    def test_mrt_score_calculation(self, unified_dataset, mrt_stations):
        """Test MRT accessibility score calculation."""
        has_coords = unified_dataset["lat"].notna() & unified_dataset["lon"].notna()
        
        if has_coords.sum() < 10:
            pytest.skip("Insufficient properties with coordinates")

        sample_df = unified_dataset[has_coords].head(50).copy()
        sample_with_mrt = calculate_nearest_mrt(
            sample_df, mrt_stations_df=mrt_stations, show_progress=False
        )

        # Verify score exists and is numeric
        assert "nearest_mrt_score" in sample_with_mrt.columns
        assert sample_with_mrt["nearest_mrt_score"].notna().all()
        assert sample_with_mrt["nearest_mrt_score"].max() > 0
