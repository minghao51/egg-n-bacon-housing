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
