"""Enhanced Causal Inference: Difference-in-Differences Analysis.

This script performs segmented DiD analysis for Condominium and HDB properties,
analyzing policy impacts with post-2021 data.

Usage:
    uv run python scripts/analytics/analysis/causal/analyze_causal_did_enhanced.py
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.core.config import Config
from scripts.core.data_helpers import load_parquet

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


# Regional classification for DiD analysis
CCR_REGIONS = [
    'Bukit Timah', 'Downtown Core', 'Marine Parade', 'Newton',
    'Orchard', 'Outram', 'River Valley', 'Rochor', 'Singapore River', 'Straits View'
]

RCR_REGIONS = [
    'Bishan', 'Bukit Merah', 'Geylang', 'Kallang', 'Lavender',
    'Marina East', 'Marina South', 'Novena', 'Queenstown',
    'Southern Islands', 'Tanglin', 'Toa Payoh'
]


def classify_region(planning_area: str) -> str:
    """Classify planning area into CCR/RCR/OCR.

    Uses case-insensitive matching to handle both 'Bukit Timah' and 'BUKIT TIMAH'.
    """
    if pd.isna(planning_area):
        return 'Unknown'

    # Normalize to title case for matching
    planning_area_norm = planning_area.title()

    # Normalize region lists to title case for comparison
    ccr_normalized = [r.title() for r in CCR_REGIONS]
    rcr_normalized = [r.title() for r in RCR_REGIONS]

    if planning_area_norm in ccr_normalized:
        return 'CCR'
    elif planning_area_norm in rcr_normalized:
        return 'RCR'
    else:
        return 'OCR'


def load_and_prepare_data(property_type: str | None = None, min_year: int = 2017) -> pd.DataFrame:
    """Load L3 unified data and filter by property type and date range.

    Args:
        property_type: 'HDB', 'Condominium', or None for all
        min_year: Minimum year to include (default 2017)

    Returns:
        Prepared DataFrame with region column and date filters
    """
    logger.info("=" * 60)
    logger.info(f"Loading L3 Unified Data ({property_type if property_type else 'All'})")
    logger.info("=" * 60)

    try:
        df = load_parquet("housing_unified")
    except ValueError:
        l3_path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
        logger.info(f"Loading from direct path: {l3_path}")
        df = pd.read_parquet(l3_path)

    if df.empty:
        logger.error("No data loaded")
        return pd.DataFrame()

    logger.info(f"Loaded {len(df):,} total transactions")

    # Filter by property type if specified
    if property_type:
        df = df[df['property_type'] == property_type].copy()
        logger.info(f"{property_type} transactions: {len(df):,}")

    # Filter by date
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])
    df = df[df['transaction_date'] >= f'{min_year}-01-01'].copy()
    logger.info(f"Post-{min_year} transactions: {len(df):,}")

    # Add region classification
    df['region'] = df['planning_area'].apply(classify_region)

    # Count by region
    region_counts = df['region'].value_counts()
    logger.info("\nTransaction Counts by Region:")
    for region in ['CCR', 'RCR', 'OCR', 'Unknown']:
        count = region_counts.get(region, 0)
        pct = count / len(df) * 100 if len(df) > 0 else 0
        logger.info(f"  {region}: {count:,} ({pct:.1f}%)")

    # Add temporal columns
    df['year'] = df['transaction_date'].dt.year
    df['month'] = df['transaction_date'].dt.to_period('M').astype(str)

    return df


def run_did_regression(
    df: pd.DataFrame,
    treatment_region: str = 'CCR',
    control_region: str = 'OCR',
    policy_date: str = '2020-07-01'
) -> dict:
    """Run Difference-in-Differences regression analysis.

    Args:
        df: Transaction data with region and transaction_date columns
        treatment_region: Region that received treatment (default 'CCR')
        control_region: Control region (default 'OCR')
        policy_date: Date of policy intervention

    Returns:
        Dictionary with DiD results
    """
    logger.info("=" * 60)
    logger.info(f"DiD Regression: {treatment_region} vs {control_region}")
    logger.info(f"Policy Date: {policy_date}")
    logger.info("=" * 60)

    # Filter to treatment and control regions
    df_filtered = df[df['region'].isin([treatment_region, control_region])].copy()

    if df_filtered.empty:
        logger.error(f"No data for regions: {treatment_region}, {control_region}")
        return {}

    # Create treatment and post indicators
    df_filtered['treatment'] = (df_filtered['region'] == treatment_region).astype(int)
    df_filtered['post'] = (df_filtered['transaction_date'] >= policy_date).astype(int)
    df_filtered['treatment_x_post'] = df_filtered['treatment'] * df_filtered['post']

    # Sample size check
    n_treatment_pre = len(df_filtered[
        (df_filtered['treatment'] == 1) & (df_filtered['post'] == 0)
    ])
    n_treatment_post = len(df_filtered[
        (df_filtered['treatment'] == 1) & (df_filtered['post'] == 1)
    ])
    n_control_pre = len(df_filtered[
        (df_filtered['treatment'] == 0) & (df_filtered['post'] == 0)
    ])
    n_control_post = len(df_filtered[
        (df_filtered['treatment'] == 0) & (df_filtered['post'] == 1)
    ])

    logger.info("\nSample Sizes:")
    logger.info(f"  Treatment ({treatment_region}) Pre: {n_treatment_pre:,}")
    logger.info(f"  Treatment ({treatment_region}) Post: {n_treatment_post:,}")
    logger.info(f"  Control ({control_region}) Pre: {n_control_pre:,}")
    logger.info(f"  Control ({control_region}) Post: {n_control_post:,}")

    # Check minimum sample size (require at least 100 per group)
    min_sample = 100
    if min(n_treatment_pre, n_treatment_post, n_control_pre, n_control_post) < min_sample:
        logger.warning(f"Insufficient sample size (<{min_sample}) for reliable DiD")
        return {}

    # Run DiD regression
    formula = 'price ~ treatment + post + treatment_x_post'
    model = smf.ols(formula, data=df_filtered).fit()

    # Extract results
    did_coef = model.params.get('treatment_x_post', np.nan)
    did_se = model.bse.get('treatment_x_post', np.nan)
    did_pval = model.pvalues.get('treatment_x_post', np.nan)

    # Calculate confidence intervals
    conf_int = model.conf_int()
    ci_lower = conf_int.loc['treatment_x_post', 0] if 'treatment_x_post' in conf_int.index else np.nan
    ci_upper = conf_int.loc['treatment_x_post', 1] if 'treatment_x_post' in conf_int.index else np.nan

    # Calculate group means
    treatment_pre = df_filtered[
        (df_filtered['treatment'] == 1) & (df_filtered['post'] == 0)
    ]['price'].median()
    treatment_post = df_filtered[
        (df_filtered['treatment'] == 1) & (df_filtered['post'] == 1)
    ]['price'].median()
    control_pre = df_filtered[
        (df_filtered['treatment'] == 0) & (df_filtered['post'] == 0)
    ]['price'].median()
    control_post = df_filtered[
        (df_filtered['treatment'] == 0) & (df_filtered['post'] == 1)
    ]['price'].median()

    # Manual DiD calculation (for verification)
    treatment_change = treatment_post - treatment_pre
    control_change = control_post - control_pre
    did_manual = treatment_change - control_change

    logger.info("\nDiD Regression Results:")
    logger.info(f"  Treatment ({treatment_region}) Pre: ${treatment_pre:,.0f}")
    logger.info(f"  Treatment ({treatment_region}) Post: ${treatment_post:,.0f}")
    logger.info(f"  Treatment Change: ${treatment_change:,.0f} ({treatment_change/treatment_pre*100:+.2f}%)")
    logger.info(f"  Control ({control_region}) Pre: ${control_pre:,.0f}")
    logger.info(f"  Control ({control_region}) Post: ${control_post:,.0f}")
    logger.info(f"  Control Change: ${control_change:,.0f} ({control_change/control_pre*100:+.2f}%)")
    logger.info(f"\n  DiD Estimate: ${did_coef:,.0f}")
    logger.info(f"  Manual DiD: ${did_manual:,.0f}")
    logger.info(f"  Standard Error: ${did_se:,.0f}")
    logger.info(f"  95% CI: [${ci_lower:,.0f}, ${ci_upper:,.0f}]")
    logger.info(f"  P-value: {did_pval:.4f}")

    # Statistical significance
    if did_pval < 0.01:
        sig = '*** (p < 0.01)'
    elif did_pval < 0.05:
        sig = '** (p < 0.05)'
    elif did_pval < 0.10:
        sig = '* (p < 0.10)'
    else:
        sig = 'ns (not significant)'
    logger.info(f"  Significance: {sig}")

    # Model fit
    logger.info(f"\n  R-squared: {model.rsquared:.4f}")
    logger.info(f"  N: {len(df_filtered):,}")

    return {
        'treatment_region': treatment_region,
        'control_region': control_region,
        'policy_date': policy_date,
        'n_treatment_pre': n_treatment_pre,
        'n_treatment_post': n_treatment_post,
        'n_control_pre': n_control_pre,
        'n_control_post': n_control_post,
        'treatment_pre_price': treatment_pre,
        'treatment_post_price': treatment_post,
        'control_pre_price': control_pre,
        'control_post_price': control_post,
        'treatment_change': treatment_change,
        'control_change': control_change,
        'did_estimate': did_coef,
        'did_manual': did_manual,
        'std_error': did_se,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'p_value': did_pval,
        'significance': sig,
        'r_squared': model.rsquared,
        'n_total': len(df_filtered)
    }


def run_hdb_temporal_analysis(
    df: pd.DataFrame,
    policy_date: str = '2023-12-01'
) -> dict:
    """Run temporal analysis for HDB (all in OCR, so CCR vs OCR DiD not applicable).

    Args:
        df: HDB transaction data
        policy_date: Date of policy intervention

    Returns:
        Dictionary with temporal comparison results
    """
    logger.info("=" * 60)
    logger.info(f"HDB Temporal Analysis (pre/post {policy_date})")
    logger.info("=" * 60)

    # Create post indicator
    df['post'] = (df['transaction_date'] >= policy_date).astype(int)

    # Sample sizes
    n_pre = len(df[df['post'] == 0])
    n_post = len(df[df['post'] == 1])

    logger.info("\nSample Sizes:")
    logger.info(f"  Pre-policy: {n_pre:,}")
    logger.info(f"  Post-policy: {n_post:,}")

    # Calculate price changes
    pre_price = df[df['post'] == 0]['price'].median()
    post_price = df[df['post'] == 1]['price'].median()
    price_change = post_price - pre_price
    price_change_pct = (price_change / pre_price) * 100

    # Volume changes
    pre_volume = n_pre
    post_volume = n_post
    volume_change_pct = ((post_volume - pre_volume) / pre_volume) * 100

    # YoY growth rates
    yearly = df.groupby('year')['price'].median()
    yoy_growth = yearly.pct_change() * 100

    logger.info("\nPrice Analysis:")
    logger.info(f"  Pre-policy median: ${pre_price:,.0f}")
    logger.info(f"  Post-policy median: ${post_price:,.0f}")
    logger.info(f"  Price change: ${price_change:,.0f} ({price_change_pct:+.2f}%)")

    logger.info("\nVolume Analysis:")
    logger.info(f"  Pre-policy volume: {pre_volume:,}")
    logger.info(f"  Post-policy volume: {post_volume:,}")
    logger.info(f"  Volume change: {volume_change_pct:+.2f}%")

    logger.info("\nYoY Growth Rates:")
    for year, growth in yoy_growth.items():
        if not pd.isna(growth) and year >= 2022:
            logger.info(f"  {int(year)}: {growth:+.2f}% (median: ${yearly[year]:,.0f})")

    return {
        'policy_date': policy_date,
        'n_pre': n_pre,
        'n_post': n_post,
        'pre_price': pre_price,
        'post_price': post_price,
        'price_change': price_change,
        'price_change_pct': price_change_pct,
        'volume_change_pct': volume_change_pct,
        'yoy_growth': yoy_growth.to_dict()
    }


def save_results(
    condo_results: dict,
    hdb_results: dict,
    output_dir: Path
):
    """Save DiD results to CSV files.

    Args:
        condo_results: DiD results for condominium
        hdb_results: Temporal analysis results for HDB
        output_dir: Output directory for CSV files
    """
    logger.info("=" * 60)
    logger.info("Saving Results")
    logger.info("=" * 60)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save Condo DiD results
    if condo_results:
        condo_df = pd.DataFrame([condo_results])
        condo_path = output_dir / 'causal_did_condo.csv'
        condo_df.to_csv(condo_path, index=False)
        logger.info(f"Saved: {condo_path}")

    # Save HDB temporal results
    if hdb_results:
        hdb_flat = {
            'policy_date': hdb_results['policy_date'],
            'n_pre': hdb_results['n_pre'],
            'n_post': hdb_results['n_post'],
            'pre_price': hdb_results['pre_price'],
            'post_price': hdb_results['post_price'],
            'price_change': hdb_results['price_change'],
            'price_change_pct': hdb_results['price_change_pct'],
            'volume_change_pct': hdb_results['volume_change_pct']
        }
        hdb_df = pd.DataFrame([hdb_flat])
        hdb_path = output_dir / 'causal_did_hdb.csv'
        hdb_df.to_csv(hdb_path, index=False)
        logger.info(f"Saved: {hdb_path}")


def main():
    """Main analysis pipeline for enhanced causal DiD analysis."""
    logger.info("\n" + "=" * 60)
    logger.info("ENHANCED CAUSAL INFERENCE: DIFFERENCE-IN-DIFFERENCES")
    logger.info("=" * 60 + "\n")

    output_dir = Config.DATA_DIR / "analysis" / "causal_did_enhanced"

    # 1. Condominium DiD Analysis (CCR vs OCR, Sep 2022 ABSD changes)
    # Note: L3 condo data starts 2021-01-01, so July 2020 policy not applicable
    # Using Sep 2022 ABSD hike for foreigners as alternative policy event
    logger.info("\n### PART 1: CONDOMINIUM DiD ANALYSIS ###\n")
    condo_df = load_and_prepare_data(property_type='Condominium', min_year=2021)

    if not condo_df.empty:
        condo_results = run_did_regression(
            condo_df,
            treatment_region='CCR',
            control_region='OCR',
            policy_date='2022-09-01'  # Sep 2022 ABSD changes
        )
    else:
        logger.error("No condominium data available")
        condo_results = {}

    # 2. HDB Temporal Analysis (pre/post Dec 2023 cooling measures)
    logger.info("\n### PART 2: HDB TEMPORAL ANALYSIS ###\n")
    hdb_df = load_and_prepare_data(property_type='HDB', min_year=2022)

    if not hdb_df.empty:
        hdb_results = run_hdb_temporal_analysis(
            hdb_df,
            policy_date='2023-12-01'
        )
    else:
        logger.error("No HDB data available")
        hdb_results = {}

    # 3. Save results
    save_results(condo_results, hdb_results, output_dir)

    logger.info("\n" + "=" * 60)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 60)

    return {
        'condo': condo_results,
        'hdb': hdb_results
    }


if __name__ == '__main__':
    main()
