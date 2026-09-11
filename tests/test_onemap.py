"""Tests for adapters/onemap.py."""

import base64
import importlib
import json
import logging
import os
import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests
from pydantic import SecretStr

from egg_n_bacon_housing.config import settings

pytestmark = pytest.mark.unit


def _get_onemap_module():
    return importlib.import_module("egg_n_bacon_housing.adapters.onemap")


def _stub_credentials(monkeypatch) -> None:
    """Make token tests hermetic: valid-looking creds regardless of local .env."""
    monkeypatch.setattr(settings.onemap_email, "get_secret_value", lambda: "test@example.com")
    monkeypatch.setattr(settings.onemap_password, "get_secret_value", lambda: "pw")


def _stub_token(monkeypatch, token: str | None) -> None:
    """Point the settings singleton's ONEMAP_TOKEN at an explicit value (or None)."""
    monkeypatch.setattr(settings, "onemap_token", SecretStr(token) if token else None)


def _stub_token_response(token: str) -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.text = json.dumps({"access_token": token})
    return response


def _patch_session_post(**kwargs):
    """Patch requests.Session.post (the adapter uses per-thread sessions)."""
    return patch.object(requests.Session, "post", **kwargs)


def _patch_session_get(**kwargs):
    return patch.object(requests.Session, "get", **kwargs)


class TestSetupOnemapHeaders:
    def test_uses_logger_not_print(self, monkeypatch, caplog):
        """setup_onemap_headers should use logger, not print."""
        onemap = _get_onemap_module()

        _stub_token(monkeypatch, None)
        _stub_credentials(monkeypatch)

        with _patch_session_post(return_value=_stub_token_response("test-token-123")):
            with caplog.at_level(logging.INFO, logger="egg_n_bacon_housing.adapters.onemap"):
                result = onemap.setup_onemap_headers(settings)

        assert result == {"Authorization": "test-token-123"}
        assert any("Obtained new OneMap token" in r.message for r in caplog.records)

    def test_credential_error_fails_fast_without_retry(self, monkeypatch):
        """Credential failures must fail fast instead of being retried."""
        onemap = _get_onemap_module()

        _stub_token(monkeypatch, None)
        # Force-empty creds regardless of the local .env
        monkeypatch.setattr(settings.onemap_email, "get_secret_value", lambda: "")
        monkeypatch.setattr(settings.onemap_password, "get_secret_value", lambda: "")
        mock_post = MagicMock()

        with _patch_session_post(return_value=mock_post):
            with pytest.raises(onemap.CredentialError):
                onemap._request_new_token(settings)

        mock_post.assert_not_called()
        assert onemap._request_new_token.statistics["attempt_number"] == 1

    def test_retries_on_transient_auth_failure(self, monkeypatch):
        """Auth should retry on transient failures."""
        onemap = _get_onemap_module()

        _stub_token(monkeypatch, None)
        _stub_credentials(monkeypatch)

        call_count = 0

        def mock_post(url, json=None, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                resp = MagicMock()
                resp.status_code = 500
                resp.text = "Server Error"
                return resp
            return _stub_token_response("retry-token")

        with _patch_session_post(side_effect=mock_post):
            result = onemap.setup_onemap_headers(settings)

        assert call_count == 3
        assert result == {"Authorization": "retry-token"}

    def test_missing_credentials_fail_preflight(self, monkeypatch):
        """Should fail before outbound request when required credentials are missing."""
        onemap = _get_onemap_module()

        with _patch_session_post() as mock_post:
            with patch.object(
                settings.onemap_email,
                "get_secret_value",
                return_value="",
            ):
                with pytest.raises(onemap.CredentialError):
                    onemap._get_required_secret(settings, "onemap_email")
        mock_post.assert_not_called()

    def test_token_read_from_settings_not_environ(self, monkeypatch):
        """The pre-issued token comes from Settings (SecretStr), not os.environ."""
        onemap = _get_onemap_module()

        # Env var present but settings token absent: env must be ignored.
        monkeypatch.setenv("ONEMAP_TOKEN", "env-should-be-ignored")
        _stub_token(monkeypatch, None)
        _stub_credentials(monkeypatch)

        with _patch_session_post(return_value=_stub_token_response("from-settings-flow")):
            result = onemap.setup_onemap_headers(settings)

        assert result == {"Authorization": "from-settings-flow"}


class TestFetchDataCached:
    def test_duration_hours_pins_the_ttl_knob(self, tmp_path):
        """T7: duration_hours overrides the manager default on both read and
        write — an entry older than the knob expires even when the manager's
        longer default would keep it."""
        onemap = _get_onemap_module()
        cache = importlib.import_module("egg_n_bacon_housing.utils.cache")
        # Manager default (24h) is deliberately longer than the knob under test.
        manager = cache.CacheManager(tmp_path, use_caching=True, cache_duration_hours=24)

        mock_df = pd.DataFrame([{"SEARCHVAL": "TEST", "LATITUDE": "1.3", "LONGITUDE": "103.8"}])
        headers = {"Authorization": "Bearer x"}

        with patch.object(onemap, "fetch_data", return_value=mock_df) as mock_fetch:
            onemap.fetch_data_cached("ttl knob", headers, duration_hours=2, cache_manager=manager)
            assert mock_fetch.call_count == 1

            # Fresh entry: a read within the knob is a hit.
            onemap.fetch_data_cached("ttl knob", headers, duration_hours=2, cache_manager=manager)
            assert mock_fetch.call_count == 1

            # Age the entry past the 2h knob (manager default is 24h).
            key = manager._get_cache_key("onemap_search:ttl knob")
            stale = time.time() - 3 * 3600
            os.utime(tmp_path / f"{key}.parquet", (stale, stale))

            onemap.fetch_data_cached("ttl knob", headers, duration_hours=2, cache_manager=manager)
            assert mock_fetch.call_count == 2  # knob expired the entry

    def test_no_duration_hours_falls_back_to_manager_default(self, tmp_path):
        """Without the knob the manager default applies (backwards compatible)."""
        onemap = _get_onemap_module()
        cache = importlib.import_module("egg_n_bacon_housing.utils.cache")
        manager = cache.CacheManager(tmp_path, use_caching=True, cache_duration_hours=1)

        mock_df = pd.DataFrame([{"SEARCHVAL": "TEST", "LATITUDE": "1.3", "LONGITUDE": "103.8"}])
        headers = {"Authorization": "Bearer x"}

        with patch.object(onemap, "fetch_data", return_value=mock_df) as mock_fetch:
            onemap.fetch_data_cached("default ttl", headers, cache_manager=manager)

            key = manager._get_cache_key("onemap_search:default ttl")
            stale = time.time() - 2 * 3600
            os.utime(tmp_path / f"{key}.parquet", (stale, stale))

            onemap.fetch_data_cached("default ttl", headers, cache_manager=manager)

        assert mock_fetch.call_count == 2  # expired under the 1h manager default


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

        with _patch_session_get(side_effect=mock_get):
            df = onemap.fetch_data("Test Query", {"Authorization": "Bearer x"}, timeout=5)

        assert call_count == 3
        assert not df.empty
        assert "search_result" in df.columns

    def test_missing_results_key_raises_retryable_error(self, monkeypatch, caplog):
        """A 200 payload without 'results' is an error shape, not "0 matches":
        it must raise DatasetFetchError (retried as transient) instead of
        silently returning an empty success."""
        onemap = _get_onemap_module()
        monkeypatch.setattr("tenacity.nap.sleep", lambda _s: None)

        response = MagicMock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        response.text = json.dumps({"error": "boom"})

        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return response

        with caplog.at_level(logging.ERROR, logger="egg_n_bacon_housing.adapters.onemap"):
            with _patch_session_get(side_effect=mock_get):
                with pytest.raises(onemap.DatasetFetchError, match="results"):
                    onemap.fetch_data("Test Query", {"Authorization": "x"}, timeout=5)

        assert call_count == 3  # retried as a transient/malformed response
        assert any("missing 'results' key" in r.message for r in caplog.records)

    def test_missing_results_key_response_is_never_cached(self, monkeypatch, tmp_path):
        """A malformed payload must not be cached as an authoritative empty
        success — the address stays geocodable on the next run."""
        onemap = _get_onemap_module()
        cache = importlib.import_module("egg_n_bacon_housing.utils.cache")
        manager = cache.CacheManager(tmp_path, use_caching=True)
        monkeypatch.setattr("tenacity.nap.sleep", lambda _s: None)

        response = MagicMock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        response.text = json.dumps({"error": "boom"})

        with _patch_session_get(return_value=response):
            with pytest.raises(onemap.DatasetFetchError):
                onemap.fetch_data_cached("bad shape", {"Authorization": "x"}, cache_manager=manager)

        assert list(tmp_path.iterdir()) == []  # nothing cached for the failed address

    def test_found_zero_with_empty_results_caches_empty_success(self, tmp_path):
        """found:0 with results:[] is a valid 'no match' response and caches
        an empty frame (a legitimate negative result, not an error shape)."""
        onemap = _get_onemap_module()
        cache = importlib.import_module("egg_n_bacon_housing.utils.cache")
        manager = cache.CacheManager(tmp_path, use_caching=True)

        response = MagicMock()
        response.status_code = 200
        response.raise_for_status.return_value = None
        response.text = json.dumps({"found": 0, "totalResults": 0, "results": [], "pageNum": 1})

        with _patch_session_get(return_value=response) as mock_get:
            df1 = onemap.fetch_data_cached(
                "no match addr", {"Authorization": "x"}, cache_manager=manager
            )
            df2 = onemap.fetch_data_cached(
                "no match addr", {"Authorization": "x"}, cache_manager=manager
            )

        assert df1.empty
        assert df2.empty
        assert mock_get.call_count == 1  # second read served from cache


class TestJWTTokenHandling:
    def test_valid_jwt_token_with_future_expiry(self, monkeypatch):
        """Valid JWT token with future expiry is used directly."""
        onemap = _get_onemap_module()

        payload = {"exp": 9999999999, "sub": "test"}
        payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        token = f"header.{payload_b64}.signature"

        _stub_token(monkeypatch, token)

        result = onemap.setup_onemap_headers(settings)

        assert result == {"Authorization": token}

    def test_valid_jwt_token_with_aligned_payload_padding(self, monkeypatch):
        """A payload segment already a multiple of 4 chars (with its own '='
        padding) must decode — the padding fix must not append redundant '='."""
        onemap = _get_onemap_module()

        payload = {"exp": 99999999999999}
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        assert len(encoded) % 4 == 0  # b64encode emits aligned segments incl. '='
        token = f"header.{encoded}.signature"

        _stub_token(monkeypatch, token)

        assert onemap.setup_onemap_headers(settings) == {"Authorization": token}

    def test_expired_jwt_token_requests_new_one(self, monkeypatch):
        """Expired JWT token triggers new token request."""
        onemap = _get_onemap_module()

        payload = {"exp": 1, "sub": "test"}
        payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        token = f"header.{payload_b64}.signature"

        _stub_token(monkeypatch, token)
        _stub_credentials(monkeypatch)

        with _patch_session_post(return_value=_stub_token_response("fresh-token")):
            result = onemap.setup_onemap_headers(settings)

        assert result == {"Authorization": "fresh-token"}

    def test_invalid_token_format_requests_new_one(self, monkeypatch):
        """Token without 3 JWT parts triggers new token request."""
        onemap = _get_onemap_module()

        _stub_token(monkeypatch, "not-a-jwt")
        _stub_credentials(monkeypatch)

        with _patch_session_post(return_value=_stub_token_response("new-token")):
            result = onemap.setup_onemap_headers(settings)

        assert result == {"Authorization": "new-token"}

    def test_corrupt_jwt_payload_falls_through_to_password_flow(self, monkeypatch):
        """A 3-part token with undecodable base64 payload must not crash; it
        falls through to the email/password flow."""
        onemap = _get_onemap_module()

        _stub_token(monkeypatch, "header.!!!not-valid-base64!!!.sig")
        _stub_credentials(monkeypatch)

        with _patch_session_post(return_value=_stub_token_response("fallback-token")):
            result = onemap.setup_onemap_headers(settings)

        assert result == {"Authorization": "fallback-token"}

    def test_missing_access_token_in_response_raises(self, monkeypatch):
        """Response without access_token raises error after retries."""
        onemap = _get_onemap_module()

        _stub_token(monkeypatch, None)

        response = MagicMock()
        response.status_code = 200
        response.text = json.dumps({"error": "no token"})

        with _patch_session_post(return_value=response):
            with pytest.raises((onemap.OneMapAuthError, Exception)):
                onemap._request_new_token(settings)

    def test_non_200_status_raises(self, monkeypatch):
        """Non-200 status from token endpoint raises error."""
        onemap = _get_onemap_module()

        _stub_token(monkeypatch, None)

        response = MagicMock()
        response.status_code = 401
        response.text = "Unauthorized"

        with _patch_session_post(return_value=response):
            with pytest.raises((onemap.OneMapAuthError, Exception)):
                onemap._request_new_token(settings)


class TestThreadLocalSessions:
    def test_each_thread_gets_its_own_session(self):
        """Sessions are per-thread (the geocoder runs a ThreadPoolExecutor)."""
        import threading

        onemap = _get_onemap_module()
        sessions = {}
        barrier = threading.Barrier(2)

        def worker(name):
            barrier.wait()
            sessions[name] = onemap._get_session()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert sessions[0] is not sessions[1]
        # Main thread has its own stable session, distinct from both workers.
        assert onemap._get_session() not in sessions.values()
        assert onemap._get_session() is onemap._get_session()


def _http_error(status: int, retry_after: str | None = None) -> requests.HTTPError:
    response = MagicMock()
    response.status_code = status
    response.headers = {"Retry-After": retry_after} if retry_after else {}
    return requests.HTTPError(f"HTTP {status}", response=response)


class TestRetryPolicy:
    """fetch_data retries only transient failures and honors Retry-After."""

    def test_parse_retry_after_delta_seconds(self):
        onemap = _get_onemap_module()

        assert onemap._parse_retry_after("5") == 5.0
        assert onemap._parse_retry_after(" 12 ") == 12.0
        assert onemap._parse_retry_after(None) is None
        assert onemap._parse_retry_after("") is None
        assert onemap._parse_retry_after("soon") is None

    def test_parse_retry_after_http_date(self):
        import datetime as dt
        import email.utils

        onemap = _get_onemap_module()
        future = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=30)
        header = email.utils.format_datetime(future)

        wait = onemap._parse_retry_after(header)

        assert wait is not None
        assert 25 <= wait <= 30

    def test_is_retryable_classification(self):
        onemap = _get_onemap_module()

        assert onemap._is_retryable_exception(_http_error(429))
        assert onemap._is_retryable_exception(_http_error(503))
        assert onemap._is_retryable_exception(requests.ConnectionError("down"))
        assert onemap._is_retryable_exception(requests.Timeout("slow"))
        assert not onemap._is_retryable_exception(_http_error(404))
        assert not onemap._is_retryable_exception(_http_error(400))
        assert not onemap._is_retryable_exception(onemap.CredentialError("no creds"))
        assert not onemap._is_retryable_exception(onemap.OneMapAuthError("bad token"))

    def test_wait_honors_retry_after_on_429(self):
        from types import SimpleNamespace

        onemap = _get_onemap_module()
        outcome = SimpleNamespace(exception=lambda: _http_error(429, retry_after="7"))
        retry_state = SimpleNamespace(outcome=outcome)

        assert onemap._wait_after_error(retry_state) == 7.0

        capped = SimpleNamespace(
            outcome=SimpleNamespace(exception=lambda: _http_error(429, retry_after="3600"))
        )
        assert onemap._wait_after_error(capped) == onemap.MAX_RETRY_AFTER_WAIT

    def test_401_raises_auth_error_without_retry(self):
        """401 is an auth problem for the caller to refresh, not a retry."""
        onemap = _get_onemap_module()

        response = MagicMock()
        response.status_code = 401

        with _patch_session_get(return_value=response):
            with pytest.raises(onemap.OneMapAuthError, match="refresh"):
                onemap.fetch_data("Test", {"Authorization": "expired"}, timeout=5)

        assert onemap.fetch_data.statistics["attempt_number"] == 1

    def test_429_is_retried_then_succeeds(self, monkeypatch):
        onemap = _get_onemap_module()
        monkeypatch.setattr("tenacity.nap.sleep", lambda _s: None)

        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise _http_error(429, retry_after="1")
            response = MagicMock()
            response.status_code = 200
            response.raise_for_status.return_value = None
            response.text = json.dumps(
                {"results": [{"SEARCHVAL": "TEST", "LATITUDE": "1.3", "LONGITUDE": "103.8"}]}
            )
            return response

        with _patch_session_get(side_effect=mock_get):
            df = onemap.fetch_data("Test", {"Authorization": "x"}, timeout=5)

        assert call_count == 2
        assert not df.empty

    def test_404_is_not_retried(self):
        onemap = _get_onemap_module()

        with _patch_session_get(side_effect=_http_error(404)):
            with pytest.raises(requests.HTTPError):
                onemap.fetch_data("Test", {"Authorization": "x"}, timeout=5)

        assert onemap.fetch_data.statistics["attempt_number"] == 1
