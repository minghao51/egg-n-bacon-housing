"""
Heterogeneous School Impact Analysis Within HDB

Analyzes whether school impact varies by:
- Flat type (1 ROOM to EXECUTIVE)
- Town (26 HDB towns)
- Lease remaining (<60 years to 90+ years)
- Price tier (budget vs premium)

Focus: HDB-only analysis to understand subgroup heterogeneity
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error
from scipy import stats

import matplotlib.pyplot as plt
import seaborn as sns

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Paths
DATA_DIR = Path("data/pipeline/L3")
OUTPUT_DIR = Path("data/analysis/school_impact")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_data():
    """Load HDB data with school features."""
    print("="*80)
    print("HETEROGENEOUS SCHOOL IMPACT ANALYSIS - HDB SUB-GROUPS")
    print("="*80)

    df = pd.read_parquet(DATA_DIR / "housing_unified.parquet")
    df = df[df['year'] >= 2021].copy()

    # Filter to HDB only
    hdb = df[df['property_type'] == 'HDB'].copy()

    print(f"\nDataset:")
    print(f"  Total records (2021+): {len(df):,}")
    print(f"  HDB records: {len(hdb):,}")

    # Check school feature coverage
    print("\nSchool feature coverage:")
    for feature in ['school_within_1km', 'school_accessibility_score', 'school_primary_quality_score']:
        if feature in hdb.columns:
            coverage = hdb[feature].notna().sum()
            pct = coverage / len(hdb) * 100
            print(f"  {feature}: {coverage:,}/{len(hdb):,} ({pct:.1f}%)")

    return hdb


def analyze_by_flat_type(hdb, feature='school_accessibility_score'):
    """Analyze school impact by flat type."""
    print(f"\n{'='*80}")
    print(f"ANALYSIS BY FLAT TYPE - {feature}")
    print(f"{'='*80}")

    # Filter to data with feature
    hdb = hdb.dropna(subset=[feature])

    results = []

    for flat_type in hdb['flat_type'].unique():
        subset = hdb[hdb['flat_type'] == flat_type].copy()

        if len(subset) < 100:
            continue

        # Prepare features
        feature_cols = [feature, 'floor_area_sqm', 'remaining_lease_months', 'year']
        available_features = [col for col in feature_cols if col in subset.columns]

        X = subset[available_features].values
        y = subset['price_psf'].values

        # Drop NaN
        mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X, y = X[mask], y[mask]

        if len(X) < 50:
            continue

        # Fit model
        model = LinearRegression()
        model.fit(X, y)

        # Extract school coefficient
        school_coef = model.coef_[0]

        # Calculate metrics
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)
        mae = mean_absolute_error(y, y_pred)

        results.append({
            'flat_type': flat_type,
            'n': len(X),
            'mean_price': y.mean(),
            'mean_feature_value': X[:, 0].mean(),
            'school_coef': school_coef,
            'school_premium_10pt': school_coef * 10,
            'r2': r2,
            'mae': mae
        })

    results_df = pd.DataFrame(results).sort_values('school_premium_10pt')

    if not results_df.empty:
        print("\nSchool Impact by Flat Type (Every 0.1 score increase):")
        print(results_df[['flat_type', 'n', 'mean_price', 'school_premium_10pt', 'r2']].to_string(index=False))
    else:
        print("\n  No flat types had sufficient data")

    return results_df


def analyze_by_town(hdb, feature='school_accessibility_score', min_n=500):
    """Analyze school impact by town."""
    print(f"\n{'='*80}")
    print(f"ANALYSIS BY TOWN (min {min_n:,} transactions) - {feature}")
    print(f"{'='*80}")

    # Filter to data with feature
    hdb = hdb.dropna(subset=[feature])

    results = []

    for town in hdb['town'].unique():
        subset = hdb[hdb['town'] == town].copy()

        if len(subset) < min_n:
            continue

        # Prepare features
        feature_cols = [feature, 'floor_area_sqm', 'remaining_lease_months', 'year']
        available_features = [col for col in feature_cols if col in subset.columns]

        X = subset[available_features].values
        y = subset['price_psf'].values

        # Drop NaN
        mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X, y = X[mask], y[mask]

        if len(X) < 100:
            continue

        # Fit model
        model = LinearRegression()
        model.fit(X, y)

        # Extract school coefficient
        school_coef = model.coef_[0]

        # Calculate metrics
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)

        results.append({
            'town': town,
            'n': len(X),
            'mean_price': y.mean(),
            'mean_feature_value': X[:, 0].mean(),
            'school_premium_10pt': school_coef * 10,
            'r2': r2
        })

    results_df = pd.DataFrame(results).sort_values('school_premium_10pt', ascending=False)

    if not results_df.empty:
        print(f"\nTop 10 Towns by School Impact (Premium per 0.1 score increase):")
        print(results_df.head(10)[['town', 'n', 'mean_price', 'school_premium_10pt']].to_string(index=False))

        print(f"\nBottom 10 Towns by School Impact (or negative impact):")
        print(results_df.tail(10)[['town', 'n', 'mean_price', 'school_premium_10pt']].to_string(index=False))
    else:
        print("\n  No towns had sufficient data")

    return results_df


def analyze_by_lease_remaining(hdb, feature='school_accessibility_score'):
    """Analyze school impact by remaining lease."""
    print(f"\n{'='*80}")
    print(f"ANALYSIS BY REMAINING LEASE - {feature}")
    print(f"{'='*80}")

    # Filter to data with feature
    hdb = hdb.dropna(subset=[feature])

    # Create lease bands
    hdb = hdb.copy()
    if 'remaining_lease_months' in hdb.columns:
        hdb['lease_years'] = hdb['remaining_lease_months'] / 12
        hdb['lease_band'] = pd.cut(
            hdb['lease_years'],
            bins=[0, 60, 70, 80, 90, 100],
            labels=['<60 years', '60-70 years', '70-80 years', '80-90 years', '90+ years']
        )
    else:
        print("  remaining_lease_months not available, skipping lease analysis")
        return pd.DataFrame()

    results = []

    for lease_band in ['<60 years', '60-70 years', '70-80 years', '80-90 years', '90+ years']:
        subset = hdb[hdb['lease_band'] == lease_band].copy()

        if len(subset) < 100:
            continue

        # Prepare features
        feature_cols = [feature, 'floor_area_sqm', 'year']
        available_features = [col for col in feature_cols if col in subset.columns]

        X = subset[available_features].values
        y = subset['price_psf'].values

        # Drop NaN
        mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X, y = X[mask], y[mask]

        if len(X) < 50:
            continue

        # Fit model
        model = LinearRegression()
        model.fit(X, y)

        # Extract school coefficient
        school_coef = model.coef_[0]

        # Calculate metrics
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)

        results.append({
            'lease_band': lease_band,
            'n': len(X),
            'mean_price': y.mean(),
            'mean_lease_years': X[:, 0].mean() if 'remaining_lease_months' not in feature_cols else subset['lease_years'].mean(),
            'school_premium_10pt': school_coef * 10,
            'r2': r2
        })

    results_df = pd.DataFrame(results)

    if not results_df.empty:
        print("\nSchool Impact by Remaining Lease:")
        print(results_df[['lease_band', 'n', 'mean_price', 'school_premium_10pt']].to_string(index=False))
    else:
        print("\n  No lease bands had sufficient data")

    return results_df


def analyze_by_price_tier(hdb, feature='school_accessibility_score'):
    """Analyze school impact by price tier."""
    print(f"\n{'='*80}")
    print(f"ANALYSIS BY PRICE TIER - {feature}")
    print(f"{'='*80}")

    # Filter to data with feature
    hdb = hdb.dropna(subset=[feature])

    # Create price tiers based on price_psf quartiles
    hdb = hdb.copy()
    hdb['price_tier'] = pd.qcut(
        hdb['price_psf'],
        q=4,
        labels=['Budget', 'Mid-Budget', 'Mid-Premium', 'Premium'],
        duplicates='drop'
    )

    results = []

    for tier in ['Budget', 'Mid-Budget', 'Mid-Premium', 'Premium']:
        subset = hdb[hdb['price_tier'] == tier].copy()

        if len(subset) < 100:
            continue

        # Prepare features
        feature_cols = [feature, 'floor_area_sqm', 'remaining_lease_months', 'year']
        available_features = [col for col in feature_cols if col in subset.columns]

        X = subset[available_features].values
        y = subset['price_psf'].values

        # Drop NaN
        mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X, y = X[mask], y[mask]

        if len(X) < 50:
            continue

        # Fit model
        model = LinearRegression()
        model.fit(X, y)

        # Extract school coefficient
        school_coef = model.coef_[0]

        # Calculate metrics
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)

        results.append({
            'price_tier': tier,
            'n': len(X),
            'mean_price': y.mean(),
            'price_range': f"{y.min():.0f}-{y.max():.0f}",
            'school_premium_10pt': school_coef * 10,
            'r2': r2
        })

    results_df = pd.DataFrame(results)

    if not results_df.empty:
        print("\nSchool Impact by Price Tier:")
        print(results_df[['price_tier', 'n', 'mean_price', 'price_range', 'school_premium_10pt']].to_string(index=False))
    else:
        print("\n  No price tiers had sufficient data")

    return results_df


def visualize_heterogeneous_effects(flat_type_results, town_results, lease_results, price_tier_results):
    """Create visualizations of heterogeneous effects."""

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 1. School Impact by Flat Type
    ax = axes[0, 0]
    if not flat_type_results.empty:
        colors = ['green' if x > 0 else 'red' for x in flat_type_results['school_premium_10pt']]
        ax.barh(flat_type_results['flat_type'], flat_type_results['school_premium_10pt'], color=colors)
        ax.axvline(x=0, color='black', linestyle='--', linewidth=1)
        ax.set_xlabel('School Premium per 0.1 Score Increase ($ PSF)')
        ax.set_title('School Impact by Flat Type', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
    else:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)

    # 2. School Impact by Town (Top 15)
    ax = axes[0, 1]
    if not town_results.empty:
        top_towns = town_results.head(15)
        colors = ['green' if x > 0 else 'red' for x in top_towns['school_premium_10pt']]
        ax.barh(top_towns['town'], top_towns['school_premium_10pt'], color=colors)
        ax.axvline(x=0, color='black', linestyle='--', linewidth=1)
        ax.set_xlabel('School Premium per 0.1 Score Increase ($ PSF)')
        ax.set_title('Top 15 Towns by School Premium', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
    else:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)

    # 3. School Impact by Remaining Lease
    ax = axes[1, 0]
    if not lease_results.empty:
        colors = sns.color_palette("RdYlGn", len(lease_results))
        ax.bar(lease_results['lease_band'], lease_results['school_premium_10pt'], color=colors)
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
        ax.set_ylabel('School Premium per 0.1 Score Increase ($ PSF)')
        ax.set_title('School Impact by Remaining Lease', fontweight='bold')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3, axis='y')
    else:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)

    # 4. Town Mean Price vs School Impact
    ax = axes[1, 1]
    if not town_results.empty:
        ax.scatter(town_results['mean_price'], town_results['school_premium_10pt'],
                   alpha=0.6, s=100, edgecolors='black', linewidths=0.5)
        ax.axhline(y=0, color='red', linestyle='--', linewidth=1)
        ax.set_xlabel('Mean Town Price ($ PSF)')
        ax.set_ylabel('School Premium per 0.1 Score Increase ($ PSF)')
        ax.set_title('Relationship: Town Price Level vs School Impact', fontweight='bold')

        # Add correlation
        corr = town_results[['mean_price', 'school_premium_10pt']].corr().iloc[0, 1]
        ax.text(0.05, 0.95, f'Correlation: {corr:.3f}',
                transform=ax.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)

    plt.tight_layout()
    fig_path = OUTPUT_DIR / "heterogeneous_effects.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"\nSaved visualization: {fig_path}")
    plt.close()


def main():
    """Main analysis pipeline."""

    # Load data
    hdb = load_data()

    # Check if school features are available
    if 'school_accessibility_score' not in hdb.columns:
        print("\n" + "="*80)
        print("⚠️  WARNING: School features not available!")
        print("="*80)
        print("\nPlease ensure school features have been calculated in L3_export.py")
        print("\nOnce complete, re-run this script.")
        print("="*80)
        return

    # Analyze by flat type
    flat_type_results = analyze_by_flat_type(hdb)
    if not flat_type_results.empty:
        flat_type_path = OUTPUT_DIR / "heterogeneous_flat_type.csv"
        flat_type_results.to_csv(flat_type_path, index=False)
        print(f"\nSaved: {flat_type_path}")

    # Analyze by town
    town_results = analyze_by_town(hdb, min_n=500)
    if not town_results.empty:
        town_path = OUTPUT_DIR / "heterogeneous_town.csv"
        town_results.to_csv(town_path, index=False)
        print(f"Saved: {town_path}")

    # Analyze by lease remaining
    lease_results = analyze_by_lease_remaining(hdb)
    if not lease_results.empty:
        lease_path = OUTPUT_DIR / "heterogeneous_lease.csv"
        lease_results.to_csv(lease_path, index=False)
        print(f"Saved: {lease_path}")

    # Analyze by price tier
    price_tier_results = analyze_by_price_tier(hdb)
    if not price_tier_results.empty:
        price_tier_path = OUTPUT_DIR / "heterogeneous_price_tier.csv"
        price_tier_results.to_csv(price_tier_path, index=False)
        print(f"Saved: {price_tier_path}")

    # Visualizations
    visualize_heterogeneous_effects(flat_type_results, town_results, lease_results, price_tier_results)

    # Summary statistics
    print(f"\n{'='*80}")
    print("SUMMARY OF HETEROGENEOUS EFFECTS")
    print(f"{'='*80}")

    if not flat_type_results.empty:
        print("\nBy Flat Type:")
        print(f"  Range: ${flat_type_results['school_premium_10pt'].min():.2f} to ${flat_type_results['school_premium_10pt'].max():.2f} per 0.1 score")
        most_sensitive = flat_type_results.iloc[0] if flat_type_results['school_premium_10pt'].abs().idxmax() == flat_type_results.index[0] else flat_type_results.loc[flat_type_results['school_premium_10pt'].abs().idxmax()]
        print(f"  Most sensitive: {most_sensitive['flat_type']} (${abs(most_sensitive['school_premium_10pt']):.2f})")

    if not town_results.empty:
        print("\nBy Town:")
        print(f"  Range: ${town_results['school_premium_10pt'].min():.2f} to ${town_results['school_premium_10pt'].max():.2f} per 0.1 score")
        print(f"  Most sensitive: {town_results.iloc[0]['town']} (${abs(town_results.iloc[0]['school_premium_10pt']):.2f})")

    if not price_tier_results.empty:
        print("\nBy Price Tier:")
        for _, row in price_tier_results.iterrows():
            print(f"  {row['price_tier']:15s}: ${row['school_premium_10pt']:6.2f} per 0.1 score")

    if not lease_results.empty:
        print("\nBy Remaining Lease:")
        for _, row in lease_results.iterrows():
            print(f"  {row['lease_band']:15s}: ${row['school_premium_10pt']:6.2f} per 0.1 score")

    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
