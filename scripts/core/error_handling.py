"""
Error handling and validation utilities for Singapore Housing Dashboard.

Provides centralized error handling, validation, and user feedback.
"""

import logging

import pandas as pd
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


def validate_coordinates(
    df: pd.DataFrame, lat_col: str = "lat", lon_col: str = "lon"
) -> tuple[bool, str]:
    """
    Validate coordinate columns in DataFrame.

    Args:
        df: DataFrame to validate
        lat_col: Latitude column name
        lon_col: Longitude column name

    Returns:
        Tuple of (is_valid, error_message)
    """
    if df.empty:
        return False, "DataFrame is empty"

    if lat_col not in df.columns:
        return False, f"Latitude column '{lat_col}' not found"

    if lon_col not in df.columns:
        return False, f"Longitude column '{lon_col}' not found"

    # Check for NaN values
    if df[lat_col].isna().all():
        return False, "All latitude values are NaN"

    if df[lon_col].isna().all():
        return False, "All longitude values are NaN"

    # Check coordinate ranges for Singapore
    valid_lat = df[lat_col].between(1.2, 1.5)
    valid_lon = df[lon_col].between(103.6, 104.0)

    if not valid_lat.any():
        return False, "No valid latitude coordinates found (should be 1.2-1.5 for Singapore)"

    if not valid_lon.any():
        return False, "No valid longitude coordinates found (should be 103.6-104.0 for Singapore)"

    return True, ""


def validate_price_column(df: pd.DataFrame) -> tuple[bool, str, str | None]:
    """
    Validate price column exists in DataFrame.

    Args:
        df: DataFrame to validate

    Returns:
        Tuple of (is_valid, error_message, price_column_name)
    """
    if df.empty:
        return False, "DataFrame is empty", None

    # Check possible price column names
    price_columns = ["resale_price", "Transacted Price ($)", "price"]

    for col in price_columns:
        if col in df.columns:
            if df[col].notna().any():
                return True, "", col

    return False, "No valid price column found", None


def validate_date_column(df: pd.DataFrame) -> tuple[bool, str, str | None]:
    """
    Validate date column exists in DataFrame.

    Args:
        df: DataFrame to validate

    Returns:
        Tuple of (is_valid, error_message, date_column_name)
    """
    if df.empty:
        return False, "DataFrame is empty", None

    # Check possible date column names
    date_columns = ["month", "sale_date", "Sale Date", "date"]

    for col in date_columns:
        if col in df.columns:
            return True, "", col

    return False, "No valid date column found", None


def safe_load_data(load_func, func_name: str = "Data loading") -> pd.DataFrame | None:
    """
    Safely load data with error handling.

    Args:
        load_func: Function that loads data
        func_name: Name of the operation for logging

    Returns:
        DataFrame or None if error occurs
    """
    try:
        df = load_func()
        if df is None or df.empty:
            st.warning(f"{func_name} returned no data")
            return None
        return df
    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
        logger.error(f"File not found in {func_name}: {e}")
        return None
    except Exception as e:
        st.error(f"Error in {func_name}: {str(e)}")
        logger.error(f"Error in {func_name}: {e}", exc_info=True)
        return None


def safe_filter_data(df: pd.DataFrame, filters: dict, func_name: str = "Filtering") -> pd.DataFrame:
    """
    Safely filter data with error handling.

    Args:
        df: DataFrame to filter
        filters: Dictionary of filters to apply
        func_name: Name of the operation for logging

    Returns:
        Filtered DataFrame (original if error occurs)
    """
    if df.empty:
        return df

    try:
        # Apply filters with validation
        filtered_df = df.copy()

        # Property type filter
        if "property_types" in filters and filters["property_types"]:
            if "property_type" in filtered_df.columns:
                filtered_df = filtered_df[
                    filtered_df["property_type"].isin(filters["property_types"])
                ]

        # Town filter
        if "towns" in filters and filters["towns"]:
            if "town" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["town"].isin(filters["towns"])]

        # Price range filter
        if "price_range" in filters and filters["price_range"]:
            price_col = (
                "resale_price" if "resale_price" in filtered_df.columns else "Transacted Price ($)"
            )
            if price_col in filtered_df.columns:
                min_price, max_price = filters["price_range"]
                filtered_df = filtered_df[filtered_df[price_col].between(min_price, max_price)]

        # Date range filter
        if "date_range" in filters and filters["date_range"]:
            date_col = "month" if "month" in filtered_df.columns else "sale_date"
            if date_col in filtered_df.columns:
                start_date, end_date = filters["date_range"]
                filtered_df = filtered_df[
                    pd.to_datetime(filtered_df[date_col]).between(start_date, end_date)
                ]

        return filtered_df

    except Exception as e:
        st.error(f"Error in {func_name}: {str(e)}")
        logger.error(f"Error in {func_name}: {e}", exc_info=True)
        return df  # Return original dataframe on error


def show_data_quality_warning(df: pd.DataFrame):
    """
    Show warnings about data quality issues.

    Args:
        df: DataFrame to check
    """
    warnings = []

    # Check for missing coordinates
    if "lat" in df.columns and "lon" in df.columns:
        missing_coords = df[["lat", "lon"]].isna().any(axis=1).sum()
        if missing_coords > 0:
            pct_missing = (missing_coords / len(df)) * 100
            warnings.append(
                f"{missing_coords:,} properties ({pct_missing:.1f}%) have missing coordinates"
            )

    # Check for missing prices
    price_col = "resale_price" if "resale_price" in df.columns else "Transacted Price ($)"
    if price_col in df.columns:
        missing_prices = df[price_col].isna().sum()
        if missing_prices > 0:
            pct_missing = (missing_prices / len(df)) * 100
            warnings.append(
                f"{missing_prices:,} transactions ({pct_missing:.1f}%) have missing prices"
            )

    # Display warnings
    if warnings:
        st.warning("⚠️ Data Quality Issues:\n" + "\n".join(f"- {w}" for w in warnings))


def show_loading_spinner(message: str = "Loading..."):
    """
    Context manager for loading operations with error handling.

    Args:
        message: Message to display during loading

    Returns:
        Context manager
    """
    return st.spinner(message)


def handle_plotly_error(fig, error_message: str = "Error creating chart"):
    """
    Handle Plotly chart errors gracefully.

    Args:
        fig: Plotly figure to display
        error_message: Message to show if error occurs
    """
    try:
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"{error_message}: {str(e)}")
        logger.error(f"Plotly error: {e}", exc_info=True)


def validate_filters(filters: dict) -> tuple[bool, str]:
    """
    Validate filter parameters.

    Args:
        filters: Dictionary of filter parameters

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate price range
    if "price_range" in filters and filters["price_range"]:
        min_price, max_price = filters["price_range"]
        if min_price > max_price:
            return False, "Minimum price cannot be greater than maximum price"
        if min_price < 0 or max_price < 0:
            return False, "Price values must be positive"

    # Validate date range
    if "date_range" in filters and filters["date_range"]:
        start_date, end_date = filters["date_range"]
        if start_date > end_date:
            return False, "Start date cannot be after end date"

    return True, ""


def show_info_tooltip(text: str, icon: str = "ℹ️"):
    """
    Display an info tooltip with expander.

    Args:
        text: Information text to display
        icon: Icon to use
    """
    with st.expander(f"{icon} More Info"):
        st.markdown(text)


def get_performance_warning(row_count: int, view_mode: str = "scatter") -> str | None:
    """
    Get performance warning based on data size.

    Args:
        row_count: Number of rows in dataset
        view_mode: Type of visualization

    Returns:
        Warning message or None
    """
    if view_mode == "scatter" and row_count > 5000:
        return (
            f"⚠️ Showing {row_count:,} points in scatter mode. "
            f"For better performance, consider applying more filters or switching to heatmap mode."
        )
    elif row_count > 20000:
        return (
            f"⚠️ Large dataset ({row_count:,} rows). "
            f"Consider filtering by date range or location for better performance."
        )
    return None


def log_data_info(df: pd.DataFrame, data_name: str = "Dataset"):
    """
    Log information about dataset for debugging.

    Args:
        df: DataFrame to log info about
        data_name: Name of the dataset
    """
    logger.info(f"{data_name} Info:")
    logger.info(f"  Shape: {df.shape}")
    logger.info(f"  Columns: {list(df.columns)}")
    logger.info(f"  Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")

    if "month" in df.columns:
        logger.info(f"  Date range: {df['month'].min()} to {df['month'].max()}")

    if "town" in df.columns:
        logger.info(f"  Towns: {df['town'].nunique()} unique")

    if "property_type" in df.columns:
        logger.info(f"  Property types: {df['property_type'].unique()}")


def create_error_boundary(func, *args, error_message: str = "An error occurred", **kwargs):
    """
    Execute function with error boundary.

    Args:
        func: Function to execute
        *args: Positional arguments for function
        error_message: Message to display if error occurs
        **kwargs: Keyword arguments for function

    Returns:
        Function result or None if error occurs
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        st.error(f"{error_message}: {str(e)}")
        logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
        return None
