"""Tests for scripts/v2_observed.py — v2 period, aggregate and pack contracts.

Hermetic: synthetic frames and temporary directories only. No parquet IO, no
network, no full export run.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

pytestmark = pytest.mark.unit

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load_module():
    spec = importlib.util.spec_from_file_location("v2_observed", _SCRIPTS / "v2_observed.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Dataclasses resolve their module through sys.modules during creation.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def v2():
    return _load_module()


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["property_label"] = v2_property_labels(frame)
    return frame


def v2_property_labels(frame: pd.DataFrame) -> pd.Series:
    """Mirror of the exporter's property mapping, kept local to the fixture."""
    labels = []
    for _, row in frame.iterrows():
        if row.get("is_ec"):
            labels.append("EC")
        elif str(row.get("property_type", "")).lower() == "hdb":
            labels.append("HDB")
        else:
            labels.append("Condominium")
    return pd.Series(labels, index=frame.index)


class TestPeriods:
    def test_october_cutoff_bounds_and_comparators(self, v2):
        periods = {p.id: p for p in v2.build_periods("2026-10")}

        assert periods["month_2026_10"].months == ("2026-10",)
        assert periods["ytd_2026_10"].start_month == "2026-01"
        assert periods["ytd_2026_10"].end_month == "2026-10"
        assert len(periods["ytd_2026_10"].months) == 10
        assert periods["ttm_2026_10"].start_month == "2025-11"
        assert len(periods["ttm_2026_10"].months) == 12
        assert periods["year_2025"].months[0] == "2025-01"
        assert periods["year_2025"].months[-1] == "2025-12"

        assert periods["month_2026_10"].comparator_id == "month_2025_10"
        assert periods["ytd_2026_10"].comparator_id == "ytd_2025_10"
        assert periods["ttm_2026_10"].comparator_id == "ttm_2025_10"
        assert periods["year_2025"].comparator_id == "year_2024"

    def test_comparators_are_published_only_when_fully_covered(self, v2):
        covered = {f"{year}-{month:02d}" for year in (2024, 2025, 2026) for month in range(1, 13)}
        ids = {p.id for p in v2.build_periods("2026-10", covered_months=covered)}

        assert {"month_2025_10", "ytd_2025_10", "ttm_2025_10", "year_2024"} <= ids

        sparse = {"2026-10", "2026-09"}
        sparse_ids = {p.id for p in v2.build_periods("2026-10", covered_months=sparse)}
        assert "month_2025_10" not in sparse_ids
        assert "ttm_2025_10" not in sparse_ids

    def test_january_cutoff_does_not_invent_a_full_year(self, v2):
        periods = {p.id: p for p in v2.build_periods("2027-01")}

        assert periods["ytd_2027_01"].months == ("2027-01",)
        assert periods["ttm_2027_01"].start_month == "2026-02"
        assert "year_2027" not in periods

    def test_december_cutoff_treats_the_year_as_complete(self, v2):
        periods = {p.id: p for p in v2.build_periods("2026-12")}

        assert periods["year_2026"].start_month == "2026-01"
        assert periods["year_2026"].end_month == "2026-12"
        assert periods["ytd_2026_12"].months[-1] == "2026-12"
        assert periods["ttm_2026_12"].start_month == "2026-01"

    def test_leap_year_february_is_a_valid_month(self, v2):
        months = v2.month_range("2028-01", "2028-03")

        assert months == ["2028-01", "2028-02", "2028-03"]

    @pytest.mark.parametrize("bad", ["2026-13", "2026-1", "26-10", "", "2026/10"])
    def test_invalid_month_rejected(self, v2, bad):
        with pytest.raises(v2.ContractError):
            v2.build_periods(bad)

    def test_reversed_bounds_rejected(self, v2):
        with pytest.raises(v2.ContractError):
            v2.month_range("2026-10", "2026-01")

    def test_duplicate_period_ids_rejected(self, v2):
        period = v2._period_for("month", "2026-10")
        with pytest.raises(v2.ContractError):
            v2._validate_periods([period, period])


class TestCutoffResolution:
    def test_declared_cutoff_is_recorded_as_declared(self, v2):
        assert v2.cutoff_from_last_complete_month("2026-10") == ("2026-10", "declared")

    def test_omitted_cutoff_falls_back_to_clock_and_says_so(self, v2):
        from datetime import date

        cutoff, source = v2.cutoff_from_last_complete_month(None, today=date(2026, 11, 5))

        assert cutoff == "2026-10"
        assert source == "utc-clock"

    def test_previous_month_across_a_year_boundary(self, v2):
        from datetime import date

        cutoff, _ = v2.cutoff_from_last_complete_month(None, today=date(2027, 1, 3))

        assert cutoff == "2026-12"


class TestAggregates:
    def _rows(self) -> list[dict[str, object]]:
        return [
            # Punggol HDB across three months; monthly medians differ so the
            # period median can only be right if computed from transactions.
            {
                "month": "2026-01",
                "property_type": "hdb",
                "is_ec": False,
                "planning_area": "PUNGGOL",
                "price": 400000.0,
                "psf": 500.0,
            },
            {
                "month": "2026-02",
                "property_type": "hdb",
                "is_ec": False,
                "planning_area": "PUNGGOL",
                "price": 600000.0,
                "psf": 600.0,
            },
            {
                "month": "2026-03",
                "property_type": "hdb",
                "is_ec": False,
                "planning_area": "PUNGGOL",
                "price": 700000.0,
                "psf": None,
            },
            # A condo row for the national scope only.
            {
                "month": "2026-02",
                "property_type": "condo",
                "is_ec": False,
                "planning_area": "TAMPINES",
                "price": 1800000.0,
                "psf": 1900.0,
            },
        ]

    def test_period_median_uses_transactions_not_monthly_medians(self, v2):
        frame = _frame(self._rows())
        periods = [v2._period_for("ytd", "2026-03")]

        observations, months = v2.build_observations(
            frame, periods, include_areas=True, covered_months=set(frame["month"])
        )
        punggol = next(
            o for o in observations if o["geographyId"] == "PUNGGOL" and o["propertyType"] == "hdb"
        )

        assert months == ["2026-01", "2026-02", "2026-03"]
        assert punggol["metrics"]["transactionCount"]["value"] == 3
        # Median of {400k, 600k, 700k} = 600k. The monthly medians were
        # 400k/600k/700k, whose mean would also be 566k — different value.
        assert punggol["metrics"]["medianPrice"]["value"] == 600000.0

    def test_null_psf_is_excluded_and_counted_separately(self, v2):
        frame = _frame(self._rows())
        periods = [v2._period_for("ytd", "2026-03")]
        observations, _ = v2.build_observations(
            frame, periods, include_areas=False, covered_months=set(frame["month"])
        )
        hdb = next(o for o in observations if o["propertyType"] == "hdb")

        assert hdb["metrics"]["transactionCount"]["value"] == 3
        assert hdb["metrics"]["medianPsf"]["value"] == pytest.approx(550.0)
        assert hdb["metrics"]["medianPsf"]["observations"] == 2

    def test_zero_sales_scope_keeps_count_zero_and_null_medians(self, v2):
        frame = _frame(self._rows())
        periods = [v2._period_for("month", "2026-03")]
        observations, _ = v2.build_observations(
            frame, periods, include_areas=True, covered_months=set(frame["month"])
        )
        ec = next(o for o in observations if o["geographyId"] == "SG" and o["propertyType"] == "ec")

        assert ec["status"] == "no-sales"
        assert ec["metrics"]["transactionCount"]["value"] == 0
        assert ec["metrics"]["medianPrice"]["value"] is None
        assert ec["metrics"]["medianPsf"]["value"] is None

    def test_missing_month_is_reported_not_zero_filled(self, v2):
        frame = _frame(self._rows())
        periods = [v2._period_for("year", "2025-12")]

        observations, _ = v2.build_observations(
            frame, periods, include_areas=False, covered_months={"2026-01", "2026-02"}
        )
        all_types = next(o for o in observations if o["propertyType"] == "all")

        # The requested window is outside coverage: no rows, no invented zero
        # sales claim beyond the empty count itself.
        assert all_types["coverage"]["months"] == []
        assert all_types["coverage"]["requestedMonths"] == 12
        assert all_types["metrics"]["transactionCount"]["value"] == 0


class TestRollingQuarter:
    def test_bounds_months_and_comparator(self, v2):
        period = v2._period_for("rolling3", "2026-10")

        assert period.id == "rolling3_2026_10"
        assert period.kind == "rolling3"
        assert period.start_month == "2026-08"
        assert period.end_month == "2026-10"
        assert period.months == ("2026-08", "2026-09", "2026-10")
        assert period.comparator_id == "rolling3_2025_10"

    def test_build_periods_publishes_the_cutoff_quarter(self, v2):
        periods = {p.id: p for p in v2.build_periods("2026-10")}

        assert "rolling3_2026_10" in periods
        assert periods["rolling3_2026_10"].months == ("2026-08", "2026-09", "2026-10")

    def test_exact_three_month_edges_across_a_year_boundary(self, v2):
        assert v2._period_for("rolling3", "2026-02").months == (
            "2025-12",
            "2026-01",
            "2026-02",
        )
        assert v2._period_for("rolling3", "2026-01").months == (
            "2025-11",
            "2025-12",
            "2026-01",
        )
        assert v2._period_for("rolling3", "2026-03").months == (
            "2026-01",
            "2026-02",
            "2026-03",
        )

    def test_comparator_quarter_is_published_only_when_fully_covered(self, v2):
        complete = {
            p.id
            for p in v2.build_periods(
                "2026-10",
                covered_months={"2025-08", "2025-09", "2025-10", "2026-08", "2026-09", "2026-10"},
            )
        }
        partial = {
            p.id
            for p in v2.build_periods(
                "2026-10", covered_months={"2025-08", "2025-09", "2026-08", "2026-09", "2026-10"}
            )
        }

        assert "rolling3_2025_10" in complete
        assert "rolling3_2025_10" not in partial

    def test_quarter_count_is_a_transaction_count_not_a_month_sum_of_medians(self, v2):
        frame = _frame(
            [
                {
                    "month": month,
                    "property_type": "hdb",
                    "is_ec": False,
                    "planning_area": "PUNGGOL",
                    "price": price,
                    "psf": 500.0,
                }
                for month, price in (
                    ("2026-08", 400000.0),
                    ("2026-09", 600000.0),
                    ("2026-10", 700000.0),
                )
            ]
        )
        period = v2._period_for("rolling3", "2026-10")
        observations, _ = v2.build_observations(
            frame, [period], include_areas=False, covered_months=set(frame["month"])
        )
        hdb = next(o for o in observations if o["propertyType"] == "hdb")

        assert hdb["metrics"]["transactionCount"]["value"] == 3
        assert hdb["metrics"]["medianPrice"]["value"] == 600000.0


class TestMonthlyHistory:
    def _rows(self) -> list[dict[str, object]]:
        return [
            {
                "month": "2026-01",
                "property_type": "hdb",
                "is_ec": False,
                "planning_area": "PUNGGOL",
                "price": 400000.0,
                "psf": 500.0,
            },
            {
                "month": "2026-02",
                "property_type": "hdb",
                "is_ec": False,
                "planning_area": "PUNGGOL",
                "price": 600000.0,
                "psf": 600.0,
            },
            {
                "month": "2026-03",
                "property_type": "hdb",
                "is_ec": False,
                "planning_area": "BEDOK",
                "price": 700000.0,
                "psf": None,
            },
            {
                "month": "2026-03",
                "property_type": "condo",
                "is_ec": False,
                "planning_area": "TAMPINES",
                "price": 1800000.0,
                "psf": 1900.0,
            },
        ]

    def test_grid_is_aligned_and_cells_decode_by_field(self, v2):
        payloads = v2.build_monthly_history(_frame(self._rows()), cutoff_month="2026-03")
        hdb = payloads["area-monthly-hdb"]

        assert hdb["propertyType"] == "hdb"
        assert hdb["cellFields"] == list(v2.CELL_FIELDS)
        assert hdb["months"] == ["2026-01", "2026-02", "2026-03"]
        assert hdb["coverage"]["monthCount"] == 3
        for entry in hdb["series"]:
            assert len(entry["cells"]) == len(hdb["months"])
            assert all(len(cell) == len(v2.CELL_FIELDS) for cell in entry["cells"])

    def test_month_cell_matches_the_same_window_observation(self, v2):
        frame = _frame(self._rows())
        month = v2._period_for("month", "2026-01")
        observations, _ = v2.build_observations(
            frame, [month], covered_months=set(frame["month"]), include_areas=True
        )
        cell_observation = next(
            o for o in observations if o["geographyId"] == "PUNGGOL" and o["propertyType"] == "hdb"
        )
        payload = v2.build_monthly_history(frame, cutoff_month="2026-03")["area-monthly-hdb"]
        series = next(s for s in payload["series"] if s["geographyId"] == "PUNGGOL")
        cell = dict(zip(v2.CELL_FIELDS, series["cells"][0], strict=True))

        assert cell["transactionCount"] == cell_observation["metrics"]["transactionCount"]["value"]
        assert cell["medianPrice"] == cell_observation["metrics"]["medianPrice"]["value"]
        assert cell["medianPsf"] == cell_observation["metrics"]["medianPsf"]["value"]

    def test_covered_month_without_area_rows_is_no_sales_not_missing(self, v2):
        payload = v2.build_monthly_history(_frame(self._rows()), cutoff_month="2026-03")[
            "area-monthly-hdb"
        ]
        punggol = next(s for s in payload["series"] if s["geographyId"] == "PUNGGOL")
        march = dict(zip(v2.CELL_FIELDS, punggol["cells"][2], strict=True))

        assert march["transactionCount"] == 0
        assert march["medianPrice"] is None
        assert march["medianPsf"] is None
        assert punggol["noSalesMonths"] == 1

    def test_each_property_type_declares_its_own_coverage(self, v2):
        payloads = v2.build_monthly_history(_frame(self._rows()), cutoff_month="2026-03")

        # HDB is observed in January and February; the private types only in
        # March. A month outside a type's grid is missing source, not zero
        # sales — so the grids differ rather than being back-filled.
        assert payloads["area-monthly-hdb"]["months"] == ["2026-01", "2026-02", "2026-03"]
        assert payloads["area-monthly-condo"]["months"] == ["2026-03"]
        assert payloads["area-monthly-ec"]["months"] == []
        assert payloads["area-monthly-ec"]["coverage"]["firstMonth"] is None

    def test_national_series_leads_and_areas_are_namespaced(self, v2):
        payload = v2.build_monthly_history(_frame(self._rows()), cutoff_month="2026-03")[
            "area-monthly-all"
        ]

        assert payload["series"][0]["geographyId"] == v2.NATIONAL_ID
        assert [s["geographyId"] for s in payload["series"]][1:] == ["BEDOK", "PUNGGOL", "TAMPINES"]

    def test_include_areas_false_publishes_only_the_national_series(self, v2):
        payload = v2.build_monthly_history(
            _frame(self._rows()), cutoff_month="2026-03", include_areas=False
        )["area-monthly-all"]

        assert [s["geographyId"] for s in payload["series"]] == [v2.NATIONAL_ID]

    def test_payload_carries_the_type_disposition(self, v2):
        payloads = v2.build_monthly_history(
            _frame(self._rows()),
            cutoff_month="2026-03",
            dispositions={"hdb": "publish", "ec": "withhold"},
        )

        assert payloads["area-monthly-hdb"]["disposition"] == "publish"
        assert payloads["area-monthly-condo"]["disposition"] == "limited-display"

    def test_named_areas_are_not_the_whole_geography_list(self, v2):
        payload = v2.build_monthly_history(_frame(self._rows()), cutoff_month="2026-03")[
            "area-monthly-all"
        ]

        # SG is national, and a consumer that counts series as areas would be
        # off by one before any transaction is read. The payload says so.
        assert payload["geographies"] == {
            "national": "SG",
            "unassigned": [],
            "areaCount": 3,
        }

    def test_unassigned_transactions_are_declared_not_named_as_an_area(self, v2):
        rows = [
            *self._rows(),
            # The pipeline could not assign these rows to a planning area. They
            # are real transactions: they belong to the national scope and get
            # their own series, but they are not an area.
            {
                "month": "2026-03",
                "property_type": "hdb",
                "is_ec": False,
                "planning_area": "NONE",
                "price": 300000.0,
                "psf": 400.0,
            },
        ]
        payload = v2.build_monthly_history(_frame(rows), cutoff_month="2026-03")["area-monthly-hdb"]

        assert payload["geographies"] == {
            "national": "SG",
            "unassigned": ["NONE"],
            "areaCount": 3,
        }
        ids = [entry["geographyId"] for entry in payload["series"]]
        assert ids == ["SG", "NONE", "BEDOK", "PUNGGOL", "TAMPINES"]
        national = payload["series"][0]
        assert national["cells"][2][0] == 2  # BEDOK + the unassigned row
        unassigned = payload["series"][1]
        assert unassigned["cells"][2][0] == 1


class TestDispositions:
    def test_default_is_the_cautious_disposition(self, v2):
        resolved = v2._resolve_dispositions({})

        assert set(resolved.values()) == {"limited-display"}

    def test_combined_scope_is_only_as_publishable_as_its_weakest_member(self, v2):
        resolved = v2._resolve_dispositions(
            {"hdb": "publish", "ec": "withhold", "condo": "publish"}
        )

        assert resolved["all"] == "withhold"
        assert resolved["hdb"] == "publish"

    def test_explicit_combined_disposition_is_kept(self, v2):
        resolved = v2._resolve_dispositions({"hdb": "publish", "all": "limited-display"})

        assert resolved["all"] == "limited-display"

    def test_unknown_disposition_is_rejected(self, v2):
        with pytest.raises(v2.ContractError):
            v2._resolve_dispositions({"hdb": "yes"})
        with pytest.raises(v2.ContractError):
            v2.build_observations(
                _frame([]), [v2._period_for("month", "2026-10")], dispositions={"hdb": "yes"}
            )


class TestPackIdentity:
    def _emit(self, v2, tmp_path: Path, *, price: float = 500000.0):
        frame = _frame(
            [
                {
                    "month": "2026-10",
                    "property_type": "hdb",
                    "is_ec": False,
                    "planning_area": "PUNGGOL",
                    "price": price,
                    "psf": 500.0,
                },
            ]
        )
        periods = v2.build_periods("2026-10", covered_months={"2026-10"})
        observations, months = v2.build_observations(
            frame, periods, covered_months=set(months_of(frame))
        )
        summary = {
            "schemaVersion": v2.SCHEMA_VERSION,
            "cutoffMonth": "2026-10",
            "monthsPresent": months,
            "observations": observations,
        }
        periods_payload = {
            "schemaVersion": v2.SCHEMA_VERSION,
            "periods": [p.as_dict() for p in periods],
        }
        monthly_payloads = v2.build_monthly_history(
            frame, cutoff_month="2026-10", include_areas=True
        )
        return v2.emit_pack(
            output_dir=tmp_path,
            summary=summary,
            periods_payload=periods_payload,
            cutoff_month="2026-10",
            cutoff_source="declared",
            inputs={"unified_dataset": "a" * 64},
            monthly_payloads=monthly_payloads,
        )

    def test_identical_inputs_emit_identical_bytes(self, v2, tmp_path):
        first = tmp_path / "a"
        second = tmp_path / "b"
        result_a = self._emit(v2, first)
        result_b = self._emit(v2, second)

        assert result_a.generation == result_b.generation
        assert set(result_a.roles) == {
            "periods",
            "summary",
            "area-monthly-all",
            "area-monthly-hdb",
            "area-monthly-ec",
            "area-monthly-condo",
        }
        for role in result_a.roles:
            assert (first / result_a.roles[role]["path"]).read_bytes() == (
                second / result_b.roles[role]["path"]
            ).read_bytes()

    def test_payloads_do_not_embed_their_generation(self, v2, tmp_path):
        result = self._emit(v2, tmp_path)
        for role in result.roles:
            raw = gzip.decompress((tmp_path / result.roles[role]["path"]).read_bytes())
            assert result.generation.encode() not in raw

    def test_changing_one_transaction_changes_the_generation(self, v2, tmp_path):
        first = self._emit(v2, tmp_path / "a", price=500000.0)
        second = self._emit(v2, tmp_path / "b", price=500001.0)

        assert first.generation != second.generation

    def test_verify_pack_passes_and_detects_tampering(self, v2, tmp_path):
        result = self._emit(v2, tmp_path)
        assert v2.verify_pack(result.manifest_path) == []

        target = tmp_path / result.roles["summary"]["path"]
        payload = bytearray(target.read_bytes())
        payload[-1] = payload[-1] ^ 0xFF
        target.write_bytes(bytes(payload))

        problems = v2.verify_pack(result.manifest_path)
        assert any("hash mismatch" in problem for problem in problems)

    def test_a_tampered_monthly_asset_is_detected(self, v2, tmp_path):
        result = self._emit(v2, tmp_path)
        target = tmp_path / result.roles["area-monthly-hdb"]["path"]
        payload = bytearray(target.read_bytes())
        payload[-1] = payload[-1] ^ 0xFF
        target.write_bytes(bytes(payload))

        problems = v2.verify_pack(result.manifest_path)
        assert any("area-monthly-hdb" in problem for problem in problems)

    def test_every_history_role_is_a_published_asset(self, v2, tmp_path):
        result = self._emit(v2, tmp_path)
        manifest = json.loads(result.manifest_path.read_text())

        roles = [asset["role"] for asset in manifest["assets"]]
        assert roles[:2] == ["periods", "summary"]
        assert sorted(roles[2:]) == [
            "area-monthly-all",
            "area-monthly-condo",
            "area-monthly-ec",
            "area-monthly-hdb",
        ]
        assert set(manifest["identity"]["roles"]) == set(result.roles)
        for asset in manifest["assets"]:
            assert asset["path"] == f"observed/{manifest['generation']}/{asset['role']}.json.gz"

    def test_manifest_is_written_last_and_points_inside_the_pack(self, v2, tmp_path):
        result = self._emit(v2, tmp_path)
        manifest = json.loads(result.manifest_path.read_text())

        assert manifest["cutoffMonth"] == "2026-10"
        assert manifest["cutoffSource"] == "declared"
        for asset in manifest["assets"]:
            assert asset["path"].startswith(f"observed/{manifest['generation']}/")
            assert (tmp_path / asset["path"]).is_file()

    def test_sanitizer_keeps_booleans_and_nulls_distinct(self, v2):
        cleaned = v2.sanitize({"flag": True, "count": 3, "missing": float("nan")})

        assert cleaned == {"flag": True, "count": 3, "missing": None}
        assert isinstance(cleaned["flag"], bool)

    def test_canonical_hash_ignores_key_order(self, v2):
        first = v2.canonical_json_bytes({"b": 1, "a": 2})
        second = v2.canonical_json_bytes({"a": 2, "b": 1})

        assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()


def months_of(frame: pd.DataFrame) -> list[str]:
    return sorted(str(value) for value in frame["month"].unique())
