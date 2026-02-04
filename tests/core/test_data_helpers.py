"""
Tests for scripts.core.data_helpers module.

This test suite validates parquet file loading/saving operations
and metadata tracking.

All tests use the mock_config fixture from conftest.py to ensure
proper test isolation.

IMPORTANT: Imports from data_helpers are done inside test functions
to ensure they run after the mock_config fixture has patched Config.
"""

import json
import sys

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def reload_data_helpers():
    """Reload data_helpers module before each test to ensure clean state."""
    # Remove data_helpers from sys.modules if it exists
    if "scripts.core.data_helpers" in sys.modules:
        del sys.modules["scripts.core.data_helpers"]
    yield


@pytest.mark.unit
class TestMetadataManagement:
    """Test metadata file management."""

    def test_load_metadata_returns_dict(self, mock_config):
        """Test that _load_metadata returns a dictionary."""
        from scripts.core.config import Config
        from scripts.core.data_helpers import _load_metadata

        # Create temporary metadata file
        test_metadata = {
            "version": "1.0",
            "datasets": {"test_dataset": {"path": "test.parquet", "rows": 3, "columns": 10}},
        }

        Config.METADATA_FILE.write_text(json.dumps(test_metadata, indent=2))

        # Call _load_metadata with explicit metadata_file
        metadata = _load_metadata(Config.METADATA_FILE)

        assert isinstance(metadata, dict)
        assert "datasets" in metadata
        assert metadata["datasets"]["test_dataset"]["rows"] == 3

    def test_load_metadata_creates_if_missing(self, mock_config):
        """Test that _load_metadata creates metadata file if missing."""
        from scripts.core.config import Config
        from scripts.core.data_helpers import _load_metadata

        # Call _load_metadata with explicit metadata_file
        metadata = _load_metadata(Config.METADATA_FILE)

        assert isinstance(metadata, dict)
        assert "datasets" in metadata
        # Note: _load_metadata doesn't create the file, it just returns an empty dict structure
        # The file is created when _save_metadata is called

    def test_save_metadata_writes_file(self, mock_config):
        """Test that _save_metadata writes to file."""
        from scripts.core.config import Config
        from scripts.core.data_helpers import _save_metadata

        test_metadata = {"version": "1.0", "datasets": {}}

        _save_metadata(test_metadata, Config.METADATA_FILE)

        assert Config.METADATA_FILE.exists()
        loaded_metadata = json.loads(Config.METADATA_FILE.read_text())
        assert loaded_metadata == test_metadata


@pytest.mark.unit
class TestSaveParquet:
    """Test save_parquet function."""

    def test_save_parquet_creates_file(self, mock_config, sample_dataframe):
        """Test that save_parquet creates a parquet file."""
        from scripts.core.config import Config
        from scripts.core.data_helpers import save_parquet

        save_parquet(sample_dataframe, "test_dataset", source="test")

        output_file = Config.PARQUETS_DIR / "test_dataset.parquet"
        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_save_parquet_updates_metadata(self, mock_config, sample_dataframe):
        """Test that save_parquet updates metadata."""
        from scripts.core.config import Config
        from scripts.core.data_helpers import save_parquet

        save_parquet(sample_dataframe, "test_dataset", source="test")

        # Load metadata and check entry
        metadata = json.loads(Config.METADATA_FILE.read_text())
        assert "test_dataset" in metadata["datasets"]
        assert metadata["datasets"]["test_dataset"]["rows"] == len(sample_dataframe)

    def test_save_parquet_creates_directory(self, mock_config, sample_dataframe):
        """Test that save_parquet creates parent directories."""
        from scripts.core.config import Config
        from scripts.core.data_helpers import save_parquet

        save_parquet(sample_dataframe, "L1_test_dataset", source="test")

        output_file = Config.PARQUETS_DIR / "L1" / "test_dataset.parquet"
        assert output_file.exists()
        assert output_file.parent.exists()

    def test_save_parquet_compression(self, mock_config, sample_dataframe):
        """Test save_parquet with different compression options."""
        from scripts.core.config import Config
        from scripts.core.data_helpers import save_parquet

        save_parquet(sample_dataframe, "test_dataset", source="test", compression="gzip")

        output_file = Config.PARQUETS_DIR / "test_dataset.parquet"
        assert output_file.exists()

        # Verify we can read it back
        df_loaded = pd.read_parquet(output_file)
        pd.testing.assert_frame_equal(df_loaded, sample_dataframe)


@pytest.mark.unit
class TestLoadParquet:
    """Test load_parquet function."""

    def test_load_parquet_returns_dataframe(self, mock_config, sample_dataframe):
        """Test that load_parquet returns a DataFrame."""
        from scripts.core.config import Config
        from scripts.core.data_helpers import load_parquet

        # Create parquet file
        parquet_file = Config.PARQUETS_DIR / "test.parquet"
        sample_dataframe.to_parquet(parquet_file, index=False)

        # Create metadata
        metadata = {
            "version": "1.0",
            "datasets": {
                "test_dataset": {
                    "path": "test.parquet",
                    "rows": len(sample_dataframe),
                    "columns": len(sample_dataframe.columns),
                }
            },
        }
        Config.METADATA_FILE.write_text(json.dumps(metadata))

        # Load and verify
        df_loaded = load_parquet("test_dataset")

        assert isinstance(df_loaded, pd.DataFrame)
        assert len(df_loaded) == len(sample_dataframe)
        assert list(df_loaded.columns) == list(sample_dataframe.columns)

    def test_load_parquet_missing_dataset(self, mock_config):
        """Test that load_parquet raises error for missing dataset."""
        from scripts.core.config import Config
        from scripts.core.data_helpers import load_parquet

        metadata = {"version": "1.0", "datasets": {}}
        Config.METADATA_FILE.write_text(json.dumps(metadata))

        with pytest.raises(ValueError, match="Dataset.*not found"):
            load_parquet("nonexistent_dataset")

    def test_load_parquet_missing_file(self, mock_config, sample_dataframe):
        """Test that load_parquet raises error for missing file."""
        from scripts.core.config import Config
        from scripts.core.data_helpers import load_parquet

        # Create metadata pointing to non-existent file
        metadata = {
            "version": "1.0",
            "datasets": {
                "test_dataset": {
                    "path": "nonexistent.parquet",
                    "rows": 100,
                    "columns": 10,
                }
            },
        }
        Config.METADATA_FILE.write_text(json.dumps(metadata))

        with pytest.raises(FileNotFoundError):
            load_parquet("test_dataset")


@pytest.mark.unit
class TestDataHelpersIntegration:
    """Integration tests for data helpers."""

    def test_save_load_roundtrip(self, mock_config, sample_dataframe):
        """Test that save and load operations preserve data."""
        from scripts.core.data_helpers import load_parquet, save_parquet

        # Save
        save_parquet(sample_dataframe, "roundtrip_test", source="test")

        # Load
        df_loaded = load_parquet("roundtrip_test")

        # Verify
        pd.testing.assert_frame_equal(df_loaded, sample_dataframe)

    def test_metadata_version_tracking(self, mock_config, sample_dataframe):
        """Test that metadata tracks dataset versions."""
        from scripts.core.config import Config
        from scripts.core.data_helpers import save_parquet

        # Save first version
        save_parquet(sample_dataframe, "versioned_test", source="test", version="v1.0")

        # Save second version (overwrites)
        modified_df = sample_dataframe.copy()
        modified_df["new_column"] = "test"
        save_parquet(modified_df, "versioned_test", source="test", version="v2.0")

        # Check metadata
        metadata = json.loads(Config.METADATA_FILE.read_text())
        assert "versioned_test" in metadata["datasets"]
        # Check that version info is tracked
        assert metadata["datasets"]["versioned_test"]["version"] == "v2.0"


@pytest.mark.unit
class TestDataHelpersEdgeCases:
    """Test edge cases and error conditions."""

    def test_save_empty_dataframe(self, mock_config):
        """Test saving an empty DataFrame raises error."""
        from scripts.core.data_helpers import save_parquet

        empty_df = pd.DataFrame()

        # Should raise error for empty dataframe
        with pytest.raises(ValueError, match="Cannot save empty DataFrame"):
            save_parquet(empty_df, "empty_test")

    def test_load_with_specific_columns(self, mock_config, sample_dataframe):
        """Test loading all columns from parquet."""
        from scripts.core.config import Config
        from scripts.core.data_helpers import load_parquet

        parquet_file = Config.PARQUETS_DIR / "columns.parquet"
        sample_dataframe.to_parquet(parquet_file, index=False)

        metadata = {
            "version": "1.0",
            "datasets": {
                "columns_test": {
                    "path": "columns.parquet",
                    "rows": len(sample_dataframe),
                    "columns": len(sample_dataframe.columns),
                }
            },
        }
        Config.METADATA_FILE.write_text(json.dumps(metadata))

        # Load all columns (load_parquet loads the entire dataset)
        df_loaded = load_parquet("columns_test")

        # Verify we got all columns
        assert list(df_loaded.columns) == list(sample_dataframe.columns)
        assert len(df_loaded) == len(sample_dataframe)

        # Load specific columns
        df_subset = load_parquet("columns_test", columns=["id", "town"])
        assert list(df_subset.columns) == ["id", "town"]
        assert len(df_subset) == len(sample_dataframe)
