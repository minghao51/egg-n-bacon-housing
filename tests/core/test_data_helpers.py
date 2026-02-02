"""
Tests for scripts.core.data_helpers module.

This test suite validates parquet file loading/saving operations
and metadata tracking.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from scripts.core.data_helpers import load_parquet, save_parquet, _load_metadata, _save_metadata


@pytest.mark.unit
class TestMetadataManagement:
    """Test metadata file management."""

    def test_load_metadata_returns_dict(self, temp_dir, monkeypatch):
        """Test that _load_metadata returns a dictionary."""
        # Create temporary metadata file
        metadata_file = temp_dir / "metadata.json"
        test_metadata = {
            "version": "1.0",
            "datasets": {
                "test_dataset": {
                    "path": "test.parquet",
                    "rows": 100,
                    "columns": 10
                }
            }
        }

        metadata_file.write_text(json.dumps(test_metadata, indent=2))

        # Mock Config.METADATA_FILE
        from scripts.core import config
        monkeypatch.setattr(config, "METADATA_FILE", metadata_file)

        metadata = _load_metadata()

        assert isinstance(metadata, dict)
        assert "datasets" in metadata
        assert metadata["datasets"]["test_dataset"]["rows"] == 100

    def test_load_metadata_creates_if_missing(self, temp_dir, monkeypatch):
        """Test that _load_metadata creates metadata file if missing."""
        metadata_file = temp_dir / "new_metadata.json"

        # Mock Config.METADATA_FILE
        from scripts.core import config
        monkeypatch.setattr(config, "METADATA_FILE", metadata_file)

        metadata = _load_metadata()

        assert isinstance(metadata, dict)
        assert "datasets" in metadata
        assert metadata_file.exists()

    def test_save_metadata_writes_file(self, temp_dir, monkeypatch):
        """Test that _save_metadata writes to file."""
        metadata_file = temp_dir / "metadata.json"

        # Mock Config.METADATA_FILE
        from scripts.core import config
        monkeypatch.setattr(config, "METADATA_FILE", metadata_file)

        test_metadata = {
            "version": "1.0",
            "datasets": {}
        }

        _save_metadata(test_metadata)

        assert metadata_file.exists()
        loaded_metadata = json.loads(metadata_file.read_text())
        assert loaded_metadata == test_metadata


@pytest.mark.unit
class TestSaveParquet:
    """Test save_parquet function."""

    def test_save_parquet_creates_file(self, temp_dir, monkeypatch, sample_dataframe):
        """Test that save_parquet creates a parquet file."""
        # Mock Config paths
        from scripts.core import config
        monkeypatch.setattr(config, "METADATA_FILE", temp_dir / "metadata.json")

        output_file = temp_dir / "test_output.parquet"

        save_parquet(sample_dataframe, "test_dataset", output_file)

        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_save_parquet_updates_metadata(self, temp_dir, monkeypatch, sample_dataframe):
        """Test that save_parquet updates metadata."""
        from scripts.core import config
        metadata_file = temp_dir / "metadata.json"
        monkeypatch.setattr(config, "METADATA_FILE", metadata_file)

        output_file = temp_dir / "test_output.parquet"

        save_parquet(sample_dataframe, "test_dataset", output_file)

        # Load metadata and check entry
        metadata = json.loads(metadata_file.read_text())
        assert "test_dataset" in metadata["datasets"]
        assert metadata["datasets"]["test_dataset"]["rows"] == len(sample_dataframe)

    def test_save_parquet_creates_directory(self, temp_dir, monkeypatch, sample_dataframe):
        """Test that save_parquet creates parent directories."""
        from scripts.core import config
        monkeypatch.setattr(config, "METADATA_FILE", temp_dir / "metadata.json")

        output_file = temp_dir / "subdir" / "nested" / "test.parquet"

        save_parquet(sample_dataframe, "test_dataset", output_file)

        assert output_file.exists()
        assert output_file.parent.exists()

    def test_save_parquet_compression(self, temp_dir, monkeypatch, sample_dataframe):
        """Test save_parquet with different compression options."""
        from scripts.core import config
        monkeypatch.setattr(config, "METADATA_FILE", temp_dir / "metadata.json")

        output_file = temp_dir / "test_compressed.parquet"

        save_parquet(sample_dataframe, "test_dataset", output_file, compression="gzip")

        assert output_file.exists()

        # Verify we can read it back
        df_loaded = pd.read_parquet(output_file)
        pd.testing.assert_frame_equal(df_loaded, sample_dataframe)


@pytest.mark.unit
class TestLoadParquet:
    """Test load_parquet function."""

    def test_load_parquet_returns_dataframe(self, temp_dir, monkeypatch, sample_dataframe):
        """Test that load_parquet returns a DataFrame."""
        from scripts.core import config

        # Create parquet file
        parquet_file = temp_dir / "test.parquet"
        sample_dataframe.to_parquet(parquet_file, index=False)

        # Create metadata
        metadata_file = temp_dir / "metadata.json"
        metadata = {
            "version": "1.0",
            "datasets": {
                "test_dataset": {
                    "path": str(parquet_file),
                    "rows": len(sample_dataframe),
                    "columns": len(sample_dataframe.columns)
                }
            }
        }
        metadata_file.write_text(json.dumps(metadata))
        monkeypatch.setattr(config, "METADATA_FILE", metadata_file)

        # Load and verify
        df_loaded = load_parquet("test_dataset")

        assert isinstance(df_loaded, pd.DataFrame)
        assert len(df_loaded) == len(sample_dataframe)
        assert list(df_loaded.columns) == list(sample_dataframe.columns)

    def test_load_parquet_missing_dataset(self, temp_dir, monkeypatch):
        """Test that load_parquet raises error for missing dataset."""
        from scripts.core import config

        metadata_file = temp_dir / "metadata.json"
        metadata = {
            "version": "1.0",
            "datasets": {}
        }
        metadata_file.write_text(json.dumps(metadata))
        monkeypatch.setattr(config, "METADATA_FILE", metadata_file)

        with pytest.raises(ValueError, match="Dataset not found"):
            load_parquet("nonexistent_dataset")

    def test_load_parquet_missing_file(self, temp_dir, monkeypatch):
        """Test that load_parquet raises error for missing file."""
        from scripts.core import config

        metadata_file = temp_dir / "metadata.json"
        metadata = {
            "version": "1.0",
            "datasets": {
                "test_dataset": {
                    "path": str(temp_dir / "nonexistent.parquet"),
                    "rows": 100,
                    "columns": 10
                }
            }
        }
        metadata_file.write_text(json.dumps(metadata))
        monkeypatch.setattr(config, "METADATA_FILE", metadata_file)

        with pytest.raises(FileNotFoundError):
            load_parquet("test_dataset")


@pytest.mark.unit
class TestDataHelpersIntegration:
    """Integration tests for data helpers."""

    def test_save_load_roundtrip(self, temp_dir, monkeypatch, sample_dataframe):
        """Test that save and load operations preserve data."""
        from scripts.core import config

        metadata_file = temp_dir / "metadata.json"
        monkeypatch.setattr(config, "METADATA_FILE", metadata_file)

        parquet_file = temp_dir / "roundtrip.parquet"

        # Save
        save_parquet(sample_dataframe, "roundtrip_test", parquet_file)

        # Load
        df_loaded = load_parquet("roundtrip_test")

        # Verify
        pd.testing.assert_frame_equal(df_loaded, sample_dataframe)

    def test_metadata_version_tracking(self, temp_dir, monkeypatch, sample_dataframe):
        """Test that metadata tracks dataset versions."""
        from scripts.core import config

        metadata_file = temp_dir / "metadata.json"
        monkeypatch.setattr(config, "METADATA_FILE", metadata_file)

        parquet_file = temp_dir / "versioned.parquet"

        # Save first version
        save_parquet(sample_dataframe, "versioned_test", parquet_file, version="v1.0")

        # Save second version
        modified_df = sample_dataframe.copy()
        modified_df["new_column"] = "test"
        save_parquet(modified_df, "versioned_test", parquet_file, version="v2.0")

        # Check metadata
        metadata = json.loads(metadata_file.read_text())
        assert "versioned_test" in metadata["datasets"]
        # Check that version info is tracked
        assert "version" in metadata["datasets"]["versioned_test"]


@pytest.mark.unit
class TestDataHelpersEdgeCases:
    """Test edge cases and error conditions."""

    def test_save_empty_dataframe(self, temp_dir, monkeypatch):
        """Test saving an empty DataFrame."""
        from scripts.core import config

        metadata_file = temp_dir / "metadata.json"
        monkeypatch.setattr(config, "METADATA_FILE", metadata_file)

        empty_df = pd.DataFrame()
        parquet_file = temp_dir / "empty.parquet"

        # Should handle empty dataframe
        save_parquet(empty_df, "empty_test", parquet_file)

        assert parquet_file.exists()

    def test_load_with_specific_columns(self, temp_dir, monkeypatch, sample_dataframe):
        """Test loading specific columns from parquet."""
        from scripts.core import config

        parquet_file = temp_dir / "columns.parquet"
        sample_dataframe.to_parquet(parquet_file, index=False)

        metadata_file = temp_dir / "metadata.json"
        metadata = {
            "version": "1.0",
            "datasets": {
                "columns_test": {
                    "path": str(parquet_file),
                    "rows": len(sample_dataframe),
                    "columns": len(sample_dataframe.columns)
                }
            }
        }
        metadata_file.write_text(json.dumps(metadata))
        monkeypatch.setattr(config, "METADATA_FILE", metadata_file)

        # Load specific columns
        df_subset = load_parquet("columns_test", columns=["id", "town"])

        assert list(df_subset.columns) == ["id", "town"]
        assert len(df_subset) == len(sample_dataframe)
