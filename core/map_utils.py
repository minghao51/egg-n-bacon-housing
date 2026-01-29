"""
Map visualization utilities for Singapore Housing Price Dashboard.

This module provides functions to create interactive maps using
Plotly with OpenStreetMap tiles.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import h3
import json
import geopandas as gpd
from pathlib import Path
from typing import Optional, List, Tuple

# Constants
SINGAPORE_CENTER = {"lat": 1.3521, "lon": 103.8198}
SINGAPORE_ZOOM = 11

# Color scales for price visualization
PRICE_COLORSCALE = [
    [0.0, "#2E5EAA"],    # Blue (low)
    [0.25, "#54A24B"],   # Green
    [0.5, "#F4D03F"],    # Yellow
    [0.75, "#DC7633"],   # Orange
    [1.0, "#CB4335"]     # Red (high)
]

# Theme selection - Plotly native styles
# Available styles: https://plotly.com/python/mapbox-layers/#mapbox-tile-layers
MAP_STYLES = {
    "Default (OSM)": "open-street-map",
    "Positron (Light)": "carto-positron",
    "Dark Matter": "carto-darkmatter",
    "Voyager": "carto-voyager",
    "Basic Light": "white-bg",
    "Basic Dark": "basic",
}

DARK_THEME = "carto-darkmatter"
LIGHT_THEME = "open-street-map"
POSITRON_THEME = "carto-positron"  # Clean, minimal light theme
DEFAULT_THEME = LIGHT_THEME  # Changed to light theme

# Color column options for map visualization
COLOR_BY_OPTIONS = {
    "Median Price": "median_price",
    "Median PSF": "median_psf",
    "Transaction Count": "count",
    "Average Price": "mean_price",
}


def get_available_map_styles():
    """Return list of available map style display names."""
    return list(MAP_STYLES.keys())


def get_map_style_value(style_name: str) -> str:
    """Convert display name to Plotly style value."""
    return MAP_STYLES.get(style_name, LIGHT_THEME)


def get_available_color_by_options():
    """Return list of available color-by display names."""
    return list(COLOR_BY_OPTIONS.keys())


def get_color_column_value(color_by_name: str) -> str:
    """Convert display name to column name."""
    return COLOR_BY_OPTIONS.get(color_by_name, "median_price")


def aggregate_by_planning_area(
    df: pd.DataFrame,
    color_column: str = "price"
) -> pd.DataFrame:
    """
    Aggregate property data by planning area with statistics.

    Args:
        df: DataFrame with property data including 'planning_area', 'lat', 'lon'
        color_column: Column to use for color coding (e.g., 'price', 'price_psf')

    Returns:
        Aggregated DataFrame with statistics per planning area:
        - planning_area, lat, lon (centroids)
        - count, median_price, mean_price, median_psf
        - min_price, max_price, q1_price, q3_price
    """
    if df.empty or 'planning_area' not in df.columns:
        return pd.DataFrame()

    # Ensure coordinates are numeric
    df_copy = df.copy()
    if df_copy['lat'].dtype == 'object':
        df_copy['lat'] = pd.to_numeric(df_copy['lat'], errors='coerce')
    if df_copy['lon'].dtype == 'object':
        df_copy['lon'] = pd.to_numeric(df_copy['lon'], errors='coerce')

    # Drop rows with invalid coordinates or missing planning area
    df_copy = df_copy.dropna(subset=['planning_area', 'lat', 'lon', color_column])

    if df_copy.empty:
        return pd.DataFrame()

    # Aggregate by planning area
    agg_df = df_copy.groupby('planning_area').agg({
        'lat': 'median',
        'lon': 'median',
        color_column: ['count', 'median', 'mean', 'min', 'max', lambda x: x.quantile(0.25), lambda x: x.quantile(0.75)]
    }).reset_index()

    # Flatten column names
    agg_df.columns = ['planning_area', 'lat', 'lon', 'count', 'median_price', 'mean_price', 'min_price', 'max_price', 'q1_price', 'q3_price']

    # Add price_psf if available
    if 'price_psf' in df_copy.columns:
        psf_stats = df_copy.groupby('planning_area')['price_psf'].median().reset_index()
        psf_stats.columns = ['planning_area', 'median_psf']
        agg_df = agg_df.merge(psf_stats, on='planning_area', how='left')

    return agg_df


def aggregate_by_h3(
    df: pd.DataFrame,
    resolution: int = 7,
    color_column: str = "price"
) -> pd.DataFrame:
    """
    Aggregate property data by H3 hexagonal grid with statistics.

    Args:
        df: DataFrame with property data including 'lat', 'lon'
        resolution: H3 resolution (5-9, higher = more detailed)
        color_column: Column to use for color coding

    Returns:
        Aggregated DataFrame with statistics per H3 cell:
        - h3_cell, lat, lon (cell centers)
        - count, median_price, mean_price, median_psf
        - min_price, max_price, q1_price, q3_price
    """
    if df.empty or 'lat' not in df.columns or 'lon' not in df.columns:
        return pd.DataFrame()

    # Ensure coordinates are numeric
    df_copy = df.copy()
    if df_copy['lat'].dtype == 'object':
        df_copy['lat'] = pd.to_numeric(df_copy['lat'], errors='coerce')
    if df_copy['lon'].dtype == 'object':
        df_copy['lon'] = pd.to_numeric(df_copy['lon'], errors='coerce')

    # Drop invalid coordinates
    df_copy = df_copy.dropna(subset=['lat', 'lon', color_column])

    if df_copy.empty:
        return pd.DataFrame()

    # Convert lat/lon to H3 cells
    df_copy['h3_cell'] = df_copy.apply(
        lambda row: h3.latlng_to_cell(row['lat'], row['lon'], resolution),
        axis=1
    )

    # Aggregate by H3 cell
    agg_df = df_copy.groupby('h3_cell').agg({
        color_column: ['count', 'median', 'mean', 'min', 'max', lambda x: x.quantile(0.25), lambda x: x.quantile(0.75)]
    }).reset_index()

    # Flatten column names
    agg_df.columns = ['h3_cell', 'count', 'median_price', 'mean_price', 'min_price', 'max_price', 'q1_price', 'q3_price']

    # Get cell centers from H3 IDs
    agg_df['lat'] = agg_df['h3_cell'].apply(lambda cell: h3.cell_to_latlng(cell)[0])
    agg_df['lon'] = agg_df['h3_cell'].apply(lambda cell: h3.cell_to_latlng(cell)[1])

    # Add price_psf if available
    if 'price_psf' in df_copy.columns:
        psf_stats = df_copy.groupby('h3_cell')['price_psf'].median().reset_index()
        psf_stats.columns = ['h3_cell', 'median_psf']
        agg_df = agg_df.merge(psf_stats, on='h3_cell', how='left')

    return agg_df


def create_base_map(
    center: dict = None,
    zoom: int = SINGAPORE_ZOOM,
    theme: str = DARK_THEME
) -> go.Figure:
    """
    Create a base map figure with OpenStreetMap tiles.

    Args:
        center: Dictionary with 'lat' and 'lon' keys
        zoom: Initial zoom level (1-20)
        theme: Map style (dark or light theme)

    Returns:
        Plotly Figure object
    """
    if center is None:
        center = SINGAPORE_CENTER

    fig = go.Figure()

    fig.update_layout(
        mapbox=dict(
            style=theme,
            center=center,
            zoom=zoom,
        ),
        height=700,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#1e1e1e" if theme == DARK_THEME else "#ffffff",
        plot_bgcolor="#1e1e1e" if theme == DARK_THEME else "#ffffff",
        font=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333"),
    )

    return fig


def create_price_heatmap(
    df: pd.DataFrame,
    color_column: str = "resale_price",
    radius: int = 10,
    theme: str = DARK_THEME
) -> go.Figure:
    """
    Create density heatmap for price visualization.

    Uses Plotly's Densitymapbox for performance with large datasets.
    Automatically aggregates points into hexagonal bins.

    Args:
        df: DataFrame with 'lat', 'lon', and color_column
        color_column: Column name for color coding (e.g., 'resale_price', 'price_psf')
        radius: Radius of influence for each point (higher = smoother heatmap)
        theme: Map theme (dark or light)

    Returns:
        Plotly Figure with density heatmap
    """
    if df.empty or 'lat' not in df.columns or 'lon' not in df.columns:
        return create_base_map()

    # Filter out invalid coordinates
    df_valid = df.dropna(subset=['lat', 'lon', color_column]).copy()

    # Ensure coordinates are numeric (defensive, handles cached data issues)
    if df_valid['lat'].dtype == 'object':
        df_valid['lat'] = pd.to_numeric(df_valid['lat'], errors='coerce')
    if df_valid['lon'].dtype == 'object':
        df_valid['lon'] = pd.to_numeric(df_valid['lon'], errors='coerce')

    # Remove any rows that became NaN after conversion
    df_valid = df_valid.dropna(subset=['lat', 'lon'])

    if df_valid.empty:
        st.warning("No valid coordinates found for heatmap")
        return create_base_map()

    # Normalize color column for better visualization
    prices = df_valid[color_column]
    zmin = prices.quantile(0.05)  # Exclude extreme outliers
    zmax = prices.quantile(0.95)

    fig = go.Figure(go.Densitymapbox(
        lat=df_valid['lat'],
        lon=df_valid['lon'],
        z=prices,
        radius=radius,
        colorscale=PRICE_COLORSCALE,
        zmin=zmin,
        zmax=zmax,
        text=df_valid.get('address', df_valid.index.astype(str)),
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Price: $%{z:,.0f}<br>"
            "<extra></extra>"
        ),
        colorbar=dict(
            title=dict(
                text="Price (SGD)",
                font=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
            ),
            tickfont=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
        )
    ))

    # Update layout with dark theme
    fig.update_layout(
        mapbox=dict(
            style=theme,
            center=dict(
                lat=df_valid['lat'].median(),
                lon=df_valid['lon'].median()
            ),
            zoom=SINGAPORE_ZOOM
        ),
        height=700,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#1e1e1e" if theme == DARK_THEME else "#ffffff",
        plot_bgcolor="#1e1e1e" if theme == DARK_THEME else "#ffffff",
    )

    return fig


def create_planning_area_map(
    aggregated_df: pd.DataFrame,
    color_column: str = "median_price",
    size_column: str = "count",
    theme: str = DARK_THEME
) -> go.Figure:
    """
    Create map with planning area markers showing aggregated statistics.

    Args:
        aggregated_df: DataFrame from aggregate_by_planning_area()
        color_column: Column to use for color coding (e.g., 'median_price', 'median_psf')
        size_column: Column to use for marker size (e.g., 'count')
        theme: Map theme (dark or light)

    Returns:
        Plotly Figure with planning area markers
    """
    if aggregated_df.empty:
        return create_base_map(theme=theme)

    # Normalize sizes for better visualization
    sizes = aggregated_df[size_column]
    size_min = sizes.quantile(0.1)
    size_max = sizes.quantile(0.9)
    aggregated_df['marker_size'] = 10 + 30 * (
        (sizes - size_min) / (size_max - size_min + 1)
    ).clip(0, 1)

    # Normalize colors
    colors = aggregated_df[color_column]
    color_min = colors.quantile(0.05)
    color_max = colors.quantile(0.95)

    # Create trace
    fig = go.Figure(go.Scattermapbox(
        lat=aggregated_df['lat'],
        lon=aggregated_df['lon'],
        mode='markers',
        marker=dict(
            size=aggregated_df['marker_size'],
            color=colors,
            colorscale=PRICE_COLORSCALE,
            cmin=color_min,
            cmax=color_max,
            opacity=0.7,
            colorbar=dict(
                title=dict(
                    text=color_column.replace('_', ' ').title(),
                    font=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
                ),
                tickfont=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
            )
        ),
        text=aggregated_df['planning_area'],
        customdata=aggregated_df[['count', 'median_price', 'mean_price', 'median_psf', 'min_price', 'max_price', 'q1_price', 'q3_price']].values,
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Transactions: %{customdata[0]:,.0f}<br>"
            "Median Price: $%{customdata[1]:,.0f}<br>"
            "Mean Price: $%{customdata[2]:,.0f}<br>"
            "Median PSF: $%{customdata[3]:,.0f}<br>"
            "Price Range: $%{customdata[4]:,.0f} - $%{customdata[5]:,.0f}<br>"
            "<extra></extra>"
        ) if 'median_psf' in aggregated_df.columns else (
            "<b>%{text}</b><br>"
            "Transactions: %{customdata[0]:,.0f}<br>"
            "Median Price: $%{customdata[1]:,.0f}<br>"
            "Mean Price: $%{customdata[2]:,.0f}<br>"
            "<extra></extra>"
        ),
        name='Planning Areas'
    ))

    # Update layout
    fig.update_layout(
        mapbox=dict(
            style=theme,
            center=dict(
                lat=aggregated_df['lat'].median(),
                lon=aggregated_df['lon'].median()
            ),
            zoom=SINGAPORE_ZOOM
        ),
        height=700,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#1e1e1e" if theme == DARK_THEME else "#ffffff",
        plot_bgcolor="#1e1e1e" if theme == DARK_THEME else "#ffffff",
        font=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
    )

    return fig


def create_planning_area_polygon_map(
    aggregated_df: pd.DataFrame,
    geojson_path: str = "data/raw_data/onemap_planning_area_polygon.geojson",
    color_column: str = "median_price",
    theme: str = LIGHT_THEME
) -> go.Figure:
    """
    Create choropleth map with planning area polygons colored by price metrics.

    Uses the OneMap planning area GeoJSON to render actual polygon boundaries
    instead of point markers at centroids.

    Args:
        aggregated_df: DataFrame from aggregate_by_planning_area() with planning_area column
        geojson_path: Path to the planning area polygon GeoJSON file
        color_column: Column to use for color coding (e.g., 'median_price', 'median_psf')
        theme: Map theme (dark or light)

    Returns:
        Plotly Figure with choropleth map of planning area polygons
    """
    if aggregated_df.empty:
        return create_base_map(theme=theme)

    geojson_file = Path(geojson_path)
    if not geojson_file.exists():
        st.warning(f"GeoJSON file not found: {geojson_path}")
        return create_planning_area_map(aggregated_df, color_column, theme=theme)

    with open(geojson_file) as f:
        geojson_data = json.load(f)

    aggregated_df = aggregated_df.copy()

    aggregated_df['planning_area'] = aggregated_df['planning_area'].str.strip()

    color_min = aggregated_df[color_column].quantile(0.05)
    color_max = aggregated_df[color_column].quantile(0.95)

    fig = go.Figure(go.Choroplethmapbox(
        geojson=geojson_data,
        locations=aggregated_df['planning_area'],
        z=aggregated_df[color_column],
        featureidkey="properties.pln_area_n",
        colorscale=PRICE_COLORSCALE,
        zmin=color_min,
        zmax=color_max,
        marker=dict(opacity=0.7, line=dict(width=1, color='rgba(255,255,255,0.5)')),
        colorbar=dict(
            title=dict(
                text=color_column.replace('_', ' ').title(),
                font=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
            ),
            tickfont=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
        ),
        customdata=np.stack([
            aggregated_df['count'],
            aggregated_df['median_price'],
            aggregated_df['mean_price'],
            aggregated_df.get('median_psf', [0] * len(aggregated_df)),
            aggregated_df['min_price'],
            aggregated_df['max_price']
        ], axis=-1),
        hovertemplate=(
            "<b>%{location}</b><br>"
            "Transactions: %{customdata[0]:,.0f}<br>"
            "Median Price: $%{customdata[1]:,.0f}<br>"
            "Mean Price: $%{customdata[2]:,.0f}<br>"
            "Median PSF: $%{customdata[3]:,.0f}<br>"
            "Price Range: $%{customdata[4]:,.0f} - $%{customdata[5]:,.0f}<br>"
            "<extra></extra>"
        )
    ))

    lat_center = aggregated_df['lat'].median()
    lon_center = aggregated_df['lon'].median()

    fig.update_layout(
        mapbox=dict(
            style=theme,
            center=dict(lat=lat_center, lon=lon_center),
            zoom=SINGAPORE_ZOOM
        ),
        height=700,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#1e1e1e" if theme == DARK_THEME else "#ffffff",
        plot_bgcolor="#1e1e1e" if theme == DARK_THEME else "#ffffff",
        font=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
    )

    return fig


def create_h3_grid_map(
    aggregated_df: pd.DataFrame,
    resolution: int,
    color_column: str = "median_price",
    size_column: str = "count",
    theme: str = DARK_THEME
) -> go.Figure:
    """
    Create map with H3 hexagonal grid showing aggregated statistics.

    Args:
        aggregated_df: DataFrame from aggregate_by_h3()
        resolution: H3 resolution used for aggregation
        color_column: Column to use for color coding
        size_column: Column to use for marker size
        theme: Map theme (dark or light)

    Returns:
        Plotly Figure with H3 hexagonal markers
    """
    if aggregated_df.empty:
        return create_base_map(theme=theme)

    # Normalize sizes
    sizes = aggregated_df[size_column]
    size_min = sizes.quantile(0.1)
    size_max = sizes.quantile(0.9)
    aggregated_df['marker_size'] = 8 + 20 * (
        (sizes - size_min) / (size_max - size_min + 1)
    ).clip(0, 1)

    # Normalize colors
    colors = aggregated_df[color_column]
    color_min = colors.quantile(0.05)
    color_max = colors.quantile(0.95)

    # Create trace with hexagonal markers
    fig = go.Figure(go.Scattermapbox(
        lat=aggregated_df['lat'],
        lon=aggregated_df['lon'],
        mode='markers',
        marker=dict(
            size=aggregated_df['marker_size'],
            color=colors,
            colorscale=PRICE_COLORSCALE,
            cmin=color_min,
            cmax=color_max,
            symbol='hexagon',
            opacity=0.7,
            colorbar=dict(
                title=dict(
                    text=color_column.replace('_', ' ').title(),
                    font=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
                ),
                tickfont=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
            )
        ),
        text=aggregated_df['h3_cell'],
        customdata=aggregated_df[['count', 'median_price', 'mean_price', 'median_psf', 'min_price', 'max_price', 'q1_price', 'q3_price']].values,
        hovertemplate=(
            "<b>H3 Cell: %{text}</b><br>"
            "Transactions: %{customdata[0]:,.0f}<br>"
            "Median Price: $%{customdata[1]:,.0f}<br>"
            "Mean Price: $%{customdata[2]:,.0f}<br>"
            "Median PSF: $%{customdata[3]:,.0f}<br>"
            "Price Range: $%{customdata[4]:,.0f} - $%{customdata[5]:,.0f}<br>"
            "<extra></extra>"
        ) if 'median_psf' in aggregated_df.columns else (
            "<b>H3 Cell: %{text}</b><br>"
            "Transactions: %{customdata[0]:,.0f}<br>"
            "Median Price: $%{customdata[1]:,.0f}<br>"
            "<extra></extra>"
        ),
        name=f'H3 Grid R{resolution}'
    ))

    # Update layout
    fig.update_layout(
        mapbox=dict(
            style=theme,
            center=dict(
                lat=aggregated_df['lat'].median(),
                lon=aggregated_df['lon'].median()
            ),
            zoom=SINGAPORE_ZOOM
        ),
        height=700,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#1e1e1e" if theme == DARK_THEME else "#ffffff",
        plot_bgcolor="#1e1e1e" if theme == DARK_THEME else "#ffffff",
        font=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
    )

    return fig


def create_scatter_map(
    properties_df: pd.DataFrame,
    amenities_df: Optional[pd.DataFrame] = None,
    selected_amenities: Optional[List[str]] = None,
    size_column: str = "floor_area_sqft",
    color_column: str = "price_psf",
    theme: str = DARK_THEME
) -> go.Figure:
    """
    Create scatter plot map with property markers and optional amenity overlays.

    Properties are shown as colored circles sized by floor area.
    Amenities (if selected) are shown as icons.

    Args:
        properties_df: Property data with coordinates and metrics
        amenities_df: Amenity location data
        selected_amenities: List of amenity types to overlay (e.g., ['MRT', 'Hawker'])
        size_column: Column for marker size (e.g., 'floor_area_sqft')
        color_column: Column for marker color (e.g., 'price_psf')
        theme: Map theme (dark or light)

    Returns:
        Plotly Figure with scatter map
    """
    if properties_df.empty or 'lat' not in properties_df.columns:
        return create_base_map()

    fig = go.Figure()

    # Filter valid properties
    props_valid = properties_df.dropna(subset=['lat', 'lon', color_column]).copy()

    # Ensure coordinates are numeric (defensive, handles cached data issues)
    if props_valid['lat'].dtype == 'object':
        props_valid['lat'] = pd.to_numeric(props_valid['lat'], errors='coerce')
    if props_valid['lon'].dtype == 'object':
        props_valid['lon'] = pd.to_numeric(props_valid['lon'], errors='coerce')

    # Remove any rows that became NaN after conversion
    props_valid = props_valid.dropna(subset=['lat', 'lon'])

    if props_valid.empty:
        return create_base_map()

    # Normalize sizes for better visualization
    if size_column in props_valid.columns:
        sizes = props_valid[size_column]
        size_min = sizes.quantile(0.1)
        size_max = sizes.quantile(0.9)
        # Scale to 5-25 range
        props_valid['marker_size'] = 5 + 20 * (
            (sizes - size_min) / (size_max - size_min + 1)
        ).clip(0, 1)
    else:
        props_valid['marker_size'] = 10

    # Normalize colors
    colors = props_valid[color_column]
    color_min = colors.quantile(0.05)
    color_max = colors.quantile(0.95)

    # Add properties trace
    fig.add_trace(go.Scattermapbox(
        lat=props_valid['lat'],
        lon=props_valid['lon'],
        mode='markers',
        marker=dict(
            size=props_valid['marker_size'],
            color=colors,
            colorscale=PRICE_COLORSCALE,
            cmin=color_min,
            cmax=color_max,
            opacity=0.7,
            colorbar=dict(
                title=dict(
                    text="$ PSF",
                    font=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
                ),
                tickfont=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
            )
        ),
        text=props_valid.get('address', 'Property'),
        customdata=props_valid[[size_column, color_column]].values if size_column in props_valid.columns else None,
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Price: $%{customdata[1]:,.0f} PSF<br>"
            "Area: %{customdata[0]:.0f} sqft<br>"
            "<extra></extra>"
        ) if size_column in props_valid.columns else (
            "<b>%{text}</b><br>"
            "Price: $%{marker.color:.0f}<br>"
            "<extra></extra>"
        ),
        name='Properties'
    ))

    # Add amenity overlays
    if amenities_df is not None and not amenities_df.empty and selected_amenities:
        amenity_config = {
            'mrt': {'color': '#E74C3C', 'symbol': 'circle', 'size': 8},
            'hawker': {'color': '#F39C12', 'symbol': 'square', 'size': 8},
            'school': {'color': '#3498DB', 'symbol': 'diamond', 'size': 6},
            'park': {'color': '#27AE60', 'symbol': 'circle-open', 'size': 10},
            'childcare': {'color': '#9B59B6', 'symbol': 'triangle-up', 'size': 6},
            'preschool': {'color': '#1ABC9C', 'symbol': 'triangle-up', 'size': 6},
            'supermarket': {'color': '#E67E22', 'symbol': 'diamond', 'size': 6}
        }

        for amenity_type in selected_amenities:
            # Filter amenities by type
            if 'amenity_type' in amenities_df.columns:
                amenity_subset = amenities_df[
                    amenities_df['amenity_type'].str.lower() == amenity_type.lower()
                ].copy()
            elif 'type' in amenities_df.columns:
                amenity_subset = amenities_df[
                    amenities_df['type'].str.lower() == amenity_type.lower()
                ].copy()
            else:
                continue

            if amenity_subset.empty:
                continue

            amenity_subset = amenity_subset.dropna(subset=['lat', 'lon'])

            config = amenity_config.get(
                amenity_type.lower(),
                {'color': '#95A5A6', 'symbol': 'circle', 'size': 8}
            )

            fig.add_trace(go.Scattermapbox(
                lat=amenity_subset['lat'],
                lon=amenity_subset['lon'],
                mode='markers',
                marker=dict(
                    size=config['size'],
                    color=config['color'],
                    symbol=config['symbol'],
                    opacity=0.8
                ),
                text=amenity_subset.get('name', amenity_subset.get('address', amenity_type)),
                hovertemplate="<b>%{text}</b><extra></extra>",
                name=amenity_type.capitalize()
            ))

    # Update layout
    fig.update_layout(
        mapbox=dict(
            style=theme,
            center=dict(
                lat=props_valid['lat'].median(),
                lon=props_valid['lon'].median()
            ),
            zoom=SINGAPORE_ZOOM
        ),
        height=700,
        hovermode='closest',
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#1e1e1e" if theme == DARK_THEME else "#ffffff",
        plot_bgcolor="#1e1e1e" if theme == DARK_THEME else "#ffffff",
        legend=dict(
            bgcolor="rgba(30, 30, 30, 0.8)" if theme == DARK_THEME else "rgba(255, 255, 255, 0.8)",
            font=dict(color="#e0e0e0" if theme == DARK_THEME else "#333333")
        )
    )

    return fig


def create_multi_layer_map(
    properties_df: pd.DataFrame,
    amenities_df: Optional[pd.DataFrame] = None,
    show_heatmap: bool = True,
    show_amenities: bool = False,
    amenity_types: Optional[List[str]] = None,
    theme: str = DARK_THEME
) -> go.Figure:
    """
    Create multi-layer map with toggleable heatmap and scatter layers.

    This is a convenience function that combines heatmap and scatter modes.

    Args:
        properties_df: Property data
        amenities_df: Amenity location data
        show_heatmap: Whether to show heatmap layer
        show_amenities: Whether to show amenity markers
        amenity_types: Which amenity types to show
        theme: Map theme

    Returns:
        Plotly Figure with appropriate layers
    """
    if show_heatmap:
        return create_price_heatmap(properties_df, theme=theme)
    else:
        return create_scatter_map(
            properties_df,
            amenities_df if show_amenities else None,
            amenity_types if show_amenities else None,
            theme=theme
        )


def display_map_with_stats(fig: go.Figure, df: pd.DataFrame, theme: str = DARK_THEME):
    """
    Display map with summary statistics in columns.

    Args:
        fig: Plotly figure to display
        df: Property data for statistics
        theme: Color theme for stats
    """
    # Calculate stats
    total_properties = len(df)

    price_col = None
    for col in ['resale_price', 'Transacted Price ($)', 'price']:
        if col in df.columns:
            price_col = col
            break

    if price_col:
        median_price = df[price_col].median()
        avg_price = df[price_col].mean()
    else:
        median_price = 0
        avg_price = 0

    # Display map
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.metric(
            "Total Properties",
            f"{total_properties:,}",
            help="Number of properties in current view"
        )

    with col3:
        st.metric(
            "Median Price",
            f"${median_price:,.0f}",
            help="Median transaction price"
        )


def display_enhanced_metrics_dashboard(filtered_df: pd.DataFrame, aggregated_df: pd.DataFrame = None):
    """
    Display a comprehensive tiered metrics dashboard above the map.

    Shows primary metrics (always visible), secondary metrics (compact),
    and advanced metrics (expandable).

    Args:
        filtered_df: Filtered property data
        aggregated_df: Aggregated data (optional, for map-specific metrics)
    """
    if filtered_df.empty:
        st.warning("No data available for metrics")
        return

    # ===== PRIMARY METRICS (Always Visible, Prominent) =====
    st.markdown("### 📊 Key Metrics")

    # Calculate primary metrics
    total_properties = len(filtered_df)

    # Find price column
    price_col = None
    for col in ['resale_price', 'Transacted Price ($)', 'price']:
        if col in filtered_df.columns:
            price_col = col
            break

    if price_col:
        median_price = filtered_df[price_col].median()
        avg_price = filtered_df[price_col].mean()
        min_price = filtered_df[price_col].min()
        max_price = filtered_df[price_col].max()
    else:
        median_price = avg_price = min_price = max_price = 0

    # Calculate PSF
    if 'price_psf' in filtered_df.columns:
        avg_psf = filtered_df['price_psf'].mean()
        median_psf = filtered_df['price_psf'].median()
    else:
        avg_psf = median_psf = 0

    # Display primary metrics in 4 columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "🏠 Total Properties",
            f"{total_properties:,}",
            help="Number of transactions in current view"
        )

    with col2:
        st.metric(
            "💰 Median Price",
            f"${median_price:,.0f}",
            delta=f"${avg_price - median_price:,.0f} vs avg" if avg_price != median_price else None,
            help="Median transaction price"
        )

    with col3:
        st.metric(
            "📐 Avg PSF",
            f"${avg_psf:,.0f}" if avg_psf > 0 else "N/A",
            delta=f"${median_psf - avg_psf:,.0f} vs median" if avg_psf > 0 and median_psf != avg_psf else None,
            help="Average price per square foot"
        )

    with col4:
        # Total market value
        total_value = filtered_df[price_col].sum() if price_col else 0
        st.metric(
            "💵 Total Market Value",
            f"${total_value / 1e9:.2f}B" if total_value >= 1e9 else f"${total_value / 1e6:.1f}M",
            help="Total value of all transactions"
        )

    st.markdown("---")

    # ===== SECONDARY METRICS (Compact, Two Rows) =====
    st.markdown("#### 📈 Additional Insights")

    # First row of secondary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Planning areas covered
        if 'planning_area' in filtered_df.columns:
            num_pas = filtered_df['planning_area'].nunique()
            st.metric("Planning Areas", f"{num_pas}", help="Number of URA planning areas")

    with col2:
        # MRT accessibility
        if 'dist_to_nearest_mrt' in filtered_df.columns:
            near_mrt = (filtered_df['dist_to_nearest_mrt'] <= 500).sum()
            pct_near = near_mrt / len(filtered_df) * 100
            st.metric("Near MRT (≤500m)", f"{pct_near:.1f}%", help=f"{near_mrt:,} properties within 500m")
        else:
            st.metric("MRT Data", "N/A", "Not available")

    with col3:
        # Rental yield
        if 'rental_yield_pct' in filtered_df.columns:
            rental_data = filtered_df[filtered_df['rental_yield_pct'].notna()]
            if not rental_data.empty:
                avg_yield = rental_data['rental_yield_pct'].mean()
                st.metric("Avg Rental Yield", f"{avg_yield:.2f}%", help="HDB properties only")
            else:
                st.metric("Rental Yield", "N/A", "No data")
        else:
            st.metric("Rental Yield", "N/A", "Not available")

    with col4:
        # Amenity coverage
        amenity_cols = [col for col in filtered_df.columns if '_within_500m' in col]
        if amenity_cols:
            sample_col = amenity_cols[0]
            with_amenities = (filtered_df[sample_col] >= 1).sum()
            pct = with_amenities / len(filtered_df) * 100
            st.metric("Near Amenities", f"{pct:.1f}%", help="Properties with ≥1 amenity within 500m")
        else:
            st.metric("Amenity Data", "N/A", "Not available")

    # ===== ADVANCED METRICS (Expandable) =====
    with st.expander("🔍 Show Advanced Metrics", expanded=False):
        st.markdown("##### 🎯 Price Distribution")

        # Price quartiles
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Min Price", f"${min_price:,.0f}")
        with col2:
            if price_col:
                q1 = filtered_df[price_col].quantile(0.25)
                st.metric("25th Percentile", f"${q1:,.0f}")
        with col3:
            if price_col:
                q3 = filtered_df[price_col].quantile(0.75)
                st.metric("75th Percentile", f"${q3:,.0f}")
        with col4:
            st.metric("Max Price", f"${max_price:,.0f}")

        st.markdown("##### 📍 Geographic Coverage")

        geo_col1, geo_col2, geo_col3 = st.columns(3)

        with geo_col1:
            if 'town' in filtered_df.columns:
                num_towns = filtered_df['town'].nunique()
                st.metric("Towns Covered", f"{num_towns}")

        with geo_col2:
            if 'planning_area' in filtered_df.columns:
                top_pa = filtered_df['planning_area'].value_counts().index[0]
                st.metric("Most Active Area", top_pa)

        with geo_col3:
            if 'town' in filtered_df.columns:
                top_town = filtered_df['town'].value_counts().index[0]
                st.metric("Most Active Town", top_town)

        # Phase 2 metrics
        if 'period_5yr' in filtered_df.columns or 'market_tier_period' in filtered_df.columns:
            st.markdown("##### ⏳ Phase 2: Time Period Analysis")

            phase2_col1, phase2_col2 = st.columns(2)

            with phase2_col1:
                if 'period_5yr' in filtered_df.columns:
                    current_period = filtered_df['period_5yr'].iloc[0] if len(filtered_df) > 0 else "N/A"
                    st.metric("Current Period", current_period)

            with phase2_col2:
                if 'market_tier_period' in filtered_df.columns:
                    tier_dist = filtered_df['market_tier_period'].value_counts()
                    if not tier_dist.empty:
                        top_tier = tier_dist.index[0]
                        st.metric("Dominant Tier", top_tier)

        # Aggregated data metrics (if available)
        if aggregated_df is not None and not aggregated_df.empty:
            st.markdown("##### 🗺️ Map Aggregation Stats")

            agg_col1, agg_col2 = st.columns(2)

            with agg_col1:
                st.metric("Aggregated Cells", f"{len(aggregated_df):,}")

            with agg_col2:
                if 'count' in aggregated_df.columns:
                    avg_cell_size = aggregated_df['count'].mean()
                    st.metric("Avg Properties/Cell", f"{avg_cell_size:.1f}")

    st.markdown("---")



def get_map_bounds(df: pd.DataFrame, padding: float = 0.1) -> dict:
    """
    Calculate map bounds to fit all data points.

    Args:
        df: DataFrame with 'lat' and 'lon' columns
        padding: Padding around bounds (0.1 = 10%)

    Returns:
        Dictionary with center and zoom for map
    """
    if df.empty or 'lat' not in df.columns or 'lon' not in df.columns:
        return {'center': SINGAPORE_CENTER, 'zoom': SINGAPORE_ZOOM}

    lat_min, lat_max = df['lat'].min(), df['lat'].max()
    lon_min, lon_max = df['lon'].min(), df['lon'].max()

    center = {
        'lat': (lat_min + lat_max) / 2,
        'lon': (lon_min + lon_max) / 2
    }

    # Calculate zoom based on bounds (simplified)
    lat_range = lat_max - lat_min
    lon_range = lon_max - lon_min

    # Approximate zoom calculation
    max_range = max(lat_range, lon_range)
    if max_range < 0.01:
        zoom = 14
    elif max_range < 0.05:
        zoom = 12
    elif max_range < 0.1:
        zoom = 11
    elif max_range < 0.2:
        zoom = 10
    else:
        zoom = 9

    return {'center': center, 'zoom': zoom}
