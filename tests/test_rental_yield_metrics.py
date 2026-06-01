"""Tests for components/05_metrics.py — rental_yield_by_area."""

import importlib

import pandas as pd
import pytest

pytestmark = pytest.mark.unit


def _get_metrics_module():
    return importlib.import_module("egg_n_bacon_housing.components.05_metrics")


class TestRentalYieldByArea:
    def test_computes_expected_columns(self, tmp_path):
        metrics = _get_metrics_module()
        platinum_dir = tmp_path / "platinum"

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "rental_yield_pct": 4.5,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "planning_area": "Toa Payoh",
                    "rental_yield_pct": 5.0,
                    "transaction_date": pd.Timestamp("2024-01-20"),
                },
            ]
        )

        result = metrics.rental_yield_by_area(df, platinum_dir)

        assert not result.empty
        assert "median_rental_yield" in result.columns
        assert "avg_rental_yield" in result.columns
        assert "count" in result.columns
        assert result.iloc[0]["median_rental_yield"] == pytest.approx(4.75)
        assert result.iloc[0]["avg_rental_yield"] == pytest.approx(4.75)
        assert result.iloc[0]["count"] == 2

    def test_empty_input(self, tmp_path):
        metrics = _get_metrics_module()

        result = metrics.rental_yield_by_area(pd.DataFrame(), tmp_path / "platinum")
        assert result.empty

    def test_missing_rental_yield_column(self, tmp_path):
        metrics = _get_metrics_module()

        df = pd.DataFrame(
            [
                {"planning_area": "Toa Payoh", "transaction_date": pd.Timestamp("2024-01-01")},
            ]
        )

        result = metrics.rental_yield_by_area(df, tmp_path / "platinum")
        assert result.empty

    def test_missing_planning_area_column(self, tmp_path):
        metrics = _get_metrics_module()

        df = pd.DataFrame(
            [
                {"rental_yield_pct": 4.5, "transaction_date": pd.Timestamp("2024-01-01")},
            ]
        )

        result = metrics.rental_yield_by_area(df, tmp_path / "platinum")
        assert result.empty

    def test_single_data_point(self, tmp_path):
        metrics = _get_metrics_module()

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Bishan",
                    "rental_yield_pct": 3.8,
                    "transaction_date": pd.Timestamp("2024-06-01"),
                }
            ]
        )

        result = metrics.rental_yield_by_area(df, tmp_path / "platinum")
        assert len(result) == 1
        assert result.iloc[0]["median_rental_yield"] == pytest.approx(3.8)

    def test_multiple_areas_grouped_separately(self, tmp_path):
        metrics = _get_metrics_module()

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "rental_yield_pct": 4.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
                {
                    "planning_area": "Bishan",
                    "rental_yield_pct": 3.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
                {
                    "planning_area": "Toa Payoh",
                    "rental_yield_pct": 5.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
            ]
        )

        result = metrics.rental_yield_by_area(df, tmp_path / "platinum")
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
                    "rental_yield_pct": 4.5,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                }
            ]
        )

        metrics.rental_yield_by_area(df, platinum_dir)

        out_path = platinum_dir / "metrics" / "L5_rental_yield_by_area.parquet"
        assert out_path.exists()
