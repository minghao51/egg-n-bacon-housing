"""Test ingestion component."""

import fnmatch
import json
import logging
import re
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
import requests

pytestmark = pytest.mark.unit


def _disable_live_mrt_fetch(ingestion, monkeypatch):
    """Make the live LTA MRT fetch fail fast so tests exercise legacy paths."""
    from egg_n_bacon_housing.adapters.exceptions import DatasetFetchError

    def _boom(*_a, **_kw):
        raise DatasetFetchError("live fetch disabled in test")

    monkeypatch.setattr(ingestion.geojson.datagovsg, "fetch_datagovsg_geojson", _boom)


def _get_ingestion_module():
    """Get the ingestion module."""
    from egg_n_bacon_housing.components import ingestion

    return ingestion


def _get_macro_module():
    from egg_n_bacon_housing.components.ingestion import macro

    return macro


def _get_geojson_module():
    from egg_n_bacon_housing.components.ingestion import geojson

    return geojson


def _get_ura_csv_module():
    from egg_n_bacon_housing.components.ingestion import ura_csv

    return ura_csv


class TestBronzeLayer:
    """Test bronze layer data ingestion functions."""

    def test_raw_hdb_resale_transactions_prefers_bronze_cache(self, tmp_path, monkeypatch):
        """Test that HDB resale loads from the configured bronze directory."""
        ingestion = _get_ingestion_module()
        expected = pd.DataFrame([{"resale_price": 500000.0, "month": "2024-01"}])
        (tmp_path / "raw_hdb_resale.parquet").parent.mkdir(parents=True, exist_ok=True)
        expected.to_parquet(tmp_path / "raw_hdb_resale.parquet", index=False)

        from egg_n_bacon_housing.adapters import datagovsg

        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *args, **kwargs: pytest.fail("network fetch should not run when cache exists"),
        )

        result = ingestion.raw_dataset(
            bronze_dir=tmp_path,
            resource_id="d_5785799d63a9da091f4e0b456291eeb8",
            cache_filenames=("raw_hdb_resale.parquet",),
            display_name="HDB resale",
            error_name="hdb_resale",
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_raw_hdb_resale_transactions_hard_fails_on_empty_fetch(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters import datagovsg

        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *args, **kwargs: pd.DataFrame(),
        )
        with pytest.raises(RuntimeError, match="Core dataset fetch failed: hdb_resale"):
            ingestion.raw_dataset(
                bronze_dir=tmp_path,
                resource_id="d_5785799d63a9da091f4e0b456291eeb8",
                cache_filenames=("raw_hdb_resale.parquet",),
                display_name="HDB resale",
                error_name="hdb_resale",
            )

    def test_raw_rental_index_reads_legacy_bronze_filename(self, tmp_path, monkeypatch):
        """Test that rental index reads the tracked bronze parquet filename."""
        ingestion = _get_ingestion_module()
        expected = pd.DataFrame([{"quarter": "2024-Q1", "index": "100.0"}])
        expected.to_parquet(tmp_path / "raw_datagov_rental_index.parquet", index=False)

        from egg_n_bacon_housing.adapters import datagovsg

        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *args, **kwargs: pytest.fail("network fetch should not run when cache exists"),
        )

        result = ingestion.raw_dataset(
            bronze_dir=tmp_path,
            resource_id="d_e03d53203e43c32df38b5123c9e1d2a4",
            cache_filenames=("raw_rental_index.parquet", "raw_datagov_rental_index.parquet"),
            display_name="rental index",
            error_name="rental_index",
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_raw_hdb_rental_reads_tracked_bronze_filename(self, tmp_path, monkeypatch):
        """Test that HDB rental reads the tracked bronze parquet filename."""
        ingestion = _get_ingestion_module()
        expected = pd.DataFrame([{"town": "TOA PAYOH", "monthly_rent": "3500"}])
        expected.to_parquet(tmp_path / "raw_datagov_hdb_rental.parquet", index=False)

        from egg_n_bacon_housing.adapters import datagovsg

        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *args, **kwargs: pytest.fail("network fetch should not run when cache exists"),
        )

        result = ingestion.raw_dataset(
            bronze_dir=tmp_path,
            resource_id="d_8b84f0dfe7acb6d6585a7d7e6e406b31",
            cache_filenames=("raw_hdb_rental.parquet", "raw_datagov_hdb_rental.parquet"),
            display_name="HDB rental",
            error_name="hdb_rental",
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_raw_mrt_stations_reads_from_bronze_external(self, tmp_path, monkeypatch):
        """Test that MRT station reference data is read from bronze/external."""
        ingestion = _get_ingestion_module()
        _disable_live_mrt_fetch(ingestion, monkeypatch)
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)
        mrt_payload = [{"name": "TOA PAYOH", "lat": 1.33, "lon": 103.85}]
        (external_dir / "mrt_stations.json").write_text(json.dumps(mrt_payload))

        result = ingestion.raw_mrt_stations(bronze_dir=tmp_path)

        assert result.to_dict(orient="records") == mrt_payload

    def test_raw_mrt_stations_accepts_legacy_mapping_payload(self, tmp_path, monkeypatch):
        """Legacy station->line mapping payloads remain readable."""
        ingestion = _get_ingestion_module()
        _disable_live_mrt_fetch(ingestion, monkeypatch)
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)
        mrt_payload = {"TOA PAYOH": ["NSL"], "BISHAN": "CCL"}
        (external_dir / "mrt_stations.json").write_text(json.dumps(mrt_payload))

        result = ingestion.raw_mrt_stations(bronze_dir=tmp_path)

        assert result.to_dict(orient="records") == [
            {"name": "TOA PAYOH", "line": "NSL"},
            {"name": "BISHAN", "line": "CCL"},
        ]

    def test_raw_macro_data_returns_expected_keys(self, tmp_path, monkeypatch):
        """Test that macro loaders resolve files from bronze/external."""
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"rate": 1.2}]).to_parquet(external_dir / "sora_rates.parquet", index=False)
        pd.DataFrame([{"value": 100}]).to_parquet(external_dir / "cpi.parquet", index=False)

        from egg_n_bacon_housing.adapters import datagovsg

        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *a, **kw: pd.DataFrame(),
        )

        result = ingestion.raw_macro_data(bronze_dir=tmp_path)

        assert isinstance(result, dict)
        assert {"sora", "cpi", "gdp", "unemployment"}.issubset(set(result))
        assert not result["sora"].empty
        assert not result["cpi"].empty
        assert result["gdp"].empty

    def test_raw_macro_data_gdp_falls_back_to_first_series(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"rate": 1.2}]).to_parquet(external_dir / "sora_rates.parquet", index=False)

        from egg_n_bacon_housing.adapters import datagovsg

        def fake_fetch(_base_url, resource_id, use_cache=False):
            if resource_id == ingestion.macro.GDP_RESOURCE_ID:
                return pd.DataFrame(
                    [
                        {
                            "DataSeries": "Fallback GDP Label",
                            "20261Q": "100.0",
                            "20262Q": "110.0",
                        }
                    ]
                )
            return pd.DataFrame()

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", fake_fetch)

        result = ingestion.raw_macro_data(bronze_dir=tmp_path)

        assert list(result["gdp"]["gdp"]) == [100.0, 110.0]
        assert list(result["gdp"]["quarter"].dt.strftime("%Y-%m-%d")) == [
            "2026-03-31",
            "2026-06-30",
        ]

    def test_raw_macro_data_rebuilds_empty_wage_growth_cache(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"rate": 1.2}]).to_parquet(external_dir / "sora_rates.parquet", index=False)
        pd.DataFrame().to_parquet(external_dir / "wage_growth.parquet", index=False)

        from egg_n_bacon_housing.adapters import datagovsg

        def fake_fetch(_base_url, resource_id, use_cache=False):
            if resource_id == ingestion.macro.WAGE_GROWTH_RESOURCE_ID:
                return pd.DataFrame(
                    [{"metric": "ignored", "DataSeries": "Overall Economy", "2025": "4.5"}]
                )
            return pd.DataFrame()

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", fake_fetch)

        result = ingestion.raw_macro_data(bronze_dir=tmp_path)

        assert len(result["wage_growth"]) == 4
        assert result["wage_growth"]["wage_growth"].tolist() == [4.5, 4.5, 4.5, 4.5]
        assert (external_dir / "wage_growth.parquet").exists()

    def test_raw_macro_data_ignores_empty_cache_and_refetches(self, tmp_path, monkeypatch):
        """An empty bronze cache must be treated as a miss, not valid data."""
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"rate": 1.2}]).to_parquet(external_dir / "sora_rates.parquet", index=False)
        pd.DataFrame().to_parquet(external_dir / "cpi.parquet", index=False)

        from egg_n_bacon_housing.adapters import datagovsg

        def fake_fetch(_base_url, resource_id, use_cache=False):
            if resource_id == ingestion.macro.CPI_RESOURCE_ID:
                return pd.DataFrame(
                    [
                        {"DataSeries": "All Items", "2026Jan": "101.0", "2026Feb": "102.0"},
                    ]
                )
            return pd.DataFrame()

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", fake_fetch)

        result = ingestion.raw_macro_data(bronze_dir=tmp_path)

        assert len(result["cpi"]) == 2
        # The stale empty cache is replaced by the fetched data.
        repopulated = pd.read_parquet(external_dir / "cpi.parquet")
        assert len(repopulated) == 2

    def test_raw_macro_data_does_not_cache_empty_parse(self, tmp_path, monkeypatch):
        """A parse that yields no rows must not write an empty bronze cache."""
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"rate": 1.2}]).to_parquet(external_dir / "sora_rates.parquet", index=False)

        from egg_n_bacon_housing.adapters import datagovsg

        def fake_fetch(_base_url, resource_id, use_cache=False):
            if resource_id == ingestion.macro.CPI_RESOURCE_ID:
                # Pivot whose label matches no value filter -> empty melt.
                return pd.DataFrame(
                    [
                        {"DataSeries": "Something Else", "2026Jan": "101.0"},
                    ]
                )
            return pd.DataFrame()

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", fake_fetch)

        result = ingestion.raw_macro_data(bronze_dir=tmp_path)

        assert result["cpi"].empty
        assert not (external_dir / "cpi.parquet").exists()

    def test_raw_macro_data_degrades_on_network_error_and_logs_summary(
        self, tmp_path, monkeypatch, caplog
    ):
        """Network failures degrade each indicator to empty and emit ONE summary.

        Previously each failure emitted a scattered warning that was easy to
        miss (the "silent NaN" problem). The narrowed handler now records each
        failure and logs a single consolidated summary at the end.
        """
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)

        from egg_n_bacon_housing.adapters import datagovsg

        def raise_network(*a, **kw):
            raise requests.ConnectionError("boom")

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", raise_network)

        with caplog.at_level(logging.WARNING, logger=ingestion.macro.logger.name):
            result = ingestion.raw_macro_data(bronze_dir=tmp_path)

        assert isinstance(result, dict)
        for key in (
            "cpi",
            "unemployment",
            "gdp",
            "bank_rates",
            "hdb_rpi",
            "ura_ppi",
            "supply_pipeline",
            "wage_growth",
        ):
            assert result[key].empty, f"{key} should degrade to empty on network error"

        summary_records = [r for r in caplog.records if "Macro ingestion" in r.getMessage()]
        assert len(summary_records) == 1, "exactly one consolidated summary should be logged"
        msg = summary_records[0].getMessage()
        assert "8 indicator" in msg
        assert "cpi:" in msg and "wage_growth:" in msg
        assert "ConnectionError" in msg

    def test_raw_macro_data_propagates_unexpected_error(self, tmp_path, monkeypatch):
        """Programming bugs (RuntimeError etc.) must NOT be swallowed -- they
        indicate a real fault, not transient data-fetch trouble, and must
        surface immediately instead of degrading to silent NaNs."""
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)

        from egg_n_bacon_housing.adapters import datagovsg

        def raise_bug(*a, **kw):
            raise RuntimeError("a real programming bug")

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", raise_bug)

        with pytest.raises(RuntimeError, match="a real programming bug"):
            ingestion.raw_macro_data(bronze_dir=tmp_path)

    def test_raw_macro_data_degrades_on_schema_keyerror(self, tmp_path, monkeypatch):
        """Schema drift surfacing as KeyError still degrades gracefully (and
        is captured in the summary) rather than aborting the whole run."""
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)

        from egg_n_bacon_housing.adapters import datagovsg

        def raise_schema(*a, **kw):
            raise KeyError("DataSeries")

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", raise_schema)

        result = ingestion.raw_macro_data(bronze_dir=tmp_path)

        for key in ("cpi", "gdp", "hdb_rpi"):
            assert result[key].empty

    @staticmethod
    def _valid_raw_frame(ingestion, resource_id):
        """Minimal raw frame that each source's transform parses successfully."""
        if resource_id == ingestion.macro.UNEMPLOYMENT_RESOURCE_ID:
            return pd.DataFrame([{"DataSeries": "Total Unemployment Rate", "20261Q": "2.0"}])
        if resource_id == ingestion.macro.BANK_RATES_RESOURCE_ID:
            return pd.DataFrame(
                [
                    {
                        "DataSeries": "Compounded Singapore Overnight Rate Average (SORA) - 3 Month",
                        "2026Jan": "3.0",
                    }
                ]
            )
        if resource_id == ingestion.macro.HDB_RPI_RESOURCE_ID:
            return pd.DataFrame([{"quarter": "2026Q1", "index": "180.0"}])
        if resource_id == ingestion.macro.URA_PPI_RESOURCE_ID:
            return pd.DataFrame(
                [{"property_type": "All Residential", "quarter": "2026Q1", "index": "200.0"}]
            )
        if resource_id == ingestion.macro.SUPPLY_PIPELINE_RESOURCE_ID:
            return pd.DataFrame([{"quarter": "2026Q1", "no_of_units": "1234"}])
        if resource_id == ingestion.macro.WAGE_GROWTH_RESOURCE_ID:
            return pd.DataFrame([{"DataSeries": "Overall Economy", "2025": "4.5"}])
        return pd.DataFrame([{"DataSeries": "All Items", "2026Jan": "101.0"}])  # cpi

    def test_raw_macro_data_concurrent_fetch_isolates_retrievable_failure(
        self, tmp_path, monkeypatch, caplog
    ):
        """Under concurrent fetching, one source's retrievable failure degrades
        only that source: the others succeed, exactly one consolidated summary
        names the failure, no exception escapes, and no manifest entry is lost
        to the overlapping cache writes."""
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)

        from egg_n_bacon_housing.adapters import datagovsg

        in_flight = 0
        max_in_flight = 0
        gate = threading.Lock()

        def fake_fetch(_base_url, resource_id, use_cache=False):
            nonlocal in_flight, max_in_flight
            with gate:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
            try:
                # Hold each fetch open briefly so sibling workers provably overlap.
                time.sleep(0.1)
                if resource_id == ingestion.macro.GDP_RESOURCE_ID:
                    raise requests.ConnectionError("gdp endpoint down")
                return self._valid_raw_frame(ingestion, resource_id)
            finally:
                with gate:
                    in_flight -= 1

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", fake_fetch)

        with caplog.at_level(logging.WARNING, logger=ingestion.macro.logger.name):
            result = ingestion.raw_macro_data(bronze_dir=tmp_path)

        # The macro sources really were fetched concurrently, not serially.
        assert max_in_flight >= 2
        # Only the failed source degraded; every other source produced data.
        assert result["gdp"].empty
        assert len(result["cpi"]) == 1
        assert len(result["unemployment"]) == 1
        assert len(result["bank_rates"]) == 1
        assert len(result["hdb_rpi"]) == 1
        assert len(result["ura_ppi"]) == 1
        assert len(result["supply_pipeline"]) == 1
        assert len(result["wage_growth"]) == 4
        # Exactly one consolidated summary naming the failed source.
        summary_records = [r for r in caplog.records if "Macro ingestion" in r.getMessage()]
        assert len(summary_records) == 1
        msg = summary_records[0].getMessage()
        assert "1 indicator" in msg
        assert "gdp:" in msg and "ConnectionError" in msg
        # Concurrent cache writes must not lose any manifest entry.
        manifest = json.loads((tmp_path / "bronze_manifest.json").read_text(encoding="utf-8"))
        for filename in (
            "cpi.parquet",
            "unemployment.parquet",
            "bank_rates.parquet",
            "hdb_rpi.parquet",
            "ura_ppi.parquet",
            "supply_pipeline.parquet",
            "wage_growth.parquet",
        ):
            assert filename in manifest

    def test_raw_macro_data_concurrent_fetch_propagates_programming_defect(
        self, tmp_path, monkeypatch
    ):
        """A programming defect in a single source (TypeError is NOT
        retrievable) must still propagate out of the concurrent fetch instead
        of being swallowed into the per-source failure list."""
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)

        from egg_n_bacon_housing.adapters import datagovsg

        def fake_fetch(_base_url, resource_id, use_cache=False):
            if resource_id == ingestion.macro.HDB_RPI_RESOURCE_ID:
                raise TypeError("unexpected frame shape - programming defect")
            return pd.DataFrame([{"DataSeries": "All Items", "2026Jan": "101.0"}])

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", fake_fetch)

        with pytest.raises(TypeError, match="programming defect"):
            ingestion.raw_macro_data(bronze_dir=tmp_path)

    def test_raw_shopping_malls_prefers_geocoded_bronze_file(self, tmp_path):
        """Test that geocoded mall bronze output is preferred when present."""
        ingestion = _get_ingestion_module()
        geocoded = pd.DataFrame(
            [
                {
                    "shopping_mall": "ION Orchard",
                    "matched_name": "ION ORCHARD",
                    "lat": 1.3048,
                    "lon": 103.8318,
                    "found": True,
                }
            ]
        )
        geocoded.to_parquet(tmp_path / "raw_wiki_shopping_mall_geocoded.parquet", index=False)
        pd.DataFrame([{"shopping_mall": "ION Orchard"}]).to_parquet(
            tmp_path / "raw_wiki_shopping_mall.parquet",
            index=False,
        )

        from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

        result = ingestion.raw_shopping_malls(bronze_dir=tmp_path, geocoder=InMemoryGeocoder({}))

        assert result.loc[0, "shopping_mall"] == "ION Orchard"
        assert result.loc[0, "lat"] == pytest.approx(1.3048)
        assert result.loc[0, "lon"] == pytest.approx(103.8318)

    def test_raw_shopping_malls_geocodes_name_only_dataset(self, tmp_path):
        """Test that name-only mall data is geocoded and persisted to bronze."""
        ingestion = _get_ingestion_module()
        pd.DataFrame([{"shopping_mall": "ION Orchard"}]).to_parquet(
            tmp_path / "raw_wiki_shopping_mall.parquet",
            index=False,
        )

        from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

        geocoder = InMemoryGeocoder({"ION Orchard": (1.3048, 103.8318)})

        result = ingestion.raw_shopping_malls(bronze_dir=tmp_path, geocoder=geocoder)

        assert result.loc[0, "shopping_mall"] == "ION Orchard"
        assert result.loc[0, "lat"] == pytest.approx(1.3048)
        assert result.loc[0, "lon"] == pytest.approx(103.8318)
        assert (tmp_path / "raw_wiki_shopping_mall_geocoded.parquet").exists()

    def test_wiki_mall_deprecation_remedy_actually_clears_legacy_files(self, tmp_path, caplog):
        """The --refresh pattern in the warning must match what clear_bronze deletes."""
        ingestion = _get_ingestion_module()
        pd.DataFrame([{"shopping_mall": "ION Orchard"}]).to_parquet(
            tmp_path / "raw_wiki_shopping_mall.parquet", index=False
        )
        pd.DataFrame(
            [{"shopping_mall": "ION Orchard", "lat": 1.3048, "lon": 103.8318, "found": True}]
        ).to_parquet(tmp_path / "raw_wiki_shopping_mall_geocoded.parquet", index=False)

        from egg_n_bacon_housing.utils.bronze import clear_bronze
        from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

        with caplog.at_level(
            logging.WARNING, logger="egg_n_bacon_housing.components.ingestion.datagov"
        ):
            ingestion.raw_shopping_malls(bronze_dir=tmp_path, geocoder=InMemoryGeocoder({}))

        deprecation = [r for r in caplog.records if "deprecated wiki-sourced" in r.getMessage()]
        assert deprecation, caplog.text
        message = deprecation[0].getMessage()
        assert "deprecated" in message
        match = re.search(r"--refresh '([^']+)'", message)
        assert match, message
        pattern = match.group(1)

        # clear_bronze fnmatches the suffix-stripped relative bronze path
        for legacy_name in ("raw_wiki_shopping_mall", "raw_wiki_shopping_mall_geocoded"):
            assert fnmatch.fnmatch(legacy_name, pattern)

        removed = clear_bronze(tmp_path, pattern=pattern)
        assert {p.name for p in removed} == {
            "raw_wiki_shopping_mall.parquet",
            "raw_wiki_shopping_mall_geocoded.parquet",
        }

    @pytest.mark.parametrize(
        ("func_name", "cache_name"),
        [
            ("raw_hdb_property_info", "raw_hdb_property_info.parquet"),
            ("raw_dwelling_units_by_town", "raw_dwelling_units_by_town.parquet"),
            ("raw_median_annual_value", "raw_median_annual_value.parquet"),
            ("raw_hdb_resident_population", "raw_hdb_resident_population.parquet"),
        ],
    )
    def test_datagov_fetch_nodes_cache_successful_fetches(
        self, tmp_path, monkeypatch, func_name, cache_name
    ):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters import datagovsg

        fetched = pd.DataFrame([{"value": 1}])
        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", lambda *a, **kw: fetched)

        result = getattr(ingestion, func_name)(bronze_dir=tmp_path)

        pd.testing.assert_frame_equal(result, fetched)
        assert (tmp_path / cache_name).exists()

    @pytest.mark.parametrize(
        "func_name",
        [
            "raw_hdb_property_info",
            "raw_dwelling_units_by_town",
            "raw_median_annual_value",
            "raw_hdb_resident_population",
        ],
    )
    def test_datagov_fetch_nodes_return_empty_on_empty_fetch(
        self, tmp_path, monkeypatch, func_name
    ):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters import datagovsg

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", lambda *a, **kw: pd.DataFrame())

        result = getattr(ingestion, func_name)(bronze_dir=tmp_path)

        assert result.empty

    def test_raw_income_by_planning_area_computes_grouped_median(self, tmp_path, monkeypatch):
        """10k below 1k + 20k in [1_000, 1_500): median interpolates to 1_125
        (1000 + (15-10)/20 * 500), not the 1_250 bracket midpoint (WS12)."""
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters import datagovsg

        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *a, **kw: pd.DataFrame(
                [
                    {"Thousands": "Total", "Below_1_000": "10", "1_000_1_499": "20"},
                    {"Thousands": "Toa Payoh", "Below_1_000": "10", "1_000_1_499": "20"},
                ]
            ),
        )

        result = ingestion.raw_income_by_planning_area(bronze_dir=tmp_path)

        assert result["planning_area"].tolist() == ["Toa Payoh"]
        assert result["median_monthly_income"].tolist() == [1125]

    def test_raw_green_mark_buildings_filters_blank_postal_codes(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters import datagovsg

        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *a, **kw: pd.DataFrame(
                [
                    {"Project_Name": "A", "Postal_Code": "123456"},
                    {"Project_Name": "B", "Postal_Code": ""},
                    {"Project_Name": "C", "Postal_Code": None},
                ]
            ),
        )

        result = ingestion.raw_green_mark_buildings(bronze_dir=tmp_path)

        assert result["postal_code"].tolist() == ["123456"]

    def test_geocoded_green_mark_buildings_geocodes_unique_postal_codes(self, tmp_path):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

        raw = pd.DataFrame(
            [
                {"Project_Name": "A", "postal_code": "123456"},
                {"Project_Name": "B", "postal_code": "123456"},
                {"Project_Name": "C", "postal_code": "654321"},
            ]
        )

        result = ingestion.geocoded_green_mark_buildings(
            bronze_dir=tmp_path,
            raw_green_mark_buildings=raw,
            geocoder=InMemoryGeocoder({"123456": (1.3, 103.8), "654321": (1.31, 103.81)}),
        )

        assert result["lat"].tolist() == [1.3, 1.3, 1.31]
        assert result["name"].tolist() == ["A", "B", "C"]
        assert (tmp_path / "raw_green_mark_buildings_geocoded.parquet").exists()


class TestMacroHelpers:
    def test_melt_pivot_monthly_uses_dataseries_column(self):
        macro = _get_macro_module()
        raw = pd.DataFrame(
            [
                {"_id": 1, "DataSeries": "All Items", "2026Apr": "101.2", "2026May": "102.3"},
                {"_id": 2, "DataSeries": "Core Inflation", "2026Apr": "99.9", "2026May": "99.8"},
            ]
        )

        result = macro._melt_pivot_monthly(raw, "All Items", "cpi")

        assert result["cpi"].tolist() == [101.2, 102.3]
        assert result["date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-04-01", "2026-05-01"]

    def test_parse_datagov_quarter_accepts_both_supported_formats(self):
        macro = _get_macro_module()

        result = macro._parse_datagov_quarter(pd.Series(["20261Q", "2026Q2", "bad-value"]))

        assert result.iloc[0] == pd.Timestamp("2026-03-31")
        assert result.iloc[1] == pd.Timestamp("2026-06-30")
        assert pd.isna(result.iloc[2])


class TestGeojsonHelpers:
    def test_load_geojson_amenities_supports_polygon_centroids(self, tmp_path):
        geojson = _get_geojson_module()
        path = tmp_path / "parks.geojson"
        path.write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "properties": {"NAME": "Test Park"},
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [
                                    [[103.8, 1.3], [103.82, 1.3], [103.82, 1.32], [103.8, 1.32]]
                                ],
                            },
                        }
                    ]
                }
            )
        )

        result = geojson._load_geojson_amenities(path, ["NAME"], "park")

        assert result.loc[0, "name"] == "Test Park"
        assert result.loc[0, "lat"] == pytest.approx(1.31)
        assert result.loc[0, "lon"] == pytest.approx(103.81)

    def test_raw_mrt_stations_merges_geojson_and_line_metadata(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        _disable_live_mrt_fetch(ingestion, monkeypatch)
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)
        (external_dir / "mrt_stations.json").write_text(
            json.dumps([{"name": "TOA PAYOH", "line": "NSL"}])
        )
        (external_dir / "MRTStations.geojson").write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "properties": {"NAME": "TOA PAYOH"},
                            "geometry": {"type": "Point", "coordinates": [103.8478, 1.3329]},
                        }
                    ]
                }
            )
        )

        result = ingestion.raw_mrt_stations(bronze_dir=tmp_path)

        assert result.to_dict(orient="records") == [
            {"name": "TOA PAYOH", "lat": 1.3329, "lon": 103.8478, "line": "NSL"}
        ]


class TestUraCsvIngestion:
    def test_raw_condo_transactions_loads_cached_parquet(self, tmp_path):
        ura_csv = _get_ura_csv_module()
        cached = pd.DataFrame([{"price": 1000000.0}])
        cached.to_parquet(tmp_path / "raw_condo_transactions.parquet", index=False)

        result = ura_csv.raw_condo_transactions(bronze_dir=tmp_path, manual_dir=tmp_path / "manual")

        assert result.loc[0, "price"] == 1000000.0
        assert pd.isna(result.loc[0, "property_subtype"])

    def test_raw_condo_transactions_raises_when_no_manual_csvs_exist(self, tmp_path, monkeypatch):
        ura_csv = _get_ura_csv_module()
        monkeypatch.setattr(ura_csv, "_load_ura_csvs", lambda ura_dir, prefix: [])

        with pytest.raises(RuntimeError, match="no URA CSVs found"):
            ura_csv.raw_condo_transactions(bronze_dir=tmp_path, manual_dir=tmp_path / "manual")

    def test_raw_condo_transactions_normalizes_columns(self, tmp_path):
        ura_csv = _get_ura_csv_module()
        data_root = tmp_path / "data"
        ura_dir = data_root / "manual" / "csv" / "ura"
        ura_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                {
                    "Project Name": "Orchard Residences",
                    "Transacted Price ($)": "1,500,000",
                    "Area (SQFT)": "1,292",
                    "Area (SQM)": "120",
                    "Unit Price ($ PSF)": "1,161",
                    "Unit Price ($ PSM)": "12,500",
                    "Sale Date": "Jan-24",
                    "Street Name": "ORCHARD ROAD",
                    "Postal District": "9",
                }
            ]
        ).to_csv(ura_dir / "ResidentialTransaction2024.csv", index=False)

        result = ura_csv.raw_condo_transactions(
            bronze_dir=data_root / "pipeline" / "01_bronze", manual_dir=data_root / "manual"
        )

        assert result.loc[0, "project_name"] == "Orchard Residences"
        assert result.loc[0, "price"] == pytest.approx(1500000.0)
        assert result.loc[0, "area_sqft"] == pytest.approx(1292.0)
        assert result.loc[0, "transaction_date"] == pd.Timestamp("2024-01-01")
        assert result.loc[0, "property_type"] == "condo"
        assert pd.isna(result.loc[0, "property_subtype"])


def _mp25_malls_geojson():
    """Minimal URA MP25 mall-layer fixture: one MALL polygon, one PROMENADE polygon, one MALL point."""
    return {
        "features": [
            {
                "properties": {"CLASSIFCTN": "MALL"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[103.8, 1.3], [103.82, 1.3], [103.82, 1.32], [103.8, 1.32]]],
                },
            },
            {
                "properties": {"CLASSIFCTN": "PROMENADE"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[103.7, 1.2], [103.72, 1.2], [103.72, 1.22], [103.7, 1.22]]],
                },
            },
            {
                "properties": {"CLASSIFCTN": "MALL"},
                "geometry": {"type": "Point", "coordinates": [103.85, 1.35]},
            },
        ]
    }


class TestRawShoppingMallsMP25:
    """Test the URA MP25 mall layer as the primary malls source."""

    def test_builds_centroids_and_filters_classification(self):
        ingestion = _get_ingestion_module()

        result = ingestion.datagov._malls_from_mp25_geojson(_mp25_malls_geojson())

        assert len(result) == 2
        assert (result["name"] == "").all()
        assert result.loc[0, "lat"] == pytest.approx(1.31)
        assert result.loc[0, "lon"] == pytest.approx(103.81)
        assert result.loc[1, "lat"] == pytest.approx(1.35)
        assert result.loc[1, "lon"] == pytest.approx(103.85)

    def test_fetches_and_caches_to_bronze(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

        monkeypatch.setattr(
            ingestion.datagov.datagovsg,
            "fetch_datagovsg_geojson",
            lambda *a, **kw: _mp25_malls_geojson(),
        )

        result = ingestion.raw_shopping_malls(bronze_dir=tmp_path, geocoder=InMemoryGeocoder({}))

        assert len(result) == 2
        assert (tmp_path / "raw_mp25_malls.parquet").exists()

        # Second run must read bronze without re-fetching.
        calls = {"n": 0}

        def counting_fetch(*a, **kw):
            calls["n"] += 1
            return {}

        monkeypatch.setattr(ingestion.datagov.datagovsg, "fetch_datagovsg_geojson", counting_fetch)
        again = ingestion.raw_shopping_malls(bronze_dir=tmp_path, geocoder=InMemoryGeocoder({}))

        assert calls["n"] == 0
        assert len(again) == 2

    def test_empty_fetch_not_cached(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

        monkeypatch.setattr(
            ingestion.datagov.datagovsg,
            "fetch_datagovsg_geojson",
            lambda *a, **kw: {"features": []},
        )

        result = ingestion.raw_shopping_malls(bronze_dir=tmp_path, geocoder=InMemoryGeocoder({}))

        assert result.empty
        assert not (tmp_path / "raw_mp25_malls.parquet").exists()

    def test_fetch_error_degrades_to_empty(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters.exceptions import DatasetFetchError
        from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

        def boom(*a, **kw):
            raise DatasetFetchError("network down")

        monkeypatch.setattr(ingestion.datagov.datagovsg, "fetch_datagovsg_geojson", boom)

        result = ingestion.raw_shopping_malls(bronze_dir=tmp_path, geocoder=InMemoryGeocoder({}))

        assert result.empty
        assert not (tmp_path / "raw_mp25_malls.parquet").exists()


class TestEmptyBronzeCacheIsAMiss:
    """A 0-row bronze parquet is a miss (warn + refetch), never valid data.

    Mirrors the macro empty-guard contract
    (test_raw_macro_data_ignores_empty_cache_and_refetches) at the three
    datagov sites that previously treated an empty cache as a hit.
    """

    @pytest.mark.parametrize(
        ("error_name", "cache_filenames"),
        [
            ("rental_index", ("raw_rental_index.parquet", "raw_datagov_rental_index.parquet")),
            ("hdb_rental", ("raw_hdb_rental.parquet", "raw_datagov_hdb_rental.parquet")),
            (
                "school_directory",
                ("raw_school_directory.parquet", "raw_datagov_school_directory.parquet"),
            ),
        ],
    )
    def test_parameterized_nodes_ignore_empty_cache_and_refetch(
        self, tmp_path, monkeypatch, caplog, error_name, cache_filenames
    ):
        """rental_index / hdb_rental / school_directory via _load_or_fetch_dataset."""
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters import datagovsg

        pd.DataFrame().to_parquet(tmp_path / cache_filenames[0], index=False)
        fetched = pd.DataFrame([{"value": 1}])
        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", lambda *a, **kw: fetched)

        with caplog.at_level(
            logging.WARNING, logger="egg_n_bacon_housing.components.ingestion.datagov"
        ):
            result = ingestion.raw_dataset(
                bronze_dir=tmp_path,
                resource_id="d_test",
                cache_filenames=cache_filenames,
                display_name=error_name,
                error_name=error_name,
            )

        assert len(result) == 1
        assert any(
            "Ignoring empty bronze cache" in r.getMessage() and cache_filenames[0] in r.getMessage()
            for r in caplog.records
        )
        # The stale empty cache is replaced by the fetched data.
        repopulated = pd.read_parquet(tmp_path / cache_filenames[0])
        assert len(repopulated) == 1

    def test_raw_hdb_resale_transactions_ignores_empty_cache_and_refetches(
        self, tmp_path, monkeypatch, caplog
    ):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters import datagovsg

        pd.DataFrame().to_parquet(tmp_path / "raw_hdb_resale.parquet", index=False)
        fetched = pd.DataFrame([{"month": "2024-01", "resale_price": 500000.0}])
        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", lambda *a, **kw: fetched)

        with caplog.at_level(
            logging.WARNING, logger="egg_n_bacon_housing.components.ingestion.datagov"
        ):
            result = ingestion.raw_hdb_resale_transactions(
                bronze_dir=tmp_path, manual_dir=tmp_path / "manual"
            )

        assert len(result) == 1
        assert any("Ignoring empty bronze cache" in r.getMessage() for r in caplog.records)
        repopulated = pd.read_parquet(tmp_path / "raw_hdb_resale.parquet")
        assert len(repopulated) == 1

    def test_wiki_mall_empty_caches_fall_through_to_mp25(self, tmp_path, monkeypatch, caplog):
        """Empty wiki parquets are misses: warn per file and fetch the MP25 layer."""
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

        pd.DataFrame().to_parquet(tmp_path / "raw_wiki_shopping_mall.parquet", index=False)
        pd.DataFrame().to_parquet(tmp_path / "raw_wiki_shopping_mall_geocoded.parquet", index=False)
        monkeypatch.setattr(
            ingestion.datagov.datagovsg,
            "fetch_datagovsg_geojson",
            lambda *a, **kw: _mp25_malls_geojson(),
        )

        with caplog.at_level(
            logging.WARNING, logger="egg_n_bacon_housing.components.ingestion.datagov"
        ):
            result = ingestion.raw_shopping_malls(
                bronze_dir=tmp_path, geocoder=InMemoryGeocoder({})
            )

        # The MP25 primary source was fetched and cached despite wiki files existing.
        assert len(result) == 2
        assert (tmp_path / "raw_mp25_malls.parquet").exists()
        warnings = [
            r.getMessage()
            for r in caplog.records
            if "Ignoring empty bronze cache" in r.getMessage()
        ]
        assert len(warnings) == 2
        assert any("raw_wiki_shopping_mall.parquet" in w for w in warnings)
        assert any("raw_wiki_shopping_mall_geocoded.parquet" in w for w in warnings)

    def test_parameterized_fetch_calls_adapter_directly_despite_stale_api_cache(
        self, tmp_path, monkeypatch
    ):
        """Bronze is the only cache layer under these nodes: a stale API-cache
        entry under the legacy cache_id must never suppress the adapter call
        (WO-5 refresh correctness)."""
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters import datagovsg
        from egg_n_bacon_housing.utils import cache as cache_utils

        manager = cache_utils.CacheManager(tmp_path / "api_cache")
        manager.set("bronze_rental_index", pd.DataFrame([{"stale": 1}]))  # legacy cache_id

        fetched = pd.DataFrame([{"rent": 100.0}])
        calls = {"n": 0}

        def counting_fetch(*a, **kw):
            calls["n"] += 1
            return fetched

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", counting_fetch)

        result = ingestion.raw_dataset(
            bronze_dir=tmp_path,
            resource_id="d_test",
            cache_filenames=("raw_rental_index.parquet",),
            display_name="rental index",
            error_name="rental_index",
        )

        assert calls["n"] == 1  # adapter invoked directly; stale entry not served
        pd.testing.assert_frame_equal(result, fetched)


class TestGeojsonNameExtraction:
    """Test amenity name resolution: VENUE fallback and KML Description tables."""

    def test_sportsg_venue_fallback(self, tmp_path):
        geojson = _get_geojson_module()
        path = tmp_path / "SportSGFacilities.geojson"
        path.write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "properties": {"OBJECTID": 1, "VENUE": "ActiveSG Stadium"},
                            "geometry": {"type": "Point", "coordinates": [103.8, 1.3]},
                        }
                    ]
                }
            )
        )

        result = geojson._load_geojson_amenities(path, ["Name", "NAME", "VENUE"], "sports_facility")

        assert result.loc[0, "name"] == "ActiveSG Stadium"

    def test_chas_name_extracted_from_description_html(self, tmp_path):
        """KML placeholder names (kml_1) fall through to the Description table."""
        geojson = _get_geojson_module()
        path = tmp_path / "CHASClinics.geojson"
        path.write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "properties": {
                                "Name": "kml_1",
                                "Description": (
                                    "<table><tr><th>HCI_NAME</th> "
                                    "<td>Acumed Medical Group</td></tr></table>"
                                ),
                            },
                            "geometry": {"type": "Point", "coordinates": [103.8, 1.3]},
                        }
                    ]
                }
            )
        )

        result = geojson._load_geojson_amenities(path, ["Name", "NAME", "HCI_NAME"], "chas_clinic")

        assert result.loc[0, "name"] == "Acumed Medical Group"

    def test_kml_placeholder_without_description_yields_empty_name(self, tmp_path):
        geojson = _get_geojson_module()
        path = tmp_path / "CHASClinics.geojson"
        path.write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "properties": {"Name": "kml_1"},
                            "geometry": {"type": "Point", "coordinates": [103.8, 1.3]},
                        }
                    ]
                }
            )
        )

        result = geojson._load_geojson_amenities(path, ["Name", "NAME", "HCI_NAME"], "chas_clinic")

        assert result.loc[0, "name"] == ""


def _mrt_exits_geojson():
    """LTA MRT Station Exit fixture: two exits for one MRT station, one LRT station."""
    return {
        "features": [
            {
                "properties": {"STATION_NA": "BAYSHORE MRT STATION", "EXIT_CODE": "Exit 1"},
                "geometry": {"type": "Point", "coordinates": [103.9412, 1.3118]},
            },
            {
                "properties": {"STATION_NA": "BAYSHORE MRT STATION", "EXIT_CODE": "Exit 2"},
                "geometry": {"type": "Point", "coordinates": [103.9414, 1.3122]},
            },
            {
                "properties": {"STATION_NA": "RAPTOR LRT STATION", "EXIT_CODE": "Exit A"},
                "geometry": {"type": "Point", "coordinates": [103.9, 1.4]},
            },
        ]
    }


def _station_codes_df():
    return pd.DataFrame(
        [
            {
                "stn_code": "TE29",
                "mrt_station_english": "Bayshore",
                "mrt_line_english": "Thomson-East Coast Line",
            },
            {
                "stn_code": "BP1",
                "mrt_station_english": "Raptor",
                "mrt_line_english": "Bukit Panjang LRT",
            },
        ]
    )


class TestRawMrtStationsLive:
    """Test the live LTA MRT station fetch (exits + station codes)."""

    def test_builds_station_centroids_from_exits(self):
        geojson = _get_geojson_module()

        stations = geojson._stations_from_exits(_mrt_exits_geojson())

        assert len(stations) == 2
        bayshore = stations[stations["name"] == "BAYSHORE"].iloc[0]
        assert bayshore["lat"] == pytest.approx((1.3118 + 1.3122) / 2)
        assert bayshore["lon"] == pytest.approx((103.9412 + 103.9414) / 2)
        # " MRT STATION" / " LRT STATION" suffixes are stripped
        assert "RAPTOR" in set(stations["name"])

    def test_station_lines_mapping_normalizes_line_names(self):
        geojson = _get_geojson_module()

        mapping = geojson._station_lines_mapping(_station_codes_df())

        assert mapping["BAYSHORE"] == ["TEL"]
        assert mapping["RAPTOR"] == ["BPLR"]
        # static supplement covers stations LTA's codes dataset lacks (TEL)
        assert mapping["NAPIER"] == ["TEL"]
        assert mapping["BAYSHORE"] == ["TEL"]

    def test_supplement_merges_with_codes_for_interchanges(self):
        """Outram Park is NEL+EWL in the codes table and TEL in the supplement."""
        geojson = _get_geojson_module()
        codes = pd.DataFrame(
            [
                {
                    "stn_code": "NE3",
                    "mrt_station_english": "Outram Park",
                    "mrt_line_english": "North East Line",
                },
                {
                    "stn_code": "EW16",
                    "mrt_station_english": "Outram Park",
                    "mrt_line_english": "East West Line",
                },
            ]
        )

        mapping = geojson._station_lines_mapping(codes)

        assert mapping["OUTRAM PARK"] == ["NEL", "EWL", "TEL"]

    def test_live_fetch_wins_cache_and_refreshes_mapping_json(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        geojson = _get_geojson_module()
        fetches = {"n": 0}

        def fake_geojson_fetch(*_a, **_kw):
            fetches["n"] += 1
            return _mrt_exits_geojson()

        monkeypatch.setattr(geojson.datagovsg, "fetch_datagovsg_geojson", fake_geojson_fetch)
        monkeypatch.setattr(
            geojson.datagovsg,
            "fetch_datagovsg_dataset",
            lambda *a, **kw: _station_codes_df(),
        )

        result = ingestion.raw_mrt_stations(bronze_dir=tmp_path)

        assert fetches["n"] == 1
        assert len(result) == 2
        assert set(result["name"]) == {"BAYSHORE", "RAPTOR"}
        assert result.loc[result["name"] == "BAYSHORE", "line"].iloc[0] == "TEL"
        # station->line mapping written where mrt_line_mapping reads it
        mapping = json.loads((tmp_path / "external" / "mrt_stations.json").read_text())
        assert mapping["BAYSHORE"] == ["TEL"]
        assert (tmp_path / "raw_mrt_stations.parquet").exists()

        # second run reads bronze without re-fetching
        again = ingestion.raw_mrt_stations(bronze_dir=tmp_path)
        assert fetches["n"] == 1
        assert len(again) == 2

    def test_exit_fetch_failure_falls_back_to_legacy(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        _disable_live_mrt_fetch(ingestion, monkeypatch)
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)
        (external_dir / "mrt_stations.json").write_text(json.dumps({"BISHAN": ["NSL"]}))
        (external_dir / "MRTStations.geojson").write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "properties": {"NAME": "BISHAN"},
                            "geometry": {"type": "Point", "coordinates": [103.83, 1.35]},
                        }
                    ]
                }
            )
        )

        result = ingestion.raw_mrt_stations(bronze_dir=tmp_path)

        assert result.to_dict(orient="records") == [
            {"name": "BISHAN", "lat": 1.35, "lon": 103.83, "line": "NSL"}
        ]

    def test_empty_live_result_not_cached(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        geojson = _get_geojson_module()
        monkeypatch.setattr(
            geojson.datagovsg,
            "fetch_datagovsg_geojson",
            lambda *a, **kw: {"features": []},
        )

        result = ingestion.raw_mrt_stations(bronze_dir=tmp_path)

        assert result.empty
        assert not (tmp_path / "raw_mrt_stations.parquet").exists()


class TestMacroSourceSpec:
    """The declarative macro spec must cover exactly the fetchable keys."""

    def test_macro_sources_cover_all_fetchable_keys(self):
        import importlib

        macro = importlib.import_module("egg_n_bacon_housing.components.ingestion.macro")

        keys = [source.key for source in macro._MACRO_SOURCES]
        assert keys == [
            "cpi",
            "unemployment",
            "gdp",
            "bank_rates",
            "hdb_rpi",
            "ura_ppi",
            "supply_pipeline",
            "wage_growth",
        ]
        # every resource id present and filenames unique
        assert all(source.resource_id for source in macro._MACRO_SOURCES)
        filenames = [source.filename for source in macro._MACRO_SOURCES]
        assert len(filenames) == len(set(filenames))


def _read_bronze_manifest(bronze_dir: Path) -> dict:
    path = bronze_dir / "bronze_manifest.json"
    assert path.exists(), f"expected bronze manifest at {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _seed_stale_manifest(bronze_dir: Path, name: str, age_days: int) -> None:
    """Write a manifest entry for ``name`` with an old fetched_at."""
    bronze_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = bronze_dir / "bronze_manifest.json"
    manifest: dict = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[name] = {
        "fetched_at": (datetime.now(UTC) - timedelta(days=age_days)).isoformat(),
        "source": "test",
        "rows": 1,
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


class TestBronzeFetchMetadataWiring:
    """record_bronze_fetch fires on fetch paths; warn_if_stale on rolling cache hits."""

    def test_parameterized_datagov_node_records_on_fetch_not_on_cache_hit(
        self, tmp_path, monkeypatch
    ):
        """Representative node: fetch writes a manifest entry; cache hit never re-records."""
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters import datagovsg

        fetched = pd.DataFrame([{"rent": 100.0}])
        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", lambda *a, **kw: fetched)

        ingestion.raw_dataset(
            bronze_dir=tmp_path,
            resource_id="d_test",
            cache_filenames=("raw_rental_index.parquet",),
            display_name="rental index",
            error_name="rental_index",
        )

        entry = _read_bronze_manifest(tmp_path)["raw_rental_index"]
        assert entry["source"] == "datagov_api"
        assert entry["rows"] == 1
        first_fetched_at = entry["fetched_at"]

        # Cache hit: fetch must not even be attempted, and fetched_at stays put.
        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *a, **kw: pytest.fail("cache hit must not re-fetch"),
        )
        ingestion.raw_dataset(
            bronze_dir=tmp_path,
            resource_id="d_test",
            cache_filenames=("raw_rental_index.parquet",),
            display_name="rental index",
            error_name="rental_index",
        )
        assert _read_bronze_manifest(tmp_path)["raw_rental_index"]["fetched_at"] == (
            first_fetched_at
        )

    def test_hdb_resale_fetch_records_manifest(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters import datagovsg

        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *a, **kw: pd.DataFrame([{"month": "2024-01", "resale_price": 500000.0}]),
        )

        ingestion.raw_hdb_resale_transactions(bronze_dir=tmp_path, manual_dir=tmp_path / "manual")

        entry = _read_bronze_manifest(tmp_path)["raw_hdb_resale"]
        # No historical CSV dir in tmp_path -> API-only source id.
        assert entry["source"] == "datagov_api"
        assert entry["rows"] == 1

    def test_hdb_resale_cache_hit_warns_when_stale(self, tmp_path, monkeypatch, caplog):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters import datagovsg

        pd.DataFrame([{"month": "2024-01"}]).to_parquet(
            tmp_path / "raw_hdb_resale.parquet", index=False
        )
        _seed_stale_manifest(tmp_path, "raw_hdb_resale", age_days=40)
        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *a, **kw: pytest.fail("stale cache must not re-fetch"),
        )

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.utils.bronze"):
            result = ingestion.raw_hdb_resale_transactions(
                bronze_dir=tmp_path, manual_dir=tmp_path / "manual"
            )

        assert len(result) == 1
        stale = [r for r in caplog.records if "is stale" in r.getMessage()]
        assert len(stale) == 1
        assert "raw_hdb_resale" in stale[0].getMessage()
        assert "main.py --refresh raw_hdb_resale" in stale[0].getMessage()

    def test_hdb_resale_cache_hit_fresh_is_silent(self, tmp_path, monkeypatch, caplog):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters import datagovsg

        pd.DataFrame([{"month": "2024-01"}]).to_parquet(
            tmp_path / "raw_hdb_resale.parquet", index=False
        )
        record = {"fetched_at": datetime.now(UTC).isoformat(), "source": "t", "rows": 1}
        (tmp_path / "bronze_manifest.json").write_text(
            json.dumps({"raw_hdb_resale": record}), encoding="utf-8"
        )
        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *a, **kw: pytest.fail("fresh cache must not re-fetch"),
        )

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.utils.bronze"):
            ingestion.raw_hdb_resale_transactions(
                bronze_dir=tmp_path, manual_dir=tmp_path / "manual"
            )

        assert [r for r in caplog.records if "raw_hdb_resale" in r.getMessage()] == []

    def test_condo_csv_fetch_records_manifest(self, tmp_path):
        ura_csv = _get_ura_csv_module()
        data_root = tmp_path / "data"
        ura_dir = data_root / "manual" / "csv" / "ura"
        ura_dir.mkdir(parents=True)
        pd.DataFrame(
            [
                {
                    "Project Name": "Orchard Residences",
                    "Transacted Price ($)": "1,500,000",
                    "Area (SQFT)": "1,292",
                    "Area (SQM)": "120",
                    "Sale Date": "Jan-24",
                    "Street Name": "ORCHARD ROAD",
                    "Postal District": "9",
                }
            ]
        ).to_csv(ura_dir / "ResidentialTransaction2024.csv", index=False)
        bronze_dir = data_root / "pipeline" / "01_bronze"

        ura_csv.raw_condo_transactions(bronze_dir=bronze_dir, manual_dir=data_root / "manual")

        entry = _read_bronze_manifest(bronze_dir)["raw_condo_transactions"]
        assert entry["source"] == "manual_csv"  # no access key -> CSV-only path
        assert entry["rows"] == 1

    def test_condo_cache_hit_warns_when_stale(self, tmp_path, caplog):
        ura_csv = _get_ura_csv_module()
        pd.DataFrame([{"price": 1.0}]).to_parquet(
            tmp_path / "raw_condo_transactions.parquet", index=False
        )
        _seed_stale_manifest(tmp_path, "raw_condo_transactions", age_days=36)

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.utils.bronze"):
            ura_csv.raw_condo_transactions(bronze_dir=tmp_path, manual_dir=tmp_path / "manual")

        stale = [r for r in caplog.records if "is stale" in r.getMessage()]
        assert len(stale) == 1
        assert "main.py --refresh raw_condo_transactions" in stale[0].getMessage()

    def test_amenity_load_records_r2_external_source(self, tmp_path):
        geojson = _get_geojson_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True)
        (external_dir / "HawkerCentresGEOJSON.geojson").write_text(
            json.dumps(
                {
                    "features": [
                        {
                            "properties": {"NAME": "Maxwell"},
                            "geometry": {"type": "Point", "coordinates": [103.84, 1.28]},
                        }
                    ]
                }
            )
        )

        result = geojson.raw_hawker_centres(bronze_dir=tmp_path)

        assert len(result) == 1
        entry = _read_bronze_manifest(tmp_path)["HawkerCentresGEOJSON.geojson"]
        assert entry["source"] == "r2_external"
        assert entry["rows"] == 1

    def test_missing_amenity_file_records_nothing(self, tmp_path):
        geojson = _get_geojson_module()

        result = geojson.raw_hawker_centres(bronze_dir=tmp_path)

        assert result.empty
        assert not (tmp_path / "bronze_manifest.json").exists()

    def test_live_mrt_fetch_records_lta_api_source(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        geojson = _get_geojson_module()
        monkeypatch.setattr(
            geojson.datagovsg, "fetch_datagovsg_geojson", lambda *a, **kw: _mrt_exits_geojson()
        )
        monkeypatch.setattr(
            geojson.datagovsg,
            "fetch_datagovsg_dataset",
            lambda *a, **kw: _station_codes_df(),
        )

        ingestion.raw_mrt_stations(bronze_dir=tmp_path)

        entry = _read_bronze_manifest(tmp_path)["raw_mrt_stations"]
        assert entry["source"] == "lta_api"
        assert entry["rows"] == 2

    def test_macro_fetch_records_datagov_api_source(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True)
        pd.DataFrame([{"rate": 1.2}]).to_parquet(external_dir / "sora_rates.parquet", index=False)

        from egg_n_bacon_housing.adapters import datagovsg

        def fake_fetch(_base_url, resource_id, use_cache=False):
            if resource_id == ingestion.macro.CPI_RESOURCE_ID:
                return pd.DataFrame([{"DataSeries": "All Items", "2026Jan": "101.0"}])
            return pd.DataFrame()

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", fake_fetch)

        ingestion.raw_macro_data(bronze_dir=tmp_path)

        entry = _read_bronze_manifest(tmp_path)["cpi.parquet"]
        assert entry["source"] == "datagov_api"
        assert entry["rows"] == 1
        # SORA is a seeded static file, never fetched — no manifest entry.
        assert "sora_rates.parquet" not in _read_bronze_manifest(tmp_path)

    def test_geocoded_green_mark_write_records_onemap_source(self, tmp_path):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

        raw = pd.DataFrame([{"Project_Name": "A", "postal_code": "123456"}])

        ingestion.geocoded_green_mark_buildings(
            bronze_dir=tmp_path,
            raw_green_mark_buildings=raw,
            geocoder=InMemoryGeocoder({"123456": (1.3, 103.8)}),
        )

        entry = _read_bronze_manifest(tmp_path)["raw_green_mark_buildings_geocoded"]
        assert entry["source"] == "onemap_geocode"

    def test_mp25_malls_fetch_records_datagov_source(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

        monkeypatch.setattr(
            ingestion.datagov.datagovsg,
            "fetch_datagovsg_geojson",
            lambda *a, **kw: _mp25_malls_geojson(),
        )

        ingestion.raw_shopping_malls(bronze_dir=tmp_path, geocoder=InMemoryGeocoder({}))

        entry = _read_bronze_manifest(tmp_path)["raw_mp25_malls"]
        assert entry["source"] == "datagov_api"
        assert entry["rows"] == 2


def _spy_write_bronze_cache(monkeypatch, module) -> list[str]:
    """Wrap a module's write_bronze_cache, recording the manifest names written.

    The spy delegates to the real helper, so written files and manifest entries
    stay observable while the test asserts routing through the choke point.
    """
    from egg_n_bacon_housing.utils.bronze import write_bronze_cache as real_write

    calls: list[str] = []

    def spy(bronze_dir, df, name, source, **kwargs):
        calls.append(name)
        return real_write(bronze_dir, df, name, source, **kwargs)

    monkeypatch.setattr(module, "write_bronze_cache", spy)
    return calls


class TestCentralizedBronzeCacheHelpers:
    """One representative node per module routes cache I/O through utils.bronze."""

    def test_datagov_fetch_writes_via_helper_and_cache_hit_reads_only(self, tmp_path, monkeypatch):
        """Representative node: the @parameterize base of all datagov fetches."""
        ingestion = _get_ingestion_module()
        import egg_n_bacon_housing.components.ingestion.datagov as datagov
        from egg_n_bacon_housing.adapters import datagovsg

        calls = _spy_write_bronze_cache(monkeypatch, datagov)
        monkeypatch.setattr(
            datagovsg, "fetch_datagovsg_dataset", lambda *a, **kw: pd.DataFrame([{"rent": 1.0}])
        )

        def run_node():
            return ingestion.raw_dataset(
                bronze_dir=tmp_path,
                resource_id="d_test",
                cache_filenames=("raw_rental_index.parquet",),
                display_name="rental index",
                error_name="rental_index",
            )

        result = run_node()

        assert calls == ["raw_rental_index"]
        assert len(result) == 1
        assert (tmp_path / "raw_rental_index.parquet").exists()
        assert _read_bronze_manifest(tmp_path)["raw_rental_index"]["rows"] == 1

        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *a, **kw: pytest.fail("cache hit must not re-fetch"),
        )
        assert len(run_node()) == 1
        assert calls == ["raw_rental_index"]  # cache-hit path writes nothing

    def test_geojson_mrt_fetch_writes_via_helper_and_cache_hit_reads_only(
        self, tmp_path, monkeypatch
    ):
        ingestion = _get_ingestion_module()
        geojson = _get_geojson_module()
        monkeypatch.setattr(
            geojson.datagovsg, "fetch_datagovsg_geojson", lambda *a, **kw: _mrt_exits_geojson()
        )
        monkeypatch.setattr(
            geojson.datagovsg, "fetch_datagovsg_dataset", lambda *a, **kw: _station_codes_df()
        )
        calls = _spy_write_bronze_cache(monkeypatch, geojson)

        result = ingestion.raw_mrt_stations(bronze_dir=tmp_path)

        assert calls == ["raw_mrt_stations"]
        assert len(result) == 2
        assert _read_bronze_manifest(tmp_path)["raw_mrt_stations"]["rows"] == 2

        again = ingestion.raw_mrt_stations(bronze_dir=tmp_path)

        assert len(again) == 2
        assert calls == ["raw_mrt_stations"]  # cache-hit path writes nothing

    def test_macro_fetch_writes_via_helper_and_cache_hit_reads_only(self, tmp_path, monkeypatch):
        ingestion = _get_ingestion_module()
        macro = _get_macro_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True)
        pd.DataFrame([{"rate": 1.2}]).to_parquet(external_dir / "sora_rates.parquet", index=False)

        from egg_n_bacon_housing.adapters import datagovsg

        def fake_fetch(_base_url, resource_id, use_cache=False):
            if resource_id == macro.CPI_RESOURCE_ID:
                return pd.DataFrame([{"DataSeries": "All Items", "2026Jan": "101.0"}])
            return pd.DataFrame()

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", fake_fetch)
        calls = _spy_write_bronze_cache(monkeypatch, macro)

        result = ingestion.raw_macro_data(bronze_dir=tmp_path)

        assert calls == ["cpi.parquet"]
        assert len(result["cpi"]) == 1
        assert (external_dir / "cpi.parquet").exists()
        assert _read_bronze_manifest(tmp_path)["cpi.parquet"]["rows"] == 1

        def no_cpi_fetch(_base_url, resource_id, use_cache=False):
            if resource_id == macro.CPI_RESOURCE_ID:
                pytest.fail("cpi cache hit must not re-fetch")
            return pd.DataFrame()  # other indicators degrade to empty (never cached)

        monkeypatch.setattr(datagovsg, "fetch_datagovsg_dataset", no_cpi_fetch)
        again = ingestion.raw_macro_data(bronze_dir=tmp_path)

        assert len(again["cpi"]) == 1
        assert calls == ["cpi.parquet"]  # cache-hit path writes nothing

    def test_ura_fetch_writes_via_helper_and_cache_hit_reads_only(self, tmp_path, monkeypatch):
        ura_csv = _get_ura_csv_module()
        manual_dir = tmp_path / "manual"
        ura_dir = manual_dir / "csv" / "ura"
        ura_dir.mkdir(parents=True)
        pd.DataFrame(
            [
                {
                    "Project Name": "Orchard Residences",
                    "Transacted Price ($)": "1,500,000",
                    "Area (SQFT)": "1,292",
                    "Sale Date": "Jan-24",
                    "Street Name": "ORCHARD ROAD",
                }
            ]
        ).to_csv(ura_dir / "ResidentialTransaction2024.csv", index=False)
        bronze_dir = tmp_path / "pipeline" / "01_bronze"
        calls = _spy_write_bronze_cache(monkeypatch, ura_csv)

        def run_node():
            return ura_csv.raw_condo_transactions(bronze_dir=bronze_dir, manual_dir=manual_dir)

        result = run_node()

        assert calls == ["raw_condo_transactions"]
        assert len(result) == 1
        assert (bronze_dir / "raw_condo_transactions.parquet").exists()
        assert _read_bronze_manifest(bronze_dir)["raw_condo_transactions"]["rows"] == 1

        assert len(run_node()) == 1
        assert calls == ["raw_condo_transactions"]  # cache-hit path writes nothing

    def test_geocoded_green_mark_all_na_coordinates_not_cached(self, tmp_path):
        """All-NA-coordinate frames must not be cached as valid bronze (macro semantics)."""
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

        raw = pd.DataFrame([{"Project_Name": "A", "postal_code": "999999"}])

        result = ingestion.geocoded_green_mark_buildings(
            bronze_dir=tmp_path,
            raw_green_mark_buildings=raw,
            geocoder=InMemoryGeocoder({}),
        )

        assert len(result) == 1
        assert result["lat"].isna().all()
        assert not (tmp_path / "raw_green_mark_buildings_geocoded.parquet").exists()
        assert not (tmp_path / "bronze_manifest.json").exists()


class TestManualDirInjection:
    """manual_dir is injected by the pipeline; bronze-dir traversal is banned."""

    def test_hdb_resale_merges_manual_csvs_from_injected_manual_dir(self, tmp_path, monkeypatch):
        """Pre-2017 CSVs are found via the injected manual_dir, wherever it points."""
        ingestion = _get_ingestion_module()
        from egg_n_bacon_housing.adapters import datagovsg

        manual_dir = tmp_path / "anywhere" / "manual"
        csv_dir = manual_dir / "csv" / "ResaleFlatPrices"
        csv_dir.mkdir(parents=True)
        pd.DataFrame(
            [
                {
                    "month": "2016-12",
                    "resale_price": 300000.0,
                    "floor_area_sqm": "90",
                    "lease_commence_date": "1990",
                    "remaining_lease": "64 years",
                }
            ]
        ).to_csv(csv_dir / "ResaleFlatPrices2016.csv", index=False)

        monkeypatch.setattr(
            datagovsg,
            "fetch_datagovsg_dataset",
            lambda *a, **kw: pd.DataFrame([{"month": "2017-01", "resale_price": 500000.0}]),
        )

        bronze_dir = tmp_path / "pipeline" / "01_bronze"
        result = ingestion.raw_hdb_resale_transactions(bronze_dir=bronze_dir, manual_dir=manual_dir)

        assert result["month"].tolist() == ["2016-12", "2017-01"]
        assert (bronze_dir / "raw_hdb_resale.parquet").exists()
        entry = _read_bronze_manifest(bronze_dir)["raw_hdb_resale"]
        assert entry["source"] == "datagov_api+manual_csv"
        assert entry["rows"] == 2

    def test_ura_manual_dir_respected_outside_bronze_siblings(self, tmp_path):
        """Injection, not traversal: manual_dir need not be bronze_dir's sibling.

        A decoy directory at the old traversal location (bronze_dir.parent.parent
        / "manual") stays empty, so only the injected manual_dir can succeed.
        """
        ura_csv = _get_ura_csv_module()
        bronze_dir = tmp_path / "pipeline" / "01_bronze"
        decoy = tmp_path / "manual" / "csv" / "ura"
        decoy.mkdir(parents=True)  # exists but holds no CSVs
        manual_dir = tmp_path / "manuals-v2"
        ura_dir = manual_dir / "csv" / "ura"
        ura_dir.mkdir(parents=True)
        pd.DataFrame(
            [
                {
                    "Project Name": "Orchard Residences",
                    "Transacted Price ($)": "1,500,000",
                    "Area (SQFT)": "1,292",
                    "Sale Date": "Jan-24",
                    "Street Name": "ORCHARD ROAD",
                }
            ]
        ).to_csv(ura_dir / "ResidentialTransaction2024.csv", index=False)

        result = ura_csv.raw_condo_transactions(bronze_dir=bronze_dir, manual_dir=manual_dir)

        assert result.loc[0, "project_name"] == "Orchard Residences"
        assert (bronze_dir / "raw_condo_transactions.parquet").exists()

    def test_no_parent_parent_remains_under_components(self):
        """Grep-style guard: manual-CSV lookup must use injected manual_dir."""
        import egg_n_bacon_housing.components as components_pkg

        root = Path(components_pkg.__file__).resolve().parent
        offenders = sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*.py")
            if "parent.parent" in path.read_text(encoding="utf-8")
        )
        assert offenders == []
