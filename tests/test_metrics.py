"""Tests for components/05_metrics.py."""

import logging

import pandas as pd
import pytest
from pydantic import ValidationError

from egg_n_bacon_housing.schemas.platinum_models import AppreciationHotspot, PaMonthlyMetric
from egg_n_bacon_housing.utils.layer_writer import SimpleWriter

pytestmark = pytest.mark.unit


def _get_metrics_module():
    from egg_n_bacon_housing.components import metrics

    return metrics


class TestPaMonthlyMetrics:
    def test_pa_monthly_metrics_produces_expected_columns(self, tmp_path):
        metrics = _get_metrics_module()

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

        result = metrics.pa_monthly_metrics(df)

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

        result = metrics.pa_monthly_metrics(pd.DataFrame())

        assert result.empty

    def test_pa_monthly_metrics_missing_planning_area(self, tmp_path):
        metrics = _get_metrics_module()

        df = pd.DataFrame([{"price": 500000.0, "transaction_date": pd.Timestamp("2024-01-15")}])

        result = metrics.pa_monthly_metrics(df)

        assert result.empty

    def test_null_planning_area_rows_dropped_with_count_warning(self, tmp_path, caplog):
        """WO-7: the null-planning_area filter announces dropped/kept counts."""
        metrics = _get_metrics_module()
        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "planning_area": None,
                    "price": 600000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "planning_area": "Bishan",
                    "price": 700000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.components.metrics"):
            result = metrics.pa_monthly_metrics(df)

        assert set(result["planning_area"]) == {"Toa Payoh", "Bishan"}
        drop_warnings = [r for r in caplog.records if "null planning_area" in r.getMessage()]
        assert len(drop_warnings) == 1, caplog.text
        assert drop_warnings[0].levelno == logging.WARNING
        message = drop_warnings[0].getMessage()
        assert "dropped 1 row(s)" in message
        assert "kept 2" in message

    def test_all_valid_planning_areas_log_no_drop_warning(self, tmp_path, caplog):
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

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.components.metrics"):
            metrics.pa_monthly_metrics(df)

        assert not [r for r in caplog.records if "null planning_area" in r.getMessage()]

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

        result = metrics.pa_monthly_metrics(df)

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

        result = metrics.pa_monthly_metrics(df)

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

    def test_multiple_planning_areas_ranked_and_capped(self, tmp_path):
        """Vectorized concat across planning areas still ranks by appreciation and
        caps at the top 20 rows (regression for the inner-loop vectorization)."""
        metrics = _get_metrics_module()

        rows = []
        for pa, base, step in [("ANG MO KIO", 500000.0, 10000.0), ("BISHAN", 400000.0, 15000.0)]:
            for i in range(13):
                month = f"2024-{i + 1:02d}" if i < 12 else "2025-01"
                rows.append(
                    {
                        "planning_area": pa,
                        "month": month,
                        "median_price": base + i * step,
                    }
                )

        df = pd.DataFrame(rows)
        result = metrics.appreciation_hotspots(df)

        assert not result.empty
        assert set(result["planning_area"]).issubset({"ANG MO KIO", "BISHAN"})
        # Faster-appreciating (higher %) PA dominates the top of the ranking.
        assert result.iloc[0]["planning_area"] == "BISHAN"
        assert "is_declining" in result.columns
        assert len(result) <= 20


class TestAppreciationHotspotsVolumeFloor:
    """transaction_count volume floor (min_transactions_for_hotspot)."""

    @staticmethod
    def _month_frame(pa, prices_counts: dict[str, tuple[float, int]]) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "planning_area": pa,
                    "month": month,
                    "median_price": price,
                    "transaction_count": count,
                }
                for month, (price, count) in prices_counts.items()
            ]
        )

    def test_low_txn_spike_month_excluded_despite_extreme_pct_change(self, tmp_path, caplog):
        metrics = _get_metrics_module()
        df = self._month_frame(
            "TOA PAYOH",
            {
                "2024-01": (500000.0, 10),
                "2024-02": (510000.0, 10),
                "2024-03": (520000.0, 10),
                "2024-04": (530000.0, 10),
                "2024-05": (540000.0, 10),
                "2024-06": (560000.0, 10),
                "2024-07": (2000000.0, 1),  # single-txn spike
            },
        )

        with caplog.at_level(logging.INFO):
            result = metrics.appreciation_hotspots(df)

        assert not result.empty
        assert "2024-07" not in set(result["month"])
        # No floored-spike distortion survives in the ranked appreciations.
        assert result["appreciation_3m_pct"].max() < 10.0
        assert "floored 1 (planning_area, month) row(s)" in caplog.text

    def test_floored_base_month_cannot_distort_later_3m_appreciation(self, tmp_path):
        """A 1-txn outlier BASE month is ffilled over, not used as a base."""
        metrics = _get_metrics_module()
        df = self._month_frame(
            "TOA PAYOH",
            {
                "2024-01": (500000.0, 10),
                "2024-02": (1000000.0, 1),  # 1-txn outlier base for May's 3m window
                "2024-03": (504000.0, 10),
                "2024-04": (506000.0, 10),
                "2024-05": (508000.0, 10),
                "2024-06": (510000.0, 10),
            },
        )

        result = metrics.appreciation_hotspots(df)

        assert not result.empty
        may = result[result["month"] == "2024-05"]
        assert not may.empty
        # Feb floored -> ffill uses Jan (500k): 508/500 - 1, not 508/1_000_000 - 1.
        expected = (508000.0 - 500000.0) / 500000.0 * 100
        assert may.iloc[0]["appreciation_3m_pct"] == pytest.approx(expected, rel=1e-6)

    def test_exactly_five_transactions_included_boundary(self, tmp_path):
        metrics = _get_metrics_module()
        df = self._month_frame(
            "TOA PAYOH",
            {
                "2024-01": (500000.0, 10),
                "2024-02": (510000.0, 10),
                "2024-03": (520000.0, 10),
                "2024-04": (530000.0, 10),
                "2024-05": (540000.0, 10),
                "2024-06": (800000.0, 5),  # exactly at the floor -> eligible
            },
        )

        result = metrics.appreciation_hotspots(df)

        assert "2024-06" in set(result["month"])
        # Raising the floor by one excludes the same month.
        stricter = metrics.appreciation_hotspots(df, min_transactions_for_hotspot=6)
        assert "2024-06" not in set(stricter["month"])

    def test_min_transactions_one_reproduces_prefloor_behavior(self, tmp_path):
        """Regression guard: min_transactions_for_hotspot=1 keeps spike months."""
        metrics = _get_metrics_module()
        df = self._month_frame(
            "TOA PAYOH",
            {
                "2024-01": (500000.0, 10),
                "2024-02": (510000.0, 10),
                "2024-03": (520000.0, 10),
                "2024-04": (530000.0, 10),
                "2024-05": (540000.0, 10),
                "2024-06": (560000.0, 10),
                "2024-07": (2000000.0, 1),
            },
        )

        result = metrics.appreciation_hotspots(df, min_transactions_for_hotspot=1)

        assert "2024-07" in set(result["month"])
        assert result.iloc[0]["month"] == "2024-07"  # spike dominates the ranking

    def test_empty_after_floor_returns_empty_frame(self, tmp_path):
        metrics = _get_metrics_module()
        df = self._month_frame(
            "TOA PAYOH",
            {
                "2024-01": (500000.0, 2),
                "2024-02": (510000.0, 3),
                "2024-03": (520000.0, 4),
            },
        )

        result = metrics.appreciation_hotspots(df)

        assert result.empty


class TestPaMonthlyMetricsPlatinumContract:
    """pa_monthly_metrics validates against PaMonthlyMetric."""

    def test_poisoned_group_quarantined(self, tmp_path, caplog):
        metrics = _get_metrics_module()
        df = pd.DataFrame(
            [
                {
                    "planning_area": "Good Area",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "planning_area": "Bad Area",
                    "price": -5.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        with caplog.at_level(logging.WARNING):
            result = metrics.pa_monthly_metrics(df)

        assert list(result["planning_area"]) == ["Good Area"]
        assert result["median_price"].iloc[0] == 500000.0
        assert "pa_monthly_metrics: 1 PA-month row(s) quarantined" in caplog.text

    def test_node_writes_nothing(self, tmp_path):
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

        metrics.pa_monthly_metrics(df)

        # Materializer owns persistence — persist=False writes nothing.
        assert list(tmp_path.rglob("*.parquet")) == []


class TestAppreciationHotspotsPlatinumContract:
    """appreciation_hotspots validates against AppreciationHotspot."""

    def test_poisoned_hotspot_rows_quarantined(self, tmp_path, caplog):
        metrics = _get_metrics_module()
        rows = []
        for pa, base in [("GOOD AREA", 500000.0), ("BAD AREA", -500000.0)]:
            for i in range(5):
                rows.append(
                    {
                        "planning_area": pa,
                        "month": f"2024-{i + 1:02d}",
                        "median_price": base + i * 1000.0,
                    }
                )

        with caplog.at_level(logging.WARNING):
            result = metrics.appreciation_hotspots(pd.DataFrame(rows))

        assert not result.empty
        assert set(result["planning_area"]) == {"GOOD AREA"}
        assert "appreciation_hotspots: 2 row(s) quarantined" in caplog.text

    def test_node_writes_nothing(self, tmp_path):
        metrics = _get_metrics_module()
        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "month": f"2024-{i + 1:02d}",
                    "median_price": 500000.0 + i,
                }
                for i in range(4)
            ]
        )

        metrics.appreciation_hotspots(df)

        assert list(tmp_path.rglob("*.parquet")) == []

    def test_materializer_does_not_write_legacy_alias(self, tmp_path):
        from egg_n_bacon_housing.components.materialization import (
            materialize_appreciation_hotspots,
        )

        df = pd.DataFrame(
            [
                {
                    "planning_area": "Toa Payoh",
                    "month": "2024-01",
                    "median_price": 500000.0,
                    "appreciation_3m_pct": 1.5,
                    "appreciation_12m_pct": 4.0,
                    "is_declining": False,
                }
            ]
        )
        writer = SimpleWriter(tmp_path)

        path = materialize_appreciation_hotspots(df, writer)

        assert path.exists()
        files = list((tmp_path / "04_platinum" / "metrics").glob("*.parquet"))
        assert files == [tmp_path / "04_platinum" / "metrics" / "appreciation_hotspots.parquet"]


class TestPlatinumModelConstraints:
    """Schema constraint sanity for the platinum models."""

    @staticmethod
    def _metric_row(**overrides) -> dict:
        row = {
            "planning_area": "Toa Payoh",
            "month": "2024-01",
            "median_price": 500000.0,
            "mean_price": 510000.0,
            "transaction_count": 2,
            "affordability_ratio": 5.9,
            "affordability_class": "Moderate",
        }
        row.update(overrides)
        return row

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            PaMonthlyMetric(**self._metric_row(median_price=-1.0))

    def test_negative_count_rejected(self):
        with pytest.raises(ValidationError):
            PaMonthlyMetric(**self._metric_row(transaction_count=-1))

    @pytest.mark.parametrize("bad_month", ["2024-1", "Jan 2024", "2024/01", "24-01"])
    def test_bad_month_format_rejected(self, bad_month):
        with pytest.raises(ValidationError):
            PaMonthlyMetric(**self._metric_row(month=bad_month))

    def test_unknown_affordability_class_rejected(self):
        with pytest.raises(ValidationError):
            PaMonthlyMetric(**self._metric_row(affordability_class="Cheap"))

    def test_hotspot_rejects_bad_month_and_price(self):
        base = {
            "planning_area": "Toa Payoh",
            "month": "2024-01",
            "median_price": 500000.0,
            "appreciation_3m_pct": 1.5,
            "is_declining": False,
        }
        with pytest.raises(ValidationError):
            AppreciationHotspot(**(base | {"month": "2024-1"}))
        with pytest.raises(ValidationError):
            AppreciationHotspot(**(base | {"median_price": -1.0}))

    def test_hotspot_allows_null_12m_and_negative_3m(self):
        model = AppreciationHotspot(
            planning_area="Toa Payoh",
            month="2024-01",
            median_price=500000.0,
            appreciation_3m_pct=-2.0,
            appreciation_12m_pct=None,
            is_declining=True,
        )
        assert model.appreciation_12m_pct is None
        assert model.is_declining is True


class TestAffordabilityClassificationVectorized:
    """WO-9: np.select classification must match the retired per-row apply."""

    def test_thresholds_are_exclusive(self, tmp_path):
        """A ratio exactly on a threshold lands in the next band up (strict
        less-than), pinning the np.select banding order."""
        metrics = _get_metrics_module()

        # income=100000 -> ratios exactly 5.0 / 7.0 / 9.0 for the first three
        df = pd.DataFrame(
            [
                {
                    "planning_area": "A",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
                {
                    "planning_area": "B",
                    "price": 700000.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
                {
                    "planning_area": "C",
                    "price": 900000.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
                {
                    "planning_area": "D",
                    "price": 499999.0,
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
            ]
        )

        result = metrics.pa_monthly_metrics(df, median_household_income=100_000)

        assert result.set_index("planning_area")["affordability_class"].to_dict() == {
            "A": "Moderate",
            "B": "Expensive",
            "C": "Severely Unaffordable",
            "D": "Affordable",
        }

    def test_nan_ratio_falls_through_to_default_band(self, tmp_path, monkeypatch):
        """A NaN ratio fails every comparison and lands in the default band —
        the exact behavior of the retired scalar classifier. Validation is
        bypassed here because PaMonthlyMetric rejects a NaN ratio before the
        class is observable downstream."""
        metrics = _get_metrics_module()
        monkeypatch.setattr(metrics, "validate_and_quarantine", lambda df, *args, **kwargs: df)

        df = pd.DataFrame(
            [
                {
                    "planning_area": "A",
                    "price": float("nan"),
                    "transaction_date": pd.Timestamp("2024-01-01"),
                },
            ]
        )

        result = metrics.pa_monthly_metrics(df, median_household_income=100_000)

        assert result.loc[0, "affordability_class"] == "Severely Unaffordable"
