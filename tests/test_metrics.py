"""Tests for components/05_metrics.py."""

import importlib

import pandas as pd
import pytest

pytestmark = pytest.mark.unit


def _get_metrics_module():
    return importlib.import_module("egg_n_bacon_housing.components.05_metrics")


class TestPaMonthlyMetrics:
    def test_pa_monthly_metrics_produces_expected_columns(self, tmp_path):
        metrics = _get_metrics_module()
        platinum_dir = tmp_path / "platinum"

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                    "psf": 500.0,
                },
                {
                    "planning_area": "Toa Payoh",
                    "price": 520000.0,
                    "transaction_date": pd.Timestamp("2024-01-20"),
                    "psf": 520.0,
                },
            ]
        )

        result = metrics.pa_monthly_metrics(df, platinum_dir=platinum_dir)

        assert not result.empty
        assert "median_price" in result.columns
        assert "mean_price" in result.columns
        assert "transaction_count" in result.columns
        assert "avg_psf" in result.columns
        assert "affordability_ratio" in result.columns
        assert "affordability_class" in result.columns
        assert result.loc[0, "median_price"] == 510000.0
        assert result.loc[0, "avg_psf"] == pytest.approx(510.0)

    def test_pa_monthly_metrics_empty_input(self, tmp_path):
        metrics = _get_metrics_module()

        result = metrics.pa_monthly_metrics(pd.DataFrame(), platinum_dir=tmp_path / "platinum")

        assert result.empty

    def test_pa_monthly_metrics_missing_planning_area(self, tmp_path):
        metrics = _get_metrics_module()

        df = pd.DataFrame([{"price": 500000.0, "transaction_date": pd.Timestamp("2024-01-15")}])

        result = metrics.pa_monthly_metrics(df, platinum_dir=tmp_path / "platinum")

        assert result.empty

    def test_pa_monthly_metrics_without_psf(self, tmp_path):
        metrics = _get_metrics_module()

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        result = metrics.pa_monthly_metrics(df, platinum_dir=tmp_path / "platinum")

        assert not result.empty
        assert "avg_psf" not in result.columns

    def test_pa_monthly_metrics_with_rental_yield(self, tmp_path):
        metrics = _get_metrics_module()

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                    "rental_yield_pct": 3.5,
                },
            ]
        )

        result = metrics.pa_monthly_metrics(df, platinum_dir=tmp_path / "platinum")

        assert not result.empty
        assert "median_rental_yield" in result.columns


class TestAffordabilityInPaMonthly:
    def test_affordability_uses_config_income(self, tmp_path):
        metrics = _get_metrics_module()

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        result = metrics.pa_monthly_metrics(
            df,
            platinum_dir=tmp_path / "platinum",
            median_household_income=100000,
        )

        assert not result.empty
        assert result.loc[0, "affordability_ratio"] == pytest.approx(5.0)

    @pytest.mark.parametrize(
        "price,expected_class",
        [
            (400000.0, "Affordable"),
            (550000.0, "Moderate"),
            (700000.0, "Expensive"),
            (900000.0, "Severely Unaffordable"),
        ],
    )
    def test_affordability_classification(self, tmp_path, price, expected_class):
        metrics = _get_metrics_module()

        df = pd.DataFrame(
            [
                {
                    "planning_area": "TestArea",
                    "price": price,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
            ]
        )

        result = metrics.pa_monthly_metrics(
            df,
            platinum_dir=tmp_path / "platinum",
            median_household_income=85000,
        )

        assert not result.empty
        assert result.loc[0, "affordability_class"] == expected_class


class TestAppreciationHotspots:
    def test_contiguous_months_produce_correct_pct_change(self, tmp_path, monkeypatch):
        metrics = _get_metrics_module()

        rows = []
        for i in range(13):
            month = f"2024-{i + 1:02d}" if i < 12 else "2025-01"
            rows.append(
                {
                    "planning_area": "Toa Payoh",
                    "month": month,
                    "median_price": 500000.0 + i * 10000,
                }
            )

        df = pd.DataFrame(rows)

        result = metrics.appreciation_hotspots(df, platinum_dir=tmp_path / "platinum")

        assert not result.empty
        assert "appreciation_3m_pct" in result.columns
        assert "appreciation_12m_pct" in result.columns

        three_m = result[result["month"] == "2025-01"]
        assert not three_m.empty
        expected_3m = (620000.0 - 590000.0) / 590000.0 * 100
        assert three_m.iloc[0]["appreciation_3m_pct"] == pytest.approx(expected_3m, rel=1e-3)

    def test_gaps_in_months_handled_correctly(self, tmp_path, monkeypatch):
        metrics = _get_metrics_module()

        rows = [
            {"planning_area": "Toa Payoh", "month": "2024-01", "median_price": 500000.0},
            {"planning_area": "Toa Payoh", "month": "2024-02", "median_price": 510000.0},
            {"planning_area": "Toa Payoh", "month": "2024-05", "median_price": 540000.0},
            {"planning_area": "Toa Payoh", "month": "2024-06", "median_price": 550000.0},
        ]

        df = pd.DataFrame(rows)

        result = metrics.appreciation_hotspots(df, platinum_dir=tmp_path / "platinum")

        if not result.empty:
            for _, row in result.iterrows():
                assert row["appreciation_3m_pct"] > 0
