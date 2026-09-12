"""Export dataframe construction for the platinum layer."""

import logging
from typing import Literal

import pandas as pd
from hamilton.function_modifiers import extract_fields, hamilton_exclude

from egg_n_bacon_housing.schemas.platinum_models import HUnifiedRecord
from egg_n_bacon_housing.utils.contracts import require_columns
from egg_n_bacon_housing.utils.validation_gateway import (
    empty_extracted,
    extracted_validation,
    validate_and_quarantine,
)

logger = logging.getLogger(__name__)


@hamilton_exclude
def unified_dataset(*args, **kwargs) -> pd.DataFrame:
    # Persistence is owned exclusively by ``materialize_unified_dataset``.
    return validate_unified_dataset(*args, **kwargs)["unified_dataset"]


@extract_fields({"unified_dataset": pd.DataFrame, "unified_dataset_quarantine": pd.DataFrame})
def validate_unified_dataset(
    transactions_enriched: pd.DataFrame,
    large_table_validation_policy: Literal["sample", "full", "fail"] = "sample",
    sample_validation_size: int = 10_000,
) -> dict[str, pd.DataFrame]:
    """Create the unified dataset for platinum layer.

    Every row is validated against the platinum contract (``HUnifiedRecord``),
    respecting the injected large-table policy. Invalid rows are returned to
    the quarantine materializer and dropped from the published frame.

    Re-validating gold-validated rows at the platinum boundary is deliberate
    (roadmap item 22d): the platinum quarantine trail is a published contract
    (``materialize_unified_dataset_quarantine``), so this boundary routes
    through the same gateway as gold rather than trusting the upstream frame.
    No defensive copy is taken — the gateway never mutates its input, and
    copying the ~1.2M-row frame just to hand it to a read-only validator was
    the largest avoidable cost of this node.

    Args:
        transactions_enriched: Output from features transactions_enriched.
        large_table_validation_policy: Injected policy for the ~1M-row table.
        sample_validation_size: Sample size used when the policy is "sample".

    Returns:
        DataFrame ready for analysis and dashboards.
    """
    if transactions_enriched.empty:
        return empty_extracted(
            transactions_enriched, "unified_dataset", "unified_dataset_quarantine"
        )

    require_columns(
        transactions_enriched,
        {"price", "property_type", "transaction_date"},
        "transactions_enriched",
    )

    return extracted_validation(
        validate_and_quarantine(
            transactions_enriched,
            HUnifiedRecord,
            "unified_dataset",
            sample_validation_size=sample_validation_size,
            large_table_policy=large_table_validation_policy,
        ),
        "unified_dataset",
        "unified_dataset_quarantine",
    )
