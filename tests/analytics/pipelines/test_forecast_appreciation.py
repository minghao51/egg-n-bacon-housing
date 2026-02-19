# tests/analytics/pipelines/test_forecast_appreciation.py
import pandas as pd

from scripts.analytics.pipelines.forecast_appreciation import (
    generate_regional_forecasts,
    run_forecasting_pipeline,
)


def test_generate_regional_forecasts():
    """Test regional forecast generation."""
    # Create sample regional data
    dates = pd.date_range('2021-01', periods=50, freq='ME')
    data = pd.DataFrame({
        'month': dates,
        'region': ['CCR'] * 50,
        'regional_appreciation': [5.0 + i * 0.1 for i in range(50)],
        'regional_volume': [100] * 50,
        'regional_price_psf': [1500] * 50,
        'sora_rate': [2.0] * 50,
        'cpi': [100] * 50,
        'gdp_growth': [0.03] * 50
    })

    forecasts = generate_regional_forecasts(
        regional_data=data,
        horizon_months=12
    )

    assert len(forecasts) == 1  # Should have forecasts (even if some fail)
    # Check that forecast has the required columns
    if forecasts[0] is not None:
        assert 'forecast_mean' in forecasts[0].columns

def test_run_forecasting_pipeline():
    """Test complete forecasting pipeline."""
    # This test uses mock data since we don't have the actual L5 datasets yet
    from unittest.mock import patch

    # Mock the load_parquet function to return sample data
    mock_regional_data = pd.DataFrame({
        'month': pd.date_range('2021-01', periods=50, freq='ME'),
        'region': ['CCR'] * 50,
        'regional_appreciation': [5.0 + i * 0.1 for i in range(50)],
        'regional_volume': [100] * 50,
        'regional_price_psf': [1500] * 50,
        'sora_rate': [2.0] * 50,
        'cpi': [100] * 50,
        'gdp_growth': [0.03] * 50
    })

    mock_area_data = pd.DataFrame({
        'month': pd.date_range('2021-01', periods=50, freq='ME'),
        'area': ['Downtown'] * 50,
        'area_appreciation': [5.0 + i * 0.1 for i in range(50)],
        'regional_appreciation': [5.0 + i * 0.1 for i in range(50)],
        'mrt_within_1km_mean': [1] * 50,
        'hawker_within_1km_mean': [1] * 50
    })

    with patch('scripts.analytics.pipelines.forecast_appreciation.load_parquet') as mock_load:
        # Setup mock to return appropriate data based on dataset name
        def load_side_effect(dataset_name):
            if 'regional' in dataset_name:
                return mock_regional_data
            elif 'area' in dataset_name:
                return mock_area_data
            return pd.DataFrame()

        mock_load.side_effect = load_side_effect

        results = run_forecasting_pipeline(
            scenario='baseline',
            horizon_months=12
        )

    assert 'regional_forecasts' in results
    assert 'area_forecasts' in results
