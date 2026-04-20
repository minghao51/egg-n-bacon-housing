"""Tests for scripts.core.stages.L2_features."""

import numpy as np
import pandas as pd

from scripts.core.stages.L2_features import (
    create_nearby_facilities,
    create_private_facilities,
    create_property_table,
    create_transaction_sales,
    extract_lease_info,
    extract_two_digits,
    prepare_unique_properties,
    process_hdb_transactions,
    process_private_transactions,
)


class TestExtractLeaseInfo:
    def test_99_year_lease(self):
        year, hold_type = extract_lease_info("99 yrs lease commencing from 2007")
        assert year == 2007
        assert hold_type == "leasehold"

    def test_freehold(self):
        year, hold_type = extract_lease_info("Freehold")
        assert year is None
        assert hold_type == "freehold"

    def test_999_year_lease(self):
        year, hold_type = extract_lease_info("999 yrs lease commencing from 1950")
        assert year == 1950
        assert hold_type == "leasehold"


class TestExtractTwoDigits:
    def test_standard_range(self):
        low, high = extract_two_digits("01 to 05")
        assert low == "01"
        assert high == "05"

    def test_higher_range(self):
        low, high = extract_two_digits("10 to 15")
        assert low == "10"
        assert high == "15"


class TestPrepareUniqueProperties:
    def test_filters_search_result_zero(self):
        df = pd.DataFrame(
            {
                "search_result": [0, 1, 0, 2],
                "LATITUDE": [1.3, 1.4, 1.5, 1.6],
                "LONGITUDE": [103.8, 103.9, 104.0, 104.1],
            }
        )
        result = prepare_unique_properties(df)
        assert len(result) == 2
        assert "lat" in result.columns
        assert "lon" in result.columns

    def test_renames_coordinates(self):
        df = pd.DataFrame({"search_result": [0], "LATITUDE": [1.35], "LONGITUDE": [103.82]})
        result = prepare_unique_properties(df)
        assert result["lat"].iloc[0] == 1.35
        assert result["lon"].iloc[0] == 103.82


class TestProcessHDBTransactions:
    def test_basic_processing(self):
        df = pd.DataFrame(
            {
                "block": ["123", "456"],
                "street_name": ["Bishan St 12", "Toa Payoh St 1"],
                "month": ["2023-01", "2023-02"],
                "floor_area_sqm": [90, 100],
                "resale_price": [500000, 600000],
                "storey_range": ["01 to 05", "06 to 10"],
                "flat_type": ["4 Room", "5 Room"],
                "remaining_lease_months": [900, 950],
                "lease_commence_date": [1990, 1995],
                "flat_model": ["Model A", "Model A"],
                "town": ["Bishan", "Toa Payoh"],
            }
        )
        result = process_hdb_transactions(df)
        assert "property_index" in result.columns
        assert "property_type" in result.columns
        assert result["property_type"].iloc[0] == "HDB"
        assert "area_sqft" in result.columns
        assert "unitprice_psf" in result.columns

    def test_creates_property_index(self):
        df = pd.DataFrame(
            {
                "block": ["123"],
                "street_name": ["Bishan St 12"],
                "month": ["2023-01"],
                "floor_area_sqm": [90],
                "resale_price": [500000],
                "storey_range": ["01 to 05"],
                "flat_type": ["4 Room"],
                "remaining_lease_months": [900],
                "lease_commence_date": [1990],
                "flat_model": ["Model A"],
                "town": ["Bishan"],
            }
        )
        result = process_hdb_transactions(df)
        assert result["property_index"].iloc[0] == "123 BISHAN ST 12"


class TestProcessPrivateTransactions:
    def test_basic_processing(self):
        condo_df = pd.DataFrame(
            {
                "projectname": ["Skyline"],
                "saledate": ["Jan-23"],
                "transactedprice": ["1,000,000"],
                "unitprice_psf": ["1,000"],
                "unitprice_psm": ["10,000"],
                "area_sqft": ["1000"],
                "tenure": ["99 yrs lease commencing from 2020"],
                "propertytype": ["Condominium"],
                "nettprice": ["1,000,000"],
                "numberofunits": ["1"],
                "typeofarea": ["Strata"],
                "typeofsale": ["New Sale"],
                "floorlevel": ["01 to 05"],
                "streetname": ["Orchard Road"],
                "marketsegment": ["CCR"],
                "postaldistrict": ["01"],
                "area_sqm": [92.9],
            }
        )
        ec_df = pd.DataFrame()
        result = process_private_transactions(condo_df, ec_df)
        assert len(result) == 1
        assert "property_type" in result.columns
        assert result["property_type"].iloc[0] == "Private"


class TestCreateTransactionSales:
    def test_combines_dataframes(self):
        hdb = pd.DataFrame({"resale_price": [500000], "property_type": ["HDB"]})
        private = pd.DataFrame({"resale_price": [1000000], "property_type": ["Private"]})
        result = create_transaction_sales(hdb, private)
        assert len(result) == 2


class TestCreatePropertyTable:
    def test_creates_table(self):
        from geopandas import GeoDataFrame
        from shapely.geometry import Point

        gdf = GeoDataFrame(
            {
                "nameaddress": ["123 BISHAN ST 12"],
                "BLK_NO": ["123"],
                "ROAD_NAME": ["BISHAN ST 12"],
                "BUILDING": ["BLOCK 123"],
                "ADDRESS": ["123 BISHAN ST 12 SINGAPORE"],
                "POSTAL": ["570123"],
                "planning_area": ["Bishan"],
                "property_type": ["HDB"],
                "geometry": [Point(103.82, 1.35)],
            },
            crs="EPSG:4326",
        )
        result = create_property_table(gdf)
        assert "property_id" in result.columns
        assert len(result) == 1


class TestCreatePrivateFacilities:
    def test_creates_facilities(self):
        property_df = pd.DataFrame(
            {
                "property_id": ["prop_1", "prop_2", "prop_3"],
                "property_type": ["Private", "Private", "HDB"],
            }
        )
        result = create_private_facilities(property_df)
        assert len(result) > 0
        assert "facilities" in result.columns
        assert "property_id" in result.columns


class TestCreateNearbyFacilities:
    def test_creates_table(self):
        joined = pd.DataFrame(
            {
                "searchval": ["123 bishan st 12", "123 bishan st 12"],
                "type": ["mrt_station", "supermarket"],
                "name": ["Bishan MRT", "NTUC"],
                "distance": [150.5, 200.3],
            }
        )
        result = create_nearby_facilities(joined)
        assert "property_index" in result.columns
        assert "distance_m" in result.columns
        assert result["distance_m"].dtype == np.int32
