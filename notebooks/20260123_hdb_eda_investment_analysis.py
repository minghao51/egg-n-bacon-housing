# %%
"""
HDB Housing Investment Analysis - Exploratory Data Analysis
================================================================

This notebook analyzes HDB housing data in Singapore to provide investment recommendations
based on planning area performance, appreciation potential, and rental yield.

Focus areas:
1. Planning area price trends and appreciation
2. Rental yield analysis by area
3. Investment scoring and recommendations
4. Risk-adjusted returns analysis

Author: Auto-generated analysis
Date: 2026-01-23
"""

# %%
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

warnings.filterwarnings('ignore')

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# %%
# Load data
DATA_PATH = Path('data/parquets/L3/housing_unified.parquet')
df = pd.read_parquet(DATA_PATH)

# Filter HDB only
hdb = df[df['property_type'] == 'HDB'].copy()
print(f"Total HDB transactions: {len(hdb):,}")
print(f"Date range: {hdb['transaction_date'].min().strftime('%Y-%m')} to {hdb['transaction_date'].max().strftime('%Y-%m')}")
print(f"Number of planning areas: {hdb['planning_area'].nunique()}")

# %%
# 1. DATA QUALITY OVERVIEW
print("=" * 80)
print("DATA QUALITY OVERVIEW")
print("=" * 80)

# Check key metrics availability
metrics_summary = pd.DataFrame({
    'Total Records': len(hdb),
    'Non-Null': hdb[['price_psm', 'rental_yield_pct', 'yoy_change_pct',
                     'mom_change_pct', 'dist_to_nearest_mrt']].notna().sum(),
    'Percentage': hdb[['price_psm', 'rental_yield_pct', 'yoy_change_pct',
                       'mom_change_pct', 'dist_to_nearest_mrt']].notna().sum() / len(hdb) * 100
}).T

print("\nKey Metrics Availability:")
print(metrics_summary.round(1))

# %%
# 2. PLANNING AREA OVERVIEW
print("\n" + "=" * 80)
print("PLANNING AREA OVERVIEW")
print("=" * 80)

area_stats = hdb.groupby('planning_area').agg({
    'price': ['count', 'mean', 'median', 'std'],
    'price_psm': ['mean', 'median'],
    'floor_area_sqm': 'mean'
}).round(2)

area_stats.columns = ['_'.join(col).strip() for col in area_stats.columns.values]
area_stats = area_stats.sort_values('price_count', ascending=False)

print("\nTop 15 Planning Areas by Transaction Volume:")
print(area_stats.head(15)[['price_count', 'price_mean', 'price_median', 'price_psm_mean']])

# %%
# 3. PRICE APPRECIATION ANALYSIS BY PLANNING AREA
print("\n" + "=" * 80)
print("PRICE APPRECIATION ANALYSIS (2015-2025)")
print("=" * 80)

# Filter to recent data with price trends
recent_data = hdb[hdb['year'] >= 2015].copy()

# Calculate appreciation by planning area
appreciation_by_area = recent_data.groupby(['planning_area', 'year'])['price_psm'].mean().unstack()

# Calculate CAGR for each area
cagr_by_area = {}
for area in appreciation_by_area.index:
    prices = appreciation_by_area.loc[area].dropna()
    if len(prices) >= 2:
        start_price = prices.iloc[0]
        end_price = prices.iloc[-1]
        years = len(prices) - 1
        if start_price > 0 and years > 0:
            cagr = ((end_price / start_price) ** (1/years) - 1) * 100
            cagr_by_area[area] = {
                'start_year': prices.index[0],
                'end_year': prices.index[-1],
                'start_psm': start_price,
                'end_psm': end_price,
                'cagr_pct': cagr,
                'total_appreciation_pct': ((end_price / start_price) - 1) * 100
            }

appreciation_df = pd.DataFrame(cagr_by_area).T
appreciation_df = appreciation_df.sort_values('cagr_pct', ascending=False)

print("\nTop 10 Planning Areas by Price Appreciation (CAGR):")
print(appreciation_df.head(10).round(2))

# %%
# 4. RENTAL YIELD ANALYSIS
print("\n" + "=" * 80)
print("RENTAL YIELD ANALYSIS BY PLANNING AREA")
print("=" * 80)

# Filter records with rental yield data
rental_data = hdb[hdb['rental_yield_pct'].notna()].copy()
print(f"\nRecords with rental yield data: {len(rental_data):,}")

rental_yield_by_area = rental_data.groupby('planning_area')['rental_yield_pct'].agg([
    ('count', 'count'),
    ('mean_yield', 'mean'),
    ('median_yield', 'median'),
    ('std_yield', 'std'),
    ('min_yield', 'min'),
    ('max_yield', 'max')
]).round(2)

rental_yield_by_area = rental_yield_by_area[rental_yield_by_area['count'] >= 50]  # Minimum sample size
rental_yield_by_area = rental_yield_by_area.sort_values('mean_yield', ascending=False)

print("\nTop 15 Planning Areas by Average Rental Yield:")
print(rental_yield_by_area.head(15))

# %%
# 5. COMBINED INVESTMENT SCORE
print("\n" + "=" * 80)
print("INVESTMENT ATTRACTIVENESS SCORE")
print("=" * 80)

# Merge appreciation and rental yield data
combined_scores = pd.merge(
    appreciation_df[['cagr_pct', 'total_appreciation_pct']],
    rental_yield_by_area[['mean_yield', 'median_yield']],
    left_index=True,
    right_index=True,
    how='inner'
)

# Calculate z-scores for normalization
combined_scores['appreciation_zscore'] = (combined_scores['cagr_pct'] - combined_scores['cagr_pct'].mean()) / combined_scores['cagr_pct'].std()
combined_scores['yield_zscore'] = (combined_scores['mean_yield'] - combined_scores['mean_yield'].mean()) / combined_scores['mean_yield'].std()

# Calculate composite score (50% appreciation, 50% rental yield)
combined_scores['investment_score'] = (combined_scores['appreciation_zscore'] * 0.5 + combined_scores['yield_zscore'] * 0.5) * 10 + 50

# Scale to 0-100
combined_scores['investment_score'] = ((combined_scores['investment_score'] - combined_scores['investment_score'].min()) /
                                      (combined_scores['investment_score'].max() - combined_scores['investment_score'].min()) * 100)

combined_scores = combined_scores.sort_values('investment_score', ascending=False)

print("\nTop 15 Planning Areas by Investment Score:")
print(combined_scores.head(15)[['cagr_pct', 'mean_yield', 'investment_score']].round(2))

# %%
# 6. MARKET MOMENTUM ANALYSIS
print("\n" + "=" * 80)
print("MARKET MOMENTUM ANALYSIS")
print("=" * 80)

momentum_data = hdb[hdb['yoy_change_pct'].notna()].copy()
print(f"\nRecords with YoY change data: {len(momentum_data):,}")

# Recent momentum (2023-2025)
recent_momentum = momentum_data[momentum_data['year'] >= 2023].copy()
momentum_by_area = recent_momentum.groupby('planning_area')['yoy_change_pct'].agg([
    ('count', 'count'),
    ('mean_yoy_change', 'mean'),
    ('median_yoy_change', 'median'),
    ('volatility', 'std')  # Lower is better
]).round(2)

momentum_by_area = momentum_by_area[momentum_by_area['count'] >= 10]
momentum_by_area['risk_adjusted_momentum'] = momentum_by_area['mean_yoy_change'] / (momentum_by_area['volatility'] + 1)
momentum_by_area = momentum_by_area.sort_values('risk_adjusted_momentum', ascending=False)

print("\nTop 10 Planning Areas by Risk-Adjusted Momentum:")
print(momentum_by_area.head(10))

# %%
# 7. AMENITY IMPACT ANALYSIS
print("\n" + "=" * 80)
print("AMENITY IMPACT ON PRICES")
print("=" * 80)

# Correlation between amenities and prices
amenity_cols = ['dist_to_nearest_mrt', 'dist_to_nearest_supermarket',
                'dist_to_nearest_park', 'dist_to_nearest_hawker',
                'dist_to_nearest_preschool', 'dist_to_nearest_childcare']

# Filter data with amenity information
amenity_data = hdb[amenity_cols + ['price_psm', 'planning_area']].dropna()

if len(amenity_data) > 0:
    amenity_corr = amenity_data[['price_psm'] + amenity_cols].corr()['price_psm'].sort_values()
    print("\nCorrelation between Distance to Amenities and Price PSM:")
    print(amenity_corr[amenity_cols].round(3))

# %%
# 8. VISUALIZATIONS

# Figure 1: Price Appreciation by Planning Area
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Top 15 areas by CAGR
top_appreciation = appreciation_df.head(15)
axes[0, 0].barh(range(len(top_appreciation)), top_appreciation['cagr_pct'])
axes[0, 0].set_yticks(range(len(top_appreciation)))
axes[0, 0].set_yticklabels(top_appreciation.index, fontsize=9)
axes[0, 0].set_xlabel('CAGR (%)')
axes[0, 0].set_title('Top 15 Planning Areas - Price Appreciation CAGR', fontweight='bold')
axes[0, 0].axvline(x=0, color='red', linestyle='--', alpha=0.5)

# Top 15 areas by rental yield
top_yield = rental_yield_by_area.head(15)
axes[0, 1].barh(range(len(top_yield)), top_yield['mean_yield'])
axes[0, 1].set_yticks(range(len(top_yield)))
axes[0, 1].set_yticklabels(top_yield.index, fontsize=9)
axes[0, 1].set_xlabel('Rental Yield (%)')
axes[0, 1].set_title('Top 15 Planning Areas - Average Rental Yield', fontweight='bold')
axes[0, 1].axvline(x=5.9, color='red', linestyle='--', alpha=0.5, label='Overall Mean')

# Investment score distribution
axes[1, 0].hist(combined_scores['investment_score'], bins=20, edgecolor='black', alpha=0.7)
axes[1, 0].set_xlabel('Investment Score')
axes[1, 0].set_ylabel('Frequency')
axes[1, 0].set_title('Distribution of Investment Scores', fontweight='bold')
axes[1, 0].axvline(x=combined_scores['investment_score'].mean(), color='red', linestyle='--', label='Mean')
axes[1, 0].legend()

# Risk-Adjusted Momentum
top_momentum = momentum_by_area.head(15)
axes[1, 1].barh(range(len(top_momentum)), top_momentum['risk_adjusted_momentum'])
axes[1, 1].set_yticks(range(len(top_momentum)))
axes[1, 1].set_yticklabels(top_momentum.index, fontsize=9)
axes[1, 1].set_xlabel('Risk-Adjusted Momentum')
axes[1, 1].set_title('Top 10 Planning Areas - Risk-Adjusted Momentum', fontweight='bold')

plt.tight_layout()
plt.savefig('analysis_output/hdb_investment_analysis.png', dpi=300, bbox_inches='tight')
plt.show()

# %%
# 9. FINAL RECOMMENDATIONS
print("\n" + "=" * 80)
print("INVESTMENT RECOMMENDATIONS BY PLANNING AREA")
print("=" * 80)

# Create recommendation tiers
def get_tier(score):
    if score >= 80:
        return 'Tier 1: Excellent'
    elif score >= 60:
        return 'Tier 2: Good'
    elif score >= 40:
        return 'Tier 3: Moderate'
    else:
        return 'Tier 4: Below Average'

combined_scores['tier'] = combined_scores['investment_score'].apply(get_tier)

# Merge with momentum data
final_recommendations = combined_scores.merge(
    momentum_by_area[['mean_yoy_change', 'volatility']],
    left_index=True,
    right_index=True,
    how='left'
)

# Sort by investment score
final_recommendations = final_recommendations.sort_values('investment_score', ascending=False)

print("\nTop 20 Planning Areas for HDB Investment:")
print("\n" + "-" * 120)
print(f"{'Planning Area':<25} {'Inv Score':<10} {'CAGR %':<10} {'Yield %':<10} {'YoY %':<10} {'Volatility':<12} {'Tier'}")
print("-" * 120)

for idx, row in final_recommendations.head(20).iterrows():
    print(f"{idx:<25} {row['investment_score']:>6.1f}     {row['cagr_pct']:>6.2f}%    {row['mean_yield']:>6.2f}%    "
          f"{row.get('mean_yoy_change', 0):>6.2f}%    {row.get('volatility', 0):>6.2f}%       {row['tier']}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
print("\nSummary:")
print(f"- Analyzed {len(hdb):,} HDB transactions")
print(f"- Covered {hdb['planning_area'].nunique()} planning areas")
print(f"- Date range: {hdb['transaction_date'].min().strftime('%Y')} to {hdb['transaction_date'].max().strftime('%Y')}")
print("- Investment score based on: 50% price appreciation (CAGR) + 50% rental yield")
print("\nVisualization saved to: analysis_output/hdb_investment_analysis.png")
