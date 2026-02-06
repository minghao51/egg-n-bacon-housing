#!/usr/bin/env python3
"""
Advanced Lease Decay Analysis - Enhanced Version.

This script extends the base lease decay analysis with:
1. Financing & Policy Threshold Analysis
2. Bala's Curve Validation
3. Geospatial Hedonic Regression
4. 70-80 Year Decay Peak Deep-Dive

Usage:
    uv run python scripts/analytics/analysis/market/analyze_lease_decay_advanced.py
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import statsmodels.api as sm
import patsy

project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.core.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_hdb_data() -> pd.DataFrame:
    """Load HDB transaction data from L1 pipeline."""
    logger.info("Loading HDB transaction data...")

    path = Config.PARQUETS_DIR / "L1" / "housing_hdb_transaction.parquet"
    df = pd.read_parquet(path)

    logger.info(f"Loaded {len(df):,} transactions")
    return df


def load_l3_unified() -> pd.DataFrame:
    """Load L3 unified data for advanced analysis."""
    logger.info("Loading L3 unified data...")

    path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
    df = pd.read_parquet(path)

    logger.info(f"Loaded {len(df):,} records from L3 unified")
    return df


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare data with derived features."""
    logger.info("Preparing data with derived features...")

    df = df.copy()

    df['remaining_lease_years'] = df['remaining_lease_months'] / 12

    if 'floor_area_sqm' in df.columns and 'resale_price' in df.columns:
        df['price_psm'] = df['resale_price'] / df['floor_area_sqm']

    if 'lease_commence_date' in df.columns:
        df['year_of_completion'] = df['lease_commence_date'].astype(int)
        df['building_age'] = 2026 - df['year_of_completion']

    df = df[df['remaining_lease_years'].between(30, 99)]

    logger.info(f"Prepared data: {len(df):,} records")
    return df


def create_policy_bands(df: pd.DataFrame) -> pd.DataFrame:
    """Create policy-relevant lease bands for threshold analysis."""
    logger.info("Creating policy bands for threshold analysis...")

    df = df.copy()

    bins = [0, 30, 55, 60, 65, 70, 80, 90, 100]
    labels = ['<30 yrs', '30-55 yrs', '55-60 yrs', '60-65 yrs', '65-70 yrs', '70-80 yrs', '80-90 yrs', '90+ yrs']

    df['policy_band'] = pd.cut(
        df['remaining_lease_years'],
        bins=bins,
        labels=labels,
        include_lowest=True
    )

    for band in labels:
        count = (df['policy_band'] == band).sum()
        logger.info(f"  {band}: {count:,} transactions")

    return df


def analyze_policy_thresholds(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze price impacts at policy thresholds (60-year and 30-year marks).

    Key thresholds:
    - 60 years: CPF usage restricted if remaining lease < 60 years
    - 30 years: Bank loans become very difficult
    """
    logger.info("Analyzing policy threshold effects...")

    results = []

    for threshold in [60, 30]:
        above = df[df['remaining_lease_years'] > threshold]['price_psm'].dropna()
        below = df[df['remaining_lease_years'] <= threshold]['price_psm'].dropna()

        if len(above) > 0 and len(below) > 0:
            above_median = above.median()
            below_median = below.median()
            price_gap_pct = ((above_median - below_median) / above_median) * 100

            t_stat, p_value = stats.mannwhitneyu(above, below, alternative='greater')

            results.append({
                'threshold': threshold,
                'above_median_psm': above_median,
                'below_median_psm': below_median,
                'price_gap_pct': price_gap_pct,
                'above_n': len(above),
                'below_n': len(below),
                't_statistic': t_stat,
                'p_value': p_value
            })

            logger.info(f"\n{threshold}-Year Threshold Analysis:")
            logger.info(f"  Above ({threshold}+ years): ${above_median:,.0f}/PSM (n={len(above):,})")
            logger.info(f"  Below ({threshold} years): ${below_median:,.0f}/PSM (n={len(below):,})")
            logger.info(f"  Price Gap: {price_gap_pct:.1f}%")

    return pd.DataFrame(results)


def analyze_liquidity_tax(df: pd.DataFrame) -> pd.DataFrame:
    """
    Quantify the 'Liquidity Tax' between 61-year and 59-year leases.

    This measures the price gap imposed by financing rules.
    """
    logger.info("Analyzing liquidity tax (61 vs 59 year gap)...")

    df = df.copy()
    df['lease_rounded'] = df['remaining_lease_years'].round(0).astype(int)

    year_61 = df[df['lease_rounded'] == 61]['price_psm'].dropna()
    year_59 = df[df['lease_rounded'] == 59]['price_psm'].dropna()

    if len(year_61) > 0 and len(year_59) > 0:
        median_61 = year_61.median()
        median_59 = year_59.median()
        liquidity_tax = ((median_61 - median_59) / median_61) * 100

        logger.info(f"\nLiquidity Tax Analysis (61 vs 59 years):")
        logger.info(f"  61-year lease median: ${median_61:,.0f}/PSM (n={len(year_61)})")
        logger.info(f"  59-year lease median: ${median_59:,.0f}/PSM (n={len(year_59)})")
        logger.info(f"  Liquidity Tax: {liquidity_tax:.2f}%")

        return pd.DataFrame([{
            'year_61_median_psm': median_61,
            'year_59_median_psm': median_59,
            'liquidity_tax_pct': liquidity_tax,
            'year_61_n': len(year_61),
            'year_59_n': len(year_59)
        }])

    return pd.DataFrame()


def balas_curve_theoretical(lease_years: np.ndarray) -> np.ndarray:
    """
    Generate theoretical leasehold value curve (Bala's Curve approximation).

    Bala's Table represents standard valuation practice in Singapore.
    Based on typical actuarial leasehold discount rates.

    Approximation formula based on standard valuation tables:
    - Value decays slowly initially, accelerates near expiry
    - At 99 years: ~95-100% of freehold value
    - At 75 years: ~70-80% of freehold value
    - At 50 years: ~50-60% of freehold value
    """
    freehold_equivalent = 100

    normalized_lease = lease_years / 99.0

    value_pct = np.where(
        lease_years >= 90,
        95 + (lease_years - 90) * 0.5,
        np.where(
            lease_years >= 70,
            70 + (lease_years - 70) * 1.25,
            np.where(
                lease_years >= 50,
                50 + (lease_years - 50) * 1.0,
                30 + (lease_years - 30) * 1.0
            )
        )
    )

    value_pct = np.clip(value_pct, 30, 100)

    return value_pct


def analyze_balas_curve(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    Validate empirical data against theoretical Bala's Curve.

    Returns:
        DataFrame with comparison results
        Dictionary with deviation statistics
    """
    logger.info("Analyzing Bala's Curve validation...")

    df = df.copy()
    df['lease_rounded'] = df['remaining_lease_years'].round(0).astype(int)

    empirical = df.groupby('lease_rounded').agg({
        'price_psm': ['median', 'mean', 'count']
    }).reset_index()
    empirical.columns = ['lease_years', 'empirical_median_psm', 'empirical_mean_psm', 'n']

    empirical = empirical[empirical['n'] >= 30]

    theoretical_values = balas_curve_theoretical(empirical['lease_years'].values)

    baseline_median = empirical[empirical['lease_years'] >= 90]['empirical_median_psm'].median()
    empirical['empirical_value_pct'] = (empirical['empirical_median_psm'] / baseline_median) * 100
    empirical['theoretical_value_pct'] = theoretical_values
    empirical['deviation_pct'] = empirical['empirical_value_pct'] - empirical['theoretical_value_pct']

    avg_deviation = empirical['deviation_pct'].mean()
    max_deviation = empirical['deviation_pct'].abs().max()
    deviation_std = empirical['deviation_pct'].std()

    overvalued = empirical[empirical['deviation_pct'] > 5]
    undervalued = empirical[empirical['deviation_pct'] < -5]

    logger.info(f"\nBala's Curve Validation Results:")
    logger.info(f"  Average Deviation: {avg_deviation:+.2f}%")
    logger.info(f"  Max Deviation: {max_deviation:.2f}%")
    logger.info(f"  Deviation Std Dev: {deviation_std:.2f}%")

    if len(overvalued) > 0:
        logger.info(f"\nOvervalued lease years (>5% premium):")
        for _, row in overvalued.iterrows():
            logger.info(f"  {int(row['lease_years'])} yrs: +{row['deviation_pct']:.1f}% (n={row['n']})")

    if len(undervalued) > 0:
        logger.info(f"\nUndervalued lease years (>5% discount):")
        for _, row in undervalued.iterrows():
            logger.info(f"  {int(row['lease_years'])} yrs: {row['deviation_pct']:.1f}% (n={row['n']})")

    stats_dict = {
        'avg_deviation': avg_deviation,
        'max_deviation': max_deviation,
        'deviation_std': deviation_std,
        'n_years_analyzed': len(empirical),
        'overvalued_count': len(overvalued),
        'undervalued_count': len(undervalued)
    }

    return empirical, stats_dict


def run_hedonic_regression(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run hedonic regression to isolate lease effect controlling for other factors.

    Model:
    Price = β₀ + β₁(Lease) + β₂(FloorLevel) + β₃(DistToMRT) + β₄(Town) + ε
    """
    logger.info("Running hedonic regression to isolate lease effect...")

    df = df.copy()

    if 'storey_range' in df.columns:
        df['storey'] = df['storey_range'].str.extract(r'(\d+)').astype(float)
        df['storey'] = df['storey'].fillna(df['storey'].median())

    if 'dist_to_nearest_mrt' in df.columns:
        df['dist_to_mrt_km'] = df['dist_to_nearest_mrt'] / 1000
        df['dist_to_mrt_km'] = df['dist_to_mrt_km'].fillna(df['dist_to_mrt_km'].median())

    df = df.dropna(subset=['remaining_lease_years', 'price_psm', 'town'])

    df = pd.get_dummies(df, columns=['town'], prefix='town', drop_first=True, dtype=float)

    feature_cols = ['remaining_lease_years', 'floor_area_sqm', 'storey']
    dist_cols = [c for c in df.columns if c.startswith('town_')]

    all_features = feature_cols + dist_cols

    available_features = [c for c in all_features if c in df.columns]
    available_features = [c for c in available_features if c in df.columns]

    X = df[available_features].copy()

    for col in X.columns:
        if X[col].dtype == 'object':
            X[col] = pd.to_numeric(X[col], errors='coerce')

    X = X.fillna(X.median())

    X = sm.add_constant(X)

    y = df['price_psm']

    try:
        model = sm.OLS(y, X).fit()

        logger.info("\nHedonic Regression Results:")
        logger.info(f"R-squared: {model.rsquared:.4f}")
        logger.info(f"Adjusted R-squared: {model.rsquared_adj:.4f}")
        logger.info(f"\nLease Coefficient:")
        if 'remaining_lease_years' in model.params.index:
            lease_coef = model.params['remaining_lease_years']
            lease_pval = model.pvalues['remaining_lease_years']
            logger.info(f"  Coefficient: {lease_coef:.2f} SGD/PSM per year")
            logger.info(f"  P-value: {lease_pval:.4f}")
            logger.info(f"  Interpretation: Each additional year of lease adds ~{lease_coef:.0f} SGD/PSM")

        results_df = pd.DataFrame({
            'Variable': model.params.index,
            'Coefficient': model.params.values,
            'Std_Error': model.bse.values,
            'P_Value': model.pvalues.values,
            'CI_Lower': model.conf_int()[0].values,
            'CI_Upper': model.conf_int()[1].values
        })

        return results_df

    except Exception as e:
        logger.error(f"Regression failed: {e}")
        return pd.DataFrame()


def analyze_town_normalized_lease(df: pd.DataFrame) -> pd.DataFrame:
    """
    Town-specific normalization: Compare within same town.

    Compare 60-year vs 90-year leases within the same town.
    """
    logger.info("Analyzing town-normalized lease effects...")

    df = df.copy()

    df['lease_category'] = pd.cut(
        df['remaining_lease_years'],
        bins=[0, 65, 95, 100],
        labels=['short', 'fresh', 'very_fresh']
    )

    town_results = []

    for town in df['town'].unique():
        town_data = df[df['town'] == town]

        short = town_data[town_data['lease_category'] == 'short']['price_psm'].dropna()
        fresh = town_data[town_data['lease_category'] == 'fresh']['price_psm'].dropna()

        if len(short) > 10 and len(fresh) > 10:
            short_median = short.median()
            fresh_median = fresh.median()
            discount = ((fresh_median - short_median) / fresh_median) * 100

            town_results.append({
                'town': town,
                'short_lease_n': len(short),
                'short_lease_median_psm': short_median,
                'fresh_lease_n': len(fresh),
                'fresh_lease_median_psm': fresh_median,
                'discount_pct': discount
            })

    results_df = pd.DataFrame(town_results)
    results_df = results_df.sort_values('discount_pct', ascending=False)

    logger.info(f"\nTown-Normalized Lease Discounts:")
    for _, row in results_df.iterrows():
        logger.info(f"  {row['town']}: {row['discount_pct']:.1f}% (short: {row['short_lease_n']}, fresh: {row['fresh_lease_n']})")

    return results_df


def analyze_maturity_cliff(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deep-dive into the 70-80 year decay peak (Maturity Cliff).

    Investigate correlation with building age and maintenance costs.
    """
    logger.info("Analyzing Maturity Cliff (70-80 year band)...")

    df = df.copy()

    if 'year_of_completion' not in df.columns and 'lease_commence_date' in df.columns:
        df['year_of_completion'] = df['lease_commence_date'].astype(int)

    df['completion_decade'] = (df['year_of_completion'] // 10) * 10

    df['lease_decade'] = (df['remaining_lease_years'] // 10) * 10

    cliff_analysis = df.groupby('lease_decade').agg({
        'price_psm': ['median', 'count'],
        'year_of_completion': ['mean', 'min', 'max']
    }).reset_index()

    cliff_analysis.columns = ['lease_decade', 'median_psm', 'transaction_count', 'avg_completion_year', 'min_completion_year', 'max_completion_year']

    decade_70_80 = df[(df['remaining_lease_years'] >= 70) & (df['remaining_lease_years'] < 80)]
    other_decades = df[(df['remaining_lease_years'] < 70) | (df['remaining_lease_years'] >= 80)]

    cliff_prevalence = decade_70_80['flat_type'].value_counts(normalize=True)
    other_prevalence = other_decades['flat_type'].value_counts(normalize=True)

    flat_type_diff = cliff_prevalence.subtract(other_prevalence).dropna()

    logger.info(f"\n70-80 Year Band (Maturity Cliff) Analysis:")
    logger.info(f"  Transactions: {len(decade_70_80):,}")
    logger.info(f"  Median PSM: ${decade_70_80['price_psm'].median():,.0f}")
    logger.info(f"  Avg Completion Year: {decade_70_80['year_of_completion'].mean():.0f}")

    logger.info(f"\nFlat Type Distribution (vs other bands):")
    for flat_type, diff in flat_type_diff.sort_values().items():
        logger.info(f"  {flat_type}: {diff*100:+.1f}%")

    return cliff_analysis


def visualize_advanced_analysis(
    df: pd.DataFrame,
    balas_df: pd.DataFrame,
    hedonic_results: pd.DataFrame,
    town_results: pd.DataFrame,
    output_dir: Path
):
    """Create advanced visualizations."""
    logger.info("Creating advanced visualizations...")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (14, 8)

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    ax1 = axes[0, 0]
    if not balas_df.empty:
        ax1.plot(balas_df['lease_years'], balas_df['empirical_value_pct'], 'b-o', label='Empirical Data', markersize=4)
        ax1.plot(balas_df['lease_years'], balas_df['theoretical_value_pct'], 'r--', label="Bala's Curve (Theoretical)", linewidth=2)
        ax1.fill_between(balas_df['lease_years'], balas_df['theoretical_value_pct'], balas_df['empirical_value_pct'],
                        alpha=0.3, color='green', label='Overvaluation' if balas_df['empirical_value_pct'].mean() > balas_df['theoretical_value_pct'].mean() else 'Undervaluation')
        ax1.set_xlabel('Remaining Lease (Years)')
        ax1.set_ylabel('Value (% of Fresh Lease)')
        ax1.set_title("Bala's Curve Validation: Empirical vs Theoretical")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

    ax2 = axes[0, 1]
    if not town_results.empty:
        town_results_sorted = town_results.sort_values('discount_pct', ascending=True)
        colors = ['green' if x < 15 else 'orange' if x < 25 else 'red' for x in town_results_sorted['discount_pct']]
        ax2.barh(town_results_sorted['town'], town_results_sorted['discount_pct'], color=colors)
        ax2.set_xlabel('Discount (%)')
        ax2.set_ylabel('Town')
        ax2.set_title('Town-Normalized Lease Discount\n(Short vs Fresh Lease)')
        ax2.axvline(x=20, color='gray', linestyle='--', alpha=0.5)

    ax3 = axes[1, 0]
    lease_years = df['remaining_lease_years']
    price_psm = df['price_psm']
    scatter = ax3.scatter(lease_years, price_psm, alpha=0.1, s=1, c='blue')
    ax3.set_xlabel('Remaining Lease (Years)')
    ax3.set_ylabel('Price PSM (SGD)')
    ax3.set_title('Lease Decay Scatter Plot')
    ax3.set_xlim(30, 100)

    ax4 = axes[1, 1]
    if not hedonic_results.empty:
        lease_coef = hedonic_results[hedonic_results['Variable'] == 'remaining_lease_years']
        if not lease_coef.empty:
            coef = lease_coef['Coefficient'].values[0]
            ci_lower = lease_coef['CI_Lower'].values[0]
            ci_upper = lease_coef['CI_Upper'].values[0]
            ax4.bar(['Lease Effect'], [coef], yerr=[[coef - ci_lower], [ci_upper - coef]], capsize=10, color='steelblue')
            ax4.set_ylabel('Coefficient (SGD/PSM per year)')
            ax4.set_title(f'Hedonic Regression: Isolated Lease Effect\n(Controlled for floor, MRT, town)')
            ax4.axhline(y=0, color='gray', linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_dir / 'lease_decay_advanced_analysis.png', dpi=150)
    logger.info(f"Saved: {output_dir / 'lease_decay_advanced_analysis.png'}")
    plt.close()


def analyze_spline_arbitrage(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    Spline-based arbitrage analysis: Compare empirical market curve to Bala's theoretical.

    Uses restricted cubic splines to model actual market depreciation,
    then calculates "arbitrage gaps" where market prices deviate from theory.

    Returns:
        Tuple of (arbitrage opportunities DataFrame, summary statistics dict)
    """
    logger.info("=" * 70)
    logger.info("SPLINE-BASED ARBITRAGE ANALYSIS")
    logger.info("=" * 70)

    df = df.copy()
    df['lease_rounded'] = df['remaining_lease_years'].round(0).astype(int)

    # Group by lease year and calculate empirical median
    empirical = df.groupby('lease_rounded').agg({
        'price_psm': ['median', 'count']
    }).reset_index()
    empirical.columns = ['lease_years', 'empirical_median_psm', 'n']

    # Filter to sufficient sample size
    empirical = empirical[empirical['n'] >= 100]

    if len(empirical) < 10:
        logger.warning("Insufficient data for spline analysis")
        return pd.DataFrame(), {}

    logger.info(f"Fitting splines to {len(empirical)} lease-year points")

    # Create restricted cubic spline basis with 4 degrees of freedom
    # Using patsy for spline basis functions
    try:
        # Create B-spline basis (4 knots = 5 degrees of freedom - 1)
        from scipy.interpolate import BSpline, make_smoothing_spline

        # Fit smoothing spline to empirical data
        lease_range = empirical['lease_years'].values
        price_range = empirical['empirical_median_psm'].values

        # Use scipy's smoothing spline
        spline = make_smoothing_spline(lease_range, price_range, w=empirical['n'].values)

        # Generate predictions across full range
        lease_full_range = np.linspace(30, 99, 70)
        spline_predictions = spline(lease_full_range)

        # Normalize to 99-year baseline
        baseline_idx = np.where(lease_full_range >= 98)[0]
        if len(baseline_idx) > 0:
            baseline_value = spline_predictions[baseline_idx].mean()
            spline_normalized = (spline_predictions / baseline_value) * 100
        else:
            baseline_value = price_range.max()
            spline_normalized = (spline_predictions / baseline_value) * 100

        # Calculate theoretical Bala's curve for comparison
        theoretical = balas_curve_theoretical(lease_full_range)

        # Calculate arbitrage gap
        arbitrage_gap = spline_normalized - theoretical

        # Identify opportunities
        # Overvalued: Market > Theoretical + 5% (SELL signal)
        # Undervalued: Market < Theoretical - 5% (BUY signal)
        overvalued_mask = arbitrage_gap > 5
        undervalued_mask = arbitrage_gap < -5

        opportunities = pd.DataFrame({
            'lease_years': lease_full_range,
            'market_value_pct': spline_normalized,
            'theoretical_value_pct': theoretical,
            'arbitrage_gap_pct': arbitrage_gap,
            'signal': np.where(overvalued_mask, 'SELL',
                      np.where(undervalued_mask, 'BUY', 'HOLD'))
        })

        logger.info(f"\nArbitrage Opportunities Identified:")
        logger.info(f"  Overvalued (SELL): {overvalued_mask.sum()} lease years")
        logger.info(f"  Undervalued (BUY): {undervalued_mask.sum()} lease years")
        logger.info(f"  Fair value (HOLD): {(~overvalued_mask & ~undervalued_mask).sum()} lease years")

        # Top opportunities
        top_sell = opportunities[opportunities['signal'] == 'SELL'].nlargest(5, 'arbitrage_gap_pct')
        top_buy = opportunities[opportunities['signal'] == 'BUY'].nsmallest(5, 'arbitrage_gap_pct')

        if not top_sell.empty:
            logger.info(f"\nTop 5 OVERVALUED (Sell Opportunities):")
            for _, row in top_sell.iterrows():
                logger.info(f"  {int(row['lease_years'])} years: +{row['arbitrage_gap_pct']:.1f}% "
                          f"(Market {row['market_value_pct']:.1f}% vs Theory {row['theoretical_value_pct']:.1f}%)")

        if not top_buy.empty:
            logger.info(f"\nTop 5 UNDERVALUED (Buy Opportunities):")
            for _, row in top_buy.iterrows():
                logger.info(f"  {int(row['lease_years'])} years: {row['arbitrage_gap_pct']:.1f}% "
                          f"(Market {row['market_value_pct']:.1f}% vs Theory {row['theoretical_value_pct']:.1f}%)")

        # Summary statistics
        stats_dict = {
            'max_arbitrage_gap': arbitrage_gap.max(),
            'min_arbitrage_gap': arbitrage_gap.min(),
            'mean_arbitrage_gap': arbitrage_gap.mean(),
            'n_overvalued': overvalued_mask.sum(),
            'n_undervalued': undervalued_mask.sum(),
            'n_analyzed': len(opportunities)
        }

        return opportunities, stats_dict

    except Exception as e:
        logger.error(f"Spline fitting failed: {e}")
        return pd.DataFrame(), {}


def save_advanced_results(
    policy_thresholds: pd.DataFrame,
    liquidity_tax: pd.DataFrame,
    balas_df: pd.DataFrame,
    balas_stats: dict,
    hedonic_results: pd.DataFrame,
    town_results: pd.DataFrame,
    cliff_analysis: pd.DataFrame,
    output_dir: Path,
    arbitrage_df: pd.DataFrame = None,
    arbitrage_stats: dict = None
):
    """Save all advanced analysis results."""
    logger.info("Saving advanced analysis results...")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not policy_thresholds.empty:
        policy_thresholds.to_csv(output_dir / 'policy_threshold_analysis.csv', index=False)
        logger.info(f"Saved: {output_dir / 'policy_threshold_analysis.csv'}")

    if not liquidity_tax.empty:
        liquidity_tax.to_csv(output_dir / 'liquidity_tax_analysis.csv', index=False)
        logger.info(f"Saved: {output_dir / 'liquidity_tax_analysis.csv'}")

    if not balas_df.empty:
        balas_df.to_csv(output_dir / 'balas_curve_validation.csv', index=False)
        logger.info(f"Saved: {output_dir / 'balas_curve_validation.csv'}")

    with open(output_dir / 'balas_curve_stats.json', 'w') as f:
        import json
        json.dump(balas_stats, f, indent=2)
        logger.info(f"Saved: {output_dir / 'balas_curve_stats.json'}")

    if not hedonic_results.empty:
        hedonic_results.to_csv(output_dir / 'hedonic_regression_results.csv', index=False)
        logger.info(f"Saved: {output_dir / 'hedonic_regression_results.csv'}")

    if not town_results.empty:
        town_results.to_csv(output_dir / 'town_normalized_lease_analysis.csv', index=False)
        logger.info(f"Saved: {output_dir / 'town_normalized_lease_analysis.csv'}")

    if not cliff_analysis.empty:
        cliff_analysis.to_csv(output_dir / 'maturity_cliff_analysis.csv', index=False)
        logger.info(f"Saved: {output_dir / 'maturity_cliff_analysis.csv'}")

    if arbitrage_df is not None and not arbitrage_df.empty:
        arbitrage_df.to_csv(output_dir / 'lease_arbitrage_opportunities.csv', index=False)
        logger.info(f"Saved: {output_dir / 'lease_arbitrage_opportunities.csv'}")

    if arbitrage_stats:
        # Convert numpy types to native Python types for JSON serialization
        arbitrage_stats_json = {
            k: int(v) if isinstance(v, (np.integer, np.int64, np.int32)) else
               float(v) if isinstance(v, (np.floating, np.float64, np.float32)) else v
            for k, v in arbitrage_stats.items()
        }
        with open(output_dir / 'arbitrage_stats.json', 'w') as f:
            import json
            json.dump(arbitrage_stats_json, f, indent=2)
            logger.info(f"Saved: {output_dir / 'arbitrage_stats.json'}")


def main():
    """Main pipeline execution for advanced lease decay analysis."""

    logger.info("=" * 70)
    logger.info("Advanced HDB Lease Decay Analysis")
    logger.info("=" * 70)

    output_dir = Config.DATA_DIR / "analysis" / "lease_decay_advanced"

    hdb_df = load_hdb_data()
    hdb_df = prepare_data(hdb_df)
    hdb_df = create_policy_bands(hdb_df)

    logger.info("\n" + "=" * 70)
    logger.info("1. POLICY THRESHOLD ANALYSIS")
    logger.info("=" * 70)
    policy_thresholds = analyze_policy_thresholds(hdb_df)

    logger.info("\n" + "=" * 70)
    logger.info("2. LIQUIDITY TAX ANALYSIS")
    logger.info("=" * 70)
    liquidity_tax = analyze_liquidity_tax(hdb_df)

    logger.info("\n" + "=" * 70)
    logger.info("3. BALA'S CURVE VALIDATION")
    logger.info("=" * 70)
    balas_df, balas_stats = analyze_balas_curve(hdb_df)

    logger.info("\n" + "=" * 70)
    logger.info("4. HEDONIC REGRESSION (Isolating Lease Effect)")
    logger.info("=" * 70)
    hedonic_results = run_hedonic_regression(hdb_df)

    logger.info("\n" + "=" * 70)
    logger.info("5. TOWN-NORMALIZED LEASE ANALYSIS")
    logger.info("=" * 70)
    town_results = analyze_town_normalized_lease(hdb_df)

    logger.info("\n" + "=" * 70)
    logger.info("6. MATURITY CLIFF DEEP-DIVE (70-80 Year Band)")
    logger.info("=" * 70)
    cliff_analysis = analyze_maturity_cliff(hdb_df)

    logger.info("\n" + "=" * 70)
    logger.info("7. SPLINE-BASED ARBITRAGE ANALYSIS")
    logger.info("=" * 70)
    arbitrage_df, arbitrage_stats = analyze_spline_arbitrage(hdb_df)

    logger.info("\n" + "=" * 70)
    logger.info("VISUALIZATIONS")
    logger.info("=" * 70)
    visualize_advanced_analysis(hdb_df, balas_df, hedonic_results, town_results, output_dir)

    logger.info("\n" + "=" * 70)
    logger.info("SAVING RESULTS")
    logger.info("=" * 70)
    save_advanced_results(
        policy_thresholds,
        liquidity_tax,
        balas_df,
        balas_stats,
        hedonic_results,
        town_results,
        cliff_analysis,
        output_dir,
        arbitrage_df,
        arbitrage_stats
    )

    logger.info("\n" + "=" * 70)
    logger.info("Advanced Lease Decay Analysis Complete!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
