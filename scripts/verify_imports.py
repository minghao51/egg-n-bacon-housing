#!/usr/bin/env python3
"""Compatibility wrapper for the relocated import verification script."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.tools.verify_imports import *  # noqa: F401,F403

if __name__ == "__main__":
    raise SystemExit(main())
