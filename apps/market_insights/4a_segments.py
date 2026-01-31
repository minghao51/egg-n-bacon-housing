"""Market Segments Analysis - Enhanced Visualization

This app provides in-depth market segmentation analysis:
- Tier-based classification (Mass Market, Mid Tier, Premium, Luxury)
- Radar charts comparing segments across multiple dimensions
- Bubble scatter plots for segment comparison
- Investment strategies by segment
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.core.config import Config
from scripts.core.ui_components import (
    custom_warning,
    info_box,
    load_css,
    page_header,
    section_header,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Market Segments", page_icon="", layout="wide")

load_css()


@st.cache_data
def load_cluster_profiles():
    """Load market segmentation cluster profiles."""
    path = Config.DATA_DIR / "analysis" / "market_segmentation_2.0" / "cluster_profiles.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_investment_strategies():
    """Load investment strategies per segment."""
    path = Config.DATA_DIR / "analysis" / "market_segmentation_2.0" / "investment_strategies.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def get_segment_tier(segment_name: str) -> str:
    """Map segment to tier classification."""
    tier_mapping = {
        "Large Size Stable": "Mid Tier",
        "High Growth Recent": "Premium",
        "Speculator Hotspots": "Premium",
        "Declining Areas": "Mass Market",
        "Mid-Tier Value": "Mid Tier",
        "Premium New Units": "Luxury",
    }
    return tier_mapping.get(str(segment_name), "Unknown")


def get_segment_color(segment_name: str) -> str:
    """Get color for segment visualization."""
    color_mapping = {
        "Large Size Stable": "#3498db",
        "High Growth Recent": "#2ecc71",
        "Speculator Hotspots": "#9b59b6",
        "Declining Areas": "#e74c3c",
        "Mid-Tier Value": "#f39c12",
        "Premium New Units": "#1abc9c",
    }
    return color_mapping.get(str(segment_name), "#95a5a6")


def main():
    page_header(
        "Market Segmentation Analysis",
        "K-means behavioral clustering to identify distinct market segments",
    )

    # ============================================================================
    # SIDEBAR FILTERS
    # ============================================================================
    st.sidebar.header("🔍 Filter Options")

    # Check if unified data has era column
    from scripts.core.data_loader import load_unified_data

    df = load_unified_data()

    # ============================================================================
    # SECTION 1: TIME ANALYSIS
    # ============================================================================
    st.sidebar.subheader("**📅 Time Period Analysis**")

    if "era" in df.columns:
        period_mode = st.sidebar.radio(
            "Analysis Period",
            options=["whole", "pre_covid", "recent"],
            format_func=lambda x: {
                "whole": "All Historical Data",
                "pre_covid": "Pre-COVID (2015-2021)",
                "recent": "Recent (2022-2026)",
            }[x],
            index=0,
        )

        # Show era stats
        era_counts = df["era"].value_counts()
        if period_mode != "whole":
            count = era_counts.get(period_mode, 0)
            st.sidebar.info(
                f"📊 **{period_mode.replace('_', ' ').title()}**: {count:,} transactions"
            )
    else:
        period_mode = "whole"
        st.sidebar.info("Era data not available. Run create_period_segmentation.py")

    # ============================================================================
    # SECTION 2: ADVANCED ANALYSIS
    # ============================================================================
    st.sidebar.subheader("**🔬 Advanced Analysis**")

    # Cross-Era Comparison
    compare_mode = st.sidebar.checkbox(
        "Cross-Era Comparison",
        value=False,
        help="Compare segments between two eras",
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

    cluster_profiles = load_cluster_profiles()
    investment_strategies = load_investment_strategies()

    if cluster_profiles.empty:
        custom_warning(
            "Market segmentation results not available. Run scripts/quick_cluster_profiles.py first."
        )
        return

    section_header("Segment Overview")

    tier_mapping = {str(s): get_segment_tier(s) for s in cluster_profiles["segment_name"]}
    cluster_profiles["tier"] = cluster_profiles["segment_name"].map(tier_mapping)

    tier_colors = {
        "Mass Market": "#e74c3c",
        "Mid Tier": "#3498db",
        "Premium": "#f39c12",
        "Luxury": "#9b59b6",
    }
    cluster_profiles["color"] = cluster_profiles["tier"].map(tier_colors)

    tier_counts = cluster_profiles.groupby("tier")["cluster_size"].sum()
    total = tier_counts.sum()
    tier_pcts = (tier_counts / total * 100).round(1)

    tier_data = pd.DataFrame(
        {
            "Tier": tier_pcts.index,
            "Percentage": tier_pcts.values,
            "Count": [tier_counts[t] for t in tier_pcts.index],
        }
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        fig_tier = px.pie(
            tier_data,
            values="Percentage",
            names="Tier",
            title="Market Distribution by Tier",
            color="Tier",
            color_discrete_map=tier_colors,
            hole=0.4,
        )
        fig_tier.update_traces(
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>Percentage: %{percent}<br>Count: %{customdata}",
            customdata=tier_data["Count"],
        )
        st.plotly_chart(fig_tier, use_container_width=True)

    with col2:
        st.markdown("""
        ### Tier Classification

        **Mass Market** (Declining Areas)
        - Lower price PSF, negative growth
        - Focus on affordability

        **Mid Tier** (Large Size Stable, Mid-Tier Value)
        - Balanced price and yield
        - Most of the market volume (38%)
        - Stable growth & value opportunities

        **Premium** (High Growth Recent, Speculator Hotspots)
        - Higher appreciation potential
        - Growth-oriented segments (24-84% growth)
        - Active trading & speculation

        **Luxury** (Premium New Units)
        - Highest price PSF ($826)
        - Newest leases (89 years remaining)
        - Premium pricing & quality
        """)

    st.markdown("---")
    section_header("Segment Profiles")

    for _, row in cluster_profiles.iterrows():
        tier = str(row.get("tier", "Unknown"))
        tier_color = tier_colors.get(tier, "#95a5a6")
        segment_name_val = str(row["segment_name"])
        segment_color = get_segment_color(segment_name_val)

        # Determine key characteristics tags
        characteristics = []
        growth = row.get("yoy_change_pct_mean", 0)
        yield_val = row.get("rental_yield_pct_mean", 0)
        area = row.get("floor_area_sqft_mean", 0)
        lease = row.get("remaining_lease_months_mean", 0)
        price = row.get("price_psf_mean", 0)

        if growth > 20:
            characteristics.append("📈 High Growth")
        elif growth < 0:
            characteristics.append("📉 Declining")
        elif growth > 10:
            characteristics.append("📊 Moderate Growth")

        if yield_val > 6:
            characteristics.append("💰 High Yield")
        elif yield_val < 5:
            characteristics.append("💵 Low Yield")

        if area > 1200:
            characteristics.append("🏠 Large Units")
        elif area < 800:
            characteristics.append("🏘️ Compact Units")

        if lease > 900:
            characteristics.append("🆕 New Lease")
        elif lease < 700:
            characteristics.append("⏰ Aging Lease")

        if price > 700:
            characteristics.append("💎 Premium")
        elif price < 500:
            characteristics.append("💸 Affordable")

        with st.expander(
            f"**{segment_name_val}** - {int(row['cluster_size']):,} properties ({row['cluster_percentage']:.1f}%)",
            expanded=True,
        ):
            col_top, col_mid = st.columns([3, 1])

            with col_top:
                st.markdown(
                    f"""
                <div style="
                    border-left: 5px solid {segment_color};
                    background-color: rgba(255,255,255,0.5);
                    padding: 1rem;
                    margin: 0.5rem 0;
                    border-radius: 0 5px 5px 0;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <div>
                            <span style="font-size: 1.2rem; font-weight: bold; color: {segment_color};">{segment_name_val}</span>
                            <span style="
                                background-color: {tier_color};
                                color: white;
                                padding: 0.2rem 0.6rem;
                                border-radius: 12px;
                                font-size: 0.75rem;
                                margin-left: 0.5rem;
                            ">{tier}</span>
                        </div>
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem;">
                        {''.join([f'<span style="background-color: #f0f0f0; padding: 0.2rem 0.5rem; border-radius: 8px; font-size: 0.8rem;">{tag}</span>' for tag in characteristics])}
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with col_mid:
                st.metric("Market Share", f"{row['cluster_percentage']:.1f}%")

            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                price_min = row.get("price_psf_min", 0)
                price_max = row.get("price_psf_max", 0)
                price_label = f"${price_min:,.0f}-${price_max:,.0f}" if (price_min and price_max) else "N/A"
                st.metric("Price Range (PSF)", price_label)
            with col_b:
                yield_val = row.get("rental_yield_pct_mean", 0)
                st.metric("Avg Yield", f"{yield_val:.2f}%" if yield_val else "N/A")
            with col_c:
                growth = row.get("yoy_change_pct_mean", 0)
                delta_color = "normal" if growth >= 0 else "inverse"
                st.metric("Avg Growth", f"{growth:.1f}%", delta=f"{growth:+.1f}%", delta_color=delta_color)
            with col_d:
                area = row.get("floor_area_sqft_mean", 0)
                st.metric("Avg Floor Area", f"{area:,.0f} sqft" if area else "N/A")

            # Additional details
            col_e, col_f, col_g = st.columns(3)
            with col_e:
                lease = row.get("remaining_lease_months_mean", 0)
                st.metric("Remaining Lease", f"{lease:,.0f} mo" if lease else "N/A")
            with col_f:
                trans_vol = row.get("transaction_count_mean", 0)
                st.metric("Avg Transactions", f"{trans_vol:,.0f}" if trans_vol else "N/A")
            with col_g:
                price_std = row.get("price_psf_std", 0)
                st.metric("Price Std Dev", f"${price_std:,.0f}" if price_std else "N/A")

    st.markdown("---")
    section_header("Cluster Summary Table")

    # Create comprehensive summary table
    summary_data = []
    for _, row in cluster_profiles.iterrows():
        segment = str(row["segment_name"])
        tier = str(row.get("tier", "Unknown"))

        # Format key metrics
        price_range = f"${row.get('price_psf_min', 0):,.0f}-${row.get('price_psf_max', 0):,.0f}"
        yield_val = f"{row.get('rental_yield_pct_mean', 0):.2f}%"
        growth = f"{row.get('yoy_change_pct_mean', 0):.1f}%"
        area = f"{row.get('floor_area_sqft_mean', 0):,.0f} sqft"
        lease = f"{row.get('remaining_lease_months_mean', 0):,.0f} mo"
        trans_count = f"{row.get('transaction_count_mean', 0):,.0f}"
        market_share = f"{row.get('cluster_percentage', 0):.1f}%"

        summary_data.append({
            "Segment": segment,
            "Tier": tier,
            "Market Share": market_share,
            "Price Range (PSF)": price_range,
            "Avg Yield": yield_val,
            "Avg Growth": growth,
            "Avg Area": area,
            "Remaining Lease": lease,
            "Avg Transactions": trans_count,
        })

    summary_df = pd.DataFrame(summary_data)

    # Display with styling
    st.dataframe(
        summary_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Segment": st.column_config.TextColumn("Segment", width="medium"),
            "Tier": st.column_config.TextColumn("Tier", width="small"),
            "Market Share": st.column_config.TextColumn("Market Share", width="small"),
            "Price Range (PSF)": st.column_config.TextColumn("Price Range (PSF)", width="medium"),
            "Avg Yield": st.column_config.TextColumn("Avg Yield", width="small"),
            "Avg Growth": st.column_config.TextColumn("Avg Growth", width="small"),
            "Avg Area": st.column_config.TextColumn("Avg Area", width="medium"),
            "Remaining Lease": st.column_config.TextColumn("Remaining Lease", width="medium"),
            "Avg Transactions": st.column_config.TextColumn("Avg Transactions", width="medium"),
        }
    )

    st.markdown("---")
    section_header("Segment Comparison")

    col_left, col_right = st.columns(2)

    with col_left:
        metrics = ["price_psf_mean", "rental_yield_pct_mean", "yoy_change_pct_mean"]
        metric_labels = {
            "price_psf_mean": "Price PSF ($)",
            "rental_yield_pct_mean": "Rental Yield (%)",
            "yoy_change_pct_mean": "YoY Growth (%)",
        }

        available_metrics = [m for m in metrics if m in cluster_profiles.columns]
        if available_metrics:

            def format_metric(x):
                return metric_labels.get(x, str(x))

            x_metric = st.selectbox(
                "X-axis Metric", available_metrics, index=0, format_func=format_metric
            )
            y_metric = st.selectbox(
                "Y-axis Metric",
                available_metrics,
                index=1 if len(available_metrics) > 1 else 0,
                format_func=format_metric,
            )

            if x_metric and y_metric and x_metric != y_metric:
                # Prepare custom data for rich hover text
                custom_data_cols = [
                    "segment_name",
                    "cluster_size",
                    "cluster_percentage",
                    "price_psf_mean",
                    "rental_yield_pct_mean",
                    "yoy_change_pct_mean",
                    "floor_area_sqft_mean",
                    "remaining_lease_months_mean",
                    "tier",
                ]
                available_custom_data = [c for c in custom_data_cols if c in cluster_profiles.columns]

                fig_scatter = px.scatter(
                    cluster_profiles,
                    x=x_metric,
                    y=y_metric,
                    size="cluster_size",
                    color="segment_name",
                    color_discrete_map={
                        str(s): get_segment_color(str(s)) for s in cluster_profiles["segment_name"]
                    },
                    hover_name="segment_name",
                    text="segment_name",
                    title="Segment Comparison (Bubble Size = Transaction Count)",
                    custom_data=available_custom_data,
                )

                # Custom hover template with rich cluster information
                fig_scatter.update_traces(
                    textposition="top center",
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "<i>%{customdata[8]}</i><br>"
                        "─<br>"
                        "Market Share: %{customdata[2]:.1f}%<br>"
                        "Properties: %{customdata[1]:,.0f}<br>"
                        "Price PSF: $%{customdata[3]:,.0f}<br>"
                        "Yield: %{customdata[4]:.2f}%<br>"
                        "Growth: %{customdata[5]:.1f}%<br>"
                        "Area: %{customdata[6]:,.0f} sqft<br>"
                        "Lease: %{customdata[7]:,.0f} mo<br>"
                        "<extra></extra>"
                    ) if len(available_custom_data) >= 9 else None
                )
                fig_scatter.update_layout(template="plotly_white", height=500)
                st.plotly_chart(fig_scatter, use_container_width=True)

    with col_right:
        dimensions = [
            "price_psf_mean",
            "rental_yield_pct_mean",
            "yoy_change_pct_mean",
            "floor_area_sqft_mean",
            "transaction_count_mean",
        ]
        dim_labels = {
            "price_psf_mean": "Price PSF",
            "rental_yield_pct_mean": "Rental Yield",
            "yoy_change_pct_mean": "YoY Growth",
            "floor_area_sqft_mean": "Floor Area",
            "transaction_count_mean": "Transaction Volume",
        }

        radar_metrics = [m for m in dimensions if m in cluster_profiles.columns]
        if len(radar_metrics) >= 3:
            dim_labels_safe = {d: dim_labels.get(d, str(d)) for d in dimensions}

            def format_dim(x):
                return dim_labels_safe.get(x, str(x))

            selected_dims = st.multiselect(
                "Select dimensions for radar chart",
                radar_metrics,
                default=radar_metrics[:4],
                format_func=format_dim,
            )

            if selected_dims:
                categories = [dim_labels.get(d, d) for d in selected_dims]
                fig_radar = go.Figure()

                normalized_data = cluster_profiles.copy()
                for dim in selected_dims:
                    max_val = normalized_data[dim].max()
                    if max_val > 0:
                        normalized_data[dim] = normalized_data[dim] / max_val * 100

                for _, row in normalized_data.iterrows():
                    segment_name_val = str(row["segment_name"])
                    values = [row[d] for d in selected_dims]
                    values += values[:1]
                    angles = [
                        n / len(selected_dims) * 2 * 3.14159 for n in range(len(selected_dims))
                    ]
                    angles += angles[:1]

                    fig_radar.add_trace(
                        go.Scatterpolar(
                            r=values,
                            theta=categories,
                            fill="toself",
                            fillcolor=f"rgba({int(get_segment_color(segment_name_val)[1:3], 16)}, {int(get_segment_color(segment_name_val)[3:5], 16)}, {int(get_segment_color(segment_name_val)[5:7], 16)}, 0.33)",
                            line=dict(color=get_segment_color(segment_name_val), width=2),
                            name=segment_name_val,
                        )
                    )

                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
                    title="Segment Radar Chart (Normalized to 0-100)",
                    template="plotly_white",
                    height=500,
                )
                st.plotly_chart(fig_radar, use_container_width=True)

    st.markdown("---")
    section_header("Investment Strategies by Segment")

    if not investment_strategies.empty:
        col1, col2 = st.columns(2)

        for idx, (_, row) in enumerate(investment_strategies.iterrows()):
            segment = str(row["segment_name"])
            strategy = row["strategy"]
            avg_yield = row["avg_yield_pct"]
            avg_growth = row["avg_growth_pct"]
            avg_price = row["avg_price_psf"]

            tier = get_segment_tier(segment)
            tier_color = tier_colors.get(tier, "#95a5a6")
            segment_color = get_segment_color(segment)

            # Determine strategy type and color
            strategy_type = "BALANCED"
            strategy_color = "#e3f2fd"
            risk_level = "Medium"
            risk_color = "#ff9800"

            if "HOLD & GROW" in strategy:
                strategy_type = "HOLD & GROW"
                strategy_color = "#d4edda"
                risk_level = "Low-Medium"
                risk_color = "#4caf50"
            elif "YIELD PLAY" in strategy:
                strategy_type = "YIELD"
                strategy_color = "#fff3cd"
                risk_level = "Low"
                risk_color = "#8bc34a"
            elif "GROWTH PLAY" in strategy:
                strategy_type = "GROWTH"
                strategy_color = "#f8d7da"
                risk_level = "High"
                risk_color = "#f44336"
            elif "VALUE" in strategy:
                strategy_type = "VALUE"
                strategy_color = "#d1ecf1"
                risk_level = "Low"
                risk_color = "#8bc34a"
            elif "LUXURY" in strategy:
                strategy_type = "LUXURY"
                strategy_color = "#f3e5f5"
                risk_level = "Medium"
                risk_color = "#9c27b0"

            # Calculate risk score
            if avg_growth > 50 or avg_yield < 4:
                risk_level = "Very High"
                risk_color = "#d32f2f"
            elif avg_growth > 20 or avg_yield < 5:
                risk_level = "High"
                risk_color = "#f44336"
            elif avg_growth > 10:
                risk_level = "Medium-High"
                risk_color = "#ff5722"

            with col1 if idx % 2 == 0 else col2:
                st.markdown(
                    f"""
                <div style="background-color: {strategy_color}; padding: 1.2rem; margin: 0.5rem 0; border-radius: 0.5rem; border-left: 5px solid {segment_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
                        <strong style="font-size: 1.15rem; color: {segment_color};">{segment}</strong>
                        <div style="display: flex; gap: 0.5rem; align-items: center;">
                            <span style="background-color: {tier_color}; color: white; padding: 0.25rem 0.6rem; border-radius: 10px; font-size: 0.7rem;">{tier}</span>
                            <span style="background-color: {risk_color}; color: white; padding: 0.25rem 0.6rem; border-radius: 10px; font-size: 0.7rem;">{risk_level} Risk</span>
                        </div>
                    </div>
                    <div style="font-size: 0.95rem; margin-bottom: 0.8rem; color: #333; line-height: 1.4;">{strategy}</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 1rem; font-size: 0.85rem; color: #555;">
                        <span style="display: flex; align-items: center; gap: 0.3rem;">
                            <span style="color: #4caf50;">💰</span>
                            <b>Yield:</b> {avg_yield:.2f}%
                        </span>
                        <span style="display: flex; align-items: center; gap: 0.3rem;">
                            <span style="color: #2196f3;">📈</span>
                            <b>Growth:</b> {avg_growth:+.1f}%
                        </span>
                        <span style="display: flex; align-items: center; gap: 0.3rem;">
                            <span style="color: #ff9800;">💎</span>
                            <b>Price PSF:</b> ${avg_price:,.0f}
                        </span>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            "Investment strategies not available. Run scripts/quick_cluster_profiles.py first."
        )

    # ============================================================================
    # PHASE 4: Cross-Era Comparison Section
    # ============================================================================
    if compare_mode and "era" in df.columns:
        st.markdown("---")
        st.subheader("🔄 Cross-Era Segment Comparison")

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

        # Property type distribution comparison
        st.markdown("#### Property Type Distribution by Era")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown(f"**{era_1_label}**")
            if "property_type" in df_era_1.columns:
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
            if "property_type" in df_era_2.columns:
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

    st.markdown("---")
    section_header("Methodology")

    info_box("""
    <strong>K-means Clustering:</strong> Groups properties based on behavioral metrics including
    price PSF, floor area, remaining lease, rental yield, appreciation, and transaction volume.
    Optimal number of clusters determined using silhouette analysis.
    """)

    info_box("""
    <strong>Applications:</strong> Identify natural market segments for targeted investment strategies.
    Compare segments on yield vs growth trade-offs. Discover emerging market behaviors.
    """)


if __name__ == "__main__":
    main()
