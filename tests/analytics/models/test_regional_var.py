# tests/analytics/models/test_regional_var.py
import numpy as np
import pandas as pd

from scripts.analytics.models.regional_var import (
    RegionalVARModel,
    check_stationarity,
    select_lag_order,
)


def test_regional_var_model_initialization():
    """Test VAR model can be initialized."""
    model = RegionalVARModel(region='CCR')

    assert model.region == 'CCR'
    assert model.model is None  # Not fitted yet

def test_check_stationarity_with_stationary_series():
    """Test stationarity check identifies stationary series."""
    # Generate stationary AR(1) series
    np.random.seed(42)
    stationary_series = np.random.normal(0, 1, 100)

    is_stationary, p_value = check_stationarity(stationary_series)

    assert bool(is_stationary) is True
    assert p_value < 0.05

def test_select_lag_order_returns_valid_lag():
    """Test lag order selection returns valid lag (1-6)."""
    # Generate VAR(1) data
    np.random.seed(42)
    n_periods = 100
    data_matrix = np.zeros((n_periods, 2))
    for t in range(1, n_periods):
        data_matrix[t] = 0.5 * data_matrix[t-1] + np.random.normal(0, 0.1, 2)

    data = pd.DataFrame(data_matrix, columns=['appreciation', 'volume'])

    lag = select_lag_order(data, max_lag=6)

    assert 1 <= lag <= 6

def test_fit_and_forecast():
    """Test model can be fitted and generate forecasts."""
    # Create sample regional data
    dates = pd.date_range('2021-01', periods=50, freq='ME')
    data = pd.DataFrame({
        'month': dates,
        'regional_appreciation': np.random.normal(5, 2, 50),
        'regional_volume': np.random.normal(100, 20, 50),
        'regional_price_psf': np.random.normal(1500, 300, 50)
    })

    model = RegionalVARModel(region='TestRegion')
    model.fit(data)

    assert model.model is not None
    assert model.lag_order is not None

    # Generate forecast
    forecast = model.forecast(horizon=12)

    assert len(forecast) == 12
    assert 'forecast_mean' in forecast.columns
