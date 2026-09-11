"""Centralized logging configuration for egg-n-bacon-housing project.

This module provides a consistent logging setup across all scripts,
replacing scattered logging.basicConfig calls.

Usage:
    from egg_n_bacon_housing.utils.logging_config import get_logger, setup_logging

    # Get a logger for your module
    logger = get_logger(__name__)
    logger.info("Script started")

    # Or setup root logging (in main scripts)
    setup_logging(level=logging.INFO)
"""

import logging
import os
import sys
from pathlib import Path

DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logging(
    level: int = logging.INFO,
    format_string: str | None = None,
    date_format: str | None = None,
    log_file: Path | None = None,
) -> None:
    """Configure root logging for the application.

    This should be called once at the beginning of main scripts.
    After calling this, use get_logger() to get module-specific loggers.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (default: DEFAULT_FORMAT)
        date_format: Custom date format (default: DEFAULT_DATE_FORMAT)
        log_file: Optional path to log file for file output. Console
            routing: records at INFO and below go to stdout only; records at
            WARNING and above go to stderr (mirrored on stdout). File
            handlers receive everything at or above ``level``.

    Example:
        >>> import logging
        >>> from pathlib import Path
        >>> from egg_n_bacon_housing.utils.logging_config import setup_logging
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

    # Console routing: INFO-and-below traffic goes to stdout, while
    # WARNING/ERROR/CRITICAL are additionally mirrored to stderr so failures
    # are visible even when stdout is piped to a file or a downstream tool.
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(min(level, logging.INFO))
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)

    handlers: list[logging.Handler] = [stdout_handler, stderr_handler]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(fmt, date_fmt))
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=date_fmt,
        handlers=handlers,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module.

    Use this in all modules (not main scripts) to get a properly configured logger.

    Args:
        name: Usually __name__ from the calling module

    Returns:
        Configured logger instance

    Example:
        >>> from egg_n_bacon_housing.utils.logging_config import get_logger
        >>>
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing data")
        >>> logger.debug("Detailed debug info")
        >>> logger.error("Something went wrong")
    """
    return logging.getLogger(name)


def _get_logger_level_from_env() -> int:
    """Get logging level from environment variable.

    Reads LOG_LEVEL environment variable and converts to logging level.
    Defaults to INFO if not set or invalid.

    Returns:
        Logging level constant
    """
    level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    return LEVEL_MAP.get(level_str, logging.INFO)


def setup_logging_from_env(log_file: Path | None = None) -> None:
    """Setup logging using environment variables.

    Reads LOG_LEVEL from environment and configures logging accordingly.

    Args:
        log_file: Optional path to log file for file output

    Example:
        >>> # In .env file:
        >>> # LOG_LEVEL=DEBUG
        >>>
        >>> from egg_n_bacon_housing.utils.logging_config import setup_logging_from_env
        >>> setup_logging_from_env()
    """
    level = _get_logger_level_from_env()
    setup_logging(level=level, log_file=log_file)
