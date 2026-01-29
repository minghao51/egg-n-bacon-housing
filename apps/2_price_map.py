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

from core.data_loader import (
    load_unified_data,
    load_amenity_locations,
    get_unified_filter_options,
    apply_unified_filters,
    get_unified_data_summary,
)
from core.map_utils import (
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
    get_color_column_value,
)
from core.ui_components import load_css, page_header, section_header, divider, info_box

# Page config
st.set_page_config(page_title="Price Map", page_icon="", layout="wide")

# Load centralized design system
load_css()


def render_filters():
    """Render filter controls in sidebar with logical grouping."""

    st.sidebar.header("🔍 Filter Controls")

    # Get data for filter options
    df = load_unified_data()

    if df.empty:
        st.error("No data available. Please check your data files.")
        return {}

    filter_options = get_unified_filter_options(df)

    # ============================================================================
    # SECTION 1: PROPERTY TYPE (What)
    # ============================================================================
    st.sidebar.subheader("**🏠 Property Type**")
    property_types = st.sidebar.multiselect(
        "Select Property Types",
        filter_options.get("property_types", []),
        default=filter_options.get("property_types", []),
    )

    # ============================================================================
    # SECTION 2: TIME ANALYSIS (When)
    # ============================================================================
    st.sidebar.subheader("**📅 Time Period Analysis**")

    # Era Selection
    period_mode = st.sidebar.radio(
        "Analysis Period",
        options=["whole", "pre_covid", "recent"],
        format_func=lambda x: {
            "whole": "All Historical Data",
            "pre_covid": "Pre-COVID (2015-2021)",
            "recent": "Recent (2022-2026)",
        }[x],
        index=0,
        help="Filter by era for comparative analysis",
    )

    # 5-Year Period Filter
    if "period_5yr" in df.columns:
        available_periods = sorted(df["period_5yr"].unique())
        default_period = available_periods[-1] if available_periods else None

        selected_period = st.sidebar.selectbox(
            "5-Year Period",
            available_periods,
            index=len(available_periods) - 1 if available_periods else 0,
            help="Filter by 5-year period to compare different eras (accounts for inflation)",
        )
    else:
        selected_period = None

    # Market Tier Filter
    if "market_tier_period" in df.columns:
        market_tiers = st.sidebar.multiselect(
            "Market Tier (Period-Dependent)",
            ["Mass Market", "Mid-Tier", "Luxury"],
            default=["Mass Market", "Mid-Tier", "Luxury"],
            help="Filter by price tier (calculated within each period)",
        )
    else:
        market_tiers = None

    # Transaction Date Range
    if "transaction_date" in df.columns:
        date_min = df["transaction_date"].min().to_pydatetime()
        date_max = df["transaction_date"].max().to_pydatetime()
    else:
        date_min = datetime(2015, 1, 1)
        date_max = datetime.now()

    date_range = st.sidebar.slider(
        "Transaction Date Range",
        date_min,
        date_max,
        (date_min, date_max),
        format="%Y-%m"
    )

    # ============================================================================
    # SECTION 3: LOCATION (Where)
    # ============================================================================
    st.sidebar.subheader("**📍 Location Filters**")

    # Planning Area Filter
    if "planning_area" in df.columns:
        planning_areas = st.sidebar.multiselect(
            "Planning Area",
            sorted(df["planning_area"].unique()),
            default=None,
            help="Filter by URA planning area (55 areas available)",
        )
    else:
        planning_areas = None

    towns = st.sidebar.multiselect(
        "Town",
        sorted(df["town"].unique()) if "town" in df.columns else [],
        default=None,
        help="Filter by HDB town",
    )

    postal_range = st.sidebar.slider(
        "Postal District",
        1, 83, (1, 83),
        help="Singapore postal districts (01-83)"
    )

    # ============================================================================
    # SECTION 4: PROPERTY DETAILS (Specs)
    # ============================================================================
    st.sidebar.subheader("**💰 Price & Size**")

    if "price" in df.columns and df["price"].notna().any():
        price_min = int(df["price"].min())
        price_max = int(df["price"].max())
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

    if "floor_area_sqft" in df.columns and df["floor_area_sqft"].notna().any():
        area_min = int(df["floor_area_sqft"].min())
        area_max = int(df["floor_area_sqft"].max())
    else:
        area_min = 300
        area_max = 5000

    floor_area_range = st.sidebar.slider(
        "Floor Area (sqft)",
        area_min, area_max,
        (area_min, area_max),
        step=50
    )

    # ============================================================================
    # SECTION 5: AMENITY ACCESSIBILITY (Quality)
    # ============================================================================
    st.sidebar.subheader("**🚇 Amenity Accessibility**")

    if "dist_to_nearest_mrt" in df.columns:
        max_mrt_dist = int(df["dist_to_nearest_mrt"].max())
        mrt_distance = st.sidebar.slider(
            "Max Distance to MRT",
            0,
            min(2000, max_mrt_dist),
            0,
            step=100,
            help="Filter properties within X meters of MRT (0 = no filter)",
        )
    else:
        mrt_distance = 0

    # ============================================================================
    # SECTION 6: ADVANCED FEATURES (Optional)
    # ============================================================================
    st.sidebar.subheader("**🔬 Advanced Analysis**")

    # Cross-Era Comparison
    enable_cross_era = st.sidebar.checkbox(
        "Cross-Era Comparison",
        value=False,
        help="Compare metrics side-by-side between two eras",
    )

    if enable_cross_era:
        era_1 = st.sidebar.selectbox(
            "Primary Era",
            options=["pre_covid", "recent"],
            format_func=lambda x: {
                "pre_covid": "Pre-COVID (2015-2021)",
                "recent": "Recent (2022-2026)",
            }[x],
            index=0,
        )
        era_2 = st.sidebar.selectbox(
            "Comparison Era",
            options=["pre_covid", "recent"],
            format_func=lambda x: {
                "pre_covid": "Pre-COVID (2015-2021)",
                "recent": "Recent (2022-2026)",
            }[x],
            index=1,
        )
    else:
        era_1 = None
        era_2 = None

    # Custom Date Range Override
    enable_custom_range = st.sidebar.checkbox(
        "Custom Date Range Override",
        value=False,
        help="Override era selection with a specific date range",
    )

    if enable_custom_range:
        if "transaction_date" in df.columns:
            data_min_date = df["transaction_date"].min().to_pydatetime()
            data_max_date = df["transaction_date"].max().to_pydatetime()
        else:
            data_min_date = datetime(2015, 1, 1)
            data_max_date = datetime.now()

        custom_date_range = st.sidebar.slider(
            "Custom Transaction Period",
            data_min_date,
            data_max_date,
            (data_min_date, data_max_date),
            format="%Y-%m",
        )
    else:
        custom_date_range = None

    # 3-Way Era Comparison
    enable_3way_comparison = st.sidebar.checkbox(
        "3-Way Era Comparison",
        value=False,
        help="Compare Pre-COVID, COVID, and Post-COVID periods side-by-side",
    )

    if enable_3way_comparison:
        st.sidebar.info("💡 Pre-COVID (2015-2019), COVID (2020-2021), Post-COVID (2022-2026)")

    # Map settings moved to top of main page (not sidebar)
    show_amenities = False
    selected_amenities = []

    return {
        "property_types": property_types,
        "selected_period": selected_period,
        "market_tiers": market_tiers,
        "period_mode": period_mode,
        "date_range": date_range,
        "planning_areas": planning_areas,
        "towns": towns,
        "postal_range": postal_range,
        "price_range": price_range,
        "floor_area_range": floor_area_range,
        "mrt_distance": mrt_distance,
        "enable_cross_era": enable_cross_era,
        "era_1": era_1,
        "era_2": era_2,
        "enable_custom_range": enable_custom_range,
        "custom_date_range": custom_date_range,
        "enable_3way_comparison": enable_3way_comparison,
        "show_amenities": show_amenities,
        "selected_amenities": selected_amenities,
    }


def render_map_settings():
    """Render map settings at the top of the page with session state persistence."""

    st.markdown("### 🗺️ Map Visualization Settings")

    # Initialize session state for map settings
    if "map_view_mode" not in st.session_state:
        st.session_state.map_view_mode = "Planning Areas"
    if "map_style_name" not in st.session_state:
        st.session_state.map_style_name = "Positron (Light)"
    if "map_color_by_name" not in st.session_state:
        st.session_state.map_color_by_name = "Median Price"

    # Use columns for horizontal layout
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1.5])

    with col1:
        view_mode = st.selectbox(
            "**View Mode**",
            ["Planning Areas", "H3 Grid R6", "H3 Grid R7", "H3 Grid R8", "H3 Grid R9"],
            index=["Planning Areas", "H3 Grid R6", "H3 Grid R7", "H3 Grid R8", "H3 Grid R9"].index(
                st.session_state.map_view_mode
            ),
            help=(
                "**Planning Areas**: 55 URA planning areas with polygon boundaries\n"
                "**H3 Grid R6**: ~700 hexagonal cells (broader view)\n"
                "**H3 Grid R7**: ~5,000 hexagonal cells (balanced detail)\n"
                "**H3 Grid R8**: ~14,000 hexagonal cells (fine detail)\n"
                "**H3 Grid R9**: ~100,000 hexagonal cells (ultra-fine detail, use with narrow filters)"
            ),
            key="map_view_mode_select",
        )

    with col2:
        # Map style selector with persistence
        available_styles = get_available_map_styles()
        map_style_name = st.selectbox(
            "**Map Style**",
            available_styles,
            index=available_styles.index(st.session_state.map_style_name),
            help="Choose the visual style of the map background",
            key="map_style_select",
        )
        map_style = get_map_style_value(map_style_name)

    with col3:
        # Color by selector with persistence
        color_by_options = get_available_color_by_options()
        color_by_name = st.selectbox(
            "**Color By**",
            color_by_options,
            index=color_by_options.index(st.session_state.map_color_by_name),
            help="Choose the metric to color-code the map cells",
            key="map_color_by_select",
        )
        color_column = get_color_column_value(color_by_name)

    with col4:
        st.write("")  # Spacing
        st.write("")
        # Reset button
        if st.button("🔄 **Reset Defaults**", help="Reset all map settings to defaults"):
            st.session_state.map_view_mode = "Planning Areas"
            st.session_state.map_style_name = "Positron (Light)"
            st.session_state.map_color_by_name = "Median Price"
            st.rerun()

    st.markdown("---")

    return {
        "view_mode": view_mode,
        "map_style": map_style,
        "map_style_name": map_style_name,
        "color_column": color_column,
        "color_by_name": color_by_name,
    }


def main():
    """Main function for Price Map page."""

    # Page Header
    page_header(
        "Interactive Price Map",
        "Explore Singapore housing prices with advanced mapping and filtering",
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
            property_types=filters.get("property_types"),
            towns=filters.get("towns"),
            price_range=filters.get("price_range"),
            date_range=filters.get("date_range"),
            floor_area_range=filters.get("floor_area_range"),
        )

        # Apply NEW L3 filters
        # Planning area filter
        if filters.get("planning_areas") and "planning_area" in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df["planning_area"].isin(filters.get("planning_areas"))
            ]

        # MRT distance filter
        mrt_dist = filters.get("mrt_distance", 0)
        if mrt_dist > 0 and "dist_to_nearest_mrt" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["dist_to_nearest_mrt"] <= mrt_dist]

        # Period filter
        if filters.get("selected_period") and "period_5yr" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["period_5yr"] == filters.get("selected_period")]

        # Market tier filter
        if filters.get("market_tiers") and "market_tier_period" in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df["market_tier_period"].isin(filters.get("market_tiers"))
            ]

        # Custom Date Range Override (Phase 4)
        if filters.get("enable_custom_range") and filters.get("custom_date_range"):
            custom_start, custom_end = filters.get("custom_date_range")
            if "transaction_date" in filtered_df.columns:
                filtered_df = filtered_df[
                    (filtered_df["transaction_date"] >= custom_start) &
                    (filtered_df["transaction_date"] <= custom_end)
                ]
            st.info(f"📆 **Custom Date Range:** {custom_start.strftime('%Y-%m')} to {custom_end.strftime('%Y-%m')}")

        # Era filter (Phase 3)
        elif filters.get("period_mode") and filters.get("period_mode") != "whole":
            era = filters.get("period_mode")
            if "era" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["era"] == era]

        # Cross-Era Comparison (Phase 4)
        if filters.get("enable_cross_era") and filters.get("era_1") and filters.get("era_2"):
            era_1 = filters.get("era_1")
            era_2 = filters.get("era_2")

            # Create separate DataFrames for each era
            df_era_1 = df[df["era"] == era_1] if "era" in df.columns else df
            df_era_2 = df[df["era"] == era_2] if "era" in df.columns else df

            # Show comparison banner
            st.markdown("### 🔄 Cross-Era Comparison")
            col1, col2 = st.columns(2)

            with col1:
                st.info(f"**{era_1.upper()}** ({'2015-2021' if era_1 == 'pre_covid' else '2022-2026'})")
                era_1_stats = {
                    'count': len(df_era_1),
                    'median_price': df_era_1['price'].median() if 'price' in df_era_1.columns else 0,
                    'median_psf': df_era_1['price_psf'].median() if 'price_psf' in df_era_1.columns else 0,
                }
                st.metric("Transactions", f"{era_1_stats['count']:,}")
                st.metric("Median Price", f"${era_1_stats['median_price']:,.0f}")
                st.metric("Median PSF", f"${era_1_stats['median_psf']:,.0f}")

            with col2:
                st.info(f"**{era_2.upper()}** ({'2015-2021' if era_2 == 'pre_covid' else '2022-2026'})")
                era_2_stats = {
                    'count': len(df_era_2),
                    'median_price': df_era_2['price'].median() if 'price' in df_era_2.columns else 0,
                    'median_psf': df_era_2['price_psf'].median() if 'price_psf' in df_era_2.columns else 0,
                }
                st.metric("Transactions", f"{era_2_stats['count']:,}")
                st.metric("Median Price", f"${era_2_stats['median_price']:,.0f}")
                st.metric("Median PSF", f"${era_2_stats['median_psf']:,.0f}")

            # Calculate changes
            if era_1_stats['median_price'] > 0:
                price_change = ((era_2_stats['median_price'] - era_1_stats['median_price']) / era_1_stats['median_price']) * 100
                st.metric("Price Change", f"{price_change:+.1f}%", delta=f"{price_change:+.1f}%")

            if era_1_stats['median_psf'] > 0:
                psf_change = ((era_2_stats['median_psf'] - era_1_stats['median_psf']) / era_1_stats['median_psf']) * 100
                st.metric("PSF Change", f"{psf_change:+.1f}%", delta=f"{psf_change:+.1f}%")

            st.markdown("---")

        # 3-Way Era Comparison (Phase 4)
        if filters.get("enable_3way_comparison"):
            st.markdown("### 📊 3-Way Era Comparison")

            # Create DataFrames for each sub-era
            if 'year' in df.columns:
                df_pre_covid = df[df['year'] <= 2019]
                df_covid = df[(df['year'] >= 2020) & (df['year'] <= 2021)]
                df_post_covid = df[df['year'] >= 2022]
            else:
                df_pre_covid = df[df['transaction_date'].dt.year <= 2019]
                df_covid = df[(df['transaction_date'].dt.year >= 2020) & (df['transaction_date'].dt.year <= 2021)]
                df_post_covid = df[df['transaction_date'].dt.year >= 2022]

            # Display comparison table
            era_data = []
            for era_name, era_df in [('Pre-COVID (2015-2019)', df_pre_covid), ('COVID (2020-2021)', df_covid), ('Post-COVID (2022-2026)', df_post_covid)]:
                if not era_df.empty and 'price' in era_df.columns:
                    era_data.append({
                        'Era': era_name,
                        'Transactions': len(era_df),
                        'Median Price': f"${era_df['price'].median():,.0f}",
                        'Median PSF': f"${era_df['price_psf'].median():,.0f}" if 'price_psf' in era_df.columns else 'N/A',
                    })

            if era_data:
                st.table(pd.DataFrame(era_data))

            st.markdown("---")

        # Show era banner - more professional presentation
        period_mode = filters.get("period_mode", "whole")
        if filters.get("enable_custom_range"):
            pass  # Custom range banner already shown above
        elif period_mode == "whole":
            st.info(
                "📊 **Analysis Period**: **All Historical Data** (1990-2026) | "
                f"Showing **{len(filtered_df):,}** transactions across all time periods"
            )
        elif period_mode == "pre_covid":
            st.info(
                "📊 **Analysis Period**: **Pre-COVID Era** (2015-2021) | "
                f"Showing **{len(filtered_df):,}** transactions from pre-pandemic market"
            )
        elif period_mode == "recent":
            st.info(
                "📊 **Analysis Period**: **Post-COVID Era** (2022-2026) | "
                f"Showing **{len(filtered_df):,}** transactions from recent market recovery"
            )

    if filtered_df.empty:
        st.warning("No properties match your filters. Try adjusting your criteria.")
        return

    # Create map based on view mode
    with st.spinner("Aggregating data and rendering map..."):
        view_mode = map_settings.get("view_mode", "Planning Areas")
        map_style = map_settings.get("map_style", LIGHT_THEME)

        color_col = map_settings.get("color_column", "median_price")

        if view_mode == "Planning Areas":
            # Aggregate by planning area
            with st.spinner("Aggregating by planning area..."):
                aggregated_df = aggregate_by_planning_area(filtered_df, price_column="price")
            fig = create_planning_area_polygon_map(
                aggregated_df, color_column=color_col, theme=map_style
            )

        elif view_mode == "H3 Grid R6":
            with st.spinner("Aggregating by H3 grid (resolution 6)..."):
                aggregated_df = aggregate_by_h3(filtered_df, resolution=6, price_column="price")
            fig = create_h3_grid_map(
                aggregated_df, resolution=6, color_column=color_col, theme=map_style
            )

        elif view_mode == "H3 Grid R7":
            with st.spinner("Aggregating by H3 grid (resolution 7)..."):
                aggregated_df = aggregate_by_h3(filtered_df, resolution=7, price_column="price")
            fig = create_h3_grid_map(
                aggregated_df, resolution=7, color_column=color_col, theme=map_style
            )

        elif view_mode == "H3 Grid R8":
            with st.spinner("Aggregating by H3 grid (resolution 8)..."):
                aggregated_df = aggregate_by_h3(filtered_df, resolution=8, price_column="price")
            fig = create_h3_grid_map(
                aggregated_df, resolution=8, color_column=color_col, theme=map_style
            )

        elif view_mode == "H3 Grid R9":
            with st.spinner("Aggregating by H3 grid (resolution 9)..."):
                aggregated_df = aggregate_by_h3(filtered_df, resolution=9, price_column="price")
            fig = create_h3_grid_map(
                aggregated_df, resolution=9, color_column=color_col, theme=map_style
            )

    # Display the map
    st.markdown("### 📍 Interactive Map")
    st.plotly_chart(fig, use_container_width=True)

    # Info about aggregation - more professional presentation
    info_col1, info_col2 = st.columns([3, 1])
    with info_col1:
        st.info(
            f"**📊 Aggregation Summary**: Displaying **{len(aggregated_df):,}** {view_mode.lower()} cells "
            f"representing **{len(filtered_df):,}** property transactions"
        )

    # Performance warning for large datasets
    if view_mode in ["H3 Grid R6", "H3 Grid R7", "H3 Grid R8", "H3 Grid R9"] and len(aggregated_df) > 10000:
        with info_col2:
            st.warning(
                f"⚠️ **Large Dataset**: {len(aggregated_df):,} cells\n\n"
                "For better performance, apply filters or switch to Planning Areas view."
            )

    st.markdown("---")

    # Display metrics dashboard
    display_enhanced_metrics_dashboard(filtered_df, aggregated_df)

    # Data preview
    with st.expander("📋 View Filtered Data (First 100 Rows)", expanded=False):
        display_cols = [
            "transaction_date",
            "property_type",
            "town",
            "planning_area",
            "address",
            "price",
            "floor_area_sqft",
            "price_psf",
            "rental_yield_pct",
            "dist_to_nearest_mrt",
            "mom_change_pct",
            "period_5yr",
            "market_tier_period",
            "psf_tier_period",
        ]
        display_cols = [col for col in display_cols if col in filtered_df.columns]

        st.dataframe(filtered_df[display_cols].head(100), use_container_width=True)

    # Export section - more professional
    st.markdown("### 💾 Export Data")
    col1, col2 = st.columns([1, 2])

    with col1:
        if st.button("📥 **Export Filtered Data to CSV**", type="primary"):
            csv = filtered_df.to_csv(index=False)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name=f"sg_housing_prices_{timestamp}.csv",
                mime="text/csv",
            )

    with col2:
        st.info(
            "💡 **Tip**: Use the filters on the left to narrow down your search. "
            "The exported CSV contains all filtered data (not just the preview)."
        )

    # Help section - more professional
    with st.expander("📖 User Guide", expanded=False):
        st.markdown("""
        ## Map Visualization Guide

        ### 🎨 Understanding View Modes

        **Planning Areas** (Default)
        - Shows 55 URA planning areas with polygon boundaries
        - Best for: Regional price comparisons, neighborhood analysis
        - Performance: Excellent

        **H3 Grid R6/R7/R8/R9** (Hexagonal Grids)
        - Hierarchical hexagonal spatial indexing
        - **R6**: ~700 cells - Quick regional overview
        - **R7**: ~5,000 cells - Balanced detail
        - **R8**: ~14,000 cells - Fine-grained analysis
        - **R9**: ~100,000 cells - Ultra-fine detail (use with narrow filters)
        - Best for: Detecting micro-price patterns, hotspots

        ### 🎨 Color Scale

        The map uses a 5-point color scale:
        - 🔵 **Blue** = Lowest prices/value
        - 🟢 **Green** = Below average
        - 🟡 **Yellow** = Average
        - 🟠 **Orange** = Above average
        - 🔴 **Red** = Highest prices/value

        ### 📊 "Color By" Options

        - **Median Price**: Typical transaction price in the area/cell
        - **Median PSF**: Price per square foot (normalizes for property size)
        - **Transaction Count**: Number of transactions (shows market activity)
        - **Average Price**: Mean transaction price

        ### 🔍 Filter Tips

        **Property Type**
        - Select multiple types to compare
        - HDB = Public housing (95% of market)
        - Condominium = Private apartments

        **Location Filters**
        - **Planning Area**: 55 URA planning areas
        - **Town**: HDB town (e.g., Ang Mo Kio, Bedok)
        - **Postal District**: 01-83 (District 09 = Orchard, District 10 = Holland Rd)
        - **Combine filters**: Use multiple filters for precise results

        **Price & Size**
        - Set price range to focus on your budget
        - Filter by floor area for specific room sizes

        **Time Period**
        - View recent trends or historical data
        - Narrow range = better performance

        ### ⚡ Performance Tips

        1. **Planning Areas view** is fastest
        2. **H3 R6** for quick overviews
        3. **H3 R7** for balanced detail
        4. **Apply filters** to reduce data size
        5. **Use H3 R8/R9 only** with narrow filters

        ### 📊 Data Overview

        - **Sources**: HDB Resale (1990-2026), URA Private (2015-2026)
        - **Total**: ~1M+ transactions
        - **Coordinates**: Geocoded via OneMap API
        - **Updates**: Monthly

        ### 🎯 Common Workflows

        **Find Affordable Areas**
        1. Select "Median Price" for Color By
        2. Look for blue/green regions
        3. Apply price filters to narrow search

        **Investment Analysis**
        1. Use H3 Grid R7 for detail
        2. Color by "Transaction Count" to find active markets
        3. Switch to "Median PSF" to compare value

        **Compare Neighborhoods**
        1. Use Planning Areas view
        2. Select specific areas in filters
        3. Color by "Median PSF" for size-normalized comparison
        """)


if __name__ == "__main__":
    main()
