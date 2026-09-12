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

    Rows with null required fields are routed to the quarantine frame with a
    ``_rejection_reason`` of ``"missing required field(s): ..."`` — they are
    never silently dropped. Pydantic cannot flag these rows itself (NaN is a
    valid float), which is why the prefilter exists; the destination is the
    quarantine frame, not deletion.

    Returns:
        Tuple of (valid_df with ALL original columns, quarantine_df with
        _rejection_reason column).
    """
    # A non-unique index makes df.loc[list_of_labels] return one row per
    # occurrence of each label, multiplying valid rows. Reset once up front so
    # .loc selections stay 1:1; unique-index frames keep their original index
    # and row order untouched.
    if not df.index.is_unique:
        logger.debug("%s frame has a non-unique index; resetting for row-safe .loc", entity_name)
        df = df.reset_index(drop=True)

    if df.empty:
        empty = df.iloc[0:0].copy()
        quarantine = empty.copy()
        quarantine["_source_index"] = pd.Series(index=quarantine.index, dtype="object")
        quarantine["_rejection_reason"] = pd.Series(index=quarantine.index, dtype="string")
        return empty, quarantine

    quarantine_records: list[dict] = []

    required_fields = {
        name for name, field in model_cls.model_fields.items() if field.is_required()
    }
    existing_required = [col for col in required_fields if col in df.columns]
    if existing_required:
        missing_mask = df[existing_required].isna().any(axis=1)
        if missing_mask.any():
            missing_flags = df.loc[missing_mask, existing_required].isna()
            for idx, flags in missing_flags.iterrows():
                missing_cols = [col for col in existing_required if bool(flags[col])]
                record = df.loc[idx].to_dict()
                record["_source_index"] = idx
                record["_rejection_reason"] = (
                    f"missing required field(s): {', '.join(missing_cols)}"
                )
                quarantine_records.append(record)
            logger.warning(
                "Required-field prefilter quarantined %s %s record(s)",
                int(missing_mask.sum()),
                entity_name,
            )
            df = df.loc[~missing_mask]
            if df.empty:
                logger.warning("No %s records left after required-field prefilter", entity_name)
                return df.iloc[0:0].copy(), pd.DataFrame(quarantine_records)

    model_fields = set(model_cls.model_fields.keys())
    common_cols = [c for c in df.columns if c in model_fields]
    df_validate = df[common_cols]

    # Vectorized null-scrub, done ONCE before chunking. This replaces a
    # per-cell Python loop (`for record: for key, value:`) that issued one
    # pd.isna call per row x column — ~10^8 calls per run across the large
    # fact tables. Semantics are identical: pydantic treats NaN/NaT/pd.NA as
    # valid values (NaN is a legitimate float), so null scalars must become
    # None; `notna()` + `where` classify and replace in one vectorized pass
    # per column, and container cells (lists, dicts, arrays) count as
    # non-null under both paths and pass through untouched. The conversion
    # is skipped entirely for frames with no nulls, so boxing never runs on
    # data that needs no scrubbing.
    notna_mask = df_validate.notna()
    if not bool(notna_mask.all().all()):
        df_validate = df_validate.astype(object).where(notna_mask, None)

    adapter = TypeAdapter(list[model_cls])  # type: ignore[valid-type]
    valid_indices: list = []
    indices = df.index.tolist()
    chunk_size = 5000

    for chunk_start in range(0, len(df_validate), chunk_size):
        chunk_idx = indices[chunk_start : chunk_start + chunk_size]
        # Materialize one chunk at a time. A whole-frame to_dict(orient=
        # "records") would expand the entire table into dicts (~5-10x memory)
        # before any chunking happens. Nulls were already scrubbed to None
        # in one vectorized pass above, so chunks need no per-record fixup.
        chunk = df_validate.iloc[chunk_start : chunk_start + chunk_size].to_dict(orient="records")
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
                    original_row["_source_index"] = chunk_idx[i]
                    original_row["_rejection_reason"] = str(e)
                    quarantine_records.append(original_row)

    quarantine_count = len(quarantine_records)
    if quarantine_count:
        logger.warning("Validation failed for %s %s records", quarantine_count, entity_name)

    if quarantine_records:
        quarantine_df = pd.DataFrame(quarantine_records)
    else:
        quarantine_df = df.iloc[0:0].copy()
        quarantine_df["_source_index"] = pd.Series(index=quarantine_df.index, dtype="object")
        quarantine_df["_rejection_reason"] = pd.Series(index=quarantine_df.index, dtype="string")

    if valid_indices:
        valid_df = df.loc[valid_indices]
        logger.info("Validated %s %s records successfully", len(valid_df), entity_name)
        return valid_df, quarantine_df
    logger.warning("No %s records passed validation", entity_name)
    return df.iloc[0:0].copy(), quarantine_df
