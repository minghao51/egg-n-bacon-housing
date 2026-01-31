"""Town Leaderboard - Ranked Town Analysis

This app provides ranked analysis of towns by:
- Overall investment score
- Value ranking (affordability + growth potential)
- Momentum ranking (recent price trends)
- Investor ranking (rental yield potential)
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
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

st.set_page_config(page_title="Town Leaderboard", page_icon="", layout="wide")

load_css()


@st.cache_data
def load_town_leaderboard():
    """Load town leaderboard summary."""
    path = Config.DATA_DIR / "analysis" / "town_leaderboard" / "town_leaderboard_summary.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def main():
    page_header(
        "Town Leaderboard",
        "Ranked analysis of towns by investment value, momentum, and overall score",
    )

    # ============================================================================
    # ERA SELECTOR (Phase 3-4)
    # ============================================================================
    st.sidebar.subheader("📅 Period Mode")

    from scripts.core.data_loader import load_unified_data

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
        "Enable Cross-Era Comparison", value=False, help="Compare town rankings between two eras"
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

    leaderboard = load_town_leaderboard()

    if leaderboard.empty:
        custom_warning(
            "Town leaderboard data not available. Run scripts/town_leaderboard.py first."
        )
        return

    hdb_towns = leaderboard[
        ~leaderboard["town"].str.startswith(("Condo", "EC", "Condo -", "EC -"))
    ].copy()

    if hdb_towns.empty:
        custom_warning("No HDB town data available in the leaderboard.")
        return

    section_header("Top Towns by Overall Score")

    st.info("""
    Towns are ranked by a composite score considering:
    - **Value Rank:** Affordability and price growth potential
    - **Momentum Rank:** Recent price appreciation trends
    - **Investor Rank:** Rental yield and cash flow potential
    Lower ranks = Better performance
    """)

    hdb_towns_sorted = hdb_towns.sort_values("overall_rank")

    col1, col2 = st.columns([2, 1])

    with col1:
        fig_bar = px.bar(
            hdb_towns_sorted.head(15),
            x="overall_rank",
            y="town",
            orientation="h",
            title="Top 15 Towns by Overall Score (Lower is Better)",
            labels={"overall_rank": "Overall Rank", "town": "Town"},
            color="overall_rank",
            color_continuous_scale="RdYlGn_r",
        )
        fig_bar.update_layout(
            yaxis_title="Town",
            xaxis_title="Overall Rank (Lower = Better)",
            template="plotly_white",
            height=500,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.markdown("### Top 5 Towns")
        top5 = hdb_towns_sorted.head(5)
        for _, row in top5.iterrows():
            overall = int(row["overall_rank"]) if pd.notna(row["overall_rank"]) else "N/A"
            value = int(row["value_rank"]) if pd.notna(row["value_rank"]) else "N/A"
            momentum = int(row["momentum_rank"]) if pd.notna(row["momentum_rank"]) else "N/A"
            st.markdown(
                f"""
            <div style="
                background-color: rgba(52, 152, 219, 0.1);
                padding: 0.75rem;
                margin: 0.25rem 0;
                border-radius: 0.5rem;
                border-left: 3px solid #3498db;
            ">
                <strong>{row["town"]}</strong><br>
                <span style="font-size: 0.8rem; color: #666;">
                    Overall: #{overall} | Value: #{value} | Momentum: #{momentum}
                </span>
            </div>
            """,
                unsafe_allow_html=True,
            )

    st.markdown("---")
    section_header("Town Performance Dimensions")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("### Best for Value")
        value_towns = hdb_towns.nlargest(10, "value_rank", keep="first").sort_values("value_rank")
        if not value_towns.empty:
            fig_value = px.bar(
                value_towns,
                x="value_rank",
                y="town",
                orientation="h",
                title="Top 10 Towns by Value Score",
                color="value_rank",
                color_continuous_scale="Blues_r",
            )
            fig_value.update_layout(
                yaxis_title="Town", xaxis_title="Value Rank", template="plotly_white", height=400
            )
            st.plotly_chart(fig_value, use_container_width=True)

    with col_b:
        st.markdown("### Best for Momentum")
        momentum_towns = hdb_towns.nlargest(10, "momentum_rank", keep="first").sort_values(
            "momentum_rank"
        )
        if not momentum_towns.empty:
            fig_momentum = px.bar(
                momentum_towns,
                x="momentum_rank",
                y="town",
                orientation="h",
                title="Top 10 Towns by Momentum Score",
                color="momentum_rank",
                color_continuous_scale="Greens_r",
            )
            fig_momentum.update_layout(
                yaxis_title="Town", xaxis_title="Momentum Rank", template="plotly_white", height=400
            )
            st.plotly_chart(fig_momentum, use_container_width=True)

    with col_c:
        st.markdown("### Best for Investors")
        investor_towns = hdb_towns.nlargest(10, "investor_rank", keep="first").sort_values(
            "investor_rank"
        )
        if not investor_towns.empty:
            fig_investor = px.bar(
                investor_towns,
                x="investor_rank",
                y="town",
                orientation="h",
                title="Top 10 Towns by Investor Score",
                color="investor_rank",
                color_continuous_scale="Purples_r",
            )
            fig_investor.update_layout(
                yaxis_title="Town", xaxis_title="Investor Rank", template="plotly_white", height=400
            )
            st.plotly_chart(fig_investor, use_container_width=True)

    st.markdown("---")
    section_header("Detailed Town Data")

    display_cols = ["town", "overall_rank", "value_rank", "momentum_rank", "investor_rank"]
    available_cols = [c for c in display_cols if c in hdb_towns.columns]
    if available_cols:
        display_df = hdb_towns[available_cols].copy()
        display_df = display_df.sort_values("overall_rank")
        st.dataframe(
            display_df.rename(
                columns={
                    "town": "Town",
                    "overall_rank": "Overall Rank",
                    "value_rank": "Value Rank",
                    "momentum_rank": "Momentum Rank",
                    "investor_rank": "Investor Rank",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")
    section_header("Investment Recommendations by Town Type")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### High-Value Towns (Rank 1-10)
        - Jurong West, Jurong East, Yishun, Ang Mo Kio, Woodlands
        - Best for first-time buyers seeking value
        - Strong rental demand from local workers

        ### Growth Towns (High Momentum)
        - Geylang, Serangoon, Kallang/Whampoa, Bishan
        - Emerging appreciation potential
        - Consider for medium-term hold (5-10 years)
        """)

    with col2:
        st.markdown("""
        ### Balanced Towns (Rank 11-20)
        - Bedok, Sembawang, Central Area, Clementi
        - Mix of value and growth potential
        - Good for diversified portfolios

        ### Premium Towns (Rank 21+)
        - Bukit Timah, Queenstown, Bukit Merah, Marine Parade
        - Higher entry point but stable demand
        - Focus on quality over value
        """)

    # ============================================================================
    # PHASE 4: Cross-Era Town Comparison
    # ============================================================================
    if compare_mode and "era" in df.columns:
        st.markdown("---")
        st.subheader("🔄 Cross-Era Town Comparison")

        era_1 = comparison_era_1 if comparison_era_1 else "pre_covid"
        era_2 = comparison_era_2 if comparison_era_2 else "recent"

        era_1_label = "Pre-COVID (2015-2021)" if era_1 == "pre_covid" else "Recent (2022-2026)"
        era_2_label = "Pre-COVID (2015-2021)" if era_2 == "pre_covid" else "Recent (2022-2026)"

        df_era_1 = df[df["era"] == era_1].copy() if "era" in df.columns else df
        df_era_2 = df[df["era"] == era_2].copy() if "era" in df.columns else df

        # Calculate town-level metrics for each era
        def calculate_town_metrics(era_df):
            if "town" not in era_df.columns or "price" not in era_df.columns:
                return pd.DataFrame()
            return (
                era_df.groupby("town")
                .agg(
                    {
                        "price": ["count", "median", "mean"],
                        "price_psf": "median" if "price_psf" in era_df.columns else "count",
                    }
                )
                .reset_index()
            )

        town_metrics_1 = calculate_town_metrics(df_era_1)
        town_metrics_2 = calculate_town_metrics(df_era_2)

        if not town_metrics_1.empty and not town_metrics_2.columns.nlevels == 2:
            # Fix multi-level columns
            town_metrics_1.columns = [
                "town",
                "count_1",
                "median_price_1",
                "mean_price_1",
                "median_psf_1",
            ]
            town_metrics_2.columns = [
                "town",
                "count_2",
                "median_price_2",
                "mean_price_2",
                "median_psf_2",
            ]
        elif not town_metrics_1.empty:
            town_metrics_1.columns = ["town"] + [f"{a}_{b}" for a, b in town_metrics_1.columns[1:]]
            town_metrics_2.columns = ["town"] + [f"{a}_{b}" for a, b in town_metrics_2.columns[1:]]

        # Merge and calculate changes
        if not town_metrics_1.empty and not town_metrics_2.empty:
            comparison_df = pd.merge(town_metrics_1, town_metrics_2, on="town", how="outer")
            comparison_df = comparison_df.fillna(0)

            # Calculate changes
            comparison_df["price_change_pct"] = (
                (comparison_df["median_price_2"] - comparison_df["median_price_1"])
                / comparison_df["median_price_1"].replace(0, 1)
                * 100
            )
            comparison_df["volume_change_pct"] = (
                (comparison_df["count_2"] - comparison_df["count_1"])
                / comparison_df["count_1"].replace(0, 1)
                * 100
            )

            # Top movers by price change
            st.markdown("#### Top 10 Towns by Price Change")

            top_movers = comparison_df.nlargest(10, "price_change_pct")

            fig_movers = px.bar(
                top_movers,
                x="price_change_pct",
                y="town",
                orientation="h",
                title=f"Top 10 Towns by Price Change: {era_1_label} → {era_2_label}",
                color="price_change_pct",
                color_continuous_scale="RdYlGn",
            )
            fig_movers.update_layout(
                yaxis_title="Town",
                xaxis_title="Price Change (%)",
                template="plotly_white",
                height=400,
            )
            st.plotly_chart(fig_movers, use_container_width=True)

            # Volume comparison
            st.markdown("#### Transaction Volume by Town")

            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown(f"**{era_1_label}**")
                vol_1 = town_metrics_1.sort_values("count_1", ascending=False).head(10)
                st.dataframe(
                    pd.DataFrame({"Town": vol_1["town"], "Transactions": vol_1["count_1"]}),
                    hide_index=True,
                    use_container_width=True,
                )

            with col_b:
                st.markdown(f"**{era_2_label}**")
                vol_2 = town_metrics_2.sort_values("count_2", ascending=False).head(10)
                st.dataframe(
                    pd.DataFrame({"Town": vol_2["town"], "Transactions": vol_2["count_2"]}),
                    hide_index=True,
                    use_container_width=True,
                )

            st.info(f"💡 **Town Comparison:** {era_1_label} vs {era_2_label}")

    st.markdown("---")


if __name__ == "__main__":
    main()
