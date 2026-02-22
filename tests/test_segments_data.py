"""
Tests for segments data generation.

Tests the generate_segments_data.py module which generates enhanced
segments data for the interactive dashboard.
"""

import pytest

from scripts.generate_segments_data import load_investment_clusters


def test_load_investment_clusters():
    """Test loading investment clusters from findings."""
    clusters = load_investment_clusters()

    assert isinstance(clusters, list)
    assert len(clusters) == 6

    # Check first cluster structure
    first_cluster = clusters[0]
    assert 'id' in first_cluster
    assert 'name' in first_cluster
    assert 'investmentType' in first_cluster
    assert 'metrics' in first_cluster
    assert 'characteristics' in first_cluster


def test_cluster_ids():
    """Test that all 6 cluster IDs are present."""
    clusters = load_investment_clusters()
    cluster_ids = {c['id'] for c in clusters}

    expected_ids = {
        'large_size_stable',
        'high_growth_recent',
        'speculator_hotspots',
        'declining_areas',
        'mid_tier_value',
        'premium_new_units'
    }

    assert cluster_ids == expected_ids
