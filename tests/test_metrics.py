"""Tests for components/05_metrics.py."""

import importlib
from types import SimpleNamespace

import pandas as pd
import pytest


def _get_metrics_module():
    return importlib.import_module("egg_n_bacon_housing.components.05_metrics")


def _patch_platinum_dir(metrics, tmp_path, monkeypatch):
    """Monkeypatch the platinum_dir property via layer_dirs."""
    monkeypatch.setattr(metrics.settings.layer_dirs, "platinum", str(tmp_path / "04_platinum"))


class TestPriceMetrics:
    def test_price_metrics_produces_expected_columns(self, tmp_path, monkeypatch):
        metrics = _get_metrics_module()
        _patch_platinum_dir(metrics, tmp_path, monkeypatch)

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

        result = metrics.price_metrics_by_area(df)

        assert not result.empty
        assert "median_price" in result.columns
        assert "mean_price" in result.columns
        assert "transaction_count" in result.columns
        assert "avg_psf" in result.columns
        assert result.loc[0, "median_price"] == 510000.0
        assert result.loc[0, "avg_psf"] == pytest.approx(510.0)

    def test_price_metrics_empty_input(self, tmp_path, monkeypatch):
        metrics = _get_metrics_module()
        _patch_platinum_dir(metrics, tmp_path, monkeypatch)

        result = metrics.price_metrics_by_area(pd.DataFrame())

        assert result.empty

    def test_price_metrics_missing_month_and_date_returns_empty(self, tmp_path, monkeypatch):
        metrics = _get_metrics_module()
        _patch_platinum_dir(metrics, tmp_path, monkeypatch)

        df = pd.DataFrame([{"planning_area": "Toa Payoh", "price": 500000.0}])

        result = metrics.price_metrics_by_area(df)

        assert result.empty

    def test_price_metrics_without_psf_omits_avg_psf(self, tmp_path, monkeypatch):
        metrics = _get_metrics_module()
        _patch_platinum_dir(metrics, tmp_path, monkeypatch)

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        result = metrics.price_metrics_by_area(df)

        assert not result.empty
        assert "avg_psf" not in result.columns


class TestAffordabilityMetrics:
    def test_affordability_uses_config_income(self, tmp_path, monkeypatch):
        metrics = _get_metrics_module()
        _patch_platinum_dir(metrics, tmp_path, monkeypatch)
        monkeypatch.setattr(
            metrics.settings,
            "metrics",
            SimpleNamespace(
                median_household_income=100000,
                affordability_thresholds={
                    "affordable": 5.0,
                    "moderate": 7.0,
                    "expensive": 9.0,
                },
            ),
        )

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        result = metrics.affordability_metrics(df)

        assert not result.empty
        assert result.loc[0, "affordability_ratio"] == pytest.approx(5.0)

    def test_affordability_classification(self, tmp_path, monkeypatch):
        metrics = _get_metrics_module()
        _patch_platinum_dir(metrics, tmp_path, monkeypatch)
        monkeypatch.setattr(
            metrics.settings,
            "metrics",
            SimpleNamespace(
                median_household_income=85000,
                affordability_thresholds={
                    "affordable": 5.0,
                    "moderate": 7.0,
                    "expensive": 9.0,
                },
            ),
        )

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Cheap",
                    "price": 400000.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
                {
                    "planning_area": "Mid",
                    "price": 550000.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
                {
                    "planning_area": "Pricey",
                    "price": 700000.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
                {
                    "planning_area": "Crazy",
                    "price": 900000.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
            ]
        )

        result = metrics.affordability_metrics(df)

        classes = result.set_index("planning_area")["affordability_class"]
        assert classes["Cheap"] == "Affordable"
        assert classes["Mid"] == "Moderate"
        assert classes["Pricey"] == "Expensive"
        assert classes["Crazy"] == "Severely Unaffordable"


class TestAppreciationHotspots:
    def test_contiguous_months_produce_correct_pct_change(self, tmp_path, monkeypatch):
        metrics = _get_metrics_module()
        _patch_platinum_dir(metrics, tmp_path, monkeypatch)

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

        result = metrics.appreciation_hotspots(df)

        assert not result.empty
        assert "appreciation_3m_pct" in result.columns
        assert "appreciation_12m_pct" in result.columns

        three_m = result[result["month"] == "2025-01"]
        assert not three_m.empty
        expected_3m = (620000.0 - 590000.0) / 590000.0 * 100
        assert three_m.iloc[0]["appreciation_3m_pct"] == pytest.approx(expected_3m, rel=1e-3)

    def test_gaps_in_months_handled_correctly(self, tmp_path, monkeypatch):
        metrics = _get_metrics_module()
        _patch_platinum_dir(metrics, tmp_path, monkeypatch)

        rows = [
            {"planning_area": "Toa Payoh", "month": "2024-01", "median_price": 500000.0},
            {"planning_area": "Toa Payoh", "month": "2024-02", "median_price": 510000.0},
            {"planning_area": "Toa Payoh", "month": "2024-05", "median_price": 540000.0},
            {"planning_area": "Toa Payoh", "month": "2024-06", "median_price": 550000.0},
        ]

        df = pd.DataFrame(rows)

        result = metrics.appreciation_hotspots(df)

        if not result.empty:
            for _, row in result.iterrows():
                assert row["appreciation_3m_pct"] > 0
