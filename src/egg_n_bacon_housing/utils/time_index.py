"""TimeIndex: shared month-period derivation for time-grouped operations.

Deduplicates dt.to_period("M").astype(str) from 4 locations
(features, metrics) into one function.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def ensure_month_column(
    df: pd.DataFrame,
    date_column: str = "transaction_date",
    month_column: str = "month",
) -> pd.DataFrame:
    """Derive a month column from a date column if it doesn't already exist.

    The month format is Period('M').astype(str) — e.g. "2024-01".
    Returns the DataFrame with a guaranteed month_column.
    Returns an empty DataFrame if the date column is missing and month
    column cannot be derived.

    Args:
        df: Input DataFrame.
        date_column: Name of the date column to derive from.
        month_column: Name of the target month column.

    Returns:
        DataFrame with month_column present, or empty DataFrame if
        derivation is impossible.
    """
    if month_column in df.columns:
        return df

    if date_column not in df.columns:
        logger.error("No %s or %s column — cannot derive month", date_column, month_column)
        return pd.DataFrame()

    df = df.copy()
    df[month_column] = (
        pd.to_datetime(df[date_column], errors="coerce").dt.to_period("M").astype(str)
    )
    return df
