"""Contract tests for adapters/datagovsg.py retry behavior."""

import importlib
from unittest.mock import MagicMock

import pandas as pd
import pytest
import requests

pytestmark = pytest.mark.unit


def _get_datagov_module():
    return importlib.import_module("egg_n_bacon_housing.adapters.datagovsg")


class TestDatagovRetryBehavior:
    def test_retries_on_server_error_then_succeeds(self, monkeypatch):
        """Should retry 5xx responses and eventually return records."""
        datagov = _get_datagov_module()

        call_count = 0

        def fake_get(url, timeout=60):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                response = MagicMock()
                response.status_code = 503
                response.raise_for_status.side_effect = requests.HTTPError(response=response)
                return response

            response = MagicMock()
            response.status_code = 200
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "result": {
                    "records": [{"month": "2024-01", "resale_price": 500000}],
                    "_links": {},
                    "total": 1,
                }
            }
            return response

        monkeypatch.setattr(datagov.requests, "get", fake_get)
        monkeypatch.setattr(datagov.time, "sleep", lambda *_: None)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "dataset-id",
            use_cache=False,
        )

        assert call_count == 3
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    def test_raises_on_incomplete_paginated_fetch(self, monkeypatch):
        """Should raise when paginated fetch fails before reaching expected total."""
        datagov = _get_datagov_module()

        call_count = 0

        def fake_get(url, timeout=60):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                response = MagicMock()
                response.status_code = 200
                response.raise_for_status.return_value = None
                response.json.return_value = {
                    "result": {
                        "records": [{"month": "2024-01", "resale_price": 500000}],
                        "_links": {"next": "/api/action/datastore_search?offset=10000"},
                        "total": 20000,
                    }
                }
                return response

            response = MagicMock()
            response.status_code = 500
            response.raise_for_status.side_effect = requests.HTTPError(response=response)
            return response

        monkeypatch.setattr(datagov.requests, "get", fake_get)
        monkeypatch.setattr(datagov.time, "sleep", lambda *_: None)

        with pytest.raises(datagov.IncompleteDatasetFetchError):
            datagov.fetch_datagovsg_dataset(
                "https://data.gov.sg/api/action/datastore_search?resource_id=",
                "dataset-id",
                use_cache=False,
            )

    def test_retries_on_request_exception_then_succeeds(self, monkeypatch):
        """Should retry transient request exceptions."""
        datagov = _get_datagov_module()

        call_count = 0

        def fake_get(url, timeout=60):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.ConnectionError("temporary network issue")

            response = MagicMock()
            response.status_code = 200
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "result": {
                    "records": [{"month": "2024-01", "resale_price": 600000}],
                    "_links": {},
                    "total": 1,
                }
            }
            return response

        monkeypatch.setattr(datagov.requests, "get", fake_get)
        monkeypatch.setattr(datagov.time, "sleep", lambda *_: None)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "dataset-id",
            use_cache=False,
        )

        assert call_count == 3
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1


class TestDatagovMultiPagePagination:
    def test_multi_page_fetch_concatenates_records(self, monkeypatch):
        """Should fetch multiple pages and concatenate all records."""
        datagov = _get_datagov_module()

        call_count = 0

        def fake_get(url, timeout=60):
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            response.status_code = 200
            response.raise_for_status.return_value = None

            if call_count == 1:
                response.json.return_value = {
                    "result": {
                        "records": [{"id": 1}, {"id": 2}],
                        "_links": {"next": "/api/action/datastore_search?offset=2"},
                        "total": 4,
                    }
                }
            else:
                response.json.return_value = {
                    "result": {
                        "records": [{"id": 3}, {"id": 4}],
                        "_links": {},
                        "total": 4,
                    }
                }
            return response

        monkeypatch.setattr(datagov.requests, "get", fake_get)
        monkeypatch.setattr(datagov.time, "sleep", lambda *_: None)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "dataset-id",
            use_cache=False,
        )

        assert call_count == 2
        assert len(result) == 4

    def test_rate_limit_429_retries_with_retry_after(self, monkeypatch):
        """Should retry on 429 and respect Retry-After header."""
        datagov = _get_datagov_module()

        call_count = 0
        sleep_calls = []

        def fake_get(url, timeout=60):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                response = MagicMock()
                response.status_code = 429
                response.headers = {"Retry-After": "2"}
                response.raise_for_status.side_effect = requests.HTTPError(response=response)
                return response

            response = MagicMock()
            response.status_code = 200
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "result": {
                    "records": [{"id": 1}],
                    "_links": {},
                    "total": 1,
                }
            }
            return response

        def fake_sleep(seconds):
            sleep_calls.append(seconds)

        monkeypatch.setattr(datagov.requests, "get", fake_get)
        monkeypatch.setattr(datagov.time, "sleep", fake_sleep)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "dataset-id",
            use_cache=False,
        )

        assert call_count == 2
        assert len(result) == 1
        assert len(sleep_calls) == 1
        assert sleep_calls[0] == 2

    def test_empty_results_returns_empty_dataframe(self, monkeypatch):
        """Should return empty DataFrame when no records in response."""
        datagov = _get_datagov_module()

        def fake_get(url, timeout=60):
            response = MagicMock()
            response.status_code = 200
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "result": {
                    "records": [],
                    "_links": {},
                    "total": 0,
                }
            }
            return response

        monkeypatch.setattr(datagov.requests, "get", fake_get)
        monkeypatch.setattr(datagov.time, "sleep", lambda *_: None)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "dataset-id",
            use_cache=False,
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_no_records_key_returns_empty(self, monkeypatch):
        """Should return empty when result has no records key."""
        datagov = _get_datagov_module()

        def fake_get(url, timeout=60):
            response = MagicMock()
            response.status_code = 200
            response.raise_for_status.return_value = None
            response.json.return_value = {"result": {"_links": {}}}
            return response

        monkeypatch.setattr(datagov.requests, "get", fake_get)
        monkeypatch.setattr(datagov.time, "sleep", lambda *_: None)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "dataset-id",
            use_cache=False,
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty
