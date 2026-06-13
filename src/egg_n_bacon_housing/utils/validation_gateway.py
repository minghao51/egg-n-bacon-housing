"""ValidationGateway: validate, quarantine, and persist in one call.

Absorbs the validate_schema + quarantine_path + save_parquet pattern
that was repeated across 6 DAG nodes in 02_cleaning and 03_features.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from egg_n_bacon_housing.utils.io_helpers import save_parquet
from egg_n_bacon_housing.utils.validation import validate_schema

logger = logging.getLogger(__name__)


def validate_and_quarantine(
    df: pd.DataFrame,
    model_cls: type[Any],
    entity_name: str,
    layer_dir: Path,
    filename: str,
) -> pd.DataFrame:
    """Validate DataFrame against schema, quarantine failures, persist both.

    Args:
        df: DataFrame to validate.
        model_cls: Pydantic model class to validate against.
        entity_name: Human-readable name for logging (e.g. "HDB").
        layer_dir: Directory for valid output and quarantine subdirectory.
        filename: Output parquet filename (e.g. "cleaned_hdb_transactions.parquet").

    Returns:
        Valid DataFrame with all original columns.
    """
    if df.empty:
        logger.warning("Empty DataFrame passed to validation for %s", entity_name)
        return df

    valid_df, quarantine_df = validate_schema(df, model_cls, entity_name)

    save_parquet(valid_df, layer_dir / filename, f"validated {entity_name}")

    if not quarantine_df.empty:
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        q_dir = layer_dir / "_quarantine"
        q_path = q_dir / f"{entity_name}_{timestamp}.parquet"
        save_parquet(quarantine_df, q_path, f"quarantined {entity_name}")

    return valid_df
