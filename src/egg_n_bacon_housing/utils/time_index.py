"""TimeIndex: shared month-period derivation for time-grouped operations.

Deduplicates dt.to_period("M").astype(str) from 4 locations
(features, metrics) into one function.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def _drop_unparseable_months(df: pd.DataFrame, date_column: str, month_column: str) -> pd.DataFrame:
    """Drop NaT month rows; warn with column name and dropped/kept counts."""
    keep = df[month_column].notna() & (df[month_column] != "NaT")
    dropped = int((~keep).sum())
    if dropped:
        logger.warning(
            "month derivation from %s dropped %d/%d rows (unparseable dates); kept %d",
            date_column,
            dropped,
            len(df),
            int(keep.sum()),
        )
    return df[keep]


def ensure_month_column(
    df: pd.DataFrame,
    date_column: str = "transaction_date",
    month_column: str = "month",
) -> pd.DataFrame:
    """Derive a month column from a date column if it doesn't already exist.

    The month format is Period('M').astype(str) — e.g. "2024-01". Rows whose
    month cannot be parsed are dropped; when any row is dropped, a warning
    logs the source column name with the dropped and kept counts so silent
    aggregation shrinkage is observable.

    Raises:
        ValueError: If neither ``month_column`` nor ``date_column`` exists.
            Caller audit (WS14): every call site structurally guarantees one
            of the two columns — ``feature_rental`` guards its required
            sale/rent columns, ``feature_transactions`` enforces the time
            contract (raises without ``transaction_date``, always sets
            ``month``), and ``metrics`` consumes the upstream
            ``transactions_enriched`` contract (empty frames short-circuit).
            A missing column is a schema break, not data sparsity.

    Args:
        df: Input DataFrame.
        date_column: Name of the date column to derive from.
        month_column: Name of the target month column.

    Returns:
        DataFrame with month_column present and unparseable months dropped.
    """
    if month_column in df.columns:
        # Never allow missing dates to become the literal string ``NaT``.
        result = df.copy()
        values = result[month_column]
        if isinstance(values.dtype, pd.PeriodDtype):
            result[month_column] = values.astype("period[M]").astype("string")
        else:
            parsed = pd.to_datetime(values, errors="coerce")
            result[month_column] = parsed.dt.to_period("M").astype("string")
        return _drop_unparseable_months(result, date_column, month_column)

    if date_column not in df.columns:
        raise ValueError(
            f"ensure_month_column: schema break — neither {month_column!r} nor "
            f"{date_column!r} column exists; cannot derive month"
        )

    df = df.copy()
    df[month_column] = (
        pd.to_datetime(df[date_column], errors="coerce").dt.to_period("M").astype("string")
    )
    return _drop_unparseable_months(df, date_column, month_column)
