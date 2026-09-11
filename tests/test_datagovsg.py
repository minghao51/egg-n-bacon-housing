"""Contract tests for adapters/datagovsg.py retry behavior."""

import importlib
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests
from requests import RequestException

from egg_n_bacon_housing.adapters.exceptions import DatasetFetchError

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

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
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

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
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

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
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

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
        monkeypatch.setattr(datagov.time, "sleep", lambda *_: None)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "dataset-id",
            use_cache=False,
        )

        assert call_count == 2
        assert len(result) == 4

    def test_relative_next_link_gets_datagovsg_prefix(self, monkeypatch):
        """A relative _links.next URL must be prefixed with the data.gov.sg origin."""
        datagov = _get_datagov_module()
        requested_urls = []

        def fake_get(url, timeout=60):
            requested_urls.append(url)
            response = MagicMock()
            response.status_code = 200
            response.raise_for_status.return_value = None

            if len(requested_urls) == 1:
                response.json.return_value = {
                    "result": {
                        "records": [{"id": 1}, {"id": 2}],
                        "_links": {
                            "next": "/api/action/datastore_search?resource_id=d_rel&offset=2"
                        },
                        "total": 4,
                    }
                }
            else:
                response.json.return_value = {
                    "result": {"records": [{"id": 3}, {"id": 4}], "_links": {}, "total": 4}
                }
            return response

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
        monkeypatch.setattr(datagov.time, "sleep", lambda *_: None)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "d_rel",
            use_cache=False,
        )

        assert len(result) == 4
        assert (
            requested_urls[1] == "https://data.gov.sg/api/action/datastore_search"
            "?resource_id=d_rel&offset=2"
        )

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

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
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

    def test_rate_limit_429_retries_with_http_date_retry_after(self, monkeypatch):
        """HTTP-date Retry-After (RFC 7231) must not raise; it should sleep the parsed delay."""
        import datetime as dt
        import email.utils

        datagov = _get_datagov_module()

        retry_at = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=30)
        header = email.utils.format_datetime(retry_at)

        call_count = 0
        sleep_calls = []

        def fake_get(url, timeout=60):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                response = MagicMock()
                response.status_code = 429
                response.headers = {"Retry-After": header}
                response.raise_for_status.side_effect = requests.HTTPError(
                    "429 Too Many Requests", response=response
                )
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

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
        monkeypatch.setattr(datagov.time, "sleep", fake_sleep)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "dataset-id",
            use_cache=False,
        )

        assert call_count == 2
        assert len(result) == 1
        assert len(sleep_calls) == 1
        # Parsed seconds-from-now for a date 30s in the future (small drift allowance).
        assert 25 <= sleep_calls[0] <= 30

    def test_rate_limit_429_garbage_retry_after_falls_back_to_backoff(self, monkeypatch):
        """Unparseable Retry-After must fall back to the exponential backoff path."""
        datagov = _get_datagov_module()

        call_count = 0
        sleep_calls = []

        def fake_get(url, timeout=60):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                response = MagicMock()
                response.status_code = 429
                response.headers = {"Retry-After": "not-a-date-or-number"}
                response.raise_for_status.side_effect = requests.HTTPError(
                    "429 Too Many Requests", response=response
                )
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

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
        monkeypatch.setattr(datagov.time, "sleep", fake_sleep)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "dataset-id",
            use_cache=False,
        )

        assert call_count == 2
        assert len(result) == 1
        # Fallback is min(2**1, 30) for the first retry attempt.
        assert sleep_calls == [2]

    def test_rate_limit_429_caps_huge_numeric_retry_after_at_60(self, monkeypatch):
        """A hostile/misconfigured Retry-After: 3600 must sleep exactly 60s, not an hour."""
        datagov = _get_datagov_module()

        call_count = 0
        sleep_calls = []

        def fake_get(url, timeout=60):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                response = MagicMock()
                response.status_code = 429
                response.headers = {"Retry-After": "3600"}
                response.raise_for_status.side_effect = requests.HTTPError(
                    "429 Too Many Requests", response=response
                )
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

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
        monkeypatch.setattr(datagov.time, "sleep", fake_sleep)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "dataset-id",
            use_cache=False,
        )

        assert call_count == 2
        assert len(result) == 1
        assert sleep_calls == [60]

    def test_rate_limit_429_caps_far_future_http_date_retry_after_at_60(self, monkeypatch):
        """An HTTP-date Retry-After one hour in the future must also be capped to 60s."""
        import datetime as dt
        import email.utils

        datagov = _get_datagov_module()

        retry_at = dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)
        header = email.utils.format_datetime(retry_at)

        call_count = 0
        sleep_calls = []

        def fake_get(url, timeout=60):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                response = MagicMock()
                response.status_code = 429
                response.headers = {"Retry-After": header}
                response.raise_for_status.side_effect = requests.HTTPError(
                    "429 Too Many Requests", response=response
                )
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

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
        monkeypatch.setattr(datagov.time, "sleep", fake_sleep)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "dataset-id",
            use_cache=False,
        )

        assert call_count == 2
        assert len(result) == 1
        assert sleep_calls == [60]

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

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
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

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
        monkeypatch.setattr(datagov.time, "sleep", lambda *_: None)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "dataset-id",
            use_cache=False,
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestFetchDatagovsgGeojson:
    """Test the GEOJSON download flow (initiate -> poll -> presigned URL)."""

    @staticmethod
    def _response(json_body=None, status=200):
        response = MagicMock()
        response.status_code = status
        response.raise_for_status.side_effect = (
            None if status == 200 else requests.HTTPError(f"HTTP {status}")
        )
        if json_body is not None:
            response.json.return_value = json_body
        return response

    def _geojson(self):
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "properties": {"CLASSIFCTN": "MALL"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[103.8, 1.3], [103.8, 1.31], [103.81, 1.31]]],
                    },
                }
            ],
        }

    def test_success_flow(self, monkeypatch):
        datagov = _get_datagov_module()
        requested = []

        def fake_get(url, timeout=0, params=None):
            requested.append(url)
            if "initiate-download" in url:
                return self._response({"code": 0, "data": {"message": "initiated"}})
            if "poll-download" in url:
                return self._response({"code": 0, "data": {"url": "https://s3/presigned"}})
            return self._response(self._geojson())

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))

        result = datagov.fetch_datagovsg_geojson("d_test", use_cache=False)

        assert result["type"] == "FeatureCollection"
        assert len(requested) == 3
        assert "initiate-download" in requested[0]
        assert "poll-download" in requested[1]

    def test_raises_when_poll_never_ready(self, monkeypatch):
        datagov = _get_datagov_module()

        def fake_get(url, timeout=0, params=None):
            if "initiate-download" in url:
                return self._response({"code": 0, "data": {}})
            return self._response({"code": 0, "data": {"message": "still preparing"}})

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
        monkeypatch.setattr(datagov.time, "sleep", lambda *_: None)

        with pytest.raises(DatasetFetchError, match="never became ready"):
            datagov.fetch_datagovsg_geojson("d_test", use_cache=False, poll_attempts=2)

    def test_raises_on_initiate_failure(self, monkeypatch):
        datagov = _get_datagov_module()
        monkeypatch.setattr(requests.Session, "get", lambda *a, **kw: self._response(status=500))

        with pytest.raises(DatasetFetchError, match="initiate"):
            datagov.fetch_datagovsg_geojson("d_test", use_cache=False)

    def test_raises_on_malformed_download_body(self, monkeypatch):
        datagov = _get_datagov_module()

        def fake_get(url, timeout=0, params=None):
            if "initiate-download" in url:
                return self._response({"code": 0, "data": {}})
            if "poll-download" in url:
                return self._response({"code": 0, "data": {"url": "https://s3/presigned"}})
            response = self._response()
            response.json.side_effect = ValueError("not json")
            return response

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))

        with pytest.raises(DatasetFetchError, match="download GeoJSON"):
            datagov.fetch_datagovsg_geojson("d_test", use_cache=False)


class TestInitiateDownloadRetry:
    """The initiate-download step retries transient rate limits (429/5xx)."""

    def test_initiate_retries_429_then_succeeds(self, monkeypatch):
        datagovsg = _get_datagov_module()
        monkeypatch.setattr("tenacity.nap.sleep", lambda _s: None)

        status_codes = iter([429, 429, 200])

        def mock_get(*args, **kwargs):
            status = next(status_codes)
            response = MagicMock()
            response.status_code = status
            if status == 429:
                response.raise_for_status.side_effect = RequestException("429 Too Many Requests")
            else:
                response.raise_for_status.return_value = None
            return response

        # poll returns a ready URL immediately; blob returns a tiny FeatureCollection
        def mock_poll_get(*args, **kwargs):
            response = MagicMock()
            response.status_code = 200
            response.raise_for_status.return_value = None
            response.json.return_value = {"data": {"url": "https://presigned/example"}}
            return response

        def mock_blob_get(*args, **kwargs):
            response = MagicMock()
            response.status_code = 200
            response.raise_for_status.return_value = None
            response.json.return_value = {"type": "FeatureCollection", "features": []}
            return response

        with patch.object(
            requests.Session,
            "get",
            side_effect=[mock_get() for _ in range(3)] + [mock_poll_get(), mock_blob_get()],
        ):
            result = datagovsg.fetch_datagovsg_geojson("d_test", use_cache=False)

        assert result["type"] == "FeatureCollection"

    def test_initiate_exhausts_retries_then_raises(self, monkeypatch):
        datagovsg = _get_datagov_module()
        monkeypatch.setattr("tenacity.nap.sleep", lambda _s: None)

        def mock_get(*args, **kwargs):
            response = MagicMock()
            response.status_code = 429
            response.raise_for_status.side_effect = RequestException("429")
            return response

        with patch.object(requests.Session, "get", side_effect=mock_get):
            with pytest.raises(datagovsg.DatasetFetchError, match="initiate"):
                datagovsg.fetch_datagovsg_geojson("d_test", use_cache=False)


class TestDatagov413PageShrink:
    """413 responses shrink the page limit while preserving the current offset."""

    def test_413_shrinks_page_size_preserving_offset(self, monkeypatch):
        datagov = _get_datagov_module()
        requested_urls = []

        def fake_get(url, timeout=60):
            requested_urls.append(url)
            response = MagicMock()
            if len(requested_urls) == 1:
                # First page rejected: request entity too large at limit=2000.
                response.status_code = 413
                response.raise_for_status.side_effect = requests.HTTPError(
                    "413 Payload Too Large", response=response
                )
                return response
            if len(requested_urls) == 2:
                # Retry at halved limit succeeds and pages forward.
                response.status_code = 200
                response.raise_for_status.return_value = None
                response.json.return_value = {
                    "result": {
                        "records": [{"id": 1}, {"id": 2}],
                        "_links": {
                            "next": "/api/action/datastore_search?resource_id=d_413&offset=2"
                        },
                        "total": 4,
                    }
                }
                return response
            response.status_code = 200
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "result": {"records": [{"id": 3}, {"id": 4}], "_links": {}, "total": 4}
            }
            return response

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
        monkeypatch.setattr(datagov.time, "sleep", lambda *_: None)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "d_413",
            use_cache=False,
        )

        # Final dataframe is complete across the shrunk pages.
        assert len(result) == 4
        assert list(result["id"]) == [1, 2, 3, 4]
        # First request went out at the default page size...
        assert "limit=2000" in requested_urls[0]
        # ...the 413 retry halved the limit and preserved offset=0.
        assert "limit=1000" in requested_urls[1]
        assert "offset=0" in requested_urls[1]
        # ...and pagination continued from the server-provided next link.
        assert "offset=2" in requested_urls[2]

    def test_413_mid_pagination_shrinks_page_size_preserving_offset(self, monkeypatch):
        """A 413 on a later page must shrink the limit while keeping the current offset."""
        datagov = _get_datagov_module()
        requested_urls = []

        def fake_get(url, timeout=60):
            requested_urls.append(url)
            response = MagicMock()
            if len(requested_urls) == 1:
                # First page succeeds at the default limit=2000 and pages forward.
                response.status_code = 200
                response.raise_for_status.return_value = None
                response.json.return_value = {
                    "result": {
                        "records": [{"id": 1}, {"id": 2}],
                        "_links": {
                            "next": "/api/action/datastore_search?resource_id=d_mid413&offset=2000"
                        },
                        "total": 4000,
                    }
                }
                return response
            if len(requested_urls) == 2:
                # Second page rejected mid-pagination: shrink while preserving offset.
                response.status_code = 413
                response.raise_for_status.side_effect = requests.HTTPError(
                    "413 Payload Too Large", response=response
                )
                return response
            # Retry at the halved limit succeeds and finishes the dataset.
            response.status_code = 200
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "result": {"records": [{"id": 3}, {"id": 4}], "_links": {}, "total": 4000}
            }
            return response

        monkeypatch.setattr(requests.Session, "get", MagicMock(side_effect=fake_get))
        monkeypatch.setattr(datagov.time, "sleep", lambda *_: None)

        result = datagov.fetch_datagovsg_dataset(
            "https://data.gov.sg/api/action/datastore_search?resource_id=",
            "d_mid413",
            use_cache=False,
        )

        assert list(result["id"]) == [1, 2, 3, 4]
        # Page 1 went out at the default limit and followed the next link.
        assert "limit=2000" in requested_urls[0]
        assert requested_urls[1].endswith("offset=2000")
        # The mid-pagination 413 retry halved the limit and kept offset=2000.
        assert "limit=1000" in requested_urls[2]
        assert "offset=2000" in requested_urls[2]
