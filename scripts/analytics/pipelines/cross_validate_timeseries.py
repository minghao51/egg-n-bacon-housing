# scripts/analytics/pipelines/cross_validate_timeseries.py
"""
Cross-validation pipeline for VAR/ARIMAX models.

Implements expanding window validation for robust performance estimation.

Usage:
    from scripts.analytics.pipelines.cross_validate_timeseries import run_cross_validation

    results = run_cross_validation(
        regional_data=regional_df,
        area_data=area_df,
        n_folds=5
    )
"""

import logging
from typing import Dict, List

import numpy as np
import pandas as pd

from scripts.analytics.models.regional_var import RegionalVARModel
from scripts.analytics.models.area_arimax import AreaARIMAXModel

logger = logging.getLogger(__name__)


def evaluate_model_performance(actual: pd.Series, forecast: pd.Series) -> Dict[str, float]:
    """
    Calculate performance metrics.

    Args:
        actual: Actual values
        forecast: Forecasted values

    Returns:
        Dictionary with RMSE, MAE, MAPE, directional_accuracy
    """
    # Align indices
    aligned_actual, aligned_forecast = actual.align(forecast, join='inner')

    if len(aligned_actual) == 0:
        logger.warning("No overlapping data for evaluation")
        return {}

    # Calculate metrics
    rmse = np.sqrt(np.mean((aligned_actual - aligned_forecast) ** 2))
    mae = np.mean(np.abs(aligned_actual - aligned_forecast))

    # MAPE (handle zeros)
    mask = aligned_actual != 0
    if mask.sum() > 0:
        mape = np.mean(np.abs((aligned_actual[mask] - aligned_forecast[mask]) / aligned_actual[mask])) * 100
    else:
        mape = np.nan

    # Directional accuracy
    actual_changes = np.sign(aligned_actual.diff().dropna())
    forecast_changes = np.sign(aligned_forecast.diff().dropna())
    directional_accuracy = (actual_changes == forecast_changes).mean() * 100

    return {
        'rmse': rmse,
        'mae': mae,
        'mape': mape,
        'directional_accuracy': directional_accuracy
    }


def run_rolling_validation(
    data: pd.DataFrame,
    region: str,
    n_folds: int = 5,
    forecast_horizon: int = 12
) -> Dict:
    """
    Run expanding window cross-validation for regional VAR.

    Args:
        data: Regional time series data
        region: Region name
        n_folds: Number of validation folds
        forecast_horizon: Forecast horizon (months)

    Returns:
        Dictionary with fold_metrics, mean_rmse, mean_mae, etc.
    """
    logger.info(f"Running rolling validation for {region}: {n_folds} folds, {forecast_horizon}-month horizon")

    fold_metrics = []
    min_train_size = 30  # Minimum training size

    for fold in range(n_folds):
        train_end = min_train_size + fold * 3  # Expand by 3 months each fold

        if train_end + forecast_horizon > len(data):
            logger.warning(f"Fold {fold}: insufficient data, skipping")
            continue

        # Split data
        train_data = data.iloc[:train_end]
        test_data = data.iloc[train_end:train_end + forecast_horizon]

        logger.info(f"Fold {fold}: Train size={len(train_data)}, Test size={len(test_data)}")

        try:
            # Fit model
            model = RegionalVARModel(region=region)
            model.fit(train_data, test_size=0)

            # Forecast
            forecast = model.forecast(horizon=forecast_horizon)

            # Evaluate
            actual = test_data['regional_appreciation'].reset_index(drop=True)
            predicted = forecast['forecast_mean']

            metrics = evaluate_model_performance(actual, predicted)
            metrics['fold'] = fold

            fold_metrics.append(metrics)

            logger.info(f"  Fold {fold} RMSE: {metrics['rmse']:.2f}, MAE: {metrics['mae']:.2f}")

        except Exception as e:
            logger.error(f"Fold {fold} failed: {e}")
            continue

    # Aggregate metrics
    if fold_metrics:
        mean_rmse = np.mean([m['rmse'] for m in fold_metrics])
        mean_mae = np.mean([m['mae'] for m in fold_metrics])
        mean_directional = np.mean([m['directional_accuracy'] for m in fold_metrics])
    else:
        mean_rmse = mean_mae = mean_directional = np.nan

    results = {
        'region': region,
        'n_folds': len(fold_metrics),
        'fold_metrics': fold_metrics,
        'mean_rmse': mean_rmse,
        'mean_mae': mean_mae,
        'mean_directional_accuracy': mean_directional
    }

    logger.info(f"Validation complete: RMSE={mean_rmse:.2f}, MAE={mean_mae:.2f}, DirAcc={mean_directional:.1f}%")

    return results


def run_cross_validation(
    regional_data: pd.DataFrame,
    area_data: pd.DataFrame,
    n_folds: int = 5
) -> Dict:
    """
    Run complete cross-validation for all models.

    Args:
        regional_data: Regional time series
        area_data: Area time series
        n_folds: Number of validation folds

    Returns:
        Dictionary with regional and area results
    """
    logger.info("=" * 60)
    logger.info("Cross-Validation Pipeline")
    logger.info("=" * 60)

    results = {
        'regional': {},
        'area': {}
    }

    # Regional cross-validation
    for region in regional_data['region'].unique():
        region_data = regional_data[regional_data['region'] == region]

        if len(region_data) < 36:  # Need at least 36 months
            logger.warning(f"Skipping {region}: insufficient data")
            continue

        region_results = run_rolling_validation(
            data=region_data,
            region=region,
            n_folds=n_folds,
            forecast_horizon=12
        )

        results['regional'][region] = region_results

    # Area cross-validation (simplified - just 1 fold for speed)
    for area in area_data['area'].unique()[:10]:  # Test 10 areas for now
        area_data_subset = area_data[area_data['area'] == area]

        if len(area_data_subset) < 30:
            continue

        logger.info(f"Validating area: {area}")

        try:
            # Simple train/test split
            train_size = int(len(area_data_subset) * 0.8)
            train_data = area_data_subset.iloc[:train_size]
            test_data = area_data_subset.iloc[train_size:]

            # Fit model
            model = AreaARIMAXModel(area=area, region='Unknown')
            model.fit(train_data, test_size=0)

            # Forecast
            # Use actual values as proxy for regional forecast in test
            exog_cols = [col for col in ['regional_appreciation', 'mrt_within_1km_mean', 'hawker_within_1km_mean']
                         if col in train_data.columns]

            if exog_cols and len(test_data) > 0:
                regional_forecast = pd.DataFrame({
                    'month': test_data['month'].values,
                    **{col: test_data[col].values for col in exog_cols}
                })

                forecast = model.forecast(horizon=len(test_data), exog_future=regional_forecast)

                # Evaluate
                actual = test_data['area_appreciation'].reset_index(drop=True)
                predicted = forecast['forecast_mean']

                metrics = evaluate_model_performance(actual, predicted)
                results['area'][area] = metrics

                logger.info(f"  {area} RMSE: {metrics['rmse']:.2f}")

        except Exception as e:
            logger.error(f"Area validation failed for {area}: {e}")
            continue

    logger.info("=" * 60)
    logger.info("Cross-validation complete!")
    logger.info("=" * 60)

    return results
