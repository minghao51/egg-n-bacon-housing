"""
Centralized logging configuration for egg-n-bacon-housing project.

This module provides a consistent logging setup across all scripts,
replacing scattered logging.basicConfig calls.

Usage:
    from scripts.core.logging_config import get_logger, setup_logging

    # Get a logger for your module
    logger = get_logger(__name__)
    logger.info("Script started")

    # Or setup root logging (in main scripts)
    setup_logging(level=logging.INFO)
"""

import logging
import sys
from pathlib import Path
from typing import Optional


# Default log format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    date_format: Optional[str] = None,
    log_file: Optional[Path] = None,
) -> None:
    """
    Configure root logging for the application.

    This should be called once at the beginning of main scripts.
    After calling this, use get_logger() to get module-specific loggers.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (default: DEFAULT_FORMAT)
        date_format: Custom date format (default: DEFAULT_DATE_FORMAT)
        log_file: Optional path to log file for file output

    Example:
        >>> import logging
        >>> from pathlib import Path
        >>> from scripts.core.logging_config import setup_logging
        >>>
        >>> # Console logging only
        >>> setup_logging(level=logging.INFO)
        >>>
        >>> # Console + file logging
        >>> setup_logging(
        ...     level=logging.DEBUG,
        ...     log_file=Path("data/logs/script.log")
        ... )
    """
    fmt = format_string or DEFAULT_FORMAT
    date_fmt = date_format or DEFAULT_DATE_FORMAT

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    # Add file handler if log_file specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(fmt, date_fmt))
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=date_fmt,
        handlers=handlers,
        force=True,  # Override any existing configuration
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module.

    Use this in all modules (not main scripts) to get a properly configured logger.

    Args:
        name: Usually __name__ from the calling module

    Returns:
        Configured logger instance

    Example:
        >>> from scripts.core.logging_config import get_logger
        >>>
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing data")
        >>> logger.debug("Detailed debug info")
        >>> logger.error("Something went wrong")
    """
    return logging.getLogger(name)


def get_logger_level_from_env() -> int:
    """
    Get logging level from environment variable.

    Reads LOG_LEVEL environment variable and converts to logging level.
    Defaults to INFO if not set or invalid.

    Returns:
        Logging level constant

    Example:
        >>> import os
        >>> from scripts.core.logging_config import get_logger_level_from_env
        >>>
        >>> # Set in .env or environment
        >>> # LOG_LEVEL=DEBUG
        >>> level = get_logger_level_from_env()
        >>> setup_logging(level=level)
    """
    import os

    level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    return level_map.get(level_str, logging.INFO)


def setup_logging_from_env(log_file: Optional[Path] = None) -> None:
    """
    Setup logging using environment variables.

    Reads LOG_LEVEL from environment and configures logging accordingly.

    Args:
        log_file: Optional path to log file for file output

    Example:
        >>> # In .env file:
        >>> # LOG_LEVEL=DEBUG
        >>>
        >>> from scripts.core.logging_config import setup_logging_from_env
        >>> setup_logging_from_env()
    """
    level = get_logger_level_from_env()
    setup_logging(level=level, log_file=log_file)
