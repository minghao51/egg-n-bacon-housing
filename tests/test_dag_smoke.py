"""WS20 — hermetic full-DAG smoke test (Batch 5).

Graph-level regression net: runs ``build_pipeline()`` -> ``run_pipeline()``
end-to-end over the REAL Hamilton DAG on a tiny synthetic data tree, with all
external transport mocked at the ``requests.Session`` level (WS15 adapters use
module/thread-local sessions, so patching ``Session.request`` covers every
adapter) and the ``InMemoryGeocoder`` injected for geocoding paths.

The rental-yield join defect (Batch 1 WS2) was invisible to node-level tests
because fixtures exercised node shapes production never produces. This test
pins the wiring contracts instead:

- every published output in ``utils.output_registry.PUBLISHED_LAYERS`` is
  materialized by its companion node into the right layer directory;
- ``rental_yield_pct`` is non-null on ``transactions_enriched`` rows — the
  original critical bug, pinned at graph level;
- ``unified_dataset`` is a row-count pass-through of ``transactions_enriched``;
- WS17 column contracts: ``dist_to_nearest_mrt`` is emitted; the removed
  ``nearest_school`` / ``nearest_mrt_distance`` columns are gone;
- WS16 per-type geocoding coverage thresholds flow from ``Settings``;
- WS13 hotspot volume floor flows from ``Settings``;
- no quarantine files on the happy path (quarantine = fixture bug);
- ``bronze_manifest.json`` exists with fetch entries;
- ``main.py --stage all`` drives the SAME graph through the real CLI entry
  point (main -> build_pipeline -> run_pipeline -> Hamilton Driver) and all
  12 published outputs materialize. This closes the regression gap that let a
  main.py stage-collapse bug (materialization narrowed to the 6 terminal
  frames) ship through a green suite that only called ``run_pipeline()`
  directly; argument-level pinning with a mocked ``run_pipeline`` lives in
  ``TestMainCLIStagePassthrough`` (tests/test_pipeline_integration.py).

Hermetic: no network (any unexpected external URL fails loudly), no repo
``data/`` dependency, no external environment-wrapper requirement — every behavior-relevant
setting is passed explicitly. Note: aliased credential fields must be
overridden by alias (``URA_API_ACCESS_KEY``), otherwise a repo-root ``.env``
silently wins over by-name kwargs.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import requests

from egg_n_bacon_housing.components.ingestion.datagov import (
    DWELLING_UNITS_RESOURCE_ID,
    GREEN_MARK_BUILDINGS_RESOURCE_ID,
    HDB_PROPERTY_INFO_RESOURCE_ID,
    HDB_RESALE_RESOURCE_ID,
    HDB_RESIDENT_POPULATION_RESOURCE_ID,
    INCOME_BY_PLANNING_AREA_RESOURCE_ID,
    MEDIAN_ANNUAL_VALUE_RESOURCE_ID,
    MP25_MALLS_DATASET_ID,
)
from egg_n_bacon_housing.components.ingestion.geojson import (
    MRT_STATION_EXITS_DATASET_ID,
    TRAIN_STATION_CODES_DATASET_ID,
)
from egg_n_bacon_housing.components.ingestion.macro import (
    BANK_RATES_RESOURCE_ID,
    CPI_RESOURCE_ID,
    GDP_RESOURCE_ID,
    HDB_RPI_RESOURCE_ID,
    UNEMPLOYMENT_RESOURCE_ID,
    URA_PPI_RESOURCE_ID,
    WAGE_GROWTH_RESOURCE_ID,
)
from egg_n_bacon_housing.config import (
    AFFORDABILITY_THRESHOLD_DEFAULTS,
    GeocodingConfig,
    LayerDirs,
    MetricsConfig,
    PipelineConfig,
    Settings,
)
from egg_n_bacon_housing.pipeline import STAGE_VARS, run_pipeline
from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder
from egg_n_bacon_housing.utils.output_registry import PUBLISHED_LAYERS, TERMINAL_OUTPUTS

pytestmark = pytest.mark.integration

# --- Resource ids that only exist as @parameterize values (not importable) ---
_RENTAL_INDEX_RESOURCE_ID = "d_8e4c50283fb7052a391dfb746a05c853"
_HDB_RENTAL_RESOURCE_ID = "d_c9f57187485a850908655db0e8cfe651"
_SCHOOL_DIRECTORY_RESOURCE_ID = "d_688b934f82c1059ed0a6993d2a829089"

# --- Shared synthetic geography (all points inside the planning polygon) -----

_HDB_COORD = (1.3523, 103.8550)
_CONDO_CSV_COORD = (1.3060, 103.8320)
_CONDO_API_COORD = (1.3620, 103.8890)
_GREEN_MARK_COORD = (1.3340, 103.8470)

GEOCODE_LOOKUP: dict[str, tuple[float, float]] = {
    "123a lorong 1 toa payoh": _HDB_COORD,
    "orchard boulevard": _CONDO_CSV_COORD,
    "upper serangoon view": _CONDO_API_COORD,
    "318944": _GREEN_MARK_COORD,
}

_PLANNING_POLYGON_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"pln_area_n": "TOA PAYOH"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [103.80, 1.28],
                        [103.90, 1.28],
                        [103.90, 1.38],
                        [103.80, 1.38],
                        [103.80, 1.28],
                    ]
                ],
            },
        }
    ],
}

_MP25_MALLS_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"CLASSIFCTN": "MALL"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [103.852, 1.349],
                        [103.856, 1.349],
                        [103.856, 1.353],
                        [103.852, 1.353],
                        [103.852, 1.349],
                    ]
                ],
            },
        }
    ],
}

_MRT_EXITS_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"STATION_NA": "TOA PAYOH MRT STATION"},
            "geometry": {"type": "Point", "coordinates": [103.8443, 1.3329]},
        }
    ],
}


def _point_feature(properties: dict[str, str], lon: float, lat: float) -> dict:
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


# --- Canned data.gov.sg datastore payloads (minimal but schema-faithful) -----


def _hdb_resale_api_rows() -> list[dict]:
    """HDB resale via API (Jan 2017+ contract, incl. remaining_lease)."""
    rows = []
    for month, price in [
        ("2024-01", "500000"),
        ("2024-02", "510000"),
        ("2024-03", "520000"),
        ("2024-04", "530000"),
    ]:
        rows.append(
            {
                "month": month,
                "town": "TOA PAYOH",
                "flat_type": "4 ROOM",
                "block": "123A",
                "street_name": "LORONG 1 TOA PAYOH",
                "storey_range": "01 TO 03",
                "floor_area_sqm": "92",
                "flat_model": "New Generation",
                "lease_commence_date": "1978",
                "resale_price": price,
                "remaining_lease": "55 years 05 months",
            }
        )
    return rows


def _hdb_rental_rows() -> list[dict]:
    return [
        {
            "month": month,
            "town": "TOA PAYOH",
            "flat_type": "4 ROOM",
            "monthly_rent": "3000",
            "rent_approval_date": month,
        }
        for month in ("2024-01", "2024-02", "2024-03", "2024-04")
    ]


def _rental_index_rows() -> list[dict]:
    return [
        {"quarter": "2024-Q1", "locality": "Whole Island", "index": "155.0"},
        {"quarter": "2024-Q2", "locality": "Whole Island", "index": "157.0"},
    ]


def _school_directory_rows() -> list[dict]:
    """Latitude/longitude present so the injected geocoder is not needed here."""
    return [
        {
            "school_name": "Toa Payoh Primary",
            "postal_code": "319541",
            "mainlevel_code": "PRIMARY",
            "latitude": "1.3525",
            "longitude": "103.8542",
        },
        {
            "school_name": "Toa Payoh Secondary",
            "postal_code": "319542",
            "mainlevel_code": "SECONDARY (S1-S5)",
            "latitude": "1.3505",
            "longitude": "103.8562",
        },
        {
            "school_name": "Toa Payoh JC",
            "postal_code": "319543",
            "mainlevel_code": "JUNIOR COLLEGE",
            "latitude": "1.3535",
            "longitude": "103.8522",
        },
    ]


def _macro_rows() -> dict[str, list[dict]]:
    """One series row per macro pivot, keyed by the datagov.py resource ids."""
    return {
        CPI_RESOURCE_ID: [{"DataSeries": "All Items", "2024Jan": "100.0", "2024Feb": "100.5"}],
        UNEMPLOYMENT_RESOURCE_ID: [{"DataSeries": "Total Unemployment Rate", "20241Q": "2.0"}],
        GDP_RESOURCE_ID: [{"DataSeries": "GDP In Chained (2015) Dollars", "20241Q": "100.0"}],
        BANK_RATES_RESOURCE_ID: [
            {
                "DataSeries": ("Compounded Singapore Overnight Rate Average (SORA) - 3 Month"),
                "2024Jan": "3.5",
            }
        ],
        HDB_RPI_RESOURCE_ID: [{"quarter": "2024-Q1", "index": "150.0"}],
        URA_PPI_RESOURCE_ID: [
            {"property_type": "All Residential", "quarter": "2024-Q1", "index": "140.0"}
        ],
        WAGE_GROWTH_RESOURCE_ID: [{"DataSeries": "Overall Economy", "2024": "4.0"}],
    }


def _datastore_rows() -> dict[str, list[dict]]:
    rows = {
        HDB_RESALE_RESOURCE_ID: _hdb_resale_api_rows(),
        _RENTAL_INDEX_RESOURCE_ID: _rental_index_rows(),
        _HDB_RENTAL_RESOURCE_ID: _hdb_rental_rows(),
        _SCHOOL_DIRECTORY_RESOURCE_ID: _school_directory_rows(),
        HDB_PROPERTY_INFO_RESOURCE_ID: [
            {
                "blk_no": "123A",
                "street": "LORONG 1 TOA PAYOH",
                "max_floor_lvl": "12",
                "year_completed": "2015",
                "total_dwelling_units": "100",
                "residential": "Y",
                "commercial": "N",
                "market_hawker": "N",
                "multistorey_carpark": "N",
            }
        ],
        INCOME_BY_PLANNING_AREA_RESOURCE_ID: [
            {"Thousands": "TOA PAYOH", "Below_1_000": "100", "1_000_1_499": "300"}
        ],
        GREEN_MARK_BUILDINGS_RESOURCE_ID: [
            {"Postal_Code": "318944", "Project_Name": "Toa Payoh Green"}
        ],
        DWELLING_UNITS_RESOURCE_ID: [
            {
                "town_or_estate": "TOA PAYOH",
                "no_of_dwelling_units": "1000",
                "financial_year": "2024",
                "sold_or_rental": "Sold Units",
            }
        ],
        MEDIAN_ANNUAL_VALUE_RESOURCE_ID: [
            {
                "type_of_hdb": "4 Room",
                "median_annual_value": "9600",
                "property_tax_collection": "2400",
                "financial_year": "2024",
            }
        ],
        HDB_RESIDENT_POPULATION_RESOURCE_ID: [
            {"town_estate": "TOA PAYOH", "number": "120000", "shs_year": "2024"}
        ],
        # LTA station-codes table consumed by raw_mrt_stations (line assignment
        # + bronze/external/mrt_stations.json refresh).
        TRAIN_STATION_CODES_DATASET_ID: [
            {
                "stn_code": "NS1",
                "mrt_station_english": "TOA PAYOH MRT STATION",
                "mrt_line_english": "North South Line",
            }
        ],
    }
    rows.update(_macro_rows())
    return rows


_GEOJSON_PAYLOADS: dict[str, dict] = {
    MRT_STATION_EXITS_DATASET_ID: _MRT_EXITS_GEOJSON,
    MP25_MALLS_DATASET_ID: _MP25_MALLS_GEOJSON,
}

# --- Canned URA API payloads (token + one batch of property rows) ------------

_URA_API_ROWS: list[dict] = [
    {
        "project": "Skyline Test",
        "street": "UPPER SERANGOON VIEW",
        "marketSegment": "OCR",
        "x": "103.889",
        "y": "1.362",
        "transaction": [
            {
                "contractDate": "0124",
                "typeOfArea": "Strata",
                "area": "900",
                "price": "1200000",
                "floorRange": "03-05",
                "typeOfSale": "3",
                "propertyType": "Condominium",
                "noOfUnits": "1",
                "tenure": "Freehold",
                "district": "19",
            }
        ],
    }
]

# --- Fake transport -----------------------------------------------------------


class _FakeResponse:
    """Minimal requests.Response stand-in for the canned payloads."""

    def __init__(self, payload: Any, status: int = 200):
        self._payload = payload
        self.status_code = status
        self.headers: dict[str, str] = {}
        self.text = json.dumps(payload)

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)  # type: ignore[arg-type]


def _datastore_response(records: list[dict]) -> dict:
    """datastore_search payload with no pagination continuation."""
    return {"result": {"records": records, "total": len(records), "_links": {}}}


def _make_transport() -> Callable[..., _FakeResponse]:
    """Build a Session.request replacement serving canned DGS/URA/LTA data.

    Known hosts get schema-faithful minimal payloads; ANY other URL raises —
    an unexpected external call must fail the smoke test loudly (hermeticity).
    """

    def fake_request(self: requests.Session, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        url = str(url)
        if "eservice.ura.gov.sg" in url:
            if "insertNewToken" in url:
                return _FakeResponse({"Status": "Success", "Result": "ws20-fake-token"})
            batch = str((kwargs.get("params") or {}).get("batch", "1"))
            ura_rows = _URA_API_ROWS if batch == "1" else []
            return _FakeResponse({"Status": "Success", "Result": ura_rows})
        if "initiate-download" in url:
            return _FakeResponse({"code": 0, "data": {"message": "initiated"}})
        if "poll-download" in url:
            dataset_id = url.split("/datasets/")[1].split("/")[0]
            assert dataset_id in _GEOJSON_PAYLOADS, f"unexpected geojson dataset: {dataset_id}"
            return _FakeResponse(
                {"code": 0, "data": {"url": f"https://ws20-mock-cdn.test/{dataset_id}"}}
            )
        if "ws20-mock-cdn.test" in url:
            return _FakeResponse(_GEOJSON_PAYLOADS[url.rsplit("/", 1)[1]])
        if "datastore_search" in url:
            resource_id = url.split("resource_id=")[1].split("&")[0]
            rows = _datastore_rows()
            assert resource_id in rows, f"unexpected datastore resource: {resource_id}"
            return _FakeResponse(_datastore_response(rows[resource_id]))
        if "onemap.gov.sg" in url:
            # Injected InMemoryGeocoder owns all geocoding paths; this only
            # proves no accidental OneMap transport escape.
            return _FakeResponse({"results": []})
        raise AssertionError(
            f"WS20 smoke test saw an unexpected external HTTP call: {method} {url}"
        )

    return fake_request


# --- Fixture writers (inline payloads; no new data files in the repo) ---------

_HDB_RESALE_CSV = """month,town,flat_type,block,street_name,storey_range,floor_area_sqm,flat_model,lease_commence_date,resale_price
2015-06,TOA PAYOH,4 ROOM,123A,LORONG 1 TOA PAYOH,01 TO 03,92,New Generation,1978,420000
"""

_URA_CONDO_CSV = (
    "Project Name,Street Name,Transacted Price ($),Area (SQFT),Area (SQM),"
    "Unit Price ($ PSF),Unit Price ($ PSM),Sale Date,Type of Sale,Property Type,"
    "Number of Units,Tenure,Postal District,Market Segment,Floor Level,"
    "Type of Area,Nett Price($)\n"
    'Orchid Residences,ORCHARD BOULEVARD,"1,500,000",1076,100,1394,15000,Jan-24,'
    "Resale,Condominium,1,Freehold,10,CORE CENTRAL REGION,01 TO 05,Strata,\n"
    'Orchid Residences,ORCHARD BOULEVARD,"1,520,000",1076,100,1412,15200,Feb-24,'
    "Resale,Condominium,1,Freehold,10,CORE CENTRAL REGION,01 TO 05,Strata,\n"
)

_MRT_LINES_JSON = {
    "NSL": {
        "name": "North South Line",
        "color": "#DC241F",
        "tier": 1,
        "description": "smoke fixture",
    }
}

_MRT_STATIONS_JSON = {"TOA PAYOH": ["NSL"]}

_AMENITY_SEEDS: tuple[tuple[str, dict], ...] = (
    ("HawkerCentresGEOJSON.geojson", {"NAME": "TOA PAYOH MARKET"}),
    ("SupermarketsGEOJSON.geojson", {"Name": "NTUC TOA PAYOH"}),
    ("NParksParksandNatureReserves.geojson", {"NAME": "TOA PAYOH PARK"}),
    ("ChildCareServices.geojson", {"NAME": "TOA PAYOH CARE"}),
    ("PreSchoolsLocation.geojson", {"Name": "TOA PAYOH PCF"}),
    ("BusStops.geojson", {"BUS_STOP_NUM": "52011"}),
    ("CHASClinics.geojson", {"Name": "TOA PAYOH CLINIC"}),
    ("SportSGFacilities.geojson", {"Name": "TOA PAYOH STADIUM"}),
    ("CommunityClubs.geojson", {"Name": "TOA PAYOH CC"}),
)

_AMENITY_COORDS = (
    (103.8530, 1.3530),
    (103.8560, 1.3510),
    (103.8500, 1.3500),
    (103.8540, 1.3520),
    (103.8555, 1.3535),
    (103.8545, 1.3525),
    (103.8525, 1.3515),
    (103.8515, 1.3540),
    (103.8535, 1.3545),
)


def _write_manual_fixtures(data_root: Path) -> None:
    """Manual CSVs + planning-area polygon under ``data_root/manual`` (WS15 layout)."""
    resale_dir = data_root / "manual" / "csv" / "ResaleFlatPrices"
    resale_dir.mkdir(parents=True)
    (resale_dir / "resale-flat-prices-1990.csv").write_text(_HDB_RESALE_CSV, encoding="utf-8")

    ura_dir = data_root / "manual" / "csv" / "ura"
    ura_dir.mkdir(parents=True)
    (ura_dir / "ResidentialTransaction-2024.csv").write_text(_URA_CONDO_CSV, encoding="utf-8")

    geojsons_dir = data_root / "manual" / "geojsons"
    geojsons_dir.mkdir(parents=True)
    (geojsons_dir / "onemap_planning_area_polygon.geojson").write_text(
        json.dumps(_PLANNING_POLYGON_GEOJSON), encoding="utf-8"
    )


def _write_bronze_external_seeds(data_root: Path) -> None:
    """Pre-seed bronze/external so seed_bronze_external finds everything."""
    external = data_root / "pipeline" / "01_bronze" / "external"
    external.mkdir(parents=True)

    for (filename, properties), (lon, lat) in zip(_AMENITY_SEEDS, _AMENITY_COORDS, strict=True):
        collection = {
            "type": "FeatureCollection",
            "features": [_point_feature(properties, lon, lat)],
        }
        (external / filename).write_text(json.dumps(collection), encoding="utf-8")

    # Legacy static MRT seeds (fallback path; the mocked live LTA path supersedes).
    (external / "MRTStations.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [_point_feature({"NAME": "TOA PAYOH"}, 103.8443, 1.3329)],
            }
        ),
        encoding="utf-8",
    )
    (external / "mrt_lines.json").write_text(json.dumps(_MRT_LINES_JSON), encoding="utf-8")
    (external / "mrt_stations.json").write_text(json.dumps(_MRT_STATIONS_JSON), encoding="utf-8")

    # SORA loads straight from bronze/external (no fetch path).
    pd.DataFrame([{"date": "2024-01-15", "sora_rate": 3.5}]).to_parquet(
        external / "sora_rates.parquet", index=False
    )


def _build_settings(data_root: Path) -> Settings:
    """Explicit settings: every behavior-relevant field overrides ambient env."""
    return Settings(
        data_path=str(data_root),
        tracking_enabled=False,
        pipeline=PipelineConfig(
            use_caching=True,
            large_table_validation_policy="full",
            max_transaction_age_days=None,
        ),
        geocoding=GeocodingConfig(
            coordinate_coverage_policy="fail",
            min_coordinate_coverage_hdb=0.7,
            min_coordinate_coverage_condo=0.1,
        ),
        metrics=MetricsConfig(
            min_transactions_for_hotspot=1,
            affordability_thresholds=dict(AFFORDABILITY_THRESHOLD_DEFAULTS),
        ),
        layer_dirs=LayerDirs(
            bronze="data/pipeline/01_bronze",
            silver="data/pipeline/02_silver",
            gold="data/pipeline/03_gold",
            platinum="data/pipeline/04_platinum",
        ),
        # Alias form is required: an aliased field's by-name init kwarg loses
        # to a repo-root .env entry, and this key must never come from ambient config.
        URA_API_ACCESS_KEY="ws20-fake-access-key",  # noqa: N803 - pydantic field alias
    )


@pytest.fixture
def hermetic_dag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Settings, Path]:
    """Tiny tmp data tree + fully mocked transport, ready for run_pipeline."""
    data_root = tmp_path / "data"
    _write_manual_fixtures(data_root)
    _write_bronze_external_seeds(data_root)
    monkeypatch.setattr(requests.Session, "request", _make_transport())
    return _build_settings(data_root), data_root


# --- Assertions ---------------------------------------------------------------


def _assert_no_quarantine(pipeline_root: Path) -> None:
    quarantined = sorted(p for p in pipeline_root.rglob("*") if "_quarantine" in p.parts)
    assert not quarantined, f"happy-path fixtures must not quarantine rows: {quarantined}"


def _assert_published_files(settings: Settings, data_root: Path) -> None:
    for name, layer in PUBLISHED_LAYERS.items():
        path = settings.layer_dir(layer, str(data_root)) / f"{name}.parquet"
        assert path.exists(), f"missing published output {name!r} at {path}"


# --- The smoke test -----------------------------------------------------------


# PRODUCTION BLOCKER (WS20) — FIXED: sf-hamilton 1.89.0 rejected the
# protocol-typed runtime inputs run_pipeline() injects (htypes.check_input_type
# skips its isinstance branch for Protocol classes and the `Protocol | None`
# union check failed), so ANY end-to-end run -- main.py included -- failed with
# "Type requirement mismatch" before the first node executed. Fixed by the
# _ProtocolUnionInputValidator lifecycle adapter in pipeline.py (protocol
# isinstance semantics + delegation to the default checker) with the service
# Protocols in utils.runtime now @runtime_checkable; this test runs unmarked.
def test_full_dag_end_to_end(hermetic_dag: tuple[Settings, Path]) -> None:
    """build_pipeline -> run_pipeline over the full graph on tiny hermetic data."""
    settings, data_root = hermetic_dag
    geocoder = InMemoryGeocoder(GEOCODE_LOOKUP)
    final_vars = sorted(PUBLISHED_LAYERS)

    results = run_pipeline(
        settings,
        data_path=str(data_root),
        final_vars=final_vars,
        geocoder=geocoder,
    )

    pipeline_root = data_root / "pipeline"

    # 1. Every requested final var computed, incl. the full "all" stage set.
    assert set(results) == set(final_vars)
    assert set(STAGE_VARS["all"]).issubset(results)

    # 2. Every published output materialized in its layer.
    _assert_published_files(settings, data_root)

    # 3. Rental-yield join pinned at graph level (original WS2 defect).
    enriched = results["transactions_enriched"]
    assert not results["rental_yield"].empty
    assert enriched["rental_yield_pct"].notna().any()

    # 4. Pass-through contract: platinum == gold row grain, nothing quarantined.
    unified = results["unified_dataset"]
    assert len(unified) == len(enriched) > 0

    # 5. WS17 column contracts on the published gold frame.
    assert "nearest_school" not in enriched.columns
    assert "nearest_mrt_distance" not in enriched.columns
    assert enriched["dist_to_nearest_mrt"].notna().any()

    # 6. Planning-area derivation reached the published metrics.
    assert enriched["planning_area"].notna().any()
    assert not results["pa_monthly_metrics"].empty
    assert not results["appreciation_hotspots"].empty  # WS13 floor = 1 in fixtures

    # 7. Happy path quarantines nothing (fixture bug tripwire).
    _assert_no_quarantine(pipeline_root)

    # 8. Bronze observability + cache adapter exercised.
    manifest = json.loads(
        (pipeline_root / "01_bronze" / "bronze_manifest.json").read_text(encoding="utf-8")
    )
    assert len(manifest) >= 1
    assert (pipeline_root / "01_bronze" / "raw_hdb_resale.parquet").exists()
    assert (pipeline_root / "01_bronze" / "raw_condo_transactions.parquet").exists()


# --- CLI-level smoke test (main.py entry point) --------------------------------


def test_main_cli_stage_all_end_to_end(
    hermetic_dag: tuple[Settings, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """``main.main()`` with ``--stage all`` executes the real entrypoint path:
    argument parsing -> build_pipeline -> run_pipeline -> Hamilton Driver ->
    companion materializers, over the hermetic tree.

    Unlike ``TestMainCLIStagePassthrough`` (mocked ``run_pipeline``, argument
    contract only), this test must catch behavioral main.py regressions: the
    stage-collapse bug passed argument checks while materializing 6/12
    outputs. Hence the assertions here are on persisted artifacts (all 12
    published parquets) and the returned terminal frames, not just call args.
    """
    import sys

    from hamilton import driver as hamilton_driver

    settings, data_root = hermetic_dag

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parent.parent))
    import main as main_module

    # main() resolves every path through its module-global settings singleton;
    # point it at the hermetic tree (the fixture already faked HTTP transport).
    monkeypatch.setattr(main_module, "settings", settings)

    # run_pipeline constructs the production OneMap geocoder lazily; swap the
    # factory so no OneMap client or credential flow is ever built.
    from egg_n_bacon_housing import pipeline as pipeline_module

    monkeypatch.setattr(
        pipeline_module,
        "build_default_geocoder",
        lambda settings, cache_manager: InMemoryGeocoder(GEOCODE_LOOKUP),
    )

    # Transparent spy: forward to the REAL run_pipeline and record the CLI
    # contract plus the returned terminal frames. No behavior is mocked.
    real_run_pipeline = main_module.run_pipeline
    captured: dict[str, object] = {}
    returned: dict[str, pd.DataFrame] = {}

    def spy_run_pipeline(run_settings: Settings, **kwargs: object) -> dict:
        captured["final_vars"] = kwargs.get("final_vars")
        captured["stage"] = kwargs.get("stage")
        captured["dr"] = kwargs.get("dr")
        results = real_run_pipeline(run_settings, **kwargs)  # type: ignore[arg-type]
        returned.update(results)
        return results

    monkeypatch.setattr(main_module, "run_pipeline", spy_run_pipeline)
    monkeypatch.setattr(sys, "argv", ["main.py", "--stage", "all"])

    main_module.main()  # must exit without exception

    # Stage passed through uncollapsed, with the REAL driver attached — the
    # wiring whose absence narrowed materialization to the terminal frames.
    assert captured["final_vars"] is None
    assert captured["stage"] == "all"
    assert isinstance(captured["dr"], hamilton_driver.Driver)

    # The six terminal frames came back through the real driver.
    assert set(returned) == set(TERMINAL_OUTPUTS)
    assert all(isinstance(frame, pd.DataFrame) for frame in returned.values())

    # The regression tripwire: all 12 published outputs materialized, not
    # just the 6 terminal frames that stage-collapse would persist.
    _assert_published_files(settings, data_root)
