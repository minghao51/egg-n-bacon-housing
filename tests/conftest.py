"""
Shared pytest fixtures and configuration for egg-n-bacon-housing tests.

This file provides common fixtures used across multiple test files.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def project_root_path() -> Path:
    """Get the project root path."""
    return Path(__file__).parent.parent


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for test files.

    Yields:
        Path to temporary directory

    Example:
        >>> def test_something(temp_dir):
        ...     test_file = temp_dir / "test.txt"
        ...     test_file.write_text("content")
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_data_dir(temp_dir) -> Generator[Path, None, None]:
    """
    Create a temporary data directory structure.

    Creates subdirectories mimicking the medallion pipeline structure.

    Yields:
        Path to temporary data directory
    """
    data_dir = temp_dir / "data"
    data_dir.mkdir()

    # Create medallion pipeline directories
    (data_dir / "pipeline").mkdir()
    (data_dir / "pipeline" / "01_bronze").mkdir()
    (data_dir / "pipeline" / "02_silver").mkdir()
    (data_dir / "pipeline" / "03_gold").mkdir()
    (data_dir / "pipeline" / "04_platinum").mkdir()
    (data_dir / "cache").mkdir()
    (data_dir / "manual").mkdir()

    yield data_dir


@pytest.fixture
def mock_env_vars(monkeypatch):
    """
    Set up mock environment variables for testing.

    Args:
        monkeypatch: pytest's monkeypatch fixture

    Example:
        >>> def test_with_env(mock_env_vars):
        ...     import os
        ...     assert os.getenv("ONEMAP_EMAIL") == "test@example.com"
    """
    env_vars = {
        "ONEMAP_EMAIL": "test@example.com",
        "GOOGLE_API_KEY": "test-api-key",
        "ONEMAP_EMAIL_PASSWORD": "test-password",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test-key",
        "JINA_AI": "test-jina-key",
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars
