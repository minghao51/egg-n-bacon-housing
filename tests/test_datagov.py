"""Unit tests for the datagov.sg ingestion transforms (WS12).

Focus: the income-by-planning-area grouped-median interpolation, replacing
the biased bracket-midpoint lookup. All expected values below are
hand-computed with ``lower + (total/2 - cum_before) / weight * width``.
"""

import logging

import pandas as pd
import pytest

from egg_n_bacon_housing.components.ingestion import datagov

pytestmark = pytest.mark.unit

_DATAGOV_LOGGER = "egg_n_bacon_housing.components.ingestion.datagov"

_BRACKET_COLS = [col for col, _lower, _upper in datagov._INCOME_BRACKETS]


def _income_raw(**counts: float) -> pd.DataFrame:
    """One-row raw frame (planning area "TestPA") with zero-filled brackets."""
    row: dict[str, object] = {"Thousands": "TestPA"}
    for col in _BRACKET_COLS:
        row[col] = 0
    row.update(counts)
    return pd.DataFrame([row])


def _transform_counts(**counts: float) -> pd.DataFrame:
    return datagov._transform_income_by_planning_area(_income_raw(**counts))


class TestGroupedMedianIncome:
    def test_median_mid_bracket_interpolates(self):
        """10k below 1k + 20k in [1_000, 1_500): 1000 + (15-10)/20 * 500 = 1125.

        The old midpoint transform returned 1250 here — interpolation must not.
        """
        result = _transform_counts(Below_1_000=10, **{"1_000_1_499": 20})

        assert result.loc[0, "median_monthly_income"] == pytest.approx(1125.0)

    def test_median_exactly_on_bracket_boundary_returns_boundary(self):
        """5k / 5k / 10k: total 20, target 10 sits exactly on the 1_500
        boundary between [1_000, 1_500) and [1_500, 2_000)."""
        result = _transform_counts(Below_1_000=5, **{"1_000_1_499": 5, "1_500_1_999": 10})

        assert result.loc[0, "median_monthly_income"] == 1500.0

    def test_single_bracket_distribution_interpolates_to_bracket_center(self):
        """100k in [3_000, 4_000): 3000 + 50/100 * 1000 = 3500.

        For a single closed bracket the interpolation necessarily lands at
        its centre (uniform-within-bracket property) — hand-computed, and
        only coincidentally equal to the old midpoint.
        """
        result = _transform_counts(**{"3_000_3_999": 100})

        assert result.loc[0, "median_monthly_income"] == pytest.approx(3500.0)

    def test_open_top_bracket_uses_documented_convention_value(self):
        """All 40k in '12_000andOver': assumed width 1000 (previous bracket's
        width) gives 12000 + 20/40 * 1000 = 12500, not the old 15000."""
        result = _transform_counts(**{"12_000andOver": 40})

        assert result.loc[0, "median_monthly_income"] == pytest.approx(12500.0)

    def test_open_top_bracket_crossing_interpolates_within_assumed_width(self):
        """9k in [11_000, 12_000) + 21k open: 12000 + (15-9)/21 * 1000
        = 12285.714..."""
        result = _transform_counts(**{"11_000_11_999": 9, "12_000andOver": 21})

        assert result.loc[0, "median_monthly_income"] == pytest.approx(12000 + (15 - 9) / 21 * 1000)

    def test_open_top_bracket_landings_are_logged_once_per_transform(self, caplog):
        """Bias tripwire: one INFO naming the count of PAs in the open bracket."""
        raw = pd.concat(
            [
                _income_raw(**{"12_000andOver": 40}),
                _income_raw(**{"11_000_11_999": 9, "12_000andOver": 21}),
                _income_raw(**{"Below_1_000": 10, "1_000_1_499": 20}),
            ],
            ignore_index=True,
        )

        with caplog.at_level(logging.INFO, logger=_DATAGOV_LOGGER):
            result = datagov._transform_income_by_planning_area(raw)

        assert result.loc[2, "median_monthly_income"] == pytest.approx(1125.0)
        infos = [r for r in caplog.records if "12_000andOver" in r.getMessage()]
        assert len(infos) == 1, caplog.text
        assert "2 planning area(s)" in infos[0].getMessage()

    def test_missing_bracket_columns_warn_and_are_skipped(self, caplog):
        """An absent (schema-drifted) bracket column must warn by name, not
        silently drop out of the distribution."""
        raw = _income_raw(**{"Below_1_000": 10, "10_000_10_999": 10})
        raw = raw.drop(columns=["10_000_10_999"])

        with caplog.at_level(logging.WARNING, logger=_DATAGOV_LOGGER):
            result = datagov._transform_income_by_planning_area(raw)

        warnings = [r for r in caplog.records if "bracket column" in r.getMessage()]
        assert len(warnings) == 1
        assert "10_000_10_999" in warnings[0].getMessage()
        # Remaining distribution (10 below 1k only) -> 500; demonstrates the
        # low bias the warning is guarding against.
        assert result.loc[0, "median_monthly_income"] == pytest.approx(500.0)

    def test_zero_total_returns_na(self):
        result = _transform_counts()

        assert pd.isna(result.loc[0, "median_monthly_income"])

    def test_total_rows_excluded_and_planning_area_stripped(self):
        raw = _income_raw(**{"Below_1_000": 10, "1_000_1_499": 20})
        total_row = raw.iloc[0].to_dict()
        total_row["Thousands"] = "Total"
        raw = pd.concat([raw, pd.DataFrame([total_row])], ignore_index=True)
        raw.loc[0, "Thousands"] = "  TestPA  "

        result = datagov._transform_income_by_planning_area(raw)

        assert result["planning_area"].tolist() == ["TestPA"]

    def test_open_bracket_width_constant_matches_previous_bracket(self):
        """The documented convention (previous bracket's width) must stay in
        sync with the bracket table."""
        prev_lower, prev_upper = datagov._INCOME_BRACKETS[-2][1], datagov._INCOME_BRACKETS[-2][2]

        assert prev_upper is not None
        assert datagov._OPEN_BRACKET_ASSUMED_WIDTH == prev_upper - prev_lower


class TestGreenMarkPostalCodeFilter:
    """WO-7: blank-Postal_Code drops are counted, not silent."""

    def test_blank_postal_codes_dropped_with_count_warning(self, caplog):
        raw = pd.DataFrame(
            {
                "Postal_Code": ["310101", None, "  "],
                "Project_Name": ["A", "B", "C"],
            }
        )

        with caplog.at_level(logging.WARNING, logger=_DATAGOV_LOGGER):
            result = datagov._transform_green_mark_buildings(raw)

        assert len(result) == 1
        assert result.loc[0, "postal_code"] == "310101"
        warnings = [r for r in caplog.records if "blank Postal_Code" in r.getMessage()]
        assert len(warnings) == 1, caplog.text
        assert warnings[0].levelno == logging.WARNING
        message = warnings[0].getMessage()
        assert "dropped 2/3 row(s)" in message
        assert "kept 1" in message

    def test_all_valid_postal_codes_do_not_warn(self, caplog):
        raw = pd.DataFrame({"Postal_Code": ["310101", "560234"]})

        with caplog.at_level(logging.WARNING, logger=_DATAGOV_LOGGER):
            result = datagov._transform_green_mark_buildings(raw)

        assert len(result) == 2
        assert not [r for r in caplog.records if "Postal_Code" in r.getMessage()]
