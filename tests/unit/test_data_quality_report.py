import tempfile
from pathlib import Path

from scripts.core.data_quality import DataQualityCollector, QualitySnapshot
from scripts.utils.data_quality_report import format_summary_report, generate_summary_report


def test_generate_summary_report():
    """Test generating summary report."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        collector = DataQualityCollector(db_path)

        # Add some snapshots
        for i in range(5):
            snapshot = QualitySnapshot(
                timestamp=f"2026-03-03 12:0{i}:00",
                dataset_name=f"test_dataset_{i}",
                input_rows=1000,
                output_rows=1000,
                duplicate_count=0,
                null_percentage=2.0,
                columns=["col1"],
                data_types={"col1": "int64"},
                source="test",
                stage="L1",
            )
            collector.record_snapshot(snapshot)

        # Generate report
        report = generate_summary_report(db_path, limit=5)

        assert len(report) == 5
        assert "id" in report[0]
        assert "dataset_name" in report[0]
        assert "output_rows" in report[0]


def test_generate_summary_report_orders_latest_insert_first():
    """Test summary ordering is stable when timestamps match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        collector = DataQualityCollector(db_path)

        for suffix in ("first", "second"):
            snapshot = QualitySnapshot(
                timestamp="2026-03-03 12:00:00",
                dataset_name=f"test_dataset_{suffix}",
                input_rows=1000,
                output_rows=1000,
                duplicate_count=0,
                null_percentage=2.0,
                columns=["col1"],
                data_types={"col1": "int64"},
                source="test",
                stage="L1",
            )
            collector.record_snapshot(snapshot)

        report = generate_summary_report(db_path, limit=2)

        assert [row["dataset_name"] for row in report] == [
            "test_dataset_second",
            "test_dataset_first",
        ]


def test_format_summary_report_suppresses_known_duplicate_heavy_warnings():
    """Test report formatting for datasets that are expected to contain duplicates."""
    report = [
        {
            "id": 1,
            "timestamp": "2026-03-03 12:00:00",
            "dataset_name": "L3_property_nearby_facilities",
            "output_rows": 100,
            "duplicate_count": 25,
            "null_percentage": 1.5,
            "input_rows": 100,
        }
    ]

    formatted = format_summary_report(report)

    assert "25" in formatted
    assert "✅ OK (expected duplicates)" in formatted
