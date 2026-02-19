# tests/analytics/test_prepare_timeseries_data.py
import pandas as pd

from scripts.analytics.pipelines.prepare_timeseries_data import (
    aggregate_to_regional_timeseries,
    create_area_timeseries,
    handle_missing_months,
)


def test_aggregate_to_regional_creates_correct_columns():
    """Test regional aggregation creates required columns."""
    # Create sample transaction data with sufficient rows
    dates_list = ['2021-01', '2021-02', '2021-03'] * 12 + ['2021-01', '2021-02'] * 5
    transactions = pd.DataFrame({
        'planning_area': ['Downtown'] * 36 + ['Bedok'] * 10,
        'transaction_date': pd.to_datetime(dates_list),
        'price_psf': [2000, 2100, 2200] * 12 + [800, 820] * 5,
        'yoy_change_pct': [5.0, 5.5, 6.0] * 12 + [3.0, 3.2] * 5,
        'address': ['addr1', 'addr2', 'addr3'] * 12 + ['addr4', 'addr5'] * 5,
        'lat': [1.28] * 46,
    })

    regional = aggregate_to_regional_timeseries(transactions, pd.DataFrame())

    assert 'region' in regional.columns
    assert 'month' in regional.columns
    assert 'regional_appreciation' in regional.columns
    assert 'regional_volume' in regional.columns

def test_handle_missing_months_interpolates():
    """Test missing months are interpolated."""
    dates = pd.date_range('2021-01', periods=6, freq='ME')
    values = pd.Series([1.0, 2.0, None, None, 5.0, 6.0], index=dates)

    filled = handle_missing_months(values, max_gap=2)

    assert filled.isna().sum() == 0
    assert filled.iloc[2] == 3.0  # Linear interpolation (between 2.0 and 5.0)

def test_create_area_timeseries_filters_low_volume_areas():
    """Test low-volume areas are filtered out."""

    # Create area with only 10 months (below MIN_MONTHS_REQUIRED=24)
    # Need to include transaction_date column for the function
    low_volume_area = pd.DataFrame({
        'planning_area': ['SmallArea'] * 10,
        'transaction_date': pd.date_range('2021-01', periods=10, freq='ME'),
        'yoy_change_pct': [5.0] * 10,
        'price_psf': [1000] * 10,
        'address': ['addr1'] * 10,
    })

    filtered = create_area_timeseries(low_volume_area, pd.DataFrame())

    # Should be filtered out due to insufficient months (< MIN_MONTHS_REQUIRED)
    assert len(filtered) == 0
