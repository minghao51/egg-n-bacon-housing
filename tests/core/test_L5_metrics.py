"""Tests for scripts.core.stages.L5_metrics."""

import pandas as pd
import pytest

from scripts.core.stages.L5_metrics import (
    calculate_affordability_by_area,
    calculate_growth_metrics_by_area,
    calculate_price_metrics_by_area,
    calculate_rental_yield_by_area,
    calculate_temporal_features,
    calculate_volume_metrics_by_area,
    identify_appreciation_hotspots,
    merge_macro_with_metrics,
)


@pytest.fixture
def sample_transactions():
    dates = pd.date_range("2022-01", periods=24, freq="ME")
    areas = ["Bedok", "Bishan", "Tampines"]
    records = []
    for i, date in enumerate(dates):
        for area in areas:
            records.append(
                {
                    "transaction_date": date,
                    "planning_area": area,
                    "property_type": "HDB",
                    "resale_price": 400000 + i * 5000 + hash(area) % 50000,
                    "area_sqft": 900 + i * 10,
                    "rental_yield_pct": 3.5 + (hash(area) % 10) * 0.1,
                }
            )
    df = pd.DataFrame(records)
    df["year"] = df["transaction_date"].dt.year
    df["month"] = df["transaction_date"].dt.to_period("M").astype(str)
    return df


class TestCalculatePriceMetricsByArea:
    def test_returns_dataframe(self, sample_transactions):
        result = calculate_price_metrics_by_area(sample_transactions)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_includes_planning_area(self, sample_transactions):
        result = calculate_price_metrics_by_area(sample_transactions)
        assert "planning_area" in result.columns

    def test_empty_dataframe_returns_empty(self):
        result = calculate_price_metrics_by_area(pd.DataFrame())
        assert isinstance(result, pd.DataFrame)

    def test_missing_price_column(self):
        df = pd.DataFrame({"planning_area": ["Bedok"], "month": ["2023-01"]})
        result = calculate_price_metrics_by_area(df)
        assert result.empty


class TestCalculateVolumeMetricsByArea:
    def test_returns_dataframe(self, sample_transactions):
        result = calculate_volume_metrics_by_area(sample_transactions)
        assert isinstance(result, pd.DataFrame)
        assert "transaction_count" in result.columns

    def test_missing_required_columns(self):
        df = pd.DataFrame({"col_a": [1, 2, 3]})
        result = calculate_volume_metrics_by_area(df)
        assert result.empty


class TestCalculateGrowthMetricsByArea:
    def test_returns_dataframe(self, sample_transactions):
        result = calculate_growth_metrics_by_area(sample_transactions)
        assert isinstance(result, pd.DataFrame)
        assert "mom_change_pct" in result.columns
        assert "yoy_change_pct" in result.columns
        assert "momentum" in result.columns

    def test_momentum_signal_labels(self, sample_transactions):
        result = calculate_growth_metrics_by_area(sample_transactions)
        assert "momentum_signal" in result.columns
        valid_labels = {
            "Strong Deceleration",
            "Moderate Deceleration",
            "Stable",
            "Moderate Acceleration",
            "Strong Acceleration",
        }
        signals = set(result["momentum_signal"].dropna().unique())
        assert signals.issubset(valid_labels)

    def test_missing_group_column(self):
        df = pd.DataFrame({"resale_price": [500000], "month": ["2023-01"]})
        result = calculate_growth_metrics_by_area(df)
        assert result.empty


class TestCalculateTemporalFeatures:
    def test_adds_lag_columns(self, sample_transactions):
        growth = calculate_growth_metrics_by_area(sample_transactions)
        result = calculate_temporal_features(growth)
        assert "yoy_change_pct_lag1" in result.columns
        assert "yoy_change_pct_lag2" in result.columns
        assert "yoy_change_pct_lag3" in result.columns

    def test_adds_acceleration(self, sample_transactions):
        growth = calculate_growth_metrics_by_area(sample_transactions)
        result = calculate_temporal_features(growth)
        assert "acceleration_2y" in result.columns

    def test_adds_trend_stability(self, sample_transactions):
        growth = calculate_growth_metrics_by_area(sample_transactions)
        result = calculate_temporal_features(growth)
        assert "trend_stability" in result.columns

    def test_missing_column_returns_unchanged(self):
        df = pd.DataFrame({"planning_area": ["Bedok"], "month": ["2023-01"]})
        result = calculate_temporal_features(df)
        assert len(result.columns) == len(df.columns)


class TestCalculateRentalYieldByArea:
    def test_returns_dataframe(self, sample_transactions):
        result = calculate_rental_yield_by_area(sample_transactions)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_missing_column_returns_empty(self):
        df = pd.DataFrame({"planning_area": ["Bedok"], "resale_price": [500000]})
        result = calculate_rental_yield_by_area(df)
        assert result.empty


class TestCalculateAffordabilityByArea:
    def test_returns_dataframe(self, sample_transactions):
        result = calculate_affordability_by_area(sample_transactions)
        assert isinstance(result, pd.DataFrame)
        assert "affordability_ratio" in result.columns
        assert "affordability_class" in result.columns

    def test_affordability_classes(self, sample_transactions):
        result = calculate_affordability_by_area(sample_transactions)
        valid_classes = {"Affordable", "Moderate", "Expensive", "Severely Unaffordable"}
        classes = set(result["affordability_class"].dropna().unique())
        assert classes.issubset(valid_classes)

    def test_missing_columns_returns_empty(self):
        df = pd.DataFrame({"col_a": [1]})
        result = calculate_affordability_by_area(df)
        assert result.empty


class TestIdentifyAppreciationHotspots:
    def test_returns_dataframe(self, sample_transactions):
        growth = calculate_growth_metrics_by_area(sample_transactions)
        result = identify_appreciation_hotspots(growth)
        assert isinstance(result, pd.DataFrame)

    def test_hotspot_categories(self, sample_transactions):
        growth = calculate_growth_metrics_by_area(sample_transactions)
        result = identify_appreciation_hotspots(growth)
        if not result.empty:
            valid_cats = {"Elite Hotspot", "High Growth", "Moderate Growth", "Low Growth"}
            cats = set(result["category"].dropna().unique())
            assert cats.issubset(valid_cats)

    def test_missing_columns_returns_empty(self):
        df = pd.DataFrame({"planning_area": ["Bedok"]})
        result = identify_appreciation_hotspots(df)
        assert result.empty


class TestMergeMacroWithMetrics:
    def test_empty_metrics_returns_empty(self):
        result = merge_macro_with_metrics(pd.DataFrame(), {})
        assert result.empty

    def test_preserves_data_without_macro(self):
        df = pd.DataFrame({"month": ["2023-01"], "value": [100]})
        result = merge_macro_with_metrics(df, {})
        assert len(result) == 1
