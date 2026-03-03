#!/usr/bin/env python3
"""Compatibility wrapper for the relocated spatial hotspots transformer."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.webapp.transform_spatial_hotspots import *  # noqa: F401,F403

if __name__ == "__main__":
    transform_spatial_hotspots()
