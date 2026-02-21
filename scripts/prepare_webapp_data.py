#!/usr/bin/env python3
"""
Runner script to export data for the Web Dashboard.
"""

import sys

from scripts.core.config import Config
from scripts.core.logging_config import get_logger, setup_logging_from_env
from scripts.core.script_base import setup_script_environment


def main():
    """Export dashboard data."""
    logger = get_logger(__name__)
    logger.info("🚀 Starting Webapp Data Export")

    # Import after path setup
    from scripts.core.stages.webapp_data_preparation import export_dashboard_data

    export_dashboard_data()

    logger.info("✅ Webapp Export Complete")


if __name__ == "__main__":
    # Setup environment and logging
    setup_script_environment()
    setup_logging_from_env()

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger = get_logger(__name__)
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Run main function
    main()
