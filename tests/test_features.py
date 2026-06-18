"""Test 03_features component."""

import pandas as pd
import pytest

from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder

pytestmark = pytest.mark.unit


def _get_features_module():
    """Get the 03_features module."""
    from egg_n_bacon_housing.components import features

    return features


def _make_mrt_stations():
    return pd.DataFrame([{"name": "Toa Payoh", "lat": 1.332, "lon": 103.847}])


class TestGoldLayer:
    """Test gold layer feature engineering functions."""

    def test_rental_yield_uses_rental_transactions_instead_of_placeholder(self, tmp_path):
        """Test that rental yield is derived from observed rent and sale data."""
        features = _get_features_module()

        hdb_validated = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "flat_type": "4 ROOM",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "town": "TOA PAYOH",
                    "price": 520000.0,
                    "flat_type": "4 ROOM",
                    "transaction_date": pd.Timestamp("2024-01-28"),
                },
            ]
        )

        raw_hdb_rental = pd.DataFrame(
            [
                {
                    "town": "TOA PAYOH",
                    "flat_type": "4-ROOM",
                    "monthly_rent": "3500",
                    "rent_approval_date": "2024-01",
                }
            ]
        )

        raw_rental_index = pd.DataFrame(
            [
                {
                    "quarter": "2024-Q1",
                    "locality": "Whole Island",
                    "index": "108.2",
                }
            ]
        )

        result = features.rental_yield(
            hdb_validated, raw_hdb_rental, raw_rental_index, gold_dir=tmp_path / "gold"
        )

        assert isinstance(result, pd.DataFrame)
        assert list(result["town"]) == ["TOA PAYOH"]
        assert result.loc[0, "month"] == "2024-01"
        assert result.loc[0, "median_rent"] == 3500
        assert result.loc[0, "rental_yield_pct"] == pytest.approx((3500 * 12 / 510000) * 100)
        assert result.loc[0, "rental_yield_pct"] != pytest.approx(0.48)

    def test_rental_yield_with_empty_input(self, tmp_path):
        """Test that rental_yield handles empty input."""
        features = _get_features_module()

        hdb_validated = pd.DataFrame()
        raw_hdb_rental = pd.DataFrame()
        raw_rental_index = pd.DataFrame()

        result = features.rental_yield(
            hdb_validated, raw_hdb_rental, raw_rental_index, gold_dir=tmp_path / "gold"
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty


def _empty_poi_args():
    """Return kwargs with empty DataFrames for all POI types."""
    return dict(
        raw_hawker_centres=pd.DataFrame(),
        raw_supermarkets=pd.DataFrame(),
        raw_parks=pd.DataFrame(),
        raw_childcare=pd.DataFrame(),
        raw_kindergartens=pd.DataFrame(),
        raw_bus_stops=pd.DataFrame(),
        raw_chas_clinics=pd.DataFrame(),
        raw_sports_facilities=pd.DataFrame(),
        raw_community_clubs=pd.DataFrame(),
        geocoded_green_mark_buildings=pd.DataFrame(),
    )


class TestLocationDim:
    """Test the location_dim entity dimension table."""

    def test_location_dim_extracts_unique_coords(self, tmp_path, monkeypatch):
        """Test that location_dim deduplicates to unique (lat, lon) pairs."""
        features = _get_features_module()

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "town": "TOA PAYOH",
                    "price": 520000.0,
                    "transaction_date": pd.Timestamp("2024-02-15"),
                },
                {
                    "lat": 1.36,
                    "lon": 103.82,
                    "block": "456",
                    "street_name": "BEDOK NTH RD",
                    "town": "BEDOK",
                    "price": 400000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "compute_proximity_features", lambda props, **kw: props)

        result = features.location_dim(
            geocoded_validated,
            raw_mrt_stations=pd.DataFrame(),
            raw_school_directory=pd.DataFrame(),
            raw_shopping_malls=pd.DataFrame(),
            raw_hdb_property_info=pd.DataFrame(),
            gold_dir=tmp_path / "gold",
            geocoder=InMemoryGeocoder({}),
            **_empty_poi_args(),
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_location_dim_with_empty_input(self, tmp_path):
        """Test that location_dim handles empty geocoded data."""
        features = _get_features_module()

        result = features.location_dim(
            pd.DataFrame(),
            raw_mrt_stations=pd.DataFrame(),
            raw_school_directory=pd.DataFrame(),
            raw_shopping_malls=pd.DataFrame(),
            raw_hdb_property_info=pd.DataFrame(),
            gold_dir=tmp_path / "gold",
            geocoder=InMemoryGeocoder({}),
            **_empty_poi_args(),
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_location_dim_computes_proximity(self, tmp_path, monkeypatch):
        """Test that location_dim calls proximity features."""
        features = _get_features_module()

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "LOR 1",
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        def fake_proximity(props, **kw):
            props["dist_to_nearest_mrt"] = 456.0
            props["nearest_mrt_station"] = "Toa Payoh"
            return props

        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "compute_proximity_features", fake_proximity)

        result = features.location_dim(
            geocoded_validated,
            raw_mrt_stations=_make_mrt_stations(),
            raw_school_directory=pd.DataFrame(),
            raw_shopping_malls=pd.DataFrame(),
            raw_hdb_property_info=pd.DataFrame(),
            gold_dir=tmp_path / "gold",
            geocoder=InMemoryGeocoder({}),
            **_empty_poi_args(),
        )

        assert not result.empty
        assert result.loc[0, "dist_to_nearest_mrt"] == pytest.approx(456.0)
        assert result.loc[0, "nearest_mrt_station"] == "Toa Payoh"

    def test_location_dim_merges_block_metadata(self, tmp_path, monkeypatch):
        """Test that location_dim merges HDB property info."""
        features = _get_features_module()

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        raw_hdb_property_info = pd.DataFrame(
            [
                {
                    "blk_no": "123",
                    "street": "TOA PAYOH LOR 1",
                    "max_floor_lvl": 25,
                    "year_completed": 1990,
                    "total_dwelling_units": 100,
                    "residential": "Y",
                    "commercial": "N",
                    "market_hawker": "N",
                    "multistorey_carpark": "N",
                }
            ]
        )

        monkeypatch.setattr(features, "calculate_school_features", lambda props, schools: props)
        monkeypatch.setattr(features, "compute_proximity_features", lambda props, **kw: props)

        result = features.location_dim(
            geocoded_validated,
            raw_mrt_stations=pd.DataFrame(),
            raw_school_directory=pd.DataFrame(),
            raw_shopping_malls=pd.DataFrame(),
            raw_hdb_property_info=raw_hdb_property_info,
            gold_dir=tmp_path / "gold",
            geocoder=InMemoryGeocoder({}),
            **_empty_poi_args(),
        )

        assert not result.empty
        assert result.loc[0, "year_completed"] == 1990
        assert result.loc[0, "max_floor_lvl"] == 25


class TestTransactionsEnriched:
    """Test the transactions_enriched fact table."""

    def test_transactions_enriched_joins_location_dim(self, tmp_path):
        """Test that transactions_enriched joins location_dim by (lat, lon)."""
        features = _get_features_module()

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "block": "123",
                    "street_name": "LOR 1",
                    "town": "TOA PAYOH",
                    "price": 500000.0,
                    "floor_area_sqft": 1000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                    "remaining_lease_months": 960,
                },
            ]
        )

        location_dim = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "planning_area": "Toa Payoh",
                    "dist_to_nearest_mrt": 300.0,
                    "region": "RCR",
                },
            ]
        )

        result = features.transactions_enriched(
            geocoded_validated,
            location_dim,
            rental_yield=pd.DataFrame(),
            raw_macro_data={},
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            gold_dir=tmp_path / "gold",
        )

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "planning_area" in result.columns
        assert result.loc[0, "planning_area"] == "Toa Payoh"
        assert result.loc[0, "dist_to_nearest_mrt"] == pytest.approx(300.0)
        assert result.loc[0, "psf"] == pytest.approx(500.0)
        assert result.loc[0, "remaining_lease_years"] == pytest.approx(80.0)

    def test_transactions_enriched_with_empty_input(self, tmp_path):
        """Test that transactions_enriched handles empty input."""
        features = _get_features_module()

        result = features.transactions_enriched(
            pd.DataFrame(),
            pd.DataFrame(),
            rental_yield=pd.DataFrame(),
            raw_macro_data={},
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            gold_dir=tmp_path / "gold",
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_transactions_enriched_merges_rental_yield(self, tmp_path):
        """Test that rental yield is merged."""
        features = _get_features_module()

        geocoded_validated = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "price": 500000.0,
                    "property_type": "hdb",
                    "transaction_date": pd.Timestamp("2024-01-15"),
                },
            ]
        )

        rental_yield = pd.DataFrame(
            [
                {"town": "TOA PAYOH", "month": "2024-01", "rental_yield_pct": 4.5},
            ]
        )

        result = features.transactions_enriched(
            geocoded_validated,
            location_dim=pd.DataFrame(),
            rental_yield=rental_yield,
            raw_macro_data={},
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            gold_dir=tmp_path / "gold",
        )

        assert not result.empty
        assert result.loc[0, "rental_yield_pct"] == pytest.approx(4.5)


class TestPlanningArea360:
    """Test the planning_area_360 entity table."""

    def test_basic_produces_expected_columns(self, tmp_path):
        """Test spatial medians and market stats are aggregated correctly."""
        features = _get_features_module()

        location_dim = pd.DataFrame(
            [
                {
                    "lat": 1.35,
                    "lon": 103.8,
                    "planning_area": "Toa Payoh",
                    "region": "RCR",
                    "dist_to_nearest_mrt": 300.0,
                    "dist_to_nearest_mall": 500.0,
                    "year_completed": 1990,
                    "max_floor_lvl": 25,
                    "total_dwelling_units": 100,
                },
            ]
        )
        transactions_enriched = pd.DataFrame(
            [
                {"planning_area": "Toa Payoh", "price": 500000.0, "psf": 500.0},
            ]
        )

        result = features.planning_area_360(
            location_dim,
            transactions_enriched,
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data={},
            gold_dir=tmp_path / "gold",
        )

        assert not result.empty
        assert result.loc[0, "planning_area"] == "Toa Payoh"
        assert "median_dist_to_mrt" in result.columns
        assert result.loc[0, "median_dist_to_mrt"] == pytest.approx(300.0)
        assert "median_price" in result.columns
        assert result.loc[0, "median_price"] == pytest.approx(500000.0)
        assert "avg_year_completed" in result.columns

    def test_empty_input_returns_empty(self, tmp_path):
        features = _get_features_module()
        result = features.planning_area_360(
            pd.DataFrame(),
            pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data={},
            gold_dir=tmp_path / "gold",
        )
        assert result.empty

    def test_missing_planning_area_returns_empty(self, tmp_path):
        features = _get_features_module()
        location_dim = pd.DataFrame([{"lat": 1.35, "lon": 103.8}])
        result = features.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data={},
            gold_dir=tmp_path / "gold",
        )
        assert result.empty

    def test_income_merge(self, tmp_path):
        features = _get_features_module()
        location_dim = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "planning_area": "Toa Payoh", "region": "RCR"}]
        )
        income = pd.DataFrame([{"planning_area": "Toa Payoh", "median_monthly_income": 8000}])
        result = features.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=income,
            raw_macro_data={},
            gold_dir=tmp_path / "gold",
        )
        assert not result.empty
        assert "median_monthly_income" in result.columns
        assert result.loc[0, "median_monthly_income"] == pytest.approx(8000)

    def test_macro_indicators_broadcast_latest(self, tmp_path):
        features = _get_features_module()
        location_dim = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "planning_area": "Toa Payoh", "region": "RCR"}]
        )
        macro = {
            "cpi": pd.DataFrame(
                [
                    {"date": pd.Timestamp("2024-01-01"), "cpi": 104.5},
                    {"date": pd.Timestamp("2024-06-01"), "cpi": 105.0},
                ]
            ),
            "gdp": pd.DataFrame(
                [
                    {"quarter": pd.Timestamp("2024-03-31"), "gdp": 100.0},
                    {"quarter": pd.Timestamp("2024-06-30"), "gdp": 102.0},
                ]
            ),
        }
        result = features.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data=macro,
            gold_dir=tmp_path / "gold",
        )
        assert not result.empty
        assert "cpi" in result.columns
        assert result.loc[0, "cpi"] == pytest.approx(105.0)
        assert "gdp" in result.columns
        assert result.loc[0, "gdp"] == pytest.approx(102.0)

    def test_macro_indicators_broadcast_all_keys(self, tmp_path):
        """All 4 macro keys broadcast their latest values."""
        features = _get_features_module()
        location_dim = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "planning_area": "Toa Payoh", "region": "RCR"}]
        )
        macro = {
            "cpi": pd.DataFrame(
                [
                    {"date": pd.Timestamp("2024-01-01"), "cpi": 104.5},
                    {"date": pd.Timestamp("2024-06-01"), "cpi": 105.0},
                ]
            ),
            "bank_rates": pd.DataFrame(
                [
                    {"date": pd.Timestamp("2024-01-01"), "sora_3m": 3.5},
                    {"date": pd.Timestamp("2024-06-01"), "sora_3m": 3.8},
                ]
            ),
            "unemployment": pd.DataFrame(
                [
                    {"quarter": pd.Timestamp("2024-03-31"), "unemployment_rate": 2.1},
                    {"quarter": pd.Timestamp("2024-06-30"), "unemployment_rate": 2.3},
                ]
            ),
            "gdp": pd.DataFrame(
                [
                    {"quarter": pd.Timestamp("2024-03-31"), "gdp": 100.0},
                    {"quarter": pd.Timestamp("2024-06-30"), "gdp": 102.0},
                ]
            ),
        }
        result = features.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data=macro,
            gold_dir=tmp_path / "gold",
        )
        assert not result.empty
        assert result.loc[0, "cpi"] == pytest.approx(105.0)
        assert result.loc[0, "sora_3m"] == pytest.approx(3.8)
        assert result.loc[0, "unemployment_rate"] == pytest.approx(2.3)
        assert result.loc[0, "gdp"] == pytest.approx(102.0)

    def test_region_present(self, tmp_path):
        features = _get_features_module()
        location_dim = pd.DataFrame(
            [{"lat": 1.35, "lon": 103.8, "planning_area": "Toa Payoh", "region": "RCR"}]
        )
        result = features.planning_area_360(
            location_dim,
            pd.DataFrame(),
            raw_income_by_planning_area=pd.DataFrame(),
            raw_macro_data={},
            gold_dir=tmp_path / "gold",
        )
        assert not result.empty
        assert "region" in result.columns
        assert result.loc[0, "region"] == "RCR"


class TestTown360:
    """Test the town_360 entity table."""

    def test_basic_produces_expected_columns(self, tmp_path):
        features = _get_features_module()
        tx = pd.DataFrame(
            [
                {"town": "TOA PAYOH", "price": 500000.0, "psf": 500.0},
                {"town": "TOA PAYOH", "price": 520000.0, "psf": 520.0},
                {"town": "BEDOK", "price": 400000.0, "psf": 400.0},
            ]
        )
        result = features.town_360(
            tx,
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            gold_dir=tmp_path / "gold",
        )
        assert not result.empty
        assert len(result) == 2
        assert "median_price" in result.columns
        assert "transaction_volume" in result.columns

    def test_annual_value_broadcasts_to_all_rows(self, tmp_path):
        """Phase 1 fix: ALL rows must get the value, not just index[0]."""
        features = _get_features_module()
        tx = pd.DataFrame(
            [
                {"town": "TOA PAYOH", "price": 500000.0},
                {"town": "BEDOK", "price": 400000.0},
                {"town": "ANG MO KIO", "price": 450000.0},
            ]
        )
        mav = pd.DataFrame(
            [
                {
                    "type_of_hdb": "3 Room",
                    "median_annual_value": 5000,
                    "property_tax_collection": 800,
                    "financial_year": 2024,
                },
                {
                    "type_of_hdb": "4 Room",
                    "median_annual_value": 7000,
                    "property_tax_collection": 1200,
                    "financial_year": 2024,
                },
                {
                    "type_of_hdb": "5 Room",
                    "median_annual_value": 9000,
                    "property_tax_collection": 1600,
                    "financial_year": 2024,
                },
            ]
        )
        result = features.town_360(
            tx,
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=mav,
            gold_dir=tmp_path / "gold",
        )
        assert not result.empty
        assert "annual_value_3_room" in result.columns
        assert "annual_value_4_room" in result.columns
        assert "annual_value_5_room" in result.columns
        assert result["annual_value_3_room"].notna().all()
        assert result["annual_value_4_room"].notna().all()
        assert result["annual_value_5_room"].notna().all()
        assert (result["annual_value_3_room"] == 5000).all()
        assert (result["annual_value_4_room"] == 7000).all()
        assert (result["annual_value_5_room"] == 9000).all()
        assert (result["property_tax_3_room"] == 800).all()

    def test_title_case_output(self, tmp_path):
        features = _get_features_module()
        tx = pd.DataFrame([{"town": "TOA PAYOH", "price": 500000.0}])
        result = features.town_360(
            tx,
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            gold_dir=tmp_path / "gold",
        )
        assert result.loc[0, "town"] == "Toa Payoh"

    def test_empty_input_returns_empty(self, tmp_path):
        features = _get_features_module()
        result = features.town_360(
            pd.DataFrame(),
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            gold_dir=tmp_path / "gold",
        )
        assert result.empty

    def test_missing_town_column_returns_empty(self, tmp_path):
        features = _get_features_module()
        tx = pd.DataFrame([{"price": 500000.0}])
        result = features.town_360(
            tx,
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            gold_dir=tmp_path / "gold",
        )
        assert result.empty

    def test_no_annual_value_source_creates_na_columns(self, tmp_path):
        """When raw_median_annual_value is empty, per-flat-type columns default to NA."""
        features = _get_features_module()
        tx = pd.DataFrame([{"town": "TOA PAYOH", "price": 500000.0}])
        result = features.town_360(
            tx,
            raw_dwelling_units_by_town=pd.DataFrame(),
            raw_hdb_resident_population=pd.DataFrame(),
            raw_median_annual_value=pd.DataFrame(),
            gold_dir=tmp_path / "gold",
        )
        assert not result.empty
        for col in (
            "annual_value_3_room",
            "annual_value_4_room",
            "annual_value_5_room",
            "property_tax_3_room",
            "property_tax_4_room",
            "property_tax_5_room",
        ):
            assert col in result.columns
            assert result[col].isna().all()


class TestBlockProfile:
    """Test the block_profile entity table."""

    def test_basic_aggregates_by_block_street(self, tmp_path):
        features = _get_features_module()
        tx = pd.DataFrame(
            [
                {
                    "block": "123",
                    "street_name": "LOR 1",
                    "price": 500000.0,
                    "psf": 500.0,
                    "remaining_lease_years": 80.0,
                    "town": "TOA PAYOH",
                },
                {
                    "block": "123",
                    "street_name": "LOR 1",
                    "price": 520000.0,
                    "psf": 520.0,
                    "remaining_lease_years": 80.0,
                    "town": "TOA PAYOH",
                },
                {
                    "block": "456",
                    "street_name": "NTH RD",
                    "price": 400000.0,
                    "psf": 400.0,
                    "remaining_lease_years": 70.0,
                    "town": "BEDOK",
                },
            ]
        )
        result = features.block_profile(tx, gold_dir=tmp_path / "gold")
        assert not result.empty
        assert len(result) == 2
        assert "median_price" in result.columns
        assert "transaction_count" in result.columns
        assert "median_psf" in result.columns
        assert "avg_remaining_lease_years" in result.columns

    def test_missing_block_column_returns_empty(self, tmp_path):
        features = _get_features_module()
        tx = pd.DataFrame([{"price": 500000.0}])
        result = features.block_profile(tx, gold_dir=tmp_path / "gold")
        assert result.empty

    def test_empty_input_returns_empty(self, tmp_path):
        features = _get_features_module()
        result = features.block_profile(pd.DataFrame(), gold_dir=tmp_path / "gold")
        assert result.empty
