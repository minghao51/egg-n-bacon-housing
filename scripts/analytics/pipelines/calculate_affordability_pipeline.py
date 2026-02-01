#!/usr/bin/env python3
"""
Calculate Affordability Index by Planning Area

This script calculates the affordability index for Singapore housing
using estimated household income data.

Affordability Ratio = Median Property Price / Annual Household Income

Author: Automated Pipeline
Date: 2026-01-24
"""

import pandas as pd
import numpy as np
from pathlib import Path


def load_data() -> tuple:
    """Load required data files."""
    
    # Load HDB transactions with planning area
    hdb_path = Path('data/pipeline/L1/housing_hdb_transaction.parquet')
    hdb = pd.read_parquet(hdb_path)

    # Load income estimates
    income_path = Path('data/pipeline/L1/household_income_estimates.parquet')
    income = pd.read_parquet(income_path)

    # Load rental yields (optional, for yield-adjusted affordability)
    rental_path = Path('data/pipeline/L2/rental_yield.parquet')
    if rental_path.exists():
        rental = pd.read_parquet(rental_path)
    else:
        rental = None
    
    return hdb, income, rental


def calculate_affordability_ratio(price: float, annual_income: float) -> float:
    """Calculate affordability ratio (price / annual income)."""
    if annual_income <= 0:
        return np.nan
    return price / annual_income


def calculate_mortgage_payment(
    price: float,
    down_payment_pct: float = 0.20,
    interest_rate: float = 0.035,  # 3.5% rate
    loan_term_years: float = 25.0
) -> float:
    """
    Calculate estimated monthly mortgage payment.
    
    Uses standard Singapore mortgage terms:
    - 20% down payment (CPF or cash)
    - 80% loan-to-value
    - 25-year loan term (maximum for HDB)
    """
    
    loan_amount = price * (1 - down_payment_pct)
    monthly_rate = interest_rate / 12
    num_payments = loan_term_years * 12
    
    if monthly_rate > 0:
        monthly_payment = loan_amount * (
            (monthly_rate * (1 + monthly_rate) ** num_payments) /
            ((1 + monthly_rate) ** num_payments - 1)
        )
    else:
        monthly_payment = loan_amount / num_payments
    
    return monthly_payment


def calculate_affordability_metrics(
    hdb: pd.DataFrame,
    income: pd.DataFrame,
    rental: pd.DataFrame = None
) -> pd.DataFrame:
    """Calculate affordability metrics for each planning area."""
    
    print("Calculating affordability metrics...")
    print("=" * 60)
    
    # Create income lookup dictionary
    income_lookup = dict(zip(
        income['planning_area'],
        income['estimated_median_annual_income']
    ))
    
    # Calculate median price per town
    price_by_pa = hdb.groupby('town')['resale_price'].agg(['median', 'count']).reset_index()
    price_by_pa.columns = ['town', 'median_price', 'transaction_count']

    # Merge with income data
    affordability = price_by_pa.merge(
        income.rename(columns={'planning_area': 'town'})[['town', 'estimated_median_annual_income', 'estimated_median_monthly_income']],
        on='town',
        how='left'
    )
    
    # Calculate affordability ratio
    affordability['affordability_ratio'] = (
        affordability['median_price'] / affordability['estimated_median_annual_income']
    )
    
    # Calculate mortgage payment (20% down, 3.5% rate, 25 years)
    affordability['monthly_mortgage'] = affordability['median_price'].apply(
        lambda p: calculate_mortgage_payment(p)
    )
    
    # Calculate mortgage as % of income
    affordability['mortgage_to_income_pct'] = (
        affordability['monthly_mortgage'] * 12 / affordability['estimated_median_annual_income'] * 100
    )
    
    # Calculate months of income to buy (median price / monthly income)
    affordability['months_of_income'] = (
        affordability['median_price'] / affordability['estimated_median_monthly_income']
    )
    
    # Add affordability classification
    def classify_affordability(ratio):
        if ratio < 3.0:
            return 'Affordable'
        elif ratio < 5.0:
            return 'Moderate'
        elif ratio < 7.0:
            return 'Expensive'
        else:
            return 'Severely Unaffordable'
    
    affordability['affordability_class'] = affordability['affordability_ratio'].apply(classify_affordability)
    
    # Add average rental yield if available
    if rental is not None:
        # Map rental yields to planning areas
        rental_by_pa = rental.groupby('town')['rental_yield_pct'].mean().reset_index()
        rental_by_pa.columns = ['town', 'avg_rental_yield']

        affordability = affordability.merge(rental_by_pa, on='town', how='left')
        
        # Calculate gross rental yield
        affordability['gross_yield_pct'] = (
            (affordability['avg_rental_yield'] * 12 / affordability['median_price']) * 100
        )
    
    # Sort by affordability ratio (best first)
    affordability = affordability.sort_values('affordability_ratio')
    
    print(f"Calculated affordability for {len(affordability)} planning areas")
    
    return affordability


def generate_summary(affordability: pd.DataFrame) -> None:
    """Generate summary statistics and insights."""
    
    print("\n" + "=" * 60)
    print("Affordability Summary")
    print("=" * 60)
    
    # Overall statistics
    print(f"\nMedian Affordability Ratio: {affordability['affordability_ratio'].median():.2f}")
    print(f"Mean Affordability Ratio: {affordability['affordability_ratio'].mean():.2f}")
    print(f"Range: {affordability['affordability_ratio'].min():.2f} - {affordability['affordability_ratio'].max():.2f}")
    
    # Classification breakdown
    print("\nClassification Breakdown:")
    class_counts = affordability['affordability_class'].value_counts()
    for cls, count in class_counts.items():
        print(f"  {cls}: {count} planning areas")
    
    # Most affordable areas
    print("\n" + "-" * 40)
    print("Most Affordable Planning Areas:")
    most_affordable = affordability.head(5)[
        ['town', 'median_price', 'estimated_median_annual_income',
         'affordability_ratio', 'mortgage_to_income_pct']
    ]
    for _, row in most_affordable.iterrows():
        print(f"  {row['town']:20s}: Ratio {row['affordability_ratio']:.2f}, "
              f"Price ${row['median_price']:,.0f}, "
              f"Mortgage {row['mortgage_to_income_pct']:.1f}% of income")

    # Least affordable areas
    print("\n" + "-" * 40)
    print("Least Affordable Planning Areas:")
    least_affordable = affordability.tail(5)[
        ['town', 'median_price', 'estimated_median_annual_income',
         'affordability_ratio', 'mortgage_to_income_pct']
    ]
    for _, row in least_affordable.iterrows():
        print(f"  {row['town']:20s}: Ratio {row['affordability_ratio']:.2f}, "
              f"Price ${row['median_price']:,.0f}, "
              f"Mortgage {row['mortgage_to_income_pct']:.1f}% of income")


def create_affordability_by_month(affordability: pd.DataFrame, hdb: pd.DataFrame) -> pd.DataFrame:
    """Create monthly affordability time series."""
    
    print("\nCreating monthly affordability time series...")
    
    # Calculate monthly median prices
    hdb['month'] = pd.to_datetime(hdb['month'])
    monthly_prices = hdb.groupby(['town', 'month'])['resale_price'].median().reset_index()
    monthly_prices.columns = ['town', 'month', 'median_price']

    # Load income estimates
    income = pd.read_parquet('data/pipeline/L1/household_income_estimates.parquet')
    income_lookup = dict(zip(
        income['planning_area'],
        income['estimated_median_annual_income']
    ))

    # Add income data
    monthly_prices['estimated_annual_income'] = monthly_prices['town'].map(income_lookup)
    
    # Calculate monthly affordability ratio
    monthly_prices['affordability_ratio'] = (
        monthly_prices['median_price'] / monthly_prices['estimated_annual_income']
    )
    
    print(f"Generated {len(monthly_prices)} monthly affordability records")
    
    return monthly_prices


def main():
    """Main execution function."""
    
    output_dir = Path('data/pipeline/L3')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print("Loading data...")
    hdb, income, rental = load_data()
    print(f"  Loaded {len(hdb):,} HDB transactions")
    print(f"  Loaded {len(income)} income estimates")
    if rental is not None:
        print(f"  Loaded {len(rental)} rental yield records")
    
    # Calculate affordability metrics
    affordability = calculate_affordability_metrics(hdb, income, rental)
    
    # Generate summary
    generate_summary(affordability)
    
    # Create monthly time series
    monthly_affordability = create_affordability_by_month(affordability, hdb)
    
    # Save outputs
    print("\n" + "=" * 60)
    print("Saving outputs...")
    
    # Save affordability by planning area
    pa_output = output_dir / 'affordability_by_pa.parquet'
    affordability.to_parquet(pa_output, index=False)
    print(f"  Saved: {pa_output}")
    
    # Save monthly affordability
    monthly_output = output_dir / 'affordability_monthly.parquet'
    monthly_affordability.to_parquet(monthly_output, index=False)
    print(f"  Saved: {monthly_output}")
    
    print("\n" + "=" * 60)
    print("Affordability calculation complete!")
    print("=" * 60)
    
    return affordability, monthly_affordability


if __name__ == '__main__':
    main()
