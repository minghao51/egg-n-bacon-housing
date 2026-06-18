"""Tests for components/05_metrics.py — rental yield in pa_monthly_metrics."""

import pandas as pd
import pytest

from egg_n_bacon_housing.utils.layer_writer import SimpleWriter

pytestmark = pytest.mark.unit


def _get_metrics_module():
    from egg_n_bacon_housing.components import metrics

    return metrics


class TestRentalYieldInPaMonthly:
    def test_computes_expected_columns(self, tmp_path):
        metrics = _get_metrics_module()
        writer = SimpleWriter(tmp_path)

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

        result = metrics.pa_monthly_metrics(df, writer)

        assert not result.empty
        assert "median_rental_yield" in result.columns
        assert "avg_rental_yield" in result.columns
        assert result.iloc[0]["median_rental_yield"] == pytest.approx(4.75)
        assert result.iloc[0]["avg_rental_yield"] == pytest.approx(4.75)

    def test_empty_input(self, tmp_path):
        metrics = _get_metrics_module()

        result = metrics.pa_monthly_metrics(pd.DataFrame(), SimpleWriter(tmp_path))
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

        result = metrics.pa_monthly_metrics(df, SimpleWriter(tmp_path))
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

        result = metrics.pa_monthly_metrics(df, SimpleWriter(tmp_path))
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

        result = metrics.pa_monthly_metrics(df, SimpleWriter(tmp_path))
        assert len(result) == 2

        tp = result[result["planning_area"] == "Toa Payoh"]
        assert tp.iloc[0]["median_rental_yield"] == pytest.approx(4.5)

    def test_saves_parquet(self, tmp_path):
        metrics = _get_metrics_module()
        writer = SimpleWriter(tmp_path)

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

        metrics.pa_monthly_metrics(df, writer)

        out_path = writer.resolve_path("pa_monthly_metrics", "platinum_metrics", tmp_path)
        assert out_path.exists()
