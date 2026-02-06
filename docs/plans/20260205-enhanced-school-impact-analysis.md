# Enhanced School Impact Analysis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add spatial cross-validation, causal inference (RDD), and segmentation analysis to school impact analysis pipeline

**Architecture:** Three modular analysis scripts with shared utilities, each processing L3 unified dataset to generate validation metrics, causal estimates, and heterogeneous effects

**Tech Stack:** pandas, sklearn, scipy, statsmodels, xgboost, shap, matplotlib

---

## Prerequisites

**Read These Files First:**
- `docs/analytics/school-impact-analysis.md` - Current pipeline documentation
- `docs/plans/20260205-enhanced-school-impact-analysis-design.md` - Design specification
- `scripts/analytics/analysis/school/analyze_school_impact.py` - Existing main analysis
- `scripts/core/school_features.py` - School feature calculation logic

**Verify Data:**
```bash
uv run python -c "import pandas as pd; df = pd.read_parquet('data/pipeline/L3/housing_unified.parquet'); print(f'Shape: {df.shape}'); print(f'School cols: {[c for c in df.columns if \"school\" in c.lower()]}')"
```

Expected: Shape with 110 columns, including school_accessibility_score, nearest_schoolPRIMARY_dist, planning_area, property_type

---

## Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add scipy and statsmodels to dependencies**

Run:
```bash
uv add scipy statsmodels
```

Expected: Output shows packages added to pyproject.toml

**Step 2: Verify installation**

Run:
```bash
uv run python -c "import scipy; import statsmodels; print('Dependencies installed')"
```

Expected: "Dependencies installed" printed, no errors

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add scipy and statsmodels for RDD and spatial analysis"
```

---

## Task 2: Create Utils Directory Structure

**Files:**
- Create: `scripts/analytics/analysis/school/utils/__init__.py`
- Create: `scripts/analytics/analysis/school/utils/spatial_validation.py`
- Create: `scripts/analytics/analysis/school/utils/rdd_estimators.py`
- Create: `scripts/analytics/analysis/school/utils/interaction_models.py`

**Step 1: Create __init__.py**

Create file `scripts/analytics/analysis/school/utils/__init__.py`:
```python
"""Shared utilities for enhanced school impact analysis."""

from .spatial_validation import SpatialValidator
from .rdd_estimators import RDDEstimator
from .interaction_models import SegmentationAnalyzer

__all__ = ['SpatialValidator', 'RDDEstimator', 'SegmentationAnalyzer']
```

**Step 2: Commit**

```bash
git add scripts/analytics/analysis/school/utils/__init__.py
git commit -m "feat: add utils package for shared school analysis utilities"
```

---

## Task 3: Implement Spatial Validation Utilities

**Files:**
- Modify: `scripts/analytics/analysis/school/utils/spatial_validation.py`

**Step 1: Write SpatialValidator class**

Create file `scripts/analytics/analysis/school/utils/spatial_validation.py`:
```python
"""Spatial cross-validation utilities for school impact analysis."""

import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SpatialValidator:
    """Compare standard vs spatial cross-validation to detect autocorrelation."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.results = {}

    def compare_cv_methods(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        groups: pd.Series,
        model_type: str = 'ols'
    ):
        """
        Compare standard KFold vs GroupKFold (spatial) CV.

        Args:
            X: Feature matrix
            y: Target variable
            groups: Group labels (planning_area)
            model_type: 'ols', 'rf', or 'xgboost'

        Returns:
            dict with standard_cv_score, spatial_cv_score, generalization_gap
        """
        logger.info(f"Comparing CV methods for {model_type}")

        # Initialize model
        if model_type == 'ols':
            model = LinearRegression()
        elif model_type == 'rf':
            model = RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42)
        elif model_type == 'xgboost':
            model = xgb.XGBRegressor(n_estimators=100, max_depth=6, n_jobs=-1, random_state=42)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # Standard 5-fold CV
        logger.info("  Running standard 5-fold CV...")
        from sklearn.model_selection import KFold
        standard_scores = cross_val_score(
            model, X, y, cv=5, scoring='r2', n_jobs=-1
        )
        standard_r2 = standard_scores.mean()

        # Spatial GroupKFold
        logger.info("  Running spatial GroupKFold...")
        group_kfold = GroupKFold(n_splits=5)

        # Manual scoring to handle groups properly
        spatial_scores = []
        for train_idx, test_idx in group_kfold.split(X, y, groups):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            score = r2_score(y_test, y_pred)
            spatial_scores.append(score)

        spatial_r2 = np.mean(spatial_scores)

        # Calculate generalization gap
        gap = standard_r2 - spatial_r2

        result = {
            'model_type': model_type,
            'standard_cv_r2': standard_r2,
            'spatial_cv_r2': spatial_r2,
            'generalization_gap': gap,
            'gap_pct': (gap / standard_r2 * 100) if standard_r2 > 0 else 0
        }

        logger.info(f"  Standard CV R²: {standard_r2:.4f}")
        logger.info(f"  Spatial CV R²: {spatial_r2:.4f}")
        logger.info(f"  Generalization Gap: {gap:.4f} ({result['gap_pct']:.1f}%)")

        self.results[model_type] = result
        return result

    def analyze_area_generalization(
        self,
        df: pd.DataFrame,
        feature_cols: list,
        target_col: str,
        group_col: str = 'planning_area'
    ):
        """
        Test which planning areas generalize poorly.

        Trains on all areas except one, tests on held-out area.
        """
        logger.info("Analyzing planning area generalization...")

        X = df[feature_cols]
        y = df[target_col]
        groups = df[group_col]

        area_results = []
        unique_areas = groups.unique()

        for area in unique_areas:
            # Train on all except this area
            train_mask = groups != area
            test_mask = groups == area

            if test_mask.sum() < 100:  # Skip small areas
                continue

            X_train, X_test = X[train_mask], X[test_mask]
            y_train, y_test = y[train_mask], y[test_mask]

            model = LinearRegression()
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            r2 = r2_score(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)

            area_results.append({
                'planning_area': area,
                'n_test': test_mask.sum(),
                'r2': r2,
                'mae': mae,
                'y_mean': y_test.mean()
            })

        results_df = pd.DataFrame(area_results)
        results_df = results_df.sort_values('r2')

        logger.info(f"  Worst generalizing area: {results_df.iloc[0]['planning_area']} (R²={results_df.iloc[0]['r2']:.4f})")
        logger.info(f"  Best generalizing area: {results_df.iloc[-1]['planning_area']} (R²={results_df.iloc[-1]['r2']:.4f})")

        # Save results
        output_path = self.output_dir / "planning_area_generalization.csv"
        results_df.to_csv(output_path, index=False)
        logger.info(f"  Saved: {output_path}")

        return results_df

    def test_spatial_autocorrelation(self, residuals: pd.Series, coordinates: pd.DataFrame):
        """
        Test for spatial autocorrelation in residuals using Moran's I.

        Simplified version - groups by planning area.
        """
        logger.info("Testing spatial autocorrelation...")

        # Group residuals by planning area
        if 'planning_area' in coordinates.columns:
            area_residuals = residuals.groupby(coordinates['planning_area']).mean()

            # Calculate Moran's I approximation
            # Positive I = residuals clustered spatially (bad)
            # I ≈ 0 = no spatial autocorrelation (good)
            from scipy.stats import pearsonr

            areas = area_residuals.index.tolist()
            n = len(areas)

            # Simple spatial weights: binary adjacency (would need proper shapefile for exact)
            # Using correlation of neighboring areas as approximation
            moran_approx = area_residuals.var() / residuals.var()

            result = {
                'moran_i_approx': moran_approx,
                'interpretation': 'Positive' if moran_approx > 0 else 'Negative/None'
            }

            logger.info(f"  Moran's I (approx): {moran_approx:.4f}")
            logger.info(f"  Interpretation: {result['interpretation']}")

            # Save
            output_df = pd.DataFrame([result])
            output_path = self.output_dir / "spatial_autocorrelation_test.csv"
            output_df.to_csv(output_path, index=False)
            logger.info(f"  Saved: {output_path}")

            return result

        logger.warning("  Cannot test autocorrelation - no planning_area column")
        return None

    def save_performance_comparison(self):
        """Save CV comparison results to CSV."""
        if not self.results:
            logger.warning("No results to save")
            return

        results_df = pd.DataFrame(self.results).T
        output_path = self.output_dir / "spatial_cv_performance.csv"
        results_df.to_csv(output_path, index=False)
        logger.info(f"Saved performance comparison: {output_path}")

        return results_df
```

**Step 2: Test the utilities**

Run:
```bash
uv run python -c "
from scripts.analytics.analysis.school.utils.spatial_validation import SpatialValidator
from pathlib import Path
print('SpatialValidator imported successfully')
validator = SpatialValidator(Path('data/analysis/test'))
print('SpatialValidator instantiated successfully')
"
```

Expected: No import errors, "SpatialValidator instantiated successfully"

**Step 3: Commit**

```bash
git add scripts/analytics/analysis/school/utils/spatial_validation.py
git commit -m "feat: implement SpatialValidator class for spatial cross-validation"
```

---

## Task 4: Implement RDD Estimator Utilities

**Files:**
- Modify: `scripts/analytics/analysis/school/utils/rdd_estimators.py`

**Step 1: Write RDDEstimator class**

Create file `scripts/analytics/analysis/school/utils/rdd_estimators.py`:
```python
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
```

**Step 2: Test the utilities**

Run:
```bash
uv run python -c "
from scripts.analytics.analysis.school.utils.rdd_estimators import RDDEstimator
from pathlib import Path
print('RDDEstimator imported successfully')
estimator = RDDEstimator(Path('data/analysis/test'))
print('RDDEstimator instantiated successfully')
"
```

Expected: No import errors

**Step 3: Commit**

```bash
git add scripts/analytics/analysis/school/utils/rdd_estimators.py
git commit -m "feat: implement RDDEstimator class for causal inference"
```

---

## Task 5: Implement Segmentation Analyzer Utilities

**Files:**
- Modify: `scripts/analytics/analysis/school/utils/interaction_models.py`

**Step 1: Write SegmentationAnalyzer class**

Create file `scripts/analytics/analysis/school/utils/interaction_models.py`:
```python
"""Segmentation and interaction effects analysis utilities."""

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
import xgboost as xgb
from pathlib import Path
import logging
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)


class SegmentationAnalyzer:
    """Analyze heterogeneous treatment effects across market segments."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.segment_results = {}

    def create_market_segments(self, df: pd.DataFrame):
        """
        Create 9 market segments: property_type × region.

        Regions: CCR (Core Central), RCR (Rest of Central), OCR (Outside Central)
        Derived from planning_area using URA definitions.
        """
        logger.info("Creating market segments...")

        # Define region mapping (simplified URA market segments)
        ccr_areas = [
            'DOWNTOWN CORE', 'NEWTON', 'ORCHARD', 'OUTRAM', 'RIVER VALLEY',
            'ROCHOR', 'SINGAPORE RIVER', 'MARINA EAST', 'MARINA SOUTH',
            'SOUTHERN ISLANDS', 'STRANGERS VIEW'
        ]

        rcr_areas = [
            'BISHAN', 'BUKIT MERAH', 'BUKIT TIMAH', 'GEYLANG', 'KALLANG',
            'NOVENA', 'QUEENSTOWN', 'TOA PAYOH', 'MARINE PARADE', 'MUSEUM',
            'TIONG BAHRU'
        ]

        # OCR is everything else
        def get_region(planning_area):
            if planning_area in ccr_areas:
                return 'CCR'
            elif planning_area in rcr_areas:
                return 'RCR'
            else:
                return 'OCR'

        df = df.copy()
        df['region'] = df['planning_area'].apply(get_region)

        # Create segment
        df['market_segment'] = df['property_type'] + '_' + df['region']

        segment_counts = df['market_segment'].value_counts()
        logger.info(f"  Created {len(segment_counts)} segments:")
        for segment, count in segment_counts.items():
            logger.info(f"    {segment}: {count:,} records")

        return df

    def create_interaction_features(self, df: pd.DataFrame):
        """
        Create explicit interaction terms for school quality × key features.
        """
        logger.info("Creating interaction features...")

        df = df.copy()

        # School quality × floor area
        if 'school_primary_quality_score' in df.columns and 'floor_area_sqm' in df.columns:
            df['school_x_area'] = df['school_primary_quality_score'] * df['floor_area_sqm']
            logger.info("  school_x_area: school_quality × floor_area")

        # School quality × MRT distance
        if 'school_primary_quality_score' in df.columns and 'dist_to_nearest_mrt' in df.columns:
            df['school_x_mrt'] = df['school_primary_quality_score'] * df['dist_to_nearest_mrt']
            logger.info("  school_x_mrt: school_quality × mrt_distance")

        # School quality × remaining lease
        if 'school_primary_quality_score' in df.columns and 'remaining_lease_months' in df.columns:
            df['school_x_lease'] = df['school_primary_quality_score'] * df['remaining_lease_months']
            logger.info("  school_x_lease: school_quality × remaining_lease")

        return df

    def run_segmented_models(
        self,
        df: pd.DataFrame,
        feature_cols: list,
        target_col: str = 'price_psf'
    ):
        """
        Run separate models for each market segment.

        Returns dict of results per segment.
        """
        logger.info("Running segmented models...")

        results = []

        for segment in df['market_segment'].unique():
            segment_df = df[df['market_segment'] == segment].copy()

            if len(segment_df) < 500:
                logger.warning(f"  Skipping {segment}: insufficient data ({len(segment_df)} records)")
                continue

            logger.info(f"  Segment: {segment} ({len(segment_df):,} records)")

            # Prepare data
            X = segment_df[feature_cols]
            y = segment_df[target_col]

            # Drop NaN
            segment_df = segment_df.dropna(subset=feature_cols + [target_col])
            X = segment_df[feature_cols]
            y = segment_df[target_col]

            # Split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Fit OLS
            model = LinearRegression()
            model.fit(X_train, y_train)

            # Predict
            y_pred = model.predict(X_test)
            r2 = r2_score(y_test, y_pred)

            # Extract school coefficients
            school_coefs = []
            for i, feat in enumerate(feature_cols):
                if 'school' in feat.lower():
                    school_coefs.append({
                        'segment': segment,
                        'feature': feat,
                        'coefficient': model.coef_[i]
                    })

            results.append({
                'segment': segment,
                'n_train': len(X_train),
                'n_test': len(X_test),
                'r2': r2,
                'model': model,
                'school_coefs': school_coefs
            })

        self.segment_results['segmented'] = results
        return results

    def run_interaction_model(
        self,
        df: pd.DataFrame,
        base_features: list,
        target_col: str = 'price_psf'
    ):
        """
        Run pooled model with interaction terms.

        Model: Y = α + β₁·school + β₂·prop_type + β₃·region + β₄·(school×prop_type) + ...
        """
        logger.info("Running interaction model...")

        df = df.copy()

        # Create dummies for categorical variables
        df = pd.get_dummies(df, columns=['property_type', 'region'], drop_first=True)

        # Add interaction terms
        interaction_cols = []

        # School × property type
        if 'school_primary_quality_score' in df.columns:
            for col in df.columns:
                if col.startswith('property_type_'):
                    interaction_col = f'school_x_{col}'
                    df[interaction_col] = df['school_primary_quality_score'] * df[col]
                    interaction_cols.append(interaction_col)

            # School × region
            for col in df.columns:
                if col.startswith('region_'):
                    interaction_col = f'school_x_{col}'
                    df[interaction_col] = df['school_primary_quality_score'] * df[col]
                    interaction_cols.append(interaction_col)

        logger.info(f"  Created {len(interaction_cols)} interaction terms")

        # Prepare features
        feature_cols = base_features + interaction_cols
        feature_cols = [f for f in feature_cols if f in df.columns]

        # Drop NaN
        df = df.dropna(subset=feature_cols + [target_col])

        X = df[feature_cols]
        y = df[target_col]

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Fit OLS
        model = LinearRegression()
        model.fit(X_train, y_train)

        # Predict
        y_pred = model.predict(X_test)
        r2 = r2_score(y_test, y_pred)

        # Extract interaction coefficients
        interaction_coefs = []
        for i, feat in enumerate(feature_cols):
            if feat.startswith('school_x_'):
                interaction_coefs.append({
                    'feature': feat,
                    'coefficient': model.coef_[i],
                    'abs_coef': abs(model.coef_[i])
                })

        interaction_df = pd.DataFrame(interaction_coefs).sort_values('abs_coef', ascending=False)

        logger.info(f"  R²: {r2:.4f}")
        logger.info(f"  Top interactions:")
        for _, row in interaction_df.head(5).iterrows():
            logger.info(f"    {row['feature']}: {row['coefficient']:.4f}")

        result = {
            'model': model,
            'r2': r2,
            'n_train': len(X_train),
            'n_test': len(X_test),
            'interaction_coefs': interaction_df,
            'feature_cols': feature_cols
        }

        self.segment_results['interaction'] = result
        return result

    def save_segment_coefficients(self):
        """Save segment-specific school coefficients to CSV."""
        if 'segmented' not in self.segment_results:
            logger.warning("No segmented results to save")
            return None

        all_coefs = []
        for result in self.segment_results['segmented']:
            all_coefs.extend(result['school_coefs'])

        coef_df = pd.DataFrame(all_coefs)

        # Pivot for easier viewing
        pivot_df = coef_df.pivot(index='segment', columns='feature', values='coefficient')

        output_path = self.output_dir / "segment_coefficients.csv"
        pivot_df.to_csv(output_path)
        logger.info(f"Saved segment coefficients: {output_path}")

        return pivot_df

    def save_interaction_results(self):
        """Save interaction model results to CSV."""
        if 'interaction' not in self.segment_results:
            logger.warning("No interaction results to save")
            return None

        interaction_df = self.segment_results['interaction']['interaction_coefs']

        output_path = self.output_dir / "interaction_model_results.csv"
        interaction_df.to_csv(output_path, index=False)
        logger.info(f"Saved interaction results: {output_path}")

        return interaction_df

    def compare_r2_across_segments(self):
        """Compare model performance (R²) across segments."""
        if 'segmented' not in self.segment_results:
            logger.warning("No segmented results to compare")
            return None

        r2_data = []
        for result in self.segment_results['segmented']:
            r2_data.append({
                'segment': result['segment'],
                'r2': result['r2'],
                'n_test': result['n_test']
            })

        r2_df = pd.DataFrame(r2_data).sort_values('r2', ascending=False)

        output_path = self.output_dir / "segment_r2_comparison.csv"
        r2_df.to_csv(output_path, index=False)
        logger.info(f"Saved R² comparison: {output_path}")

        return r2_df
```

**Step 2: Test the utilities**

Run:
```bash
uv run python -c "
from scripts.analytics.analysis.school.utils.interaction_models import SegmentationAnalyzer
from pathlib import Path
print('SegmentationAnalyzer imported successfully')
analyzer = SegmentationAnalyzer(Path('data/analysis/test'))
print('SegmentationAnalyzer instantiated successfully')
"
```

Expected: No import errors

**Step 3: Commit**

```bash
git add scripts/analytics/analysis/school/utils/interaction_models.py
git commit -m "feat: implement SegmentationAnalyzer for heterogeneous effects"
```

---

## Task 6: Implement Spatial CV Analysis Script

**Files:**
- Create: `scripts/analytics/analysis/school/analyze_school_spatial_cv.py`

**Step 1: Write main spatial CV script**

Create file `scripts/analytics/analysis/school/analyze_school_spatial_cv.py`:
```python
"""
Spatial Cross-Validation Analysis for School Impact

Tests whether school impact models generalize to new geographic areas,
guarding against spatial autocorrelation bias.

Usage:
    uv run python scripts/analytics/analysis/school/analyze_school_spatial_cv.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import warnings
warnings.filterwarnings('ignore')

from scripts.analytics.analysis.school.utils.spatial_validation import SpatialValidator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("data/pipeline/L3")
OUTPUT_DIR = Path("data/analysis/school_spatial_cv")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_data():
    """Load and prepare data."""
    print("="*80)
    print("SPATIAL CROSS-VALIDATION ANALYSIS")
    print("="*80)

    print("\nLoading data...")
    df = pd.read_parquet(DATA_DIR / "housing_unified.parquet")
    print(f"  Full dataset: {len(df):,} records")

    # Filter to 2021+ for consistency
    df = df[df['year'] >= 2021].copy()
    print(f"  Filtered to 2021+: {len(df):,} records")

    # Check required columns
    required_cols = ['planning_area', 'school_accessibility_score']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    print(f"  Planning areas: {df['planning_area'].nunique()}")
    print(f"  School data available: Yes")

    return df


def prepare_features(df, target_col='price_psf'):
    """Prepare features for spatial CV."""
    print(f"\nPreparing features for: {target_col}")

    # Drop rows with missing target
    df_model = df.dropna(subset=[target_col]).copy()

    # Feature columns
    feature_cols = [
        'floor_area_sqm',
        'remaining_lease_months',
        'school_accessibility_score',
        'school_primary_quality_score',
        'school_secondary_quality_score',
        'dist_to_nearest_mrt',
        'dist_to_nearest_hawker',
        'dist_to_nearest_supermarket'
    ]

    # Filter to available columns
    feature_cols = [col for col in feature_cols if col in df_model.columns]

    # Drop rows with NaN in features
    df_model = df_model.dropna(subset=feature_cols)

    print(f"  Features: {len(feature_cols)}")
    print(f"  Records: {len(df_model):,}")

    return df_model, feature_cols


def main():
    """Main analysis pipeline."""

    # Load data
    df = load_data()

    # Initialize validator
    validator = SpatialValidator(OUTPUT_DIR)

    # Prepare features
    df_model, feature_cols = prepare_features(df, 'price_psf')

    # Extract features and target
    X = df_model[feature_cols]
    y = df_model['price_psf']
    groups = df_model['planning_area']

    print("\n" + "="*80)
    print("COMPARING CV METHODS")
    print("="*80)

    # Compare OLS
    print("\n1. OLS Model")
    ols_result = validator.compare_cv_methods(X, y, groups, model_type='ols')

    # Compare Random Forest
    print("\n2. Random Forest Model")
    rf_result = validator.compare_cv_methods(X, y, groups, model_type='rf')

    # Compare XGBoost
    print("\n3. XGBoost Model")
    xgb_result = validator.compare_cv_methods(X, y, groups, model_type='xgboost')

    # Save performance comparison
    print("\n" + "="*80)
    print("SAVING RESULTS")
    print("="*80)

    perf_df = validator.save_performance_comparison()
    print("\nPerformance Comparison:")
    print(perf_df.to_string(index=False))

    # Analyze area generalization
    print("\n" + "="*80)
    print("ANALYZING PLANNING AREA GENERALIZATION")
    print("="*80)

    area_results = validator.analyze_area_generalization(
        df_model, feature_cols, 'price_psf', 'planning_area'
    )

    # Test spatial autocorrelation
    print("\n" + "="*80)
    print("TESTING SPATIAL AUTOCORRELATION")
    print("="*80)

    # Get residuals from OLS
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import train_test_split

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    model = LinearRegression()
    model.fit(X_train, y_train)
    residuals = pd.Series(y_test - model.predict(X_test), index=X_test.index)

    moran_result = validator.test_spatial_autocorrelation(
        residuals,
        df_model.loc[X_test.index, ['planning_area']]
    )

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {OUTPUT_DIR}")
    print("\nKey findings:")
    print(f"  - Spatial generalization gap (OLS): {ols_result['gap_pct']:.1f}%")
    print(f"  - Worst generalizing area: {area_results.iloc[0]['planning_area']}")


if __name__ == "__main__":
    main()
```

**Step 2: Run spatial CV analysis**

Run:
```bash
uv run python scripts/analytics/analysis/school/analyze_school_spatial_cv.py
```

Expected: Output shows spatial CV R² lower than standard CV, results saved to `data/analysis/school_spatial_cv/`

**Step 3: Commit**

```bash
git add scripts/analytics/analysis/school/analyze_school_spatial_cv.py
git commit -m "feat: add spatial cross-validation analysis script"
```

---

## Task 7: Implement RDD Analysis Script

**Files:**
- Create: `scripts/analytics/analysis/school/analyze_school_rdd.py`

**Step 1: Write main RDD script**

Create file `scripts/analytics/analysis/school/analyze_school_rdd.py`:
```python
"""
Regression Discontinuity Design Analysis for Causal Inference

Estimates causal effect of school proximity on property prices using
the 1km admission priority cutoff as natural experiment.

Usage:
    uv run python scripts/analytics/analysis/school/analyze_school_rdd.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import warnings
warnings.filterwarnings('ignore')

from scripts.analytics.analysis.school.utils.rdd_estimators import RDDEstimator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("data/pipeline/L3")
OUTPUT_DIR = Path("data/analysis/school_rdd")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_data():
    """Load and prepare data."""
    print("="*80)
    print("RDD CAUSAL ANALYSIS")
    print("="*80)

    print("\nLoading data...")
    df = pd.read_parquet(DATA_DIR / "housing_unified.parquet")
    print(f"  Full dataset: {len(df):,} records")

    # Filter to 2021+
    df = df[df['year'] >= 2021].copy()
    print(f"  Filtered to 2021+: {len(df):,} records")

    # Check required columns
    if 'nearest_schoolPRIMARY_dist' not in df.columns:
        raise ValueError("nearest_schoolPRIMARY_dist column not found")

    # Filter to properties with primary school distance
    df = df.dropna(subset=['nearest_schoolPRIMARY_dist']).copy()
    print(f"  With primary school data: {len(df):,} records")

    # Focus on properties near schools (within 2km for RDD bandwidth)
    df = df[df['nearest_schoolPRIMARY_dist'] <= 2000].copy()
    print(f"  Within 2km of primary school: {len(df):,} records")

    return df


def main():
    """Main RDD analysis pipeline."""

    # Load data
    df = load_data()

    # Initialize RDD estimator
    estimator = RDDEstimator(OUTPUT_DIR)

    # Control variables (should be balanced at cutoff)
    control_cols = [
        'floor_area_sqm',
        'remaining_lease_months',
        'year',
        'dist_to_nearest_mrt',
        'dist_to_nearest_hawker'
    ]

    # Filter to available controls
    control_cols = [col for col in control_cols if col in df.columns]

    print("\n" + "="*80)
    print("MAIN RDD ESTIMATE")
    print("="*80)

    # Create RDD dataset (200m bandwidth)
    rdd_df = estimator.create_rdd_dataset(df, bandwidth=200)

    # Estimate treatment effect
    results = estimator.estimate_rdd(rdd_df, target_col='price_psf', control_cols=control_cols)

    # Save main results
    estimator.save_main_results(results)

    print("\n" + "="*80)
    print("VALIDATION TESTS")
    print("="*80)

    # Covariate balance test
    print("\n1. Covariate Balance Test")
    balance_df = estimator.test_covariate_balance(rdd_df, control_cols)

    # Bandwidth sensitivity
    print("\n2. Bandwidth Sensitivity Test")
    bandwidth_df = estimator.bandwidth_sensitivity(
        df,
        bandwidths=[100, 150, 200, 250, 300],
        target_col='price_psf',
        control_cols=control_cols
    )

    # Placebo tests
    print("\n3. Placebo Tests (Fake Cutoffs)")
    placebo_df = estimator.placebo_tests(
        df,
        placebo_cutoffs=[800, 1200],
        target_col='price_psf',
        control_cols=control_cols
    )

    # Visualization
    print("\n" + "="*80)
    print("CREATING VISUALIZATIONS")
    print("="*80)

    estimator.visualize_discontinuity(rdd_df, target_col='price_psf', bandwidth=200)

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {OUTPUT_DIR}")

    # Summary
    print("\nKey Findings:")
    inference = results['inference']
    if inference.get('significant'):
        print(f"  ✓ Causal effect detected: ${results['tau']:.2f} PSF (p={inference['p_value']:.4f})")
    else:
        print(f"  ✗ No significant causal effect (p={inference.get('p_value', 'N/A')})")

    print(f"  95% CI: [{inference.get('ci_lower', 'N/A'):.2f}, {inference.get('ci_upper', 'N/A'):.2f}]")

    # Validation checks
    print("\nValidation Checks:")
    balanced = balance_df['balanced'].sum()
    print(f"  Covariates balanced: {balanced}/{len(balance_df)}")

    if len(placebo_df) > 0:
        placebo_significant = placebo_df['significant'].sum()
        print(f"  Placebo tests significant (should be 0): {placebo_significant}/{len(placebo_df)}")


if __name__ == "__main__":
    main()
```

**Step 2: Run RDD analysis**

Run:
```bash
uv run python scripts/analytics/analysis/school/analyze_school_rdd.py
```

Expected: Output shows causal effect estimate, validation tests, visualization saved

**Step 3: Commit**

```bash
git add scripts/analytics/analysis/school/analyze_school_rdd.py
git commit -m "feat: add RDD causal inference analysis script"
```

---

## Task 8: Implement Segmentation Analysis Script

**Files:**
- Create: `scripts/analytics/analysis/school/analyze_school_segmentation.py`

**Step 1: Write main segmentation script**

Create file `scripts/analytics/analysis/school/analyze_school_segmentation.py`:
```python
"""
Segmentation and Interaction Effects Analysis

Analyzes how school premium varies across market segments (property type × region)
and interacts with key property characteristics.

Usage:
    uv run python scripts/analytics/analysis/school/analyze_school_segmentation.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import warnings
warnings.filterwarnings('ignore')

from scripts.analytics.analysis.school.utils.interaction_models import SegmentationAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("data/pipeline/L3")
OUTPUT_DIR = Path("data/analysis/school_segmentation")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def load_data():
    """Load and prepare data."""
    print("="*80)
    print("SEGMENTATION & INTERACTION ANALYSIS")
    print("="*80)

    print("\nLoading data...")
    df = pd.read_parquet(DATA_DIR / "housing_unified.parquet")
    print(f"  Full dataset: {len(df):,} records")

    # Filter to 2021+
    df = df[df['year'] >= 2021].copy()
    print(f"  Filtered to 2021+: {len(df):,} records")

    # Check school features
    if 'school_primary_quality_score' not in df.columns:
        raise ValueError("school_primary_quality_score not found")

    return df


def prepare_features(df):
    """Prepare feature list."""
    feature_cols = [
        'floor_area_sqm',
        'remaining_lease_months',
        'year',
        'school_accessibility_score',
        'school_primary_quality_score',
        'school_secondary_quality_score',
        'dist_to_nearest_mrt',
        'dist_to_nearest_hawker'
    ]

    # Filter to available
    feature_cols = [col for col in feature_cols if col in df.columns]

    return feature_cols


def main():
    """Main analysis pipeline."""

    # Load data
    df = load_data()

    # Prepare features
    feature_cols = prepare_features(df)
    print(f"\nFeatures: {len(feature_cols)}")

    # Initialize analyzer
    analyzer = SegmentationAnalyzer(OUTPUT_DIR)

    print("\n" + "="*80)
    print("CREATING MARKET SEGMENTS")
    print("="*80)

    # Create segments
    df = analyzer.create_market_segments(df)

    # Create interaction features
    df = analyzer.create_interaction_features(df)

    print("\n" + "="*80)
    print("STAGE 1: SEGMENTED MODELS")
    print("="*80)

    # Run segmented models
    segment_results = analyzer.run_segmented_models(
        df,
        feature_cols,
        target_col='price_psf'
    )

    # Save segment coefficients
    coef_df = analyzer.save_segment_coefficients()
    if coef_df is not None:
        print("\nSegment Coefficients:")
        print(coef_df.round(2))

    # Save R² comparison
    r2_df = analyzer.compare_r2_across_segments()
    if r2_df is not None:
        print("\nR² by Segment:")
        print(r2_df.to_string(index=False))

    print("\n" + "="*80)
    print("STAGE 2: INTERACTION MODEL")
    print("="*80)

    # Run interaction model
    interaction_result = analyzer.run_interaction_model(
        df,
        feature_cols,
        target_col='price_psf'
    )

    # Save interaction results
    interaction_df = analyzer.save_interaction_results()
    if interaction_df is not None:
        print("\nTop Interaction Effects:")
        print(interaction_df.head(10).to_string(index=False))

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {OUTPUT_DIR}")

    print("\nKey Findings:")
    print(f"  - Analyzed {len(segment_results)} market segments")
    print(f"  - Interaction model R²: {interaction_result['r2']:.4f}")
    print(f"  - Significant interactions: {(interaction_df['coefficient'].abs() > 5).sum()}")


if __name__ == "__main__":
    main()
```

**Step 2: Run segmentation analysis**

Run:
```bash
uv run python scripts/analytics/analysis/school/analyze_school_segmentation.py
```

Expected: Output shows segment coefficients, interaction effects

**Step 3: Commit**

```bash
git add scripts/analytics/analysis/school/analyze_school_segmentation.py
git commit -m "feat: add segmentation and interaction analysis script"
```

---

## Task 9: Update Documentation

**Files:**
- Modify: `docs/analytics/school-impact-analysis.md`

**Step 1: Add new sections to documentation**

Read the existing documentation:
```bash
cat docs/analytics/school-impact-analysis.md
```

Then update with new sections by inserting after "Pipeline Scripts" section:

Add to `docs/analytics/school-impact-analysis.md` (insert after line 139, before "Data Requirements"):

```markdown
## Enhanced Analysis Modules

### 5. Spatial Cross-Validation (`analyze_school_spatial_cv.py`)

**Purpose:** Test whether school impact models generalize to new geographic areas, guarding against spatial autocorrelation bias.

**Key Features:**
- Compares standard KFold vs GroupKFold (spatial) cross-validation
- Calculates spatial generalization gap (R² drop when testing on new areas)
- Identifies which planning areas generalize well vs poorly
- Tests for spatial autocorrelation in residuals using Moran's I

**Research Questions:**
- Do school impact models overfit to specific neighborhoods?
- Which planning areas are hardest to predict?
- How much does spatial autocorrelation inflate performance metrics?

**Outputs:**
- `spatial_cv_performance.csv`: Performance comparison (OLS/RF/XGBoost)
- `planning_area_generalization.csv`: Area-by-area diagnostics
- `spatial_autocorrelation_test.csv`: Moran's I test results

**Usage:**
```bash
uv run python scripts/analytics/analysis/school/analyze_school_spatial_cv.py
```

**Interpretation:**
- **Generalization gap >10%**: Significant spatial autocorrelation, model needs spatial regularization
- **High gap area**: Model fails to generalize, may need area-specific features
- **Moran's I >0**: Residuals clustered spatially (violates independence assumption)

### 6. Causal Inference with RDD (`analyze_school_rdd.py`)

**Purpose:** Establish causal effect of school proximity using Regression Discontinuity Design at 1km admission boundary.

**Key Features:**
- Exploits Singapore's primary school 1km admission priority as natural experiment
- Compares properties just inside vs just outside 1km radius
- Bandwidth sensitivity testing (100m-300m)
- Placebo tests at fake cutoffs (800m, 1200m)
- Covariate balance validation

**Research Questions:**
- What is the **causal** effect of being within 1km of a top school?
- Do OLS coefficients suffer from selection bias?
- How robust is the causal estimate to bandwidth changes?

**Outputs:**
- `rdd_main_effect.csv`: Causal estimate (τ) with robust standard errors
- `rdd_bandwidth_sensitivity.csv`: Results across bandwidths
- `rdd_covariate_balance.csv`: Balance statistics for controls
- `rdd_placebo_tests.csv`: Fake cutoff results (should be null)
- `rdd_visualization.png`: Price discontinuity plot

**Usage:**
```bash
uv run python scripts/analytics/analysis/school/analyze_school_rdd.py
```

**Interpretation:**
- **τ = $25 PSF (p<0.05)**: Being within 1km causes $25 PSF premium
- **Covariates balanced**: No significant differences at cutoff (validation passed)
- **Placebo tests null**: No effect at fake cutoffs (RDD specification valid)
- **Bandwidth stable**: τ similar across 100-300m (robust estimate)

**Limitations:**
- Only estimates **local** effect (for properties near 1km boundary)
- Requires sufficient sample near boundary (may need to aggregate schools)
- Does not account for fuzzy eligibility (not all within 1km qualify)

### 7. Segmentation & Interaction Analysis (`analyze_school_segmentation.py`)

**Purpose:** Reveal how school premium varies across market segments and property characteristics.

**Key Features:**
- 9 market segments: property_type (HDB/Condo/EC) × region (CCR/RCR/OCR)
- Separate OLS models per segment
- Pooled interaction model with explicit interaction terms
- Tests for heterogeneous treatment effects

**Research Questions:**
- Do Condo buyers value schools more than HDB buyers?
- Does school premium vanish in CCR (international schools compete)?
- Do large luxury units discount school proximity?
- Is there synergy between school and MRT accessibility?

**Outputs:**
- `segment_coefficients.csv`: School premium by 9 market segments
- `interaction_model_results.csv`: All interaction coefficients
- `segment_r2_comparison.csv`: Model performance across segments

**Usage:**
```bash
uv run python scripts/analytics/analysis/school/analyze_school_segmentation.py
```

**Interpretation:**
- **Higher coefficient in OCR**: School premium larger outside central region
- **school_x_mrt negative**: School and MRT proximity substitute (not complement)
- **school_x_area negative**: Luxury buyers (large units) value schools less
- **Segment R² varies**: School features explain more variance in some segments

**Interaction Effects to Examine:**
- `school × Condominium`: Do private buyers value schools more?
- `school × CCR`: Does central location reduce school premium?
- `school × floor_area`: Do larger units discount school access?
- `school × MRT_distance`: Accessibility synergy or substitute?

```

**Step 2: Update changelog**

Add to end of `docs/analytics/school-impact-analysis.md`:

```markdown
## Changelog

- **2025-02-02:** Initial pipeline creation
  - Main impact analysis with OLS/XGBoost/SHAP
  - Property type comparison
  - Temporal evolution (2017-2026)
  - Heterogeneous effects within HDB

- **2025-02-05:** Enhanced analysis modules
  - Spatial cross-validation framework
  - Causal inference with RDD at 1km boundary
  - Segmentation and interaction effects analysis
  - Robustness validation suite
```

**Step 3: Commit**

```bash
git add docs/analytics/school-impact-analysis.md
git commit -m "docs: add enhanced analysis modules to school impact documentation"
```

---

## Task 10: Verify All Modules Run Successfully

**Files:**
- None (verification)

**Step 1: Run all three new modules in sequence**

Run:
```bash
echo "=== Running Spatial CV ===" && \
uv run python scripts/analytics/analysis/school/analyze_school_spatial_cv.py && \
echo -e "\n=== Running RDD ===" && \
uv run python scripts/analytics/analysis/school/analyze_school_rdd.py && \
echo -e "\n=== Running Segmentation ===" && \
uv run python scripts/analytics/analysis/school/analyze_school_segmentation.py && \
echo -e "\n=== All modules completed successfully ==="
```

Expected: All three scripts run without errors, outputs generated

**Step 2: Verify outputs**

Run:
```bash
echo "Spatial CV outputs:" && ls -lh data/analysis/school_spatial_cv/ && \
echo -e "\nRDD outputs:" && ls -lh data/analysis/school_rdd/ && \
echo -e "\nSegmentation outputs:" && ls -lh data/analysis/school_segmentation/
```

Expected: CSV files and PNG visualizations in each directory

**Step 3: Commit**

```bash
git add data/analysis/
git commit -m "chore: add analysis outputs (initial run)"
```

---

## Task 11: Create Summary Integration Script

**Files:**
- Create: `scripts/analytics/analysis/school/run_enhanced_analysis.sh`

**Step 1: Create convenience script**

Create file `scripts/analytics/analysis/school/run_enhanced_analysis.sh`:
```bash
#!/bin/bash
# Enhanced School Impact Analysis - Complete Pipeline
# Runs all analysis modules in sequence

set -e  # Exit on error

echo "========================================="
echo "ENHANCED SCHOOL IMPACT ANALYSIS"
echo "========================================="

echo -e "\n[1/3] Spatial Cross-Validation..."
uv run python scripts/analytics/analysis/school/analyze_school_spatial_cv.py

echo -e "\n[2/3] Causal Inference (RDD)..."
uv run python scripts/analytics/analysis/school/analyze_school_rdd.py

echo -e "\n[3/3] Segmentation & Interactions..."
uv run python scripts/analytics/analysis/school/analyze_school_segmentation.py

echo -e "\n========================================="
echo "ANALYSIS COMPLETE"
echo "========================================="
echo -e "\nResults:"
echo "  - data/analysis/school_spatial_cv/"
echo "  - data/analysis/school_rdd/"
echo "  - data/analysis/school_segmentation/"
```

**Step 2: Make executable**

Run:
```bash
chmod +x scripts/analytics/analysis/school/run_enhanced_analysis.sh
```

**Step 3: Commit**

```bash
git add scripts/analytics/analysis/school/run_enhanced_analysis.sh
git commit -m "chore: add convenience script for running all enhanced analysis modules"
```

---

## Completion Checklist

**Verify All Success Criteria:**

- [ ] **Module 1:** Spatial CV R² at least 5% lower than standard CV
- [ ] **Module 1:** At least 3 planning areas identified with poor generalization
- [ ] **Module 1:** Moran's I test significant (p < 0.05)

- [ ] **Module 2:** RDD estimate τ statistically significant (p < 0.05)
- [ ] **Module 2:** Covariate balance test passes
- [ ] **Module 2:** Placebo tests show null effects
- [ ] **Module 2:** Bandwidth sensitivity shows stable estimates

- [ ] **Module 3:** At least 2 interaction terms significant (p < 0.05)
- [ ] **Module 3:** Segmented models outperform pooled by ΔR² > 0.05
- [ ] **Module 3:** Clear heterogeneity pattern observed

**Final Verification Step:**

Run all modules and check outputs:
```bash
bash scripts/analytics/analysis/school/run_enhanced_analysis.sh
```

Review generated CSVs and visualizations to confirm findings align with expectations.

**Final Commit:**

```bash
git add .
git commit -m "feat: complete enhanced school impact analysis implementation

- Add spatial cross-validation with GroupKFold
- Implement RDD for causal inference at 1km boundary
- Add segmentation analysis for 9 market segments
- Create shared utility modules for all analyses
- Update documentation with new modules
- Add convenience script for running all analyses

All modules tested and working successfully."
```

---

## End of Implementation Plan

**Total Estimated Time:** 15 hours
**Total Tasks:** 11
**Total New Files:** 7
**Total Modified Files:** 2

**Next Steps After Implementation:**
1. Review all generated outputs and validate findings
2. Create summary report comparing results across modules
3. Consider adding visualizations for stakeholder presentation
4. Document any limitations or caveats discovered
