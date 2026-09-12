"""Pure validation-gateway contract tests."""

import logging
from datetime import datetime

import pandas as pd
import pytest
from annotated_types import Ge, MinLen

from egg_n_bacon_housing.schemas.feature_models import HFeatureTransaction
from egg_n_bacon_housing.schemas.platinum_models import HUnifiedRecord
from egg_n_bacon_housing.utils.validation_gateway import (
    empty_extracted,
    validate_and_quarantine,
    vectorized_precheck,
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


def test_sample_policy_quarantines_sampled_rejects_once_and_drops_them_from_valid(caplog):
    """Sampled rejects are quarantined exactly once, never published (item 22b).

    random_state=42 with size 5 over the 11-row frame samples positions
    [5, 0, 9, 10, 2]; the poisoned row sits at index 10, inside the sample.
    """
    source = pd.DataFrame([_row(price=500_000 + i) for i in range(10)] + [_row(price=-1)])
    with caplog.at_level(logging.WARNING):
        result = validate_and_quarantine(
            source,
            HUnifiedRecord,
            "unified_dataset",
            sample_validation_size=5,
            large_table_policy="sample",
        )
    assert len(result["rejected"]) == 1
    assert list(result["rejected"]["_source_index"]) == [10]
    # Absent from the published frame, present exactly once in quarantine.
    assert 10 not in result["valid"].index
    assert len(result["valid"]) == len(source) - 1
    # Source order of the surviving rows is preserved.
    assert list(result["valid"]["price"]) == [500_000 + i for i in range(10)]
    assert "left 6/11 rows unvalidated" in caplog.text


def test_sample_policy_all_sampled_rejects_quarantined_exactly_once():
    """Every sampled reject leaves valid; valid and quarantine are disjoint."""
    source = pd.DataFrame([_row(price=-1.0 if i % 3 == 0 else 500_000 + i) for i in range(12)])
    result = validate_and_quarantine(
        source,
        HUnifiedRecord,
        "unified_dataset",
        sample_validation_size=6,
        large_table_policy="sample",
    )
    sampled = source.sample(n=6, random_state=42)
    expected_rejects = sorted(sampled.index[sampled["price"] < 0].tolist())
    assert expected_rejects, "fixture must poison at least one sampled row"
    rejected_idx = sorted(result["rejected"]["_source_index"].tolist())
    assert rejected_idx == expected_rejects
    valid_idx = result["valid"].index.tolist()
    assert not set(valid_idx) & set(rejected_idx)
    assert len(result["valid"]) == len(source) - len(rejected_idx)


def test_sample_policy_precheck_covers_unsampled_rows(caplog):
    """The vectorized pre-check is a 100%-coverage diagnostic: violations on
    unsampled rows are reported even though they never reach pydantic."""
    source = pd.DataFrame([_row(price=500_000 + i) for i in range(10)] + [_row(price=-1)])
    with caplog.at_level(logging.WARNING):
        validate_and_quarantine(
            source,
            HUnifiedRecord,
            "unified_dataset",
            sample_validation_size=5,
            large_table_policy="sample",
        )
    assert "Vectorized pre-check" in caplog.text
    assert "price: 1 values violate gt 0" in caplog.text


def test_sample_full_fail_policies_agree_on_clean_fixtures():
    """Constraint-satisfying fixtures publish identical frames in every policy."""
    source = pd.DataFrame([_row(price=500_000 + i) for i in range(20)])
    results = {
        policy: validate_and_quarantine(
            source,
            HUnifiedRecord,
            "unified_dataset",
            sample_validation_size=5,
            large_table_policy=policy,
        )
        for policy in ("sample", "full", "fail")
    }
    for policy in ("full", "fail"):
        pd.testing.assert_frame_equal(results["sample"]["valid"], results[policy]["valid"])
        pd.testing.assert_frame_equal(results["sample"]["rejected"], results[policy]["rejected"])
    assert results["fail"]["rejected"].empty


def test_fail_policy_raises_for_vectorized_or_schema_violations():
    source = pd.DataFrame([_row(price=-1.0)])
    with pytest.raises(ValueError, match="validation failed"):
        validate_and_quarantine(
            source, HUnifiedRecord, "unified_dataset", large_table_policy="fail"
        )


def test_fail_policy_precheck_catches_datetime_bound():
    """Datetime bounds are vectorized-checkable, so fail mode raises pre-pydantic."""
    source = pd.DataFrame([_row(transaction_date=pd.Timestamp("1989-06-01"))])
    with pytest.raises(ValueError, match="violate ge 1990-01-01"):
        validate_and_quarantine(
            source, HUnifiedRecord, "unified_dataset", large_table_policy="fail"
        )


class TestModelDerivedPrecheckConstraints:
    """Item 22a: datetime-bound and min_length pre-check coverage derives
    from the pydantic models' ``Field`` metadata, not hardcoded values."""

    def test_transaction_date_dataset_floor_is_declared_on_the_gold_model(self):
        ge_bounds = [
            m.ge
            for m in HFeatureTransaction.model_fields["transaction_date"].metadata
            if isinstance(m, Ge)
        ]
        assert ge_bounds == [datetime(1990, 1, 1)]

    def test_platinum_model_inherits_gold_datetime_floor(self):
        ge_bounds = [
            m.ge
            for m in HUnifiedRecord.model_fields["transaction_date"].metadata
            if isinstance(m, Ge)
        ]
        assert ge_bounds == [datetime(1990, 1, 1)]

    def test_property_type_min_length_is_declared_on_the_gold_model(self):
        min_lens = [
            m.min_length
            for m in HFeatureTransaction.model_fields["property_type"].metadata
            if isinstance(m, MinLen)
        ]
        assert min_lens == [1]

    def test_precheck_flags_datetime_bounds_below_dataset_floor(self):
        source = pd.DataFrame(
            [
                _row(transaction_date=pd.Timestamp("2024-01-01")),
                _row(transaction_date=pd.Timestamp("1989-12-31")),
            ]
        )
        issues = vectorized_precheck(source, HUnifiedRecord, "unified_dataset")
        joined = "\n".join(issues)
        assert "transaction_date: 1 values violate ge 1990-01-01" in joined

    def test_precheck_flags_empty_required_strings(self):
        source = pd.DataFrame([_row(), _row(property_type="")])
        issues = vectorized_precheck(source, HUnifiedRecord, "unified_dataset")
        assert "property_type: 1 values shorter than min_length 1" in "\n".join(issues)

    def test_precheck_clean_frame_reports_no_issues(self):
        source = pd.DataFrame(
            [
                _row(),
                _row(property_type="condo", transaction_date=pd.Timestamp("1990-01-01")),
            ]
        )
        assert vectorized_precheck(source, HUnifiedRecord, "unified_dataset") == []

    def test_precheck_datetime_bound_enforced_at_model_level(self):
        """The declared floor is a real pydantic constraint, not just prose."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HUnifiedRecord(**_row(transaction_date=pd.Timestamp("1989-12-31")))


def test_empty_extracted_retains_source_schema_and_quarantine_columns():
    source = pd.DataFrame(columns=["town", "price"])
    result = empty_extracted(source, "valid_rows", "rejected_rows")
    assert list(result["valid_rows"].columns) == ["town", "price"]
    assert {"town", "price", "_source_index", "_rejection_reason"} == set(
        result["rejected_rows"].columns
    )
