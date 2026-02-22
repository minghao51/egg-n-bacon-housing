# Interactive Market Segments Dashboard - Design Document

**Date**: 2026-02-22
**Status**: Design Approved
**Author**: Claude (with user input)
**Related Analytics**:
- Spatial Hotspots (`docs/analytics/spatial-hotspots.md`)
- Spatial Autocorrelation (`docs/analytics/spatial-autocorrelation.md`)
- MRT Impact (`docs/analytics/mrt-impact.md`)
- School Quality (`docs/analytics/school-quality.md`)
- Key Findings (`docs/analytics/findings.md`)

---

## Executive Summary

Transform the current simple scatter plot visualization into an **interactive property discovery tool** that helps property buyers and investors explore Singapore's housing market through multiple analytical dimensions.

**Primary Goal**: Enable property buyers and investors to discover, compare, and understand market segments through interactive filters, persona-based guidance, and comprehensive segment details.

**Key Enhancement**: Move from a single visualization (Price PSF vs Rental Yield scatter plot) to a multi-dimensional exploration tool integrating 4 analytical dimensions: Investment Clusters, Spatial Clusters, MRT/CBD Segments, and School Quality Segments.

---

## User Personas & Goals

### Primary Personas

1. **First-Time Home Buyers**
   - Goals: Affordability, school access, long-term value
   - Key Metrics: Affordability ratio (<3x), school tier, lease remaining (90+ years)
   - Pain Points: Information overwhelm, unclear trade-offs

2. **Property Investors**
   - Goals: Rental yield (>4%), capital appreciation, MRT proximity
   - Key Metrics: Yield, YoY growth, MRT sensitivity (15x for condos), persistence probability
   - Pain Points: Identifying yield vs appreciation opportunities, timing market

3. **Upsizers**
   - Goals: Space value, neighborhood quality, commute trade-offs
   - Key Metrics: Space premium (20-30% in OCR), amenities, family-friendliness
   - Pain Points: Balancing budget with space needs, location flexibility

4. **All Personas** (default mode)
   - Goals: Exploration, learning, discovery
   - Approach: Flexible filters, no presets

---

## Multi-Dimensional Segmentation

### 4 Key Dimensions

#### 1. Investment Clusters (6 Types)
Source: `docs/analytics/findings.md`

| Cluster | % of Properties | Strategy | Key Characteristics |
|---------|----------------|----------|-------------------|
| **Large Size Stable** | 12.6% | Buy and hold | High PSF ($570), stable yields (5.54%) |
| **High Growth Recent** | 33.0% | Growth investing | Moderate PSF ($509), +24.4% YoY growth |
| **Speculator Hotspots** | 5.7% | Short-term flips | Premium PSF ($550), +83.9% YoY growth |
| **Declining Areas** | 12.4% | Avoid / contrarian | Moderate PSF ($564), -3.6% growth |
| **Mid-Tier Value** | 25.3% | Rental income | Affordable PSF ($463), 6.36% yields |
| **Premium New Units** | 11.0% | Luxury segment | High PSF ($826), 12.3% growth |

#### 2. Spatial Clusters
Source: `docs/analytics/spatial-autocorrelation.md`

| Cluster | Classification | Appreciation | Persistence | Geographic Pattern |
|---------|---------------|-------------|-------------|-------------------|
| **HH (Hotspots)** | MATURE_HOTSPOT | 12.7% YoY | 58-62% | Central-south Singapore |
| **LH (Lagging)** | VALUE_OPPORTUNITY | 11.3% YoY | 33% upside | Northern outliers |
| **LL (Coldspots)** | STABLE_AREA / DECLINING | ~10% YoY | 50% remain | Dispersed |

- **Neighborhood Effect**: Properties 71-78% correlated with neighbors
- **Moran's I**: 0.766 (very strong spatial autocorrelation)

#### 3. MRT/CBD Segments
Source: `docs/analytics/mrt-impact.md`

| Dimension | HDB | Condominium | EC |
|-----------|-----|-------------|----|
| **MRT Sensitivity** | $1.28/100m | $19.20-$45.62/100m | Volatile (+$6 to -$34) |
| **Sensitivity Ratio** | 1x | **15x** | -1790% post-COVID |
| **CBD Distance Impact** | 22.6% variance | High (varies by region) | Moderate |
| **Best Region** | OCR (value) | RCR (balance) | Timing-dependent |

**Key Insight**: "MRT Premium" = "CBD Premium" (CBD explains 22.6%, MRT adds only 0.78%)

#### 4. School Quality Segments
Source: `docs/analytics/school-quality.md`

| Region | School Premium | Interpretation |
|--------|---------------|----------------|
| **OCR** | +$9.63 PSF | Positive premium for families |
| **RCR** | -$23.67 PSF | Negative effect (confounded) |
| **CCR** | ~$0 PSF | No effect (location dominates) |

- **Primary School**: +$9.66 PSF per quality point (~$70K premium for 1000 sqft near Tier 1)
- **Secondary School**: #1 predictor of appreciation (21.8% importance)
- **1km Boundary Paradox**: RDD shows -$79 PSF effect (selection bias)

---

## UI/UX Design

### Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  Header: Market Segments Dashboard                               │
│  [Persona Selector: All ▼]  [Quick Actions: ⚙️]                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────────────────────────────┐    │
│  │              │  │                                       │    │
│  │   Filters    │  │         Main Content Area            │    │
│  │              │  │  ┌──────────────────────────────┐   │    │
│  │ • Investment │  │  │ [Discover] [Compare] [Details] │   │    │
│  │   Goals      │  │  └──────────────────────────────┘   │    │
│  │ • Budget     │  │                                       │    │
│  │ • Property   │  │  ┌──────────────────────────────┐   │    │
│  │   Type       │  │  │    Visualization/Content      │   │    │
│  │ • Location   │  │  │                              │   │    │
│  │ • Time       │  │  │                              │   │    │
│  │   Horizon    │  │  │                              │   │    │
│  │              │  │  └──────────────────────────────┘   │    │
│  │ [Reset All]  │  │                                       │    │
│  └──────────────┘  │  ┌──────────────────────────────┐   │    │
│                    │  │  Insight Cards / Quick Stats  │   │    │
│                    │  └──────────────────────────────┘   │    │
│                    └──────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Filter Panel Specifications

**Investment Goal** (single select)
- Yield Focus (4%+ target)
- Growth Focus (12%+ YoY)
- Value Play (below market)
- Balanced Approach

**Budget Range** (dual-handle slider)
- Price PSF: $400 - $1000+
- Total Price: $300K - $2M+

**Property Type** (multi-select with smart insights)
- [x] HDB (note: MRT impact minimal ~$5/100m)
- [x] Condominium (note: 15x MRT sensitive)
- [x] EC (note: volatile post-COVID, -1790% shift)

**Location Preferences** (multi-select)
- Region: CCR / RCR / OCR
- CBD Distance: <2km, 2-5km, 5-10km, >10km
- MRT Distance: <500m, 500m-1km, >1km
- Spatial Cluster: HH / LH / LL (with persistence indicators)

**Time Horizon** (single select)
- Short-term (1-3 years): Focus on growth segments
- Medium-term (3-7 years): Balanced growth + yield
- Long-term (7+ years): Focus on stable yields, appreciation

### Three Main Tabs

#### Tab 1: Discover
**Purpose**: Explore segments matching user criteria

**Components**:
1. **Segment Grid**: Cards showing matching segments
   - Segment name with icon (e.g., 🔥 High Growth Recent)
   - Match score to user criteria (0-100%)
   - Key metrics: Price PSF, Yield, YoY Growth
   - Property count and market share
   - Color coding by segment type

2. **Sorting Options**:
   - Relevance (match score)
   - Price PSF (low to high)
   - Rental Yield (high to low)
   - YoY Growth (high to low)
   - Transaction Volume

3. **Quick Actions**:
   - [View Details] → Opens detail modal
   - [Add to Compare] → Adds to comparison set
   - [View Properties] → Shows representative properties

4. **Contextual Insight Cards**:
   - Display based on active filters
   - Examples:
     - "Condos are 15x more MRT-sensitive than HDB"
     - "Hotspots have 58-62% persistence probability"
     - "School premiums vary by region (OCR +$9.63, RCR -$23.67 PSF)"

**Segment Card Design**:
```
┌─────────────────────────────────────┐
│ 🔥 High Growth Recent      Match: 92%│
│ ───────────────────────────────────  │
│ 💰 $509 PSF    📈 +24.4% YoY         │
│ 🏦 5.2% Yield  📊 33.0% of market    │
│                                      │
│ [Details] [Compare] [View Properties]│
└─────────────────────────────────────┘
```

#### Tab 2: Compare
**Purpose**: Side-by-side comparison of selected segments

**Components**:
1. **Comparison Table**:
   - Rows: Price PSF, Yield, YoY Growth, Volume, Persistence, Risk Level
   - Columns: 2-4 selected segments
   - Highlighting: Best values in each column

2. **Visual Comparisons**:
   - Bar chart: Key metrics comparison
   - Radar chart: Multi-dimensional comparison
   - Charts update dynamically when segments added/removed

3. **Investment Implications** (by persona):
   - **For Investors**: Yield/growth trade-offs, risk assessments
   - **For First-Time Buyers**: Affordability, long-term value
   - **For Upsizers**: Space value, neighborhood quality

**Comparison Table Example**:
```
┌────────────────────────────────────────────────────────────┐
│                        Compare Segments                    │
├──────────────────┬─────────────────┬─────────────────────┤
│ Metric           │ High Growth     │ Mid-Tier Value       │
├──────────────────┼─────────────────┼─────────────────────┤
│ Price PSF        │ $509            │ $463 ✓              │
│ Rental Yield     │ 5.2%            │ 6.36% ✓             │
│ YoY Growth       │ 24.4% ✓         │ 8.5%                │
│ Persistence      │ 58-62%          │ Stable              │
│ Risk Level       │ Medium          │ Low ✓               │
└──────────────────┴─────────────────┴─────────────────────┘
```

#### Tab 3: Details
**Purpose**: Comprehensive deep-dive into a selected segment

**Sections**:
1. **Overview**:
   - Segment name, type, icon
   - Key stats (price, yield, growth, volume)
   - Description and characteristics
   - Risk level badge

2. **Geographic Distribution**:
   - Map view showing planning areas in this segment
   - List of top areas by transaction volume
   - Regional breakdown (CCR/RCR/OCR)

3. **Representative Properties**:
   - Sample properties with key metrics
   - Filter/sort within segment
   - Links to property details (if available)

4. **Investment Implications** (by persona):
   - **Investors**: Strategy, expected returns, risks
   - **First-Time Buyers**: Suitability, considerations
   - **Upsizers**: Space value, trade-offs

5. **Risk Factors**:
   - List of specific risks for this segment
   - Mitigation strategies
   - Warning indicators

6. **Related Segments**:
   - Similar segments users might consider
   - "Consider also" suggestions

### Persona Selector Component

**Location**: Header, top-right

**Functionality**:
- Dropdown with options: All Personas, First-Time Buyer, Property Investor, Upsizer
- When persona selected:
  - Auto-configures filters to persona defaults
  - Shows persona-specific insight cards
  - Adjusts segment sorting priorities
  - Tails implications language

**Persona Presets**:

```typescript
const PERSONA_PRESETS = {
  first_time_buyer: {
    investmentGoal: 'value',
    budgetRange: [400, 600],  // Price PSF
    propertyTypes: ['HDB'],
    timeHorizon: 'long',
    priorityMetrics: ['affordability', 'school_quality', 'lease_remaining'],
    defaultInsights: [
      'school_premiums_by_region',
      'affordability_ratios',
      'lease_decay_bands'
    ]
  },
  investor: {
    investmentGoal: 'yield',
    budgetRange: [500, 1000],
    propertyTypes: ['Condominium', 'HDB'],
    timeHorizon: 'medium',
    priorityMetrics: ['rental_yield', 'mrt_proximity', 'appreciation'],
    defaultInsights: [
      'condo_mrt_sensitivity',
      'hotspot_persistence',
      'yield_vs_growth_tradeoff'
    ]
  },
  upgrader: {
    investmentGoal: 'balanced',
    budgetRange: [500, 800],
    propertyTypes: ['HDB', 'Condominium'],
    timeHorizon: 'long',
    priorityMetrics: ['space_value', 'neighborhood', 'amenities'],
    defaultInsights: [
      'ocr_space_premium',
      'amenity_importance',
      'commute_tradeoffs'
    ]
  }
};
```

---

## Data Integration

### Data Sources

The dashboard will integrate data from 5 analytics outputs:

1. **Investment Clusters** (`docs/analytics/findings.md`)
   - 6 cluster types with metrics and strategies
   - Segment sizes and market shares

2. **Spatial Clusters** (`docs/analytics/spatial-autocorrelation.md`)
   - HH/LH/LL classifications
   - Persistence probabilities (58-62%)
   - Neighborhood effect correlations (71-78%)

3. **Spatial Hotspots** (`docs/analytics/spatial-hotspots.md`)
   - Gi* statistics and p-values
   - 99% confidence hotspots (12 cells)
   - Geographic distribution

4. **MRT Impact** (`docs/analytics/mrt-impact.md`)
   - MRT premiums by property type
   - CBD vs MRT decomposition
   - Temporal evolution (2017-2026)

5. **School Quality** (`docs/analytics/school-quality.md`)
   - School tiers and quality scores
   - Regional variations (OCR +$9.63, RCR -$23.67)
   - 1km boundary effects

### Data Schema

```typescript
interface SegmentsData {
  segments: Segment[];
  planningAreas: Record<string, PlanningArea>;
  insights: Insight[];
  lastUpdated: string;
  version: string;
}

interface Segment {
  id: string;  // e.g., "high_growth_recent"
  name: string;
  description: string;
  investmentType: 'yield' | 'growth' | 'value' | 'balanced' | 'luxury' | 'speculative';

  // Classification
  clusterClassification: 'HH' | 'LH' | 'LL';
  persistenceProbability: number;  // 0.58 for HH

  // Metrics
  metrics: {
    avgPricePsf: number;
    avgYield: number;
    yoyGrowth: number;
    transactionCount: number;
    marketShare: number;
  };

  // Characteristics
  characteristics: {
    priceTier: 'affordable' | 'moderate' | 'premium' | 'luxury';
    riskLevel: 'low' | 'medium' | 'high' | 'very_high';
    volatility: 'low' | 'moderate' | 'high';
    appreciationPotential: 'low' | 'moderate' | 'high' | 'exceptional';
  };

  // Persona-Specific Implications
  implications: {
    investor: string;
    firstTimeBuyer: string;
    upgrader: string;
  };

  // Geographic Coverage
  planningAreas: string[];
  regions: ('CCR' | 'RCR' | 'OCR')[];

  // Property Types
  propertyTypes: ('HDB' | 'Condominium' | 'EC')[];

  // Spatial/MRT/School Characteristics
  spatialClassification: 'HH' | 'LH' | 'LL';
  mrtSensitivity: 'low' | 'moderate' | 'high';
  schoolQuality: 'tier_1' | 'tier_2' | 'tier_3' | 'mixed';

  // Guidance
  riskFactors: string[];
  opportunities: string[];
}

interface PlanningArea {
  name: string;
  region: 'CCR' | 'RCR' | 'OCR';

  // Spatial Classification
  spatialCluster: 'HH' | 'LH' | 'LL';
  hotspotConfidence: '99%' | '95%' | 'not_significant';
  persistenceProbability: number;

  // MRT Characteristics
  mrtPremium: number;  // Per 100m
  mrtSensitivity: 'low' | 'moderate' | 'high';
  cbdDistance: number;  // km

  // School Characteristics
  schoolTier: 'tier_1' | 'tier_2' | 'tier_3' | 'mixed';
  schoolPremium: number;  // PSF

  // Market Data
  forecast6m: number;  // % change
  avgPricePsf: number;
  avgYield: number;

  // Segment Membership
  segments: string[];
}

interface Insight {
  id: string;
  title: string;
  content: string;
  source: string;  // Analytics document

  // Applicability
  relevantFor: ('investor' | 'first_time_buyer' | 'upgrader')[];
  propertyTypes?: ('HDB' | 'Condominium' | 'EC')[];
  segments?: string[];

  // Priority
  personaApplicability: {
    investor: 'critical' | 'helpful' | 'optional';
    firstTimeBuyer: 'critical' | 'helpful' | 'optional';
    upgrader: 'critical' | 'helpful' | 'optional';
  };

  // Link
  learnMoreUrl?: string;
}
```

### Example Data

```json
{
  "segments": [
    {
      "id": "high_growth_recent",
      "name": "High Growth Recent",
      "description": "Moderate PSF with exceptional YoY growth for growth-oriented investors",
      "investmentType": "growth",
      "clusterClassification": "HH",
      "persistenceProbability": 0.58,
      "metrics": {
        "avgPricePsf": 509,
        "avgYield": 5.2,
        "yoyGrowth": 24.4,
        "transactionCount": 300872,
        "marketShare": 0.33
      },
      "characteristics": {
        "priceTier": "moderate",
        "riskLevel": "medium",
        "volatility": "high",
        "appreciationPotential": "exceptional"
      },
      "implications": {
        "investor": "Growth investing for capital appreciation. Target 3-5 year holding period.",
        "firstTimeBuyer": "Risky for first-time buyers. Consider if holding 10+ years.",
        "upgrader": "Good for upgrading to high-appreciation areas if timing is right."
      },
      "planningAreas": ["Toa Payoh", "Queenstown", "Serangoon", "Bishan"],
      "regions": ["RCR", "OCR"],
      "propertyTypes": ["HDB", "Condominium"],
      "spatialClassification": "HH",
      "mrtSensitivity": "moderate",
      "schoolQuality": "mixed",
      "riskFactors": [
        "High volatility - timing critical",
        "Hotspot persistence 58% - not guaranteed",
        "Market correction risk"
      ],
      "opportunities": [
        "Exceptional 24.4% YoY growth",
        "Emerging hotspots with upside",
        "Strong rental demand in HH areas"
      ]
    }
  ],
  "planningAreas": {
    "toa_payoh": {
      "name": "Toa Payoh",
      "region": "RCR",
      "spatialCluster": "HH",
      "hotspotConfidence": "99%",
      "persistenceProbability": 0.62,
      "mrtPremium": 5.88,
      "mrtSensitivity": "moderate",
      "cbdDistance": 4.2,
      "schoolTier": "mixed",
      "schoolPremium": 9.63,
      "forecast6m": 79.2,
      "avgPricePsf": 644,
      "avgYield": 5.1,
      "segments": ["high_growth_recent", "large_size_stable"]
    }
  },
  "insights": [
    {
      "id": "condo_mrt_sensitivity",
      "title": "Condos are 15x More MRT-Sensitive Than HDB",
      "content": "Condo MRT premium: $35/100m vs HDB: $5/100m. Prioritize MRT proximity for condos, but focus on CBD distance and lease for HDB.",
      "source": "mrt-impact.md",
      "relevantFor": ["investor", "first_time_buyer", "upgrader"],
      "propertyTypes": ["Condominium", "HDB"],
      "personaApplicability": {
        "investor": "critical",
        "firstTimeBuyer": "helpful",
        "upgrader": "helpful"
      },
      "learnMoreUrl": "/analytics/mrt-impact"
    },
    {
      "id": "hotspot_persistence",
      "title": "Hotspots Have 58-62% Persistence Probability",
      "content": "Once an area becomes a hotspot (HH cluster), there's a 58-62% chance it remains a hotspot year-over-year. Offers relatively predictable appreciation for investors.",
      "source": "spatial-autocorrelation.md",
      "relevantFor": ["investor"],
      "segments": ["high_growth_recent", "large_size_stable"],
      "personaApplicability": {
        "investor": "critical",
        "firstTimeBuyer": "helpful",
        "upgrader": "helpful"
      },
      "learnMoreUrl": "/analytics/spatial-autocorrelation"
    },
    {
      "id": "school_premiums_by_region",
      "title": "School Premiums Vary Dramatically by Region",
      "content": "OCR shows positive school premium (+$9.63 PSF), RCR shows negative effect (-$23.67 PSF), CCR shows no effect. Location matters more than school access.",
      "source": "school-quality.md",
      "relevantFor": ["first_time_buyer", "upgrader"],
      "personaApplicability": {
        "investor": "helpful",
        "firstTimeBuyer": "critical",
        "upgrader": "helpful"
      },
      "learnMoreUrl": "/analytics/school-quality"
    }
  ],
  "lastUpdated": "2026-02-22T10:00:00Z",
  "version": "1.0.0"
}
```

### Data Generation Pipeline

**New Script**: `scripts/generate_segments_data.py`

```python
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
from datetime import datetime
from pathlib import Path
import pandas as pd

def generate_segments_data():
    """Generate comprehensive segments data."""

    # 1. Load analysis outputs
    segments = load_investment_clusters()
    spatial_data = load_spatial_clusters()
    hotspot_data = load_hotspot_data()
    mrt_data = load_mrt_analysis()
    school_data = load_school_impact()

    # 2. Enrich segments with spatial/MRT/school data
    for segment in segments:
        segment['spatialClassification'] = map_to_spatial_cluster(segment)
        segment['persistenceProbability'] = get_persistence(segment['clusterClassification'])
        segment['mrtSensitivity'] = determine_mrt_sensitivity(segment, mrt_data)
        segment['schoolQuality'] = determine_school_quality(segment, school_data)
        segment['planningAreas'] = get_areas_in_segment(segment, spatial_data)
        segment['implications'] = generate_implications(segment)

    # 3. Enrich planning areas
    planning_areas = {}
    for area in spatial_data['planning_areas']:
        planning_areas[area['name']] = {
            'name': area['name'],
            'region': area['region'],
            'spatialCluster': area['cluster'],
            'persistenceProbability': area.get('persistence', 0.58),
            'mrtPremium': mrt_data['by_town'].get(area['name'], {}).get('premium', 0),
            'cbdDistance': area.get('cbd_distance', 0),
            'schoolTier': school_data['by_area'].get(area['name'], {}).get('tier', 'mixed'),
            'forecast6m': area.get('forecast_6m', 0),
            'segments': area.get('segments', [])
        }

    # 4. Generate insight cards
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

    print(f"✅ Generated segments data with {len(segments)} segments")
    print(f"   - {len(planning_areas)} planning areas")
    print(f"   - {len(insights)} insight cards")
    print(f"   - Saved to {output_path}")

    return output

if __name__ == '__main__':
    generate_segments_data()
```

**Integration with Existing Pipeline**:

Update `scripts/prepare_webapp_data.py`:

```python
# Add to main function
def main():
    # ... existing code ...

    # Generate enhanced segments data
    print("Generating enhanced segments data...")
    from scripts.generate_segments_data import generate_segments_data
    generate_segments_data()

    # ... rest of pipeline ...
```

---

## Implementation Phases

### Phase 1: Data Foundation (Week 1-2)

**Goal**: Build data pipeline to generate enhanced segments data

**Tasks**:
1. Create `scripts/generate_segments_data.py`
2. Define data schema and TypeScript interfaces
3. Integrate outputs from 5 analytics sources
4. Implement segment enrichment logic
5. Generate insight cards from analytics
6. Update `prepare_webapp_data.py`
7. Write unit tests for data generation

**Deliverables**:
- `scripts/generate_segments_data.py`
- `segments_enhanced.json.gz`
- TypeScript types file
- Unit tests

**Acceptance Criteria**:
- All 6 investment clusters present with complete metadata
- All planning areas enriched with spatial/MRT/school data
- Insight cards generated from all 4 analytics sources
- Data validated against analytics outputs
- Tests pass

---

### Phase 2: Core UI Components (Week 3-4)

**Goal**: Build fundamental UI components

**Tasks**:
1. **FilterPanel Component**
   - Multi-section collapsible filters
   - Investment goal, budget, property type, location, time horizon
   - Reset button with active filter count

2. **PersonaSelector Component**
   - Dropdown in header
   - Persona presets with auto-configuration
   - Visual feedback

3. **SegmentCard Component**
   - Card layout with segment icon, name, match score
   - Key metrics display
   - Action buttons

4. **TabNavigation Component**
   - Discover / Compare / Details tabs
   - Tab-specific content areas

5. **State Management Hooks**
   - `useSegmentsData.ts`
   - `useFilterState.ts`
   - `useSegmentMatching.ts`

**Deliverables**:
- `FilterPanel.tsx`
- `PersonaSelector.tsx`
- `SegmentCard.tsx`
- `TabNavigation.tsx`
- Custom hooks

**Acceptance Criteria**:
- All filters functional with state persistence
- Persona selection updates filter defaults
- Segment cards display correctly with all metrics
- Tab switching works smoothly

---

### Phase 3: Discover Tab (Week 5)

**Goal**: Build main discovery interface

**Tasks**:
1. **SegmentGrid Component**
   - Responsive grid layout
   - Sorting by relevance, price, yield, growth
   - Empty state handling

2. **Match Score Algorithm**
   - Implement scoring logic
   - Display match percentage
   - Sort by relevance by default

3. **InsightCard Component**
   - Contextual insight display
   - "Learn more" links
   - Dynamic based on filters/persona

4. **SegmentDetailModal Component**
   - Quick preview overlay
   - Full segment details
   - Link to Details tab

**Deliverables**:
- `DiscoverTab.tsx`
- `SegmentGrid.tsx`
- `InsightCard.tsx`
- `SegmentDetailModal.tsx`

**Acceptance Criteria**:
- All segments display in grid
- Sorting works for all options
- Match scores calculated accurately
- Insight cards show relevant context

---

### Phase 4: Compare Tab (Week 6)

**Goal**: Build segment comparison functionality

**Tasks**:
1. **ComparisonTable Component**
   - Side-by-side layout (2-4 segments)
   - Metrics comparison with highlighting
   - Best value indicators

2. **ComparisonCharts Component**
   - Bar chart for metrics
   - Radar chart for multi-dimensional
   - Recharts integration

3. **Add to Compare Functionality**
   - Checkbox on cards
   - Comparison limit (4 max)
   - Remove from compare

4. **InvestmentImplications Component**
   - Persona-specific pros/cons
   - Risk comparisons
   - Scenario examples

**Deliverables**:
- `CompareTab.tsx`
- `ComparisonTable.tsx`
- `ComparisonCharts.tsx`
- `InvestmentImplications.tsx`

**Acceptance Criteria**:
- Add/remove segments works
- Comparison table displays accurately
- Charts render correctly with 2-4 segments
- Investment implications show for each persona

---

### Phase 5: Details Tab (Week 7)

**Goal**: Build comprehensive segment detail view

**Tasks**:
1. **SegmentOverview Component**
   - Stats, description, cluster type
   - Risk level badge
   - Characteristics display

2. **GeographicDistribution Component**
   - Map placeholder for future
   - List of planning areas
   - Regional breakdown

3. **SegmentProperties Component**
   - Representative properties list
   - Filter/sort within segment
   - Property cards

4. **RiskFactors Component**
   - Risk list
   - Mitigation strategies
   - Warning indicators

5. **RelatedSegments Component**
   - Similar segments
   - "Consider also" suggestions

**Deliverables**:
- `DetailsTab.tsx`
- `SegmentOverview.tsx`
- `GeographicDistribution.tsx`
- `SegmentProperties.tsx`
- `RiskFactors.tsx`
- `RelatedSegments.tsx`

**Acceptance Criteria**:
- All sections display correctly
- Representative properties load accurately
- Related segments suggestions work
- Navigation back to discover works

---

### Phase 6: Polish & Testing (Week 8)

**Goal**: Refine UX, fix bugs, optimize performance

**Tasks**:
1. **Performance Optimization**
   - Lazy loading for segment cards
   - Code splitting
   - React.memo for optimization

2. **Accessibility**
   - Keyboard navigation
   - Screen reader support
   - Color contrast validation
   - ARIA labels

3. **Responsive Design**
   - Mobile layout optimization
   - Tablet adjustments
   - Filter sidebar toggle on mobile

4. **Edge Cases**
   - Empty states
   - Loading states
   - Error states
   - Validation

5. **Testing**
   - Unit tests for components
   - Integration tests for flows
   - E2E tests for journeys
   - Cross-browser testing

**Deliverables**:
- Performance optimizations
- Accessibility audit
- Responsive design
- Test suite

**Acceptance Criteria**:
- Lighthouse score >90
- WCAG 2.1 AA compliance
- Works on mobile, tablet, desktop
- Test coverage >80%

---

## File Structure

```
app/src/
├── pages/dashboard/
│   └── segments.astro (existing - update)
├── components/dashboard/segments/
│   ├── SegmentsDashboard.tsx (new - main container)
│   ├── FilterPanel.tsx
│   ├── PersonaSelector.tsx
│   ├── TabNavigation.tsx
│   ├── discover/
│   │   ├── DiscoverTab.tsx
│   │   ├── SegmentGrid.tsx
│   │   ├── SegmentCard.tsx
│   │   ├── InsightCard.tsx
│   │   └── SegmentDetailModal.tsx
│   ├── compare/
│   │   ├── CompareTab.tsx
│   │   ├── ComparisonTable.tsx
│   │   ├── ComparisonCharts.tsx
│   │   └── InvestmentImplications.tsx
│   └── details/
│       ├── DetailsTab.tsx
│       ├── SegmentOverview.tsx
│       ├── GeographicDistribution.tsx
│       ├── SegmentProperties.tsx
│       ├── RiskFactors.tsx
│       └── RelatedSegments.tsx
├── hooks/
│   ├── useSegmentsData.ts (new)
│   ├── useFilterState.ts (new)
│   ├── useSegmentMatching.ts (new)
│   └── usePersonaPresets.ts (new)
├── types/
│   └── segments.ts (new - TypeScript interfaces)
└── lib/
    └── segmentMatching.ts (new - matching algorithms)

scripts/
└── generate_segments_data.py (new)
```

---

## Key Algorithms

### Match Score Calculation

```typescript
interface FilterState {
  investmentGoal: string | null;
  budgetRange: [number, number];
  propertyTypes: string[];
  locations: string[];
  timeHorizon: string | null;
}

function calculateMatchScore(
  segment: Segment,
  filters: FilterState
): number {
  let score = 0;
  let maxScore = 0;

  // Investment goal (30% weight)
  if (filters.investmentGoal === 'yield' && segment.metrics.avgYield >= 4) {
    score += 30;
  }
  if (filters.investmentGoal === 'growth' && segment.metrics.yoyGrowth >= 12) {
    score += 30;
  }
  if (filters.investmentGoal === 'value' && segment.characteristics.priceTier === 'affordable') {
    score += 30;
  }
  maxScore += 30;

  // Budget fit (25% weight)
  if (
    segment.metrics.avgPricePsf >= filters.budgetRange[0] &&
    segment.metrics.avgPricePsf <= filters.budgetRange[1]
  ) {
    score += 25;
  }
  maxScore += 25;

  // Property type match (20% weight)
  if (filters.propertyTypes.some(t => segment.propertyTypes.includes(t))) {
    score += 20;
  }
  maxScore += 20;

  // Time horizon fit (15% weight)
  if (filters.timeHorizon === 'short' && segment.characteristics.volatility === 'high') {
    score += 15;
  }
  if (filters.timeHorizon === 'long' && segment.characteristics.volatility === 'low') {
    score += 15;
  }
  maxScore += 15;

  // Risk alignment (10% weight)
  if (filters.investmentGoal === 'yield' && segment.characteristics.riskLevel === 'low') {
    score += 10;
  }
  if (filters.investmentGoal === 'growth' && segment.characteristics.riskLevel === 'medium') {
    score += 10;
  }
  maxScore += 10;

  return Math.round((score / maxScore) * 100);
}
```

### Persona Presets Configuration

```typescript
const PERSONA_PRESETS: Record<
  string,
  { filters: Partial<FilterState>; priorityMetrics: string[]; defaultInsights: string[] }
> = {
  first_time_buyer: {
    filters: {
      investmentGoal: 'value',
      budgetRange: [400, 600],
      propertyTypes: ['HDB'],
      timeHorizon: 'long',
    },
    priorityMetrics: ['affordability', 'school_quality', 'lease_remaining'],
    defaultInsights: ['school_premiums_by_region', 'affordability_ratios', 'lease_decay_bands'],
  },
  investor: {
    filters: {
      investmentGoal: 'yield',
      budgetRange: [500, 1000],
      propertyTypes: ['Condominium', 'HDB'],
      timeHorizon: 'medium',
    },
    priorityMetrics: ['rental_yield', 'mrt_proximity', 'appreciation'],
    defaultInsights: ['condo_mrt_sensitivity', 'hotspot_persistence', 'yield_vs_growth_tradeoff'],
  },
  upgrader: {
    filters: {
      investmentGoal: 'balanced',
      budgetRange: [500, 800],
      propertyTypes: ['HDB', 'Condominium'],
      timeHorizon: 'long',
    },
    priorityMetrics: ['space_value', 'neighborhood', 'amenities'],
    defaultInsights: ['ocr_space_premium', 'amenity_importance', 'commute_tradeoffs'],
  },
};
```

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| **Data Complexity** | High | Medium | Start with subset of segments, expand gradually; validate data thoroughly |
| **Performance Issues** | High | Low | Implement pagination/virtualization if segment count >50; use React.memo |
| **Analytics Changes** | Medium | Low | Version the data schema; handle backward compatibility |
| **User Overwhelm** | Medium | Medium | Provide persona presets; progressive disclosure; helpful defaults |
| **Browser Compatibility** | Low | Low | Test on major browsers; use polyfills if needed |

---

## Success Metrics

### User Engagement
- Time on page: >5 minutes (indicating exploration)
- Filter usage: >70% of users apply filters
- Tab switching: >50% of users use multiple tabs
- Persona selector: >40% of users select a persona

### Feature Usage
- Compare functionality: >30% of users compare segments
- Details view: >60% of users view segment details
- Insight card clicks: >20% of users click "Learn More"

### Performance
- Initial load: <2 seconds
- Filter response: <500ms
- Tab switch: <300ms
- Lighthouse score: >90

### Accessibility
- WCAG 2.1 AA compliance
- Keyboard navigation: All features accessible
- Screen reader: All content announced

---

## Next Steps

1. **Get final approval** of this design document
2. **Invoke writing-plans skill** to create detailed implementation plan
3. **Begin Phase 1**: Data Foundation

---

## Appendix: Analytics Reference

### Key Metrics Summary

| Metric | Value | Source |
|--------|-------|--------|
| **Investment Clusters** | 6 types | findings.md |
| **Spatial Clusters (HH)** | 47.1% of areas, 12.7% YoY | spatial-autocorrelation.md |
| **Hotspot Persistence** | 58-62% probability | spatial-hotspots.md |
| **Condo MRT Sensitivity** | 15x vs HDB | mrt-impact.md |
| **HDB MRT Premium** | $1.28/100m | mrt-impact.md |
| **School Premium (OCR)** | +$9.63 PSF | school-quality.md |
| **School Premium (RCR)** | -$23.67 PSF | school-quality.md |
| **Neighborhood Effect** | 71-78% correlation | spatial-autocorrelation.md |
| **CBD Distance Impact** | 22.6% variance | findings.md |

### Segment Mapping

| Investment Cluster | Spatial Cluster | MRT Sensitivity | School Quality | Strategy |
|--------------------|-----------------|-----------------|----------------|----------|
| Large Size Stable | HH | Moderate | Mixed | Buy and hold |
| High Growth Recent | HH | Moderate | Mixed | Growth investing |
| Speculator Hotspots | HH | High | Tier 1 | Short-term flips |
| Declining Areas | LH | Low | Mixed | Avoid / contrarian |
| Mid-Tier Value | LL | Low | Mixed | Rental income |
| Premium New Units | HH | High | Tier 1 | Luxury segment |

---

**Document End**
