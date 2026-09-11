"""Shared HTTP helpers used by the API adapters.

Currently owns ``Retry-After`` parsing (RFC 7231 allows both delta-seconds and
HTTP-date forms) so every adapter treats the header identically instead of
crashing on the date form with a ``ValueError``.
"""

import time
from email.utils import parsedate_to_datetime


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
        The parsed value is uncapped — callers apply their own ceiling (the
        OneMap and data.gov.sg adapters both cap at 60s) so an oversized
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
