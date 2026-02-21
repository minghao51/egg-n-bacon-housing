# scripts/analytics/pipelines/forecast_appreciation.py
"""
Forecasting pipeline for housing appreciation predictions.

Generates multi-scenario forecasts (baseline, bullish, bearish, policy shock)
for regional VAR and planning area ARIMAX models.

Usage:
    from scripts.analytics.pipelines.forecast_appreciation import run_forecasting_pipeline

    forecasts = run_forecasting_pipeline(scenario='baseline', horizon_months=36)
"""

import logging

import pandas as pd

from scripts.analytics.models.area_arimax import AreaARIMAXModel
from scripts.analytics.models.regional_var import RegionalVARModel
from scripts.core.data_helpers import load_parquet
from scripts.core.regional_mapping import get_region_for_planning_area

logger = logging.getLogger(__name__)


def generate_regional_forecasts(
    regional_data: pd.DataFrame,
    horizon_months: int = 36,
    scenario: str = 'baseline'
) -> list[dict]:
    """
    Generate forecasts for all regions.

    Args:
        regional_data: Regional time series data
        horizon_months: Forecast horizon
        scenario: 'baseline', 'bullish', 'bearish', or 'policy_shock'

    Returns:
        List of forecast DataFrames (one per region)
    """
    logger.info(f"Generating regional forecasts: scenario={scenario}, horizon={horizon_months}")

    forecasts = []

    for region in regional_data['region'].unique():
        region_data = regional_data[regional_data['region'] == region].copy()

        try:
            # Fit model
            model = RegionalVARModel(region=region)
            model.fit(region_data, test_size=0)

            # Apply scenario adjustments
            if scenario == 'bullish':
                # Lower interest rates
                if 'sora_rate' in region_data.columns:
                    region_data['sora_rate'] = region_data['sora_rate'] - 0.01
            elif scenario == 'bearish':
                # Higher interest rates
                if 'sora_rate' in region_data.columns:
                    region_data['sora_rate'] = region_data['sora_rate'] + 0.01
            elif scenario == 'policy_shock':
                # Additional ABSD (reduce appreciation)
                region_data['regional_appreciation'] = region_data['regional_appreciation'] - 2.0

            # Re-fit with scenario adjustments
            model.fit(region_data, test_size=0)

            # Generate forecast
            forecast = model.forecast(horizon=horizon_months)
            forecast['region'] = region
            forecast['scenario'] = scenario

            forecasts.append(forecast)

            logger.info(f"  {region}: {len(forecast)} months forecasted")

        except Exception as e:
            logger.error(f"Regional forecast failed for {region}: {e}")
            forecasts.append(None)

    logger.info(f"Generated {len([f for f in forecasts if f is not None])} regional forecasts")

    return forecasts


def generate_area_forecasts(
    area_data: pd.DataFrame,
    regional_forecasts: list[pd.DataFrame],
    horizon_months: int = 24
) -> list[pd.DataFrame]:
    """
    Generate forecasts for planning areas using regional forecasts as inputs.

    Args:
        area_data: Area time series data
        regional_forecasts: Regional forecast DataFrames
        horizon_months: Forecast horizon

    Returns:
        List of forecast DataFrames (one per area)
    """
    logger.info(f"Generating area forecasts: horizon={horizon_months}")

    forecasts = []

    # Create region -> forecast mapping
    regional_fc_dict = {}
    for fc in regional_forecasts:
        if fc is not None and 'region' in fc.columns:
            region = fc['region'].iloc[0]
            regional_fc_dict[region] = fc

    for area in area_data['area'].unique()[:20]:  # Top 20 areas
        area_subset = area_data[area_data['area'] == area].copy()

        if len(area_subset) < 24:
            logger.warning(f"Skipping {area}: insufficient data")
            continue

        # Get parent region
        region = get_region_for_planning_area(area)

        if region is None or region not in regional_fc_dict:
            logger.warning(f"Skipping {area}: unknown region or no regional forecast")
            continue

        regional_fc = regional_fc_dict[region]

        try:
            # Fit model
            model = AreaARIMAXModel(area=area, region=region)

            # Check if required exog vars exist
            required_vars = ['regional_appreciation', 'mrt_within_1km_mean', 'hawker_within_1km_mean']
            available_vars = [v for v in required_vars if v in area_subset.columns]

            if len(available_vars) < 1:
                logger.warning(f"Skipping {area}: insufficient exogenous variables")
                continue

            model.fit(area_subset, exog_vars=available_vars, test_size=0)

            # Prepare regional forecast as exog
            exog_future = pd.DataFrame({
                'month': regional_fc['month'].values[:horizon_months],
                'regional_appreciation': regional_fc['forecast_mean'].values[:horizon_months]
            })

            # Add amenity constants (use last observed value)
            for var in available_vars:
                if var != 'regional_appreciation' and var in area_subset.columns:
                    exog_future[var] = area_subset[var].iloc[-1]

            # Generate forecast
            forecast = model.forecast(horizon=horizon_months, exog_future=exog_future)
            forecast['area'] = area

            forecasts.append(forecast)

            logger.info(f"  {area}: {len(forecast)} months forecasted")

        except Exception as e:
            logger.error(f"Area forecast failed for {area}: {e}")
            continue

    logger.info(f"Generated {len(forecasts)} area forecasts")

    return forecasts


def run_forecasting_pipeline(
    scenario: str = 'baseline',
    horizon_months: int = 36
) -> dict:
    """
    Run complete forecasting pipeline.

    Args:
        scenario: Forecast scenario ('baseline', 'bullish', 'bearish', 'policy_shock')
        horizon_months: Forecast horizon in months

    Returns:
        Dictionary with regional_forecasts, area_forecasts, metadata
    """
    logger.info("=" * 60)
    logger.info("Forecasting Pipeline")
    logger.info(f"Scenario: {scenario}, Horizon: {horizon_months} months")
    logger.info("=" * 60)

    # Load prepared time series data
    try:
        regional_data = load_parquet("L5_regional_timeseries")
        area_data = load_parquet("L5_area_timeseries")
    except Exception as e:
        logger.error(f"Failed to load time series data: {e}")
        return {
            'regional_forecasts': [],
            'area_forecasts': [],
            'metadata': {
                'scenario': scenario,
                'horizon_months': horizon_months,
                'n_regions': 0,
                'n_areas': 0,
                'error': str(e)
            }
        }

    # Generate regional forecasts
    regional_forecasts = generate_regional_forecasts(
        regional_data=regional_data,
        horizon_months=horizon_months,
        scenario=scenario
    )

    # Generate area forecasts
    area_forecasts = generate_area_forecasts(
        area_data=area_data,
        regional_forecasts=regional_forecasts,
        horizon_months=min(horizon_months, 24)  # Cap areas at 24 months
    )

    results = {
        'regional_forecasts': regional_forecasts,
        'area_forecasts': area_forecasts,
        'metadata': {
            'scenario': scenario,
            'horizon_months': horizon_months,
            'n_regions': len([f for f in regional_forecasts if f is not None]),
            'n_areas': len(area_forecasts)
        }
    }

    logger.info("=" * 60)
    logger.info("Forecasting complete!")
    logger.info(f"  Regions: {results['metadata']['n_regions']}")
    logger.info(f"  Areas: {results['metadata']['n_areas']}")
    logger.info("=" * 60)

    return results


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    run_forecasting_pipeline()
