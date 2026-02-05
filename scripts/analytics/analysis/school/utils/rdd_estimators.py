"""Regression Discontinuity Design utilities for causal inference."""

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from scipy import stats
from pathlib import Path
import logging
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class RDDEstimator:
    """
    Estimate causal effect of school proximity using RDD at 1km boundary.

    Natural experiment: Singapore primary school admission priority for <1km residents.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.cutoff = 1000  # 1km in meters

    def create_rdd_dataset(
        self,
        df: pd.DataFrame,
        bandwidth: int = 200,
        distance_col: str = 'nearest_schoolPRIMARY_dist'
    ):
        """
        Create RDD dataset focusing on properties around 1km boundary.

        Args:
            df: Full dataset
            bandwidth: Meters on each side of boundary (default: 200m)
            distance_col: Column with distance to nearest primary school

        Returns:
            DataFrame with treatment, running variable, and controls
        """
        logger.info(f"Creating RDD dataset with bandwidth={bandwidth}m")

        # Calculate running variable (distance - cutoff)
        df = df.copy()
        df['running_var'] = df[distance_col] - self.cutoff

        # Treatment: within 1km
        df['treated'] = (df[distance_col] <= self.cutoff).astype(int)

        # Filter to optimal bandwidth (around cutoff)
        lower_bound = -bandwidth
        upper_bound = bandwidth

        rdd_sample = df[
            (df['running_var'] >= lower_bound) &
            (df['running_var'] <= upper_bound)
        ].copy()

        logger.info(f"  RDD sample size: {len(rdd_sample):,}")
        logger.info(f"  Treated (≤1km): {(rdd_sample['treated']==1).sum():,}")
        logger.info(f"  Control (>1km): {(rdd_sample['treated']==0).sum():,}")

        return rdd_sample

    def estimate_rdd(
        self,
        rdd_df: pd.DataFrame,
        target_col: str = 'price_psf',
        control_cols: list = None
    ):
        """
        Estimate RDD treatment effect.

        Model: price = α + τ·treated + β·running_var + γ·(treated×running_var) + controls

        Args:
            rdd_df: RDD dataset from create_rdd_dataset()
            target_col: Outcome variable
            control_cols: List of control variables

        Returns:
            dict with coefficient estimates and diagnostics
        """
        logger.info("Estimating RDD treatment effect...")

        # Prepare features
        feature_cols = ['treated', 'running_var']

        # Add interaction term
        rdd_df = rdd_df.copy()
        rdd_df['treated_x_running'] = rdd_df['treated'] * rdd_df['running_var']
        feature_cols.append('treated_x_running')

        # Add controls if provided
        if control_cols:
            feature_cols.extend(control_cols)

        # Drop missing values
        rdd_df = rdd_df.dropna(subset=feature_cols + [target_col])

        X = rdd_df[feature_cols]
        y = rdd_df[target_col]

        # Fit OLS
        model = LinearRegression()
        model.fit(X, y)

        # Extract coefficients
        coef_df = pd.DataFrame({
            'feature': feature_cols,
            'coefficient': model.coef_,
            'abs_coef': np.abs(model.coef_)
        }).sort_values('abs_coef', ascending=False)

        # Treatment effect (tau) is coefficient on 'treated'
        tau_idx = feature_cols.index('treated')
        tau = model.coef_[tau_idx]

        # Calculate standard errors using statsmodels for inference
        try:
            import statsmodels.api as sm
            X_sm = sm.add_constant(X)
            model_sm = sm.OLS(y, X_sm).fit(cov_type='HC3')  # Robust SE

            tau_sm = model_sm.params['treated']
            tau_se = model_sm.bse['treated']
            tau_pval = model_sm.pvalues['treated']
            tau_ci_lower = model_sm.conf_int().loc['treated', 0]
            tau_ci_upper = model_sm.conf_int().loc['treated', 1]

            inference = {
                'tau': tau_sm,
                'se': tau_se,
                'p_value': tau_pval,
                'ci_lower': tau_ci_lower,
                'ci_upper': tau_ci_upper,
                'significant': tau_pval < 0.05
            }

            logger.info(f"  Treatment Effect (τ): ${tau_sm:.2f} PSF")
            logger.info(f"  Std Error: ${tau_se:.2f}")
            logger.info(f"  95% CI: [{tau_ci_lower:.2f}, {tau_ci_upper:.2f}]")
            logger.info(f"  P-value: {tau_pval:.4f}")
            logger.info(f"  Significant: {inference['significant']}")

        except ImportError:
            logger.warning("  statsmodels not available - skipping inference")
            inference = {'tau': tau, 'se': None, 'p_value': None}

        # R²
        y_pred = model.predict(X)
        r2 = 1 - np.sum((y - y_pred)**2) / np.sum((y - y.mean())**2)

        results = {
            'tau': tau,
            'r2': r2,
            'n': len(rdd_df),
            'n_treated': (rdd_df['treated'] == 1).sum(),
            'n_control': (rdd_df['treated'] == 0).sum(),
            'inference': inference,
            'coefficients': coef_df,
            'model': model
        }

        return results

    def test_covariate_balance(
        self,
        rdd_df: pd.DataFrame,
        covariate_cols: list
    ):
        """
        Test if covariates are balanced at the cutoff.

        Covariates should vary smoothly (no jump at 1km).
        """
        logger.info("Testing covariate balance...")

        balance_results = []

        for col in covariate_cols:
            if col not in rdd_df.columns:
                continue

            # Compare means of treated vs control
            treated_mean = rdd_df[rdd_df['treated'] == 1][col].mean()
            control_mean = rdd_df[rdd_df['treated'] == 0][col].mean()

            # T-test for difference
            treated_vals = rdd_df[rdd_df['treated'] == 1][col].dropna()
            control_vals = rdd_df[rdd_df['treated'] == 0][col].dropna()

            t_stat, p_val = stats.ttest_ind(treated_vals, control_vals)

            balance_results.append({
                'covariate': col,
                'treated_mean': treated_mean,
                'control_mean': control_mean,
                'diff': treated_mean - control_mean,
                'diff_pct': (treated_mean - control_mean) / control_mean * 100 if control_mean != 0 else np.nan,
                't_stat': t_stat,
                'p_value': p_val,
                'balanced': p_val > 0.05  # Not significantly different
            })

        balance_df = pd.DataFrame(balance_results)

        logger.info(f"  Balanced covariates: {balance_df['balanced'].sum()}/{len(balance_df)}")

        # Save
        output_path = self.output_dir / "rdd_covariate_balance.csv"
        balance_df.to_csv(output_path, index=False)
        logger.info(f"  Saved: {output_path}")

        return balance_df

    def bandwidth_sensitivity(
        self,
        df: pd.DataFrame,
        bandwidths: list = [100, 150, 200, 250, 300],
        target_col: str = 'price_psf',
        control_cols: list = None
    ):
        """
        Test RDD across multiple bandwidths to check robustness.
        """
        logger.info("Testing bandwidth sensitivity...")

        sensitivity_results = []

        for bw in bandwidths:
            logger.info(f"  Bandwidth: {bw}m")

            # Create RDD dataset
            rdd_df = self.create_rdd_dataset(df, bandwidth=bw)

            if len(rdd_df) < 100:
                logger.warning(f"    Insufficient data, skipping")
                continue

            # Estimate effect
            results = self.estimate_rdd(rdd_df, target_col, control_cols)

            sensitivity_results.append({
                'bandwidth': bw,
                'n': results['n'],
                'tau': results['tau'],
                'r2': results['r2'],
                'p_value': results['inference'].get('p_value'),
                'significant': results['inference'].get('significant', False)
            })

        sensitivity_df = pd.DataFrame(sensitivity_results)

        logger.info(f"  Tau range: ${sensitivity_df['tau'].min():.2f} - ${sensitivity_df['tau'].max():.2f} PSF")

        # Save
        output_path = self.output_dir / "rdd_bandwidth_sensitivity.csv"
        sensitivity_df.to_csv(output_path, index=False)
        logger.info(f"  Saved: {output_path}")

        return sensitivity_df

    def placebo_tests(
        self,
        df: pd.DataFrame,
        placebo_cutoffs: list = [800, 1200],
        target_col: str = 'price_psf',
        control_cols: list = None
    ):
        """
        Run placebo tests at fake cutoffs (should show no effect).

        If effect exists at fake cutoffs, RDD specification is invalid.
        """
        logger.info("Running placebo tests...")

        placebo_results = []

        for fake_cutoff in placebo_cutoffs:
            logger.info(f"  Placebo cutoff: {fake_cutoff}m")

            # Temporarily change cutoff
            original_cutoff = self.cutoff
            self.cutoff = fake_cutoff

            # Create RDD dataset
            rdd_df = self.create_rdd_dataset(df, bandwidth=200)

            if len(rdd_df) < 100:
                self.cutoff = original_cutoff
                continue

            # Estimate effect
            results = self.estimate_rdd(rdd_df, target_col, control_cols)

            placebo_results.append({
                'cutoff': fake_cutoff,
                'n': results['n'],
                'tau': results['tau'],
                'p_value': results['inference'].get('p_value'),
                'significant': results['inference'].get('significant', False)
            })

            # Reset cutoff
            self.cutoff = original_cutoff

        placebo_df = pd.DataFrame(placebo_results)

        logger.info(f"  Placebo effects should be null (insignificant)")

        # Save
        output_path = self.output_dir / "rdd_placebo_tests.csv"
        placebo_df.to_csv(output_path, index=False)
        logger.info(f"  Saved: {output_path}")

        return placebo_df

    def visualize_discontinuity(
        self,
        rdd_df: pd.DataFrame,
        target_col: str = 'price_psf',
        bandwidth: int = 200
    ):
        """
        Create visualization of price discontinuity at 1km boundary.
        """
        logger.info("Creating RDD visualization...")

        fig, ax = plt.subplots(figsize=(12, 6))

        # Bin the data for cleaner visualization
        bin_width = 20  # 20m bins
        rdd_df['distance_bin'] = (rdd_df['running_var'] // bin_width) * bin_width

        binned = rdd_df.groupby('distance_bin').agg({
            target_col: 'mean',
            'treated': 'first'
        }).reset_index()

        # Plot control and treated separately
        control = binned[binned['treated'] == 0]
        treated = binned[binned['treated'] == 1]

        ax.scatter(control['distance_bin'] + self.cutoff, control[target_col],
                   alpha=0.6, s=30, label='Control (>1km)', color='coral')
        ax.scatter(treated['distance_bin'] + self.cutoff, treated[target_col],
                   alpha=0.6, s=30, label='Treated (≤1km)', color='steelblue')

        # Add vertical line at cutoff
        ax.axvline(x=self.cutoff, color='red', linestyle='--', linewidth=2, label='1km Cutoff')

        # Add loess smoothing lines
        for data, label, color in [(control, 'Control', 'coral'), (treated, 'Treated', 'steelblue')]:
            if len(data) > 3:
                # Simple moving average
                window = max(3, len(data) // 5)
                smoothed = data[target_col].rolling(window, center=True, min_periods=1).mean()
                ax.plot(data['distance_bin'] + self.cutoff, smoothed,
                       color=color, linewidth=2, alpha=0.7)

        ax.set_xlabel('Distance to Primary School (m)', fontsize=12)
        ax.set_ylabel('Price PSF ($)', fontsize=12)
        ax.set_title('RDD: Price Discontinuity at 1km School Boundary', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        output_path = self.output_dir / "rdd_visualization.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"  Saved: {output_path}")
        plt.close()

    def save_main_results(self, results: dict):
        """Save main RDD effect estimate to CSV."""
        inference = results['inference']

        result_df = pd.DataFrame([{
            'metric': 'treatment_effect',
            'value': results['tau'],
            'std_error': inference.get('se'),
            'p_value': inference.get('p_value'),
            'ci_lower': inference.get('ci_lower'),
            'ci_upper': inference.get('ci_upper'),
            'significant': inference.get('significant', False),
            'r2': results['r2'],
            'n': results['n'],
            'n_treated': results['n_treated'],
            'n_control': results['n_control']
        }])

        output_path = self.output_dir / "rdd_main_effect.csv"
        result_df.to_csv(output_path, index=False)
        logger.info(f"Saved main results: {output_path}")

        return result_df
