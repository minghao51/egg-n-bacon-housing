from langchain.schema import ChatMessage
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import streamlit as st
from langchain_core.messages import HumanMessage
import os
from src.agent import general_agent
from langgraph.checkpoint.memory import MemorySaver

agent_executor = general_agent.create_agent_executor()

if "messages" not in st.session_state:
    st.session_state["messages"] = [ChatMessage(
        role="assistant", content="How can I help you?")]

for msg in st.session_state.messages:
    st.chat_message(msg.role).write(msg.content)

if prompt := st.chat_input():
    st.session_state.messages.append(ChatMessage(role="user", content=prompt))
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        config = {"configurable": {"thread_id": "abc123"}} # TODO: remove hardcode
        response = agent_executor.invoke(input = {"messages": [HumanMessage(content=prompt)]}, config = config)
        st.write(response['messages'][-1].content)
        st.session_state.messages.append(ChatMessage(role="assistant", content=response['messages'][-1].content))