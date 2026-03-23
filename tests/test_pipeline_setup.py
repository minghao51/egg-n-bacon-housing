#!/usr/bin/env python
"""Tests to verify pipeline components are working."""

import pytest
import pandas as pd
import json
import sys
from pathlib import Path


class TestPipelineSetup:
    """Test suite for pipeline setup verification."""

    def test_config(self):
        """Test config module."""
        from core.config import Config

        # Test paths
        assert Config.BASE_DIR.exists()
        assert Config.DATA_DIR.exists()
        assert Config.SRC_DIR.exists()

    def test_data_helpers(self):
        """Test data_helpers module."""
        from core.data_helpers import list_datasets, load_parquet, save_parquet

        # Create test data
        df = pd.DataFrame(
            {"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"], "value": [10.5, 20.3, 30.1]}
        )

        # Save
        save_parquet(df, "pipeline_test", source="pipeline test")

        # List
        datasets = list_datasets()
        assert "pipeline_test" in datasets

        # Load
        loaded = load_parquet("pipeline_test")
        assert loaded.equals(df)

    def test_parquet_structure(self):
        """Test parquet file structure."""
        from core.config import Config

        # Check directories
        parquets_dir = Config.PARQUETS_DIR
        assert parquets_dir.exists()

        # Count files
        parquet_files = list(parquets_dir.rglob("*.parquet"))
        assert len(parquet_files) > 0

    def test_metadata(self):
        """Test metadata file."""
        from core.config import Config

        metadata_file = Config.METADATA_FILE
        assert metadata_file.exists()

        with open(metadata_file) as f:
            metadata = json.load(f)

        assert "datasets" in metadata
        assert "last_updated" in metadata

    def test_notebook_imports(self):
        """Test that notebooks can import required modules."""
        # Test common imports used in notebooks
        import pandas as pd
        import numpy as np
        import requests
        
        # Test src imports
        sys.path.insert(0, "notebooks")
        from core import data_helpers
