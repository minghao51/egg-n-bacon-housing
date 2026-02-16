# tests/analytics/models/test_area_arimax.py
import pytest
import pandas as pd
import numpy as np
from scripts.analytics.models.area_arimax import (
    AreaARIMAXModel,
    select_arima_order
)

def test_area_arimax_initialization():
    """Test ARIMAX model can be initialized."""
    model = AreaARIMAXModel(area='Downtown', region='CCR')

    assert model.area == 'Downtown'
    assert model.region == 'CCR'
    assert model.model is None

def test_select_arima_order():
    """Test ARIMA order selection."""
    # Generate AR(2) series
    np.random.seed(42)
    T = 100
    series = np.zeros(T)
    for t in range(2, T):
        series[t] = 0.5 * series[t-1] + 0.3 * series[t-2] + np.random.normal(0, 0.1)

    order = select_arima_order(series, max_p=6)

    assert order[0] >= 1  # AR order >= 1
    assert order[1] == 0  # No differencing (stationary)
    assert order[2] >= 0  # MA order

def test_fit_and_forecast():
    """Test ARIMAX can be fitted and forecast."""
    # Create sample area data
    dates = pd.date_range('2021-01', periods=50, freq='ME')
    data = pd.DataFrame({
        'month': dates,
        'area_appreciation': np.random.normal(5, 2, 50),
        'regional_appreciation': np.random.normal(5, 2, 50),
        'mrt_within_1km_mean': np.random.randint(0, 3, 50),
        'hawker_within_1km_mean': np.random.randint(0, 3, 50)
    })

    model = AreaARIMAXModel(area='Downtown', region='CCR')
    model.fit(data)

    assert model.is_fitted

    # Forecast
    forecast = model.forecast(horizon=12, exog_future=pd.DataFrame({
        'month': pd.date_range('2025-03', periods=12, freq='ME'),
        'regional_appreciation': np.random.normal(5, 2, 12),
        'mrt_within_1km_mean': [1] * 12,
        'hawker_within_1km_mean': [1] * 12
    }))

    assert len(forecast) == 12
    assert 'forecast_mean' in forecast.columns
