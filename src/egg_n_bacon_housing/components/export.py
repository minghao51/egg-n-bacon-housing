"""Export: Platinum layer export.

This module keeps the Hamilton export stage focused on writing the platinum
dataset. Published app assets are maintained separately from this stage.
"""

import pandas as pd

from egg_n_bacon_housing.utils.contracts import require_columns
from egg_n_bacon_housing.utils.layer_writer import LayerWriter


def unified_dataset(
    transactions_enriched: pd.DataFrame,
    writer: LayerWriter,
) -> pd.DataFrame:
    """Create the unified dataset for platinum layer.

    Args:
        transactions_enriched: Output from features transactions_enriched.

    Returns:
        DataFrame ready for analysis and dashboards.
    """
    if transactions_enriched.empty:
        return pd.DataFrame()

    df = transactions_enriched.copy()
    require_columns(df, {"price", "property_type", "transaction_date"}, "transactions_enriched")

    writer.write(df, "unified_dataset", "platinum")

    return df
