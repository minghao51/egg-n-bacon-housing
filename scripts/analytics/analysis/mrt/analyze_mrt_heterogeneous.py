"""
Heterogeneous MRT Impact Analysis Within HDB

Analyzes whether MRT impact varies by:
- Flat type (1 ROOM to EXECUTIVE)
- Town (26 HDB towns)
- Era (pre-2021 vs 2021+)
- Price tier (budget vs premium)

Focus: HDB-only analysis (amenity features only available for HDB)
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Paths
DATA_DIR = Path("data/pipeline/L3")
OUTPUT_DIR = Path("data/analytics/mrt_impact")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_data():
    """Load HDB data with amenity features."""
    print("="*80)
    print("HETEROGENEOUS MRT IMPACT ANALYSIS - HDB SUB-GROUPS")
    print("="*80)

    df = pd.read_parquet(DATA_DIR / "housing_unified.parquet")
    df = df[df['year'] >= 2021].copy()

    # Filter to HDB only (amenity features only available for HDB)
    hdb = df[df['property_type'] == 'HDB'].copy()

    print("\nDataset:")
    print(f"  Total records (2021+): {len(df):,}")
    print(f"  HDB records: {len(hdb):,}")
    print(f"  Condo/EC: {len(df) - len(hdb):,} (no amenity data)")

    return hdb


def analyze_by_flat_type(hdb):
    """Analyze MRT impact by flat type."""
    print(f"\n{'='*80}")
    print("ANALYSIS BY FLAT TYPE")
    print(f"{'='*80}")

    results = []

    for flat_type in hdb['flat_type'].unique():
        subset = hdb[hdb['flat_type'] == flat_type].copy()

        if len(subset) < 100:
            continue

        # Prepare features
        X = subset[['dist_to_nearest_mrt', 'floor_area_sqm',
                    'remaining_lease_months', 'year']].values
        y = subset['price_psf'].values

        # Drop NaN
        mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X, y = X[mask], y[mask]

        if len(X) < 50:
            continue

        # Fit model
        model = LinearRegression()
        model.fit(X, y)

        # Extract MRT coefficient
        mrt_coef = model.coef_[0]

        # Calculate metrics
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)
        mae = mean_absolute_error(y, y_pred)

        results.append({
            'flat_type': flat_type,
            'n': len(X),
            'mean_price': y.mean(),
            'mean_mrt_dist': X[:, 0].mean(),
            'mrt_coef': mrt_coef,
            'mrt_coef_100m': mrt_coef * 100,
            'r2': r2,
            'mae': mae
        })

    results_df = pd.DataFrame(results).sort_values('mrt_coef_100m')

    print("\nMRT Impact by Flat Type (Every 100m closer to MRT):")
    print(results_df[['flat_type', 'n', 'mean_price', 'mrt_coef_100m', 'r2']].to_string(index=False))

    return results_df


def analyze_by_town(hdb, min_n=500):
    """Analyze MRT impact by town."""
    print(f"\n{'='*80}")
    print(f"ANALYSIS BY TOWN (min {min_n:,} transactions)")
    print(f"{'='*80}")

    results = []

    for town in hdb['town'].unique():
        subset = hdb[hdb['town'] == town].copy()

        if len(subset) < min_n:
            continue

        # Prepare features
        X = subset[['dist_to_nearest_mrt', 'floor_area_sqm',
                    'remaining_lease_months', 'year']].values
        y = subset['price_psf'].values

        # Drop NaN
        mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X, y = X[mask], y[mask]

        if len(X) < 100:
            continue

        # Fit model
        model = LinearRegression()
        model.fit(X, y)

        # Extract MRT coefficient
        mrt_coef = model.coef_[0]

        # Calculate metrics
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)

        results.append({
            'town': town,
            'n': len(X),
            'mean_price': y.mean(),
            'mean_mrt_dist': X[:, 0].mean(),
            'mrt_coef_100m': mrt_coef * 100,
            'r2': r2
        })

    results_df = pd.DataFrame(results).sort_values('mrt_coef_100m', ascending=False)

    print("\nTop 10 Towns by MRT Impact (Premium per 100m closer):")
    print(results_df.head(10)[['town', 'n', 'mean_price', 'mrt_coef_100m']].to_string(index=False))

    print("\nBottom 10 Towns by MRT Impact (or negative impact):")
    print(results_df.tail(10)[['town', 'n', 'mean_price', 'mrt_coef_100m']].to_string(index=False))

    return results_df


def analyze_by_price_tier(hdb):
    """Analyze MRT impact by price tier."""
    print(f"\n{'='*80}")
    print("ANALYSIS BY PRICE TIER")
    print(f"{'='*80}")

    # Create price tiers based on price_psf quartiles
    hdb = hdb.copy()
    hdb['price_tier'] = pd.qcut(
        hdb['price_psf'],
        q=4,
        labels=['Budget', 'Mid-Budget', 'Mid-Premium', 'Premium']
    )

    results = []

    for tier in ['Budget', 'Mid-Budget', 'Mid-Premium', 'Premium']:
        subset = hdb[hdb['price_tier'] == tier].copy()

        # Prepare features
        X = subset[['dist_to_nearest_mrt', 'floor_area_sqm',
                    'remaining_lease_months', 'year']].values
        y = subset['price_psf'].values

        # Drop NaN
        mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X, y = X[mask], y[mask]

        # Fit model
        model = LinearRegression()
        model.fit(X, y)

        # Extract MRT coefficient
        mrt_coef = model.coef_[0]

        # Calculate metrics
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)

        results.append({
            'price_tier': tier,
            'n': len(X),
            'mean_price': y.mean(),
            'price_range': f"{y.min():.0f}-{y.max():.0f}",
            'mrt_coef_100m': mrt_coef * 100,
            'r2': r2
        })

    results_df = pd.DataFrame(results)

    print("\nMRT Impact by Price Tier:")
    print(results_df[['price_tier', 'n', 'mean_price', 'price_range', 'mrt_coef_100m']].to_string(index=False))

    return results_df


def create_town_premiums_ranked_chart(town_results):
    """Create horizontal bar chart of all towns ranked by MRT premium."""
    print("\nCreating town-level MRT premiums chart...")

    # Sort by premium (descending order)
    town_sorted = town_results.sort_values('mrt_coef_100m', ascending=True)

    # Create color gradient from red (negative) to green (positive)
    premiums = town_sorted['mrt_coef_100m'].values
    max_val = max(abs(premiums.min()), abs(premiums.max()))
    colors = []
    for val in premiums:
        if val < 0:
            # Red for negative
            intensity = abs(val) / max_val
            colors.append((1, 1 - intensity * 0.7, 1 - intensity * 0.7))  # Red gradient
        else:
            # Green for positive
            intensity = val / max_val
            colors.append((1 - intensity * 0.7, 1, 1 - intensity * 0.7))  # Green gradient

    # Create chart
    fig, ax = plt.subplots(figsize=(12, 10))

    bars = ax.barh(range(len(town_sorted)), premiums, color=colors, edgecolor='black', linewidth=0.5)

    # Add vertical line at x=0
    ax.axvline(x=0, color='black', linestyle='--', linewidth=1)

    # Customize
    ax.set_yticks(range(len(town_sorted)))
    ax.set_yticklabels(town_sorted['town'])
    ax.set_xlabel('MRT Premium per 100m Closer ($ PSF)', fontsize=12, fontweight='bold')
    ax.set_title('MRT Premium by Town (HDB Properties, 2021+)',
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')

    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, premiums)):
        offset = 5 if val >= 0 else -5
        ax.text(val + offset, i, f'${val:.1f}',
                va='center', ha='left' if val >= 0 else 'right',
                fontsize=8, fontweight='bold')

    # Add annotations for extremes
    max_idx = premiums.argmax()
    min_idx = premiums.argmin()
    max_town = town_sorted.iloc[max_idx]['town']
    min_town = town_sorted.iloc[min_idx]['town']
    max_val = premiums[max_idx]
    min_val = premiums[min_idx]

    ax.text(0.98, 0.02, f'Highest: {max_town} (+${max_val:.1f}/100m)\nLowest: {min_town} (${min_val:.1f}/100m)',
            transform=ax.transAxes, va='bottom', ha='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7),
            fontsize=10)

    plt.tight_layout()
    fig_path = OUTPUT_DIR / "town_mrt_premiums_ranked.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"  Saved: {fig_path}")
    plt.close()


def visualize_heterogeneous_effects(flat_type_results, town_results, price_tier_results):
    """Create visualizations of heterogeneous effects."""

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 1. MRT Impact by Flat Type
    ax = axes[0, 0]
    colors = ['green' if x > 0 else 'red' for x in flat_type_results['mrt_coef_100m']]
    ax.barh(flat_type_results['flat_type'], flat_type_results['mrt_coef_100m'], color=colors)
    ax.axvline(x=0, color='black', linestyle='--', linewidth=1)
    ax.set_xlabel('MRT Premium per 100m Closer ($ PSF)')
    ax.set_title('MRT Impact by Flat Type', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')

    # 2. MRT Impact by Town (Top 15)
    ax = axes[0, 1]
    top_towns = town_results.head(15)
    colors = ['green' if x > 0 else 'red' for x in top_towns['mrt_coef_100m']]
    ax.barh(top_towns['town'], top_towns['mrt_coef_100m'], color=colors)
    ax.axvline(x=0, color='black', linestyle='--', linewidth=1)
    ax.set_xlabel('MRT Premium per 100m Closer ($ PSF)')
    ax.set_title('Top 15 Towns by MRT Premium', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')

    # 3. MRT Impact by Price Tier
    ax = axes[1, 0]
    colors = sns.color_palette("RdYlGn", len(price_tier_results))
    ax.bar(price_tier_results['price_tier'], price_tier_results['mrt_coef_100m'], color=colors)
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
    ax.set_ylabel('MRT Premium per 100m Closer ($ PSF)')
    ax.set_title('MRT Impact by Price Tier', fontweight='bold')
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True, alpha=0.3, axis='y')

    # 4. Town Mean Price vs MRT Impact
    ax = axes[1, 1]
    ax.scatter(town_results['mean_price'], town_results['mrt_coef_100m'],
               alpha=0.6, s=100, edgecolors='black', linewidths=0.5)
    ax.axhline(y=0, color='red', linestyle='--', linewidth=1)
    ax.set_xlabel('Mean Town Price ($ PSF)')
    ax.set_ylabel('MRT Premium per 100m Closer ($ PSF)')
    ax.set_title('Relationship: Town Price Level vs MRT Impact', fontweight='bold')

    # Add correlation
    corr = town_results[['mean_price', 'mrt_coef_100m']].corr().iloc[0, 1]
    ax.text(0.05, 0.95, f'Correlation: {corr:.3f}',
            transform=ax.transAxes, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = OUTPUT_DIR / "heterogeneous_effects.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"\nSaved visualization: {fig_path}")
    plt.close()


def main():
    """Main analysis pipeline."""

    # Load data
    hdb = load_data()

    # Analyze by flat type
    flat_type_results = analyze_by_flat_type(hdb)
    flat_type_path = OUTPUT_DIR / "heterogeneous_flat_type.csv"
    flat_type_results.to_csv(flat_type_path, index=False)
    print(f"\nSaved: {flat_type_path}")

    # Analyze by town
    town_results = analyze_by_town(hdb, min_n=500)
    town_path = OUTPUT_DIR / "heterogeneous_town.csv"
    town_results.to_csv(town_path, index=False)
    print(f"Saved: {town_path}")

    # Analyze by price tier
    price_tier_results = analyze_by_price_tier(hdb)
    price_tier_path = OUTPUT_DIR / "heterogeneous_price_tier.csv"
    price_tier_results.to_csv(price_tier_path, index=False)
    print(f"Saved: {price_tier_path}")

    # Visualizations
    visualize_heterogeneous_effects(flat_type_results, town_results, price_tier_results)

    # Create additional town premiums chart
    create_town_premiums_ranked_chart(town_results)

    # Summary statistics
    print(f"\n{'='*80}")
    print("SUMMARY OF HETEROGENEOUS EFFECTS")
    print(f"{'='*80}")

    print("\nBy Flat Type:")
    print(f"  Range: ${flat_type_results['mrt_coef_100m'].min():.2f} to ${flat_type_results['mrt_coef_100m'].max():.2f} per 100m")
    print(f"  Most sensitive: {flat_type_results.iloc[0]['flat_type']} (${abs(flat_type_results.iloc[0]['mrt_coef_100m']):.2f})")

    print("\nBy Town:")
    print(f"  Range: ${town_results['mrt_coef_100m'].min():.2f} to ${town_results['mrt_coef_100m'].max():.2f} per 100m")
    print(f"  Most sensitive: {town_results.iloc[0]['town']} (${abs(town_results.iloc[0]['mrt_coef_100m']):.2f})")

    print("\nBy Price Tier:")
    for _, row in price_tier_results.iterrows():
        print(f"  {row['price_tier']:15s}: ${row['mrt_coef_100m']:6.2f} per 100m")

    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
