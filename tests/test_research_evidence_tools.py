"""Tests for the RS01/RS02 evidence tools.

Hermetic: tiny parquet/geojson fixtures in a temporary tree, with the tools'
path constants repointed at it. No network, no pipeline run, no repo state.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

pytestmark = pytest.mark.unit

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts" / "tools"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Dataclasses resolve their module through sys.modules during creation.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


@pytest.fixture()
def inventory():
    return _load("source_inventory")


@pytest.fixture()
def rental():
    module = _load("rental_yield_evidence")
    return module


def _point_inventory_at(module, root: Path) -> None:
    module.REPO_ROOT = root
    module.BRONZE_DIR = root / "data" / "pipeline" / "01_bronze"
    module.EXTERNAL_DIR = module.BRONZE_DIR / "external"
    module.MANUAL_DIR = root / "data" / "manual"
    module.PLATINUM_DIR = root / "data" / "pipeline" / "04_platinum"
    module.GOLD_DIR = root / "data" / "pipeline" / "03_gold"


def test_inventory_measures_rows_hash_and_coverage(inventory, tmp_path):
    _point_inventory_at(inventory, tmp_path)
    sales = pd.DataFrame(
        {
            "month": ["2025-01", "2025-02", "2025-02"],
            "town": ["BEDOK", "BEDOK", "PUNGGOL"],
            "resale_price": [400000, 410000, 500000],
        }
    )
    target = tmp_path / "data" / "pipeline" / "01_bronze" / "raw_hdb_resale.parquet"
    _write_parquet(target, sales)

    measured = inventory.measure_parquet(target, "bronze")

    assert measured.rows == 3
    assert measured.coverage == {"column": "month", "min": "2025-01", "max": "2025-02"}
    assert measured.sha256 == hashlib.sha256(target.read_bytes()).hexdigest()


def test_inventory_flags_a_csv_file_named_geojson(inventory, tmp_path):
    _point_inventory_at(inventory, tmp_path)
    # This is the real defect in data/manual/csv/datagov/: CSV under a .geojson name.
    target = tmp_path / "data" / "manual" / "csv" / "Kindergartens.geojson"
    target.parent.mkdir(parents=True)
    target.write_text("centre_code,centre_name\nPT9622,3HOUSE KINDERGARTEN\n", encoding="utf-8")

    measured = inventory.measure_file(target, "manual")

    assert measured.format == "delimited"
    assert measured.format_matches_extension is False
    assert measured.rows == 1


def test_inventory_marks_files_without_a_manifest_entry(inventory, tmp_path):
    _point_inventory_at(inventory, tmp_path)
    bronze = tmp_path / "data" / "pipeline" / "01_bronze"
    _write_parquet(bronze / "raw_hdb_resale.parquet", pd.DataFrame({"month": ["2025-01"]}))
    _write_parquet(
        bronze / "external" / "cpi.parquet",
        pd.DataFrame({"date": pd.to_datetime(["2025-01-01"]), "cpi": [100.0]}),
    )
    (bronze / "bronze_manifest.json").write_text(
        json.dumps({"cpi.parquet": {"fetched_at": "2026-11-13T00:00:00+00:00", "rows": 1}}),
        encoding="utf-8",
    )

    payload = inventory.build_inventory()
    by_path = {entry["path"]: entry for entry in payload["sources"]}

    assert payload["summary"]["files"] == 2
    assert payload["summary"]["bronze"] == 1
    assert payload["summary"]["external"] == 1
    assert by_path["data/pipeline/01_bronze/raw_hdb_resale.parquet"]["acquisition"]["status"] == (
        "not-recorded"
    )
    assert by_path["data/pipeline/01_bronze/external/cpi.parquet"]["acquisition"]["status"] == (
        "recorded"
    )
    assert payload["summary"]["unrecordedAcquisition"] == 1


def test_inventory_check_detects_drift(inventory, tmp_path, capsys):
    _point_inventory_at(inventory, tmp_path)
    bronze = tmp_path / "data" / "pipeline" / "01_bronze"
    target = bronze / "raw_hdb_resale.parquet"
    _write_parquet(target, pd.DataFrame({"month": ["2025-01"], "resale_price": [400000]}))

    ledger = tmp_path / "ledger.json"
    assert inventory.main(["--output", str(ledger)]) == 0
    assert inventory.main(["--output", str(ledger), "--check"]) == 0
    assert "matches the tree" in capsys.readouterr().out

    _write_parquet(target, pd.DataFrame({"month": ["2025-01", "2025-02"], "resale_price": [1, 2]}))
    assert inventory.main(["--output", str(ledger), "--check"]) == 1
    assert "row drift" in capsys.readouterr().out


def test_inventory_check_detects_derived_row_drift(inventory, tmp_path, capsys):
    """A derivation can change when the pipeline reruns, so it is checked too."""
    _point_inventory_at(inventory, tmp_path)
    gold = tmp_path / "data" / "pipeline" / "03_gold" / "rental_yield.parquet"
    _write_parquet(
        gold, pd.DataFrame({"town": ["BEDOK", "BEDOK"], "month": ["2025-01", "2025-02"]})
    )

    ledger = tmp_path / "ledger.json"
    assert inventory.main(["--output", str(ledger)]) == 0

    _write_parquet(gold, pd.DataFrame({"town": ["BEDOK"], "month": ["2025-01"]}))
    assert inventory.main(["--output", str(ledger), "--check"]) == 1
    assert "derived row drift rental_yield: 2 -> 1" in capsys.readouterr().out


def _point_rental_at(module, tmp_path: Path) -> None:
    module.REPO_ROOT = tmp_path
    module.SALES = tmp_path / "raw_hdb_resale.parquet"
    module.RENTALS = tmp_path / "raw_hdb_rental.parquet"
    module.YIELDS = tmp_path / "rental_yield.parquet"


def test_rental_join_coverage_depends_on_flat_type_normalisation(rental, tmp_path):
    _point_rental_at(rental, tmp_path)
    # Same flats, different spellings: only the normaliser makes them join.
    _write_parquet(
        rental.SALES,
        pd.DataFrame(
            {
                "month": ["2025-01", "2025-01"],
                "town": ["BEDOK", "BEDOK"],
                "flat_type": ["3 ROOM", "4 ROOM"],
                "resale_price": [400000, 500000],
            }
        ),
    )
    _write_parquet(
        rental.RENTALS,
        pd.DataFrame(
            {
                "rent_approval_date": ["2025-01", "2025-01"],
                "town": ["BEDOK", "BEDOK"],
                "flat_type": ["3-ROOM", "4-ROOM"],
                "monthly_rent": [2000, 2400],
            }
        ),
    )

    coverage = rental.join_coverage()

    assert coverage["recentMatchedShare"]["median"] == 1.0
    assert coverage["recentMatchedShareRawFlatTypes"]["median"] == 0.0


def test_rental_join_reports_months_missing_a_side(rental, tmp_path):
    _point_rental_at(rental, tmp_path)
    _write_parquet(
        rental.SALES,
        pd.DataFrame(
            {
                "month": ["2025-01", "2025-02"],
                "town": ["BEDOK", "BEDOK"],
                "flat_type": ["3 ROOM", "3 ROOM"],
                "resale_price": [400000, 410000],
            }
        ),
    )
    _write_parquet(
        rental.RENTALS,
        pd.DataFrame(
            {
                "rent_approval_date": ["2025-01"],
                "town": ["BEDOK"],
                "flat_type": ["3-ROOM"],
                "monthly_rent": [2000],
            }
        ),
    )

    coverage = rental.join_coverage()

    assert coverage["monthsWithoutRentals"] == ["2025-02"]


def test_published_yields_measure_duplication_rather_than_hiding_it(rental, tmp_path):
    _point_rental_at(rental, tmp_path)
    row = {
        "town": "BEDOK",
        "month": "2025-01",
        "median_price": 400000.0,
        "median_rent": 2000.0,
        "rental_yield_pct": 6.0,
        "sample_size": 40,
        "property_type": "HDB",
        "flat_type": "ALL",
        "rental_index": 100.0,
    }
    _write_parquet(rental.YIELDS, pd.DataFrame([row, row, {**row, "sample_size": 40}]))

    measured = rental.published_yields()

    assert measured["rows"] == 3
    assert measured["uniqueTownMonths"] == 1
    assert measured["duplicateRows"] == 3
    # The fixture's duplicated rows agree on every column.
    assert measured["duplicateRowsValueIdentical"] is True
    assert measured["duplicateColumnsDiffering"] == []
    assert measured["sampleSizeSumRaw"] == 120
    assert measured["sampleSizeSumDeduped"] == 40
    assert measured["rowsBelow20Sales"] == 0
    assert measured["rowsBelow20SalesDeduped"] == 0


def test_duplicate_detection_names_the_differing_column(rental, tmp_path):
    """A duplicated pair is not "identical" when one column disagrees."""
    _point_rental_at(rental, tmp_path)
    base = {
        "town": "BEDOK",
        "month": "2025-01",
        "median_price": 400000.0,
        "median_rent": 2000.0,
        "rental_yield_pct": 6.0,
        "sample_size": 40,
        "property_type": "HDB",
        "flat_type": "ALL",
    }
    _write_parquet(
        rental.YIELDS,
        pd.DataFrame([{**base, "rental_index": 100.0}, {**base, "rental_index": 93.5}]),
    )

    measured = rental.published_yields()

    assert measured["duplicateRowsValueIdentical"] is False
    assert measured["duplicateColumnsDiffering"] == ["rental_index"]


def test_rental_block_overlap_states_that_units_cannot_be_matched(rental, tmp_path):
    _point_rental_at(rental, tmp_path)
    _write_parquet(
        rental.SALES,
        pd.DataFrame(
            {
                "month": ["2025-01"],
                "town": ["BEDOK"],
                "block": ["101"],
                "street_name": ["BEDOK NORTH AVE 1"],
                "flat_type": ["3 ROOM"],
                "resale_price": [400000],
            }
        ),
    )
    _write_parquet(
        rental.RENTALS,
        pd.DataFrame(
            {
                "rent_approval_date": ["2025-01"],
                "town": ["BEDOK"],
                "block": ["101"],
                "street_name": ["BEDOK NORTH AVE 1"],
                "flat_type": ["3-ROOM"],
                "monthly_rent": [2000],
            }
        ),
    )

    overlap = rental.block_overlap()

    assert overlap["matchedBlocks"] == 1
    assert "no source carries a unit identifier" in overlap["unitLevelMatching"]
