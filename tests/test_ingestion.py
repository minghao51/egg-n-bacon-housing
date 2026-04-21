"""Test 01_ingestion component."""

import importlib
import json

import pandas as pd
import pytest


def _get_ingestion_module():
    """Get the 01_ingestion module."""
    return importlib.import_module("egg_n_bacon_housing.components.01_ingestion")


class TestBronzeLayer:
    """Test bronze layer data ingestion functions."""

    def test_raw_hdb_resale_transactions_prefers_bronze_cache(self, tmp_path, monkeypatch):
        """Test that HDB resale loads from the configured bronze directory."""
        ingestion = _get_ingestion_module()
        expected = pd.DataFrame([{"resale_price": 500000.0, "month": "2024-01"}])
        (tmp_path / "raw_hdb_resale.parquet").parent.mkdir(parents=True, exist_ok=True)
        expected.to_parquet(tmp_path / "raw_hdb_resale.parquet", index=False)

        monkeypatch.setattr(ingestion, "bronze_dir", lambda: tmp_path)
        monkeypatch.setattr(
            ingestion.datagovsg,
            "fetch_datagovsg_dataset",
            lambda *args, **kwargs: pytest.fail("network fetch should not run when cache exists"),
        )

        result = ingestion.raw_hdb_resale_transactions()
        pd.testing.assert_frame_equal(result, expected)

    def test_raw_rental_index_reads_legacy_bronze_filename(self, tmp_path, monkeypatch):
        """Test that rental index reads the tracked bronze parquet filename."""
        ingestion = _get_ingestion_module()
        expected = pd.DataFrame([{"quarter": "2024-Q1", "index": "100.0"}])
        expected.to_parquet(tmp_path / "raw_datagov_rental_index.parquet", index=False)

        monkeypatch.setattr(ingestion, "bronze_dir", lambda: tmp_path)
        monkeypatch.setattr(
            ingestion.datagovsg,
            "fetch_datagovsg_dataset",
            lambda *args, **kwargs: pytest.fail("network fetch should not run when cache exists"),
        )

        result = ingestion.raw_rental_index()
        pd.testing.assert_frame_equal(result, expected)

    def test_raw_hdb_rental_reads_tracked_bronze_filename(self, tmp_path, monkeypatch):
        """Test that HDB rental reads the tracked bronze parquet filename."""
        ingestion = _get_ingestion_module()
        expected = pd.DataFrame([{"town": "TOA PAYOH", "monthly_rent": "3500"}])
        expected.to_parquet(tmp_path / "raw_datagov_hdb_rental.parquet", index=False)

        monkeypatch.setattr(ingestion, "bronze_dir", lambda: tmp_path)
        monkeypatch.setattr(
            ingestion.datagovsg,
            "fetch_datagovsg_dataset",
            lambda *args, **kwargs: pytest.fail("network fetch should not run when cache exists"),
        )

        result = ingestion.raw_hdb_rental()
        pd.testing.assert_frame_equal(result, expected)

    def test_raw_mrt_stations_reads_from_bronze_external(self, tmp_path, monkeypatch):
        """Test that MRT station reference data is read from bronze/external."""
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)
        mrt_payload = [{"name": "TOA PAYOH", "lat": 1.33, "lon": 103.85}]
        (external_dir / "mrt_stations.json").write_text(json.dumps(mrt_payload))

        monkeypatch.setattr(ingestion, "bronze_dir", lambda: tmp_path)
        result = ingestion.raw_mrt_stations()

        assert result.to_dict(orient="records") == mrt_payload

    def test_raw_macro_data_returns_expected_keys(self, tmp_path, monkeypatch):
        """Test that macro loaders resolve files from bronze/external."""
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"rate": 1.2}]).to_parquet(external_dir / "sora_rates.parquet", index=False)
        pd.DataFrame([{"value": 100}]).to_parquet(external_dir / "cpi.parquet", index=False)

        monkeypatch.setattr(ingestion, "bronze_dir", lambda: tmp_path)

        result = ingestion.raw_macro_data()

        assert isinstance(result, dict)
        assert set(result) == {"sora", "cpi", "gdp", "unemployment", "ppi"}
        assert not result["sora"].empty
        assert not result["cpi"].empty
        assert result["gdp"].empty

    def test_raw_shopping_malls_prefers_geocoded_bronze_file(self, tmp_path, monkeypatch):
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

        monkeypatch.setattr(ingestion, "bronze_dir", lambda: tmp_path)
        monkeypatch.setattr(
            ingestion,
            "_geocode_shopping_malls",
            lambda malls_df: pytest.fail("geocoding should not run when geocoded bronze exists"),
        )

        result = ingestion.raw_shopping_malls()

        assert result.loc[0, "shopping_mall"] == "ION Orchard"
        assert result.loc[0, "lat"] == pytest.approx(1.3048)
        assert result.loc[0, "lon"] == pytest.approx(103.8318)

    def test_raw_shopping_malls_geocodes_name_only_dataset(self, tmp_path, monkeypatch):
        """Test that name-only mall data is geocoded and persisted to bronze."""
        ingestion = _get_ingestion_module()
        pd.DataFrame([{"shopping_mall": "ION Orchard"}]).to_parquet(
            tmp_path / "raw_wiki_shopping_mall.parquet",
            index=False,
        )

        query_log = []

        monkeypatch.setattr(ingestion, "bronze_dir", lambda: tmp_path)
        monkeypatch.setattr(
            ingestion.onemap, "setup_onemap_headers", lambda: {"Authorization": "x"}
        )

        def fake_fetch(search_string, headers, timeout):
            query_log.append(search_string)
            if search_string == "ION Orchard":
                return pd.DataFrame()
            return pd.DataFrame(
                [
                    {
                        "SEARCHVAL": "ION ORCHARD",
                        "LATITUDE": "1.3048",
                        "LONGITUDE": "103.8318",
                        "POSTAL": "238801",
                        "ADDRESS": "2 ORCHARD TURN",
                        "BUILDING": "ION ORCHARD",
                        "search_result": 0,
                    }
                ]
            )

        monkeypatch.setattr(ingestion.onemap, "fetch_data_cached", fake_fetch)

        result = ingestion.raw_shopping_malls()

        assert query_log == ["ION Orchard", "ION Orchard Singapore"]
        assert result.loc[0, "shopping_mall"] == "ION Orchard"
        assert result.loc[0, "matched_name"] == "ION ORCHARD"
        assert result.loc[0, "lat"] == pytest.approx(1.3048)
        assert result.loc[0, "lon"] == pytest.approx(103.8318)
        assert (tmp_path / "raw_wiki_shopping_mall_geocoded.parquet").exists()
