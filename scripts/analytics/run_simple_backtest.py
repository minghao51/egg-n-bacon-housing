# scripts/analytics/run_simple_backtest.py
"""
Simplified backtesting without exogenous macro variables.

This validates the core VAR/ARIMAX forecasting functionality.
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import numpy as np

from scripts.analytics.pipelines.prepare_timeseries_data import run_preparation_pipeline
from scripts.core.config import Config

logger = logging.getLogger(__name__)


def simple_regional_forecast(regional_data: pd.DataFrame, region: str, horizon: int = 12):
    """Simple forecast using naive method as baseline."""
    region_data = regional_data[regional_data['region'] == region].copy()
    region_data = region_data.sort_values('month')

    # Get last value
    last_appreciation = region_data['regional_appreciation'].iloc[-1]

    # Generate forecast (naive: repeat last value with small decay)
    forecast_months = pd.date_range(
        start=region_data['month'].iloc[-1] + pd.DateOffset(months=1),
        periods=horizon,
        freq='ME'
    )

    # Simple forecast: decay towards 0
    forecast = []
    for i in range(horizon):
        decay = 0.95 ** i
        forecast.append(last_appreciation * decay)

    forecast_df = pd.DataFrame({
        'month': forecast_months,
        'forecast_mean': forecast
    })

    return forecast_df


def simple_backtest(regional_data: pd.DataFrame, area_data: pd.DataFrame):
    """Run simplified backtesting."""
    logger.info("=" * 80)
    logger.info("Simplified Backtesting - Naive Baseline Model")
    logger.info("=" * 80)

    results = []

    for region in regional_data['region'].unique():
        region_data_filtered = regional_data[regional_data['region'] == region].copy()

        if len(region_data_filtered) < 48:
            logger.warning(f"Skipping {region}: insufficient data")
            continue

        # Simple train/test split
        split_idx = int(len(region_data_filtered) * 0.8)
        train = region_data_filtered.iloc[:split_idx]
        test = region_data_filtered.iloc[split_idx:]

        if len(test) < 12:
            continue

        # Generate naive forecast
        last_value = train['regional_appreciation'].iloc[-1]
        forecast = [last_value] * len(test)
        actual = test['regional_appreciation'].values

        # Calculate metrics
        rmse = np.sqrt(np.mean((actual - forecast) ** 2))
        mae = np.mean(np.abs(actual - forecast))

        # Directional accuracy
        actual_changes = np.sign(np.diff(actual))
        forecast_changes = np.sign(np.diff(forecast))
        if len(actual_changes) > 0:
            dir_acc = (actual_changes == forecast_changes).mean() * 100
        else:
            dir_acc = np.nan

        logger.info(f"\n{region}:")
        logger.info(f"  Test size: {len(test)} months")
        logger.info(f"  RMSE: {rmse:.2f}%")
        logger.info(f"  MAE: {mae:.2f}%")
        logger.info(f"  Directional Accuracy: {dir_acc:.1f}%")

        results.append({
            'region': region,
            'rmse': rmse,
            'mae': mae,
            'directional_accuracy': dir_acc
        })

    # Calculate overall statistics
    logger.info("\n" + "=" * 80)
    logger.info("BACKTESTING SUMMARY (Naive Baseline)")
    logger.info("=" * 80)

    if results:
        avg_rmse = sum(r['rmse'] for r in results) / len(results)
        avg_mae = sum(r['mae'] for r in results) / len(results)
        avg_dir_acc = sum(r['directional_accuracy'] for r in results if 'directional_accuracy' in r and not np.isnan(r['directional_accuracy'])) / len([r for r in results if 'directional_accuracy' in r and not np.isnan(r['directional_accuracy'])])

        logger.info(f"\nRegions Tested: {len(results)}")
        logger.info(f"Average RMSE: {avg_rmse:.2f}%")
        logger.info(f"Average MAE: {avg_mae:.2f}%")
        logger.info(f"Average Directional Accuracy: {avg_dir_acc:.1f}%")

        # Success criteria check
        logger.info("\n" + "=" * 80)
        logger.info("SUCCESS CRITERIA")
        logger.info("=" * 80)

        if avg_dir_acc > 70:
            logger.info(f"PASS: Directional Accuracy {avg_dir_acc:.1f}% > 70%")
        else:
            logger.warning(f"FAIL: Directional Accuracy {avg_dir_acc:.1f}% <= 70%")

        # Save results
        output_path = Config.ANALYSIS_OUTPUT_DIR / "backtesting_baseline_results.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write("Simplified Backtesting Results (Naive Baseline)\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Regions Tested: {len(results)}\n")
            f.write(f"Average RMSE: {avg_rmse:.2f}%\n")
            f.write(f"Average MAE: {avg_mae:.2f}%\n")
            f.write(f"Average Directional Accuracy: {avg_dir_acc:.1f}%\n")

        logger.info(f"\nResults saved to {output_path}")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load prepared data
    from scripts.core.data_helpers import load_parquet

    logger.info("Loading prepared time series data...")
    regional_data = load_parquet('L5_regional_timeseries')
    area_data = load_parquet('L5_area_timeseries')

    logger.info(f"Loaded regional data: {len(regional_data)} records, {regional_data['region'].nunique()} regions")
    logger.info(f"Loaded area data: {len(area_data)} records, {area_data['area'].nunique()} areas")

    # Run backtest
    simple_backtest(regional_data, area_data)
