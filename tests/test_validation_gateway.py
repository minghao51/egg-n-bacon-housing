"""Pure validation-gateway contract tests."""

import logging

import pandas as pd
import pytest

from egg_n_bacon_housing.schemas.platinum_models import HUnifiedRecord
from egg_n_bacon_housing.utils.validation_gateway import (
    empty_extracted,
    validate_and_quarantine,
)

pytestmark = pytest.mark.unit


def _row(**overrides):
    row = {
        "town": "TOA PAYOH",
        "lat": 1.35,
        "lon": 103.8,
        "price": 500_000.0,
        "property_type": "hdb",
        "transaction_date": pd.Timestamp("2024-01-01"),
    }
    row.update(overrides)
    return row


def test_validation_result_preserves_valid_source_values_and_columns():
    source = pd.DataFrame([_row(price="500000")])
    result = validate_and_quarantine(source, HUnifiedRecord, "unified_dataset")
    assert set(result) == {"valid", "rejected"}
    assert list(result["valid"].columns) == list(source.columns)
    assert result["valid"].loc[0, "price"] == "500000"
    assert result["rejected"].empty


def test_invalid_rows_keep_source_identity_and_reason():
    source = pd.DataFrame([_row(), _row(price=-1.0)])
    result = validate_and_quarantine(source, HUnifiedRecord, "unified_dataset")
    assert len(result["valid"]) == 1
    rejected = result["rejected"]
    assert list(rejected["_source_index"]) == [1]
    assert rejected.iloc[0]["_rejection_reason"]
    assert set(source.columns).issubset(rejected.columns)


def test_sample_policy_returns_full_source_and_quarantines_sampled_rows(caplog):
    source = pd.DataFrame([_row(price=500_000 + i) for i in range(10)] + [_row(price=-1)])
    with caplog.at_level(logging.WARNING):
        result = validate_and_quarantine(
            source,
            HUnifiedRecord,
            "unified_dataset",
            sample_validation_size=5,
            large_table_policy="sample",
        )
    assert len(result["valid"]) == len(source)
    assert "left 6/11 rows unvalidated" in caplog.text


def test_fail_policy_raises_for_vectorized_or_schema_violations():
    source = pd.DataFrame([_row(price=-1.0)])
    with pytest.raises(ValueError, match="validation failed"):
        validate_and_quarantine(
            source, HUnifiedRecord, "unified_dataset", large_table_policy="fail"
        )


def test_empty_extracted_retains_source_schema_and_quarantine_columns():
    source = pd.DataFrame(columns=["town", "price"])
    result = empty_extracted(source, "valid_rows", "rejected_rows")
    assert list(result["valid_rows"].columns) == ["town", "price"]
    assert {"town", "price", "_source_index", "_rejection_reason"} == set(
        result["rejected_rows"].columns
    )
