"""Helper functions for L2 feature engineering."""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Conversion constants
SQM_TO_SQFT = 10.764
SQFT_TO_SQM = 1 / SQM_TO_SQFT


def extract_lease_info(lease_str: str) -> tuple[int | None, str]:
    """
    Extract lease information from tenure string.

    Args:
        lease_str: Tenure string like "99 yrs lease commencing from 2007" or "Freehold"

    Returns:
        Tuple of (commencing_year or None, hold_type)
    """
    if lease_str == "Freehold":
        return None, "freehold"

    parts = lease_str.split(" ")

    # Check if last part is a year
    if parts[-1].isdigit() and 1900 <= int(parts[-1]) <= 2100:
        return int(parts[-1]), "leasehold"

    return None, "leasehold"


def extract_floor_range(floor_level: str) -> tuple[str, str]:
    """
    Extract first two digits from floor range string.

    Args:
        floor_level: String like "01 to 05"

    Returns:
        Tuple of (low_floor, high_floor) as strings
    """
    digits_parts = floor_level.split(" to ")
    return (digits_parts[0], digits_parts[1])


def infer_room_count(property_sub_type: str, area_sqft: float) -> int:
    """
    Infer room count from property type and floor area.

    For properties without explicit room numbers, estimates based on:
    - Typical room size: 150-250 sqft per room
    - Assumes bedrooms + living room

    Args:
        property_sub_type: Property type string (e.g., "3 room", "executive")
        area_sqft: Floor area in square feet

    Returns:
        Estimated room count (1-6)
    """
    # If type contains room number, extract it
    if "room" in property_sub_type.lower():
        try:
            return int(property_sub_type[0])
        except (ValueError, IndexError):
            pass

    # Estimate from floor area (random within realistic range)
    # Assuming 150-250 sqft per room
    estimated = area_sqft / np.random.randint(150, 250) / SQM_TO_SQFT

    return np.clip(int(estimated), 1, 6)


def estimate_bathroom_count(area_sqft: float) -> int:
    """
    Estimate bathroom count from floor area.

    Typical assumption: 1 bathroom per 350-450 sqft

    Args:
        area_sqft: Floor area in square feet

    Returns:
        Estimated bathroom count (1-4)
    """
    estimated = area_sqft / np.random.randint(35, 45) / SQM_TO_SQFT

    return np.clip(int(estimated), 1, 4)


def calculate_floor_number(floor_low: str, floor_high: str) -> int:
    """
    Calculate a representative floor number from floor range.

    Takes the floor range and returns a random floor within that range.

    Args:
        floor_low: Low floor (e.g., "01")
        floor_high: High floor (e.g., "05")

    Returns:
        Floor number as integer
    """
    try:
        # Remove "B" suffix if present (basement floors)
        low_clean = floor_low.replace("B", "-").lstrip("-").zfill(2)
        high_clean = floor_high.replace("B", "-").lstrip("-").zfill(2)

        low_int = int(low_clean)
        high_int = int(high_clean)

        # Return random floor in range
        return int(np.random.randint(low_int, high_int + 1))

    except (ValueError, AttributeError):
        # Default to mid-range if parsing fails
        return 3


def process_private_property_tenure(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process tenure information for private properties using vectorized operations.

    More efficient alternative to df.apply() for extracting lease info.

    Args:
        df: DataFrame with 'tenure' column

    Returns:
        DataFrame with lease_start_yr and hold_type columns added
    """
    df = df.copy()

    # Initialize new columns
    df["lease_start_yr"] = None
    df["hold_type"] = "leasehold"

    # Process freehold
    freehold_mask = df["tenure"] == "Freehold"
    df.loc[freehold_mask, "hold_type"] = "freehold"

    # Process leasehold with years
    leasehold_mask = ~freehold_mask
    df.loc[leasehold_mask, "lease_start_yr"] = (
        df.loc[leasehold_mask, "tenure"]
        .str.split()
        .str[-1]
        .astype(str)
        .pipe(lambda x: pd.to_numeric(x, errors="coerce"))
        .astype("Int64")
    )

    return df


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize private property column names.

    Removes special characters, converts to lowercase, and cleans up naming.

    Args:
        df: DataFrame with raw column names

    Returns:
        DataFrame with standardized column names
    """
    df = df.copy()

    # Remove parentheticals and special characters
    df.columns = (
        df.columns.str.replace(r"\((.*?)\)", r"_\1", regex=True)
        .str.replace(r"\)$", "", regex=True)
        .str.replace(r"[^a-zA-Z0-9_]", "", regex=True)
        .str.replace(r"_$", "", regex=True)
        .str.lower()
    )

    return df
