"""Tests for the shared HTTP retry policy in ``adapters/_http.py``.

Unit-level: parsing, classification, and the wait strategy. Adapter-level
behavior (URA fail-fast + Retry-After over a mocked session) lives in
``tests/test_ura.py``; OneMap's parameterization is covered in
``tests/test_onemap.py``.
"""

import time
from email.utils import formatdate
from unittest.mock import MagicMock

import pytest
import requests
from tenacity import wait_fixed

from egg_n_bacon_housing.adapters import _http, datagovsg

pytestmark = pytest.mark.unit


def _http_error(status: int, headers: dict | None = None) -> requests.HTTPError:
    response = MagicMock()
    response.status_code = status
    response.headers = headers or {}
    return requests.HTTPError(f"HTTP {status}", response=response)


def _retry_state(exc: BaseException) -> MagicMock:
    state = MagicMock()
    outcome = MagicMock()
    outcome.exception.return_value = exc
    state.outcome = outcome
    return state


# --- parse_retry_after -----------------------------------------------------


class TestParseRetryAfter:
    def test_delta_seconds(self):
        assert _http.parse_retry_after("120") == 120.0

    def test_delta_seconds_with_whitespace(self):
        assert _http.parse_retry_after("  7 ") == 7.0

    def test_missing_or_empty_returns_default(self):
        assert _http.parse_retry_after(None) is None
        assert _http.parse_retry_after("") is None
        assert _http.parse_retry_after(None, default=0.0) == 0.0

    def test_garbage_returns_default(self):
        assert _http.parse_retry_after("soon-ish") is None
        assert _http.parse_retry_after("soon-ish", default=0.0) == 0.0

    def test_http_date_past_clamps_to_zero(self):
        past = formatdate(time.time() - 3600, usegmt=True)
        assert _http.parse_retry_after(past) == 0.0

    def test_http_date_future_is_seconds_from_now(self):
        header = formatdate(time.time() + 30, usegmt=True)
        assert _http.parse_retry_after(header) == pytest.approx(30.0, abs=5.0)

    def test_naive_http_date_returns_default(self):
        # parsedate_to_datetime raises for a date without a timezone
        assert _http.parse_retry_after("21 Oct 2015 07:28:00") is None


# --- is_transient_status ---------------------------------------------------


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (429, True),
        (500, True),
        (502, True),
        (503, True),
        (599, True),
        (200, False),
        (400, False),
        (401, False),
        (403, False),
        (404, False),
        (413, False),
        (0, False),
    ],
)
def test_is_transient_status(status: int, expected: bool):
    assert _http.is_transient_status(status) is expected


# --- is_retryable_exception ------------------------------------------------


class TestIsRetryableException:
    @pytest.mark.parametrize("status", [429, 500, 503])
    def test_transient_statuses_retry(self, status):
        assert _http.is_retryable_exception(_http_error(status))

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 413])
    def test_permanent_4xx_fail_fast(self, status):
        assert not _http.is_retryable_exception(_http_error(status))

    def test_http_error_without_response_is_permanent(self):
        assert not _http.is_retryable_exception(requests.HTTPError("orphan"))

    @pytest.mark.parametrize(
        "exc",
        [requests.ConnectionError("down"), requests.Timeout("slow")],
    )
    def test_network_errors_retry(self, exc):
        assert _http.is_retryable_exception(exc)

    def test_unrelated_exceptions_do_not_retry(self):
        assert not _http.is_retryable_exception(ValueError("bug"))

    def test_retryable_parameter_extends_policy(self):
        assert _http.is_retryable_exception(ValueError("malformed-200"), retryable=(ValueError,))

    def test_permanent_parameter_takes_precedence_over_retryable(self):
        class AuthError(Exception):
            pass

        assert not _http.is_retryable_exception(
            AuthError("bad token"), permanent=(AuthError,), retryable=(AuthError,)
        )


# --- retry_after_wait ------------------------------------------------------


class TestRetryAfterWait:
    def setup_method(self):
        self._wait = _http.retry_after_wait(wait_fixed(99.0))

    def test_honors_retry_after_delta_seconds(self):
        exc = _http_error(429, {"Retry-After": "5"})
        assert self._wait(_retry_state(exc)) == 5.0

    def test_caps_oversized_retry_after(self):
        exc = _http_error(429, {"Retry-After": "3600"})
        assert self._wait(_retry_state(exc)) == _http.MAX_RETRY_AFTER_WAIT == 60.0

    def test_honors_retry_after_http_date(self):
        header = formatdate(time.time() + 30, usegmt=True)
        exc = _http_error(429, {"Retry-After": header})
        assert self._wait(_retry_state(exc)) == pytest.approx(30.0, abs=5.0)

    def test_absent_header_falls_back(self):
        assert self._wait(_retry_state(_http_error(429))) == 99.0

    def test_garbage_header_falls_back(self):
        exc = _http_error(429, {"Retry-After": "soon-ish"})
        assert self._wait(_retry_state(exc)) == 99.0

    def test_non_429_ignores_retry_after(self):
        exc = _http_error(503, {"Retry-After": "5"})
        assert self._wait(_retry_state(exc)) == 99.0

    def test_non_http_error_falls_back(self):
        assert self._wait(_retry_state(requests.ConnectionError("down"))) == 99.0


# --- single-sourcing across adapters ---------------------------------------


def test_max_retry_after_wait_is_single_sourced():
    # onemap no longer imports the constant (the shared wait strategy caps
    # internally); datagovsg still uses it directly in its 429 loop and must
    # reference the one definition, not redefine it.
    assert datagovsg.MAX_RETRY_AFTER_WAIT is _http.MAX_RETRY_AFTER_WAIT


def test_resource_url_builds_canonical_datastore_url():
    assert datagovsg.resource_url("d_example") == (
        f"{datagovsg.DATAGOVSG_BASE_URL}?resource_id=d_example"
    )
