"""
Singapore Housing Price Visualization Dashboard

Main entry point for the Streamlit multi-page application.

Features:
- Interactive Price Map with heatmap/scatter views
- Market Overview with key statistics
- Trends & Analytics with time-series analysis
- Market Insights with Phase 2 features
- Property filtering by type, location, price, time
- Amenity overlays and advanced analytics
"""

import sys
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.ui_components import load_css, hero_banner, feature_highlight, divider

# Load environment variables
load_dotenv()

# Set page config - MUST be first Streamlit command
st.set_page_config(
    page_title="Singapore Housing Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': """
        ## Singapore Housing Price Dashboard

        A comprehensive visualization and analysis platform for Singapore's housing market.

        **Features:**
        - 1M+ transaction records (2015-2026)
        - Real-time market insights
        - Interactive maps & charts
        - Advanced filtering & analysis
        - Market segmentation & tier analysis
        - Town leaderboard rankings
        """
    }
)

# Load centralized CSS design system
load_css()

# Initialize session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# ============================================================================
# HERO SECTION
# ============================================================================

hero_banner(
    title="Singapore Housing Market Dashboard",
    subtitle="Comprehensive visualization & analysis platform with 1M+ transactions | 2015-2026"
)

# ============================================================================
# WELCOME MESSAGE
# ============================================================================

st.markdown("""
<div style="text-align: center; margin: 2rem 0;">
    <p style="font-size: 1.1rem; color: var(--text-secondary); line-height: 1.8;">
        Welcome to Singapore's most comprehensive housing market analytics platform.
        Explore trends, discover insights, and make data-driven decisions with our advanced visualization tools.
    </p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# PAGE NAVIGATION (Streamlit Native)
# ============================================================================

# Define pages (using list for flat navigation)
pages = [
    st.Page(
        "apps/1_market_overview.py",
        title="Market Overview",
        default=True
    ),
    st.Page(
        "apps/2_price_map.py",
        title="Price Map"
    ),
    st.Page(
        "apps/3_trends_analytics.py",
        title="Trends & Analytics"
    ),
    st.Page(
        "apps/market_insights/4a_segments.py",
        title="Market Segments"
    ),
    st.Page(
        "apps/market_insights/4b_tier_analysis.py",
        title="Tier Analysis"
    ),
    st.Page(
        "apps/market_insights/4c_town_leaderboard.py",
        title="Town Leaderboard"
    ),
]

# Create navigation
pg = st.navigation(pages)

# Run the app
if __name__ == "__main__":
    pg.run()
