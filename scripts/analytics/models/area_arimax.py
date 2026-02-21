# scripts/analytics/models/area_arimax.py
"""
Planning Area ARIMAX model for housing appreciation forecasting.

This module implements Stage 2 of the two-stage hierarchical VAR approach:
- Estimate ARIMAX models for individual planning areas
- Use regional VAR forecasts as exogenous predictors
- Include local amenity features (MRT, hawker, school)
- Generate forecasts with uncertainty quantification

Usage:
    from scripts.analytics.models.area_arimax import AreaARIMAXModel

    model = AreaARIMAXModel(area='Downtown', region='CCR')
    model.fit(area_data, regional_forecast)
    forecast = model.forecast(horizon=12, regional_forecast)
"""

import logging

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA

logger = logging.getLogger(__name__)


def select_arima_order(
    series: pd.Series,
    max_p: int = 6,
    max_d: int = 1,
    max_q: int = 1
) -> tuple:
    """
    Select optimal ARIMA order using grid search with AIC.

    Args:
        series: Time series data
        max_p: Maximum AR order
        max_d: Maximum differencing order
        max_q: Maximum MA order

    Returns:
        Tuple of (p, d, q) order
    """
    best_aic = float('inf')
    best_order = (1, 0, 0)  # Default fallback

    # Convert to Series if needed
    if not isinstance(series, pd.Series):
        series = pd.Series(series)

    series_clean = series.dropna()

    if len(series_clean) < 30:
        logger.warning("Series too short for order selection, using (1,0,0)")
        return best_order

    # Grid search
    for p in range(1, max_p + 1):
        for d in range(max_d + 1):
            for q in range(max_q + 1):
                try:
                    model = ARIMA(series_clean, order=(p, d, q))
                    fitted = model.fit()

                    if fitted.aic < best_aic:
                        best_aic = fitted.aic
                        best_order = (p, d, q)

                except Exception:
                    continue

    logger.info(f"Selected ARIMA order: {best_order} (AIC={best_aic:.2f})")

    return best_order


class AreaARIMAXModel:
    """Planning area ARIMAX model with regional forecasts as exogenous predictors."""

    def __init__(self, area: str, region: str):
        """
        Initialize area ARIMAX model.

        Args:
            area: Planning area name (e.g., 'Downtown')
            region: Parent region name (e.g., 'CCR')
        """
        self.area = area
        self.region = region
        self.model: ARIMA | None = None
        self.order: tuple | None = None
        self.exog_vars: list = []
        self.is_fitted = False

        # Training data
        self.y_train: pd.Series | None = None
        self.X_train: pd.DataFrame | None = None
        self.y_test: pd.Series | None = None
        self.X_test: pd.DataFrame | None = None

    def fit(
        self,
        data: pd.DataFrame,
        endog_var: str = 'area_appreciation',
        exog_vars: list = None,
        test_size: int = 12
    ):
        """
        Fit ARIMAX model for planning area.

        Args:
            data: Area time series data
            endog_var: Target variable name
            exog_vars: Exogenous variable names (regional forecast + amenities)
            test_size: Test set size (months)
        """
        logger.info(f"Fitting ARIMAX model for area: {self.area}")

        # Default exogenous variables
        if exog_vars is None:
            exog_vars = ['regional_appreciation', 'mrt_within_1km_mean', 'hawker_within_1km_mean']

        # Filter to available variables
        available_exog = [v for v in exog_vars if v in data.columns]
        self.exog_vars = available_exog

        logger.info(f"Endogenous: {endog_var}, Exogenous: {available_exog}")

        # Prepare data
        data = data.sort_values('month').reset_index(drop=True)

        y = data[endog_var].copy()
        X = data[available_exog].copy() if available_exog else None

        # Train/test split
        if test_size > 0:
            split_idx = len(y) - test_size
            self.y_train = y.iloc[:split_idx]
            self.y_test = y.iloc[split_idx:]
            self.X_train = X.iloc[:split_idx] if X is not None else None
            self.X_test = X.iloc[split_idx:] if X is not None else None
        else:
            self.y_train = y
            self.X_train = X
            self.y_test = None
            self.X_test = None

        logger.info(f"Train size: {len(self.y_train)}, Test size: {len(self.y_test) if self.y_test is not None else 0}")

        # Check stationarity
        from scripts.analytics.models.regional_var import check_stationarity

        is_stationary, p_value = check_stationarity(self.y_train)

        if not is_stationary:
            logger.info(f"Series non-stationary (p={p_value:.3f}), applying differencing")
            self.y_train = self.y_train.diff().dropna()
            # Align X with differenced y
            if self.X_train is not None:
                self.X_train = self.X_train.iloc[1:]
                if self.y_test is not None:
                    # Also adjust test indices if needed
                    self.y_test = self.y_test.iloc[1:]
                    self.X_test = self.X_test.iloc[1:] if self.X_test is not None else None

        # Select ARIMA order
        self.order = select_arima_order(self.y_train, max_p=6, max_d=1, max_q=1)

        # Fit model
        try:
            if self.X_train is not None and not self.X_train.empty:
                self.model = ARIMA(
                    endog=self.y_train,
                    exog=self.X_train,
                    order=self.order
                ).fit()
            else:
                self.model = ARIMA(
                    endog=self.y_train,
                    order=self.order
                ).fit()

            self.is_fitted = True
            logger.info(f"ARIMAX{self.order} fitted successfully for {self.area}")

        except Exception as e:
            logger.error(f"ARIMAX fitting failed for {self.area}: {e}")
            raise

        return self

    def forecast(
        self,
        horizon: int = 12,
        exog_future: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Generate forecasts with confidence intervals.

        Args:
            horizon: Forecast horizon (months)
            exog_future: Future exogenous variables (required if model has exog)

        Returns:
            DataFrame with columns: month, forecast_mean, ci_lower_95, ci_upper_95
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before forecasting")

        logger.info(f"Generating {horizon}-month forecast for {self.area}")

        try:
            # Prepare future exogenous variables
            X_future = None
            if self.exog_vars and exog_future is not None:
                X_future = exog_future[self.exog_vars]
                # Make sure X_future has the right length
                if len(X_future) < horizon:
                    logger.warning(f"exog_future has {len(X_future)} rows but horizon is {horizon}")

            # Generate forecast
            forecast_result = self.model.get_forecast(
                steps=horizon,
                exog=X_future
            )

            # Extract forecast and confidence intervals
            forecast_mean = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=0.05)

            # Create forecast DataFrame
            last_date = self.y_train.index[-1]
            forecast_months = pd.date_range(start=last_date, periods=horizon + 1, freq='ME')[1:]

            forecast_df = pd.DataFrame({
                'month': forecast_months,
                'forecast_mean': forecast_mean.values,
                'ci_lower_95': conf_int.iloc[:, 0].values,
                'ci_upper_95': conf_int.iloc[:, 1].values
            })

            return forecast_df

        except Exception as e:
            logger.error(f"Forecasting failed for {self.area}: {e}")
            raise

    def evaluate(self, actual: pd.Series = None) -> dict:
        """
        Evaluate model against actual values.

        Args:
            actual: Actual appreciation values (uses test set if None)

        Returns:
            Dictionary with RMSE, MAE, MAPE
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before evaluation")

        logger.info(f"Evaluating model for {self.area}")

        # Use test set if actual not provided
        if actual is None:
            actual = self.y_test

        if actual is None or actual.empty:
            logger.warning("No actual values available for evaluation")
            return {}

        try:
            # Generate forecast for same period as actual
            forecast = self.forecast(
                horizon=len(actual),
                exog_future=self.X_test
            )

            # Compare to actual
            actual_values = actual.values
            predicted_values = forecast['forecast_mean'].values

            # Calculate metrics
            rmse = np.sqrt(np.mean((actual_values - predicted_values) ** 2))
            mae = np.mean(np.abs(actual_values - predicted_values))

            # MAPE (handle zeros)
            mask = actual_values != 0
            if mask.sum() > 0:
                mape = np.mean(np.abs((actual_values[mask] - predicted_values[mask]) / actual_values[mask])) * 100
            else:
                mape = np.nan

            metrics = {
                'rmse': rmse,
                'mae': mae,
                'mape': mape
            }

            logger.info(f"  RMSE: {rmse:.2f}, MAE: {mae:.2f}, MAPE: {mape:.2f}%")

            return metrics

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {}
