"""
Tests for scripts.core.config module.

This test suite validates configuration loading, validation,
and path management.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.core.config import Config


@pytest.mark.unit
class TestConfigPaths:
    """Test configuration path setup."""

    def test_base_dir_exists(self):
        """Test that BASE_DIR is correctly set."""
        assert Config.BASE_DIR is not None
        assert isinstance(Config.BASE_DIR, Path)
        assert Config.BASE_DIR.exists()

    def test_data_dir_relative_to_base(self):
        """Test that DATA_DIR is relative to BASE_DIR."""
        assert Config.DATA_DIR == Config.BASE_DIR / "data"

    def test_pipeline_dir_relative_to_data(self):
        """Test that PIPELINE_DIR is relative to DATA_DIR."""
        assert Config.PIPELINE_DIR == Config.DATA_DIR / "pipeline"

    def test_parquets_dir_alias(self):
        """Test that PARQUETS_DIR is an alias for PIPELINE_DIR."""
        assert Config.PARQUETS_DIR == Config.PIPELINE_DIR

    def test_manual_dir_relative_to_data(self):
        """Test that MANUAL_DIR is relative to DATA_DIR."""
        assert Config.MANUAL_DIR == Config.DATA_DIR / "manual"

    def test_analysis_dir_relative_to_data(self):
        """Test that ANALYSIS_DIR is relative to DATA_DIR."""
        assert Config.ANALYSIS_DIR == Config.DATA_DIR / "analysis"


@pytest.mark.unit
class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_with_missing_env_vars(self, monkeypatch):
        """Test that validation fails with missing required env vars."""
        # Remove required env vars
        monkeypatch.delenv("ONEMAP_EMAIL", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with pytest.raises(ValueError, match="Missing required configuration"):
            Config.validate()

    def test_validate_with_missing_data_dir(self, monkeypatch, temp_dir):
        """Test that validation fails if DATA_DIR doesn't exist."""
        monkeypatch.setenv("ONEMAP_EMAIL", "test@example.com")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        # Mock BASE_DIR to point to non-existent directory
        with patch.object(Config, "BASE_DIR", temp_dir / "nonexistent"):
            with patch.object(Config, "DATA_DIR", temp_dir / "nonexistent" / "data"):
                with pytest.raises(ValueError, match="DATA_DIR does not exist"):
                    Config.validate()

    def test_validate_creates_directories(self, monkeypatch, temp_data_dir):
        """Test that validation creates required directories."""
        monkeypatch.setenv("ONEMAP_EMAIL", "test@example.com")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        # Remove existing directories
        for stage in ["L0", "L1", "L2", "L3"]:
            stage_dir = temp_data_dir / "pipeline" / stage
            if stage_dir.exists():
                stage_dir.rmdir()

        # Mock Config to use temp directory
        with patch.object(Config, "DATA_DIR", temp_data_dir):
            with patch.object(Config, "PIPELINE_DIR", temp_data_dir / "pipeline"):
                with patch.object(Config, "MANUAL_DIR", temp_data_dir / "manual"):
                    with patch.object(Config, "ANALYSIS_DIR", temp_data_dir / "analysis"):
                        with patch.object(Config, "ARCHIVE_DIR", temp_data_dir.parent / "archive"):
                            with patch.object(Config, "CACHE_DIR", temp_data_dir / "cache"):
                                Config.validate()

                                # Check that directories were created
                                for stage in ["L0", "L1", "L2", "L3"]:
                                    stage_dir = temp_data_dir / "pipeline" / stage
                                    assert stage_dir.exists()
                                    assert stage_dir.is_dir()


@pytest.mark.unit
class TestConfigAPIKeys:
    """Test API key configuration."""

    def test_onemap_email_from_env(self, monkeypatch):
        """Test ONEMAP_EMAIL is loaded from environment."""
        test_email = "test@example.com"
        monkeypatch.setenv("ONEMAP_EMAIL", test_email)

        # Force reload of config
        import importlib
        import scripts.core.config
        importlib.reload(scripts.core.config)
        from scripts.core.config import Config

        assert Config.ONEMAP_EMAIL == test_email

    def test_google_api_key_from_env(self, monkeypatch):
        """Test GOOGLE_API_KEY is loaded from environment."""
        test_key = "test-google-key-123"
        monkeypatch.setenv("GOOGLE_API_KEY", test_key)

        # Force reload of config
        import importlib
        import scripts.core.config
        importlib.reload(scripts.core.config)
        from scripts.core.config import Config

        assert Config.GOOGLE_API_KEY == test_key

    def test_optional_api_keys_none_if_missing(self):
        """Test that optional API keys are None if not set."""
        # These should not raise errors if missing
        assert Config.SUPABASE_URL is None or isinstance(Config.SUPABASE_URL, str)
        assert Config.SUPABASE_KEY is None or isinstance(Config.SUPABASE_KEY, str)
        assert Config.JINA_AI is None or isinstance(Config.JINA_AI, str)


@pytest.mark.unit
class TestConfigPrint:
    """Test configuration printing."""

    def test_print_config_runs(self, capsys):
        """Test that print_config executes without errors."""
        Config.print_config()

        captured = capsys.readouterr()
        assert "BASE_DIR:" in captured.out
        assert "DATA_DIR:" in captured.out
        assert "PIPELINE_DIR:" in captured.out


@pytest.mark.unit
class TestConfigFeatureFlags:
    """Test feature flag configuration."""

    def test_use_caching_default(self):
        """Test USE_CACHING has a default value."""
        assert isinstance(Config.USE_CACHING, bool)

    def test_cache_dir_set(self):
        """Test CACHE_DIR is configured."""
        assert Config.CACHE_DIR is not None
        assert isinstance(Config.CACHE_DIR, Path)

    def test_verbose_logging_default(self):
        """Test VERBOSE_LOGGING has a default value."""
        assert isinstance(Config.VERBOSE_LOGGING, bool)

    def test_cache_duration_hours_default(self):
        """Test CACHE_DURATION_HOURS has a default value."""
        assert isinstance(Config.CACHE_DURATION_HOURS, (int, float))


@pytest.mark.unit
class TestConfigGeocodingSettings:
    """Test geocoding configuration settings."""

    def test_geocoding_max_workers(self):
        """Test GEOCODING_MAX_WORKERS is configured."""
        assert isinstance(Config.GEOCODING_MAX_WORKERS, int)
        assert Config.GEOCODING_MAX_WORKERS > 0

    def test_geocoding_api_delay(self):
        """Test GEOCODING_API_DELAY is configured."""
        assert isinstance(Config.GEOCODING_API_DELAY, (int, float))
        assert Config.GEOCODING_API_DELAY > 0

    def test_geocoding_timeout(self):
        """Test GEOCODING_TIMEOUT is configured."""
        assert isinstance(Config.GEOCODING_TIMEOUT, int)
        assert Config.GEOCODING_TIMEOUT > 0


@pytest.mark.unit
class TestConfigParquetSettings:
    """Test parquet file configuration settings."""

    def test_parquet_compression(self):
        """Test PARQUET_COMPRESSION is set."""
        assert Config.PARQUET_COMPRESSION in ["snappy", "gzip", "brotli", "zstd"]

    def test_parquet_index(self):
        """Test PARQUET_INDEX is a boolean."""
        assert isinstance(Config.PARQUET_INDEX, bool)

    def test_parquet_engine(self):
        """Test PARQUET_ENGINE is set."""
        assert Config.PARQUET_ENGINE in ["pyarrow", "fastparquet"]


@pytest.mark.integration
class TestConfigIntegration:
    """Integration tests for configuration."""

    def test_full_config_validation(self, mock_env_vars, monkeypatch):
        """Test full configuration validation with proper environment."""
        # This test requires proper environment setup
        # Should not raise any errors
        try:
            Config.validate()
        except Exception as e:
            pytest.fail(f"Config.validate() raised {e} unexpectedly")
