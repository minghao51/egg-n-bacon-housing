"""Tests for config module."""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config


def test_config_paths():
    """Test that all expected paths exist."""
    assert Config.BASE_DIR.exists(), "BASE_DIR should exist"
    assert Config.DATA_DIR.exists(), "DATA_DIR should exist"
    assert Config.SRC_DIR.exists(), "SRC_DIR should exist"
    assert Config.NOTEBOOKS_DIR.exists(), "NOTEBOOKS_DIR should exist"


def test_parquets_dir_creation():
    """Test that PARQUETS_DIR can be created."""
    # The directory may not exist yet, but should be creatable
    if not Config.PARQUETS_DIR.exists():
        Config.PARQUETS_DIR.mkdir(parents=True, exist_ok=True)
    assert Config.PARQUETS_DIR.exists(), "PARQUETS_DIR should exist after creation"


def test_config_attributes():
    """Test that config has expected attributes."""
    assert hasattr(Config, "BASE_DIR")
    assert hasattr(Config, "DATA_DIR")
    assert hasattr(Config, "PARQUETS_DIR")
    assert hasattr(Config, "USE_CACHING")
    assert hasattr(Config, "VERBOSE_LOGGING")


def test_config_feature_flags():
    """Test that feature flags are set correctly."""
    assert isinstance(Config.USE_CACHING, bool)
    assert isinstance(Config.VERBOSE_LOGGING, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
