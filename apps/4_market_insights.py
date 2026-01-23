"""Market Insights Dashboard - Comprehensive Analysis

This app provides in-depth market analysis:
- Feature Importance Analysis (ML-driven feature drivers)
- Market Segmentation (K-means behavioral clustering)
- Rental Market Analysis
- Investment Opportunity Matrix
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.ui_components import (
    load_css, page_header, section_header, info_box, 
    custom_warning, custom_success, metric_card
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Market Insights",
    page_icon="",
    layout="wide"
)

# Load centralized design system
load_css()


@st.cache_data
def load_l3_data():
    """Load L3 unified dataset."""
    path = Config.PARQUETS_DIR / "L3" / "housing_unified.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


@st.cache_data
def load_period_segmented_data():
    """Load period-segmented dataset."""
    path = Config.DATA_DIR / "analysis" / "market_segmentation_period" / "housing_unified_period_segmented.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None


@st.cache_data
def load_lease_decay_analysis():
    """Load lease decay analysis."""
    path = Config.DATA_DIR / "analysis" / "lease_decay" / "lease_decay_analysis.csv"
    if path.exists():
        return pd.read_csv(path)
    return None


@st.cache_data
def load_rental_vs_resale():
    """Load rental vs resale comparison."""
    path = Config.DATA_DIR / "analysis" / "rental_market" / "rental_vs_resale_comparison.csv"
    if path.exists():
        return pd.read_csv(path)
    return None


@st.cache_data
def load_tier_thresholds():
    """Load tier threshold evolution."""
    path = Config.DATA_DIR / "analysis" / "market_segmentation_period" / "tier_thresholds_evolution.csv"
    if path.exists():
        return pd.read_csv(path)
    return None


@st.cache_data
def load_rental_yield_data() -> pd.DataFrame:
    """Load rental yield data from L2."""
    path = Config.PARQUETS_DIR / "L2" / "rental_yield.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


@st.cache_data
def load_feature_importance() -> pd.DataFrame:
    """Load feature importance results."""
    path = Config.DATA_DIR / "analysis" / "feature_importance" / "model_comparison.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_cluster_profiles() -> pd.DataFrame:
    """Load market segmentation cluster profiles."""
    path = Config.DATA_DIR / "analysis" / "market_segmentation_2.0" / "cluster_profiles.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_investment_strategies() -> pd.DataFrame:
    """Load investment strategies per segment."""
    path = Config.DATA_DIR / "analysis" / "market_segmentation_2.0" / "investment_strategies.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_amenity_temporal() -> pd.DataFrame:
    """Load amenity temporal analysis."""
    path = Config.DATA_DIR / "analysis" / "amenity_impact" / "temporal_comparison.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_amenity_within_town() -> pd.DataFrame:
    """Load within-town amenity effects."""
    path = Config.DATA_DIR / "analysis" / "amenity_impact" / "within_town_effects.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_amenity_distance_strat() -> pd.DataFrame:
    """Load MRT distance stratification."""
    path = Config.DATA_DIR / "analysis" / "amenity_impact" / "mrt_distance_stratification.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def load_amenity_summary() -> pd.DataFrame:
    """Load amenity summary statistics."""
    path = Config.DATA_DIR / "analysis" / "amenity_impact" / "summary_stats.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


def render_overview_tab(df, lease_decay, rental_comparison):
    """Render the Overview tab."""
    page_header("Market Insights Overview", "Comprehensive Analysis from Phase 2 Quick Wins")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Records", f"{len(df):,}")
    with col2:
        st.metric("Property Types", df['property_type'].nunique() if 'property_type' in df.columns else "N/A")
    with col3:
        if 'transaction_date' in df.columns:
            st.metric("Date Range", f"{df['transaction_date'].min().year} - {df['transaction_date'].max().year}")
    with col4:
        if 'lat' in df.columns:
            st.metric("Geocoding Coverage", f"{df['lat'].notna().sum()/len(df)*100:.1f}%")

    if 'property_type' in df.columns:
        st.subheader("Property Type Distribution")
        col1, col2, col3 = st.columns(3)
        for i, (ptype, count) in enumerate(df['property_type'].value_counts().items()):
            with [col1, col2, col3][i % 3]:
                pct = count / len(df) * 100
                st.metric(ptype, f"{count:,} ({pct:.1f}%)")

    st.markdown("---")
    section_header("Key Phase 2 Findings")

    info_box("""
    ML Model Performance: Random Forest models achieve excellent prediction accuracy (R2 > 0.96) for
    price PSM, rental yield, and appreciation. Storey range and property type drive 90% of price variation.
    Trading volume is the strongest predictor of future appreciation.
    """)

    info_box("""
    Rental Yields: HDB properties deliver higher rental yields (avg 5.93%) compared to condos (avg 3.85%).
    Top opportunities exceed 5% yield in specific town + flat type combinations.
    """)

    info_box("""
    Lease Decay: Properties with shorter remaining leases sell at significant discounts.
    Those with <60 years lease trade at ~15% discount vs 90+ year leases.
    """)

    col1, col2 = st.columns(2)

    with col1:
        section_header("Lease Decay Summary")
        if lease_decay is not None:
            st.dataframe(
                lease_decay[['lease_band', 'median_price', 'discount_to_baseline', 'annual_decay_pct']],
                use_container_width=True,
                hide_index=True
            )

            lease_path = Config.DATA_DIR / "analysis" / "lease_decay" / "lease_decay_psm_by_band.png"
            if lease_path.exists():
                st.image(str(lease_path), caption="Median Price per SQM by Remaining Lease", use_container_width=True)
        else:
            custom_warning("Lease decay analysis not available. Run scripts/analyze_lease_decay.py first.")

    with col2:
        section_header("Rental Yield Summary")
        if rental_comparison is not None:
            st.metric("Median Yield", f"{rental_comparison['rental_yield_pct'].median():.2f}%")
            st.metric("Max Yield", f"{rental_comparison['rental_yield_pct'].max():.2f}%")
            st.metric("High-Yield Opportunities", f"{(rental_comparison['rental_yield_pct'] > 5.0).sum()} combos")

            distribution_path = Config.DATA_DIR / "analysis" / "rental_market" / "rental_by_flat_type.png"
            if distribution_path.exists():
                st.image(str(distribution_path), caption="Rent Distribution by Flat Type", use_container_width=True)
        else:
            custom_warning("Rental analysis not available. Run scripts/analyze_hdb_rental_market.py first.")


def render_feature_drivers_tab():
    """Render the Feature Drivers tab."""
    page_header("Feature Importance Analysis", "ML-driven identification of key price, yield, and appreciation drivers")

    model_results = load_feature_importance()
    cluster_profiles = load_cluster_profiles()

    section_header("Model Performance Summary")

    if not model_results.empty:
        st.info("Key Finding: Random Forest models achieve R2 > 0.96 for all targets. Pre-2020 patterns do NOT predict post-2020 prices.")

        col1, col2, col3 = st.columns(3)

        with col1:
            price_r2 = model_results[(model_results['target'] == 'price_psm')]['test_r2'].max()
            st.metric("Price PSM Prediction", f"R2 = {price_r2:.3f}", delta="Excellent")

        with col2:
            yield_r2 = model_results[(model_results['target'] == 'rental_yield_pct')]['test_r2'].max()
            st.metric("Rental Yield Prediction", f"R2 = {yield_r2:.3f}", delta="Excellent")

        with col3:
            app_r2 = model_results[(model_results['target'] == 'yoy_change_pct')]['test_r2'].max()
            st.metric("Appreciation Prediction", f"R2 = {app_r2:.3f}", delta="Excellent")

        st.subheader("Model Comparison by Target")
        st.dataframe(
            model_results[['model', 'target_name', 'test_r2', 'test_mae', 'test_rmse']],
            use_container_width=True,
            hide_index=True
        )
    else:
        custom_warning("Feature importance results not available. Run scripts/analyze_feature_importance.py first.")

    st.markdown("---")
    section_header("Top Feature Drivers")

    info_box("""
    <strong>1. Transaction Price (PSM)</strong><br>
    Top drivers: storey_range (29.6%), flat_type (24.4%), property_type_HDB (20.0%), psm_tier_High PSM (16.3%)<br>
    <em>Insight: Property characteristics (storey, type, segment) drive 90% of price variation. Location features (amenities) surprisingly < 5%.</em>
    """)

    info_box("""
    <strong>2. Rental Yield (%)</strong><br>
    Top drivers: property_type_HDB (42.6%), storey_range (13.6%), psm_tier_High PSM (10.3%), town_TAMPINES (8.3%)<br>
    <em>Insight: Property type dominates yield calculation. HDBs yield significantly more than condos. Premium properties have lower yields.</em>
    """)

    info_box("""
    <strong>3. Year-over-Year Appreciation (%)</strong><br>
    Top drivers: volume_12m_avg (27.2%), transaction_count (25.2%), stratified_median_price (15.9%), volume_3m_avg (13.1%)<br>
    <em>Insight: Market momentum features explain 81% of appreciation variation. Trading volume is the strongest predictor of future price growth.</em>
    """)

    st.markdown("---")
    section_header("Key Business Implications")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **For Price Prediction:**
        - Automated Valuation Models (AVMs) can achieve high accuracy (R2 = 0.978) with basic property attributes
        - Storey level and flat type are primary drivers
        - Location features have minimal impact once town is known

        **For Rental Yield:**
        - HDBs consistently outperform condos in yield (5.93% vs 3.85%)
        - Investors should prioritize property type over location for yield
        """)

    with col2:
        st.markdown("""
        **For Appreciation Prediction:**
        - Timing matters more than property selection for capital gains
        - Trading volume is the leading indicator of price growth
        - Property characteristics have minimal impact on appreciation

        **Important Warning:**
        - Pre-2020 patterns fail to predict post-2020 prices (R2 = -0.497)
        - Market structure changed fundamentally post-2020 (COVID, interest rates, cooling measures)
        """)

    st.markdown("---")
    section_header("Amenity Impact Analysis")
    st.markdown("### Deep dive into MRT and amenity proximity effects")

    amenity_temporal = load_amenity_temporal()
    amenity_within_town = load_amenity_within_town()
    amenity_dist_strat = load_amenity_distance_strat()
    amenity_summary = load_amenity_summary()

    if not amenity_summary.empty:
        summary = amenity_summary.iloc[0]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("MRT Importance (Pre-COVID)", f"{summary['mrt_importance_pre_covid']:.2%}")
        with col2:
            st.metric("MRT Importance (Post-COVID)", f"{summary['mrt_importance_post_covid']:.2%}")
        with col3:
            change = summary.get('mrt_importance_change_pct', 0)
            st.metric("Importance Change", f"{change:.1f}%")
        with col4:
            premium = summary.get('mrt_proximity_premium_pct', 0)
            st.metric("MRT Proximity Premium", f"{premium:.1f}%")

        st.info(f"**Key Finding:** Properties within 200m of MRT command {premium:.1f}% price premium vs 2000m+.")

    st.markdown("---")
    st.markdown("#### Temporal Analysis: Pre-COVID vs COVID vs Post-COVID")

    if not amenity_temporal.empty:
        periods = ['pre_covid', 'covid', 'post_covid']
        period_labels = {'pre_covid': 'Pre-COVID (2015-2019)', 'covid': 'COVID (2020-2022)', 'post_covid': 'Post-COVID (2023-2025)'}

        mrt_features = ['dist_to_nearest_mrt', 'mrt_within_500m', 'mrt_within_1km', 'mrt_within_2km']

        mrt_temporal = amenity_temporal[amenity_temporal['feature'].isin(mrt_features)]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**MRT Distance Feature Importance by Period**")
            mrt_pivot = mrt_temporal.pivot_table(index='feature', columns='period', values='importance', fill_value=0)
            mrt_pivot = mrt_pivot[[p for p in periods if p in mrt_pivot.columns]]
            mrt_pivot.columns = [period_labels.get(c, c) for c in mrt_pivot.columns]
            st.dataframe(mrt_pivot.style.format("{:.2%}"), use_container_width=True)

        with col2:
            st.markdown("**Top Amenity Features (Average Importance)**")
            top_amenity = amenity_temporal[~amenity_temporal['feature'].str.contains('mrt', case=False, na=False)]
            top_amenity = top_amenity.groupby('feature')['importance'].mean().sort_values(ascending=False).head(5)
            fig = px.bar(
                x=[f.replace('_within_', ' <').replace('_', ' ').title() + 'm' if 'within' in f else f.replace('_', ' ').title() for f in top_amenity.index],
                y=top_amenity.values,
                title='Top 5 Amenity Features',
                labels={'x': 'Feature', 'y': 'Importance'},
                color=top_amenity.values,
                color_continuous_scale='RdYlGn'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Within-Town MRT Sensitivity")

    if not amenity_within_town.empty:
        top_towns = amenity_within_town.nlargest(15, 'mrt_distance_importance')

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Top 15 Towns by MRT Distance Sensitivity**")
            fig = px.bar(
                top_towns,
                x='mrt_distance_importance',
                y='town',
                orientation='h',
                title='MRT Distance Impact Within Town',
                labels={'mrt_distance_importance': 'Importance', 'town': 'Town'},
                color='mrt_distance_importance',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Top Towns Table**")
            display = top_towns[['town', 'n_transactions', 'mrt_distance_importance']].copy()
            display['mrt_distance_importance'] = [f"{x:.4f}" for x in display['mrt_distance_importance']]
            st.dataframe(display, use_container_width=True, hide_index=True)

            st.markdown(f"""
            **Insight:** {top_towns.iloc[0]['town']} shows highest within-town MRT sensitivity ({top_towns.iloc[0]['mrt_distance_importance']:.2%}).
            Within this town, MRT proximity has significant impact on price after controlling for town-level effects.
            """)

    st.markdown("---")
    st.markdown("#### MRT Distance Stratification")

    if not amenity_dist_strat.empty:
        st.markdown("**Price PSM by MRT Distance Band**")

        fig = px.bar(
            amenity_dist_strat,
            x='dist_band',
            y='price_psm_median',
            title='Median Price PSM by MRT Distance',
            labels={'dist_band': 'MRT Distance Band', 'price_psm_median': 'Median Price PSM (SGD)'},
            color='price_psm_median',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            closest = amenity_dist_strat.iloc[0]
            st.metric("Closest (0-200m)", f"${closest['price_psm_median']:,.0f}/psm", f"{int(closest['dist_to_nearest_mrt_mean'])}m avg")
        with col2:
            middle = amenity_dist_strat[amenity_dist_strat['dist_band'] == '600-800m']
            if not middle.empty:
                st.metric("Middle (600-800m)", f"${middle['price_psm_median'].values[0]:,.0f}/psm")
            else:
                st.metric("Middle (600-800m)", "N/A")
        with col3:
            farthest = amenity_dist_strat.iloc[-1]
            st.metric("Farthest (2000m+)", f"${farthest['price_psm_median']:,.0f}/psm", f"{int(farthest['dist_to_nearest_mrt_mean'])}m avg")

    st.markdown("---")
    section_header("Key Amenity Insights")

    info_box("""
    <strong>1. COVID Effect on MRT Importance:</strong><br>
    MRT distance importance DECREASED from Pre-COVID (2.68%) to Post-COVID (1.27%), a -52.7% change.
    This suggests COVID disrupted the MRT proximity premium, possibly due to remote work reducing commuting importance.
    """)

    info_box("""
    <strong>2. Hawker Centers Trump MRT:</strong><br>
    Hawker center proximity (hawker_within_2km) consistently ranks as the top amenity feature (31-41% importance),
    significantly more important than MRT proximity. Daily lifestyle amenities matter more for pricing.
    """)

    info_box("""
    <strong>3. Within-Town Variation:</strong><br>
    MRT sensitivity varies significantly by town. Sembawang (21.1%), Bishan (14.3%), and Woodlands (10.8%)
    show highest within-town MRT sensitivity. In these towns, MRT proximity commands a premium even after controlling for town.
    """)

    info_box("""
    <strong>4. MRT Proximity Premium:</strong><br>
    Properties within 200m of MRT command a 16.3% price premium vs properties 2000m+ away.
    The premium is strongest in the 0-400m range and diminishes with distance.
    """)


def render_segments_tab():
    """Render the Market Segments tab."""
    page_header("Market Segmentation Analysis", "K-means behavioral clustering to identify distinct market segments")

    cluster_profiles = load_cluster_profiles()
    investment_strategies = load_investment_strategies()

    if not cluster_profiles.empty:
        section_header("Cluster Profiles")

        profile_cols = ['segment_name', 'cluster_size', 'cluster_percentage']
        if 'price_psm_mean' in cluster_profiles.columns:
            profile_cols.append('price_psm_mean')
        if 'rental_yield_pct_mean' in cluster_profiles.columns:
            profile_cols.append('rental_yield_pct_mean')
        if 'yoy_change_pct_mean' in cluster_profiles.columns:
            profile_cols.append('yoy_change_pct_mean')

        available_cols = [c for c in profile_cols if c in cluster_profiles.columns]
        if available_cols:
            display_df = cluster_profiles[available_cols].copy()
            if 'price_psm_mean' in display_df.columns:
                display_df['price_psm_mean'] = [f"${x:,.0f}" if pd.notna(x) else x for x in display_df['price_psm_mean']]
            if 'rental_yield_pct_mean' in display_df.columns:
                display_df['rental_yield_pct_mean'] = [f"{x:.2f}%" if pd.notna(x) else x for x in display_df['rental_yield_pct_mean']]
            if 'yoy_change_pct_mean' in display_df.columns:
                display_df['yoy_change_pct_mean'] = [f"{x:.2f}%" if pd.notna(x) else x for x in display_df['yoy_change_pct_mean']]
            display_df.columns = [c.replace('_mean', '').replace('_', ' ').title() for c in display_df.columns]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        section_header("Segment Visualization")

        col1, col2 = st.columns(2)

        with col1:
            pca_path = Config.DATA_DIR / "analysis" / "market_segmentation_2.0" / "clusters_pca.png"
            if pca_path.exists():
                st.image(str(pca_path), caption="PCA Cluster Visualization", use_container_width=True)
            elif 'price_psm_mean' in cluster_profiles.columns:
                fig = px.bar(
                    cluster_profiles.sort_values('price_psm_mean'),
                    x='segment_name',
                    y='price_psm_mean',
                    title='Average Price PSM by Segment',
                    labels={'segment_name': 'Segment', 'price_psm_mean': 'Avg Price PSM (SGD)'},
                    color='price_psm_mean',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            optimal_path = Config.DATA_DIR / "analysis" / "market_segmentation_2.0" / "optimal_clusters.png"
            if optimal_path.exists():
                st.image(str(optimal_path), caption="Optimal Cluster Selection", use_container_width=True)
            elif 'rental_yield_pct_mean' in cluster_profiles.columns:
                fig = px.bar(
                    cluster_profiles.sort_values('rental_yield_pct_mean'),
                    x='segment_name',
                    y='rental_yield_pct_mean',
                    title='Average Rental Yield by Segment',
                    labels={'segment_name': 'Segment', 'rental_yield_pct_mean': 'Avg Yield (%)'},
                    color='rental_yield_pct_mean',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        section_header("Investment Strategies by Segment")

        if not investment_strategies.empty:
            for _, row in investment_strategies.iterrows():
                strategy_color = "#e8f4fd"
                if "HOLD & GROW" in row['strategy']:
                    strategy_color = "#d4edda"
                elif "YIELD PLAY" in row['strategy']:
                    strategy_color = "#fff3cd"
                elif "GROWTH PLAY" in row['strategy']:
                    strategy_color = "#f8d7da"
                elif "VALUE" in row['strategy']:
                    strategy_color = "#d1ecf1"

                st.markdown(f"""
                <div style="background-color: {strategy_color}; padding: 1rem; margin: 0.5rem 0; border-radius: 0.5rem;">
                    <strong>{row['segment_name']}</strong><br>
                    {row['strategy']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("Investment strategies not available. Run scripts/quick_cluster_profiles.py first.")

    else:
        custom_warning("Market segmentation results not available. Run scripts/quick_cluster_profiles.py first.")

    st.markdown("---")
    section_header("Behavioral Clustering Insights")

    info_box("""
    <strong>Methodology:</strong> K-means clustering on key behavioral metrics (price PSM, floor area, remaining lease,
    rental yield, appreciation, transaction volume). Optimal clusters determined using silhouette analysis.
    """)

    info_box("""
    <strong>Applications:</strong> Identify natural market segments for targeted investment strategies.
    Compare segments on yield vs growth trade-offs. Discover emerging market behaviors before they appear in traditional metrics.
    """)


def render_rental_tab(rental_comparison, df):
    """Render the Rental Analysis tab."""
    page_header("Rental Market Analysis", "HDB rental trends, affordability, and yield opportunities")

    col_trend, col_yields = st.columns([2, 1])

    with col_trend:
        section_header("Rental Trend Over Time")
        trend_path = Config.DATA_DIR / "analysis" / "rental_market" / "rental_trend_over_time.png"
        if trend_path.exists():
            st.image(str(trend_path), caption="Median Monthly Rent Trend (2015-2025)", use_container_width=True)
        else:
            st.info("Rental trend visualization not available.")

    with col_yields:
        section_header("Key Metrics")
        if rental_comparison is not None:
            st.metric("Median Yield", f"{rental_comparison['rental_yield_pct'].median():.2f}%")
            st.metric("Max Yield", f"{rental_comparison['rental_yield_pct'].max():.2f}%")
            st.metric("High-Yield (>5%)", f"{(rental_comparison['rental_yield_pct'] > 5.0).sum()} combos")
        else:
            st.info("Rental comparison data not available.")

    if rental_comparison is not None:
        section_header("Top 15 Highest Rental Yields")

        st.info("Key Insight: Median rental yield is 4.97%. Executive flats in Jurong West offer yields up to 5.86%.")

        top_yields = rental_comparison.nlargest(15, 'rental_yield_pct')

        display_yields = top_yields[['town', 'flat_type', 'monthly_rent', 'resale_price', 'rental_yield_pct']].copy()
        display_yields['monthly_rent'] = [f"${x:,.0f}" for x in display_yields['monthly_rent']]
        display_yields['resale_price'] = [f"${x:,.0f}" for x in display_yields['resale_price']]
        display_yields['rental_yield_pct'] = [f"{x:.2f}%" for x in display_yields['rental_yield_pct']]

        st.dataframe(display_yields, use_container_width=True, hide_index=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            section_header("Yield Statistics")
            st.metric("Median Yield", f"{rental_comparison['rental_yield_pct'].median():.2f}%")
            st.metric("Mean Yield", f"{rental_comparison['rental_yield_pct'].mean():.2f}%")
            st.metric("Min Yield", f"{rental_comparison['rental_yield_pct'].min():.2f}%")

        with col2:
            section_header("Yield Distribution")
            fig = px.histogram(
                rental_comparison,
                x='rental_yield_pct',
                nbins=30,
                title="Rental Yield Distribution",
                labels={'rental_yield_pct': 'Rental Yield (%)', 'count': 'Count'},
                color_discrete_sequence=['#3498db']
            )
            fig.add_vline(x=5.0, line_dash="dash", line_color="red",
                         annotation_text="5% Threshold")
            st.plotly_chart(fig, use_container_width=True)

        with col3:
            section_header("Rent by Flat Type")
            flat_type_path = Config.DATA_DIR / "analysis" / "rental_market" / "rental_by_flat_type.png"
            if flat_type_path.exists():
                st.image(str(flat_type_path), caption="Rent Distribution by Flat Type", use_container_width=True)
            elif 'flat_type' in rental_comparison.columns:
                yield_by_flat = rental_comparison.groupby('flat_type')['rental_yield_pct'].median().sort_values(ascending=False)
                fig = px.bar(
                    x=yield_by_flat.index,
                    y=yield_by_flat.values,
                    title='Median Rental Yield by Flat Type',
                    labels={'x': 'Flat Type', 'y': 'Median Yield (%)'},
                    color=yield_by_flat.values,
                    color_continuous_scale='RdYlGn'
                )
                fig.update_xaxes(type='category')
                st.plotly_chart(fig, use_container_width=True)

        with col1:
            section_header("Rental Trend Over Time")
            trend_path = Config.DATA_DIR / "analysis" / "rental_market" / "rental_trend_over_time.png"
            if trend_path.exists():
                st.image(str(trend_path), caption="Median Monthly Rent Trend (2015-2025)", use_container_width=True)
            else:
                st.info("Rental trend visualization not available.")

        with col2:
            section_header("Rent by Flat Type")
            flat_type_path = Config.DATA_DIR / "analysis" / "rental_market" / "rental_by_flat_type.png"
            if flat_type_path.exists():
                st.image(str(flat_type_path), caption="Monthly Rent Distribution by Flat Type", use_container_width=True)
            elif 'flat_type' in rental_comparison.columns:
                yield_by_flat = rental_comparison.groupby('flat_type')['rental_yield_pct'].median().sort_values(ascending=False)
                fig = px.bar(
                    x=yield_by_flat.index,
                    y=yield_by_flat.values,
                    title='Median Rental Yield by Flat Type',
                    labels={'x': 'Flat Type', 'y': 'Median Yield (%)'},
                    color=yield_by_flat.values,
                    color_continuous_scale='RdYlGn'
                )
                fig.update_xaxes(type='category')
                st.plotly_chart(fig, use_container_width=True)

    else:
        custom_warning("Rental analysis not available. Run scripts/analyze_hdb_rental_market.py first.")

    st.markdown("---")
    section_header("HDB Affordability Analysis")

    if 'property_type' in df.columns:
        hdb_data = df[df['property_type'] == 'HDB']

        if not hdb_data.empty:
            col1, col2 = st.columns(2)

            with col1:
                if 'price' in hdb_data.columns:
                    st.metric("HDB Median Price", f"${hdb_data['price'].median():,.0f}")
                    st.metric("HDB Price Range", f"${hdb_data['price'].min():,.0f} - ${hdb_data['price'].max():,.0f}")

            with col2:
                if 'floor_area_sqm' in hdb_data.columns:
                    st.metric("Avg Floor Area", f"{hdb_data['floor_area_sqm'].mean():.0f} sqm")
                    st.metric("Area Range", f"{hdb_data['floor_area_sqm'].min():.0f} - {hdb_data['floor_area_sqm'].max():.0f} sqm")
        else:
            st.info("No HDB data available for affordability analysis.")

    st.markdown("---")
    section_header("HDB vs Condo Yield Comparison")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **HDB Rental Yields**
        - Average Yield: 5.93%
        - Range: 2.92% to 9.64%
        - Methodology: (monthly_rent x 12 / resale_price) x 100
        - Coverage: 27 towns x 59 months (2021-2025)
        """)

    with col2:
        st.markdown("""
        **Condo Rental Yields**
        - Average Yield: 3.85%
        - Range: 3.13% to 4.97%
        - Methodology: Index-based estimation (URA Rental Index)
        - Coverage: 3 regions (CCR/RCR/OCR)
        """)

    info_box("""
    <strong>Key Insight:</strong> HDB properties deliver significantly higher rental yields than condos.
    For cash flow-focused investors, HDB mass market properties in suburban towns offer the best yields.
    """)


def render_investment_tab(df):
    """Render the Investment Matrix tab."""
    page_header("Investment Opportunity Matrix", "Quadrant analysis comparing rental yield vs price appreciation")

    st.info("Quadrant Analysis: Compare rental yield vs price appreciation across planning areas. Bubble size = Transaction volume. Median values determine quadrant boundaries.")

    rental_yield_df = load_rental_yield_data()
    df = load_l3_data()

    if not df.empty and not rental_yield_df.empty:
        from src.chart_utils import aggregate_investment_metrics, create_investment_quadrant_chart

        tab_hdb, tab_condo = st.tabs(["HDB", "Condominium"])

        property_types = {
            "HDB": (tab_hdb, "HDB"),
            "Condominium": (tab_condo, "Condominium")
        }

        for tab, ptype in property_types.values():
            with tab:
                metrics_df = aggregate_investment_metrics(df, rental_yield_df, ptype)

                if metrics_df.empty:
                    if ptype == "Condominium":
                        st.warning("Condominium investment analysis requires rental yield data by town. Currently only region-level data (CCR/RCR/OCR) is available.")
                    else:
                        st.warning(f"No investment data available for {ptype}. This may occur if rental yield data doesn't overlap with transaction periods.")
                    continue

                fig = create_investment_quadrant_chart(metrics_df, property_type=ptype)
                st.plotly_chart(fig, use_container_width=True)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Areas Analyzed", f"{len(metrics_df)}")
                with col2:
                    st.metric("Median Rental Yield", f"{metrics_df['rental_yield_pct'].median():.2f}%")
                with col3:
                    st.metric("Median Appreciation", f"{metrics_df['appreciation_pct'].median():.2f}%")
                with col4:
                    best_count = len(metrics_df[
                        (metrics_df['rental_yield_pct'] >= metrics_df['rental_yield_pct'].median()) &
                        (metrics_df['appreciation_pct'] >= metrics_df['appreciation_pct'].median())
                    ])
                    st.metric("Best Investment Areas", f"{best_count}")

                with st.expander("View Detailed Data"):
                    display_df = metrics_df.copy()
                    display_df['rental_yield_pct'] = display_df['rental_yield_pct'].apply(lambda x: f"{x:.2f}%")
                    display_df['appreciation_pct'] = display_df['appreciation_pct'].apply(lambda x: f"{x:.2f}%")
                    display_df['median_price'] = display_df['median_price'].apply(lambda x: f"${x:,.0f}")
                    display_df['transaction_count'] = display_df['transaction_count'].apply(lambda x: f"{x:,}")
                    st.dataframe(
                        display_df[['planning_area', 'rental_yield_pct', 'appreciation_pct', 'median_price', 'transaction_count']],
                        use_container_width=True,
                        hide_index=True
                    )

    else:
        if df.empty:
            st.warning("Unified dataset not found. Run scripts/create_l3_unified_dataset.py first.")
        if rental_yield_df.empty:
            st.warning("Rental yield data not found. Run scripts/calculate_rental_yield.py first.")

    st.markdown("---")
    section_header("Investment Strategy Guide")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **High Yield + High Growth (Top Right Quadrant)**
        - Best of both worlds: strong cash flow AND capital appreciation
        - Action: Prioritize these areas for investment

        **High Yield + Low Growth (Bottom Right Quadrant)**
        - Cash flow focus: good for income-focused investors
        - Action: Consider for buy-and-hold strategies

        **Low Yield + High Growth (Top Left Quadrant)**
        - Capital gains focus: appreciation potential outweighs low yield
        - Action: Timing critical, exit strategy important
        """)

    with col2:
        st.markdown("""
        **Low Yield + Low Growth (Bottom Left Quadrant)**
        - Avoid for investment purposes
        - Action: Only consider for owner-occupation

        **Key Metrics:**
        - Bubble size = Transaction volume (liquidity indicator)
        - X-axis = Rental yield (cash flow)
        - Y-axis = Appreciation rate (capital gains)
        - Dotted lines = Median values (quadrant boundaries)
        """)


def main():
    """Main application with tab navigation."""
    page_header("Market Insights Dashboard", "Comprehensive Analysis from Phase 2 Quick Wins")

    with st.spinner("Loading data..."):
        df = load_l3_data()
        df_period = load_period_segmented_data()
        lease_decay = load_lease_decay_analysis()
        rental_comparison = load_rental_vs_resale()
        tier_thresholds = load_tier_thresholds()

    tab_overview, tab_features, tab_segments, tab_rental, tab_investment = st.tabs([
        "Overview",
        "Feature Drivers",
        "Market Segments",
        "Rental Analysis",
        "Investment Matrix"
    ])

    with tab_overview:
        render_overview_tab(df, lease_decay, rental_comparison)

    with tab_features:
        render_feature_drivers_tab()

    with tab_segments:
        render_segments_tab()

    with tab_rental:
        render_rental_tab(rental_comparison, df)

    with tab_investment:
        render_investment_tab(df)

    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #7f8c8d; margin-top: 2rem;'>
        <p><b>Market Insights Dashboard</b> - Phase 2 Quick Wins</p>
        <p>Feature Importance | Market Segmentation | Rental Analysis | Investment Matrix</p>
        <p style='font-size: 0.8rem;'>Last updated: 2026-01-22</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
