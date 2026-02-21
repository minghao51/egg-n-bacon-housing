# scripts/analytics/models/regional_var.py
"""
Regional VAR (Vector Autoregression) model for housing appreciation forecasting.

This module implements Stage 1 of the two-stage hierarchical VAR approach:
- Estimate regional VAR with endogenous variables (appreciation, volume, price)
- Include exogenous macroeconomic variables (interest rate, CPI, GDP)
- Provide forecasting with confidence intervals
- Enable causal inference (Granger causality, IRF, FEVD)

Usage:
    from scripts.analytics.models.regional_var import RegionalVARModel

    model = RegionalVARModel(region='CCR')
    model.fit(regional_data)
    forecast = model.forecast(horizon=36)
"""

import logging

import numpy as np
import pandas as pd
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

logger = logging.getLogger(__name__)


def check_stationarity(series, significance_level: float = 0.05) -> tuple[bool, float]:
    """
    Check if time series is stationary using Augmented Dickey-Fuller test.

    Args:
        series: Time series data (pd.Series or np.array)
        significance_level: Threshold for rejecting null hypothesis

    Returns:
        Tuple of (is_stationary, p_value)
    """
    try:
        # Convert to Series if needed
        if not isinstance(series, pd.Series):
            series = pd.Series(series)

        # Drop NaN values
        series_clean = series.dropna()

        if len(series_clean) < 20:
            logger.warning("Series too short for stationarity test, assuming non-stationary")
            return False, 1.0

        # Run ADF test
        result = adfuller(series_clean, autolag='AIC')

        p_value = result[1]
        is_stationary = p_value < significance_level

        return is_stationary, p_value

    except Exception as e:
        logger.error(f"Stationarity test failed: {e}")
        return False, 1.0


def select_lag_order(data: pd.DataFrame, max_lag: int = 6) -> int:
    """
    Select optimal lag order for VAR model using AIC.

    Args:
        data: Time series data (endogenous variables only)
        max_lag: Maximum lag order to test

    Returns:
        Optimal lag order (1-6)
    """
    try:
        model = VAR(data)
        lag_order = model.select_order(maxlags=max_lag)

        # Use AIC (Akaike Information Criterion)
        selected_lag = lag_order.aic

        # Ensure lag is within bounds
        selected_lag = max(1, min(selected_lag, max_lag))

        return selected_lag

    except Exception as e:
        logger.error(f"Lag selection failed: {e}")
        return 3  # Default fallback


class RegionalVARModel:
    """Regional VAR model for housing appreciation forecasting."""

    def __init__(self, region: str):
        """
        Initialize regional VAR model.

        Args:
            region: Region name (e.g., 'CCR', 'RCR')
        """
        self.region = region
        self.model: VAR | None = None
        self.lag_order: int | None = None
        self.endog_vars: list = []
        self.exog_vars: list = []
        self.is_fitted = False

        # Data splits
        self.Y_train: pd.DataFrame | None = None
        self.X_train: pd.DataFrame | None = None
        self.Y_test: pd.DataFrame | None = None
        self.X_test: pd.DataFrame | None = None

    def fit(
        self,
        data: pd.DataFrame,
        endog_vars: list = None,
        exog_vars: list = None,
        test_size: int = 12
    ):
        """
        Fit regional VAR model.

        Args:
            data: Regional time series data
            endog_vars: Endogenous variable names (default: appreciation, volume, price_psf)
            exog_vars: Exogenous variable names (default: sora_rate, cpi, gdp_growth)
            test_size: Number of months to hold out for testing
        """
        logger.info(f"Fitting VAR model for region: {self.region}")

        # Default variables
        if endog_vars is None:
            endog_vars = ['regional_appreciation', 'regional_volume', 'regional_price_psf']
        if exog_vars is None:
            exog_vars = ['sora_rate', 'cpi', 'gdp_growth']

        self.endog_vars = endog_vars
        self.exog_vars = exog_vars

        # Prepare data
        data = data.sort_values('month').reset_index(drop=True)

        # Check stationarity and apply differencing if needed
        Y = data[endog_vars].copy()

        for var in endog_vars:
            if var in Y.columns:
                is_stationary, p_value = check_stationarity(Y[var])

                if not is_stationary:
                    logger.info(f"{var} is non-stationary (p={p_value:.3f}), applying first difference")
                    Y[var] = Y[var].diff()

        # Drop NaN from differencing
        Y = Y.dropna()

        # Prepare exogenous variables
        X = None
        if all(v in data.columns for v in exog_vars):
            # Align X with Y after differencing
            X = data[exog_vars].loc[Y.index] if len(Y) < len(data) else data[exog_vars]

        # Train/test split
        if test_size > 0:
            split_idx = len(Y) - test_size
            self.Y_train = Y.iloc[:split_idx]
            self.Y_test = Y.iloc[split_idx:]
            self.X_train = X.iloc[:split_idx] if X is not None else None
            self.X_test = X.iloc[split_idx:] if X is not None else None
        else:
            self.Y_train = Y
            self.X_train = X
            self.Y_test = None
            self.X_test = None

        logger.info(f"Train size: {len(self.Y_train)}, Test size: {len(self.Y_test) if self.Y_test is not None else 0}")

        # Select lag order
        self.lag_order = select_lag_order(self.Y_train, max_lag=6)
        logger.info(f"Selected lag order: {self.lag_order}")

        # Fit VAR model
        try:
            if self.X_train is not None and not self.X_train.empty:
                self.model = VAR(endog=self.Y_train, exog=self.X_train).fit(self.lag_order)
            else:
                self.model = VAR(endog=self.Y_train).fit(self.lag_order)

            self.is_fitted = True
            logger.info(f"VAR model fitted successfully for {self.region}")

        except Exception as e:
            logger.error(f"VAR fitting failed for {self.region}: {e}")
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

        logger.info(f"Generating {horizon}-month forecast for {self.region}")

        try:
            # Generate forecast
            forecast_result = self.model.forecast(
                y=self.Y_train.values,
                steps=horizon,
                exog_future=exog_future.values if exog_future is not None else None
            )

            # Get confidence intervals
            # Note: statsmodels VAR forecast doesn't directly support CIs
            # We'll use a simple approximation based on residual std
            forecast_mean = forecast_result[:, 0]  # First variable = appreciation

            # Calculate residual std from training
            # resid is a DataFrame, get first column
            residuals = self.model.resid.iloc[:, 0]  # Appreciation residuals
            residual_std = residuals.std()

            # Approximate CI: mean ± z * std * sqrt(horizon)
            # z = 1.96 for 95% CI
            ci_half_width = 1.96 * residual_std * np.sqrt(np.arange(1, horizon + 1))

            ci_lower = forecast_mean - ci_half_width
            ci_upper = forecast_mean + ci_half_width

            # Create forecast DataFrame
            last_month = self.Y_train.index[-1]
            forecast_months = pd.date_range(start=last_month, periods=horizon + 1, freq='ME')[1:]

            forecast_df = pd.DataFrame({
                'month': forecast_months,
                'forecast_mean': forecast_mean,
                'ci_lower_95': ci_lower,
                'ci_upper_95': ci_upper
            })

            return forecast_df

        except Exception as e:
            logger.error(f"Forecasting failed for {self.region}: {e}")
            raise

    def granger_causality_tests(self, variable: str = 'regional_appreciation') -> dict[str, float]:
        """
        Perform Granger causality tests for appreciation.

        Args:
            variable: Target variable to test (default: appreciation)

        Returns:
            Dictionary of variable -> p_value for Granger causality
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before Granger tests")

        logger.info(f"Performing Granger causality tests for {self.region}")

        # Prepare data with all variables
        all_vars = self.endog_vars
        data = self.Y_train[all_vars]

        results = {}

        for test_var in all_vars:
            if test_var == variable:
                continue

            try:
                # Test if test_var Granger-causes variable
                test_data = data[[variable, test_var]]
                gc_result = grangercausalitytests(test_data, maxlag=2, verbose=False)

                # Extract p-value from F-test (lag=1)
                p_value = gc_result[1][0]['ssr_ftest'][1]

                results[test_var] = p_value

                logger.info(f"  {test_var} -> {variable}: p = {p_value:.4f}")

            except Exception as e:
                logger.warning(f"Granger test failed for {test_var}: {e}")
                results[test_var] = 1.0  # Fail-safe: not significant

        return results

    def evaluate(self) -> dict[str, float]:
        """
        Evaluate model on test set.

        Returns:
            Dictionary with RMSE, MAE, MAPE
        """
        if self.Y_test is None or self.Y_test.empty:
            logger.warning("No test set available for evaluation")
            return {}

        logger.info(f"Evaluating model for {self.region}")

        # Generate forecast for test period
        try:
            forecast = self.forecast(
                horizon=len(self.Y_test),
                exog_future=self.X_test
            )

            # Compare to actual (first variable = appreciation)
            actual = self.Y_test['regional_appreciation'].values
            predicted = forecast['forecast_mean'].values

            # Calculate metrics
            rmse = np.sqrt(np.mean((actual - predicted) ** 2))
            mae = np.mean(np.abs(actual - predicted))
            mape = np.mean(np.abs((actual - predicted) / actual)) * 100

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
