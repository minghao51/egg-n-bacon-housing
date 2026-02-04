"""Verify all imports work correctly from different contexts.

This script tests that all modules can be imported using absolute imports
from the project root directory.
"""

import sys
from pathlib import Path


def verify_from_project_root():
    """Test imports when running from project root."""
    print("Testing imports from project root...")

    try:
        import scripts.core.config
        print("  ✓ scripts.core.config")
    except ImportError as e:
        print(f"  ✗ scripts.core.config: {e}")
        return False

    try:
        import scripts.core.data_loader
        print("  ✓ scripts.core.data_loader")
    except ImportError as e:
        print(f"  ✗ scripts.core.data_loader: {e}")
        return False

    try:
        import scripts.core.geocoding
        print("  ✓ scripts.core.geocoding")
    except ImportError as e:
        print(f"  ✗ scripts.core.geocoding: {e}")
        return False

    try:
        import scripts.core.cache
        print("  ✓ scripts.core.cache")
    except ImportError as e:
        print(f"  ✗ scripts.core.cache: {e}")
        return False

    try:
        import scripts.core.data_helpers
        print("  ✓ scripts.core.data_helpers")
    except ImportError as e:
        print(f"  ✗ scripts.core.data_helpers: {e}")
        return False

    try:
        import scripts.core.stages.L0_collect
        print("  ✓ scripts.core.stages.L0_collect")
    except ImportError as e:
        print(f"  ✗ scripts.core.stages.L0_collect: {e}")
        return False

    try:
        import scripts.core.stages.L3_export
        print("  ✓ scripts.core.stages.L3_export")
    except ImportError as e:
        print(f"  ✗ scripts.core.stages.L3_export: {e}")
        return False

    print("✓ All imports from project root work!\n")
    return True


def verify_as_module():
    """Test imports when running as module."""
    print("Testing module imports...")

    try:
        from scripts.core.config import Config
        print("  ✓ from scripts.core.config import Config")
    except ImportError as e:
        print(f"  ✗ from scripts.core.config import Config: {e}")
        return False

    try:
        from scripts.core.data_loader import TransactionLoader, CSVLoader
        print("  ✓ from scripts.core.data_loader import TransactionLoader, CSVLoader")
    except ImportError as e:
        print(f"  ✗ from scripts.core.data_loader import TransactionLoader, CSVLoader: {e}")
        return False

    try:
        from scripts.core.geocoding import load_ura_files
        print("  ✓ from scripts.core.geocoding import load_ura_files")
    except ImportError as e:
        print(f"  ✗ from scripts.core.geocoding import load_ura_files: {e}")
        return False

    print("✓ All module imports work!\n")
    return True


def verify_config_paths():
    """Verify that Config path constants exist."""
    print("Testing Config path constants...")

    from scripts.core.config import Config

    required_attrs = [
        'L0_DIR', 'L1_DIR', 'L2_DIR', 'L3_DIR',
        'CSV_DIR', 'GEOJSON_DIR', 'CROSSWALK_DIR',
        'URA_DIR', 'HDB_RESALE_DIR',
        'DATASET_HDB_TRANSACTION', 'DATASET_CONDO_TRANSACTION', 'DATASET_EC_TRANSACTION'
    ]

    for attr in required_attrs:
        if hasattr(Config, attr):
            print(f"  ✓ Config.{attr}")
        else:
            print(f"  ✗ Config.{attr} is missing")
            return False

    print("✓ All Config path constants exist!\n")
    return True


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Import Verification Script")
    print("=" * 60)
    print()

    # Add project root to sys.path if not already there
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        print(f"Added {project_root} to sys.path")
        print()

    all_passed = True

    # Run checks
    all_passed &= verify_from_project_root()
    all_passed &= verify_as_module()
    all_passed &= verify_config_paths()

    # Summary
    print("=" * 60)
    if all_passed:
        print("✓ All verification checks passed!")
        print("=" * 60)
        return 0
    else:
        print("✗ Some verification checks failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit(main())
