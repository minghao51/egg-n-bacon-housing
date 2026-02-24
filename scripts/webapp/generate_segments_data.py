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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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
    """
    Load spatial cluster data from LISA analysis.

    Based on spatial-autocorrelation.md:
    - HH (hotspots): 47.1% of areas, 12.7% YoY appreciation
    - LH (lagging): 50.0% of areas, 11.3% YoY appreciation
    - LL (coldspots): 2.9% of areas, ~10% YoY appreciation
    """
    return {
        "clusters": {
            "HH": {
                "count": 16,
                "percentage": 47.1,
                "avgAppreciation": 12.7,
                "persistence": 0.60,  # 58-62% average
            },
            "LH": {
                "count": 17,
                "percentage": 50.0,
                "avgAppreciation": 11.3,
                "persistence": 0.33,  # 33% upside
            },
            "LL": {
                "count": 1,
                "percentage": 2.9,
                "avgAppreciation": 10.0,
                "persistence": 0.50,  # 50% remain declining
            },
        },
        "planning_areas": [
            # HH Hotspots (Central-south)
            {"name": "Bishan", "region": "RCR", "cluster": "HH", "cbd_distance": 4.2},
            {"name": "Toa Payoh", "region": "RCR", "cluster": "HH", "cbd_distance": 3.8},
            {"name": "Queenstown", "region": "RCR", "cluster": "HH", "cbd_distance": 3.5},
            {"name": "Serangoon", "region": "RCR", "cluster": "HH", "cbd_distance": 5.5},
            {"name": "Bukit Timah", "region": "CCR", "cluster": "HH", "cbd_distance": 6.0},
            {"name": "Orchard", "region": "CCR", "cluster": "HH", "cbd_distance": 1.5},
            {"name": "Marina South", "region": "CCR", "cluster": "HH", "cbd_distance": 1.0},
            {"name": "Tanglin", "region": "CCR", "cluster": "HH", "cbd_distance": 2.5},
            {"name": "Newton", "region": "RCR", "cluster": "HH", "cbd_distance": 2.8},
            {"name": "River Valley", "region": "RCR", "cluster": "HH", "cbd_distance": 2.2},
            {"name": "Clementi", "region": "RCR", "cluster": "HH", "cbd_distance": 5.5},
            {"name": "Ang Mo Kio", "region": "OCR", "cluster": "HH", "cbd_distance": 8.0},
            {"name": "Bukit Merah", "region": "RCR", "cluster": "HH", "cbd_distance": 2.5},
            {"name": "Kallang", "region": "RCR", "cluster": "HH", "cbd_distance": 3.0},
            {"name": "Geylang", "region": "RCR", "cluster": "HH", "cbd_distance": 3.5},
            {"name": "Marine Parade", "region": "RCR", "cluster": "HH", "cbd_distance": 4.0},
            # LH Lagging Areas (Northern)
            {"name": "Woodlands", "region": "OCR", "cluster": "LH", "cbd_distance": 12.0},
            {"name": "Yishun", "region": "OCR", "cluster": "LH", "cbd_distance": 10.5},
            {"name": "Sembawang", "region": "OCR", "cluster": "LH", "cbd_distance": 13.0},
            {"name": "Punggol", "region": "OCR", "cluster": "LH", "cbd_distance": 9.0},
            {"name": "Sengkang", "region": "OCR", "cluster": "LH", "cbd_distance": 8.5},
            {"name": "Choa Chu Kang", "region": "OCR", "cluster": "LH", "cbd_distance": 11.0},
            {"name": "Jurong West", "region": "OCR", "cluster": "LH", "cbd_distance": 10.0},
            {"name": "Tampines", "region": "OCR", "cluster": "LH", "cbd_distance": 7.5},
            {"name": "Pasir Ris", "region": "OCR", "cluster": "LH", "cbd_distance": 10.5},
            {"name": "Hougang", "region": "OCR", "cluster": "LH", "cbd_distance": 8.0},
            {"name": "Bedok", "region": "OCR", "cluster": "LH", "cbd_distance": 6.5},
            {"name": "Jurong East", "region": "OCR", "cluster": "LH", "cbd_distance": 9.5},
            {"name": "Bukit Panjang", "region": "OCR", "cluster": "LH", "cbd_distance": 9.0},
            {"name": "Bukit Batok", "region": "OCR", "cluster": "LH", "cbd_distance": 9.5},
            {"name": "Yishun", "region": "OCR", "cluster": "LH", "cbd_distance": 10.5},
            {"name": "Woodlands", "region": "OCR", "cluster": "LH", "cbd_distance": 12.0},
            {"name": "Sembawang", "region": "OCR", "cluster": "LH", "cbd_distance": 13.0},
            # LL Coldspots
            {"name": "Lim Chu Kang", "region": "OCR", "cluster": "LL", "cbd_distance": 18.0},
        ],
    }


def load_hotspot_data() -> dict[str, Any]:
    """Load hotspot data from Getis-Ord Gi* analysis."""
    # TODO: Implement in next task
    return {}


def load_mrt_analysis() -> dict[str, Any]:
    """
    Load MRT impact analysis by property type and region.

    Based on mrt-impact.md:
    - HDB: $1.28/100m average premium
    - Condominium: $19.20-$45.62/100m (15x more sensitive)
    - EC: Volatile (+$6 to -$34/100m post-COVID)
    """
    return {
        "by_property_type": {
            "HDB": {
                "premium": -1.28,  # Per 100m
                "sensitivity": "low",
                "appreciation_impact": 0.35,  # 35% higher for <500m
            },
            "Condominium": {
                "premium": -35.0,  # Average across analyses
                "sensitivity": "high",
                "sensitivity_ratio": 15,  # 15x vs HDB
                "appreciation_impact": 0.35,
            },
            "EC": {
                "premium": -20.0,  # Volatile post-COVID
                "sensitivity": "volatile",
                "premium_shift": -1790,  # % change post-COVID
                "appreciation_impact": 0.25,
            },
        },
        "by_town": {
            # Top positive premiums
            "Central Area": {"premium": 59.19, "mean_price": 903},
            "Serangoon": {"premium": 12.91, "mean_price": 566},
            "Bishan": {"premium": 5.88, "mean_price": 644},
            "Pasir Ris": {"premium": 1.84, "mean_price": 510},
            "Jurong East": {"premium": 0.73, "mean_price": 486},
            # Negative premiums
            "Bukit Merah": {"premium": -12.57, "mean_price": 725},
            "Punggol": {"premium": -10.15, "mean_price": 571},
            "Sengkang": {"premium": -16.88, "mean_price": 558},
            "Geylang": {"premium": -20.54, "mean_price": 584},
            "Marine Parade": {"premium": -38.54, "mean_price": 629},
        },
        "by_region": {
            "CCR": {
                "mrt_premium": -4.86,
                "cbd_premium": -43.05,
                "mean_price": 746,
            },
            "RCR": {
                "mrt_premium": -1.68,
                "cbd_premium": -24.64,
                "mean_price": 562,
            },
            "OCR": {
                "mrt_premium": -0.62,
                "cbd_premium": -8.86,
                "mean_price": 490,
            },
        },
        "cbd_explained_variance": 0.226,  # 22.6%
        "mrt_additional_variance": 0.0078,  # 0.78%
    }


def load_school_impact() -> dict[str, Any]:
    """
    Load school quality impact analysis by region.

    Based on school-quality.md:
    - OCR: +$9.63 PSF positive premium
    - RCR: -$23.67 PSF negative effect
    - CCR: ~$0 PSF no effect
    """
    return {
        "by_region": {
            "OCR": {
                "premium": 9.63,  # Per PSF
                "interpretation": "Positive premium for families",
            },
            "RCR": {
                "premium": -23.67,
                "interpretation": "Negative effect (confounded with other factors)",
            },
            "CCR": {
                "premium": 0.0,
                "interpretation": "No effect (location dominates)",
            },
        },
        "by_tier": {
            "tier_1": {
                "premium_psf": 9.66,  # Per quality point
                "avg_score": 7.5,
                "total_premium_1000sqft": 29000,  # ~$29K vs tier 3
            },
            "tier_2": {
                "premium_psf": 9.66,
                "avg_score": 6.0,
                "total_premium_1000sqft": 14500,
            },
            "tier_3": {
                "premium_psf": 9.66,
                "avg_score": 4.5,
                "total_premium_1000sqft": 0,  # Baseline
            },
        },
        "primary_importance": 11.5,  # Feature importance %
        "secondary_importance": 21.8,  # #1 predictor of appreciation
        "one_km_effect": -79.47,  # PSF (RDD causal estimate)
    }


def map_to_spatial_cluster(segment: dict[str, Any], spatial_data: dict[str, Any]) -> str:
    """Map segment to spatial cluster classification."""
    # Use the predefined clusterClassification from segment
    return segment.get('clusterClassification', 'HH')


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
    prop_types = segment.get('propertyTypes', [])

    if 'Condominium' in prop_types:
        return 'high'
    elif 'EC' in prop_types:
        return 'moderate'  # Volatile, but moderate on average
    else:
        return 'low'  # HDB


def determine_school_quality(segment: dict[str, Any], school_data: dict[str, Any]) -> str:
    """Determine school quality profile for segment."""
    # Based on regions where segment operates
    regions = segment.get('regions', [])

    if 'CCR' in regions:
        return 'tier_1'  # International schools, top local schools
    elif 'OCR' in regions and segment['investmentType'] == 'value':
        return 'tier_2'  # Family-friendly suburban areas
    else:
        return 'mixed'


def get_areas_in_segment(segment: dict[str, Any], spatial_data: dict[str, Any]) -> list[str]:
    """Get list of planning areas in this segment."""
    # Map segments to planning areas based on region and cluster
    segment_regions = segment.get('regions', [])
    segment_cluster = segment.get('clusterClassification', 'HH')

    matching_areas = []
    for area in spatial_data['planning_areas']:
        if area['region'] in segment_regions and area['cluster'] == segment_cluster:
            matching_areas.append(area['name'])

    return matching_areas[:10]  # Return top 10


def generate_implications(segment: dict[str, Any]) -> dict[str, str]:
    """Generate persona-specific implications for segment."""
    inv_type = segment['investmentType']
    metrics = segment['metrics']

    implications = {
        "investor": "",
        "firstTimeBuyer": "",
        "upgrader": "",
    }

    if inv_type == "yield":
        implications["investor"] = f"Buy and hold for steady income. Target {metrics['avgYield']:.1f}% yield."
        implications["firstTimeBuyer"] = "Suitable for long-term holds if yield covers mortgage."
        implications["upgrader"] = "Consider for rental income from current unit."

    elif inv_type == "growth":
        implications["investor"] = f"Growth investing for capital appreciation. {metrics['yoyGrowth']:.1f}% YoY growth."
        implications["firstTimeBuyer"] = "Risky for first-time buyers. Consider if holding 10+ years."
        implications["upgrader"] = "Good for upgrading to high-appreciation areas if timing is right."

    elif inv_type == "value":
        implications["investor"] = "Value play with potential upside. Monitor for turnaround signals."
        implications["firstTimeBuyer"] = "Affordable option with long-term potential if area improves."
        implications["upgrader"] = "Get more space for budget, but verify growth catalysts."

    elif inv_type == "luxury":
        implications["investor"] = "Luxury segment for high-net-worth investors. Capital preservation focus."
        implications["firstTimeBuyer"] = "Generally not suitable for first-time buyers due to high entry."
        implications["upgrader"] = "Consider for lifestyle upgrade if budget permits."

    elif inv_type == "speculative":
        implications["investor"] = "Short-term flips only. High risk, high reward. Market timing critical."
        implications["firstTimeBuyer"] = "Avoid - too volatile for first-time buyers."
        implications["upgrader"] = "Not recommended - timing mismatch with upgrade needs."

    else:  # balanced/default
        implications["investor"] = "Balanced approach with moderate growth and yield."
        implications["firstTimeBuyer"] = "Good balance of affordability and potential."
        implications["upgrader"] = "Solid choice for steady appreciation with reasonable entry cost."

    return implications


def generate_insight_cards(
    spatial_data: dict[str, Any],
    mrt_data: dict[str, Any],
    school_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate insight cards from analytics."""
    return [
        {
            "id": "condo_mrt_sensitivity",
            "title": "Condos are 15x More MRT-Sensitive Than HDB",
            "content": (
                "Condo MRT premium: $35/100m vs HDB: $5/100m. "
                "Prioritize MRT proximity for condos, but focus on CBD distance and lease for HDB."
            ),
            "source": "mrt-impact.md",
            "relevantFor": ["investor", "first-time-buyer", "upgrader"],
            "propertyTypes": ["Condominium", "HDB"],
            "personaApplicability": {
                "all": "optional",
                "investor": "critical",
                "first-time-buyer": "helpful",
                "upgrader": "helpful",
            },
            "learnMoreUrl": "/analytics/mrt-impact",
        },
        {
            "id": "hotspot_persistence",
            "title": "Hotspots Have 58-62% Persistence Probability",
            "content": (
                "Once an area becomes a hotspot (HH cluster), there's a 58-62% chance "
                "it remains a hotspot year-over-year. Offers relatively predictable appreciation for investors."
            ),
            "source": "spatial-autocorrelation.md",
            "relevantFor": ["investor"],
            "segments": ["high_growth_recent", "large_size_stable"],
            "personaApplicability": {
                "all": "optional",
                "investor": "critical",
                "first-time-buyer": "helpful",
                "upgrader": "helpful",
            },
            "learnMoreUrl": "/analytics/spatial-autocorrelation",
        },
        {
            "id": "school_premiums_by_region",
            "title": "School Premiums Vary Dramatically by Region",
            "content": (
                "OCR shows positive school premium (+$9.63 PSF), RCR shows negative effect "
                "(-$23.67 PSF), CCR shows no effect. Location matters more than school access."
            ),
            "source": "school-quality.md",
            "relevantFor": ["first-time-buyer", "upgrader"],
            "personaApplicability": {
                "all": "optional",
                "investor": "helpful",
                "first-time-buyer": "critical",
                "upgrader": "helpful",
            },
            "learnMoreUrl": "/analytics/school-quality",
        },
        {
            "id": "cbd_vs_mrt",
            "title": "CBD Distance Explains 22.6% of Price Variation",
            "content": (
                "Distance to city center explains 22.6% of price variation, while MRT access "
                "adds only 0.78%. The 'MRT premium' is actually measuring CBD proximity."
            ),
            "source": "findings.md",
            "relevantFor": ["investor", "first-time-buyer", "upgrader"],
            "personaApplicability": {
                "all": "helpful",
                "investor": "critical",
                "first-time-buyer": "helpful",
                "upgrader": "helpful",
            },
            "learnMoreUrl": "/analytics/findings",
        },
    ]


def enrich_planning_areas(
    spatial_data: dict[str, Any],
    mrt_data: dict[str, Any],
    school_data: dict[str, Any],
) -> dict[str, Any]:
    """Enrich planning areas with spatial/MRT/school data."""
    enriched = {}

    for area in spatial_data['planning_areas']:
        name = area['name']
        region = area['region']
        cluster = area['cluster']

        # Get MRT premium for this town (if available)
        mrt_premium = mrt_data['by_town'].get(name, {}).get('premium', 0)

        # Determine MRT sensitivity
        mrt_sensitivity = "moderate"
        if abs(mrt_premium) > 20:
            mrt_sensitivity = "high"
        elif abs(mrt_premium) < 5:
            mrt_sensitivity = "low"

        # Get school premium for region
        school_premium = school_data['by_region'][region]['premium']

        # Determine school tier based on region and cluster
        school_tier = "mixed"
        if region == "CCR":
            school_tier = "tier_1"  # International schools
        elif cluster == "HH" and region == "OCR":
            school_tier = "tier_2"

        enriched[name] = {
            "name": name,
            "region": region,
            "spatialCluster": cluster,
            "hotspotConfidence": "99%" if cluster == "HH" else "95%" if cluster == "LH" else "not_significant",
            "persistenceProbability": spatial_data['clusters'][cluster]['persistence'],
            "mrtPremium": mrt_premium,
            "mrtSensitivity": mrt_sensitivity,
            "cbdDistance": area['cbd_distance'],
            "schoolTier": school_tier,
            "schoolPremium": school_premium,
            "forecast6m": 0.0,  # TODO: Add from forecast data
            "avgPricePsf": mrt_data['by_town'].get(name, {}).get('mean_price', 500),
            "avgYield": 5.0,  # TODO: Calculate from data
            "segments": [],  # Will be filled later
        }

    return enriched


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

    # Link segments to planning areas (reverse mapping)
    print("  Linking segments to planning areas...")
    for segment in segments:
        for area_name in segment['planningAreas']:
            if area_name in planning_areas:
                if segment['id'] not in planning_areas[area_name]['segments']:
                    planning_areas[area_name]['segments'].append(segment['id'])

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
