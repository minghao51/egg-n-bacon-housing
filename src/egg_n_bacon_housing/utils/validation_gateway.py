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


def _ordering_bound_issues(
    field_name: str, non_null: pd.Series, bounds: dict[str, Any]
) -> list[str]:
    """Count ordering-bound (gt/ge/lt/le) violations on non-null values."""
    issues: list[str] = []
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


def vectorized_precheck(df: pd.DataFrame, model_cls: type[Any], entity_name: str) -> list[str]:
    """Run inexpensive vectorized checks for useful diagnostics.

    Covers every constraint family the pydantic models express that can be
    checked without materializing rows: required-field nulls, numeric and
    datetime ordering bounds (``gt``/``ge``/``lt``/``le`` read from the
    models' ``Field`` metadata), and string ``min_length``. Sample mode leans
    on this for 100%-coverage diagnostics — only the sampled spot-check rows
    go through pydantic — so bounds that exist only on the models must be
    declared as ``Field`` constraints to be seen here.
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
        bounds: dict[str, Any] = {}
        min_length: int | None = None
        for metadata in field_info.metadata:
            if isinstance(metadata, annotated_types.Gt):
                bounds["gt"] = metadata.gt
            elif isinstance(metadata, annotated_types.Ge):
                bounds["ge"] = metadata.ge
            elif isinstance(metadata, annotated_types.Lt):
                bounds["lt"] = metadata.lt
            elif isinstance(metadata, annotated_types.Le):
                bounds["le"] = metadata.le
            elif isinstance(metadata, annotated_types.MinLen):
                min_length = metadata.min_length
        if bounds and (
            pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series)
        ):
            issues.extend(_ordering_bound_issues(field_name, series.dropna(), bounds))
        elif min_length is not None and (
            pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)
        ):
            # Non-string cells yield NaN lengths and are ignored here; the
            # sampled pydantic spot-check still catches type errors.
            lengths = series.dropna().str.len()
            short = int((lengths < min_length).sum())
            if short:
                issues.append(
                    f"  {field_name}: {short} values shorter than min_length {min_length}"
                )
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

    Policies:
        - "full": every row is validated in deterministic chunks; rejects are
          quarantined and dropped from ``valid``.
        - "fail": like "full", but any invalid row raises instead of
          returning frames.
        - "sample": for frames larger than ``sample_validation_size``, a
          deterministic random sample goes through pydantic as a spot-check
          while ``vectorized_precheck`` covers every row for the constraints
          the models express. Sampled rejects are quarantined and dropped
          from ``valid`` (a row is never published and quarantined at the
          same time); the exact unvalidated row count is logged.
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
        # Quarantined sampled rejects must not also ride in the published
        # frame (roadmap item 22b double-count fix). ``_source_index`` holds
        # the boundary frame's index labels — the same row-identity contract
        # as full mode — so an ``isin`` mask drops exactly the rejected rows
        # while preserving source order.
        valid = df
        if not rejected.empty:
            valid = df[~df.index.isin(rejected["_source_index"])]
        return {"valid": valid, "rejected": rejected}

    valid, rejected = validate_schema(df, model_cls, entity_name)
    return {"valid": valid, "rejected": rejected}
