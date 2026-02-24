#!/usr/bin/env python3
"""Convenience wrapper for the L3 unified dataset creator."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.data.create_l3_unified_dataset import *  # noqa: F401,F403


if __name__ == "__main__":
    main()
