"""Tests for validate_schema: quarantine routing, chunking, null handling."""

import logging
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from pydantic import BaseModel

from egg_n_bacon_housing.utils.validation import _is_null_scalar, validate_schema

pytestmark = pytest.mark.unit

CHUNK_SIZE = 5000


class _Record(BaseModel):
    record_id: int
    name: str
    score: float | None = None


class TestRequiredFieldPrefilter:
    """NaN required-field rows must be quarantined, not silently dropped."""

    def test_nan_required_rows_routed_to_quarantine(self):
        df = pd.DataFrame(
            {
                "record_id": [1, 2, np.nan],
                "name": ["alpha", np.nan, "gamma"],
                "score": [1.0, 2.0, np.nan],
            }
        )

        valid_df, quarantine_df = validate_schema(df, _Record, "test")

        assert len(valid_df) == 1
        assert valid_df.iloc[0]["record_id"] == 1
        assert len(quarantine_df) == 2
        assert set(quarantine_df["_rejection_reason"]) == {
            "missing required field(s): name",
            "missing required field(s): record_id",
        }

    def test_row_missing_multiple_required_fields_lists_them_all(self):
        df = pd.DataFrame(
            {"record_id": [np.nan], "name": [np.nan], "score": [1.0]},
        )

        valid_df, quarantine_df = validate_schema(df, _Record, "test")

        assert valid_df.empty
        assert len(quarantine_df) == 1
        reason = quarantine_df.iloc[0]["_rejection_reason"]
        assert reason.startswith("missing required field(s): ")
        missing = set(reason.removeprefix("missing required field(s): ").split(", "))
        assert missing == {"record_id", "name"}

    def test_all_nan_frame_fully_quarantined_with_log(self, caplog):
        df = pd.DataFrame({"record_id": [np.nan] * 3, "name": [np.nan] * 3})

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.utils.validation"):
            valid_df, quarantine_df = validate_schema(df, _Record, "test")

        assert valid_df.empty
        assert len(quarantine_df) == 3  # 100% quarantine, zero silent drops
        assert quarantine_df["_rejection_reason"].str.startswith("missing required field(s):").all()
        assert any("prefilter" in record.message.lower() for record in caplog.records)

    def test_nan_in_required_field_with_nullable_dtype_quarantined(self):
        df = pd.DataFrame(
            {
                "record_id": pd.array([1, 2, pd.NA], dtype="Int64"),
                "name": ["alpha", "beta", "gamma"],
            }
        )

        valid_df, quarantine_df = validate_schema(df, _Record, "test")

        assert len(valid_df) == 2
        assert len(quarantine_df) == 1
        assert quarantine_df.iloc[0]["_rejection_reason"] == "missing required field(s): record_id"


class TestNullScalarConversion:
    """pd.NA and numpy NaN in nullable columns become None, not type errors."""

    def test_pd_na_and_float32_nan_treated_as_none(self):
        df = pd.DataFrame(
            {
                "record_id": [1, 2, 3, 4],
                "name": ["a", "b", "c", "d"],
                # Nullable Float32: mixes a real np.float32 value, an
                # np.float32 NaN, and a pd.NA.
                "score": pd.array([2.5, np.float32("nan"), pd.NA, np.nan], dtype="Float32"),
            }
        )

        valid_df, quarantine_df = validate_schema(df, _Record, "test")

        assert quarantine_df.empty
        assert len(valid_df) == 4
        # None (not NaN/pd.NA) means pydantic coerced them as nulls, not errors.
        assert list(valid_df["score"].isna()) == [False, True, True, True]

    def test_object_column_pd_na_treated_as_none(self):
        df = pd.DataFrame(
            {
                "record_id": [1, 2],
                "name": ["a", "b"],
                "score": pd.Series([1.0, pd.NA], dtype=object),
            }
        )

        valid_df, quarantine_df = validate_schema(df, _Record, "test")

        assert quarantine_df.empty
        assert len(valid_df) == 2


class TestChunkedMaterialization:
    """validate_schema must never materialize the whole frame via to_dict."""

    def test_to_dict_only_called_per_chunk(self, monkeypatch):
        frame_sizes: list[int] = []
        original_to_dict = pd.DataFrame.to_dict

        def spy(self, *args, **kwargs):
            frame_sizes.append(len(self))
            return original_to_dict(self, *args, **kwargs)

        monkeypatch.setattr(pd.DataFrame, "to_dict", spy)

        n_rows = 3 * CHUNK_SIZE - 1000  # forces 3 uneven chunks
        df = pd.DataFrame({"record_id": range(n_rows), "name": [f"n{i}" for i in range(n_rows)]})

        valid_df, quarantine_df = validate_schema(df, _Record, "big")

        assert len(valid_df) == n_rows
        assert quarantine_df.empty
        assert len(frame_sizes) >= 3  # per-chunk calls, not one whole-frame call
        assert max(frame_sizes) <= CHUNK_SIZE  # no call ever saw the full frame


class TestPydanticQuarantine:
    """Non-null schema violations keep the existing quarantine behavior."""

    def test_type_violation_row_quarantined_with_reason(self):
        df = pd.DataFrame({"record_id": [1, 2], "name": pd.Series(["ok", 12345], dtype=object)})

        valid_df, quarantine_df = validate_schema(df, _Record, "test")

        assert len(valid_df) == 1
        assert valid_df.iloc[0]["record_id"] == 1
        assert len(quarantine_df) == 1
        assert "name" in quarantine_df.iloc[0]["_rejection_reason"]


class TestIndexSafety:
    """WS17: a non-unique index must not multiply rows in df.loc selections."""

    def test_non_unique_index_does_not_multiply_rows(self):
        """df.loc[[0, 0, 1]] on a duplicated index returns 4 rows; validate_schema
        must reset the index up front so valid rows stay 1:1 with input rows."""
        df = pd.DataFrame(
            {"record_id": [1, 2, 3], "name": ["a", "b", "c"]},
            index=pd.Index([0, 0, 1]),
        )
        assert not df.index.is_unique

        valid_df, quarantine_df = validate_schema(df, _Record, "test")

        assert quarantine_df.empty
        assert len(valid_df) == 3  # not 4 — no label-duplication blowup
        assert list(valid_df["record_id"]) == [1, 2, 3]

    def test_non_unique_index_with_quarantines_accounts_every_row(self):
        """Valid + quarantined counts must sum to the input row count even when
        the duplicated labels belong to invalid rows."""
        df = pd.DataFrame(
            {"record_id": [1, np.nan, 3, 4], "name": ["a", "b", "c", "d"]},
            index=pd.Index([7, 7, 7, 9]),
        )

        valid_df, quarantine_df = validate_schema(df, _Record, "test")

        assert len(valid_df) == 3
        assert len(quarantine_df) == 1
        assert quarantine_df.iloc[0]["_rejection_reason"] == "missing required field(s): record_id"

    def test_unique_non_default_index_preserves_order_and_labels(self):
        """Unique-index frames keep their original index and row order."""
        df = pd.DataFrame(
            {"record_id": [1, 2, 3], "name": ["a", "b", "c"]},
            index=pd.Index([10, 20, 30]),
        )

        valid_df, quarantine_df = validate_schema(df, _Record, "test")

        assert quarantine_df.empty
        assert list(valid_df.index) == [10, 20, 30]
        assert list(valid_df["record_id"]) == [1, 2, 3]

    def test_unique_index_with_rejection_keeps_row_order(self):
        df = pd.DataFrame(
            {"record_id": [1, 2, 3], "name": ["a", 12345, "c"]},
            index=pd.Index([5, 3, 8]),
        )

        valid_df, quarantine_df = validate_schema(df, _Record, "test")

        assert list(valid_df.index) == [5, 8]
        assert list(valid_df["record_id"]) == [1, 3]
        assert len(quarantine_df) == 1


class TestVectorizedNullScrub:
    """WO-9: the vectorized null-scrub must reproduce the retired per-cell
    loop's outcomes exactly on frames mixing NaN, pd.NA, None, and NaT
    across column dtypes."""

    class _TypesRecord(BaseModel):
        dt: datetime | None = None
        count: int | None = None
        flag: bool | None = None
        tag: str | None = None
        ratio: float | None = None

    def _hand_built_frame(self) -> pd.DataFrame:
        # Column dtypes: datetime64 (NaT), Int64 (pd.NA + None), boolean
        # (pd.NA + None), object (np.nan + None + a container + type
        # violations). Rows 4/5 carry genuine pydantic violations so
        # rejection reasons are exercised too.
        return pd.DataFrame(
            {
                "dt": pd.to_datetime(
                    [
                        "2024-01-01",
                        None,
                        "2024-03-01",
                        "2024-04-01",
                        "2024-05-01",
                        "2024-06-01",
                        "2024-07-01",
                    ]
                ),
                "count": pd.array([1, pd.NA, None, 4, 5, 6, 7], dtype="Int64"),
                "flag": pd.array([True, False, pd.NA, None, True, False, True], dtype="boolean"),
                "tag": np.array(["a", np.nan, None, "d", 12345, "f", ["x"]], dtype=object),
                "ratio": np.array([0.5, np.nan, 2.5, None, 1.5, "high", 3.5], dtype=object),
            }
        )

    def test_outcomes_identical_to_legacy_per_cell_scrub(self):
        """Valid count, quarantine count, and rejection reasons must match a
        reference run that applies the retired per-cell scrub up front."""
        df = self._hand_built_frame()

        valid_new, quarantine_new = validate_schema(df, self._TypesRecord, "test")

        # Reference path: the retired per-cell scrub, then the same call.
        records = df.to_dict(orient="records")
        for record in records:
            for key, value in record.items():
                if _is_null_scalar(value):
                    record[key] = None
        legacy_df = pd.DataFrame(records)
        valid_legacy, quarantine_legacy = validate_schema(legacy_df, self._TypesRecord, "test")

        assert len(valid_new) == len(valid_legacy)
        assert len(quarantine_new) == len(quarantine_legacy)
        assert list(quarantine_new["_rejection_reason"]) == list(
            quarantine_legacy["_rejection_reason"]
        )

    def test_null_variants_valid_and_violations_quarantined(self):
        df = self._hand_built_frame()

        valid_df, quarantine_df = validate_schema(df, self._TypesRecord, "test")

        # Rows 4 (tag=12345), 5 (ratio="high"), and 6 (tag=["x"]) fail
        # pydantic; every null variant (NaT, pd.NA, None, NaN) passes as None.
        assert len(valid_df) == 4
        assert len(quarantine_df) == 3
        assert list(valid_df.index) == [0, 1, 2, 3]

    def test_all_null_frame_passes_as_none(self):
        df = pd.DataFrame(
            {
                "dt": pd.to_datetime([None, "2024-01-01"]),
                "count": pd.array([pd.NA, 1], dtype="Int64"),
                "flag": pd.array([pd.NA, None], dtype="boolean"),
                "tag": np.array([np.nan, None], dtype=object),
                "ratio": np.array([np.nan, None], dtype=object),
            }
        )

        valid_df, quarantine_df = validate_schema(df, self._TypesRecord, "test")

        assert quarantine_df.empty
        assert len(valid_df) == 2
