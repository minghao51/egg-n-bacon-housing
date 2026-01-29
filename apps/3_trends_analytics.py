"""
Trends & Analytics - Time-series trend analysis and comparative statistics.

Features:
- Customizable time granularity (Monthly, Quarterly, Yearly)
- Price trend charts with growth rates
- Comparative analysis by town and property type
- Transaction volume analysis
- Correlation matrices and scatter plots
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_loader import load_unified_data, apply_unified_filters
from core.chart_utils import (
    aggregate_by_timeperiod,
    create_trend_line_chart,
    create_multi_series_trend,
    create_volume_bar_chart,
    create_growth_rate_chart,
    create_comparison_boxplot,
    create_correlation_heatmap,
    create_scatter_analysis,
    display_metrics_cards,
)

# Page config
st.set_page_config(page_title="Trends & Analytics", page_icon="", layout="wide")

# Light theme styling
st.markdown(
    """
<style>
    .stApp {
        background-color: #ffffff;
    }
    .chart-container {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


def render_filters():
    """Render filter controls for trends."""

    st.sidebar.header("Trend Filters")

    # Get data
    df = load_unified_data()

    if df.empty:
        return {}

    # Property Type
    st.sidebar.subheader("Property Type")
    property_types = st.sidebar.multiselect(
        "Property Types",
        sorted(df["property_type"].unique()) if "property_type" in df.columns else [],
        default=sorted(df["property_type"].unique()) if "property_type" in df.columns else [],
    )

    # Date Range
    st.sidebar.subheader("Time Period")
    if "month" in df.columns:
        date_min = df["month"].min().to_pydatetime()
        date_max = df["month"].max().to_pydatetime()

        date_range = st.sidebar.slider("Date Range", date_min, date_max, (date_min, date_max))
    else:
        date_range = (datetime(2015, 1, 1), datetime.now())

    # Planning Area selection (for comparison)
    st.sidebar.subheader("📍 Location")
    if "planning_area" in df.columns:
        all_areas = sorted(df["planning_area"].unique())
        show_comparison = st.sidebar.checkbox("Enable Planning Area Comparison", value=False)

        if show_comparison:
            compare_areas = st.sidebar.multiselect(
                "Select Planning Areas to Compare", all_areas, default=all_areas[:5]
            )
        else:
            compare_areas = None
    else:
        show_comparison = False
        compare_areas = None

    # ============================================================================
    # PHASE 3 FEATURES: Era-Based Period Selection
    # ============================================================================
    st.sidebar.subheader("📅 Period Mode")

    period_mode = st.sidebar.radio(
        "Select Analysis Period",
        options=["whole", "pre_covid", "recent"],
        format_func=lambda x: {
            "whole": "Whole Period (All Data)",
            "pre_covid": "Pre-COVID (2015-2021)",
            "recent": "Recent (2022-2026)",
        }[x],
        index=0,
        help="Filter by era for comparative analysis",
    )

    # Show era statistics
    if period_mode != "whole" and "era" in df.columns:
        era_stats = df.groupby("era").agg({"price": ["count", "median"]}).reset_index()
        era_stats.columns = ["era", "count", "median_price"]
        selected_era_data = era_stats[era_stats["era"] == period_mode]
        if not selected_era_data.empty:
            count = selected_era_data.iloc[0]["count"]
            median = selected_era_data.iloc[0]["median_price"]
            st.sidebar.info(
                f"📊 {period_mode.replace('_', ' ').title()}: {count:,} transactions | Median: ${median:,.0f}"
            )

    # Period Filter
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

    # ============================================================================
    # PHASE 4: Cross-Era Comparison
    # ============================================================================
    st.sidebar.subheader("🔄 Era Comparison Mode")
    compare_mode = st.sidebar.checkbox(
        "Enable Cross-Era Comparison",
        value=False,
        help="Compare metrics between two different eras side-by-side",
    )

    if compare_mode:
        comparison_era_1 = st.sidebar.selectbox(
            "First Era to Compare",
            ["pre_covid", "recent"],
            index=0,
            format_func=lambda x: {
                "pre_covid": "Pre-COVID (2015-2021)",
                "recent": "Recent (2022-2026)",
            }[x],
        )

        comparison_era_2 = st.sidebar.selectbox(
            "Second Era to Compare",
            ["pre_covid", "recent"],
            index=1,
            format_func=lambda x: {
                "pre_covid": "Pre-COVID (2015-2021)",
                "recent": "Recent (2022-2026)",
            }[x],
        )
    else:
        comparison_era_1 = None
        comparison_era_2 = None

    # ============================================================================
    # PHASE 4: Custom Date Range
    # ============================================================================
    st.sidebar.subheader("📆 Custom Date Range")
    use_custom_range = st.sidebar.checkbox(
        "Use Custom Date Range",
        value=False,
        help="Override era selection with a specific date range",
    )

    if use_custom_range:
        if "month" in df.columns:
            date_min = df["month"].min().to_pydatetime()
            date_max = df["month"].max().to_pydatetime()

            custom_date_range = st.sidebar.slider(
                "Custom Date Range",
                date_min,
                date_max,
                (date_min, date_max),
            )
        else:
            custom_date_range = None
    else:
        custom_date_range = None

    return {
        "property_types": property_types,
        "date_range": date_range,
        "show_comparison": show_comparison,
        "compare_areas": compare_areas,
        "selected_period": selected_period,
        "market_tiers": market_tiers,
        "period_mode": period_mode,
        "compare_mode": compare_mode,
        "comparison_era_1": comparison_era_1,
        "comparison_era_2": comparison_era_2,
        "use_custom_range": use_custom_range,
        "custom_date_range": custom_date_range,
    }


def main():
    """Main function for Trends & Analytics page."""

    st.title("📈 Singapore Housing Trends & Analytics")
    st.markdown("---")

    # Render filters
    filters = render_filters()

    # Phase 3 Era Banner
    period_mode = filters.get("period_mode", "whole")
    if period_mode == "whole":
        st.info("📊 **Analysis Mode: Whole Period** - Viewing all data from 1990-2026")
    elif period_mode == "pre_covid":
        st.info(
            "📊 **Analysis Mode: Pre-COVID (2015-2021)** - Viewing historical market before recent boom"
        )
    elif period_mode == "recent":
        st.info("📊 **Analysis Mode: Recent (2022-2026)** - Viewing post-pandemic market recovery")

    # Phase 2 Feature Banner
    st.info("""
    💡 **NEW Phase 2 Features:**
    • **⏳ 5-Year Period Analysis** - Compare different eras (1990s vs 2020s)
    • **🎯 Market Tier Tracking** - See how Mass/Mid/Luxury thresholds evolved
    • **📊 New "Phase 2 Analysis" Tab** - Tier evolution, period comparison, lease decay

    Use the **"📅 Period Mode"** and **"⏳ Time Period Analysis"** filters in the sidebar!
    """)

    # Load and filter data
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
            towns=filters.get("compare_areas"),  # Apply town filter
            date_range=filters.get("date_range"),
        )

        # PHASE 2: Apply period filter
        if filters.get("selected_period") and "period_5yr" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["period_5yr"] == filters.get("selected_period")]

        # PHASE 2: Apply market tier filter
        if filters.get("market_tiers") and "market_tier_period" in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df["market_tier_period"].isin(filters.get("market_tiers"))
            ]

        # PHASE 3: Apply era filter
        if filters.get("period_mode") and filters.get("period_mode") != "whole":
            era = filters.get("period_mode")
            if "era" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["era"] == era]
            elif "year" in filtered_df.columns:
                if era == "pre_covid":
                    filtered_df = filtered_df[filtered_df["year"] <= 2021]
                elif era == "recent":
                    filtered_df = filtered_df[filtered_df["year"] >= 2022]

    if filtered_df.empty:
        st.warning("No data matches your filters. Try adjusting your criteria.")
        return

    # Display key metrics
    st.subheader("📊 Key Metrics")
    display_metrics_cards(filtered_df, columns=4)

    # ============================================================================
    # PHASE 4: Cross-Era Comparison Section
    # ============================================================================
    if filters.get("compare_mode"):
        st.markdown("---")
        st.subheader("🔄 Cross-Era Comparison")

        era_1 = filters.get("comparison_era_1", "pre_covid")
        era_2 = filters.get("comparison_era_2", "recent")

        era_1_label = "Pre-COVID (2015-2021)" if era_1 == "pre_covid" else "Recent (2022-2026)"
        era_2_label = "Pre-COVID (2015-2021)" if era_2 == "pre_covid" else "Recent (2022-2026)"

        # Filter data for each era
        df_era_1 = (
            df[df["era"] == era_1].copy() if "era" in df.columns else df[df["year"] <= 2021].copy()
        )
        df_era_2 = (
            df[df["era"] == era_2].copy() if "era" in df.columns else df[df["year"] >= 2022].copy()
        )

        # Apply same property type and tier filters to both
        if filters.get("property_types"):
            df_era_1 = df_era_1[df_era_1["property_type"].isin(filters.get("property_types", []))]
            df_era_2 = df_era_2[df_era_2["property_type"].isin(filters.get("property_types", []))]

        if filters.get("market_tiers") and "market_tier_period" in df.columns:
            df_era_1 = df_era_1[
                df_era_1["market_tier_period"].isin(filters.get("market_tiers", []))
            ]
            df_era_2 = df_era_2[
                df_era_2["market_tier_period"].isin(filters.get("market_tiers", []))
            ]

        # Calculate metrics for comparison
        era_1_median = df_era_1["price"].median() if "price" in df_era_1.columns else 0
        era_2_median = df_era_2["price"].median() if "price" in df_era_2.columns else 0
        median_change = (
            ((era_2_median - era_1_median) / era_1_median * 100) if era_1_median > 0 else 0
        )

        era_1_count = len(df_era_1)
        era_2_count = len(df_era_2)
        count_change = ((era_2_count - era_1_count) / era_1_count * 100) if era_1_count > 0 else 0

        era_1_mean_psf = df_era_1["price_psf"].median() if "price_psf" in df_era_1.columns else 0
        era_2_mean_psf = df_era_2["price_psf"].median() if "price_psf" in df_era_2.columns else 0
        psf_change = (
            ((era_2_mean_psf - era_1_mean_psf) / era_1_mean_psf * 100) if era_1_mean_psf > 0 else 0
        )

        # Display comparison metrics
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(f"Median Price ({era_1_label})", f"${era_1_median:,.0f}")
        with c2:
            st.metric(
                f"Median Price ({era_2_label})",
                f"${era_2_median:,.0f}",
                delta=f"{median_change:.1f}%",
            )
        with c3:
            st.metric(f"Transactions ({era_1_label})", f"{era_1_count:,}")
        with c4:
            st.metric(
                f"Transactions ({era_2_label})", f"{era_2_count:,}", delta=f"{count_change:.1f}%"
            )

        # Property type breakdown comparison
        st.markdown("#### Property Type Distribution")

        if "property_type" in df.columns:
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown(f"**{era_1_label}**")
                era_1_dist = df_era_1["property_type"].value_counts()
                st.dataframe(
                    pd.DataFrame(
                        {
                            "Property Type": era_1_dist.index,
                            "Count": era_1_dist.values,
                            "%": (era_1_dist.values / era_1_dist.sum() * 100).round(1),
                        }
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

            with col_b:
                st.markdown(f"**{era_2_label}**")
                era_2_dist = df_era_2["property_type"].value_counts()
                st.dataframe(
                    pd.DataFrame(
                        {
                            "Property Type": era_2_dist.index,
                            "Count": era_2_dist.values,
                            "%": (era_2_dist.values / era_2_dist.sum() * 100).round(1),
                        }
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

        st.info(
            f"💡 **Comparison:** {era_1_label} vs {era_2_label} | Price Change: {median_change:+.1f}% | Volume Change: {count_change:+.1f}%"
        )

    # ============================================================================
    # PHASE 4: Custom Date Range Indicator
    # ============================================================================
    if filters.get("use_custom_range") and filters.get("custom_date_range"):
        dr = filters.get("custom_date_range")
        st.info(
            f"📆 **Custom Date Range:** {dr[0].strftime('%Y-%m')} to {dr[1].strftime('%Y-%m')} | {len(filtered_df):,} transactions"
        )

    st.markdown("---")

    # Time granularity selector
    col1, col2, col3 = st.columns([2, 2, 3])

    with col1:
        granularity = st.selectbox(
            "Time Granularity",
            ["Monthly", "Quarterly", "Yearly"],
            index=0,
            help="Level of time aggregation",
        )

    with col2:
        metric = st.selectbox(
            "Metric", ["Median Price", "Transaction Volume", "Price Growth (%)"], index=0
        )

    with col3:
        chart_height = st.slider("Chart Height", 400, 800, 500, step=50)

    # Aggregate data
    agg_df = aggregate_by_timeperiod(filtered_df, granularity.lower())

    if agg_df.empty:
        st.warning("Unable to aggregate data by time period.")
        return

    # Create tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Price Trends", "Comparisons", "Volume Analysis", "Correlations", "Phase 2 Analysis"]
    )

    with tab1:
        st.subheader(f"Price Trends - {granularity}")

        # Main trend chart
        if metric == "Median Price":
            fig = create_trend_line_chart(
                agg_df, metric="median_price", title=f"Median Price ({granularity})"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Growth rate
            st.subheader("Price Growth Rate")
            growth_fig = create_growth_rate_chart(agg_df)
            st.plotly_chart(growth_fig, use_container_width=True)

        elif metric == "Transaction Volume":
            fig = create_volume_bar_chart(agg_df)
            st.plotly_chart(fig, use_container_width=True)

        else:  # Price Growth
            growth_fig = create_growth_rate_chart(agg_df)
            st.plotly_chart(growth_fig, use_container_width=True)

        # Data table - dynamic columns based on what's available
        with st.expander("📊 View Data Table"):
            # Build column list dynamically
            display_cols = ["period_str"]

            # Add price column if available
            if "median_price" in agg_df.columns:
                display_cols.append("median_price")
            elif "mean_price" in agg_df.columns:
                display_cols.append("mean_price")

            # Add transaction count if available
            if "transaction_count" in agg_df.columns:
                display_cols.append("transaction_count")

            # Add growth rate if available
            if "price_growth_pct" in agg_df.columns:
                display_cols.append("price_growth_pct")

            # PHASE 2: Add period columns if available (from filtered_df, not agg_df)
            # Note: agg_df is time-aggregated, so period info might be lost
            # We'll show period info in a separate expander

            # Create column config dynamically
            col_config = {
                "period_str": st.column_config.TextColumn("Period"),
            }

            if "median_price" in display_cols:
                col_config["median_price"] = st.column_config.NumberColumn(
                    "Median Price", format="$%d"
                )
            elif "mean_price" in display_cols:
                col_config["mean_price"] = st.column_config.NumberColumn("Mean Price", format="$%d")

            if "transaction_count" in display_cols:
                col_config["transaction_count"] = st.column_config.NumberColumn("Transactions")

            if "price_growth_pct" in display_cols:
                col_config["price_growth_pct"] = st.column_config.NumberColumn(
                    "Growth %", format="%.2f%%"
                )

            st.dataframe(agg_df[display_cols], column_config=col_config, use_container_width=True)

            # PHASE 2: Period information
            if filters.get("selected_period"):
                st.info(f"📅 **Current Period Filter:** {filters.get('selected_period')}")

            if filters.get("market_tiers"):
                st.info(f"🎯 **Current Tier Filter:** {', '.join(filters.get('market_tiers'))}")

    with tab2:
        st.subheader("Comparative Analysis")

        col1, col2 = st.columns(2)

        with col1:
            comparison_type = st.selectbox(
                "Compare By", ["Planning Area", "Property Type", "Flat Type"], index=0
            )

        with col2:
            top_n = st.slider("Number of Categories", 5, 20, 10)

        if comparison_type == "Planning Area":
            group_col = "planning_area"
        elif comparison_type == "Property Type":
            group_col = "property_type"
        else:  # Flat Type
            group_col = "flat_type" if "flat_type" in filtered_df.columns else "property_type"

        # Box plot
        st.subheader(f"Price Distribution by {comparison_type}")

        price_col = "price"  # L3 unified dataset uses 'price' column
        if price_col in filtered_df.columns and group_col in filtered_df.columns:
            box_fig = create_comparison_boxplot(
                filtered_df, group_column=group_col, price_column=price_col
            )
            st.plotly_chart(box_fig, use_container_width=True)

        # Multi-series trend
        if filters.get("show_comparison") and filters.get("compare_areas"):
            st.subheader("Price Trends by Planning Area")

            # Aggregate by planning area and time period
            df_with_area = filtered_df[filtered_df["planning_area"].isin(filters["compare_areas"])]

            if not df_with_area.empty:
                # Create time period grouping
                df_with_area = df_with_area.copy()
                df_with_area["date"] = pd.to_datetime(df_with_area["month"])

                if granularity == "monthly":
                    df_with_area["period"] = df_with_area["date"].dt.to_period("M")
                elif granularity == "quarterly":
                    df_with_area["period"] = df_with_area["date"].dt.to_period("Q")
                else:
                    df_with_area["period"] = df_with_area["date"].dt.to_period("Y")

                df_with_area["period_str"] = df_with_area["period"].astype(str)

                # Aggregate by planning area and period
                area_agg = (
                    df_with_area.groupby(["period", "planning_area"])[price_col]
                    .median()
                    .reset_index()
                )
                area_agg["period_str"] = area_agg["period"].astype(str)

                multi_fig = create_multi_series_trend(
                    area_agg, series_column="planning_area", top_n=len(filters["compare_areas"])
                )
                st.plotly_chart(multi_fig, use_container_width=True)
        else:
            st.info("💡 Enable planning area comparison in the sidebar to see multi-area trends.")

    with tab3:
        st.subheader("Transaction Volume Analysis")

        col1, col2 = st.columns(2)

        with col1:
            vol_fig = create_volume_bar_chart(agg_df)
            st.plotly_chart(vol_fig, use_container_width=True)

        with col2:
            # Volume by property type
            if "property_type" in filtered_df.columns:
                prop_type_volume = filtered_df.groupby("property_type").size()

                import plotly.express as px

                pie_fig = px.pie(
                    values=prop_type_volume.values,
                    names=prop_type_volume.index,
                    title="Transactions by Property Type",
                    template="plotly_dark",
                )
                st.plotly_chart(pie_fig, use_container_width=True)

        # Volume over time by property type
        if "property_type" in filtered_df.columns:
            st.subheader("Transaction Volume by Property Type Over Time")

            # Add time grouping
            df_for_vol = filtered_df.copy()
            df_for_vol["date"] = pd.to_datetime(df_for_vol["month"])

            if granularity == "monthly":
                df_for_vol["period"] = df_for_vol["date"].dt.to_period("M")
            elif granularity == "quarterly":
                df_for_vol["period"] = df_for_vol["date"].dt.to_period("Q")
            else:
                df_for_vol["period"] = df_for_vol["date"].dt.to_period("Y")

            df_for_vol["period_str"] = df_for_vol["period"].astype(str)

            vol_by_type = (
                df_for_vol.groupby(["period", "property_type"]).size().reset_index(name="count")
            )
            vol_by_type["period_str"] = vol_by_type["period"].astype(str)

            # Create stacked bar chart
            import plotly.graph_objects as go

            prop_types = vol_by_type["property_type"].unique()

            fig = go.Figure()

            for prop_type in prop_types:
                data = vol_by_type[vol_by_type["property_type"] == prop_type]
                fig.add_trace(go.Bar(x=data["period_str"], y=data["count"], name=prop_type))

            fig.update_layout(
                barmode="stack",
                title="Transaction Volume by Property Type",
                xaxis_title="Time Period",
                yaxis_title="Number of Transactions",
                template="plotly_dark",
                height=500,
            )

            st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.subheader("Correlations & Relationships")

        col1, col2 = st.columns(2)

        with col1:
            x_axis = st.selectbox(
                "X-Axis", ["Floor Area (sqft)", "Price ($PSF)", "Remaining Lease"], index=0
            )

        with col2:
            y_axis = st.selectbox(
                "Y-Axis", ["Resale Price", "Price ($PSF)", "Floor Area (sqft)"], index=0
            )

        # Map column names
        col_mapping = {
            "Floor Area (sqft)": "floor_area_sqft"
            if "floor_area_sqft" in filtered_df.columns
            else "Area (SQFT)",
            "Price ($PSF)": "price_psf"
            if "price_psf" in filtered_df.columns
            else "Unit Price ($ PSF)",
            "Remaining Lease": "remaining_lease_months",
            "Resale Price": "price",  # L3 unified dataset uses 'price' column
        }

        x_col = col_mapping.get(x_axis)
        y_col = col_mapping.get(y_axis)

        if x_col and y_col and x_col in filtered_df.columns and y_col in filtered_df.columns:
            scatter_fig = create_scatter_analysis(
                filtered_df,
                x_column=x_col,
                y_column=y_col,
                color_column="property_type" if "property_type" in filtered_df.columns else None,
            )
            st.plotly_chart(scatter_fig, use_container_width=True)

        # Correlation heatmap
        with st.expander("📊 Correlation Matrix"):
            corr_fig = create_correlation_heatmap(filtered_df)
            st.plotly_chart(corr_fig, use_container_width=True)

    with tab5:
        st.subheader("⏳ Phase 2: Time Period & Market Segmentation Analysis")

        # Phase 2 info banner
        st.info("""
        💡 **NEW Phase 2 Features:**
        • **📊 Tier Evolution** - See how market tier thresholds changed over 36 years
        • **⏳ Period Comparison** - Compare different 5-year periods side-by-side
        • **🏠 Lease Decay** - Understand price impact by remaining lease (HDB)

        These analyses account for inflation and market evolution, showing how "luxury" and "mass market" definitions change over time.
        """)

        # Check if Phase 2 columns are available
        if "period_5yr" not in filtered_df.columns:
            st.warning(
                "Phase 2 features require period-dependent segmentation. Please ensure your L3 dataset includes period columns."
            )
            return

        # ============================================================================
        # Section 1: Tier Threshold Evolution Chart
        # ============================================================================
        st.markdown("---")
        st.markdown("### 📊 Tier Threshold Evolution")

        st.markdown("""
        **How Tier Thresholds Changed Over 36 Years**

        This chart shows the maximum price for each market tier within every 5-year period.
        Notice how "Luxury" in the 1990s ($130K for HDB) became "Mass Market" by the 2020s.
        """)

        # Property type selector
        ptype_select = st.selectbox(
            "Select Property Type for Tier Evolution",
            sorted(filtered_df["property_type"].unique()),
            key="tier_evolution_ptype",
        )

        # Calculate tier thresholds by period
        if ptype_select:
            ptype_df = filtered_df[filtered_df["property_type"] == ptype_select].copy()

            if not ptype_df.empty and "market_tier_period" in ptype_df.columns:
                # Get max price for each tier in each period
                tier_thresholds = (
                    ptype_df.groupby(["period_5yr", "market_tier_period"])["price"]
                    .max()
                    .reset_index()
                )

                # Sort periods
                tier_thresholds = tier_thresholds.sort_values("period_5yr")

                # Create evolution chart
                import plotly.express as px

                fig_evolution = px.line(
                    tier_thresholds,
                    x="period_5yr",
                    y="price",
                    color="market_tier_period",
                    markers=True,
                    title=f"{ptype_select} Tier Threshold Evolution (Max Price by Tier)",
                    labels={
                        "period_5yr": "5-Year Period",
                        "price": "Maximum Price ($)",
                        "market_tier_period": "Market Tier",
                    },
                    template="plotly_white",
                    height=500,
                )

                fig_evolution.update_layout(
                    hovermode="x unified",
                    xaxis_title="5-Year Period",
                    yaxis_title="Maximum Price ($)",
                )

                fig_evolution.update_traces(
                    hovertemplate="<b>%{fullData.name}</b><br>Period: %{x}<br>Max Price: $%{y:,.0f}<extra></extra>"
                )

                st.plotly_chart(fig_evolution, use_container_width=True)

                # Insights callout
                with st.expander("💡 Key Insights: Tier Evolution"):
                    # Calculate growth rate for luxury tier
                    luxury_data = tier_thresholds[tier_thresholds["market_tier_period"] == "Luxury"]
                    if len(luxury_data) >= 2:
                        first_luxury = luxury_data.iloc[0]["price"]
                        last_luxury = luxury_data.iloc[-1]["price"]
                        growth_rate = ((last_luxury - first_luxury) / first_luxury) * 100

                        st.markdown(f"""
                        **{ptype_select} Luxury Tier Growth:**
                        - **First Period** ({luxury_data.iloc[0]["period_5yr"]}): ${first_luxury:,.0f}
                        - **Last Period** ({luxury_data.iloc[-1]["period_5yr"]}): ${last_luxury:,.0f}
                        - **Total Growth**: {growth_rate:.1f}% over {len(luxury_data) * 5} years

                        This demonstrates long-term price appreciation and inflation effects.
                        """)

        # ============================================================================
        # Section 2: Period Comparison
        # ============================================================================
        st.markdown("---")
        st.markdown("### ⏳ Period Comparison Analysis")

        st.markdown("""
        **Compare Different Eras Side-by-Side**

        Select two periods to compare transaction patterns, price distributions, and tier mixes.
        """)

        col1, col2 = st.columns(2)

        with col1:
            # Period selector for comparison
            all_periods = sorted(filtered_df["period_5yr"].unique())

            if len(all_periods) >= 2:
                period_1 = st.selectbox(
                    "Select First Period",
                    all_periods,
                    index=len(all_periods) - 2 if len(all_periods) >= 2 else 0,
                    key="period_1_compare",
                )
            else:
                period_1 = all_periods[0] if all_periods else None

        with col2:
            if len(all_periods) >= 2:
                period_2 = st.selectbox(
                    "Select Second Period",
                    all_periods,
                    index=len(all_periods) - 1 if len(all_periods) >= 2 else 0,
                    key="period_2_compare",
                )
            else:
                period_2 = all_periods[-1] if len(all_periods) > 1 else None

        if period_1 and period_2 and period_1 != period_2:
            # Get data for both periods
            df_p1 = filtered_df[filtered_df["period_5yr"] == period_1]
            df_p2 = filtered_df[filtered_df["period_5yr"] == period_2]

            # Comparison metrics
            c1, c2, c3, c4 = st.columns(4)

            with c1:
                median_p1 = df_p1["price"].median()
                st.metric(f"Median Price ({period_1})", f"${median_p1:,.0f}")

            with c2:
                median_p2 = df_p2["price"].median()
                st.metric(f"Median Price ({period_2})", f"${median_p2:,.0f}")

            with c3:
                pct_change = ((median_p2 - median_p1) / median_p1) * 100
                delta_color = "normal" if pct_change >= 0 else "inverse"
                st.metric("Price Change", f"{pct_change:+.1f}%", delta_color=delta_color)

            with c4:
                vol_p1 = len(df_p1)
                vol_p2 = len(df_p2)
                vol_change = ((vol_p2 - vol_p1) / vol_p1) * 100
                st.metric("Volume Change", f"{vol_change:+.1f}%")

            # Tier distribution comparison
            st.markdown("**Tier Distribution Comparison**")

            tier_dist_p1 = df_p1["market_tier_period"].value_counts(normalize=True) * 100
            tier_dist_p2 = df_p2["market_tier_period"].value_counts(normalize=True) * 100

            comparison_df = pd.DataFrame({period_1: tier_dist_p1, period_2: tier_dist_p2}).T

            st.dataframe(comparison_df.style.format("{:.1f}%"), use_container_width=True)

        # ============================================================================
        # Section 3: Lease Decay Analysis (HDB only)
        # ============================================================================
        st.markdown("---")
        st.markdown("### 🏠 Lease Decay Impact (HDB)")

        if "property_type" in filtered_df.columns:
            hdb_df = filtered_df[filtered_df["property_type"] == "HDB"].copy()

            # Convert remaining_lease_months to years if needed
            if (
                "remaining_lease_months" in hdb_df.columns
                and "remaining_lease_years" not in hdb_df.columns
            ):
                hdb_df["remaining_lease_years"] = hdb_df["remaining_lease_months"] / 12

            if not hdb_df.empty and "remaining_lease_years" in hdb_df.columns:
                st.markdown("""
                **How Remaining Lease Affects HDB Prices**

                Properties with shorter remaining leases typically sell at discounts due to
                the finite nature of HDB leases (99 years from construction).
                """)

                # Create lease bands
                hdb_df["lease_band"] = pd.cut(
                    hdb_df["remaining_lease_years"],
                    bins=[0, 60, 70, 80, 90, 100],
                    labels=["<60 years", "60-70 years", "70-80 years", "80-90 years", "90+ years"],
                )

                # Calculate median price by lease band
                lease_prices = (
                    hdb_df.groupby("lease_band", observed=True)["price"].median().sort_index()
                )

                # Calculate discount to baseline (90+ years)
                if "90+ years" in lease_prices.index:
                    baseline = lease_prices["90+ years"]
                    lease_discounts = ((baseline - lease_prices) / baseline * 100).sort_values(
                        ascending=False
                    )

                    # Display discount chart
                    import plotly.graph_objects as go

                    fig_lease = go.Figure()

                    fig_lease.add_trace(
                        go.Bar(
                            x=lease_discounts.index.astype(str),
                            y=lease_discounts.values,
                            marker_color=[
                                "#ef4444" if x > 5 else "#f97316" if x > 2 else "#22c55e"
                                for x in lease_discounts.values
                            ],
                            text=[f"{x:.1f}%" for x in lease_discounts.values],
                            textposition="outside",
                        )
                    )

                    fig_lease.update_layout(
                        title="HDB Price Discount by Remaining Lease Band (vs 90+ years)",
                        xaxis_title="Remaining Lease Band",
                        yaxis_title="Discount to Baseline (%)",
                        template="plotly_white",
                        height=450,
                    )

                    st.plotly_chart(fig_lease, use_container_width=True)

                    # Data table
                    with st.expander("📊 Lease Band Statistics"):
                        lease_stats = (
                            hdb_df.groupby("lease_band", observed=True)
                            .agg({"price": ["count", "median", "mean"]})
                            .round(0)
                        )

                        lease_stats.columns = ["Transactions", "Median Price", "Mean Price"]
                        lease_stats["Median Price"] = lease_stats["Median Price"].apply(
                            lambda x: f"${x:,.0f}"
                        )
                        lease_stats["Mean Price"] = lease_stats["Mean Price"].apply(
                            lambda x: f"${x:,.0f}"
                        )

                        st.dataframe(lease_stats, use_container_width=True)

                else:
                    st.info("No properties with 90+ years remaining lease in current filter.")
            else:
                st.info("Lease decay analysis requires HDB properties with remaining lease data.")
        else:
            st.info("Lease decay analysis is available for HDB properties only.")

    # ============================================================================
    # NEW: Precomputed L3 Metrics Section
    # ============================================================================
    st.markdown("---")
    st.subheader("📊 Precomputed Market Metrics (L3)")

    if "mom_change_pct" in filtered_df.columns:
        metrics_data = filtered_df[filtered_df["mom_change_pct"].notna()].copy()

        if not metrics_data.empty:
            st.info("""
            **💡 L3 Precomputed Metrics:**
            These metrics were precomputed using stratified median methodology to eliminate compositional bias.
            Data available from 2015 onwards for accurate growth rate calculations.
            """)

            # Metric overview cards
            mcol1, mcol2, mcol3, mcol4 = st.columns(4)

            with mcol1:
                avg_mom = metrics_data["mom_change_pct"].mean()
                st.metric("Avg Monthly Growth", f"{avg_mom:.2f}%")

            with mcol2:
                if "yoy_change_pct" in metrics_data.columns:
                    avg_yoy = metrics_data["yoy_change_pct"].mean()
                    st.metric("Avg Yearly Growth", f"{avg_yoy:.2f}%")

            with mcol3:
                if "momentum_signal" in metrics_data.columns:
                    bullish_count = (metrics_data["momentum_signal"] == "Strong Acceleration").sum()
                    bullish_pct = bullish_count / len(metrics_data) * 100
                    st.metric("Bullish Signals", f"{bullish_pct:.1f}%")

            with mcol4:
                coverage = len(metrics_data) / len(filtered_df) * 100
                st.metric("Metrics Coverage", f"{coverage:.1f}%")

            # Growth rate trend by planning area (if available)
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Recent Market Momentum by Area**")

                if (
                    "planning_area" in metrics_data.columns
                    and "momentum_signal" in metrics_data.columns
                ):
                    # Get recent data (last 3 months)
                    recent_date = metrics_data["transaction_date"].max()
                    three_months_ago = recent_date - pd.DateOffset(months=3)
                    recent_metrics = metrics_data[
                        metrics_data["transaction_date"] >= three_months_ago
                    ]

                    if not recent_metrics.empty:
                        # Count momentum signals by area
                        momentum_summary = (
                            recent_metrics.groupby("planning_area")["momentum_signal"]
                            .apply(lambda x: (x == "Strong Acceleration").sum())
                            .sort_values(ascending=False)
                            .head(10)
                        )

                        if not momentum_summary.empty:
                            momentum_df = pd.DataFrame(
                                {
                                    "Planning Area": momentum_summary.index,
                                    "Bullish Signals (3mo)": momentum_summary.values,
                                }
                            )
                            st.dataframe(momentum_df, use_container_width=True)

            with col2:
                st.markdown("**Top Growth Areas (Month-over-Month)**")

                if "planning_area" in metrics_data.columns:
                    # Get last month's data
                    last_month = metrics_data["transaction_date"].max()
                    last_month_data = metrics_data[metrics_data["transaction_date"] == last_month]

                    if not last_month_data.empty:
                        top_growth = (
                            last_month_data.groupby("planning_area")["mom_change_pct"]
                            .mean()
                            .sort_values(ascending=False)
                            .head(10)
                        )

                        if not top_growth.empty:
                            growth_df = pd.DataFrame(
                                {
                                    "Planning Area": top_growth.index,
                                    "MoM Growth %": top_growth.values.round(2),
                                }
                            )
                            st.dataframe(growth_df, use_container_width=True)

            # Market Momentum Timeline
            st.markdown("**Market Momentum Timeline**")

            if (
                "transaction_date" in metrics_data.columns
                and "mom_change_pct" in metrics_data.columns
            ):
                # Aggregate by month
                monthly_momentum = (
                    metrics_data.groupby("transaction_date")
                    .agg(
                        {
                            "mom_change_pct": "mean",
                            "stratified_median_price": "mean"
                            if "stratified_median_price" in metrics_data.columns
                            else "count",
                        }
                    )
                    .reset_index()
                )

                if not monthly_momentum.empty:
                    import plotly.graph_objects as go

                    fig_momentum = go.Figure()

                    # Add growth rate line
                    fig_momentum.add_trace(
                        go.Scatter(
                            x=monthly_momentum["transaction_date"],
                            y=monthly_momentum["mom_change_pct"],
                            mode="lines+markers",
                            name="Monthly Growth %",
                            line=dict(color="#00BCD4", width=2),
                        )
                    )

                    # Add zero line
                    fig_momentum.add_hline(y=0, line_dash="dash", line_color="gray")

                    fig_momentum.update_layout(
                        title="Average Month-over-Month Growth Rate Over Time",
                        xaxis_title="Date",
                        yaxis_title="Growth Rate (%)",
                        template="plotly_white",
                        height=400,
                        hovermode="x unified",
                    )

                    st.plotly_chart(fig_momentum, use_container_width=True)

        else:
            st.info("""
            **⚠️ No Precomputed Metrics Available**

            Precomputed metrics require:
            - Transaction data from 2015 onwards
            - Sufficient transaction volume per area

            Try adjusting your filters to include more recent data (2015+).
            """)
    else:
        st.info("""
        **📊 Precomputed Metrics Not Available**

        The enhanced L3 dataset with precomputed market metrics is not available.
        Ensure you have run the enhanced L3 pipeline: `uv run python scripts/create_l3_unified_dataset.py`
        """)

    # Help/info section
    with st.expander("💡 Tips & Instructions"):
        st.markdown("""
        ### How to Use This Page

        **1. Time Granularity**
        - Choose Monthly for detailed trends (more data points)
        - Choose Quarterly for balanced view
        - Choose Yearly for long-term patterns

        **2. Metrics**
        - Median Price: Track price changes over time
        - Transaction Volume: See market activity
        - Price Growth: View percentage changes

        **3. Comparisons**
        - Enable planning area comparison in sidebar
        - Compare by planning area, property type, or flat type
        - View distribution with box plots

        **4. Correlations**
        - Explore relationships between variables
        - Check if larger properties cost more per sqft
        - Identify patterns in the data

        **5. Filters**
        - Use sidebar to filter by property type and date range
        - Narrowing date range improves performance
        """)

    # Export option
    st.markdown("---")
    col1, col2 = st.columns([3, 1])

    with col2:
        if st.button("📥 Export Aggregated Data"):
            csv = agg_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"sg_housing_trends_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()
