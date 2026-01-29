"""
Market Overview - Enhanced dashboard with L3 features.

Provides high-level market statistics and trends using enhanced L3 dataset:
- Planning area analysis
- Rental yield metrics
- Amenity accessibility scores
- Market momentum indicators
- Precomputed growth metrics
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_loader import load_unified_data, get_unified_data_summary
from core.ui_components import (
    load_css,
    page_header,
    section_header,
    divider,
    display_metrics_row,
    info_box,
)

st.set_page_config(page_title="Market Overview", page_icon="", layout="wide")

# Load centralized design system
load_css()

# Page Header
page_header(
    "Market Overview",
    "Comprehensive market statistics with planning areas, rental yields, and market analysis",
)

# ============================================================================
# SIDEBAR FILTERS
# ============================================================================
st.sidebar.header("🔍 Filter Options")

with st.spinner("Loading market data..."):
    df = load_unified_data()

if df.empty:
    st.error("No data available. Please check your data files.")
    st.stop()

# ============================================================================
# SECTION 1: TIME ANALYSIS
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

# Apply era filter
if period_mode != "whole" and "era" in df.columns:
    df = df[df["era"] == period_mode].copy()

# 5-Year Period Filter
if "period_5yr" in df.columns:
    available_periods = sorted(df["period_5yr"].unique())
    selected_period = st.sidebar.selectbox(
        "5-Year Period",
        available_periods,
        index=len(available_periods) - 1 if available_periods else 0,
        help="Filter by 5-year period to view specific era",
    )

    # Apply period filter
    if selected_period:
        df = df[df["period_5yr"] == selected_period].copy()
else:
    selected_period = None

# Market Tier Filter
if "market_tier_period" in df.columns:
    market_tiers = st.sidebar.multiselect(
        "Market Tier (Period-Dependent)",
        ["Mass Market", "Mid-Tier", "Luxury"],
        default=["Mass Market", "Mid-Tier", "Luxury"],
        help="Filter by price tier",
    )

    # Apply tier filter
    if market_tiers:
        df = df[df["market_tier_period"].isin(market_tiers)].copy()
else:
    market_tiers = None

# ============================================================================
# SECTION 2: ADVANCED ANALYSIS
# ============================================================================
st.sidebar.subheader("**🔬 Advanced Analysis**")

# Cross-Era Comparison
compare_mode = st.sidebar.checkbox(
    "Cross-Era Comparison",
    value=False,
    help="Compare metrics between two different eras",
)

if compare_mode:
    comparison_era_1 = st.sidebar.selectbox(
        "Primary Era",
        ["pre_covid", "recent"],
        index=0,
        format_func=lambda x: {
            "pre_covid": "Pre-COVID (2015-2021)",
            "recent": "Recent (2022-2026)",
        }[x],
    )
    comparison_era_2 = st.sidebar.selectbox(
        "Comparison Era",
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

# Custom Date Range Override
use_custom_range = st.sidebar.checkbox(
    "Custom Date Range Override",
    value=False,
    help="Override era selection with a specific date range",
)

if use_custom_range and "transaction_date" in df.columns:
    date_min = df["transaction_date"].min().to_pydatetime()
    date_max = df["transaction_date"].max().to_pydatetime()
    custom_date_range = st.sidebar.slider(
        "Custom Date Range", date_min, date_max, (date_min, date_max)
    )
else:
    custom_date_range = None

# Show era info
if period_mode != "whole":
    st.info(f"📊 **{period_mode.replace('_', ' ').title()}** - {len(df):,} transactions")

# Show custom date range info
if use_custom_range and custom_date_range:
    st.info(
        f"📆 **Custom Range:** {custom_date_range[0].strftime('%Y-%m')} to {custom_date_range[1].strftime('%Y-%m')}"
    )

# ============================================================================
# PHASE 4: Cross-Era Comparison Section
# ============================================================================
if compare_mode and "era" in df.columns:
    era_1 = comparison_era_1 if comparison_era_1 else "pre_covid"
    era_2 = comparison_era_2 if comparison_era_2 else "recent"

    era_1_label = "Pre-COVID (2015-2021)" if era_1 == "pre_covid" else "Recent (2022-2026)"
    era_2_label = "Pre-COVID (2015-2021)" if era_2 == "pre_covid" else "Recent (2022-2026)"

    # Filter data for each era
    df_era_1 = df[df["era"] == era_1].copy() if "era" in df.columns else df
    df_era_2 = df[df["era"] == era_2].copy() if "era" in df.columns else df

    # Calculate metrics
    era_1_median = df_era_1["price"].median() if "price" in df_era_1.columns else 0
    era_2_median = df_era_2["price"].median() if "price" in df_era_2.columns else 0
    median_change = ((era_2_median - era_1_median) / era_1_median * 100) if era_1_median > 0 else 0

    era_1_count = len(df_era_1)
    era_2_count = len(df_era_2)
    count_change = ((era_2_count - era_1_count) / era_1_count * 100) if era_1_count > 0 else 0

    st.subheader("🔄 Cross-Era Comparison")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(f"Median Price ({era_1_label})", f"${era_1_median:,.0f}")
    with c2:
        st.metric(
            f"Median Price ({era_2_label})", f"${era_2_median:,.0f}", delta=f"{median_change:.1f}%"
        )
    with c3:
        st.metric(f"Transactions ({era_1_label})", f"{era_1_count:,}")
    with c4:
        st.metric(f"Transactions ({era_2_label})", f"{era_2_count:,}", delta=f"{count_change:.1f}%")

    st.info(
        f"💡 **Comparison:** {era_1_label} vs {era_2_label} | Price Change: {median_change:+.1f}%"
    )

    divider()

summary = get_unified_data_summary(df)

# ============================================================================
# TOP METRICS ROW
# ============================================================================
section_header("Market Snapshot ")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Transactions",
        f"{summary.get('total_records', 0):,}",
        help="Total number of geocoded transactions",
    )

with col2:
    if "price_stats" in summary:
        st.metric(
            "Median Price",
            f"${summary['price_stats']['median']:,.0f}",
            help="Median transaction price across all properties",
        )

with col3:
    planning_areas = df["planning_area"].nunique() if "planning_area" in df.columns else 0
    st.metric("Planning Areas", planning_areas, help="Number of URA planning areas covered")

with col4:
    date_range = summary.get("date_range", ("N/A", "N/A"))
    st.metric("Date Span", f"{date_range[0]} to {date_range[1]}", help="Transaction date range")

divider()

# ============================================================================
# PROPERTY TYPE DISTRIBUTION
# ============================================================================
col1, col2 = st.columns(2)

with col1:
    section_header("Property Type Distribution")

    if "property_type" in df.columns:
        prop_counts = df["property_type"].value_counts()

        # Display as metrics
        ptype_col1, ptype_col2, ptype_col3 = st.columns(3)
        with ptype_col1:
            if "HDB" in prop_counts:
                st.metric(
                    "HDB Transactions",
                    f"{prop_counts['HDB']:,}",
                    f"{prop_counts['HDB'] / len(df) * 100:.1f}%",
                )
        with ptype_col2:
            if "Condominium" in prop_counts:
                st.metric(
                    "Condo Transactions",
                    f"{prop_counts['Condominium']:,}",
                    f"{prop_counts['Condominium'] / len(df) * 100:.1f}%",
                )
        with ptype_col3:
            if "EC" in prop_counts:
                st.metric(
                    "EC Transactions",
                    f"{prop_counts['EC']:,}",
                    f"{prop_counts['EC'] / len(df) * 100:.1f}%",
                )

        # Bar chart using plotly for better visualization
        import plotly.express as px

        fig = px.bar(
            x=prop_counts.index,
            y=prop_counts.values,
            title="Transaction Count by Property Type",
            labels={"x": "Property Type", "y": "Number of Transactions"},
            text=prop_counts.values,
            color=prop_counts.index,
            color_discrete_sequence=["#3498DB", "#E74C3C", "#2ECC71"],
        )
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

        # Phase 2: Tier breakdown (NEW)
        if "market_tier_period" in df.columns:
            st.markdown("**Market Tier Distribution**")
            tier_dist = df["market_tier_period"].value_counts()

            for tier in ["Mass Market", "Mid-Tier", "Luxury"]:
                if tier in tier_dist.index:
                    pct = tier_dist[tier] / len(df) * 100
                    st.metric(tier, f"{tier_dist[tier]:,}", f"{pct:.1f}% of filtered data")

# ============================================================================
# RENTAL YIELD ANALYSIS (Enhanced - Phase 2)
# ============================================================================
with col2:
    section_header("Rental Yield Analysis")

    if "rental_yield_pct" in df.columns:
        rental_data = df[df["rental_yield_pct"].notna()].copy()

        if not rental_data.empty:
            ry_col1, ry_col2, ry_col3 = st.columns(3)

            with ry_col1:
                st.metric("Mean Yield", f"{rental_data['rental_yield_pct'].mean():.2f}%")

            with ry_col2:
                st.metric("Median Yield", f"{rental_data['rental_yield_pct'].median():.2f}%")

            with ry_col3:
                st.metric(
                    "Range",
                    f"{rental_data['rental_yield_pct'].min():.2f}% - {rental_data['rental_yield_pct'].max():.2f}%",
                )

            # Top 15 towns by rental yield (was Top 10)
            st.markdown("**Top 15 Towns by Rental Yield:**")
            top_rental = (
                rental_data.groupby("town")["rental_yield_pct"]
                .mean()
                .sort_values(ascending=False)
                .head(15)
            )
            st.dataframe(
                top_rental.to_frame("Yield %").style.format("{:.2f}"), use_container_width=True
            )

            # Phase 2: Top 15 by town/flat type combo (NEW)
            if "flat_type" in rental_data.columns:
                st.markdown("**Top 15 Town & Flat Type Combinations:**")
                rental_data["town_flat"] = rental_data["town"] + " - " + rental_data["flat_type"]
                top_combo = (
                    rental_data.groupby("town_flat")["rental_yield_pct"]
                    .mean()
                    .sort_values(ascending=False)
                    .head(15)
                )

                st.dataframe(
                    top_combo.to_frame("Yield %").style.format("{:.2f}"), use_container_width=True
                )
        else:
            st.info("No rental yield data available for current filters")
    else:
        st.info("Rental yield data not available in dataset")

# ============================================================================
# PLANNING AREA BREAKDOWN
# ============================================================================
divider()
section_header("Top 20 Planning Areas by Transaction Volume")

if "planning_area" in df.columns:
    pa_counts = df["planning_area"].value_counts().head(20)

    pa_col1, pa_col2, pa_col3 = st.columns(3)

    with pa_col1:
        st.metric(
            "Most Active Area", f"{pa_counts.index[0]}", f"{pa_counts.iloc[0]:,} transactions"
        )

    with pa_col2:
        st.metric(
            "Coverage",
            f"{df['planning_area'].nunique()} planning areas",
            "100% of geocoded properties",
        )

    with pa_col3:
        avg_per_area = pa_counts.mean()
        st.metric("Avg per Area", f"{avg_per_area:.0f} transactions")

    # Bar chart
    st.bar_chart(pa_counts)

    # Detailed table
    with st.expander("📋 View All Planning Areas"):
        pa_full = df["planning_area"].value_counts()
        pa_df = pd.DataFrame(
            {
                "Planning Area": pa_full.index,
                "Transactions": pa_full.values,
                "Percentage": (pa_full.values / len(df) * 100).round(1),
            }
        )
        st.dataframe(pa_df, use_container_width=True)

# ============================================================================
# AMENITY ACCESSIBILITY SCORES
# ============================================================================
divider()
section_header("Amenity Accessibility Analysis")

amenity_distance_cols = [col for col in df.columns if col.startswith("dist_to_nearest_")]
amenity_count_cols = [col for col in df.columns if "_within_500m" in col or "_within_1km" in col]

if amenity_distance_cols:
    amenity_col1, amenity_col2 = st.columns(2)

    with amenity_col1:
        st.markdown("**Average Distance to Nearest Amenities**")

        avg_distances = {}
        for col in amenity_distance_cols:
            amenity_name = col.replace("dist_to_nearest_", "").replace("_", " ").title()
            avg_dist = df[col].mean()
            if pd.notna(avg_dist):
                avg_distances[amenity_name] = f"{avg_dist:.0f}m"

        for amenity, distance in avg_distances.items():
            st.metric(amenity, distance)

    with amenity_col2:
        st.markdown("**Properties with Amenities Within 500m**")

        if amenity_count_cols:
            within_500m_cols = [col for col in amenity_count_cols if "_within_500m" in col]

            for col in within_500m_cols:
                amenity_name = col.replace("_within_500m", "").replace("_", " ").title()
                count = (df[col] >= 1).sum()
                pct = count / len(df) * 100
                st.metric(amenity, f"{pct:.1f}%", f"{count:,} properties")

# ============================================================================
# LEASE DECAY SUMMARY (Phase 2 - NEW)
# ============================================================================
divider()
section_header("Lease Decay Impact Summary (HDB)")

if "property_type" in df.columns:
    hdb_df = df[df["property_type"] == "HDB"].copy()

    if not hdb_df.empty and "remaining_lease_years" in hdb_df.columns:
        # Create lease bands
        hdb_df["lease_band"] = pd.cut(
            hdb_df["remaining_lease_years"],
            bins=[0, 60, 70, 80, 90, 100],
            labels=["<60 years", "60-70 years", "70-80 years", "80-90 years", "90+ years"],
        )

        # Calculate statistics by lease band
        lease_stats = (
            hdb_df.groupby("lease_band", observed=True)
            .agg({"price": ["count", "median", "mean"]})
            .round(0)
        )

        lease_stats.columns = ["Transactions", "Median Price", "Mean Price"]

        # Calculate discount to baseline (90+ years)
        if "90+ years" in lease_stats.index:
            baseline_median = lease_stats.loc["90+ years", "Median Price"]

            ld_col1, ld_col2, ld_col3 = st.columns(3)

            with ld_col1:
                if "<60 years" in lease_stats.index:
                    discount_60 = (
                        (baseline_median - lease_stats.loc["<60 years", "Median Price"])
                        / baseline_median
                        * 100
                    )
                    st.metric(
                        "<60 Year Lease Discount",
                        f"{discount_60:.1f}%",
                        help="Properties with <60 years lease vs 90+ years",
                    )

            with ld_col2:
                if "60-70 years" in lease_stats.index:
                    discount_70 = (
                        (baseline_median - lease_stats.loc["60-70 years", "Median Price"])
                        / baseline_median
                        * 100
                    )
                    st.metric(
                        "60-70 Year Lease Discount",
                        f"{discount_70:.1f}%",
                        help="Properties with 60-70 years lease vs 90+ years",
                    )

            with ld_col3:
                if "70-80 years" in lease_stats.index:
                    discount_80 = (
                        (baseline_median - lease_stats.loc["70-80 years", "Median Price"])
                        / baseline_median
                        * 100
                    )
                    st.metric(
                        "70-80 Year Lease Discount",
                        f"{discount_80:.1f}%",
                        help="Properties with 70-80 years lease vs 90+ years",
                    )

            # Display table
            st.markdown("**Lease Band Statistics:**")
            display_stats = lease_stats.copy()
            display_stats["Median Price"] = display_stats["Median Price"].apply(
                lambda x: f"${x:,.0f}"
            )
            display_stats["Mean Price"] = display_stats["Mean Price"].apply(lambda x: f"${x:,.0f}")

            st.dataframe(display_stats, use_container_width=True)

            # Investment insight
            with st.expander("💡 Investment Insights"):
                st.markdown(f"""
                **Key Findings:**
                - Properties with **<60 years** remaining lease sell at **{discount_60:.1f}%** discount vs 90+ years
                - Properties with **60-70 years** remaining lease sell at **{discount_70:.1f}%** discount vs 90+ years
                - Each 10-year reduction in lease costs approximately **{discount_70:.1f}%** in price

                **Recommendation:**
                - Short-lease properties (<60 years) offer significant discounts
                - Suitable for buyers not planning long-term holds (10+ years)
                - Consider lease decay impact when evaluating investment returns
                """)
        else:
            st.info(
                "Lease decay analysis requires properties with 90+ years remaining lease as baseline"
            )
    else:
        st.info("Lease decay analysis requires HDB properties with remaining lease data")
else:
    st.info("Lease decay analysis is available for HDB properties only")

# ============================================================================
# MARKET METRICS (Precomputed)
# ============================================================================
divider()
section_header("Market Growth & Momentum")

if "mom_change_pct" in df.columns:
    metrics_data = df[df["mom_change_pct"].notna()].copy()

    if not metrics_data.empty:
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)

        with metrics_col1:
            avg_mom = metrics_data["mom_change_pct"].mean()
            st.metric("Avg Monthly Growth", f"{avg_mom:.2f}%")

        with metrics_col2:
            avg_yoy = (
                metrics_data["yoy_change_pct"].mean()
                if "yoy_change_pct" in metrics_data.columns
                else 0
            )
            st.metric("Avg Yearly Growth", f"{avg_yoy:.2f}%")

        with metrics_col3:
            momentum_bullish = (
                (metrics_data["momentum_signal"] == "Strong Acceleration").sum()
                if "momentum_signal" in metrics_data.columns
                else 0
            )
            momentum_pct = momentum_bullish / len(metrics_data) * 100
            st.metric("Bullish Signal Rate", f"{momentum_pct:.1f}%")

        # Recent market trends
        st.markdown("**Recent Market Trends (Last 12 Months)**")

        if "transaction_date" in metrics_data.columns:
            recent_cutoff = metrics_data["transaction_date"].max() - pd.DateOffset(months=12)
            recent_metrics = metrics_data[metrics_data["transaction_date"] >= recent_cutoff]

            if not recent_metrics.empty:
                trend_col1, trend_col2 = st.columns(2)

                with trend_col1:
                    recent_mom = recent_metrics["mom_change_pct"].mean()
                    st.metric("Recent Monthly Growth", f"{recent_mom:.2f}%", delta_color="normal")

                with trend_col2:
                    recent_vol = (
                        recent_metrics["transaction_count"].mean()
                        if "transaction_count" in recent_metrics.columns
                        else 0
                    )
                    st.metric("Avg Monthly Volume", f"{recent_vol:.0f}", delta_color="normal")
    else:
        st.info("Precomputed market metrics not available (requires data from 2015 onwards)")
else:
    st.info("Market metrics not available. Ensure L3 metrics are computed.")

# ============================================================================
# INSIGHTS & RECOMMENDATIONS
# ============================================================================
divider()
section_header("Key Insights")

insights = []

# Phase 2: Period indicator
if selected_period:
    insights.append(f"Period: {selected_period}")

# Planning area concentration
if "planning_area" in df.columns:
    top_pa = df["planning_area"].value_counts().index[0]
    top_pa_pct = df["planning_area"].value_counts().iloc[0] / len(df) * 100
    insights.append(
        f"{top_pa} has the highest transaction volume at {top_pa_pct:.1f}% of all transactions"
    )

# Rental yield insight
if "rental_yield_pct" in df.columns:
    rental_data = df[df["rental_yield_pct"].notna()]
    if not rental_data.empty:
        high_yield_pa = rental_data.groupby("planning_area")["rental_yield_pct"].mean().idxmax()
        high_yield_val = rental_data.groupby("planning_area")["rental_yield_pct"].mean().max()
        insights.append(f"{high_yield_pa} offers the highest rental yield at {high_yield_val:.2f}%")

# Tier distribution insight
if "market_tier_period" in df.columns:
    tier_dist = df["market_tier_period"].value_counts(normalize=True) * 100
    dominant_tier = tier_dist.idxmax()
    insights.append(
        f"{dominant_tier} properties dominate at {tier_dist.max():.1f}% of filtered data"
    )

# Amenity insight
if amenity_distance_cols:
    best_mrt = df[df["dist_to_nearest_mrt"].notna()]["dist_to_nearest_mrt"].min()
    if best_mrt < 500:
        insights.append(
            f"{(df['dist_to_nearest_mrt'] <= 500).sum():,} properties are within 500m of an MRT station"
        )

# Market momentum
if "mom_change_pct" in df.columns:
    metrics_data = df[df["mom_change_pct"].notna()]
    if not metrics_data.empty:
        latest_growth = metrics_data.sort_values("transaction_date")["mom_change_pct"].iloc[-1]
        if latest_growth > 0:
            insights.append(f"Latest month shows positive growth of {latest_growth:.2f}%")
        else:
            insights.append(f"Latest month shows negative growth of {latest_growth:.2f}%")

# Display insights
for insight in insights:
    st.markdown(f"- {insight}")

# ============================================================================
# DATA QUALITY NOTES
# ============================================================================
st.markdown("---")
st.info(f"""
**Dataset Notes:**
- This dashboard uses the enhanced L3 unified dataset with 59 features
- Planning area coverage: 100% of geocoded properties
- Rental yield coverage: 15.3% (HDB only, 2021-2025)
- Precomputed metrics: 26.9% (2015-2026 data)
- Amenity features: 24 columns (6 distance + 18 count features)

**Current View:**
- {f"Period: {selected_period}" if selected_period else "Period: All data"}
- {f"Tiers: {', '.join(market_tiers)}" if market_tiers else "Tiers: All tiers"}
- Records: {len(df):,} transactions
""")
