"""Tests for scripts/export_app_data.py — completed-months drop rule.

Synthetic frames only: no parquet IO, no full export runs.
"""

import importlib.util
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pytest

pytestmark = pytest.mark.unit

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load_exporter():
    """Load export_app_data.py as a module (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location(
        "export_app_data", _SCRIPTS / "export_app_data.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def export_mod():
    return _load_exporter()


class TestDropIncompleteTrailingMonth:
    def test_keeps_past_months_and_drops_current(self, export_mod):
        months = ["2026-07", "2026-08", "2026-09", "2026-10"]
        df = pd.DataFrame({"month": months})
        result = export_mod.drop_incomplete_trailing_month(df, "month", today=date(2026, 10, 24))
        assert list(result["month"]) == ["2026-07", "2026-08", "2026-09"]

    def test_drops_current_and_future_months(self, export_mod):
        months = ["2026-08", "2026-09", "2026-10", "2026-11", "2027-01"]
        df = pd.DataFrame({"month": months})
        result = export_mod.drop_incomplete_trailing_month(df, "month", today=date(2026, 10, 24))
        assert list(result["month"]) == ["2026-08", "2026-09"]

    def test_year_boundary_january_keeps_december(self, export_mod):
        df = pd.DataFrame({"month": ["2026-11", "2026-12", "2027-01"]})
        result = export_mod.drop_incomplete_trailing_month(df, "month", today=date(2027, 1, 5))
        assert list(result["month"]) == ["2026-11", "2026-12"]

    def test_today_defaults_to_real_clock(self, export_mod):
        current = pd.Period(datetime.now(UTC).date(), freq="M")
        df = pd.DataFrame({"month": [str(current - 2), str(current - 1), str(current)]})
        result = export_mod.drop_incomplete_trailing_month(df, "month")
        assert list(result["month"]) == [str(current - 2), str(current - 1)]

    def test_empty_frame_survives(self, export_mod):
        df = pd.DataFrame({"month": pd.Series([], dtype=str)})
        result = export_mod.drop_incomplete_trailing_month(df, "month", today=date(2026, 10, 24))
        assert result.empty

    def test_last_completed_year_excludes_current_year(self, export_mod):
        assert export_mod.last_completed_year(date(2026, 10, 24)) == 2025
        assert export_mod.last_completed_year(date(2027, 1, 1)) == 2026


class TestGrowthKeysOffCompletedMonths:
    def test_yoy_snapshot_uses_last_completed_month(self, export_mod):
        """After the drop the latest growth row is the last COMPLETED month.

        A price shock confined to the partial current month must not leak
        into the published MoM/YoY/momentum snapshot. ``today`` is pinned so
        the test cannot drift with the wall clock.
        """
        today = date(2026, 10, 24)
        months = pd.period_range("2025-09", "2026-10", freq="M")  # 14 months
        prices = [100.0] * 13 + [200.0]  # shock only in the partial month
        pa_metrics = pd.DataFrame(
            {
                "planning_area": ["ANG MO KIO"] * len(months),
                "month": [str(m) for m in months],
                "median_price": prices,
            }
        )

        growth = export_mod.build_growth_table(pa_metrics, today=today)

        assert (growth["month"] < "2026-10").all()
        last = growth.sort_values("month").iloc[-1]
        assert last["month"] == "2026-09"
        # Flat 100 -> 100 against the same month a year earlier.
        assert last["yoy_change_pct"] == pytest.approx(0.0)
        assert last["mom_change_pct"] == pytest.approx(0.0)
        assert last["momentum"] == pytest.approx(0.0)


class TestTrendsEndAtCompletedMonth:
    def test_trends_last_row_is_last_completed_month(self, export_mod):
        today = date(2026, 10, 24)  # 2026-10 is the partial month
        months = pd.period_range("2026-07", "2026-10", freq="M")
        df = pd.DataFrame(
            {
                "month": [str(m) for m in months],
                "price": [500_000.0] * len(months),
                "property_label": ["HDB"] * len(months),
            }
        )

        trends = export_mod.generate_trends_data(df, today=today)

        assert [row["date"] for row in trends] == ["2026-07", "2026-08", "2026-09"]
        assert trends[-1]["HDB Price"] == 500_000
        assert trends[-1]["HDB Volume"] == 1


class TestLeaderboardYearPairCompleted:
    def test_yoy_growth_uses_completed_year_pair(self, export_mod):
        """The current (partial) year must not be paired against a full year.

        Published yoy_growth_pct keys off the last completed year pair:
        with a 10x price shock confined to the partial year, the YoY must
        stay 0% (previous pair is flat), not +900%. ``today`` is pinned so
        the completed-year rule cannot drift with the wall clock.
        """
        today = date(2026, 10, 24)  # last completed year: 2025
        rows = []
        for year, price in (
            (2024, 100.0),
            (2025, 100.0),
            (2026, 1000.0),  # partial year: 10x shock must be ignored
        ):
            n_months = 12 if year != 2026 else 10  # partial: some months in
            rows.extend(
                {
                    "planning_area": "ANG MO KIO",
                    "year": year,
                    "month": f"{year}-{month:02d}",
                    "price": price,
                    "psf": 500.0,
                    "rental_yield_pct": 4.0,
                    "property_label": "HDB",
                }
                for month in range(1, n_months + 1)
            )
        df = pd.DataFrame(rows)

        entries = export_mod.generate_leaderboard_data(
            df,
            growth_lookup={},
            recent_yield={},
            affordability={},
            hotspots={},
            area_metadata={
                "ang mo kio": {"region": "NORTH-EAST REGION", "coordinates": [103.8, 1.38]}
            },
            today=today,
        )

        assert len(entries) == 1
        assert entries[0]["yoy_growth_pct"] == pytest.approx(0.0)
        # Era YoY inside by_time_period follows the same completed-year rule.
        assert entries[0]["by_time_period"]["whole"]["yoy_growth"] == pytest.approx(0.0)


class TestNonResidentialAreas:
    def test_drops_nature_reserve_and_industrial_rows(self, export_mod):
        df = pd.DataFrame(
            {
                "planning_area": [
                    "BEDOK",
                    "CENTRAL WATER CATCHMENT",
                    "mandai",
                    "SUNGEI KADUT",
                    "TAMPINES",
                ],
                "price": [1.0, 2.0, 3.0, 4.0, 5.0],
            }
        )
        kept = export_mod.drop_non_residential(df)

        assert list(kept["planning_area"]) == ["BEDOK", "TAMPINES"]

    def test_global_aggregates_keep_all_rows(self, export_mod):
        """The exclusion is area-level only: overview totals keep every row."""
        df = pd.DataFrame(
            {
                "planning_area": ["BEDOK", "CENTRAL WATER CATCHMENT"],
                "property_label": ["HDB", "Condominium"],
                "price": [500_000.0, 1_700_000.0],
                "psf": [500.0, 1065.0],
                "month": ["2026-09", "2026-09"],
                "year": [2026, 2026],
                "transaction_date": pd.to_datetime(["2026-09-01", "2026-09-15"]),
            }
        )

        overview = export_mod.generate_overview_data(df)

        assert overview["metadata"]["total_records"] == 2
        assert "CENTRAL WATER CATCHMENT" in overview["distributions"]["planning_area"]


class TestRankingVolumeGate:
    def _df(self, areas_and_months):
        rows = []
        for area, n_months in areas_and_months.items():
            rows.extend(
                {
                    "planning_area": area,
                    "year": 2025,
                    "month": f"2025-{month:02d}",
                    "price": 100.0,
                    "psf": 500.0,
                    "rental_yield_pct": 4.0,
                    "property_label": "HDB",
                }
                for month in range(1, n_months + 1)
            )
        return pd.DataFrame(rows)

    def test_recent_volume_counts_only_trailing_12_completed_months(self, export_mod):
        today = date(2026, 10, 24)
        df = pd.DataFrame(
            {
                "planning_area": ["A"] * 24,
                "month": [f"2025-{m:02d}" for m in range(1, 13)]
                + [f"2026-{m:02d}" for m in range(1, 13)],
            }
        )
        vols = export_mod.recent_volume_by_area(df, today=today)

        # Window is 2025-10 .. 2026-09 inclusive (12 completed months);
        # 2026-10 (current, partial) is excluded.
        assert int(vols["A"]) == 12

    def test_thin_area_sorts_behind_qualified_areas(self, export_mod):
        """A tiny-sample area with a wild score must not outrank a big one."""
        today = date(2026, 10, 24)
        # Months 2024-01..2026-09: the trailing 12-month ranking window is
        # 2025-10..2026-09, and the YoY year pair is 2024 vs 2025.
        months = [
            (y, m) for y in (2024, 2025, 2026) for m in range(1, 13) if not (y, m) > (2026, 9)
        ]
        # BEDOK: 30 rows/month = 360 in the ranking window (>= 150).
        # SELETAR: 1 row/month = 12 in the ranking window (< 150).
        rows = []
        for area, per_month, price_2024, price_2025 in (
            ("BEDOK", 30, 95.0, 100.0),
            ("SELETAR", 1, 50.0, 100.0),  # +100% YoY — would win on score
        ):
            for year, month in months:
                price = price_2024 if year == 2024 else price_2025
                rows.extend(
                    {
                        "planning_area": area,
                        "year": year,
                        "month": f"{year}-{month:02d}",
                        "price": price,
                        "psf": 500.0,
                        "rental_yield_pct": 4.0,
                        "property_label": "HDB",
                    }
                    for _ in range(per_month)
                )
        df = pd.DataFrame(rows)

        entries = export_mod.generate_leaderboard_data(
            df,
            growth_lookup={},
            recent_yield={},
            affordability={},
            hotspots={},
            area_metadata={
                "bedok": {"region": "EAST REGION", "coordinates": [103.9, 1.32]},
                "seletar": {"region": "NORTH-EAST REGION", "coordinates": [103.8, 1.4]},
            },
            today=today,
        )

        by_area = {e["planning_area"]: e for e in entries}
        assert by_area["SELETAR"]["yoy_growth_pct"] > by_area["BEDOK"]["yoy_growth_pct"]
        assert by_area["BEDOK"]["rank_overall"] == 1
        assert by_area["SELETAR"]["rank_overall"] == 2


class TestRankingScoreDeterminism:
    def test_nan_components_score_as_zero(self, export_mod):
        """Area with a missing growth component must not inherit NaN ordering."""
        assert export_mod._ranking_score({"yoy_growth_pct": None, "rental_yield_mean": 4.0}) == 4.0
        assert (
            export_mod._ranking_score({"yoy_growth_pct": float("nan"), "rental_yield_mean": None})
            == 0.0
        )
        assert export_mod._ranking_score({"yoy_growth_pct": 10.0, "rental_yield_mean": 2.0}) == 12.0
