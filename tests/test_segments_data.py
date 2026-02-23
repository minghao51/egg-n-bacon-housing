"""
Tests for segments data generation.

Tests the generate_segments_data.py module which generates enhanced
segments data for the interactive dashboard.
"""

import pytest

from scripts.generate_segments_data import (
    load_investment_clusters,
    load_spatial_clusters,
    load_mrt_analysis,
    load_school_impact,
    generate_insight_cards,
    enrich_planning_areas,
    map_to_spatial_cluster,
    get_persistence,
    determine_mrt_sensitivity,
    determine_school_quality,
    get_areas_in_segment,
    generate_implications,
)


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


def test_load_spatial_clusters():
    """Test loading spatial clusters from LISA analysis."""
    spatial_data = load_spatial_clusters()

    assert 'planning_areas' in spatial_data
    assert 'clusters' in spatial_data
    assert isinstance(spatial_data['planning_areas'], list)

    # Check that some known areas are present
    area_names = {a['name'] for a in spatial_data['planning_areas']}
    assert 'Bishan' in area_names
    assert 'Toa Payoh' in area_names


def test_load_mrt_analysis():
    """Test loading MRT impact analysis by property type."""
    mrt_data = load_mrt_analysis()

    assert 'by_property_type' in mrt_data
    assert 'by_town' in mrt_data
    assert 'by_region' in mrt_data

    # Check property type sensitivity
    by_type = mrt_data['by_property_type']
    assert 'HDB' in by_type
    assert 'Condominium' in by_type
    assert 'EC' in by_type

    # Condo should be more sensitive than HDB
    condo_sensitivity = abs(by_type['Condominium']['premium'])
    hdb_sensitivity = abs(by_type['HDB']['premium'])
    ratio = condo_sensitivity / hdb_sensitivity
    assert ratio > 10  # At least 10x more sensitive


def test_mrt_town_data():
    """Test MRT premiums by town."""
    mrt_data = load_mrt_analysis()

    town_data = mrt_data['by_town']

    # Central Area should have highest premium
    assert 'Central Area' in town_data
    assert town_data['Central Area']['premium'] > 50

    # Marine Parade should have negative premium
    assert 'Marine Parade' in town_data
    assert town_data['Marine Parade']['premium'] < 0


def test_load_school_impact():
    """Test loading school quality impact by region."""
    school_data = load_school_impact()

    assert 'by_region' in school_data
    assert 'by_tier' in school_data

    # OCR should have positive premium
    assert school_data['by_region']['OCR']['premium'] > 0

    # RCR should have negative premium
    assert school_data['by_region']['RCR']['premium'] < 0

    # CCR should be near zero
    assert abs(school_data['by_region']['CCR']['premium']) < 5


def test_school_tier_impact():
    """Test school tier premium calculations."""
    school_data = load_school_impact()

    by_tier = school_data['by_tier']

    # Tier 1 should have highest premium
    assert by_tier['tier_1']['premium_psf'] > 0
    assert by_tier['tier_1']['total_premium_1000sqft'] > by_tier['tier_3']['total_premium_1000sqft']


def test_generate_insight_cards():
    """Test generating insight cards from analytics."""
    spatial_data = load_spatial_clusters()
    mrt_data = load_mrt_analysis()
    school_data = load_school_impact()

    insights = generate_insight_cards(spatial_data, mrt_data, school_data)

    assert len(insights) >= 4

    # Check required insight
    condo_insight = next((i for i in insights if i['id'] == 'condo_mrt_sensitivity'), None)
    assert condo_insight is not None
    # Check that content mentions condos and MRT
    assert 'Condo' in condo_insight['content'] and 'MRT' in condo_insight['content']
    assert condo_insight['source'] == 'mrt-impact.md'


def test_insight_structure():
    """Test insight card structure."""
    spatial_data = load_spatial_clusters()
    mrt_data = load_mrt_analysis()
    school_data = load_school_impact()

    insights = generate_insight_cards(spatial_data, mrt_data, school_data)

    for insight in insights:
        assert 'id' in insight
        assert 'title' in insight
        assert 'content' in insight
        assert 'source' in insight
        assert 'relevantFor' in insight
        assert 'personaApplicability' in insight


def test_enrich_planning_areas():
    """Test enriching planning areas with spatial/MRT/school data."""
    spatial_data = load_spatial_clusters()
    mrt_data = load_mrt_analysis()
    school_data = load_school_impact()

    areas = enrich_planning_areas(spatial_data, mrt_data, school_data)

    assert 'Bishan' in areas
    assert 'Toa Payoh' in areas

    bishan = areas['Bishan']
    assert bishan['region'] == 'RCR'
    assert bishan['spatialCluster'] == 'HH'
    assert 'mrtPremium' in bishan
    assert 'schoolTier' in bishan
    assert 'segments' in bishan


def test_segment_enrichment():
    """Test segment enrichment with spatial/MRT/school data."""
    segments = load_investment_clusters()
    spatial_data = load_spatial_clusters()
    mrt_data = load_mrt_analysis()
    school_data = load_school_impact()

    # Test first segment
    segment = segments[0]

    cluster = map_to_spatial_cluster(segment, spatial_data)
    assert cluster in ['HH', 'LH', 'LL']

    persistence = get_persistence(cluster)
    assert 0 <= persistence <= 1

    mrt_sens = determine_mrt_sensitivity(segment, mrt_data)
    assert mrt_sens in ['low', 'moderate', 'high']

    school_qual = determine_school_quality(segment, school_data)
    assert school_qual in ['tier_1', 'tier_2', 'tier_3', 'mixed']

    areas = get_areas_in_segment(segment, spatial_data)
    assert isinstance(areas, list)

    impl = generate_implications(segment)
    assert 'investor' in impl
    assert 'firstTimeBuyer' in impl
    assert 'upgrader' in impl
