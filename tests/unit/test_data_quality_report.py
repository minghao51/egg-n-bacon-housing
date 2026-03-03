import tempfile
from pathlib import Path

from scripts.core.data_quality import DataQualityCollector, QualitySnapshot
from scripts.utils.data_quality_report import generate_summary_report


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
        assert "dataset_name" in report[0]
        assert "output_rows" in report[0]
