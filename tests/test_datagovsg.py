"""Contract tests for adapters/datagovsg.py retry behavior."""

import importlib
from unittest.mock import MagicMock

import pandas as pd
import requests


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
