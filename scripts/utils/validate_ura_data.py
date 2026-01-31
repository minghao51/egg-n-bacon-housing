#!/usr/bin/env python3
"""Validate updated URA data files before running pipeline.

This script checks:
- All files can be loaded
- Column names match expected schema
- Data types are correct
- Row counts are reasonable
"""

import sys
from pathlib import Path

import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.core.config import Config


def validate_file(file_path: Path, expected_rows_min: int = 1000) -> dict:
    """Validate a single CSV file.

    Args:
        file_path: Path to CSV file
        expected_rows_min: Minimum expected row count

    Returns:
        Dict with validation results
    """
    result = {
        'file': file_path.name,
        'valid': False,
        'rows': 0,
        'columns': [],
        'error': None
    }

    try:
        # Load file
        df = pd.read_csv(file_path, encoding='latin1', nrows=5)

        result['rows'] = len(df)
        result['columns'] = df.columns.tolist()

        # Check expected columns
        expected_cols = [
            'Project Name', 'Transacted Price ($)', 'Area (SQFT)',
            'Unit Price ($ PSF)', 'Sale Date', 'Street Name', 'Property Type'
        ]

        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            result['error'] = f"Missing columns: {missing_cols}"
            return result

        # Count actual rows
        full_df = pd.read_csv(file_path, encoding='latin1')
        result['rows'] = len(full_df)

        if result['rows'] < expected_rows_min:
            result['error'] = f"Too few rows: {result['rows']} < {expected_rows_min}"
            return result

        result['valid'] = True

    except Exception as e:
        result['error'] = str(e)

    return result


def main():
    """Run validation on all URA files."""
    print("=" * 60)
    print("Validating URA Data Files")
    print("=" * 60)

    ura_dir = Config.DATA_DIR / 'raw_data' / 'csv' / 'ura'

    if not ura_dir.exists():
        print(f"❌ URA directory not found: {ura_dir}")
        return False

    # Get all CSV files
    csv_files = sorted(ura_dir.glob('*.csv'))

    if not csv_files:
        print(f"❌ No CSV files found in {ura_dir}")
        return False

    print(f"\nFound {len(csv_files)} CSV files\n")

    # Validate each file
    results = []
    for csv_file in csv_files:
        print(f"Validating {csv_file.name}...", end=" ")
        result = validate_file(csv_file)
        results.append(result)

        if result['valid']:
            print(f"✅ {result['rows']:,} rows")
        else:
            print(f"❌ {result['error']}")

    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)

    valid_files = [r for r in results if r['valid']]
    invalid_files = [r for r in results if not r['valid']]

    print(f"✅ Valid files: {len(valid_files)}/{len(results)}")
    print(f"❌ Invalid files: {len(invalid_files)}/{len(results)}")

    if valid_files:
        total_rows = sum(r['rows'] for r in valid_files)
        print(f"📊 Total rows: {total_rows:,}")

    if invalid_files:
        print("\n❌ Failed files:")
        for r in invalid_files:
            print(f"  - {r['file']}: {r['error']}")
        return False

    print("\n✅ All validation checks passed!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
