"""Tier Analysis - Market Tier Evolution

This app provides analysis of market tiers and their evolution over time:
- Tier threshold changes across different property types
- Current tier classifications and definitions
- Price thresholds for mass market, mid-tier, and luxury segments
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Config
from core.ui_components import (
    custom_warning,
    info_box,
    load_css,
    page_header,
    section_header,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Tier Analysis", page_icon="", layout="wide")

load_css()


@st.cache_data
def load_tier_thresholds_evolution():
    """Load tier threshold evolution data."""
    path = (
        Config.DATA_DIR
        / "analysis"
        / "market_segmentation_period"
        / "tier_thresholds_evolution.csv"
    )
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def main():
    page_header(
        "Market Tier Analysis",
        "Understand how market tiers (Mass Market, Mid Tier, Luxury) have evolved over time",
    )

    # ============================================================================
    # ERA SELECTOR (Phase 3-4)
    # ============================================================================
    st.sidebar.subheader("📅 Period Mode")

    from core.data_loader import load_unified_data

    df = load_unified_data()

    if "era" in df.columns:
        period_mode = st.sidebar.radio(
            "Select Analysis Period",
            options=["whole", "pre_covid", "recent"],
            format_func=lambda x: {
                "whole": "Whole Period (All Data)",
                "pre_covid": "Pre-COVID (2015-2021)",
                "recent": "Recent (2022-2026)",
            }[x],
            index=0,
        )

        era_counts = df["era"].value_counts()
        if period_mode != "whole":
            count = era_counts.get(period_mode, 0)
            st.sidebar.info(
                f"📊 **{period_mode.replace('_', ' ').title()}**: {count:,} transactions"
            )
    else:
        period_mode = "whole"
        st.sidebar.info("Era data not available. Run create_period_segmentation.py")

    # Phase 4: Cross-Era Comparison
    st.sidebar.subheader("🔄 Era Comparison")
    compare_mode = st.sidebar.checkbox(
        "Enable Cross-Era Comparison", value=False, help="Compare tier thresholds between two eras"
    )

    if compare_mode:
        comparison_era_1 = st.sidebar.selectbox(
            "First Era",
            ["pre_covid", "recent"],
            index=0,
            format_func=lambda x: {
                "pre_covid": "Pre-COVID (2015-2021)",
                "recent": "Recent (2022-2026)",
            }[x],
        )
        comparison_era_2 = st.sidebar.selectbox(
            "Second Era",
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

    tier_thresholds = load_tier_thresholds_evolution()

    if tier_thresholds.empty:
        custom_warning(
            "Tier threshold data not available. Run scripts/create_period_segmentation.py first."
        )
        return

    section_header("Tier Threshold Evolution Over Time")

    st.info("""
    Market tiers are defined by price thresholds that separate segments. These thresholds have evolved significantly
    due to inflation, market appreciation, and changing buyer demographics.
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### HDB Tier Thresholds")
        hdb_tiers = tier_thresholds[tier_thresholds["property_type"] == "HDB"].copy()

        if not hdb_tiers.empty:
            hdb_tiers["period"] = hdb_tiers["period"].astype(str)

            fig_hdb = px.bar(
                hdb_tiers,
                x="period",
                y=["mass_market_max", "mid_tier_max"],
                title="HDB Tier Price Thresholds Over Time",
                labels={"value": "Price Threshold ($)", "period": "Period", "variable": "Tier"},
                color_discrete_map={"mass_market_max": "#3498db", "mid_tier_max": "#f39c12"},
            )
            fig_hdb.update_layout(
                xaxis_title="Time Period",
                yaxis_title="Price Threshold (SGD)",
                legend_title="Tier",
                template="plotly_white",
                height=400,
            )
            st.plotly_chart(fig_hdb, use_container_width=True)
        else:
            st.info("No HDB tier data available for selected periods.")

    with col2:
        st.markdown("### Condo/EC Tier Thresholds")
        condo_tiers = tier_thresholds[
            tier_thresholds["property_type"].isin(["Condominium", "EC"])
        ].copy()

        if not condo_tiers.empty:
            condo_tiers["period"] = condo_tiers["period"].astype(str)

            fig_condo = px.bar(
                condo_tiers,
                x="period",
                y=["mass_market_max", "mid_tier_max", "luxury_min"],
                title="Condo/EC Tier Price Thresholds Over Time",
                labels={"value": "Price Threshold ($)", "period": "Period", "variable": "Tier"},
                color_discrete_map={
                    "mass_market_max": "#3498db",
                    "mid_tier_max": "#f39c12",
                    "luxury_min": "#9b59b6",
                },
            )
            fig_condo.update_layout(
                xaxis_title="Time Period",
                yaxis_title="Price Threshold (SGD)",
                legend_title="Tier",
                template="plotly_white",
                height=400,
            )
            st.plotly_chart(fig_condo, use_container_width=True)
        else:
            st.info("No Condo/EC tier data available for selected periods.")

    st.markdown("---")
    section_header("Current Tier Thresholds (2020-2024)")

    current_tiers = tier_thresholds[tier_thresholds["period"] == "2020-2024"].copy()

    if not current_tiers.empty:
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.markdown("### HDB")
            hdb_current = current_tiers[current_tiers["property_type"] == "HDB"]
            if not hdb_current.empty:
                row = hdb_current.iloc[0]
                st.metric("Mass Market Max", f"${row['mass_market_max']:,.0f}")
                st.metric("Mid Tier Max", f"${row['mid_tier_max']:,.0f}")
                st.metric("Max Recorded", f"${row['max_price']:,.0f}")
                if "transaction_count" in row:
                    st.metric("Transactions", f"{int(row['transaction_count']):,}")
            else:
                st.info("No recent HDB data")

        with col_b:
            st.markdown("### Condominium")
            condo_current = current_tiers[current_tiers["property_type"] == "Condominium"]
            if not condo_current.empty:
                row = condo_current.iloc[0]
                st.metric("Mass Market Max", f"${row['mass_market_max']:,.0f}")
                st.metric("Mid Tier Max", f"${row['mid_tier_max']:,.0f}")
                st.metric("Max Recorded", f"${row['max_price']:,.0f}")
                if "transaction_count" in row:
                    st.metric("Transactions", f"{int(row['transaction_count']):,}")
            else:
                st.info("No recent Condo data")

        with col_c:
            st.markdown("### Executive Condo")
            ec_current = current_tiers[current_tiers["property_type"] == "EC"]
            if not ec_current.empty:
                row = ec_current.iloc[0]
                st.metric("Mass Market Max", f"${row['mass_market_max']:,.0f}")
                st.metric("Mid Tier Max", f"${row['mid_tier_max']:,.0f}")
                st.metric("Max Recorded", f"${row['max_price']:,.0f}")
                if "transaction_count" in row:
                    st.metric("Transactions", f"{int(row['transaction_count']):,}")
            else:
                st.info("No recent EC data")
    else:
        st.info("No current tier data available for 2020-2024 period.")

    st.markdown("---")
    section_header("Tier Definitions")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### Understanding Market Tiers

        **Mass Market** (Entry-Level)
        - First-time buyers, affordable housing
        - Lower price points, government subsidies
        - High transaction volume

        **Mid Tier** (Mainstream)
        - Upgraders, mature markets
        - Balanced price and amenity access
        - Largest segment by volume

        **Premium/Luxury** (High-End)
        - Affluent buyers, investment focus
        - Prime locations, larger units
        - Lower volume, higher price variance
        """)

    with col2:
        st.markdown("""
        ### Tier Classification Criteria

        **Price-Based Thresholds:**
        - Mass Market: Below tier-specific threshold
        - Mid Tier: Between mass market and luxury
        - Luxury: Above tier-specific threshold

        **Key Factors:**
        - Property type (HDB vs Condo vs EC)
        - Location (CCR vs RCR vs OCR)
        - Floor area and storey
        - Remaining lease

        **Note:** Thresholds vary by property type
        and have evolved significantly over time.
        """)

    st.markdown("---")
    section_header("Historical Tier Evolution")

    st.dataframe(
        tier_thresholds.rename(
            columns={
                "property_type": "Property Type",
                "period": "Period",
                "mass_market_max": "Mass Market Max",
                "mid_tier_max": "Mid Tier Max",
                "luxury_min": "Luxury Min",
                "max_price": "Max Price",
                "transaction_count": "Transactions",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # ============================================================================
    # PHASE 4: Cross-Era Tier Comparison
    # ============================================================================
    if compare_mode and "era" in df.columns:
        st.markdown("---")
        st.subheader("🔄 Cross-Era Tier Comparison")

        era_1 = comparison_era_1 if comparison_era_1 else "pre_covid"
        era_2 = comparison_era_2 if comparison_era_2 else "recent"

        era_1_label = "Pre-COVID (2015-2021)" if era_1 == "pre_covid" else "Recent (2022-2026)"
        era_2_label = "Pre-COVID (2015-2021)" if era_2 == "pre_covid" else "Recent (2022-2026)"

        df_era_1 = df[df["era"] == era_1].copy() if "era" in df.columns else df
        df_era_2 = df[df["era"] == era_2].copy() if "era" in df.columns else df

        # Calculate tier thresholds for each era
        def calculate_tier_thresholds(era_df, property_type):
            ptype_data = era_df[era_df["property_type"] == property_type]
            if ptype_data.empty or "price" not in ptype_data.columns:
                return None, None
            return ptype_data["price"].quantile(0.30), ptype_data["price"].quantile(0.70)

        # HDB comparison
        hdb_p30_1, hdb_p70_1 = calculate_tier_thresholds(df_era_1, "HDB")
        hdb_p30_2, hdb_p70_2 = calculate_tier_thresholds(df_era_2, "HDB")

        # Display tier threshold comparison
        st.markdown("#### Tier Threshold Comparison (HDB)")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown(f"**{era_1_label}**")
            st.metric("Mass Market Max", f"${hdb_p30_1:,.0f}" if hdb_p30_1 else "N/A")
            st.metric("Mid Tier Max", f"${hdb_p70_1:,.0f}" if hdb_p70_1 else "N/A")

        with c2:
            st.markdown(f"**{era_2_label}**")
            st.metric(
                "Mass Market Max",
                f"${hdb_p30_2:,.0f}" if hdb_p30_2 else "N/A",
                delta=f"{((hdb_p30_2 - hdb_p30_1) / hdb_p30_1 * 100) if hdb_p30_1 and hdb_p30_2 else 0:.1f}%"
                if hdb_p30_1 and hdb_p30_2
                else None,
            )
            st.metric(
                "Mid Tier Max",
                f"${hdb_p70_2:,.0f}" if hdb_p70_2 else "N/A",
                delta=f"{((hdb_p70_2 - hdb_p70_1) / hdb_p70_1 * 100) if hdb_p70_1 and hdb_p70_2 else 0:.1f}%"
                if hdb_p70_1 and hdb_p70_2
                else None,
            )

        with c3:
            st.markdown("**Change**")
            if hdb_p30_1 and hdb_p30_2:
                st.metric(
                    "Mass Market Threshold Change",
                    f"{((hdb_p30_2 - hdb_p30_1) / hdb_p30_1 * 100):+.1f}%",
                )
            if hdb_p70_1 and hdb_p70_2:
                st.metric(
                    "Mid Tier Threshold Change",
                    f"{((hdb_p70_2 - hdb_p70_1) / hdb_p70_1 * 100):+.1f}%",
                )

        # Transaction distribution by tier
        st.markdown("#### Transaction Distribution by Tier")

        def get_tier_distribution(era_df, ptype):
            ptype_data = era_df[era_df["property_type"] == ptype]
            if ptype_data.empty or "price" not in ptype_data.columns:
                return {}
            p30 = ptype_data["price"].quantile(0.30)
            p70 = ptype_data["price"].quantile(0.70)
            return {
                "Mass Market": (ptype_data["price"] <= p30).sum(),
                "Mid Tier": ((ptype_data["price"] > p30) & (ptype_data["price"] <= p70)).sum(),
                "Luxury": (ptype_data["price"] > p70).sum(),
            }

        hdb_dist_1 = get_tier_distribution(df_era_1, "HDB")
        hdb_dist_2 = get_tier_distribution(df_era_2, "HDB")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown(f"**{era_1_label} (HDB)**")
            if hdb_dist_1:
                dist_df_1 = pd.DataFrame(list(hdb_dist_1.items()), columns=["Tier", "Count"])
                dist_df_1["%"] = (dist_df_1["Count"] / dist_df_1["Count"].sum() * 100).round(1)
                st.dataframe(dist_df_1, hide_index=True, use_container_width=True)

        with col_b:
            st.markdown(f"**{era_2_label} (HDB)**")
            if hdb_dist_2:
                dist_df_2 = pd.DataFrame(list(hdb_dist_2.items()), columns=["Tier", "Count"])
                dist_df_2["%"] = (dist_df_2["Count"] / dist_df_2["Count"].sum() * 100).round(1)
                st.dataframe(dist_df_2, hide_index=True, use_container_width=True)

        st.info(f"💡 **Tier Comparison:** {era_1_label} vs {era_2_label}")

    st.markdown("---")

    st.markdown("### Historical Tier Evolution")

    st.dataframe(
        tier_thresholds.rename(
            columns={
                "property_type": "Property Type",
                "period": "Period",
                "mass_market_max": "Mass Market Max",
                "mid_tier_max": "Mid Tier Max",
                "luxury_min": "Luxury Min",
                "max_price": "Max Price",
                "transaction_count": "Transactions",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
