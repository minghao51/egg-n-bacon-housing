#!/usr/bin/env python3
"""Create L3 unified housing dataset with comprehensive features.

This script combines:
- HDB and Condo transaction data from L1
- Geocoding and amenity features from L2
- Planning areas from geojson
- Rental yield data
- Precomputed growth metrics

Creates a comprehensive dataset for Streamlit visualization.

Output:
    L3/housing_unified.parquet - Complete dataset with all features
    L3/market_summary.parquet - Precomputed summary by property_type/period/tier
    L3/tier_thresholds_evolution.parquet - Tier thresholds over time
    L3/planning_area_metrics.parquet - Planning area aggregated metrics
    L3/lease_decay_stats.parquet - HDB lease decay statistics
    L3/rental_yield_top_combos.parquet - Top rental yield combinations

Usage:
    uv run python scripts/create_l3_unified_dataset.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.dashboard.create_l3_unified_dataset import main

if __name__ == "__main__":
    main()
