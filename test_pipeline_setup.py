#!/usr/bin/env python
"""Test script to verify pipeline components are working."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_config():
    """Test config module."""
    print("Testing config module...")
    try:
        from src.config import Config

        # Test paths
        assert Config.BASE_DIR.exists()
        assert Config.DATA_DIR.exists()
        assert Config.SRC_DIR.exists()

        print(f"✅ BASE_DIR: {Config.BASE_DIR}")
        print(f"✅ DATA_DIR: {Config.DATA_DIR}")
        print(f"✅ PARQUETS_DIR: {Config.PARQUETS_DIR}")
        print(f"✅ Config module working!\n")
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}\n")
        return False


def test_data_helpers():
    """Test data_helpers module."""
    print("Testing data_helpers module...")
    try:
        from src.data_helpers import save_parquet, load_parquet, list_datasets
        import pandas as pd

        # Create test data
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "value": [10.5, 20.3, 30.1]
        })

        # Save
        save_parquet(df, "pipeline_test", source="pipeline test")

        # List
        datasets = list_datasets()
        assert "pipeline_test" in datasets
        print(f"✅ Datasets available: {list(datasets.keys())}")

        # Load
        loaded = load_parquet("pipeline_test")
        assert loaded.equals(df)
        print(f"✅ Loaded {len(loaded)} rows successfully")

        print(f"✅ Data helpers working!\n")
        return True
    except Exception as e:
        print(f"❌ Data helpers test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_parquet_structure():
    """Test parquet file structure."""
    print("Testing parquet directory structure...")
    try:
        from src.config import Config

        # Check directories
        parquets_dir = Config.PARQUETS_DIR
        assert parquets_dir.exists()

        # Count files
        parquet_files = list(parquets_dir.rglob("*.parquet"))
        print(f"✅ Found {len(parquet_files)} parquet files")

        for pf in parquet_files[:5]:  # Show first 5
            print(f"  - {pf.relative_to(Config.DATA_DIR)}")

        print(f"✅ Parquet structure correct!\n")
        return True
    except Exception as e:
        print(f"❌ Parquet structure test failed: {e}\n")
        return False


def test_metadata():
    """Test metadata file."""
    print("Testing metadata.json...")
    try:
        import json
        from src.config import Config

        metadata_file = Config.METADATA_FILE
        assert metadata_file.exists()

        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        assert "datasets" in metadata
        assert "last_updated" in metadata

        print(f"✅ Metadata file exists")
        print(f"✅ Last updated: {metadata['last_updated']}")
        print(f"✅ Datasets tracked: {len(metadata['datasets'])}")

        for name, info in list(metadata['datasets'].items())[:3]:
            print(f"  - {name}: {info['rows']} rows")

        print(f"✅ Metadata working!\n")
        return True
    except Exception as e:
        print(f"❌ Metadata test failed: {e}\n")
        return False


def test_notebook_imports():
    """Test that notebooks can import required modules."""
    print("Testing notebook imports...")
    try:
        # Test common imports used in notebooks
        import pandas as pd
        import numpy as np
        import requests

        # Test src imports
        sys.path.insert(0, 'notebooks')
        from src.data_helpers import save_parquet, load_parquet

        print("✅ pandas: OK")
        print("✅ numpy: OK")
        print("✅ requests: OK")
        print("✅ src.data_helpers: OK")
        print(f"✅ Notebook imports working!\n")
        return True
    except Exception as e:
        print(f"❌ Notebook imports test failed: {e}\n")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("PIPELINE SETUP TEST")
    print("=" * 60)
    print()

    results = {
        "Config": test_config(),
        "Data Helpers": test_data_helpers(),
        "Parquet Structure": test_parquet_structure(),
        "Metadata": test_metadata(),
        "Notebook Imports": test_notebook_imports(),
    }

    print("=" * 60)
    print("TEST RESULTS")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Pipeline is ready to run.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
