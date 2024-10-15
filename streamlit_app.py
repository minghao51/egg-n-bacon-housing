import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import os
load_dotenv()
st.session_state['GOOGLE_API_KEY'] = os.environ["GOOGLE_API_KEY"]
"""
# Welcome to Streamlit!

"""

if 'GOOGLE_API_KEY' not in st.session_state:
    GOOGLE_API_KEY = st.sidebar.text_input("GOOGLE_API_KEY", type="password")
    
dashboard = st.Page(
    "apps/spiral.py", title="Dashboard", icon=":material/dashboard:", default=True
)
bugs3 = st.Page("apps/single_agent.py", title="Single Agent - No Memory", icon=":material/bug_report:")
bugs4 = st.Page("apps/single_agent2.py", title="Single Agent - Memory", icon=":material/bug_report:")
alerts = st.Page(
    "apps/spiral3.py", title="System alerts", icon=":material/notification_important:"
)

pg = st.navigation(
    {
        "Reports": [dashboard, bugs3, bugs4, alerts],

    }
)


pg.run()
