"""Tests for components/05_metrics.py — rental yield in pa_monthly_metrics."""

import importlib

import pandas as pd
import pytest

pytestmark = pytest.mark.unit


def _get_metrics_module():
    return importlib.import_module("egg_n_bacon_housing.components.05_metrics")


class TestRentalYieldInPaMonthly:
    def test_computes_expected_columns(self, tmp_path):
        metrics = _get_metrics_module()
        platinum_dir = tmp_path / "platinum"

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "price": 500000.0,
                    "rental_yield_pct": 4.5,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "planning_area": "Toa Payoh",
                    "price": 520000.0,
                    "rental_yield_pct": 5.0,
                    "transaction_date": pd.Timestamp("2024-01-20"),
                },
            ]
        )

        result = metrics.pa_monthly_metrics(df, platinum_dir)

        assert not result.empty
        assert "median_rental_yield" in result.columns
        assert "avg_rental_yield" in result.columns
        assert result.iloc[0]["median_rental_yield"] == pytest.approx(4.75)
        assert result.iloc[0]["avg_rental_yield"] == pytest.approx(4.75)

    def test_empty_input(self, tmp_path):
        metrics = _get_metrics_module()

        result = metrics.pa_monthly_metrics(pd.DataFrame(), tmp_path / "platinum")
        assert result.empty

    def test_without_rental_yield_column(self, tmp_path):
        metrics = _get_metrics_module()

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
            ]
        )

        result = metrics.pa_monthly_metrics(df, tmp_path / "platinum")
        assert not result.empty
        assert "median_rental_yield" not in result.columns

    def test_single_data_point(self, tmp_path):
        metrics = _get_metrics_module()

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Bishan",
                    "price": 600000.0,
                    "rental_yield_pct": 3.8,
                    "transaction_date": pd.Timestamp("2024-06-01"),
                }
            ]
        )

        result = metrics.pa_monthly_metrics(df, tmp_path / "platinum")
        assert len(result) == 1
        assert result.iloc[0]["median_rental_yield"] == pytest.approx(3.8)

    def test_multiple_areas_grouped_separately(self, tmp_path):
        metrics = _get_metrics_module()

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "price": 500000.0,
                    "rental_yield_pct": 4.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
                {
                    "planning_area": "Bishan",
                    "price": 800000.0,
                    "rental_yield_pct": 3.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
                {
                    "planning_area": "Toa Payoh",
                    "price": 550000.0,
                    "rental_yield_pct": 5.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
            ]
        )

        result = metrics.pa_monthly_metrics(df, tmp_path / "platinum")
        assert len(result) == 2

        tp = result[result["planning_area"] == "Toa Payoh"]
        assert tp.iloc[0]["median_rental_yield"] == pytest.approx(4.5)

    def test_saves_parquet(self, tmp_path):
        metrics = _get_metrics_module()
        platinum_dir = tmp_path / "platinum"

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "price": 500000.0,
                    "rental_yield_pct": 4.5,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                }
            ]
        )

        metrics.pa_monthly_metrics(df, platinum_dir)

        out_path = platinum_dir / "metrics" / "pa_monthly_metrics.parquet"
        assert out_path.exists()
