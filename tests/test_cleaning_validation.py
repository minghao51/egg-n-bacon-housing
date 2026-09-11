"""Test schema validation in 02_cleaning.py."""

import logging

import pandas as pd
import pytest

from egg_n_bacon_housing.utils.geocoding import InMemoryGeocoder
from egg_n_bacon_housing.utils.layer_writer import PUBLISHED_LAYERS, SimpleWriter

pytestmark = pytest.mark.unit


def _get_cleaning_module():
    """Get the 02_cleaning module."""
    from egg_n_bacon_housing.components import cleaning

    return cleaning


class TestHDBValidation:
    """Test HDB transaction validation."""

    def test_hdb_validated_with_valid_data(self, tmp_path):
        """Test that valid HDB transactions pass validation."""
        cleaning = _get_cleaning_module()

        valid_data = pd.DataFrame(
            [
                {
                    "transaction_date": pd.Timestamp("2023-01-01"),
                    "price": 500000.0,
                    "lat": 1.35,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "planning_area": "Toa Payoh",
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "storey_min": 4,
                    "storey_max": 6,
                    "floor_area_sqm": 90.0,
                    "floor_area_sqft": 969.0,
                    "remaining_lease_months": 960,
                    "address": "123 TOA PAYOH LOR 1",
                },
            ]
        )

        result = cleaning.hdb_validated(valid_data)

        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["price"] == 500000.0
        assert not list(tmp_path.rglob("*.parquet"))

    def test_hdb_validated_with_invalid_price(self, tmp_path):
        """Test that transactions with invalid price fail validation."""
        cleaning = _get_cleaning_module()

        invalid_data = pd.DataFrame(
            [
                {
                    "transaction_date": pd.Timestamp("2023-01-01"),
                    "price": -100.0,
                    "lat": 1.35,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "planning_area": "Toa Payoh",
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "storey_min": 4,
                    "storey_max": 6,
                    "floor_area_sqm": 90.0,
                    "floor_area_sqft": 969.0,
                    "remaining_lease_months": 960,
                    "address": "123 TOA PAYOH LOR 1",
                },
            ]
        )

        result = cleaning.hdb_validated(invalid_data)

        assert result.empty

    def test_hdb_validated_with_empty_dataframe(self):
        """Test that empty DataFrame is handled correctly."""
        cleaning = _get_cleaning_module()

        result = cleaning.hdb_validated(pd.DataFrame())

        assert result.empty

    def test_cleaned_hdb_transactions_fills_remaining_lease_in_months(self, tmp_path):
        """Test missing remaining_lease_months is backfilled in months, not years."""
        cleaning = _get_cleaning_module()

        raw_data = pd.DataFrame(
            [
                {
                    "month": "2024-01",
                    "resale_price": 500000.0,
                    "lease_commence_date": 2000,
                    "remaining_lease_months": pd.NA,
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "floor_area_sqm": 90.0,
                }
            ]
        )

        result = cleaning.cleaned_hdb_transactions(raw_data)

        assert not result.empty
        assert result.loc[0, "remaining_lease_months"] == 900

    def test_cleaned_hdb_transactions_requires_month_column(self, tmp_path):
        cleaning = _get_cleaning_module()
        with pytest.raises(ValueError, match="missing required columns"):
            cleaning.cleaned_hdb_transactions(pd.DataFrame([{"resale_price": 500000.0}]))

    def test_cleaned_hdb_requires_floor_area_sqm(self, tmp_path):
        """Losing floor_area_sqm must fail loudly, not degrade psf to all-NaN."""
        cleaning = _get_cleaning_module()
        raw_data = pd.DataFrame(
            [
                {
                    "month": "2024-01",
                    "resale_price": 500000.0,
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                }
            ]
        )

        with pytest.raises(ValueError, match="floor_area_sqm"):
            cleaning.cleaned_hdb_transactions(raw_data)

    def test_cleaned_hdb_dropped_row_counts_logged(self, tmp_path, caplog):
        """Silent filters announce their dropped-row counts."""
        cleaning = _get_cleaning_module()

        def valid_row(i: int) -> dict:
            return {
                "month": "2024-01",
                "resale_price": 500000.0 + i,
                "town": "TOA PAYOH",
                "flat_type": "4 ROOM",
                "floor_area_sqm": 90.0,
            }

        raw_data = pd.DataFrame(
            [
                valid_row(0),
                {**valid_row(1), "resale_price": pd.NA},  # null price
                {**valid_row(2), "month": "not-a-month"},  # unparseable date
                {**valid_row(3), "resale_price": -5.0},  # non-positive price
            ]
        )

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.components.cleaning"):
            result = cleaning.cleaned_hdb_transactions(raw_data)

        assert len(result) == 1
        messages = [record.getMessage() for record in caplog.records]
        assert any(
            "cleaned_hdb_transactions: dropped 2 row(s) with null price/transaction_date" in m
            for m in messages
        )
        assert any(
            "cleaned_hdb_transactions: dropped 1 row(s) with non-positive price" in m
            for m in messages
        )

    def test_cleaned_condo_dropped_row_counts_logged(self, tmp_path, caplog):
        cleaning = _get_cleaning_module()
        raw_data = pd.DataFrame(
            [
                {"price": 1_500_000, "transaction_date": "2024-01-15", "street_name": "A"},
                {"price": pd.NA, "transaction_date": "2024-01-15", "street_name": "B"},
                {"price": 0, "transaction_date": "2024-01-15", "street_name": "C"},
            ]
        )

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.components.cleaning"):
            result = cleaning.cleaned_condo_transactions(raw_data)

        assert len(result) == 1
        messages = [record.getMessage() for record in caplog.records]
        assert any(
            "cleaned_condo_transactions: dropped 1 row(s) with null price/transaction_date" in m
            for m in messages
        )
        assert any(
            "cleaned_condo_transactions: dropped 1 row(s) with non-positive price" in m
            for m in messages
        )

    def test_cleaned_hdb_transactions_derives_storey_and_address(self, tmp_path):
        cleaning = _get_cleaning_module()
        raw_data = pd.DataFrame(
            [
                {
                    "month": "2024-01",
                    "resale_price": 500000.0,
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "floor_area_sqm": 90.0,
                    "storey_range": "04 TO 06",
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                }
            ]
        )

        result = cleaning.cleaned_hdb_transactions(raw_data)

        assert result.loc[0, "storey_min"] == 4
        assert result.loc[0, "storey_max"] == 6
        assert result.loc[0, "address"] == "123 TOA PAYOH LOR 1"

    def test_cleaned_hdb_sqft_uses_unified_constant(self):
        """HDB sqft derives via SQFT_PER_SQM (10.7639), not the legacy 10.764."""
        from egg_n_bacon_housing.utils.hdb_lookups import SQFT_PER_SQM

        cleaning = _get_cleaning_module()
        raw_data = pd.DataFrame(
            [
                {
                    "month": "2024-01",
                    "resale_price": 500000.0,
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "floor_area_sqm": 90.0,
                }
            ]
        )

        result = cleaning.cleaned_hdb_transactions(raw_data)

        assert result.loc[0, "floor_area_sqft"] == pytest.approx(90.0 * SQFT_PER_SQM)
        assert result.loc[0, "floor_area_sqft"] == pytest.approx(968.751)


class TestCondoValidation:
    """Test condo transaction validation."""

    def test_condo_validated_with_valid_data(self, tmp_path):
        """Test that valid condo transactions pass validation."""
        cleaning = _get_cleaning_module()

        valid_data = pd.DataFrame(
            [
                {
                    "transaction_date": pd.Timestamp("2023-01-01"),
                    "price": 1500000.0,
                    "lat": 1.30,
                    "lon": 103.8,
                    "property_type": "condo",
                    "planning_area": "Orchard",
                    "project_name": "Orchard Residences",
                    "area": "Central",
                    "postal_district": 9,
                    "tenure": "Freehold",
                    "floor_area_sqm": 120.0,
                    "floor_area_sqft": 1292.0,
                    "address": "1 ORCHARD ROAD",
                },
            ]
        )

        result = cleaning.condo_validated(valid_data)

        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["price"] == 1500000.0
        assert not list(tmp_path.rglob("*.parquet"))

    def test_cleaned_condo_transactions_requires_price_column(self, tmp_path):
        cleaning = _get_cleaning_module()
        with pytest.raises(ValueError, match="missing required columns"):
            cleaning.cleaned_condo_transactions(
                pd.DataFrame([{"transaction_date": "2023-01-01", "street_name": "ORCHARD ROAD"}])
            )

    def test_cleaned_condo_transactions_requires_transaction_date_column(self, tmp_path):
        """Bronze contract guarantees transaction_date — losing it fails loudly."""
        cleaning = _get_cleaning_module()
        with pytest.raises(ValueError, match="transaction_date"):
            cleaning.cleaned_condo_transactions(
                pd.DataFrame([{"price": 1_500_000.0, "street_name": "ORCHARD ROAD"}])
            )

    def test_cleaned_condo_transactions_requires_street_name_column(self, tmp_path):
        """street_name is the condo geocode substrate — empty addresses fail loudly."""
        cleaning = _get_cleaning_module()
        with pytest.raises(ValueError, match="street_name"):
            cleaning.cleaned_condo_transactions(
                pd.DataFrame([{"price": 1_500_000.0, "transaction_date": "2023-01-01"}])
            )

    def test_cleaned_condo_transactions_fills_defaults_and_normalizes_types(self, tmp_path):
        cleaning = _get_cleaning_module()
        raw_data = pd.DataFrame(
            [
                {
                    "price": "1500000",
                    "transaction_date": "2024-01-15",
                    "area_sqft": "1292",
                    "area_sqm": "120",
                    "postal_district": "9",
                    "street_name": "ORCHARD ROAD",
                }
            ]
        )

        result = cleaning.cleaned_condo_transactions(raw_data)

        assert result.loc[0, "price"] == pytest.approx(1500000.0)
        assert result.loc[0, "floor_area_sqft"] == pytest.approx(1292.0)
        assert result.loc[0, "floor_area_sqm"] == pytest.approx(120.0)
        assert result.loc[0, "postal_district"] == 9
        assert result.loc[0, "address"] == "ORCHARD ROAD"
        assert result.loc[0, "area"] == ""
        assert result.loc[0, "project_name"] == ""

    def test_cleaned_condo_transactions_derives_month_for_schema_parity(self, tmp_path):
        """Condo rows must carry "month" like HDB rows — monthly joins key on it."""
        cleaning = _get_cleaning_module()
        raw_data = pd.DataFrame(
            [
                {"price": "1500000", "transaction_date": "2024-01-15", "street_name": "A"},
                {"price": "950000", "transaction_date": "2023-12-01", "street_name": "B"},
            ]
        )

        result = cleaning.cleaned_condo_transactions(raw_data)

        assert result.loc[0, "month"] == "2024-01"
        assert result.loc[1, "month"] == "2023-12"

    @pytest.mark.parametrize(
        ("subtype", "segment", "is_ec"),
        [
            ("Condominium", "condominium", False),
            ("Apartment", "apartment", False),
            ("Executive Condominium", "ec", True),
            ("Terrace House", "terrace_house", False),
            (None, "private_residential_unspecified", False),
        ],
    )
    def test_cleaned_condo_transactions_derives_analytical_segment(self, subtype, segment, is_ec):
        cleaning = _get_cleaning_module()
        raw_data = pd.DataFrame(
            [
                {
                    "price": 1_500_000,
                    "transaction_date": "2024-01-15",
                    "street_name": "ORCHARD ROAD",
                    "property_subtype": subtype,
                }
            ]
        )

        result = cleaning.cleaned_condo_transactions(raw_data)

        assert result.loc[0, "property_segment"] == segment
        assert bool(result.loc[0, "is_ec"]) is is_ec

    def test_geocoded_properties_marks_hdb_segment(self):
        cleaning = _get_cleaning_module()
        hdb = pd.DataFrame([{"address": "1 TEST ROAD", "price": 500_000}])

        result = cleaning.geocoded_properties(
            hdb,
            pd.DataFrame(),
            geocoder=InMemoryGeocoder({"1 TEST ROAD": (1.3, 103.8)}),
        )

        assert result.loc[0, "property_segment"] == "hdb"
        assert not bool(result.loc[0, "is_ec"])


class TestGeocodedValidation:
    """Test geocoded property validation."""

    def test_geocoded_validated_with_valid_data(self, tmp_path):
        """Test that valid geocoded properties pass validation."""
        cleaning = _get_cleaning_module()

        valid_data = pd.DataFrame(
            [
                {
                    "address": "123 TOA PAYOH LOR 1",
                    "lat": 1.35,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "postal_code": "312345",
                },
            ]
        )

        result = cleaning.geocoded_validated(valid_data)

        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["lat"] == 1.35
        assert not list(tmp_path.rglob("*.parquet"))

    def test_geocoded_validated_with_invalid_coordinates(self, tmp_path):
        """Test that invalid coordinates fail validation."""
        cleaning = _get_cleaning_module()

        invalid_data = pd.DataFrame(
            [
                {
                    "address": "123 TOA PAYOH LOR 1",
                    "lat": 91.0,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "postal_code": "312345",
                },
            ]
        )

        result = cleaning.geocoded_validated(invalid_data)

        assert result.empty

    def test_geocoded_properties_fills_na_when_coordinate_columns_missing(self, tmp_path):
        """Test geocoded_properties fills lat/lon with NA when columns missing."""
        cleaning = _get_cleaning_module()

        hdb_validated = pd.DataFrame([{"town": "TOA PAYOH", "price": 500000.0}])
        condo_validated = pd.DataFrame()

        result = cleaning.geocoded_properties(
            hdb_validated,
            condo_validated,
            geocoder=InMemoryGeocoder({}),
        )

        assert not result.empty
        assert "lat" in result.columns
        assert "lon" in result.columns
        assert pd.isna(result.loc[0, "lat"])

    def test_geocoded_properties_warns_on_low_coordinate_coverage(self, tmp_path):
        """Test geocoded_properties logs warning when coverage is low."""
        cleaning = _get_cleaning_module()

        hdb_validated = pd.DataFrame(
            [
                {"town": "TOA PAYOH", "price": 500000.0, "lat": 1.35, "lon": 103.8},
                {"town": "ANG MO KIO", "price": 600000.0, "lat": pd.NA, "lon": 103.84},
            ]
        )
        condo_validated = pd.DataFrame()

        result = cleaning.geocoded_properties(
            hdb_validated,
            condo_validated,
            geocoder=InMemoryGeocoder({}),
            min_coordinate_coverage=0.8,
            coordinate_coverage_policy="warn",
        )

        assert not result.empty
        assert len(result) == 2

    def test_geocoded_properties_fails_on_low_coordinate_coverage(self):
        cleaning = _get_cleaning_module()
        hdb_validated = pd.DataFrame(
            [{"address": "UNKNOWN", "town": "TOA PAYOH", "price": 500000.0}]
        )

        with pytest.raises(ValueError, match="Geocoding coverage"):
            cleaning.geocoded_properties(
                hdb_validated,
                pd.DataFrame(),
                geocoder=InMemoryGeocoder({}),
                min_coordinate_coverage=0.8,
            )

    def test_geocoded_properties_reruns_geocoding_not_stale_parquet(self, tmp_path):
        """Re-ingestion must re-geocode via the geocoder, not return a stale silver parquet.

        Regression: a non-null cached parquet previously short-circuited the
        node, so new transactions added on re-ingestion were never geocoded
        until the parquet was manually deleted. The geocoder's own address
        cache is what makes repeat runs cheap; the silver parquet is now a
        pure output snapshot.
        """
        cleaning = _get_cleaning_module()

        stale = pd.DataFrame([{"address": "OLD ADDRESS", "lat": 1.1, "lon": 103.1}])
        stale.to_parquet(tmp_path / "geocoded_properties.parquet", index=False)

        hdb_validated = pd.DataFrame([{"address": "NEW ADDRESS", "price": 500000.0}])

        result = cleaning.geocoded_properties(
            hdb_validated,
            pd.DataFrame(),
            geocoder=InMemoryGeocoder({"NEW ADDRESS": (1.4, 103.9)}),
        )

        assert "NEW ADDRESS" in set(result["address"])
        assert "OLD ADDRESS" not in set(result["address"])
        assert result.loc[result.index[0], "lat"] == 1.4
        assert result.loc[result.index[0], "lon"] == 103.9


class TestPerTypeGeocodeCoverage:
    """WS16: per-property-type geocoding coverage gates (HDB strict, condo lenient)."""

    HDB_ROWS = 20
    HDB_GEOCODED = 19  # 0.95 coverage — passes the strict 0.7 HDB gate
    CONDO_ROWS = 10
    CONDO_GEOCODED = 2  # 0.2 coverage — fails the lenient 0.3 condo gate

    def _frames(self):
        """HDB frame at 95% coverage + condo frame at 20% coverage."""
        cleaning = _get_cleaning_module()
        hdb_addresses = [f"HDB BLOCK {i} STREET" for i in range(self.HDB_ROWS)]
        condo_addresses = [f"CONDO STREET {i}" for i in range(self.CONDO_ROWS)]
        hdb = pd.DataFrame({"address": hdb_addresses, "price": 500_000.0})
        condo = pd.DataFrame({"address": condo_addresses, "price": 1_500_000.0})
        lookup = {
            addr: (1.3 + i / 1000, 103.8 + i / 1000)
            for i, addr in enumerate(hdb_addresses[: self.HDB_GEOCODED])
        }
        lookup.update(
            {
                addr: (1.1 + i / 1000, 103.9 + i / 1000)
                for i, addr in enumerate(condo_addresses[: self.CONDO_GEOCODED])
            }
        )
        return cleaning, hdb, condo, InMemoryGeocoder(lookup)

    def test_fail_policy_names_failing_condo_segment(self):
        cleaning, hdb, condo, geocoder = self._frames()

        with pytest.raises(ValueError) as excinfo:
            cleaning.geocoded_properties(hdb, condo, geocoder=geocoder)

        message = str(excinfo.value)
        assert "condo 20.0% < threshold 30.0%" in message
        assert "Geocoding coverage 70.0%" in message  # aggregate included
        assert "hdb" not in message  # hdb passes its strict gate

    def test_warn_policy_warns_per_failing_segment(self, caplog):
        cleaning, hdb, condo, geocoder = self._frames()

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.components.cleaning"):
            result = cleaning.geocoded_properties(
                hdb, condo, geocoder=geocoder, coordinate_coverage_policy="warn"
            )

        assert len(result) == self.HDB_ROWS + self.CONDO_ROWS
        warnings = [
            record.getMessage()
            for record in caplog.records
            if "proceeding under warn policy" in record.getMessage()
        ]
        assert len(warnings) == 1  # only the failing condo segment warns
        assert "condo" in warnings[0]
        assert "20.0%" in warnings[0] and "30.0%" in warnings[0]
        assert "70.0%" in warnings[0]  # aggregate coverage in the log line
        assert "hdb" not in warnings[0]

    def test_condo_lenient_default_lets_moderate_coverage_pass(self):
        """All-condo frame at 50% coverage passes the 0.3 default (old gate was 0.7)."""
        cleaning = _get_cleaning_module()
        condo_addresses = [f"CONDO STREET {i}" for i in range(10)]
        condo = pd.DataFrame({"address": condo_addresses, "price": 1_500_000.0})
        geocoder = InMemoryGeocoder(
            {addr: (1.1, 103.9) for addr in condo_addresses[:5]}  # 50% coverage
        )

        result = cleaning.geocoded_properties(pd.DataFrame(), condo, geocoder=geocoder)

        assert len(result) == 10

    def test_unknown_property_type_uses_legacy_threshold(self):
        """Segments without a dedicated gate fall back to min_coordinate_coverage."""
        cleaning = _get_cleaning_module()
        combined = pd.DataFrame(
            {
                "property_type": ["executive_condominium"] * 4,
                "lat": [1.3, 1.3, pd.NA, pd.NA],
                "lon": [103.8, 103.8, pd.NA, pd.NA],
            }
        )

        segments = cleaning._per_type_coverage(
            combined,
            min_coordinate_coverage=0.5,
            min_coordinate_coverage_hdb=0.7,
            min_coordinate_coverage_condo=0.3,
        )

        assert len(segments) == 1
        assert segments[0].segment == "executive_condominium"
        assert segments[0].threshold == 0.5  # legacy field, not hdb/condo gates
        assert segments[0].coverage == pytest.approx(0.5)
        assert segments[0].rows == 4


class TestQuarantineIntegration:
    """Migrated silver nodes warn on quarantined rows and write nothing themselves.

    Since the materializer migration the gateway runs with persist=False:
    quarantine files are no longer produced by the nodes — persistence (for
    valid rows only) is owned by the companion materializers.
    """

    def test_hdb_invalid_rows_warned_not_persisted(self, tmp_path, caplog):
        cleaning = _get_cleaning_module()

        mixed_data = pd.DataFrame(
            [
                {
                    "transaction_date": pd.Timestamp("2023-01-01"),
                    "price": 500000.0,
                    "lat": 1.35,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "planning_area": "Toa Payoh",
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "storey_min": 4,
                    "storey_max": 6,
                    "floor_area_sqm": 90.0,
                    "floor_area_sqft": 969.0,
                    "remaining_lease_months": 960,
                    "address": "123 TOA PAYOH LOR 1",
                },
                {
                    "transaction_date": pd.Timestamp("2023-01-01"),
                    "price": -100.0,
                    "lat": 1.35,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "planning_area": "Toa Payoh",
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "block": "456",
                    "street_name": "ANG MO KIO AVE 1",
                    "storey_min": 4,
                    "storey_max": 6,
                    "floor_area_sqm": 90.0,
                    "floor_area_sqft": 969.0,
                    "remaining_lease_months": 960,
                    "address": "456 ANG MO KIO AVE 1",
                },
            ]
        )

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.components.cleaning"):
            result = cleaning.hdb_validated(mixed_data)

        assert len(result) == 1
        assert result.iloc[0]["price"] == 500000.0

        quarantine_warnings = [
            record
            for record in caplog.records
            if "hdb_validated: 1 row(s) quarantined at the silver boundary" in record.getMessage()
        ]
        assert len(quarantine_warnings) == 1

        # The node itself must not persist anything — no output, no quarantine.
        assert not list(tmp_path.rglob("*.parquet"))


class TestSilverContractTightening:
    """WS9: real silver contract — pass-through fields validated, tighter bounds."""

    def _geocoded_row(self, **overrides):
        row = {
            "address": "123 TOA PAYOH LOR 1",
            "lat": 1.35,
            "lon": 103.8,
            "property_type": "hdb",
            "postal_code": "312345",
            "block": "123",
            "street_name": "TOA PAYOH LOR 1",
            "town": "TOA PAYOH",
            "flat_type": "4 ROOM",
            "floor_area_sqm": 90.0,
            "floor_area_sqft": 969.0,
            "month": "2024-01",
        }
        row.update(overrides)
        return pd.DataFrame([row])

    def test_pass_through_fields_validated_and_preserved(self, tmp_path):
        """block/town/flat_type/floor areas/month are real GeocodedProperty fields."""
        cleaning = _get_cleaning_module()

        result = cleaning.geocoded_validated(self._geocoded_row())

        assert len(result) == 1
        for col in (
            "block",
            "street_name",
            "town",
            "flat_type",
            "floor_area_sqm",
            "floor_area_sqft",
            "month",
        ):
            assert col in result.columns

    def test_pass_through_fields_may_be_null(self):
        """Condo rows lack the HDB-only columns — nulls must stay valid."""
        cleaning = _get_cleaning_module()

        result = cleaning.geocoded_validated(
            self._geocoded_row(
                block=pd.NA,
                street_name=pd.NA,
                town=pd.NA,
                flat_type=pd.NA,
                floor_area_sqm=pd.NA,
                floor_area_sqft=pd.NA,
                month=pd.NA,
            ),
        )

        assert len(result) == 1
        assert pd.isna(result.loc[0, "town"])

    def test_wrong_type_pass_through_field_quarantined(self, tmp_path, caplog):
        cleaning = _get_cleaning_module()

        with caplog.at_level(logging.WARNING, logger="egg_n_bacon_housing.components.cleaning"):
            result = cleaning.geocoded_validated(self._geocoded_row(floor_area_sqm="not-a-number"))

        assert result.empty
        assert any(
            "geocoded_validated: 1 row(s) quarantined at the silver boundary" in record.getMessage()
            for record in caplog.records
        )
        assert not (tmp_path / "02_silver" / "_quarantine").exists()
        assert not list(tmp_path.rglob("*.parquet"))

    def test_non_positive_floor_area_quarantined(self):
        cleaning = _get_cleaning_module()

        result = cleaning.geocoded_validated(self._geocoded_row(floor_area_sqft=0.0))

        assert result.empty

    def test_empty_property_type_quarantined(self):
        cleaning = _get_cleaning_module()

        result = cleaning.geocoded_validated(self._geocoded_row(property_type=""))

        assert result.empty

    def test_pre_1990_transaction_date_quarantined(self, tmp_path):
        """transaction_date has a plausibility floor at 1990-01-01 (dataset start)."""
        cleaning = _get_cleaning_module()

        hdb = pd.DataFrame(
            [
                {
                    "transaction_date": pd.Timestamp("1989-12-31"),
                    "price": 500000.0,
                    "lat": 1.35,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "floor_area_sqm": 90.0,
                    "floor_area_sqft": 969.0,
                },
            ]
        )

        result = cleaning.hdb_validated(hdb)

        assert result.empty

    def test_1990_boundary_transaction_date_valid(self, tmp_path):
        cleaning = _get_cleaning_module()

        hdb = pd.DataFrame(
            [
                {
                    "transaction_date": pd.Timestamp("1990-01-01"),
                    "price": 500000.0,
                    "lat": 1.35,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "town": "TOA PAYOH",
                    "flat_type": "4 ROOM",
                    "block": "123",
                    "street_name": "TOA PAYOH LOR 1",
                    "floor_area_sqm": 90.0,
                    "floor_area_sqft": 969.0,
                },
            ]
        )

        result = cleaning.hdb_validated(hdb)

        assert len(result) == 1


class TestSilverMaterializationEquivalence:
    """Gateway persist=False + companion materializer == old inline-persist output.

    Before the materializer migration the silver nodes wrote their valid rows
    through the validation gateway (persist=True). Now the nodes write nothing
    and the companion materializers persist the exact frames the nodes return,
    under the PUBLISHED_LAYERS name/layer pair.
    """

    @staticmethod
    def _mixed_hdb_rows() -> pd.DataFrame:
        valid_row = {
            "transaction_date": pd.Timestamp("2023-01-01"),
            "price": 500000.0,
            "lat": 1.35,
            "lon": 103.8,
            "property_type": "hdb",
            "planning_area": "Toa Payoh",
            "town": "TOA PAYOH",
            "flat_type": "4 ROOM",
            "block": "123",
            "street_name": "TOA PAYOH LOR 1",
            "storey_min": 4,
            "storey_max": 6,
            "floor_area_sqm": 90.0,
            "floor_area_sqft": 969.0,
            "remaining_lease_months": 960,
            "address": "123 TOA PAYOH LOR 1",
        }
        invalid_row = {**valid_row, "price": -100.0, "address": "456 BAD PLACE"}
        return pd.DataFrame([valid_row, invalid_row])

    def test_hdb_validated_node_plus_materializer_reproduces_inline_output(self, tmp_path):
        from egg_n_bacon_housing.components.materialization import materialize_hdb_validated

        cleaning = _get_cleaning_module()
        writer = SimpleWriter(tmp_path)

        result = cleaning.hdb_validated(self._mixed_hdb_rows())

        # Node phase: valid rows only, nothing on disk yet.
        assert len(result) == 1
        assert not list(tmp_path.rglob("*.parquet"))

        path = materialize_hdb_validated(result, writer)

        layer = PUBLISHED_LAYERS["hdb_validated"]
        assert path == writer.resolve_path("hdb_validated", layer, tmp_path)
        persisted = pd.read_parquet(path)
        pd.testing.assert_frame_equal(persisted, result)

    def test_geocoded_validated_node_plus_materializer_reproduces_inline_output(self, tmp_path):
        from egg_n_bacon_housing.components.materialization import materialize_geocoded_validated

        cleaning = _get_cleaning_module()
        writer = SimpleWriter(tmp_path)
        frame = pd.DataFrame(
            [
                {
                    "address": "123 TOA PAYOH LOR 1",
                    "lat": 1.35,
                    "lon": 103.8,
                    "property_type": "hdb",
                    "postal_code": "312345",
                }
            ]
        )

        result = cleaning.geocoded_validated(frame)

        assert len(result) == 1
        assert not list(tmp_path.rglob("*.parquet"))

        path = materialize_geocoded_validated(result, writer)

        layer = PUBLISHED_LAYERS["geocoded_validated"]
        assert path == writer.resolve_path("geocoded_validated", layer, tmp_path)
        pd.testing.assert_frame_equal(pd.read_parquet(path), result)
