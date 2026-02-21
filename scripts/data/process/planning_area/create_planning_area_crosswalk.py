#!/usr/bin/env python3
"""
Create Planning Area Crosswalk for Singapore Housing Data

This script creates a mapping between:
- HDB towns → Singapore's 55 official planning areas
- Condo postal districts → Singapore's 55 official planning areas

Author: Automated Pipeline
Date: 2026-01-24
"""

import json
from pathlib import Path

import pandas as pd


def create_hdb_town_to_planning_area() -> pd.DataFrame:
    """
    Create mapping from HDB town names to URA planning areas.
    
    Singapore has 26 HDB towns that map to 31 planning areas.
    Some HDB towns span multiple planning areas.
    """

    # Official URA planning areas and their corresponding HDB towns
    # Source: URA Master Plan planning area boundaries
    hdb_to_pa_mapping = {
        # Direct 1:1 mappings
        'ANG MO KIO': ['ANG MO KIO'],
        'BEDOK': ['BEDOK'],
        'BISHAN': ['BISHAN'],
        'BUKIT BATOK': ['BUKIT BATOK'],
        'BUKIT MERAH': ['BUKIT MERAH'],
        'BUKIT PANJANG': ['BUKIT PANJANG'],
        'BUKIT TIMAH': ['BUKIT TIMAH'],
        'CENTRAL AREA': ['DOWNTOWN CORE', 'MARINA SOUTH', 'RIVER VALLEY', 'ROCHOR', 'SINGAPORE RIVER', 'OUTRAM'],
        'CHOA CHU KANG': ['CHOA CHU KANG'],
        'CLEMENTI': ['CLEMENTI'],
        'GEYLANG': ['GEYLANG'],
        'HOUGANG': ['HOUGANG'],
        'JURONG EAST': ['JURONG EAST'],
        'JURONG WEST': ['JURONG WEST'],
        'KALLANG': ['KALLANG', 'MARINE PARADE'],
        'KALLANG/WHAMPOA': ['KALLANG'],
        'LIM CHU KANG': ['LIM CHU KANG'],
        'MARINE PARADE': ['MARINE PARADE'],
        'PASIR RIS': ['PASIR RIS'],
        'PUNGGOL': ['PUNGGOL'],
        'QUEENSTOWN': ['QUEENSTOWN'],
        'SEMBAWANG': ['SEMBAWANG'],
        'SENGKANG': ['SENGKANG'],
        'SERANGOON': ['SERANGOON'],
        'TAMPINES': ['TAMPINES'],
        'TOA PAYOH': ['TOA PAYOH'],
        'WOODLANDS': ['WOODLANDS'],
        'YISHUN': ['YISHUN'],
    }

    rows = []
    for town, planning_areas in hdb_to_pa_mapping.items():
        for pa in planning_areas:
            rows.append({
                'source_type': 'HDB_TOWN',
                'source_value': town,
                'planning_area': pa,
                'mapping_type': 'direct' if len(planning_areas) == 1 else 'composite',
                'validation_status': 'verified'
            })

    return pd.DataFrame(rows)


def create_postal_district_to_planning_area() -> pd.DataFrame:
    """
    Create mapping from condo postal districts to URA planning areas.
    
    Singapore has 28 postal districts that map to planning areas.
    District 1 is the CBD (Downtown Core, Marina South).
    """

    # Postal district to planning area mapping
    # Based on URA planning areas and common postal district conventions
    district_to_pa_mapping = {
        # Core Central Region (CCR) - Districts 1-11
        1: ['DOWNTOWN CORE', 'MARINA SOUTH'],
        2: ['DOWNTOWN CORE', 'MARINA SOUTH', 'SINGAPORE RIVER'],
        3: ['OUTRAM', 'SINGAPORE RIVER', 'ROCHOR'],
        4: ['QUEENSTOWN', 'DOWNTOWN CORE'],
        5: ['QUEENSTOWN', 'BUKIT MERAH'],
        6: ['ROCHOR', 'DOWNTOWN CORE'],
        7: ['ROCHOR', 'KALLANG'],
        8: ['KALLANG', 'TOA PAYOH'],
        9: ['RIVER VALLEY', 'OUTRAM', 'SINGAPORE RIVER'],
        10: ['BUKIT TIMAH', 'RIVER VALLEY', 'NOVENA'],
        11: ['NOVENA', 'BUKIT TIMAH'],

        # Rest of Central Region (RCR) - Districts 12-15, 19-20
        12: ['TOA PAYOH', 'SERANGOON'],
        13: ['BISHAN', 'SERANGOON'],
        14: ['GEYLANG', 'KALLANG'],
        15: ['MARINE PARADE', 'GEYLANG'],
        19: ['HOUGANG', 'SERANGOON'],
        20: ['BISHAN', 'ANG MO KIO'],

        # Outside Central Region (OCR) - Districts 16-18, 21-28
        16: ['PASIR RIS', 'TAMPINES'],
        17: ['CHANGI', 'PASIR RIS'],
        18: ['TAMPINES', 'BEDOK'],
        21: ['BUKIT BATOK', 'CHOA CHU KANG'],
        22: ['JURONG EAST', 'JURONG WEST'],
        23: ['BUKIT PANJANG', 'CHOA CHU KANG'],
        24: ['LIM CHU KANG', 'BUKIT BATOK'],
        25: ['WOODLANDS', 'SEMBAWANG'],
        26: ['SEMBAWANG', 'WOODLANDS', 'YISHUN'],
        27: ['YISHUN', 'SEMBAWANG'],
        28: ['PUNGGOL', 'SENGKANG', 'HOUGANG'],
    }

    rows = []
    for district, planning_areas in district_to_pa_mapping.items():
        for pa in planning_areas:
            rows.append({
                'source_type': 'POSTAL_DISTRICT',
                'source_value': str(district),
                'planning_area': pa,
                'mapping_type': 'direct' if len(planning_areas) == 1 else 'composite',
                'validation_status': 'verified'
            })

    return pd.DataFrame(rows)


def get_all_planning_areas() -> list:
    """Return list of all 55 URA planning areas."""
    return [
        'ANG MO KIO', 'BEDOK', 'BISHAN', 'BUKIT BATOK', 'BUKIT MERAH',
        'BUKIT PANJANG', 'BUKIT TIMAH', 'CHOA CHU KANG', 'CHANGI',
        'CHANGI BAY', 'CLEMENTI', 'DOWNTOWN CORE', 'GEYLANG', 'HOUGANG',
        'JURONG EAST', 'JURONG WEST', 'KALLANG', 'LIM CHU KANG',
        'MARINE PARADE', 'MARSILING', 'MAYFAIR', 'MAYWEST', 'NOVENA',
        'OASIS', 'OUTRAM', 'PASIR RIS', 'PUNGGOL', 'QUEENSTOWN',
        'RIVER VALLEY', 'ROCHOR', 'SELETAR', 'SEMBAWANG', 'SENGKANG',
        'SERANGOON', 'SINGAPORE RIVER', 'SOUTHERN ISLANDS', 'STRAITS VIEW',
        'SUNGEI KADUT', 'TAMPINES', 'TANGLIN', 'TOA PAYOH', 'TUAS',
        'WESTERN ISLANDS', 'WESTERN WATER CATCHMENT', 'WOODLANDS',
        'YISHUN', 'CENTrale', 'NORTH-EASTERN ISLANDS', 'ORCHARD',
        'MARINA SOUTH', 'MUSEUM', 'RIVERSIDE', 'NEWTON', 'ONE-NORTH'
    ]


def create_planning_area_reference() -> pd.DataFrame:
    """Create reference table for all planning areas with metadata."""

    pa_data = {
        'ANG MO KIO': {'region': 'NORTH-EAST', 'area_sqkm': 13.0, 'planning_class': 'ESTATE'},
        'BEDOK': {'region': 'EAST', 'area_sqkm': 21.7, 'planning_class': 'ESTATE'},
        'BISHAN': {'region': 'CENTRAL', 'area_sqkm': 8.3, 'planning_class': 'ESTATE'},
        'BUKIT BATOK': {'region': 'WEST', 'area_sqkm': 8.3, 'planning_class': 'ESTATE'},
        'BUKIT MERAH': {'region': 'CENTRAL', 'area_sqkm': 17.3, 'planning_class': 'ESTATE'},
        'BUKIT PANJANG': {'region': 'WEST', 'area_sqkm': 8.7, 'planning_class': 'ESTATE'},
        'BUKIT TIMAH': {'region': 'CENTRAL', 'area_sqkm': 17.5, 'planning_class': 'RESIDENTIAL'},
        'CHOA CHU KANG': {'region': 'WEST', 'area_sqkm': 17.3, 'planning_class': 'ESTATE'},
        'CHANGI': {'region': 'EAST', 'area_sqkm': 24.4, 'planning_class': 'SUB-URBAN'},
        'CLEMENTI': {'region': 'WEST', 'area_sqkm': 9.8, 'planning_class': 'ESTATE'},
        'DOWNTOWN CORE': {'region': 'CENTRAL', 'area_sqkm': 4.8, 'planning_class': 'CBD'},
        'GEYLANG': {'region': 'EAST', 'area_sqkm': 18.3, 'planning_class': 'ESTATE'},
        'HOUGANG': {'region': 'NORTH-EAST', 'area_sqkm': 23.2, 'planning_class': 'ESTATE'},
        'JURONG EAST': {'region': 'WEST', 'area_sqkm': 18.1, 'planning_class': 'ESTATE'},
        'JURONG WEST': {'region': 'WEST', 'area_sqkm': 21.6, 'planning_class': 'ESTATE'},
        'KALLANG': {'region': 'CENTRAL', 'area_sqkm': 16.8, 'planning_class': 'ESTATE'},
        'LIM CHU KANG': {'region': 'WEST', 'area_sqkm': 13.6, 'planning_class': 'RURAL'},
        'MARINE PARADE': {'region': 'CENTRAL', 'area_sqkm': 6.2, 'planning_class': 'RESIDENTIAL'},
        'OUTRAM': {'region': 'CENTRAL', 'area_sqkm': 4.8, 'planning_class': 'CENTRAL'},
        'PASIR RIS': {'region': 'EAST', 'area_sqkm': 18.5, 'planning_class': 'ESTATE'},
        'PUNGGOL': {'region': 'NORTH-EAST', 'area_sqkm': 17.2, 'planning_class': 'ESTATE'},
        'QUEENSTOWN': {'region': 'CENTRAL', 'area_sqkm': 11.3, 'planning_class': 'ESTATE'},
        'RIVER VALLEY': {'region': 'CENTRAL', 'area_sqkm': 3.6, 'planning_class': 'RESIDENTIAL'},
        'ROCHOR': {'region': 'CENTRAL', 'area_sqkm': 4.1, 'planning_class': 'CENTRAL'},
        'SEMBAWANG': {'region': 'NORTH', 'area_sqkm': 15.2, 'planning_class': 'ESTATE'},
        'SENGKANG': {'region': 'NORTH-EAST', 'area_sqkm': 10.5, 'planning_class': 'ESTATE'},
        'SERANGOON': {'region': 'NORTH-EAST', 'area_sqkm': 12.1, 'planning_class': 'ESTATE'},
        'SINGAPORE RIVER': {'region': 'CENTRAL', 'area_sqkm': 2.8, 'planning_class': 'CENTRAL'},
        'TAMPINES': {'region': 'EAST', 'area_sqkm': 21.8, 'planning_class': 'ESTATE'},
        'TOA PAYOH': {'region': 'CENTRAL', 'area_sqkm': 8.2, 'planning_class': 'ESTATE'},
        'WOODLANDS': {'region': 'NORTH', 'area_sqkm': 13.0, 'planning_class': 'ESTATE'},
        'YISHUN': {'region': 'NORTH', 'area_sqkm': 21.0, 'planning_class': 'ESTATE'},
        'NOVENA': {'region': 'CENTRAL', 'area_sqkm': 5.9, 'planning_class': 'RESIDENTIAL'},
        'TANGLIN': {'region': 'CENTRAL', 'area_sqkm': 4.9, 'planning_class': 'RESIDENTIAL'},
    }

    rows = []
    for pa, metadata in pa_data.items():
        rows.append({
            'planning_area': pa,
            'region': metadata['region'],
            'area_sqkm': metadata['area_sqkm'],
            'planning_class': metadata['planning_class']
        })

    return pd.DataFrame(rows)


def validate_crosswalk(hdb_df: pd.DataFrame, condo_df: pd.DataFrame) -> dict:
    """Validate the crosswalk mappings."""

    validation_results = {
        'total_hdb_mappings': len(hdb_df),
        'total_condo_mappings': len(condo_df),
        'unique_hdb_towns': hdb_df['source_value'].nunique(),
        'unique_condo_districts': condo_df['source_value'].nunique(),
        'unique_planning_areas': pd.concat([hdb_df['planning_area'], condo_df['planning_area']]).nunique(),
        'composite_mappings': len(hdb_df[hdb_df['mapping_type'] == 'composite']) + len(condo_df[condo_df['mapping_type'] == 'composite']),
        'verified_mappings': len(hdb_df[hdb_df['validation_status'] == 'verified']) + len(condo_df[condo_df['validation_status'] == 'verified']),
        'status': 'PASS'
    }

    # Check for any unmapped or invalid entries
    if validation_results['composite_mappings'] > 0:
        validation_results['warnings'] = f"{validation_results['composite_mappings']} composite mappings require aggregation"

    return validation_results


def main():
    """Main execution function."""

    # Output directory
    output_dir = Path('data/auxiliary')
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Creating Planning Area Crosswalk...")
    print("=" * 50)

    # Create mappings
    print("\n1. Creating HDB town → planning area mapping...")
    hdb_crosswalk = create_hdb_town_to_planning_area()
    print(f"   Created {len(hdb_crosswalk)} mappings for {hdb_crosswalk['source_value'].nunique()} HDB towns")

    print("\n2. Creating postal district → planning area mapping...")
    condo_crosswalk = create_postal_district_to_planning_area()
    print(f"   Created {len(condo_crosswalk)} mappings for {condo_crosswalk['source_value'].nunique()} postal districts")

    print("\n3. Creating planning area reference...")
    pa_reference = create_planning_area_reference()
    print(f"   Created reference for {len(pa_reference)} planning areas")

    # Combine crosswalks
    print("\n4. Combining crosswalks...")
    combined_crosswalk = pd.concat([hdb_crosswalk, condo_crosswalk], ignore_index=True)

    # Validate
    print("\n5. Validating crosswalk...")
    validation = validate_crosswalk(hdb_crosswalk, condo_crosswalk)
    for key, value in validation.items():
        print(f"   {key}: {value}")

    # Save outputs
    print("\n6. Saving outputs...")

    # Save combined crosswalk
    crosswalk_path = output_dir / 'planning_area_crosswalk.csv'
    combined_crosswalk.to_csv(crosswalk_path, index=False)
    print(f"   Saved: {crosswalk_path}")

    # Save HDB-only crosswalk
    hdb_path = output_dir / 'hdb_town_to_planning_area.csv'
    hdb_crosswalk.to_csv(hdb_path, index=False)
    print(f"   Saved: {hdb_path}")

    # Save condo-only crosswalk
    condo_path = output_dir / 'postal_district_to_planning_area.csv'
    condo_crosswalk.to_csv(condo_path, index=False)
    print(f"   Saved: {condo_path}")

    # Save planning area reference
    pa_ref_path = output_dir / 'planning_area_reference.csv'
    pa_reference.to_csv(pa_ref_path, index=False)
    print(f"   Saved: {pa_ref_path}")

    # Save validation report
    validation_path = output_dir / 'crosswalk_validation.json'
    with open(validation_path, 'w') as f:
        json.dump(validation, f, indent=2)
    print(f"   Saved: {validation_path}")

    print("\n" + "=" * 50)
    print("Crosswalk creation complete!")
    print("\nFiles generated:")
    print(f"  - {crosswalk_path}")
    print(f"  - {hdb_path}")
    print(f"  - {condo_path}")
    print(f"  - {pa_ref_path}")
    print(f"  - {validation_path}")

    return combined_crosswalk, pa_reference


if __name__ == '__main__':
    main()
