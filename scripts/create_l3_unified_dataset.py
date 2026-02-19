#!/usr/bin/env python3
"""Create L3 unified housing dataset for analytics.

This script is a convenience wrapper that imports the main function
from scripts/data/create_l3_unified_dataset.py.

Output:
    L3/housing_unified.parquet - Complete dataset with all features

Usage:
    uv run python scripts/create_l3_unified_dataset.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.data.create_l3_unified_dataset import main  # noqa: E402

if __name__ == "__main__":
    main()
