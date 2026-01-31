import os

import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent


@st.cache_resource
def create_agent_executor():
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest", api_key=os.environ['GOOGLE_API_KEY'])

    system_prompt = 'You are a virtual real estate agent.'
    memory = MemorySaver()
    agent_executor = create_react_agent(llm, tools=[], state_modifier=system_prompt, checkpointer = memory)

    return agent_executor
