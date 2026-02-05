"""
Regression Discontinuity Design (RDD) Analysis for School Impact

Uses Singapore's primary school admission priority cutoff (1km) as a natural experiment
to estimate the causal effect of school proximity on housing prices.

Natural Experiment:
- Singapore primary schools give admission priority to residents living within 1km
- Creates sharp discontinuity in treatment at 1km boundary
- Properties just inside vs outside 1km should be similar except for school access

RDD Framework:
- Running variable: distance to nearest primary school
- Cutoff: 1000m (1km)
- Treatment: within 1km (priority admission)
- Bandwidth: 200m on each side (focus on local variation)

Output:
- Causal estimate of school proximity effect
- Validation tests (covariate balance, bandwidth sensitivity, placebo tests)
- Visualization of price discontinuity
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
import logging
import warnings
warnings.filterwarnings('ignore')

from scripts.analytics.analysis.school.utils.rdd_estimators import RDDEstimator

# Setup paths
DATA_PATH = Path("data/pipeline/L3/housing_unified.parquet")
OUTPUT_DIR = Path("data/analysis/school_rdd")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_and_filter_data():
    """Load housing data and filter to relevant sample."""
    print("=" * 80)
    print("RDD CAUSAL INFERENCE ANALYSIS - SCHOOL PROXIMITY EFFECT")
    print("=" * 80)

    print("\nLoading data...")
    df = pd.read_parquet(DATA_PATH)
    print(f"  Full dataset: {len(df):,} records")

    # Filter to recent transactions (2021+)
    df = df[df['year'] >= 2021].copy()
    print(f"  Filtered to 2021+: {len(df):,} records")

    # Filter to properties within 2km of primary schools
    df = df[df['nearest_schoolPRIMARY_dist'] <= 2000].copy()
    print(f"  Within 2km of primary school: {len(df):,} records")

    # Drop missing prices
    df = df.dropna(subset=['price_psf'])
    print(f"  Valid prices: {len(df):,} records")

    print("\nDistance distribution:")
    print(f"  Mean: {df['nearest_schoolPRIMARY_dist'].mean():.0f}m")
    print(f"  Median: {df['nearest_schoolPRIMARY_dist'].median():.0f}m")
    print(f"  Within 1km: {(df['nearest_schoolPRIMARY_dist'] <= 1000).sum():,} records")

    return df


def main():
    """Run RDD analysis pipeline."""

    # Step 1: Load data
    df = load_and_filter_data()

    # Step 2: Initialize RDD estimator
    print("\n" + "=" * 80)
    print("INITIALIZING RDD ESTIMATOR")
    print("=" * 80)

    estimator = RDDEstimator(output_dir=OUTPUT_DIR)

    # Step 3: Create RDD dataset with optimal bandwidth
    print("\n" + "=" * 80)
    print("CREATING RDD DATASET")
    print("=" * 80)

    bandwidth = 200  # 200m on each side of 1km boundary
    rdd_df = estimator.create_rdd_dataset(
        df,
        bandwidth=bandwidth,
        distance_col='nearest_schoolPRIMARY_dist'
    )

    # Step 4: Estimate treatment effect
    print("\n" + "=" * 80)
    print("ESTIMATING CAUSAL EFFECT")
    print("=" * 80)

    # Control variables (property characteristics that should vary smoothly at cutoff)
    control_cols = [
        'floor_area_sqm',
        'remaining_lease_months',
        'year',
        'dist_to_nearest_mrt',
        'dist_to_nearest_hawker'
    ]

    # Filter to available controls
    available_controls = [col for col in control_cols if col in rdd_df.columns]
    print(f"\nControl variables: {available_controls}")

    results = estimator.estimate_rdd(
        rdd_df,
        target_col='price_psf',
        control_cols=available_controls
    )

    # Step 5: Save main results
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)

    estimator.save_main_results(results)

    # Step 6: Validation tests
    print("\n" + "=" * 80)
    print("VALIDATION TESTS")
    print("=" * 80)

    # 6a. Covariate balance test
    print("\n[Covariate Balance Test]")
    print("Testing that covariates are balanced at the cutoff...")
    balance_df = estimator.test_covariate_balance(
        rdd_df,
        covariate_cols=available_controls
    )

    print("\nCovariate Balance Results:")
    print(balance_df.to_string(index=False))

    # 6b. Bandwidth sensitivity
    print("\n[Bandwidth Sensitivity Test]")
    print("Testing robustness across different bandwidths...")
    sensitivity_df = estimator.bandwidth_sensitivity(
        df,
        bandwidths=[100, 150, 200, 250, 300],
        target_col='price_psf',
        control_cols=available_controls
    )

    print("\nBandwidth Sensitivity Results:")
    print(sensitivity_df.to_string(index=False))

    # 6c. Placebo tests
    print("\n[Placebo Tests]")
    print("Testing for fake cutoffs (should show no effect)...")
    placebo_df = estimator.placebo_tests(
        df,
        placebo_cutoffs=[800, 1200],
        target_col='price_psf',
        control_cols=available_controls
    )

    print("\nPlacebo Test Results:")
    print(placebo_df.to_string(index=False))

    # Step 7: Visualization
    print("\n" + "=" * 80)
    print("CREATING VISUALIZATION")
    print("=" * 80)

    estimator.visualize_discontinuity(
        rdd_df,
        target_col='price_psf',
        bandwidth=bandwidth
    )

    # Step 8: Summary
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)

    inference = results['inference']

    print("\n📊 CAUSAL EFFECT ESTIMATE")
    print(f"  Treatment Effect (τ): ${inference['tau']:.2f} PSF")
    print(f"  Standard Error: ${inference['se']:.2f}" if inference['se'] else "  Standard Error: N/A")
    print(f"  95% CI: [{inference['ci_lower']:.2f}, {inference['ci_upper']:.2f}]"
          if inference['ci_lower'] else "  95% CI: N/A")
    print(f"  P-value: {inference['p_value']:.4f}" if inference['p_value'] else "  P-value: N/A")
    print(f"  Statistically Significant: {'✓ YES' if inference.get('significant') else '✗ NO'}")

    print(f"\n📈 MODEL FIT")
    print(f"  R²: {results['r2']:.4f}")
    print(f"  Sample Size: {results['n']:,}")
    print(f"  Treated (≤1km): {results['n_treated']:,}")
    print(f"  Control (>1km): {results['n_control']:,}")

    print("\n✅ VALIDATION CHECKS")
    n_balanced = balance_df['balanced'].sum()
    n_total = len(balance_df)
    print(f"  Covariate Balance: {n_balanced}/{n_total} balanced")
    print(f"  Bandwidth Sensitivity: {len(sensitivity_df)} bandwidths tested")
    print(f"  Placebo Tests: {len(placebo_df)} fake cutoffs tested")

    placebo_sig = placebo_df['significant'].sum() if 'significant' in placebo_df.columns else 0
    print(f"  Placebo Effects: {placebo_sig} significant (should be 0)")

    print("\n💡 INTERPRETATION")
    if inference.get('significant'):
        print(f"  Properties within 1km of primary schools command a")
        print(f"  premium of ${inference['tau']:.2f} PSF compared to similar")
        print(f"  properties just outside 1km (p={inference['p_value']:.4f}).")
        print(f"\n  This effect is CAUSAL, not just correlation, because:")
        print(f"  - RDD exploits sharp admission priority cutoff at 1km")
        print(f"  - Properties just inside/outside cutoff are similar")
        print(f"  - Only difference is school admission priority")
    else:
        print(f"  No statistically significant discontinuity detected at 1km.")
        print(f"  School proximity may not directly drive price differences.")

    print("\n📁 OUTPUT FILES")
    print(f"  Main results: {OUTPUT_DIR / 'rdd_main_effect.csv'}")
    print(f"  Covariate balance: {OUTPUT_DIR / 'rdd_covariate_balance.csv'}")
    print(f"  Bandwidth sensitivity: {OUTPUT_DIR / 'rdd_bandwidth_sensitivity.csv'}")
    print(f"  Placebo tests: {OUTPUT_DIR / 'rdd_placebo_tests.csv'}")
    print(f"  Visualization: {OUTPUT_DIR / 'rdd_visualization.png'}")

    print("\n" + "=" * 80)
    print("RDD ANALYSIS COMPLETE")
    print("=" * 80)

    return results


if __name__ == "__main__":
    main()
