"""Tests for data_helpers module."""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_helpers import list_datasets, load_parquet, save_parquet


def test_save_and_load():
    """Test basic save and load functionality."""
    # Create a simple test dataframe
    df = pd.DataFrame({
        "a": [1, 2, 3],
        "b": [4, 5, 6],
        "c": ["x", "y", "z"]
    })

    # Save the dataframe
    save_parquet(df, "test_dataset", source="test")

    # Load it back
    loaded = load_parquet("test_dataset")

    # Verify the data is the same
    assert loaded.equals(df), "Loaded dataframe should match saved dataframe"

    # Clean up
    datasets = list_datasets()
    if "test_dataset" in datasets:
        # Note: In real tests, you'd want to clean up the files
        pass


def test_metadata_tracking():
    """Test that save_parquet updates metadata."""
    df = pd.DataFrame({
        "col1": [1, 2],
        "col2": [3, 4]
    })

    save_parquet(df, "test_metadata", source="unit test")

    # Check that it's in the list
    datasets = list_datasets()
    assert "test_metadata" in datasets, "Dataset should be tracked in metadata"


def test_load_nonexistent_dataset():
    """Test that loading a nonexistent dataset raises an error."""
    with pytest.raises(ValueError):
        load_parquet("this_dataset_definitely_does_not_exist")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
