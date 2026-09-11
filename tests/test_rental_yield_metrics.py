"""Tests for components/05_metrics.py — rental yield in pa_monthly_metrics."""

import logging

import pandas as pd
import pytest

from egg_n_bacon_housing.utils.layer_writer import SimpleWriter

pytestmark = pytest.mark.unit

_RENTAL_LOGGER = "egg_n_bacon_housing.components.feature_rental"


def _get_metrics_module():
    from egg_n_bacon_housing.components import metrics

    return metrics


class TestRentalYieldInPaMonthly:
    def test_computes_expected_columns(self, tmp_path):
        metrics = _get_metrics_module()

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

        result = metrics.pa_monthly_metrics(df)

        assert not result.empty
        assert "median_rental_yield" in result.columns
        assert "avg_rental_yield" in result.columns
        assert result.iloc[0]["median_rental_yield"] == pytest.approx(4.75)
        assert result.iloc[0]["avg_rental_yield"] == pytest.approx(4.75)

    def test_empty_input(self, tmp_path):
        metrics = _get_metrics_module()

        result = metrics.pa_monthly_metrics(pd.DataFrame())
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

        result = metrics.pa_monthly_metrics(df)
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

        result = metrics.pa_monthly_metrics(df)
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

        result = metrics.pa_monthly_metrics(df)
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

        result = metrics.pa_monthly_metrics(df)
        from egg_n_bacon_housing.components.materialization import materialize_pa_monthly_metrics

        materialize_pa_monthly_metrics(result, writer)

        out_path = writer.resolve_path("pa_monthly_metrics", "platinum_metrics", tmp_path)
        assert out_path.exists()


class TestRentalYieldMergeCoverageWarning:
    """WO-7: the sales×rents inner-merge drop warns with coverage numbers."""

    def test_merge_drop_warning_includes_group_coverage(self, tmp_path, caplog):
        from egg_n_bacon_housing.components.feature_rental import rental_yield

        hdb_validated = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "flat_type": "4 ROOM",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                # BEDOK has sales but no rents -> dropped by the inner merge.
                {
                    "town": "BEDOK",
                    "price": 400000.0,
                    "flat_type": "4 ROOM",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )
        raw_hdb_rental = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "flat_type": "4-ROOM",
                    "monthly_rent": "3500",
                    "rent_approval_date": "2024-01",
                }
            ]
        )

        with caplog.at_level(logging.WARNING, logger=_RENTAL_LOGGER):
            result = rental_yield(hdb_validated, raw_hdb_rental, pd.DataFrame())

        # Only the matched town survives the inner merge.
        assert list(result["town"].unique()) == ["TOA PAYOH"]
        merge_warnings = [r for r in caplog.records if "Rental yield join" in r.getMessage()]
        assert len(merge_warnings) == 1, caplog.text
        assert merge_warnings[0].levelno == logging.WARNING
        message = merge_warnings[0].getMessage()
        assert "1 of 2 sales" in message
        assert "coverage 50.0%" in message

    def test_fully_matched_groups_do_not_warn(self, tmp_path, caplog):
        from egg_n_bacon_housing.components.feature_rental import rental_yield

        hdb_validated = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "flat_type": "4 ROOM",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                }
            ]
        )
        raw_hdb_rental = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "flat_type": "4-ROOM",
                    "monthly_rent": "3500",
                    "rent_approval_date": "2024-01",
                }
            ]
        )

        with caplog.at_level(logging.WARNING, logger=_RENTAL_LOGGER):
            rental_yield(hdb_validated, raw_hdb_rental, pd.DataFrame())

        assert not [r for r in caplog.records if "Rental yield join" in r.getMessage()]


class TestRentalYieldNodeMaterialization:
    """rental_yield validates (persist=False); materialize_rental_yield persists.

    Mirrors the old inline-gateway contract: the persisted frame contains only
    schema-valid rows, under the PUBLISHED_LAYERS name/layer pair.
    """

    @staticmethod
    def _node_inputs(monthly_rent: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        hdb_validated = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "flat_type": "4 ROOM",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "town": "TOA PAYOH",
                    "price": 520000.0,
                    "flat_type": "4 ROOM",
                    "transaction_date": pd.Timestamp("2024-01-28"),
                },
            ]
        )
        raw_hdb_rental = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "flat_type": "4-ROOM",
                    "monthly_rent": monthly_rent,
                    "rent_approval_date": "2024-01",
                }
            ]
        )
        raw_rental_index = pd.DataFrame(
            [{"quarter": "2024-Q1", "locality": "Whole Island", "index": "108.2"}]
        )
        return hdb_validated, raw_hdb_rental, raw_rental_index

    def test_node_writes_nothing_and_materializer_persists_gold(self, tmp_path):
        from egg_n_bacon_housing.components.feature_rental import rental_yield
        from egg_n_bacon_housing.components.materialization import materialize_rental_yield
        from egg_n_bacon_housing.utils.layer_writer import PUBLISHED_LAYERS, SimpleWriter

        writer = SimpleWriter(tmp_path)

        df = rental_yield(*self._node_inputs(monthly_rent="3500"))

        assert not df.empty
        assert not list(tmp_path.rglob("*.parquet"))

        path = materialize_rental_yield(df, writer)

        layer = PUBLISHED_LAYERS["rental_yield"]
        assert path == writer.resolve_path("rental_yield", layer, tmp_path)
        pd.testing.assert_frame_equal(pd.read_parquet(path), df)

    def test_quarantined_rows_warn_and_write_nothing(self, tmp_path, caplog):
        """A computed row violating HRentalYieldRecord is dropped with a warning."""
        import logging

        from egg_n_bacon_housing.components.feature_rental import rental_yield

        # yield = 20000*12/510000*100 ~ 47% violates rental_yield_pct <= 20.
        with caplog.at_level(
            logging.WARNING, logger="egg_n_bacon_housing.components.feature_rental"
        ):
            df = rental_yield(*self._node_inputs(monthly_rent="20000"))

        assert df.empty
        assert any(
            "rental_yield: 1 row(s) quarantined at the gold boundary" in record.getMessage()
            for record in caplog.records
        )
        assert not list(tmp_path.rglob("*.parquet"))
