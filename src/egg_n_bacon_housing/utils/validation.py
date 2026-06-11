"""Shared schema validation utility for silver and gold layers."""

import logging
from typing import Any

import pandas as pd
from pydantic import TypeAdapter, ValidationError

logger = logging.getLogger(__name__)


def validate_schema(
    df: pd.DataFrame,
    model_cls: type[Any],
    entity_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate DataFrame rows against a Pydantic schema.

    Validates only schema-matching columns but preserves all original columns
    in the returned valid DataFrame.

    Returns:
        Tuple of (valid_df with ALL original columns, quarantine_df with
        _rejection_reason column).
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    required_fields = {
        name for name, field in model_cls.model_fields.items() if field.is_required()
    }
    existing_required = [col for col in required_fields if col in df.columns]
    if existing_required:
        df = df.dropna(subset=existing_required)
        if df.empty:
            logger.warning("No %s records left after required-field prefilter", entity_name)
            return pd.DataFrame(), pd.DataFrame()

    model_fields = set(model_cls.model_fields.keys())
    common_cols = [c for c in df.columns if c in model_fields]
    df_validate = df[common_cols]

    adapter = TypeAdapter(list[model_cls])  # type: ignore[valid-type]
    valid_indices: list = []
    quarantine_records: list[dict] = []
    records = df_validate.to_dict(orient="records")
    indices = df.index.tolist()
    chunk_size = 5000

    for chunk_start in range(0, len(records), chunk_size):
        chunk = records[chunk_start : chunk_start + chunk_size]
        chunk_idx = indices[chunk_start : chunk_start + chunk_size]
        try:
            adapter.validate_python(chunk)
            valid_indices.extend(chunk_idx)
        except ValidationError:
            for i, row in enumerate(chunk):
                try:
                    model_cls(**row)
                    valid_indices.append(chunk_idx[i])
                except ValidationError as e:
                    original_row = df.loc[chunk_idx[i]].to_dict()
                    original_row["_rejection_reason"] = str(e)
                    quarantine_records.append(original_row)

    quarantine_count = len(quarantine_records)
    if quarantine_count:
        logger.warning("Validation failed for %s %s records", quarantine_count, entity_name)

    quarantine_df = pd.DataFrame(quarantine_records) if quarantine_records else pd.DataFrame()

    if valid_indices:
        valid_df = df.loc[valid_indices]
        logger.info("Validated %s %s records successfully", len(valid_df), entity_name)
        return valid_df, quarantine_df
    logger.warning("No %s records passed validation", entity_name)
    return pd.DataFrame(), quarantine_df
