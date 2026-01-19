"""
# Placeholder
"""

import streamlit as st

# # Adjust the width of the Streamlit page
# st.set_page_config(
#     page_title="Use Pygwalker In Streamlit",
#     layout="wide"
# )

# Add Title
st.title("Use Pygwalker In Streamlit")

# # You should cache your pygwalker renderer, if you don't want your memory to explode
# @st.cache_resource
# def get_pyg_renderer() -> "StreamlitRenderer":
#     uploaded_file = st.file_uploader("Upload a CSV file", type='csv')
#     if uploaded_file is not None:
#         df = pd.read_csv(uploaded_file)
#     # If you want to use feature of saving chart config, set `spec_io_mode="rw"`
#     return StreamlitRenderer(df, spec="./gw_config.json", spec_io_mode="rw")


# renderer = get_pyg_renderer()

renderer.explorer()
