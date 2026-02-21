"""Regression Discontinuity in Time (RDiT) for Policy Analysis.

This script implements RDiT to detect policy effects by testing for "jumps"
(level changes) and "kinks" (slope changes) at policy cutoff dates.

Usage:
    uv run python scripts/analytics/analysis/causal/analyze_rd_policy_timing.py
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


# Regional classification
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
    """Classify planning area into CCR/RCR/OCR (case-insensitive)."""
    if pd.isna(planning_area):
        return 'Unknown'
    planning_area_norm = planning_area.title()
    ccr_normalized = [r.title() for r in CCR_REGIONS]
    rcr_normalized = [r.title() for r in RCR_REGIONS]
    if planning_area_norm in ccr_normalized:
        return 'CCR'
    elif planning_area_norm in rcr_normalized:
        return 'RCR'
    else:
        return 'OCR'


def prepare_rd_data(
    df: pd.DataFrame,
    policy_date: str,
    bandwidth_months: int = 6
) -> pd.DataFrame:
    """Prepare data for RDiT analysis around policy cutoff.

    Args:
        df: Transaction data with transaction_date
        policy_date: Policy cutoff date
        bandwidth_months: Months to include before/after policy (default 6)

    Returns:
        DataFrame with time_since_policy and post indicators
    """
    df = df.copy()
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])

    # Create running variable: months since policy (negative = before, positive = after)
    policy_dt = pd.to_datetime(policy_date)
    df['months_since_policy'] = (
        (df['transaction_date'].dt.year - policy_dt.year) * 12 +
        (df['transaction_date'].dt.month - policy_dt.month)
    )

    # Filter to bandwidth
    df = df[
        df['months_since_policy'].between(-bandwidth_months, bandwidth_months)
    ].copy()

    # Create post indicator
    df['post'] = (df['months_since_policy'] >= 0).astype(int)

    logger.info(f"RDiT Data Preparation (Bandwidth: ±{bandwidth_months} months):")
    logger.info(f"  Pre-policy: {len(df[df['post'] == 0]):,} transactions")
    logger.info(f"  Post-policy: {len(df[df['post'] == 1]):,} transactions")

    return df


def run_rd_jump(df: pd.DataFrame) -> dict:
    """Test for level change ("jump") at policy cutoff.

    Model: price = α + β*post + ε
    β captures the instantaneous price level change at policy date.

    Args:
        df: RDiT prepared data

    Returns:
        Dictionary with jump test results
    """
    logger.info("\n" + "=" * 60)
    logger.info("Testing for Level Change (Jump) at Policy Cutoff")
    logger.info("=" * 60)

    # Simple jump model
    formula = 'price ~ post'
    model = smf.ols(formula, data=df).fit()

    jump_coef = model.params['post']
    jump_se = model.bse['post']
    jump_pval = model.pvalues['post']
    jump_ci = model.conf_int().loc['post']

    pre_mean = df[df['post'] == 0]['price'].mean()
    post_mean = df[df['post'] == 1]['price'].mean()
    observed_jump = post_mean - pre_mean

    logger.info("\nJump Test Results:")
    logger.info(f"  Pre-policy mean: ${pre_mean:,.0f}")
    logger.info(f"  Post-policy mean: ${post_mean:,.0f}")
    logger.info(f"  Observed jump: ${observed_jump:,.0f}")
    logger.info(f"  Regression jump coefficient: ${jump_coef:,.0f}")
    logger.info(f"  Standard error: ${jump_se:,.0f}")
    logger.info(f"  95% CI: [${jump_ci[0]:,.0f}, ${jump_ci[1]:,.0f}]")
    logger.info(f"  P-value: {jump_pval:.4f}")

    if jump_pval < 0.05:
        logger.info("  ** SIGNIFICANT JUMP DETECTED **")
    else:
        logger.info("  No significant jump (p >= 0.05)")

    logger.info(f"  R-squared: {model.rsquared:.4f}")

    return {
        'test_type': 'jump',
        'jump_coef': jump_coef,
        'jump_se': jump_se,
        'jump_pval': jump_pval,
        'jump_ci_lower': jump_ci[0],
        'jump_ci_upper': jump_ci[1],
        'pre_mean': pre_mean,
        'post_mean': post_mean,
        'observed_jump': observed_jump,
        'r_squared': model.rsquared,
        'significant': jump_pval < 0.05
    }


def run_rd_kink(df: pd.DataFrame) -> dict:
    """Test for slope change ("kink") at policy cutoff.

    Model: price = α + β1*time + β2*post + β3*(post*time) + ε
    β3 captures the change in trend (slope) after policy.

    Args:
        df: RDiT prepared data

    Returns:
        Dictionary with kink test results
    """
    logger.info("\n" + "=" * 60)
    logger.info("Testing for Slope Change (Kink) at Policy Cutoff")
    logger.info("=" * 60)

    # Create interaction term for kink
    df['post_x_time'] = df['post'] * df['months_since_policy']

    # Kink model
    formula = 'price ~ months_since_policy + post + post_x_time'
    model = smf.ols(formula, data=df).fit()

    kink_coef = model.params.get('post_x_time', np.nan)
    kink_se = model.bse.get('post_x_time', np.nan)
    kink_pval = model.pvalues.get('post_x_time', np.nan)

    if not np.isnan(kink_coef):
        kink_ci = model.conf_int().loc['post_x_time']

        # Calculate pre and post slopes
        pre_slope = model.params['months_since_policy']
        post_slope = pre_slope + kink_coef
        slope_change_pct = (kink_coef / abs(pre_slope)) * 100 if pre_slope != 0 else np.nan

        logger.info("\nKink Test Results:")
        logger.info(f"  Pre-policy slope: ${pre_slope:,.0f}/month")
        logger.info(f"  Post-policy slope: ${post_slope:,.0f}/month")
        logger.info(f"  Slope change: ${kink_coef:,.0f}/month ({slope_change_pct:+.2f}%)")
        logger.info(f"  Standard error: ${kink_se:,.0f}")
        logger.info(f"  95% CI: [${kink_ci[0]:,.0f}, ${kink_ci[1]:,.0f}]")
        logger.info(f"  P-value: {kink_pval:.4f}")

        if kink_pval < 0.05:
            logger.info("  ** SIGNIFICANT KINK DETECTED **")
        else:
            logger.info("  No significant kink (p >= 0.05)")

        logger.info(f"  R-squared: {model.rsquared:.4f}")

        return {
            'test_type': 'kink',
            'pre_slope': pre_slope,
            'post_slope': post_slope,
            'kink_coef': kink_coef,
            'kink_se': kink_se,
            'kink_pval': kink_pval,
            'kink_ci_lower': kink_ci[0],
            'kink_ci_upper': kink_ci[1],
            'slope_change_pct': slope_change_pct,
            'r_squared': model.rsquared,
            'significant': kink_pval < 0.05
        }
    else:
        logger.error("Could not estimate kink coefficient")
        return {}


def run_rd_robustness(
    df: pd.DataFrame,
    bandwidths: list[int] = [3, 6, 9, 12]
) -> pd.DataFrame:
    """Test robustness across different bandwidths.

    Args:
        df: Full transaction data (not yet bandwidth-filtered)
        bandwidths: List of bandwidths to test

    Returns:
        DataFrame with results across bandwidths
    """
    logger.info("\n" + "=" * 60)
    logger.info("Robustness Analysis: Different Bandwidths")
    logger.info("=" * 60)

    results = []
    policy_date = df[df['post'] == 0]['transaction_date'].max() + pd.Timedelta(days=1)

    for bw in bandwidths:
        logger.info(f"\nBandwidth: ±{bw} months")

        # Prepare data with this bandwidth
        df_bw = prepare_rd_data(df, policy_date.strftime('%Y-%m-%d'), bandwidth_months=bw)

        if len(df_bw) < 100:
            logger.warning(f"Insufficient data ({len(df_bw)}), skipping")
            continue

        # Run jump and kink tests
        jump_result = run_rd_jump(df_bw)
        kink_result = run_rd_kink(df_bw)

        results.append({
            'bandwidth': bw,
            'n': len(df_bw),
            'jump_coef': jump_result.get('jump_coef', np.nan),
            'jump_pval': jump_result.get('jump_pval', np.nan),
            'jump_sig': jump_result.get('significant', False),
            'kink_coef': kink_result.get('kink_coef', np.nan),
            'kink_pval': kink_result.get('kink_pval', np.nan),
            'kink_sig': kink_result.get('significant', False)
        })

    results_df = pd.DataFrame(results)

    logger.info("\nRobustness Summary:")
    logger.info(f"{'Bandwidth':<12} {'N':<10} {'Jump':<15} {'Jump p':<10} {'Kink':<15} {'Kink p':<10}")
    logger.info("-" * 75)
    for _, row in results_df.iterrows():
        logger.info(
            f"±{int(row['bandwidth'])} months   "
            f"{int(row['n']):<10} "
            f"${row['jump_coef']:,.0f}    "
            f"{row['jump_pval']:.4f}   "
            f"${row['kink_coef']:,.0f}    "
            f"{row['kink_pval']:.4f}"
        )

    return results_df


def save_results(
    hdb_results: dict,
    robustness_df: pd.DataFrame,
    output_dir: Path
):
    """Save RDiT results to CSV files.

    Args:
        hdb_results: Main RDiT results for HDB
        robustness_df: Robustness analysis results
        output_dir: Output directory
    """
    logger.info("\n" + "=" * 60)
    logger.info("Saving RDiT Results")
    logger.info("=" * 60)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save main results
    if hdb_results:
        # Flatten nested dict
        hdb_flat = {}
        for key, value in hdb_results.items():
            if isinstance(value, dict):
                for subkey, subval in value.items():
                    hdb_flat[f"{key}_{subkey}"] = subval
            else:
                hdb_flat[key] = value

        hdb_df = pd.DataFrame([hdb_flat])
        hdb_path = output_dir / 'rdit_policy_timing.csv'
        hdb_df.to_csv(hdb_path, index=False)
        logger.info(f"Saved: {hdb_path}")

    # Save robustness results
    if not robustness_df.empty:
        robust_path = output_dir / 'rdit_robustness.csv'
        robustness_df.to_csv(robust_path, index=False)
        logger.info(f"Saved: {robust_path}")


def main():
    """Main RDiT analysis pipeline."""
    logger.info("\n" + "=" * 60)
    logger.info("REGRESSION DISCONTINUITY IN TIME (RDiT) ANALYSIS")
    logger.info("=" * 60 + "\n")

    output_dir = Config.DATA_DIR / "analysis" / "causal_rd_policy_timing"

    # Load HDB data
    logger.info("Loading L3 Unified Data (HDB)")
    try:
        df_all = load_parquet("housing_unified")
    except ValueError:
        l3_path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
        df_all = pd.read_parquet(l3_path)

    df_hdb = df_all[df_all['property_type'] == 'HDB'].copy()
    df_hdb['transaction_date'] = pd.to_datetime(df_hdb['transaction_date'])

    # Focus on period around Dec 2023 cooling measures
    policy_date = '2023-12-01'
    df_hdb = df_hdb[
        df_hdb['transaction_date'].between(
            '2022-06-01',  # 18 months before
            '2025-06-01'   # 18 months after
        )
    ].copy()

    logger.info(f"HDB transactions in analysis window: {len(df_hdb):,}")

    # Prepare RDiT data (6-month bandwidth)
    df_rd = prepare_rd_data(df_hdb, policy_date, bandwidth_months=6)

    if df_rd.empty:
        logger.error("No data available for RDiT analysis")
        return

    # Run jump test
    jump_results = run_rd_jump(df_rd)

    # Run kink test
    kink_results = run_rd_kink(df_rd)

    # Run robustness analysis
    robustness_df = run_rd_robustness(df_rd, bandwidths=[3, 6, 9, 12])

    # Save results
    save_results(
        {'jump': jump_results, 'kink': kink_results},
        robustness_df,
        output_dir
    )

    logger.info("\n" + "=" * 60)
    logger.info("RDiT ANALYSIS COMPLETE")
    logger.info("=" * 60)

    return {
        'jump': jump_results,
        'kink': kink_results,
        'robustness': robustness_df
    }


if __name__ == '__main__':
    main()
