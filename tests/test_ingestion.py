"""Test ingestion component."""

import json

import pandas as pd
import pytest

pytestmark = pytest.mark.unit


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
            cache_id="bronze_hdb_resale_raw",
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
                cache_id="bronze_hdb_resale_raw",
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
            cache_id="bronze_rental_index",
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
            cache_id="bronze_hdb_rental_raw",
            cache_filenames=("raw_hdb_rental.parquet", "raw_datagov_hdb_rental.parquet"),
            display_name="HDB rental",
            error_name="hdb_rental",
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_raw_mrt_stations_reads_from_bronze_external(self, tmp_path, monkeypatch):
        """Test that MRT station reference data is read from bronze/external."""
        ingestion = _get_ingestion_module()
        external_dir = tmp_path / "external"
        external_dir.mkdir(parents=True, exist_ok=True)
        mrt_payload = [{"name": "TOA PAYOH", "lat": 1.33, "lon": 103.85}]
        (external_dir / "mrt_stations.json").write_text(json.dumps(mrt_payload))

        result = ingestion.raw_mrt_stations(bronze_dir=tmp_path)

        assert result.to_dict(orient="records") == mrt_payload

    def test_raw_mrt_stations_accepts_legacy_mapping_payload(self, tmp_path):
        """Legacy station->line mapping payloads remain readable."""
        ingestion = _get_ingestion_module()
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

    def test_raw_income_by_planning_area_computes_weighted_median(self, tmp_path, monkeypatch):
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
        assert result["median_monthly_income"].tolist() == [1250]

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

    def test_raw_mrt_stations_merges_geojson_and_line_metadata(self, tmp_path):
        ingestion = _get_ingestion_module()
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
        expected = pd.DataFrame([{"price": 1000000.0}])
        expected.to_parquet(tmp_path / "raw_condo_transactions.parquet", index=False)

        result = ura_csv.raw_condo_transactions(bronze_dir=tmp_path)

        pd.testing.assert_frame_equal(result, expected)

    def test_raw_condo_transactions_raises_when_no_manual_csvs_exist(self, tmp_path, monkeypatch):
        ura_csv = _get_ura_csv_module()
        monkeypatch.setattr(ura_csv, "_load_ura_csvs", lambda ura_dir, prefix: [])

        with pytest.raises(RuntimeError, match="no URA CSVs found"):
            ura_csv.raw_condo_transactions(bronze_dir=tmp_path)

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

        result = ura_csv.raw_condo_transactions(bronze_dir=data_root / "pipeline" / "01_bronze")

        assert result.loc[0, "project_name"] == "Orchard Residences"
        assert result.loc[0, "price"] == pytest.approx(1500000.0)
        assert result.loc[0, "area_sqft"] == pytest.approx(1292.0)
        assert result.loc[0, "transaction_date"] == pd.Timestamp("2024-01-01")
        assert result.loc[0, "property_type"] == "condo"
