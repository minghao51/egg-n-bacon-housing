
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI

def generate_response(input_text):
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", api_key=st.session_state['GOOGLE_API_KEY'])
    st.info(model.invoke(input_text))
    # convert_system_message_to_human=True, 

# with st.form("my_form"):
#     text = st.text_area(
#         "Enter text:",
#         "What are the three key pieces of advice for learning how to code?",
#     )
#     submitted = st.form_submit_button("Submit")
#     # if not openai_api_key.startswith("sk-"):
#     #     st.warning("Please enter your OpenAI API key!", icon="⚠")
#     # if submitted and openai_api_key.startswith("sk-"):
#     generate_response(text)

# with st.chat_message("user"):
#     st.write("Hello 👋")
#     st.line_chart(np.random.randn(30, 3))
    
with st.form('my_form'):
    text = st.text_area('Enter text:', 'Example prompt')
    submitted = st.form_submit_button('Submit')
    if submitted:
        response = generate_response(text)
        st.chat_message('content').markdown(response)

        st.write(response)