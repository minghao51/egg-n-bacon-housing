"""
Price Map Page - Interactive map visualization for Singapore housing prices.

This page provides:
- Interactive map with heatmap and scatter views
- Property filtering by type, location, price, time
- Amenity overlays (MRT, hawker, schools, parks)
- Summary statistics and metrics
"""

import streamlit as st
from datetime import datetime
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import (
    load_unified_data,
    load_amenity_locations,
    get_unified_filter_options,
    apply_unified_filters,
    get_unified_data_summary
)
from src.map_utils import (
    aggregate_by_planning_area,
    aggregate_by_h3,
    create_planning_area_polygon_map,
    create_h3_grid_map,
    display_map_with_stats,
    display_enhanced_metrics_dashboard,
    LIGHT_THEME,
    get_available_map_styles,
    get_map_style_value,
    get_available_color_by_options,
    get_color_column_value
)
from src.ui_components import (
    load_css, page_header, section_header, divider, info_box
)

# Page config
st.set_page_config(
    page_title="Price Map",
    page_icon="",
    layout="wide"
)

# Load centralized design system
load_css()


def render_filters():
    """Render filter controls in sidebar."""

    st.sidebar.header("🔍 Filters")

    # Get data for filter options
    df = load_unified_data()

    if df.empty:
        st.error("No data available. Please check your data files.")
        return {}

    filter_options = get_unified_filter_options(df)

    # 1. Property Type
    st.sidebar.subheader("Property Type")
    property_types = st.sidebar.multiselect(
        "Select Property Types",
        filter_options.get('property_types', []),
        default=filter_options.get('property_types', [])
    )

    # 1.5. FEATURES - Period & Market Segmentation
    st.sidebar.subheader("Time Period Analysis")

    # Period Filter
    if 'period_5yr' in df.columns:
        available_periods = sorted(df['period_5yr'].unique())
        default_period = available_periods[-1] if available_periods else None  # Most recent period

        selected_period = st.sidebar.selectbox(
            "5-Year Period",
            available_periods,
            index=len(available_periods)-1 if available_periods else 0,
            help="Filter by 5-year period to compare different eras (accounts for inflation)"
        )
    else:
        selected_period = None

    # Market Tier Filter
    if 'market_tier_period' in df.columns:
        market_tiers = st.sidebar.multiselect(
            "Market Tier (Period-Dependent)",
            ['Mass Market', 'Mid-Tier', 'Luxury'],
            default=['Mass Market', 'Mid-Tier', 'Luxury'],
            help="Filter by price tier (calculated within each period)"
        )
    else:
        market_tiers = None

    # 2. Location Filters
    st.sidebar.subheader("Location")

    # Planning Area Filter
    if 'planning_area' in df.columns:
        planning_areas = st.sidebar.multiselect(
            "Planning Area",
            sorted(df['planning_area'].unique()),
            default=None,
            help="Filter by URA planning area (55 areas available)"
        )
    else:
        planning_areas = None

    towns = st.sidebar.multiselect(
        "Town",
        sorted(df['town'].unique()) if 'town' in df.columns else [],
        default=None,
        help="Filter by HDB town"
    )

    postal_range = st.sidebar.slider(
        "Postal District",
        1, 83,
        (1, 83),
        help="Singapore postal districts (01-83)"
    )

    # Amenity Accessibility Filters
    st.sidebar.subheader("Amenity Accessibility")

    if 'dist_to_nearest_mrt' in df.columns:
        max_mrt_dist = int(df['dist_to_nearest_mrt'].max())
        mrt_distance = st.sidebar.slider(
            "Max Distance to MRT",
            0, min(2000, max_mrt_dist),
            0,
            step=100,
            help="Filter properties within X meters of MRT (0 = no filter)"
        )
    else:
        mrt_distance = 0

    # 3. Price Filters
    st.sidebar.subheader("💰 Price")

    if 'price' in df.columns and df['price'].notna().any():
        price_min = int(df['price'].min())
        price_max = int(df['price'].max())
    else:
        price_min = 100000
        price_max = 5000000

    price_range = st.sidebar.slider(
        "Price Range (SGD)",
        price_min, price_max,
        (price_min, price_max),
        step=50000,
        format="$%d"
    )

    # 4. Floor Area
    # Now uses standardized floor_area_sqft column
    if 'floor_area_sqft' in df.columns and df['floor_area_sqft'].notna().any():
        area_min = int(df['floor_area_sqft'].min())
        area_max = int(df['floor_area_sqft'].max())
    else:
        area_min = 300
        area_max = 5000

    floor_area_range = st.sidebar.slider(
        "Floor Area (sqft)",
        area_min, area_max,
        (area_min, area_max),
        step=50
    )

    # 5. Time Period
    st.sidebar.subheader("Time Period")

    if 'transaction_date' in df.columns:
        date_min = df['transaction_date'].min().to_pydatetime()
        date_max = df['transaction_date'].max().to_pydatetime()
    else:
        date_min = datetime(2015, 1, 1)
        date_max = datetime.now()

    date_range = st.sidebar.slider(
        "Transaction Period",
        date_min, date_max,
        (date_min, date_max)
    )

    # Map settings moved to top of main page (not sidebar)
    show_amenities = False
    selected_amenities = []

    return {
        'property_types': property_types,
        'selected_period': selected_period,
        'market_tiers': market_tiers,
        'planning_areas': planning_areas,
        'towns': towns,
        'postal_range': postal_range,
        'mrt_distance': mrt_distance,
        'price_range': price_range,
        'floor_area_range': floor_area_range,
        'date_range': date_range,
        'show_amenities': show_amenities,
        'selected_amenities': selected_amenities
    }


def render_map_settings():
    """Render map settings at the top of the page with session state persistence."""

    st.markdown("### Map Settings")

    # Initialize session state for map settings
    if 'map_view_mode' not in st.session_state:
        st.session_state.map_view_mode = "Planning Areas"
    if 'map_style_name' not in st.session_state:
        st.session_state.map_style_name = "Default (OSM)"
    if 'map_color_by_name' not in st.session_state:
        st.session_state.map_color_by_name = "Median Price"

    # Use columns for horizontal layout
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

    with col1:
        view_mode = st.selectbox(
            "View Mode",
            ["Planning Areas", "H3 Grid R7", "H3 Grid R8"],
            index=["Planning Areas", "H3 Grid R7", "H3 Grid R8"].index(st.session_state.map_view_mode),
            help="Planning Areas: 40 areas | H3 R7: ~5K hex cells | H3 R8: ~14K hex cells",
            key='map_view_mode_select'
        )

    with col2:
        # Map style selector with persistence
        available_styles = get_available_map_styles()
        map_style_name = st.selectbox(
            "Map Style",
            available_styles,
            index=available_styles.index(st.session_state.map_style_name),
            help="Choose the visual style of the map",
            key='map_style_select'
        )
        map_style = get_map_style_value(map_style_name)

    with col3:
        # Color by selector with persistence
        color_by_options = get_available_color_by_options()
        color_by_name = st.selectbox(
            "Color By",
            color_by_options,
            index=color_by_options.index(st.session_state.map_color_by_name),
            help="Choose the metric to color-code the map",
            key='map_color_by_select'
        )
        color_column = get_color_column_value(color_by_name)

    with col4:
        # Reset button
        if st.button("🔄 Reset Defaults", help="Reset all map settings to defaults"):
            st.session_state.map_view_mode = "Planning Areas"
            st.session_state.map_style_name = "Default (OSM)"
            st.session_state.map_color_by_name = "Median Price"
            st.rerun()

    st.markdown("---")

    return {
        'view_mode': view_mode,
        'map_style': map_style,
        'map_style_name': map_style_name,
        'color_column': color_column,
        'color_by_name': color_by_name
    }


def main():
    """Main function for Price Map page."""

    # Page Header
    page_header(
        "Interactive Price Map",
        "Explore Singapore housing prices with advanced mapping and filtering"
    )

    # Render map settings at the top
    map_settings = render_map_settings()

    # Render filters in sidebar
    filters = render_filters()

    # Load data
    with st.spinner("Loading data..."):
        df = load_unified_data()

    if df.empty:
        st.error("No data available. Please check your data files.")
        return

    # Apply filters
    with st.spinner("Applying filters..."):
        filtered_df = apply_unified_filters(
            df,
            property_types=filters.get('property_types'),
            towns=filters.get('towns'),
            price_range=filters.get('price_range'),
            date_range=filters.get('date_range'),
            floor_area_range=filters.get('floor_area_range')
        )

        # Apply NEW L3 filters
        # Planning area filter
        if filters.get('planning_areas') and 'planning_area' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['planning_area'].isin(filters.get('planning_areas'))]

        # MRT distance filter
        mrt_dist = filters.get('mrt_distance', 0)
        if mrt_dist > 0 and 'dist_to_nearest_mrt' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['dist_to_nearest_mrt'] <= mrt_dist]

        # Period filter
        if filters.get('selected_period') and 'period_5yr' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['period_5yr'] == filters.get('selected_period')]

        # Market tier filter
        if filters.get('market_tiers') and 'market_tier_period' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['market_tier_period'].isin(filters.get('market_tiers'))]

    if filtered_df.empty:
        st.warning("No properties match your filters. Try adjusting your criteria.")
        return

    # Create map based on view mode
    with st.spinner("Aggregating data and rendering map..."):
        view_mode = map_settings.get('view_mode', 'Planning Areas')
        map_style = map_settings.get('map_style', LIGHT_THEME)
        color_column = map_settings.get('color_column', 'median_price')

        if view_mode == "Planning Areas":
            # Aggregate by planning area
            with st.spinner("Aggregating by planning area..."):
                aggregated_df = aggregate_by_planning_area(filtered_df, color_column='price')
            # Use selected color column if it exists, otherwise fallback
            color_col = color_column if color_column in aggregated_df.columns else 'median_price'
            fig = create_planning_area_polygon_map(aggregated_df, color_column=color_col, theme=map_style)

        elif view_mode == "H3 Grid R7":
            # Aggregate by H3 grid resolution 7
            with st.spinner("Aggregating by H3 grid (resolution 7)..."):
                aggregated_df = aggregate_by_h3(filtered_df, resolution=7, color_column='price')
            color_col = color_column if color_column in aggregated_df.columns else 'median_price'
            fig = create_h3_grid_map(aggregated_df, resolution=7, color_column=color_col, theme=map_style)

        elif view_mode == "H3 Grid R8":
            # Aggregate by H3 grid resolution 8
            with st.spinner("Aggregating by H3 grid (resolution 8)..."):
                aggregated_df = aggregate_by_h3(filtered_df, resolution=8, color_column='price')
            color_col = color_column if color_column in aggregated_df.columns else 'median_price'
            fig = create_h3_grid_map(aggregated_df, resolution=8, color_column=color_col, theme=map_style)

    # Display the map
    section_header("Map Visualization")
    st.plotly_chart(fig, use_container_width=True)

    # Info about aggregation
    st.info(f"Aggregation: Displaying {len(aggregated_df):,} {view_mode.lower()} instead of {len(filtered_df):,} individual properties")

    # Performance warning for large datasets
    if view_mode in ["H3 Grid R7", "H3 Grid R8"] and len(aggregated_df) > 10000:
        st.warning(
            f"Showing {len(aggregated_df):,} aggregated cells. "
            "For better performance, consider applying more filters or switching to Planning Areas view."
        )

    # Display metrics dashboard
    display_enhanced_metrics_dashboard(filtered_df, aggregated_df)

    # Data preview
    with st.expander("View Filtered Data"):
        display_cols = [
            'transaction_date',
            'property_type',
            'town',
            'planning_area',
            'address',
            'price',
            'floor_area_sqft',
            'price_psf',
            'rental_yield_pct',
            'dist_to_nearest_mrt',
            'mom_change_pct',
            'period_5yr',
            'market_tier_period',
            'psm_tier_period',
        ]
        display_cols = [col for col in display_cols if col in filtered_df.columns]

        st.dataframe(
            filtered_df[display_cols].head(100),
            use_container_width=True
        )

    # Download option
    divider()
    section_header("Export Data")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Export Filtered Data to CSV"):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"sg_housing_prices_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    with col2:
        st.info(
            "Tip: Use the filters on the left to narrow down your search. "
            "Switch between Heatmap and Scatter modes for different views."
        )

    # Help section
    with st.expander("How to Use This Page"):
        st.markdown("""
        ### Map Visualization Guide

        **Heatmap Mode (Default)**
        - Best for large datasets (>5,000 points)
        - Colors represent price levels:
          - 🔵 Blue = Lower prices
          - 🟢 Green = Mid-range prices
          - 🟡 Yellow = Above average
          - 🟠 Orange = High prices
          - 🔴 Red = Premium prices
        - Smooth performance with automatic aggregation

        **Scatter Plot Mode**
        - Shows individual properties as points
        - Circle size = Floor area
        - Circle color = Price per square foot ($PSF)
        - Can overlay amenity locations

        **Amenity Overlays** (Scatter mode only)
        - 🚇 MRT Stations (red circles)
        - 🍜 Hawker Centres (orange squares)
        - 🏫 Schools (blue diamonds)
        - 🌳 Parks (green circles)

        ### 🔍 Filter Tips

        **Property Type**
        - Select multiple types to compare
        - HDB = Public housing
        - Condominium = Private apartments

        **Location Filters**
        - Town: HDB town (e.g., Ang Mo Kio, Bedok)
        - Postal District: 01-83 (District 09 = Orchard, District 10 = Holland Rd)
        - Combine multiple filters for precise results

        **Price Range**
        - Set min/max prices
        - Helps focus on your budget range
        - Updates map automatically

        **Floor Area**
        - Filter by property size
        - Useful for finding specific room sizes
        - HDB: 2-room (~45 sqm) to 5-room (~120 sqm)
        - Condo: Studio to penthouse

        **Time Period**
        - Filter by transaction date
        - View recent trends or historical data
        - Narrow range = faster performance

        ### ⚡ Performance Tips

        1. **Use Heatmap mode** for large datasets
        2. **Narrow date range** (e.g., last 2 years)
        3. **Select fewer towns** instead of all
        4. **Apply price filters** to reduce data size
        5. **Export data** if you need detailed analysis

        ### 📊 Understanding the Data

        - **Source**: HDB and URA (government data)
        - **Coverage**: 2015-present
        - **HDB**: ~969K resale transactions
        - **Condo**: ~49K private transactions
        - **Coordinates**: Geocoded via OneMap API

        ### 🎯 Common Use Cases

        **Find Affordable Properties**
        1. Set price range to your budget
        2. Select HDB property type
        3. View heatmap to find low-price areas
        4. Switch to scatter mode for details

        **Compare Towns**
        1. Clear all filters
        2. Select 2-3 towns to compare
        3. Use scatter mode to see distribution
        4. Check amenity overlays

        **Investment Analysis**
        1. Narrow to recent transactions (last 1-2 years)
        2. Enable amenity overlays (MRT, schools)
        3. Check areas with high price density
        4. Export data for further analysis

        **Find Properties Near Amenities**
        1. Switch to scatter mode
        2. Enable "Show Amenities"
        3. Select desired amenity types
        4. Hover over property points for details
        """)


if __name__ == "__main__":
    main()
