#!/usr/bin/env python3
"""
Estimate Household Income by Planning Area

This script estimates household income for Singapore planning areas using
HDB loan eligibility ratios as a proxy for median income distribution.

Methodology:
- Uses HDB loan eligibility bands as reference points
- Adjusts by planning area using proxy factors:
  - MRT proximity score
  - Flat type distribution
  - Historical transaction prices

Author: Automated Pipeline
Date: 2026-01-24
"""

from pathlib import Path

import pandas as pd

# HDB loan eligibility bands (2024-2025)
# These represent maximum monthly household incomes for various grant categories
ELIGIBILITY_BANDS = {
    'low': 7000,       # Maximum monthly income for enhanced grants
    'middle': 14000,   # Maximum for standard housing grants
    'upper': 21000     # Maximum for public housing
}

# Estimate median income as 60% of middle band
BASE_MEDIAN_INCOME = ELIGIBILITY_BANDS['middle'] * 0.6 * 12  # $100,800/year


def get_mrt_proximity_factor(planning_area: str) -> float:
    """
    Get MRT proximity factor for a planning area.
    Areas closer to MRT tend to have higher household incomes.
    
    Returns a factor between 0.8 and 1.2.
    """

    # High MRT accessibility areas (CBD, prime residential)
    high_access = [
        'DOWNTOWN CORE', 'MARINA SOUTH', 'RIVER VALLEY', 'ORCHARD',
        'BUKIT TIMAH', 'NOVENA', 'TANGLIN', 'OUTRAM', 'KALLANG'
    ]

    # Medium accessibility areas
    medium_access = [
        'ANG MO KIO', 'BEDOK', 'BISHAN', 'CLEMENTI', 'GEYLANG',
        'HOUGANG', 'JURONG EAST', 'MARINE PARADE', 'PASIR RIS',
        'QUEENSTOWN', 'SERANGOON', 'TAMPINES', 'TOA PAYOH', 'WOODLANDS'
    ]

    # Lower accessibility areas (suburban, rural)
    low_access = [
        'BUKIT BATOK', 'BUKIT PANJANG', 'CHOA CHU KANG', 'CHANGI',
        'LIM CHU KANG', 'PUNGGOL', 'SEMBAWANG', 'SENGKANG', 'YISHUN',
        'JURONG WEST', 'SUNGEI KADUT', 'WESTERN WATER CATCHMENT'
    ]

    if planning_area in high_access:
        return 1.15
    elif planning_area in medium_access:
        return 1.0
    elif planning_area in low_access:
        return 0.85
    else:
        return 1.0  # Default for unknown areas


def get_price_level_factor(planning_area: str, hdb_prices: dict) -> float:
    """
    Get price level factor based on historical transaction prices.
    Higher price areas tend to have higher income residents.
    
    Returns a factor between 0.8 and 1.3.
    """

    # Get median price for planning area
    median_price = hdb_prices.get(planning_area, 400000)  # Default $400K

    # Calculate price tier factor
    if median_price >= 600000:
        return 1.25  # Premium areas
    elif median_price >= 500000:
        return 1.10  # Above average
    elif median_price >= 400000:
        return 1.00  # Average
    elif median_price >= 300000:
        return 0.90  # Below average
    else:
        return 0.80  # Budget areas


def get_flat_type_factor(planning_area: str, flat_type_dist: dict) -> float:
    """
    Get flat type distribution factor.
    Areas with more larger flats (5-room, Executive) tend to have higher incomes.
    
    Returns a factor between 0.9 and 1.1.
    """

    # Percentage of larger flats (5-room + Executive)
    large_flat_pct = flat_type_dist.get('large_flat_pct', 0.30)

    if large_flat_pct >= 0.45:
        return 1.10  # Many large flats = higher income
    elif large_flat_pct >= 0.35:
        return 1.05
    elif large_flat_pct >= 0.25:
        return 1.00  # Average
    elif large_flat_pct >= 0.15:
        return 0.95
    else:
        return 0.90  # Mostly small flats


def calculate_estimated_income(
    planning_area: str,
    hdb_prices: dict,
    flat_type_dist: dict
) -> dict:
    """
    Calculate estimated household income for a planning area.
    
    Returns:
        dict with income estimates and factors
    """

    # Get adjustment factors
    mrt_factor = get_mrt_proximity_factor(planning_area)
    price_factor = get_price_level_factor(planning_area, hdb_prices)
    flat_type_factor = get_flat_type_factor(planning_area, flat_type_dist)

    # Calculate combined factor (weighted average)
    # Price level is most indicative (50%), MRT access (30%), flat type (20%)
    combined_factor = (
        0.50 * price_factor +
        0.30 * mrt_factor +
        0.20 * flat_type_factor
    )

    # Calculate estimated income
    estimated_annual_income = BASE_MEDIAN_INCOME * combined_factor
    estimated_monthly_income = estimated_annual_income / 12

    # Calculate income quintiles (approximate)
    quintile_20 = estimated_annual_income * 0.6
    quintile_40 = estimated_annual_income * 0.8
    quintile_60 = estimated_annual_income * 1.0
    quintile_80 = estimated_annual_income * 1.3

    return {
        'planning_area': planning_area,
        'estimated_median_annual_income': round(estimated_annual_income, -3),  # Round to nearest $1000
        'estimated_median_monthly_income': round(estimated_monthly_income, -2),
        'income_quintile_20': round(quintile_20, -3),
        'income_quintile_40': round(quintile_40, -3),
        'income_quintile_60': round(quintile_60, -3),
        'income_quintile_80': round(quintile_80, -3),
        'mrt_factor': round(mrt_factor, 3),
        'price_factor': round(price_factor, 3),
        'flat_type_factor': round(flat_type_factor, 3),
        'combined_factor': round(combined_factor, 3),
        'data_source': 'estimated_hdb_eligibility',
        'notes': 'Based on HDB loan eligibility ratios as proxy'
    }


def get_hdb_prices_by_planning_area() -> dict:
    """Get median HDB prices by planning area from existing data."""

    try:
        hdb = pd.read_parquet('data/pipeline/L1/housing_hdb_transaction.parquet')

        if 'planning_area' not in hdb.columns:
            print("⚠️  Planning area column not found. Using default prices.")
            return {}

        prices = hdb.groupby('planning_area')['resale_price'].median()
        return prices.to_dict()

    except Exception as e:
        print(f"⚠️  Error loading HDB prices: {e}")
        return {}


def get_flat_type_distribution() -> dict:
    """Get flat type distribution by planning area."""

    try:
        hdb = pd.read_parquet('data/pipeline/L1/housing_hdb_transaction.parquet')

        if 'planning_area' not in hdb.columns:
            return {}

        # Count flat types
        large_flats = ['5-ROOM', 'EXECUTIVE', 'MULTI-GENERATION']

        def calc_large_pct(group):
            total = len(group)
            large = group['flat_type'].isin(large_flats).sum()
            return large / total if total > 0 else 0

        dist = hdb.groupby('planning_area').apply(calc_large_pct)
        return dist.to_dict()

    except Exception as e:
        print(f"⚠️  Error loading flat type distribution: {e}")
        return {}


def generate_all_estimates() -> pd.DataFrame:
    """Generate income estimates for all planning areas."""

    print("Calculating household income estimates...")
    print("=" * 60)

    # Load data
    hdb_prices = get_hdb_prices_by_planning_area()
    flat_type_dist = get_flat_type_distribution()

    # Get list of planning areas from crosswalk
    crosswalk = pd.read_csv('data/manual/crosswalks/hdb_town_to_planning_area.csv')
    planning_areas = crosswalk['planning_area'].unique().tolist()

    # Calculate estimates for each planning area
    results = []
    for pa in planning_areas:
        flat_dist = {
            'large_flat_pct': flat_type_dist.get(pa, 0.30)
        }

        estimate = calculate_estimated_income(pa, hdb_prices, flat_dist)
        results.append(estimate)

        print(f"  {pa:20s}: ${estimate['estimated_median_annual_income']:,.0f}/year "
              f"(factor: {estimate['combined_factor']:.3f})")

    df = pd.DataFrame(results)

    # Sort by income
    df = df.sort_values('estimated_median_annual_income', ascending=False)

    print("\n" + "=" * 60)
    print(f"Generated estimates for {len(df)} planning areas")

    return df


def main():
    """Main execution function."""

    output_dir = Path('data/pipeline/L1')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate estimates
    df = generate_all_estimates()

    # Save to parquet
    output_path = output_dir / 'household_income_estimates.parquet'
    df.to_parquet(output_path, index=False)

    print(f"\nSaved to: {output_path}")
    print(f"Total records: {len(df)}")

    # Summary statistics
    print("\n" + "=" * 60)
    print("Income Estimate Summary")
    print("=" * 60)
    print(f"Median across planning areas: ${df['estimated_median_annual_income'].median():,.0f}/year")
    print(f"Range: ${df['estimated_median_annual_income'].min():,.0f} - ${df['estimated_median_annual_income'].max():,.0f}")

    print("\nTop 5 highest income areas:")
    print(df.head()[['planning_area', 'estimated_median_annual_income']].to_string(index=False))

    print("\nTop 5 lowest income areas:")
    print(df.tail()[['planning_area', 'estimated_median_annual_income']].to_string(index=False))

    return df


if __name__ == '__main__':
    main()
