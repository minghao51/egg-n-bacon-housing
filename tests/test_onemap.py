"""Tests for adapters/onemap.py."""

import importlib
import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from egg_n_bacon_housing.config import settings

pytestmark = pytest.mark.unit


def _get_onemap_module():
    return importlib.import_module("egg_n_bacon_housing.adapters.onemap")


class TestSetupOnemapHeaders:
    def test_uses_logger_not_print(self, monkeypatch, caplog):
        """setup_onemap_headers should use logger, not print."""
        onemap = _get_onemap_module()

        monkeypatch.delenv("ONEMAP_TOKEN", raising=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"access_token": "test-token-123"})

        with patch("requests.post", return_value=mock_response):
            import logging

            with caplog.at_level(logging.INFO, logger="egg_n_bacon_housing.adapters.onemap"):
                result = onemap.setup_onemap_headers(settings)

        assert result == {"Authorization": "test-token-123"}
        assert any("Obtained new OneMap token" in r.message for r in caplog.records)

    def test_retries_on_transient_auth_failure(self, monkeypatch):
        """Auth should retry on transient failures."""
        onemap = _get_onemap_module()

        monkeypatch.delenv("ONEMAP_TOKEN", raising=False)

        call_count = 0

        def mock_post(url, json=None, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                resp = MagicMock()
                resp.status_code = 500
                resp.text = "Server Error"
                return resp
            resp = MagicMock()
            resp.status_code = 200
            resp.text = json_dumps({"access_token": "retry-token"})
            return resp

        json_dumps = json.dumps

        with patch("requests.post", side_effect=mock_post):
            result = onemap.setup_onemap_headers(settings)

        assert call_count == 3
        assert result == {"Authorization": "retry-token"}

    def test_missing_credentials_fail_preflight(self, monkeypatch):
        """Should fail before outbound request when required credentials are missing."""
        onemap = _get_onemap_module()

        with patch("requests.post") as mock_post:
            with patch.object(
                settings.onemap_email,
                "get_secret_value",
                return_value="",
            ):
                with pytest.raises(onemap.CredentialError):
                    onemap._get_required_secret(settings, "onemap_email")
        mock_post.assert_not_called()


class TestFetchDataCached:
    def test_uses_geocoding_cache_duration_config(self, monkeypatch, tmp_path):
        """fetch_data_cached should use cache manager's configured duration."""
        onemap = _get_onemap_module()
        cache = importlib.import_module("egg_n_bacon_housing.utils.cache")

        cache.configure(tmp_path, use_caching=True)

        mock_df = pd.DataFrame([{"SEARCHVAL": "TEST", "LATITUDE": "1.3", "LONGITUDE": "103.8"}])

        with patch.object(onemap, "fetch_data", return_value=mock_df):
            result = onemap.fetch_data_cached("test query", {"Authorization": "Bearer x"})

        assert not result.empty

        with patch.object(onemap, "fetch_data") as mock_fetch:
            onemap.fetch_data_cached("test query", {"Authorization": "Bearer x"})
            mock_fetch.assert_not_called()


class TestFetchDataRetry:
    def test_fetch_data_retries_transient_failures(self):
        """fetch_data should retry transient request failures and eventually succeed."""
        onemap = _get_onemap_module()

        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.ConnectionError("temporary network issue")

            response = MagicMock()
            response.status_code = 200
            response.raise_for_status.return_value = None
            response.text = json.dumps(
                {
                    "results": [
                        {
                            "SEARCHVAL": "TEST",
                            "LATITUDE": "1.3",
                            "LONGITUDE": "103.8",
                        }
                    ]
                }
            )
            return response

        with patch("requests.get", side_effect=mock_get):
            df = onemap.fetch_data("Test Query", {"Authorization": "Bearer x"}, timeout=5)

        assert call_count == 3
        assert not df.empty
        assert "search_result" in df.columns


class TestJWTTokenHandling:
    def test_valid_jwt_token_with_future_expiry(self, monkeypatch):
        """Valid JWT token with future expiry is used directly."""
        import base64

        onemap = _get_onemap_module()

        payload = {"exp": 9999999999, "sub": "test"}
        payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        token = f"header.{payload_b64}.signature"

        monkeypatch.setenv("ONEMAP_TOKEN", token)

        result = onemap.setup_onemap_headers(settings)

        assert result == {"Authorization": token}

    def test_expired_jwt_token_requests_new_one(self, monkeypatch):
        """Expired JWT token triggers new token request."""
        import base64

        onemap = _get_onemap_module()

        payload = {"exp": 1, "sub": "test"}
        payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        token = f"header.{payload_b64}.signature"

        monkeypatch.setenv("ONEMAP_TOKEN", token)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"access_token": "fresh-token"})

        with patch("requests.post", return_value=mock_response):
            result = onemap.setup_onemap_headers(settings)

        assert result == {"Authorization": "fresh-token"}

    def test_invalid_token_format_requests_new_one(self, monkeypatch):
        """Token without 3 JWT parts triggers new token request."""
        onemap = _get_onemap_module()

        monkeypatch.setenv("ONEMAP_TOKEN", "not-a-jwt")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"access_token": "new-token"})

        with patch("requests.post", return_value=mock_response):
            result = onemap.setup_onemap_headers(settings)

        assert result == {"Authorization": "new-token"}

    def test_missing_access_token_in_response_raises(self, monkeypatch):
        """Response without access_token raises error after retries."""
        onemap = _get_onemap_module()

        monkeypatch.delenv("ONEMAP_TOKEN", raising=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"error": "no token"})

        with patch("requests.post", return_value=mock_response):
            with pytest.raises((onemap.OneMapAuthError, Exception)):
                onemap._request_new_token(settings)

    def test_non_200_status_raises(self, monkeypatch):
        """Non-200 status from token endpoint raises error."""
        onemap = _get_onemap_module()

        monkeypatch.delenv("ONEMAP_TOKEN", raising=False)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("requests.post", return_value=mock_response):
            with pytest.raises((onemap.OneMapAuthError, Exception)):
                onemap._request_new_token(settings)
