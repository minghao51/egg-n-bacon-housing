"""
Town Performance Leaderboard - Comparative Analytics

Analyzes and ranks Singapore housing towns across multiple dimensions:
- Price performance (YoY growth)
- Rental yield
- Market activity (trading volume)
- Liquidity (time trend)
- Affordability

Creates actionable insights for investors and policymakers.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

import matplotlib.pyplot as plt
import seaborn as sns

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (14, 8)

# Paths
DATA_DIR = Path("data/analysis/market_segmentation")
OUTPUT_DIR = Path("data/analysis/town_leaderboard")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

print("="*80)
print("TOWN PERFORMANCE LEADERBOARD - SINGAPORE HOUSING MARKET")
print("="*80)

# ============================================================================
# 1. LOAD DATA
# ============================================================================
print("\nLoading dataset...")

df = pd.read_parquet(DATA_DIR / "housing_unified_segmented.parquet")
print(f"Loaded {len(df):,} records")

# Focus on recent data (2021+)
df_recent = df[df['year'] >= 2021].copy()
print(f"Recent transactions (2021+): {len(df_recent):,} records")

# ============================================================================
# 2. CALCULATE TOWN-LEVEL METRICS
# ============================================================================
print("\nCalculating town-level metrics...")

# Group by town
town_metrics = df_recent.groupby('town').agg({
    'price_psm': ['mean', 'median', 'std', 'count'],
    'price': ['mean', 'median'],
    'floor_area_sqm': 'mean',
    'rental_yield_pct': 'mean',
    'yoy_change_pct': 'mean',
    'mom_change_pct': 'mean',
    'transaction_count': 'mean',
    'volume_3m_avg': 'mean',
    'volume_12m_avg': 'mean',
    'year': 'max'
}).round(2)

# Flatten column names
town_metrics.columns = ['_'.join(col).strip() for col in town_metrics.columns.values]
town_metrics = town_metrics.reset_index()
town_metrics = town_metrics.rename(columns={'town': 'town'})

# Filter for towns with sufficient data (min 100 transactions)
town_metrics = town_metrics[town_metrics['price_psm_count'] >= 100]
print(f"  Towns with sufficient data: {len(town_metrics)}")

# ============================================================================
# 3. CALCULATE ADDITIONAL METRICS
# ============================================================================
print("\nCalculating additional metrics...")

# 3.1 Price Growth Rate (YoY)
town_growth = df_recent.groupby(['town', 'year'])['price_psm'].mean().reset_index()
town_growth_pivot = town_growth.pivot(index='town', columns='year', values='price_psm')

# Calculate YoY growth
for town in town_metrics['town']:
    if town in town_growth_pivot.index:
        years = sorted([y for y in town_growth_pivot.columns if y >= 2021])
        if len(years) >= 2:
            first_year = min(years)
            last_year = max(years)
            if pd.notna(town_growth_pivot.loc[town, first_year]) and pd.notna(town_growth_pivot.loc[town, last_year]):
                initial_price = town_growth_pivot.loc[town, first_year]
                final_price = town_growth_pivot.loc[town, last_year]
                growth_rate = ((final_price - initial_price) / initial_price) * 100
                town_metrics.loc[town_metrics['town'] == town, 'price_growth_yoy'] = growth_rate

# 3.2 Market Activity Score (trading volume)
# Normalize and combine multiple volume metrics
volume_metrics = ['transaction_count_mean', 'volume_3m_avg_mean', 'volume_12m_avg_mean']
for metric in volume_metrics:
    if metric in town_metrics.columns:
        town_metrics[f'{metric}_norm'] = (town_metrics[metric] - town_metrics[metric].min()) / \
                                        (town_metrics[metric].max() - town_metrics[metric].min())

# 3.3 Affordability Score (lower price = higher score)
if 'price_psm_median' in town_metrics.columns:
    # Invert: lower price = higher affordability
    town_metrics['affordability_score'] = 1 - ((town_metrics['price_psm_median'] - town_metrics['price_psm_median'].min()) /
                                                 (town_metrics['price_psm_median'].max() - town_metrics['price_psm_median'].min()))

# 3.4 Liquidity Score (based on transaction count)
if 'price_psm_count' in town_metrics.columns:
    town_metrics['liquidity_score'] = (town_metrics['price_psm_count'] - town_metrics['price_psm_count'].min()) / \
                                       (town_metrics['price_psm_count'].max() - town_metrics['price_psm_count'].min())

# 3.5 Overall Activity Score
activity_cols = [c for c in town_metrics.columns if '_norm' in c]
if activity_cols:
    town_metrics['market_activity_score'] = town_metrics[activity_cols].mean(axis=1)

# ============================================================================
# 4. CREATE COMPOSITE SCORES
# ============================================================================
print("\nCreating composite scores...")

# 4.1 Investor Score (combination of yield, growth, activity)
investor_components = []
if 'rental_yield_pct_mean' in town_metrics.columns:
    # Normalize yield
    town_metrics['rental_yield_norm'] = (town_metrics['rental_yield_pct_mean'] - town_metrics['rental_yield_pct_mean'].min()) / \
                                          (town_metrics['rental_yield_pct_mean'].max() - town_metrics['rental_yield_pct_mean'].min())
    investor_components.append('rental_yield_norm')

if 'price_growth_yoy' in town_metrics.columns:
    # Normalize growth
    town_metrics['price_growth_norm'] = (town_metrics['price_growth_yoy'] - town_metrics['price_growth_yoy'].min()) / \
                                        (town_metrics['price_growth_yoy'].max() - town_metrics['price_growth_yoy'].min())
    investor_components.append('price_growth_norm')

if 'market_activity_score' in town_metrics.columns:
    investor_components.append('market_activity_score')

if investor_components:
    town_metrics['investor_score'] = town_metrics[investor_components].mean(axis=1)

# 4.2 Value Score (affordability + yield)
value_components = []
if 'affordability_score' in town_metrics.columns:
    value_components.append('affordability_score')
if 'rental_yield_norm' in town_metrics.columns:
    value_components.append('rental_yield_norm')

if value_components:
    town_metrics['value_score'] = town_metrics[value_components].mean(axis=1)

# 4.3 Momentum Score (recent price trends)
momentum_components = []
if 'mom_change_pct_mean' in town_metrics.columns:
    # Normalize MoM (handle negative values)
    mom_min = town_metrics['mom_change_pct_mean'].min()
    mom_range = town_metrics['mom_change_pct_mean'].max() - mom_min
    if mom_range > 0:
        town_metrics['mom_change_norm'] = (town_metrics['mom_change_pct_mean'] - mom_min) / mom_range
        momentum_components.append('mom_change_norm')

if 'price_growth_norm' in town_metrics.columns:
    momentum_components.append('price_growth_norm')

if momentum_components:
    town_metrics['momentum_score'] = town_metrics[momentum_components].mean(axis=1)

# ============================================================================
# 5. RANK TOWNS BY CATEGORY
# ============================================================================
print("\nRanking towns by category...")

# Sort by investor score
town_metrics_sorted = town_metrics.sort_values('investor_score', ascending=False)

# Create rankings
town_metrics['investor_rank'] = town_metrics['investor_score'].rank(ascending=False)
town_metrics['value_rank'] = town_metrics['value_score'].rank(ascending=False)
town_metrics['momentum_rank'] = town_metrics['momentum_score'].rank(ascending=False)
town_metrics['affordability_rank'] = town_metrics['affordability_score'].rank(ascending=False)
town_metrics['liquidity_rank'] = town_metrics['liquidity_score'].rank(ascending=False)

print(f"  Rankings created for {len(town_metrics)} towns")

# ============================================================================
# 6. GENERATE LEADERBOARDS
# ============================================================================
print("\n" + "="*80)
print("TOWN LEADERBOARDS")
print("="*80)

# Top 10 for Investor Score
print("\n🏆 TOP 10 TOWNS - INVESTOR SCORE (Yield + Growth + Activity)")
print("-" * 80)
top_investor = town_metrics_sorted.head(10)[['town', 'investor_score', 'rental_yield_pct_mean',
                                               'price_growth_yoy', 'market_activity_score']].copy()
top_investor['investor_score'] = top_investor['investor_score'].apply(lambda x: f"{x:.3f}")
top_investor['rental_yield_pct_mean'] = top_investor['rental_yield_pct_mean'].apply(lambda x: f"{x:.2f}%")
top_investor['price_growth_yoy'] = top_investor['price_growth_yoy'].apply(lambda x: f"{x:.2f}%")
top_investor['market_activity_score'] = top_investor['market_activity_score'].apply(lambda x: f"{x:.3f}")
print(top_investor.to_string(index=False))

# Top 10 for Value (Affordability + Yield)
print("\n💰 TOP 10 TOWNS - VALUE SCORE (Affordability + Yield)")
print("-" * 80)
top_value = town_metrics.sort_values('value_score', ascending=False).head(10)[
    ['town', 'value_score', 'price_psm_median', 'rental_yield_pct_mean']
].copy()
top_value['value_score'] = top_value['value_score'].apply(lambda x: f"{x:.3f}")
top_value['price_psm_median'] = top_value['price_psm_median'].apply(lambda x: f"${x:,.0f}")
top_value['rental_yield_pct_mean'] = top_value['rental_yield_pct_mean'].apply(lambda x: f"{x:.2f}%")
print(top_value.to_string(index=False))

# Top 10 for Momentum
print("\n📈 TOP 10 TOWNS - MOMENTUM SCORE (Recent Price Growth)")
print("-" * 80)
top_momentum = town_metrics.sort_values('momentum_score', ascending=False).head(10)[
    ['town', 'momentum_score', 'mom_change_pct_mean', 'price_growth_yoy']
].copy()
top_momentum['momentum_score'] = top_momentum['momentum_score'].apply(lambda x: f"{x:.3f}")
top_momentum['mom_change_pct_mean'] = top_momentum['mom_change_pct_mean'].apply(lambda x: f"{x:.2f}%")
top_momentum['price_growth_yoy'] = top_momentum['price_growth_yoy'].apply(lambda x: f"{x:.2f}%")
print(top_momentum.to_string(index=False))

# Top 10 for Affordability
print("\n💵 TOP 10 TOWNS - AFFORDABILITY (Lowest Price/PSM)")
print("-" * 80)
top_affordable = town_metrics.sort_values('price_psm_median').head(10)[
    ['town', 'price_psm_median', 'floor_area_sqm_mean', 'rental_yield_pct_mean']
].copy()
top_affordable['price_psm_median'] = top_affordable['price_psm_median'].apply(lambda x: f"${x:,.0f}")
top_affordable['floor_area_sqm_mean'] = top_affordable['floor_area_sqm_mean'].apply(lambda x: f"{x:,.0f} sqm")
top_affordable['rental_yield_pct_mean'] = top_affordable['rental_yield_pct_mean'].apply(lambda x: f"{x:.2f}%")
print(top_affordable.to_string(index=False))

# Top 10 for Liquidity (Most Active)
print("\n🔄 TOP 10 TOWNS - MARKET LIQUIDITY (Transaction Volume)")
print("-" * 80)
top_liquid = town_metrics.sort_values('price_psm_count', ascending=False).head(10)[
    ['town', 'price_psm_count', 'transaction_count_mean', 'volume_12m_avg_mean']
].copy()
top_liquid['price_psm_count'] = top_liquid['price_psm_count'].apply(lambda x: f"{x:,.0f}")
top_liquid['transaction_count_mean'] = top_liquid['transaction_count_mean'].apply(lambda x: f"{x:,.0f}")
top_liquid['volume_12m_avg_mean'] = top_liquid['volume_12m_avg_mean'].apply(lambda x: f"{x:,.0f}")
print(top_liquid.to_string(index=False))

# ============================================================================
# 7. VISUALIZATIONS
# ============================================================================
print("\n" + "="*80)
print("GENERATING VISUALIZATIONS")
print("="*80)

# Visualization 1: Comprehensive Leaderboard
fig, axes = plt.subplots(2, 3, figsize=(20, 12))

# Investor Score
top_15_investor = town_metrics.sort_values('investor_score', ascending=False).head(15)
axes[0, 0].barh(range(len(top_15_investor)), top_15_investor['investor_score'], color='steelblue')
axes[0, 0].set_yticks(range(len(top_15_investor)))
axes[0, 0].set_yticklabels(top_15_investor['town'])
axes[0, 0].set_xlabel('Investor Score', fontsize=11, fontweight='bold')
axes[0, 0].set_title('Top 15 Towns - Investor Score\n(Yield + Growth + Activity)', fontsize=12, fontweight='bold')
axes[0, 0].grid(True, alpha=0.3, axis='x')

# Value Score
top_15_value = town_metrics.sort_values('value_score', ascending=False).head(15)
axes[0, 1].barh(range(len(top_15_value)), top_15_value['value_score'], color='coral')
axes[0, 1].set_yticks(range(len(top_15_value)))
axes[0, 1].set_yticklabels(top_15_value['town'])
axes[0, 1].set_xlabel('Value Score', fontsize=11, fontweight='bold')
axes[0, 1].set_title('Top 15 Towns - Value Score\n(Affordability + Yield)', fontsize=12, fontweight='bold')
axes[0, 1].grid(True, alpha=0.3, axis='x')

# Momentum Score
top_15_momentum = town_metrics.sort_values('momentum_score', ascending=False).head(15)
axes[0, 2].barh(range(len(top_15_momentum)), top_15_momentum['momentum_score'], color='green')
axes[0, 2].set_yticks(range(len(top_15_momentum)))
axes[0, 2].set_yticklabels(top_15_momentum['town'])
axes[0, 2].set_xlabel('Momentum Score', fontsize=11, fontweight='bold')
axes[0, 2].set_title('Top 15 Towns - Momentum Score\n(Recent Growth)', fontsize=12, fontweight='bold')
axes[0, 2].grid(True, alpha=0.3, axis='x')

# Rental Yield
top_15_yield = town_metrics.sort_values('rental_yield_pct_mean', ascending=False).head(15)
axes[1, 0].barh(range(len(top_15_yield)), top_15_yield['rental_yield_pct_mean'], color='purple')
axes[1, 0].set_yticks(range(len(top_15_yield)))
axes[1, 0].set_yticklabels(top_15_yield['town'])
axes[1, 0].set_xlabel('Rental Yield (%)', fontsize=11, fontweight='bold')
axes[1, 0].set_title('Top 15 Towns - Rental Yield', fontsize=12, fontweight='bold')
axes[1, 0].grid(True, alpha=0.3, axis='x')

# Price Level (ascending for affordability)
bottom_15_price = town_metrics.sort_values('price_psm_median').head(15)
axes[1, 1].barh(range(len(bottom_15_price)), bottom_15_price['price_psm_median'], color='orange')
axes[1, 1].set_yticks(range(len(bottom_15_price)))
axes[1, 1].set_yticklabels(bottom_15_price['town'])
axes[1, 1].set_xlabel('Median Price ($/psm)', fontsize=11, fontweight='bold')
axes[1, 1].set_title('Top 15 Most Affordable Towns', fontsize=12, fontweight='bold')
axes[1, 1].grid(True, alpha=0.3, axis='x')

# Transaction Volume
top_15_volume = town_metrics.sort_values('price_psm_count', ascending=False).head(15)
axes[1, 2].barh(range(len(top_15_volume)), top_15_volume['price_psm_count'], color='brown')
axes[1, 2].set_yticks(range(len(top_15_volume)))
axes[1, 2].set_yticklabels(top_15_volume['town'])
axes[1, 2].set_xlabel('Transaction Count', fontsize=11, fontweight='bold')
axes[1, 2].set_title('Top 15 Towns - Market Activity', fontsize=12, fontweight='bold')
axes[1, 2].grid(True, alpha=0.3, axis='x')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'town_leaderboard.png', dpi=300, bbox_inches='tight')
plt.show()

print("  Saved: town_leaderboard.png")

# Visualization 2: Scatter Plot Matrix
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Price vs Yield
scatter = axes[0].scatter(town_metrics['price_psm_median'], town_metrics['rental_yield_pct_mean'],
                        s=town_metrics['price_psm_count']/100,  # Size by transaction count
                        c=town_metrics['investor_score'],
                        cmap='RdYlGn',
                        alpha=0.6,
                        edgecolors='black',
                        linewidths=0.5)
axes[0].set_xlabel('Median Price ($/psm)', fontsize=12, fontweight='bold')
axes[0].set_ylabel('Rental Yield (%)', fontsize=12, fontweight='bold')
axes[0].set_title('Price vs Yield (Size = Transaction Count, Color = Investor Score)', fontsize=13, fontweight='bold')
cbar = plt.colorbar(scatter, ax=axes[0])
cbar.set_label('Investor Score', fontsize=10)
axes[0].grid(True, alpha=0.3)

# Growth vs Yield
scatter2 = axes[1].scatter(town_metrics['price_growth_yoy'], town_metrics['rental_yield_pct_mean'],
                         s=town_metrics['price_psm_count']/100,
                         c=town_metrics['momentum_score'],
                         cmap='RdYlGn',
                         alpha=0.6,
                         edgecolors='black',
                         linewidths=0.5)
axes[1].set_xlabel('Price Growth (YoY %)', fontsize=12, fontweight='bold')
axes[1].set_ylabel('Rental Yield (%)', fontsize=12, fontweight='bold')
axes[1].set_title('Growth vs Yield (Size = Transaction Count, Color = Momentum Score)', fontsize=13, fontweight='bold')
cbar2 = plt.colorbar(scatter2, ax=axes[1])
cbar2.set_label('Momentum Score', fontsize=10)
axes[1].grid(True, alpha=0.3)
axes[1].axvline(x=0, color='black', linestyle='--', linewidth=1)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'town_relationships.png', dpi=300, bbox_inches='tight')
plt.show()

print("  Saved: town_relationships.png")

# ============================================================================
# 8. EXPORT RESULTS
# ============================================================================
print("\n" + "="*80)
print("EXPORTING RESULTS")
print("="*80)

# Select columns for export
export_cols = [
    'town',
    'price_psm_median', 'price_psm_mean', 'rental_yield_pct_mean',
    'price_growth_yoy', 'mom_change_pct_mean',
    'investor_score', 'investor_rank',
    'value_score', 'value_rank',
    'momentum_score', 'momentum_rank',
    'affordability_score', 'affordability_rank',
    'liquidity_score', 'liquidity_rank',
    'price_psm_count', 'market_activity_score'
]

# Only export columns that exist
export_cols = [c for c in export_cols if c in town_metrics.columns]

town_metrics[export_cols].to_csv(
    OUTPUT_DIR / 'town_leaderboard.csv',
    index=False
)
print(f"  Saved: town_leaderboard.csv ({len(town_metrics)} towns)")

# Create summary leaderboard
leaderboard_summary = town_metrics[['town', 'investor_rank', 'value_rank', 'momentum_rank']].copy()
leaderboard_summary['overall_rank'] = (
    town_metrics['investor_rank'] +
    town_metrics['value_rank'] +
    town_metrics['momentum_rank']
) / 3
leaderboard_summary = leaderboard_summary.sort_values('overall_rank')
leaderboard_summary.to_csv(
    OUTPUT_DIR / 'town_leaderboard_summary.csv',
    index=False
)
print(f"  Saved: town_leaderboard_summary.csv")

print("\n" + "="*80)
print("TOWN LEADERBOARD ANALYSIS COMPLETE")
print("="*80)
print(f"\nResults saved to: {OUTPUT_DIR}")
print(f"\nKey Insights:")
print(f"  • {len(town_metrics)} towns analyzed")
print(f"  • Top investor town: {town_metrics.loc[town_metrics['investor_score'].idxmax(), 'town']}")
print(f"  • Top value town: {town_metrics.loc[town_metrics['value_score'].idxmax(), 'town']}")
print(f"  • Top momentum town: {town_metrics.loc[town_metrics['momentum_score'].idxmax(), 'town']}")
print(f"  • Most affordable: {town_metrics.loc[town_metrics['affordability_score'].idxmax(), 'town']}")
