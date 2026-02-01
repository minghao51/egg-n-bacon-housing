#!/usr/bin/env python3
"""
Runner script to export data for the Web Dashboard.
"""

import sys
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.core.stages.web_export import export_dashboard_data

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    export_dashboard_data()
