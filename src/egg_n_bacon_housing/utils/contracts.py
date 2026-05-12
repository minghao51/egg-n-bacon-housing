"""Data contract helpers for stage boundary validation."""

from __future__ import annotations

import pandas as pd


def require_columns(df: pd.DataFrame, required: set[str], dataset_name: str) -> None:
    """Raise ValueError when required columns are missing."""
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{dataset_name} is missing required columns: {missing}")
