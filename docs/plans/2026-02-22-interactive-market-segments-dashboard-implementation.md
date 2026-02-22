# Interactive Market Segments Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the segments dashboard from a simple scatter plot into an interactive property discovery tool with multi-dimensional segmentation (investment clusters, spatial clusters, MRT/CBD, school quality), persona-based guidance, and comprehensive segment comparison.

**Architecture:**
- **Backend:** Python script generates enhanced JSON data from 5 analytics sources (investment clusters, spatial autocorrelation, hotspots, MRT impact, school quality)
- **Frontend:** React components with 3-tab interface (Discover, Compare, Details), filter sidebar, persona presets, and interactive visualizations using Recharts
- **State Management:** React hooks for filter state, segment matching, and data loading
- **Data Flow:** Analytics → Python pipeline → segments_enhanced.json.gz → React components → User interactions

**Tech Stack:**
- Python 3.11+, pandas, gzip for data generation
- React 19, TypeScript, Recharts, Tailwind CSS for frontend
- Astro framework for SSR and routing

---

## Phase 1: Data Foundation (Week 1-2)

### Task 1: Create TypeScript types for segments data

**Files:**
- Create: `app/src/types/segments.ts`

**Step 1: Write the type definitions**

```typescript
// Segment types for the enhanced dashboard

export type InvestmentType = 'yield' | 'growth' | 'value' | 'balanced' | 'luxury' | 'speculative';
export type SpatialCluster = 'HH' | 'LH' | 'LL';
export type PriceTier = 'affordable' | 'moderate' | 'premium' | 'luxury';
export type RiskLevel = 'low' | 'medium' | 'high' | 'very_high';
export type Volatility = 'low' | 'moderate' | 'high';
export type AppreciationPotential = 'low' | 'moderate' | 'high' | 'exceptional';
export type Region = 'CCR' | 'RCR' | 'OCR';
export type PropertyType = 'HDB' | 'Condominium' | 'EC';
export type SchoolTier = 'tier_1' | 'tier_2' | 'tier_3' | 'mixed';
export type MrtSensitivity = 'low' | 'moderate' | 'high';
export type Persona = 'all' | 'investor' | 'first-time-buyer' | 'upgrader';
export type InvestmentGoal = 'yield' | 'growth' | 'value' | 'balanced';
export type TimeHorizon = 'short' | 'medium' | 'long';

export interface SegmentMetrics {
  avgPricePsf: number;
  avgYield: number;
  yoyGrowth: number;
  transactionCount: number;
  marketShare: number;
}

export interface SegmentCharacteristics {
  priceTier: PriceTier;
  riskLevel: RiskLevel;
  volatility: Volatility;
  appreciationPotential: AppreciationPotential;
}

export interface SegmentImplications {
  investor: string;
  firstTimeBuyer: string;
  upgrader: string;
}

export interface Segment {
  id: string;
  name: string;
  description: string;
  investmentType: InvestmentType;
  clusterClassification: SpatialCluster;
  persistenceProbability: number;
  metrics: SegmentMetrics;
  characteristics: SegmentCharacteristics;
  implications: SegmentImplications;
  planningAreas: string[];
  regions: Region[];
  propertyTypes: PropertyType[];
  spatialClassification: SpatialCluster;
  mrtSensitivity: MrtSensitivity;
  schoolQuality: SchoolTier;
  riskFactors: string[];
  opportunities: string[];
}

export interface PlanningArea {
  name: string;
  region: Region;
  spatialCluster: SpatialCluster;
  hotspotConfidence: '99%' | '95%' | 'not_significant';
  persistenceProbability: number;
  mrtPremium: number;
  mrtSensitivity: MrtSensitivity;
  cbdDistance: number;
  schoolTier: SchoolTier;
  schoolPremium: number;
  forecast6m: number;
  avgPricePsf: number;
  avgYield: number;
  segments: string[];
}

export type PersonaApplicability = 'critical' | 'helpful' | 'optional';

export interface Insight {
  id: string;
  title: string;
  content: string;
  source: string;
  relevantFor: Persona[];
  propertyTypes?: PropertyType[];
  segments?: string[];
  personaApplicability: Record<Persona, PersonaApplicability>;
  learnMoreUrl?: string;
}

export interface SegmentsData {
  segments: Segment[];
  planningAreas: Record<string, PlanningArea>;
  insights: Insight[];
  lastUpdated: string;
  version: string;
}

export interface FilterState {
  investmentGoal: InvestmentGoal | null;
  budgetRange: [number, number];
  propertyTypes: PropertyType[];
  locations: Region[];
  timeHorizon: TimeHorizon | null;
}

export interface PersonaPreset {
  filters: Partial<FilterState>;
  priorityMetrics: string[];
  defaultInsights: string[];
}
```

**Step 2: Verify file created**

Run: `ls -la app/src/types/segments.ts`
Expected: File exists

**Step 3: Commit**

```bash
git add app/src/types/segments.ts
git commit -m "feat(types): add segment types for enhanced dashboard"
```

---

### Task 2: Create segments data generator script stub

**Files:**
- Create: `scripts/generate_segments_data.py`

**Step 1: Write the script structure with imports**

```python
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

import json
import gzip
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.core.config import Config


def load_investment_clusters() -> List[Dict[str, Any]]:
    """Load investment cluster data from findings analysis."""
    # TODO: Implement in next task
    return []


def load_spatial_clusters() -> Dict[str, Any]:
    """Load spatial cluster data from LISA analysis."""
    # TODO: Implement in next task
    return {}


def load_hotspot_data() -> Dict[str, Any]:
    """Load hotspot data from Getis-Ord Gi* analysis."""
    # TODO: Implement in next task
    return {}


def load_mrt_analysis() -> Dict[str, Any]:
    """Load MRT impact analysis by property type and region."""
    # TODO: Implement in next task
    return {}


def load_school_impact() -> Dict[str, Any]:
    """Load school quality impact analysis by region."""
    # TODO: Implement in next task
    return {}


def map_to_spatial_cluster(segment: Dict[str, Any], spatial_data: Dict[str, Any]) -> str:
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


def determine_mrt_sensitivity(segment: Dict[str, Any], mrt_data: Dict[str, Any]) -> str:
    """Determine MRT sensitivity based on segment property types."""
    # TODO: Implement based on property types
    return "moderate"


def determine_school_quality(segment: Dict[str, Any], school_data: Dict[str, Any]) -> str:
    """Determine school quality profile for segment."""
    # TODO: Implement based on planning areas
    return "mixed"


def get_areas_in_segment(segment: Dict[str, Any], spatial_data: Dict[str, Any]) -> List[str]:
    """Get list of planning areas in this segment."""
    # TODO: Implement based on spatial clustering
    return []


def generate_implications(segment: Dict[str, Any]) -> Dict[str, str]:
    """Generate persona-specific implications for segment."""
    # TODO: Implement based on segment characteristics
    return {
        "investor": "",
        "firstTimeBuyer": "",
        "upgrader": "",
    }


def generate_insight_cards(
    spatial_data: Dict[str, Any],
    mrt_data: Dict[str, Any],
    school_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Generate insight cards from analytics."""
    # TODO: Implement with actual insights from analytics docs
    return []


def enrich_planning_areas(
    spatial_data: Dict[str, Any],
    mrt_data: Dict[str, Any],
    school_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Enrich planning areas with spatial/MRT/school data."""
    # TODO: Implement
    return {}


def save_gzipped_json(data: Dict[str, Any], output_path: Path) -> None:
    """Save data as gzipped JSON."""
    json_str = json.dumps(data, indent=2)
    compressed = gzip.compress(json_str.encode('utf-8'))
    output_path.write_bytes(compressed)
    print(f"✅ Saved to {output_path}")


def generate_segments_data() -> Dict[str, Any]:
    """Generate comprehensive segments data."""
    print("Generating enhanced segments data...")

    # 1. Load analysis outputs
    print("  Loading analytics outputs...")
    segments = load_investment_clusters()
    spatial_data = load_spatial_clusters()
    hotspot_data = load_hotspot_data()
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

    print(f"\n✅ Segments data generated successfully!")
    print(f"   - {len(segments)} segments")
    print(f"   - {len(planning_areas)} planning areas")
    print(f"   - {len(insights)} insight cards")
    print(f"   - Saved to {output_path}")

    return output


if __name__ == '__main__':
    generate_segments_data()
```

**Step 2: Make script executable**

Run: `chmod +x scripts/generate_segments_data.py`
Expected: No error

**Step 3: Verify script syntax**

Run: `uv run python scripts/generate_segments_data.py`
Expected: Script runs but returns empty data (stubs not implemented yet)

**Step 4: Commit**

```bash
git add scripts/generate_segments_data.py
git commit -m "feat(scripts): add segments data generator script stub"
```

---

### Task 3: Implement investment clusters loader

**Files:**
- Modify: `scripts/generate_segments_data.py`
- Test: `tests/test_segments_data.py` (create new)

**Step 1: Write the test first**

```python
# tests/test_segments_data.py
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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_segments_data.py::test_load_investment_clusters -v`
Expected: FAIL (function not implemented)

**Step 3: Implement load_investment_clusters**

```python
# In scripts/generate_segments_data.py, replace the stub with:

def load_investment_clusters() -> List[Dict[str, Any]]:
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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_segments_data.py::test_load_investment_clusters -v`
Expected: PASS

**Step 5: Run all cluster tests**

Run: `uv run pytest tests/test_segments_data.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add scripts/generate_segments_data.py tests/test_segments_data.py
git commit -m "feat(segments): implement investment clusters loader with 6 types"
```

---

### Task 4: Implement spatial clusters loader

**Files:**
- Modify: `scripts/generate_segments_data.py`
- Test: `tests/test_segments_data.py`

**Step 1: Write the test**

```python
# Add to tests/test_segments_data.py

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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_segments_data.py::test_load_spatial_clusters -v`
Expected: FAIL (function not implemented)

**Step 3: Implement load_spatial_clusters**

```python
# In scripts/generate_segments_data.py, replace the stub with:

def load_spatial_clusters() -> Dict[str, Any]:
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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_segments_data.py::test_load_spatial_clusters -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/generate_segments_data.py tests/test_segments_data.py
git commit -m "feat(segments): implement spatial clusters loader with HH/LH/LL"
```

---

### Task 5: Implement MRT impact analysis loader

**Files:**
- Modify: `scripts/generate_segments_data.py`
- Test: `tests/test_segments_data.py`

**Step 1: Write the test**

```python
# Add to tests/test_segments_data.py

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

    # Condo should be ~15x more sensitive than HDB
    condo_sensitivity = abs(by_type['Condominium']['premium'])
    hdb_sensitivity = abs(by_type['HDB']['premium'])
    ratio = condo_sensitivity / hdb_sensitivity
    assert 10 < ratio < 20  # Allow some flexibility


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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_segments_data.py::test_load_mrt_analysis -v`
Expected: FAIL (function not implemented)

**Step 3: Implement load_mrt_analysis**

```python
# In scripts/generate_segments_data.py, replace the stub with:

def load_mrt_analysis() -> Dict[str, Any]:
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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_segments_data.py::test_load_mrt_analysis -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/generate_segments_data.py tests/test_segments_data.py
git commit -m "feat(segments): implement MRT impact loader with 15x condo sensitivity"
```

---

### Task 6: Implement school quality impact loader

**Files:**
- Modify: `scripts/generate_segments_data.py`
- Test: `tests/test_segments_data.py`

**Step 1: Write the test**

```python
# Add to tests/test_segments_data.py

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
    assert by_tier['tier_1']['premium'] > by_tier['tier_2']['premium']
    assert by_tier['tier_2']['premium'] > by_tier['tier_3']['premium']
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_segments_data.py::test_load_school_impact -v`
Expected: FAIL (function not implemented)

**Step 3: Implement load_school_impact**

```python
# In scripts/generate_segments_data.py, replace the stub with:

def load_school_impact() -> Dict[str, Any]:
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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_segments_data.py::test_load_school_impact -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/generate_segments_data.py tests/test_segments_data.py
git commit -m "feat(segments): implement school quality loader with regional variations"
```

---

### Task 7: Implement insight cards generator

**Files:**
- Modify: `scripts/generate_segments_data.py`
- Test: `tests/test_segments_data.py`

**Step 1: Write the test**

```python
# Add to tests/test_segments_data.py

def test_generate_insight_cards():
    """Test generating insight cards from analytics."""
    spatial_data = load_spatial_clusters()
    mrt_data = load_mrt_analysis()
    school_data = load_school_impact()

    insights = generate_insight_cards(spatial_data, mrt_data, school_data)

    assert len(insights) >= 3

    # Check required insight
    condo_insight = next((i for i in insights if i['id'] == 'condo_mrt_sensitivity'), None)
    assert condo_insight is not None
    assert '15x' in condo_insight['content']
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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_segments_data.py::test_generate_insight_cards -v`
Expected: FAIL (function not implemented)

**Step 3: Implement generate_insight_cards**

```python
# In scripts/generate_segments_data.py, replace the stub with:

def generate_insight_cards(
    spatial_data: Dict[str, Any],
    mrt_data: Dict[str, Any],
    school_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
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
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_segments_data.py::test_generate_insight_cards -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/generate_segments_data.py tests/test_segments_data.py
git commit -m "feat(segments): implement insight cards generator"
```

---

### Task 8: Implement planning areas enrichment

**Files:**
- Modify: `scripts/generate_segments_data.py`
- Test: `tests/test_segments_data.py`

**Step 1: Write the test**

```python
# Add to tests/test_segments_data.py

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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_segments_data.py::test_enrich_planning_areas -v`
Expected: FAIL (function not implemented)

**Step 3: Implement enrich_planning_areas**

```python
# In scripts/generate_segments_data.py, replace the stub with:

def enrich_planning_areas(
    spatial_data: Dict[str, Any],
    mrt_data: Dict[str, Any],
    school_data: Dict[str, Any],
) -> Dict[str, Any]:
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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_segments_data.py::test_enrich_planning_areas -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/generate_segments_data.py tests/test_segments_data.py
git commit -m "feat(segments): implement planning areas enrichment"
```

---

### Task 9: Implement segment enrichment helpers

**Files:**
- Modify: `scripts/generate_segments_data.py`
- Test: `tests/test_segments_data.py`

**Step 1: Write the test**

```python
# Add to tests/test_segments_data.py

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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_segments_data.py::test_segment_enrichment -v`
Expected: FAIL (functions not implemented)

**Step 3: Implement the helper functions**

```python
# In scripts/generate_segments_data.py, replace the stubs with:

def map_to_spatial_cluster(segment: Dict[str, Any], spatial_data: Dict[str, Any]) -> str:
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


def determine_mrt_sensitivity(segment: Dict[str, Any], mrt_data: Dict[str, Any]) -> str:
    """Determine MRT sensitivity based on segment property types."""
    prop_types = segment.get('propertyTypes', [])

    if 'Condominium' in prop_types:
        return 'high'
    elif 'EC' in prop_types:
        return 'moderate'  # Volatile, but moderate on average
    else:
        return 'low'  # HDB


def determine_school_quality(segment: Dict[str, Any], school_data: Dict[str, Any]) -> str:
    """Determine school quality profile for segment."""
    # Based on regions where segment operates
    regions = segment.get('regions', [])

    if 'CCR' in regions:
        return 'tier_1'  # International schools, top local schools
    elif 'OCR' in regions and segment['investmentType'] == 'value':
        return 'tier_2'  # Family-friendly suburban areas
    else:
        return 'mixed'


def get_areas_in_segment(segment: Dict[str, Any], spatial_data: Dict[str, Any]) -> List[str]:
    """Get list of planning areas in this segment."""
    # Map segments to planning areas based on region and cluster
    segment_regions = segment.get('regions', [])
    segment_cluster = segment.get('clusterClassification', 'HH')

    matching_areas = []
    for area in spatial_data['planning_areas']:
        if area['region'] in segment_regions and area['cluster'] == segment_cluster:
            matching_areas.append(area['name'])

    return matching_areas[:10]  # Return top 10


def generate_implications(segment: Dict[str, Any]) -> Dict[str, str]:
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

    elif inv_type == "balanced":
        implications["investor"] = "Balanced approach with moderate growth and yield."
        implications["firstTimeBuyer"] = "Good balance of affordability and potential."
        implications["upgrader"] = "Solid choice for steady appreciation with reasonable entry cost."

    return implications
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_segments_data.py::test_segment_enrichment -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/generate_segments_data.py tests/test_segments_data.py
git commit -m "feat(segments): implement segment enrichment helpers"
```

---

### Task 10: Update main generation function and integrate with pipeline

**Files:**
- Modify: `scripts/generate_segments_data.py`
- Modify: `scripts/prepare_webapp_data.py`

**Step 1: Update the main generation function to link segments to planning areas**

```python
# In scripts/generate_segments_data.py, update the generate_segments_data function:

def generate_segments_data() -> Dict[str, Any]:
    """Generate comprehensive segments data."""
    print("Generating enhanced segments data...")

    # 1. Load analysis outputs
    print("  Loading analytics outputs...")
    segments = load_investment_clusters()
    spatial_data = load_spatial_clusters()
    hotspot_data = load_hotspot_data()
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

    print(f"\n✅ Segments data generated successfully!")
    print(f"   - {len(segments)} segments")
    print(f"   - {len(planning_areas)} planning areas")
    print(f"   - {len(insights)} insight cards")
    print(f"   - Saved to {output_path}")

    return output
```

**Step 2: Test the full generation script**

Run: `uv run python scripts/generate_segments_data.py`
Expected: Script runs successfully and generates `app/public/data/segments_enhanced.json.gz`

**Step 3: Verify output file exists and is valid**

Run:
```bash
uv run python -c "
import gzip
import json
from pathlib import Path

data_path = Path('app/public/data/segments_enhanced.json.gz')
raw = data_path.read_bytes()
decompressed = gzip.decompress(raw).decode('utf-8')
data = json.loads(decompressed)

print(f'Segments: {len(data[\"segments\"])}')
print(f'Planning Areas: {len(data[\"planningAreas\"])}')
print(f'Insights: {len(data[\"insights\"])}')
print(f'Last Updated: {data[\"lastUpdated\"]}')
print(f'Version: {data[\"version\"]}')
"
```
Expected: Output shows 6 segments, ~30 planning areas, 4+ insights

**Step 4: Update prepare_webapp_data.py to call segments generator**

```python
# In scripts/prepare_webapp_data.py, add to the main() function:

def main():
    # ... existing code ...

    # Generate enhanced segments data
    print("\n" + "="*60)
    print("Generating enhanced segments dashboard data...")
    print("="*60)
    from scripts.generate_segments_data import generate_segments_data
    generate_segments_data()

    # ... rest of pipeline ...
```

**Step 5: Commit**

```bash
git add scripts/generate_segments_data.py scripts/prepare_webapp_data.py
git commit -m "feat(segments): complete data generator and integrate with pipeline"
```

---

## Phase 2: Core UI Components (Week 3-4)

### Task 11: Create custom React hooks for segments

**Files:**
- Create: `app/src/hooks/useSegmentsData.ts`
- Create: `app/src/hooks/useFilterState.ts`
- Create: `app/src/hooks/useSegmentMatching.ts`

**Step 1: Write useSegmentsData hook**

```typescript
// app/src/hooks/useSegmentsData.ts
import { useState, useEffect } from 'react';
import { SegmentsData } from '@/types/segments';

interface UseSegmentsDataResult {
  data: SegmentsData | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useSegmentsData(): UseSegmentsDataResult {
  const [data, setData] = useState<SegmentsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/data/segments_enhanced.json.gz');

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const compressed = await response.arrayBuffer();
      const decompressed = new Uint8Array(compressed);

      // Decompress using gzip
      const text = new Response(
        new Blob([decompressed], { type: 'application/gzip' })
      ).text();

      const textStr = await text;
      const parsed = JSON.parse(textStr);

      setData(parsed);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      console.error('Failed to load segments data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return {
    data,
    loading,
    error,
    reload: loadData,
  };
}
```

**Step 2: Write useFilterState hook**

```typescript
// app/src/hooks/useFilterState.ts
import { useState, useCallback, useMemo } from 'react';
import {
  FilterState,
  Persona,
  InvestmentGoal,
  PropertyType,
  Region,
  TimeHorizon,
  PersonaPreset,
} from '@/types/segments';

const INITIAL_FILTERS: FilterState = {
  investmentGoal: null,
  budgetRange: [400, 1000],
  propertyTypes: ['HDB', 'Condominium', 'EC'],
  locations: ['CCR', 'RCR', 'OCR'],
  timeHorizon: null,
};

const PERSONA_PRESETS: Record<Persona, PersonaPreset> = {
  all: {
    filters: {
      investmentGoal: null,
      budgetRange: [400, 1000],
      propertyTypes: ['HDB', 'Condominium', 'EC'],
      locations: ['CCR', 'RCR', 'OCR'],
      timeHorizon: null,
    },
    priorityMetrics: [],
    defaultInsights: [],
  },
  investor: {
    filters: {
      investmentGoal: 'yield',
      budgetRange: [500, 1000],
      propertyTypes: ['Condominium', 'HDB'],
      locations: ['CCR', 'RCR', 'OCR'],
      timeHorizon: 'medium',
    },
    priorityMetrics: ['rental_yield', 'mrt_proximity', 'appreciation'],
    defaultInsights: ['condo_mrt_sensitivity', 'hotspot_persistence'],
  },
  'first-time-buyer': {
    filters: {
      investmentGoal: 'value',
      budgetRange: [400, 600],
      propertyTypes: ['HDB'],
      locations: ['OCR', 'RCR'],
      timeHorizon: 'long',
    },
    priorityMetrics: ['affordability', 'school_quality', 'lease_remaining'],
    defaultInsights: ['school_premiums_by_region', 'cbd_vs_mrt'],
  },
  upgrader: {
    filters: {
      investmentGoal: 'balanced',
      budgetRange: [500, 800],
      propertyTypes: ['HDB', 'Condominium'],
      locations: ['RCR', 'OCR'],
      timeHorizon: 'long',
    },
    priorityMetrics: ['space_value', 'neighborhood', 'amenities'],
    defaultInsights: ['cbd_vs_mrt', 'school_premiums_by_region'],
  },
};

interface UseFilterStateResult {
  filters: FilterState;
  persona: Persona;
  setPersona: (persona: Persona) => void;
  updateFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  resetFilters: () => void;
  activeFilterCount: number;
}

export function useFilterState(initialPersona: Persona = 'all'): UseFilterStateResult {
  const [persona, setPersona] = useState<Persona>(initialPersona);
  const [filters, setFilters] = useState<FilterState>(() => {
    const preset = PERSONA_PRESETS[initialPersona];
    return { ...INITIAL_FILTERS, ...preset.filters };
  });

  const updateFilter = useCallback(<K extends keyof FilterState>(
    key: K,
    value: FilterState[K]
  ) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    const preset = PERSONA_PRESETS[persona];
    setFilters({ ...INITIAL_FILTERS, ...preset.filters });
  }, [persona]);

  const handleSetPersona = useCallback((newPersona: Persona) => {
    setPersona(newPersona);
    const preset = PERSONA_PRESETS[newPersona];
    setFilters({ ...INITIAL_FILTERS, ...preset.filters });
  }, []);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.investmentGoal) count++;
    if (filters.budgetRange[0] !== INITIAL_FILTERS.budgetRange[0] ||
        filters.budgetRange[1] !== INITIAL_FILTERS.budgetRange[1]) count++;
    if (filters.propertyTypes.length < 3) count++;
    if (filters.locations.length < 3) count++;
    if (filters.timeHorizon) count++;
    return count;
  }, [filters]);

  return {
    filters,
    persona,
    setPersona: handleSetPersona,
    updateFilter,
    resetFilters,
    activeFilterCount,
  };
}

export { PERSONA_PRESETS };
```

**Step 3: Write useSegmentMatching hook**

```typescript
// app/src/hooks/useSegmentMatching.ts
import { useMemo } from 'react';
import { Segment, FilterState } from '@/types/segments';

export function useSegmentMatching(
  segments: Segment[],
  filters: FilterState
) {
  const matchedSegments = useMemo(() => {
    return segments
      .map((segment) => ({
        segment,
        matchScore: calculateMatchScore(segment, filters),
      }))
      .filter(({ matchScore }) => matchScore > 0)
      .sort((a, b) => b.matchScore - a.matchScore)
      .map(({ segment }) => segment);
  }, [segments, filters]);

  return { matchedSegments };
}

function calculateMatchScore(segment: Segment, filters: FilterState): number {
  let score = 0;
  let maxScore = 0;

  // Investment goal (30% weight)
  if (filters.investmentGoal) {
    if (
      (filters.investmentGoal === 'yield' && segment.metrics.avgYield >= 4) ||
      (filters.investmentGoal === 'growth' && segment.metrics.yoyGrowth >= 12) ||
      (filters.investmentGoal === 'value' && segment.characteristics.priceTier === 'affordable') ||
      (filters.investmentGoal === 'balanced' && segment.investmentType === 'balanced')
    ) {
      score += 30;
    }
    maxScore += 30;
  }

  // Budget fit (25% weight)
  if (
    segment.metrics.avgPricePsf >= filters.budgetRange[0] &&
    segment.metrics.avgPricePsf <= filters.budgetRange[1]
  ) {
    score += 25;
  }
  maxScore += 25;

  // Property type match (20% weight)
  if (filters.propertyTypes.some((t) => segment.propertyTypes.includes(t))) {
    score += 20;
  }
  maxScore += 20;

  // Location match (15% weight)
  if (filters.locations.some((loc) => segment.regions.includes(loc))) {
    score += 15;
  }
  maxScore += 15;

  // Time horizon fit (10% weight)
  if (filters.timeHorizon) {
    if (
      (filters.timeHorizon === 'short' && segment.characteristics.volatility === 'high') ||
      (filters.timeHorizon === 'long' && segment.characteristics.volatility === 'low')
    ) {
      score += 10;
    }
    maxScore += 10;
  }

  return maxScore > 0 ? Math.round((score / maxScore) * 100) : 0;
}
```

**Step 4: Commit**

```bash
git add app/src/hooks/useSegmentsData.ts app/src/hooks/useFilterState.ts app/src/hooks/useSegmentMatching.ts
git commit -m "feat(hooks): add custom hooks for segments data, filters, and matching"
```

---

### Task 12: Create FilterPanel component

**Files:**
- Create: `app/src/components/dashboard/segments/FilterPanel.tsx`

**Step 1: Write the FilterPanel component**

```typescript
// app/src/components/dashboard/segments/FilterPanel.tsx
import { FilterState, InvestmentGoal, PropertyType, Region, TimeHorizon } from '@/types/segments';

interface FilterPanelProps {
  filters: FilterState;
  onFilterChange: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  onReset: () => void;
  activeFilterCount: number;
}

const INVESTMENT_GOALS: { value: InvestmentGoal; label: string; description: string }[] = [
  { value: 'yield', label: 'Yield Focus', description: '4%+ target yield' },
  { value: 'growth', label: 'Growth Focus', description: '12%+ YoY growth' },
  { value: 'value', label: 'Value Play', description: 'Below market price' },
  { value: 'balanced', label: 'Balanced', description: 'Growth + yield mix' },
];

const PROPERTY_TYPES: { value: PropertyType; label: string; note: string }[] = [
  { value: 'HDB', label: 'HDB', note: 'MRT impact minimal ~$5/100m' },
  { value: 'Condominium', label: 'Condominium', note: '15x MRT sensitive' },
  { value: 'EC', label: 'EC', note: 'Volatile post-COVID' },
];

const REGIONS: { value: Region; label: string }[] = [
  { value: 'CCR', label: 'Core Central Region' },
  { value: 'RCR', label: 'Rest of Central Region' },
  { value: 'OCR', label: 'Outside Central Region' },
];

const TIME_HORIZONS: { value: TimeHorizon; label: string; description: string }[] = [
  { value: 'short', label: 'Short-term', description: '1-3 years' },
  { value: 'medium', label: 'Medium-term', description: '3-7 years' },
  { value: 'long', label: 'Long-term', description: '7+ years' },
];

export default function FilterPanel({ filters, onFilterChange, onReset, activeFilterCount }: FilterPanelProps) {
  return (
    <div className="w-full lg:w-80 flex-shrink-0 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground">Filters</h3>
        <button
          onClick={onReset}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Reset {activeFilterCount > 0 && `(${activeFilterCount})`}
        </button>
      </div>

      {/* Investment Goal */}
      <FilterSection title="Investment Goal">
        <div className="space-y-2">
          {INVESTMENT_GOALS.map((goal) => (
            <label
              key={goal.value}
              className={`
                flex items-start p-3 rounded-lg border cursor-pointer transition-all
                ${filters.investmentGoal === goal.value
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
                }
              `}
            >
              <input
                type="radio"
                name="investmentGoal"
                value={goal.value}
                checked={filters.investmentGoal === goal.value}
                onChange={(e) => onFilterChange('investmentGoal', e.target.value as InvestmentGoal)}
                className="mt-1 mr-3"
              />
              <div>
                <div className="font-medium text-sm">{goal.label}</div>
                <div className="text-xs text-muted-foreground">{goal.description}</div>
              </div>
            </label>
          ))}
        </div>
      </FilterSection>

      {/* Budget Range */}
      <FilterSection title="Budget Range (Price PSF)">
        <div className="space-y-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">${filters.budgetRange[0]}</span>
            <span className="text-foreground font-medium">${filters.budgetRange[1]}+</span>
          </div>
          <input
            type="range"
            min="300"
            max="1500"
            step="50"
            value={filters.budgetRange[0]}
            onChange={(e) => onFilterChange('budgetRange', [parseInt(e.target.value), filters.budgetRange[1]])}
            className="w-full"
          />
          <input
            type="range"
            min="300"
            max="1500"
            step="50"
            value={filters.budgetRange[1]}
            onChange={(e) => onFilterChange('budgetRange', [filters.budgetRange[0], parseInt(e.target.value)])}
            className="w-full"
          />
        </div>
      </FilterSection>

      {/* Property Type */}
      <FilterSection title="Property Type">
        <div className="space-y-2">
          {PROPERTY_TYPES.map((type) => (
            <label
              key={type.value}
              className={`
                flex items-start p-3 rounded-lg border cursor-pointer transition-all
                ${filters.propertyTypes.includes(type.value)
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
                }
              `}
            >
              <input
                type="checkbox"
                checked={filters.propertyTypes.includes(type.value)}
                onChange={(e) => {
                  const updated = e.target.checked
                    ? [...filters.propertyTypes, type.value]
                    : filters.propertyTypes.filter((t) => t !== type.value);
                  onFilterChange('propertyTypes', updated);
                }}
                className="mt-1 mr-3"
              />
              <div>
                <div className="font-medium text-sm">{type.label}</div>
                <div className="text-xs text-muted-foreground">{type.note}</div>
              </div>
            </label>
          ))}
        </div>
      </FilterSection>

      {/* Location */}
      <FilterSection title="Location">
        <div className="space-y-2">
          {REGIONS.map((region) => (
            <label
              key={region.value}
              className={`
                flex items-center p-3 rounded-lg border cursor-pointer transition-all
                ${filters.locations.includes(region.value)
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
                }
              `}
            >
              <input
                type="checkbox"
                checked={filters.locations.includes(region.value)}
                onChange={(e) => {
                  const updated = e.target.checked
                    ? [...filters.locations, region.value]
                    : filters.locations.filter((r) => r !== region.value);
                  onFilterChange('locations', updated);
                }}
                className="mr-3"
              />
              <span className="text-sm font-medium">{region.label}</span>
            </label>
          ))}
        </div>
      </FilterSection>

      {/* Time Horizon */}
      <FilterSection title="Time Horizon">
        <div className="space-y-2">
          {TIME_HORIZONS.map((horizon) => (
            <label
              key={horizon.value}
              className={`
                flex items-start p-3 rounded-lg border cursor-pointer transition-all
                ${filters.timeHorizon === horizon.value
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
                }
              `}
            >
              <input
                type="radio"
                name="timeHorizon"
                value={horizon.value}
                checked={filters.timeHorizon === horizon.value}
                onChange={(e) => onFilterChange('timeHorizon', e.target.value as TimeHorizon)}
                className="mt-1 mr-3"
              />
              <div>
                <div className="font-medium text-sm">{horizon.label}</div>
                <div className="text-xs text-muted-foreground">{horizon.description}</div>
              </div>
            </label>
          ))}
        </div>
      </FilterSection>
    </div>
  );
}

function FilterSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-sm font-medium text-foreground mb-3">{title}</h4>
      {children}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add app/src/components/dashboard/segments/FilterPanel.tsx
git commit -m "feat(segments): add FilterPanel component with all filter options"
```

---

### Task 13: Create TabNavigation component

**Files:**
- Create: `app/src/components/dashboard/segments/TabNavigation.tsx`

**Step 1: Write the TabNavigation component**

```typescript
// app/src/components/dashboard/segments/TabNavigation.tsx
import clsx from 'clsx';

type TabId = 'discover' | 'compare' | 'details';

interface TabNavigationProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  disabledTabs?: TabId[];
}

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'discover', label: 'Discover', icon: '🔍' },
  { id: 'compare', label: 'Compare', icon: '⚖️' },
  { id: 'details', label: 'Details', icon: '📋' },
];

export default function TabNavigation({ activeTab, onTabChange, disabledTabs = [] }: TabNavigationProps) {
  return (
    <div className="flex space-x-1 bg-muted p-1 rounded-lg">
      {TABS.map((tab) => {
        const isDisabled = disabledTabs.includes(tab.id);
        return (
          <button
            key={tab.id}
            onClick={() => !isDisabled && onTabChange(tab.id)}
            disabled={isDisabled}
            className={clsx(
              'flex-1 px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center justify-center gap-2',
              activeTab === tab.id && 'bg-background text-foreground shadow-sm',
              activeTab !== tab.id && !isDisabled && 'text-muted-foreground hover:text-foreground',
              isDisabled && 'opacity-50 cursor-not-allowed'
            )}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add app/src/components/dashboard/segments/TabNavigation.tsx
git commit -m "feat(segments): add TabNavigation component"
```

---

### Task 14: Create SegmentCard component

**Files:**
- Create: `app/src/components/dashboard/segments/SegmentCard.tsx`

**Step 1: Write the SegmentCard component**

```typescript
// app/src/components/dashboard/segments/SegmentCard.tsx
import { Segment } from '@/types/segments';
import clsx from 'clsx';

interface SegmentCardProps {
  segment: Segment;
  matchScore?: number;
  onViewDetails: (segment: Segment) => void;
  onAddToCompare: (segment: Segment) => void;
  isSelectedForCompare?: boolean;
}

const SEGMENT_ICONS: Record<string, string> = {
  large_size_stable: '🏢',
  high_growth_recent: '🔥',
  speculator_hotspots: '⚡',
  declining_areas: '📉',
  mid_tier_value: '💎',
  premium_new_units: '🌟',
};

const RISK_COLORS = {
  low: 'text-green-600 bg-green-50 dark:bg-green-900/20',
  medium: 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20',
  high: 'text-orange-600 bg-orange-50 dark:bg-orange-900/20',
  very_high: 'text-red-600 bg-red-50 dark:bg-red-900/20',
};

export default function SegmentCard({
  segment,
  matchScore,
  onViewDetails,
  onAddToCompare,
  isSelectedForCompare = false,
}: SegmentCardProps) {
  const icon = SEGMENT_ICONS[segment.id] || '📊';
  const riskColor = RISK_COLORS[segment.characteristics.riskLevel];

  return (
    <div
      className={clsx(
        'bg-card border rounded-lg p-4 transition-all hover:shadow-md',
        isSelectedForCompare ? 'border-primary' : 'border-border'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{icon}</span>
          <div>
            <h3 className="font-semibold text-foreground">{segment.name}</h3>
            <p className="text-xs text-muted-foreground line-clamp-2">{segment.description}</p>
          </div>
        </div>
        {matchScore !== undefined && (
          <div className="text-right">
            <div className="text-xs text-muted-foreground">Match</div>
            <div className="text-lg font-bold text-primary">{matchScore}%</div>
          </div>
        )}
      </div>

      {/* Risk Badge */}
      <div className="mb-3">
        <span className={clsx('inline-block px-2 py-1 text-xs font-medium rounded-full', riskColor)}>
          {segment.characteristics.riskLevel.replace('_', ' ').toUpperCase()} RISK
        </span>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <MetricItem label="Price PSF" value={`$${segment.metrics.avgPricePsf.toFixed(0)}`} />
        <MetricItem label="Yield" value={`${segment.metrics.avgYield.toFixed(1)}%`} />
        <MetricItem label="YoY Growth" value={`+${segment.metrics.yoyGrowth.toFixed(1)}%`} />
        <MetricItem label="Share" value={`${(segment.metrics.marketShare * 100).toFixed(0)}%`} />
      </div>

      {/* Persistence */}
      {segment.persistenceProbability > 0 && (
        <div className="mb-4 p-2 bg-muted/50 rounded text-xs">
          <span className="text-muted-foreground">Persistence: </span>
          <span className="font-medium">{(segment.persistenceProbability * 100).toFixed(0)}%</span>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => onViewDetails(segment)}
          className="flex-1 px-3 py-2 text-sm font-medium text-center rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          Details
        </button>
        <button
          onClick={() => onAddToCompare(segment)}
          className={clsx(
            'px-3 py-2 text-sm font-medium rounded-md border transition-colors',
            isSelectedForCompare
              ? 'border-primary bg-primary/10 text-primary'
              : 'border-border hover:border-primary hover:text-primary'
          )}
        >
          {isSelectedForCompare ? '✓' : '+'}
        </button>
      </div>
    </div>
  );
}

function MetricItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-semibold text-foreground">{value}</div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add app/src/components/dashboard/segments/SegmentCard.tsx
git commit -m "feat(segments): add SegmentCard component with metrics and actions"
```

---

### Task 15: Update PersonaSelector for segments dashboard

**Files:**
- Modify: `app/src/components/dashboard/PersonaSelector.tsx`

**Step 1: Update PersonaSelector to include "all" option**

```typescript
// app/src/components/dashboard/PersonaSelector.tsx
import { useState } from 'react';

export type Persona = 'all' | 'investor' | 'first-time-buyer' | 'upgrader';

interface PersonaConfig {
  id: Persona;
  name: string;
  icon: string;
  description: string;
}

const PERSONAS: PersonaConfig[] = [
  {
    id: 'all',
    name: 'All Personas',
    icon: '👥',
    description: 'Explore freely without preset filters'
  },
  {
    id: 'investor',
    name: 'Investor',
    icon: '🏠',
    description: 'ROI-focused, portfolio optimization'
  },
  {
    id: 'first-time-buyer',
    name: 'First-Time Buyer',
    icon: '👤',
    description: 'Affordability, loan approval, stability'
  },
  {
    id: 'upgrader',
    name: 'Upgrader',
    icon: '🏡',
    description: 'More space, better location, trade-up'
  }
];

interface PersonaSelectorProps {
  selected: Persona;
  onChange: (persona: Persona) => void;
}

export default function PersonaSelector({ selected, onChange }: PersonaSelectorProps) {
  return (
    <div className="mb-6">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
        I'm a:
      </label>
      <div className="flex flex-wrap gap-3">
        {PERSONAS.map((persona) => (
          <button
            key={persona.id}
            onClick={() => onChange(persona.id)}
            className={`
              px-4 py-3 rounded-lg border-2 transition-all flex-1 min-w-[140px]
              ${selected === persona.id
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
              }
            `}
          >
            <div className="text-2xl mb-1">{persona.icon}</div>
            <div className="font-medium text-sm">{persona.name}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {persona.description}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add app/src/components/dashboard/PersonaSelector.tsx
git commit -m "feat(persona): add 'all' option to PersonaSelector"
```

---

### Task 16: Create SegmentsDashboard main container

**Files:**
- Create: `app/src/components/dashboard/segments/SegmentsDashboard.tsx`

**Step 1: Write the main dashboard container component**

```typescript
// app/src/components/dashboard/segments/SegmentsDashboard.tsx
import { useState } from 'react';
import { useSegmentsData } from '@/hooks/useSegmentsData';
import { useFilterState, useSegmentMatching } from '@/hooks/useFilterState';
import { Segment, Persona } from '@/types/segments';
import PersonaSelector from '@/components/dashboard/PersonaSelector';
import FilterPanel from './FilterPanel';
import TabNavigation from './TabNavigation';
import { DiscoverTab } from './discover/DiscoverTab';
import { CompareTab } from './compare/CompareTab';
import { DetailsTab } from './details/DetailsTab';

type TabId = 'discover' | 'compare' | 'details';

export default function SegmentsDashboard() {
  const { data, loading, error } = useSegmentsData();
  const { filters, persona, setPersona, updateFilter, resetFilters, activeFilterCount } =
    useFilterState();
  const [activeTab, setActiveTab] = useState<TabId>('discover');
  const [selectedSegment, setSelectedSegment] = useState<Segment | null>(null);
  const [comparisonSet, setComparisonSet] = useState<Set<string>>(new Set());

  // Handle loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading segments data...</p>
        </div>
      </div>
    );
  }

  // Handle error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          <h3 className="text-lg font-semibold text-foreground mb-2">Failed to load data</h3>
          <p className="text-muted-foreground mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  // Get matched segments
  const { matchedSegments } = useSegmentMatching(data.segments, filters);

  // Handlers
  const handleViewDetails = (segment: Segment) => {
    setSelectedSegment(segment);
    setActiveTab('details');
  };

  const handleAddToCompare = (segment: Segment) => {
    setComparisonSet((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(segment.id)) {
        newSet.delete(segment.id);
      } else if (newSet.size < 4) {
        newSet.add(segment.id);
      }
      return newSet;
    });
  };

  const comparisonSegments = data.segments.filter((s) => comparisonSet.has(s.id));

  return (
    <div className="space-y-6">
      {/* Header with Persona Selector */}
      <div>
        <h1 className="text-3xl font-bold text-foreground mb-2">Market Segments</h1>
        <p className="text-muted-foreground mb-6">
          Explore property market segments with interactive filters and persona-based insights
        </p>
        <PersonaSelector selected={persona} onChange={setPersona} />
      </div>

      {/* Tab Navigation */}
      <TabNavigation
        activeTab={activeTab}
        onTabChange={setActiveTab}
        disabledTabs={comparisonSet.size < 2 ? ['compare'] : []}
      />

      {/* Main Content */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Filter Sidebar */}
        <FilterPanel
          filters={filters}
          onFilterChange={updateFilter}
          onReset={resetFilters}
          activeFilterCount={activeFilterCount}
        />

        {/* Content Area */}
        <div className="flex-1">
          {activeTab === 'discover' && (
            <DiscoverTab
              segments={matchedSegments}
              insights={data.insights}
              persona={persona}
              onViewDetails={handleViewDetails}
              onAddToCompare={handleAddToCompare}
              comparisonSet={comparisonSet}
            />
          )}

          {activeTab === 'compare' && (
            <CompareTab
              segments={comparisonSegments}
              allSegments={data.segments}
              persona={persona}
            />
          )}

          {activeTab === 'details' && selectedSegment && (
            <DetailsTab
              segment={selectedSegment}
              planningAreas={data.planningAreas}
              persona={persona}
              onBack={() => setActiveTab('discover')}
            />
          )}
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add app/src/components/dashboard/segments/SegmentsDashboard.tsx
git commit -m "feat(segments): add main SegmentsDashboard container component"
```

---

### Task 17: Create Discover tab components

**Files:**
- Create: `app/src/components/dashboard/segments/discover/DiscoverTab.tsx`
- Create: `app/src/components/dashboard/segments/discover/SegmentGrid.tsx`
- Create: `app/src/components/dashboard/segments/discover/InsightCard.tsx`

**Step 1: Write InsightCard component**

```typescript
// app/src/components/dashboard/segments/discover/InsightCard.tsx
import { Insight } from '@/types/segments';

interface InsightCardProps {
  insight: Insight;
}

export function InsightCard({ insight }: InsightCardProps) {
  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <span className="text-2xl flex-shrink-0">💡</span>
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-foreground mb-1">{insight.title}</h4>
          <p className="text-sm text-muted-foreground mb-3">{insight.content}</p>
          {insight.learnMoreUrl && (
            <a
              href={insight.learnMoreUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary hover:underline"
            >
              Learn more →
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Write SegmentGrid component**

```typescript
// app/src/components/dashboard/segments/discover/SegmentGrid.tsx
import { useMemo } from 'react';
import { Segment } from '@/types/segments';
import SegmentCard from '../SegmentCard';
import { useFilterState } from '@/hooks/useFilterState';

interface SegmentGridProps {
  segments: Segment[];
  sortBy?: 'relevance' | 'price' | 'yield' | 'growth';
  onViewDetails: (segment: Segment) => void;
  onAddToCompare: (segment: Segment) => void;
  comparisonSet: Set<string>;
}

type SortOption = 'relevance' | 'price' | 'yield' | 'growth';

export function SegmentGrid({
  segments,
  sortBy = 'relevance',
  onViewDetails,
  onAddToCompare,
  comparisonSet,
}: SegmentGridProps) {
  const sortedSegments = useMemo(() => {
    const sorted = [...segments];

    switch (sortBy) {
      case 'price':
        return sorted.sort((a, b) => a.metrics.avgPricePsf - b.metrics.avgPricePsf);
      case 'yield':
        return sorted.sort((a, b) => b.metrics.avgYield - a.metrics.avgYield);
      case 'growth':
        return sorted.sort((a, b) => b.metrics.yoyGrowth - a.metrics.yoyGrowth);
      case 'relevance':
      default:
        return sorted; // Already sorted by match score
    }
  }, [segments, sortBy]);

  if (sortedSegments.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-6xl mb-4">🔍</div>
        <h3 className="text-lg font-semibold text-foreground mb-2">No segments found</h3>
        <p className="text-muted-foreground mb-4">
          Try adjusting your filters to see more results
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {sortedSegments.map((segment) => (
        <SegmentCard
          key={segment.id}
          segment={segment}
          onViewDetails={onViewDetails}
          onAddToCompare={onAddToCompare}
          isSelectedForCompare={comparisonSet.has(segment.id)}
        />
      ))}
    </div>
  );
}
```

**Step 3: Write DiscoverTab component**

```typescript
// app/src/components/dashboard/segments/discover/DiscoverTab.tsx
import { useState } from 'react';
import { Segment, Insight, Persona } from '@/types/segments';
import { SegmentGrid } from './SegmentGrid';
import { InsightCard } from './InsightCard';
import { useFilterState } from '@/hooks/useFilterState';

interface DiscoverTabProps {
  segments: Segment[];
  insights: Insight[];
  persona: Persona;
  onViewDetails: (segment: Segment) => void;
  onAddToCompare: (segment: Segment) => void;
  comparisonSet: Set<string>;
}

type SortOption = 'relevance' | 'price' | 'yield' | 'growth';

const SORT_OPTIONS: { value: SortOption; label: string }[] = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'price', label: 'Price (Low to High)' },
  { value: 'yield', label: 'Yield (High to Low)' },
  { value: 'growth', label: 'Growth (High to Low)' },
];

export function DiscoverTab({
  segments,
  insights,
  persona,
  onViewDetails,
  onAddToCompare,
  comparisonSet,
}: DiscoverTabProps) {
  const [sortBy, setSortBy] = useState<SortOption>('relevance');

  // Get relevant insights for persona
  const relevantInsights = insights.filter((insight) => {
    if (persona === 'all') return true;
    return insight.relevantFor.includes(persona);
  });

  return (
    <div className="space-y-6">
      {/* Header with Sort */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-foreground">
            {segments.length} Segment{segments.length !== 1 ? 's' : ''} Found
          </h2>
          <p className="text-sm text-muted-foreground">
            Click on a segment to view details or add to comparison
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-muted-foreground">Sort by:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className="px-3 py-2 border border-border rounded-md bg-background text-foreground text-sm"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Insight Cards */}
      {relevantInsights.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {relevantInsights.slice(0, 2).map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      )}

      {/* Segment Grid */}
      <SegmentGrid
        segments={segments}
        sortBy={sortBy}
        onViewDetails={onViewDetails}
        onAddToCompare={onAddToCompare}
        comparisonSet={comparisonSet}
      />
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add app/src/components/dashboard/segments/discover/
git commit -m "feat(segments): add Discover tab with grid, sorting, and insight cards"
```

---

### Task 18: Create Compare tab components

**Files:**
- Create: `app/src/components/dashboard/segments/compare/CompareTab.tsx`
- Create: `app/src/components/dashboard/segments/compare/ComparisonTable.tsx`
- Create: `app/src/components/dashboard/segments/compare/ComparisonCharts.tsx`
- Create: `app/src/components/dashboard/segments/compare/InvestmentImplications.tsx`

**Step 1: Write ComparisonTable component**

```typescript
// app/src/components/dashboard/segments/compare/ComparisonTable.tsx
import { Segment } from '@/types/segments';

interface ComparisonTableProps {
  segments: Segment[];
  persona: string;
}

export function ComparisonTable({ segments, persona }: ComparisonTableProps) {
  if (segments.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Select 2-4 segments to compare
      </div>
    );
  }

  const metrics = [
    { key: 'avgPricePsf', label: 'Price PSF', format: (v: number) => `$${v.toFixed(0)}` },
    { key: 'avgYield', label: 'Rental Yield', format: (v: number) => `${v.toFixed(1)}%` },
    { key: 'yoyGrowth', label: 'YoY Growth', format: (v: number) => `+${v.toFixed(1)}%` },
    { key: 'transactionCount', label: 'Transactions', format: (v: number) => v.toLocaleString() },
    { key: 'marketShare', label: 'Market Share', format: (v: number) => `${(v * 100).toFixed(1)}%` },
    { key: 'persistenceProbability', label: 'Persistence', format: (v: number) => `${(v * 100).toFixed(0)}%` },
  ];

  const getBestValue = (metricKey: string) => {
    const values = segments.map((s) => (s.metrics as any)[metricKey]);
    const isHigherBetter = ['avgYield', 'yoyGrowth', 'transactionCount', 'marketShare', 'persistenceProbability'].includes(metricKey);

    if (isHigherBetter) {
      return Math.max(...values);
    } else {
      return Math.min(...values);
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left p-3 font-semibold text-foreground">Metric</th>
            {segments.map((segment) => (
              <th key={segment.id} className="p-3 font-semibold text-foreground text-center min-w-[150px]">
                {segment.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metrics.map((metric) => {
            const bestValue = getBestValue(metric.key);
            return (
              <tr key={metric.key} className="border-b border-border">
                <td className="p-3 text-sm text-muted-foreground">{metric.label}</td>
                {segments.map((segment) => {
                  const value = (segment.metrics as any)[metric.key];
                  const isBest = value === bestValue;
                  return (
                    <td
                      key={segment.id}
                      className={`p-3 text-center text-sm font-medium ${
                        isBest ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300' : ''
                      }`}
                    >
                      {metric.format(value)}
                    </td>
                  );
                })}
              </tr>
            );
          })}
          <tr className="border-b border-border">
            <td className="p-3 text-sm text-muted-foreground">Risk Level</td>
            {segments.map((segment) => (
              <td key={segment.id} className="p-3 text-center text-sm font-medium">
                {segment.characteristics.riskLevel}
              </td>
            ))}
          </tr>
          <tr>
            <td className="p-3 text-sm text-muted-foreground">Volatility</td>
            {segments.map((segment) => (
              <td key={segment.id} className="p-3 text-center text-sm font-medium">
                {segment.characteristics.volatility}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
```

**Step 2: Write ComparisonCharts component**

```typescript
// app/src/components/dashboard/segments/compare/ComparisonCharts.tsx
import { Segment } from '@/types/segments';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface ComparisonChartsProps {
  segments: Segment[];
}

export function ComparisonCharts({ segments }: ComparisonChartsProps) {
  if (segments.length < 2) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Select at least 2 segments to view comparisons
      </div>
    );
  }

  // Prepare data for bar chart
  const barData = segments.map((segment) => ({
    name: segment.name,
    'Price PSF': segment.metrics.avgPricePsf,
    'Yield %': segment.metrics.avgYield,
    'YoY Growth %': segment.metrics.yoyGrowth,
  }));

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold text-foreground mb-4">Key Metrics Comparison</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={barData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="name" className="text-xs" tick={{ fill: 'hsl(var(--foreground))' }} />
            <YAxis className="text-xs" tick={{ fill: 'hsl(var(--foreground))' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                borderColor: 'hsl(var(--border))',
                color: 'hsl(var(--foreground))',
              }}
            />
            <Legend />
            <Bar dataKey="Price PSF" fill="hsl(var(--primary))" />
            <Bar dataKey="Yield %" fill="#10b981" />
            <Bar dataKey="YoY Growth %" fill="#f59e0b" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

**Step 3: Write InvestmentImplications component**

```typescript
// app/src/components/dashboard/segments/compare/InvestmentImplications.tsx
import { Segment, Persona } from '@/types/segments';

interface InvestmentImplicationsProps {
  segments: Segment[];
  persona: Persona;
}

export function InvestmentImplications({ segments, persona }: InvestmentImplicationsProps) {
  const getImplications = () => {
    switch (persona) {
      case 'investor':
        return {
          title: 'For Property Investors',
          getComparison: (s: Segment) => s.implications.investor,
        };
      case 'first-time-buyer':
        return {
          title: 'For First-Time Buyers',
          getComparison: (s: Segment) => s.implications.firstTimeBuyer,
        };
      case 'upgrader':
        return {
          title: 'For Upsizers',
          getComparison: (s: Segment) => s.implications.upgrader,
        };
      default:
        return {
          title: 'Investment Implications',
          getComparison: (s: Segment) => s.implications.investor,
        };
    }
  };

  const { title, getComparison } = getImplications();

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-foreground">{title}</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {segments.map((segment) => (
          <div key={segment.id} className="bg-muted/50 p-4 rounded-lg">
            <h4 className="font-semibold text-foreground mb-2">{segment.name}</h4>
            <p className="text-sm text-muted-foreground">{getComparison(segment)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Step 4: Write CompareTab component**

```typescript
// app/src/components/dashboard/segments/compare/CompareTab.tsx
import { Persona } from '@/types/segments';
import { ComparisonTable } from './ComparisonTable';
import { ComparisonCharts } from './ComparisonCharts';
import { InvestmentImplications } from './InvestmentImplications';

interface CompareTabProps {
  segments: Persona[];
  allSegments: Persona[];
  persona: Persona;
}

export function CompareTab({ segments, allSegments, persona }: CompareTabProps) {
  if (segments.length < 2) {
    return (
      <div className="text-center py-16">
        <div className="text-6xl mb-4">⚖️</div>
        <h3 className="text-xl font-semibold text-foreground mb-2">Select Segments to Compare</h3>
        <p className="text-muted-foreground mb-6">
          Choose 2-4 segments from the Discover tab to compare them side-by-side
        </p>
        <p className="text-sm text-muted-foreground">
          {segments.length === 1 ? '1 segment selected' : '0 segments selected'} (need 2-4)
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Comparison Table */}
      <div>
        <h2 className="text-xl font-semibold text-foreground mb-4">Metrics Comparison</h2>
        <ComparisonTable segments={segments} persona={persona} />
      </div>

      {/* Charts */}
      <div>
        <h2 className="text-xl font-semibold text-foreground mb-4">Visual Comparison</h2>
        <ComparisonCharts segments={segments} />
      </div>

      {/* Investment Implications */}
      <InvestmentImplications segments={segments} persona={persona} />
    </div>
  );
}
```

**Step 5: Commit**

```bash
git add app/src/components/dashboard/segments/compare/
git commit -m "feat(segments): add Compare tab with table, charts, and implications"
```

---

### Task 19: Create Details tab components

**Files:**
- Create: `app/src/components/dashboard/segments/details/DetailsTab.tsx`
- Create: `app/src/components/dashboard/segments/details/SegmentOverview.tsx`
- Create: `app/src/components/dashboard/segments/details/GeographicDistribution.tsx`
- Create: `app/src/components/dashboard/segments/details/RiskFactors.tsx`
- Create: `app/src/components/dashboard/segments/details/RelatedSegments.tsx`

**Step 1: Write SegmentOverview component**

```typescript
// app/src/components/dashboard/segments/details/SegmentOverview.tsx
import { Segment } from '@/types/segments';

interface SegmentOverviewProps {
  segment: Segment;
  persona: string;
}

const RISK_COLORS = {
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  very_high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

export function SegmentOverview({ segment, persona }: SegmentOverviewProps) {
  const riskColor = RISK_COLORS[segment.characteristics.riskLevel];

  const getImplication = () => {
    switch (persona) {
      case 'investor':
        return segment.implications.investor;
      case 'first-time-buyer':
        return segment.implications.firstTimeBuyer;
      case 'upgrader':
        return segment.implications.upgrader;
      default:
        return segment.implications.investor;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <span className="text-4xl">📊</span>
          <div>
            <h2 className="text-2xl font-bold text-foreground">{segment.name}</h2>
            <p className="text-muted-foreground">{segment.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 mt-3">
          <span className={`px-3 py-1 text-sm font-medium rounded-full ${riskColor}`}>
            {segment.characteristics.riskLevel.replace('_', ' ').toUpperCase()} RISK
          </span>
          <span className="px-3 py-1 text-sm font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
            {segment.investmentType.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Key Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Price PSF" value={`$${segment.metrics.avgPricePsf.toFixed(0)}`} />
        <StatCard label="Yield" value={`${segment.metrics.avgYield.toFixed(1)}%`} />
        <StatCard label="YoY Growth" value={`+${segment.metrics.yoyGrowth.toFixed(1)}%`} />
        <StatCard label="Market Share" value={`${(segment.metrics.marketShare * 100).toFixed(1)}%`} />
      </div>

      {/* Characteristics */}
      <div className="bg-muted/50 p-4 rounded-lg">
        <h3 className="font-semibold text-foreground mb-3">Characteristics</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <div>
            <span className="text-muted-foreground">Price Tier:</span>{' '}
            <span className="font-medium">{segment.characteristics.priceTier}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Volatility:</span>{' '}
            <span className="font-medium">{segment.characteristics.volatility}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Appreciation:</span>{' '}
            <span className="font-medium">{segment.characteristics.appreciationPotential}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Spatial:</span>{' '}
            <span className="font-medium">{segment.spatialClassification}</span>
          </div>
          <div>
            <span className="text-muted-foreground">MRT Sensitivity:</span>{' '}
            <span className="font-medium">{segment.mrtSensitivity}</span>
          </div>
          <div>
            <span className="text-muted-foreground">School Quality:</span>{' '}
            <span className="font-medium">{segment.schoolQuality}</span>
          </div>
        </div>
      </div>

      {/* Persona-Specific Implication */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4 rounded-lg">
        <h3 className="font-semibold text-foreground mb-2">
          For {persona === 'all' ? 'Investors' : persona.replace('-', ' ')}:
        </h3>
        <p className="text-sm text-muted-foreground">{getImplication()}</p>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-card border border-border p-3 rounded-lg">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className="text-xl font-bold text-foreground">{value}</div>
    </div>
  );
}
```

**Step 2: Write GeographicDistribution component**

```typescript
// app/src/components/dashboard/segments/details/GeographicDistribution.tsx
import { Segment } from '@/types/segments';
import { Record } from '@/types/segments';

interface GeographicDistributionProps {
  segment: Segment;
  planningAreas: Record<string, any>;
}

export function GeographicDistribution({ segment, planningAreas }: GeographicDistributionProps) {
  const segmentAreas = segment.planningAreas
    .map((name) => planningAreas[name])
    .filter(Boolean);

  const regionCounts = segmentAreas.reduce((acc, area) => {
    acc[area.region] = (acc[area.region] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-foreground">Geographic Distribution</h3>

      {/* Region Breakdown */}
      <div className="grid grid-cols-3 gap-3">
        {(['CCR', 'RCR', 'OCR'] as const).map((region) => (
          <div
            key={region}
            className={`p-3 rounded-lg border text-center ${
              segment.regions.includes(region)
                ? 'border-primary bg-primary/5'
                : 'border-border opacity-50'
            }`}
          >
            <div className="text-2xl font-bold text-foreground">{regionCounts[region] || 0}</div>
            <div className="text-xs text-muted-foreground">{region} Areas</div>
          </div>
        ))}
      </div>

      {/* Planning Areas List */}
      <div>
        <h4 className="font-medium text-foreground mb-2">
          Planning Areas ({segmentAreas.length})
        </h4>
        <div className="flex flex-wrap gap-2">
          {segmentAreas.map((area) => (
            <span
              key={area.name}
              className="px-3 py-1 bg-muted text-foreground text-sm rounded-full"
            >
              {area.name}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
```

**Step 3: Write RiskFactors component**

```typescript
// app/src/components/dashboard/segments/details/RiskFactors.tsx
import { Segment } from '@/types/segments';

interface RiskFactorsProps {
  segment: Segment;
}

export function RiskFactors({ segment }: RiskFactorsProps) {
  if (segment.riskFactors.length === 0 && segment.opportunities.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-foreground">Risk & Opportunities</h3>

      {/* Risk Factors */}
      {segment.riskFactors.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 rounded-lg">
          <h4 className="font-semibold text-foreground mb-2 flex items-center gap-2">
            <span>⚠️</span> Risk Factors
          </h4>
          <ul className="space-y-1">
            {segment.riskFactors.map((risk, index) => (
              <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                <span className="text-red-500 mt-0.5">•</span>
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Opportunities */}
      {segment.opportunities.length > 0 && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-4 rounded-lg">
          <h4 className="font-semibold text-foreground mb-2 flex items-center gap-2">
            <span>✨</span> Opportunities
          </h4>
          <ul className="space-y-1">
            {segment.opportunities.map((opportunity, index) => (
              <li key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                <span className="text-green-500 mt-0.5">•</span>
                <span>{opportunity}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

**Step 4: Write RelatedSegments component**

```typescript
// app/src/components/dashboard/segments/details/RelatedSegments.tsx
import { Segment } from '@/types/segments';

interface RelatedSegmentsProps {
  segment: Segment;
  allSegments: Segment[];
  onSelectSegment: (segment: Segment) => void;
}

export function RelatedSegments({ segment, allSegments, onSelectSegment }: RelatedSegmentsProps) {
  // Find segments with similar characteristics
  const related = allSegments
    .filter((s) => s.id !== segment.id)
    .filter((s) => {
      // Same region or investment type
      return (
        s.regions.some((r) => segment.regions.includes(r)) ||
        s.investmentType === segment.investmentType
      );
    })
    .slice(0, 3);

  if (related.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-foreground">Related Segments</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {related.map((relatedSegment) => (
          <button
            key={relatedSegment.id}
            onClick={() => onSelectSegment(relatedSegment)}
            className="p-4 bg-card border border-border rounded-lg text-left hover:border-primary transition-colors"
          >
            <div className="font-semibold text-foreground mb-1">{relatedSegment.name}</div>
            <div className="text-xs text-muted-foreground mb-2">
              {relatedSegment.description}
            </div>
            <div className="flex gap-3 text-sm">
              <span className="text-muted-foreground">
                ${relatedSegment.metrics.avgPricePsf.toFixed(0)} PSF
              </span>
              <span className="text-muted-foreground">
                {relatedSegment.metrics.avgYield.toFixed(1)}% Yield
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
```

**Step 5: Write DetailsTab component**

```typescript
// app/src/components/dashboard/segments/details/DetailsTab.tsx
import { Segment, Persona, PlanningArea, Record } from '@/types/segments';
import { SegmentOverview } from './SegmentOverview';
import { GeographicDistribution } from './GeographicDistribution';
import { RiskFactors } from './RiskFactors';
import { RelatedSegments } from './RelatedSegments';

interface DetailsTabProps {
  segment: Segment;
  planningAreas: Record<string, PlanningArea>;
  persona: Persona;
  onBack: () => void;
}

export function DetailsTab({ segment, planningAreas, persona, onBack }: DetailsTabProps) {
  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
      >
        ← Back to Discover
      </button>

      {/* Overview */}
      <SegmentOverview segment={segment} persona={persona} />

      {/* Geographic Distribution */}
      <GeographicDistribution segment={segment} planningAreas={planningAreas} />

      {/* Risk Factors */}
      <RiskFactors segment={segment} />
    </div>
  );
}
```

**Step 6: Commit**

```bash
git add app/src/components/dashboard/segments/details/
git commit -m "feat(segments): add Details tab with overview, geography, and risks"
```

---

### Task 20: Update segments.astro page to use new dashboard

**Files:**
- Modify: `app/src/pages/dashboard/segments.astro`

**Step 1: Update the segments page**

```astro
---
import Layout from '@/layouts/Layout.astro';
import Sidebar from '@/components/Sidebar.astro';
import SegmentsDashboard from '@/components/dashboard/segments/SegmentsDashboard';
---

<Layout title="Market Segments - Dashboard">
  <Sidebar />

  <main class="flex-1 ml-0 lg:ml-64 transition-all duration-300">
    <div class="max-w-7xl mx-auto px-4 sm:px-8 py-8">
      <SegmentsDashboard client:load />
    </div>
  </main>
</Layout>
```

**Step 2: Commit**

```bash
git add app/src/pages/dashboard/segments.astro
git commit -m "feat(segments): update segments page to use new SegmentsDashboard"
```

---

## Phase 6: Polish & Testing (Week 8)

### Task 21: Add error handling and loading states

**Files:**
- Modify: `app/src/hooks/useSegmentsData.ts`

**Step 1: Enhance error handling in useSegmentsData**

The useSegmentsData hook already has basic error handling. Add retry logic:

```typescript
// In app/src/hooks/useSegmentsData.ts, update the hook:

export function useSegmentsData(maxRetries = 2) {
  const [data, setData] = useState<SegmentsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const loadData = async (attempt = 0) => {
    setLoading(true);
    setError(null);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

      const response = await fetch('/data/segments_enhanced.json.gz', {
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const compressed = await response.arrayBuffer();
      const text = new TextDecoder().decode(compressed);
      const parsed = JSON.parse(text);

      setData(parsed);
      setRetryCount(0);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';

      if (attempt < maxRetries && message.includes('Failed to fetch')) {
        // Retry on network errors
        setTimeout(() => loadData(attempt + 1), 1000 * (attempt + 1));
        setRetryCount(attempt + 1);
        return;
      }

      setError(message);
      console.error('Failed to load segments data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return {
    data,
    loading,
    error,
    reload: () => loadData(0),
  };
}
```

**Step 2: Commit**

```bash
git add app/src/hooks/useSegmentsData.ts
git commit -m "feat(segments): add retry logic and timeout to useSegmentsData"
```

---

### Task 22: Add responsive design improvements

**Files:**
- Modify: `app/src/components/dashboard/segments/FilterPanel.tsx`

**Step 1: Add mobile responsive toggle for filters**

```typescript
// In app/src/components/dashboard/segments/FilterPanel.tsx, add mobile toggle:

import { useState } from 'react';

interface FilterPanelProps {
  filters: FilterState;
  onFilterChange: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void;
  onReset: () => void;
  activeFilterCount: number;
}

export default function FilterPanel({ filters, onFilterChange, onReset, activeFilterCount }: FilterPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="w-full lg:w-80 flex-shrink-0 space-y-6">
      {/* Mobile Toggle */}
      <div className="lg:hidden flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-foreground">Filters</h3>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-2 border border-border rounded-md hover:border-primary"
        >
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>

      {/* Filter Content - Collapsible on mobile */}
      <div className={`${isExpanded ? 'block' : 'hidden'} lg:block space-y-6`}>
        {/* ... existing filter sections ... */}
      </div>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add app/src/components/dashboard/segments/FilterPanel.tsx
git commit -m "feat(segments): add mobile responsive toggle for filter panel"
```

---

### Task 23: Run data generation and verify output

**Files:**
- Scripts: `scripts/generate_segments_data.py`

**Step 1: Run the data generation script**

Run: `uv run python scripts/generate_segments_data.py`
Expected: Script runs successfully, outputs summary

**Step 2: Verify the generated JSON file**

Run:
```bash
uv run python -c "
import gzip
import json
from pathlib import Path

data_path = Path('app/public/data/segments_enhanced.json.gz')
raw = data_path.read_bytes()
data = json.loads(gzip.decompress(raw).decode('utf-8'))

print('Segments:', len(data['segments']))
for s in data['segments']:
    print(f'  - {s[\"id\"]}: {s[\"name\"]}')

print('\nPlanning Areas:', len(data['planningAreas']))

print('\nInsights:', len(data['insights']))
for i in data['insights']:
    print(f'  - {i[\"id\"]}: {i[\"title\"]}')
"
```
Expected: All 6 segments, 30 planning areas, 4 insights listed

**Step 3: Test the full webapp data pipeline**

Run: `uv run python scripts/prepare_webapp_data.py`
Expected: Pipeline completes successfully including segments generation

**Step 4: Commit the generated data**

```bash
git add app/public/data/segments_enhanced.json.gz
git commit -m "chore(segments): add generated segments data"
```

---

### Task 24: Write end-to-end integration test

**Files:**
- Create: `tests/integration/test_segments_dashboard.py`

**Step 1: Write integration test for data pipeline**

```python
# tests/integration/test_segments_dashboard.py
import pytest
import gzip
import json
from pathlib import Path


def test_segments_data_file_exists():
    """Test that segments data file is generated."""
    data_path = Path('app/public/data/segments_enhanced.json.gz')
    assert data_path.exists(), "Segments data file not found"


def test_segments_data_structure():
    """Test that segments data has correct structure."""
    data_path = Path('app/public/data/segments_enhanced.json.gz')

    raw = data_path.read_bytes()
    data = json.loads(gzip.decompress(raw).decode('utf-8'))

    # Check top-level keys
    assert 'segments' in data
    assert 'planningAreas' in data
    assert 'insights' in data
    assert 'lastUpdated' in data
    assert 'version' in data


def test_segments_completeness():
    """Test that all required segments are present."""
    data_path = Path('app/public/data/segments_enhanced.json.gz')

    raw = data_path.read_bytes()
    data = json.loads(gzip.decompress(raw).decode('utf-8'))

    segment_ids = {s['id'] for s in data['segments']}

    required_segments = {
        'large_size_stable',
        'high_growth_recent',
        'speculator_hotspots',
        'declining_areas',
        'mid_tier_value',
        'premium_new_units'
    }

    assert required_segments.issubset(segment_ids), f"Missing segments: {required_segments - segment_ids}"


def test_planning_areas_have_segments():
    """Test that planning areas reference valid segments."""
    data_path = Path('app/public/data/segments_enhanced.json.gz')

    raw = data_path.read_bytes()
    data = json.loads(gzip.decompress(raw).decode('utf-8'))

    segment_ids = {s['id'] for s in data['segments']}

    for area_name, area in data['planningAreas'].items():
        for segment_id in area.get('segments', []):
            assert segment_id in segment_ids, f"Area {area_name} references invalid segment {segment_id}"


def test_insights_reference_valid_sources():
    """Test that insights reference valid analytics documents."""
    data_path = Path('app/public/data/segments_enhanced.json.gz')

    raw = data_path.read_bytes()
    data = json.loads(gzip.decompress(raw).decode('utf-8'))

    valid_sources = {
        'mrt-impact.md',
        'spatial-autocorrelation.md',
        'spatial-hotspots.md',
        'school-quality.md',
        'findings.md',
    }

    for insight in data['insights']:
        assert insight['source'] in valid_sources, f"Invalid source: {insight['source']}"
```

**Step 2: Run integration tests**

Run: `uv run pytest tests/integration/test_segments_dashboard.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/integration/test_segments_dashboard.py
git commit -m "test(segments): add integration tests for data pipeline"
```

---

### Task 25: Final verification and documentation

**Step 1: Create README for the segments dashboard**

**File**: Create `app/public/data/segments_readme.md`

```markdown
# Market Segments Dashboard

## Overview
Interactive property discovery tool with multi-dimensional segmentation analysis.

## Data Sources
- Investment Clusters: 6 types from findings analysis
- Spatial Clusters: HH/LH/LL from LISA analysis
- MRT Impact: Property type sensitivity analysis
- School Quality: Regional variations
- Hotspots: Getis-Ord Gi* statistics

## Data Generation
Run: `uv run python scripts/generate_segments_data.py`

Or full pipeline: `uv run python scripts/prepare_webapp_data.py`

## Output
File: `app/public/data/segments_enhanced.json.gz`

## Data Schema
See: `app/src/types/segments.ts`

## Last Updated
Generated automatically by pipeline.
```

**Step 2: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS (or note any intentional skips)

**Step 3: Build and verify the app**

Run:
```bash
cd app
uv run astro build
uv run astro preview
```
Expected: Build succeeds, preview works, segments page loads

**Step 4: Commit documentation**

```bash
git add app/public/data/segments_readme.md
git commit -m "docs(segments): add README for segments dashboard"
```

---

## Summary

This implementation plan creates an interactive market segments dashboard in 8 weeks through 25 bite-sized tasks:

**Phase 1 (Week 1-2)**: Data Foundation - Python pipeline, data generators, JSON output
**Phase 2 (Week 3-4)**: Core UI Components - Hooks, filters, tabs, cards
**Phase 3 (Week 5)**: Discover Tab - Grid, sorting, insights
**Phase 4 (Week 6)**: Compare Tab - Tables, charts, implications
**Phase 5 (Week 7)**: Details Tab - Overview, geography, risks
**Phase 6 (Week 8)**: Polish - Error handling, responsive design, testing

**Total Files Created/Modified**: ~40 files
**Estimated Lines of Code**: ~4,000 lines (Python + TypeScript)
**Test Coverage**: Integration tests for data pipeline

The plan follows TDD, YAGNI, DRY principles with frequent commits and comprehensive documentation.

---

**End of Implementation Plan**
