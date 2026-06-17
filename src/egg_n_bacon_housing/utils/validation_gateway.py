"""ValidationGateway: validate, quarantine, and persist in one call.

Absorbs the validate_schema + quarantine_path + save_parquet pattern
that was repeated across 6 DAG nodes in 02_cleaning and 03_features.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import annotated_types
import pandas as pd

from egg_n_bacon_housing.utils.io_helpers import save_parquet
from egg_n_bacon_housing.utils.validation import validate_schema

logger = logging.getLogger(__name__)


def vectorized_precheck(
    df: pd.DataFrame,
    model_cls: type[Any],
    entity_name: str,
) -> list[str]:
    """Run fast vectorized checks against Pydantic model constraints.

    Scans the full DataFrame with pandas (no per-row Pydantic validation)
    to surface systemic data-quality issues before sampling.

    Args:
        df: DataFrame to check.
        model_cls: Pydantic model class with field constraints.
        entity_name: Human-readable name for log messages.

    Returns:
        List of human-readable issue descriptions (empty if clean).
    """
    issues: list[str] = []
    total = len(df)

    for field_name, field_info in model_cls.model_fields.items():
        if field_name not in df.columns:
            continue

        series = df[field_name]

        if field_info.is_required():
            null_count = int(series.isna().sum())
            if null_count:
                pct = null_count / total * 100 if total else 0
                issues.append(f"  {field_name}: {null_count} null ({pct:.1f}%) — required field")

        bounds: dict[str, float] = {}
        for m in field_info.metadata:
            if isinstance(m, annotated_types.Gt):
                bounds["gt"] = m.gt
            elif isinstance(m, annotated_types.Ge):
                bounds["ge"] = m.ge
            elif isinstance(m, annotated_types.Lt):
                bounds["lt"] = m.lt
            elif isinstance(m, annotated_types.Le):
                bounds["le"] = m.le

        if bounds and pd.api.types.is_numeric_dtype(series):
            non_null = series.dropna()
            for op, bound in bounds.items():
                if op == "gt":
                    bad = int((non_null <= bound).sum())
                elif op == "ge":
                    bad = int((non_null < bound).sum())
                elif op == "lt":
                    bad = int((non_null >= bound).sum())
                elif op == "le":
                    bad = int((non_null > bound).sum())
                else:
                    continue
                if bad:
                    issues.append(f"  {field_name}: {bad} values violate {op} {bound}")

    return issues


def validate_and_quarantine(
    df: pd.DataFrame,
    model_cls: type[Any],
    entity_name: str,
    layer_dir: Path,
    filename: str,
    sample_validation_size: int | None = None,
) -> pd.DataFrame:
    """Validate DataFrame against schema, quarantine failures, persist both.

    Args:
        df: DataFrame to validate.
        model_cls: Pydantic model class to validate against.
        entity_name: Human-readable name for logging (e.g. "HDB").
        layer_dir: Directory for valid output and quarantine subdirectory.
        filename: Output parquet filename (e.g. "cleaned_hdb_transactions.parquet").
        sample_validation_size: When set and df exceeds this row count,
            validate only a random sample to catch schema violations while
            saving all rows. Use for large fact tables (~1M rows).

    Returns:
        Full validation: valid DataFrame with all original columns.
        Sample validation: the original unvalidated DataFrame (all rows),
        since only a random sample was schema-checked.
    """
    if df.empty:
        logger.warning("Empty DataFrame passed to validation for %s", entity_name)
        return df

    if sample_validation_size is not None and len(df) > sample_validation_size:
        logger.info(
            "Large table detected (%s rows) — sampling %s for %s validation",
            len(df),
            sample_validation_size,
            entity_name,
        )
        precheck_issues = vectorized_precheck(df, model_cls, entity_name)
        if precheck_issues:
            logger.warning(
                "Vectorized pre-check for %s found %s issue(s):\n%s",
                entity_name,
                len(precheck_issues),
                "\n".join(precheck_issues),
            )
        sample = df.sample(n=sample_validation_size, random_state=42)
        valid_sample, quarantine_sample = validate_schema(
            sample,
            model_cls,
            f"{entity_name} (sample)",
        )
        save_parquet(df, layer_dir / filename, f"validated {entity_name}")
        if not quarantine_sample.empty:
            logger.warning(
                "Sample validation quarantined %s/%s rows for %s — "
                "full table saved but may contain invalid records",
                len(quarantine_sample),
                sample_validation_size,
                entity_name,
            )
            timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
            q_dir = layer_dir / "_quarantine"
            q_path = q_dir / f"{entity_name}_sample_{timestamp}.parquet"
            save_parquet(quarantine_sample, q_path, f"quarantined {entity_name} (sample)")
        return df

    valid_df, quarantine_df = validate_schema(df, model_cls, entity_name)

    save_parquet(valid_df, layer_dir / filename, f"validated {entity_name}")

    if not quarantine_df.empty:
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        q_dir = layer_dir / "_quarantine"
        q_path = q_dir / f"{entity_name}_{timestamp}.parquet"
        save_parquet(quarantine_df, q_path, f"quarantined {entity_name}")

    return valid_df
