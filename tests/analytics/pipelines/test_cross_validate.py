# tests/analytics/pipelines/test_cross_validate.py
import pandas as pd

from scripts.analytics.pipelines.cross_validate_timeseries import (
    evaluate_model_performance,
    run_rolling_validation,
)


def test_rolling_validation_returns_metrics():
    """Test rolling validation returns performance metrics."""
    # Create sample regional data
    dates = pd.date_range("2021-01", periods=48, freq="ME")
    data = pd.DataFrame(
        {
            "month": dates,
            "region": ["CCR"] * 48,
            "regional_appreciation": [5.0 + i * 0.1 for i in range(48)],
            "regional_volume": [100] * 48,
            "regional_price_psf": [1500] * 48,
        }
    )

    results = run_rolling_validation(data=data, region="CCR", n_folds=3, forecast_horizon=6)

    assert "fold_metrics" in results
    assert "mean_rmse" in results
    assert len(results["fold_metrics"]) == 3


def test_evaluate_model_performance():
    """Test performance evaluation."""
    actual = pd.Series([5.0, 5.5, 6.0, 6.5])
    forecast = pd.Series([5.2, 5.3, 6.1, 6.8])

    metrics = evaluate_model_performance(actual, forecast)

    assert "rmse" in metrics
    assert "mae" in metrics
    assert metrics["rmse"] > 0
