"""Tests for scripts/tools/quality_report.py (read-only quality report CLI).

Builds a tmp quality DB through the production write path
(``record_dataframe_quality``), tmp layer dirs with quarantine parquets and a
bronze manifest via ``record_bronze_fetch``, then asserts every report section:
anomaly flags, row-count deltas (incl. collapse-to-zero), quarantine parsing,
bronze freshness, JSON mode, read-only behavior, and exit codes.
"""

import importlib.util
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from egg_n_bacon_housing.config import LayerDirs
from egg_n_bacon_housing.utils.bronze import record_bronze_fetch
from egg_n_bacon_housing.utils.data_quality import record_dataframe_quality
from egg_n_bacon_housing.utils.layer_writer import SimpleWriter, resolve_layer_paths

pytestmark = pytest.mark.unit

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "tools" / "quality_report.py"


@pytest.fixture(scope="module")
def report_module() -> Any:
    """Load quality_report.py as a module (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location("quality_report", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def quality_tree(tmp_path: Path) -> dict[str, Any]:
    """Tmp data root with quality DB, quarantine parquets, and bronze manifest."""
    data_root = tmp_path / "data"
    pipeline = data_root / "pipeline"
    db_path = data_root / "quality_metrics.db"

    # Stable dataset: 5 identical snapshots → no anomaly, zero delta.
    for _ in range(5):
        record_dataframe_quality(
            pd.DataFrame({"a": range(100)}),
            dataset_name="stable",
            db_path=db_path,
            source="test",
            stage="L_silver",
        )

    # Collapse dataset: 100 rows then an empty (0-row) write.
    record_dataframe_quality(
        pd.DataFrame({"a": range(100)}), dataset_name="collapser", db_path=db_path, stage="L_silver"
    )
    record_dataframe_quality(
        pd.DataFrame({"a": pd.Series([], dtype="int64")}),
        dataset_name="collapser",
        db_path=db_path,
        stage="L_silver",
    )

    # Outlier dataset: 5×100-row baseline, then a 1000-row snapshot injected via
    # raw SQL so the stored baseline (mean=100, std=0) stays untouched — the
    # report must flag it (>50% row change against the stored baseline).
    for _ in range(5):
        record_dataframe_quality(
            pd.DataFrame({"a": range(100)}),
            dataset_name="outlier",
            db_path=db_path,
            source="test",
            stage="L_gold",
        )
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO run_snapshots "
            "(timestamp, dataset_name, stage, input_rows, output_rows, "
            "duplicate_count, null_percentage, column_count, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("2099-01-01 00:00:00", "outlier", "L_gold", 1000, 1000, 0, 0.0, 1, "test"),
        )
        conn.commit()
    finally:
        conn.close()

    # Quarantine parquets with the gateway's `_quarantine/<entity>_<ts>` naming.
    writer = SimpleWriter(data_dir=pipeline)
    writer.write(
        pd.DataFrame({"town": [f"T{i}" for i in range(10)]}),
        "_quarantine/HDB_20260101_120000",
        "silver",
        track_quality=False,
    )
    writer.write(
        pd.DataFrame({"town": [f"U{i}" for i in range(5)]}),
        "_quarantine/HDB_20260102_130000",
        "silver",
        track_quality=False,
    )
    writer.write(
        pd.DataFrame({"x": [1, 2]}),
        "_quarantine/Condo_sample_20260101_090000",
        "gold",
        track_quality=False,
    )
    writer.write(pd.DataFrame({"x": [1]}), "_quarantine/unparsed_name", "gold", track_quality=False)

    # Bronze manifest: one stale rolling dataset, one missing-with-parquet, one
    # threshold-free entry.
    bronze_dir = pipeline / "01_bronze"
    record_bronze_fetch(bronze_dir, "raw_hdb_resale", "datagov_api", 100)
    manifest_path = bronze_dir / "bronze_manifest.json"
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["raw_hdb_resale"]["fetched_at"] = (
        datetime.now(tz=UTC) - timedelta(days=40)
    ).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    record_bronze_fetch(bronze_dir, "external/MRTStations.geojson", "seed", 0)
    pd.DataFrame({"id": pd.Series([], dtype="int64")}).to_parquet(
        bronze_dir / "raw_condo_transactions.parquet", index=False
    )

    return {
        "data_root": data_root,
        "pipeline": pipeline,
        "db_path": db_path,
        "layer_paths": resolve_layer_paths(LayerDirs(), pipeline),
    }


@pytest.fixture()
def report(quality_tree: dict[str, Any], report_module: Any) -> dict[str, Any]:
    return report_module.build_report(quality_tree["db_path"], quality_tree["layer_paths"])


def _find(entries: list[dict[str, Any]], **match: Any) -> dict[str, Any]:
    hits = [e for e in entries if all(e[k] == v for k, v in match.items())]
    assert len(hits) == 1, f"expected exactly one match for {match}, got {hits}"
    return hits[0]


class TestTrends:
    def test_outlier_dataset_is_flagged(self, report: dict[str, Any]) -> None:
        trend = _find(report["trends"], dataset="outlier")
        assert trend["flagged"] is True
        assert trend["latest"]["rows"] == 1000
        assert trend["baseline"]["mean_rows"] == pytest.approx(100.0)
        assert any("Row count: 1000" in a for a in trend["anomalies"])
        assert "outlier [L_gold]" in report["flags"]["anomalous_datasets"]

    def test_stable_dataset_is_not_flagged(self, report: dict[str, Any]) -> None:
        trend = _find(report["trends"], dataset="stable")
        assert trend["flagged"] is False
        assert trend["latest"]["rows"] == 100
        assert trend["baseline"]["sample_count"] == 5
        assert trend["anomalies"] == []


class TestDeltas:
    def test_collapse_to_zero_detected(self, report: dict[str, Any]) -> None:
        delta = _find(report["deltas"], dataset="collapser")
        assert delta["previous_rows"] == 100
        assert delta["latest_rows"] == 0
        assert delta["row_delta"] == -100
        assert delta["pct_change"] == -100.0
        assert delta["collapse_to_zero"] is True
        assert "collapser [L_silver]" in report["flags"]["collapsed_datasets"]

    def test_stable_delta_is_zero(self, report: dict[str, Any]) -> None:
        delta = _find(report["deltas"], dataset="stable")
        assert delta["row_delta"] == 0
        assert delta["collapse_to_zero"] is False


class TestQuarantine:
    def test_counts_parsed_per_entity(self, report: dict[str, Any]) -> None:
        entities = report["quarantine"]["entities"]
        hdb = _find(entities, entity="HDB")
        assert hdb["layer"] == "silver"
        assert hdb["files"] == 2
        assert hdb["rows"] == 15
        assert hdb["newest"] == "20260102_130000"

        condo = _find(entities, entity="Condo_sample")
        assert condo["files"] == 1
        assert condo["rows"] == 2

        unparsed = _find(entities, entity="unparsed_name")
        assert unparsed["newest"] == ""  # timestamp unparseable → sorts last

    def test_newest_first_ordering_and_totals(self, report: dict[str, Any]) -> None:
        entities = report["quarantine"]["entities"]
        newest = [e["newest"] for e in entities]
        assert newest == sorted(newest, reverse=True)
        assert newest[-1] == ""
        assert report["quarantine"]["total_files"] == 4
        assert report["quarantine"]["total_rows"] == 18
        assert report["flags"]["quarantine_files"] == 4

    def test_top_limits_entities(self, quality_tree: dict[str, Any], report_module: Any) -> None:
        report = report_module.build_report(
            quality_tree["db_path"], quality_tree["layer_paths"], top=1
        )
        assert report["quarantine"]["shown"] == 1
        assert report["quarantine"]["total_entities"] == 3


class TestFreshness:
    def test_stale_entry_flagged(self, report: dict[str, Any]) -> None:
        entry = _find(report["freshness"]["entries"], name="raw_hdb_resale")
        assert entry["flagged"] is True
        assert entry["status"] == "stale"
        assert entry["threshold_days"] == 35
        assert entry["age_days"] > 35
        assert "raw_hdb_resale" in report["flags"]["stale_bronze"]

    def test_missing_manifest_entry_flagged_when_parquet_present(
        self, report: dict[str, Any]
    ) -> None:
        entry = _find(report["freshness"]["entries"], name="raw_condo_transactions")
        assert entry["flagged"] is True
        assert entry["status"] == "missing manifest entry (parquet present)"

    def test_threshold_free_entry_not_flagged(self, report: dict[str, Any]) -> None:
        entry = _find(report["freshness"]["entries"], name="external/MRTStations.geojson")
        assert entry["flagged"] is False
        assert entry["status"] == "ok"
        assert entry["threshold_days"] is None


class TestCli:
    def test_json_mode_is_valid_and_consistent(
        self, quality_tree: dict[str, Any], report_module: Any, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = report_module.main(["--json", "--data", str(quality_tree["data_root"])])
        out = capsys.readouterr().out
        assert exit_code == 0
        parsed = json.loads(out)

        direct = report_module.build_report(quality_tree["db_path"], quality_tree["layer_paths"])
        assert parsed["flags"] == direct["flags"]
        assert parsed["quarantine"]["entities"] == direct["quarantine"]["entities"]
        outlier = _find(parsed["trends"], dataset="outlier")
        assert outlier["flagged"] is True
        assert _find(parsed["freshness"]["entries"], name="raw_hdb_resale")["status"] == "stale"

    def test_human_report_read_only_and_exit_zero(
        self,
        tmp_path: Path,
        quality_tree: dict[str, Any],
        report_module: Any,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def tree_state() -> set[tuple[str, int]]:
            return {
                (str(p.relative_to(tmp_path)), p.stat().st_mtime_ns)
                for p in tmp_path.rglob("*")
                if p.is_file()
            }

        before = tree_state()
        exit_code = report_module.main(["--data", str(quality_tree["data_root"])])
        out = capsys.readouterr().out
        assert exit_code == 0
        for section in ("Snapshot trends", "Row-count deltas", "Quarantine", "Bronze freshness"):
            assert section in out
        assert "COLLAPSE TO ZERO" in out
        assert tree_state() == before  # nothing written, no mtime touched

    def test_missing_db_and_manifest_exit_zero(
        self, tmp_path: Path, report_module: Any, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = report_module.main(["--json", "--data", str(tmp_path / "empty")])
        out = capsys.readouterr().out
        assert exit_code == 0
        parsed = json.loads(out)
        assert parsed["quality_db"]["exists"] is False
        assert parsed["quality_db"]["snapshot_count"] == 0
        assert parsed["freshness"]["manifest_exists"] is False
        assert any("manifest not found" in note for note in parsed["freshness"]["notes"])
        assert parsed["flags"] == {
            "anomalous_datasets": [],
            "collapsed_datasets": [],
            "stale_bronze": [],
            "quarantine_files": 0,
            "quarantine_rows": 0,
        }

    def test_unreadable_db_exit_one(
        self, tmp_path: Path, report_module: Any, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bad_root = tmp_path / "bad"
        bad_root.mkdir()
        (bad_root / "quality_metrics.db").write_bytes(b"this is not a sqlite database")
        exit_code = report_module.main(["--json", "--data", str(bad_root)])
        assert exit_code == 1
        assert "unreadable" in capsys.readouterr().err

    def test_dataset_filter_narrows_all_sections(
        self, quality_tree: dict[str, Any], report_module: Any
    ) -> None:
        report = report_module.build_report(
            quality_tree["db_path"], quality_tree["layer_paths"], dataset="hdb"
        )
        assert [t["dataset"] for t in report["trends"]] == []
        assert [e["entity"] for e in report["quarantine"]["entities"]] == ["HDB"]
        assert all("hdb" in e["name"].lower() for e in report["freshness"]["entries"])
