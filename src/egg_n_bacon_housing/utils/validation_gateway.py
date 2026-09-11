"""Pure validation gateway used by Hamilton validation boundaries."""

import logging
from typing import Any, Literal, TypedDict

import annotated_types
import pandas as pd

from egg_n_bacon_housing.utils.validation import validate_schema

logger = logging.getLogger(__name__)


class ValidationResult(TypedDict):
    """Validated rows and rejected rows produced by one boundary."""

    valid: pd.DataFrame
    rejected: pd.DataFrame


def extracted_validation(
    result: ValidationResult, valid_name: str, rejected_name: str
) -> dict[str, pd.DataFrame]:
    """Map the pure result to boundary-specific Hamilton extracted fields."""
    if not result["rejected"].empty:
        logger.warning("%s: %s row(s) quarantined", valid_name, len(result["rejected"]))
    return {valid_name: result["valid"], rejected_name: result["rejected"]}


def empty_extracted(
    df: pd.DataFrame, valid_name: str, rejected_name: str
) -> dict[str, pd.DataFrame]:
    """Build correctly named empty fields while retaining the input schema."""
    empty = df.iloc[0:0].copy()
    rejected = empty.copy()
    rejected["_source_index"] = pd.Series(index=rejected.index, dtype="object")
    rejected["_rejection_reason"] = pd.Series(index=rejected.index, dtype="string")
    return {valid_name: empty, rejected_name: rejected}


def vectorized_precheck(df: pd.DataFrame, model_cls: type[Any], entity_name: str) -> list[str]:
    """Run inexpensive vectorized checks for useful diagnostics."""
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
        bounds: dict[str, Any] = {}
        for metadata in field_info.metadata:
            if isinstance(metadata, annotated_types.Gt):
                bounds["gt"] = metadata.gt
            elif isinstance(metadata, annotated_types.Ge):
                bounds["ge"] = metadata.ge
            elif isinstance(metadata, annotated_types.Lt):
                bounds["lt"] = metadata.lt
            elif isinstance(metadata, annotated_types.Le):
                bounds["le"] = metadata.le
        if bounds and pd.api.types.is_numeric_dtype(series):
            non_null = series.dropna()
            for op, bound in bounds.items():
                bad = {
                    "gt": (non_null <= bound).sum,
                    "ge": (non_null < bound).sum,
                    "lt": (non_null >= bound).sum,
                    "le": (non_null > bound).sum,
                }[op]()
                if bad:
                    issues.append(f"  {field_name}: {int(bad)} values violate {op} {bound}")
    return issues


def validate_and_quarantine(
    df: pd.DataFrame,
    model_cls: type[Any],
    entity_name: str,
    sample_validation_size: int | None = None,
    large_table_policy: Literal["sample", "full", "fail"] = "full",
) -> ValidationResult:
    """Validate rows without persistence or mutation.

    The returned ``valid`` frame retains all source columns and values. The
    ``rejected`` frame retains source columns and adds ``_source_index`` and
    ``_rejection_reason``. Persistence belongs exclusively to Hamilton
    materializers.
    """
    if large_table_policy not in {"sample", "full", "fail"}:
        raise ValueError(f"Unknown large_table_policy: {large_table_policy}")

    if df.empty:
        valid, rejected = validate_schema(df, model_cls, entity_name)
        return {"valid": valid, "rejected": rejected}

    if large_table_policy == "fail":
        issues = vectorized_precheck(df, model_cls, entity_name)
        if issues:
            raise ValueError(f"Vectorized validation failed for {entity_name}: {'; '.join(issues)}")
        valid, rejected = validate_schema(df, model_cls, entity_name)
        if not rejected.empty:
            raise ValueError(
                f"Full schema validation failed for {entity_name}: "
                f"{len(rejected)}/{len(df)} invalid rows"
            )
        return {"valid": valid, "rejected": rejected}

    if (
        large_table_policy == "sample"
        and sample_validation_size is not None
        and len(df) > sample_validation_size
    ):
        issues = vectorized_precheck(df, model_cls, entity_name)
        if issues:
            logger.warning("Vectorized pre-check for %s found issues: %s", entity_name, issues)
        sample = df.sample(n=sample_validation_size, random_state=42)
        _valid_sample, rejected = validate_schema(sample, model_cls, f"{entity_name} (sample)")
        logger.warning(
            "Sample validation for %s left %s/%s rows unvalidated",
            entity_name,
            len(df) - sample_validation_size,
            len(df),
        )
        return {"valid": df, "rejected": rejected}

    valid, rejected = validate_schema(df, model_cls, entity_name)
    return {"valid": valid, "rejected": rejected}
