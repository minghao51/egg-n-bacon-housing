"""Shared HTTP retry policy used by the API adapters.

One transient-only retry policy for every external source (URA, OneMap,
data.gov.sg), with tenacity remaining the retry engine:

- ``is_retryable_exception`` — transient means 429/5xx statuses and network
  errors; permanent 4xx responses (and per-source auth/credential errors,
  bound via the ``permanent`` parameter) fail fast. Sources with extra
  retryable semantics (e.g. OneMap's malformed-200 payload) bind them via the
  ``retryable`` parameter instead of forking the policy.
- ``retry_after_wait`` — tenacity wait strategy honoring ``Retry-After`` on
  429s (both RFC 7231 forms, via :func:`parse_retry_after`), capped at
  ``MAX_RETRY_AFTER_WAIT``, otherwise falling back to exponential backoff.
- ``parse_retry_after`` — the shared ``Retry-After`` header parser so every
  adapter treats the header identically instead of crashing on the date form
  with a ``ValueError``.
"""

import time
from collections.abc import Callable
from email.utils import parsedate_to_datetime

import requests
from tenacity import RetryCallState

MAX_RETRY_AFTER_WAIT = 60.0
"""Ceiling for ``Retry-After`` sleeps across all adapters.

A hostile or misconfigured gateway sending ``Retry-After: 3600`` must not
stall a pipeline run for an hour.
"""


def parse_retry_after(header: str | None, default: float | None = None) -> float | None:
    """Parse a ``Retry-After`` header (delta-seconds or HTTP-date) into seconds.

    Args:
        header: Raw header value, e.g. ``"120"`` or
            ``"Wed, 21 Oct 2015 07:28:00 GMT"``.
        default: Value returned when the header is missing/empty/garbage
            (``None`` by default; pass ``0.0`` to fall back to zero).

    Returns:
        Seconds to wait: the integer value for delta-seconds, or
        seconds-from-now for an HTTP-date (negative/past values clamp to 0).
        Returns ``default`` when the header is absent or unparseable.
        The parsed value is uncapped — callers apply ``MAX_RETRY_AFTER_WAIT``
        (via :func:`retry_after_wait` or directly) so an oversized
        ``Retry-After`` cannot stall a run.
    """
    if not header:
        return default
    value = header.strip()
    if value.isdigit():
        return float(value)
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return default
    if retry_at.tzinfo is None:
        return default
    return max(0.0, retry_at.timestamp() - time.time())


def is_transient_status(status: int) -> bool:
    """True for the retry-worthy HTTP statuses: 429 and 5xx.

    Permanent 4xx responses (401/403/404/413/...) cannot succeed by
    resending the same request and must fail fast.
    """
    return status == 429 or status >= 500


def is_retryable_exception(
    exc: BaseException,
    *,
    permanent: tuple[type[BaseException], ...] = (),
    retryable: tuple[type[BaseException], ...] = (),
) -> bool:
    """Shared transient-only retry predicate (tenacity-compatible).

    Transient = 429/5xx responses, network-level ``RequestException``s, and
    any exception types listed in ``retryable`` (e.g. a malformed-but-200
    payload). Permanent 4xx responses and the types listed in ``permanent``
    (auth/credential errors the caller handles by refreshing tokens) fail
    fast — ``permanent`` takes precedence over ``retryable``.

    Args:
        exc: The exception tenacity is deciding on.
        permanent: Adapter-specific exception types that must never retry.
        retryable: Adapter-specific exception types that always retry.
    """
    if isinstance(exc, permanent):
        return False
    if isinstance(exc, retryable):
        return True
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else 0
        return is_transient_status(status)
    return isinstance(exc, requests.RequestException)


def retry_after_wait(
    fallback: Callable[[RetryCallState], float],
) -> Callable[[RetryCallState], float]:
    """Build a tenacity wait strategy that honors ``Retry-After`` on 429s.

    Both RFC 7231 forms (delta-seconds and HTTP-date) are accepted via
    :func:`parse_retry_after`; the parsed wait is capped at
    ``MAX_RETRY_AFTER_WAIT``. Any other failure (or an absent/unparseable
    header) falls back to the given wait strategy, typically
    ``wait_exponential(...)``.
    """

    def _wait(retry_state: RetryCallState) -> float:
        outcome = retry_state.outcome
        exc = outcome.exception() if outcome is not None else None
        if (
            isinstance(exc, requests.HTTPError)
            and exc.response is not None
            and exc.response.status_code == 429
        ):
            retry_after = parse_retry_after(exc.response.headers.get("Retry-After"))
            if retry_after is not None:
                return min(retry_after, MAX_RETRY_AFTER_WAIT)
        return fallback(retry_state)

    return _wait


__all__ = [
    "MAX_RETRY_AFTER_WAIT",
    "is_retryable_exception",
    "is_transient_status",
    "parse_retry_after",
    "retry_after_wait",
]
