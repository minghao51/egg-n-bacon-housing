"""Tests for scripts/export_app_data.py — completed-months drop rule and release manifest.

Synthetic frames only: no parquet IO, no full export runs.
"""

import hashlib
import importlib.util
import json
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


class TestMonthPolicy:
    """The published-month boundary is declared, not read off the clock.

    The same parquet exported on 2026-10-24 and again on 2026-11-03 used to
    publish different trailing months, because the drop rule asked the wall
    clock whether October was complete. A declared month removes that.
    """

    def test_parses_declared_month(self, export_mod):
        assert export_mod.parse_last_complete_month("2026-09") == pd.Period("2026-09", freq="M")
        assert export_mod.parse_last_complete_month(" 2026-01 ") == pd.Period("2026-01", freq="M")

    @pytest.mark.parametrize("raw", ["2026-9", "2026-13", "2026-00", "26-09", "", "2026-09-01"])
    def test_rejects_malformed_month(self, export_mod, raw):
        with pytest.raises(ValueError):
            export_mod.parse_last_complete_month(raw)

    def test_declared_policy_maps_to_first_of_following_month(self, export_mod):
        policy = export_mod.resolve_month_policy(
            pd.Period("2026-10", freq="M"), "2026-09", today=date(2026, 11, 3)
        )
        assert policy.last_complete_month == pd.Period("2026-09", freq="M")
        assert policy.as_of == date(2026, 10, 1)
        assert policy.resolved_from == "declared"

    def test_declared_policy_is_clock_independent(self, export_mod):
        latest = pd.Period("2026-10", freq="M")
        early = export_mod.resolve_month_policy(latest, "2026-09", today=date(2026, 10, 24))
        late = export_mod.resolve_month_policy(latest, "2026-09", today=date(2027, 3, 2))
        assert early == late

    def test_declared_month_after_source_is_rejected(self, export_mod):
        with pytest.raises(ValueError, match="after the latest source month"):
            export_mod.resolve_month_policy(pd.Period("2026-09", freq="M"), "2026-10")

    def test_clock_fallback_is_labelled(self, export_mod):
        policy = export_mod.resolve_month_policy(
            pd.Period("2026-10", freq="M"), today=date(2026, 11, 3)
        )
        assert policy.last_complete_month == pd.Period("2026-10", freq="M")
        assert policy.as_of == date(2026, 11, 3)
        assert policy.resolved_from == "utc-clock"
        assert policy.manifest_block() == {
            "lastCompleteMonth": "2026-10",
            "resolvedFrom": "utc-clock",
        }

    def test_declared_policy_drops_later_months(self, export_mod):
        policy = export_mod.resolve_month_policy(pd.Period("2026-10", freq="M"), "2026-09")
        df = pd.DataFrame({"month": ["2026-08", "2026-09", "2026-10"]})
        result = export_mod.drop_incomplete_trailing_month(df, "month", today=policy.as_of)
        assert list(result["month"]) == ["2026-08", "2026-09"]


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


# ---------------------------------------------------------------------------
# Release manifest / publication compatibility metadata
# ---------------------------------------------------------------------------

_SOURCE_IDENTITIES = [
    {
        "name": "unified_dataset",
        "path": "data/pipeline/04_platinum/unified_dataset.parquet",
        "sha256": "a" * 64,
        "bytes": 1024,
        "rows": 3,
        "columns": ["price", "psf"],
    },
    {
        "name": "pa_monthly_metrics",
        "path": "data/pipeline/04_platinum/metrics/pa_monthly_metrics.parquet",
        "sha256": "b" * 64,
        "bytes": 512,
        "rows": 12,
        "columns": ["planning_area", "month", "median_price"],
    },
]


def _synthetic_payloads() -> dict[str, object]:
    """Seven payload-shaped objects; months drive the observation range."""
    months = [f"2025-{month:02d}" for month in range(1, 13)] + [
        f"2026-{month:02d}" for month in range(1, 10)
    ]
    return {
        "dashboard_overview.json.gz": {
            "metadata": {"total_records": 100},
            "stats": {},
            "distributions": {},
        },
        "dashboard_trends.json.gz": [{"date": month, "Overall Price": 500_000} for month in months],
        "dashboard_segments.json.gz": {"whole": []},
        "dashboard_leaderboard.json.gz": [{"planning_area": "BEDOK"}],
        "map_metrics.json.gz": {"whole": {}},
        "hotspots.json.gz": {"BEDOK": {"category": "Moderate Growth"}},
        "amenity_summary.json.gz": [{"planning_area": "BEDOK"}],
    }


def _publish_payloads(root: Path, payloads: dict[str, object]) -> dict[str, dict[str, int | str]]:
    """Write payload files and return their real hashes/bytes.

    The files are gzipped exactly like the exporter writes them so the recorded
    ``contentSha256`` is the hash of the decompressed JSON text, which is what a
    browser can verify when the host applies ``Content-Encoding: gzip``.
    """
    import gzip

    root.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, dict[str, int | str]] = {}
    for filename, payload in payloads.items():
        text = json.dumps(payload)
        raw = gzip.compress(text.encode("utf-8"), mtime=0)
        (root / filename).write_bytes(raw)
        hashes[filename] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "contentSha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "bytes": len(raw),
        }
    return hashes


def _manifest(export_mod, payloads, hashes, *, generated_at=None, excluded_transactions=None):
    return export_mod.build_release_manifest(
        payloads,
        hashes,
        _SOURCE_IDENTITIES,
        generated_at=generated_at or datetime(2026, 10, 24, 12, 0, tzinfo=UTC),
        excluded_transactions=excluded_transactions,
    )


def _walk(value):
    if isinstance(value, dict):
        for nested in value.values():
            yield from _walk(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk(nested)
    else:
        yield value


class TestReleaseManifestContent:
    def test_records_each_asset_and_verifies_clean_tree(self, export_mod, tmp_path):
        payloads = _synthetic_payloads()
        hashes = _publish_payloads(tmp_path, payloads)

        manifest = _manifest(export_mod, payloads, hashes, excluded_transactions=2)

        assert manifest["schemaVersion"] == export_mod.RELEASE_SCHEMA_VERSION
        assert manifest["generatedAt"] == "2026-10-24T12:00:00Z"
        assert [asset["path"] for asset in manifest["assets"]] == list(export_mod.DASHBOARD_FILES)
        for asset in manifest["assets"]:
            raw = (tmp_path / asset["path"]).read_bytes()
            assert asset["sha256"] == hashlib.sha256(raw).hexdigest()
            assert asset["bytes"] == len(raw)
            assert asset["shape"] == (
                "array" if isinstance(payloads[asset["path"]], list) else "object"
            )
            assert asset["metricScopes"], f"{asset['path']} claims no metric scope"
        assert manifest["inclusionRules"]["excludedTransactions"] == 2
        assert export_mod.verify_release_manifest(manifest, tmp_path) == []

    def test_manifest_has_no_floats_and_json_serialises(self, export_mod, tmp_path):
        payloads = _synthetic_payloads()
        hashes = _publish_payloads(tmp_path, payloads)

        manifest = _manifest(export_mod, payloads, hashes, excluded_transactions=2)

        assert not [value for value in _walk(manifest) if isinstance(value, float)]
        # No numpy/pandas scalar leakage: strict dumps would reject them.
        assert json.dumps(manifest, allow_nan=False)

    def test_manifest_records_trailing_month_policy(self, export_mod, tmp_path):
        payloads = _synthetic_payloads()
        hashes = _publish_payloads(tmp_path, payloads)
        policy = export_mod.resolve_month_policy(pd.Period("2026-10", freq="M"), "2026-09")

        manifest = export_mod.build_release_manifest(
            payloads,
            hashes,
            _SOURCE_IDENTITIES,
            generated_at=datetime(2026, 11, 3, 12, 0, tzinfo=UTC),
            month_policy=policy,
        )

        assert manifest["trailingMonth"] == {
            "lastCompleteMonth": "2026-09",
            "resolvedFrom": "declared",
        }
        # The policy feeds the generation id: a clock-derived release must not
        # be able to claim the identity of a declared one.
        clock_manifest = export_mod.build_release_manifest(
            payloads,
            hashes,
            _SOURCE_IDENTITIES,
            generated_at=datetime(2026, 11, 3, 12, 0, tzinfo=UTC),
            month_policy=export_mod.resolve_month_policy(
                pd.Period("2026-10", freq="M"), today=date(2026, 11, 3)
            ),
        )
        assert clock_manifest["generation"] != manifest["generation"]

    def test_manifest_omits_trailing_month_when_no_policy_given(self, export_mod, tmp_path):
        payloads = _synthetic_payloads()
        hashes = _publish_payloads(tmp_path, payloads)

        manifest = _manifest(export_mod, payloads, hashes)

        assert "trailingMonth" not in manifest

    def test_staged_gzip_bytes_are_stable_across_runs(self, export_mod, tmp_path):
        """Unchanged payloads must stage byte-identical files.

        ``gzip.open`` stamps the write time into the header, which dirtied
        every published asset on re-export even when the data was unchanged.
        """
        payload = _synthetic_payloads()["hotspots.json.gz"]
        first = export_mod.stage_json_gzip(payload, tmp_path / "hotspots.json.gz")
        digest_one = hashlib.sha256(first.read_bytes()).hexdigest()
        first.unlink()

        second = export_mod.stage_json_gzip(payload, tmp_path / "hotspots.json.gz")
        assert hashlib.sha256(second.read_bytes()).hexdigest() == digest_one

        import gzip

        with gzip.open(second, "rt", encoding="utf-8") as handle:
            assert json.load(handle) == payload

    def test_observation_range_is_derived_from_frame_months(self, export_mod, tmp_path):
        payloads = _synthetic_payloads()
        hashes = _publish_payloads(tmp_path, payloads)

        manifest = _manifest(export_mod, payloads, hashes)

        assert manifest["observationRange"] == {
            "startMonth": "2025-01",
            "endMonth": "2026-09",
            "completeYear": 2025,
        }

    def test_period_definitions_match_era_filters(self, export_mod, tmp_path):
        payloads = _synthetic_payloads()
        hashes = _publish_payloads(tmp_path, payloads)

        definitions = _manifest(export_mod, payloads, hashes)["periodDefinitions"]

        assert set(definitions) == set(export_mod.ERA_FILTERS)
        for era, rule in export_mod.ERA_FILTERS.items():
            assert definitions[era]["filter"] == rule
            assert definitions[era]["label"] == export_mod.PERIOD_LITERALS[era]
        assert "all history" in definitions["whole"]["label"]
        assert "2021" in definitions["pre_covid"]["label"]
        assert "2022" in definitions["recent"]["label"]
        assert "2025" in definitions["year_2025"]["label"]


class TestVerifyReleaseManifest:
    def _fresh(self, export_mod, tmp_path):
        payloads = _synthetic_payloads()
        hashes = _publish_payloads(tmp_path, payloads)
        return payloads, hashes, _manifest(export_mod, payloads, hashes)

    def test_detects_modified_byte(self, export_mod, tmp_path):
        _, _, manifest = self._fresh(export_mod, tmp_path)
        target = tmp_path / "hotspots.json.gz"
        target.write_bytes(target.read_bytes() + b" ")

        problems = export_mod.verify_release_manifest(manifest, tmp_path)

        # A byte-level change is reported both as a file hash mismatch and, when
        # the gzip stream can no longer be read, as a content mismatch.
        assert any("hotspots.json.gz" in problem and "mismatch" in problem for problem in problems)

    def test_detects_missing_asset(self, export_mod, tmp_path):
        _, _, manifest = self._fresh(export_mod, tmp_path)
        (tmp_path / "dashboard_trends.json.gz").unlink()

        problems = export_mod.verify_release_manifest(manifest, tmp_path)

        assert "missing asset file: dashboard_trends.json.gz" in problems

    def test_detects_unexpected_asset(self, export_mod, tmp_path):
        _, _, manifest = self._fresh(export_mod, tmp_path)
        manifest["assets"].append(
            {"path": "extra.json.gz", "sha256": "0" * 64, "bytes": 1, "shape": "object"}
        )

        problems = export_mod.verify_release_manifest(manifest, tmp_path)

        assert "unexpected asset: extra.json.gz" in problems
        assert any(problem.startswith("asset count") for problem in problems)

    def test_detects_wrong_schema_version(self, export_mod, tmp_path):
        _, _, manifest = self._fresh(export_mod, tmp_path)
        manifest["schemaVersion"] = "9.9.9"

        problems = export_mod.verify_release_manifest(manifest, tmp_path)

        assert any(problem.startswith("schemaVersion") for problem in problems)


class TestReleaseGeneration:
    def test_deterministic_across_generated_at(self, export_mod, tmp_path):
        payloads = _synthetic_payloads()
        hashes = _publish_payloads(tmp_path, payloads)

        first = _manifest(
            export_mod, payloads, hashes, generated_at=datetime(2026, 1, 1, tzinfo=UTC)
        )
        second = _manifest(
            export_mod, payloads, hashes, generated_at=datetime(2026, 6, 1, tzinfo=UTC)
        )

        assert first["generatedAt"] != second["generatedAt"]
        assert first["generation"] == second["generation"]

    def test_changes_when_an_asset_hash_changes(self, export_mod, tmp_path):
        payloads = _synthetic_payloads()
        hashes = _publish_payloads(tmp_path, payloads)
        baseline = _manifest(export_mod, payloads, hashes)

        changed = {name: dict(record) for name, record in hashes.items()}
        record = changed["hotspots.json.gz"]
        record["sha256"] = "0" * 64
        record["bytes"] = int(record["bytes"]) + 1
        mutated = _manifest(export_mod, payloads, changed)

        assert mutated["generation"] != baseline["generation"]


class TestExportReleaseOrdering:
    """Export swaps the seven payloads first and the release manifest last."""

    def _synthetic_frames(self):
        unified = pd.DataFrame(
            {
                "transaction_date": pd.to_datetime(["2023-01-10", "2023-02-10", "2023-03-10"]),
                "price": [400_000.0, 420_000.0, 430_000.0],
                "psf": [500.0, 505.0, 510.0],
                "property_type": ["hdb", "hdb", "condo"],
                "is_ec": [False, False, False],
                "planning_area": ["BEDOK", "BEDOK", "TAMPINES"],
                "town": ["BEDOK", "BEDOK", "TAMPINES"],
                "rental_yield_pct": [4.0, 4.1, 3.5],
            }
        )
        pa_metrics = pd.DataFrame(
            {
                "planning_area": ["BEDOK"] * 12,
                "month": [f"2023-{month:02d}" for month in range(1, 13)],
                "median_price": [400_000.0 + 1_000 * month for month in range(12)],
            }
        )
        return unified, pa_metrics

    def _patch_pipeline(self, export_mod, monkeypatch):
        unified, pa_metrics = self._synthetic_frames()
        monkeypatch.setattr(export_mod, "load_inputs", lambda: (unified, pa_metrics))
        monkeypatch.setattr(export_mod, "load_area_metadata", lambda: {})
        monkeypatch.setattr(export_mod, "validate_payloads", lambda payloads: None)
        monkeypatch.setattr(
            export_mod,
            "describe_source_identities",
            lambda unified, pa_metrics: _SOURCE_IDENTITIES,
        )

    def test_manifest_stage_failure_keeps_previous_release(self, export_mod, monkeypatch, tmp_path):
        self._patch_pipeline(export_mod, monkeypatch)
        published = {}
        for filename in export_mod.DASHBOARD_FILES:
            published[filename] = f"previous-release:{filename}".encode()
            (tmp_path / filename).write_bytes(published[filename])

        original_stage = export_mod.stage_release_manifest

        def failing_stage(manifest, filepath):
            original_stage(manifest, filepath)  # writes the .tmp first
            raise RuntimeError("simulated manifest write failure")

        monkeypatch.setattr(export_mod, "stage_release_manifest", failing_stage)

        with pytest.raises(RuntimeError, match="simulated manifest write failure"):
            export_mod.export_app_data(tmp_path)

        for filename, raw in published.items():
            assert (tmp_path / filename).read_bytes() == raw
        assert not (tmp_path / export_mod.RELEASE_MANIFEST_NAME).exists()
        assert list(tmp_path.glob("*.tmp")) == []

    def test_manifest_is_written_last(self, export_mod, monkeypatch, tmp_path):
        self._patch_pipeline(export_mod, monkeypatch)
        replaced: list[str] = []
        real_replace = export_mod.os.replace

        def recording_replace(src, dst):
            replaced.append(Path(dst).name)
            return real_replace(src, dst)

        monkeypatch.setattr(export_mod.os, "replace", recording_replace)

        export_mod.export_app_data(tmp_path)

        assert replaced == [*export_mod.DASHBOARD_FILES, export_mod.RELEASE_MANIFEST_NAME]
        manifest = json.loads((tmp_path / export_mod.RELEASE_MANIFEST_NAME).read_text())
        assert manifest["schemaVersion"] == export_mod.RELEASE_SCHEMA_VERSION
        assert len(manifest["assets"]) == len(export_mod.DASHBOARD_FILES)
        assert export_mod.verify_release_manifest(manifest, tmp_path) == []
        assert list(tmp_path.glob("*.tmp")) == []


class TestReleaseContractSync:
    """The Python asset list and the Node verifier must not drift."""

    def test_node_verifier_lists_the_same_dashboard_files(self, export_mod):
        source = (
            Path(__file__).resolve().parent.parent / "app" / "scripts" / "validate-data.mjs"
        ).read_text()
        block = source.split("const RELEASE_ASSETS = [", 1)[1].split("];", 1)[0]
        node_files = [line.strip().strip('",') for line in block.splitlines() if line.strip()]
        assert node_files == list(export_mod.DASHBOARD_FILES)

    def test_manifest_scopes_hotspots_as_growth_not_price(self, export_mod):
        scopes = export_mod.ASSET_METRIC_SCOPES["hotspots.json.gz"]
        assert "spatial_hotspots" in scopes
        # hotspots carry growth statistics only: no price level, no era block.
        assert "median_price" not in scopes
        assert "by_time_period" not in scopes

    def test_source_identities_mark_publication_time_unknown(
        self, export_mod, tmp_path, monkeypatch
    ):
        """Identities carry the parquet bytes and never a publication time.

        Hermetic: CI has no platinum data, so the two source paths are pointed
        at parquets written here instead of the 78MB pipeline outputs.
        """
        unified_path = tmp_path / "unified_dataset.parquet"
        pa_metrics_path = tmp_path / "pa_monthly_metrics.parquet"
        pd.DataFrame({"a": [1]}).to_parquet(unified_path)
        pd.DataFrame({"b": [1, 2]}).to_parquet(pa_metrics_path)
        monkeypatch.setattr(
            export_mod, "input_source_paths", lambda: (unified_path, pa_metrics_path)
        )

        ids = export_mod.describe_source_identities(
            pd.DataFrame({"a": [1]}), pd.DataFrame({"b": [1, 2]})
        )

        assert all(identity["sourcePublishedAt"] is None for identity in ids)
        assert [identity["rows"] for identity in ids] == [1, 2]
        assert [identity["name"] for identity in ids] == [
            "unified_dataset",
            "pa_monthly_metrics",
        ]
        assert all(len(str(identity["sha256"])) == 64 for identity in ids)
        assert all(int(identity["bytes"]) > 0 for identity in ids)
