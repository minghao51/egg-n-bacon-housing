#!/usr/bin/env python3
"""
Prepare interactive tools data for trends dashboard.

Generates 4 JSON files with analytics insights:
- mrt_cbd_impact.json.gz: Town-level MRT and CBD distance effects
- lease_decay_analysis.json.gz: Lease age band price discounts
- affordability_metrics.json.gz: Town-level affordability ratios
- spatial_hotspots.json.gz: Cluster classifications and performance
"""

import gzip
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd

# Add project root to path for direct script execution
if __name__ == "__main__" and __file__:
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet

logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = Path("app/public/data/interactive_tools")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def compress_json(data: Any, filepath: Path) -> None:
    """Save data as gzip-compressed JSON."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(filepath, 'wt', encoding='utf-8') as f:
        json.dump(data, f)
    logger.info(f"✅ Saved {filepath} ({filepath.stat().st_size / 1024:.1f} KB)")


def generate_mrt_cbd_impact() -> Dict[str, Any]:
    """
    Generate MRT and CBD distance impact data.

    Returns:
        Dictionary with:
        - property_type_multipliers: Base premium per 100m by property type
        - town_multipliers: Town-specific adjustment factors
        - cbd_coefficients: CBD distance effects by property type
        - town_premiums: Full list of town-level MRT premiums
    """
    logger.info("Generating MRT/CBD impact data...")

    # Load unified dataset
    df = load_parquet("L3_housing_unified")

    # Property type base premiums (from analytics findings)
    # HDB: $5 per 100m, Condo: $35 per 100m, EC: estimated $20 per 100m
    property_type_multipliers = {
        "HDB": {"premium_per_100m": 5, "cbd_per_km": 15000},
        "Condominium": {"premium_per_100m": 35, "cbd_per_km": 35000},
        "EC": {"premium_per_100m": 20, "cbd_per_km": 25000}
    }

    # Calculate town-level MRT premiums (HDB only)
    hdb_df = df[df["property_type"] == "HDB"].copy()

    # Group by town, calculate median price and MRT distance
    hdb_prices = hdb_df.groupby("town").agg({
        "price_psf": "median",
        "dist_nearest_mrt_station": "median"
    }).reset_index()

    # Normalize premiums relative to mean
    mean_psf = hdb_df["price_psf"].median()
    hdb_prices["premium_multiplier"] = hdb_prices["price_psf"] / mean_psf

    # Town multipliers (simplified - in production would use regression coefficients)
    town_multipliers = {}
    for _, row in hdb_prices.iterrows():
        town_multipliers[row["town"]] = round(row["premium_multiplier"], 2)

    # Known adjustments from analytics
    town_multipliers.update({
        "Central Area": 2.5,  # +$59/100m
        "Marine Parade": 0.6,  # -$39/100m
        "Bishan": 1.8,
        "Toa Payoh": 1.5,
        "Pasir Ris": 0.8
    })

    return {
        "property_type_multipliers": property_type_multipliers,
        "town_multipliers": town_multipliers,
        "cbd_coefficients": {
            "HDB": {"discount_per_km": 15000, "explanation": "22.6% of price variation"},
            "Condominium": {"discount_per_km": 35000, "explanation": "Higher CBD sensitivity"},
            "EC": {"discount_per_km": 25000, "explanation": "Moderate CBD sensitivity"}
        },
        "town_premiums": [
            {
                "town": town,
                "multiplier": multiplier,
                "hdb_premium_per_100m": round(5 * multiplier, 2),
                "condo_premium_per_100m": round(35 * multiplier, 2)
            }
            for town, multiplier in sorted(town_multipliers.items(), key=lambda x: x[1], reverse=True)
        ]
    }


def main():
    """Generate all interactive tools data files."""
    logger.info("Starting interactive tools data preparation")

    # Generate each dataset
    mrt_cbd_data = generate_mrt_cbd_impact()
    compress_json(mrt_cbd_data, OUTPUT_DIR / "mrt_cbd_impact.json.gz")

    lease_decay_data = generate_lease_decay_analysis()
    compress_json(lease_decay_data, OUTPUT_DIR / "lease_decay_analysis.json.gz")

    affordability_data = generate_affordability_metrics()
    compress_json(affordability_data, OUTPUT_DIR / "affordability_metrics.json.gz")

    hotspots_data = generate_spatial_hotspots()
    compress_json(hotspots_data, OUTPUT_DIR / "spatial_hotspots.json.gz")

    logger.info("✅ Interactive tools data preparation complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
