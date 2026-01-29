#!/usr/bin/env python3
"""
Add Planning Area Column to Housing Data Files

This script adds the planning_area column to L1 and L2 parquet files
using the crosswalk mappings created by create_planning_area_crosswalk.py.

Author: Automated Pipeline
Date: 2026-01-24
"""

import pandas as pd
from pathlib import Path


def load_crosswalk() -> tuple:
    """Load the crosswalk mappings."""
    crosswalk_dir = Path('data/auxiliary')
    
    hdb_crosswalk = pd.read_csv(crosswalk_dir / 'hdb_town_to_planning_area.csv')
    condo_crosswalk = pd.read_csv(crosswalk_dir / 'postal_district_to_planning_area.csv')
    
    return hdb_crosswalk, condo_crosswalk


def create_hdb_planning_area_map(crosswalk: pd.DataFrame) -> dict:
    """Create a town → planning area mapping dictionary."""
    mapping = {}
    for _, row in crosswalk[crosswalk['source_type'] == 'HDB_TOWN'].iterrows():
        mapping[row['source_value'].upper()] = row['planning_area']
    return mapping


def create_condo_planning_area_map(crosswalk: pd.DataFrame) -> dict:
    """Create a postal district → planning area mapping dictionary."""
    mapping = {}
    for _, row in crosswalk[crosswalk['source_type'] == 'POSTAL_DISTRICT'].iterrows():
        district = int(row['source_value'])
        mapping[district] = row['planning_area']
    return mapping


def update_hdb_transactions():
    """Add planning_area to HDB transaction data."""
    
    print("\nUpdating HDB transactions...")
    
    # Load data
    hdb_path = Path('data/parquets/L1/housing_hdb_transaction.parquet')
    if not hdb_path.exists():
        print(f"   ⚠️  File not found: {hdb_path}")
        return None
    
    df = pd.read_parquet(hdb_path)
    print(f"   Loaded {len(df):,} HDB transactions")
    
    # Load crosswalk
    hdb_crosswalk, _ = load_crosswalk()
    town_to_pa = create_hdb_planning_area_map(hdb_crosswalk)
    
    # Add planning_area column
    # Handle both 'town' and 'TOWN' column names
    town_col = 'town' if 'town' in df.columns else 'TOWN'
    df['town_upper'] = df[town_col].str.upper()
    df['planning_area'] = df['town_upper'].map(town_to_pa)
    
    # Drop helper column
    df.drop(columns=['town_upper'], inplace=True)
    
    # Check mapping coverage
    mapped = df['planning_area'].notna().sum()
    total = len(df)
    coverage = mapped / total * 100
    print(f"   Mapped {mapped:,} of {total:,} records ({coverage:.1f}%)")
    
    if df['planning_area'].isna().sum() > 0:
        unmapped = df[df['planning_area'].isna()][town_col].unique()
        print(f"   ⚠️  Unmapped towns: {unmapped.tolist()}")
    
    # Save
    output_path = Path('data/parquets/L1/housing_hdb_transaction.parquet')
    df.to_parquet(output_path, index=False)
    print(f"   Saved: {output_path}")
    
    return df


def update_condo_transactions():
    """Add planning_area to condo transaction data."""
    
    print("\nUpdating Condo transactions...")
    
    # Load data
    condo_path = Path('data/parquets/L1/housing_condo_transaction.parquet')
    if not condo_path.exists():
        print(f"   ⚠️  File not found: {condo_path}")
        return None
    
    df = pd.read_parquet(condo_path)
    print(f"   Loaded {len(df):,} Condo transactions")
    
    # Load crosswalk
    _, condo_crosswalk = load_crosswalk()
    district_to_pa = create_condo_planning_area_map(condo_crosswalk)
    
    # Add planning_area column
    # Try to find postal district column
    possible_cols = ['Postal District', 'postal_district', 'district', 'POSTAL_DISTRICT', 'DISTRICT']
    district_col = None
    for col in possible_cols:
        if col in df.columns:
            district_col = col
            break
    
    if district_col is None:
        # Try to extract from postal code
        if 'postal_code' in df.columns:
            df['extracted_district'] = df['postal_code'].astype(str).str[:2].astype(int)
            district_col = 'extracted_district'
        else:
            print(f"   ⚠️  No district column found")
            return None
    
    df['planning_area'] = df[district_col].map(district_to_pa)
    
    # Drop helper column if created
    if 'extracted_district' in df.columns:
        df.drop(columns=['extracted_district'], inplace=True)
    
    # Check mapping coverage
    mapped = df['planning_area'].notna().sum()
    total = len(df)
    coverage = mapped / total * 100
    print(f"   Mapped {mapped:,} of {total:,} records ({coverage:.1f}%)")
    
    if df['planning_area'].isna().sum() > 0:
        unmapped_districts = df[df['planning_area'].isna()][district_col].unique()
        print(f"   ⚠️  Unmapped districts: {unmapped_districts.tolist()}")
    
    # Save
    output_path = Path('data/parquets/L1/housing_condo_transaction.parquet')
    df.to_parquet(output_path, index=False)
    print(f"   Saved: {output_path}")
    
    return df


def update_l2_features():
    """Add planning_area to L2 feature data."""
    
    print("\nUpdating L2 feature data...")
    
    # Load data
    l2_path = Path('data/parquets/L2/housing_multi_amenity_features.parquet')
    if not l2_path.exists():
        print(f"   ⚠️  File not found: {l2_path}")
        return None
    
    df = pd.read_parquet(l2_path)
    print(f"   Loaded {len(df):,} L2 feature records")
    
    # Load crosswalk
    hdb_crosswalk, _ = load_crosswalk()
    town_to_pa = create_hdb_planning_area_map(hdb_crosswalk)
    
    # Check if town column exists
    if 'town' not in df.columns and 'TOWN' not in df.columns:
        print(f"   ⚠️  No town column found in L2 data")
        return None
    
    town_col = 'town' if 'town' in df.columns else 'TOWN'
    
    # Add planning_area column
    df['town_upper'] = df[town_col].str.upper()
    df['planning_area'] = df['town_upper'].map(town_to_pa)
    df.drop(columns=['town_upper'], inplace=True)
    
    # Check mapping coverage
    mapped = df['planning_area'].notna().sum()
    total = len(df)
    coverage = mapped / total * 100
    print(f"   Mapped {mapped:,} of {total:,} records ({coverage:.1f}%)")
    
    # Save
    output_path = Path('data/parquets/L2/housing_multi_amenity_features.parquet')
    df.to_parquet(output_path, index=False)
    print(f"   Saved: {output_path}")
    
    return df


def generate_summary():
    """Generate a summary of planning area coverage."""
    
    print("\n" + "=" * 60)
    print("Planning Area Coverage Summary")
    print("=" * 60)
    
    # Load updated files
    hdb_path = Path('data/parquets/L1/housing_hdb_transaction.parquet')
    condo_path = Path('data/parquets/L1/housing_condo_transaction.parquet')
    
    if hdb_path.exists():
        hdb = pd.read_parquet(hdb_path)
        hdb_pa = hdb.groupby('planning_area').agg({
            'resale_price': ['count', 'median']
        }).reset_index()
        hdb_pa.columns = ['planning_area', 'hdb_transactions', 'median_price']
        print(f"\nHDB Transactions by Planning Area:")
        print(hdb_pa.sort_values('hdb_transactions', ascending=False).head(10).to_string(index=False))
    
    if condo_path.exists():
        condo = pd.read_parquet(condo_path)
        condo_pa = condo.groupby('planning_area').size().reset_index(name='condo_transactions')
        print(f"\nCondo Transactions by Planning Area:")
        print(condo_pa.sort_values('condo_transactions', ascending=False).head(10).to_string(index=False))
    
    print("\n" + "=" * 60)


def main():
    """Main execution function."""
    
    print("=" * 60)
    print("Adding Planning Area Column to Housing Data Files")
    print("=" * 60)
    
    # Update each file
    hdb_df = update_hdb_transactions()
    condo_df = update_condo_transactions()
    l2_df = update_l2_features()
    
    # Generate summary
    generate_summary()
    
    print("\n" + "=" * 60)
    print("Planning area mapping complete!")
    print("=" * 60)
    
    return hdb_df, condo_df, l2_df


if __name__ == '__main__':
    main()
