#!/usr/bin/env python3
"""
Generate enhanced segments data for the interactive dashboard.

Integrates outputs from:
- Investment clusters (findings.md)
- Spatial clusters (spatial-autocorrelation.md)
- Spatial hotspots (spatial-hotspots.md)
- MRT impact (mrt-impact.md)
- School quality (school-quality.md)
"""

import gzip
import json

# Add project root to path
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_investment_clusters() -> list[dict[str, Any]]:
    """
    Load investment cluster data from findings analysis.

    Based on findings.md cluster analysis:
    - Large Size Stable (12.6%): High PSF ($570), stable yields (5.54%)
    - High Growth Recent (33.0%): Moderate PSF ($509), +24.4% YoY
    - Speculator Hotspots (5.7%): Premium PSF ($550), +83.9% YoY
    - Declining Areas (12.4%): Moderate PSF ($564), -3.6% YoY
    - Mid-Tier Value (25.3%): Affordable PSF ($463), 6.36% yields
    - Premium New Units (11.0%): High PSF ($826), 12.3% YoY
    """
    return [
        {
            "id": "large_size_stable",
            "name": "Large Size Stable",
            "description": "High PSF properties with stable rental yields for buy-and-hold investors",
            "investmentType": "yield",
            "clusterClassification": "HH",
            "metrics": {
                "avgPricePsf": 570,
                "avgYield": 5.54,
                "yoyGrowth": 12.0,
                "transactionCount": 114700,  # 12.6% of ~910K
                "marketShare": 0.126,
            },
            "characteristics": {
                "priceTier": "premium",
                "riskLevel": "low",
                "volatility": "low",
                "appreciationPotential": "moderate",
            },
            "propertyTypes": ["HDB", "Condominium"],
            "regions": ["CCR", "RCR"],
        },
        {
            "id": "high_growth_recent",
            "name": "High Growth Recent",
            "description": "Moderate PSF with exceptional YoY growth for growth-oriented investors",
            "investmentType": "growth",
            "clusterClassification": "HH",
            "metrics": {
                "avgPricePsf": 509,
                "avgYield": 5.2,
                "yoyGrowth": 24.4,
                "transactionCount": 300872,  # 33.0%
                "marketShare": 0.330,
            },
            "characteristics": {
                "priceTier": "moderate",
                "riskLevel": "medium",
                "volatility": "high",
                "appreciationPotential": "exceptional",
            },
            "propertyTypes": ["HDB", "Condominium"],
            "regions": ["RCR", "OCR"],
        },
        {
            "id": "speculator_hotspots",
            "name": "Speculator Hotspots",
            "description": "Premium PSF with massive YoY growth for short-term flips",
            "investmentType": "speculative",
            "clusterClassification": "HH",
            "metrics": {
                "avgPricePsf": 550,
                "avgYield": 4.8,
                "yoyGrowth": 83.9,
                "transactionCount": 51957,  # 5.7%
                "marketShare": 0.057,
            },
            "characteristics": {
                "priceTier": "premium",
                "riskLevel": "very_high",
                "volatility": "high",
                "appreciationPotential": "high",
            },
            "propertyTypes": ["Condominium", "HDB"],
            "regions": ["CCR", "RCR"],
        },
        {
            "id": "declining_areas",
            "name": "Declining Areas",
            "description": "Moderate PSF with negative growth - avoid or contrarian plays",
            "investmentType": "value",
            "clusterClassification": "LH",
            "metrics": {
                "avgPricePsf": 564,
                "avgYield": 5.0,
                "yoyGrowth": -3.6,
                "transactionCount": 112943,  # 12.4%
                "marketShare": 0.124,
            },
            "characteristics": {
                "priceTier": "moderate",
                "riskLevel": "high",
                "volatility": "low",
                "appreciationPotential": "low",
            },
            "propertyTypes": ["HDB", "Condominium"],
            "regions": ["OCR", "RCR"],
        },
        {
            "id": "mid_tier_value",
            "name": "Mid-Tier Value",
            "description": "Affordable PSF with highest yields for rental income focus",
            "investmentType": "yield",
            "clusterClassification": "LL",
            "metrics": {
                "avgPricePsf": 463,
                "avgYield": 6.36,
                "yoyGrowth": 8.5,
                "transactionCount": 230685,  # 25.3%
                "marketShare": 0.253,
            },
            "characteristics": {
                "priceTier": "affordable",
                "riskLevel": "low",
                "volatility": "low",
                "appreciationPotential": "moderate",
            },
            "propertyTypes": ["HDB"],
            "regions": ["OCR"],
        },
        {
            "id": "premium_new_units",
            "name": "Premium New Units",
            "description": "High PSF luxury segment with moderate growth",
            "investmentType": "luxury",
            "clusterClassification": "HH",
            "metrics": {
                "avgPricePsf": 826,
                "avgYield": 3.8,
                "yoyGrowth": 12.3,
                "transactionCount": 100297,  # 11.0%
                "marketShare": 0.110,
            },
            "characteristics": {
                "priceTier": "luxury",
                "riskLevel": "medium",
                "volatility": "moderate",
                "appreciationPotential": "moderate",
            },
            "propertyTypes": ["Condominium", "EC"],
            "regions": ["CCR", "RCR"],
        },
    ]


def load_spatial_clusters() -> dict[str, Any]:
    """Load spatial cluster data from LISA analysis."""
    # TODO: Implement in next task
    return {}


def load_hotspot_data() -> dict[str, Any]:
    """Load hotspot data from Getis-Ord Gi* analysis."""
    # TODO: Implement in next task
    return {}


def load_mrt_analysis() -> dict[str, Any]:
    """Load MRT impact analysis by property type and region."""
    # TODO: Implement in next task
    return {}


def load_school_impact() -> dict[str, Any]:
    """Load school quality impact analysis by region."""
    # TODO: Implement in next task
    return {}


def map_to_spatial_cluster(segment: dict[str, Any], spatial_data: dict[str, Any]) -> str:
    """Map segment to spatial cluster classification."""
    # TODO: Implement
    return "HH"


def get_persistence(classification: str) -> float:
    """Get persistence probability for cluster classification."""
    persistence_map = {
        "HH": 0.60,  # Average of 58-62%
        "LH": 0.33,  # 33% upside to hotspot
        "LL": 0.50,  # 50% remain declining
    }
    return persistence_map.get(classification, 0.50)


def determine_mrt_sensitivity(segment: dict[str, Any], mrt_data: dict[str, Any]) -> str:
    """Determine MRT sensitivity based on segment property types."""
    # TODO: Implement based on property types
    return "moderate"


def determine_school_quality(segment: dict[str, Any], school_data: dict[str, Any]) -> str:
    """Determine school quality profile for segment."""
    # TODO: Implement based on planning areas
    return "mixed"


def get_areas_in_segment(segment: dict[str, Any], spatial_data: dict[str, Any]) -> list[str]:
    """Get list of planning areas in this segment."""
    # TODO: Implement based on spatial clustering
    return []


def generate_implications(segment: dict[str, Any]) -> dict[str, str]:
    """Generate persona-specific implications for segment."""
    # TODO: Implement based on segment characteristics
    return {
        "investor": "",
        "firstTimeBuyer": "",
        "upgrader": "",
    }


def generate_insight_cards(
    spatial_data: dict[str, Any],
    mrt_data: dict[str, Any],
    school_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate insight cards from analytics."""
    # TODO: Implement with actual insights from analytics docs
    return []


def enrich_planning_areas(
    spatial_data: dict[str, Any],
    mrt_data: dict[str, Any],
    school_data: dict[str, Any],
) -> dict[str, Any]:
    """Enrich planning areas with spatial/MRT/school data."""
    # TODO: Implement
    return {}


def save_gzipped_json(data: dict[str, Any], output_path: Path) -> None:
    """Save data as gzipped JSON."""
    json_str = json.dumps(data, indent=2)
    compressed = gzip.compress(json_str.encode('utf-8'))
    output_path.write_bytes(compressed)
    print(f"✅ Saved to {output_path}")


def generate_segments_data() -> dict[str, Any]:
    """Generate comprehensive segments data."""
    print("Generating enhanced segments data...")

    # 1. Load analysis outputs
    print("  Loading analytics outputs...")
    segments = load_investment_clusters()
    spatial_data = load_spatial_clusters()
    hotspot_data = load_hotspot_data()  # TODO: Will be used in future for hotspot integration  # noqa: F841
    mrt_data = load_mrt_analysis()
    school_data = load_school_impact()

    # 2. Enrich segments
    print("  Enriching segments with spatial/MRT/school data...")
    for segment in segments:
        segment['spatialClassification'] = map_to_spatial_cluster(segment, spatial_data)
        segment['persistenceProbability'] = get_persistence(segment['clusterClassification'])
        segment['mrtSensitivity'] = determine_mrt_sensitivity(segment, mrt_data)
        segment['schoolQuality'] = determine_school_quality(segment, school_data)
        segment['planningAreas'] = get_areas_in_segment(segment, spatial_data)
        segment['implications'] = generate_implications(segment)

    # 3. Enrich planning areas
    print("  Enriching planning areas...")
    planning_areas = enrich_planning_areas(spatial_data, mrt_data, school_data)

    # 4. Generate insight cards
    print("  Generating insight cards...")
    insights = generate_insight_cards(spatial_data, mrt_data, school_data)

    # 5. Compile output
    output = {
        'segments': segments,
        'planningAreas': planning_areas,
        'insights': insights,
        'lastUpdated': datetime.now().isoformat(),
        'version': '1.0.0'
    }

    # 6. Save to file
    output_path = Path('app/public/data/segments_enhanced.json.gz')
    save_gzipped_json(output, output_path)

    print("\n✅ Segments data generated successfully!")
    print(f"   - {len(segments)} segments")
    print(f"   - {len(planning_areas)} planning areas")
    print(f"   - {len(insights)} insight cards")
    print(f"   - Saved to {output_path}")

    return output


if __name__ == '__main__':
    generate_segments_data()
