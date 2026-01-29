#!/usr/bin/env python3
"""Verify PSF conversion worked correctly."""

import pandas as pd

# Load the newly created dataset
df = pd.read_parquet('data/parquets/L3/housing_unified.parquet')

print('=' * 80)
print('PSF CONVERSION VERIFICATION')
print('=' * 80)

print('\n1. Sample price data (first 5 records):')
print(df[['price', 'floor_area_sqft', 'floor_area_sqm', 'price_psf', 'price_psm']].head())

print('\n2. Conversion verification - price_psf calculation:')
print('   Expected: price_psf = price / floor_area_sqft')
all_match = True
for i in range(5):
    row = df.iloc[i]
    calculated_psf = row['price'] / row['floor_area_sqft']
    actual_psf = row['price_psf']
    match = abs(calculated_psf - actual_psf) < 0.01
    all_match = all_match and match
    status = '✓' if match else '✗'
    print(f'   Row {i}: ${actual_psf:.2f} (expected ${calculated_psf:.2f}) {status}')

print(f'\n   Overall: {'✓ ALL MATCH' if all_match else '✗ SOME MISMATCHES'}')

print('\n3. Conversion verification - price_psm calculation:')
print('   Expected: price_psm = price_psf * 10.764')
all_match_psm = True
for i in range(5):
    row = df.iloc[i]
    calculated_psm = row['price_psf'] * 10.764
    actual_psm = row['price_psm']
    match = abs(calculated_psm - actual_psm) < 0.01
    all_match_psm = all_match_psm and match
    status = '✓' if match else '✗'
    print(f'   Row {i}: ${actual_psm:.2f} (expected ${calculated_psm:.2f}) {status}')

print(f'\n   Overall: {'✓ ALL MATCH' if all_match_psm else '✗ SOME MISMATCHES'}')

print('\n4. PSF Tier Distribution:')
print(df['psf_tier_period'].value_counts())

print('\n5. Price PSF Statistics by Property Type:')
print(df.groupby('property_type')['price_psf'].describe()[['count', 'mean', 'min', 'max']])

print('\n6. Sample comparison - HDB vs Condo:')
hdb_sample = df[df['property_type'] == 'HDB'].iloc[0]
condo_sample = df[df['property_type'] == 'Condominium'].iloc[0]
print(f'\n   HDB Sample: ${hdb_sample["price_psf"]:.2f} psf (${hdb_sample["price_psm"]:.2f} psm)')
print(f'   Condo Sample: ${condo_sample["price_psf"]:.2f} psf (${condo_sample["price_psm"]:.2f} psm)')

print('\n' + '=' * 80)
print('VERIFICATION COMPLETE')
print('=' * 80)
