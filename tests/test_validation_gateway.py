"""Test validate_and_quarantine including the sample_validation_size branch."""

import logging

import pandas as pd
import pytest

from egg_n_bacon_housing.schemas.feature_models import HFeatureTransaction, Town360
from egg_n_bacon_housing.utils.validation_gateway import (
    validate_and_quarantine,
    vectorized_precheck,
)

pytestmark = pytest.mark.unit


class TestSampleValidation:
    """Test the sample_validation_size branch (G1)."""

    def test_large_table_triggers_sampling(self, tmp_path):
        """Large table returns all rows even though only a sample is validated."""
        df = pd.DataFrame({"town": [f"Town {i}" for i in range(15_000)]})

        result = validate_and_quarantine(
            df,
            Town360,
            "test_large",
            layer_dir=tmp_path,
            filename="test_large.parquet",
            sample_validation_size=10_000,
        )

        assert len(result) == 15_000
        assert (tmp_path / "test_large.parquet").exists()

    def test_small_table_uses_full_validation(self, tmp_path):
        """Table below threshold goes through full validation path."""
        df = pd.DataFrame({"town": [f"Town {i}" for i in range(500)]})

        result = validate_and_quarantine(
            df,
            Town360,
            "test_small",
            layer_dir=tmp_path,
            filename="test_small.parquet",
            sample_validation_size=10_000,
        )

        assert len(result) == 500
        assert (tmp_path / "test_small.parquet").exists()
        assert not (tmp_path / "_quarantine").exists()

    def test_sample_with_bad_rows_quarantines(self, tmp_path):
        """Large table with invalid rows: full table saved, sample quarantine written."""
        rows = [{"town": f"Town {i}", "annual_value_3_room": 5000.0} for i in range(500)]
        rows += [{"town": f"Bad {i}", "annual_value_3_room": -1.0} for i in range(14_500)]
        df = pd.DataFrame(rows)

        result = validate_and_quarantine(
            df,
            Town360,
            "test_bad",
            layer_dir=tmp_path,
            filename="test_bad.parquet",
            sample_validation_size=10_000,
        )

        assert len(result) == 15_000
        assert (tmp_path / "test_bad.parquet").exists()
        q_files = list((tmp_path / "_quarantine").glob("test_bad_sample_*.parquet"))
        assert len(q_files) == 1


class TestVectorizedPrecheck:
    """Test the vectorized_precheck function (O1)."""

    def test_detects_null_required_fields(self):
        """Null values in required fields are flagged."""
        df = pd.DataFrame({"town": ["A", None, "C"], "annual_value_3_room": [100.0, 200.0, 300.0]})
        issues = vectorized_precheck(df, Town360, "test")
        assert len(issues) == 1
        assert "town" in issues[0]
        assert "null" in issues[0]

    def test_detects_constraint_violations(self):
        """Values violating ge/gt/le/lt bounds are flagged."""
        df = pd.DataFrame(
            {
                "transaction_date": [pd.Timestamp("2024-01-01")] * 3,
                "price": [100.0, -50.0, 200.0],
                "lat": [1.35, 95.0, -95.0],
                "lon": [103.8, 103.8, 103.8],
                "property_type": ["hdb", "hdb", "hdb"],
            }
        )
        issues = vectorized_precheck(df, HFeatureTransaction, "test")
        issue_text = "\n".join(issues)
        assert "price" in issue_text
        assert "gt 0" in issue_text
        assert "lat" in issue_text

    def test_clean_data_no_issues(self):
        """Clean data produces no issues."""
        df = pd.DataFrame({"town": ["A", "B", "C"], "annual_value_3_room": [100.0, 200.0, 300.0]})
        issues = vectorized_precheck(df, Town360, "test")
        assert issues == []

    def test_skips_missing_columns(self):
        """Columns not in DataFrame are silently skipped."""
        df = pd.DataFrame({"town": ["A", "B"]})
        issues = vectorized_precheck(df, Town360, "test")
        assert issues == []

    def test_precheck_integrated_in_sample_path(self, tmp_path, caplog):
        """Precheck runs and logs warnings during sample validation."""
        rows = [{"town": f"Town {i}", "annual_value_3_room": -1.0} for i in range(15_000)]
        df = pd.DataFrame(rows)

        with caplog.at_level(
            logging.WARNING, logger="egg_n_bacon_housing.utils.validation_gateway"
        ):
            result = validate_and_quarantine(
                df,
                Town360,
                "test_precheck",
                layer_dir=tmp_path,
                filename="test_precheck.parquet",
                sample_validation_size=10_000,
            )

        assert len(result) == 15_000
        assert any("pre-check" in r.message.lower() for r in caplog.records)
        assert any("annual_value_3_room" in r.message for r in caplog.records)
