"""
Network availability checking utilities.

Provides functions to check network connectivity before attempting
web downloads, and to check if local data already exists.
"""

import logging
import socket
from pathlib import Path

logger = logging.getLogger(__name__)


def is_network_available(host: str = "8.8.8.8", port: int = 53, timeout: float = 2.0) -> bool:
    """
    Check if network is available by attempting TCP connection to a host.

    Args:
        host: Host to check connectivity to (default: 8.8.8.8 - Google DNS)
        port: Port to connect to (default: 53 - DNS)
        timeout: Connection timeout in seconds

    Returns:
        True if network is available, False otherwise

    Example:
        >>> if not is_network_available():
        ...     print("Network unavailable - using cached data")
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except OSError:
        return False


def is_host_reachable(url: str, timeout: float = 5.0) -> bool:
    """
    Check if a specific URL is reachable.

    Args:
        url: URL to check (without query parameters)
        timeout: Request timeout in seconds

    Returns:
        True if host is reachable, False otherwise
    """
    try:
        import requests
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code < 400
    except requests.exceptions.RequestException:
        return False
    except Exception:
        return False


def check_local_file_exists(file_path: Path, min_size_bytes: int = 100) -> bool:
    """
    Check if a local file exists and has valid content.

    Args:
        file_path: Path to the file to check
        min_size_bytes: Minimum file size to consider valid (default: 100 bytes)

    Returns:
        True if file exists and has valid content, False otherwise
    """
    if not file_path.exists():
        return False

    if not file_path.is_file():
        return False

    try:
        file_size = file_path.stat().st_size
        return file_size >= min_size_bytes
    except Exception:
        return False


def require_network(raise_error: bool = False) -> bool:
    """
    Check if network is available with logging.

    Args:
        raise_error: If True, raise RuntimeError when network unavailable

    Returns:
        True if network available, False otherwise

    Raises:
        RuntimeError: If network unavailable and raise_error is True
    """
    if is_network_available():
        logger.debug("Network is available")
        return True

    logger.warning("Network is unavailable - web downloads will fail")

    if raise_error:
        raise RuntimeError("Network is unavailable. Connect to the internet or use cached data.")

    return False
