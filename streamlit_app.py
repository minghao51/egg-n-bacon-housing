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
bugs = st.Page("apps/google_api.py", title="Bug reports", icon=":material/bug_report:")
bugs2 = st.Page("apps/google_api2.py", title="Bug reports", icon=":material/bug_report:")
bugs3 = st.Page("apps/single_agent.py", title="Single Agent - No Memory", icon=":material/bug_report:")
bugs4 = st.Page("apps/single_agent2.py", title="Single Agent - Memory", icon=":material/bug_report:")
alerts = st.Page(
    "apps/spiral3.py", title="System alerts", icon=":material/notification_important:"
)
# search = st.Page("tools/spiral.py", title="Search", icon=":material/search:")
# history = st.Page("tools/spiral2.py", title="History", icon=":material/history:")

# if st.session_state.logged_in:
pg = st.navigation(
    {
        # "Account": [logout_page],
        "Reports": [dashboard, bugs, bugs2, bugs3, bugs4, alerts],
        # "Tools": [search, history],
    }
)
# else:
# pg = st.navigation([login_page])

pg.run()
