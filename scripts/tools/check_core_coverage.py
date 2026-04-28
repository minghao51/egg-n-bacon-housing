"""Fail CI when core pipeline modules fall below minimum line coverage."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_MIN_COVERAGE = 60.0
CORE_MODULES = [
    "src/egg_n_bacon_housing/components/01_ingestion.py",
    "src/egg_n_bacon_housing/components/02_cleaning.py",
    "src/egg_n_bacon_housing/components/03_features.py",
    "src/egg_n_bacon_housing/components/04_export.py",
    "src/egg_n_bacon_housing/components/05_metrics.py",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--coverage-xml", default="coverage.xml", help="Path to coverage XML report"
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=DEFAULT_MIN_COVERAGE,
        help="Minimum allowed line coverage percentage per core module",
    )
    return parser.parse_args()


def load_line_rates(coverage_xml: Path) -> dict[str, float]:
    root = ET.parse(coverage_xml).getroot()
    rates: dict[str, float] = {}
    for class_node in root.findall(".//class"):
        filename = class_node.get("filename")
        line_rate = class_node.get("line-rate")
        if not filename or line_rate is None:
            continue
        rates[filename] = float(line_rate) * 100.0
    return rates


def main() -> int:
    args = parse_args()
    coverage_path = Path(args.coverage_xml)
    if not coverage_path.exists():
        print(f"Coverage XML not found: {coverage_path}", file=sys.stderr)
        return 2

    line_rates = load_line_rates(coverage_path)

    failures: list[tuple[str, float]] = []
    for module in CORE_MODULES:
        rate = line_rates.get(module, 0.0)
        if rate < args.min_coverage:
            failures.append((module, rate))

    if failures:
        print("Core coverage gate failed:")
        for module, rate in failures:
            print(f"  - {module}: {rate:.1f}% (required >= {args.min_coverage:.1f}%)")
        return 1

    print(f"Core coverage gate passed ({len(CORE_MODULES)} modules >= {args.min_coverage:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
