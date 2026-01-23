"""
Chart utilities for Singapore Housing Price Dashboard.

Provides functions for creating interactive trend charts,
comparative analysis, and statistical visualizations.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, List, Tuple
from datetime import datetime


def _get_price_column(df: pd.DataFrame) -> str:
    """
    Determine the price column name in the DataFrame.

    Checks for L3 standardized column names first, then falls back to legacy names.

    Args:
        df: DataFrame to check

    Returns:
        Name of the price column found, or empty string if none found
    """
    # Check for L3 unified dataset column (preferred)
    if 'price' in df.columns:
        return 'price'
    # Check for legacy HDB column
    if 'resale_price' in df.columns:
        return 'resale_price'
    # Check for legacy Condo column
    if 'Transacted Price ($)' in df.columns:
        return 'Transacted Price ($)'
    return ''


def aggregate_by_timeperiod(
    df: pd.DataFrame,
    granularity: str = "monthly"
) -> pd.DataFrame:
    """
    Aggregate transaction data by time period.

    Args:
        df: Transaction data with 'month' column
        granularity: 'monthly', 'quarterly', or 'yearly'

    Returns:
        Aggregated DataFrame with time period and statistics
    """
    if df.empty or 'month' not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df['date'] = pd.to_datetime(df['month'])

    # Create time period grouping
    if granularity == "monthly":
        df['period'] = df['date'].dt.to_period('M')
        period_label = "Month"
    elif granularity == "quarterly":
        df['period'] = df['date'].dt.to_period('Q')
        period_label = "Quarter"
    else:  # yearly
        df['period'] = df['date'].dt.to_period('Y')
        period_label = "Year"

    # Determine price column using helper
    price_col = _get_price_column(df)
    if not price_col or price_col not in df.columns:
        st.error(f"Price column not found in data. Available columns: {df.columns.tolist()[:10]}")
        return pd.DataFrame()

    # Aggregate metrics
    agg_funcs = {
        price_col: ['median', 'mean', 'count', 'std']
    }

    # Add floor area if available
    if 'floor_area_sqm' in df.columns:
        agg_funcs['floor_area_sqm'] = ['median']
    elif 'Area (SQFT)' in df.columns:
        agg_funcs['Area (SQFT)'] = ['median']

    # Add price per sqft if available
    if 'price_psf' in df.columns:
        agg_funcs['price_psf'] = ['median']
    elif 'Unit Price ($ PSF)' in df.columns:
        agg_funcs['Unit Price ($ PSF)'] = ['median']

    # Perform aggregation
    agg_df = df.groupby('period').agg(agg_funcs).reset_index()

    # Flatten MultiIndex columns properly
    agg_df.columns = ['_'.join(col).strip('_') if col[1] else col[0] for col in agg_df.columns.values]

    # Rename columns to standardized names
    column_mapping = {
        'period': 'period',
        f'{price_col}_median': 'median_price',
        f'{price_col}_mean': 'mean_price',
        f'{price_col}_count': 'transaction_count',
        f'{price_col}_std': 'price_std',
    }

    # Add floor area column mapping if it exists
    if 'floor_area_sqm' in df.columns:
        column_mapping['floor_area_sqm_median'] = 'median_area_sqm'
    elif 'Area (SQFT)_median' in agg_df.columns:
        column_mapping['Area (SQFT)_median'] = 'median_area_sqft'

    # Add price per sqft mapping if it exists
    if 'price_psf' in df.columns:
        column_mapping['price_psf_median'] = 'median_psf'
    elif 'Unit Price ($ PSF)_median' in agg_df.columns:
        column_mapping['Unit Price ($ PSF)_median'] = 'median_psf'

    # Rename columns
    agg_df = agg_df.rename(columns=column_mapping)

    # Convert period to string for plotting
    agg_df['period_str'] = agg_df['period'].astype(str)

    # Calculate growth rate
    agg_df['price_growth_pct'] = agg_df['median_price'].pct_change() * 100

    return agg_df


def create_trend_line_chart(
    df: pd.DataFrame,
    metric: str = "median_price",
    title: str = "Price Trend Over Time",
    color: str = "#54A24B"
) -> go.Figure:
    """
    Create interactive line chart for price trends.

    Args:
        df: Aggregated data with 'period_str' and metric column
        metric: Column name for y-axis (e.g., 'median_price', 'transaction_count')
        title: Chart title
        color: Line color

    Returns:
        Plotly Figure
    """
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['period_str'],
        y=df[metric],
        mode='lines+markers',
        name=metric.replace('_', ' ').title(),
        line=dict(color=color, width=2),
        marker=dict(size=6),
        hovertemplate=(
            "<b>%{x}</b><br>"
            f"{metric}: %{{y:,.0f}}<br>"
            "<extra></extra>"
        )
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Time Period",
        yaxis_title=metric.replace('_', ' ').title(),
        hovermode='x unified',
        template="plotly_white",
        height=500,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def create_comparison_boxplot(
    df: pd.DataFrame,
    group_column: str = "town",
    price_column: Optional[str] = None
) -> go.Figure:
    """
    Create box plot comparing prices across categories.

    Args:
        df: Transaction data
        group_column: Column to group by (e.g., 'town', 'property_type')
        price_column: Price column for y-axis (auto-detected if None)

    Returns:
        Plotly Figure with box plot
    """
    if df.empty or group_column not in df.columns:
        return go.Figure()

    # Auto-detect price column if not specified
    if price_column is None:
        price_column = _get_price_column(df)

    if not price_column or price_column not in df.columns:
        return go.Figure()

    # Get top 20 categories by transaction count
    top_categories = df[group_column].value_counts().head(20).index
    df_filtered = df[df[group_column].isin(top_categories)]

    # Sort by median price
    median_prices = df_filtered.groupby(group_column)[price_column].median().sort_values(ascending=True)
    df_filtered[group_column] = pd.Categorical(
        df_filtered[group_column],
        categories=median_prices.index,
        ordered=True
    )

    fig = go.Figure()

    for category in median_prices.index:
        category_data = df_filtered[df_filtered[group_column] == category][price_column]

        fig.add_trace(go.Box(
            y=category_data,
            name=str(category),
            boxpoints='outliers',
            jitter=0.3,
            pointpos=-1.8,
            marker_color='#54A24B'
        ))

    fig.update_layout(
        title=f"Price Distribution by {group_column.replace('_', ' ').title()}",
        xaxis_title=group_column.replace('_', ' ').title(),
        yaxis_title="Price (SGD)",
        template="plotly_white",
        height=600,
        margin=dict(l=20, r=20, t=40, b=100),
        showlegend=False
    )

    return fig


def create_multi_series_trend(
    df: pd.DataFrame,
    period_column: str = "period_str",
    value_column: str = "median_price",
    series_column: str = "town",
    top_n: int = 10
) -> go.Figure:
    """
    Create multi-series trend chart comparing categories over time.

    Args:
        df: Aggregated data
        period_column: Time period column
        value_column: Metric to plot
        series_column: Column to create series from (e.g., 'town', 'property_type')
        top_n: Number of top categories to show

    Returns:
        Plotly Figure with multiple lines
    """
    if df.empty:
        return go.Figure()

    # Get top categories by overall median
    top_categories = df.groupby(series_column)[value_column].median().nlargest(top_n).index
    df_filtered = df[df[series_column].isin(top_categories)]

    fig = go.Figure()

    colors = px.colors.qualitative.Plotly

    for idx, category in enumerate(top_categories):
        category_data = df_filtered[df_filtered[series_column] == category]

        fig.add_trace(go.Scatter(
            x=category_data[period_column],
            y=category_data[value_column],
            mode='lines+markers',
            name=str(category),
            line=dict(color=colors[idx % len(colors)], width=2),
            marker=dict(size=5)
        ))

    fig.update_layout(
        title=f"{value_column.replace('_', ' ').title()} by {series_column.replace('_', ' ').title()}",
        xaxis_title="Time Period",
        yaxis_title=value_column.replace('_', ' ').title(),
        template="plotly_white",
        height=600,
        hovermode='x unified',
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def create_volume_bar_chart(
    df: pd.DataFrame,
    period_column: str = "period_str",
    count_column: str = "transaction_count"
) -> go.Figure:
    """
    Create bar chart for transaction volume.

    Args:
        df: Aggregated data with transaction counts
        period_column: Time period column
        count_column: Count column

    Returns:
        Plotly Figure with bar chart
    """
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df[period_column],
        y=df[count_column],
        marker_color='#3498DB',
        hovertemplate=(
            "<b>%{x}</b><br>"
            f"Transactions: %{{y:,.0f}}<br>"
            "<extra></extra>"
        )
    ))

    fig.update_layout(
        title="Transaction Volume Over Time",
        xaxis_title="Time Period",
        yaxis_title="Number of Transactions",
        template="plotly_white",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def create_growth_rate_chart(
    df: pd.DataFrame,
    period_column: str = "period_str",
    growth_column: str = "price_growth_pct"
) -> go.Figure:
    """
    Create chart showing price growth rates.

    Args:
        df: Aggregated data with growth rates
        period_column: Time period column
        growth_column: Growth rate column

    Returns:
        Plotly Figure
    """
    if df.empty:
        return go.Figure()

    fig = go.Figure()

    # Add color coding for positive/negative growth
    colors = ['#27AE60' if x >= 0 else '#E74C3C' for x in df[growth_column]]

    fig.add_trace(go.Bar(
        x=df[period_column],
        y=df[growth_column],
        marker_color=colors,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Growth: %{y:.2f}%<br>"
            "<extra></extra>"
        )
    ))

    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="white",
        opacity=0.5
    )

    fig.update_layout(
        title="Price Growth Rate (%)",
        xaxis_title="Time Period",
        yaxis_title="Growth Rate (%)",
        template="plotly_white",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def create_correlation_heatmap(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None
) -> go.Figure:
    """
    Create correlation heatmap for numerical columns.

    Args:
        df: Transaction data
        columns: List of columns to include (auto-select if None)

    Returns:
        Plotly Figure with heatmap
    """
    if df.empty:
        return go.Figure()

    # Auto-select numeric columns if not specified
    if columns is None:
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        # Limit to relevant columns (include both L3 and legacy column names)
        relevant_cols = [
            'price',  # L3 unified
            'resale_price', 'floor_area_sqm', 'price_psf',
            'remaining_lease_months', 'Transacted Price ($)',
            'Area (SQFT)', 'Unit Price ($ PSF)'
        ]
        columns = [col for col in relevant_cols if col in df.columns]

    if not columns:
        return go.Figure()

    # Calculate correlation
    corr_matrix = df[columns].corr()

    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=[col.replace('_', ' ').title() for col in columns],
        y=[col.replace('_', ' ').title() for col in columns],
        colorscale='RdBu',
        zmid=0,
        text=np.round(corr_matrix.values, 2),
        texttemplate='%{text}',
        textfont={"size": 10},
        hovertemplate=(
            "<b>%{x}</b> vs <b>%{y}</b><br>"
            "Correlation: %{z:.2f}<br>"
            "<extra></extra>"
        )
    ))

    fig.update_layout(
        title="Price Correlation Matrix",
        template="plotly_white",
        height=600,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def create_scatter_analysis(
    df: pd.DataFrame,
    x_column: str = "floor_area_sqft",
    y_column: str = "price",  # Updated to L3 standardized column
    color_column: Optional[str] = None
) -> go.Figure:
    """
    Create scatter plot for analyzing relationships.

    Args:
        df: Transaction data
        x_column: X-axis column
        y_column: Y-axis column
        color_column: Optional color grouping

    Returns:
        Plotly Figure with scatter plot
    """
    # If y_column is 'price' but not found, try legacy columns
    if y_column == "price" and "price" not in df.columns:
        if "resale_price" in df.columns:
            y_column = "resale_price"
        elif "Transacted Price ($)" in df.columns:
            y_column = "Transacted Price ($)"
    if df.empty or x_column not in df.columns or y_column not in df.columns:
        return go.Figure()

    df_plot = df.dropna(subset=[x_column, y_column])

    # Sample if too many points
    if len(df_plot) > 10000:
        df_plot = df_plot.sample(n=10000, random_state=42)

    fig = px.scatter(
        df_plot,
        x=x_column,
        y=y_column,
        color=color_column if color_column else None,
        trendline="ols",
        title=f"{y_column.replace('_', ' ').title()} vs {x_column.replace('_', ' ').title()}",
        template="plotly_white",
        opacity=0.6
    )

    fig.update_layout(
        height=600,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def display_metrics_cards(
    df: pd.DataFrame,
    columns: int = 4
):
    """
    Display key metrics as cards.

    Args:
        df: Data to calculate metrics from
        columns: Number of columns for layout
    """
    if df.empty:
        return

    price_col = _get_price_column(df)
    if not price_col or price_col not in df.columns:
        st.warning(f"Price column not found in data. Available columns: {df.columns.tolist()[:10]}")
        return

    metrics = []

    # Total transactions
    metrics.append(("Total Transactions", f"{len(df):,}"))

    # Median price
    median_price = df[price_col].median()
    metrics.append(("Median Price", f"${median_price:,.0f}"))

    # Average price
    avg_price = df[price_col].mean()
    metrics.append(("Average Price", f"${avg_price:,.0f}"))

    # Price range
    min_price = df[price_col].min()
    max_price = df[price_col].max()
    metrics.append(("Price Range", f"${min_price:,.0f} - ${max_price:,.0f}"))

    # Display in columns
    cols = st.columns(columns)
    for idx, (label, value) in enumerate(metrics):
        col_idx = idx % columns
        with cols[col_idx]:
            st.metric(label, value)


# ============================================================================
# INVESTMENT MATRIX CHARTS
# ============================================================================

def aggregate_investment_metrics(
    transactions_df: pd.DataFrame,
    rental_yield_df: pd.DataFrame,
    property_type: str
) -> pd.DataFrame:
    """Aggregate by planning_area for investment scatter plot.

    Args:
        transactions_df: L3 unified dataset with property transactions
        rental_yield_df: Rental yield data from L2/rental_yield.parquet
        property_type: Filter for 'HDB' or 'Condominium'

    Returns:
        DataFrame with aggregated metrics by planning_area:
        - planning_area, property_type
        - rental_yield_pct: median rental yield
        - appreciation_pct: median YoY price change
        - transaction_count: total transactions
        - median_price: median property price
    """
    if transactions_df.empty:
        return pd.DataFrame()

    # Map property type names (L3 uses 'Condominium', L2 uses 'Condo')
    l2_property_type = 'Condo' if property_type == 'Condominium' else property_type

    # Filter by property type
    df = transactions_df[transactions_df['property_type'] == property_type].copy()

    if df.empty:
        return pd.DataFrame()

    # Use existing rental_yield_pct from L3 if available, otherwise merge
    if 'rental_yield_pct' in df.columns and df['rental_yield_pct'].notna().sum() > 0:
        pass  # Already has rental yield data
    else:
        # Merge rental yield data by town
        rental_yield_df = rental_yield_df.copy()
        rental_yield_df['town'] = rental_yield_df['town'].str.upper()
        rental_yield_df = rental_yield_df[rental_yield_df['property_type'] == l2_property_type]

        if rental_yield_df.empty:
            return pd.DataFrame()

        # Parse dates
        def parse_rental_month(val):
            val_str = str(val)
            if '-' in val_str and len(val_str.split('-')[0]) == 4:
                return pd.to_datetime(val_str)
            elif 'Q' in val_str.upper():
                year, quarter = val_str.upper().split('Q')
                month = (int(quarter) - 1) * 3 + 1
                return pd.to_datetime(f"{year}-{month:02d}-01")
            return pd.NaT

        rental_yield_df['month'] = rental_yield_df['month'].apply(parse_rental_month)
        rental_yield_df = rental_yield_df.dropna(subset=['month'])

        # Aggregate rental yield by town (median)
        rental_by_town = rental_yield_df.groupby('town')['rental_yield_pct'].median().reset_index()
        rental_by_town.columns = ['town', 'rental_yield_pct']

        # Merge with transactions
        df['town_upper'] = df['town'].str.upper()
        df = df.merge(rental_by_town, left_on='town_upper', right_on='town', how='left')
        df['rental_yield_pct'] = df['rental_yield_pct_y'].fillna(df.get('rental_yield_pct_x'))
        df = df.drop(columns=['town_upper', 'town_y', 'rental_yield_pct_y'], errors='ignore')

    # Aggregate by planning_area
    agg = df.groupby(['planning_area', 'property_type']).agg({
        'rental_yield_pct': 'median',
        'yoy_change_pct': 'median',
        'price': 'median',
        'transaction_date': 'count'
    }).reset_index()

    agg.columns = ['planning_area', 'property_type', 'rental_yield_pct', 'appreciation_pct', 'median_price', 'transaction_count']

    # Remove rows with missing key metrics
    agg = agg.dropna(subset=['rental_yield_pct', 'appreciation_pct'])

    # Sort by rental yield ascending
    agg = agg.sort_values('rental_yield_pct', ascending=True)

    return agg


def create_investment_quadrant_chart(
    df: pd.DataFrame,
    x_col: str = "rental_yield_pct",
    y_col: str = "appreciation_pct",
    size_col: str = "transaction_count",
    property_type: str = "HDB"
) -> go.Figure:
    """Create quadrant scatter chart for investment analysis.

    Args:
        df: Aggregated investment metrics DataFrame
        x_col: X-axis column (rental_yield_pct)
        y_col: Y-axis column (appreciation_pct)
        size_col: Bubble size column (transaction_count)
        property_type: Property type label for title

    Returns:
        Plotly Figure with quadrant zones and scatter points
    """
    if df.empty:
        return go.Figure()

    # Calculate median thresholds for quadrants
    x_median = df[x_col].median()
    y_median = df[y_col].median()

    # Determine axis ranges with padding
    x_min, x_max = df[x_col].min(), df[x_col].max()
    y_min, y_max = df[y_col].min(), df[y_col].max()
    x_pad = (x_max - x_min) * 0.1 if x_max > x_min else 0.5
    y_pad = (y_max - y_min) * 0.1 if y_max > y_min else 1

    fig = go.Figure()

    # Add shaded quadrant backgrounds
    quadrant_colors = {
        'best': 'rgba(46, 204, 113, 0.15)',  # Green - high yield + high appreciation
        'cash_flow': 'rgba(52, 152, 219, 0.15)',  # Blue - high yield + low appreciation
        'growth': 'rgba(155, 89, 182, 0.15)',  # Purple - low yield + high appreciation
        'avoid': 'rgba(231, 76, 60, 0.15)'  # Red - low yield + low appreciation
    }

    # Best Investment (top-right): high yield + high appreciation
    fig.add_shape(type="rect",
        x0=x_median, y0=y_median, x1=x_max + x_pad, y1=y_max + y_pad,
        fillcolor=quadrant_colors['best'], line_width=0
    )

    # Cash Flow Focus (bottom-right): high yield + low appreciation
    fig.add_shape(type="rect",
        x0=x_median, y0=y_min - y_pad, x1=x_max + x_pad, y1=y_median,
        fillcolor=quadrant_colors['cash_flow'], line_width=0
    )

    # Capital Growth (top-left): low yield + high appreciation
    fig.add_shape(type="rect",
        x0=x_min - x_pad, y0=y_median, x1=x_median, y1=y_max + y_pad,
        fillcolor=quadrant_colors['growth'], line_width=0
    )

    # Avoid (bottom-left): low yield + low appreciation
    fig.add_shape(type="rect",
        x0=x_min - x_pad, y0=y_min - y_pad, x1=x_median, y1=y_median,
        fillcolor=quadrant_colors['avoid'], line_width=0
    )

    # Add threshold lines
    fig.add_hline(y=y_median, line_dash="dash", line_color="gray", opacity=0.7)
    fig.add_vline(x=x_median, line_dash="dash", line_color="gray", opacity=0.7)

    # Add quadrant labels
    label_positions = {
        'best': dict(x=(x_median + x_max + x_pad) / 2, y=(y_median + y_max + y_pad) / 2),
        'cash_flow': dict(x=(x_median + x_max + x_pad) / 2, y=(y_min - y_pad + y_median) / 2),
        'growth': dict(x=(x_min - x_pad + x_median) / 2, y=(y_median + y_max + y_pad) / 2),
        'avoid': dict(x=(x_min - x_pad + x_median) / 2, y=(y_min - y_pad + y_median) / 2)
    }

    quadrant_labels = {
        'best': '⭐ Best Investment',
        'cash_flow': '💵 Cash Flow Focus',
        'growth': '📈 Capital Growth',
        'avoid': '⚠️ Avoid'
    }

    for quadrant, pos in label_positions.items():
        fig.add_annotation(
            x=pos['x'], y=pos['y'],
            text=quadrant_labels[quadrant],
            showarrow=False,
            font=dict(size=12, color='gray'),
            opacity=0.8
        )

    # Calculate bubble sizes (normalized for visibility)
    df['bubble_size'] = df[size_col] / df[size_col].max() * 50 + 10

    # Prepare hover text
    df['hover_text'] = (
        df['planning_area'] + '<br>' +
        'Rental Yield: ' + df[x_col].apply(lambda x: f"{x:.2f}%") + '<br>' +
        'Appreciation: ' + df[y_col].apply(lambda x: f"{x:.2f}%") + '<br>' +
        'Transactions: ' + df[size_col].apply(lambda x: f"{x:,}") + '<br>' +
        'Median Price: $' + df['median_price'].apply(lambda x: f"{x:,.0f}")
    )

    # Add scatter points
    fig.add_trace(go.Scatter(
        x=df[x_col],
        y=df[y_col],
        mode='markers',
        marker=dict(
            size=df['bubble_size'],
            color=df[y_col],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="Appreciation %", thickness=15),
            opacity=0.75,
            line=dict(width=1, color='white')
        ),
        text=df['hover_text'],
        hovertemplate="%{text}<extra></extra>",
        name='Planning Areas'
    ))

    # Update layout
    fig.update_layout(
        title=dict(
            text=f"Investment Opportunity Matrix - {property_type}<br><sub>Bubble size = Transaction volume | Median thresholds = Quadrant boundaries</sub>",
            font=dict(size=18)
        ),
        xaxis_title="Rental Yield (%)",
        yaxis_title="Year-over-Year Price Appreciation (%)",
        template="plotly_white",
        height=650,
        width=900,
        margin=dict(l=60, r=60, t=80, b=60),
        showlegend=False,
        hovermode='closest'
    )

    return fig
