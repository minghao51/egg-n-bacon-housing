"""
Shared pytest fixtures and configuration for egg-n-bacon-housing tests.

This file provides common fixtures used across multiple test files.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pandas as pd
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


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

    Creates subdirectories mimicking the project's data structure.

    Yields:
        Path to temporary data directory
    """
    data_dir = temp_dir / "data"
    data_dir.mkdir()

    # Create subdirectories
    (data_dir / "pipeline").mkdir()
    (data_dir / "pipeline" / "L0").mkdir()
    (data_dir / "pipeline" / "L1").mkdir()
    (data_dir / "pipeline" / "L2").mkdir()
    (data_dir / "pipeline" / "L3").mkdir()
    (data_dir / "cache").mkdir()
    (data_dir / "manual").mkdir()

    yield data_dir


@pytest.fixture
def mock_config(monkeypatch, temp_data_dir):
    """
    Mock configuration for testing.

    Sets up test environment variables and paths.

    Example:
        >>> def test_with_mock_config(mock_config):
        ...     # Config is ready for testing
        ...     from scripts.core.config import Config
        ...     assert Config.DATA_DIR.exists()
    """
    # Set required environment variables
    monkeypatch.setenv("ONEMAP_EMAIL", "test@example.com")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    # Import Config after environment is set
    from scripts.core.config import Config

    # Temporarily override paths
    original_data_dir = Config.DATA_DIR
    original_pipeline_dir = Config.PIPELINE_DIR

    Config.DATA_DIR = temp_data_dir
    Config.PIPELINE_DIR = temp_data_dir / "pipeline"
    Config.CACHE_DIR = temp_data_dir / "cache"
    Config.MANUAL_DIR = temp_data_dir / "manual"

    yield Config

    # Restore original paths
    Config.DATA_DIR = original_data_dir
    Config.PIPELINE_DIR = original_pipeline_dir


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """
    Create a sample DataFrame for testing.

    Returns:
        DataFrame with sample data

    Example:
        >>> def test_dataframe_operations(sample_dataframe):
        ...     assert len(sample_dataframe) == 100
        ...     assert "price" in sample_dataframe.columns
    """
    return pd.DataFrame({
        "id": range(100),
        "town": ["Bishan", "Toa Payoh", "Ang Mo Kio"] * 33 + ["Bishan"],
        "price": [500000 + i * 1000 for i in range(100)],
        "floor_area_sqft": [800 + i * 10 for i in range(100)],
        "lease_remaining_years": [99 - i for i in range(100)],
        "latitude": [1.350 + i * 0.001 for i in range(100)],
        "longitude": [103.820 + i * 0.001 for i in range(100)],
    })


@pytest.fixture
def sample_transactions(sample_dataframe) -> pd.DataFrame:
    """
    Create sample transaction data for testing.

    Returns:
        DataFrame with sample HDB transactions

    Example:
        >>> def test_transaction_analysis(sample_transactions):
        ...     assert len(sample_transactions) == 100
    """
    return sample_dataframe


@pytest.fixture
def mock_onemap_response():
    """
    Mock OneMap API response for testing.

    Returns:
        Mock response object

    Example:
        >>> def test_geocoding(mock_onemap_response):
        ...     response = mock_onemap_response
        ...     assert response.status_code == 200
    """
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = {
        "found": 1,
        "totalNumPages": 1,
        "results": [{
            "SEARCHVAL": "BISHAN STREET 12",
            "BLK_NO": "123",
            "ROAD": "BISHAN STREET 12",
            "BUILDING": "BLOCK 123",
            "ADDRESS": "123 BISHAN STREET 12",
            "LATITUDE": "1.350",
            "LONGITUDE": "103.820",
        }]
    }
    return mock


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


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (slow, requires external resources)"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (should be run infrequently)"
    )
    config.addinivalue_line(
        "markers", "api: mark test as making API calls (may need mocking)"
    )

