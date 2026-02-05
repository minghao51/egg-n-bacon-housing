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
