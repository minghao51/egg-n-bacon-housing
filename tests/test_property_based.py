"""Property-based tests using hypothesis."""

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from egg_n_bacon_housing.utils.geo import haversine_distance

pytestmark = pytest.mark.unit


sg_lat = st.floats(min_value=1.2, max_value=1.5, allow_nan=False, allow_infinity=False)
sg_lon = st.floats(min_value=103.6, max_value=104.1, allow_nan=False, allow_infinity=False)
valid_lat = st.floats(min_value=-90.0, max_value=90.0, allow_nan=False, allow_infinity=False)
valid_lon = st.floats(min_value=-180.0, max_value=180.0, allow_nan=False, allow_infinity=False)
positive_price = st.floats(
    min_value=1.0, max_value=100_000_000.0, allow_nan=False, allow_infinity=False
)
positive_area = st.floats(min_value=1.0, max_value=100_000.0, allow_nan=False, allow_infinity=False)


class TestHaversineProperties:
    @given(lat=valid_lat, lon=valid_lon)
    @settings(max_examples=50)
    def test_identity_distance(self, lat, lon):
        assert haversine_distance(lat, lon, lat, lon) == pytest.approx(0.0, abs=1.0)

    @given(lat1=valid_lat, lon1=valid_lon, lat2=valid_lat, lon2=valid_lon)
    @settings(max_examples=50)
    def test_symmetry(self, lat1, lon1, lat2, lon2):
        assert haversine_distance(lat1, lon1, lat2, lon2) == pytest.approx(
            haversine_distance(lat2, lon2, lat1, lon1), abs=0.1
        )

    @given(lat1=sg_lat, lon1=sg_lon, lat2=sg_lat, lon2=sg_lon)
    @settings(max_examples=50)
    def test_non_negative(self, lat1, lon1, lat2, lon2):
        assert haversine_distance(lat1, lon1, lat2, lon2) >= 0.0

    @given(
        lat1=sg_lat,
        lon1=sg_lon,
        lat2=sg_lat,
        lon2=sg_lon,
        lat3=sg_lat,
        lon3=sg_lon,
    )
    @settings(max_examples=30)
    def test_triangle_inequality(self, lat1, lon1, lat2, lon2, lat3, lon3):
        d12 = haversine_distance(lat1, lon1, lat2, lon2)
        d13 = haversine_distance(lat1, lon1, lat3, lon3)
        d23 = haversine_distance(lat2, lon2, lat3, lon3)
        assert d12 <= d13 + d23 + 1.0


class TestValidationPreservesColumns:
    @given(
        price=positive_price,
        lat=valid_lat,
        lon=valid_lon,
        property_type=st.sampled_from(["hdb", "condo"]),
    )
    @settings(max_examples=20)
    def test_validate_schema_preserves_extra_columns(self, price, lat, lon, property_type):
        from egg_n_bacon_housing.schemas.clean_models import HCleanTransactionBase
        from egg_n_bacon_housing.utils.validation import validate_schema

        df = pd.DataFrame(
            [
                {
                    "transaction_date": "2024-01-15",
                    "price": price,
                    "lat": lat,
                    "lon": lon,
                    "property_type": property_type,
                    "enriched_col": "should_survive",
                    "another_extra": 42,
                }
            ]
        )

        valid_df, quarantine_df = validate_schema(df, HCleanTransactionBase, "test")

        assert not valid_df.empty
        assert "enriched_col" in valid_df.columns
        assert "another_extra" in valid_df.columns
        assert valid_df.iloc[0]["enriched_col"] == "should_survive"


class TestSchemaRoundTrip:
    @given(
        price=positive_price,
        lat=valid_lat,
        lon=valid_lon,
        property_type=st.sampled_from(["hdb", "condo", "ec"]),
    )
    @settings(max_examples=30)
    def test_geocoded_property_round_trip(self, price, lat, lon, property_type):
        from egg_n_bacon_housing.schemas.clean_models import GeocodedProperty

        original = GeocodedProperty(
            address="123 Test St",
            lat=lat,
            lon=lon,
            property_type=property_type,
            postal_code="123456",
            search_confidence=0.9,
        )

        as_dict = original.model_dump()
        reconstructed = GeocodedProperty(**as_dict)

        assert reconstructed.lat == pytest.approx(lat)
        assert reconstructed.lon == pytest.approx(lon)
        assert reconstructed.property_type == property_type

    @given(
        price=positive_price,
        floor_area_sqft=positive_area,
        floor_area_sqm=positive_area,
        town=st.sampled_from(["TOA PAYOH", "ANG MO KIO", "BISHAN", "YISHUN"]),
        flat_type=st.sampled_from(["3 ROOM", "4 ROOM", "5 ROOM"]),
    )
    @settings(max_examples=30)
    def test_hdb_transaction_round_trip_through_dataframe(
        self, price, floor_area_sqft, floor_area_sqm, town, flat_type
    ):
        from egg_n_bacon_housing.schemas.clean_models import HCleanHDBTransaction

        original = HCleanHDBTransaction(
            transaction_date="2024-01-15",
            price=price,
            lat=1.35,
            lon=103.82,
            property_type="hdb",
            planning_area="Toa Payoh",
            town=town,
            flat_type=flat_type,
            block="123",
            street_name="TEST ST",
            floor_area_sqm=floor_area_sqm,
            floor_area_sqft=floor_area_sqft,
        )

        as_dict = original.model_dump()
        df = pd.DataFrame([as_dict])
        records = df.to_dict(orient="records")
        reconstructed = HCleanHDBTransaction(**records[0])

        assert reconstructed.price == pytest.approx(price)
        assert reconstructed.town == town
        assert reconstructed.flat_type == flat_type

    @given(price=st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False))
    @settings(max_examples=20)
    def test_negative_price_rejected_by_schema(self, price):
        from egg_n_bacon_housing.schemas.clean_models import HCleanHDBTransaction

        with pytest.raises(ValidationError):
            HCleanHDBTransaction(
                transaction_date="2024-01-15",
                price=price,
                lat=1.35,
                lon=103.82,
                property_type="hdb",
                town="TOA PAYOH",
                flat_type="4 ROOM",
                block="123",
                street_name="TEST ST",
                floor_area_sqm=90.0,
                floor_area_sqft=969.0,
            )
