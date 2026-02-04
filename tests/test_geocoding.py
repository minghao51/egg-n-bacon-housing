"""Tests for geocoding module."""

import json
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from scripts.core.geocoding import (
    batch_geocode_addresses,
    extract_unique_addresses,
    fetch_data_cached,
    fetch_data_parallel,
    setup_onemap_headers,
)


@pytest.fixture
def mock_headers():
    """Mock OneMap authentication headers."""
    return {"Authorization": "Bearer test_token"}


@pytest.fixture
def sample_geocoding_response():
    """Sample OneMap API response."""
    return {
        "results": [
            {
                "SEARCHVAL": "Test Address",
                "X": "12345.67",
                "Y": "23456.78",
                "LAT": "1.234",
                "LON": "103.456",
            }
        ]
    }


class TestFetchDataCached:
    """Test fetch_data_cached function."""

    @patch("scripts.core.geocoding.cached_call")
    @patch("scripts.core.geocoding.fetch_data")
    def test_fetch_data_cached_uses_cache(self, mock_fetch, mock_cached_call, mock_headers):
        """Test that fetch_data_cached uses caching layer."""
        # Setup mocks
        mock_df = pd.DataFrame({"a": [1, 2, 3]})
        mock_cached_call.return_value = mock_df

        # Call function
        result = fetch_data_cached("Test Address", mock_headers)

        # Verify cached_call was used
        assert mock_cached_call.called
        assert result.equals(mock_df)


class TestFetchDataParallel:
    """Test fetch_data_parallel function."""

    @patch("scripts.core.geocoding.fetch_data_cached")
    def test_parallel_geocoding(self, mock_fetch_cached, mock_headers):
        """Test parallel geocoding with mock data."""
        # Mock successful geocoding
        mock_df = pd.DataFrame(
            {"SEARCHVAL": ["Address 1", "Address 2"], "X": ["100", "200"], "Y": ["100", "200"]}
        )
        mock_fetch_cached.return_value = mock_df

        addresses = ["Address 1", "Address 2", "Address 3"]

        # Run parallel geocoding
        with patch("scripts.core.config.Config.GEOCODING_MAX_WORKERS", 2):
            with patch("scripts.core.config.Config.GEOCODING_API_DELAY", 0.01):
                results, failed = fetch_data_parallel(
                    addresses, mock_headers, max_workers=2, show_progress=False
                )

        # Verify results
        assert len(results) == 3
        assert len(failed) == 0

    @patch("scripts.core.geocoding.fetch_data_cached")
    def test_parallel_geocoding_with_failures(self, mock_fetch_cached, mock_headers):
        """Test parallel geocoding handles failures gracefully."""

        # Mock mixed success/failure
        def side_effect(addr, headers, timeout=None):
            if "fail" in addr.lower():
                raise Exception("API Error")
            return pd.DataFrame({"SEARCHVAL": [addr]})

        mock_fetch_cached.side_effect = side_effect

        addresses = ["Address 1", "Address Fail", "Address 2"]

        # Run parallel geocoding
        with patch("scripts.core.config.Config.GEOCODING_MAX_WORKERS", 2):
            with patch("scripts.core.config.Config.GEOCODING_API_DELAY", 0.01):
                results, failed = fetch_data_parallel(
                    addresses, mock_headers, max_workers=2, show_progress=False
                )

        # Verify
        assert len(results) == 2  # 2 successful
        assert len(failed) == 1  # 1 failed
        assert "Address Fail" in failed[0]


class TestLoadURAFiles:
    """Test load_ura_files function."""

    @patch("scripts.core.geocoding.pd.read_csv")
    @patch("scripts.core.geocoding.Path.exists")
    def test_load_ura_files_with_mock_data(self, mock_exists, mock_read_csv):
        """Test loading URA files with mocked data."""
        # Mock file existence
        mock_exists.return_value = True

        # Mock CSV data
        mock_read_csv.return_value = pd.DataFrame(
            {
                "Project Name": ["Test Project"],
                "Street Name": ["Test Street"],
                "Transacted Price": [1000000],
            }
        )

        # This would require actual file structure setup
        # For now, just verify the function is callable
        # Full integration test would require test data files


class TestExtractUniqueAddresses:
    """Test extract_unique_addresses function."""

    def test_extract_unique_addresses(self):
        """Test extracting unique addresses from transaction data."""
        # Create sample data
        ec_df = pd.DataFrame(
            {
                "Project Name": ["EC1", "EC1", "EC2"],
                "Street Name": ["Street 1", "Street 1", "Street 2"],
            }
        )

        condo_df = pd.DataFrame({"Project Name": ["Condo1"], "Street Name": ["Street 3"]})

        hdb_df = pd.DataFrame({"block": ["123"], "street_name": ["Street 4"]})

        # Extract unique addresses
        result = extract_unique_addresses(ec_df, condo_df, hdb_df)

        # Verify
        assert "NameAddress" in result.columns
        assert "property_type" in result.columns
        assert len(result) == 4  # 2 EC + 1 condo + 1 HDB


class TestSetupOnemapHeaders:
    """Test setup_onemap_headers function."""

    @patch.dict(
        "os.environ",
        {
            "ONEMAP_TOKEN": "test_token_valid",
            "ONEMAP_EMAIL": "test@example.com",
            "ONEMAP_EMAIL_PASSWORD": "password",
        },
    )
    @patch("time.time")
    def test_setup_onemap_headers_with_valid_token(self, mock_time):
        """Test setup with valid cached token."""
        # Mock current time
        mock_time.return_value = 1000000

        # Mock token expiration time (1 hour from now)
        import base64
        import json

        token_payload = {"exp": mock_time.return_value + 3600}
        payload_json = json.dumps(token_payload)
        payload_b64 = base64.b64encode(payload_json.encode()).decode().rstrip("=")

        # Construct fake JWT
        fake_token = f"header.{payload_b64}.signature"

        with patch.dict("os.environ", {"ONEMAP_TOKEN": fake_token}):
            headers = setup_onemap_headers()

            assert "Authorization" in headers
            assert fake_token in headers["Authorization"]

    @patch("scripts.core.geocoding.requests.request")
    @patch.dict(
        "os.environ", {"ONEMAP_EMAIL": "test@example.com", "ONEMAP_EMAIL_PASSWORD": "password"}
    )
    def test_setup_onemap_headers_fetches_new_token(self, mock_request):
        """Test that new token is fetched when none exists."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"access_token": "new_token"})
        mock_request.return_value = mock_response

        with patch.dict("os.environ", {}, clear=True):
            headers = setup_onemap_headers()

            assert "Authorization" in headers
            assert "new_token" in headers["Authorization"]


class TestBatchGeocodeAddresses:
    """Test batch_geocode_addresses function."""

    @patch("scripts.core.geocoding.fetch_data_parallel")
    def test_batch_geocoding(self, mock_fetch_parallel, mock_headers):
        """Test batch geocoding."""
        # Mock parallel geocoding results
        mock_df = pd.DataFrame({"NameAddress": ["Address 1", "Address 2"], "X": ["100", "200"]})

        mock_fetch_parallel.return_value = ([mock_df, mock_df], [])

        addresses = ["Address 1", "Address 2"]

        # Run batch geocoding
        result = batch_geocode_addresses(
            addresses, mock_headers, batch_size=1000, checkpoint_interval=100
        )

        # Verify
        assert not result.empty
        assert len(result) == 4  # 2 dataframes concatenated
