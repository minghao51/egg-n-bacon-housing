# tests/core/test_metrics.py
"""Tests for housing market metrics calculations."""

import pandas as pd
import pytest

from scripts.core.metrics import (
    AffordabilityResult,
    calculate_affordability_metrics,
    calculate_affordability_ratio,
    calculate_mortgage_payment,
    classify_affordability,
    compute_monthly_metrics,
    validate_metrics,
)


class TestMortgageCalculation:
    """Test mortgage payment calculations."""

    def test_calculate_mortgage_payment_standard(self):
        """Test standard mortgage calculation."""
        payment = calculate_mortgage_payment(500000)
        assert payment > 0
        assert isinstance(payment, float)

    def test_calculate_mortgage_payment_with_custom_rate(self):
        """Test mortgage with custom interest rate."""
        payment = calculate_mortgage_payment(500000, interest_rate=0.04)
        assert payment > 0

    def test_calculate_mortgage_payment_zero_interest(self):
        """Test mortgage with zero interest rate."""
        payment = calculate_mortgage_payment(500000, interest_rate=0.0)
        assert payment > 0

    def test_calculate_mortgage_payment_100_percent_down(self):
        """Test with 100% down payment (no loan)."""
        payment = calculate_mortgage_payment(500000, down_payment_pct=1.0)
        assert payment == 0


class TestAffordabilityRatio:
    """Test affordability ratio calculations."""

    def test_affordability_ratio_positive_income(self):
        """Test affordability ratio with positive income."""
        ratio = calculate_affordability_ratio(500000, 100000)
        assert ratio == 5.0

    def test_affordability_ratio_zero_income(self):
        """Test affordability ratio with zero income returns nan."""
        ratio = calculate_affordability_ratio(500000, 0)
        import numpy as np

        assert np.isnan(ratio)

    def test_affordability_ratio_negative_income(self):
        """Test affordability ratio with negative income."""
        ratio = calculate_affordability_ratio(500000, -10000)
        import numpy as np

        assert np.isnan(ratio)


class TestAffordabilityClassification:
    """Test affordability classification."""

    def test_classify_affordable(self):
        """Test affordable classification."""
        assert classify_affordability(2.5) == "Affordable"

    def test_classify_moderate(self):
        """Test moderate classification."""
        assert classify_affordability(4.0) == "Moderate"

    def test_classify_expensive(self):
        """Test expensive classification."""
        assert classify_affordability(6.0) == "Expensive"

    def test_classify_severely_unaffordable(self):
        """Test severely unaffordable classification."""
        assert classify_affordability(8.0) == "Severely Unaffordable"


class TestAffordabilityMetrics:
    """Test comprehensive affordability metrics."""

    def test_calculate_affordability_metrics_returns_result(self):
        """Test that affordability metrics returns proper result."""
        result = calculate_affordability_metrics(
            property_price=500000, annual_household_income=100000, planning_area="Bedok"
        )
        assert isinstance(result, AffordabilityResult)
        assert result.planning_area == "Bedok"
        assert result.affordability_ratio == 5.0

    def test_calculate_affordability_metrics_all_fields(self):
        """Test all fields are populated."""
        result = calculate_affordability_metrics(
            property_price=400000, annual_household_income=100000
        )
        assert result.median_price == 400000
        assert result.estimated_annual_income == 100000
        assert result.monthly_mortgage > 0
        assert result.mortgage_to_income_pct > 0
        assert result.months_of_income > 0
        # 400000/100000 = 4.0 which is "Moderate" (< 5.0)
        assert result.affordability_class == "Moderate"


class TestMonthlyMetrics:
    """Test monthly metrics computation."""

    @pytest.fixture
    def sample_unified_df(self):
        """Create sample unified transaction DataFrame."""
        dates = pd.date_range("2023-01", periods=12, freq="ME")
        return pd.DataFrame(
            {
                "month": dates,
                "property_type": ["HDB"] * 12,
                "planning_area": ["Bedok"] * 12,
                "price": [400000 + i * 5000 for i in range(12)],
                "floor_area_sqft": [900] * 12,
                "transaction_date": dates,
            }
        )

    def test_compute_monthly_metrics_returns_dataframe(self, sample_unified_df):
        """Test monthly metrics computation returns DataFrame."""
        result = compute_monthly_metrics(sample_unified_df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_compute_monthly_metrics_has_required_columns(self, sample_unified_df):
        """Test monthly metrics has required columns."""
        result = compute_monthly_metrics(sample_unified_df)
        required_cols = ["month", "property_type", "planning_area", "stratified_median_price"]
        for col in required_cols:
            assert col in result.columns, f"Missing column: {col}"


class TestValidateMetrics:
    """Test metrics validation."""

    def test_validate_metrics_returns_dict(self):
        """Test validation returns proper dict structure."""
        df = pd.DataFrame(
            {
                "month": pd.date_range("2023-01", periods=3, freq="ME"),
                "property_type": ["HDB"] * 3,
                "planning_area": ["Bedok"] * 3,
                "stratified_median_price": [400000, 410000, 420000],
                "growth_rate": [0.02, 0.025, 0.03],
                "transaction_count": [100, 110, 120],
            }
        )
        result = validate_metrics(df)
        assert isinstance(result, dict)
        assert "total_records" in result
        assert "missing_values" in result
        assert "outliers" in result

    def test_validate_metrics_detects_issues(self):
        """Test validation detects issues."""
        df = pd.DataFrame(
            {
                "month": pd.date_range("2023-01", periods=3, freq="ME"),
                "property_type": ["HDB"] * 3,
                "planning_area": ["Bedok"] * 3,
                "stratified_median_price": [400000, None, 420000],
                "growth_rate": [0.02, 0.025, 0.03],
                "transaction_count": [100, 110, 120],
            }
        )
        result = validate_metrics(df)
        # Check missing values are detected
        assert result["missing_values"]["stratified_median_price"] > 0
