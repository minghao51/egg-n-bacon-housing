#!/usr/bin/env python3
"""CLI reporter for data quality metrics.

Usage:
    uv run python scripts/utils/data_quality_report.py --summary
    uv run python scripts/utils/data_quality_report.py --summary --limit 20
"""

import argparse
import sqlite3
from pathlib import Path

from scripts.core.data_quality import get_duplicate_status


def generate_summary_report(db_path: Path, limit: int = 10) -> list[dict]:
    """Generate summary of recent runs.

    Args:
        db_path: Path to quality_metrics.db
        limit: Number of recent runs to show

    Returns:
        List of run dictionaries
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, timestamp, dataset_name, output_rows, duplicate_count,
               null_percentage, input_rows
        FROM run_snapshots
        ORDER BY timestamp DESC, id DESC
        LIMIT ?
    """,
        (limit,),
    )

    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "timestamp": row[1],
            "dataset_name": row[2],
            "output_rows": row[3],
            "duplicate_count": row[4],
            "null_percentage": row[5],
            "input_rows": row[6],
        }
        for row in rows
    ]


def format_summary_report(report: list[dict]) -> str:
    """Format summary report as table."""
    if not report:
        return "No quality data found."

    lines = []
    lines.append("Recent Data Quality Summary")
    lines.append("=" * 80)
    lines.append(
        f"{'Timestamp':<19} | {'Dataset':<25} | {'Rows':>10} | "
        f"{'Dups':>5} | {'Nulls':>6} | {'Status'}"
    )
    lines.append("-" * 80)

    for row in report:
        output_rows = row["output_rows"]

        # Status
        status, _ = get_duplicate_status(row["dataset_name"], row["duplicate_count"])

        lines.append(
            f"{row['timestamp']:<19} | {row['dataset_name']:<25} | "
            f"{output_rows:>10,} | {row['duplicate_count']:>5} | "
            f"{row['null_percentage']:>5.1f}% | {status}"
        )

    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Data quality report CLI")
    parser.add_argument("--summary", action="store_true", help="Show last N runs summary")
    parser.add_argument("--limit", type=int, default=10, help="Number of runs to show")
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to quality_metrics.db (default: data/quality_metrics.db)",
    )

    args = parser.parse_args()

    # Determine DB path
    if args.db_path:
        db_path = Path(args.db_path)
    else:
        try:
            from scripts.core.config import Config

            db_path = Config.DATA_DIR / "quality_metrics.db"
        except ImportError:
            # Fallback if run as script
            db_path = Path("data/quality_metrics.db")

    if not db_path.exists():
        print(f"❌ Quality database not found: {db_path}")
        print("Run the pipeline first to generate quality data.")
        return

    if args.summary:
        report = generate_summary_report(db_path, limit=args.limit)
        print(format_summary_report(report))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
